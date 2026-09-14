"""Outcome-aware benchmarks; the default workload uses offline HTML fixtures."""

import argparse
import asyncio
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
from bs4 import BeautifulSoup

from .core.app import SEOAnalyzer
from .core.config import Config


class _MemorySampler:
    """Sample process RSS, retaining an observed maximum rather than a true peak."""

    def __init__(self, interval: float = 0.05):
        self.interval = interval
        self.process = psutil.Process()
        self.samples = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._poll, daemon=True)

    def _sample(self):
        self.samples.append(self.process.memory_info().rss / (1024 * 1024))

    def _poll(self):
        while not self.stop.wait(self.interval):
            self._sample()

    def __enter__(self):
        self._sample()
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()
        self._sample()

    def metrics(self):
        delta = self.samples[-1] - self.samples[0]
        return {
            'memory_rss_start_mb': round(self.samples[0], 3),
            'memory_rss_end_mb': round(self.samples[-1], 3),
            'memory_rss_delta_mb': round(delta, 3),
            'memory_sampled_peak_mb': round(max(self.samples), 3),
            'memory_sample_count': len(self.samples),
            'memory_sampling_interval_seconds': self.interval,
            'memory_measurement': 'Sampled process RSS; allocations between samples may be missed.',
            # Retained for callers of the original benchmark API; this is a delta.
            'memory_used_mb': round(delta, 3),
        }


def _outcome(result):
    if not isinstance(result, dict) or not result or result.get('error') or result.get('status') == 'error':
        return 'failed'
    if result.get('skipped') or result.get('status') == 'skipped':
        return 'skipped'
    if result.get('status') == 'partial' or result.get('analyzer_errors'):
        return 'partial'
    return 'successful' if result.get('status') == 'complete' or 'overall_score' in result else 'failed'


async def _measure(kind, operation, metadata, expected_results=None):
    """Measure an operation that records every observed page outcome."""
    pages = []
    operation_error = None
    details = {}
    with _MemorySampler() as memory:
        started = time.perf_counter()
        try:
            details = await operation(pages.append) or {}
        except Exception as exc:
            operation_error = f'{type(exc).__name__}: {exc}'
        duration = time.perf_counter() - started

    counts = {name: 0 for name in ('successful', 'partial', 'failed', 'skipped')}
    for page in pages:
        counts[_outcome(page)] += 1
    complete_count = counts['successful']
    missing = max(0, expected_results - len(pages)) if expected_results is not None else 0
    if operation_error or counts['failed'] or not pages or details.get('report_status') in ('error', 'failed'):
        status = 'failed'
    elif counts['partial'] or counts['skipped'] or missing or details.get('report_status') == 'partial':
        status = 'partial'
    else:
        status = 'complete'
    errors = [page.get('error') for page in pages if isinstance(page, dict) and page.get('error')]
    for page in pages:
        if isinstance(page, dict):
            errors.extend(page.get('analyzer_errors', {}).values())
    if operation_error:
        errors.append(operation_error)
    result = {
        'type': kind, **metadata, **details,
        'status': status,
        'successful_pages': complete_count,
        'partial_pages': counts['partial'],
        'failed_pages': counts['failed'],
        'skipped_pages': counts['skipped'],
        'observed_results': len(pages),
        'missing_results': missing,
        # These legacy names now count only complete analyses.
        'pages_analyzed': complete_count,
        'pages_per_second': complete_count / duration if duration > 0 else None,
        'avg_time_per_page': duration / complete_count if complete_count else None,
        'duration_seconds': duration,
        'clock': 'perf_counter',
        **memory.metrics(),
        'errors': errors,
        'timestamp': datetime.now().isoformat(),
    }
    if len(pages) == 1 and isinstance(pages[0], dict):
        result['score'] = pages[0].get('overall_score')
        result['issues_found'] = len(pages[0].get('issues', []))
    rate = result['pages_per_second']
    rate_text = f'{rate:.2f}' if rate is not None else 'unavailable'
    print(f'{kind}: {status}; {complete_count} complete, {counts["partial"]} partial, '
          f'{counts["failed"]} failed, {counts["skipped"]} skipped; '
          f'{duration:.3f}s, {rate_text} complete pages/sec')
    for error in errors:
        print(f'  {error}')
    return result


async def benchmark_single_page(url: str = 'https://example.com') -> Dict[str, Any]:
    """Benchmark one explicitly requested network analysis."""
    async def operation(record):
        record(await SEOAnalyzer(Config()).analyze_url(url))
    return await _measure('single_page', operation, {'url': url}, expected_results=1)


async def benchmark_crawl(start_url: str = 'https://example.com', max_pages: int = 10) -> Dict[str, Any]:
    """Benchmark a network crawl, counting incomplete and failed outcomes separately."""
    config = Config.from_dict({'crawler': {'max_pages': max_pages, 'max_concurrent': 10}})

    async def operation(record):
        async for result in SEOAnalyzer(config).crawl_site(start_url):
            record(result)
    return await _measure('crawl', operation, {'start_url': start_url, 'max_pages': max_pages})


async def benchmark_batch(urls: list, concurrent: int = 10) -> Dict[str, Any]:
    """Benchmark unique supplied network URLs without treating failures as throughput."""
    unique_urls = list(dict.fromkeys(urls))
    config = Config.from_dict({'crawler': {'max_concurrent': concurrent, 'max_pages': max(1, len(unique_urls))}})

    async def operation(record):
        async for result in SEOAnalyzer(config).analyze_urls(unique_urls):
            record(result)
    return await _measure('batch', operation, {'urls_count': len(unique_urls), 'concurrent': concurrent},
                          expected_results=len(unique_urls))


async def benchmark_offline(page_count: int = 500) -> Dict[str, Any]:
    """Measure parsing, static analysis, and report aggregation over local fixtures.

    This workload does not fetch URLs or measure browser/network performance.
    Page cache reuse is disabled, and the fixture version identifies comparable runs.
    """
    if type(page_count) is not int or page_count <= 0:
        raise ValueError('page_count must be a positive integer')
    config = Config.from_dict({'crawler': {'cache_enabled': False, 'max_pages': page_count}})
    pages = []

    async def operation(record):
        analyzer = SEOAnalyzer(config)
        for index in range(page_count):
            html = (
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<title>Offline benchmark fixture page {index}</title>'
                '<meta name="description" content="A deterministic local fixture for analysis benchmark comparisons.">'
                '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
                f'<h1>Fixture page {index}</h1><p>Local benchmark content with stable markup.</p>'
                f'<a href="/page/{(index + 1) % page_count}">Next fixture page</a></body></html>'
            )
            result = await analyzer.analyze_page({
                'url': f'https://benchmark.test/page/{index}',
                'status_code': 200,
                'headers': {'Content-Type': 'text/html; charset=utf-8'},
                'content_length': len(html.encode('utf-8')),
                'soup': BeautifulSoup(html, 'html.parser'),
                'load_time': None,
            })
            pages.append(result)
            record(result)
        report = analyzer.generate_site_report(pages)
        exported = report.get('pages', {})
        report_pages = sum(len(exported.get(name, [])) for name in ('detailed', 'failed', 'skipped'))
        if report_pages != page_count:
            raise RuntimeError(f'Report retained {report_pages} of {page_count} fixture pages')
        return {'report_pages': report_pages, 'report_status': report.get('status')}

    return await _measure('offline', operation,
                          {'fixture_version': 1, 'requested_pages': page_count, 'network_access': False,
                           'workload': 'HTML parsing, static analysis and report aggregation; no HTTP or browser measurement'},
                          expected_results=page_count)


def compare_with_targets() -> Dict[str, Any]:
    """Compatibility helper: no unverified, machine-independent targets are defined."""
    return {}


async def run_all_benchmarks(page_count: int = 500, output_file: Optional[str] = None):
    """Run the default offline workload and save its measured outcomes as JSON."""
    benchmark = await benchmark_offline(page_count)
    results = {
        'status': benchmark['status'],
        'benchmarks': [benchmark],
        'system_info': {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024 ** 3), 2),
            'python_version': sys.version,
            'timestamp': datetime.now().isoformat(),
        },
    }
    output = Path(output_file) if output_file else Path(
        f'benchmark_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8') as stream:
        json.dump(results, stream, indent=2, ensure_ascii=False, allow_nan=False)
    print(f'Benchmark results saved to: {output}')
    return results


def _positive_int(value):
    try:
        number = int(value)
        if number > 0:
            return number
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('must be a positive integer')


def main(argv=None):
    """CLI exit codes: 0 complete, 1 failed/incomplete, 2 invalid arguments, 130 cancelled."""
    parser = argparse.ArgumentParser(description='Benchmark deterministic offline HTML analysis and reporting.')
    parser.add_argument('--pages', type=_positive_int, default=500, help='fixture page count (default: 500)')
    parser.add_argument('--output', help='JSON results path (default: timestamped file)')
    args = parser.parse_args(argv)
    try:
        results = asyncio.run(run_all_benchmarks(args.pages, args.output))
        return 0 if results['status'] == 'complete' else 1
    except KeyboardInterrupt:
        print('Benchmark interrupted.', file=sys.stderr)
        return 130
    except Exception as exc:
        print(f'Benchmark failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
