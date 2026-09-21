"""URL-reference resolution shared by discovery and static analysis."""

from typing import Optional
from urllib.parse import urlsplit, urlunsplit


def _remove_dot_segments(path: str) -> str:
    """Remove literal dot segments without collapsing empty path segments."""
    segments = path.split('/')
    result = []
    for index, segment in enumerate(segments):
        if segment == '.':
            if index == len(segments) - 1:
                result.append('')
        elif segment == '..':
            if result and (len(result) > 1 or result[0] != ''):
                result.pop()
            if index == len(segments) - 1:
                result.append('')
        else:
            result.append(segment)
    return '/'.join(result)


def _authority(parsed) -> str:
    hostname = parsed.hostname
    if not hostname or any(character.isspace() or character in '/\\?#@' for character in hostname):
        raise ValueError('Invalid HTTP hostname')
    port = parsed.port  # Validates port syntax and range.
    if ':' in hostname:
        host = '[' + hostname.lower() + ']'
    else:
        if '%' in hostname:
            raise ValueError('Percent-encoded hostnames are not supported')
        host = hostname.encode('idna').decode('ascii').lower()
    userinfo = parsed.netloc.rsplit('@', 1)[0] + '@' if '@' in parsed.netloc else ''
    default_port = 443 if parsed.scheme.lower() == 'https' else 80
    return userinfo + host + (f':{port}' if port is not None and port != default_port else '')


def resolve_url(href: str, base_url: str) -> Optional[str]:
    """Resolve a URI reference, preserving duplicate slashes and query semantics.

    Only literal dot segments and HTTP authority case/default ports are
    normalized. Empty query values, query ordering, and fragments are retained.
    Invalid authorities are rejected without raising into a page analysis.
    """
    if not isinstance(href, str) or not isinstance(base_url, str):
        return None
    reference = href.strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in reference):
        return None
    try:
        ref = urlsplit(reference)
        base = urlsplit(base_url)
        has_query = '?' in reference.split('#', 1)[0]
        if ref.scheme:
            scheme, netloc, path, query = ref.scheme, ref.netloc, ref.path, ref.query
        elif ref.netloc:
            scheme, netloc, path, query = base.scheme, ref.netloc, ref.path, ref.query
        else:
            scheme, netloc = base.scheme, base.netloc
            if not ref.path:
                path = base.path
                query = ref.query if has_query else base.query
                has_query = has_query or '?' in base_url.split('#', 1)[0]
            else:
                if ref.path.startswith('/'):
                    path = ref.path
                else:
                    directory = base.path.rsplit('/', 1)[0] + '/' if '/' in base.path else ('/' if netloc else '')
                    path = directory + ref.path
                query = ref.query
        scheme = scheme.lower()
        if not scheme:
            return None
        if scheme in ('http', 'https'):
            path = _remove_dot_segments(path) or '/'
            parsed = urlsplit(urlunsplit((scheme, netloc, path, query, ref.fragment)))
            netloc = _authority(parsed)
        result = urlunsplit((scheme, netloc, path, query, ref.fragment))
        if has_query and not query:
            head, separator, fragment = result.partition('#')
            result = head + '?' + (separator + fragment if separator else '')
        if '#' in reference and not ref.fragment:
            result += '#'
        return result
    except (TypeError, ValueError, UnicodeError):
        return None


def is_internal_url(href: str, page_url: str, base_url: Optional[str] = None) -> bool:
    """Match the site hostname/port, allowing standard HTTP to HTTPS transitions."""
    resolved = resolve_url(href, base_url or page_url)
    page_resolved = resolve_url(page_url, page_url)
    if not resolved or not page_resolved:
        return False
    target, page = urlsplit(resolved), urlsplit(page_resolved)
    if target.scheme not in ('http', 'https') or page.scheme not in ('http', 'https'):
        return False
    target_host = (target.hostname or '').lower().rstrip('.')
    page_host = (page.hostname or '').lower().rstrip('.')
    default_target = 443 if target.scheme == 'https' else 80
    default_page = 443 if page.scheme == 'https' else 80
    target_port = target.port if target.port is not None else default_target
    page_port = page.port if page.port is not None else default_page
    return target_host == page_host and (
        target_port == page_port or (target_port == default_target and page_port == default_page)
    )


def classify_url(href: str, page_url: str, base_url: Optional[str] = None) -> str:
    resolved = resolve_url(href, base_url or page_url)
    if not resolved:
        return 'invalid'
    scheme = urlsplit(resolved).scheme
    if scheme in ('http', 'https'):
        return 'internal' if is_internal_url(href, page_url, base_url) else 'external'
    return {
        'mailto': 'email', 'tel': 'telephone', 'javascript': 'javascript',
        'data': 'data',
    }.get(scheme, 'other')
