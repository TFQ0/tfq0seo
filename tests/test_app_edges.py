"""Boundary tests found during independent review of configuration and run lifecycles."""

import asyncio
import copy
import threading

import pytest
from bs4 import BeautifulSoup

from tfq0seo.analyzers.links import analyze_links
from tfq0seo.cli import _configuration
from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.config import Config, ConfigProfile, CrawlerConfig


def raw_page(url='https://example.test/', body='<h1>Fixture</h1>'):
    return {'url': url, 'status_code': 200, 'headers': {}, 'load_time': 0.5,
            'soup': BeautifulSoup(f'<html lang="en"><title>Fixture title</title><body>{body}</body></html>', 'html.parser')}


def only_analyzer(name, **analysis):
    return Config.from_dict({'analysis': {'enabled_analyzers': [name], 'score_weights': {name: 1.0}, **analysis}})


def test_cli_environment_profile_changes_effective_behavior(monkeypatch):
    monkeypatch.setenv('TFQ0SEO_PROFILE', 'quick')
    config = _configuration(None)
    assert config.profile == ConfigProfile.QUICK
    assert config.analysis.analysis_mode == 'quick'
    assert config.analysis.enabled_analyzers == ['seo', 'technical']
    assert config.crawler.max_pages == 50


def test_environment_alias_overrides_default_canonical_concurrency(monkeypatch):
    monkeypatch.setenv('TFQ0SEO_CRAWLER_CONCURRENT_REQUESTS', '2')
    config = _configuration(None)
    assert config.crawler.effective_concurrency == 2
    assert _configuration(None, max_concurrent=3).crawler.effective_concurrency == 3


@pytest.mark.parametrize(('name', 'value', 'attribute'), [
    ('TFQ0SEO_EXPORT_OUTPUT_DIRECTORY', 'reports,archive', 'output_directory'),
    ('TFQ0SEO_EXPORT_FILENAME_PATTERN', '12345', 'filename_pattern'),
])
def test_string_environment_values_are_not_coerced_to_other_types(monkeypatch, name, value, attribute):
    monkeypatch.setenv(name, value)
    assert getattr(Config.from_env().export, attribute) == value


def test_explicit_constructor_component_precedes_profile_defaults():
    config = Config(profile=ConfigProfile.QUICK, crawler=CrawlerConfig(max_pages=17))
    assert config.crawler.max_pages == 17


def test_empty_effective_quick_selection_is_rejected_before_fetching():
    with pytest.raises(ValueError):
        SEOAnalyzer(only_analyzer('links', analysis_mode='quick'))


def test_cache_keeps_new_fetch_timing_observations():
    async def run():
        analyzer = SEOAnalyzer(only_analyzer('seo'))
        first = raw_page()
        first['timings'] = {'ttfb': 0.1, 'body': 0.4}
        await analyzer.analyze_page(first)
        second = dict(first, timings={'ttfb': 0.3, 'body': 0.2})
        result = await analyzer.analyze_page(second)
        assert result['timings'] == second['timings']
    asyncio.run(run())


def test_resolved_broken_links_update_scores_consistently():
    async def run():
        analyzer = SEOAnalyzer(only_analyzer('links'))
        source = raw_page(body='<h1>Fixture</h1><a href="/missing">Missing page</a>')
        page = await analyzer.analyze_page(source)
        failure = await analyzer.analyze_page({'url': 'https://example.test/missing', 'status_code': 404, 'error': 'HTTP 404'})
        expected = analyze_links(source['soup'], source['url'], broken_links={failure['url']})['score']
        report = analyzer.generate_site_report([page, failure])
        resolved = report['pages']['detailed'][0]
        assert resolved['links']['score'] == expected
        assert resolved['overall_score'] == expected
        assert report['scores']['overall'] == expected
        assert len([issue for issue in resolved['issues'] if issue.get('rule_id') == 'links.broken']) == 1
        # Regenerating a report must not compound the penalty or mutate input records.
        original = copy.deepcopy(resolved)
        second = analyzer.generate_site_report([resolved, failure])
        assert second['scores']['overall'] == expected
        assert resolved == original
    asyncio.run(run())


def test_closing_batch_generator_cancels_fetches_before_session_exit(monkeypatch):
    exits = []
    active = set()

    class FakeCrawler:
        def __init__(self, config):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            exits.append(len(active))

        async def fetch_page(self, url):
            task = asyncio.current_task()
            active.add(task)
            try:
                if url.endswith('/ready'):
                    await asyncio.sleep(0)
                    return {'url': url, 'error': 'Completed fixture request'}
                await asyncio.Event().wait()
            finally:
                active.discard(task)

    monkeypatch.setattr('tfq0seo.core.app.Crawler', FakeCrawler)

    async def run():
        config = Config.from_dict({'crawler': {'max_concurrent': 2}})
        analyzer = SEOAnalyzer(config)
        generator = analyzer.analyze_urls(['https://example.test/ready', 'https://example.test/pending'])
        try:
            await asyncio.wait_for(generator.__anext__(), timeout=1)
            await generator.aclose()
            assert exits == [0]
        finally:
            # Ensure a regression cannot leave fixture tasks alive after the test.
            pending = list(active)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            await generator.aclose()
    asyncio.run(run())


def test_cancelled_analyzers_keep_running_work_within_thread_limit():
    first_started = threading.Event()
    release = threading.Event()
    lock = threading.Lock()
    counts = {'active': 0, 'maximum': 0}

    def blocking_analyzer():
        with lock:
            counts['active'] += 1
            counts['maximum'] = max(counts['maximum'], counts['active'])
        first_started.set()
        try:
            release.wait(timeout=2)
            return {'score': 100, 'issues': []}
        finally:
            with lock:
                counts['active'] -= 1

    async def run():
        analyzer = SEOAnalyzer(only_analyzer('seo', max_analysis_threads=1))
        first = asyncio.create_task(analyzer._run_analyzer_safe('seo', blocking_analyzer))
        second = None
        try:
            for _ in range(100):
                if first_started.is_set():
                    break
                await asyncio.sleep(0.005)
            assert first_started.is_set()
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            second = asyncio.create_task(analyzer._run_analyzer_safe('seo', blocking_analyzer))
            await asyncio.sleep(0.05)
        finally:
            release.set()
            await asyncio.gather(*([second] if second else []), return_exceptions=True)
            if not first.done():
                first.cancel()
            await asyncio.gather(first, return_exceptions=True)
        assert counts['maximum'] == 1
    asyncio.run(run())
