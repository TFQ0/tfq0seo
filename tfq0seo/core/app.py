"""Advanced SEO application orchestrator with parallel processing and intelligent analysis coordination."""

import asyncio
import time
import hashlib
import json
import psutil
from typing import Dict, List, Any, Optional, AsyncIterator, Set, Tuple
from urllib.parse import urlparse
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging

from .config import Config
from .crawler import Crawler
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
    """Simple in-memory cache for analysis results."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[Dict, float]] = {}
        self.ttl = ttl_seconds
    
    def get(self, url: str) -> Optional[Dict]:
        """Get cached result if not expired."""
        if url in self.cache:
            result, timestamp = self.cache[url]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self.cache[url]
        return None
    
    def set(self, url: str, result: Dict) -> None:
        """Cache a result."""
        self.cache[url] = (result, time.time())
    
    def clear_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired = [url for url, (_, timestamp) in self.cache.items() 
                  if current_time - timestamp >= self.ttl]
        for url in expired:
            del self.cache[url]


class SEOAnalyzer:
    """Advanced SEO analyzer with parallel processing and intelligent coordination."""
    
    def __init__(self, config: Optional[Config] = None, mode: AnalysisMode = AnalysisMode.STANDARD):
        """Initialize the SEO analyzer with configuration and mode."""
        self.config = config or Config()
        self.mode = mode
        self.crawler = None
        self.results = []
        self.broken_links: Set[str] = set()
        self.redirects: Dict[str, str] = {}
        self.duplicate_content: Dict[str, List[str]] = defaultdict(list)
        self.analysis_contexts: Dict[str, AnalysisContext] = {}
        self.stats = AnalysisStats()
        self.progress = CrawlProgress()
        self.cache = AnalysisCache(ttl_seconds=self.config.crawler.cache_ttl if hasattr(self.config.crawler, 'cache_ttl') else 3600)
        self._semaphore = None
        self._start_time = None
        self._page_times: List[float] = []
        
        # Ensure backward compatibility with crawler config
        if not hasattr(self.config.crawler, 'concurrent_requests'):
            self.config.crawler.concurrent_requests = getattr(self.config.crawler, 'max_concurrent', 10)
        
    def _get_page_priority(self, url: str, depth: int = 0) -> PagePriority:
        """Determine page priority based on URL and depth."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Homepage is always critical
        if path in ['/', '', '/index.html', '/index.php']:
            return PagePriority.CRITICAL
        
        # Key pages are high priority
        key_paths = ['/about', '/contact', '/products', '/services', '/pricing', '/features']
        if any(path.startswith(p) for p in key_paths):
            return PagePriority.HIGH
        
        # Depth-based priority
        if depth <= 1:
            return PagePriority.HIGH
        elif depth <= 2:
            return PagePriority.MEDIUM
        else:
            return PagePriority.LOW
    
    def _should_skip_analysis(self, url: str) -> bool:
        """Check if URL should be skipped from analysis."""
        # Skip certain file types
        skip_extensions = {'.pdf', '.doc', '.xls', '.zip', '.mp4', '.mp3', '.jpg', '.png', '.gif'}
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        
        return any(path_lower.endswith(ext) for ext in skip_extensions)
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content for duplicate detection."""
        # Normalize content for comparison
        normalized = ' '.join(content.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    async def analyze_page(self, page_data: Dict[str, Any], context: Optional[AnalysisContext] = None) -> Dict[str, Any]:
        """Analyze a single page with enhanced error handling and caching."""
        url = page_data['url']
        
        # Check cache first
        if self.mode != AnalysisMode.DEEP:
            cached = self.cache.get(url)
            if cached:
                logger.debug(f"Using cached analysis for {url}")
                self.stats.successful_analyses += 1
                return cached
        
        # Create context if not provided
        if not context:
            context = AnalysisContext(url=url)
        
        # Handle errors
        if 'error' in page_data:
            self.stats.failed_analyses += 1
            return {
                'url': url,
                'error': page_data.get('error'),
                'status_code': page_data.get('status_code', 0),
                'context': {
                    'depth': context.depth,
                    'priority': context.priority.value
                }
            }
        
        soup = page_data.get('soup')
        if not soup:
            self.stats.failed_analyses += 1
            return {
                'url': url,
                'error': 'No content to analyze',
                'status_code': page_data.get('status_code', 0)
            }
        
        # Skip non-HTML content
        if self._should_skip_analysis(url):
            self.stats.skipped_pages += 1
            return {
                'url': url,
                'skipped': True,
                'reason': 'Non-HTML content'
            }
        
        # Track broken links and redirects
        status_code = page_data.get('status_code', 200)
        if status_code >= 400:
            self.broken_links.add(url)
        elif 300 <= status_code < 400:
            redirect_url = page_data.get('redirect_url')
            if redirect_url:
                self.redirects[url] = redirect_url
        
        # Check for duplicate content
        content_text = soup.get_text(strip=True)
        content_hash = self._calculate_content_hash(content_text[:5000])  # First 5000 chars
        self.duplicate_content[content_hash].append(url)
        
        # Initialize results
        results = {
            'url': url,
            'status_code': status_code,
            'load_time': page_data.get('load_time', 0),
            'content_length': page_data.get('content_length', 0),
            'timestamp': page_data.get('timestamp', time.time()),
            'context': {
                'depth': context.depth,
                'priority': context.priority.value,
                'parent_url': context.parent_url
            },
            'content_hash': content_hash
        }
        
        try:
            start_time = time.time()
            
            # Run analyzers based on mode
            if self.mode == AnalysisMode.QUICK:
                # Quick mode: Only essential analyzers
                tasks = [
                    self._run_analyzer_safe('seo', analyze_seo, soup, url),
                    self._run_analyzer_safe('technical', analyze_technical, soup, url, 
                                           headers=page_data.get('headers'), 
                                           status_code=status_code)
                ]
            elif self.mode == AnalysisMode.DEEP:
                # Deep mode: All analyzers with extra parameters
                tasks = [
                    self._run_analyzer_safe('seo', analyze_seo, soup, url),
                    self._run_analyzer_safe('content', analyze_content, soup, url, 
                                           target_keywords=self.config.analysis.target_keywords),
                    self._run_analyzer_safe('technical', analyze_technical, soup, url,
                                           headers=page_data.get('headers'), 
                                           status_code=status_code),
                    self._run_analyzer_safe('performance', analyze_performance, soup, url,
                                           load_time=page_data.get('load_time', 0), 
                                           content_length=page_data.get('content_length', 0)),
                    self._run_analyzer_safe('links', analyze_links, soup, url, 
                                           broken_links=self.broken_links)
                ]
            else:  # STANDARD mode
                # Standard mode: All analyzers with normal parameters
                tasks = [
                    self._run_analyzer_safe('seo', analyze_seo, soup, url),
                    self._run_analyzer_safe('content', analyze_content, soup, url,
                                           target_keywords=self.config.analysis.target_keywords),
                    self._run_analyzer_safe('technical', analyze_technical, soup, url,
                                           headers=page_data.get('headers'), 
                                           status_code=status_code),
                    self._run_analyzer_safe('performance', analyze_performance, soup, url,
                                           load_time=page_data.get('load_time', 0),
                                           content_length=page_data.get('content_length', 0)),
                    self._run_analyzer_safe('links', analyze_links, soup, url,
                                           broken_links=self.broken_links if self.config.analysis.check_external_links else None)
                ]
            
            # Run analyzers in parallel
            analyzer_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for analyzer_name, result in analyzer_results:
                if isinstance(result, Exception):
                    logger.error(f"Analyzer {analyzer_name} failed for {url}: {result}")
                    results[analyzer_name] = {'score': 0, 'error': str(result)}
                else:
                    results[analyzer_name] = result
            
            # Calculate weighted overall score
            results['overall_score'] = self._calculate_weighted_score(results)
            
            # Aggregate all issues with deduplication
            results['issues'] = self._aggregate_page_issues(results)
            
            # Issue counts
            results['issue_counts'] = self._count_issues(results['issues'])
            self.stats.total_issues += results['issue_counts']['total']
            self.stats.critical_issues += results['issue_counts']['critical']
            self.stats.warnings += results['issue_counts']['warning']
            self.stats.notices += results['issue_counts']['notice']
            
            # Generate intelligent recommendations
            results['recommendations'] = self._generate_page_recommendations(results)
            
            # Track analysis time
            analysis_time = time.time() - start_time
            results['analysis_time'] = analysis_time
            self._page_times.append(analysis_time)
            
            # Cache successful result
            self.cache.set(url, results)
            
            # Update stats
            self.stats.successful_analyses += 1
            
        except Exception as e:
            logger.error(f"Analysis error for {url}: {e}")
            results['error'] = f"Analysis error: {str(e)}"
            results['overall_score'] = 0
            results['issues'] = []
            self.stats.failed_analyses += 1
        
        return results
    
    async def _run_analyzer(self, name: str, analyzer_func: callable, *args) -> Tuple[str, Dict]:
        """Run an analyzer with error handling (deprecated, use _run_analyzer_safe)."""
        try:
            # Filter out None arguments for compatibility
            filtered_args = [arg for arg in args if arg is not None]
            result = analyzer_func(*filtered_args)
            return (name, result)
        except Exception as e:
            logger.error(f"Analyzer {name} failed: {e}", exc_info=True)
            return (name, {'score': 0, 'error': str(e), 'issues': []})
    
    async def _run_analyzer_safe(self, name: str, analyzer_func: callable, *args, **kwargs) -> Tuple[str, Dict]:
        """Run an analyzer with safe parameter handling."""
        try:
            # Call analyzer with positional and keyword arguments
            result = analyzer_func(*args, **kwargs)
            return (name, result)
        except TypeError as e:
            # Try calling with only positional arguments for backward compatibility
            try:
                result = analyzer_func(*args)
                return (name, result)
            except Exception as e2:
                logger.error(f"Analyzer {name} failed with both calling methods: {e}, {e2}")
                return (name, {'score': 0, 'error': str(e), 'issues': []})
        except Exception as e:
            logger.error(f"Analyzer {name} failed: {e}")
            return (name, {'score': 0, 'error': str(e), 'issues': []})
    
    def _calculate_weighted_score(self, results: Dict[str, Any]) -> float:
        """Calculate weighted overall score with dynamic weighting."""
        # Dynamic weights based on analysis mode
        if self.mode == AnalysisMode.QUICK:
            weights = {
                'seo': 0.60,
                'technical': 0.40
            }
        elif self.mode == AnalysisMode.DEEP:
            weights = {
                'seo': 0.25,
                'content': 0.25,
                'technical': 0.20,
                'performance': 0.20,
                'links': 0.10
            }
        else:  # STANDARD
            weights = {
                'seo': 0.30,
                'content': 0.25,
                'technical': 0.20,
                'performance': 0.15,
                'links': 0.10
            }
        
        total_score = 0
        total_weight = 0
        
        for analyzer, weight in weights.items():
            if analyzer in results and 'score' in results[analyzer]:
                score = results[analyzer]['score']
                # Apply penalty for critical issues
                if analyzer in results and 'issues' in results[analyzer]:
                    critical_count = sum(1 for i in results[analyzer]['issues'] 
                                       if i.get('severity') == 'critical')
                    score *= (1 - critical_count * 0.1)  # 10% penalty per critical issue
                
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def _aggregate_page_issues(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Aggregate and deduplicate issues from all analyzers."""
        all_issues = []
        seen_issues = set()
        
        for analyzer in ['seo', 'content', 'technical', 'performance', 'links']:
            if analyzer in results and 'issues' in results[analyzer]:
                for issue in results[analyzer]['issues']:
                    # Create unique key for deduplication
                    issue_key = f"{issue.get('category', '')}:{issue.get('message', '')}"
                    
                    if issue_key not in seen_issues:
                        seen_issues.add(issue_key)
                        # Add analyzer source
                        issue['source'] = analyzer
                        all_issues.append(issue)
        
        # Sort by severity (critical > warning > notice)
        severity_order = {'critical': 0, 'warning': 1, 'notice': 2}
        all_issues.sort(key=lambda x: severity_order.get(x.get('severity', 'notice'), 3))
        
        return all_issues
    
    def _count_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {
            'critical': 0,
            'warning': 0,
            'notice': 0,
            'total': len(issues)
        }
        
        for issue in issues:
            severity = issue.get('severity', 'notice')
            if severity in counts:
                counts[severity] += 1
        
        return counts
    
    def _generate_page_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate intelligent, prioritized recommendations."""
        recommendations = []
        issues = results.get('issues', [])
        
        # Group issues by category
        issues_by_category = defaultdict(list)
        for issue in issues:
            category = issue.get('category', 'General')
            issues_by_category[category].append(issue)
        
        # Priority 1: Critical SEO issues
        critical_seo = [i for i in issues if i.get('severity') == 'critical' and 
                        i.get('source') == 'seo']
        
        if critical_seo:
            for issue in critical_seo[:2]:  # Top 2 critical SEO issues
                rec = {
                    'priority': 'critical',
                    'category': 'SEO',
                    'recommendation': issue.get('fix', 'Fix critical SEO issue'),
                    'impact': issue.get('impact', 'High impact on search visibility'),
                    'effort': 'low'  # Most critical issues are quick fixes
                }
                recommendations.append(rec)
        
        # Priority 2: Performance issues affecting Core Web Vitals
        if 'performance' in results:
            perf_data = results['performance'].get('data', {})
            
            if perf_data.get('lcp', 0) > 2.5:
                recommendations.append({
                    'priority': 'high',
                    'category': 'Performance',
                    'recommendation': 'Optimize Largest Contentful Paint (LCP)',
                    'impact': 'Improves Core Web Vitals and search rankings',
                    'effort': 'medium'
                })
            
            if perf_data.get('cls', 0) > 0.1:
                recommendations.append({
                    'priority': 'high',
                    'category': 'Performance',
                    'recommendation': 'Fix Cumulative Layout Shift (CLS)',
                    'impact': 'Better user experience and Core Web Vitals',
                    'effort': 'low'
                })
        
        # Priority 3: Content optimization
        if 'content' in results:
            content_data = results['content'].get('data', {})
            
            if content_data.get('word_count', 0) < 300:
                recommendations.append({
                    'priority': 'high',
                    'category': 'Content',
                    'recommendation': f"Expand content from {content_data.get('word_count', 0)} to at least 300 words",
                    'impact': 'Improves content relevance and ranking potential',
                    'effort': 'medium'
                })
            
            if content_data.get('keyword_density', {}).get('primary', 0) < 0.5:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'Content',
                    'recommendation': 'Increase primary keyword usage naturally',
                    'impact': 'Better keyword relevance',
                    'effort': 'low'
                })
        
        # Priority 4: Technical improvements
        if 'technical' in results:
            tech_data = results['technical'].get('data', {})
            
            if not tech_data.get('https'):
                recommendations.append({
                    'priority': 'critical',
                    'category': 'Security',
                    'recommendation': 'Enable HTTPS with SSL certificate',
                    'impact': 'Required for security and SEO',
                    'effort': 'medium'
                })
            
            if tech_data.get('mobile', {}).get('readiness') == 'desktop_only':
                recommendations.append({
                    'priority': 'critical',
                    'category': 'Mobile',
                    'recommendation': 'Implement responsive design',
                    'impact': 'Required for mobile-first indexing',
                    'effort': 'high'
                })
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        return recommendations[:10]  # Return top 10 recommendations
    
    def _update_progress(self) -> None:
        """Update crawl progress statistics."""
        if self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed > 0 and self.progress.pages_analyzed > 0:
                self.progress.speed_pages_per_sec = self.progress.pages_analyzed / elapsed
                
                if self.progress.pages_remaining > 0 and self.progress.speed_pages_per_sec > 0:
                    self.progress.eta_seconds = self.progress.pages_remaining / self.progress.speed_pages_per_sec
    
    async def analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze a single URL with full context."""
        self._start_time = time.time()
        self.stats.analysis_start = self._start_time
        
        async with Crawler(self.config.crawler.__dict__) as crawler:
            self.crawler = crawler
            
            # Fetch page
            page_data = await crawler.fetch_page(url)
            
            if not page_data:
                self.stats.failed_analyses += 1
                return {'url': url, 'error': 'Failed to fetch page'}
            
            # Create context
            context = AnalysisContext(
                url=url,
                priority=self._get_page_priority(url)
            )
            self.analysis_contexts[url] = context
            
            # Analyze
            result = await self.analyze_page(page_data, context)
            
            # Update stats
            self.stats.analysis_end = time.time()
            self.stats.total_pages = 1
            
            return result
    
    async def crawl_site(self, start_url: str) -> AsyncIterator[Dict[str, Any]]:
        """Crawl and analyze a website with intelligent prioritization."""
        self._start_time = time.time()
        self.stats.analysis_start = self._start_time
        
        # Use semaphore for parallel analysis control
        self._semaphore = asyncio.Semaphore(self.config.crawler.concurrent_requests // 2)
        
        async with Crawler(self.config.crawler.__dict__) as crawler:
            self.crawler = crawler
            
            # Start crawling
            crawl_task = asyncio.create_task(
                crawler.crawl_site(start_url, self.config.crawler.max_pages)
            )
            
            # Track processed pages
            processed = 0
            analysis_tasks = []
            completed_urls = set()
            
            while not crawl_task.done() or processed < len(crawler.results) or analysis_tasks:
                # Process new crawled pages
                while processed < len(crawler.results):
                    page_data = crawler.results[processed]
                    processed += 1
                    
                    url = page_data['url']
                    if url in completed_urls:
                        continue
                    
                    # Create context
                    context = AnalysisContext(
                        url=url,
                        depth=page_data.get('depth', 0),
                        priority=self._get_page_priority(url, page_data.get('depth', 0))
                    )
                    self.analysis_contexts[url] = context
                    
                    # Update progress
                    self.progress.pages_crawled = processed
                    self.progress.pages_queued = len(crawler.results)
                    self.progress.current_url = url
                    self.progress.current_depth = context.depth
                    self._update_progress()
                    
                    # Start analysis task with semaphore
                    task = asyncio.create_task(
                        self._analyze_with_semaphore(page_data, context)
                    )
                    analysis_tasks.append(task)
                
                # Check for completed analysis tasks
                if analysis_tasks:
                    done, pending = await asyncio.wait(
                        analysis_tasks, 
                        timeout=0.1,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in done:
                        try:
                            result = await task
                            if result:
                                completed_urls.add(result['url'])
                                self.results.append(result)
                                self.progress.pages_analyzed += 1
                                self._update_progress()
                                yield result
                        except Exception as e:
                            logger.error(f"Analysis task failed: {e}")
                        
                        analysis_tasks.remove(task)
                    
                    # Brief sleep to prevent busy waiting
                    if not done:
                        await asyncio.sleep(0.01)
                else:
                    # Sleep when no tasks are pending
                    await asyncio.sleep(0.01)
            
            # Wait for remaining analysis tasks
            if analysis_tasks:
                remaining_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                for result in remaining_results:
                    if isinstance(result, Exception):
                        logger.error(f"Final analysis task failed: {result}")
                    elif result:
                        self.results.append(result)
                        self.progress.pages_analyzed += 1
                        yield result
            
            # Ensure crawl completes
            await crawl_task
            
            # Final stats update
            self.stats.analysis_end = time.time()
            self.stats.total_pages = len(self.results)
            self._calculate_final_stats()
    
    async def _analyze_with_semaphore(self, page_data: Dict[str, Any], context: AnalysisContext) -> Optional[Dict[str, Any]]:
        """Analyze a page with semaphore control."""
        async with self._semaphore:
            try:
                return await self.analyze_page(page_data, context)
            except Exception as e:
                logger.error(f"Analysis failed for {page_data.get('url')}: {e}")
                return None
    
    def _calculate_final_stats(self) -> None:
        """Calculate final statistics."""
        if self._page_times:
            self.stats.avg_analysis_time = sum(self._page_times) / len(self._page_times)
        
        if self.results:
            scores = [r.get('overall_score', 0) for r in self.results if 'error' not in r]
            if scores:
                self.stats.avg_page_score = sum(scores) / len(scores)
        
        # Memory peak
        process = psutil.Process()
        self.stats.memory_peak_mb = process.memory_info().rss / 1024 / 1024
    
    def generate_site_report(self, page_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate comprehensive site report with advanced analytics."""
        if page_results is None:
            page_results = self.results
        
        if not page_results:
            return {'error': 'No pages to analyze'}
        
        # Separate successful and failed pages
        successful_pages = [p for p in page_results if 'error' not in p and not p.get('skipped')]
        failed_pages = [p for p in page_results if 'error' in p]
        skipped_pages = [p for p in page_results if p.get('skipped')]
        
        # Calculate aggregate scores by category
        category_scores = defaultdict(list)
        for page in successful_pages:
            for category in ['seo', 'content', 'technical', 'performance', 'links']:
                if category in page and 'score' in page[category]:
                    category_scores[category].append(page[category]['score'])
        
        # Aggregate all issues
        all_issues = []
        for page in successful_pages:
            page_issues = page.get('issues', [])
            for issue in page_issues:
                issue['url'] = page['url']
            all_issues.extend(page_issues)
        
        # Aggregate and deduplicate issues
        aggregated_issues, aggregation_stats = aggregate_issues(all_issues)
        
        # Find duplicate content
        duplicate_groups = []
        for content_hash, urls in self.duplicate_content.items():
            if len(urls) > 1:
                duplicate_groups.append({
                    'hash': content_hash,
                    'urls': urls,
                    'count': len(urls)
                })
        
        # Compile comprehensive report
        report = {
            'summary': {
                'total_pages': len(page_results),
                'successful_pages': len(successful_pages),
                'failed_pages': len(failed_pages),
                'skipped_pages': len(skipped_pages),
                'analysis_mode': self.mode.value,
                'analysis_timestamp': time.time(),
                'analysis_duration': self.stats.analysis_end - self.stats.analysis_start if self.stats.analysis_end else 0
            },
            
            'scores': {
                'overall': sum(p.get('overall_score', 0) for p in successful_pages) / len(successful_pages) if successful_pages else 0,
                'categories': {
                    category: sum(scores) / len(scores) if scores else 0
                    for category, scores in category_scores.items()
                }
            },
            
            'issues': {
                'aggregated': aggregated_issues,
                'stats': aggregation_stats,
                'counts': {
                    'critical': self.stats.critical_issues,
                    'warning': self.stats.warnings,
                    'notice': self.stats.notices,
                    'total': self.stats.total_issues,
                    'unique': len(aggregated_issues)
                },
                'top_issues': aggregated_issues[:10] if aggregated_issues else []
            },
            
            'technical_health': {
                'broken_links': list(self.broken_links)[:50],  # Limit to 50
                'broken_links_count': len(self.broken_links),
                'redirects': dict(list(self.redirects.items())[:50]),  # Limit to 50
                'redirects_count': len(self.redirects),
                'duplicate_content': duplicate_groups[:20],  # Top 20 duplicate groups
                'duplicate_content_count': len(duplicate_groups)
            },
            
            'performance_metrics': generate_performance_metrics(successful_pages),
            
            'crawl_stats': {
                'pages_per_second': self.progress.speed_pages_per_sec,
                'avg_analysis_time': self.stats.avg_analysis_time,
                'memory_peak_mb': self.stats.memory_peak_mb,
                'cache_hits': len([1 for p in successful_pages if p.get('cached')]),
                'depth_distribution': Counter(p.get('context', {}).get('depth', 0) for p in successful_pages)
            },
            
            'recommendations': {
                'specific': generate_specific_recommendations({
                    'overall_score': report['scores']['overall'] if 'scores' in locals() else 0,
                    'category_scores': category_scores,
                    'aggregated_issues': aggregated_issues,
                    'issue_counts': self.stats.__dict__
                }),
                'executive': create_executive_summary({
                    'overall_score': report['scores']['overall'] if 'scores' in locals() else 0,
                    'issue_counts': {
                        'critical': self.stats.critical_issues,
                        'warning': self.stats.warnings,
                        'notice': self.stats.notices
                    },
                    'summary': {
                        'total_pages': len(page_results),
                        'successful_pages': len(successful_pages)
                    }
                })
            },
            
            'pages': {
                'summary': [
                    {
                        'url': p.get('url'),
                        'score': p.get('overall_score', 0),
                        'status_code': p.get('status_code'),
                        'load_time': p.get('load_time', 0),
                        'issues': p.get('issue_counts', {}),
                        'priority': p.get('context', {}).get('priority'),
                        'depth': p.get('context', {}).get('depth')
                    } for p in successful_pages[:100]  # Limit to 100
                ],
                'detailed': successful_pages[:50] if len(successful_pages) <= 50 else [
                    p for p in successful_pages if p.get('overall_score', 100) < 70
                ][:50],  # Pages with issues
                'failed': [
                    {'url': p.get('url'), 'error': p.get('error'), 'status_code': p.get('status_code', 0)}
                    for p in failed_pages[:20]
                ]
            },
            
            'metadata': {
                'analyzer_version': '2.0.0',
                'config': {
                    'max_pages': self.config.crawler.max_pages,
                    'analysis_mode': self.mode.value,
                    'concurrent_requests': self.config.crawler.concurrent_requests
                }
            }
        }
        
        return report
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time statistics for monitoring."""
        process = psutil.Process()
        
        return {
            'progress': {
                'pages_queued': self.progress.pages_queued,
                'pages_crawled': self.progress.pages_crawled,
                'pages_analyzed': self.progress.pages_analyzed,
                'current_url': self.progress.current_url,
                'current_depth': self.progress.current_depth,
                'speed': self.progress.speed_pages_per_sec,
                'eta_seconds': self.progress.eta_seconds
            },
            'stats': {
                'successful': self.stats.successful_analyses,
                'failed': self.stats.failed_analyses,
                'skipped': self.stats.skipped_pages,
                'issues_found': self.stats.total_issues,
                'avg_score': self.stats.avg_page_score,
                'avg_time': self.stats.avg_analysis_time
            },
            'resources': {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'threads': process.num_threads(),
                'cache_size': len(self.cache.cache)
            },
            'health': {
                'broken_links': len(self.broken_links),
                'redirects': len(self.redirects),
                'duplicate_content': len([g for g in self.duplicate_content.values() if len(g) > 1]),
                'errors': self.progress.errors[-10:]  # Last 10 errors
            }
        }
    
    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get current crawl statistics (backward compatibility)."""
        return self.get_real_time_stats()
    
    def cleanup(self) -> None:
        """Cleanup resources and clear caches."""
        self.cache.clear_expired()
        self.results.clear()
        self.broken_links.clear()
        self.redirects.clear()
        self.duplicate_content.clear()
        self.analysis_contexts.clear()
        self._page_times.clear()
        
        # Force garbage collection
        import gc
        gc.collect()