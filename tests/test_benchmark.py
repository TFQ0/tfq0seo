"""Benchmark outcomes use controlled fixtures, never public web targets."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tfq0seo import benchmark


@pytest.mark.parametrize('result', [None, {}, {'url': 'https://example.test/', 'status': 'error', 'error': 'Timed out'}])
def test_failed_single_analysis_never_becomes_successful_throughput(monkeypatch, result):
    analyzer = SimpleNamespace(analyze_url=AsyncMock(return_value=result))
    monkeypatch.setattr(benchmark, 'SEOAnalyzer', lambda config: analyzer)
    measured = asyncio.run(benchmark.benchmark_single_page('https://example.test/'))
    assert measured['status'] == 'failed'
    assert measured['successful_pages'] == measured['pages_analyzed'] == 0
    assert measured['failed_pages'] == 1
    assert measured['pages_per_second'] == 0
    assert measured['avg_time_per_page'] is None


def test_batch_counts_outcomes_and_uses_monotonic_elapsed_time(monkeypatch):
    class Analyzer:
        def __init__(self, config):
            pass

        async def analyze_urls(self, urls):
            yield {'url': urls[0], 'status': 'complete', 'overall_score': 90}
            yield {'url': urls[1], 'status': 'partial', 'analyzer_errors': {'seo': 'Fixture failure'}}
            yield {'url': urls[2], 'status': 'error', 'error': 'Fixture timeout'}
            yield {'url': urls[3], 'status': 'skipped', 'skipped': True}

    monkeypatch.setattr(benchmark, 'SEOAnalyzer', Analyzer)
    clock = iter([1000.0, 1002.0])
    monkeypatch.setattr(benchmark.time, 'perf_counter', lambda: next(clock))
    urls = [f'https://example.test/{index}' for index in range(4)]
    result = asyncio.run(benchmark.benchmark_batch(urls))
    assert result['status'] == 'failed'
    assert result['successful_pages'] == result['partial_pages'] == result['failed_pages'] == result['skipped_pages'] == 1
    assert result['observed_results'] == 4
    assert result['duration_seconds'] == 2
    assert result['pages_per_second'] == 0.5
    assert result['clock'] == 'perf_counter'
    assert set(result['errors']) == {'Fixture failure', 'Fixture timeout'}


def test_exception_preserves_already_recorded_outcomes(monkeypatch):
    class Analyzer:
        def __init__(self, config):
            pass

        async def crawl_site(self, url):
            yield {'url': url, 'status': 'complete', 'overall_score': 90}
            raise TimeoutError('Fixture crawl interrupted')

    monkeypatch.setattr(benchmark, 'SEOAnalyzer', Analyzer)
    result = asyncio.run(benchmark.benchmark_crawl('https://example.test/'))
    assert result['status'] == 'failed'
    assert result['successful_pages'] == 1
    assert result['observed_results'] == 1
    assert result['errors'] == ['TimeoutError: Fixture crawl interrupted']


def test_missing_batch_results_are_incomplete(monkeypatch):
    class Analyzer:
        def __init__(self, config):
            pass

        async def analyze_urls(self, urls):
            yield {'url': urls[0], 'status': 'complete', 'overall_score': 90}

    monkeypatch.setattr(benchmark, 'SEOAnalyzer', Analyzer)
    result = asyncio.run(benchmark.benchmark_batch(['https://example.test/one', 'https://example.test/two']))
    assert result['status'] == 'partial'
    assert result['missing_results'] == 1


def test_offline_fixture_measures_analysis_and_reporting_without_fetches(monkeypatch):
    async def forbid(*args, **kwargs):
        raise AssertionError('Offline benchmark must not fetch a URL')

    monkeypatch.setattr('tfq0seo.core.app.Crawler.fetch_page', forbid)
    result = asyncio.run(benchmark.benchmark_offline(3))
    assert result['status'] == 'complete'
    assert result['successful_pages'] == result['report_pages'] == 3
    assert result['network_access'] is False
    assert result['fixture_version'] == 1
    assert result['memory_sample_count'] >= 2
    assert result['memory_sampled_peak_mb'] >= result['memory_rss_start_mb']
    assert result['memory_sampled_peak_mb'] >= result['memory_rss_end_mb']
    assert result['memory_rss_delta_mb'] == pytest.approx(result['memory_rss_end_mb'] - result['memory_rss_start_mb'], abs=0.002)
    assert 'between samples may be missed' in result['memory_measurement']
    assert 'memory_peak_mb' not in result


def test_default_suite_uses_500_offline_pages_and_saves_metrics(tmp_path, monkeypatch, capsys):
    calls = []

    async def offline(page_count):
        calls.append(page_count)
        return {'status': 'complete', 'successful_pages': page_count, 'type': 'offline'}

    async def forbidden(*args, **kwargs):
        raise AssertionError('Default benchmark unexpectedly uses a network workload')

    monkeypatch.setattr(benchmark, 'benchmark_offline', offline)
    for name in ('benchmark_single_page', 'benchmark_batch', 'benchmark_crawl'):
        monkeypatch.setattr(benchmark, name, forbidden)
    path = tmp_path / 'benchmark.json'
    result = asyncio.run(benchmark.run_all_benchmarks(output_file=str(path)))
    assert calls == [500]
    assert result['status'] == 'complete'
    assert json.loads(path.read_text(encoding='utf-8')) == result
    assert benchmark.compare_with_targets() == {}
    assert 'grade' not in capsys.readouterr().out.lower()


@pytest.mark.parametrize(('status', 'expected_exit'), [('complete', 0), ('partial', 1), ('failed', 1)])
def test_cli_exit_code_reflects_benchmark_status(tmp_path, monkeypatch, status, expected_exit):
    async def offline(page_count):
        return {'status': status, 'successful_pages': 0, 'type': 'offline'}

    monkeypatch.setattr(benchmark, 'benchmark_offline', offline)
    path = tmp_path / 'outcome.json'
    assert benchmark.main(['--pages', '2', '--output', str(path)]) == expected_exit
    assert json.loads(path.read_text(encoding='utf-8'))['status'] == status


def test_cli_exceptions_return_failure(monkeypatch, capsys):
    async def fail(*args, **kwargs):
        raise RuntimeError('Fixture setup failed')

    monkeypatch.setattr(benchmark, 'run_all_benchmarks', fail)
    assert benchmark.main([]) == 1
    assert 'Fixture setup failed' in capsys.readouterr().err


@pytest.mark.parametrize('pages', [0, -1])
def test_invalid_fixture_size_is_rejected(pages):
    with pytest.raises(ValueError, match='positive integer'):
        asyncio.run(benchmark.benchmark_offline(pages))
    with pytest.raises(SystemExit) as failure:
        benchmark.main(['--pages', str(pages)])
    assert failure.value.code == 2
