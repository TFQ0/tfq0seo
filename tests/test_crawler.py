"""Crawler regressions use loopback HTTP or bounded coroutine fixtures only."""

import asyncio
import time
from collections import Counter
from contextlib import asynccontextmanager

import pytest
from aiohttp import web
from bs4 import BeautifulSoup

from tfq0seo.core.crawler import Crawler, RateLimiter


def config(**overrides):
    return {
        'respect_robots_txt': False,
        'use_sitemap': False,
        'adaptive_delay': False,
        'max_retries': 0,
        'retry_backoff_factor': 0,
        **overrides,
    }


@asynccontextmanager
async def serve(handler):
    app = web.Application()
    app.router.add_get('/{path:.*}', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield f'http://127.0.0.1:{port}'
    finally:
        await runner.cleanup()


def html(text='<html><title>Page</title><body>Hello</body></html>', status=200):
    return web.Response(body=text.encode('utf-8'), status=status,
                        headers={'Content-Type': 'text/html'})


def test_canonical_configuration_overrides_legacy_aliases():
    crawler = Crawler(config(
        max_page_size=2048, max_content_length=4096,
        max_retries=0, retry_attempts=5,
        use_sitemap=False, follow_sitemap=True,
        adaptive_delay=False, adaptive_throttle=True,
        delay_between_requests=0.01, rate_limit_per_second=20,
    ))
    assert crawler.max_content_length == 2048
    assert crawler.retry_attempts == 0
    assert crawler.follow_sitemap is False
    assert crawler.adaptive_throttle is False
    assert crawler.rate_limiter.delay == 0.05
    assert crawler.verify_ssl is True
    legacy = Crawler({'max_content_length': 4096, 'retry_attempts': 2,
                      'follow_sitemap': False, 'adaptive_throttle': False})
    assert legacy.max_content_length == 4096
    assert legacy.retry_attempts == 2
    assert legacy.follow_sitemap is False
    assert legacy.adaptive_throttle is False


@pytest.mark.parametrize('setting', [
    {'max_concurrent': 0}, {'max_concurrent': 1.5}, {'max_pages': 0},
    {'timeout': float('nan')}, {'max_crawl_time': -1},
    {'max_page_size': 0}, {'max_retries': -1},
    {'rate_limit_per_second': 0}, {'excluded_patterns': ['[']},
    {'verify_ssl': 'false'}, {'allowed_schemes': ['file']},
])
def test_invalid_configuration_fails_before_session(setting):
    with pytest.raises(ValueError):
        Crawler(setting)


@pytest.mark.parametrize('left,right', [
    ('/Product', '/product'), ('/?id=AbC', '/?id=abc'),
    ('/a/', '/a'), ('/a//b', '/a/b'),
    ('/?ref=a', '/?ref=b'), ('/?source=a', '/?source=b'),
    ('/?key=', '/'), ('/?', '/'), ('/?a=1&b=2', '/?b=2&a=1'),
])
def test_url_identity_preserves_path_and_query_semantics(left, right):
    crawler = Crawler()
    assert crawler.normalize_url('https://example.test' + left) != crawler.normalize_url('https://example.test' + right)


def test_url_identity_normalizes_only_safe_authority_and_fragment():
    crawler = Crawler()
    assert crawler.normalize_url('HTTPS://EXAMPLE.TEST:443/Page?Id=AbC#part') == 'https://example.test/Page?Id=AbC'
    assert crawler.normalize_url('https://www.example.test/') != crawler.normalize_url('https://example.test/')


def test_hostname_scope_and_explicit_wildcards():
    crawler = Crawler({'allowed_domains': ['example.test']})
    assert crawler.is_valid_url('https://example.test/a', 'https://example.test/')
    assert not crawler.is_valid_url('https://example.test.attacker.test/a', 'https://example.test/')
    assert not crawler.is_valid_url('https://child.example.test/a', 'https://example.test/')
    wildcard = Crawler({'allowed_domains': ['*.example.test']})
    assert wildcard.is_valid_url('https://child.example.test/a', 'https://example.test/')
    assert not wildcard.is_valid_url('https://example.test/a', 'https://example.test/')
    assert not wildcard.is_valid_url('https://badexample.test/a', 'https://example.test/')
    default = Crawler()
    assert default.is_valid_url('https://example.test/a', 'http://example.test/')
    assert default.is_valid_url('https://example.test:443/a', 'http://example.test:80/')
    assert not default.is_valid_url('http://example.test:8001/a', 'http://example.test:8000/')
    assert not default.is_valid_url('https://www.example.test/a', 'https://example.test/')


def test_charset_free_html_and_optional_storage(http_site):
    base, routes, _ = http_site
    routes['/plain'] = (200, {'Content-Type': 'text/html'}, '<html><title>Plain</title></html>')
    routes['/encoded'] = (200, {'Content-Type': 'text/html'},
                          b'<html><meta charset="windows-1252"><title>Caf\xe9</title></html>')

    async def run():
        async with Crawler(config(store_html=False)) as crawler:
            plain = await crawler.fetch_page(base + '/plain')
            encoded = await crawler.fetch_page(base + '/encoded')
        assert plain['status_code'] == 200 and 'error' not in plain
        assert plain['soup'].title.string == 'Plain'
        assert 'html' not in plain
        assert encoded['soup'].title.string == 'Café'
        assert encoded['requested_url'] == base + '/encoded'
    asyncio.run(run())


def test_transport_honors_verified_tls_timeout_and_headers(monkeypatch):
    async def run():
        async def handler(request):
            assert request.headers['User-Agent'] == 'TestBot'
            assert request.headers['X-Audit'] == 'yes'
            return html()
        async with serve(handler) as base:
            async with Crawler(config(custom_headers={'user-agent': 'TestBot', 'X-Audit': 'yes'},
                                      timeout=3, connect_timeout=1, read_timeout=2)) as crawler:
                original = crawler.session.get
                calls = []

                def get(url, **kwargs):
                    calls.append(kwargs)
                    return original(url, **kwargs)
                monkeypatch.setattr(crawler.session, 'get', get)
                result = await crawler.fetch_page(base + '/')
                assert crawler.session.timeout.total == 3
                assert crawler.session.timeout.sock_read == 2
                assert crawler.session.timeout.sock_connect == 1
            assert 'error' not in result
            assert calls[0]['ssl'] is True
            assert calls[0]['allow_redirects'] is False
    asyncio.run(run())


def test_connection_pooling_can_be_disabled():
    async def run():
        async with Crawler(config(use_connection_pooling=False)) as crawler:
            assert crawler.session.connector.force_close is True
    asyncio.run(run())


def test_repeated_robots_headers_preserve_all_directives():
    async def run():
        async def handler(request):
            return web.Response(body=b'<html><title>Page</title></html>', headers=[
                ('Content-Type', 'text/html'),
                ('X-Robots-Tag', 'noindex'),
                ('X-Robots-Tag', 'nofollow'),
            ])
        async with serve(handler) as base:
            async with Crawler(config()) as crawler:
                result = await crawler.fetch_page(base + '/')
            assert result['headers']['X-Robots-Tag'] == ['noindex', 'nofollow']
    asyncio.run(run())


def test_timeout_retries_and_retains_terminal_failure():
    async def run():
        counts = Counter()
        async def handler(request):
            counts[request.path] += 1
            if request.path == '/always' or counts[request.path] == 1:
                await asyncio.sleep(0.08)
            return html()
        async with serve(handler) as base:
            async with Crawler(config(timeout=0.025, max_retries=1)) as crawler:
                success = await crawler.fetch_page(base + '/once')
                failed = await crawler.fetch_page(base + '/always')
            assert counts['/once'] == counts['/always'] == 2
            assert success['status_code'] == 200
            assert failed['status_code'] == 0 and failed['error'] == 'Timeout'
            assert crawler.failed_urls[base + '/always'] == 'Timeout'
    asyncio.run(run())


def test_retryable_status_and_retry_after_are_enforced():
    async def run():
        starts = []
        async def handler(request):
            starts.append(time.monotonic())
            if len(starts) == 1:
                return web.Response(status=429, headers={'Retry-After': '0.04'})
            return html()
        async with serve(handler) as base:
            async with Crawler(config(max_retries=1)) as crawler:
                result = await crawler.fetch_page(base + '/')
            assert result['status_code'] == 200
            assert len(starts) == 2
            assert starts[1] - starts[0] >= 0.035
            assert crawler.stats.rate_limit_hits == 1
    asyncio.run(run())


def test_http_errors_are_terminal_results_after_retries(http_site):
    base, routes, requests = http_site
    routes['/unavailable'] = (503, {'Content-Type': 'text/html'}, '<title>Unavailable</title>')
    async def run():
        async with Crawler(config(max_retries=2)) as crawler:
            rows = await crawler.crawl_urls([base + '/unavailable'])
        assert requests.count('/unavailable') == 3
        assert len(rows) == 1 and rows[0]['error'] == 'HTTP 503'
        assert rows[0]['status_code'] == 503
        assert crawler.get_statistics()['failed_pages'] == 1
    asyncio.run(run())


def test_truncated_response_is_marked_incomplete(http_site):
    base, routes, _ = http_site
    routes['/large'] = (200, {'Content-Type': 'text/html'}, '<html>' + 'x' * 1000 + '</html>')
    async def run():
        async with Crawler(config(max_page_size=64)) as crawler:
            result = await crawler.fetch_page(base + '/large')
        assert result['truncated'] is True
        assert result['content_length'] == 64
        assert 'max_page_size' in result['error']
        assert 'soup' not in result
        assert 'max_page_size' in crawler.get_statistics()['limits_reached']
    asyncio.run(run())


def test_download_time_includes_streamed_body(monkeypatch):
    async def run():
        reading_body = asyncio.Event()
        read_bounded = Crawler._read_bounded

        async def observed_read(crawler, response, limit):
            reading_body.set()
            return await read_bounded(crawler, response, limit)

        monkeypatch.setattr(Crawler, '_read_bounded', observed_read)

        async def handler(request):
            response = web.StreamResponse(headers={'Content-Type': 'text/html'})
            await response.prepare(request)
            await response.write(b'<html>')
            # Start the delay only after the client records header arrival.
            # Otherwise scheduling can move part of it into headers_seconds.
            await reading_body.wait()
            body_ready = time.monotonic() + 0.06
            while True:
                remaining = body_ready - time.monotonic()
                if remaining <= 0:
                    break
                await asyncio.sleep(remaining)
            await response.write(b'<title>Delayed body</title></html>')
            await response.write_eof()
            return response
        async with serve(handler) as base:
            async with Crawler(config()) as crawler:
                result = await crawler.fetch_page(base + '/')
            assert result['load_time'] >= 0.05
            assert result['timings']['download_seconds'] >= 0.05
            assert result['soup'].title.string == 'Delayed body'
    asyncio.run(run())


def test_redirect_uses_final_url_and_html_base_for_discovery(http_site):
    base, routes, requests = http_site
    routes['/old'] = (302, {'Location': '/new/'}, '')
    routes['/new/'] = (200, {'Content-Type': 'text/html'},
                       '<html><base href="/assets/"><a href="child">Child</a></html>')
    routes['/assets/child'] = (200, {'Content-Type': 'text/html'}, '<title>Child</title>')
    async def run():
        async with Crawler(config(max_pages=5)) as crawler:
            rows = await crawler.crawl_site(base + '/old')
        assert len(rows) == 2
        assert rows[0]['url'] == base + '/new/'
        assert rows[0]['requested_url'] == base + '/old'
        assert rows[0]['redirect_chain'][0]['status_code'] == 302
        assert rows[0]['depth'] == 0
        assert rows[1]['depth'] == 1
        assert rows[1]['parent_url'] == base + '/new/'
        assert '/assets/child' in requests and '/child' not in requests
    asyncio.run(run())


def test_malformed_links_and_redirect_locations_do_not_abort_crawl(http_site):
    base, routes, requests = http_site
    routes['/'] = (200, {'Content-Type': 'text/html'},
                   '<base href="http://["><a href="http://[">Invalid</a><a href="/good">Good</a>')
    routes['/good'] = (200, {'Content-Type': 'text/html'}, '<title>Good</title>')
    routes['/redirect'] = (302, {'Location': 'http://['}, '')
    async def run():
        async with Crawler(config()) as crawler:
            rows = await crawler.crawl_site(base + '/')
            invalid = await crawler.fetch_page(base + '/redirect')
        assert len(rows) == 2
        assert '/good' in requests
        assert invalid['error'] == 'Invalid redirect Location'
    asyncio.run(run())


def test_relative_links_preserve_duplicate_slashes():
    crawler = Crawler(config())
    soup = BeautifulSoup('<a href="a//b?key=&key=Two">Page</a>', 'html.parser')
    assert crawler.extract_links(soup, 'https://example.test/dir/') == [
        ('https://example.test/dir/a//b?key=&key=Two', 5),
    ]


def test_duplicate_batch_seeds_do_not_consume_page_budget(http_site):
    base, routes, requests = http_site
    routes['/a'] = routes['/b'] = (200, {'Content-Type': 'text/html'}, '<title>Page</title>')
    async def run():
        async with Crawler(config(max_pages=2)) as crawler:
            rows = await crawler.crawl_urls([base + '/a#one', base + '/a#two', base + '/b'])
        assert len(rows) == 2
        assert sorted(requests) == ['/a', '/b']
    asyncio.run(run())


def test_off_scope_redirect_is_blocked_but_explicit_batch_seeds_work():
    async def run():
        off_scope_requests = []
        async def outside(request):
            off_scope_requests.append(request.path)
            return html()
        async with serve(outside) as outside_base:
            async def inside(request):
                if request.path == '/redirect':
                    raise web.HTTPFound(outside_base + '/unexpected')
                return html()
            async with serve(inside) as base:
                async with Crawler(config()) as crawler:
                    blocked = await crawler.fetch_page(base + '/redirect')
                    assert blocked['skipped'] is True
                    assert not off_scope_requests
                    rows = await crawler.crawl_urls([base + '/one', outside_base + '/requested'])
                assert len(rows) == 2
                assert all(row['status_code'] == 200 for row in rows)
                assert off_scope_requests == ['/requested']
    asyncio.run(run())


def test_page_budget_reserves_inflight_requests_and_depth_zero(http_site):
    base, routes, requests = http_site
    routes['/'] = (200, {'Content-Type': 'text/html'},
                    ''.join(f'<a href="/p{i}">Page</a>' for i in range(10)))
    for i in range(10):
        routes[f'/p{i}'] = (200, {'Content-Type': 'text/html'}, '<title>Page</title>')
    async def run():
        async with Crawler(config(max_pages=2, max_concurrent=8)) as crawler:
            rows = await crawler.crawl_site(base + '/')
        assert len(rows) == len(requests) == 2
        requests.clear()
        async with Crawler(config(max_depth=0, max_pages=10)) as crawler:
            rows = await crawler.crawl_site(base + '/')
        assert len(rows) == len(requests) == 1
        assert 'max_depth' in crawler.limit_reasons
    asyncio.run(run())


def test_depth_priority_preserves_shallow_coverage():
    async def run():
        counts = Counter()
        async def handler(request):
            counts[request.path] += 1
            if request.path == '/':
                return html('<a href="/fast">Fast</a><a href="/slow">Slow</a>')
            if request.path == '/fast':
                return html('<a href="/middle">Middle</a>')
            if request.path == '/slow':
                await asyncio.sleep(0.03)
                return html('<a href="/shared">Shared</a>')
            if request.path == '/middle':
                return html('<a href="/shared">Shared</a>')
            if request.path == '/shared':
                return html('<a href="/leaf">Leaf</a>')
            return html()
        async with serve(handler) as base:
            async with Crawler(config(max_depth=3)) as crawler:
                await crawler.crawl_site(base + '/')
            assert counts['/leaf'] == 1
            assert counts['/shared'] == 1
    asyncio.run(run())


def test_rate_limiter_serializes_origin_starts_and_honors_floor():
    async def run():
        limiter = RateLimiter(initial_delay=0.02)
        limiter.set_minimum_delay('a', 0.03)
        for _ in range(20):
            limiter.record_response('a', 0.001)
        starts = []
        async def wait():
            await limiter.wait('a')
            starts.append(time.monotonic())
        await asyncio.gather(*(wait() for _ in range(4)))
        assert all(right - left >= 0.025 for left, right in zip(starts, starts[1:]))
        assert len(limiter.response_times['a']) == 10
    asyncio.run(run())


def test_robots_is_cached_uses_request_identity_and_blocks_paths():
    async def run():
        counts = Counter()
        async def handler(request):
            counts[request.path] += 1
            assert request.headers['User-Agent'] == 'AuditBot'
            if request.path == '/robots.txt':
                return web.Response(text='User-agent: AuditBot\nDisallow: /private\n')
            return html()
        async with serve(handler) as base:
            async with Crawler(config(respect_robots_txt=True, user_agent='AuditBot')) as crawler:
                results = await crawler.crawl_urls([base + '/public', base + '/private', base + '/other'])
            assert counts['/robots.txt'] == 1
            assert counts['/private'] == 0
            assert len(results) == 3
            assert next(r for r in results if r['url'].endswith('/private'))['error'] == 'Blocked by robots.txt'
    asyncio.run(run())


def test_unreachable_robots_does_not_allow_crawl(http_site):
    base, routes, requests = http_site
    routes['/robots.txt'] = (503, {}, '')
    routes['/'] = (200, {'Content-Type': 'text/html'}, '<title>Private</title>')
    async def run():
        async with Crawler(config(respect_robots_txt=True)) as crawler:
            result = await crawler.fetch_page(base + '/')
        assert result['error'] == 'Blocked by robots.txt'
        assert requests == ['/robots.txt']
    asyncio.run(run())


def test_sitemap_parser_needs_no_lxml_handles_cycles_and_over_100_urls(http_site, monkeypatch):
    base, routes, requests = http_site
    monkeypatch.setattr('tfq0seo.core.crawler.PARSER', 'html.parser')
    routes['/index.xml'] = (200, {'Content-Type': 'application/xml'},
                           f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                           f'<sitemap><loc>{base}/index.xml</loc></sitemap>'
                           f'<sitemap><loc>{base}/pages.xml</loc></sitemap></sitemapindex>')
    routes['/pages.xml'] = (200, {'Content-Type': 'application/xml'},
                           '<urlset>' + ''.join(f'<url><loc>{base}/page/{i}</loc></url>' for i in range(150)) + '</urlset>')
    async def run():
        async with Crawler(config(max_pages=200)) as crawler:
            urls = await crawler.parse_sitemap(base + '/index.xml')
        assert len(urls) == 150
        assert requests == ['/index.xml', '/pages.xml']
    asyncio.run(run())


def test_sitemap_scope_applies_to_child_indexes_and_page_locations(http_site):
    base, routes, requests = http_site
    routes['/index.xml'] = (200, {'Content-Type': 'application/xml'},
                           '<sitemapindex><sitemap><loc>http://127.0.0.1:1/child.xml</loc></sitemap>'
                           '<sitemap><loc>/pages.xml</loc></sitemap></sitemapindex>')
    routes['/pages.xml'] = (200, {'Content-Type': 'application/xml'},
                           '<urlset><url><loc>http://127.0.0.1:1/offscope</loc></url>'
                           '<url><loc>/excluded/page</loc></url><url><loc>/ok</loc></url></urlset>')
    async def run():
        async with Crawler(config(excluded_patterns=['/excluded/'])) as crawler:
            urls = await crawler.parse_sitemap(base + '/index.xml')
        assert urls == [base + '/ok']
        assert requests == ['/index.xml', '/pages.xml']
        assert len(crawler.discovery_errors) == 3
    asyncio.run(run())


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
def test_sitemap_rejects_dtd_and_entities(http_site, encoding):
    base, routes, requests = http_site
    payload = '<?xml version="1.0"?><!DOCTYPE urlset [<!ENTITY secret SYSTEM "file:///not-read">]><urlset><url><loc>&secret;</loc></url></urlset>'
    routes['/unsafe.xml'] = (200, {'Content-Type': 'application/xml'}, payload.encode(encoding))
    async def run():
        async with Crawler(config()) as crawler:
            urls = await crawler.parse_sitemap(base + '/unsafe.xml')
        assert urls == []
        assert crawler.discovery_errors
        assert 'document type' in crawler.discovery_errors[0]['error']
        assert requests == ['/unsafe.xml']
    asyncio.run(run())


def test_sitemap_bytes_and_discovery_count_are_bounded(http_site):
    base, routes, requests = http_site
    routes['/large.xml'] = (200, {'Content-Type': 'application/xml'}, '<urlset>' + ' ' * 1000 + '</urlset>')
    async def run():
        async with Crawler(config(max_page_size=64)) as crawler:
            assert await crawler.parse_sitemap(base + '/large.xml') == []
        assert 'max_page_size' in crawler.limit_reasons
        for i in range(30):
            routes[f'/map{i}.xml'] = (200, {'Content-Type': 'application/xml'},
                                      f'<sitemapindex><sitemap><loc>/map{i+1}.xml</loc></sitemap></sitemapindex>')
        requests.clear()
        async with Crawler(config(max_pages=1)) as crawler:
            assert await crawler.parse_sitemap(base + '/map0.xml') == []
        assert len(requests) <= 16
        assert 'sitemap_discovery' in crawler.limit_reasons
    asyncio.run(run())


def test_sitemap_discovery_stops_after_requested_urls(http_site):
    base, routes, requests = http_site
    routes['/robots.txt'] = (200, {}, f'Sitemap: {base}/declared.xml\nSitemap: {base}/unused.xml\n')
    routes['/declared.xml'] = (200, {'Content-Type': 'application/xml'}, '<urlset><url><loc>/first</loc></url><url><loc>/second</loc></url></urlset>')
    async def run():
        async with Crawler(config(use_sitemap=True)) as crawler:
            urls = await crawler.discover_sitemap_urls(base + '/', max_urls=1)
        assert urls == [base + '/first']
        assert requests == ['/robots.txt', '/declared.xml']
    asyncio.run(run())


def test_guessed_missing_sitemaps_are_not_declared_discovery_errors(http_site):
    base, routes, _ = http_site
    routes['/robots.txt'] = (200, {}, f'Sitemap: {base}/declared.xml\n')
    async def run():
        async with Crawler(config(use_sitemap=True)) as crawler:
            assert await crawler.discover_sitemap_urls(base + '/') == []
        assert len(crawler.discovery_errors) == 1
        assert crawler.discovery_errors[0]['url'] == base + '/declared.xml'
        assert crawler.discovery_errors[0]['error'] == 'HTTP 404'
    asyncio.run(run())


def test_crawl_deadline_retains_inflight_failures_and_cleans_up():
    async def run():
        running = set()
        crawler = Crawler(config(max_crawl_time=0.04, max_concurrent=2, max_pages=2))
        async def stalled(url):
            task = asyncio.current_task()
            running.add(task)
            try:
                await asyncio.Event().wait()
            finally:
                running.discard(task)
        crawler.fetch_page = stalled
        rows = await crawler.crawl_urls(['https://example.test/one', 'https://example.test/two'])
        assert len(rows) == 2
        assert all(row['error'] == 'Crawl time limit exceeded' for row in rows)
        assert 'max_crawl_time' in crawler.limit_reasons
        assert not running
    asyncio.run(run())


def test_cancelling_crawl_cancels_and_awaits_fetch_tasks():
    async def run():
        running = set()
        started = asyncio.Event()
        crawler = Crawler(config(max_concurrent=2))
        async def stalled(url):
            task = asyncio.current_task()
            running.add(task)
            if len(running) == 2:
                started.set()
            try:
                await asyncio.Event().wait()
            finally:
                running.discard(task)
        crawler.fetch_page = stalled
        task = asyncio.create_task(crawler.crawl_urls(['https://example.test/one', 'https://example.test/two']))
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not running
    asyncio.run(run())


@pytest.mark.parametrize('url', ['not a URL', 'file:///private', 'https://example.test:invalid/', 'javascript:alert(1)', 'http://127.0.0.1:0/'])
def test_invalid_seeds_return_terminal_errors_without_network(url):
    async def run():
        async with Crawler(config()) as crawler:
            result = await crawler.fetch_page(url)
            assert result['status_code'] == 0 and result['error']
            assert result['load_time'] is None
            assert crawler.stats.requests_made == 0
    asyncio.run(run())
