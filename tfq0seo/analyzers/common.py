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
