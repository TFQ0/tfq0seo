"""Robots path and group semantics, exercised without network access."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from tfq0seo.core.crawler import Crawler
from tfq0seo.core.robots import RobotsRules


@pytest.mark.parametrize('rules,path,allowed', [
    ('Disallow: /private/*', '/private/a', False),
    ('Disallow: /private/*', '/private/', False),
    ('Disallow: /private/*', '/private', True),
    ('Disallow: /\nAllow: /public', '/public/a', True),
    ('Allow: /public\nDisallow: /', '/public/a', True),
    ('Allow: /public\nDisallow: /public/private', '/public/private/a', False),
    ('Disallow: /same\nAllow: /same', '/same', True),
    ('Allow: /same\nDisallow: /same', '/same', True),
    ('Disallow: /*.pdf$', '/file.pdf', False),
    ('Disallow: *.gif$', '/path/image.gif', False),
    ('Disallow: /*.pdf$', '/file.pdf?download=1', True),
    ('Disallow: /foo$', '/foo/bar', True),
    ('Disallow: /foo$', '/foo#fragment', False),
    ('Disallow: /foo/*/bar$', '/foo/a/bar/b/bar', False),
    ('Disallow: /foo/*/bar$', '/foo/a/bar/b', True),
    ('Disallow: /*a*b*c$', '/abc', False),
    ('Disallow: /foo', '/Foo', True),
    ('Disallow: /foo', '/else/foo', True),
    ('Disallow: /search?q=private', '/search?q=private', False),
    ('Disallow: /caf\u00e9', '/caf%C3%A9', False),
    ('Disallow: /caf%c3%a9', '/caf\u00e9', False),
    ('Disallow: /%7Euser', '/~user', False),
    ('Disallow: /~user', '/%7euser', False),
    ('Disallow: /foo%2Fbar', '/foo/bar', True),
    ('Disallow: /foo%2fbar', '/foo%2Fbar', False),
    ('Disallow: /literal%2A$', '/literal*', False),
    ('Disallow: /literal%2A$', '/literal%2a', False),
    ('Disallow: /literal%24$', '/literal%24', False),
    ('Disallow: /literal%24$', '/literal$', False),
    ('Disallow: /literal$/file', '/literal$/file', False),
    ('Disallow: /hash%23part # comment', '/hash%23part', False),
    ('Disallow: / # comment', '/robots.txt', True),
    ('Disallow: \nAllow:', '/anything', True),
])
def test_path_rules_through_crawler(rules, path, allowed):
    async def run():
        crawler = Crawler({'respect_robots_txt': True, 'user_agent': 'AuditBot'})
        crawler._request = AsyncMock(return_value={
            'status_code': 200, 'content': ('User-agent: *\n' + rules).encode(),
        })
        assert await crawler.check_robots_txt('https://example.test' + path) is allowed
        assert await crawler.check_robots_txt('https://example.test' + path) is allowed
        assert crawler._request.await_count == 1
    asyncio.run(run())


@pytest.mark.parametrize('agent', ['AuditBot', 'auditbot/1.0', 'Mozilla/5.0 (compatible; AuditBot/1.0)'])
def test_matching_groups_combine_and_ignore_wildcard_fallback(agent):
    parser = RobotsRules()
    parser.parse('''User-agent: *
Disallow: /
User-agent: AuditBot
Disallow: /private
User-agent: OtherBot
Disallow: /public
User-agent: AUDITBOT
Allow: /private/public
Disallow: /other
'''.splitlines())
    assert not parser.can_fetch(agent, 'https://example.test/private')
    assert not parser.can_fetch(agent, 'https://example.test/other')
    assert parser.can_fetch(agent, 'https://example.test/private/public')
    assert parser.can_fetch(agent, 'https://example.test/public')


def test_empty_lines_unknown_records_and_multiple_agents_do_not_split_group():
    parser = RobotsRules()
    parser.parse('''Disallow: /ignored
User-agent: AuditBot

Sitemap: https://example.test/sitemap.xml
User-agent: SecondBot
Unknown: value
Disallow: /private
Crawl-delay: 2
Request-rate: 1/5
'''.splitlines())
    for agent in ('AuditBot', 'SecondBot'):
        assert not parser.can_fetch(agent, 'https://example.test/private')
        assert parser.can_fetch(agent, 'https://example.test/ignored')
    assert parser.can_fetch('AuditBotOther', 'https://example.test/private')
    assert parser.site_maps() == ['https://example.test/sitemap.xml']
    assert parser.crawl_delay('SecondBot') == 2
    assert parser.request_rate('SecondBot').seconds == 5


def test_wildcard_groups_combine_and_trailing_empty_specific_group_allows():
    parser = RobotsRules()
    parser.parse('User-agent: *\nDisallow: /a\nUser-agent: *\nDisallow: /b\nUser-agent: AuditBot'.splitlines())
    assert not parser.can_fetch('OtherBot', 'https://example.test/a')
    assert not parser.can_fetch('OtherBot', 'https://example.test/b')
    assert parser.can_fetch('AuditBot', 'https://example.test/a')


def test_many_wildcards_do_not_require_exponential_backtracking():
    parser = RobotsRules()
    parser.parse(['User-agent: *', 'Disallow: /' + '*a' * 200 + 'b$'])
    assert parser.can_fetch('AuditBot', 'https://example.test/' + 'a' * 10000)
