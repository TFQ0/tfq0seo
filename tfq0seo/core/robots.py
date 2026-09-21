"""RFC 9309 path matching, retaining stdlib sitemap and pacing extensions."""

import re
from urllib.parse import quote, urlsplit
from urllib.robotparser import RobotFileParser


_UNRESERVED = frozenset(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~')


def _octets(value, *, pattern=False):
    # Keep escaped reserved characters distinct from their literal form (notably
    # %2F versus /), normalize hex case, and decode only unreserved ASCII.
    value = quote(value, safe="/%:?!&'()+,;=@-._~" + ('*$' if pattern else ''))

    def normalize(match):
        octet = int(match.group()[1:], 16)
        return chr(octet) if octet in _UNRESERVED else '%%%02X' % octet

    return re.sub(r'%[0-9a-fA-F]{2}', normalize, value)


def _matches(parts, anchored, path):
    """Match literal segments without a backtracking regular expression."""
    if not path.startswith(parts[0]):
        return False
    offset = len(parts[0])
    if len(parts) == 1:
        return not anchored or offset == len(path)
    for part in parts[1:-1]:
        offset = path.find(part, offset)
        if offset < 0:
            return False
        offset += len(part)
    last = parts[-1]
    if anchored:
        return path.endswith(last) and len(path) - len(last) >= offset
    return path.find(last, offset) >= 0


class RobotsRules(RobotFileParser):
    """Combine matching product groups; prefer the longest matching path.

    HTTP product names are matched case-insensitively, including a bot product
    in a compatible User-Agent header. Names containing digits remain supported
    for existing clients such as tfq0seo. Path matching is case-sensitive.
    """

    def __init__(self):
        super().__init__()
        self._groups = []

    def parse(self, lines):
        lines = list(lines)
        super().parse(lines)
        self._groups = []
        agents, rules, has_rules = [], [], False
        for line in lines:
            key, separator, value = line.partition('#')[0].partition(':')
            if not separator:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == 'user-agent':
                if has_rules:
                    self._groups.append((agents, rules))
                    agents, rules, has_rules = [], [], False
                if re.fullmatch(r'[A-Za-z0-9_-]+|\*', value):
                    agents.append(value.lower())
            elif key in ('allow', 'disallow') and agents:
                has_rules = True
                if not value.startswith(('/', '*')):
                    continue  # Empty paths have no matching effect.
                pattern = _octets(value, pattern=True)
                anchored = pattern.endswith('$')
                if anchored:
                    pattern = pattern[:-1]
                pattern = pattern.replace('$', '%24')
                parts = pattern.split('*')
                rules.append((sum(map(len, parts)), key == 'allow', parts, anchored))
        if agents:
            self._groups.append((agents, rules))

    def can_fetch(self, useragent, url):
        if self.disallow_all:
            return False
        if self.allow_all:
            return True
        if not self.last_checked:
            return False
        parsed = urlsplit(url)
        path = _octets(parsed.path or '/')
        if path == '/robots.txt':
            return True
        if parsed.query:
            path += '?' + _octets(parsed.query)
        products = {name.lower() for name in re.findall(
            r'(?:^|[\s(;])([A-Za-z0-9_-]+)(?=/|[\s;)]|$)', useragent)}
        groups = [rules for agents, rules in self._groups if products.intersection(agents)]
        if not groups:
            groups = [rules for agents, rules in self._groups if '*' in agents]
        best = (-1, True)
        for rules in groups:
            for length, allowed, parts, anchored in rules:
                if (length, allowed) > best and _matches(parts, anchored, path):
                    best = (length, allowed)
        return best[1]
