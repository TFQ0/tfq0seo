"""Advanced async crawler module with intelligent features and optimizations."""

import asyncio
import time
import hashlib
import random
from typing import Dict, List, Set, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from urllib.robotparser import RobotFileParser
from collections import deque, defaultdict
from dataclasses import dataclass, field
import re
import warnings
import logging

import aiohttp
from aiohttp import ClientTimeout, ClientError, ServerTimeoutError
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import validators

# Suppress XML parsing warnings when handling sitemaps
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Setup logging
logger = logging.getLogger(__name__)

try:
    from lxml import etree, html
    PARSER = 'lxml'
    HTML_PARSER = html
except ImportError:
    PARSER = 'html.parser'
    HTML_PARSER = None


@dataclass
class CrawlStats:
    """Statistics tracker for crawl performance."""
    start_time: float = field(default_factory=time.time)
    requests_made: int = 0
    bytes_downloaded: int = 0
    errors_encountered: int = 0
    rate_limit_hits: int = 0
    robots_blocked: int = 0
    redirects_followed: int = 0
    
    def get_summary(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time
        return {
            'elapsed_seconds': elapsed,
            'requests_made': self.requests_made,
            'requests_per_second': self.requests_made / elapsed if elapsed > 0 else 0,
            'bytes_downloaded': self.bytes_downloaded,
            'mb_downloaded': self.bytes_downloaded / (1024 * 1024),
            'errors': self.errors_encountered,
            'rate_limits': self.rate_limit_hits,
            'robots_blocked': self.robots_blocked,
            'redirects': self.redirects_followed
        }


class URLQueue:
    """Priority queue for URL management with deduplication."""
    
    def __init__(self):
        self.queue = deque()
        self.seen = set()
        self.priorities = {}
        
    def add(self, url: str, priority: int = 5, depth: int = 0):
        """Add URL with priority (lower = higher priority)."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if url_hash not in self.seen:
            self.seen.add(url_hash)
            self.queue.append((priority, depth, url))
            # Keep queue sorted by priority
            self.queue = deque(sorted(self.queue, key=lambda x: (x[0], x[1])))
    
    def get(self) -> Optional[Tuple[int, int, str]]:
        """Get next URL from queue."""
        if self.queue:
            return self.queue.popleft()
        return None
    
    def __len__(self):
        return len(self.queue)
    
    def has_url(self, url: str) -> bool:
        """Check if URL has been seen."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return url_hash in self.seen


class RateLimiter:
    """Adaptive rate limiter for respectful crawling."""
    
    def __init__(self, initial_delay: float = 0.1, max_delay: float = 5.0):
        self.delay = initial_delay
        self.max_delay = max_delay
        self.last_request_time = defaultdict(float)
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
    
    async def wait(self, domain: str):
        """Wait appropriate time before next request."""
        now = time.time()
        elapsed = now - self.last_request_time[domain]
        
        # Adaptive delay based on response times and errors
        if self.error_counts[domain] > 3:
            self.delay = min(self.delay * 2, self.max_delay)
        elif self.response_times[domain]:
            avg_response = sum(self.response_times[domain][-10:]) / len(self.response_times[domain][-10:])
            if avg_response > 2.0:  # Slow server
                self.delay = min(self.delay * 1.5, self.max_delay)
            elif avg_response < 0.5:  # Fast server
                self.delay = max(self.delay * 0.8, 0.05)
        
        wait_time = max(0, self.delay - elapsed)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self.last_request_time[domain] = time.time()
    
    def record_response(self, domain: str, response_time: float, is_error: bool = False):
        """Record response metrics for adaptive throttling."""
        self.response_times[domain].append(response_time)
        if is_error:
            self.error_counts[domain] += 1
        else:
            self.error_counts[domain] = max(0, self.error_counts[domain] - 1)


class EnhancedCrawler:
    """Advanced async crawler with intelligent features."""
    
    def __init__(self, config=None):
        """Initialize enhanced crawler with configuration."""
        self.config = config or {}
        self.visited_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}  # URL -> error message
        self.results: List[Dict[str, Any]] = []
        self.robots_cache: Dict[str, Tuple[RobotFileParser, float]] = {}  # Include expiry time
        self.session: Optional[aiohttp.ClientSession] = None
        self.url_queue = URLQueue()
        self.rate_limiter = RateLimiter()
        self.stats = CrawlStats()
        
        # Configuration with defaults
        self.max_concurrent = self.config.get('max_concurrent', 10)
        self.timeout = self.config.get('timeout', 30)
        self.user_agent = self.config.get('user_agent', 'tfq0seo/2.3.2 (Advanced Crawler)')
        self.follow_redirects = self.config.get('follow_redirects', True)
        self.max_redirects = self.config.get('max_redirects', 5)
        self.max_pages = self.config.get('max_pages', 500)
        self.max_depth = self.config.get('max_depth', 5)
        self.allowed_domains = self.config.get('allowed_domains', [])
        self.excluded_patterns = self.config.get('excluded_patterns', [])
        self.respect_robots = self.config.get('respect_robots_txt', True)
        self.max_content_length = self.config.get('max_content_length', 1024 * 1024)  # 1MB
        self.retry_attempts = self.config.get('retry_attempts', 2)
        self.retry_delay = self.config.get('retry_delay', 1.0)
        self.adaptive_throttle = self.config.get('adaptive_throttle', True)
        self.parse_javascript = self.config.get('parse_javascript', False)
        self.store_html = self.config.get('store_html', True)
        self.follow_sitemap = self.config.get('follow_sitemap', True)
        
        # Advanced browser headers for better compatibility
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Advanced connector with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent * 2,
            limit_per_host=self.max_concurrent,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
            force_close=False,
            keepalive_timeout=30
        )
        
        timeout = ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_connect=10,
            sock_read=self.timeout
        )
        
        # Cookie jar for session persistence
        jar = aiohttp.CookieJar()
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers,
            cookie_jar=jar,
            trust_env=True,
            trace_configs=[self._create_trace_config()]
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            # Wait a bit for connections to close properly
            await asyncio.sleep(0.25)
    
    def _create_trace_config(self) -> aiohttp.TraceConfig:
        """Create trace config for request monitoring."""
        trace_config = aiohttp.TraceConfig()
        
        async def on_request_start(session, trace_config_ctx, params):
            trace_config_ctx.start = asyncio.get_event_loop().time()
            self.stats.requests_made += 1
        
        async def on_request_end(session, trace_config_ctx, params):
            elapsed = asyncio.get_event_loop().time() - trace_config_ctx.start
            domain = urlparse(str(params.url)).netloc
            self.rate_limiter.record_response(domain, elapsed)
        
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)
        return trace_config
    
    def normalize_url(self, url: str) -> str:
        """Advanced URL normalization for better deduplication."""
        # Parse URL
        parsed = urlparse(url.lower())
        
        # Normalize the domain
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Normalize the path
        path = parsed.path
        path = re.sub(r'/+', '/', path)  # Remove duplicate slashes
        path = path.rstrip('/') if path != '/' else '/'
        
        # Sort and normalize query parameters
        query_params = parse_qs(parsed.query)
        # Remove common tracking parameters
        tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 
                          'utm_content', 'fbclid', 'gclid', 'ref', 'source'}
        query_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        
        # Sort parameters for consistency
        sorted_query = urlencode(sorted(query_params.items()), doseq=True)
        
        # Reconstruct normalized URL
        normalized = urlunparse((
            'https' if parsed.scheme == 'https' else 'http',
            netloc,
            path,
            parsed.params,
            sorted_query,
            ''  # Remove fragment
        ))
        
        return normalized
    
    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """Enhanced URL validation with more checks."""
        # Basic validation
        if not validators.url(url):
            return False
        
        parsed = urlparse(url)
        
        # Check protocol
        if parsed.scheme not in ('http', 'https'):
            return False
        
        # Check for data URLs or javascript
        if parsed.scheme in ('data', 'javascript', 'mailto', 'tel', 'ftp'):
            return False
        
        # Check domain restrictions
        if self.allowed_domains:
            if not any(domain in parsed.netloc for domain in self.allowed_domains):
                return False
        else:
            # Default to same domain as base
            base_parsed = urlparse(base_domain)
            base_domain = base_parsed.netloc.replace('www.', '')
            current_domain = parsed.netloc.replace('www.', '')
            if base_domain != current_domain:
                return False
        
        # Check excluded patterns
        for pattern in self.excluded_patterns:
            if re.search(pattern, url):
                return False
        
        # Skip common non-HTML resources
        path = parsed.path.lower()
        skip_extensions = (
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.7z',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
            '.css', '.js', '.json', '.xml', '.txt',
            '.woff', '.woff2', '.ttf', '.eot'
        )
        if path.endswith(skip_extensions):
            return False
        
        # Skip admin/login/logout URLs
        skip_paths = ['/wp-admin', '/admin', '/login', '/logout', '/signin', 
                     '/signout', '/register', '/wp-login', '/user/login']
        if any(skip in path for skip in skip_paths):
            return False
        
        return True
    
    async def check_robots_txt(self, url: str) -> bool:
        """Enhanced robots.txt checking with caching and expiry."""
        if not self.respect_robots:
            return True
        
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # Check cache with expiry (1 hour)
        if robots_url in self.robots_cache:
            rp, expiry = self.robots_cache[robots_url]
            if time.time() < expiry:
                allowed = rp.can_fetch(self.user_agent, url)
                if not allowed:
                    self.stats.robots_blocked += 1
                return allowed
        
        # Fetch and parse robots.txt
        try:
            async with self.session.get(robots_url, timeout=ClientTimeout(total=5)) as response:
                if response.status == 200:
                    content = await response.text()
                    rp = RobotFileParser()
                    rp.parse(content.splitlines())
                    
                    # Extract crawl delay if specified
                    for line in content.splitlines():
                        if line.lower().startswith('crawl-delay:'):
                            try:
                                delay = float(line.split(':')[1].strip())
                                self.rate_limiter.delay = max(self.rate_limiter.delay, delay)
                            except:
                                pass
                    
                    # Cache with 1-hour expiry
                    self.robots_cache[robots_url] = (rp, time.time() + 3600)
                    
                    allowed = rp.can_fetch(self.user_agent, url)
                    if not allowed:
                        self.stats.robots_blocked += 1
                    return allowed
        except:
            pass
        
        return True  # Allow if robots.txt not found
    
    async def fetch_page(self, url: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """Enhanced page fetching with retries and better error handling."""
        normalized_url = self.normalize_url(url)
        
        # Check if already visited
        if normalized_url in self.visited_urls:
            return None
        
        self.visited_urls.add(normalized_url)
        
        # Rate limiting
        domain = urlparse(url).netloc
        if self.adaptive_throttle:
            await self.rate_limiter.wait(domain)
        
        # Check robots.txt
        if not await self.check_robots_txt(url):
            return {'url': url, 'error': 'Blocked by robots.txt', 'status_code': 0}
        
        try:
            start_time = time.time()
            
            # Add some randomization to headers
            headers = self.headers.copy()
            headers['User-Agent'] = self._randomize_user_agent()
            
            async with self.session.get(
                url,
                allow_redirects=self.follow_redirects,
                max_redirects=self.max_redirects,
                headers=headers,
                ssl=False  # Skip SSL verification for better compatibility
            ) as response:
                load_time = time.time() - start_time
                
                # Track redirects
                if str(response.url) != url:
                    self.stats.redirects_followed += 1
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                is_html = any(ct in content_type for ct in ['text/html', 'application/xhtml'])
                
                # Handle non-HTML content
                if not is_html and 'application/xml' not in content_type and 'text/xml' not in content_type:
                    return {
                        'url': str(response.url),
                        'status_code': response.status,
                        'content_type': content_type,
                        'error': f'Non-HTML content: {content_type}',
                        'load_time': load_time
                    }
                
                # Read content with size limit
                content = b''
                chunk_size = 10240  # 10KB chunks
                async for chunk in response.content.iter_chunked(chunk_size):
                    content += chunk
                    self.stats.bytes_downloaded += len(chunk)
                    if len(content) > self.max_content_length:
                        content = content[:self.max_content_length]
                        break
                
                # Detect encoding
                encoding = response.get_encoding()
                if not encoding:
                    # Try to detect from content
                    if b'charset=' in content[:1024]:
                        match = re.search(b'charset=([^"\'\\s>;]+)', content[:1024])
                        if match:
                            encoding = match.group(1).decode('ascii', errors='ignore')
                    else:
                        encoding = 'utf-8'
                
                # Decode content
                try:
                    html = content.decode(encoding, errors='ignore')
                except:
                    html = content.decode('utf-8', errors='ignore')
                
                # Parse HTML with appropriate parser
                if PARSER == 'lxml' and is_html:
                    # Use lxml's HTML parser for better performance
                    try:
                        soup = BeautifulSoup(html, 'lxml')
                    except:
                        soup = BeautifulSoup(html, 'html.parser')
                else:
                    soup = BeautifulSoup(html, PARSER)
                
                # Detect if JavaScript rendering needed
                js_indicators = [
                    'window.location',
                    'document.write',
                    'React',
                    'Angular',
                    'Vue',
                    '__NEXT_DATA__',
                    '_app.js'
                ]
                needs_js = any(indicator in html for indicator in js_indicators)
                
                # Build result
                result = {
                    'url': str(response.url),
                    'status_code': response.status,
                    'content_type': content_type,
                    'load_time': load_time,
                    'content_length': len(content),
                    'headers': dict(response.headers),
                    'soup': soup,
                    'timestamp': time.time(),
                    'redirected_from': url if str(response.url) != url else None,
                    'encoding': encoding,
                    'needs_javascript': needs_js
                }
                
                # Optionally store HTML
                if self.store_html:
                    result['html'] = html
                
                # Record successful response
                self.rate_limiter.record_response(domain, load_time)
                
                return result
                
        except asyncio.TimeoutError:
            self.stats.errors_encountered += 1
            if retry_count < self.retry_attempts:
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self.fetch_page(url, retry_count + 1)
            
            self.failed_urls[normalized_url] = 'Timeout'
            self.rate_limiter.record_response(domain, self.timeout, is_error=True)
            return {'url': url, 'error': 'Timeout', 'status_code': 0}
            
        except ClientError as e:
            self.stats.errors_encountered += 1
            error_msg = str(e)
            
            # Handle rate limiting
            if hasattr(e, 'status') and e.status == 429:
                self.stats.rate_limit_hits += 1
                if retry_count < self.retry_attempts:
                    # Exponential backoff for rate limits
                    wait_time = min(60, 2 ** retry_count * 5)
                    await asyncio.sleep(wait_time)
                    return await self.fetch_page(url, retry_count + 1)
            
            self.failed_urls[normalized_url] = error_msg
            self.rate_limiter.record_response(domain, 0, is_error=True)
            return {'url': url, 'error': error_msg, 'status_code': getattr(e, 'status', 0)}
            
        except Exception as e:
            self.stats.errors_encountered += 1
            self.failed_urls[normalized_url] = str(e)
            return {'url': url, 'error': str(e), 'status_code': 0}
    
    def _randomize_user_agent(self) -> str:
        """Add slight randomization to user agent to appear more natural."""
        agents = [
            self.user_agent,
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        return random.choice(agents) if random.random() < 0.1 else self.user_agent
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[str, int]]:
        """Enhanced link extraction with priority scoring."""
        links_with_priority = []
        
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if not href:
                continue
            
            # Make absolute URL
            absolute_url = urljoin(base_url, href)
            
            if not self.is_valid_url(absolute_url, base_url):
                continue
            
            # Priority scoring (lower is higher priority)
            priority = 5  # Default
            
            # Prioritize certain patterns
            if any(pattern in href.lower() for pattern in ['index', 'home', 'main']):
                priority = 1
            elif any(pattern in href.lower() for pattern in ['product', 'service', 'about']):
                priority = 2
            elif any(pattern in href.lower() for pattern in ['contact', 'blog', 'news']):
                priority = 3
            elif any(pattern in href.lower() for pattern in ['privacy', 'terms', 'legal']):
                priority = 8
            
            # Deprioritize pagination
            if re.search(r'[?&]page=\d+', href):
                priority = 9
            
            links_with_priority.append((absolute_url, priority))
        
        return links_with_priority
    
    async def crawl_site(self, start_url: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Enhanced website crawling with intelligent queue management."""
        max_pages = max_pages or self.max_pages
        
        # Initialize queue with start URL
        self.url_queue.add(start_url, priority=0, depth=0)
        
        # Check for sitemap
        if self.follow_sitemap:
            sitemap_urls = await self._discover_sitemaps(start_url)
            for url in sitemap_urls[:max_pages]:
                self.url_queue.add(url, priority=1, depth=1)
        
        # Semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await self.fetch_page(url)
        
        active_tasks = set()
        
        while (self.url_queue or active_tasks) and len(self.results) < max_pages:
            # Start new tasks up to concurrency limit
            while len(active_tasks) < self.max_concurrent and self.url_queue and len(self.results) < max_pages:
                item = self.url_queue.get()
                if item:
                    priority, depth, url = item
                    if depth <= self.max_depth:
                        task = asyncio.create_task(fetch_with_semaphore(url))
                        active_tasks.add((task, url, depth))
            
            if not active_tasks:
                break
            
            # Wait for at least one task to complete
            done, pending = await asyncio.wait(
                [task for task, _, _ in active_tasks],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Process completed tasks
            for task in done:
                # Find the associated URL and depth
                for task_tuple in active_tasks:
                    if task_tuple[0] == task:
                        _, url, depth = task_tuple
                        active_tasks.remove(task_tuple)
                        break
                
                try:
                    result = await task
                    if result and 'error' not in result:
                        self.results.append(result)
                        
                        # Extract and queue new links
                        if 'soup' in result and result.get('status_code') == 200:
                            if depth < self.max_depth:
                                links = self.extract_links(result['soup'], url)
                                for link, priority in links:
                                    self.url_queue.add(link, priority, depth + 1)
                    elif result:
                        self.results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
        
        # Cancel any remaining tasks
        for task, _, _ in active_tasks:
            task.cancel()
        
        return self.results
    
    async def _discover_sitemaps(self, base_url: str) -> List[str]:
        """Discover and parse sitemaps for a website."""
        urls = []
        parsed = urlparse(base_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Common sitemap locations
        sitemap_urls = [
            f"{base_domain}/sitemap.xml",
            f"{base_domain}/sitemap_index.xml",
            f"{base_domain}/sitemap-index.xml",
            f"{base_domain}/sitemaps/sitemap.xml"
        ]
        
        # Check robots.txt for sitemap
        robots_url = f"{base_domain}/robots.txt"
        try:
            async with self.session.get(robots_url, timeout=ClientTimeout(total=5)) as response:
                if response.status == 200:
                    content = await response.text()
                    for line in content.splitlines():
                        if line.lower().startswith('sitemap:'):
                            sitemap_url = line.split(':', 1)[1].strip()
                            if sitemap_url not in sitemap_urls:
                                sitemap_urls.append(sitemap_url)
        except:
            pass
        
        # Try to fetch sitemaps
        for sitemap_url in sitemap_urls:
            try:
                urls.extend(await self._parse_sitemap(sitemap_url))
                if urls:
                    break  # Use first successful sitemap
            except:
                continue
        
        return urls
    
    async def _parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse a sitemap or sitemap index."""
        urls = []
        
        try:
            async with self.session.get(sitemap_url, timeout=ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return urls
                
                content = await response.text()
                
                # Check if it's a sitemap index
                if '<sitemapindex' in content:
                    # Parse sitemap index
                    if PARSER == 'lxml':
                        try:
                            root = etree.fromstring(content.encode('utf-8'))
                            for sitemap in root.xpath('//ns:sitemap/ns:loc/text()', 
                                                     namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
                                # Recursively parse child sitemaps
                                child_urls = await self._parse_sitemap(sitemap)
                                urls.extend(child_urls[:100])  # Limit per sitemap
                        except:
                            pass
                    else:
                        soup = BeautifulSoup(content, 'xml')
                        for loc in soup.find_all('loc'):
                            if loc.parent.name == 'sitemap':
                                child_urls = await self._parse_sitemap(loc.text.strip())
                                urls.extend(child_urls[:100])
                else:
                    # Parse regular sitemap
                    if PARSER == 'lxml':
                        try:
                            root = etree.fromstring(content.encode('utf-8'))
                            for url in root.xpath('//ns:url/ns:loc/text()', 
                                                 namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
                                urls.append(url)
                        except:
                            pass
                    else:
                        soup = BeautifulSoup(content, 'xml')
                        for loc in soup.find_all('loc'):
                            if loc.parent.name == 'url':
                                urls.append(loc.text.strip())
        except Exception as e:
            logger.debug(f"Error parsing sitemap {sitemap_url}: {e}")
        
        return urls
    
    async def crawl_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Crawl a list of specific URLs with improved batching."""
        # Semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await self.fetch_page(url)
        
        # Process all URLs concurrently with proper error handling
        tasks = []
        for url in urls:
            task = asyncio.create_task(fetch_with_semaphore(url))
            tasks.append((task, url))
        
        # Gather results
        for task, url in tasks:
            try:
                result = await task
                if result:
                    self.results.append(result)
            except Exception as e:
                self.failed_urls[url] = str(e)
                self.results.append({'url': url, 'error': str(e), 'status_code': 0})
        
        return self.results
    
    async def crawl_sitemap(self, sitemap_url: str) -> List[Dict[str, Any]]:
        """Crawl URLs from a sitemap with sitemap index support."""
        urls = await self._parse_sitemap(sitemap_url)
        
        if not urls:
            return []
        
        # Crawl discovered URLs
        return await self.crawl_urls(urls[:self.max_pages])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive crawl statistics."""
        successful = [r for r in self.results if r.get('status_code', 0) >= 200 and r.get('status_code', 0) < 400]
        failed = [r for r in self.results if r.get('status_code', 0) >= 400 or 'error' in r]
        redirects = [r for r in self.results if 300 <= r.get('status_code', 0) < 400]
        
        total_load_time = sum(r.get('load_time', 0) for r in successful)
        avg_load_time = total_load_time / len(successful) if successful else 0
        
        # Status code distribution
        status_distribution = defaultdict(int)
        for r in self.results:
            status_distribution[r.get('status_code', 0)] += 1
        
        return {
            'total_pages': len(self.results),
            'successful_pages': len(successful),
            'failed_pages': len(failed),
            'redirected_pages': len(redirects),
            'unique_urls': len(self.visited_urls),
            'average_load_time': avg_load_time,
            'total_load_time': total_load_time,
            'pages_per_second': len(successful) / total_load_time if total_load_time > 0 else 0,
            'status_distribution': dict(status_distribution),
            'failed_urls': dict(list(self.failed_urls.items())[:10]),  # Top 10 failed
            'stats': self.stats.get_summary(),
            'queue_remaining': len(self.url_queue),
            'javascript_pages': sum(1 for r in self.results if r.get('needs_javascript', False))
        }


# Backward compatibility - keep old class name as alias
Crawler = EnhancedCrawler