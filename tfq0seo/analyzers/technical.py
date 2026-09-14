"""Advanced technical SEO analyzer with comprehensive security, performance, and crawlability analysis."""

import re
import ipaddress
import math
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup, Doctype
from .common import (document_base_url, header_values, make_issue, normalized_headers,
                     parse_robots, resolve_url)
from ..rules import RuleDefinition, RuleCollector, register_rules, score_findings, recommendations_for
from ..page_facts import PageFacts, ensure_page_facts


_REVIEWED = '2026-09-14'
_HSTS = 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Strict-Transport-Security'
_CSP = 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy'
_SCRIPT_CSP = _CSP + '/script-src'
_XFO = 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options'
_HTTP_STATUS = 'https://developers.google.com/crawling/docs/troubleshooting/http-status-codes'
_DOCTYPE = 'https://html.spec.whatwg.org/multipage/syntax.html#the-doctype'


# Optional deployment policies and source-code hints are observations, not defects.
TECHNICAL_RULES = register_rules([
    RuleDefinition('technical.http_server_error', 'technical', 'critical',
                   'Investigate the server failure and restore the intended response.',
                   'An observed HTTP response status in the 500-599 range.', (_HTTP_STATUS,), _REVIEWED),
    RuleDefinition('technical.http_client_error', 'technical', 'critical',
                   'Confirm the requested resource should exist or be accessible, then correct its response or incoming links.',
                   'An observed HTTP response status in the 400-499 range.', (_HTTP_STATUS,), _REVIEWED),
    RuleDefinition('technical.http_redirect', 'technical', 'notice',
                   'Confirm the redirect destination and choose permanent or temporary semantics to match the intended change.',
                   'An observed redirect response; permanence and publisher intent are not inferred.',
                   ('https://developers.google.com/search/docs/crawling-indexing/301-redirects',), _REVIEWED, scored=False),
    RuleDefinition('security.hsts_missing', 'technical', 'notice',
                   'Review whether this HTTPS domain should deploy HSTS; check subdomain readiness and existing browser or preload policy first.',
                   'Observed response headers on an HTTPS domain; cached HSTS and preload membership are not checked.',
                   (_HSTS,), _REVIEWED, scored=False),
    RuleDefinition('security.hsts_invalid', 'technical', 'warning',
                   'Provide one valid HSTS policy with a single nonnegative integer max-age and no repeated directives.',
                   'An HSTS header declared by an HTTPS domain.',
                   (_HSTS, 'https://www.rfc-editor.org/rfc/rfc6797.html'), _REVIEWED),
    RuleDefinition('security.hsts_preload_incomplete', 'technical', 'notice',
                   'If preloading is intended, verify all preload requirements, including max-age of at least one year and includeSubDomains.',
                   'An HTTPS domain whose HSTS header explicitly includes preload; submission and subdomain behavior are unobserved.',
                   (_HSTS,), _REVIEWED, scored=False),
    RuleDefinition('security.csp_missing', 'technical', 'notice',
                   'Evaluate a Content Security Policy appropriate to the application and test it before enforcement.',
                   'Observed headers and HTML without an enforcing CSP declaration; a universal policy is not assumed.',
                   (_CSP,), _REVIEWED, scored=False),
    RuleDefinition('security.frame_policy_missing', 'technical', 'notice',
                   'Decide which sites may embed this document and configure frame-ancestors or X-Frame-Options if restrictions are needed.',
                   'Observed document response headers; whether embedding should be restricted is unknown.',
                   (_XFO, _CSP), _REVIEWED, scored=False),
    RuleDefinition('security.csp_unsafe_inline', 'technical', 'notice',
                   'Review the observed inline-script source expression in the context of all enforced CSP policies; consider nonces or hashes where suitable.',
                   'A script source directive contains unsafe-inline without a nonce or hash in that directive; execution and combined policy effects are not tested.',
                   (_SCRIPT_CSP, _CSP), _REVIEWED, scored=False),
    RuleDefinition('security.csp_unsafe_eval', 'technical', 'notice',
                   'Check whether evaluated script strings are needed and remove unsafe-eval from the applicable policy where possible.',
                   'An observed script source directive contains unsafe-eval; exploitability is not inferred.',
                   (_SCRIPT_CSP, _CSP), _REVIEWED, scored=False),
    RuleDefinition('security.csp_wildcard_default', 'technical', 'notice',
                   'Review the wildcard default source against the resources the application needs and its more specific directives.',
                   'An observed CSP default-src directive contains a wildcard; effective resource permissions are not tested.',
                   (_CSP,), _REVIEWED, scored=False),
    RuleDefinition('security.xfo_invalid', 'technical', 'warning',
                   'Use a supported X-Frame-Options value, DENY or SAMEORIGIN, or replace it with an appropriate frame-ancestors policy.',
                   'An observed X-Frame-Options declaration.', (_XFO,), _REVIEWED),
    RuleDefinition('security.cors_wildcard_credentials', 'technical', 'warning',
                   'For intended credentialed cross-origin access, allow a validated explicit origin; otherwise remove the credential permission.',
                   'A response declares both a wildcard Access-Control-Allow-Origin and Access-Control-Allow-Credentials: true.',
                   ('https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors/CORSNotSupportingCredentials',), _REVIEWED),
    RuleDefinition('technical.http_compression', 'technical', 'notice',
                   'Measure response size and transfer savings before enabling a suitable content encoding for compressible responses.',
                   'A body-bearing HTML response has observed headers without a non-identity Content-Encoding; negotiation and savings are unmeasured.',
                   ('https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Encoding',), _REVIEWED, scored=False),
    RuleDefinition('technical.url_session_parameter', 'technical', 'notice',
                   'Verify whether these parameter names carry session state. If they do, consider cookies and stable crawlable URLs without merging distinct content.',
                   'URL query parameter names match common session identifiers; their meaning is not established.',
                   ('https://developers.google.com/search/docs/crawling-indexing/url-structure',), _REVIEWED, scored=False),
    RuleDefinition('technical.javascript_redirect_reference', 'technical', 'notice',
                   'Verify whether this code executes a redirect. If a server redirect matches the intended behavior, prefer it for predictable discovery.',
                   'Inline script text references a location assignment or redirect method; execution and intent are unknown.',
                   ('https://developers.google.com/search/docs/crawling-indexing/301-redirects',), _REVIEWED, scored=False),
    RuleDefinition('technical.http_resource_reference', 'technical', 'notice',
                   'Update applicable resource references to HTTPS and verify the rendered network requests, including browser upgrades and blocks.',
                   'An HTTPS document declares an HTTP subresource URL; an actual insecure network request is not established.',
                   ('https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Mixed_content',), _REVIEWED, scored=False),
    RuleDefinition('technical.deprecated_elements', 'technical', 'notice',
                   'Replace obsolete elements with supported semantic HTML and CSS after checking their intended presentation and behavior.',
                   'Observed obsolete HTML elements; rendered breakage is not inferred.',
                   ('https://html.spec.whatwg.org/multipage/obsolete.html',), _REVIEWED, scored=False),
    RuleDefinition('html.doctype_missing', 'technical', 'warning',
                   'Start HTML documents with <!DOCTYPE html> to request standards mode.',
                   'Documents parsed as HTML syntax; XML/XHTML syntax does not require the HTML doctype.',
                   (_DOCTYPE,), _REVIEWED),
    RuleDefinition('html.doctype_legacy', 'technical', 'notice',
                   'Consider the modern HTML doctype when updating the document, and verify rendering before changing a legacy declaration.',
                   'An observed legacy HTML doctype; quirks mode is not inferred from its age alone.',
                   (_DOCTYPE,), _REVIEWED, scored=False),
])


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
    UNKNOWN = "unknown"


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
    status: CrawlabilityStatus = CrawlabilityStatus.UNKNOWN
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
    javascript_required: Optional[bool] = None
    ajax_crawlable: bool = False
    robots_analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MobileProfile:
    """Mobile optimization analysis."""
    viewport_configured: bool = False
    viewport_content: Optional[str] = None
    mobile_readiness: MobileReadiness = MobileReadiness.DESKTOP_ONLY
    responsive_images: int = 0
    total_images: int = 0
    touch_elements_size: Optional[bool] = None
    text_readability: Optional[bool] = None
    horizontal_scrolling: Optional[bool] = None
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
    compression_ratio: Optional[float] = None
    cache_control: Optional[str] = None
    cache_ttl: Optional[int] = None
    etag_present: bool = False
    last_modified: Optional[str] = None
    cdn_detected: bool = False
    cdn_provider: Optional[str] = None
    server_push_enabled: Optional[bool] = None
    early_hints: Optional[bool] = None
    connection_reuse: Optional[bool] = None
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


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None,
                 rule_id: Optional[str] = None, evidence: Any = None,
                 confidence: str = 'high') -> Dict[str, Any]:
    """Compatibility adapter; rule metadata and advice come only from the registry."""
    return make_issue(category, severity, message, details, rule_id, evidence,
                      confidence=confidence)


def _viewport_values(content: str) -> Dict[str, str]:
    """Read authored viewport key/value pairs without inferring a rendered layout."""
    values = {}
    for part in re.split(r'[,;]', content):
        name, separator, value = part.partition('=')
        if separator:
            values[name.strip().lower()] = value.strip().lower()
    return values


def _viewport_restricts_zoom(values: Dict[str, str]) -> bool:
    if values.get('user-scalable') in ('no', '0'):
        return True
    try:
        maximum = float(values.get('maximum-scale', ''))
    except ValueError:
        return False
    return math.isfinite(maximum) and 0 <= maximum < 2


def _has_nonce_or_hash(tokens: List[str]) -> bool:
    return any(re.fullmatch(r"'(?:nonce|sha256|sha384|sha512)-[A-Za-z0-9+/_-]+={0,2}'", token)
               for token in tokens)


def _csp_policies(headers: Any, soup: Optional[BeautifulSoup] = None, *,
                  facts: Optional[PageFacts] = None) -> List[Dict[str, Any]]:
    """Preserve separate policies; duplicate directives use the first occurrence."""
    declarations = [('response_header', value) for value in header_values(headers, 'Content-Security-Policy')]
    if soup is not None or facts is not None:
        metas = [record['attrs'] for record in facts.meta] if facts is not None else soup.find_all('meta')
        declarations.extend(('meta', str(meta.get('content', ''))) for meta in metas
                            if str(meta.get('http-equiv', '')).strip().lower() == 'content-security-policy')
    policies = []
    for source, declaration in declarations:
        # A combined header may contain several serialized policies. A meta value is one policy.
        for value in declaration.split(',') if source == 'response_header' else [declaration]:
            directives = {}
            for part in value.split(';'):
                words = part.strip().split()
                if words:
                    directives.setdefault(words[0].lower(), words[1:])
            policies.append({'source': source, 'directives': directives})
    return policies


def _hsts_policy(headers: Any) -> Dict[str, Any]:
    values = header_values(headers, 'Strict-Transport-Security')
    directives = {}
    if values:
        # RFC 6797: browsers process only the first STS header field.
        parts, current, quoted, escaped = [], [], False, False
        for character in values[0]:
            if character == ';' and not quoted:
                parts.append(''.join(current))
                current = []
                continue
            current.append(character)
            if escaped:
                escaped = False
            elif quoted and character == '\\':
                escaped = True
            elif character == '"':
                quoted = not quoted
        parts.append(''.join(current))
        for part in parts:
            name, separator, value = part.strip().partition('=')
            if name:
                directives.setdefault(name.strip().lower(), []).append(value.strip() if separator else None)
    ages = directives.get('max-age', [])
    age_text = ages[0] if len(ages) == 1 and ages[0] is not None else ''
    if len(age_text) >= 2 and age_text.startswith('"') and age_text.endswith('"'):
        age_text = re.sub(r'\\(.)', r'\1', age_text[1:-1])
    valid_age = bool(re.fullmatch(r'[0-9]+', age_text))
    duplicate_directives = [name for name, items in directives.items() if len(items) > 1]
    invalid_include = any(value is not None for value in directives.get('includesubdomains', []))
    max_age = None
    if valid_age:
        digits = age_text.lstrip('0') or '0'
        # Retain field text in evidence without reporting a clamped value as a measurement.
        max_age = int(digits) if len(digits) < 19 else None
    meets_preload_duration = valid_age and (len(digits) > 8 or
                                           len(digits) == 8 and digits >= '31536000')
    return {'values': values, 'selected_header': 0 if values else None,
            'max_age': max_age, 'includesubdomains': 'includesubdomains' in directives,
            'meets_preload_duration': meets_preload_duration,
            'preload': 'preload' in directives, 'duplicate_directives': duplicate_directives,
            'validation_scope': 'max-age and includeSubDomains values; duplicate directive names',
            'valid': bool(values) and valid_age and not duplicate_directives and not invalid_include}


def analyze_security_headers(headers: Dict[str, str]) -> SecurityProfile:
    """Describe header configuration; the legacy level is a coverage heuristic."""
    profile = SecurityProfile()
    headers_lower = normalized_headers(headers)
    
    # HSTS Analysis
    hsts = _hsts_policy(headers)
    if hsts['values']:
        profile.hsts_enabled = True
        profile.hsts_max_age = hsts['max_age'] or 0
        profile.hsts_includesubdomains = hsts['includesubdomains']
        profile.hsts_preload = hsts['preload']
        
    
    # CSP Analysis
    csp = headers_lower.get('content-security-policy', '')
    if csp:
        profile.csp_enabled = True
        profile.csp_policy = csp
        
        # Check for unsafe directives
        for policy in _csp_policies(headers):
            policies = policy['directives']
            script_policy = policies.get('script-src', policies.get('default-src', []))
            if "'unsafe-inline'" in script_policy and not _has_nonce_or_hash(script_policy):
                profile.vulnerabilities.append("CSP script directive includes unsafe-inline without a nonce or hash")
            if "'unsafe-eval'" in script_policy:
                profile.vulnerabilities.append("CSP script directive includes unsafe-eval")
            if '*' in policies.get('default-src', []):
                profile.vulnerabilities.append("CSP default-src includes a wildcard")
    
    # X-Frame-Options
    xfo = headers_lower.get('x-frame-options', '')
    if xfo:
        profile.xfo_enabled = True
        profile.xfo_policy = xfo.upper()
        
        if xfo.strip().upper() not in ['DENY', 'SAMEORIGIN']:
            profile.vulnerabilities.append(f"Invalid X-Frame-Options value: {xfo}")
    
    # Other security headers
    profile.x_content_type_options = headers_lower.get('x-content-type-options', '').lower() == 'nosniff'
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
    if (profile.cors_headers.get('access-control-allow-origin') == '*' and
            profile.cors_headers.get('access-control-allow-credentials', '').lower() == 'true'):
        profile.vulnerabilities.append("Wildcard CORS origin cannot authorize credentialed browser requests")
    
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


def analyze_crawlability(soup: BeautifulSoup, headers: Dict[str, str] = None,
                        user_agent: str = 'googlebot', *, facts: Optional[PageFacts] = None) -> CrawlabilityProfile:
    """Analyze crawlability and indexability factors."""
    profile = CrawlabilityProfile()
    robots = facts.robots if facts is not None else parse_robots(soup, headers, user_agent)
    profile.robots_analysis = robots
    for attribute in ('noindex', 'nofollow', 'nosnippet', 'noarchive', 'max_snippet'):
        setattr(profile, attribute, robots[attribute])
    profile.robots_meta = ', '.join(item['value'] for item in robots['evidence'] if item['source'] == 'meta') or None
    profile.x_robots_tag = ', '.join(item['value'] for item in robots['evidence'] if item['source'] == 'header') or None
    
    # Check canonical URL
    canonical = (next((record['attrs'] for record in facts.link_tags
                       if 'canonical' in record['attrs'].get('rel', [])), None)
                 if facts is not None else soup.find('link', attrs={'rel': 'canonical'}))
    if canonical:
        profile.canonical_url = canonical.get('href')
    
    # Check for AJAX crawlability (deprecated but still check)
    ajax_meta = (next((record['attrs'] for record in facts.meta if record['attrs'].get('name') == 'fragment'), None)
                 if facts is not None else soup.find('meta', attrs={'name': 'fragment'}))
    if ajax_meta and ajax_meta.get('content') == '!':
        profile.ajax_crawlable = True
    
    # Robots meta/header directives describe indexing, not robots.txt access.
    # Static markup cannot establish whether a rendering engine needs JavaScript.
    
    return profile


def analyze_mobile_optimization(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> MobileProfile:
    """Describe markup hints; mobile_readiness is a legacy markup heuristic."""
    profile = MobileProfile()
    
    # Check viewport
    metas = [record['attrs'] for record in facts.meta] if facts is not None else soup.find_all('meta')
    links = [record['attrs'] for record in facts.link_tags] if facts is not None else soup.find_all('link')
    viewport = next((meta for meta in metas if re.fullmatch('viewport', str(meta.get('name', '')), re.I)), None)
    if viewport:
        profile.viewport_content = str(viewport.get('content', '')).strip()
        profile.viewport_configured = bool(profile.viewport_content)
        
        # Analyze viewport settings
        viewport_values = _viewport_values(profile.viewport_content)
        has_device_width = viewport_values.get('width') == 'device-width'
        has_initial_scale = viewport_values.get('initial-scale') == '1'
        prevents_zoom = _viewport_restricts_zoom(viewport_values)
        
        if has_device_width and has_initial_scale and not prevents_zoom:
            profile.mobile_readiness = MobileReadiness.OPTIMIZED
        elif has_device_width:
            profile.mobile_readiness = MobileReadiness.RESPONSIVE
        else:
            profile.mobile_readiness = MobileReadiness.ADAPTIVE
    
    # Check responsive images
    images = [record['attrs'] for record in facts.images] if facts is not None else soup.find_all('img')
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
    
    # Object/embed may be ordinary images or media, not a plugin dependency.
    plugins = soup.find_all(['embed', 'object', 'applet'])
    profile.uses_plugins = any(plugin.name == 'applet' or
                              str(plugin.get('type', '')).lower() == 'application/x-shockwave-flash'
                              for plugin in plugins)
    
    # Check for AMP
    amp_html = soup.find('html', attrs={'amp': True}) or soup.find('html', attrs={'⚡': True})
    if amp_html:
        profile.amp_version = 'AMP'
    
    amp_link = next((link for link in links if 'amphtml' in link.get('rel', [])), None)
    if amp_link:
        profile.amp_version = 'AMP Available'
    
    # Check for PWA indicators
    manifest = next((link for link in links if 'manifest' in link.get('rel', [])), None)
    service_worker = (any(re.search(r'serviceWorker', record['text']) for record in facts.scripts)
                      if facts is not None else soup.find('script', string=re.compile(r'serviceWorker')))
    
    if manifest and service_worker:
        profile.pwa_ready = True
    
    # Check for app links
    # iOS
    ios_app = next((meta for meta in metas if meta.get('name') == 'apple-itunes-app'), None)
    if ios_app:
        profile.app_links['ios'] = ios_app.get('content', '')
    
    # Android
    android_app = next((link for link in links if 'alternate' in link.get('rel', [])
                        and re.search(r'android-app://', str(link.get('href', '')))), None)
    if android_app:
        profile.app_links['android'] = android_app.get('href', '')
    
    # Check touch icon
    touch_icon = next((link for link in links if any(re.search(r'apple-touch-icon', rel)
                       for rel in link.get('rel', []))), None)
    if touch_icon:
        profile.app_links['touch_icon'] = touch_icon.get('href', '')
    
    # Layout, touch targets, and text readability require rendered measurements.
    profile.horizontal_scrolling = None
    profile.text_readability = None
    profile.touch_elements_size = None
    
    return profile


def analyze_performance_indicators(headers: Dict[str, str] = None, soup: BeautifulSoup = None) -> PerformanceProfile:
    """Analyze technical performance indicators."""
    profile = PerformanceProfile()
    headers_lower = normalized_headers(headers)
    
    # Alt-Svc advertises capabilities; headers do not prove negotiated protocol.
    # Check compression
    content_encoding = headers_lower.get('content-encoding', '')
    if content_encoding and content_encoding.strip().lower() != 'identity':
        profile.compression_enabled = True
        profile.compression_type = content_encoding
        
    # Cache analysis
    cache_control = headers_lower.get('cache-control', '')
    if cache_control:
        profile.cache_control = cache_control
        
        # Parse max-age
        max_age_match = re.search(r'max-age\s*=\s*(\d+)', cache_control, re.I)
        if max_age_match:
            profile.cache_ttl = int(max_age_match.group(1))
        
        if 'no-store' in cache_control.lower():
            profile.cache_ttl = None
    
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
    
    # Connection settings
    connection = headers_lower.get('connection', '')
    if 'keep-alive' in connection.lower():
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
        params = parse_qs(parsed.query, keep_blank_values=True)
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


def analyze_international_setup(soup: BeautifulSoup, headers: Dict[str, str] = None, *,
                                facts: Optional[PageFacts] = None) -> InternationalProfile:
    """Analyze international and localization configuration."""
    profile = InternationalProfile()
    headers_lower = normalized_headers(headers)
    
    # Check language declaration
    html_tag = soup.find('html')
    language = facts.language if facts is not None else html_tag.get('lang') if html_tag else None
    if language is not None and str(language).strip():
        profile.language_declared = True
        profile.language_code = str(language).strip()
    
    # Check for hreflang tags
    hreflang_links = ([record['attrs'] for record in facts.link_tags
                       if 'alternate' in record['attrs'].get('rel', []) and 'hreflang' in record['attrs']]
                      if facts is not None else soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True}))
    if hreflang_links:
        profile.hreflang_configured = True
        for link in hreflang_links:
            lang = link.get('hreflang')
            href = link.get('href')
            if lang and href:
                profile.hreflang_tags[lang] = href
    
    # Check charset
    metas = [record['attrs'] for record in facts.meta] if facts is not None else soup.find_all('meta')
    charset_meta = next((meta for meta in metas if 'charset' in (meta if isinstance(meta, dict) else meta.attrs)), None)
    if charset_meta:
        profile.charset = charset_meta.get('charset')
    else:
        content_type = next((meta for meta in metas if re.fullmatch('content-type', str(meta.get('http-equiv', '')), re.I)), None)
        if content_type:
            content = content_type.get('content', '')
            charset_match = re.search(r'charset\s*=\s*[\"\']?([^;\s\"\']+)', content, re.I)
            if charset_match:
                profile.charset = charset_match.group(1).strip()
    header_charset = re.search(r'charset\s*=\s*[\"\']?([^;\s\"\']+)',
                               headers_lower.get('content-type', ''), re.I)
    if header_charset:
        profile.charset = header_charset.group(1)
    
    # Check for geo-targeting meta tags
    geo_tags = ['geo.region', 'geo.placename', 'geo.position', 'ICBM']
    for tag_name in geo_tags:
        geo_tag = next((meta for meta in metas if meta.get('name') == tag_name), None)
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


def detect_javascript_seo_issues(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Detect JavaScript SEO issues and recommendations."""
    issues = {
        'client_side_rendering': None,
        'spa_detected': None,
        'framework_container_detected': False,
        'lazy_loaded_content': False,
        'infinite_scroll': None,
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
            issues['framework_container_detected'] = True
            break
    
    # Check for lazy loading indicators
    lazy_indicators = [
        ('img', {'loading': 'lazy'}),
        ('iframe', {'loading': 'lazy'}),
        (None, {'data-src': True}),
        (None, {'data-lazy': True}),
    ]
    
    for tag, attrs in lazy_indicators:
        if tag == 'img' and facts is not None:
            elements = [record for record in facts.images
                        if all(record['attrs'].get(name) == value for name, value in attrs.items())]
        else:
            elements = soup.find_all(tag, attrs) if tag else soup.find_all(attrs=attrs)
        if elements:
            issues['lazy_loaded_content'] = True
            break
    
    # Check for infinite scroll
    script_texts = ([record['text'] for record in facts.scripts] if facts is not None
                    else [script.string or '' for script in soup.find_all('script')])
    infinite_scroll_scripts = [text for text in script_texts if re.search(r'(IntersectionObserver|infinite.?scroll|waypoint)', text, re.I)]
    issues['intersection_or_scroll_code_reference'] = bool(infinite_scroll_scripts)
    
    # Check for AJAX navigation
    ajax_nav_patterns = [
        r'history\.pushState',
        r'window\.history\.replaceState',
        r'ajax.*navigation',
        r'pjax'
    ]
    
    for text in script_texts:
        if text:
            for pattern in ajax_nav_patterns:
                if re.search(pattern, text, re.I):
                    issues['ajax_navigation'] = True
                    break
    
    # Check for JavaScript redirects
    js_redirect_patterns = [
        r'(?:window\.)?location(?:\.href)?\s*=(?!=)',
        r'(?:window\.)?location\.(?:replace|assign)\s*\('
    ]
    
    for text in script_texts:
        if text:
            for pattern in js_redirect_patterns:
                if re.search(pattern, text):
                    issues['javascript_redirects'] = True
                    break
    
    # Advice is produced only by explicit registry evaluations in analyze_technical.
    return issues


def _check_security_rules(collector: RuleCollector, soup: BeautifulSoup, url: str,
                          headers: Any, html_document: bool, *, facts: Optional[PageFacts] = None) -> None:
    """Evaluate declared header configuration without assuming deployment intent."""
    parsed = urlparse(url)
    host = parsed.hostname or ''
    try:
        ipaddress.ip_address(host)
        domain = False
    except ValueError:
        domain = bool(host)
    hsts_applicable = parsed.scheme.lower() == 'https' and domain
    hsts = _hsts_policy(headers)
    hsts_evidence = {**hsts, 'headers_checked': headers is not None,
                     'browser_hsts_state_checked': False, 'host': host}
    hsts_reason = ('HSTS is a domain policy received over HTTPS; this URL is outside that scope.'
                   if not hsts_applicable else 'Response headers were not supplied.')
    collector.check('security.hsts_missing', not bool(hsts['values']) if headers is not None else None,
                    hsts_evidence, applicable=hsts_applicable, reason=hsts_reason,
                    source='response_headers', category='Security',
                    message='No HSTS header observed on this HTTPS response')
    declared_hsts = hsts_applicable and (bool(hsts['values']) if headers is not None else None)
    collector.check('security.hsts_invalid', not hsts['valid'] if headers is not None else None,
                    hsts_evidence, applicable=declared_hsts,
                    reason=hsts_reason if not hsts_applicable or headers is None else 'No HSTS policy was declared.',
                    source='response_headers', category='Security',
                    message='Declared HSTS policy has an invalid max-age or repeated/invalid directives')
    collector.check('security.hsts_preload_incomplete',
                    not hsts['meets_preload_duration'] or not hsts['includesubdomains'],
                    hsts_evidence,
                    applicable=hsts_applicable and (hsts['preload'] if headers is not None else None),
                    reason=hsts_reason if not hsts_applicable or headers is None else 'The policy does not request preloading.',
                    source='response_headers', category='Security',
                    message='Declared HSTS preload policy lacks a required duration or includeSubDomains')

    policies = _csp_policies(headers, soup, facts=facts)
    policy_evidence = {'policies': policies, 'headers_checked': headers is not None,
                       'effective_browser_policy_checked': False}
    declared_csp = any(policy['directives'] for policy in policies)
    collector.check('security.csp_missing',
                    not declared_csp if declared_csp or headers is not None else None,
                    policy_evidence, applicable=html_document,
                    reason='Response headers were not supplied.' if headers is None else 'This is not an HTML document.',
                    source='html_and_headers', category='Security',
                    message='No enforcing CSP declaration observed')
    csp_applicable = html_document and (declared_csp if headers is not None or declared_csp else None)
    for rule_id, token, message in (
        ('security.csp_unsafe_inline', "'unsafe-inline'", 'CSP script source expression includes unsafe-inline without a nonce or hash'),
        ('security.csp_unsafe_eval', "'unsafe-eval'", 'CSP script source expression includes unsafe-eval'),
        ('security.csp_wildcard_default', '*', 'CSP default source expression includes a wildcard'),
    ):
        matches = []
        for index, policy in enumerate(policies):
            directives = policy['directives']
            directive = 'default-src' if token == '*' or 'script-src' not in directives else 'script-src'
            values = directives.get(directive, [])
            if token in [value.lower() for value in values] and not (
                    token == "'unsafe-inline'" and _has_nonce_or_hash(values)):
                matches.append({'policy_index': index, 'source': policy['source'],
                                'directive': directive, 'expression': token})
        collector.check(rule_id, bool(matches), {**policy_evidence, 'matches': matches},
                        applicable=csp_applicable,
                        reason='No enforcing CSP declaration observed, or response headers are unavailable.',
                        source='html_and_headers', category='Security', message=message)

    xfo_values = header_values(headers, 'X-Frame-Options')
    frame_ancestors = [policy['directives']['frame-ancestors'] for policy in policies
                       if policy['source'] == 'response_header' and 'frame-ancestors' in policy['directives']]
    frame_evidence = {'x_frame_options': xfo_values, 'frame_ancestors': frame_ancestors,
                      'headers_checked': headers is not None, 'embedding_intent': None}
    collector.check('security.frame_policy_missing',
                    not bool(xfo_values or frame_ancestors) if headers is not None else None,
                    frame_evidence, applicable=html_document,
                    reason='Response headers were not supplied.' if headers is None else 'This is not an HTML document.',
                    source='response_headers', category='Security',
                    message='No response header declaring a frame embedding restriction observed')
    xfo_tokens = [token.strip().upper() for value in xfo_values for token in value.split(',')]
    invalid_xfo = bool(xfo_tokens) and (
        any(token not in ('DENY', 'SAMEORIGIN') for token in xfo_tokens) or len(set(xfo_tokens)) > 1)
    collector.check('security.xfo_invalid', invalid_xfo, frame_evidence,
                    applicable=html_document and (bool(xfo_values) if headers is not None else None),
                    reason='No X-Frame-Options header observed, or response headers are unavailable.',
                    source='response_headers', category='Security',
                    message='X-Frame-Options has an unsupported or conflicting value')
    origins = [value.strip() for value in header_values(headers, 'Access-Control-Allow-Origin')]
    credentials = [value.strip() for value in header_values(headers, 'Access-Control-Allow-Credentials')]
    collector.check('security.cors_wildcard_credentials',
                    '*' in origins and 'true' in credentials if headers is not None else None,
                    {'allow_origin': origins, 'allow_credentials': credentials,
                     'credentialed_request_tested': False, 'headers_checked': headers is not None},
                    reason='Response headers were not supplied.', source='response_headers', category='Security',
                    message='Wildcard CORS origin cannot authorize credentialed browser requests')


def _http_resource_references(soup: BeautifulSoup, url: str, *,
                              facts: Optional[PageFacts] = None) -> List[Dict[str, str]]:
    references = []
    base = facts.base_url if facts is not None else document_base_url(soup, url)
    shared = ({'img': facts.images, 'script': facts.scripts, 'link': facts.link_tags}
              if facts is not None else {})
    for tag_name, attr_name in (
        ('img', 'src'), ('script', 'src'), ('link', 'href'), ('iframe', 'src'),
        ('source', 'src'), ('video', 'src'), ('video', 'poster'), ('audio', 'src'),
        ('embed', 'src'), ('object', 'data'),
    ):
        elements = [record['attrs'] for record in shared[tag_name]] if tag_name in shared else soup.find_all(tag_name)
        for element in elements:
            if tag_name == 'link' and not any(str(rel).lower() in ('stylesheet', 'preload', 'icon')
                                             for rel in element.get('rel', [])):
                continue
            raw = str(element.get(attr_name, '')).strip()
            if not raw:
                continue
            resolved = resolve_url(raw, base)
            if resolved and urlparse(resolved).scheme == 'http':
                references.append({'type': tag_name, 'attribute': attr_name, 'url': resolved})
    return references


def analyze_technical(soup: BeautifulSoup, url: str, headers: Dict[str, str] = None,
                      status_code: int = 200, user_agent: Optional[str] = None, *,
                      facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Evaluate observed technical facts; retain unmeasured runtime properties as unknown."""
    facts = ensure_page_facts(soup, url, headers=headers, user_agent=user_agent, facts=facts)
    headers, user_agent = facts.headers, facts.user_agent
    collector = RuleCollector('technical')
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    host = parsed_url.hostname or ''
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = host.lower().rstrip('.') == 'localhost' or host.lower().rstrip('.').endswith('.localhost')
    content_types = header_values(headers, 'Content-Type')
    media_type = content_types[0].split(';', 1)[0].strip().lower() if content_types else None
    html_document = (media_type in ('text/html', 'application/xhtml+xml') if media_type else
                     not facts.is_xml or bool(facts.tag_counts.get('html')))
    html_syntax = html_document and not facts.is_xml and media_type != 'application/xhtml+xml'
    data = {'https': scheme == 'https', 'status_code': status_code}
    collector.check('security.https_missing', scheme == 'http',
                    {'scheme': scheme, 'host': host, 'loopback': loopback},
                    applicable=scheme in ('http', 'https') and not loopback,
                    reason='The URL is outside the public HTTP/HTTPS document scope or uses local loopback.',
                    source='url', category='Security', message='Document URL uses HTTP')
    measured_status = type(status_code) is int and 100 <= status_code <= 599
    status_evidence = {'status_code': status_code, 'status_observed': measured_status}
    for rule_id, failed, message in (
        ('technical.http_server_error', 500 <= status_code <= 599 if measured_status else None, 'HTTP server error response'),
        ('technical.http_client_error', 400 <= status_code <= 499 if measured_status else None, 'HTTP client error response'),
        ('technical.http_redirect', status_code in (300, 301, 302, 303, 305, 307, 308) if measured_status else None,
         'HTTP redirect response; verify destination and intended permanence'),
    ):
        collector.check(rule_id, failed, status_evidence, reason='No valid HTTP response status was supplied.',
                        source='response_status', category='Availability', message=message)

    security_profile = analyze_security_headers(headers)
    hsts = _hsts_policy(headers)
    data['security'] = {
        'level': None, 'level_status': 'not_assessed', 'https': data['https'],
        'header_configuration_level': security_profile.security_level.value if headers is not None else None,
        'header_configuration_level_method': 'legacy_header_presence_heuristic',
        'hsts': bool(hsts['values']) if headers is not None else None,
        'hsts_max_age': hsts['max_age'],
        'csp': security_profile.csp_enabled if headers is not None else None,
        'xfo': security_profile.xfo_enabled if headers is not None else None,
        'x_content_type_options': security_profile.x_content_type_options if headers is not None else None,
        'vulnerabilities': [], 'vulnerabilities_status': 'not_tested',
        'source': 'response_headers' if headers is not None else 'not_measured',
        'scope': 'header_configuration',
    }
    _check_security_rules(collector, soup, url, headers, html_document, facts=facts)

    crawl_profile = analyze_crawlability(soup, headers, user_agent, facts=facts)
    robots = crawl_profile.robots_analysis
    data['crawlability'] = {
        'status': crawl_profile.status.value, 'noindex': crawl_profile.noindex,
        'nofollow': crawl_profile.nofollow,
        'canonical': resolve_url(crawl_profile.canonical_url, facts.base_url) if crawl_profile.canonical_url else None,
        'javascript_required': None, 'indexability': robots['indexability'],
        'robots_analysis': robots, 'crawl_access': 'unknown',
    }
    for directive in ('noindex', 'nofollow', 'nosnippet'):
        observed = robots[directive]
        collector.check('robots.' + directive, observed if observed or headers is not None else None,
                        {'directives': robots['directives'], 'declarations': robots['evidence'],
                         'headers_checked': headers is not None, 'user_agent': user_agent,
                         'publisher_intent': None},
                        reason='No restriction was observed in markup; response headers were not supplied.',
                        source='html_and_headers', category='Crawlability',
                        message='An applicable ' + directive + ' directive is declared')

    mobile_profile = analyze_mobile_optimization(soup, facts=facts)
    viewports = [str(meta.get('content', '')).strip() for record in facts.meta for meta in [record['attrs']]
                 if str(meta.get('name', '')).strip().lower() == 'viewport']
    nonempty_viewports = [content for content in viewports if content]
    viewport_settings = [_viewport_values(content) for content in nonempty_viewports]
    viewport_evidence = {'declarations': viewports, 'settings': viewport_settings, 'rendered_layout_checked': False}
    collector.check('mobile.viewport_missing', not bool(nonempty_viewports), viewport_evidence,
                    applicable=html_document, reason='This is not an HTML document.',
                    category='Mobile', message='No nonempty viewport meta declaration observed')
    collector.check('mobile.viewport_zoom_disabled', any(_viewport_restricts_zoom(settings) for settings in viewport_settings),
                    viewport_evidence, applicable=html_document and bool(nonempty_viewports),
                    reason='No viewport declaration applies to this document.', category='Mobile',
                    message='An authored viewport setting restricts user zoom')
    data['mobile'] = {
        'readiness': None, 'layout_status': 'not_measured', 'source': 'html_attributes',
        'viewport_configured': bool(nonempty_viewports),
        'responsive_images': f"{mobile_profile.responsive_images}/{mobile_profile.total_images}",
        'responsive_images_method': 'markup_hints',
        'amp': mobile_profile.amp_version, 'amp_status': 'markup_hint',
        'pwa_ready': None, 'pwa_status': 'not_tested',
        'pwa_markup_indicators': mobile_profile.pwa_ready,
    }

    perf_profile = analyze_performance_indicators(headers, soup)
    data['performance'] = {
        'protocol': perf_profile.protocol_version.value,
        'compression': perf_profile.compression_type,
        'cache_ttl': perf_profile.cache_ttl, 'cdn': perf_profile.cdn_provider or 'None detected',
        'cdn_status': 'header_hint' if perf_profile.cdn_provider else 'not_established',
        'etag': perf_profile.etag_present if headers is not None else None,
        'server_push': None, 'source': 'response_headers' if headers is not None else 'not_measured',
        'protocol_status': 'unknown', 'transfer_savings': None,
    }
    has_body = measured_status and status_code >= 200 and status_code not in (204, 205, 304)
    collector.check('technical.http_compression',
                    not perf_profile.compression_enabled if headers is not None else None,
                    {'content_encoding': header_values(headers, 'Content-Encoding'),
                     'headers_checked': headers is not None, 'negotiation_checked': False, 'transfer_savings': None},
                    applicable=html_document and (has_body if measured_status else None),
                    reason='Response headers or a body-bearing HTML response were not observed.',
                    source='response_headers', category='Performance',
                    message='No non-identity Content-Encoding observed for this response')

    url_profile = analyze_url_structure(url)
    data['url'] = {
        'length': url_profile.length, 'depth': url_profile.depth, 'parameters': url_profile.parameters_count,
        'is_clean': url_profile.is_clean, 'is_clean_method': 'legacy_url_shape_heuristic',
        'is_seo_friendly': None, 'quality_status': 'not_assessed',
    }
    session_names = sorted(name for name in parse_qs(parsed_url.query, keep_blank_values=True)
                           if name.lower() in ('sessionid', 'session', 'sid', 'phpsessid', 'jsessionid'))
    collector.check('technical.url_session_parameter', bool(session_names),
                    {'parameter_names': session_names, 'parameter_meanings_checked': False},
                    source='url', category='URL Structure', message='Query uses a session-like parameter name')

    intl_profile = analyze_international_setup(soup, headers, facts=facts)
    data['international'] = {
        'language': intl_profile.language_code, 'charset': intl_profile.charset,
        'hreflang_count': len(intl_profile.hreflang_tags), 'geo_targeting': intl_profile.geo_targeting,
    }
    human_text = bool(facts.text)
    collector.check('language.missing', not intl_profile.language_declared,
                    {'language': intl_profile.language_code, 'human_readable_text_observed': human_text},
                    applicable=html_document and human_text,
                    reason='No human-readable HTML document content was observed.',
                    category='International', message='Primary document language is not declared')
    charset = str(intl_profile.charset).strip() if intl_profile.charset else None
    collector.check('seo.charset_non_utf8', charset.lower() not in ('utf-8', 'utf8') if charset else None,
                    {'declared_charset': charset, 'headers_checked': headers is not None,
                     'original_bytes_checked': False}, applicable=html_document,
                    reason='No encoding declaration was observed; original bytes and byte-order marks were not checked.',
                    source='html_and_headers', category='International',
                    message='A non-UTF-8 character encoding is declared')

    js_issues = detect_javascript_seo_issues(soup, facts=facts)
    js_issues['recommendations'] = []
    references = []
    for index, script in enumerate(facts.scripts):
        if script['text']:
            match = re.search(r'(?:window\.)?location(?:\.href)?\s*=(?!=)|(?:window\.)?location\.(?:replace|assign)\s*\(',
                              script['text'])
            if match:
                references.append({'script_index': index, 'expression': match.group(0)})
    collector.check('technical.javascript_redirect_reference', bool(references),
                    {'references': references, 'executed': None}, applicable=html_document,
                    reason='This is not an HTML document.', confidence='low', category='JavaScript SEO',
                    message='Inline script text references a location change; execution is unverified')
    data['javascript_seo'] = js_issues

    http_references = _http_resource_references(soup, url, facts=facts) if data['https'] else []
    collector.check('technical.http_resource_reference', bool(http_references),
                    {'count': len(http_references), 'references': http_references[:20],
                     'references_truncated': len(http_references) > 20,
                     'effective_requests_checked': False},
                    applicable=html_document and data['https'],
                    reason='Mixed-content checks apply to HTTPS HTML documents.', category='Security',
                    message='HTML declares HTTP subresource URLs on an HTTPS document')
    data['mixed_content'] = http_references[:10]
    data['mixed_content_status'] = 'source_references_only'

    tag_counts = facts.tag_counts
    obsolete_counts = {tag: tag_counts.get(tag, 0) for tag in ('applet', 'frameset', 'frame', 'font', 'center')}
    obsolete_counts = {tag: count for tag, count in obsolete_counts.items() if count}
    flash = soup.find_all(['embed', 'object'], attrs={'type': re.compile(r'^application/x-shockwave-flash$', re.I)})
    if flash:
        obsolete_counts['flash_mime_declaration'] = len(flash)
    collector.check('technical.deprecated_elements', bool(obsolete_counts),
                    {'elements': obsolete_counts, 'rendered_behavior_checked': False},
                    applicable=html_document, reason='This is not an HTML document.', category='Compatibility',
                    message='Obsolete HTML elements or legacy plugin markup observed')
    doctype = facts.doctype[0] if facts.doctype else None
    doctype_evidence = {'doctype': doctype, 'media_type': media_type,
                        'parser_is_xml': facts.is_xml, 'rendering_mode_checked': False}
    collector.check('html.doctype_missing', not bool(doctype), doctype_evidence, applicable=html_syntax,
                    reason='An HTML doctype is not required for XML/XHTML syntax.', category='HTML Standards',
                    message='Missing HTML DOCTYPE declaration')
    collector.check('html.doctype_legacy', bool(doctype and doctype.strip().lower() != 'html'),
                    doctype_evidence, applicable=html_syntax and bool(doctype),
                    reason='No doctype in an HTML-syntax document was observed.', category='HTML Standards',
                    message='Legacy HTML doctype declaration observed')
    data['structured_data_types'] = {
        'json_ld': sum(record['attrs'].get('type') == 'application/ld+json' for record in facts.scripts),
        'microdata': len(soup.find_all(attrs={'itemscope': True})),
        'rdfa': len(soup.find_all(attrs={'typeof': True})),
    }
    issues = collector.issues
    recommendations = recommendations_for(issues)
    data['recommendations'] = recommendations
    data['javascript_seo']['recommendations'] = recommendations_for(
        [issue for issue in issues if issue['rule_id'] == 'technical.javascript_redirect_reference'])
    return {'score': score_findings(issues, owner='technical'), 'issues': issues, 'data': data,
            'recommendations': recommendations, 'rule_results': collector.results,
            'rule_coverage': collector.coverage, 'coverage': collector.coverage}
