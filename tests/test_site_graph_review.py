"""Independent regressions for graph ambiguity, context, and source coverage."""

import asyncio
import copy

from bs4 import BeautifulSoup

from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.core.crawler import Crawler
from tfq0seo.page_facts import extract_page_facts
from tfq0seo.site_analysis import analyze_site


BASE = 'https://example.test'


def page(url, html=''):
    soup = BeautifulSoup(html, 'html.parser')
    return {'url': url, 'status_code': 200, 'issues': [],
            'page_facts': extract_page_facts(soup, url, {}).to_dict()}


def test_conflicting_target_responses_are_unknown_independent_of_record_order():
    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['links']}}))
        source = await analyzer.analyze_page({
            'url': BASE + '/', 'status_code': 200, 'headers': {},
            'soup': BeautifulSoup('<a href="/target">Target</a>', 'html.parser'),
        })
        good = page(BASE + '/target')
        bad = {'url': BASE + '/target', 'status_code': 404, 'error': 'Observed HTTP 404',
               'status': 'error', 'overall_score': None, 'issues': []}
        outcomes = []
        for records in ([source, good, bad], [source, bad, good]):
            report = analyzer.generate_site_report(records)
            result = report['pages']['detailed'][0]
            health = result['links']['data']['link_health']
            rule = next(item for item in result['links']['rule_results']
                        if item['rule_id'] == 'links.broken')
            outcomes.append((result['overall_score'], health, rule['status']))
        assert outcomes[0] == outcomes[1]
        _, health, status = outcomes[0]
        assert health['unchecked'] == 1 and health['broken'] == 0
        assert status == 'unknown'

    asyncio.run(run())


def test_fresh_batch_report_does_not_inherit_previous_crawl_context(monkeypatch):
    class CrawlerStub(Crawler):
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def crawl_site(self, start_url, max_pages):
            self.results.append({
                'url': start_url, 'status_code': 200, 'headers': {},
                'soup': BeautifulSoup('<html><body>Previous crawl</body></html>', 'html.parser'),
            })
            return self.results

    monkeypatch.setattr('tfq0seo.core.app.Crawler', CrawlerStub)

    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['links']}}))
        previous = [result async for result in analyzer.crawl_site('https://previous.test/start')]
        assert previous
        assert analyzer.generate_site_report()['summary']['crawl_complete'] is True

        fresh = [page(BASE + '/', '<a href="/child">Child</a>'), page(BASE + '/child')]
        report = analyzer.generate_batch_report(fresh)
        graph = report['site_analysis']
        assert graph['links']['roots'] == [BASE + '/']
        assert graph['links']['root_source'] == 'observed_homepages'
        assert graph['coverage']['crawl_complete'] is False
        assert report['summary']['crawl_complete'] is False
        assert next(row for row in graph['pages'] if row['url'] == BASE + '/child')['link_depth'] == 1

    asyncio.run(run())


def test_partial_fact_sections_do_not_count_as_complete_html_coverage():
    archive = {'url': BASE + '/archive', 'status_code': 200, 'issues': [],
               'page_facts': {'anchors': [], 'robots': {}, 'canonical': {'declarations': []}}}
    # Partial historical facts remain valid input; their missing observations
    # must not become a claim that all extraction sources were available.
    report = SEOAnalyzer().generate_site_report([archive])
    assert report['site_analysis']['coverage']['complete_html_pages'] == 0
    assert report['site_analysis']['pages'][0]['content_complete'] is False
    assert report['site_analysis']['pages'][0]['canonical_status'] == 'unknown'


def test_repeated_url_canonical_conflict_evidence_is_order_independent():
    first = page(BASE + '/same', '<head><link rel="canonical" href="/a"></head>')
    second = page(BASE + '/same', '<head><link rel="canonical" href="/b"></head>')
    assert analyze_site([first, second]) == analyze_site([second, first])


def test_external_link_observations_are_scoped_to_current_run_result_objects():
    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'analysis': {
            'enabled_analyzers': ['links'], 'check_external_links': True,
        }}))
        target = 'https://other.test/target'
        source = await analyzer.analyze_page({
            'url': BASE + '/', 'status_code': 200, 'headers': {},
            'soup': BeautifulSoup('<a href="' + target + '">Target</a>', 'html.parser'),
        })
        analyzer.results = [source]
        analyzer.link_checks = [{'url': target, 'status_code': 404, 'error': 'Observed HTTP 404'}]

        # A newly collected list of the current run's objects, as used by the
        # CLI, retains observations made for that run.
        current = analyzer.generate_batch_report([source])
        assert current['technical_health']['link_checks'] == analyzer.link_checks
        assert current['pages']['detailed'][0]['links']['data']['link_health']['broken'] == 1

        # An independent imported copy contains the same page URL but does not
        # carry the previous run's external-fetch evidence.
        fresh = analyzer.generate_batch_report([copy.deepcopy(source)])
        assert fresh['technical_health']['link_checks'] == []
        assert fresh['technical_health']['broken_links'] == []
        health = fresh['pages']['detailed'][0]['links']['data']['link_health']
        assert health['unchecked'] == 1 and health['broken'] == 0
        rule = next(item for item in fresh['pages']['detailed'][0]['links']['rule_results']
                    if item['rule_id'] == 'links.broken')
        assert rule['status'] == 'unknown'

    asyncio.run(run())
