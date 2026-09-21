"""Outcome-aware benchmarks; the default workload uses offline HTML fixtures."""

import argparse
import asyncio
import hashlib
import json
import math
import platform
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from statistics import median
from typing import Any, Dict, Optional

import psutil
from bs4 import BeautifulSoup

from .core.app import SEOAnalyzer
from .core.config import Config
from .core.models import SCHEMA_VERSION
from .page_facts import FACTS_VERSION
from .rules import RULESET_VERSION, SCORING_VERSION
from . import __version__


SCENARIOS = ('basic', 'content-heavy', 'link-dense', 'mixed')
DIRECT_DEPENDENCIES = ('aiohttp', 'beautifulsoup4', 'click', 'jinja2', 'rich', 'textstat',
                       'validators', 'pyyaml', 'python-dateutil', 'urllib3', 'psutil')
OPTIONAL_DEPENDENCIES = ('lxml', 'openpyxl', 'pandas')


def _installed_version(name):
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _cpu_model():
    if sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
                return winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
        except OSError:
            pass
    cpuinfo = Path('/proc/cpuinfo')
    if sys.platform.startswith('linux') and cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding='utf-8').splitlines():
            if line.lower().startswith('model name'):
                return line.partition(':')[2].strip()
    return platform.processor() or None


def _source_fingerprint():
    """Identify measured code and packaged templates without local paths."""
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    count = 0
    for path in sorted(path for path in root.rglob('*') if path.suffix in ('.py', '.html')):
        digest.update(path.relative_to(root).as_posix().encode('utf-8') + b'\0')
        digest.update(path.read_bytes())
        count += 1
    return {'algorithm': 'sha256', 'scope': 'package Python and HTML template paths and bytes',
            'file_count': count, 'digest': digest.hexdigest()}


def _environment():
    return {
        'os': {'system': platform.system(), 'release': platform.release(), 'version': platform.version()},
        'architecture': platform.machine(), 'cpu_model': _cpu_model(),
        'cpu_count': psutil.cpu_count(), 'physical_cpu_count': psutil.cpu_count(logical=False),
        'memory_total_gb': round(psutil.virtual_memory().total / (1024 ** 3), 2),
        'python_version': sys.version, 'python_implementation': platform.python_implementation(),
        'package_version': __version__, 'installed_distribution_version': _installed_version('tfq0seo'),
        'schema_version': SCHEMA_VERSION, 'ruleset_version': RULESET_VERSION,
        'scoring_version': SCORING_VERSION, 'facts_version': FACTS_VERSION,
        'direct_dependencies': {name: _installed_version(name) for name in DIRECT_DEPENDENCIES},
        'optional_dependencies': {name: _installed_version(name) for name in OPTIONAL_DEPENDENCIES},
        'readability_dependencies': {name: _installed_version(name) for name in ('nltk', 'pyphen', 'cmudict')},
        'source_fingerprint': _source_fingerprint(),
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }


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
        'timestamp': datetime.now(timezone.utc).isoformat(),
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


def _fixture_html(index, page_count, scenario):
    """Return stable HTML and its scenario; fixture version 1 is append-only."""
    variant = SCENARIOS[index % 3] if scenario == 'mixed' else scenario
    head = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>Offline benchmark fixture page {index}</title>'
        '<meta name="description" content="A deterministic local fixture for analysis benchmark comparisons.">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    body = (f'<h1>Fixture page {index}</h1><p>Local benchmark content with stable markup.</p>'
            f'<a href="/page/{(index + 1) % page_count}">Next fixture page</a>')
    if variant == 'content-heavy':
        head += (f'<link rel="canonical" href="https://benchmark.test/page/{index}">'
                 '<link rel="stylesheet" href="/assets/site.css">'
                 '<script src="/assets/site.js" defer></script>')
        paragraphs = []
        for section in range(12):
            sentences = [
                f'Page {index} section {section} example {example} describes how a local team plans clear '
                'instructions for readers. The guide explains each step with useful details and a short '
                'review of the result. Readers can use this example to compare different choices and '
                'record what they learn.' for example in range(2)
            ]
            paragraphs.append(f'<section><h2>Topic {section}</h2>' +
                              ''.join(f'<p>{sentence}</p>' for sentence in sentences) + '</section>')
        body += '<main><article>' + ''.join(paragraphs) + '</article>'
        body += ''.join(f'<figure><img src="/assets/photo-{image}.png" width="640" height="480" '
                        f'loading="lazy" alt="Illustration {image}"><figcaption>Example {image}</figcaption></figure>'
                        for image in range(8))
        body += '<table><caption>Local observations</caption><tr><th>Item</th><th>Value</th></tr>'
        body += ''.join(f'<tr><td>Sample {row}</td><td>{index + row}</td></tr>' for row in range(20))
        body += '</table></main>'
    elif variant == 'link-dense':
        head += f'<link rel="canonical" href="https://benchmark.test/page/{index}">'
        body += '<nav>' + ''.join(
            f'<a href="/page/{(index + offset) % page_count}">Related fixture {offset}</a>'
            for offset in range(1, 33)) + '</nav>'
        body += ''.join(f'<a href="https://reference-{external}.test/guide" rel="nofollow">Reference {external}</a>'
                        for external in range(4))
        body += '<a href="mailto:reader@benchmark.test">Contact</a><a href="#details">Details</a>'
        body += '<section id="details"><h2>Link inventory</h2><p>Only HTML references are observed.</p></section>'
    return head + '</head><body>' + body + '</body></html>', variant


def _check_offline_options(page_count, scenario, timeout_seconds):
    if type(page_count) is not int or page_count <= 0:
        raise ValueError('page_count must be a positive integer')
    if scenario not in SCENARIOS:
        raise ValueError('scenario must be one of: ' + ', '.join(SCENARIOS))
    if timeout_seconds is not None and (isinstance(timeout_seconds, bool) or
            not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise ValueError('timeout_seconds must be a finite positive number')


async def benchmark_offline(page_count: int = 500, scenario: str = 'basic',
                            timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
    """Measure parsing, static analysis, and report aggregation over local fixtures.

    This workload does not fetch URLs or measure browser/network performance.
    Page cache reuse is disabled, and the fixture version identifies comparable runs.
    """
    _check_offline_options(page_count, scenario, timeout_seconds)
    config = Config.from_dict({'crawler': {'cache_enabled': False, 'max_pages': page_count}})
    pages = []
    fixture = {'version': 1, 'generated_pages': 0, 'html_bytes': 0, 'dom_elements': 0,
               'href_references': 0, 'image_elements': 0,
               'analyzed_word_count': 0, 'pages_with_word_count': 0,
               'variants': {name: 0 for name in SCENARIOS[:3]}, 'sha256': None}
    metadata = {
        'fixture_version': 1, 'scenario': scenario, 'requested_pages': page_count,
        'network_access': False, 'config': config.to_dict(), 'fixture': fixture,
        'timeout_seconds': timeout_seconds, 'timed_out': False,
        'timeout_scope': 'Cooperative checks between pages and after reporting; synchronous work can overrun the deadline.',
        'report_completeness': None,
        'readability': {'status_counts': {}, 'missing_resources': []},
        'workload': 'Fixture generation, HTML parsing, static analysis, site report aggregation and retained-URL verification; no HTTP, browser or export measurement',
    }

    async def operation(record):
        started = time.perf_counter()
        analyzer = SEOAnalyzer(config)
        digest = hashlib.sha256()

        def check_deadline():
            if timeout_seconds is not None and time.perf_counter() - started >= timeout_seconds:
                metadata['timed_out'] = True
                raise TimeoutError(f'Offline benchmark exceeded its {timeout_seconds:g}s cooperative deadline')

        for index in range(page_count):
            check_deadline()
            html, variant = _fixture_html(index, page_count, scenario)
            url = f'https://benchmark.test/page/{index}'
            encoded = html.encode('utf-8')
            digest.update(url.encode('utf-8') + b'\0' + encoded + b'\0')
            soup = BeautifulSoup(html, 'html.parser')
            fixture['generated_pages'] += 1
            fixture['html_bytes'] += len(encoded)
            fixture['dom_elements'] += len(soup.find_all(True))
            fixture['href_references'] += len(soup.find_all('a', href=True))
            fixture['image_elements'] += len(soup.find_all('img'))
            fixture['variants'][variant] += 1
            fixture['sha256'] = digest.hexdigest()
            result = await analyzer.analyze_page({
                'url': url,
                'status_code': 200,
                'headers': {'Content-Type': 'text/html; charset=utf-8'},
                'content_length': len(encoded),
                'soup': soup,
                'load_time': None,
            })
            pages.append(result)
            record(result)
            if isinstance(result, dict):
                content = result.get('content', {}).get('data', {})
                word_count = content.get('metrics', {}).get('word_count')
                if type(word_count) is int:
                    fixture['analyzed_word_count'] += word_count
                    fixture['pages_with_word_count'] += 1
                readability = content.get('readability', {})
                status = readability.get('status', 'not_requested')
                status_counts = metadata['readability']['status_counts']
                status_counts[status] = status_counts.get(status, 0) + 1
                metadata['readability']['missing_resources'] = sorted(set(
                    metadata['readability']['missing_resources'] + readability.get('missing_resources', [])))
        check_deadline()
        report_started = time.perf_counter()
        metadata['analysis_duration_seconds'] = report_started - started
        report = analyzer.generate_site_report(pages)
        metadata['report_duration_seconds'] = time.perf_counter() - report_started
        exported = report.get('pages', {})
        rows = [row for name in ('detailed', 'failed', 'skipped') for row in exported.get(name, [])]
        urls = {row.get('url') for row in rows}
        expected = {f'https://benchmark.test/page/{index}' for index in range(page_count)}
        completeness = {
            'expected_pages': page_count, 'retained_rows': len(rows), 'unique_urls': len(urls),
            'missing_urls': len(expected - urls), 'unexpected_urls': len(urls - expected),
            'duplicate_rows': len(rows) - len(urls),
            'complete': len(rows) == page_count and urls == expected,
        }
        site = report.get('site_analysis', {})
        metadata.update({
            'report_pages': len(rows), 'report_status': report.get('status'),
            'report_completeness': completeness, 'report_summary': report.get('summary', {}),
            'rule_coverage': report.get('rule_coverage', {}),
            'site_analysis': {'version': site.get('version'), 'coverage': site.get('coverage', {}),
                              'node_count': site.get('links', {}).get('node_count'),
                              'edge_count': site.get('links', {}).get('edge_count'),
                              'finding_count': len(site.get('findings', []))},
        })
        if not completeness['complete']:
            raise RuntimeError(f'Report retained {len(rows)} rows and {len(urls & expected)} of {page_count} expected fixture URLs')
        check_deadline()
        return {'report_status': report.get('status')}

    async def bounded_operation(record):
        if timeout_seconds is None:
            return await operation(record)
        try:
            return await asyncio.wait_for(operation(record), timeout_seconds)
        except asyncio.TimeoutError as exc:
            metadata['timed_out'] = True
            raise TimeoutError(f'Offline benchmark exceeded its {timeout_seconds:g}s cooperative deadline') from exc

    return await _measure('offline', bounded_operation, metadata, expected_results=page_count)


def compare_with_targets() -> Dict[str, Any]:
    """Compatibility helper: no unverified, machine-independent targets are defined."""
    return {}


async def benchmark_pipeline(page_count: int = 500, scenario: str = 'basic',
                             timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
    """Measure real loopback HTTP crawling, analysis, reporting, and file exports.

    The seed links to every fixture so depth does not truncate a large site.
    Referenced assets and off-site destinations are excluded from crawling.
    Files live in a temporary directory; their sizes and hashes are retained.
    """
    from aiohttp import web
    from .exporters.base import ExportManager, OPENPYXL_AVAILABLE

    _check_offline_options(page_count, scenario, timeout_seconds)
    config = Config.from_dict({
        'crawler': {'cache_enabled': False, 'max_pages': page_count, 'max_depth': 2,
                    'use_sitemap': False, 'delay_between_requests': 0, 'adaptive_delay': False,
                    'excluded_patterns': [r'/assets/'],
                    'max_crawl_time': max(1, math.ceil(timeout_seconds or 3600))},
        'export': {'html_template': 'optimized'},
    })
    formats = ['json', 'html', 'csv'] + (['xlsx'] if OPENPYXL_AVAILABLE else [])
    metadata = {
        'scenario': scenario, 'requested_pages': page_count, 'fixture_version': 1,
        'network_access': 'loopback HTTP only', 'config': config.to_dict(),
        'timeout_seconds': timeout_seconds, 'timed_out': False,
        'timeout_scope': 'Cooperative crawl deadline and checks between synchronous report/export stages.',
        'workload': 'Loopback HTTP including robots, bounded crawling, static analysis, report generation, atomic exports, and file hashing. No browser or remote requests.',
        'exports': [], 'unavailable_exports': [] if OPENPYXL_AVAILABLE else ['xlsx'],
        'report_completeness': None,
        'readability': {'status_counts': {}, 'missing_resources': []},
    }

    async def operation(record):
        started = time.perf_counter()

        def check_deadline():
            if timeout_seconds is not None and time.perf_counter() - started > timeout_seconds:
                metadata['timed_out'] = True
                raise TimeoutError('Pipeline benchmark exceeded its cooperative deadline')

        requests = {}
        base = ''

        def fixture(index, origin):
            html, variant = _fixture_html(index, page_count, scenario)
            html = html.replace('https://benchmark.test', origin)
            if index == 0:
                fanout = ''.join(f'<a href="/page/{i}">Fixture {i}</a>' for i in range(1, page_count))
                html = html.replace('</body>', '<nav>' + fanout + '</nav></body>')
            return html, variant

        digest = hashlib.sha256()
        for index in range(page_count):
            html, _ = fixture(index, 'https://benchmark.test')
            digest.update(str(index).encode() + b'\0' + html.encode('utf-8'))
        metadata['fixture_sha256'] = digest.hexdigest()
        metadata['fixture_transform'] = 'Canonical origin replaced by loopback origin; seed fanout to all fixture pages. Hash uses benchmark.test before origin substitution.'

        async def handler(request):
            requests[request.path] = requests.get(request.path, 0) + 1
            if request.path == '/robots.txt':
                return web.Response(text='User-agent: *\nDisallow: /assets/\n')
            try:
                index = int(request.match_info['index'])
            except (KeyError, ValueError):
                raise web.HTTPNotFound()
            if not 0 <= index < page_count:
                raise web.HTTPNotFound()
            html, _ = fixture(index, base)
            return web.Response(text=html, content_type='text/html')

        application = web.Application()
        application.router.add_get('/robots.txt', handler)
        application.router.add_get('/page/{index}', handler)
        runner = web.AppRunner(application)
        await runner.setup()
        try:
            site = web.TCPSite(runner, '127.0.0.1', 0)
            await site.start()
            base = 'http://127.0.0.1:' + str(runner.addresses[0][1])
            analyzer = SEOAnalyzer(config)
            iterator = analyzer.crawl_site(base + '/page/0')
            try:
                async for result in iterator:
                    record(result)
                    readability = result.get('content', {}).get('data', {}).get('readability', {})
                    status = readability.get('status', 'not_requested')
                    counts = metadata['readability']['status_counts']
                    counts[status] = counts.get(status, 0) + 1
                    metadata['readability']['missing_resources'] = sorted(set(
                        metadata['readability']['missing_resources'] + readability.get('missing_resources', [])))
                    check_deadline()
            finally:
                await iterator.aclose()
            metadata['analysis_duration_seconds'] = time.perf_counter() - started
            metadata['http_requests'] = {'total': sum(requests.values()),
                                         'robots': requests.get('/robots.txt', 0),
                                         'pages': sum(count for path, count in requests.items() if path.startswith('/page/'))}
            metadata['result_buffer'] = {'capacity': analyzer.crawler.result_buffer_capacity,
                                          'peak': analyzer.crawler.result_buffer_peak}
            stage = time.perf_counter()
            report = analyzer.generate_site_report()
            metadata['report_duration_seconds'] = time.perf_counter() - stage
            rows = [row for group in ('detailed', 'failed', 'skipped') for row in report['pages'][group]]
            urls = {row['url'] for row in rows}
            expected = {base + f'/page/{index}' for index in range(page_count)}
            metadata['report_completeness'] = {
                'expected_pages': page_count, 'retained_rows': len(rows), 'unique_urls': len(urls),
                'missing_urls': len(expected - urls), 'unexpected_urls': len(urls - expected),
                'duplicate_rows': len(rows) - len(urls), 'complete': len(rows) == page_count and urls == expected,
            }
            metadata['report_status'] = report['status']
            metadata['report_summary'] = report['summary']
            if not metadata['report_completeness']['complete']:
                raise RuntimeError('Pipeline report did not retain every expected fixture URL exactly once')
            check_deadline()
            with tempfile.TemporaryDirectory(prefix='tfq0seo-pipeline-') as directory:
                exporter = ExportManager({'output_directory': directory, 'html_template': 'optimized'})
                for format in formats:
                    stage = time.perf_counter()
                    path = Path(exporter.export(report, format, str(Path(directory, 'report.' + format))))
                    duration = time.perf_counter() - stage
                    digest = hashlib.sha256()
                    with path.open('rb') as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                            digest.update(chunk)
                    metadata['exports'].append({'format': format, 'bytes': path.stat().st_size,
                                                 'sha256': digest.hexdigest(), 'duration_seconds': duration})
                    check_deadline()
            metadata['export_duration_seconds'] = sum(item['duration_seconds'] for item in metadata['exports'])
            return {'report_status': report['status']}
        finally:
            await runner.cleanup()

    return await _measure('pipeline', operation, metadata, expected_results=page_count)


def _summarize_runs(runs):
    groups = {}
    for run in runs:
        groups.setdefault((run['scenario'], run['requested_pages']), []).append(run)
    summaries = []
    for (scenario, page_count), group in groups.items():
        complete = [run for run in group if run['status'] == 'complete']
        metrics = {}
        for name in ('duration_seconds', 'analysis_duration_seconds', 'report_duration_seconds', 'export_duration_seconds',
                     'pages_per_second', 'memory_rss_delta_mb', 'memory_sampled_peak_mb'):
            values = [run[name] for run in complete if isinstance(run.get(name), (int, float))]
            if values:
                metrics[name] = {'median': median(values), 'min': min(values), 'max': max(values)}
        summaries.append({
            'scenario': scenario, 'requested_pages': page_count, 'runs': len(group),
            'complete_runs': len(complete), 'partial_runs': sum(run['status'] == 'partial' for run in group),
            'failed_runs': sum(run['status'] == 'failed' for run in group),
            'metrics_scope': 'Only complete runs; inspect raw outcomes for excluded failed or partial runs.',
            'metrics': metrics,
        })
    return summaries


async def run_all_benchmarks(page_count: int = 500, output_file: Optional[str] = None, *,
                             scenarios=None, repetitions: int = 1, page_counts=None,
                             timeout_seconds: Optional[float] = None, pipeline: bool = False):
    """Save offline runs and summaries; default remains one basic 500-page run.

    Repetitions run in the same process, with a fresh analyzer and disabled page
    cache. Library caches and allocator state can remain warm between runs.
    """
    selected = list(scenarios) if scenarios is not None else ['basic']
    sizes = list(page_counts) if page_counts is not None else [page_count]
    if not selected or not sizes:
        raise ValueError('scenarios and page_counts must not be empty')
    if type(repetitions) is not int or repetitions <= 0:
        raise ValueError('repetitions must be a positive integer')
    if len(set(selected)) != len(selected) or len(set(sizes)) != len(sizes):
        raise ValueError('scenarios and page_counts must not contain duplicates')
    for scenario in selected:
        for size in sizes:
            _check_offline_options(size, scenario, timeout_seconds)
    environment = _environment()
    benchmarks = []
    for size in sizes:
        for scenario in selected:
            for repetition in range(1, repetitions + 1):
                # Preserve the original default call shape for API wrappers.
                if pipeline:
                    run = await benchmark_pipeline(size, scenario=scenario, timeout_seconds=timeout_seconds)
                elif scenario == 'basic' and timeout_seconds is None:
                    run = await benchmark_offline(size)
                else:
                    run = await benchmark_offline(size, scenario=scenario, timeout_seconds=timeout_seconds)
                run.update({'scenario': scenario, 'requested_pages': size, 'repetition': repetition,
                            'run_order': len(benchmarks) + 1})
                benchmarks.append(run)
    source_unchanged = environment['source_fingerprint'] == _source_fingerprint()
    status = ('failed' if not source_unchanged or any(run['status'] == 'failed' for run in benchmarks)
              else 'partial' if any(run['status'] != 'complete' for run in benchmarks) else 'complete')
    results = {
        'benchmark_schema_version': 2,
        'status': status,
        'benchmarks': benchmarks,
        'summaries': _summarize_runs(benchmarks),
        'system_info': environment,
        'source_unchanged_during_suite': source_unchanged,
        'errors': [] if source_unchanged else ['Package source changed during measurement; repeat on a stable checkout.'],
        'suite': {'scenarios': selected, 'page_counts': sizes, 'repetitions': repetitions,
                  'workload': 'pipeline' if pipeline else 'offline',
                  'timeout_seconds': timeout_seconds,
                  'order': 'Page counts, then scenarios, then repetitions, in supplied order.',
                  'isolation': 'Same process; fresh analyzer per run, disabled page cache; library caches and allocator state may remain warm.'},
    }
    output = Path(output_file) if output_file else Path(
        f'benchmark_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8') as stream:
        json.dump(results, stream, indent=2, ensure_ascii=False, allow_nan=False)
    print(f'Benchmark results saved to: {output}')
    for error in results['errors']:
        print(error)
    return results


def _positive_int(value):
    try:
        number = int(value)
        if number > 0:
            return number
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('must be a positive integer')


def _positive_float(value):
    try:
        number = float(value)
        if math.isfinite(number) and number > 0:
            return number
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('must be a finite positive number')


def main(argv=None):
    """CLI exit codes: 0 complete, 1 failed/incomplete, 2 invalid arguments, 130 cancelled."""
    parser = argparse.ArgumentParser(description='Benchmark deterministic offline HTML analysis and reporting.')
    parser.add_argument('--pages', type=_positive_int, nargs='+', default=[500],
                        help='one or more fixture page counts (default: 500)')
    scenario_group = parser.add_mutually_exclusive_group()
    scenario_group.add_argument('--scenario', choices=SCENARIOS, default='basic', help='fixture scenario (default: basic)')
    scenario_group.add_argument('--suite', action='store_true', help='run every scenario')
    parser.add_argument('--repetitions', type=_positive_int, default=1, help='runs per size and scenario (default: 1)')
    parser.add_argument('--timeout-seconds', type=_positive_float,
                        help='cooperative deadline per run; synchronous work may overrun it')
    parser.add_argument('--output', help='JSON results path (default: timestamped file)')
    parser.add_argument('--pipeline', action='store_true',
                        help='measure loopback HTTP crawling through atomic JSON/HTML/CSV exports (also XLSX when installed)')
    args = parser.parse_args(argv)
    try:
        results = asyncio.run(run_all_benchmarks(
            args.pages[0], args.output, page_counts=args.pages,
            scenarios=SCENARIOS if args.suite else [args.scenario],
            repetitions=args.repetitions, timeout_seconds=args.timeout_seconds,
            **({'pipeline': True} if args.pipeline else {})))
        return 0 if results['status'] == 'complete' else 1
    except KeyboardInterrupt:
        print('Benchmark interrupted.', file=sys.stderr)
        return 130
    except Exception as exc:
        print(f'Benchmark failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
