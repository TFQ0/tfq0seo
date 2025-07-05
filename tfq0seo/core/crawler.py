"""
Web crawler module for tfq0seo
"""
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from typing import Set, Dict, List, Optional, Callable, Tuple
import re
import time
from collections import deque
import validators
from rich.console import Console

console = Console()

class WebCrawler:
    """Asynchronous web crawler for SEO analysis"""
    
    def __init__(self, config):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.queued_urls: Set[str] = set()
        self.url_queue = deque()
        self.results: Dict[str, Dict] = {}
        self.robots_parser: Optional[RobotFileParser] = None
        self.base_domain = urlparse(config.url).netloc
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(config.concurrent_requests)
        self.crawl_count = 0
        
    async def initialize(self):
        """Initialize crawler session and robots.txt"""
        timeout = ClientTimeout(total=self.config.timeout)
        headers = {'User-Agent': self.config.user_agent}
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        
        if self.config.respect_robots:
            await self._load_robots_txt()
    
    async def _load_robots_txt(self):
        """Load and parse robots.txt"""
        try:
            robots_url = urljoin(self.config.url, '/robots.txt')
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    content = await response.text()
                    self.robots_parser.parse(content.splitlines())
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load robots.txt: {e}[/yellow]")
    
    def _should_crawl_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        # Check if already visited
        if url in self.visited_urls or url in self.queued_urls:
            return False
        
        # Check max pages
        if self.crawl_count >= self.config.max_pages:
            return False
        
        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if re.search(pattern, url):
                return False
        
        # Check include patterns if specified
        if self.config.include_patterns:
            if not any(re.search(pattern, url) for pattern in self.config.include_patterns):
                return False
        
        # Check if external
        parsed = urlparse(url)
        if parsed.netloc != self.base_domain and not self.config.include_external:
            return False
        
        # Check robots.txt
        if self.robots_parser and not self.robots_parser.can_fetch(self.config.user_agent, url):
            return False
        
        return True
    
    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalize and validate URL"""
        # Remove fragments
        url = url.split('#')[0]
        
        # Make absolute
        url = urljoin(base_url, url)
        
        # Parse and normalize
        parsed = urlparse(url)
        
        # Skip non-http(s) URLs
        if parsed.scheme not in ['http', 'https']:
            return None
        
        # Normalize path
        path = parsed.path
        if not path:
            path = '/'
        elif not path.endswith('/') and '.' not in path.split('/')[-1]:
            path += '/'
        
        # Reconstruct URL
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            path,
            parsed.params,
            parsed.query,
            ''
        ))
        
        return normalized
    
    async def _fetch_page(self, url: str) -> Optional[Dict]:
        """Fetch and parse a single page"""
        async with self.semaphore:
            try:
                start_time = time.time()
                
                async with self.session.get(url, allow_redirects=True) as response:
                    load_time = time.time() - start_time
                    
                    # Get final URL after redirects
                    final_url = str(response.url)
                    
                    # Get response data
                    content = await response.text()
                    status_code = response.status
                    headers = dict(response.headers)
                    content_type = headers.get('Content-Type', '')
                    
                    # Parse HTML if applicable
                    links = []
                    if 'text/html' in content_type:
                        soup = BeautifulSoup(content, 'lxml')
                        
                        # Extract links
                        for tag in soup.find_all(['a', 'link']):
                            href = tag.get('href')
                            if href:
                                normalized = self._normalize_url(href, final_url)
                                if normalized:
                                    links.append({
                                        'url': normalized,
                                        'text': tag.get_text(strip=True),
                                        'rel': tag.get('rel', []),
                                        'tag': tag.name
                                    })
                    
                    return {
                        'url': url,
                        'final_url': final_url,
                        'status_code': status_code,
                        'content_type': content_type,
                        'content': content,
                        'headers': headers,
                        'load_time': load_time,
                        'links': links,
                        'crawled_at': time.time()
                    }
                    
            except asyncio.TimeoutError:
                return {
                    'url': url,
                    'error': 'Timeout',
                    'status_code': 0
                }
            except Exception as e:
                return {
                    'url': url,
                    'error': str(e),
                    'status_code': 0
                }
    
    async def _process_page(self, url: str, depth: int, progress_callback: Optional[Callable] = None):
        """Process a single page and queue its links"""
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        self.crawl_count += 1
        
        # Update progress
        if progress_callback:
            progress_callback(self.crawl_count, self.config.max_pages)
        
        # Fetch page
        result = await self._fetch_page(url)
        if result:
            result['depth'] = depth
            self.results[url] = result
            
            # Queue links if not at max depth
            if depth < self.config.depth and result.get('links'):
                for link in result['links']:
                    link_url = link['url']
                    if self._should_crawl_url(link_url):
                        self.queued_urls.add(link_url)
                        self.url_queue.append((link_url, depth + 1))
        
        # Respect delay
        if self.config.delay > 0:
            await asyncio.sleep(self.config.delay)
    
    async def crawl(self, progress_callback: Optional[Callable] = None) -> Dict[str, Dict]:
        """Start crawling from the configured URL"""
        await self.initialize()
        
        try:
            # Add initial URL
            self.url_queue.append((self.config.url, 0))
            self.queued_urls.add(self.config.url)
            
            # Process queue
            while self.url_queue and self.crawl_count < self.config.max_pages:
                # Get batch of URLs to process
                batch = []
                for _ in range(min(self.config.concurrent_requests, len(self.url_queue))):
                    if self.url_queue:
                        batch.append(self.url_queue.popleft())
                
                # Process batch concurrently
                if batch:
                    tasks = [
                        self._process_page(url, depth, progress_callback)
                        for url, depth in batch
                    ]
                    await asyncio.gather(*tasks)
            
            return self.results
            
        finally:
            if self.session:
                await self.session.close()
    
    async def crawl_sitemap(self, sitemap_url: Optional[str] = None) -> List[str]:
        """Crawl sitemap.xml for URLs"""
        if not sitemap_url:
            sitemap_url = urljoin(self.config.url, '/sitemap.xml')
        
        urls = []
        
        try:
            async with self.session.get(sitemap_url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'xml')
                    
                    # Extract URLs from sitemap
                    for loc in soup.find_all('loc'):
                        url = loc.get_text(strip=True)
                        if validators.url(url):
                            urls.append(url)
                    
                    # Check for sitemap index
                    for sitemap in soup.find_all('sitemap'):
                        loc = sitemap.find('loc')
                        if loc:
                            sub_urls = await self.crawl_sitemap(loc.get_text(strip=True))
                            urls.extend(sub_urls)
        
        except Exception as e:
            console.print(f"[yellow]Warning: Could not crawl sitemap: {e}[/yellow]")
        
        return urls 