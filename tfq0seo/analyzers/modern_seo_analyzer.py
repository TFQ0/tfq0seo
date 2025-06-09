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
        """Check mobile-friendliness indicators for tfq0seo compliance.
        
        Analyzes:
        - Viewport configuration
        - Touch element spacing
        - Font sizes
        - Content width optimization
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            responsive_meta = viewport and 'width=device-width' in viewport.get('content', '')
            
            # Check for mobile-friendly features
            mobile_checks = {
                'viewport_meta': bool(viewport),
                'responsive_viewport': responsive_meta,
                'touch_elements_spacing': self._check_touch_elements(soup),
                'font_size': self._check_font_size(soup),
                'content_width': self._check_content_width(soup)
            }
            
            return mobile_checks
        except Exception as e:
            return {'error': str(e)}

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
        """Analyze security aspects for tfq0seo compliance.
        
        Checks:
        - HTTPS implementation
        - Security headers
        - Mixed content detection
        - Content security policies
        """
        try:
            response = requests.get(url, headers=self.headers)
            
            security_checks = {
                'https': url.startswith('https'),
                'hsts': 'strict-transport-security' in response.headers,
                'xss_protection': 'x-xss-protection' in response.headers,
                'content_security': 'content-security-policy' in response.headers,
                'mixed_content': self._check_mixed_content(response.text)
            }
            
            return security_checks
        except Exception as e:
            return {'error': str(e)}

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

    def _check_touch_elements(self, soup: BeautifulSoup) -> Dict:
        """Check touch element spacing for mobile optimization."""
        interactive_elements = soup.find_all(['a', 'button', 'input', 'select'])
        return {
            'total_elements': len(interactive_elements),
            'potentially_small': len([el for el in interactive_elements if self._is_element_small(el)])
        }

    def _check_font_size(self, soup: BeautifulSoup) -> Dict:
        """Check font sizes for mobile readability."""
        text_elements = soup.find_all(['p', 'span', 'div'])
        small_fonts = [el for el in text_elements if 'font-size' in el.get('style', '') and self._is_font_small(el)]
        return {
            'total_text_elements': len(text_elements),
            'small_font_elements': len(small_fonts)
        }

    def _check_content_width(self, soup: BeautifulSoup) -> bool:
        """Check content width optimization for mobile devices."""
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        return bool(viewport and 'width=device-width' in viewport.get('content', ''))

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
        """Evaluate modern SEO features and generate recommendations."""
        evaluation = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }
        
        # Mobile-friendly evaluation
        if analysis['mobile_friendly']['viewport_meta']:
            evaluation['strengths'].append("Proper mobile viewport configuration")
        else:
            evaluation['weaknesses'].append("Missing mobile viewport meta tag")
            evaluation['recommendations'].append("Add proper viewport meta tag")
        
        # HTML structure evaluation
        if analysis['html_structure']['optimizations']['html_validation']['has_doctype']:
            evaluation['strengths'].append("Valid HTML structure with doctype")
        else:
            evaluation['weaknesses'].append("Missing HTML doctype declaration")
            evaluation['recommendations'].append("Add proper HTML5 doctype")
        
        # Security evaluation
        if analysis['security']['https']:
            evaluation['strengths'].append("HTTPS implementation")
        else:
            evaluation['weaknesses'].append("Not using HTTPS")
            evaluation['recommendations'].append("Implement HTTPS security")
        
        # Structured data evaluation
        if analysis['structured_data']['schemas_found'] > 0:
            evaluation['strengths'].append("Implemented structured data")
        else:
            evaluation['weaknesses'].append("Missing structured data")
            evaluation['recommendations'].append("Add relevant Schema.org markup")
        
        # Technical SEO evaluation
        if analysis['technical_seo']['robots_txt']['exists']:
            evaluation['strengths'].append("Robots.txt implemented")
        else:
            evaluation['weaknesses'].append("Missing robots.txt")
            evaluation['recommendations'].append("Add robots.txt file")
        
        return evaluation 