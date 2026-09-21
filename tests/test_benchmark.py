"""Benchmark outcomes use controlled fixtures, never public web targets."""

import asyncio
import json
import socket
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


@pytest.mark.parametrize('scenario', benchmark.SCENARIOS)
def test_varied_fixtures_are_reproducible_complete_and_offline(monkeypatch, scenario):
    attempts = []

    def no_dns(*args, **kwargs):
        attempts.append(args)
        raise AssertionError('Offline fixtures must not resolve network addresses')

    async def no_fetch(*args, **kwargs):
        attempts.append(args)
        raise AssertionError('Offline fixtures must not fetch any resources')

    monkeypatch.setattr(socket, 'getaddrinfo', no_dns)
    monkeypatch.setattr('tfq0seo.core.app.Crawler.fetch_page', no_fetch)
    first = asyncio.run(benchmark.benchmark_offline(3, scenario))
    second = asyncio.run(benchmark.benchmark_offline(3, scenario))
    assert attempts == []
    assert first['status'] == second['status'] == 'complete'
    assert first['fixture'] == second['fixture']
    assert len(first['fixture']['sha256']) == 64
    assert first['fixture']['generated_pages'] == 3
    assert first['fixture']['pages_with_word_count'] == 3
    assert sum(first['readability']['status_counts'].values()) == 3
    assert first['report_completeness'] == {
        'expected_pages': 3, 'retained_rows': 3, 'unique_urls': 3, 'missing_urls': 0,
        'unexpected_urls': 0, 'duplicate_rows': 0, 'complete': True,
    }
    assert first['analysis_duration_seconds'] > 0
    assert first['report_duration_seconds'] > 0
    assert first['config']['crawler']['cache_enabled'] is False
    assert first['config']['crawler']['max_pages'] == 3
    assert first['site_analysis']['node_count'] == 3
    if scenario == 'content-heavy':
        assert first['fixture']['image_elements'] == 24
        assert first['fixture']['html_bytes'] > 20000
        assert first['fixture']['analyzed_word_count'] > 3000
    elif scenario == 'link-dense':
        assert first['fixture']['href_references'] == 117
    elif scenario == 'mixed':
        assert first['fixture']['variants'] == {'basic': 1, 'content-heavy': 1, 'link-dense': 1}


def test_report_duplicate_urls_fail_even_when_row_count_matches(monkeypatch):
    class Analyzer:
        def __init__(self, config):
            pass

        async def analyze_page(self, page):
            return {'url': page['url'], 'status': 'complete', 'overall_score': 90}

        def generate_site_report(self, pages):
            return {'status': 'complete', 'pages': {'detailed': [pages[0], pages[0]]}}

    monkeypatch.setattr(benchmark, 'SEOAnalyzer', Analyzer)
    result = asyncio.run(benchmark.benchmark_offline(2))
    assert result['successful_pages'] == result['report_pages'] == 2
    assert result['status'] == 'failed'
    assert result['report_completeness']['duplicate_rows'] == 1
    assert result['report_completeness']['missing_urls'] == 1
    assert 'expected fixture URLs' in result['errors'][0]


def test_offline_timeout_preserves_observed_results_and_reports_failure(monkeypatch):
    class Analyzer:
        def __init__(self, config):
            self.calls = 0

        async def analyze_page(self, page):
            self.calls += 1
            if self.calls > 1:
                await asyncio.sleep(1)
            return {'url': page['url'], 'status': 'complete', 'overall_score': 90}

    monkeypatch.setattr(benchmark, 'SEOAnalyzer', Analyzer)
    result = asyncio.run(benchmark.benchmark_offline(3, timeout_seconds=0.05))
    assert result['status'] == 'failed'
    assert result['timed_out'] is True
    assert result['successful_pages'] == result['observed_results'] == 1
    assert result['missing_results'] == 2
    assert result['report_completeness'] is None
    assert 'deadline' in result['errors'][0]


def test_suite_records_repeat_order_and_excludes_incomplete_runs_from_metrics(tmp_path, monkeypatch):
    calls = []

    async def offline(page_count, scenario='basic', timeout_seconds=None):
        calls.append((page_count, scenario, timeout_seconds))
        return {'status': 'partial' if len(calls) == 2 else 'complete', 'successful_pages': page_count,
                'duration_seconds': 100 if len(calls) == 2 else 2, 'pages_per_second': page_count / 2}

    monkeypatch.setattr(benchmark, 'benchmark_offline', offline)
    result = asyncio.run(benchmark.run_all_benchmarks(
        output_file=str(tmp_path / 'suite.json'), scenarios=['mixed', 'basic'], page_counts=[3, 5],
        repetitions=2, timeout_seconds=10))
    assert calls == [(size, scenario, 10) for size in (3, 5) for scenario in ('mixed', 'basic') for _ in range(2)]
    assert result['status'] == 'partial'
    assert [run['run_order'] for run in result['benchmarks']] == list(range(1, 9))
    assert [run['repetition'] for run in result['benchmarks']] == [1, 2] * 4
    summary = result['summaries'][0]
    assert summary['runs'] == 2 and summary['complete_runs'] == summary['partial_runs'] == 1
    assert summary['metrics']['duration_seconds'] == {'median': 2, 'min': 2, 'max': 2}
    assert result['suite']['repetitions'] == 2
    assert 'Same process' in result['suite']['isolation']


def test_environment_records_dependency_versions_and_implementation(monkeypatch):
    def installed(name):
        if name == 'openpyxl':
            raise benchmark.importlib_metadata.PackageNotFoundError(name)
        return 'fixture-version'

    monkeypatch.setattr(benchmark.importlib_metadata, 'version', installed)
    environment = benchmark._environment()
    assert set(environment['direct_dependencies']) == set(benchmark.DIRECT_DEPENDENCIES)
    assert all(value == 'fixture-version' for value in environment['direct_dependencies'].values())
    assert environment['optional_dependencies']['openpyxl'] is None
    assert environment['schema_version'] == benchmark.SCHEMA_VERSION
    assert environment['ruleset_version'] == benchmark.RULESET_VERSION
    assert environment['facts_version'] == benchmark.FACTS_VERSION
    assert environment['package_version'] == benchmark.__version__
    assert environment['os']['system'] and environment['architecture']
    assert environment['cpu_count'] > 0
    assert environment['source_fingerprint']['file_count'] > 0
    assert len(environment['source_fingerprint']['digest']) == 64
    json.dumps(environment, allow_nan=False)


def test_changed_source_during_suite_invalidates_comparison(tmp_path, monkeypatch):
    fingerprints = iter([{'digest': 'before'}, {'digest': 'after'}])
    monkeypatch.setattr(benchmark, '_source_fingerprint', lambda: next(fingerprints))
    monkeypatch.setattr(benchmark, 'benchmark_offline', AsyncMock(return_value={'status': 'complete'}))
    result = asyncio.run(benchmark.run_all_benchmarks(1, str(tmp_path / 'changed.json')))
    assert result['source_unchanged_during_suite'] is False
    assert result['status'] == 'failed'


def test_cli_accepts_scenarios_sizes_repetitions_and_deadline(tmp_path, monkeypatch):
    run = AsyncMock(return_value={'status': 'complete'})
    monkeypatch.setattr(benchmark, 'run_all_benchmarks', run)
    path = str(tmp_path / 'suite.json')
    assert benchmark.main(['--suite', '--pages', '500', '2000', '--repetitions', '3',
                           '--timeout-seconds', '600', '--output', path]) == 0
    run.assert_awaited_once_with(500, path, page_counts=[500, 2000], scenarios=benchmark.SCENARIOS,
                                repetitions=3, timeout_seconds=600)


@pytest.mark.parametrize('options', [
    {'scenario': 'missing'}, {'timeout_seconds': float('nan')}, {'timeout_seconds': float('inf')},
    {'timeout_seconds': 0}, {'timeout_seconds': True},
])
def test_invalid_offline_options_are_rejected(options):
    with pytest.raises(ValueError):
        asyncio.run(benchmark.benchmark_offline(1, **options))


@pytest.mark.parametrize('options', [
    {'scenarios': []}, {'page_counts': []}, {'repetitions': 0}, {'repetitions': True},
    {'scenarios': ['basic', 'basic']}, {'page_counts': [500, 500]},
])
def test_invalid_suite_options_are_rejected_before_running(options):
    with pytest.raises(ValueError):
        asyncio.run(benchmark.run_all_benchmarks(**options))


@pytest.mark.parametrize('args', [
    ['--suite', '--scenario', 'mixed'], ['--repetitions', '0'], ['--timeout-seconds', 'nan'],
    ['--timeout-seconds', 'inf'], ['--timeout-seconds', '-1'],
])
def test_invalid_suite_cli_options_exit_two(args):
    with pytest.raises(SystemExit) as failure:
        benchmark.main(args)
    assert failure.value.code == 2
