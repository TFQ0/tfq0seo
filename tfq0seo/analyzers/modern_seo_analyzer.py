from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse
from ..utils.error_handler import handle_analysis_error

class ModernSEOAnalyzer:
    """tfq0seo Modern Features Analyzer - Analyzes modern SEO aspects of a webpage.
    
    Provides comprehensive analysis of modern SEO features including:
    - Mobile-friendliness
    - HTML structure
    - Security implementation
    - Structured data
    - Technical SEO aspects
    """
    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            'User-Agent': config['crawling']['user_agent']
        }

    @handle_analysis_error
    def analyze(self, url: str) -> Dict:
        """Perform comprehensive tfq0seo modern SEO analysis.
        
        Analyzes multiple aspects of modern SEO best practices including:
        - Mobile optimization and responsiveness
        - HTML structure and optimization
        - Security implementations and best practices
        - Structured data and rich snippets
        - Technical SEO implementation
        
        Args:
            url: The webpage URL to analyze
            
        Returns:
            Dict containing analysis results and recommendations
        """
        analysis = {
            'mobile_friendly': self._check_mobile_friendly(url),
            'html_structure': self._analyze_html_structure(url),
            'security': self._analyze_security(url),
            'structured_data': self._analyze_structured_data(url),
            'technical_seo': self._analyze_technical_seo(url)
        }
        
        return self._evaluate_modern_seo(analysis)

    def _check_mobile_friendly(self, url: str) -> Dict:
        """Check mobile-friendliness indicators with enhanced accuracy.
        
        Analyzes:
        - Viewport configuration with detailed validation
        - Touch element spacing with precise measurements
        - Font sizes with readability assessment
        - Content width optimization
        - Mobile-specific features
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Enhanced viewport analysis
            viewport_analysis = self._analyze_viewport_comprehensive(soup)
            
            # Detailed touch elements analysis
            touch_analysis = self._analyze_touch_elements_detailed(soup)
            
            # Font size analysis with context
            font_analysis = self._analyze_font_sizes_detailed(soup)
            
            # Content width and responsive design analysis
            responsive_analysis = self._analyze_responsive_design(soup)
            
            # Mobile-specific features
            mobile_features = self._analyze_mobile_features(soup)
            
            mobile_checks = {
                'viewport_meta': viewport_analysis['has_viewport'],
                'viewport_analysis': viewport_analysis,
                'responsive_viewport': viewport_analysis['is_responsive'],
                'touch_elements_spacing': touch_analysis,
                'font_size': font_analysis,
                'content_width': responsive_analysis['content_width_optimized'],
                'responsive_design': responsive_analysis,
                'mobile_features': mobile_features,
                'mobile_score': self._calculate_mobile_score(viewport_analysis, touch_analysis, font_analysis, responsive_analysis)
            }
            
            return mobile_checks
            
        except Exception as e:
            return {
                'error': str(e),
                'mobile_score': 0,
                'analysis_failed': True
            }

    def _analyze_html_structure(self, url: str) -> Dict:
        """Analyze HTML structure for tfq0seo optimization.
        
        Checks:
        - Resource usage and counts
        - Image optimization
        - HTML validation
        - Content structure
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Analyze resource usage
            resources = {
                'images': len(soup.find_all('img')),
                'scripts': len(soup.find_all('script')),
                'styles': len(soup.find_all('link', rel='stylesheet')),
                'total_size': len(response.content)
            }
            
            # Check for HTML optimizations
            optimizations = {
                'image_optimization': self._check_image_optimization(soup),
                'html_validation': self._check_html_validation(soup),
                'content_structure': self._check_content_structure(soup)
            }
            
            return {
                'resources': resources,
                'optimizations': optimizations
            }
        except Exception as e:
            return {'error': str(e)}

    def _analyze_security(self, url: str) -> Dict:
        """Analyze security aspects for tfq0seo compliance with enhanced accuracy.
        
        Checks:
        - HTTPS implementation with comprehensive validation
        - SSL certificate validity and chain
        - Security headers analysis
        - Mixed content detection with context
        - Content security policies validation
        """
        try:
            # Make request with comprehensive security checks
            session = requests.Session()
            session.headers.update(self.headers)
            
            # Set timeouts and SSL verification
            response = session.get(url, verify=True, timeout=15, allow_redirects=True)
            
            # Check if the final URL (after redirects) uses HTTPS
            final_url = response.url
            uses_https = final_url.startswith('https://')
            original_https = url.startswith('https://')
            
            # Enhanced SSL certificate validation
            ssl_valid = False
            ssl_details = {}
            if uses_https:
                try:
                    import ssl
                    import socket
                    from urllib.parse import urlparse
                    import datetime
                    
                    parsed = urlparse(final_url)
                    context = ssl.create_default_context()
                    
                    with socket.create_connection((parsed.hostname, 443), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=parsed.hostname) as ssock:
                            ssl_valid = True
                            cert = ssock.getpeercert()
                            
                            # Extract certificate details
                            ssl_details = {
                                'issuer': dict(x[0] for x in cert['issuer']),
                                'subject': dict(x[0] for x in cert['subject']),
                                'version': cert.get('version'),
                                'not_before': cert.get('notBefore'),
                                'not_after': cert.get('notAfter'),
                                'serial_number': cert.get('serialNumber')
                            }
                            
                            # Check certificate expiration
                            not_after = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                            ssl_details['expires_soon'] = (not_after - datetime.datetime.now()).days < 30
                            
                except ssl.SSLError as ssl_err:
                    ssl_details['ssl_error'] = str(ssl_err)
                except Exception as e:
                    ssl_details['validation_error'] = str(e)
            
            # Enhanced security headers analysis
            security_headers = self._analyze_security_headers(response.headers)
            
            # Mixed content detection with context
            mixed_content_issues = self._analyze_mixed_content(response.text, uses_https)
            
            security_checks = {
                'https': uses_https,
                'ssl_certificate_valid': ssl_valid,
                'ssl_details': ssl_details,
                'original_url_https': original_https,
                'redirected_to_https': not original_https and uses_https,
                'redirect_chain': [r.url for r in response.history] + [response.url],
                'hsts': 'strict-transport-security' in response.headers,
                'hsts_details': self._analyze_hsts(response.headers.get('strict-transport-security', '')),
                'security_headers': security_headers,
                'mixed_content': mixed_content_issues,
                'security_score': self._calculate_security_score(uses_https, ssl_valid, security_headers)
            }
            
            return security_checks
            
        except requests.exceptions.SSLError as ssl_err:
            return {
                'https': url.startswith('https://'),
                'ssl_certificate_valid': False,
                'ssl_error': True,
                'ssl_error_details': str(ssl_err),
                'error': 'SSL certificate verification failed',
                'recommendations': [
                    'Check SSL certificate validity and configuration',
                    'Ensure certificate chain is complete',
                    'Verify domain name matches certificate'
                ]
            }
        except requests.exceptions.ConnectionError as conn_err:
            return {
                'https': url.startswith('https://'),
                'ssl_certificate_valid': False,
                'connection_error': True,
                'error': f'Connection failed: {str(conn_err)}',
                'recommendations': [
                    'Check if the website is accessible',
                    'Verify DNS resolution',
                    'Check firewall and network settings'
                ]
            }
        except Exception as e:
            return {
                'error': f'Security analysis failed: {str(e)}',
                'https': url.startswith('https://'),
                'ssl_certificate_valid': False
            }

    def _analyze_security_headers(self, headers: Dict) -> Dict:
        """Analyze security headers comprehensively."""
        security_headers = {
            'strict_transport_security': headers.get('strict-transport-security'),
            'x_frame_options': headers.get('x-frame-options'),
            'x_content_type_options': headers.get('x-content-type-options'),
            'x_xss_protection': headers.get('x-xss-protection'),
            'content_security_policy': headers.get('content-security-policy'),
            'referrer_policy': headers.get('referrer-policy'),
            'permissions_policy': headers.get('permissions-policy'),
            'expect_ct': headers.get('expect-ct')
        }
        
        # Analyze each header
        analysis = {}
        for header, value in security_headers.items():
            if value:
                analysis[header] = {
                    'present': True,
                    'value': value,
                    'analysis': self._analyze_security_header_value(header, value)
                }
            else:
                analysis[header] = {
                    'present': False,
                    'recommendation': self._get_security_header_recommendation(header)
                }
        
        return analysis

    def _analyze_security_header_value(self, header: str, value: str) -> Dict:
        """Analyze individual security header values."""
        if header == 'strict_transport_security':
            return self._analyze_hsts(value)
        elif header == 'x_frame_options':
            return {'valid': value.upper() in ['DENY', 'SAMEORIGIN'], 'directive': value}
        elif header == 'x_content_type_options':
            return {'valid': value.lower() == 'nosniff', 'directive': value}
        elif header == 'x_xss_protection':
            return {'valid': '1' in value, 'directive': value}
        elif header == 'content_security_policy':
            return {'present': True, 'length': len(value), 'has_unsafe': 'unsafe' in value.lower()}
        else:
            return {'present': True, 'value': value}

    def _analyze_hsts(self, hsts_header: str) -> Dict:
        """Analyze HSTS header in detail."""
        if not hsts_header:
            return {'present': False}
        
        analysis = {'present': True}
        
        # Parse max-age
        if 'max-age=' in hsts_header:
            try:
                max_age = int(hsts_header.split('max-age=')[1].split(';')[0])
                analysis['max_age'] = max_age
                analysis['max_age_sufficient'] = max_age >= 31536000  # 1 year
            except ValueError:
                analysis['max_age_error'] = True
        
        # Check for includeSubDomains
        analysis['include_subdomains'] = 'includeSubDomains' in hsts_header
        
        # Check for preload
        analysis['preload'] = 'preload' in hsts_header
        
        return analysis

    def _get_security_header_recommendation(self, header: str) -> str:
        """Get recommendation for missing security headers."""
        recommendations = {
            'strict_transport_security': 'Add HSTS header: Strict-Transport-Security: max-age=31536000; includeSubDomains',
            'x_frame_options': 'Add X-Frame-Options header: X-Frame-Options: DENY or SAMEORIGIN',
            'x_content_type_options': 'Add X-Content-Type-Options header: X-Content-Type-Options: nosniff',
            'x_xss_protection': 'Add XSS Protection header: X-XSS-Protection: 1; mode=block',
            'content_security_policy': 'Implement Content Security Policy header',
            'referrer_policy': 'Add Referrer-Policy header for privacy protection'
        }
        return recommendations.get(header, f'Consider implementing {header} header')

    def _analyze_mixed_content(self, html: str, is_https: bool) -> Dict:
        """Analyze mixed content issues with context."""
        if not is_https:
            return {'analysis_skipped': 'Site does not use HTTPS'}
        
        import re
        
        # Find HTTP resources in HTTPS page
        http_resources = {
            'images': re.findall(r'<img[^>]+src=["\']http://[^"\']+["\']', html, re.IGNORECASE),
            'stylesheets': re.findall(r'<link[^>]+href=["\']http://[^"\']+["\']', html, re.IGNORECASE),
            'scripts': re.findall(r'<script[^>]+src=["\']http://[^"\']+["\']', html, re.IGNORECASE),
            'iframes': re.findall(r'<iframe[^>]+src=["\']http://[^"\']+["\']', html, re.IGNORECASE),
            'other': re.findall(r'["\']http://[^"\']+["\']', html)
        }
        
        total_issues = sum(len(resources) for resources in http_resources.values())
        
        return {
            'has_mixed_content': total_issues > 0,
            'total_issues': total_issues,
            'breakdown': {k: len(v) for k, v in http_resources.items()},
            'severity': 'high' if http_resources['scripts'] or http_resources['iframes'] else 'medium' if total_issues > 0 else 'none'
        }

    def _calculate_security_score(self, https: bool, ssl_valid: bool, security_headers: Dict) -> int:
        """Calculate overall security score."""
        score = 0
        
        # HTTPS and SSL (40 points)
        if https and ssl_valid:
            score += 40
        elif https:
            score += 25
        
        # Security headers (60 points total)
        header_scores = {
            'strict_transport_security': 15,
            'x_frame_options': 10,
            'x_content_type_options': 10,
            'x_xss_protection': 10,
            'content_security_policy': 15
        }
        
        for header, points in header_scores.items():
            if security_headers.get(header, {}).get('present'):
                score += points
        
        return min(100, score)

    def _analyze_structured_data(self, url: str) -> Dict:
        """Analyze structured data implementation for tfq0seo optimization.
        
        Examines:
        - Schema.org markup presence
        - Schema types used
        - JSON-LD implementation
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all structured data
            structured_data = []
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    structured_data.append(data)
                except json.JSONDecodeError:
                    continue
            
            return {
                'schemas_found': len(structured_data),
                'schema_types': self._extract_schema_types(structured_data)
            }
        except Exception as e:
            return {'error': str(e)}

    def _analyze_technical_seo(self, url: str) -> Dict:
        """Analyze technical SEO aspects for tfq0seo compliance.
        
        Examines:
        - URL structure and parameters
        - Internal linking patterns
        - HTTP response status
        - Robots.txt configuration
        - XML sitemap implementation
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            technical_checks = {
                'url_structure': self._analyze_url_structure(url),
                'internal_links': self._analyze_internal_links(soup, url),
                'http_status': response.status_code,
                'response_headers': dict(response.headers),
                'robots_txt': self._check_robots_txt(url),
                'sitemap': self._check_sitemap(url)
            }
            
            return technical_checks
        except Exception as e:
            return {'error': str(e)}

    def _analyze_viewport_comprehensive(self, soup: BeautifulSoup) -> Dict:
        """Comprehensive viewport meta tag analysis."""
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        
        if not viewport:
            return {
                'has_viewport': False,
                'is_responsive': False,
                'issues': ['Missing viewport meta tag'],
                'recommendations': ['Add viewport meta tag with width=device-width, initial-scale=1']
            }
        
        content = viewport.get('content', '')
        analysis = {
            'has_viewport': True,
            'content': content,
            'width_device': 'width=device-width' in content,
            'initial_scale': 'initial-scale=1' in content,
            'user_scalable': 'user-scalable=no' not in content,
            'issues': [],
            'recommendations': []
        }
        
        # Check for common issues
        if not analysis['width_device']:
            analysis['issues'].append('Viewport does not set width=device-width')
            analysis['recommendations'].append('Add width=device-width to viewport')
        
        if not analysis['initial_scale']:
            analysis['issues'].append('Viewport does not set initial-scale=1')
            analysis['recommendations'].append('Add initial-scale=1 to viewport')
        
        if not analysis['user_scalable']:
            analysis['issues'].append('Viewport disables user scaling (accessibility issue)')
            analysis['recommendations'].append('Allow user scaling for accessibility')
        
        analysis['is_responsive'] = analysis['width_device'] and analysis['initial_scale']
        
        return analysis

    def _analyze_touch_elements_detailed(self, soup: BeautifulSoup) -> Dict:
        """Detailed touch element spacing analysis."""
        interactive_elements = soup.find_all(['a', 'button', 'input', 'select', 'textarea'])
        
        analysis = {
            'total_elements': len(interactive_elements),
            'potentially_small': 0,
            'very_small': 0,
            'elements_analysis': [],
            'issues': []
        }
        
        for element in interactive_elements:
            element_analysis = self._analyze_single_touch_element(element)
            analysis['elements_analysis'].append(element_analysis)
            
            if element_analysis['likely_too_small']:
                analysis['potentially_small'] += 1
            if element_analysis['very_small']:
                analysis['very_small'] += 1
        
        if analysis['very_small'] > 0:
            analysis['issues'].append(f'{analysis["very_small"]} elements are very small for touch')
        if analysis['potentially_small'] > 3:
            analysis['issues'].append('Many elements may be too small for comfortable touch interaction')
        
        return analysis

    def _analyze_single_touch_element(self, element) -> Dict:
        """Analyze a single touch element."""
        style = element.get('style', '')
        classes = element.get('class', [])
        
        analysis = {
            'tag': element.name,
            'has_explicit_size': False,
            'likely_too_small': False,
            'very_small': False,
            'style': style
        }
        
        # Check for explicit sizing in style
        if 'width' in style or 'height' in style:
            analysis['has_explicit_size'] = True
            # Basic heuristic for small sizes
            if any(f'{i}px' in style for i in range(1, 44)):  # Less than 44px
                analysis['likely_too_small'] = True
            if any(f'{i}px' in style for i in range(1, 32)):  # Less than 32px
                analysis['very_small'] = True
        
        # Check for small-indicating classes
        small_classes = ['btn-sm', 'btn-xs', 'small', 'tiny', 'mini']
        if any(small_class in ' '.join(classes) for small_class in small_classes):
            analysis['likely_too_small'] = True
        
        return analysis

    def _check_image_optimization(self, soup: BeautifulSoup) -> Dict:
        """Check image optimization for tfq0seo compliance."""
        images = soup.find_all('img')
        return {
            'total_images': len(images),
            'missing_alt': len([img for img in images if not img.get('alt')]),
            'large_images': len([img for img in images if self._is_image_large(img)])
        }

    def _check_html_validation(self, soup: BeautifulSoup) -> Dict:
        """Check HTML structure and validation."""
        return {
            'has_doctype': bool(soup.find('doctype')),
            'has_html_tag': bool(soup.find('html')),
            'has_head_tag': bool(soup.find('head')),
            'has_body_tag': bool(soup.find('body'))
        }

    def _check_content_structure(self, soup: BeautifulSoup) -> Dict:
        """Check content structure and hierarchy."""
        headings = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}
        return {
            'headings': headings,
            'paragraphs': len(soup.find_all('p')),
            'lists': len(soup.find_all(['ul', 'ol']))
        }

    def _check_mixed_content(self, html: str) -> bool:
        """Check for mixed content security issues."""
        return 'http://' in html and 'https://' in html

    def _extract_schema_types(self, structured_data: list) -> list:
        """Extract schema types from structured data."""
        schema_types = []
        for data in structured_data:
            if isinstance(data, dict) and '@type' in data:
                schema_types.append(data['@type'])
        return schema_types

    def _analyze_url_structure(self, url: str) -> Dict:
        """Analyze URL structure for SEO optimization."""
        parsed = urlparse(url)
        return {
            'protocol': parsed.scheme,
            'domain': parsed.netloc,
            'path': parsed.path,
            'has_query': bool(parsed.query),
            'has_fragment': bool(parsed.fragment)
        }

    def _analyze_internal_links(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Analyze internal linking structure."""
        links = soup.find_all('a', href=True)
        internal_links = [link for link in links if base_url in link['href'] or link['href'].startswith('/')]
        return {
            'total_links': len(links),
            'internal_links': len(internal_links)
        }

    def _check_robots_txt(self, url: str) -> Dict:
        """Check robots.txt implementation."""
        try:
            robots_url = f"{url.rstrip('/')}/robots.txt"
            response = requests.get(robots_url, headers=self.headers)
            return {
                'exists': response.status_code == 200,
                'size': len(response.text) if response.status_code == 200 else 0
            }
        except Exception:
            return {'exists': False, 'size': 0}

    def _check_sitemap(self, url: str) -> Dict:
        """Check XML sitemap implementation."""
        try:
            sitemap_url = f"{url.rstrip('/')}/sitemap.xml"
            response = requests.get(sitemap_url, headers=self.headers)
            return {
                'exists': response.status_code == 200,
                'is_xml': 'xml' in response.headers.get('content-type', '').lower()
            }
        except Exception:
            return {'exists': False, 'is_xml': False}

    def _is_element_small(self, element) -> bool:
        """Check if an element is too small for touch interaction."""
        style = element.get('style', '')
        return 'width' in style and any(f"{i}px" in style for i in range(1, 48))

    def _is_font_small(self, element) -> bool:
        """Check if font size is too small for mobile viewing."""
        style = element.get('style', '')
        return 'font-size' in style and any(f"{i}px" in style for i in range(1, 12))

    def _is_image_large(self, img) -> bool:
        """Check if an image is potentially too large."""
        return any(dim and int(dim) > 1000 for dim in [img.get('width'), img.get('height')])

    def _evaluate_modern_seo(self, analysis: Dict) -> Dict:
        """Evaluate modern SEO features and generate tfq0seo recommendations."""
        evaluation = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }

        # Mobile-friendliness evaluation
        mobile_friendly_analysis = analysis.get('mobile_friendly', {})
        if mobile_friendly_analysis.get('viewport_meta'):
            evaluation['strengths'].append("Viewport meta tag is present")
        else:
            evaluation['weaknesses'].append("Missing viewport meta tag")
            evaluation['recommendations'].append(
                'Add a viewport meta tag to ensure proper rendering on mobile devices'
            )

        if mobile_friendly_analysis.get('responsive_viewport'):
            evaluation['strengths'].append("Responsive viewport is configured")

        # Security evaluation
        security_analysis = analysis.get('security', {})
        if security_analysis.get('https'):
            evaluation['strengths'].append("Site uses HTTPS")
        else:
            evaluation['weaknesses'].append("Site does not use HTTPS")
            evaluation['recommendations'].append(
                "Migrate to HTTPS to improve security and SEO"
            )

        # Structured data evaluation
        structured_data_analysis = analysis.get('structured_data', {})
        if structured_data_analysis.get('schemas_found', 0) > 0:
            evaluation['strengths'].append("Structured data (Schema.org) is implemented")
        else:
            evaluation['weaknesses'].append("Missing structured data")
            evaluation['recommendations'].append(
                "Implement structured data to improve search engine understanding"
            )

        return evaluation 