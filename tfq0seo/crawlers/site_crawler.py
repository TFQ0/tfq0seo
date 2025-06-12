"""
tfq0seo Site Crawler
~~~~~~~~~~~~~~~~~~~

Professional-grade website crawler for comprehensive SEO analysis.
Supports configurable depth, concurrent crawling, and advanced filtering.
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import deque, defaultdict
import re
import hashlib
from bs4 import BeautifulSoup

from ..utils.error_handler import TFQ0SEOError, handle_analysis_error
from ..utils.cache_manager import CacheManager

@dataclass
class CrawlResult:
    """Data structure for crawl results."""
    url: str
    status_code: int
    redirect_url: Optional[str] = None
    redirect_chain: List[str] = field(default_factory=list)
    response_time: float = 0.0
    content_type: str = ""
    content_length: int = 0
    title: str = ""
    meta_description: str = ""
    h1_tags: List[str] = field(default_factory=list)
    h2_tags: List[str] = field(default_factory=list)
    canonical_url: Optional[str] = None
    robots_meta: str = ""
    internal_links: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)
    images: List[Dict] = field(default_factory=list)
    schema_markup: List[Dict] = field(default_factory=list)
    word_count: int = 0
    errors: List[str] = field(default_factory=list)
    crawl_depth: int = 0
    parent_url: Optional[str] = None

@dataclass 
class CrawlConfig:
    """Configuration for site crawling."""
    max_depth: int = 3
    max_pages: int = 500
    concurrent_requests: int = 10
    delay_between_requests: float = 0.5
    follow_redirects: bool = True
    respect_robots_txt: bool = True
    include_external_links: bool = True
    crawl_images: bool = True
    crawl_css: bool = False
    crawl_js: bool = False
    user_agent: str = "TFQ0SEO-Spider/2.0 (+https://github.com/tfq0/tfq0seo)"
    timeout: int = 30
    max_retries: int = 3
    allowed_domains: List[str] = field(default_factory=list)
    excluded_paths: List[str] = field(default_factory=list)
    include_query_params: bool = False
    custom_headers: Dict[str, str] = field(default_factory=dict)

class SiteCrawler:
    """
    Professional site crawler for comprehensive SEO analysis.
    
    Features:
    - Configurable crawl depth and limits
    - Concurrent/async crawling for speed
    - Robots.txt compliance
    - Comprehensive URL analysis
    - Link discovery and validation
    - Image analysis and optimization
    - Sitemap integration
    - Custom extraction rules
    - Advanced filtering options
    - Real-time progress tracking
    """
    
    def __init__(self, config: CrawlConfig = None, cache_manager: CacheManager = None):
        self.config = config or CrawlConfig()
        self.cache = cache_manager
        self.logger = logging.getLogger('tfq0seo.crawler')
        
        # Crawl state
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.redirected_urls: Dict[str, str] = {}
        self.robots_parsers: Dict[str, RobotFileParser] = {}
        
        # Results storage
        self.crawl_results: Dict[str, CrawlResult] = {}
        self.sitemap_urls: Set[str] = set()
        
        # Statistics
        self.stats = {
            'total_urls_found': 0,
            'total_urls_crawled': 0,
            'total_errors': 0,
            'start_time': 0,
            'end_time': 0,
            'status_codes': defaultdict(int),
            'content_types': defaultdict(int)
        }

    @handle_analysis_error
    async def crawl_site(self, start_url: str, progress_callback=None) -> Dict[str, Any]:
        """
        Crawl an entire website starting from the given URL.
        
        Args:
            start_url: The starting URL for the crawl
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict containing comprehensive crawl results
        """
        self.logger.info(f"Starting site crawl for: {start_url}")
        self.stats['start_time'] = time.time()
        
        # Parse base domain
        parsed_url = urlparse(start_url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Add base domain to allowed domains if not specified
        if not self.config.allowed_domains:
            self.config.allowed_domains.append(parsed_url.netloc)
        
        # Load robots.txt if respecting it
        if self.config.respect_robots_txt:
            await self._load_robots_txt(base_domain)
        
        # Load sitemaps
        await self._load_sitemaps(base_domain)
        
        # Initialize crawl queue
        crawl_queue = deque([(start_url, 0, None)])  # (url, depth, parent_url)
        
        # Start crawling
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            connector=aiohttp.TCPConnector(limit=self.config.concurrent_requests),
            headers={'User-Agent': self.config.user_agent}
        ) as session:
            
            # Process crawl queue
            while crawl_queue and len(self.crawled_urls) < self.config.max_pages:
                
                # Get batch of URLs to process
                batch = []
                for _ in range(min(self.config.concurrent_requests, len(crawl_queue))):
                    if crawl_queue:
                        batch.append(crawl_queue.popleft())
                
                if not batch:
                    break
                
                # Process batch concurrently
                tasks = [
                    self._crawl_url(session, url, depth, parent_url) 
                    for url, depth, parent_url in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and add new URLs to queue
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        url = batch[i][0]
                        self.logger.error(f"Error crawling {url}: {str(result)}")
                        self.failed_urls.add(url)
                        continue
                    
                    if result:
                        url, depth, parent_url = batch[i]
                        
                        # Add newly discovered URLs to queue
                        if depth < self.config.max_depth:
                            new_urls = result.internal_links
                            for new_url in new_urls:
                                if (new_url not in self.crawled_urls and 
                                    new_url not in self.failed_urls and
                                    self._should_crawl_url(new_url)):
                                    crawl_queue.append((new_url, depth + 1, url))
                        
                        # Update progress
                        if progress_callback:
                            progress_callback({
                                'crawled': len(self.crawled_urls),
                                'queue_size': len(crawl_queue),
                                'current_url': url
                            })
                
                # Respect delay between requests
                if self.config.delay_between_requests > 0:
                    await asyncio.sleep(self.config.delay_between_requests)
        
        self.stats['end_time'] = time.time()
        self.stats['total_urls_crawled'] = len(self.crawled_urls)
        self.stats['total_errors'] = len(self.failed_urls)
        
        return self._compile_crawl_results()

    async def _crawl_url(self, session: aiohttp.ClientSession, url: str, depth: int, parent_url: str) -> Optional[CrawlResult]:
        """Crawl a single URL and extract SEO data."""
        if url in self.crawled_urls:
            return None
        
        # Check robots.txt
        if not self._is_allowed_by_robots(url):
            return None
        
        start_time = time.time()
        
        try:
            # Add custom headers
            headers = dict(self.config.custom_headers)
            
            async with session.get(url, headers=headers) as response:
                response_time = time.time() - start_time
                content = await response.text()
                
                # Create crawl result
                result = CrawlResult(
                    url=url,
                    status_code=response.status,
                    response_time=response_time,
                    content_type=response.headers.get('content-type', ''),
                    content_length=len(content),
                    crawl_depth=depth,
                    parent_url=parent_url
                )
                
                # Handle redirects
                if response.status in [301, 302, 303, 307, 308]:
                    result.redirect_url = str(response.url)
                    result.redirect_chain = [url, str(response.url)]
                
                # Parse HTML content for SEO data
                if 'text/html' in result.content_type.lower():
                    soup = BeautifulSoup(content, 'html.parser')
                    await self._extract_seo_data(result, soup, url)
                
                # Update statistics
                self.stats['status_codes'][response.status] += 1
                self.stats['content_types'][result.content_type] += 1
                
                # Store result
                self.crawled_urls.add(url)
                self.crawl_results[url] = result
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {str(e)}")
            self.failed_urls.add(url)
            return None

    async def _extract_seo_data(self, result: CrawlResult, soup: BeautifulSoup, base_url: str):
        """Extract comprehensive SEO data from HTML."""
        
        # Title
        title_tag = soup.find('title')
        result.title = title_tag.get_text().strip() if title_tag else ""
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        result.meta_description = meta_desc.get('content', '') if meta_desc else ""
        
        # Headings
        result.h1_tags = [h1.get_text().strip() for h1 in soup.find_all('h1')]
        result.h2_tags = [h2.get_text().strip() for h2 in soup.find_all('h2')]
        
        # Canonical URL
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        result.canonical_url = canonical.get('href') if canonical else None
        
        # Robots meta
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        result.robots_meta = robots_meta.get('content', '') if robots_meta else ""
        
        # Links analysis
        await self._analyze_links(result, soup, base_url)
        
        # Images analysis
        await self._analyze_images(result, soup, base_url)
        
        # Schema markup
        await self._analyze_schema_markup(result, soup)
        
        # Word count
        text_content = soup.get_text()
        result.word_count = len(text_content.split())

    async def _analyze_links(self, result: CrawlResult, soup: BeautifulSoup, base_url: str):
        """Analyze internal and external links."""
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if not href:
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            parsed_link = urlparse(absolute_url)
            
            # Skip non-HTTP links
            if parsed_link.scheme not in ['http', 'https']:
                continue
            
            # Categorize as internal or external
            if parsed_link.netloc == base_domain:
                # Internal link
                if not self.config.include_query_params:
                    # Remove query parameters for deduplication
                    clean_url = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                else:
                    clean_url = absolute_url
                
                if clean_url not in result.internal_links:
                    result.internal_links.append(clean_url)
            else:
                # External link
                if self.config.include_external_links:
                    result.external_links.append(absolute_url)

    async def _analyze_images(self, result: CrawlResult, soup: BeautifulSoup, base_url: str):
        """Analyze images for SEO optimization."""
        if not self.config.crawl_images:
            return
        
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, src)
            
            image_data = {
                'url': absolute_url,
                'alt_text': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width'),
                'height': img.get('height'),
                'loading': img.get('loading', ''),
                'has_alt': bool(img.get('alt')),
                'is_decorative': not bool(img.get('alt')) and img.get('role') == 'presentation'
            }
            
            result.images.append(image_data)

    async def _analyze_schema_markup(self, result: CrawlResult, soup: BeautifulSoup):
        """Analyze structured data/schema markup."""
        # JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                schema_data = json.loads(script.string)
                result.schema_markup.append({
                    'type': 'json-ld',
                    'data': schema_data
                })
            except:
                continue
        
        # Microdata
        for element in soup.find_all(attrs={'itemtype': True}):
            result.schema_markup.append({
                'type': 'microdata',
                'itemtype': element.get('itemtype'),
                'element': element.name
            })

    async def _load_robots_txt(self, base_url: str):
        """Load and parse robots.txt."""
        robots_url = f"{base_url}/robots.txt"
        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            self.robots_parsers[base_url] = rp
            self.logger.info(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            self.logger.warning(f"Could not load robots.txt from {robots_url}: {str(e)}")

    async def _load_sitemaps(self, base_url: str):
        """Load and parse XML sitemaps."""
        sitemap_urls = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml"
        ]
        
        # Also check robots.txt for sitemap declarations
        if base_url in self.robots_parsers:
            rp = self.robots_parsers[base_url]
            # Note: RobotFileParser doesn't have a direct method to get sitemaps
            # This is a simplified approach
        
        for sitemap_url in sitemap_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(sitemap_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            await self._parse_sitemap(content)
                            self.logger.info(f"Loaded sitemap from {sitemap_url}")
                            break
            except Exception as e:
                self.logger.warning(f"Could not load sitemap from {sitemap_url}: {str(e)}")

    async def _parse_sitemap(self, sitemap_content: str):
        """Parse XML sitemap and extract URLs."""
        try:
            root = ET.fromstring(sitemap_content)
            
            # Handle sitemap index
            if 'sitemapindex' in root.tag.lower():
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        # Recursively load sub-sitemaps
                        await self._load_sitemap_url(loc.text)
            
            # Handle regular sitemap
            else:
                for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        self.sitemap_urls.add(loc.text)
                        
        except ET.ParseError as e:
            self.logger.warning(f"Could not parse sitemap XML: {str(e)}")

    async def _load_sitemap_url(self, sitemap_url: str):
        """Load a specific sitemap URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sitemap_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        await self._parse_sitemap(content)
        except Exception as e:
            self.logger.warning(f"Could not load sitemap from {sitemap_url}: {str(e)}")

    def _should_crawl_url(self, url: str) -> bool:
        """Determine if a URL should be crawled based on configuration."""
        parsed_url = urlparse(url)
        
        # Check allowed domains
        if self.config.allowed_domains:
            if parsed_url.netloc not in self.config.allowed_domains:
                return False
        
        # Check excluded paths
        for excluded_path in self.config.excluded_paths:
            if excluded_path in parsed_url.path:
                return False
        
        # Check file extensions (skip non-HTML by default)
        path = parsed_url.path.lower()
        if path.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar')):
            return False
        
        return True

    def _is_allowed_by_robots(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if not self.config.respect_robots_txt:
            return True
        
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if base_url in self.robots_parsers:
            rp = self.robots_parsers[base_url]
            return rp.can_fetch(self.config.user_agent, url)
        
        return True

    def _compile_crawl_results(self) -> Dict[str, Any]:
        """Compile comprehensive crawl results."""
        return {
            'summary': {
                'total_urls_crawled': len(self.crawled_urls),
                'total_urls_failed': len(self.failed_urls),
                'crawl_duration': self.stats['end_time'] - self.stats['start_time'],
                'sitemap_urls_found': len(self.sitemap_urls)
            },
            'statistics': self.stats,
            'pages': {url: result.__dict__ for url, result in self.crawl_results.items()},
            'failed_urls': list(self.failed_urls),
            'redirects': self.redirected_urls,
            'sitemap_urls': list(self.sitemap_urls)
        }

    def export_results(self, format: str = 'json', output_path: str = None) -> str:
        """Export crawl results to various formats."""
        results = self._compile_crawl_results()
        
        if format == 'json':
            import json
            output = json.dumps(results, indent=2)
        elif format == 'csv':
            output = self._export_to_csv(results)
        elif format == 'xlsx':
            output = self._export_to_xlsx(results)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output)
        
        return output

    def _export_to_csv(self, results: Dict) -> str:
        """Export results to CSV format."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        header = [
            'URL', 'Status Code', 'Title', 'Meta Description', 'H1 Count', 'H2 Count',
            'Word Count', 'Internal Links', 'External Links', 'Images', 'Response Time',
            'Content Type', 'Canonical URL', 'Robots Meta', 'Depth', 'Parent URL'
        ]
        writer.writerow(header)
        
        # Data rows
        for url, page in results['pages'].items():
            row = [
                page['url'],
                page['status_code'],
                page['title'],
                page['meta_description'],
                len(page['h1_tags']),
                len(page['h2_tags']),
                page['word_count'],
                len(page['internal_links']),
                len(page['external_links']),
                len(page['images']),
                page['response_time'],
                page['content_type'],
                page['canonical_url'] or '',
                page['robots_meta'],
                page['crawl_depth'],
                page['parent_url'] or ''
            ]
            writer.writerow(row)
        
        return output.getvalue()

    def get_broken_links(self) -> List[Dict]:
        """Get list of broken links found during crawl."""
        broken_links = []
        
        for url, result in self.crawl_results.items():
            if result.status_code >= 400:
                broken_links.append({
                    'url': url,
                    'status_code': result.status_code,
                    'parent_url': result.parent_url,
                    'error_type': self._get_error_type(result.status_code)
                })
        
        return broken_links

    def get_redirect_chains(self) -> List[Dict]:
        """Get redirect chains analysis."""
        redirects = []
        
        for url, result in self.crawl_results.items():
            if result.redirect_chain and len(result.redirect_chain) > 1:
                redirects.append({
                    'original_url': url,
                    'final_url': result.redirect_chain[-1],
                    'chain_length': len(result.redirect_chain),
                    'redirect_chain': result.redirect_chain,
                    'redirect_type': result.status_code
                })
        
        return redirects

    def get_duplicate_content(self) -> List[List[str]]:
        """Identify potential duplicate content using title and meta description."""
        duplicates = defaultdict(list)
        
        for url, result in self.crawl_results.items():
            # Create fingerprint based on title and meta description
            fingerprint = f"{result.title}|{result.meta_description}"
            if fingerprint and fingerprint != "|":
                duplicates[fingerprint].append(url)
        
        # Return groups with more than one URL
        return [urls for urls in duplicates.values() if len(urls) > 1]

    def _get_error_type(self, status_code: int) -> str:
        """Get human-readable error type for status code."""
        error_types = {
            400: "Bad Request",
            401: "Unauthorized", 
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        return error_types.get(status_code, f"HTTP {status_code}") 