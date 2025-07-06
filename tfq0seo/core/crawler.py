"""
Web crawler module for tfq0seo
"""
import asyncio
import aiohttp
from aiohttp import ClientTimeout, ClientSession, TCPConnector
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from typing import Set, Dict, List, Optional, Callable, Tuple, Union
import re
import time
from collections import deque
import validators
from rich.console import Console
import logging
import hashlib
import ipaddress
import socket
from contextlib import asynccontextmanager
from .real_time_validator import RealTimeValidator

console = Console()
logger = logging.getLogger(__name__)

class WebCrawler:
    """Asynchronous web crawler for SEO analysis"""
    
    def __init__(self, config):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.queued_urls: Set[str] = set()
        self.url_queue = deque()
        self.results: Dict[str, Dict] = {}
        self.robots_parser: Optional[RobotFileParser] = None
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.base_domain = urlparse(config.url).netloc
        self.session: Optional[ClientSession] = None
        self.semaphore = asyncio.Semaphore(config.concurrent_requests)
        self.crawl_count = 0
        self.redirect_chains: Dict[str, List[Tuple[str, int]]] = {}
        self.retry_count = 3
        self.retry_delay = 1.0
        self.validator = RealTimeValidator()
        
    async def initialize(self):
        """Initialize crawler session and robots.txt"""
        # Create connector with connection pooling and SSL verification
        connector = TCPConnector(
            limit=self.config.concurrent_requests * 2,
            limit_per_host=self.config.concurrent_requests,
            ttl_dns_cache=300,
            ssl=True  # Enable SSL verification
        )
        
        timeout = ClientTimeout(
            total=self.config.timeout,
            connect=10,
            sock_read=10
        )
        
        headers = {
            'User-Agent': self.config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.session = ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
        
        if self.config.respect_robots:
            await self._load_robots_txt(self.config.url)
    
    async def _load_robots_txt(self, url: str):
        """Load and parse robots.txt for a given domain"""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            # Check cache first
            if parsed.netloc in self.robots_cache:
                self.robots_parser = self.robots_cache[parsed.netloc]
                return
            
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            
            async with self.session.get(robots_url, allow_redirects=True) as response:
                if response.status == 200:
                    content = await response.text()
                    # Parse robots.txt content
                    lines = content.splitlines()
                    self.robots_parser.parse(lines)
                    
                    # Cache the parser for this domain
                    self.robots_cache[parsed.netloc] = self.robots_parser
                    
                    # Extract crawl delay if specified
                    crawl_delay = self._extract_crawl_delay(lines)
                    if crawl_delay and crawl_delay > self.config.delay:
                        self.config.delay = crawl_delay
                        console.print(f"[yellow]Respecting crawl-delay: {crawl_delay}s[/yellow]")
                else:
                    # No robots.txt found, allow all
                    self.robots_parser = None
                    
        except Exception as e:
            logger.warning(f"Could not load robots.txt from {url}: {e}")
            self.robots_parser = None
    
    def _extract_crawl_delay(self, lines: List[str]) -> Optional[float]:
        """Extract crawl-delay directive from robots.txt"""
        for line in lines:
            if line.strip().lower().startswith('crawl-delay:'):
                try:
                    return float(line.split(':', 1)[1].strip())
                except:
                    pass
        return None
    
    def _should_crawl_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        # Validate URL format
        if not validators.url(url):
            return False
            
        # Check if already visited or queued
        normalized_url = self._normalize_url(url, self.config.url)
        if not normalized_url or normalized_url in self.visited_urls or normalized_url in self.queued_urls:
            return False
        
        # Check max pages
        if self.crawl_count >= self.config.max_pages:
            return False
        
        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Check include patterns if specified
        if self.config.include_patterns:
            if not any(re.search(pattern, url, re.IGNORECASE) for pattern in self.config.include_patterns):
                return False
        
        # Check if external
        parsed = urlparse(url)
        if parsed.netloc != self.base_domain and not self.config.include_external:
            return False
        
        # Security check - prevent SSRF
        if not self._is_safe_url(url):
            return False
        
        # Check robots.txt
        if self.robots_parser and not self.robots_parser.can_fetch(self.config.user_agent, url):
            return False
        
        return True
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe to crawl (prevent SSRF attacks)"""
        try:
            parsed = urlparse(url)
            
            # Block non-HTTP(S) schemes
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Block local addresses
            hostname = parsed.hostname
            if not hostname:
                return False
                
            # Check for IP addresses
            try:
                ip = ipaddress.ip_address(hostname)
                # Block private and reserved IP ranges
                if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                    return False
            except ValueError:
                # Not an IP address, check hostname
                if hostname.lower() in ['localhost', '127.0.0.1', '0.0.0.0', '::1']:
                    return False
                    
                # Resolve hostname to check for local addresses
                try:
                    addr_info = socket.getaddrinfo(hostname, None)
                    for addr in addr_info:
                        ip = ipaddress.ip_address(addr[4][0])
                        if ip.is_private or ip.is_reserved or ip.is_loopback:
                            return False
                except:
                    pass
            
            return True
            
        except Exception:
            return False
    
    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalize and validate URL"""
        try:
            # Remove fragments
            if '#' in url:
                url = url.split('#')[0]
            
            # Make absolute
            url = urljoin(base_url, url)
            
            # Parse URL
            parsed = urlparse(url)
            
            # Skip non-http(s) URLs
            if parsed.scheme not in ['http', 'https']:
                return None
            
            # Normalize hostname
            hostname = parsed.hostname.lower() if parsed.hostname else ''
            
            # Normalize path
            path = parsed.path or '/'
            # Remove duplicate slashes
            path = re.sub(r'/+', '/', path)
            # Remove trailing slash for non-directory paths
            if path != '/' and path.endswith('/') and '.' not in path.split('/')[-2]:
                path = path.rstrip('/')
            
            # Normalize query parameters
            if parsed.query:
                # Parse, sort, and reconstruct query string
                params = parse_qs(parsed.query, keep_blank_values=True)
                # Sort parameters for consistency
                sorted_params = sorted(params.items())
                query = urlencode(sorted_params, doseq=True)
            else:
                query = ''
            
            # Reconstruct normalized URL
            normalized = urlunparse((
                parsed.scheme,
                f"{hostname}:{parsed.port}" if parsed.port and (
                    (parsed.scheme == 'http' and parsed.port != 80) or
                    (parsed.scheme == 'https' and parsed.port != 443)
                ) else hostname,
                path,
                parsed.params,
                query,
                ''
            ))
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing URL {url}: {e}")
            return None
    
    async def _fetch_page(self, url: str, retry_count: int = 0) -> Optional[Dict]:
        """Fetch and parse a single page with retry logic"""
        async with self.semaphore:
            try:
                start_time = time.time()
                
                # Track redirect chain
                redirect_chain = []
                
                async with self.session.get(
                    url, 
                    allow_redirects=False,
                    ssl=True  # Verify SSL certificates
                ) as response:
                    
                    # Handle redirects manually to track chain
                    temp_response = response
                    temp_url = url
                    
                    while temp_response.status in [301, 302, 303, 307, 308]:
                        redirect_chain.append((temp_url, temp_response.status))
                        
                        location = temp_response.headers.get('Location')
                        if not location:
                            break
                            
                        temp_url = urljoin(temp_url, location)
                        
                        if len(redirect_chain) > 10:  # Prevent infinite redirects
                            break
                            
                        temp_response = await self.session.get(
                            temp_url,
                            allow_redirects=False,
                            ssl=True
                        )
                    
                    # Final response
                    response = temp_response
                    final_url = temp_url
                    
                    # Store redirect chain if any
                    if redirect_chain:
                        self.redirect_chains[url] = redirect_chain
                    
                    load_time = time.time() - start_time
                    
                    # Get response data
                    content = await response.text(errors='replace')  # Handle encoding errors
                    status_code = response.status
                    headers = dict(response.headers)
                    content_type = headers.get('Content-Type', '')
                    
                    # Parse HTML if applicable
                    links = []
                    if 'text/html' in content_type and status_code == 200:
                        try:
                            # Try lxml parser first, fall back to html.parser
                            try:
                                soup = BeautifulSoup(content, 'lxml')
                            except:
                                soup = BeautifulSoup(content, 'html.parser')
                            
                            # Extract links
                            for tag in soup.find_all(['a', 'link']):
                                href = tag.get('href')
                                if href:
                                    normalized = self._normalize_url(href, final_url)
                                    if normalized:
                                        links.append({
                                            'url': normalized,
                                            'text': tag.get_text(strip=True) if tag.name == 'a' else '',
                                            'rel': tag.get('rel', []),
                                            'tag': tag.name,
                                            'title': tag.get('title', '')
                                        })
                        except Exception as e:
                            logger.error(f"Error parsing HTML for {url}: {e}")
                    
                    # Prepare page data for validation
                    page_data = {
                        'url': url,
                        'final_url': final_url,
                        'status_code': status_code,
                        'content_type': content_type,
                        'content': content,
                        'headers': headers,
                        'load_time': load_time,
                        'links': links,
                        'redirect_chain': redirect_chain,
                        'crawled_at': time.time(),
                        'content_length': len(content.encode('utf-8')),
                        'response_headers': {
                            'cache_control': headers.get('Cache-Control', ''),
                            'expires': headers.get('Expires', ''),
                            'last_modified': headers.get('Last-Modified', ''),
                            'etag': headers.get('ETag', ''),
                            'content_encoding': headers.get('Content-Encoding', ''),
                            'server': headers.get('Server', ''),
                            'x_powered_by': headers.get('X-Powered-By', '')
                        }
                    }
                    
                    # Perform real-time validation
                    if status_code == 200 and 'text/html' in content_type:
                        validation_result = self.validator.validate_page_data(page_data)
                        page_data['validation'] = validation_result
                        
                        # Log warnings if any
                        if validation_result.get('warnings'):
                            for warning in validation_result['warnings'][:3]:  # Log first 3 warnings
                                logger.warning(f"Validation warning for {url}: {warning['message']}")
                        
                        # Add data quality score to page data
                        page_data['data_quality_score'] = validation_result.get('data_quality_score', 1.0)
                    
                    return page_data
                    
            except asyncio.TimeoutError:
                if retry_count < self.retry_count:
                    await asyncio.sleep(self.retry_delay * (2 ** retry_count))  # Exponential backoff
                    return await self._fetch_page(url, retry_count + 1)
                return {
                    'url': url,
                    'error': 'Timeout',
                    'status_code': 0
                }
            except aiohttp.ClientError as e:
                if retry_count < self.retry_count:
                    await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                    return await self._fetch_page(url, retry_count + 1)
                return {
                    'url': url,
                    'error': f'Client error: {str(e)}',
                    'status_code': 0
                }
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return {
                    'url': url,
                    'error': f'Error: {str(e)}',
                    'status_code': 0
                }
    
    async def _process_page(self, url: str, depth: int, progress_callback: Optional[Callable] = None):
        """Process a single page and queue its links"""
        normalized_url = self._normalize_url(url, self.config.url)
        if not normalized_url or normalized_url in self.visited_urls:
            return
        
        self.visited_urls.add(normalized_url)
        self.crawl_count += 1
        
        # Update progress
        if progress_callback:
            try:
                progress_callback(self.crawl_count, self.config.max_pages)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
        
        # Fetch page
        result = await self._fetch_page(normalized_url)
        if result:
            result['depth'] = depth
            self.results[normalized_url] = result
            
            # Queue links if not at max depth and page was successfully fetched
            if depth < self.config.depth and result.get('status_code') == 200 and result.get('links'):
                for link in result['links']:
                    link_url = link['url']
                    if self._should_crawl_url(link_url):
                        normalized_link = self._normalize_url(link_url, normalized_url)
                        if normalized_link and normalized_link not in self.queued_urls:
                            self.queued_urls.add(normalized_link)
                            self.url_queue.append((normalized_link, depth + 1))
        
        # Respect delay
        if self.config.delay > 0:
            await asyncio.sleep(self.config.delay)
    
    @asynccontextmanager
    async def _session_manager(self):
        """Context manager for proper session cleanup"""
        await self.initialize()
        try:
            yield self.session
        finally:
            if self.session and not self.session.closed:
                await self.session.close()
    
    async def crawl(self, progress_callback: Optional[Callable] = None) -> Dict[str, Dict]:
        """Start crawling from the configured URL"""
        async with self._session_manager():
            try:
                # Validate starting URL
                if not self._is_safe_url(self.config.url):
                    raise ValueError(f"Unsafe URL: {self.config.url}")
                
                # Add initial URL
                normalized_start = self._normalize_url(self.config.url, self.config.url)
                if not normalized_start:
                    raise ValueError(f"Invalid URL: {self.config.url}")
                
                self.url_queue.append((normalized_start, 0))
                self.queued_urls.add(normalized_start)
                
                # Process queue
                while self.url_queue and self.crawl_count < self.config.max_pages:
                    # Get batch of URLs to process
                    batch = []
                    batch_size = min(self.config.concurrent_requests, len(self.url_queue), 
                                   self.config.max_pages - self.crawl_count)
                    
                    for _ in range(batch_size):
                        if self.url_queue:
                            url, depth = self.url_queue.popleft()
                            # Remove from queued set
                            self.queued_urls.discard(url)
                            batch.append((url, depth))
                    
                    # Process batch concurrently
                    if batch:
                        tasks = [
                            self._process_page(url, depth, progress_callback)
                            for url, depth in batch
                        ]
                        
                        # Use gather with return_exceptions to handle individual failures
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Log any exceptions
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                url, depth = batch[i]
                                logger.error(f"Error processing {url}: {result}")
                
                # Clean up large content from results to save memory
                for url, data in self.results.items():
                    if 'content' in data and len(data['content']) > 100000:  # 100KB
                        # Keep only first 100KB for very large pages
                        data['content'] = data['content'][:100000] + '... [truncated]'
                
                return self.results
                
            except Exception as e:
                logger.error(f"Critical error during crawl: {e}")
                raise
    
    async def crawl_sitemap(self, sitemap_url: Optional[str] = None) -> List[str]:
        """Crawl sitemap.xml for URLs"""
        if not sitemap_url:
            parsed = urlparse(self.config.url)
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        
        urls = []
        processed_sitemaps = set()
        
        async def process_sitemap(url: str):
            """Recursively process sitemap and sitemap index files"""
            if url in processed_sitemaps:
                return
            
            processed_sitemaps.add(url)
            
            try:
                # Check if URL is safe
                if not self._is_safe_url(url):
                    logger.warning(f"Unsafe sitemap URL: {url}")
                    return
                
                result = await self._fetch_page(url)
                
                if result and result.get('status_code') == 200:
                    content = result.get('content', '')
                    
                    # Parse sitemap
                    try:
                        # Try parsing as XML first
                        soup = BeautifulSoup(content, 'xml')
                    except:
                        soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract URLs from sitemap
                    for loc in soup.find_all('loc'):
                        loc_url = loc.get_text(strip=True)
                        if validators.url(loc_url):
                            normalized = self._normalize_url(loc_url, self.config.url)
                            if normalized:
                                urls.append(normalized)
                    
                    # Check for sitemap index
                    for sitemap in soup.find_all('sitemap'):
                        loc = sitemap.find('loc')
                        if loc:
                            sub_sitemap_url = loc.get_text(strip=True)
                            if validators.url(sub_sitemap_url):
                                # Process sub-sitemap
                                await process_sitemap(sub_sitemap_url)
                    
                    # Check for common sitemap variations
                    if not urls and url.endswith('/sitemap.xml'):
                        # Try sitemap_index.xml
                        index_url = url.replace('/sitemap.xml', '/sitemap_index.xml')
                        if index_url not in processed_sitemaps:
                            await process_sitemap(index_url)
                        
                        # Try sitemaps directory
                        sitemaps_dir = url.replace('/sitemap.xml', '/sitemaps/sitemap.xml')
                        if sitemaps_dir not in processed_sitemaps:
                            await process_sitemap(sitemaps_dir)
            
            except Exception as e:
                logger.error(f"Error crawling sitemap {url}: {e}")
        
        # Initialize session if not already done
        if not self.session:
            async with self._session_manager():
                await process_sitemap(sitemap_url)
        else:
            await process_sitemap(sitemap_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        console.print(f"[green]Found {len(unique_urls)} unique URLs in sitemap[/green]")
        return unique_urls 