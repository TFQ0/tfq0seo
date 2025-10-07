"""Async crawler module using aiohttp - simple and fast."""

import asyncio
import time
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
import re
import warnings

import aiohttp
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import validators

# Suppress XML parsing warnings when handling sitemaps
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

try:
    from lxml import etree
    PARSER = 'lxml'
except ImportError:
    PARSER = 'html.parser'


class Crawler:
    """Simple async crawler with robots.txt support."""
    
    def __init__(self, config=None):
        """Initialize crawler with configuration."""
        self.config = config or {}
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.results: List[Dict[str, Any]] = []
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Configuration
        self.max_concurrent = self.config.get('max_concurrent', 20)
        self.timeout = self.config.get('timeout', 30)
        self.user_agent = self.config.get('user_agent', 'tfq0seo/2.2.0')
        self.follow_redirects = self.config.get('follow_redirects', True)
        self.max_redirects = self.config.get('max_redirects', 5)
        self.max_pages = self.config.get('max_pages', 500)
        self.max_depth = self.config.get('max_depth', 5)
        self.allowed_domains = self.config.get('allowed_domains', [])
        self.excluded_patterns = self.config.get('excluded_patterns', [])
        self.respect_robots = self.config.get('respect_robots_txt', True)
        self.max_content_length = self.config.get('max_content_length', 100000)  # 100KB
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for consistency."""
        parsed = urlparse(url.lower())
        # Remove fragment, normalize path
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/') or '/',
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return normalized
    
    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL should be crawled."""
        # Basic validation
        if not validators.url(url):
            return False
        
        parsed = urlparse(url)
        
        # Check protocol
        if parsed.scheme not in ('http', 'https'):
            return False
        
        # Check if in allowed domains
        if self.allowed_domains:
            if not any(domain in parsed.netloc for domain in self.allowed_domains):
                return False
        else:
            # Default to same domain as base
            base_parsed = urlparse(base_domain)
            if parsed.netloc != base_parsed.netloc:
                return False
        
        # Check excluded patterns
        for pattern in self.excluded_patterns:
            if re.search(pattern, url):
                return False
        
        # Skip common non-HTML resources
        path = parsed.path.lower()
        skip_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', 
                          '.exe', '.mp3', '.mp4', '.avi', '.css', '.js')
        if path.endswith(skip_extensions):
            return False
        
        return True
    
    async def check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if not self.respect_robots:
            return True
        
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # Check cache
        if robots_url in self.robots_cache:
            return self.robots_cache[robots_url].can_fetch(self.user_agent, url)
        
        # Fetch and parse robots.txt
        try:
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    content = await response.text()
                    rp = RobotFileParser()
                    rp.parse(content.splitlines())
                    self.robots_cache[robots_url] = rp
                    return rp.can_fetch(self.user_agent, url)
        except:
            pass
        
        return True  # Allow if robots.txt not found
    
    async def fetch_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single page."""
        normalized_url = self.normalize_url(url)
        
        if normalized_url in self.visited_urls:
            return None
        
        self.visited_urls.add(normalized_url)
        
        # Check robots.txt
        if not await self.check_robots_txt(url):
            return None
        
        try:
            start_time = time.time()
            async with self.session.get(
                url,
                allow_redirects=self.follow_redirects,
                max_redirects=self.max_redirects
            ) as response:
                load_time = time.time() - start_time
                
                # Get content
                content = await response.read()
                
                # Truncate if too large
                if len(content) > self.max_content_length:
                    content = content[:self.max_content_length]
                
                # Try to decode as text
                try:
                    html = content.decode('utf-8', errors='ignore')
                except:
                    html = str(content)
                
                # Parse HTML
                soup = BeautifulSoup(html, PARSER)
                
                # Extract all data in single pass
                result = {
                    'url': str(response.url),
                    'status_code': response.status,
                    'content_type': response.headers.get('content-type', ''),
                    'load_time': load_time,
                    'content_length': len(content),
                    'headers': dict(response.headers),
                    'html': html,
                    'soup': soup,
                    'timestamp': time.time(),
                    'redirected_from': url if str(response.url) != url else None
                }
                
                return result
                
        except asyncio.TimeoutError:
            self.failed_urls.add(normalized_url)
            return {'url': url, 'error': 'Timeout', 'status_code': 0}
        except Exception as e:
            self.failed_urls.add(normalized_url)
            return {'url': url, 'error': str(e), 'status_code': 0}
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from a page."""
        links = []
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if href:
                absolute_url = urljoin(base_url, href)
                if self.is_valid_url(absolute_url, base_url):
                    links.append(absolute_url)
        return list(set(links))  # Remove duplicates
    
    async def crawl_site(self, start_url: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Crawl a website starting from the given URL."""
        max_pages = max_pages or self.max_pages
        to_visit = [start_url]
        depth_map = {start_url: 0}
        
        # Semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await self.fetch_page(url)
        
        while to_visit and len(self.results) < max_pages:
            # Process batch of URLs
            batch_size = min(self.max_concurrent, len(to_visit), max_pages - len(self.results))
            batch = to_visit[:batch_size]
            to_visit = to_visit[batch_size:]
            
            # Fetch pages in parallel
            tasks = [fetch_with_semaphore(url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    self.failed_urls.add(url)
                    continue
                
                if result is None:
                    continue
                
                self.results.append(result)
                
                # Extract and queue new links if we have soup
                if 'soup' in result and result.get('status_code') == 200:
                    current_depth = depth_map.get(url, 0)
                    if current_depth < self.max_depth:
                        links = self.extract_links(result['soup'], url)
                        for link in links:
                            if link not in self.visited_urls and link not in to_visit:
                                if link not in depth_map:
                                    depth_map[link] = current_depth + 1
                                    to_visit.append(link)
        
        return self.results
    
    async def crawl_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Crawl a list of specific URLs."""
        # Semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await self.fetch_page(url)
        
        # Process all URLs in batches
        for i in range(0, len(urls), self.max_concurrent):
            batch = urls[i:i + self.max_concurrent]
            tasks = [fetch_with_semaphore(url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    self.failed_urls.add(url)
                    self.results.append({'url': url, 'error': str(result), 'status_code': 0})
                elif result:
                    self.results.append(result)
        
        return self.results
    
    async def crawl_sitemap(self, sitemap_url: str) -> List[Dict[str, Any]]:
        """Crawl URLs from a sitemap."""
        # Fetch sitemap
        result = await self.fetch_page(sitemap_url)
        if not result or result.get('status_code') != 200:
            return []
        
        urls = []
        
        # Parse sitemap XML
        try:
            # Try to parse as XML
            if PARSER == 'lxml':
                root = etree.fromstring(result['html'].encode('utf-8'))
                # Extract URLs from sitemap
                for url in root.xpath('//ns:url/ns:loc/text()', 
                                     namespaces={'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
                    urls.append(url)
            else:
                # Fallback to BeautifulSoup
                soup = BeautifulSoup(result['html'], 'html.parser')
                for loc in soup.find_all('loc'):
                    urls.append(loc.text.strip())
        except Exception as e:
            print(f"Error parsing sitemap: {e}")
            return []
        
        # Crawl all URLs from sitemap
        return await self.crawl_urls(urls[:self.max_pages])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get crawl statistics."""
        successful = [r for r in self.results if r.get('status_code', 0) >= 200 and r.get('status_code', 0) < 400]
        failed = [r for r in self.results if r.get('status_code', 0) >= 400 or 'error' in r]
        
        total_load_time = sum(r.get('load_time', 0) for r in successful)
        avg_load_time = total_load_time / len(successful) if successful else 0
        
        return {
            'total_pages': len(self.results),
            'successful_pages': len(successful),
            'failed_pages': len(failed),
            'unique_urls': len(self.visited_urls),
            'average_load_time': avg_load_time,
            'total_load_time': total_load_time,
            'pages_per_second': len(successful) / total_load_time if total_load_time > 0 else 0
        }
