"""
tfq0seo Performance Analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive performance analysis for SEO optimization.
Analyzes Core Web Vitals, page speed, and technical performance.
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import json
import re

@dataclass
class PerformanceMetrics:
    """Core Web Vitals and performance metrics."""
    # Core Web Vitals
    largest_contentful_paint: Optional[float] = None  # LCP in seconds
    first_input_delay: Optional[float] = None         # FID in milliseconds
    cumulative_layout_shift: Optional[float] = None  # CLS score
    
    # Other Performance Metrics
    first_contentful_paint: Optional[float] = None   # FCP in seconds
    time_to_first_byte: Optional[float] = None       # TTFB in seconds
    speed_index: Optional[float] = None              # SI in seconds
    total_blocking_time: Optional[float] = None      # TBT in milliseconds
    
    # Page Load Metrics
    page_load_time: Optional[float] = None
    dom_content_loaded: Optional[float] = None
    fully_loaded_time: Optional[float] = None
    
    # Resource Metrics
    total_page_size: int = 0
    total_requests: int = 0
    
    # Scores (0-100)
    performance_score: float = 0.0
    accessibility_score: float = 0.0
    seo_score: float = 0.0
    best_practices_score: float = 0.0

@dataclass
class ResourceAnalysis:
    """Analysis of individual resources."""
    url: str
    type: str  # 'image', 'css', 'js', 'font', 'html', 'other'
    size: int
    load_time: float
    is_render_blocking: bool
    is_compressed: bool
    cache_headers: Dict[str, str]
    optimization_score: float
    issues: List[str]
    recommendations: List[str]

@dataclass
class PerformanceAnalysis:
    """Comprehensive performance analysis results."""
    url: str
    metrics: PerformanceMetrics
    resources: List[ResourceAnalysis]
    
    # Technical Analysis
    render_blocking_resources: List[str]
    unused_css: List[str]
    unused_js: List[str]
    image_optimization_opportunities: List[Dict[str, Any]]
    
    # Infrastructure
    server_response_time: float
    compression_enabled: bool
    caching_score: float
    cdn_usage: bool
    
    # Mobile Performance
    mobile_performance_score: float
    mobile_friendly: bool
    
    # Issues and Recommendations
    critical_issues: List[str]
    performance_opportunities: List[Dict[str, Any]]
    overall_score: float

class PerformanceAnalyzer:
    """
    Professional performance analyzer for SEO and user experience.
    
    Features:
    - Core Web Vitals measurement
    - Resource optimization analysis
    - Render-blocking resource detection
    - Image optimization opportunities
    - Caching and compression analysis
    - Mobile performance assessment
    """
    
    def __init__(self):
        self.optimal_thresholds = {
            'lcp': 2.5,      # seconds
            'fid': 100,      # milliseconds
            'cls': 0.1,      # score
            'fcp': 1.8,      # seconds
            'ttfb': 0.6,     # seconds
            'si': 3.4,       # seconds
            'tbt': 200       # milliseconds
        }
        
        self.resource_types = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico'],
            'css': ['.css'],
            'js': ['.js'],
            'font': ['.woff', '.woff2', '.ttf', '.otf', '.eot']
        }

    async def analyze_performance(self, url: str, include_resources: bool = True) -> PerformanceAnalysis:
        """
        Perform comprehensive performance analysis.
        
        Args:
            url: URL to analyze
            include_resources: Whether to analyze individual resources
            
        Returns:
            PerformanceAnalysis object with comprehensive results
        """
        # Initialize analysis object
        analysis = PerformanceAnalysis(
            url=url,
            metrics=PerformanceMetrics(),
            resources=[],
            render_blocking_resources=[],
            unused_css=[],
            unused_js=[],
            image_optimization_opportunities=[],
            server_response_time=0.0,
            compression_enabled=False,
            caching_score=0.0,
            cdn_usage=False,
            mobile_performance_score=0.0,
            mobile_friendly=False,
            critical_issues=[],
            performance_opportunities=[],
            overall_score=0.0
        )
        
        # Measure basic metrics
        await self._measure_basic_metrics(analysis)
        
        # Analyze page structure and resources
        if include_resources:
            await self._analyze_resources(analysis)
        
        # Analyze technical aspects
        await self._analyze_technical_aspects(analysis)
        
        # Calculate scores and identify opportunities
        self._calculate_performance_scores(analysis)
        self._identify_optimization_opportunities(analysis)
        
        return analysis

    async def _measure_basic_metrics(self, analysis: PerformanceAnalysis):
        """Measure basic performance metrics."""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                # Measure TTFB and basic load time
                async with session.get(analysis.url) as response:
                    ttfb = time.time() - start_time
                    analysis.metrics.time_to_first_byte = ttfb
                    analysis.server_response_time = ttfb
                    
                    # Get page content
                    content = await response.text()
                    total_load_time = time.time() - start_time
                    analysis.metrics.page_load_time = total_load_time
                    
                    # Analyze compression
                    content_encoding = response.headers.get('content-encoding', '')
                    analysis.compression_enabled = bool(content_encoding)
                    
                    # Basic page size
                    analysis.metrics.total_page_size = len(content.encode('utf-8'))
                    
                    # Parse HTML for further analysis
                    soup = BeautifulSoup(content, 'html.parser')
                    await self._analyze_dom_structure(analysis, soup)
        
        except Exception as e:
            analysis.critical_issues.append(f"Failed to load page: {str(e)}")

    async def _analyze_dom_structure(self, analysis: PerformanceAnalysis, soup: BeautifulSoup):
        """Analyze DOM structure for performance insights."""
        # Count DOM elements
        dom_size = len(soup.find_all())
        if dom_size > 1500:
            analysis.critical_issues.append(f"Large DOM size: {dom_size} elements")
        
        # Analyze CSS
        css_links = soup.find_all('link', rel='stylesheet')
        css_count = len(css_links)
        analysis.metrics.total_requests += css_count
        
        # Check for render-blocking CSS
        for css_link in css_links:
            href = css_link.get('href')
            if href and not css_link.get('media') == 'print':
                analysis.render_blocking_resources.append(href)
        
        # Analyze JavaScript
        js_scripts = soup.find_all('script', src=True)
        js_count = len(js_scripts)
        analysis.metrics.total_requests += js_count
        
        # Check for render-blocking JavaScript
        for script in js_scripts:
            src = script.get('src')
            if src and not script.get('async') and not script.get('defer'):
                analysis.render_blocking_resources.append(src)
        
        # Analyze images
        images = soup.find_all('img', src=True)
        analysis.metrics.total_requests += len(images)
        
        # Check for image optimization opportunities
        for img in images:
            await self._analyze_image_performance(analysis, img)

    async def _analyze_image_performance(self, analysis: PerformanceAnalysis, img_element):
        """Analyze individual image for performance opportunities."""
        src = img_element.get('src')
        if not src:
            return
        
        # Resolve relative URLs
        if not src.startswith(('http://', 'https://')):
            parsed_url = urlparse(analysis.url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            src = urljoin(base_url, src)
        
        opportunity = {
            'url': src,
            'issues': [],
            'recommendations': [],
            'potential_savings': 0
        }
        
        # Check for missing alt text
        if not img_element.get('alt'):
            opportunity['issues'].append("Missing alt text")
        
        # Check for lazy loading
        if not img_element.get('loading'):
            opportunity['issues'].append("Missing lazy loading attribute")
            opportunity['recommendations'].append("Add loading='lazy' for below-the-fold images")
        
        # Check for responsive images
        if not img_element.get('srcset'):
            opportunity['issues'].append("Missing responsive images")
            opportunity['recommendations'].append("Add srcset for different screen sizes")
        
        # Check file format (basic heuristic)
        if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png']):
            if '.png' in src.lower() and 'photo' in img_element.get('alt', '').lower():
                opportunity['recommendations'].append("Consider using JPEG for photos")
            opportunity['recommendations'].append("Consider modern formats like WebP or AVIF")
        
        if opportunity['issues'] or opportunity['recommendations']:
            analysis.image_optimization_opportunities.append(opportunity)

    async def _analyze_resources(self, analysis: PerformanceAnalysis):
        """Analyze individual resources for optimization opportunities."""
        # This would typically require fetching each resource
        # For now, we'll do a simplified analysis based on HTML
        
        async with aiohttp.ClientSession() as session:
            # Sample a few critical resources
            critical_resources = analysis.render_blocking_resources[:5]  # Limit to 5 for performance
            
            for resource_url in critical_resources:
                try:
                    resource_analysis = await self._analyze_single_resource(session, resource_url, analysis.url)
                    analysis.resources.append(resource_analysis)
                except Exception as e:
                    # Skip failed resources
                    continue

    async def _analyze_single_resource(self, session: aiohttp.ClientSession, 
                                     resource_url: str, base_url: str) -> ResourceAnalysis:
        """Analyze a single resource for optimization."""
        # Resolve relative URLs
        if not resource_url.startswith(('http://', 'https://')):
            resource_url = urljoin(base_url, resource_url)
        
        resource_type = self._determine_resource_type(resource_url)
        
        start_time = time.time()
        
        try:
            async with session.head(resource_url) as response:
                load_time = time.time() - start_time
                
                size = int(response.headers.get('content-length', 0))
                cache_headers = {
                    key: value for key, value in response.headers.items()
                    if key.lower() in ['cache-control', 'expires', 'etag', 'last-modified']
                }
                
                # Check compression
                is_compressed = bool(response.headers.get('content-encoding'))
                
                # Determine if render-blocking
                is_render_blocking = (
                    resource_type in ['css', 'js'] and 
                    'async' not in resource_url and 
                    'defer' not in resource_url
                )
                
                issues = []
                recommendations = []
                
                # Size analysis
                size_thresholds = {'css': 100000, 'js': 150000, 'image': 200000}
                threshold = size_thresholds.get(resource_type, 100000)
                
                if size > threshold:
                    issues.append(f"Large file size: {size} bytes")
                    recommendations.append(f"Optimize file size (target: <{threshold} bytes)")
                
                # Compression analysis
                if not is_compressed and size > 1000:
                    issues.append("Not compressed")
                    recommendations.append("Enable gzip/brotli compression")
                
                # Caching analysis
                if not cache_headers.get('cache-control'):
                    issues.append("No cache headers")
                    recommendations.append("Add appropriate cache headers")
                
                optimization_score = self._calculate_resource_optimization_score(
                    size, is_compressed, bool(cache_headers), is_render_blocking
                )
                
                return ResourceAnalysis(
                    url=resource_url,
                    type=resource_type,
                    size=size,
                    load_time=load_time,
                    is_render_blocking=is_render_blocking,
                    is_compressed=is_compressed,
                    cache_headers=cache_headers,
                    optimization_score=optimization_score,
                    issues=issues,
                    recommendations=recommendations
                )
        
        except Exception as e:
            return ResourceAnalysis(
                url=resource_url,
                type=resource_type,
                size=0,
                load_time=0.0,
                is_render_blocking=False,
                is_compressed=False,
                cache_headers={},
                optimization_score=0.0,
                issues=[f"Failed to analyze: {str(e)}"],
                recommendations=["Check resource accessibility"]
            )

    def _determine_resource_type(self, url: str) -> str:
        """Determine resource type from URL."""
        url_lower = url.lower()
        
        for resource_type, extensions in self.resource_types.items():
            if any(ext in url_lower for ext in extensions):
                return resource_type
        
        return 'other'

    def _calculate_resource_optimization_score(self, size: int, is_compressed: bool, 
                                             has_cache: bool, is_render_blocking: bool) -> float:
        """Calculate optimization score for a resource."""
        score = 100.0
        
        # Size penalty
        if size > 100000:  # > 100KB
            score -= 20
        elif size > 50000:  # > 50KB
            score -= 10
        
        # Compression bonus
        if is_compressed:
            score += 10
        else:
            score -= 15
        
        # Caching bonus
        if has_cache:
            score += 10
        else:
            score -= 10
        
        # Render-blocking penalty
        if is_render_blocking:
            score -= 15
        
        return max(0.0, min(100.0, score))

    async def _analyze_technical_aspects(self, analysis: PerformanceAnalysis):
        """Analyze technical infrastructure aspects."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(analysis.url) as response:
                    # CDN detection (simplified)
                    cdn_headers = ['cf-ray', 'x-cache', 'x-served-by', 'x-amz-cf-id']
                    analysis.cdn_usage = any(
                        header in response.headers for header in cdn_headers
                    )
                    
                    # Caching analysis
                    cache_control = response.headers.get('cache-control', '')
                    expires = response.headers.get('expires', '')
                    etag = response.headers.get('etag', '')
                    
                    caching_score = 0
                    if cache_control:
                        caching_score += 40
                    if expires:
                        caching_score += 30
                    if etag:
                        caching_score += 30
                    
                    analysis.caching_score = caching_score
        
        except Exception as e:
            analysis.critical_issues.append(f"Technical analysis failed: {str(e)}")

    def _calculate_performance_scores(self, analysis: PerformanceAnalysis):
        """Calculate various performance scores."""
        # Performance score based on metrics
        performance_score = 100.0
        
        # TTFB scoring
        if analysis.metrics.time_to_first_byte:
            if analysis.metrics.time_to_first_byte > 1.0:
                performance_score -= 30
            elif analysis.metrics.time_to_first_byte > 0.6:
                performance_score -= 15
        
        # Page load time scoring
        if analysis.metrics.page_load_time:
            if analysis.metrics.page_load_time > 5.0:
                performance_score -= 25
            elif analysis.metrics.page_load_time > 3.0:
                performance_score -= 10
        
        # Render-blocking resources penalty
        if len(analysis.render_blocking_resources) > 3:
            performance_score -= 20
        elif len(analysis.render_blocking_resources) > 0:
            performance_score -= 10
        
        # Compression bonus
        if analysis.compression_enabled:
            performance_score += 5
        else:
            performance_score -= 15
        
        # CDN bonus
        if analysis.cdn_usage:
            performance_score += 5
        
        analysis.metrics.performance_score = max(0.0, min(100.0, performance_score))
        analysis.overall_score = analysis.metrics.performance_score

    def _identify_optimization_opportunities(self, analysis: PerformanceAnalysis):
        """Identify and prioritize optimization opportunities."""
        opportunities = []
        
        # Server response time
        if analysis.server_response_time > 1.0:
            opportunities.append({
                'category': 'Server',
                'issue': f'Slow server response time: {analysis.server_response_time:.2f}s',
                'impact': 'High',
                'savings': f'{analysis.server_response_time - 0.6:.2f}s',
                'recommendation': 'Optimize server configuration or consider faster hosting'
            })
        
        # Render-blocking resources
        if len(analysis.render_blocking_resources) > 0:
            opportunities.append({
                'category': 'Resources',
                'issue': f'{len(analysis.render_blocking_resources)} render-blocking resources',
                'impact': 'High',
                'savings': '1-3s potential improvement',
                'recommendation': 'Eliminate render-blocking resources or defer non-critical CSS/JS'
            })
        
        # Compression
        if not analysis.compression_enabled:
            potential_savings = analysis.metrics.total_page_size * 0.7  # Assume 70% compression
            opportunities.append({
                'category': 'Compression',
                'issue': 'Text compression not enabled',
                'impact': 'Medium',
                'savings': f'{potential_savings/1024:.1f}KB reduction',
                'recommendation': 'Enable gzip or brotli compression'
            })
        
        # Image optimization
        if analysis.image_optimization_opportunities:
            opportunities.append({
                'category': 'Images',
                'issue': f'{len(analysis.image_optimization_opportunities)} image optimization opportunities',
                'impact': 'Medium',
                'savings': '20-50% image size reduction',
                'recommendation': 'Optimize images, use modern formats, implement lazy loading'
            })
        
        # Caching
        if analysis.caching_score < 70:
            opportunities.append({
                'category': 'Caching',
                'issue': f'Poor caching implementation (score: {analysis.caching_score})',
                'impact': 'Medium',
                'savings': 'Faster repeat visits',
                'recommendation': 'Implement proper cache headers and CDN'
            })
        
        analysis.performance_opportunities = opportunities

    def generate_performance_report(self, analysis: PerformanceAnalysis) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            'url': analysis.url,
            'overall_score': analysis.overall_score,
            'metrics': {
                'time_to_first_byte': analysis.metrics.time_to_first_byte,
                'page_load_time': analysis.metrics.page_load_time,
                'total_page_size': analysis.metrics.total_page_size,
                'total_requests': analysis.metrics.total_requests,
                'performance_score': analysis.metrics.performance_score
            },
            'infrastructure': {
                'compression_enabled': analysis.compression_enabled,
                'cdn_usage': analysis.cdn_usage,
                'caching_score': analysis.caching_score
            },
            'issues': {
                'critical_issues': analysis.critical_issues,
                'render_blocking_resources': len(analysis.render_blocking_resources),
                'image_optimization_opportunities': len(analysis.image_optimization_opportunities)
            },
            'opportunities': analysis.performance_opportunities,
            'resource_analysis': [
                {
                    'url': resource.url,
                    'type': resource.type,
                    'size': resource.size,
                    'optimization_score': resource.optimization_score,
                    'issues': resource.issues
                }
                for resource in analysis.resources
            ]
        } 