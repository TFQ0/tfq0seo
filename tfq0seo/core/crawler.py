"""Bounded asynchronous crawling, URL discovery, and response collection."""

import asyncio
import heapq
import itertools
import logging
import math
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import aiohttp
from aiohttp import ClientError, ClientTimeout
from bs4 import BeautifulSoup, FeatureNotFound, UnicodeDammit
from ..urls import resolve_url
from .models import FetchResult, normalize_fetch_result

logger = logging.getLogger(__name__)

# XML discovery deliberately does not depend on the optional HTML parser.
try:
    import lxml.html as HTML_PARSER
    PARSER = 'lxml'
except ImportError:
    HTML_PARSER = None
    PARSER = 'html.parser'


@dataclass
class CrawlStats:
    start_time: float = field(default_factory=time.time)
    requests_made: int = 0
    bytes_downloaded: int = 0
    errors_encountered: int = 0
    rate_limit_hits: int = 0
    robots_blocked: int = 0
    redirects_followed: int = 0

    def get_summary(self) -> Dict[str, Any]:
        elapsed = max(0, time.time() - self.start_time)
        return {
            'elapsed_seconds': elapsed,
            'requests_made': self.requests_made,
            'requests_per_second': self.requests_made / elapsed if elapsed else 0,
            'bytes_downloaded': self.bytes_downloaded,
            'mb_downloaded': self.bytes_downloaded / (1024 * 1024),
            'errors': self.errors_encountered,
            'rate_limits': self.rate_limit_hits,
            'robots_blocked': self.robots_blocked,
            'redirects': self.redirects_followed,
        }


class URLQueue:
    """A bounded heap; the caller supplies normalized URL identities."""

    def __init__(self, max_size: Optional[int] = None):
        self.queue = []
        self.seen = set()
        self.max_size = max_size
        self._sequence = itertools.count()

    def add(self, url: str, priority: int = 5, depth: int = 0) -> bool:
        if url in self.seen:
            return False
        if self.max_size is not None and len(self.seen) >= self.max_size:
            return False
        self.seen.add(url)
        heapq.heappush(self.queue, (depth, priority, next(self._sequence), url))
        return True

    def get(self) -> Optional[Tuple[int, int, str]]:
        if not self.queue:
            return None
        depth, priority, _, url = heapq.heappop(self.queue)
        return priority, depth, url

    def __len__(self):
        return len(self.queue)

    def has_url(self, url: str) -> bool:
        return url in self.seen


class RateLimiter:
    """Serialize request starts per origin, independently of request duration."""

    def __init__(self, initial_delay: float = 0.1, max_delay: float = 5.0,
                 adaptive: bool = True):
        self.delay = initial_delay
        self.max_delay = max(initial_delay, max_delay)
        self.adaptive = adaptive
        self.last_request_time = defaultdict(float)
        self.response_times = defaultdict(lambda: deque(maxlen=10))
        self.error_counts = defaultdict(int)
        self._locks = defaultdict(asyncio.Lock)
        self._minimum_delays = defaultdict(float)
        self._adaptive_delays = defaultdict(lambda: initial_delay)
        self._not_before = defaultdict(float)

    def set_minimum_delay(self, domain: str, delay: float):
        self._minimum_delays[domain] = max(self._minimum_delays[domain], delay)

    def defer(self, domain: str, delay: float):
        self._not_before[domain] = max(self._not_before[domain], time.monotonic() + delay)

    async def wait(self, domain: str):
        async with self._locks[domain]:
            delay = max(self.delay, self._minimum_delays[domain],
                        self._adaptive_delays[domain] if self.adaptive else 0)
            while True:
                ready_at = max(self.last_request_time[domain] + delay,
                               self._not_before[domain])
                remaining = ready_at - time.monotonic()
                if remaining <= 0:
                    break
                await asyncio.sleep(remaining)
            self.last_request_time[domain] = time.monotonic()

    def record_response(self, domain: str, response_time: float, is_error: bool = False):
        self.response_times[domain].append(response_time)
        self.error_counts[domain] = (self.error_counts[domain] + 1 if is_error
                                     else max(0, self.error_counts[domain] - 1))
        if not self.adaptive:
            return
        current = self._adaptive_delays[domain]
        if is_error:
            current = min(self.max_delay, max(0.05, current) * 2)
        elif response_time > 2:
            current = min(self.max_delay, max(0.05, current) * 1.5)
        elif response_time < 0.5:
            current = max(self.delay, current * 0.8)
        self._adaptive_delays[domain] = current


class _SitemapTreeBuilder(ElementTree.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError('Sitemaps containing a document type declaration are not supported')


class EnhancedCrawler:
    """Collect terminal page outcomes within an origin and resource budget.

    Direct/batch fetches use each supplied URL as their scope. Site crawling and
    sitemap discovery stay on the starting hostname and port; changing between
    standard HTTP and HTTPS ports is allowed. allowed_domains overrides that
    scope using exact hostnames or explicit *.example.com subdomain patterns.
    """

    def __init__(self, config=None):
        self.config = dict(config or {})

        def option(name, default, *aliases):
            for key in (name,) + aliases:
                if key in self.config:
                    return self.config[key]
            return default

        self.max_concurrent = option('max_concurrent', 10, 'concurrent_requests')
        self.timeout = option('timeout', 30)
        self.connect_timeout = option('connect_timeout', 10)
        self.read_timeout = option('read_timeout', self.timeout)
        self.user_agent = option('user_agent', 'tfq0seo/2.3.2 (SEO Crawler)')
        self.follow_redirects = option('follow_redirects', True)
        self.max_redirects = option('max_redirects', 5)
        self.max_pages = option('max_pages', 500)
        self.max_depth = option('max_depth', 5)
        self.max_crawl_time = option('max_crawl_time', 3600)
        self.allowed_domains = option('allowed_domains', [])
        self.allowed_schemes = option('allowed_schemes', ['http', 'https'])
        self.excluded_patterns = option('excluded_patterns', [])
        self.respect_robots = option('respect_robots_txt', True)
        self.robots_cache_ttl = option('robots_cache_ttl', 86400)
        self.crawl_delay_factor = option('crawl_delay_factor', 1.0)
        self.max_content_length = option('max_page_size', 10 * 1024 * 1024, 'max_content_length')
        self.retry_attempts = option('max_retries', 3, 'retry_attempts')
        self.retry_on_status = option('retry_on_status', [429, 500, 502, 503, 504])
        self.retry_delay = option('retry_backoff_factor', 2.0, 'retry_delay')
        self.adaptive_throttle = option('adaptive_delay', True, 'adaptive_throttle')
        self.parse_javascript = option('parse_javascript', False)
        self.store_html = option('store_html', True)
        self.follow_sitemap = option('use_sitemap', True, 'follow_sitemap')
        self.discover_sitemaps = option('discover_sitemaps', True)
        self.verify_ssl = option('verify_ssl', True)
        self.proxy = option('proxy', None)
        self._base_url = None
        self._deadline = None
        self._interrupted_fetches = None
        self._validate_config()

        delay = max(option('delay_between_requests', 0), option('min_delay', 0))
        rate = option('rate_limit_per_second', None)
        if rate is not None:
            delay = max(delay, 1 / rate)
        self.rate_limiter = RateLimiter(delay, option('max_delay', 5), self.adaptive_throttle)
        self.visited_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}
        self.results: List[Dict[str, Any]] = []
        self.robots_cache: Dict[str, Tuple[RobotFileParser, float]] = {}
        self._robots_locks = defaultdict(asyncio.Lock)
        self._robots_sitemaps = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.url_queue = URLQueue(max_size=self._frontier_limit(self.max_pages))
        self._parents = {}
        self.stats = CrawlStats()
        self.limit_reasons: Set[str] = set()
        self.discovery_errors: List[Dict[str, str]] = []
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }
        for key, value in option('custom_headers', {}).items():
            previous = next((name for name in self.headers if name.lower() == key.lower()), None)
            if previous:
                del self.headers[previous]
            self.headers[key] = value
        self.user_agent = next((value for key, value in self.headers.items()
                                if key.lower() == 'user-agent'), self.user_agent)

    def _validate_config(self):
        positive = {
            'max_concurrent': self.max_concurrent, 'timeout': self.timeout,
            'connect_timeout': self.connect_timeout, 'read_timeout': self.read_timeout,
            'max_pages': self.max_pages, 'max_page_size': self.max_content_length,
            'max_crawl_time': self.max_crawl_time,
            'max_connections_per_host': self.config.get('max_connections_per_host', self.max_concurrent),
        }
        nonnegative = {
            'max_depth': self.max_depth, 'max_redirects': self.max_redirects,
            'max_retries': self.retry_attempts, 'retry_backoff_factor': self.retry_delay,
            'robots_cache_ttl': self.robots_cache_ttl, 'crawl_delay_factor': self.crawl_delay_factor,
            'dns_cache_ttl': self.config.get('dns_cache_ttl', 300),
        }
        for name in ('delay_between_requests', 'min_delay', 'max_delay'):
            nonnegative[name] = self.config.get(name, 0)
        if self.config.get('rate_limit_per_second') is not None:
            positive['rate_limit_per_second'] = self.config['rate_limit_per_second']
        for name, value in positive.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be a positive finite number')
        for name, value in nonnegative.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'{name} must be a non-negative finite number')
        for name, value in (
            ('max_concurrent', self.max_concurrent), ('max_pages', self.max_pages),
            ('max_page_size', self.max_content_length), ('max_depth', self.max_depth),
            ('max_redirects', self.max_redirects), ('max_retries', self.retry_attempts),
        ):
            if not isinstance(value, int):
                raise ValueError(f'{name} must be an integer')
        if not isinstance(self.allowed_schemes, (list, tuple)) or not self.allowed_schemes or any(s not in ('http', 'https') for s in self.allowed_schemes):
            raise ValueError('allowed_schemes must contain only http and/or https')
        for name, values in (('allowed_domains', self.allowed_domains), ('excluded_patterns', self.excluded_patterns)):
            if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
                raise ValueError(f'{name} must be a list of strings')
        try:
            self._excluded = [re.compile(pattern) for pattern in self.excluded_patterns]
        except re.error as exc:
            raise ValueError(f'Invalid excluded_patterns expression: {exc}') from exc
        if not isinstance(self.retry_on_status, (list, tuple)) or any(not isinstance(s, int) or not 400 <= s <= 599 for s in self.retry_on_status):
            raise ValueError('retry_on_status must be a list of HTTP error status codes')
        headers = self.config.get('custom_headers', {})
        if not isinstance(headers, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()):
            raise ValueError('custom_headers must be a dictionary of strings')
        for key in ('verify_ssl', 'follow_redirects', 'respect_robots_txt', 'store_html',
                    'use_sitemap', 'discover_sitemaps', 'adaptive_delay', 'use_connection_pooling'):
            if key in self.config and not isinstance(self.config[key], bool):
                raise ValueError(f'{key} must be a boolean')

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=self.config.get('max_connections_per_host', self.max_concurrent),
            ttl_dns_cache=self.config.get('dns_cache_ttl', 300),
            ssl=self.verify_ssl,
            force_close=not self.config.get('use_connection_pooling', True),
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=ClientTimeout(total=self.timeout, connect=self.connect_timeout,
                                  sock_connect=self.connect_timeout, sock_read=self.read_timeout),
            headers=self.headers,
            trust_env=False,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @staticmethod
    def _host(parsed):
        return (parsed.hostname or '').rstrip('.').encode('idna').decode('ascii').lower()

    @staticmethod
    def _port(parsed):
        return parsed.port if parsed.port is not None else (443 if parsed.scheme == 'https' else 80)

    def normalize_url(self, url: str) -> str:
        """Normalize the authority and fragment without changing path/query semantics."""
        try:
            parsed = urlparse(url)
            host = self._host(parsed)
            if ':' in host:
                host = f'[{host}]'
            port = parsed.port
            if port is not None and port != (443 if parsed.scheme.lower() == 'https' else 80):
                host += f':{port}'
            normalized = urlunparse((parsed.scheme.lower(), host, parsed.path or '/',
                                     parsed.params, parsed.query, ''))
            if '?' in url.split('#', 1)[0] and not parsed.query:
                normalized += '?'
            return normalized
        except (ValueError, UnicodeError, TypeError):
            return url

    def _valid_url(self, url: str, base_url: str, page: bool = True,
                   apply_filters: bool = True) -> bool:
        if not isinstance(url, str) or re.search(r'[\x00-\x20\x7f]', url):
            return False
        if resolve_url(url, url) is None:
            return False
        try:
            parsed = urlparse(url)
            host = self._host(parsed)
            if parsed.scheme not in self.allowed_schemes or not host or parsed.username is not None or parsed.password is not None:
                return False
            if self._port(parsed) == 0:
                return False
            if self.allowed_domains:
                allowed = False
                for domain in self.allowed_domains:
                    wildcard = domain.startswith('*.')
                    configured = urlparse('//' + (domain[2:] if wildcard else domain))
                    configured_host = self._host(configured)
                    match = (host.endswith('.' + configured_host) if wildcard else host == configured_host)
                    if match and (configured.port is None or self._port(parsed) == configured.port):
                        allowed = True
                        break
                if not allowed:
                    return False
            else:
                base = urlparse(base_url)
                if host != self._host(base):
                    return False
                default_transition = (
                    self._port(parsed) == (443 if parsed.scheme == 'https' else 80)
                    and self._port(base) == (443 if base.scheme == 'https' else 80)
                )
                if not default_transition and self._port(parsed) != self._port(base):
                    return False
        except (ValueError, UnicodeError, TypeError, AttributeError):
            return False
        if apply_filters and any(pattern.search(url) for pattern in self._excluded):
            return False
        if page:
            path = parsed.path.lower()
            extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',
                          '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                          '.zip', '.rar', '.tar', '.gz', '.7z', '.mp3', '.mp4',
                          '.avi', '.mov', '.wmv', '.flv', '.css', '.js', '.json',
                          '.xml', '.txt', '.woff', '.woff2', '.ttf', '.eot')
            if path.endswith(extensions):
                return False
            if any(re.search(r'/' + part + r'(?:/|$|\.)', path)
                   for part in ('wp-admin', 'admin', 'login', 'logout', 'signin',
                                'signout', 'register', 'wp-login')):
                return False
        return True

    def is_valid_url(self, url: str, base_domain: str) -> bool:
        return self._valid_url(url, self._base_url or base_domain)

    def _origin(self, url):
        parsed = urlparse(self.normalize_url(url))
        return f'{parsed.scheme}://{parsed.netloc}'

    def _failure(self, url: str, message: str, **fields) -> Dict[str, Any]:
        result = {'url': url, 'requested_url': url, 'status_code': 0,
                  'error': message, 'outcome': 'failed', 'headers': None,
                  'redirect_chain': [], 'load_time': None, 'timestamp': time.time(),
                  'timings': {'headers_seconds': None, 'download_seconds': None,
                              'network_seconds': None, 'total_seconds': None}}
        result.update(fields)
        return result

    @staticmethod
    def _response_headers(headers):
        values, seen = {}, set()
        for key in headers:
            if key.lower() in seen:
                continue
            seen.add(key.lower())
            instances = headers.getall(key)
            values[key] = instances if len(instances) > 1 else instances[0]
        return values

    async def _read_bounded(self, response, limit):
        content = bytearray()
        async for chunk in response.content.iter_chunked(min(16384, limit + 1)):
            self.stats.bytes_downloaded += len(chunk)
            remaining = limit - len(content)
            content.extend(chunk[:remaining])
            if len(chunk) > remaining:
                return bytes(content), True
        return bytes(content), False

    def _retry_after(self, value: Optional[str], attempt: int) -> float:
        delay = self.retry_delay * (2 ** min(attempt, 20))
        if value:
            try:
                seconds = float(value)
            except ValueError:
                try:
                    date = parsedate_to_datetime(value)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    seconds = (date - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    seconds = 0
            if math.isfinite(seconds):
                delay = max(delay, seconds)
        return max(0, delay)

    async def _request(self, url: str, base_url: str, kind: str = 'page',
                       max_bytes: Optional[int] = None, retry_count: int = 0):
        """Fetch bounded bytes; validate every redirect before sending it."""
        if self.session is None:
            return self._failure(url, 'Crawler must be used as an async context manager')
        requested_url = url
        current = url
        chain = []
        redirects_seen = set()
        started = time.monotonic()
        network_seconds = 0.0
        limit = max_bytes if max_bytes is not None else self.max_content_length
        while True:
            if not self._valid_url(current, base_url, page=(kind == 'page'),
                                   apply_filters=(kind != 'robots')):
                return self._failure(requested_url, 'URL is invalid, excluded, or outside crawl scope',
                                     blocked_url=current, redirect_chain=chain,
                                     outcome='skipped', skipped=True)
            normalized = self.normalize_url(current)
            if normalized in redirects_seen:
                return self._failure(requested_url, 'Redirect loop', redirect_chain=chain)
            redirects_seen.add(normalized)
            if kind != 'robots' and not await self.check_robots_txt(current):
                return self._failure(requested_url, 'Blocked by robots.txt',
                                     blocked_url=current, redirect_chain=chain,
                                     outcome='skipped', skipped=True)
            origin = self._origin(current)
            response_data = None
            for attempt in range(retry_count, self.retry_attempts + 1):
                await self.rate_limiter.wait(origin)
                request_started = time.monotonic()
                try:
                    self.stats.requests_made += 1
                    async with self.session.get(current, allow_redirects=False,
                                                ssl=self.verify_ssl, proxy=self.proxy) as response:
                        headers_seconds = time.monotonic() - request_started
                        content, truncated = await self._read_bounded(response, limit)
                        request_seconds = time.monotonic() - request_started
                        network_seconds += request_seconds
                        status = response.status
                        response_data = {
                            'url': str(response.url), 'requested_url': requested_url,
                            'status_code': status, 'headers': self._response_headers(response.headers),
                            'content_type': response.headers.get('Content-Type', '').lower(),
                            'content': content, 'content_length': len(content),
                            'truncated': truncated, 'redirect_chain': list(chain),
                            'load_time': network_seconds, 'timestamp': time.time(),
                            'timings': {'headers_seconds': headers_seconds,
                                        'download_seconds': request_seconds - headers_seconds,
                                        'network_seconds': network_seconds,
                                        'total_seconds': time.monotonic() - started},
                            'outcome': 'success',
                        }
                        retry_after = response.headers.get('Retry-After')
                        location = response.headers.get('Location')
                    self.rate_limiter.record_response(origin, request_seconds, status >= 400)
                    if status == 429:
                        self.stats.rate_limit_hits += 1
                    if status >= 400:
                        self.stats.errors_encountered += 1
                        if retry_after:
                            self.rate_limiter.defer(origin, self._retry_after(retry_after, attempt))
                    if status in self.retry_on_status and attempt < self.retry_attempts:
                        self.rate_limiter.defer(origin, self._retry_after(retry_after, attempt))
                        continue
                    if status >= 400:
                        response_data.update(error=f'HTTP {status}', outcome='failed')
                    break
                except asyncio.CancelledError:
                    raise
                except (asyncio.TimeoutError, ClientError, OSError, ValueError) as exc:
                    network_seconds += time.monotonic() - request_started
                    self.stats.errors_encountered += 1
                    self.rate_limiter.record_response(origin, 0, True)
                    certificate_error = isinstance(exc, (aiohttp.ClientConnectorCertificateError,
                                                         aiohttp.ClientConnectorSSLError))
                    if attempt < self.retry_attempts and not certificate_error and not isinstance(exc, ValueError):
                        self.rate_limiter.defer(origin, self._retry_after(None, attempt))
                        continue
                    message = 'Timeout' if isinstance(exc, asyncio.TimeoutError) else str(exc)
                    return self._failure(
                        requested_url, message, redirect_chain=chain,
                        timings={'headers_seconds': None, 'download_seconds': None,
                                 'network_seconds': network_seconds,
                                 'total_seconds': time.monotonic() - started},
                    )
            if response_data is None:
                return self._failure(requested_url, 'Retry budget exhausted', redirect_chain=chain)
            status = response_data['status_code']
            if status in (301, 302, 303, 307, 308) and location:
                if not self.follow_redirects:
                    response_data.update(error='Redirect not followed', outcome='skipped', skipped=True)
                    return response_data
                if len(chain) >= self.max_redirects:
                    response_data.update(error='Maximum redirects exceeded', outcome='failed')
                    return response_data
                target = resolve_url(location, response_data['url'])
                if target is None:
                    response_data.update(error='Invalid redirect Location', outcome='failed')
                    return response_data
                chain.append({'url': response_data['url'], 'status_code': status, 'location': target})
                self.stats.redirects_followed += 1
                current = target
                continue
            response_data['redirected_from'] = requested_url if chain else None
            if response_data['truncated']:
                response_data.update(error='Response exceeds max_page_size', outcome='failed')
                self.limit_reasons.add('max_page_size')
            return response_data

    async def _get_robots(self, url: str):
        origin = self._origin(url)
        robots_url = origin + '/robots.txt'
        async with self._robots_locks[origin]:
            cached = self.robots_cache.get(robots_url)
            if cached and cached[1] > time.monotonic():
                return cached[0]
            response = await self._request(robots_url, self._base_url or url, kind='robots',
                                           max_bytes=min(self.max_content_length, 512000))
            rp = RobotFileParser()
            status = response['status_code']
            if status == 200 and not response.get('error'):
                rp.parse(response['content'].decode('utf-8-sig', errors='replace').splitlines())
            elif (status in (401, 403, 429) or 300 <= status < 400 or status >= 500
                  or status == 0 or response.get('truncated')):
                rp.disallow_all = True
            else:
                rp.allow_all = True
            self._robots_sitemaps[origin] = rp.site_maps() or []
            delay = rp.crawl_delay(self.user_agent)
            if delay is not None:
                self.rate_limiter.set_minimum_delay(origin, delay * self.crawl_delay_factor)
            rate = rp.request_rate(self.user_agent)
            if rate and rate.requests:
                self.rate_limiter.set_minimum_delay(origin, rate.seconds / rate.requests)
            self.robots_cache[robots_url] = (rp, time.monotonic() + self.robots_cache_ttl)
            return rp

    async def check_robots_txt(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        rp = await self._get_robots(url)
        allowed = rp.can_fetch(self.user_agent, url)
        if not allowed:
            self.stats.robots_blocked += 1
        return allowed

    async def fetch_page(self, url: str, retry_count: int = 0) -> Optional[FetchResult]:
        base_url = self._base_url or url
        if not self._valid_url(url, base_url):
            result = self._failure(url, 'URL is invalid, excluded, or outside crawl scope',
                                   outcome='skipped', skipped=True)
            self.failed_urls[str(url)] = result['error']
            return normalize_fetch_result(result, '$.fetch')
        normalized = self.normalize_url(url)
        if normalized in self.visited_urls:
            return None
        self.visited_urls.add(normalized)
        try:
            operation = self._request(url, base_url, retry_count=max(0, retry_count))
            if self._deadline is None:
                result = await asyncio.wait_for(operation, self.max_crawl_time)
            else:
                result = await operation
        except asyncio.TimeoutError:
            result = self._failure(url, 'Crawl time limit exceeded')
            self.limit_reasons.add('max_crawl_time')
        except asyncio.CancelledError:
            raise
        content = result.pop('content', b'')
        content_type = result.get('content_type', '')
        if not result.get('error'):
            if not any(kind in content_type for kind in ('text/html', 'application/xhtml+xml')):
                result.update(error=f'Non-HTML content: {content_type or "unspecified"}',
                              outcome='skipped', skipped=True)
            else:
                charset = re.search(r'charset\s*=\s*["\']?([^;\s"\']+)', content_type, re.I)
                encodings = [charset.group(1)] if charset else None
                decoded = UnicodeDammit(content, encodings, is_html=True)
                html = decoded.unicode_markup or ''
                try:
                    soup = BeautifulSoup(html, PARSER)
                except FeatureNotFound:
                    soup = BeautifulSoup(html, 'html.parser')
                result.update(soup=soup, encoding=decoded.original_encoding or 'utf-8',
                              needs_javascript=any(indicator in html for indicator in
                                                   ('window.location', 'document.write', 'React',
                                                    'Angular', 'Vue', '__NEXT_DATA__', '_app.js')))
                if self.store_html:
                    result['html'] = html
        if result.get('error'):
            self.failed_urls[normalized] = result['error']
        return normalize_fetch_result(result, '$.fetch')

    def _randomize_user_agent(self) -> str:
        """Compatibility shim: request identity remains stable for robots rules."""
        return self.user_agent

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[str, int]]:
        document_base = soup.find('base', href=True)
        resolved_base = (resolve_url(document_base['href'], base_url)
                         if document_base else None) or base_url
        links = []
        seen = set()
        for tag in soup.find_all(['a', 'link'], href=True):
            href = tag.get('href')
            if not isinstance(href, str) or not href:
                continue
            absolute_url = resolve_url(href, resolved_base)
            if not self.is_valid_url(absolute_url, base_url):
                continue
            normalized = self.normalize_url(absolute_url)
            if normalized in seen:
                continue
            seen.add(normalized)
            lowered = href.lower()
            priority = 5
            if any(word in lowered for word in ('index', 'home', 'main')):
                priority = 1
            elif any(word in lowered for word in ('product', 'service', 'about')):
                priority = 2
            elif any(word in lowered for word in ('contact', 'blog', 'news')):
                priority = 3
            elif any(word in lowered for word in ('privacy', 'terms', 'legal')):
                priority = 8
            if re.search(r'[?&]page=\d+', href):
                priority = 9
            links.append((normalized, priority))
        return links

    @staticmethod
    def _frontier_limit(max_pages):
        return min(100000, max_pages * 10)

    def _enqueue(self, url, priority=5, depth=0, parent_url=None):
        normalized = self.normalize_url(url)
        if normalized in self.visited_urls or self.url_queue.has_url(normalized):
            return
        if not self.url_queue.add(normalized, priority, depth):
            self.limit_reasons.add('frontier')
        elif parent_url is not None:
            self._parents[normalized] = parent_url

    async def _run_queue(self, max_pages, follow_links):
        initial_count = len(self.results)
        active = {}
        try:
            while self.url_queue or active:
                while (self.url_queue and len(active) < self.max_concurrent and
                       len(self.results) - initial_count + len(active) < max_pages):
                    # Finish a breadth level before starting the next. Otherwise
                    # a slow shallow route can arrive after a deeper duplicate.
                    if active and self.url_queue.queue[0][0] > min(depth for _, depth in active.values()):
                        break
                    _, depth, url = self.url_queue.get()
                    if depth > self.max_depth:
                        continue
                    task = asyncio.create_task(self.fetch_page(url))
                    active[task] = (url, depth)
                if not active:
                    break
                done, _ = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    url, depth = active.pop(task)
                    try:
                        result = task.result()
                    except Exception as exc:
                        result = self._failure(url, str(exc))
                        self.failed_urls[url] = result['error']
                    if result is None:
                        continue
                    result['depth'] = depth
                    if url in self._parents:
                        result['parent_url'] = self._parents[url]
                    if (follow_links and not result.get('error') and
                            result.get('status_code') == 200 and 'soup' in result):
                        links = self.extract_links(result['soup'], result['url'])
                        if depth < self.max_depth:
                            for link, priority in links:
                                self._enqueue(link, priority, depth + 1, parent_url=result['url'])
                        elif any(link not in self.visited_urls and not self.url_queue.has_url(link)
                                 for link, _ in links):
                            self.limit_reasons.add('max_depth')
                    # Consumers may release soup/html as soon as this is visible.
                    self.results.append(result)
                if len(self.results) - initial_count >= max_pages:
                    if self.url_queue:
                        self.limit_reasons.add('max_pages')
                    break
        finally:
            for task in active:
                task.cancel()
            if active:
                await asyncio.gather(*active, return_exceptions=True)
                if self._interrupted_fetches is not None:
                    # wait_for can cancel before a separately sampled clock reaches
                    # its deadline. The caller decides whether this was a timeout.
                    self._interrupted_fetches.extend(
                        (url, depth, self._parents.get(url)) for url, depth in active.values())
        return self.results

    async def _run_with_deadline(self, operation, seed):
        previous = self._deadline
        previous_interrupted = self._interrupted_fetches
        interrupted = []
        self._interrupted_fetches = interrupted
        self._deadline = time.monotonic() + self.max_crawl_time
        initial_count = len(self.results)
        try:
            return await asyncio.wait_for(operation, self.max_crawl_time)
        except asyncio.TimeoutError:
            self.limit_reasons.add('max_crawl_time')
            for url, depth, parent_url in interrupted:
                result = self._failure(url, 'Crawl time limit exceeded', depth=depth)
                if parent_url is not None:
                    result['parent_url'] = parent_url
                self.failed_urls[url] = result['error']
                self.results.append(result)
            if len(self.results) == initial_count:
                result = self._failure(seed, 'Crawl time limit exceeded')
                self.failed_urls[seed] = result['error']
                self.results.append(result)
            return self.results
        finally:
            self._deadline = previous
            self._interrupted_fetches = previous_interrupted

    async def crawl_site(self, start_url: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        limit = self.max_pages if max_pages is None else max_pages
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError('max_pages must be a positive integer')
        if not self._valid_url(start_url, start_url):
            result = self._failure(start_url, 'URL is invalid, excluded, or outside crawl scope',
                                   outcome='skipped', skipped=True)
            self.failed_urls[str(start_url)] = result['error']
            self.results.append(result)
            return self.results
        previous_base = self._base_url
        self._base_url = start_url
        self.url_queue = URLQueue(self._frontier_limit(limit))
        self._parents = {}
        self._enqueue(start_url, 0, 0)

        async def crawl():
            if self.follow_sitemap and self.discover_sitemaps and limit > 1 and self.max_depth > 0:
                for url in await self.discover_sitemap_urls(start_url, limit - 1):
                    self._enqueue(url, 1, 1)
            return await self._run_queue(limit, follow_links=True)
        try:
            return await self._run_with_deadline(crawl(), start_url)
        finally:
            self._base_url = previous_base

    def _discovery_error(self, url, error):
        if len(self.discovery_errors) < 100:
            self.discovery_errors.append({'url': url, 'error': str(error)})
        logger.debug('Sitemap discovery failed for %s: %s', url, error)

    async def _parse_sitemaps(self, candidates, base_url, max_urls, speculative_urls=()):
        urls = []
        found = set()
        visited = set()
        queued = set()
        queue = deque()
        sitemap_budget = max(16, min(1000, max_urls))
        speculative = {self.normalize_url(url) for url in speculative_urls}

        def enqueue(url, depth):
            normalized = self.normalize_url(url)
            if normalized in queued:
                return
            if depth > 10 or len(queued) >= sitemap_budget:
                self.limit_reasons.add('sitemap_discovery')
                return
            if not self._valid_url(url, base_url, page=False):
                self._discovery_error(url, 'Sitemap is invalid, excluded, or outside crawl scope')
                return
            queued.add(normalized)
            queue.append((url, depth))

        for url in candidates:
            enqueue(url, 0)
        while queue and len(urls) < max_urls:
            url, depth = queue.popleft()
            normalized = self.normalize_url(url)
            if normalized in visited:
                continue
            visited.add(normalized)
            result = await self._request(url, base_url, kind='sitemap')
            if result.get('error') or result['status_code'] != 200:
                # Missing guessed locations are ordinary absence, not failed
                # declared sitemap coverage.
                if normalized in speculative and result['status_code'] in (404, 410):
                    continue
                self._discovery_error(url, result.get('error', f'HTTP {result["status_code"]}'))
                continue
            try:
                parser = ElementTree.XMLParser(target=_SitemapTreeBuilder())
                root = ElementTree.fromstring(result['content'], parser=parser)
            except (ElementTree.ParseError, ValueError) as exc:
                self._discovery_error(url, exc)
                continue
            root_name = root.tag.rsplit('}', 1)[-1]
            if root_name not in ('urlset', 'sitemapindex'):
                self._discovery_error(url, 'Expected urlset or sitemapindex root')
                continue
            entry_name = 'sitemap' if root_name == 'sitemapindex' else 'url'
            for entry in root:
                if entry.tag.rsplit('}', 1)[-1] != entry_name:
                    continue
                loc = next((child.text for child in entry
                            if child.tag.rsplit('}', 1)[-1] == 'loc'), None)
                if not loc:
                    continue
                target = resolve_url(loc, result['url'])
                if target is None:
                    self._discovery_error(loc, 'Invalid sitemap location')
                    continue
                if entry_name == 'sitemap':
                    speculative.discard(self.normalize_url(target))
                    enqueue(target, depth + 1)
                elif self._valid_url(target, base_url):
                    identity = self.normalize_url(target)
                    if identity not in found:
                        if len(urls) >= max_urls:
                            self.limit_reasons.add('max_pages')
                            return urls
                        found.add(identity)
                        urls.append(identity)
                else:
                    self._discovery_error(target, 'Page is invalid, excluded, or outside crawl scope')
        if queue and len(urls) >= max_urls:
            self.limit_reasons.add('max_pages')
        return urls

    async def _bounded_discovery(self, operation, url):
        remaining = (max(0, self._deadline - time.monotonic())
                     if self._deadline is not None else self.max_crawl_time)
        try:
            return await asyncio.wait_for(operation, remaining)
        except asyncio.TimeoutError:
            self.limit_reasons.add('max_crawl_time')
            self._discovery_error(url, 'Crawl time limit exceeded during sitemap discovery')
            return []

    async def discover_sitemap_urls(self, base_url: str, max_urls: Optional[int] = None) -> List[str]:
        """Return eligible page URLs, sharing a bounded sitemap discovery budget."""
        limit = self.max_pages if max_urls is None else max_urls
        if limit <= 0 or not self.follow_sitemap or not self.discover_sitemaps:
            return []
        if not self._valid_url(base_url, base_url, page=False):
            self._discovery_error(base_url, 'Invalid or out-of-scope base URL')
            return []

        async def discover():
            origin = self._origin(base_url)
            await self._get_robots(base_url)
            candidates = list(self._robots_sitemaps.get(origin, []))
            defaults = [origin + path for path in
                        ('/sitemap.xml', '/sitemap_index.xml', '/sitemap-index.xml', '/sitemaps/sitemap.xml')]
            speculative = [url for url in defaults if url not in candidates]
            candidates.extend(defaults)
            return await self._parse_sitemaps(candidates, base_url, limit, speculative)
        return await self._bounded_discovery(discover(), base_url)

    async def parse_sitemap(self, sitemap_url: str, max_urls: Optional[int] = None) -> List[str]:
        """Parse a sitemap/index without optional XML dependencies or recursive requests."""
        limit = self.max_pages if max_urls is None else max_urls
        if limit <= 0:
            return []
        return await self._bounded_discovery(
            self._parse_sitemaps([sitemap_url], self._base_url or sitemap_url, limit), sitemap_url)

    async def _discover_sitemaps(self, base_url: str) -> List[str]:
        return await self.discover_sitemap_urls(base_url)

    async def _parse_sitemap(self, sitemap_url: str) -> List[str]:
        return await self.parse_sitemap(sitemap_url)

    async def crawl_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        self.url_queue = URLQueue(self._frontier_limit(self.max_pages))
        self._parents = {}
        for url in urls:
            # Keep malformed user seeds intact so fetch_page records their error.
            identity = self.normalize_url(url) if self._valid_url(url, self._base_url or url) else url
            if identity not in self.visited_urls:
                self.url_queue.add(identity, depth=0)
            if len(self.url_queue) >= self.max_pages:
                break
        return await self._run_with_deadline(self._run_queue(self.max_pages, follow_links=False),
                                             urls[0] if urls else '')

    async def crawl_sitemap(self, sitemap_url: str) -> List[Dict[str, Any]]:
        previous_base = self._base_url
        self._base_url = sitemap_url

        async def crawl():
            urls = await self.parse_sitemap(sitemap_url)
            self.url_queue = URLQueue(self._frontier_limit(self.max_pages))
            self._parents = {}
            for url in urls:
                self._enqueue(url, depth=0)
            return await self._run_queue(self.max_pages, follow_links=False)
        try:
            return await self._run_with_deadline(crawl(), sitemap_url)
        finally:
            self._base_url = previous_base

    def get_statistics(self) -> Dict[str, Any]:
        successful = [r for r in self.results if 200 <= r.get('status_code', 0) < 400 and not r.get('error')]
        failed = [r for r in self.results if r.get('error') or r.get('status_code', 0) >= 400]
        load_time = sum(r.get('load_time', 0) for r in successful)
        distribution = defaultdict(int)
        for result in self.results:
            distribution[result.get('status_code', 0)] += 1
        stats = self.stats.get_summary()
        return {
            'total_pages': len(self.results), 'successful_pages': len(successful),
            'failed_pages': len(failed),
            'redirected_pages': sum(bool(r.get('redirect_chain')) for r in self.results),
            'unique_urls': len(self.visited_urls),
            'average_load_time': load_time / len(successful) if successful else 0,
            'total_load_time': load_time,
            'pages_per_second': len(successful) / stats['elapsed_seconds'] if stats['elapsed_seconds'] else 0,
            'status_distribution': dict(distribution),
            'failed_urls': dict(list(self.failed_urls.items())[:10]), 'stats': stats,
            'queue_remaining': len(self.url_queue),
            'javascript_pages': sum(bool(r.get('needs_javascript')) for r in self.results),
            'limits_reached': sorted(self.limit_reasons),
            'discovery_errors': self.discovery_errors,
        }


Crawler = EnhancedCrawler
