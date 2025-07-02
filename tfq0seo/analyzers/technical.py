"""
Technical SEO analyzer
"""
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

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
            issues.append({
                'type': 'no_https',
                'severity': 'critical',
                'message': 'Page not served over HTTPS'
            })
        
        # Response headers analysis
        headers = page_data.get('headers', {})
        header_analysis = self._analyze_headers(headers)
        issues.extend(header_analysis['issues'])
        
        # Mobile-friendliness
        mobile_analysis = self._check_mobile_friendly(soup) if soup else {}
        issues.extend(mobile_analysis.get('issues', []))
        
        # Compression
        compression = headers.get('Content-Encoding', '')
        if not compression and page_data.get('content'):
            content_length = len(page_data['content'])
            if content_length > 10000:  # 10KB
                issues.append({
                    'type': 'no_compression',
                    'severity': 'warning',
                    'message': 'Content not compressed (gzip/brotli recommended)'
                })
        
        # Caching headers
        cache_control = headers.get('Cache-Control', '')
        if not cache_control:
            issues.append({
                'type': 'no_cache_control',
                'severity': 'notice',
                'message': 'No Cache-Control header found'
            })
        
        # XML Sitemap reference
        sitemap_in_robots = self._check_sitemap_reference(soup) if soup else False
        
        # Hreflang tags
        hreflang_tags = self._analyze_hreflang(soup) if soup else []
        
        # AMP version
        amp_url = self._check_amp_version(soup) if soup else ''
        
        return {
            'https': is_https,
            'compression': compression,
            'mobile_friendly': mobile_analysis.get('is_mobile_friendly', False),
            'security_headers': header_analysis['security_headers'],
            'cache_control': cache_control,
            'sitemap_referenced': sitemap_in_robots,
            'hreflang_tags': hreflang_tags,
            'amp_url': amp_url,
            'issues': issues
        }
    
    def _analyze_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze HTTP response headers"""
        issues = []
        security_headers = {}
        
        # Check security headers
        security_header_checks = {
            'X-Frame-Options': 'clickjacking',
            'X-Content-Type-Options': 'MIME sniffing',
            'X-XSS-Protection': 'XSS attacks',
            'Strict-Transport-Security': 'HTTPS enforcement',
            'Content-Security-Policy': 'content injection',
            'Referrer-Policy': 'referrer information'
        }
        
        for header, protection in security_header_checks.items():
            if header in headers:
                security_headers[header] = headers[header]
            else:
                issues.append({
                    'type': 'missing_security_header',
                    'severity': 'notice',
                    'message': f'Missing {header} header (protects against {protection})'
                })
        
        # Check for server information disclosure
        server = headers.get('Server', '')
        if server and any(version in server.lower() for version in ['apache/', 'nginx/', 'iis/']):
            issues.append({
                'type': 'server_version_exposed',
                'severity': 'notice',
                'message': 'Server version information exposed'
            })
        
        return {
            'security_headers': security_headers,
            'issues': issues
        }
    
    def _check_mobile_friendly(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Check mobile-friendliness indicators"""
        issues = []
        is_mobile_friendly = True
        
        # Check viewport meta tag
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            is_mobile_friendly = False
            issues.append({
                'type': 'no_viewport',
                'severity': 'critical',
                'message': 'Missing viewport meta tag'
            })
        else:
            content = viewport.get('content', '')
            if 'width=device-width' not in content:
                issues.append({
                    'type': 'viewport_not_responsive',
                    'severity': 'warning',
                    'message': 'Viewport not set to device-width'
                })
        
        # Check for mobile-specific tags
        apple_mobile = soup.find('meta', attrs={'name': 'apple-mobile-web-app-capable'})
        
        # Check font sizes (basic check)
        styles = soup.find_all('style')
        small_fonts = False
        for style in styles:
            if style.string and re.search(r'font-size:\s*(\d+)px', style.string):
                matches = re.findall(r'font-size:\s*(\d+)px', style.string)
                for match in matches:
                    if int(match) < 12:
                        small_fonts = True
                        break
        
        if small_fonts:
            issues.append({
                'type': 'small_font_sizes',
                'severity': 'warning',
                'message': 'Small font sizes detected (<12px)'
            })
        
        return {
            'is_mobile_friendly': is_mobile_friendly,
            'has_viewport': viewport is not None,
            'has_apple_mobile_tag': apple_mobile is not None,
            'issues': issues
        }
    
    def _check_sitemap_reference(self, soup: BeautifulSoup) -> bool:
        """Check if sitemap is referenced in HTML"""
        # Look for sitemap link in HTML
        sitemap_link = soup.find('link', {'rel': 'sitemap'})
        return sitemap_link is not None
    
    def _analyze_hreflang(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Analyze hreflang tags for international SEO"""
        hreflang_tags = []
        
        links = soup.find_all('link', {'rel': 'alternate'})
        for link in links:
            hreflang = link.get('hreflang')
            if hreflang:
                hreflang_tags.append({
                    'lang': hreflang,
                    'url': link.get('href', '')
                })
        
        return hreflang_tags
    
    def _check_amp_version(self, soup: BeautifulSoup) -> str:
        """Check for AMP version of the page"""
        amp_link = soup.find('link', {'rel': 'amphtml'})
        return amp_link.get('href', '') if amp_link else '' 