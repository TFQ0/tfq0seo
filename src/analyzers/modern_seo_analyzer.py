from typing import Dict, Any, List, Optional, cast
import asyncio
from bs4 import BeautifulSoup
from ..utils.async_base import AsyncAnalyzer, async_retry
from ..utils.security import (
    InputSanitizer,
    SecurityHeaders,
    RequestValidator,
    RateLimitConfig,
    RateLimiter
)
from ..utils.performance import (
    MemoryConfig,
    AdvancedCache,
    ConnectionPool,
    HTMLParser,
    BatchProcessor,
    memory_efficient
)
from ..utils.types import (
    AsyncAnalysisContext,
    ModernSEOAnalysis,
    SecurityChecks,
    PerformanceMetrics
)
from ..utils.error_handler import create_error, URLFetchError
import json
from urllib.parse import urlparse
from ..utils.error_handler import handle_analysis_error

class ModernSEOAnalyzer(AsyncAnalyzer):
    """Analyzes modern SEO aspects of a webpage.
    
    Features:
    - Mobile friendliness
    - Performance metrics
    - Security checks
    - Structured data
    - Social signals
    """
    
    def __init__(self):
        """Initialize analyzer."""
        super().__init__()
        self.input_sanitizer = InputSanitizer()
        self.security_headers = SecurityHeaders()
        self.request_validator = RequestValidator()
        self.html_parser = HTMLParser()
        self.connection_pool = ConnectionPool(max_connections=100)

    async def __aenter__(self):
        """Initialize async resources."""
        await super().__aenter__()
        self.session = await self.connection_pool.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up async resources."""
        await self.connection_pool.close()
        await super().__aexit__(exc_type, exc_val, exc_tb)

    @async_retry(max_retries=3)
    async def analyze(self, url: str) -> ModernSEOAnalysis:
        """Analyze modern SEO aspects of a webpage.
        
        Args:
            url: URL to analyze
            
        Returns:
            Modern SEO analysis results
            
        Raises:
            URLFetchError: If URL fetch fails
        """
        # Sanitize and validate URL
        url = self.input_sanitizer.sanitize_url(url)
        
        if not self.request_manager:
            raise URLFetchError(create_error(
                'NO_REQUEST_MANAGER',
                'Request manager not initialized'
            ))
        
        # Fetch page content
        content = await self.request_manager.fetch(url)
        
        # Parse HTML efficiently
        soup = self.html_parser.parse(content)
        
        # Run analyses concurrently
        mobile_friendly, performance, security, structured_data, social = await asyncio.gather(
            self._check_mobile_friendly(soup),
            self._analyze_performance(soup),
            self._check_security(url),
            self._extract_structured_data(soup),
            self._analyze_social_signals(soup)
        )
        
        result = {
            'mobile_friendly': mobile_friendly,
            'performance': performance,
            'security': security,
            'structured_data': structured_data,
            'social_signals': social
        }
        
        return result

    async def analyze_batch(self, urls: List[str]) -> Dict[str, ModernSEOAnalysis]:
        """Analyze multiple URLs in batches.
        
        Args:
            urls: List of URLs to analyze
            
        Returns:
            Dictionary mapping URLs to their analysis results
        """
        # First check cache for all URLs
        cached_results = {}
        urls_to_analyze = []
        
        for url in urls:
            cached = await self.cache.get(url)
            if cached:
                cached_results[url] = cast(ModernSEOAnalysis, cached)
            else:
                urls_to_analyze.append(url)
        
        # Analyze remaining URLs in batches
        if urls_to_analyze:
            batch_results = await self.batch_processor.process_batch(
                urls_to_analyze,
                self.analyze,
                max_concurrent=10
            )
            
            # Combine results
            for url, result in zip(urls_to_analyze, batch_results):
                cached_results[url] = result
        
        return cached_results

    async def _check_mobile_friendly(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Check mobile-friendliness indicators.
        
        Analyzes:
        - Viewport configuration
        - Touch element spacing
        - Font sizes
        - Content width optimization
        """
        try:
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

    @memory_efficient(limit_mb=100)
    async def _analyze_performance(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze performance indicators.
        
        Checks:
        - Resource usage and counts
        - Image optimization
        - Resource minification
        - Browser caching
        - Content compression
        """
        try:
            # Analyze resource usage
            resources = {
                'images': len(soup.find_all('img')),
                'scripts': len(soup.find_all('script')),
                'styles': len(soup.find_all('link', rel='stylesheet')),
                'total_size': len(str(soup)),
                'load_time': 0  # Not available without actual request
            }
            
            # Check for performance optimizations
            optimizations = {
                'image_optimization': self._check_image_optimization(soup),
                'resource_minification': self._check_resource_minification(soup)
            }
            
            return {
                'resources': resources,
                'optimizations': optimizations
            }
        except Exception as e:
            return {'error': str(e)}

    async def _check_security(self, url: str) -> Dict[str, Any]:
        """Analyze security aspects.
        
        Checks:
        - HTTPS implementation
        - Mixed content detection
        """
        try:
            security_checks = {
                'https': url.startswith('https'),
                'mixed_content': self._check_mixed_content(str(soup))
            }
            
            return security_checks
        except Exception as e:
            return {'error': str(e)}

    @memory_efficient(limit_mb=150)
    async def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data.
        
        Examines:
        - Schema.org markup presence
        - Schema types used
        - JSON-LD implementation
        """
        try:
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

    async def _analyze_social_signals(self, soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
        """Analyze social media integration.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Dictionary of social media signals
        """
        # Use partial parsing for meta tags
        meta_soup = self.html_parser.parse(str(soup), targets=['meta'])
        
        social_meta = {
            'facebook': {},
            'twitter': {},
            'linkedin': {},
            'pinterest': {}
        }
        
        # Process meta tags efficiently
        for meta in meta_soup.find_all('meta'):
            property_val = meta.get('property', '')
            name_val = meta.get('name', '')
            content = meta.get('content', '')
            
            if property_val.startswith('og:'):
                social_meta['facebook'][property_val] = content
            elif name_val.startswith('twitter:'):
                social_meta['twitter'][name_val] = content
            elif property_val.startswith('linkedin:'):
                social_meta['linkedin'][property_val] = content
            elif name_val.startswith('pinterest:'):
                social_meta['pinterest'][name_val] = content
        
        return social_meta

    def _check_resource_minification(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Check resource minification.
        
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

    def _check_mixed_content(self, html: str) -> bool:
        """Check for mixed content issues.
        
        Detects HTTP resources on HTTPS pages.
        """
        soup = BeautifulSoup(html, 'html.parser')
        http_resources = []
        
        for tag in soup.find_all(['img', 'script', 'link', 'iframe']):
            src = tag.get('src') or tag.get('href')
            if src and src.startswith('http:'):
                http_resources.append(src)
        
        return bool(http_resources)

    def _find_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Find social media profile links.
        
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

    def _analyze_url_structure(self, url: str) -> Dict[str, Any]:
        """Analyze URL structure.
        
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

    def _analyze_internal_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, int]:
        """Analyze internal linking structure.
        
        Examines:
        - Internal link count
        - External link count
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

    def _check_touch_elements(self, soup: BeautifulSoup) -> bool:
        """Check if interactive elements are touch-friendly."""
        for element in soup.find_all(['button', 'a', 'input']):
            if self._is_element_small(element):
                return False
        return True

    def _check_font_size(self, soup: BeautifulSoup) -> bool:
        """Check if font sizes are mobile-friendly."""
        for element in soup.find_all(['p', 'span', 'div']):
            if self._is_font_small(element):
                return False
        return True

    def _check_content_width(self, soup: BeautifulSoup) -> bool:
        """Check if content width is optimized for mobile."""
        for img in soup.find_all('img'):
            if self._is_image_large(img):
                return False
        return True

    def _is_element_small(self, element) -> bool:
        """Check if an interactive element is too small for mobile touch targets."""
        style = element.get('style', '')
        return 'width' in style and any(f"{i}px" in style for i in range(1, 45))

    def _is_font_small(self, element) -> bool:
        """Check if font size is too small for mobile readability."""
        style = element.get('style', '')
        return 'font-size' in style and any(f"{i}px" in style for i in range(1, 12))

    def _is_image_large(self, img) -> bool:
        """Check if image dimensions exceed optimization guidelines."""
        return img.get('width', '0').isdigit() and int(img.get('width')) > 1000

    def _extract_schema_types(self, structured_data: List[Dict]) -> List[str]:
        """Extract schema types from structured data."""
        types = []
        for data in structured_data:
            if isinstance(data, dict) and '@type' in data:
                types.append(data['@type'])
        return types 