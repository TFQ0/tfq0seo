"""Advanced technical SEO analyzer with comprehensive security, performance, and crawlability analysis."""

import re
import ipaddress
from typing import Dict, List, Any, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs, unquote
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, Comment


class SecurityLevel(Enum):
    """Security implementation levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    CRITICAL = "critical"


class CrawlabilityStatus(Enum):
    """Page crawlability status."""
    FULLY_CRAWLABLE = "fully_crawlable"
    PARTIALLY_BLOCKED = "partially_blocked"
    BLOCKED = "blocked"
    CONDITIONAL = "conditional"


class MobileReadiness(Enum):
    """Mobile optimization levels."""
    OPTIMIZED = "optimized"
    RESPONSIVE = "responsive"
    ADAPTIVE = "adaptive"
    DESKTOP_ONLY = "desktop_only"
    BROKEN = "broken"


class ProtocolVersion(Enum):
    """HTTP protocol versions."""
    HTTP_1_0 = "HTTP/1.0"
    HTTP_1_1 = "HTTP/1.1"
    HTTP_2 = "HTTP/2"
    HTTP_3 = "HTTP/3"
    UNKNOWN = "Unknown"


@dataclass
class SecurityProfile:
    """Comprehensive security analysis."""
    https_enabled: bool = False
    ssl_version: Optional[str] = None
    hsts_enabled: bool = False
    hsts_max_age: int = 0
    hsts_includesubdomains: bool = False
    hsts_preload: bool = False
    csp_enabled: bool = False
    csp_policy: Optional[str] = None
    xfo_enabled: bool = False
    xfo_policy: Optional[str] = None
    x_content_type_options: bool = False
    x_xss_protection: bool = False
    referrer_policy: Optional[str] = None
    permissions_policy: Optional[str] = None
    cors_headers: Dict[str, str] = field(default_factory=dict)
    security_level: SecurityLevel = SecurityLevel.POOR
    vulnerabilities: List[str] = field(default_factory=list)


@dataclass
class CrawlabilityProfile:
    """Crawlability and indexability analysis."""
    status: CrawlabilityStatus = CrawlabilityStatus.FULLY_CRAWLABLE
    robots_meta: Optional[str] = None
    x_robots_tag: Optional[str] = None
    canonical_url: Optional[str] = None
    noindex: bool = False
    nofollow: bool = False
    noarchive: bool = False
    nosnippet: bool = False
    max_snippet: Optional[int] = None
    max_image_preview: Optional[str] = None
    unavailable_after: Optional[str] = None
    crawl_delay: Optional[float] = None
    blocked_resources: List[str] = field(default_factory=list)
    javascript_required: bool = False
    ajax_crawlable: bool = False


@dataclass
class MobileProfile:
    """Mobile optimization analysis."""
    viewport_configured: bool = False
    viewport_content: Optional[str] = None
    mobile_readiness: MobileReadiness = MobileReadiness.DESKTOP_ONLY
    responsive_images: int = 0
    total_images: int = 0
    touch_elements_size: bool = True
    text_readability: bool = True
    horizontal_scrolling: bool = False
    uses_plugins: bool = False
    amp_version: Optional[str] = None
    pwa_ready: bool = False
    app_links: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceProfile:
    """Technical performance indicators."""
    protocol_version: ProtocolVersion = ProtocolVersion.UNKNOWN
    compression_enabled: bool = False
    compression_type: Optional[str] = None
    compression_ratio: float = 0.0
    cache_control: Optional[str] = None
    cache_ttl: int = 0
    etag_present: bool = False
    last_modified: Optional[str] = None
    cdn_detected: bool = False
    cdn_provider: Optional[str] = None
    server_push_enabled: bool = False
    early_hints: bool = False
    connection_reuse: bool = False
    keep_alive_timeout: int = 0


@dataclass
class URLProfile:
    """URL structure and optimization."""
    length: int = 0
    depth: int = 0
    parameters_count: int = 0
    has_tracking_params: bool = False
    has_session_id: bool = False
    is_clean: bool = True
    is_seo_friendly: bool = True
    uses_underscores: bool = False
    uses_uppercase: bool = False
    has_file_extension: bool = False
    trailing_slash: bool = False
    special_characters: List[str] = field(default_factory=list)


@dataclass
class InternationalProfile:
    """International and localization settings."""
    language_declared: bool = False
    language_code: Optional[str] = None
    hreflang_configured: bool = False
    hreflang_tags: Dict[str, str] = field(default_factory=dict)
    geo_targeting: Optional[str] = None
    charset: Optional[str] = None
    locale_adaptive: bool = False
    rtl_support: bool = False


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create an enhanced technical issue with detailed recommendations."""
    issue = {
        'category': category,
        'severity': severity,
        'message': message
    }
    if details:
        issue['details'] = details
    
    # Add specific technical recommendations
    if 'security' in message.lower() or 'https' in message.lower():
        issue['fix'] = "Implement security headers: HSTS, CSP, X-Frame-Options. Use HTTPS everywhere with modern TLS."
        issue['impact'] = "Critical - Security issues affect trust, rankings, and user safety"
    elif 'cache' in message.lower():
        issue['fix'] = "Configure Cache-Control headers, use CDN, implement browser and edge caching strategies"
        issue['impact'] = "High - Caching improves performance and reduces server load"
    elif 'mobile' in message.lower() or 'viewport' in message.lower():
        issue['fix'] = "Add viewport meta tag, use responsive design, optimize for touch interfaces"
        issue['impact'] = "Critical - Mobile-first indexing requires mobile optimization"
    elif 'compression' in message.lower():
        issue['fix'] = "Enable Gzip or Brotli compression for text resources"
        issue['impact'] = "High - Compression reduces bandwidth by 70-90%"
    elif 'protocol' in message.lower() or 'http/2' in message.lower():
        issue['fix'] = "Upgrade to HTTP/2 or HTTP/3 for multiplexing and better performance"
        issue['impact'] = "Medium - Modern protocols improve loading speed"
    elif 'url' in message.lower():
        issue['fix'] = "Use clean, descriptive URLs without parameters. Implement URL rewriting."
        issue['impact'] = "Medium - Clean URLs improve UX and SEO"
    else:
        issue['fix'] = "Review technical SEO best practices for this issue"
        issue['impact'] = "Varies based on implementation"
    
    return issue


def analyze_security_headers(headers: Dict[str, str]) -> SecurityProfile:
    """Comprehensive security header analysis."""
    profile = SecurityProfile()
    headers_lower = {k.lower(): v for k, v in headers.items()} if headers else {}
    
    # HSTS Analysis
    hsts = headers_lower.get('strict-transport-security', '')
    if hsts:
        profile.hsts_enabled = True
        
        # Parse max-age
        max_age_match = re.search(r'max-age=(\d+)', hsts)
        if max_age_match:
            profile.hsts_max_age = int(max_age_match.group(1))
        
        profile.hsts_includesubdomains = 'includesubdomains' in hsts.lower()
        profile.hsts_preload = 'preload' in hsts.lower()
        
        # Check for recommended values
        if profile.hsts_max_age < 31536000:  # Less than 1 year
            profile.vulnerabilities.append("HSTS max-age less than recommended 1 year")
    
    # CSP Analysis
    csp = headers_lower.get('content-security-policy', '')
    if csp:
        profile.csp_enabled = True
        profile.csp_policy = csp
        
        # Check for unsafe directives
        if 'unsafe-inline' in csp:
            profile.vulnerabilities.append("CSP allows unsafe-inline scripts")
        if 'unsafe-eval' in csp:
            profile.vulnerabilities.append("CSP allows unsafe-eval")
        if '*' in csp and 'default-src' in csp:
            profile.vulnerabilities.append("CSP default-src allows all origins")
    
    # X-Frame-Options
    xfo = headers_lower.get('x-frame-options', '')
    if xfo:
        profile.xfo_enabled = True
        profile.xfo_policy = xfo.upper()
        
        if xfo.upper() not in ['DENY', 'SAMEORIGIN']:
            profile.vulnerabilities.append(f"Invalid X-Frame-Options value: {xfo}")
    
    # Other security headers
    profile.x_content_type_options = 'x-content-type-options' in headers_lower
    profile.x_xss_protection = 'x-xss-protection' in headers_lower
    profile.referrer_policy = headers_lower.get('referrer-policy')
    profile.permissions_policy = headers_lower.get('permissions-policy') or headers_lower.get('feature-policy')
    
    # CORS headers
    cors_headers = ['access-control-allow-origin', 'access-control-allow-methods', 
                   'access-control-allow-headers', 'access-control-allow-credentials']
    for header in cors_headers:
        if header in headers_lower:
            profile.cors_headers[header] = headers_lower[header]
    
    # Check for wildcard CORS
    if profile.cors_headers.get('access-control-allow-origin') == '*':
        profile.vulnerabilities.append("CORS allows all origins (wildcard)")
    
    # Calculate security level
    security_score = 0
    if profile.hsts_enabled:
        security_score += 20
        if profile.hsts_max_age >= 31536000:
            security_score += 10
    if profile.csp_enabled:
        security_score += 20
        if 'unsafe' not in (profile.csp_policy or ''):
            security_score += 10
    if profile.xfo_enabled:
        security_score += 15
    if profile.x_content_type_options:
        security_score += 10
    if profile.referrer_policy:
        security_score += 10
    if profile.permissions_policy:
        security_score += 15
    
    if security_score >= 80:
        profile.security_level = SecurityLevel.EXCELLENT
    elif security_score >= 60:
        profile.security_level = SecurityLevel.GOOD
    elif security_score >= 40:
        profile.security_level = SecurityLevel.MODERATE
    elif security_score >= 20:
        profile.security_level = SecurityLevel.POOR
    else:
        profile.security_level = SecurityLevel.CRITICAL
    
    return profile


def analyze_crawlability(soup: BeautifulSoup, headers: Dict[str, str] = None) -> CrawlabilityProfile:
    """Analyze crawlability and indexability factors."""
    profile = CrawlabilityProfile()
    headers_lower = {k.lower(): v for k, v in headers.items()} if headers else {}
    
    # Check robots meta tag
    robots_meta = soup.find('meta', attrs={'name': 'robots'})
    if robots_meta:
        profile.robots_meta = robots_meta.get('content', '').lower()
        
        # Parse directives
        if 'noindex' in profile.robots_meta:
            profile.noindex = True
            profile.status = CrawlabilityStatus.BLOCKED
        if 'nofollow' in profile.robots_meta:
            profile.nofollow = True
        if 'noarchive' in profile.robots_meta:
            profile.noarchive = True
        if 'nosnippet' in profile.robots_meta:
            profile.nosnippet = True
        
        # Parse max-snippet
        max_snippet_match = re.search(r'max-snippet:(-?\d+)', profile.robots_meta)
        if max_snippet_match:
            profile.max_snippet = int(max_snippet_match.group(1))
        
        # Parse max-image-preview
        max_image_match = re.search(r'max-image-preview:(\w+)', profile.robots_meta)
        if max_image_match:
            profile.max_image_preview = max_image_match.group(1)
        
        # Parse unavailable_after
        unavailable_match = re.search(r'unavailable_after:\s*([^,]+)', profile.robots_meta)
        if unavailable_match:
            profile.unavailable_after = unavailable_match.group(1)
    
    # Check X-Robots-Tag header
    x_robots = headers_lower.get('x-robots-tag')
    if x_robots:
        profile.x_robots_tag = x_robots.lower()
        
        if 'noindex' in profile.x_robots_tag:
            profile.noindex = True
            profile.status = CrawlabilityStatus.BLOCKED
        if 'nofollow' in profile.x_robots_tag:
            profile.nofollow = True
    
    # Check canonical URL
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    if canonical:
        profile.canonical_url = canonical.get('href')
    
    # Check for JavaScript dependency
    noscript = soup.find('noscript')
    if noscript:
        # Check if critical content is in noscript
        noscript_text = noscript.get_text(strip=True)
        if len(noscript_text) > 100:  # Substantial content in noscript
            profile.javascript_required = True
            profile.status = CrawlabilityStatus.CONDITIONAL
    
    # Check for AJAX crawlability (deprecated but still check)
    ajax_meta = soup.find('meta', attrs={'name': 'fragment'})
    if ajax_meta and ajax_meta.get('content') == '!':
        profile.ajax_crawlable = True
    
    # Check for blocked resources
    # Look for robots.txt references in comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if 'disallow' in comment.lower() or 'robots.txt' in comment.lower():
            profile.blocked_resources.append(comment[:100])
    
    # Determine final status
    if profile.noindex:
        profile.status = CrawlabilityStatus.BLOCKED
    elif profile.javascript_required or profile.ajax_crawlable:
        profile.status = CrawlabilityStatus.CONDITIONAL
    elif profile.blocked_resources:
        profile.status = CrawlabilityStatus.PARTIALLY_BLOCKED
    else:
        profile.status = CrawlabilityStatus.FULLY_CRAWLABLE
    
    return profile


def analyze_mobile_optimization(soup: BeautifulSoup) -> MobileProfile:
    """Comprehensive mobile optimization analysis."""
    profile = MobileProfile()
    
    # Check viewport
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if viewport:
        profile.viewport_configured = True
        profile.viewport_content = viewport.get('content', '')
        
        # Analyze viewport settings
        viewport_lower = profile.viewport_content.lower()
        
        has_device_width = 'width=device-width' in viewport_lower
        has_initial_scale = 'initial-scale=1' in viewport_lower
        prevents_zoom = 'user-scalable=no' in viewport_lower or 'maximum-scale=1' in viewport_lower
        
        if has_device_width and has_initial_scale and not prevents_zoom:
            profile.mobile_readiness = MobileReadiness.OPTIMIZED
        elif has_device_width:
            profile.mobile_readiness = MobileReadiness.RESPONSIVE
        else:
            profile.mobile_readiness = MobileReadiness.ADAPTIVE
    
    # Check responsive images
    images = soup.find_all('img')
    profile.total_images = len(images)
    
    for img in images:
        # Check for responsive attributes
        if any([
            img.get('srcset'),
            img.get('sizes'),
            'max-width' in img.get('style', ''),
            'width: 100%' in img.get('style', ''),
            any(cls in ' '.join(img.get('class', [])) for cls in ['responsive', 'fluid', 'img-fluid'])
        ]):
            profile.responsive_images += 1
    
    # Check for plugins
    plugins = soup.find_all(['embed', 'object', 'applet'])
    profile.uses_plugins = len(plugins) > 0
    
    # Check for Flash
    for plugin in plugins:
        if 'flash' in str(plugin).lower() or '.swf' in str(plugin):
            profile.uses_plugins = True
            profile.mobile_readiness = MobileReadiness.BROKEN
    
    # Check for AMP
    amp_html = soup.find('html', attrs={'amp': True}) or soup.find('html', attrs={'⚡': True})
    if amp_html:
        profile.amp_version = 'AMP'
    
    amp_link = soup.find('link', attrs={'rel': 'amphtml'})
    if amp_link:
        profile.amp_version = 'AMP Available'
    
    # Check for PWA indicators
    manifest = soup.find('link', attrs={'rel': 'manifest'})
    service_worker = soup.find('script', string=re.compile(r'serviceWorker'))
    
    if manifest and service_worker:
        profile.pwa_ready = True
    
    # Check for app links
    # iOS
    ios_app = soup.find('meta', attrs={'name': 'apple-itunes-app'})
    if ios_app:
        profile.app_links['ios'] = ios_app.get('content', '')
    
    # Android
    android_app = soup.find('link', attrs={'rel': 'alternate', 'href': re.compile(r'android-app://')})
    if android_app:
        profile.app_links['android'] = android_app.get('href', '')
    
    # Check touch icon
    touch_icon = soup.find('link', attrs={'rel': re.compile(r'apple-touch-icon')})
    if touch_icon:
        profile.app_links['touch_icon'] = touch_icon.get('href', '')
    
    # Check for horizontal scrolling indicators
    tables_without_scroll = soup.find_all('table', attrs={'width': re.compile(r'\d{4,}')})
    if tables_without_scroll:
        profile.horizontal_scrolling = True
    
    # Check text size
    small_fonts = soup.find_all(style=re.compile(r'font-size:\s*(\d+)(px|pt)'))
    for element in small_fonts:
        style = element.get('style', '')
        size_match = re.search(r'font-size:\s*(\d+)', style)
        if size_match:
            size = int(size_match.group(1))
            if size < 12:  # Less than 12px is too small for mobile
                profile.text_readability = False
                break
    
    return profile


def analyze_performance_indicators(headers: Dict[str, str] = None, soup: BeautifulSoup = None) -> PerformanceProfile:
    """Analyze technical performance indicators."""
    profile = PerformanceProfile()
    headers_lower = {k.lower(): v for k, v in headers.items()} if headers else {}
    
    # Detect protocol version
    if headers:
        # Check for HTTP/2 indicators
        if ':status' in headers_lower or 'http2-settings' in headers_lower:
            profile.protocol_version = ProtocolVersion.HTTP_2
        # Check for HTTP/3 indicators
        elif 'alt-svc' in headers_lower and 'h3' in headers_lower['alt-svc']:
            profile.protocol_version = ProtocolVersion.HTTP_3
        else:
            # Default to HTTP/1.1 for most cases
            profile.protocol_version = ProtocolVersion.HTTP_1_1
    
    # Check compression
    content_encoding = headers_lower.get('content-encoding', '')
    if content_encoding:
        profile.compression_enabled = True
        profile.compression_type = content_encoding
        
        # Estimate compression ratio based on encoding type
        if 'br' in content_encoding:
            profile.compression_ratio = 0.8  # Brotli typically 20-30% better than gzip
        elif 'gzip' in content_encoding:
            profile.compression_ratio = 0.7  # Gzip typically 70% compression
        elif 'deflate' in content_encoding:
            profile.compression_ratio = 0.65
    
    # Cache analysis
    cache_control = headers_lower.get('cache-control', '')
    if cache_control:
        profile.cache_control = cache_control
        
        # Parse max-age
        max_age_match = re.search(r'max-age=(\d+)', cache_control)
        if max_age_match:
            profile.cache_ttl = int(max_age_match.group(1))
        
        # Check for no-cache/no-store
        if 'no-store' in cache_control or 'no-cache' in cache_control:
            profile.cache_ttl = 0
    
    # Check for ETag
    profile.etag_present = 'etag' in headers_lower
    
    # Check for Last-Modified
    profile.last_modified = headers_lower.get('last-modified')
    
    # CDN detection
    cdn_headers = {
        'cloudflare': ['cf-ray', 'cf-cache-status'],
        'cloudfront': ['x-amz-cf-id', 'x-amz-cf-pop'],
        'akamai': ['x-akamai-transformed', 'x-akamai-request-id'],
        'fastly': ['x-served-by', 'x-fastly-request-id'],
        'maxcdn': ['x-maxcdn-request-id'],
        'keycdn': ['x-keycdn-cache', 'x-keycdn-request-id'],
        'bunny': ['x-bunny-request-id']
    }
    
    for cdn_name, cdn_indicators in cdn_headers.items():
        if any(header in headers_lower for header in cdn_indicators):
            profile.cdn_detected = True
            profile.cdn_provider = cdn_name
            break
    
    # Check for server push (HTTP/2)
    if 'link' in headers_lower and 'rel=preload' in headers_lower['link']:
        if 'nopush' not in headers_lower['link']:
            profile.server_push_enabled = True
    
    # Check for early hints (103 status)
    if headers_lower.get('status') == '103':
        profile.early_hints = True
    
    # Connection settings
    connection = headers_lower.get('connection', '')
    if 'keep-alive' in connection.lower():
        profile.connection_reuse = True
        
        # Parse Keep-Alive timeout
        keep_alive = headers_lower.get('keep-alive', '')
        timeout_match = re.search(r'timeout=(\d+)', keep_alive)
        if timeout_match:
            profile.keep_alive_timeout = int(timeout_match.group(1))
    
    return profile


def analyze_url_structure(url: str) -> URLProfile:
    """Analyze URL structure and SEO-friendliness."""
    profile = URLProfile()
    
    # Basic metrics
    profile.length = len(url)
    
    # Parse URL
    parsed = urlparse(url)
    
    # Calculate depth (number of path segments)
    path_segments = [s for s in parsed.path.split('/') if s]
    profile.depth = len(path_segments)
    
    # Count parameters
    if parsed.query:
        params = parse_qs(parsed.query)
        profile.parameters_count = len(params)
        
        # Check for tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'track'
        }
        if any(param in params for param in tracking_params):
            profile.has_tracking_params = True
        
        # Check for session IDs
        session_patterns = ['sessionid', 'session_id', 'sid', 'phpsessid', 'jsessionid']
        if any(param.lower() in session_patterns for param in params):
            profile.has_session_id = True
            profile.is_clean = False
    
    # Check for underscores
    if '_' in parsed.path:
        profile.uses_underscores = True
        profile.is_seo_friendly = False
    
    # Check for uppercase
    if any(c.isupper() for c in parsed.path):
        profile.uses_uppercase = True
        profile.is_seo_friendly = False
    
    # Check for file extensions
    if re.search(r'\.\w{2,4}$', parsed.path):
        profile.has_file_extension = True
    
    # Check trailing slash
    if parsed.path.endswith('/') and len(parsed.path) > 1:
        profile.trailing_slash = True
    
    # Check for special characters
    special_chars = re.findall(r'[^a-zA-Z0-9\-/._~:?#\[\]@!$&\'()*+,;=]', url)
    if special_chars:
        profile.special_characters = list(set(special_chars))
        profile.is_seo_friendly = False
    
    # Determine if URL is clean
    if (profile.parameters_count == 0 and 
        not profile.uses_underscores and 
        not profile.uses_uppercase and 
        not profile.special_characters):
        profile.is_clean = True
    else:
        profile.is_clean = False
    
    # SEO-friendly check
    if (profile.is_clean and 
        profile.length < 100 and 
        profile.depth < 5 and 
        not profile.has_session_id):
        profile.is_seo_friendly = True
    else:
        profile.is_seo_friendly = False
    
    return profile


def analyze_international_setup(soup: BeautifulSoup, headers: Dict[str, str] = None) -> InternationalProfile:
    """Analyze international and localization configuration."""
    profile = InternationalProfile()
    headers_lower = {k.lower(): v for k, v in headers.items()} if headers else {}
    
    # Check language declaration
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        profile.language_declared = True
        profile.language_code = html_tag.get('lang')
    
    # Check for hreflang tags
    hreflang_links = soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})
    if hreflang_links:
        profile.hreflang_configured = True
        for link in hreflang_links:
            lang = link.get('hreflang')
            href = link.get('href')
            if lang and href:
                profile.hreflang_tags[lang] = href
    
    # Check charset
    charset_meta = soup.find('meta', charset=True)
    if charset_meta:
        profile.charset = charset_meta.get('charset')
    else:
        content_type = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        if content_type:
            content = content_type.get('content', '')
            charset_match = re.search(r'charset=([^;]+)', content)
            if charset_match:
                profile.charset = charset_match.group(1).strip()
    
    # Check for geo-targeting meta tags
    geo_tags = ['geo.region', 'geo.placename', 'geo.position', 'ICBM']
    for tag_name in geo_tags:
        geo_tag = soup.find('meta', attrs={'name': tag_name})
        if geo_tag:
            profile.geo_targeting = f"{tag_name}: {geo_tag.get('content', '')}"
            break
    
    # Check for RTL support
    if html_tag and html_tag.get('dir') == 'rtl':
        profile.rtl_support = True
    
    # Check for locale-adaptive content
    if 'content-language' in headers_lower:
        profile.locale_adaptive = True
    
    # Check for language negotiation
    if 'vary' in headers_lower and 'accept-language' in headers_lower['vary'].lower():
        profile.locale_adaptive = True
    
    return profile


def detect_javascript_seo_issues(soup: BeautifulSoup) -> Dict[str, Any]:
    """Detect JavaScript SEO issues and recommendations."""
    issues = {
        'client_side_rendering': False,
        'spa_detected': False,
        'lazy_loaded_content': False,
        'infinite_scroll': False,
        'ajax_navigation': False,
        'javascript_redirects': False,
        'dynamic_meta_tags': False,
        'recommendations': []
    }
    
    # Check for React/Vue/Angular indicators
    spa_indicators = [
        ('div', {'id': 'root'}),  # React
        ('div', {'id': 'app'}),   # Vue
        ('app-root', {}),          # Angular
        ('div', {'ng-app': True}), # AngularJS
    ]
    
    for tag, attrs in spa_indicators:
        if soup.find(tag, attrs):
            issues['spa_detected'] = True
            issues['client_side_rendering'] = True
            break
    
    # Check for lazy loading indicators
    lazy_indicators = [
        ('img', {'loading': 'lazy'}),
        ('iframe', {'loading': 'lazy'}),
        (None, {'data-src': True}),
        (None, {'data-lazy': True}),
    ]
    
    for tag, attrs in lazy_indicators:
        elements = soup.find_all(tag, attrs) if tag else soup.find_all(attrs=attrs)
        if elements:
            issues['lazy_loaded_content'] = True
            break
    
    # Check for infinite scroll
    infinite_scroll_scripts = soup.find_all('script', string=re.compile(r'(IntersectionObserver|infinite.?scroll|waypoint)', re.I))
    if infinite_scroll_scripts:
        issues['infinite_scroll'] = True
    
    # Check for AJAX navigation
    ajax_nav_patterns = [
        r'history\.pushState',
        r'window\.history\.replaceState',
        r'ajax.*navigation',
        r'pjax'
    ]
    
    for script in soup.find_all('script'):
        if script.string:
            for pattern in ajax_nav_patterns:
                if re.search(pattern, script.string, re.I):
                    issues['ajax_navigation'] = True
                    break
    
    # Check for JavaScript redirects
    js_redirect_patterns = [
        r'window\.location',
        r'location\.href',
        r'location\.replace',
        r'meta.*refresh'
    ]
    
    for script in soup.find_all('script'):
        if script.string:
            for pattern in js_redirect_patterns:
                if re.search(pattern, script.string):
                    issues['javascript_redirects'] = True
                    break
    
    # Generate recommendations
    if issues['spa_detected']:
        issues['recommendations'].append("Use server-side rendering (SSR) or pre-rendering for better SEO")
    
    if issues['infinite_scroll']:
        issues['recommendations'].append("Provide paginated alternatives for infinite scroll content")
    
    if issues['ajax_navigation']:
        issues['recommendations'].append("Ensure all navigation states have unique URLs and are crawlable")
    
    if issues['javascript_redirects']:
        issues['recommendations'].append("Replace JavaScript redirects with server-side 301/302 redirects")
    
    return issues


def analyze_technical(soup: BeautifulSoup, url: str, headers: Dict[str, str] = None, status_code: int = 200) -> Dict[str, Any]:
    """Advanced technical SEO analysis with comprehensive checks."""
    issues = []
    data = {}
    
    # Parse URL
    parsed_url = urlparse(url)
    
    # HTTPS check
    data['https'] = parsed_url.scheme == 'https'
    if not data['https']:
        issues.append(create_issue('Security', 'critical', 'Site not using HTTPS'))
    
    # Status code analysis
    data['status_code'] = status_code
    if status_code >= 500:
        issues.append(create_issue('Availability', 'critical', f'Server error status code {status_code}'))
    elif status_code >= 400:
        issues.append(create_issue('Availability', 'critical', f'Client error status code {status_code}'))
    elif status_code >= 300:
        if status_code == 301:
            issues.append(create_issue('Redirects', 'notice', 'Permanent redirect (301)'))
        elif status_code == 302:
            issues.append(create_issue('Redirects', 'warning', 'Temporary redirect (302) - consider using 301 for SEO'))
        else:
            issues.append(create_issue('Redirects', 'warning', f'Redirect status {status_code}'))
    
    # Security analysis
    security_profile = analyze_security_headers(headers)
    data['security'] = {
        'level': security_profile.security_level.value,
        'https': data['https'],
        'hsts': security_profile.hsts_enabled,
        'hsts_max_age': security_profile.hsts_max_age,
        'csp': security_profile.csp_enabled,
        'xfo': security_profile.xfo_enabled,
        'x_content_type_options': security_profile.x_content_type_options,
        'vulnerabilities': security_profile.vulnerabilities[:5]  # Limit to top 5
    }
    
    # Report security issues
    if not security_profile.hsts_enabled and data['https']:
        issues.append(create_issue('Security', 'warning', 'Missing HSTS header for HTTPS site'))
    
    if security_profile.hsts_enabled and security_profile.hsts_max_age < 31536000:
        issues.append(create_issue('Security', 'notice', 
            f'HSTS max-age too short ({security_profile.hsts_max_age}s), recommend 31536000'))
    
    if not security_profile.csp_enabled:
        issues.append(create_issue('Security', 'warning', 'Missing Content Security Policy'))
    
    if not security_profile.xfo_enabled:
        issues.append(create_issue('Security', 'notice', 'Missing X-Frame-Options header'))
    
    for vulnerability in security_profile.vulnerabilities[:3]:
        issues.append(create_issue('Security', 'warning', vulnerability))
    
    if security_profile.security_level == SecurityLevel.CRITICAL:
        issues.append(create_issue('Security', 'critical', 'Critical security issues detected'))
    
    # Crawlability analysis
    crawl_profile = analyze_crawlability(soup, headers)
    data['crawlability'] = {
        'status': crawl_profile.status.value,
        'noindex': crawl_profile.noindex,
        'nofollow': crawl_profile.nofollow,
        'canonical': crawl_profile.canonical_url,
        'javascript_required': crawl_profile.javascript_required
    }
    
    if crawl_profile.noindex:
        issues.append(create_issue('Crawlability', 'critical', 'Page is set to noindex'))
    
    if crawl_profile.nofollow:
        issues.append(create_issue('Crawlability', 'warning', 'Page is set to nofollow'))
    
    if crawl_profile.javascript_required:
        issues.append(create_issue('Crawlability', 'warning', 'Content requires JavaScript for crawling'))
    
    # Mobile optimization analysis
    mobile_profile = analyze_mobile_optimization(soup)
    data['mobile'] = {
        'readiness': mobile_profile.mobile_readiness.value,
        'viewport_configured': mobile_profile.viewport_configured,
        'responsive_images': f"{mobile_profile.responsive_images}/{mobile_profile.total_images}",
        'amp': mobile_profile.amp_version,
        'pwa_ready': mobile_profile.pwa_ready
    }
    
    if not mobile_profile.viewport_configured:
        issues.append(create_issue('Mobile', 'critical', 'Missing viewport meta tag'))
    elif mobile_profile.viewport_content and 'user-scalable=no' in mobile_profile.viewport_content:
        issues.append(create_issue('Mobile', 'warning', 'Viewport prevents user zooming (accessibility issue)'))
    
    if mobile_profile.uses_plugins:
        issues.append(create_issue('Mobile', 'critical', 'Uses plugins not supported on mobile'))
    
    if mobile_profile.mobile_readiness == MobileReadiness.DESKTOP_ONLY:
        issues.append(create_issue('Mobile', 'critical', 'Site not optimized for mobile'))
    
    if mobile_profile.horizontal_scrolling:
        issues.append(create_issue('Mobile', 'warning', 'Content causes horizontal scrolling on mobile'))
    
    # Performance indicators
    perf_profile = analyze_performance_indicators(headers, soup)
    data['performance'] = {
        'protocol': perf_profile.protocol_version.value,
        'compression': perf_profile.compression_type,
        'cache_ttl': perf_profile.cache_ttl,
        'cdn': perf_profile.cdn_provider or 'None detected',
        'etag': perf_profile.etag_present,
        'server_push': perf_profile.server_push_enabled
    }
    
    if not perf_profile.compression_enabled:
        issues.append(create_issue('Performance', 'warning', 'Content not compressed'))
    
    if perf_profile.cache_ttl == 0:
        issues.append(create_issue('Performance', 'warning', 'No caching configured'))
    elif perf_profile.cache_ttl < 3600:  # Less than 1 hour
        issues.append(create_issue('Performance', 'notice', f'Short cache TTL ({perf_profile.cache_ttl}s)'))
    
    if not perf_profile.cdn_detected:
        issues.append(create_issue('Performance', 'notice', 'No CDN detected'))
    
    if perf_profile.protocol_version in [ProtocolVersion.HTTP_1_0, ProtocolVersion.HTTP_1_1]:
        issues.append(create_issue('Performance', 'notice', 'Not using HTTP/2 or HTTP/3'))
    
    # URL structure analysis
    url_profile = analyze_url_structure(url)
    data['url'] = {
        'length': url_profile.length,
        'depth': url_profile.depth,
        'parameters': url_profile.parameters_count,
        'is_clean': url_profile.is_clean,
        'is_seo_friendly': url_profile.is_seo_friendly
    }
    
    if url_profile.length > 100:
        issues.append(create_issue('URL Structure', 'warning', f'URL too long ({url_profile.length} chars)'))
    
    if url_profile.depth > 4:
        issues.append(create_issue('URL Structure', 'notice', f'Deep URL structure (depth: {url_profile.depth})'))
    
    if url_profile.has_session_id:
        issues.append(create_issue('URL Structure', 'critical', 'Session ID in URL'))
    
    if url_profile.uses_underscores:
        issues.append(create_issue('URL Structure', 'notice', 'URL uses underscores instead of hyphens'))
    
    if url_profile.uses_uppercase:
        issues.append(create_issue('URL Structure', 'warning', 'URL contains uppercase characters'))
    
    if not url_profile.is_seo_friendly:
        issues.append(create_issue('URL Structure', 'warning', 'URL is not SEO-friendly'))
    
    # International setup
    intl_profile = analyze_international_setup(soup, headers)
    data['international'] = {
        'language': intl_profile.language_code,
        'charset': intl_profile.charset,
        'hreflang_count': len(intl_profile.hreflang_tags),
        'geo_targeting': intl_profile.geo_targeting
    }
    
    if not intl_profile.language_declared:
        issues.append(create_issue('International', 'warning', 'Missing language declaration'))
    
    if intl_profile.charset and intl_profile.charset.lower() != 'utf-8':
        issues.append(create_issue('International', 'warning', f'Non-UTF-8 charset: {intl_profile.charset}'))
    
    # JavaScript SEO issues
    js_issues = detect_javascript_seo_issues(soup)
    data['javascript_seo'] = js_issues
    
    if js_issues['spa_detected']:
        issues.append(create_issue('JavaScript SEO', 'warning', 'Single Page Application detected'))
    
    if js_issues['infinite_scroll']:
        issues.append(create_issue('JavaScript SEO', 'notice', 'Infinite scroll detected'))
    
    if js_issues['javascript_redirects']:
        issues.append(create_issue('JavaScript SEO', 'warning', 'JavaScript redirects detected'))
    
    # Mixed content check (for HTTPS sites)
    if data['https']:
        mixed_content = []
        
        # Check various resource types
        resource_tags = [
            ('img', 'src'),
            ('script', 'src'),
            ('link', 'href'),
            ('iframe', 'src'),
            ('source', 'src'),
            ('video', 'src'),
            ('audio', 'src'),
            ('embed', 'src'),
            ('object', 'data')
        ]
        
        for tag_name, attr_name in resource_tags:
            for element in soup.find_all(tag_name):
                resource_url = element.get(attr_name, '')
                if resource_url.startswith('http://'):
                    mixed_content.append({
                        'type': tag_name,
                        'url': resource_url[:100]  # Truncate long URLs
                    })
        
        if mixed_content:
            issues.append(create_issue('Security', 'critical', 
                f'Mixed content: {len(mixed_content)} insecure resources on HTTPS page'))
            data['mixed_content'] = mixed_content[:10]  # Limit to first 10
    
    # Check for deprecated technologies
    deprecated_found = []
    
    # Flash
    if soup.find_all(['embed', 'object'], attrs={'type': 'application/x-shockwave-flash'}):
        deprecated_found.append('Flash')
    
    # Frameset
    if soup.find('frameset'):
        deprecated_found.append('Frameset')
    
    # Font tag
    if soup.find('font'):
        deprecated_found.append('Font tags')
    
    # Center tag
    if soup.find('center'):
        deprecated_found.append('Center tags')
    
    if deprecated_found:
        issues.append(create_issue('Compatibility', 'warning', 
            f'Deprecated technologies: {", ".join(deprecated_found)}'))
    
    # Check DOCTYPE
    doctype = None
    for item in soup.contents:
        if str(item).startswith('<!DOCTYPE'):
            doctype = str(item)
            break
    
    if not doctype:
        issues.append(create_issue('HTML Standards', 'warning', 'Missing DOCTYPE declaration'))
    elif 'html5' not in doctype.lower() and '<!doctype html>' not in doctype.lower():
        issues.append(create_issue('HTML Standards', 'notice', 'Non-HTML5 DOCTYPE'))
    
    # Check for structured data
    json_ld = soup.find_all('script', type='application/ld+json')
    microdata = soup.find_all(attrs={'itemscope': True})
    rdfa = soup.find_all(attrs={'typeof': True})
    
    data['structured_data_types'] = {
        'json_ld': len(json_ld),
        'microdata': len(microdata),
        'rdfa': len(rdfa)
    }
    
    # Calculate technical score
    score = 100
    
    for issue in issues:
        if issue['severity'] == 'critical':
            score -= 15
        elif issue['severity'] == 'warning':
            score -= 7
        elif issue['severity'] == 'notice':
            score -= 3
    
    # Additional scoring based on profiles
    if security_profile.security_level in [SecurityLevel.POOR, SecurityLevel.CRITICAL]:
        score -= 10
    
    if crawl_profile.status == CrawlabilityStatus.BLOCKED:
        score -= 20
    
    if mobile_profile.mobile_readiness in [MobileReadiness.DESKTOP_ONLY, MobileReadiness.BROKEN]:
        score -= 15
    
    if not url_profile.is_seo_friendly:
        score -= 5
    
    score = max(0, min(100, score))
    
    # Generate recommendations
    recommendations = []
    
    if not data['https']:
        recommendations.append("Priority: Migrate to HTTPS immediately for security and SEO")
    
    if security_profile.security_level in [SecurityLevel.POOR, SecurityLevel.CRITICAL]:
        recommendations.append("Priority: Implement security headers (HSTS, CSP, X-Frame-Options)")
    
    if mobile_profile.mobile_readiness == MobileReadiness.DESKTOP_ONLY:
        recommendations.append("Priority: Implement responsive design for mobile-first indexing")
    
    if perf_profile.protocol_version == ProtocolVersion.HTTP_1_1:
        recommendations.append("Upgrade to HTTP/2 or HTTP/3 for better performance")
    
    if not perf_profile.cdn_detected:
        recommendations.append("Consider using a CDN for global performance")
    
    if js_issues['spa_detected']:
        recommendations.append("Implement server-side rendering for SPA SEO")
    
    data['recommendations'] = recommendations
    
    return {
        'score': score,
        'issues': issues,
        'data': data
    }