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
    - Performance optimization
    - Security implementation
    - Structured data
    - Social media integration
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
        - Page performance and resource optimization
        - Security implementations and best practices
        - Structured data and rich snippets
        - Social media integration and sharing
        - Technical SEO implementation
        
        Args:
            url: The webpage URL to analyze
            
        Returns:
            Dict containing analysis results and recommendations
        """
        analysis = {
            'mobile_friendly': self._check_mobile_friendly(url),
            'performance': self._analyze_performance(url),
            'security': self._analyze_security(url),
            'structured_data': self._analyze_structured_data(url),
            'social_signals': self._analyze_social_signals(url),
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

    def _analyze_performance(self, url: str) -> Dict:
        """Analyze performance indicators for tfq0seo optimization.
        
        Checks:
        - Resource usage and counts
        - Image optimization
        - Resource minification
        - Browser caching
        - Content compression
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Analyze resource usage
            resources = {
                'images': len(soup.find_all('img')),
                'scripts': len(soup.find_all('script')),
                'styles': len(soup.find_all('link', rel='stylesheet')),
                'total_size': len(response.content),
                'load_time': response.elapsed.total_seconds()
            }
            
            # Check for performance optimizations
            optimizations = {
                'image_optimization': self._check_image_optimization(soup),
                'resource_minification': self._check_resource_minification(soup),
                'browser_caching': self._check_browser_caching(response),
                'compression': self._check_compression(response)
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

    def _analyze_social_signals(self, url: str) -> Dict:
        """Analyze social media integration for tfq0seo optimization.
        
        Examines:
        - Open Graph meta tags
        - Twitter Card implementation
        - Social media profile links
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for social meta tags
            social_meta = {
                'og_tags': self._get_og_tags(soup),
                'twitter_cards': self._get_twitter_cards(soup),
                'social_links': self._find_social_links(soup)
            }
            
            return social_meta
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
        """Check touch element spacing for mobile optimization.
        
        Analyzes interactive elements for proper mobile touch target sizes.
        """
        interactive_elements = soup.find_all(['a', 'button', 'input', 'select'])
        return {
            'total_elements': len(interactive_elements),
            'potentially_small': len([el for el in interactive_elements if self._is_element_small(el)])
        }

    def _check_font_size(self, soup: BeautifulSoup) -> Dict:
        """Check font sizes for mobile readability.
        
        Analyzes text elements for proper mobile-friendly font sizes.
        """
        text_elements = soup.find_all(['p', 'span', 'div'])
        small_fonts = [el for el in text_elements if 'font-size' in el.get('style', '') and self._is_font_small(el)]
        return {
            'total_text_elements': len(text_elements),
            'small_font_elements': len(small_fonts)
        }

    def _check_content_width(self, soup: BeautifulSoup) -> bool:
        """Check content width optimization for mobile devices.
        
        Verifies viewport configuration for responsive design.
        """
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        return bool(viewport and 'width=device-width' in viewport.get('content', ''))

    def _check_image_optimization(self, soup: BeautifulSoup) -> Dict:
        """Check image optimization for tfq0seo performance standards.
        
        Analyzes:
        - Image alt text presence
        - Image dimensions
        - Total image count
        """
        images = soup.find_all('img')
        optimization = {
            'total_images': len(images),
            'missing_alt': len([img for img in images if not img.get('alt')]),
            'large_images': len([img for img in images if self._is_image_large(img)])
        }
        return optimization

    def _check_resource_minification(self, soup: BeautifulSoup) -> Dict:
        """Check resource minification for performance optimization.
        
        Analyzes:
        - JavaScript minification
        - CSS minification
        - Resource count
        """
        scripts = soup.find_all('script')
        styles = soup.find_all('link', rel='stylesheet')
        
        return {
            'total_scripts': len(scripts),
            'total_styles': len(styles),
            'minified_scripts': len([s for s in scripts if '.min.js' in str(s.get('src', ''))]),
            'minified_styles': len([s for s in styles if '.min.css' in str(s.get('href', ''))])
        }

    def _check_browser_caching(self, response: requests.Response) -> bool:
        """Check browser caching configuration for performance optimization.
        
        Verifies presence of caching headers for resource optimization.
        """
        cache_headers = ['cache-control', 'expires', 'etag']
        return any(header in response.headers for header in cache_headers)

    def _check_compression(self, response: requests.Response) -> bool:
        """Check content compression for performance optimization.
        
        Verifies if GZIP or other compression is enabled.
        """
        return 'content-encoding' in response.headers

    def _check_mixed_content(self, html: str) -> bool:
        """Check for mixed content issues in tfq0seo security analysis.
        
        Detects HTTP resources on HTTPS pages.
        """
        soup = BeautifulSoup(html, 'html.parser')
        http_resources = []
        
        for tag in soup.find_all(['img', 'script', 'link', 'iframe']):
            src = tag.get('src') or tag.get('href')
            if src and src.startswith('http:'):
                http_resources.append(src)
        
        return bool(http_resources)

    def _extract_schema_types(self, structured_data: list) -> list:
        """Extract schema types from structured data for tfq0seo analysis.
        
        Identifies implemented Schema.org types for rich snippet optimization.
        """
        schema_types = []
        for data in structured_data:
            if isinstance(data, dict):
                schema_type = data.get('@type')
                if schema_type:
                    schema_types.append(schema_type)
        return schema_types

    def _get_og_tags(self, soup: BeautifulSoup) -> Dict:
        """Extract Open Graph tags for tfq0seo social optimization.
        
        Analyzes social sharing meta tags for Facebook and other platforms.
        """
        og_tags = {}
        for tag in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
            og_tags[tag['property']] = tag.get('content', '')
        return og_tags

    def _get_twitter_cards(self, soup: BeautifulSoup) -> Dict:
        """Extract Twitter Card tags for tfq0seo social optimization.
        
        Analyzes Twitter-specific meta tags for optimal sharing.
        """
        twitter_cards = {}
        for tag in soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
            twitter_cards[tag['name']] = tag.get('content', '')
        return twitter_cards

    def _find_social_links(self, soup: BeautifulSoup) -> Dict:
        """Find social media profile links for tfq0seo social presence analysis.
        
        Identifies links to major social media platforms.
        """
        social_platforms = ['facebook', 'twitter', 'linkedin', 'instagram']
        social_links = {}
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            for platform in social_platforms:
                if platform in href:
                    social_links[platform] = href
        
        return social_links

    def _analyze_url_structure(self, url: str) -> Dict:
        """Analyze URL structure for tfq0seo technical optimization.
        
        Examines:
        - Protocol usage
        - Domain structure
        - Path depth
        - Query parameters
        - URL fragments
        """
        parsed = urlparse(url)
        return {
            'protocol': parsed.scheme,
            'domain': parsed.netloc,
            'path_depth': len([p for p in parsed.path.split('/') if p]),
            'query_parameters': bool(parsed.query),
            'has_fragment': bool(parsed.fragment)
        }

    def _analyze_internal_links(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Analyze internal linking structure for tfq0seo optimization.
        
        Examines:
        - Internal link count
        - External link count
        - Link patterns
        """
        domain = urlparse(base_url).netloc
        links = soup.find_all('a', href=True)
        
        internal_links = []
        external_links = []
        
        for link in links:
            href = link['href']
            if href.startswith('/') or domain in href:
                internal_links.append(href)
            elif href.startswith('http'):
                external_links.append(href)
        
        return {
            'internal_count': len(internal_links),
            'external_count': len(external_links)
        }

    def _check_robots_txt(self, url: str) -> Dict:
        """Check robots.txt configuration for tfq0seo crawl optimization.
        
        Verifies:
        - File existence
        - Content accessibility
        """
        try:
            robots_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt"
            response = requests.get(robots_url, headers=self.headers)
            return {
                'exists': response.status_code == 200,
                'content': response.text if response.status_code == 200 else None
            }
        except:
            return {'exists': False, 'content': None}

    def _check_sitemap(self, url: str) -> Dict:
        """Check XML sitemap for tfq0seo indexing optimization.
        
        Verifies:
        - Sitemap existence
        - XML format compliance
        """
        try:
            sitemap_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/sitemap.xml"
            response = requests.get(sitemap_url, headers=self.headers)
            return {
                'exists': response.status_code == 200,
                'is_xml': 'xml' in response.headers.get('content-type', '').lower()
            }
        except:
            return {'exists': False, 'is_xml': False}

    def _is_element_small(self, element) -> bool:
        """Check if an interactive element is too small for mobile touch targets.
        
        Analyzes element dimensions against tfq0seo mobile standards.
        """
        style = element.get('style', '')
        return 'width' in style and any(f"{i}px" in style for i in range(1, 45))

    def _is_font_small(self, element) -> bool:
        """Check if font size is too small for mobile readability.
        
        Analyzes font sizes against tfq0seo mobile standards.
        """
        style = element.get('style', '')
        return 'font-size' in style and any(f"{i}px" in style for i in range(1, 12))

    def _is_image_large(self, img) -> bool:
        """Check if image dimensions exceed tfq0seo optimization guidelines.
        
        Analyzes image size for performance optimization.
        """
        return img.get('width', '0').isdigit() and int(img.get('width')) > 1000

    def _evaluate_modern_seo(self, analysis: Dict) -> Dict:
        """Evaluate modern SEO aspects and generate tfq0seo recommendations.
        
        Performs comprehensive evaluation of:
        - Mobile optimization status
        - Performance metrics and optimizations
        - Security implementations
        - Structured data usage
        - Social media integration
        - Technical SEO elements
        
        Returns:
            Dict containing:
            - strengths: List of identified SEO strengths
            - weaknesses: List of SEO issues found
            - recommendations: List of actionable improvements
            - education_tips: List of SEO best practices
        """
        evaluation = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }
        
        # Mobile-friendly evaluation
        mobile = analysis.get('mobile_friendly', {})
        if mobile.get('viewport_meta') and mobile.get('responsive_viewport'):
            evaluation['strengths'].append("Website is mobile-friendly")
        else:
            evaluation['weaknesses'].append("Mobile optimization issues detected")
            evaluation['recommendations'].append("Implement proper mobile viewport meta tag")
            evaluation['education_tips'].append(
                "Mobile-friendly websites rank better in mobile search results"
            )

        # Performance evaluation
        perf = analysis.get('performance', {})
        if perf.get('optimizations', {}).get('compression'):
            evaluation['strengths'].append("Content compression is enabled")
        else:
            evaluation['weaknesses'].append("Content compression is not enabled")
            evaluation['recommendations'].append("Enable GZIP compression")
            evaluation['education_tips'].append(
                "Compressed content loads faster, improving user experience and SEO"
            )

        # Security evaluation
        security = analysis.get('security', {})
        if security.get('https'):
            evaluation['strengths'].append("HTTPS is enabled")
        else:
            evaluation['weaknesses'].append("HTTPS is not enabled")
            evaluation['recommendations'].append("Migrate to HTTPS")
            evaluation['education_tips'].append(
                "HTTPS is a ranking factor and builds user trust"
            )

        # Structured data evaluation
        structured = analysis.get('structured_data', {})
        if structured.get('schemas_found', 0) > 0:
            evaluation['strengths'].append("Structured data is implemented")
        else:
            evaluation['weaknesses'].append("No structured data found")
            evaluation['recommendations'].append("Implement relevant Schema.org markup")
            evaluation['education_tips'].append(
                "Structured data helps search engines understand your content better"
            )

        # Social signals evaluation
        social = analysis.get('social_signals', {})
        if social.get('og_tags') or social.get('twitter_cards'):
            evaluation['strengths'].append("Social media meta tags are implemented")
        else:
            evaluation['weaknesses'].append("Missing social media meta tags")
            evaluation['recommendations'].append("Add Open Graph and Twitter Card meta tags")
            evaluation['education_tips'].append(
                "Social media meta tags improve content sharing appearance"
            )

        # Technical SEO evaluation
        technical = analysis.get('technical_seo', {})
        if technical.get('sitemap', {}).get('exists'):
            evaluation['strengths'].append("XML sitemap is present")
        else:
            evaluation['weaknesses'].append("Missing XML sitemap")
            evaluation['recommendations'].append("Create and submit an XML sitemap")
            evaluation['education_tips'].append(
                "Sitemaps help search engines discover and index your content"
            )

        return evaluation 