"""Advanced SEO application orchestrator with parallel processing and intelligent analysis coordination."""

import asyncio
import time
import hashlib
import json
import math
import copy
from functools import partial
import psutil
from typing import Dict, List, Any, Optional, AsyncIterator, Set, Tuple
from urllib.parse import urlparse
from collections import defaultdict, Counter, OrderedDict
from dataclasses import dataclass, field
from enum import Enum
import logging

from .config import Config
from .crawler import Crawler
from .models import (ANALYZER_NAMES, SCHEMA_VERSION, FetchResult, PageResult, SiteReport,
                     ContractError, normalize_fetch_result, validate_analyzer_result)
from .report_contracts import validate_page_result, validate_site_report
from ..page_facts import FACTS_VERSION, extract_page_facts
from ..urls import resolve_url
from ..site_analysis import analyze_site, url_identity
from ..rules import (RULESET_VERSION, SCORING_VERSION, get_rule, rule_result,
                     merge_rule_results, rule_coverage, finding_penalty, recommendations_for)
from .report_optimizer import (
    aggregate_issues,
    generate_specific_recommendations,
    create_executive_summary,
    generate_performance_metrics
)
from ..analyzers import (
    analyze_seo,
    analyze_content,
    analyze_technical,
    analyze_performance,
    analyze_links
)

# Setup logging
logger = logging.getLogger(__name__)


class AnalysisMode(Enum):
    """Analysis execution modes."""
    QUICK = "quick"        # Fast, basic analysis
    STANDARD = "standard"  # Default balanced analysis
    DEEP = "deep"         # Comprehensive analysis
    CUSTOM = "custom"     # Custom analyzer selection


class PagePriority(Enum):
    """Page priority levels for analysis order."""
    CRITICAL = 1  # Homepage, key landing pages
    HIGH = 2      # Main navigation pages
    MEDIUM = 3    # Regular content pages
    LOW = 4       # Deep pages, archives


@dataclass
class AnalysisContext:
    """Context for page analysis with metadata."""
    url: str
    depth: int = 0
    priority: PagePriority = PagePriority.MEDIUM
    parent_url: Optional[str] = None
    discovery_time: float = field(default_factory=time.time)
    retry_count: int = 0
    partial_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisStats:
    """Detailed analysis statistics."""
    total_pages: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    skipped_pages: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    warnings: int = 0
    notices: int = 0
    avg_analysis_time: float = 0.0
    avg_page_score: float = 0.0
    memory_peak_mb: float = 0.0
    analysis_start: float = field(default_factory=time.time)
    analysis_end: float = 0.0


@dataclass
class CrawlProgress:
    """Real-time crawl progress tracking."""
    pages_queued: int = 0
    pages_crawled: int = 0
    pages_analyzed: int = 0
    pages_remaining: int = 0
    current_url: Optional[str] = None
    current_depth: int = 0
    errors: List[str] = field(default_factory=list)
    eta_seconds: float = 0.0
    speed_pages_per_sec: float = 0.0


class AnalysisCache:
    """Bounded LRU cache of immutable snapshots, keyed by analysis inputs."""

    def __init__(self, ttl_seconds: int = 3600, max_bytes: int = 100 * 1024 * 1024):
        self.cache = OrderedDict()
        self.ttl = ttl_seconds
        self.max_bytes = max_bytes
        self.size_bytes = 0

    def get(self, key: str) -> Optional[Dict]:
        entry = self.cache.get(key)
        if entry is None:
            return None
        value, created, size = entry
        if time.monotonic() - created >= self.ttl:
            self.size_bytes -= size
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return copy.deepcopy(value)

    def set(self, key: str, result: Dict) -> None:
        self.clear_expired()
        size = len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8'))
        if size > self.max_bytes:
            return
        previous = self.cache.pop(key, None)
        if previous:
            self.size_bytes -= previous[2]
        while self.cache and self.size_bytes + size > self.max_bytes:
            self.size_bytes -= self.cache.popitem(last=False)[1][2]
        self.cache[key] = (copy.deepcopy(result), time.monotonic(), size)
        self.size_bytes += size

    def clear_expired(self) -> None:
        for key in list(self.cache):
            if time.monotonic() - self.cache[key][1] >= self.ttl:
                self.size_bytes -= self.cache.pop(key)[2]

    def clear(self) -> None:
        self.cache.clear()
        self.size_bytes = 0


class SEOAnalyzer:
    """Coordinate bounded fetches, explicit analysis outcomes, and complete reports."""

    def __init__(self, config: Optional[Config] = None, mode: Optional[AnalysisMode] = None):
        self.config = config or Config()
        self.config.require_valid()
        self.mode = AnalysisMode(mode or self.config.analysis.analysis_mode)
        if not self._enabled_analyzers():
            raise ValueError('The selected mode has no enabled analyzers')
        self.cache = AnalysisCache(self.config.crawler.cache_ttl,
                                   self.config.crawler.cache_size_mb * 1024 * 1024)
        self.crawler = None
        self._analysis_slots = None
        self._analysis_loop = None
        self._semaphore = None
        self._start_time = None
        self._reset_state()

    def _reset_state(self) -> None:
        self.results = []
        self.broken_links: Set[str] = set()
        self.redirects: Dict[str, str] = {}
        self.duplicate_content = defaultdict(list)
        self.analysis_contexts = {}
        self.stats = AnalysisStats()
        self.progress = CrawlProgress()
        self._page_times = []
        self.link_checks = []
        self._crawl_complete = False
        self._run_limits = []
        self._discovery_errors = []
        self._site_start_url = None

    def _begin_run(self) -> None:
        self.config.require_valid()
        self._reset_state()
        self._start_time = time.time()
        self.stats.analysis_start = self._start_time
        self._semaphore = asyncio.Semaphore(self.config.analysis.max_analysis_threads)

    def _get_page_priority(self, url: str, depth: int = 0) -> PagePriority:
        try:
            path = urlparse(url).path
        except ValueError:
            return PagePriority.MEDIUM
        if path in ('', '/', '/index.html', '/index.php'):
            return PagePriority.CRITICAL
        return PagePriority.HIGH if depth <= 1 else PagePriority.MEDIUM if depth <= 2 else PagePriority.LOW

    def _should_skip_analysis(self, url: str) -> bool:
        try:
            return urlparse(url).path.lower().endswith(
                ('.pdf', '.doc', '.xls', '.zip', '.mp4', '.mp3', '.jpg', '.png', '.gif'))
        except ValueError:
            return False

    def _calculate_content_hash(self, content: str) -> str:
        return hashlib.sha256(' '.join(content.split()).encode('utf-8')).hexdigest()

    def _enabled_analyzers(self) -> List[str]:
        names = self.config.analysis.enabled_analyzers
        return [name for name in names if self.mode != AnalysisMode.QUICK or name in ('seo', 'technical')]

    async def analyze_page(self, page_data: FetchResult,
                           context: Optional[AnalysisContext] = None) -> PageResult:
        page_data = normalize_fetch_result(page_data, '$.fetch')
        url = page_data['url']
        context = context or AnalysisContext(url=url, depth=page_data.get('depth', 0),
                                            parent_url=page_data.get('parent_url'))
        status = page_data.get('status_code', 0)
        result = {
            'schema_version': SCHEMA_VERSION, 'url': url,
            'requested_url': page_data.get('requested_url', page_data.get('redirected_from') or url),
            'status_code': status, 'load_time': page_data.get('load_time'),
            'content_length': page_data.get('content_length', 0),
            'timestamp': page_data.get('timestamp', time.time()),
            'timings': page_data.get('timings', {}),
            'redirect_chain': copy.deepcopy(page_data.get('redirect_chain', [])),
            'truncated': bool(page_data.get('truncated', False)),
            'context': {'depth': context.depth, 'priority': context.priority.value,
                        'parent_url': context.parent_url},
            'overall_score': None, 'issues': [], 'issue_counts': self._count_issues([]),
            'recommendations': [], 'status': 'complete'
        }
        if status >= 400:
            self.broken_links.add(url)
        if result['requested_url'] != url:
            self.redirects[result['requested_url']] = url
        if page_data.get('error') and (not page_data.get('skipped') or status >= 400):
            result.update(status='error', error=str(page_data['error']))
            self._record_analysis(result)
            return result
        if page_data.get('skipped') or self._should_skip_analysis(url):
            result.update(status='skipped', skipped=True,
                          reason=page_data.get('reason') or page_data.get('error') or 'Non-HTML content')
            self._record_analysis(result)
            return result
        soup = page_data.get('soup')
        if soup is None:
            result.update(status='error', error='No HTML content to analyze')
            self._record_analysis(result)
            return result

        facts = extract_page_facts(soup, url, headers=page_data['headers'])
        html = facts.html
        content_hash = self._calculate_content_hash(facts.text)
        result['content_hash'] = content_hash
        result['page_facts'] = facts.to_dict()
        signature = json.dumps({'url': url, 'html': html, 'headers': page_data['headers'],
                                'status': status, 'load_time': result['load_time'],
                                'content_length': result['content_length'], 'truncated': result['truncated'],
                                'mode': self.mode.value, 'analysis': self.config.to_dict()['analysis'],
                                'schema': SCHEMA_VERSION, 'ruleset': RULESET_VERSION,
                                'scoring': SCORING_VERSION, 'facts': FACTS_VERSION}, sort_keys=True, allow_nan=False)
        cache_key = hashlib.sha256(signature.encode('utf-8')).hexdigest()
        cached = self.cache.get(cache_key) if self.config.crawler.cache_enabled and self.mode != AnalysisMode.DEEP else None
        if cached is not None:
            cached.update({key: result[key] for key in ('context', 'timestamp', 'requested_url', 'redirect_chain', 'timings')})
            cached.update(cached=True, analysis_time=0.0)
            self._record_analysis(cached)
            return cached

        functions = {'seo': analyze_seo, 'content': analyze_content, 'technical': analyze_technical,
                     'performance': analyze_performance, 'links': analyze_links}
        options = {
            'seo': {'headers': page_data['headers']},
            'content': {'target_keywords': self.config.analysis.target_keywords},
            'technical': {'headers': page_data['headers'], 'status_code': status},
            'performance': {'load_time': result['load_time'], 'content_length': result['content_length']},
            # Target status is resolved after all available fetches, not in completion order.
            'links': {'broken_links': None},
        }
        started = time.perf_counter()
        names = self._enabled_analyzers()
        outputs = await asyncio.gather(*[
            self._run_analyzer_safe(name, functions[name], soup, url, facts=facts, **options.get(name, {}))
            for name in names])
        result.update(outputs)
        errors = {name: result[name]['error'] for name in names if result[name].get('error')}
        partial_analyzers = [name for name in names if result[name].get('status') == 'partial']
        result['coverage'] = {'enabled_analyzers': names,
                              'completed_analyzers': [name for name in names if name not in errors],
                              'failed_analyzers': list(errors),
                              'partial_analyzers': partial_analyzers,
                              'ratio': (len(names) - len(errors)) / len(names) if names else 0,
                              'content_complete': not result['truncated'],
                              'measurement_source': 'static_html'}
        result['analyzer_errors'] = errors
        if errors or partial_analyzers or result['truncated']:
            result['status'] = 'partial'
        if len(errors) == len(names):
            result.update(status='error', error='All enabled analyzers failed')
        self._apply_rule_scoring(result)
        result['overall_score'] = self._calculate_weighted_score(result)
        result['issues'] = self._aggregate_page_issues(result)
        result['issue_counts'] = self._count_issues(result['issues'])
        result['recommendations'] = self._generate_page_recommendations(result)
        result['analysis_time'] = time.perf_counter() - started
        self._record_analysis(result)
        if self.config.crawler.cache_enabled and not errors and not partial_analyzers:
            self.cache.set(cache_key, result)
        return result

    async def _run_analyzer_safe(self, name, analyzer_func, *args, **kwargs):
        try:
            if self.config.analysis.parallel_analysis:
                loop = asyncio.get_running_loop()
                if self._analysis_loop is not loop:
                    self._analysis_loop = loop
                    self._analysis_slots = asyncio.Semaphore(self.config.analysis.max_analysis_threads)
                slots = self._analysis_slots
                await slots.acquire()
                try:
                    future = loop.run_in_executor(None, partial(analyzer_func, *args, **kwargs))
                except Exception:
                    slots.release()
                    raise
                # Cancelling the await cannot stop a running thread. Keep its
                # reservation until the work really finishes.
                def finished(completed):
                    slots.release()
                    if not completed.cancelled():
                        completed.exception()  # Retrieve failures even if the awaiting task was cancelled.
                future.add_done_callback(finished)
                value = await asyncio.shield(future)
            else:
                value = analyzer_func(*args, **kwargs)
            validate_analyzer_result(value, '$.' + name)
            if value.get('error'):
                raise ValueError(str(value['error']))
            if 'rule_results' in value:
                if not isinstance(value['rule_results'], list):
                    raise ValueError('Analyzer rule_results must be a list')
                value['rule_coverage'] = rule_coverage(value['rule_results'])
            value['status'] = ('partial' if value.get('status') == 'partial' or
                               value.get('rule_coverage', {}).get('has_errors') else 'complete')
            return name, value
        except Exception as exc:
            logger.error('Analyzer %s failed: %s', name, exc)
            return name, {'status': 'error', 'score': None, 'error': str(exc), 'issues': [], 'data': {}}

    async def _run_analyzer(self, name, analyzer_func, *args):
        return await self._run_analyzer_safe(name, analyzer_func, *args)

    @staticmethod
    def _is_score(value):
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 100

    def _calculate_weighted_score(self, results) -> Optional[float]:
        weighted, total = 0.0, 0.0
        for name, weight in self.config.analysis.score_weights.items():
            category = results.get(name, {})
            score = category.get('score')
            if not category.get('error') and self._is_score(score):
                weighted += score * weight
                total += weight
        return round(weighted / total, 2) if total else None

    def _apply_rule_scoring(self, result):
        """Attribute each unique rule to one available category before weighting."""
        available = [name for name in ANALYZER_NAMES if isinstance(result.get(name), dict)
                     and not result[name].get('error') and 'rule_results' in result[name]]
        if not available:
            return  # Previously exported payloads retain their original scoring semantics.
        evaluations = []
        for name in available:
            for original in result[name]['rule_results']:
                evaluation = dict(original)
                evaluation['reported_by'] = sorted(set(evaluation.get('reported_by', [])) | {name})
                evaluations.append(evaluation)
        merged = merge_rule_results(evaluations, copy_evidence=False)
        penalties = {name: 0 for name in available}
        ledger = []
        for evaluation in merged:
            definition = get_rule(evaluation['rule_id'])
            candidates = [name for name in available if name in evaluation.get('reported_by', [])]
            owner = definition.owner if definition.owner in available else (candidates[0] if candidates else None)
            penalty = finding_penalty(evaluation)
            evaluation.update(score_owner=owner, penalty=penalty)
            if owner is not None and penalty:
                penalties[owner] += penalty
                ledger.append({'rule_id': definition.rule_id, 'owner': definition.owner,
                               'score_owner': owner, 'penalty': penalty,
                               'reported_by': evaluation.get('reported_by', [])})
        for name in available:
            result[name]['score'] = max(0, 100 - penalties[name])
            result[name]['score_scope'] = 'unique_rules_assigned_to_category'
            result[name]['recommendations'] = recommendations_for(result[name].get('issues', []))
            data = result[name].get('data', {})
            if 'recommendations' in data:
                data['recommendations'] = list(result[name]['recommendations'])
            score = result[name]['score']
            if name == 'seo' and isinstance(data.get('scores'), dict):
                data['scores']['total'] = score
            elif name == 'content' and isinstance(data.get('quality_assessment'), dict):
                data['quality_assessment']['score'] = score
                data['quality_assessment']['quality_level'] = (
                    'excellent' if score >= 90 else 'good' if score >= 75 else
                    'average' if score >= 60 else 'poor' if score >= 40 else 'very_poor')
            elif name == 'performance':
                grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
                result[name]['grade'] = data['grade'] = grade
        result['rule_results'] = merged
        result['rule_coverage'] = rule_coverage(merged)
        result.setdefault('coverage', {})['rules'] = result['rule_coverage']
        result['scoring'] = {
            'version': SCORING_VERSION, 'ruleset_version': RULESET_VERSION,
            'policy': 'One 15/7/3 deduction per failed applicable critical/warning/notice rule; category scores floor at zero.',
            'ownership': 'Use the canonical owner when available; otherwise the first reporting analyzer in the fixed analyzer order.',
            'weights': dict(self.config.analysis.score_weights), 'deductions': ledger,
            'scope': 'Static checklist policy; unknown and inapplicable outcomes do not count as passed checks.',
        }

    def _aggregate_page_issues(self, results):
        if 'rule_results' in results:
            return sorted([dict(item) for item in results['rule_results']
                           if item['status'] in ('fail', 'informational')],
                          key=lambda item: {'critical': 0, 'warning': 1, 'notice': 2}[item['severity']])
        issues, seen = [], set()
        for name in ANALYZER_NAMES:
            for original in results.get(name, {}).get('issues', []):
                issue = copy.deepcopy(original)
                key = issue.get('rule_id') or (issue.get('category'), issue.get('message'))
                if key in seen:
                    continue
                seen.add(key)
                issue.setdefault('source', name)
                issue.setdefault('status', 'fail')
                issues.append(issue)
        return sorted(issues, key=lambda issue: {'critical': 0, 'warning': 1, 'notice': 2}.get(issue.get('severity'), 3))

    @staticmethod
    def _count_issues(issues):
        counts = Counter(issue.get('severity', 'notice') for issue in issues)
        return {**{name: counts[name] for name in ('critical', 'warning', 'notice')}, 'total': len(issues)}

    def _generate_page_recommendations(self, results):
        recommendations, seen = [], set()
        for issue in results.get('issues', []):
            rule_id = issue.get('rule_id')
            text = get_rule(rule_id).recommendation if 'rule_version' in issue else issue.get('fix')
            key = rule_id or text
            if not text or key in seen:
                continue
            seen.add(key)
            recommendations.append({'priority': issue.get('severity', 'notice'),
                                    'category': issue.get('category', 'General'),
                                    'recommendation': text, 'rule_id': issue.get('rule_id')})
        return recommendations

    def _record_analysis(self, result):
        validate_page_result(result, strict=True)
        if result.get('error'):
            self.stats.failed_analyses += 1
            self.progress.errors.append(result['error'])
        elif result.get('skipped'):
            self.stats.skipped_pages += 1
        else:
            self.stats.successful_analyses += 1
        counts = result.get('issue_counts', {})
        self.stats.total_issues += counts.get('total', 0)
        self.stats.critical_issues += counts.get('critical', 0)
        self.stats.warnings += counts.get('warning', 0)
        self.stats.notices += counts.get('notice', 0)
        self._page_times.append(result.get('analysis_time', 0))
        if result.get('content_hash'):
            self.duplicate_content[result['content_hash']].append(result['url'])
        self.progress.pages_analyzed += 1
        self.progress.current_url = result['url']
        self._update_progress()

    def _update_progress(self):
        if self._start_time:
            elapsed = max(time.time() - self._start_time, 0.000001)
            self.progress.speed_pages_per_sec = self.progress.pages_analyzed / elapsed
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.stats.memory_peak_mb = max(self.stats.memory_peak_mb, memory)
        if memory > self.config.max_memory_mb:
            raise MemoryError(f'Process memory exceeded configured {self.config.max_memory_mb} MB limit')

    async def analyze_url(self, url: str) -> PageResult:
        self._begin_run()
        try:
            async with Crawler(self.config.crawler.as_dict()) as crawler:
                self.crawler = crawler
                raw = await crawler.fetch_page(url)
                result = await self.analyze_page(raw or {'url': url, 'error': 'No fetch result'})
                self.results.append(result)
            await self._complete_run()
            return result
        finally:
            self._calculate_final_stats()

    async def analyze_urls(self, urls: List[str]) -> AsyncIterator[PageResult]:
        self._begin_run()
        try:
            async with Crawler(self.config.crawler.as_dict()) as crawler:
                self.crawler = crawler
                iterator = self._analyze_url_list(crawler, urls)
                try:
                    async for result in iterator:
                        yield result
                finally:
                    await iterator.aclose()
            await self._complete_run()
        finally:
            self._calculate_final_stats()

    async def _analyze_url_list(self, crawler, urls):
        urls = list(dict.fromkeys(self._url_identity(url) for url in urls))
        if len(urls) > self.config.crawler.max_pages:
            self._run_limits.append('max_pages')
        urls = urls[:self.config.crawler.max_pages]
        limit = self.config.crawler.effective_concurrency
        async def fetch_analyze(url):
            raw = await crawler.fetch_page(url)
            return await self.analyze_page(raw or {'url': url, 'error': 'No fetch result'})
        for start in range(0, len(urls), limit):
            tasks = [asyncio.create_task(fetch_analyze(url)) for url in urls[start:start + limit]]
            try:
                for task in asyncio.as_completed(tasks):
                    result = await task
                    self.results.append(result)
                    yield result
                    if result.get('error') and not self.config.continue_on_error:
                        raise RuntimeError(result['error'])
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def analyze_sitemap(self, sitemap_url: str) -> List[PageResult]:
        self._begin_run()
        try:
            async with Crawler(self.config.crawler.as_dict()) as discovery:
                urls = await discovery.parse_sitemap(sitemap_url, self.config.crawler.max_pages)
                self._run_limits.extend(discovery.limit_reasons)
                self._discovery_errors.extend(copy.deepcopy(discovery.discovery_errors))
                if not urls:
                    self.results.append(await self.analyze_page({
                        'url': sitemap_url, 'error': 'Sitemap contains no eligible URLs',
                    }))
                    self.crawler = discovery
                    await self._complete_run()
                    return self.results
            async with Crawler(self.config.crawler.as_dict()) as crawler:
                self.crawler = crawler
                async for _ in self._analyze_url_list(crawler, urls):
                    pass
            await self._complete_run()
            return self.results
        finally:
            self._calculate_final_stats()

    async def crawl_site(self, start_url: str) -> AsyncIterator[PageResult]:
        self._begin_run()
        self._site_start_url = start_url
        tasks = set()
        try:
            async with Crawler(self.config.crawler.as_dict()) as crawler:
                self.crawler = crawler
                crawler.set_result_buffer_limit(
                    self.config.crawler.effective_concurrency + self.config.analysis.max_analysis_threads)
                producer = asyncio.create_task(crawler.crawl_site(start_url, self.config.crawler.max_pages))
                processed = 0
                async def analyze(raw):
                    context = AnalysisContext(url=raw['url'], depth=raw.get('depth', 0),
                                              priority=self._get_page_priority(raw['url'], raw.get('depth', 0)),
                                              parent_url=raw.get('parent_url'))
                    try:
                        return await self._analyze_with_semaphore(raw, context)
                    finally:
                        raw.pop('soup', None)
                        raw.pop('html', None)
                        crawler.release_result(raw)
                try:
                    while not producer.done() or processed < len(crawler.results) or tasks:
                        if producer.done():
                            await producer
                        while processed < len(crawler.results) and len(tasks) < self.config.analysis.max_analysis_threads:
                            raw = crawler.results[processed]
                            processed += 1
                            self.progress.pages_crawled = processed
                            tasks.add(asyncio.create_task(analyze(raw)))
                        if tasks:
                            done, _ = await asyncio.wait(tasks, timeout=0.05, return_when=asyncio.FIRST_COMPLETED)
                            for task in done:
                                tasks.remove(task)
                                result = await task
                                self.results.append(result)
                                yield result
                                if result.get('error') and not self.config.continue_on_error:
                                    raise RuntimeError(result['error'])
                        else:
                            await asyncio.sleep(0.005)
                    await producer
                finally:
                    for task in [producer] + list(tasks):
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(producer, *tasks, return_exceptions=True)
                    for raw in crawler.results:
                        raw.pop('soup', None)
                        raw.pop('html', None)
                        crawler.release_result(raw)
            await self._complete_run()
        finally:
            self._calculate_final_stats()

    async def _analyze_with_semaphore(self, page_data, context):
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.analysis.max_analysis_threads)
        async with self._semaphore:
            return await self.analyze_page(page_data, context)

    async def _complete_run(self):
        self._run_limits = sorted(set(self._run_limits) | set(getattr(self.crawler, 'limit_reasons', [])))
        for error in getattr(self.crawler, 'discovery_errors', []):
            if error not in self._discovery_errors:
                self._discovery_errors.append(copy.deepcopy(error))
        self._crawl_complete = not (self._run_limits or self._discovery_errors)
        if self.config.analysis.check_broken_links and self.config.analysis.check_external_links:
            await self._check_external_links()
        self._resolve_site_links(self.results)

    async def _check_external_links(self):
        targets = []
        for page in self.results:
            links = page.get('links', {}).get('data', {}).get('external_links', [])
            targets.extend(link['url'] for link in links[:self.config.analysis.max_external_links_per_page]
                           if urlparse(link.get('url', '')).scheme in ('http', 'https'))
        targets = list(dict.fromkeys(self._url_identity(url) for url in targets))[:self.config.crawler.max_pages]
        if not targets:
            return
        settings = self.config.crawler.as_dict()
        settings.update(timeout=self.config.analysis.external_link_timeout, use_sitemap=False)
        async with Crawler(settings) as checker:
            for start in range(0, len(targets), self.config.crawler.effective_concurrency):
                tasks = [asyncio.create_task(checker.fetch_page(url)) for url in
                         targets[start:start + self.config.crawler.effective_concurrency]]
                try:
                    results = await asyncio.gather(*tasks)
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if result:
                        self.link_checks.append({key: result[key] for key in
                                                 ('url', 'requested_url', 'status_code', 'error') if key in result})

    @staticmethod
    def _url_identity(url):
        return (resolve_url(url, url) or url).split('#', 1)[0]

    def _observed_statuses(self, pages):
        observations = defaultdict(set)
        for page in pages:
            status = page.get('status_code') or 0
            observed_urls = [page.get('url'), page.get('requested_url')]
            observed_urls.extend(hop.get('url') for hop in page.get('redirect_chain', []))
            for url in observed_urls:
                if url:
                    observations[self._url_identity(url)].add(status)
        # Repeated, contradictory observations cannot establish one outcome.
        return {url: next(iter(statuses)) if len(statuses) == 1 else 0
                for url, statuses in observations.items()}

    def _resolve_site_links(self, pages, link_checks=None):
        if not self.config.analysis.check_broken_links:
            return
        observations = self._observed_statuses(list(pages) + (self.link_checks if link_checks is None else link_checks))
        for page in pages:
            analyzer = page.get('links')
            if not analyzer or analyzer.get('error'):
                continue
            data = analyzer.setdefault('data', {})
            links = []
            if self.config.analysis.check_internal_links:
                links.extend(data.get('internal_links', []))
            if self.config.analysis.check_external_links:
                links.extend(data.get('external_links', []))
            targets = list(dict.fromkeys(self._url_identity(link['url']) for link in links
                                       if urlparse(link.get('url', '')).scheme in ('http', 'https')))
            broken = [url for url in targets if observations.get(url, 0) >= 400]
            checked = [url for url in targets if observations.get(url, 0) >= 100]
            data['link_health'] = {'checked': len(checked), 'unchecked': len(targets) - len(checked),
                                   'broken': len(broken), 'source': 'observed_http_status',
                                   'status': 'complete' if len(checked) == len(targets) else 'partial'}
            data['broken_links'] = broken
            data['link_health_status'] = data['link_health']['status']
            if ('rule_results' not in analyzer or
                    page.get('scoring', {}).get('version') != SCORING_VERSION or
                    page.get('scoring', {}).get('ruleset_version') != RULESET_VERSION):
                data['link_health']['scoring_status'] = 'Legacy scores and findings retained; link observations updated separately.'
                continue
            analyzer['issues'] = [issue for issue in analyzer.get('issues', [])
                                  if issue.get('rule_id') != 'links.broken']
            outcome = 'fail' if broken else 'unknown' if len(checked) < len(targets) else 'pass'
            link_result = rule_result('links.broken',
                                      {'http_statuses': {url: observations[url] for url in checked},
                                       'unchecked': [url for url in targets if url not in checked]},
                                      message=f'{len(broken)} broken link targets found', category='Links',
                                      status=outcome, source='observed_http_status',
                                      applicable=bool(targets),
                                      reason=('No eligible link targets are selected for checking.' if not targets else
                                              'Some link targets have no HTTP observation.' if outcome == 'unknown' else ''),
                                      details={'broken_links': broken})
            link_result['reported_by'] = ['links']
            analyzer['rule_results'] = [item for item in analyzer.get('rule_results', [])
                                        if item.get('rule_id') != 'links.broken'] + [link_result]
            analyzer['rule_coverage'] = rule_coverage(analyzer['rule_results'])
            if broken:
                analyzer['issues'].append(link_result)
            self._apply_rule_scoring(page)
            page['overall_score'] = self._calculate_weighted_score(page)
            page['issues'] = self._aggregate_page_issues(page)
            page['issue_counts'] = self._count_issues(page['issues'])
            page['recommendations'] = self._generate_page_recommendations(page)

    def _calculate_final_stats(self):
        self.stats.analysis_end = time.time()
        self.stats.total_pages = len(self.results)
        if self._page_times:
            self.stats.avg_analysis_time = sum(self._page_times) / len(self._page_times)
        scores = [page['overall_score'] for page in self.results if self._is_score(page.get('overall_score'))]
        self.stats.avg_page_score = sum(scores) / len(scores) if scores else 0
        counts = self._count_issues([issue for page in self.results for issue in page.get('issues', [])])
        self.stats.total_issues, self.stats.critical_issues = counts['total'], counts['critical']
        self.stats.warnings, self.stats.notices = counts['warning'], counts['notice']

    def generate_batch_report(self, page_results=None):
        return self.generate_site_report(page_results)

    def generate_site_report(self, page_results=None) -> SiteReport:
        supplied = self.results if page_results is None else page_results
        if not isinstance(supplied, list):
            raise ContractError('$.pages', 'must be a list of page results')
        for index, page in enumerate(supplied):
            validate_page_result(page, path=f'$.pages[{index}]')
            if not isinstance(page.get('url'), str) or not page['url'].strip():
                raise ContractError(f'$.pages[{index}].url', 'must identify the page being aggregated')
            if 'issues' in page and not isinstance(page['issues'], list):
                raise ContractError(f'$.pages[{index}].issues', 'aggregation requires issue records, not summary counts')
        # Only the current run's actual result objects carry its crawl context.
        # Imported or independently analyzed pages must not inherit old checks,
        # entry URLs, limits, or timing from this analyzer instance.
        current_run = (page_results is None or supplied is self.results or
                       bool(self.results) and Counter(map(id, supplied)) == Counter(map(id, self.results)))
        link_checks = self.link_checks if current_run else []
        crawl_complete = self._crawl_complete if current_run else False
        run_limits = copy.deepcopy(self._run_limits) if current_run else []
        discovery_errors = copy.deepcopy(self._discovery_errors) if current_run else []
        pages = copy.deepcopy(supplied)
        if not pages:
            return {'schema_version': SCHEMA_VERSION, 'status': 'error', 'error': 'No pages to analyze'}
        self._resolve_site_links(pages, link_checks)
        site_analysis = analyze_site(pages, start_url=self._site_start_url if current_run else None,
                                     crawl_complete=crawl_complete)
        site_pages = {row['url']: row for row in site_analysis['pages']}
        for page in pages:
            if url_identity(page['url']) in site_pages:
                page['site_analysis'] = copy.deepcopy(site_pages[url_identity(page['url'])])
        usable = [page for page in pages if not page.get('error') and not page.get('skipped')]
        failed = [page for page in pages if page.get('error')]
        skipped = [page for page in pages if page.get('skipped')]
        partial_pages = [page for page in usable if page.get('status') == 'partial']
        categories = {}
        for name in ANALYZER_NAMES:
            scores = [page[name]['score'] for page in usable if name in page
                      and not page[name].get('error') and self._is_score(page[name].get('score'))]
            categories[name] = round(sum(scores) / len(scores), 2) if scores else None
        scores = [page['overall_score'] for page in usable if self._is_score(page.get('overall_score'))]
        overall = round(sum(scores) / len(scores), 2) if scores else None
        # Pages are independent snapshots above. Share their owned evidence
        # through the report instead of copying it again for each derived view.
        issues = [{**issue, 'url': page['url']} for page in usable for issue in page.get('issues', [])]
        issues.extend(site_analysis['findings'])
        aggregated, stats = aggregate_issues(issues, copy_evidence=False)
        counts = self._count_issues(issues)
        duplicates = defaultdict(set)
        redirect_targets = defaultdict(set)
        for page in pages:
            if self.config.analysis.check_content_uniqueness and page.get('content_hash'):
                duplicates[page['content_hash']].add(page['url'])
            if page.get('requested_url') and page['requested_url'] != page['url']:
                redirect_targets[page['requested_url']].add(page['url'])
        redirects = {url: next(iter(targets)) for url, targets in sorted(redirect_targets.items())
                     if len(targets) == 1}
        rule_counts = Counter()
        for page in usable:
            rule_counts.update(page.get('rule_coverage', {}).get('counts', {}))
        assessed_rules = sum(rule_counts[status] for status in ('pass', 'fail', 'informational'))
        attempted_rules = assessed_rules + rule_counts['unknown'] + rule_counts['error']
        current_scoring = bool(usable) and all(
            page.get('scoring', {}).get('version') == SCORING_VERSION and
            page.get('scoring', {}).get('ruleset_version') == RULESET_VERSION for page in usable)
        duplicate_groups = [{'hash': key, 'urls': sorted(urls), 'count': len(urls)}
                            for key, urls in duplicates.items() if len(urls) > 1]
        observations = self._observed_statuses(pages + link_checks)
        broken = sorted({page['url'] for page in pages + link_checks
                         if observations.get(self._url_identity(page['url']), 0) >= 400})
        report = {
            'schema_version': SCHEMA_VERSION,
            'site_analysis': site_analysis,
            'status': 'error' if not usable else 'partial' if (
                failed or partial_pages or run_limits or discovery_errors) else 'complete',
            'summary': {'total_pages': len(pages), 'successful_pages': len(usable) - len(partial_pages),
                        'partial_pages': len(partial_pages), 'failed_pages': len(failed), 'skipped_pages': len(skipped),
                        'analysis_mode': self.mode.value, 'analysis_timestamp': time.time(),
                        'analysis_duration': max(0, self.stats.analysis_end - self.stats.analysis_start)
                        if current_run and self.stats.analysis_end else 0,
                        'crawl_complete': crawl_complete,
                        'limits_reached': run_limits,
                        'discovery_errors': discovery_errors,
                        'scope_note': 'Results describe fetched pages; unvisited targets remain unchecked.'},
            'scores': {'overall': overall, 'categories': categories, 'source': 'static_rule_heuristics',
                       'scoring_versions': sorted({page['scoring']['version'] for page in usable if page.get('scoring')})},
            'rule_coverage': {'counts': dict(rule_counts), 'assessed': assessed_rules,
                              'total': sum(rule_counts.values()),
                              'ratio': assessed_rules / attempted_rules if attempted_rules else None,
                              'scope': 'Counts are unique rule evaluations per page, not a complete site inventory.'},
            'scoring': {'version': SCORING_VERSION if current_scoring else 'legacy_or_mixed',
                        'ruleset_version': RULESET_VERSION if current_scoring else None,
                        'policy': ('Average page scores; each page deducts each failed applicable rule once in its assigned category.'
                                   if current_scoring else 'Average recorded page scores; legacy or mixed inputs retain their original scoring semantics.'),
                        'weights': dict(self.config.analysis.score_weights)},
            'issues': {'aggregated': aggregated, 'stats': stats, 'counts': {**counts, 'unique': len(aggregated)},
                       'top_issues': aggregated[:10]},
            'technical_health': {'broken_links': broken, 'broken_links_count': len(broken),
                                 'redirects': redirects, 'redirects_count': len(redirects),
                                 'duplicate_content': duplicate_groups, 'duplicate_content_count': len(duplicate_groups),
                                 'link_checks': copy.deepcopy(link_checks)},
            'performance_metrics': generate_performance_metrics(pages),
            'crawl_stats': {'pages_per_second': self.progress.speed_pages_per_sec if current_run else 0,
                            'result_buffer_capacity': getattr(self.crawler, 'result_buffer_capacity', None) if current_run else None,
                            'result_buffer_peak': getattr(self.crawler, 'result_buffer_peak', 0) if current_run else 0,
                            'avg_analysis_time': self.stats.avg_analysis_time if current_run else 0,
                            'memory_peak_mb': self.stats.memory_peak_mb if current_run else 0,
                            'cache_hits': sum(bool(page.get('cached')) for page in pages),
                            'depth_distribution': dict(Counter(page.get('context', {}).get('depth', 0) for page in pages))},
            'pages': {'summary': [{'url': page['url'], 'score': page.get('overall_score'),
                                   'status': page.get('status', 'complete'), 'status_code': page.get('status_code'),
                                   'load_time': page.get('load_time'), 'issues': page.get('issue_counts', {}),
                                   'priority': page.get('context', {}).get('priority'),
                                   'depth': page.get('context', {}).get('depth')} for page in usable],
                      'detailed': usable, 'failed': failed, 'skipped': skipped},
            'metadata': {'analyzer_version': self.config.version, 'schema_version': SCHEMA_VERSION,
                         'config': {'max_pages': self.config.crawler.max_pages, 'analysis_mode': self.mode.value,
                                    'concurrent_requests': self.config.crawler.effective_concurrency,
                                    'enabled_analyzers': self._enabled_analyzers()}},
        }
        recommendations = generate_specific_recommendations(report)
        report['recommendations'] = {'specific': recommendations}
        report['recommendations']['executive'] = create_executive_summary(report)
        validate_site_report(report, strict=True)
        return report

    def get_real_time_stats(self):
        return {'progress': {'pages_crawled': self.progress.pages_crawled,
                             'pages_analyzed': self.progress.pages_analyzed, 'current_url': self.progress.current_url,
                             'speed': self.progress.speed_pages_per_sec},
                'stats': {'successful': self.stats.successful_analyses, 'failed': self.stats.failed_analyses,
                          'skipped': self.stats.skipped_pages, 'issues_found': self.stats.total_issues,
                          'avg_score': self.stats.avg_page_score, 'avg_time': self.stats.avg_analysis_time},
                'resources': {'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
                              'cache_size': len(self.cache.cache)},
                'health': {'broken_links': len(self.broken_links), 'redirects': len(self.redirects),
                           'errors': self.progress.errors[-10:]}}

    def get_crawl_statistics(self):
        stats = self.get_real_time_stats()
        return {**stats, 'pages_per_second': self.progress.speed_pages_per_sec,
                'memory_usage': stats['resources']['memory_mb']}

    def cleanup(self):
        self.cache.clear()
        self._reset_state()
