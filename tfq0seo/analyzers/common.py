"""Shared parsing of observed page facts used by the analyzers."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit
from ..urls import classify_url, is_internal_url, resolve_url
from ..rules import rule_result


def make_issue(category: str, severity: str, message: str,
               details: Optional[Dict] = None, rule_id: Optional[str] = None,
               evidence: Optional[Any] = None, source: str = 'html',
               confidence: str = 'high', applicable: Optional[bool] = True,
               status: str = 'fail', reason: str = '') -> Dict[str, Any]:
    """Compatibility adapter; IDs and evidence are mandatory for new findings.

    Severity and recommendations come from the registry, never message text.
    The positional severity argument remains accepted for existing callers.
    """
    return rule_result(rule_id, evidence, message=message, category=category,
                       status=status, applicable=applicable, reason=reason,
                       source=source, confidence=confidence, details=details)


def heading_facts(soup: Any) -> Dict[str, Any]:
    """Extract headings and check level transitions in document order."""
    headings = {f'h{level}': [] for level in range(1, 7)}
    issues = []
    findings = []
    previous_level = 0
    for position, heading in enumerate(soup.find_all(re.compile(r'^h[1-6]$'))):
        text = heading.get_text(' ', strip=True)
        headings[heading.name].append({'text': text, 'length': len(text)})
        if not text:
            message = f'Empty {heading.name.upper()} heading'
            issues.append(message)
            findings.append({'rule_id': 'headings.empty', 'message': message,
                             'evidence': {'tag': heading.name, 'position': position, 'text': text}})
        level = int(heading.name[1])
        if previous_level and level > previous_level + 1:
            message = f'Heading hierarchy broken: H{previous_level} followed by H{level}'
            issues.append(message)
            findings.append({'rule_id': 'headings.skipped_level', 'message': message,
                             'evidence': {'previous_level': previous_level, 'level': level, 'position': position}})
        previous_level = level
    if not headings['h1']:
        issues.append('No H1 tag found')
        findings.append({'rule_id': 'headings.missing_h1', 'message': 'No H1 tag found',
                         'evidence': {'h1_count': 0}})
    lengths = [heading['length'] for group in headings.values() for heading in group]
    return {
        'headings': headings, 'total_count': len(lengths),
        'hierarchy_valid': not issues,
        'average_length': round(sum(lengths) / len(lengths), 1) if lengths else 0,
        'issues': issues,
        'findings': findings,
    }


def document_base_url(soup: Any, page_url: str) -> str:
    """Honor the first HTML base href when it resolves to an HTTP URL."""
    base = soup.find('base', href=True)
    if base:
        resolved = resolve_url(base.get('href', ''), page_url)
        if resolved and urlsplit(resolved).scheme.lower() in ('http', 'https'):
            return resolved
    return page_url








def header_values(headers: Any, name: str) -> List[str]:
    """Read all instances, including multidicts and list-valued mappings."""
    if headers is None:
        return []
    if hasattr(headers, 'getall'):
        try:
            return [str(value) for value in headers.getall(name)]
        except KeyError:
            pass
    values = []
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            if isinstance(value, (list, tuple)):
                values.extend(str(item) for item in value)
            else:
                values.append(str(value))
    return values


def normalized_headers(headers: Any) -> Dict[str, str]:
    if headers is None:
        return {}
    return {str(key).lower(): ', '.join(header_values(headers, str(key))) for key in headers}


_HTTP_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
_URI_CHARACTERS = re.compile(r"[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*")
_CANONICAL_QUALIFIERS = {'hreflang', 'lang', 'media', 'type'}


def _valid_uri_reference(value: str, allow_iri: bool = False) -> bool:
    """Reject malformed references before the deliberately permissive URL resolver."""
    if re.search(r'%(?![0-9A-Fa-f]{2})', value) or value.count('#') > 1:
        return False
    if allow_iri:
        if any(character.isspace() or ord(character) < 32 or ord(character) == 127
               or character in '<>"{}|\\^`' for character in value):
            return False
    elif not _URI_CHARACTERS.fullmatch(value):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.netloc:
            parsed.port  # Validate any authority's port spelling and range.
    except ValueError:
        return False
    if (parsed.scheme.lower() in ('http', 'https') or (not parsed.scheme and parsed.netloc)) and not resolve_url(
            value, 'https://canonical-context.invalid/'):
        return False
    return bool(parsed.scheme or ':' not in parsed.path.split('/', 1)[0])


def _canonical_target(href: Any, base_url: str, *, html: bool = False) -> Optional[str]:
    if not isinstance(href, str):
        return None
    value = href.strip() if html else href
    if (html and not value) or not _valid_uri_reference(value, allow_iri=html):
        return None
    resolved = resolve_url(value, base_url)
    return resolved if resolved and urlsplit(resolved).scheme in ('http', 'https') else None


def _split_link_values(value: str) -> List[str]:
    """Split the HTTP list without splitting commas in targets or quoted strings.

    Unbalanced delimiters keep the remainder together, so it cannot accidentally
    become a valid canonical declaration after a malformed quoted parameter.
    """
    values, start = [], 0
    in_target = in_quote = escaped = False
    for index, character in enumerate(value):
        if in_target:
            if character == '>':
                in_target = False
        elif in_quote:
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == '"':
                in_quote = False
        elif character == '<':
            in_target = True
        elif character == '"':
            in_quote = True
        elif character == ',':
            if value[start:index].strip(' \t'):
                values.append(value[start:index].strip(' \t'))
            start = index + 1
    if value[start:].strip(' \t'):
        values.append(value[start:].strip(' \t'))
    return values


def _parse_link_value(value: str):
    """Parse RFC 8288 link parameters; return safe partial evidence on failure."""
    parameters = []
    if not value.startswith('<') or '>' not in value:
        return None, parameters, 'Malformed HTTP Link target syntax.'
    end = value.index('>')
    href, position = value[1:end], end + 1
    while position < len(value):
        if value[position] in ' \t':
            position += 1
            continue
        if value[position] != ';':
            return href, parameters, 'Malformed HTTP Link parameter separator.'
        position += 1
        while position < len(value) and value[position] in ' \t':
            position += 1
        match = _HTTP_TOKEN.match(value, position)
        if not match:
            return href, parameters, 'Malformed HTTP Link parameter name.'
        name, position = match.group().lower(), match.end()
        while position < len(value) and value[position] in ' \t':
            position += 1
        parameter = None
        if position < len(value) and value[position] == '=':
            position += 1
            while position < len(value) and value[position] in ' \t':
                position += 1
            if position < len(value) and value[position] == '"':
                position += 1
                characters = []
                closed = False
                while position < len(value):
                    character = value[position]
                    position += 1
                    if character == '"':
                        closed = True
                        break
                    if character == '\\':
                        if position == len(value):
                            break
                        character = value[position]
                        position += 1
                    if (ord(character) < 32 and character != '\t') or ord(character) == 127 or ord(character) > 255:
                        return href, parameters, 'Invalid character in HTTP Link quoted parameter.'
                    characters.append(character)
                if not closed:
                    return href, parameters, 'Unterminated HTTP Link quoted parameter.'
                parameter = ''.join(characters)
            else:
                match = _HTTP_TOKEN.match(value, position)
                if not match:
                    return href, parameters, 'Malformed HTTP Link parameter value.'
                parameter, position = match.group(), match.end()
        parameters.append((name, parameter))
    if not _valid_uri_reference(href):
        return href, parameters, 'Malformed HTTP Link URI reference.'
    return href, parameters, ''


def canonical_facts(link_tags: List[Dict[str, Any]], page_url: str,
                    base_url: str, headers: Any = None) -> Dict[str, Any]:
    """Observe canonical declarations without treating parse failures as absence.

    HTTP Link syntax and context follow RFC 8288 sections 3.1-3.3. Eligibility
    also applies Google Search's head placement and alternate-attribute rules:
    https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
    No raw header or unrelated parameter values are retained in these facts.
    """
    declarations, parse_errors = [], 0
    for link in link_tags:
        attrs = {name.lower(): value for name, value in link['attrs'].items()}
        rel = attrs.get('rel') or []
        rel = rel.split() if isinstance(rel, str) else rel
        if 'canonical' not in [token.lower() for token in rel]:
            continue
        href = attrs.get('href')
        href = href if isinstance(href, str) else None
        target = _canonical_target(href, base_url, html=True)
        reasons = []
        if not link.get('in_head', False):
            reasons.append('HTML canonical declaration is outside the head.')
        if _CANONICAL_QUALIFIERS.intersection(attrs):
            reasons.append('Canonical declaration has alternate-version attributes.')
        if target is None:
            reasons.append('Canonical target is missing or is not a valid HTTP(S) URL.')
        declarations.append({'href': href, 'url': target, 'source': 'html',
                             'eligible': not reasons, 'reason': ' '.join(reasons)})

    response_url = _canonical_target(page_url, page_url)
    for field_value in header_values(headers, 'Link'):
        for value in _split_link_values(field_value):
            href, parameters, error = _parse_link_value(value)
            rel_values = [parameter for name, parameter in parameters if name == 'rel']
            anchors = [parameter for name, parameter in parameters if name == 'anchor']
            if len(rel_values) != 1 or not (rel_values[0] or '').strip():
                error = error or 'HTTP Link requires one nonempty rel parameter.'
            elif any(not (re.fullmatch(r'[a-z][a-z0-9.-]*', token, re.I) or
                          (_valid_uri_reference(token) and urlsplit(token).scheme))
                     for token in rel_values[0].split()):
                error = error or 'Malformed HTTP Link relation type.'
            if len(anchors) > 1 or (anchors and (anchors[0] is None or not _valid_uri_reference(anchors[0]))):
                error = error or 'HTTP Link anchor context is malformed or repeated.'
            if error:
                parse_errors += 1
            # Keep recognizable canonical evidence from malformed parameters,
            # but never use any part of that link-value as an eligible edge.
            if not any('canonical' in (parameter or '').lower().split() for parameter in rel_values):
                continue
            target = _canonical_target(href, page_url)
            reasons = [error] if error else []
            if anchors and not error and _canonical_target(anchors[0], page_url) != response_url:
                reasons.append('HTTP Link anchor identifies a different context.')
            if _CANONICAL_QUALIFIERS.intersection(name for name, _ in parameters):
                reasons.append('Canonical declaration has alternate-version attributes.')
            if target is None:
                reasons.append('Canonical target is not a valid HTTP(S) URL.')
            declarations.append({'href': href, 'url': target, 'source': 'http_link',
                                 'eligible': not reasons, 'reason': ' '.join(reasons)})
    return {'declarations': declarations, 'headers_checked': headers is not None,
            'parse_errors': parse_errors}


_VALUE_DIRECTIVES = {'max-snippet', 'max-image-preview', 'max-video-preview', 'unavailable_after'}
_FLAG_DIRECTIVES = {'all', 'none', 'index', 'noindex', 'follow', 'nofollow', 'nosnippet',
                    'noarchive', 'notranslate', 'noimageindex', 'indexifembedded'}


def _parse_directives(value: str, user_agent: str, scoped: bool) -> Dict[str, List[str]]:
    found = {}
    agent = None
    for part in value.split(','):
        part = part.strip().lower()
        if not part:
            continue
        name, separator, argument = part.partition(':')
        name = name.strip()
        if scoped and separator and name not in _VALUE_DIRECTIVES:
            agent = name
            part = argument.strip()
            name, separator, argument = part.partition(':')
            name = name.strip()
        if agent not in (None, '*', user_agent):
            continue
        if name in _VALUE_DIRECTIVES and separator:
            found.setdefault(name, []).append(argument.strip())
        elif name in _FLAG_DIRECTIVES and not separator:
            found.setdefault(name, []).append('')
    return found


def parse_robots(soup: Any, headers: Any = None, user_agent: str = 'googlebot') -> Dict[str, Any]:
    """Combine applicable robots directives; restrictive flags always win."""
    user_agent = user_agent.lower()
    evidence = []
    directives = {}
    for meta in soup.find_all('meta'):
        name = str(meta.get('name', '')).strip().lower()
        if name in ('robots', user_agent):
            value = str(meta.get('content', ''))
            evidence.append({'source': 'meta', 'name': name, 'value': value})
            for key, values in _parse_directives(value, user_agent, False).items():
                directives.setdefault(key, []).extend(values)
    for value in header_values(headers, 'X-Robots-Tag'):
        evidence.append({'source': 'header', 'name': 'X-Robots-Tag', 'value': value})
        for key, values in _parse_directives(value, user_agent, True).items():
            directives.setdefault(key, []).extend(values)
    flags = set(directives)
    if 'none' in flags:
        flags.update(('noindex', 'nofollow'))
    snippet_values = []
    for value in directives.get('max-snippet', []):
        try:
            snippet_values.append(int(value))
        except ValueError:
            pass
    limited_snippets = [value for value in snippet_values if value >= 0]
    return {
        'user_agent': user_agent, 'status': 'observed', 'source': 'html_and_headers',
        'directives': sorted(flags), 'evidence': evidence,
        'headers_checked': headers is not None,
        'noindex': 'noindex' in flags, 'nofollow': 'nofollow' in flags,
        'nosnippet': 'nosnippet' in flags, 'noarchive': 'noarchive' in flags,
        'max_snippet': min(limited_snippets) if limited_snippets else (-1 if snippet_values else None),
        'indexability': 'blocked_by_robots' if 'noindex' in flags else 'no_blocking_directive_observed',
    }


def is_nonblocking_script(script: Any) -> bool:
    has_attr = getattr(script, 'has_attr', None)
    has_async = has_attr('async') if callable(has_attr) else 'async' in script
    has_defer = has_attr('defer') if callable(has_attr) else 'defer' in script
    return has_async or has_defer or str(script.get('type', '')).lower() == 'module'


def score_grade(score: float) -> str:
    return 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
