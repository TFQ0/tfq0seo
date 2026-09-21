import asyncio
import copy

import pytest
from bs4 import BeautifulSoup

from tfq0seo.core.app import AnalysisCache, AnalysisMode, SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.core.report_optimizer import aggregate_issues, generate_performance_metrics


def page(url='https://example.test/', title='Example', body='<h1>Example</h1>'):
    html = f'<!doctype html><html lang="en"><head><title>{title}</title></head><body>{body}</body></html>'
    return {'url': url, 'status_code': 200, 'soup': BeautifulSoup(html, 'html.parser'),
            'headers': {}, 'load_time': 0.2, 'content_length': len(html.encode('utf-8'))}


def config(**crawler):
    return Config.from_dict({'crawler': {'use_sitemap': False, 'respect_robots_txt': False,
                                         'max_retries': 0, **crawler}})


def test_report_evidence_remains_independent_of_supplied_pages():
    async def run():
        analyzer = SEOAnalyzer(config(cache_enabled=False))
        source = await analyzer.analyze_page(page(body='<h1>Example</h1><img src="/image.png">'))
        before = copy.deepcopy(source)
        report = analyzer.generate_site_report([source])
        detail = report['pages']['detailed'][0]
        issue = next(item for item in detail['issues'] if item['rule_id'] == 'images.missing_alt')
        issue['evidence']['test_extension'] = ['owned by report']
        assert source == before
        source['page_facts']['test_extension'] = 'owned by source'
        assert 'test_extension' not in detail['page_facts']
    asyncio.run(run())


def test_analysis_mode_and_enabled_selection():
    cfg = Config.from_dict({'profile': 'quick'})
    analyzer = SEOAnalyzer(cfg)
    result = asyncio.run(analyzer.analyze_page(page()))
    assert analyzer.mode == AnalysisMode.QUICK
    assert 'seo' in result and 'technical' in result
    assert 'performance' not in result
    assert result['coverage']['failed_analyzers'] == []


def test_configured_weights_are_used_without_double_penalty():
    cfg = Config.from_dict({'analysis': {'score_weights': {'seo': 0.8, 'content': 0.2}}})
    analyzer = SEOAnalyzer(cfg)
    assert analyzer._calculate_weighted_score({'seo': {'score': 100}, 'content': {'score': 0}}) == 80
    assert analyzer._calculate_weighted_score({'seo': {'score': None, 'error': 'failed'}}) is None


def test_analyzer_exception_is_not_a_zero_website_score(monkeypatch):
    def fail(*args, **kwargs):
        raise TypeError('implementation failure')
    monkeypatch.setattr('tfq0seo.core.app.analyze_content', fail)
    result = asyncio.run(SEOAnalyzer(config()).analyze_page(page()))
    assert result['status'] == 'partial'
    assert result['content']['score'] is None
    assert result['analyzer_errors']['content'] == 'implementation failure'
    assert result['coverage']['ratio'] == 0.8
    assert result['content']['issues'] == []


def test_cache_tracks_content_and_does_not_share_mutable_results():
    async def run():
        analyzer = SEOAnalyzer(config())
        first = await analyzer.analyze_page(page())
        first['seo']['data']['title']['text'] = 'Mutated'
        cached = await analyzer.analyze_page(page())
        changed = await analyzer.analyze_page(page(title='Changed'))
        assert cached['cached'] is True
        assert cached['seo']['data']['title']['text'] == 'Example'
        assert changed['seo']['data']['title']['text'] == 'Changed'
        assert not changed.get('cached')
    asyncio.run(run())


def test_cache_obeys_size_and_expiry():
    cache = AnalysisCache(ttl_seconds=0)
    cache.set('a', {'score': 90})
    assert cache.get('a') is None
    cache = AnalysisCache(max_bytes=1)
    cache.set('a', {'score': 90})
    assert not cache.cache


def test_report_is_complete_consistent_and_does_not_mutate_inputs():
    pages = [{'url': f'https://example.test/{i}', 'status_code': 200, 'status': 'complete',
              'overall_score': 90, 'seo': {'score': 90}, 'load_time': 2,
              'issues': [{'severity': 'warning', 'category': 'SEO', 'message': 'Example finding'}]}
             for i in range(500)]
    original = copy.deepcopy(pages)
    report = SEOAnalyzer(config()).generate_site_report(pages)
    assert len(report['pages']['summary']) == len(report['pages']['detailed']) == 500
    assert report['issues']['counts']['total'] == 500
    assert report['issues']['aggregated'][0]['pages_affected'] == 500
    assert report['recommendations']['executive']['overview']['overall_score'] == report['scores']['overall'] == 90
    assert report['recommendations']['executive']['key_metrics']['total_issues'] == 500
    assert pages == original


def test_broken_links_resolve_after_target_is_analyzed():
    async def run():
        analyzer = SEOAnalyzer(config())
        home = await analyzer.analyze_page(page(body='<h1>Example</h1><a href="/missing">Missing</a>'))
        failure = await analyzer.analyze_page({'url': 'https://example.test/missing',
                                               'status_code': 404, 'error': 'HTTP 404'})
        report = analyzer.generate_site_report([home, failure])
        updated = report['pages']['detailed'][0]
        assert updated['links']['data']['link_health']['broken'] == 1
        issue = next(item for item in updated['issues'] if item.get('rule_id') == 'links.broken')
        assert issue['evidence']['http_statuses']['https://example.test/missing'] == 404
        assert report['status'] == 'partial'
        assert report['summary']['failed_pages'] == 1
        assert len(report['pages']['failed']) == 1
    asyncio.run(run())


def test_http_statuses_and_even_median_are_preserved():
    metrics = generate_performance_metrics([{'load_time': 1, 'status_code': 200},
                                            {'load_time': 3, 'status_code': 404, 'error': 'HTTP 404'}])
    assert metrics['status_codes'][404] == 1
    assert metrics['load_time_stats']['median'] == 2


def test_rule_aggregation_retains_unique_page_evidence():
    issues = [{'rule_id': 'seo.title', 'message': str(i), 'category': 'SEO', 'severity': 'warning',
               'url': f'https://example.test/{i}'} for i in range(8)]
    aggregated, stats = aggregate_issues(issues)
    assert len(aggregated) == 1
    assert len(aggregated[0]['pages']) == 8
    assert len(aggregated[0]['example_pages']) == 5
    assert stats['total_issues'] == 8


def test_repeated_runs_do_not_mix_results(http_site):
    base, routes, _ = http_site
    routes['/first'] = (200, {'Content-Type': 'text/html'}, '<html><title>First</title><h1>First</h1></html>')
    routes['/second'] = (200, {'Content-Type': 'text/html'}, '<html><title>Second</title><h1>Second</h1></html>')
    async def run():
        analyzer = SEOAnalyzer(config(max_concurrent=1))
        await analyzer.analyze_url(base + '/first')
        await analyzer.analyze_url(base + '/second')
        assert len(analyzer.results) == analyzer.stats.total_pages == 1
        assert analyzer.results[0]['url'].endswith('/second')
    asyncio.run(run())


def test_crawl_at_one_concurrent_request_finishes(http_site):
    base, routes, _ = http_site
    routes['/'] = (200, {'Content-Type': 'text/html'}, '<html><title>Home</title><h1>Home</h1><a href="/child">Child</a></html>')
    routes['/child'] = (200, {'Content-Type': 'text/html'}, '<html><title>Child</title><h1>Child</h1></html>')
    async def run():
        analyzer = SEOAnalyzer(config(max_concurrent=1, max_pages=2))
        results = [item async for item in analyzer.crawl_site(base + '/')]
        assert len(results) == 2
        assert analyzer.generate_site_report()['summary']['crawl_complete']
    asyncio.run(asyncio.wait_for(run(), timeout=10))


def test_batch_deduplicates_fetch_identity_before_applying_page_limit(http_site):
    base, routes, requests = http_site
    routes['/a'] = routes['/b'] = (200, {'Content-Type': 'text/html'}, '<html><title>Page</title><h1>Page</h1></html>')
    async def run():
        analyzer = SEOAnalyzer(config(max_pages=2))
        results = [result async for result in analyzer.analyze_urls(
            [base + '/a#one', base + '/a#two', base + '/b'])]
        assert len(results) == 2
        assert all(result['status'] == 'complete' for result in results)
        assert {result['url'] for result in results} == {base + '/a', base + '/b'}
        assert sorted(requests) == ['/a', '/b']
    asyncio.run(run())


def test_explicit_sitemap_preserves_failed_child_discovery_coverage(http_site):
    base, routes, _ = http_site
    routes['/index.xml'] = (200, {'Content-Type': 'application/xml'},
                           '<sitemapindex><sitemap><loc>/pages.xml</loc></sitemap>'
                           '<sitemap><loc>/broken.xml</loc></sitemap></sitemapindex>')
    routes['/pages.xml'] = (200, {'Content-Type': 'application/xml'},
                           '<urlset><url><loc>/one</loc></url></urlset>')
    routes['/broken.xml'] = (200, {'Content-Type': 'application/xml'}, '<invalid')
    routes['/one'] = (200, {'Content-Type': 'text/html'}, '<html><title>One</title><h1>One</h1></html>')
    async def run():
        analyzer = SEOAnalyzer(config())
        results = await analyzer.analyze_sitemap(base + '/index.xml')
        assert len(results) == 1 and results[0]['status'] == 'complete'
        summary = analyzer.generate_site_report()['summary']
        assert any(error['url'] == base + '/broken.xml' for error in summary['discovery_errors'])
        assert summary['crawl_complete'] is False
    asyncio.run(run())


def test_explicit_sitemap_page_cap_is_visible_in_report(http_site):
    base, routes, requests = http_site
    routes['/sitemap.xml'] = (200, {'Content-Type': 'application/xml'},
                             '<urlset><url><loc>/one</loc></url><url><loc>/two</loc></url></urlset>')
    routes['/one'] = routes['/two'] = (200, {'Content-Type': 'text/html'}, '<html><title>Page</title><h1>Page</h1></html>')
    async def run():
        analyzer = SEOAnalyzer(config(max_pages=1))
        results = await analyzer.analyze_sitemap(base + '/sitemap.xml')
        assert len(results) == 1
        assert '/two' not in requests
        summary = analyzer.generate_site_report()['summary']
        assert 'max_pages' in summary['limits_reached']
        assert summary['crawl_complete'] is False
    asyncio.run(run())


def test_external_link_error_cancels_and_awaits_sibling_fetches(monkeypatch):
    async def run():
        analyzer = SEOAnalyzer(config(max_concurrent=2))
        analyzer.results = [{'links': {'data': {'external_links': [
            {'url': 'https://example.test/fail'},
            {'url': 'https://example.test/pending'},
        ]}}}]
        started = asyncio.Event()
        pending = set()

        async def fetch(crawler, url):
            if url.endswith('/fail'):
                await started.wait()
                raise RuntimeError('Fixture unexpected fetch failure')
            task = asyncio.current_task()
            pending.add(task)
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                pending.discard(task)

        monkeypatch.setattr('tfq0seo.core.app.Crawler.fetch_page', fetch)
        try:
            with pytest.raises(RuntimeError, match='unexpected fetch failure'):
                await analyzer._check_external_links()
            assert not pending
        finally:
            # Keep the regression bounded even if cleanup regresses.
            leftovers = list(pending)
            for task in leftovers:
                task.cancel()
            await asyncio.gather(*leftovers, return_exceptions=True)
    asyncio.run(asyncio.wait_for(run(), 2))


def test_malformed_explicit_sitemap_returns_error_report(http_site):
    base, routes, requests = http_site
    routes['/broken.xml'] = (200, {'Content-Type': 'application/xml'}, '<invalid')
    async def run():
        analyzer = SEOAnalyzer(config())
        results = await analyzer.analyze_sitemap(base + '/broken.xml')
        assert len(results) == 1 and results[0]['status'] == 'error'
        assert results[0]['overall_score'] is None
        report = analyzer.generate_site_report()
        assert report['status'] == 'error'
        assert report['summary']['failed_pages'] == 1
        assert report['summary']['crawl_complete'] is False
        assert report['summary']['discovery_errors'][0]['url'] == base + '/broken.xml'
        assert requests == ['/broken.xml']
    asyncio.run(run())


def test_redirect_chain_intermediate_target_uses_observed_terminal_status():
    async def run():
        analyzer = SEOAnalyzer(config())
        home = await analyzer.analyze_page(page(body='<h1>Home</h1><a href="/middle">Target</a>'))
        failure = await analyzer.analyze_page({
            'url': 'https://example.test/end',
            'requested_url': 'https://example.test/start',
            'status_code': 404, 'error': 'HTTP 404',
            'redirect_chain': [
                {'url': 'https://example.test/start', 'status_code': 302,
                 'location': 'https://example.test/middle'},
                {'url': 'https://example.test/middle', 'status_code': 302,
                 'location': 'https://example.test/end'},
            ],
        })
        report = analyzer.generate_site_report([home, failure])
        links = report['pages']['detailed'][0]['links']['data']
        assert links['link_health']['checked'] == 1
        assert links['link_health']['unchecked'] == 0
        assert links['broken_links'] == ['https://example.test/middle']
    asyncio.run(run())
