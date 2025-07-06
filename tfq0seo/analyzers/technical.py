"""
Technical SEO analyzer
"""
from typing import Dict, List, Optional, Any, Set
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import json
import logging
from ..core.issue_helper import IssueHelper

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """Analyzer for technical SEO aspects"""
    
    def __init__(self, config):
        self.config = config
        
    def analyze(self, page_data: Dict, soup: Optional[BeautifulSoup]) -> Dict[str, Any]:
        """Analyze technical SEO aspects"""
        issues = []
        
        # HTTPS check
        url = page_data.get('url', '')
        parsed_url = urlparse(url)
        is_https = parsed_url.scheme == 'https'
        
        if not is_https:
            issues.append(IssueHelper.create_issue('no_https'))
        
        # Response headers analysis
        headers = page_data.get('headers', {})
        header_analysis = self._analyze_headers(headers)
        issues.extend(header_analysis['issues'])
        
        # Robots meta tag analysis
        robots_analysis = self._analyze_robots_meta(soup) if soup else {}
        issues.extend(robots_analysis.get('issues', []))
        
        # Canonical URL analysis
        canonical_analysis = self._analyze_canonical(soup, url) if soup else {}
        issues.extend(canonical_analysis.get('issues', []))
        
        # Mobile-friendliness
        mobile_analysis = self._check_mobile_friendly(soup) if soup else {}
        issues.extend(mobile_analysis.get('issues', []))
        
        # Compression
        compression_analysis = self._analyze_compression(headers, page_data)
        issues.extend(compression_analysis['issues'])
        
        # Caching headers
        cache_analysis = self._analyze_caching(headers)
        issues.extend(cache_analysis['issues'])
        
        # XML Sitemap reference
        sitemap_analysis = self._check_sitemap_reference(soup, page_data) if soup else {}
        
        # Hreflang tags
        hreflang_analysis = self._analyze_hreflang(soup, url) if soup else {}
        issues.extend(hreflang_analysis.get('issues', []))
        
        # AMP version
        amp_analysis = self._check_amp_version(soup) if soup else {}
        issues.extend(amp_analysis.get('issues', []))
        
        # Structured data validation
        structured_data = self._analyze_structured_data(soup) if soup else {}
        issues.extend(structured_data.get('issues', []))
        
        # Pagination
        pagination = self._analyze_pagination(soup) if soup else {}
        issues.extend(pagination.get('issues', []))
        
        # JavaScript framework detection
        js_frameworks = self._detect_js_frameworks(soup, page_data) if soup else []
        
        # DNS prefetch/preconnect
        resource_hints = self._analyze_resource_hints(soup) if soup else {}
        
        # PWA detection
        pwa_analysis = self._check_pwa(soup, headers) if soup else {}
        issues.extend(pwa_analysis.get('issues', []))
        
        # Cookie analysis
        cookie_analysis = self._analyze_cookies(headers)
        issues.extend(cookie_analysis['issues'])
        
        # Calculate technical score
        technical_score = self._calculate_technical_score(issues)
        
        return {
            'https': is_https,
            'compression': compression_analysis['compression'],
            'compression_ratio': compression_analysis.get('ratio', 0),
            'mobile_friendly': mobile_analysis.get('is_mobile_friendly', False),
            'security_headers': header_analysis['security_headers'],
            'cache_control': cache_analysis.get('cache_control', ''),
            'max_age': cache_analysis.get('max_age', 0),
            'sitemap_referenced': sitemap_analysis.get('found', False),
            'sitemap_locations': sitemap_analysis.get('locations', []),
            'canonical_url': canonical_analysis.get('canonical', ''),
            'is_canonical_self': canonical_analysis.get('is_self', True),
            'robots_directives': robots_analysis.get('directives', []),
            'hreflang_tags': hreflang_analysis.get('tags', []),
            'amp_url': amp_analysis.get('url', ''),
            'structured_data': structured_data.get('schemas', []),
            'pagination': pagination.get('pagination', {}),
            'js_frameworks': js_frameworks,
            'resource_hints': resource_hints,
            'pwa_features': pwa_analysis.get('features', {}),
            'cookies': cookie_analysis.get('cookies', []),
            'technical_score': technical_score,
            'issues': issues
        }
    
    def _analyze_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze HTTP response headers"""
        issues = []
        security_headers = {}
        
        # Check security headers with recommendations
        security_header_checks = {
            'X-Frame-Options': {
                'protection': 'clickjacking',
                'recommended': ['DENY', 'SAMEORIGIN']
            },
            'X-Content-Type-Options': {
                'protection': 'MIME sniffing',
                'recommended': ['nosniff']
            },
            'X-XSS-Protection': {
                'protection': 'XSS attacks',
                'recommended': ['1; mode=block']
            },
            'Strict-Transport-Security': {
                'protection': 'HTTPS enforcement',
                'recommended': ['max-age=31536000']
            },
            'Content-Security-Policy': {
                'protection': 'content injection',
                'recommended': None  # Too complex for simple check
            },
            'Referrer-Policy': {
                'protection': 'referrer information',
                'recommended': ['no-referrer-when-downgrade', 'strict-origin-when-cross-origin']
            },
            'Permissions-Policy': {
                'protection': 'feature permissions',
                'recommended': None
            }
        }
        
        for header, config in security_header_checks.items():
            value = headers.get(header, '')
            if value:
                security_headers[header] = value
                # Check if value is recommended
                if config['recommended'] and not any(rec in value for rec in config['recommended']):
                    issues.append({
                        'type': 'suboptimal_security_header',
                        'severity': 'notice',
                        'message': f'{header} value "{value}" may not be optimal'
                    })
            else:
                severity = 'warning' if header == 'Strict-Transport-Security' else 'notice'
                issues.append(IssueHelper.create_issue(
                    'missing_security_header',
                    header=header,
                    protection=config['protection']
                ))
        
        # Check for server information disclosure
        server = headers.get('Server', '')
        x_powered_by = headers.get('X-Powered-By', '')
        
        if server and re.search(r'(apache|nginx|iis|microsoft-iis)/[\d\.]+', server.lower()):
            issues.append(IssueHelper.create_issue(
                'server_version_exposed',
                server_info=server
            ))
        
        if x_powered_by:
            issues.append({
                'type': 'technology_exposed',
                'severity': 'notice',
                'message': f'Technology information exposed via X-Powered-By: {x_powered_by}'
            })
        
        # Check for problematic headers
        if 'P3P' in headers:
            issues.append({
                'type': 'deprecated_header',
                'severity': 'notice',
                'message': 'P3P header is deprecated and should be removed'
            })
        
        return {
            'security_headers': security_headers,
            'issues': issues
        }
    
    def _analyze_robots_meta(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze robots meta tags"""
        issues = []
        directives = []
        
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta:
            content = robots_meta.get('content', '').lower()
            directives = [d.strip() for d in content.split(',')]
            
            # Check for problematic directives
            if 'noindex' in directives:
                issues.append({
                    'type': 'noindex_directive',
                    'severity': 'critical',
                    'message': 'Page has noindex directive - won\'t appear in search results'
                })
            
            if 'nofollow' in directives:
                issues.append({
                    'type': 'nofollow_directive',
                    'severity': 'warning',
                    'message': 'Page has nofollow directive - links won\'t be followed'
                })
            
            if 'noarchive' in directives:
                issues.append({
                    'type': 'noarchive_directive',
                    'severity': 'notice',
                    'message': 'Page has noarchive directive - won\'t be cached by search engines'
                })
        
        # Check for googlebot specific tags
        googlebot_meta = soup.find('meta', attrs={'name': 'googlebot'})
        if googlebot_meta:
            content = googlebot_meta.get('content', '').lower()
            directives.extend([f'googlebot:{d.strip()}' for d in content.split(',')])
        
        return {
            'directives': directives,
            'issues': issues
        }
    
    def _analyze_canonical(self, soup: BeautifulSoup, current_url: str) -> Dict[str, Any]:
        """Analyze canonical URL"""
        issues = []
        canonical_link = soup.find('link', {'rel': 'canonical'})
        
        if not canonical_link:
            issues.append(IssueHelper.create_issue('missing_canonical'))
            return {'canonical': '', 'is_self': True, 'issues': issues}
        
        canonical_url = canonical_link.get('href', '')
        if not canonical_url:
            issues.append({
                'type': 'empty_canonical',
                'severity': 'warning',
                'message': 'Canonical tag exists but href is empty',
                'user_impact': 'Search engines can\'t determine the preferred URL',
                'recommendation': 'Add a valid URL to your canonical link tag',
                'example': '<link rel="canonical" href="https://example.com/page">',
                'implementation_difficulty': 'easy',
                'priority_score': 6,
                'estimated_impact': 'medium'
            })
            return {'canonical': '', 'is_self': True, 'issues': issues}
        
        # Make canonical URL absolute
        canonical_url = urljoin(current_url, canonical_url)
        
        # Check if canonical points to self
        is_self = self._normalize_url(canonical_url) == self._normalize_url(current_url)
        
        # Validate canonical URL
        parsed = urlparse(canonical_url)
        if not parsed.scheme or not parsed.netloc:
            issues.append({
                'type': 'invalid_canonical',
                'severity': 'critical',
                'message': f'Invalid canonical URL: {canonical_url}'
            })
        
        # Check for protocol mismatch
        current_parsed = urlparse(current_url)
        if parsed.scheme != current_parsed.scheme:
            issues.append({
                'type': 'canonical_protocol_mismatch',
                'severity': 'warning',
                'message': f'Canonical URL protocol ({parsed.scheme}) differs from current ({current_parsed.scheme})'
            })
        
        # Check for domain mismatch
        if parsed.netloc != current_parsed.netloc:
            issues.append({
                'type': 'canonical_cross_domain',
                'severity': 'notice',
                'message': f'Canonical URL points to different domain: {parsed.netloc}'
            })
        
        return {
            'canonical': canonical_url,
            'is_self': is_self,
            'issues': issues
        }
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        parsed = urlparse(url.lower())
        # Remove trailing slash, fragments, and normalize empty path
        path = parsed.path.rstrip('/') or '/'
        return f'{parsed.scheme}://{parsed.netloc}{path}'
    
    def _check_mobile_friendly(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Check mobile-friendliness indicators"""
        issues = []
        is_mobile_friendly = True
        features = {}
        
        # Check viewport meta tag
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            is_mobile_friendly = False
            issues.append(IssueHelper.create_issue('no_viewport'))
        else:
            content = viewport.get('content', '')
            features['viewport'] = content
            
            # Check viewport configuration
            if 'width=device-width' not in content:
                issues.append({
                    'type': 'viewport_not_responsive',
                    'severity': 'warning',
                    'message': 'Viewport not set to device-width',
                    'user_impact': 'Your site may not scale properly on different screen sizes',
                    'recommendation': 'Include width=device-width in your viewport meta tag',
                    'example': '<meta name="viewport" content="width=device-width, initial-scale=1">',
                    'implementation_difficulty': 'easy',
                    'priority_score': 7,
                    'estimated_impact': 'high'
                })
            
            if 'user-scalable=no' in content or 'maximum-scale=1' in content:
                issues.append(IssueHelper.create_issue('viewport_zoom_disabled'))
        
        # Check for mobile-specific meta tags
        apple_tags = {
            'apple-mobile-web-app-capable': 'iOS app capable',
            'apple-mobile-web-app-status-bar-style': 'iOS status bar',
            'apple-mobile-web-app-title': 'iOS app title'
        }
        
        for name, description in apple_tags.items():
            tag = soup.find('meta', attrs={'name': name})
            if tag:
                features[name] = tag.get('content', '')
        
        # Check for responsive images
        pictures = soup.find_all('picture')
        if pictures:
            features['responsive_images'] = len(pictures)
        
        # Check for mobile-first CSS (media queries)
        styles = soup.find_all('style')
        mobile_queries = 0
        desktop_queries = 0
        
        for style in styles:
            if style.string:
                mobile_queries += len(re.findall(r'@media[^{]*max-width', style.string))
                desktop_queries += len(re.findall(r'@media[^{]*min-width', style.string))
        
        # Also check linked stylesheets
        for link in soup.find_all('link', {'rel': 'stylesheet'}):
            media = link.get('media', '')
            if 'max-width' in media:
                mobile_queries += 1
            elif 'min-width' in media:
                desktop_queries += 1
        
        features['mobile_first_css'] = mobile_queries > desktop_queries
        
        # Check for touch icons
        touch_icons = soup.find_all('link', {'rel': re.compile(r'apple-touch-icon|icon')})
        features['touch_icons'] = len(touch_icons)
        
        # Check font sizes (more comprehensive)
        small_fonts = self._check_font_sizes(soup)
        if small_fonts:
            issues.append({
                'type': 'small_font_sizes',
                'severity': 'warning',
                'message': f'Found {small_fonts} text elements with small font sizes (<14px)'
            })
        
        return {
            'is_mobile_friendly': is_mobile_friendly,
            'features': features,
            'issues': issues
        }
    
    def _check_font_sizes(self, soup: BeautifulSoup) -> int:
        """Check for small font sizes in inline styles"""
        small_count = 0
        
        # Check inline styles
        elements_with_style = soup.find_all(style=True)
        for element in elements_with_style:
            style = element.get('style', '')
            match = re.search(r'font-size:\s*(\d+(?:\.\d+)?)(px|pt)', style)
            if match:
                size = float(match.group(1))
                unit = match.group(2)
                # Convert pt to px (1pt ≈ 1.333px)
                if unit == 'pt':
                    size = size * 1.333
                if size < 14:
                    small_count += 1
        
        # Check style tags
        for style in soup.find_all('style'):
            if style.string:
                matches = re.findall(r'font-size:\s*(\d+(?:\.\d+)?)(px|pt)', style.string)
                for size_str, unit in matches:
                    size = float(size_str)
                    if unit == 'pt':
                        size = size * 1.333
                    if size < 14:
                        small_count += 1
        
        return small_count
    
    def _analyze_compression(self, headers: Dict[str, str], page_data: Dict) -> Dict[str, Any]:
        """Analyze content compression"""
        issues = []
        compression = headers.get('Content-Encoding', '')
        content_length = int(headers.get('Content-Length', 0))
        
        if page_data.get('content'):
            actual_size = len(page_data['content'].encode('utf-8'))
            
            if not compression and actual_size > 1024:  # 1KB threshold
                issues.append(IssueHelper.create_issue(
                    'no_compression',
                    file_size=actual_size
                ))
                compression_ratio = 0
            else:
                # Estimate compression ratio
                if content_length > 0:
                    compression_ratio = round((1 - content_length / actual_size) * 100, 1)
                else:
                    compression_ratio = 0
                
                # Check compression effectiveness
                if compression and compression_ratio < 50 and actual_size > 10240:  # 10KB
                    issues.append({
                        'type': 'poor_compression',
                        'severity': 'notice',
                        'message': f'Poor compression ratio: {compression_ratio}%'
                    })
        else:
            compression_ratio = 0
        
        # Check for better compression algorithms
        if compression == 'gzip' and 'br' not in headers.get('Accept-Encoding', ''):
            issues.append({
                'type': 'suboptimal_compression',
                'severity': 'notice',
                'message': 'Consider using Brotli compression for better performance'
            })
        
        return {
            'compression': compression,
            'ratio': compression_ratio,
            'issues': issues
        }
    
    def _analyze_caching(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze caching headers"""
        issues = []
        cache_control = headers.get('Cache-Control', '')
        max_age = 0
        
        if not cache_control:
            issues.append(IssueHelper.create_issue('no_cache_control'))
        else:
            # Parse cache directives
            directives = [d.strip() for d in cache_control.split(',')]
            
            # Check for no-cache/no-store
            if 'no-cache' in directives or 'no-store' in directives:
                issues.append({
                    'type': 'no_caching',
                    'severity': 'notice',
                    'message': 'Page is not cacheable (no-cache/no-store directive)'
                })
            
            # Extract max-age
            for directive in directives:
                if directive.startswith('max-age='):
                    try:
                        max_age = int(directive.split('=')[1])
                    except:
                        pass
            
            # Check if max-age is too short
            if 0 < max_age < 3600:  # Less than 1 hour
                issues.append({
                    'type': 'short_cache_duration',
                    'severity': 'notice',
                    'message': f'Short cache duration: {max_age} seconds'
                })
        
        # Check ETag
        if not headers.get('ETag') and not headers.get('Last-Modified'):
            issues.append({
                'type': 'no_cache_validation',
                'severity': 'notice',
                'message': 'No ETag or Last-Modified header for cache validation'
            })
        
        # Check Expires header (legacy)
        if headers.get('Expires') and not cache_control:
            issues.append({
                'type': 'legacy_caching',
                'severity': 'notice',
                'message': 'Using legacy Expires header instead of Cache-Control'
            })
        
        return {
            'cache_control': cache_control,
            'max_age': max_age,
            'issues': issues
        }
    
    def _check_sitemap_reference(self, soup: BeautifulSoup, page_data: Dict) -> Dict[str, Any]:
        """Check for sitemap references"""
        locations = []
        
        # Check HTML link
        sitemap_link = soup.find('link', {'rel': 'sitemap'})
        if sitemap_link:
            href = sitemap_link.get('href', '')
            if href:
                locations.append({'type': 'html_link', 'url': urljoin(page_data['url'], href)})
        
        # Check if this might be the homepage to look for common sitemap locations
        parsed = urlparse(page_data['url'])
        if parsed.path in ['/', '', '/index.html', '/index.php']:
            # Common sitemap URLs to check in robots.txt during crawl
            locations.append({'type': 'standard', 'url': f'{parsed.scheme}://{parsed.netloc}/sitemap.xml'})
            locations.append({'type': 'standard', 'url': f'{parsed.scheme}://{parsed.netloc}/sitemap_index.xml'})
        
        return {
            'found': len(locations) > 0,
            'locations': locations
        }
    
    def _analyze_hreflang(self, soup: BeautifulSoup, current_url: str) -> Dict[str, Any]:
        """Analyze hreflang tags for international SEO"""
        issues = []
        hreflang_tags = []
        seen_langs = set()
        has_x_default = False
        
        links = soup.find_all('link', {'rel': 'alternate'})
        for link in links:
            hreflang = link.get('hreflang')
            if hreflang:
                href = link.get('href', '')
                if not href:
                    issues.append({
                        'type': 'empty_hreflang_url',
                        'severity': 'critical',
                        'message': f'Empty URL for hreflang="{hreflang}"'
                    })
                    continue
                
                # Make URL absolute
                href = urljoin(current_url, href)
                
                hreflang_tags.append({
                    'lang': hreflang,
                    'url': href
                })
                
                # Validate hreflang value
                if hreflang == 'x-default':
                    has_x_default = True
                else:
                    # Check format (language-country)
                    if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', hreflang):
                        issues.append({
                            'type': 'invalid_hreflang_format',
                            'severity': 'warning',
                            'message': f'Invalid hreflang format: "{hreflang}" (expected: en-US)'
                        })
                
                # Check for duplicates
                if hreflang in seen_langs:
                    issues.append({
                        'type': 'duplicate_hreflang',
                        'severity': 'critical',
                        'message': f'Duplicate hreflang: "{hreflang}"'
                    })
                seen_langs.add(hreflang)
        
        # Additional checks if hreflang tags exist
        if hreflang_tags:
            # Check for self-reference
            current_lang = None
            for tag in hreflang_tags:
                if self._normalize_url(tag['url']) == self._normalize_url(current_url):
                    current_lang = tag['lang']
                    break
            
            if not current_lang:
                issues.append({
                    'type': 'missing_self_hreflang',
                    'severity': 'warning',
                    'message': 'No hreflang tag points to current page'
                })
            
            # Check for x-default
            if not has_x_default and len(hreflang_tags) > 2:
                issues.append({
                    'type': 'missing_x_default_hreflang',
                    'severity': 'notice',
                    'message': 'Consider adding x-default hreflang for language selector'
                })
        
        return {
            'tags': hreflang_tags,
            'issues': issues
        }
    
    def _check_amp_version(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Check for AMP version of the page"""
        issues = []
        amp_link = soup.find('link', {'rel': 'amphtml'})
        amp_url = ''
        
        if amp_link:
            amp_url = amp_link.get('href', '')
            if not amp_url:
                issues.append({
                    'type': 'empty_amp_url',
                    'severity': 'warning',
                    'message': 'AMP link exists but href is empty'
                })
            else:
                # Validate AMP URL
                if not amp_url.startswith(('http://', 'https://', '/')):
                    issues.append({
                        'type': 'invalid_amp_url',
                        'severity': 'warning',
                        'message': f'Invalid AMP URL: {amp_url}'
                    })
        
        # Check if this IS an AMP page
        html_tag = soup.find('html')
        if html_tag and (html_tag.get('amp') is not None or html_tag.get('⚡') is not None):
            # This is an AMP page, check for canonical
            canonical = soup.find('link', {'rel': 'canonical'})
            if not canonical:
                issues.append({
                    'type': 'amp_missing_canonical',
                    'severity': 'critical',
                    'message': 'AMP page missing canonical link to regular version'
                })
        
        return {
            'url': amp_url,
            'issues': issues
        }
    
    def _analyze_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze structured data (JSON-LD, Microdata, RDFa)"""
        issues = []
        schemas = []
        
        # Check JSON-LD
        json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        schemas.append({
                            'type': 'json-ld',
                            'schema': item.get('@type', 'Unknown'),
                            'data': item
                        })
                else:
                    schemas.append({
                        'type': 'json-ld',
                        'schema': data.get('@type', 'Unknown'),
                        'data': data
                    })
                    
                # Validate common required fields
                self._validate_structured_data(data, issues)
                
            except json.JSONDecodeError as e:
                issues.append({
                    'type': 'invalid_json_ld',
                    'severity': 'critical',
                    'message': f'Invalid JSON-LD: {str(e)}'
                })
            except Exception as e:
                logger.error(f"Error parsing JSON-LD: {e}")
        
        # Check Microdata
        microdata_items = soup.find_all(attrs={'itemscope': True})
        for item in microdata_items:
            item_type = item.get('itemtype', '')
            if item_type:
                schemas.append({
                    'type': 'microdata',
                    'schema': item_type.split('/')[-1] if '/' in item_type else item_type,
                    'data': {'itemtype': item_type}
                })
        
        # Check RDFa
        rdfa_items = soup.find_all(attrs={'typeof': True})
        for item in rdfa_items:
            schemas.append({
                'type': 'rdfa',
                'schema': item.get('typeof', ''),
                'data': {'typeof': item.get('typeof', '')}
            })
        
        # Check for common issues
        if not schemas:
            issues.append({
                'type': 'no_structured_data',
                'severity': 'notice',
                'message': 'No structured data found (JSON-LD, Microdata, or RDFa)'
            })
        
        return {
            'schemas': schemas,
            'issues': issues
        }
    
    def _validate_structured_data(self, data: Any, issues: List[Dict]) -> None:
        """Validate structured data against common requirements"""
        if isinstance(data, list):
            for item in data:
                self._validate_structured_data(item, issues)
            return
        
        if not isinstance(data, dict):
            return
        
        schema_type = data.get('@type', '')
        
        # Common validation rules
        if schema_type == 'Article':
            required = ['headline', 'datePublished', 'author']
            for field in required:
                if field not in data:
                    issues.append({
                        'type': 'missing_structured_data_field',
                        'severity': 'warning',
                        'message': f'Article schema missing required field: {field}'
                    })
        
        elif schema_type == 'Product':
            required = ['name', 'description']
            recommended = ['offers', 'aggregateRating', 'image']
            
            for field in required:
                if field not in data:
                    issues.append({
                        'type': 'missing_structured_data_field',
                        'severity': 'warning',
                        'message': f'Product schema missing required field: {field}'
                    })
            
            for field in recommended:
                if field not in data:
                    issues.append({
                        'type': 'missing_structured_data_field',
                        'severity': 'notice',
                        'message': f'Product schema missing recommended field: {field}'
                    })
        
        elif schema_type == 'Organization':
            recommended = ['logo', 'url', 'contactPoint']
            for field in recommended:
                if field not in data:
                    issues.append({
                        'type': 'missing_structured_data_field',
                        'severity': 'notice',
                        'message': f'Organization schema missing recommended field: {field}'
                    })
    
    def _analyze_pagination(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze pagination implementation"""
        issues = []
        pagination = {}
        
        # Check for rel="prev" and rel="next"
        prev_link = soup.find('link', {'rel': 'prev'})
        next_link = soup.find('link', {'rel': 'next'})
        
        if prev_link:
            pagination['prev'] = prev_link.get('href', '')
        
        if next_link:
            pagination['next'] = next_link.get('href', '')
        
        # Check for common pagination patterns in content
        if not prev_link and not next_link:
            # Look for pagination in common selectors
            pagination_selectors = [
                'nav.pagination', 'div.pagination', 'ul.pagination',
                '.page-numbers', '.pager', 'nav[aria-label*="pagination"]'
            ]
            
            for selector in pagination_selectors:
                element = soup.select_one(selector)
                if element:
                    pagination['has_pagination_ui'] = True
                    
                    # If UI exists but no rel links, it's an issue
                    issues.append({
                        'type': 'missing_pagination_links',
                        'severity': 'notice',
                        'message': 'Pagination UI found but missing rel="prev/next" links'
                    })
                    break
        
        # Check for view-all link
        view_all = soup.find('link', {'rel': 'canonical'})
        if view_all and 'view-all' in view_all.get('href', ''):
            pagination['has_view_all'] = True
        
        return {
            'pagination': pagination,
            'issues': issues
        }
    
    def _detect_js_frameworks(self, soup: BeautifulSoup, page_data: Dict) -> List[str]:
        """Detect JavaScript frameworks and libraries"""
        frameworks = []
        content = page_data.get('content', '')
        
        # Check for common framework indicators
        framework_patterns = {
            'React': [
                r'react(?:\.min)?\.js',
                r'_react',
                r'React\.createElement',
                r'__REACT_DEVTOOLS_GLOBAL_HOOK__'
            ],
            'Vue.js': [
                r'vue(?:\.min)?\.js',
                r'new Vue\(',
                r'v-[a-z]+="',
                r'__VUE_DEVTOOLS_GLOBAL_HOOK__'
            ],
            'Angular': [
                r'angular(?:\.min)?\.js',
                r'ng-[a-z]+="',
                r'\[\(ngModel\)\]',
                r'@angular/'
            ],
            'jQuery': [
                r'jquery(?:\.min)?\.js',
                r'jQuery\(',
                r'\$\(document\)\.ready'
            ],
            'Bootstrap': [
                r'bootstrap(?:\.min)?\.(?:js|css)',
                r'class="[^"]*\b(?:btn|col-|container|row)\b'
            ],
            'WordPress': [
                r'/wp-content/',
                r'/wp-includes/',
                r'wp-json'
            ],
            'Next.js': [
                r'_next/static',
                r'__NEXT_DATA__'
            ],
            'Gatsby': [
                r'gatsby-',
                r'___gatsby'
            ]
        }
        
        for framework, patterns in framework_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    frameworks.append(framework)
                    break
        
        # Check meta generators
        generator = soup.find('meta', {'name': 'generator'})
        if generator:
            content = generator.get('content', '')
            if content and content not in frameworks:
                frameworks.append(content.split()[0])  # Get first word
        
        return list(set(frameworks))  # Remove duplicates
    
    def _analyze_resource_hints(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze resource hints (dns-prefetch, preconnect, prefetch, preload)"""
        hints = {
            'dns-prefetch': [],
            'preconnect': [],
            'prefetch': [],
            'preload': [],
            'prerender': []
        }
        
        for hint_type in hints.keys():
            links = soup.find_all('link', {'rel': hint_type})
            for link in links:
                href = link.get('href', '')
                if href:
                    hint_data = {'url': href}
                    
                    # Additional attributes for preload
                    if hint_type == 'preload':
                        hint_data['as'] = link.get('as', '')
                        hint_data['type'] = link.get('type', '')
                        hint_data['crossorigin'] = link.get('crossorigin', '')
                    
                    hints[hint_type].append(hint_data)
        
        # Count total hints
        total_hints = sum(len(h) for h in hints.values())
        hints['total'] = total_hints
        
        return hints
    
    def _check_pwa(self, soup: BeautifulSoup, headers: Dict[str, str]) -> Dict[str, Any]:
        """Check for Progressive Web App features"""
        issues = []
        features = {
            'has_manifest': False,
            'has_service_worker': False,
            'has_theme_color': False,
            'is_installable': False
        }
        
        # Check for web app manifest
        manifest_link = soup.find('link', {'rel': 'manifest'})
        if manifest_link:
            features['has_manifest'] = True
            manifest_href = manifest_link.get('href', '')
            if not manifest_href:
                issues.append({
                    'type': 'empty_manifest_href',
                    'severity': 'warning',
                    'message': 'Web app manifest link has empty href'
                })
        
        # Check for theme color
        theme_color = soup.find('meta', {'name': 'theme-color'})
        if theme_color:
            features['has_theme_color'] = True
            features['theme_color'] = theme_color.get('content', '')
        
        # Check for service worker registration (basic check in HTML)
        content = str(soup)
        if 'serviceWorker' in content and 'register' in content:
            features['has_service_worker'] = True
        
        # Check if potentially installable
        if features['has_manifest'] and features['has_service_worker']:
            features['is_installable'] = True
        
        # PWA-related meta tags
        pwa_meta_tags = [
            'apple-mobile-web-app-capable',
            'apple-mobile-web-app-status-bar-style',
            'apple-mobile-web-app-title'
        ]
        
        for tag_name in pwa_meta_tags:
            tag = soup.find('meta', {'name': tag_name})
            if tag:
                features[tag_name] = tag.get('content', '')
        
        return {
            'features': features,
            'issues': issues
        }
    
    def _analyze_cookies(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze cookies for security and privacy"""
        issues = []
        cookies = []
        
        # Parse Set-Cookie headers
        set_cookie = headers.get('Set-Cookie', '')
        if set_cookie:
            # Basic cookie parsing (in real implementation, use proper cookie parser)
            cookie_parts = set_cookie.split(';')
            cookie_name = cookie_parts[0].split('=')[0].strip() if cookie_parts else 'unknown'
            
            cookie_info = {
                'name': cookie_name,
                'secure': False,
                'httponly': False,
                'samesite': None
            }
            
            # Check cookie attributes
            for part in cookie_parts[1:]:
                part = part.strip().lower()
                if part == 'secure':
                    cookie_info['secure'] = True
                elif part == 'httponly':
                    cookie_info['httponly'] = True
                elif part.startswith('samesite='):
                    cookie_info['samesite'] = part.split('=')[1]
            
            cookies.append(cookie_info)
            
            # Security checks
            if not cookie_info['secure']:
                issues.append({
                    'type': 'insecure_cookie',
                    'severity': 'warning',
                    'message': f'Cookie "{cookie_name}" missing Secure flag'
                })
            
            if not cookie_info['httponly'] and 'session' in cookie_name.lower():
                issues.append({
                    'type': 'session_cookie_not_httponly',
                    'severity': 'warning',
                    'message': f'Session cookie "{cookie_name}" missing HttpOnly flag'
                })
            
            if not cookie_info['samesite']:
                issues.append({
                    'type': 'cookie_no_samesite',
                    'severity': 'notice',
                    'message': f'Cookie "{cookie_name}" missing SameSite attribute'
                })
        
        return {
            'cookies': cookies,
            'issues': issues
        }
    
    def _calculate_technical_score(self, issues: List[Dict]) -> float:
        """Calculate technical SEO score based on issues"""
        score = 100.0
        
        # Define score deductions
        deductions = {
            'critical': 15,
            'warning': 7,
            'notice': 3
        }
        
        # Calculate deductions
        for issue in issues:
            severity = issue.get('severity', 'notice')
            score -= deductions.get(severity, 0)
        
        # Ensure score doesn't go below 0
        return max(0, score) 