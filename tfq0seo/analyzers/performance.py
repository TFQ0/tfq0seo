"""
Performance analyzer for page speed and Core Web Vitals - Optimized
"""
from typing import Dict, List, Optional, Any, Tuple
import re
import gzip
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Simple issue creation - fast and lightweight
def create_issue(issue_type: str, severity: str = 'warning', message: str = '', **kwargs) -> Dict:
    """Create a simple issue dictionary"""
    issue = {
        'type': issue_type,
        'severity': severity,
        'message': message or issue_type.replace('_', ' ').title()
    }
    issue.update(kwargs)
    return issue

class PerformanceAnalyzer:
    """Analyzer for page performance metrics"""
    
    # Approximate resource impact on Core Web Vitals
    RESOURCE_WEIGHTS = {
        'render_blocking_css': 0.3,
        'render_blocking_js': 0.4,
        'large_images': 0.2,
        'web_fonts': 0.1
    }
    
    def __init__(self, config):
        self.config = config
    
    def analyze(self, page_data: Dict) -> Dict[str, Any]:
        """Analyze page performance metrics comprehensively"""
        issues = []
        
        # Basic metrics
        load_time = page_data.get('load_time', 0)
        content = page_data.get('content', '')
        headers = page_data.get('response_headers', {})
        
        # Load time analysis
        load_time_analysis = self._analyze_load_time(load_time)
        issues.extend(load_time_analysis['issues'])
        
        # Content size analysis
        size_analysis = self._analyze_content_size(content, headers)
        issues.extend(size_analysis['issues'])
        
        # Resource analysis
        resource_analysis = self._analyze_resources_advanced(content)
        issues.extend(resource_analysis['issues'])
        
        # Compression analysis
        compression_analysis = self._analyze_compression(headers, content)
        issues.extend(compression_analysis['issues'])
        
        # Caching analysis
        caching_analysis = self._analyze_caching(headers)
        issues.extend(caching_analysis['issues'])
        
        # Core Web Vitals estimation
        cwv_estimation = self._estimate_core_web_vitals(
            load_time, resource_analysis, size_analysis
        )
        issues.extend(cwv_estimation['issues'])
        
        # Calculate performance score
        performance_score = self._calculate_performance_score_advanced(
            load_time, size_analysis, resource_analysis, cwv_estimation
        )
        
        # Performance category
        category = self._categorize_performance(performance_score)
        
        return {
            'load_time': round(load_time, 3),
            'content_size': size_analysis,
            'performance_score': performance_score,
            'category': category,
            'resources': resource_analysis['summary'],
            'compression': compression_analysis,
            'caching': caching_analysis,
            'core_web_vitals': cwv_estimation['metrics'],
            'optimization_opportunities': self._identify_optimizations(
                resource_analysis, size_analysis, compression_analysis
            ),
            'issues': issues
        }
    
    def _analyze_load_time(self, load_time: float) -> Dict[str, Any]:
        """Analyze page load time"""
        issues = []
        
        if load_time > self.config.max_page_load_time:
            issues.append(create_issue(
                'slow_page',
                current_value=f'{load_time:.2f}s',
                recommended_value=f'<{self.config.max_page_load_time}s'
            ))
        elif load_time > 2:
            # For moderate load time, we still use slow_page but note it's less severe
            issue = create_issue(
                'slow_page',
                current_value=f'{load_time:.2f}s',
                recommended_value='<2s'
            )
            # Downgrade severity for moderate issues
            issue['severity'] = 'warning'
            issues.append(issue)
        
        return {'issues': issues}
    
    def _analyze_content_size(self, content: str, headers: Dict) -> Dict[str, Any]:
        """Analyze content size and calculate actual sizes"""
        issues = []
        
        # Calculate raw content size
        content_bytes = content.encode('utf-8')
        raw_size = len(content_bytes)
        raw_size_kb = raw_size / 1024
        
        # Check if content was compressed (from headers)
        content_encoding = headers.get('content_encoding', '').lower()
        
        # Estimate compressed size if not already compressed
        compressed_size = raw_size
        if content_encoding in ['gzip', 'br', 'deflate']:
            # Content was already compressed
            compressed_size = raw_size
        else:
            # Estimate compression ratio
            try:
                gzip_compressed = gzip.compress(content_bytes)
                compressed_size = len(gzip_compressed)
            except:
                compressed_size = int(raw_size * 0.3)  # Typical HTML compression ratio
        
        compressed_size_kb = compressed_size / 1024
        
        # Check sizes
        if raw_size_kb > 500:
            issues.append(create_issue(
                'large_page_size',
                current_value=f'{raw_size_kb:.0f}KB uncompressed',
                recommended_value='<500KB'
            ))
        
        if compressed_size_kb > 150:
            issues.append(create_issue(
                'large_page_size',
                current_value=f'{compressed_size_kb:.0f}KB compressed',
                recommended_value='<150KB compressed'
            ))
        
        return {
            'raw_size_bytes': raw_size,
            'raw_size_kb': round(raw_size_kb, 2),
            'compressed_size_bytes': compressed_size,
            'compressed_size_kb': round(compressed_size_kb, 2),
            'compression_ratio': round((1 - compressed_size / raw_size) * 100, 1) if raw_size > 0 else 0,
            'issues': issues
        }
    
    def _analyze_resources_advanced(self, content: str) -> Dict[str, Any]:
        """Analyze page resources with enhanced detail"""
        issues = []
        
        # Extract and analyze different resource types
        scripts = self._extract_scripts(content)
        stylesheets = self._extract_stylesheets(content)
        images = self._extract_images(content)
        fonts = self._extract_fonts(content)
        
        # Analyze render-blocking resources
        render_blocking = {
            'scripts': scripts['render_blocking'],
            'stylesheets': stylesheets['render_blocking'],
            'total': scripts['render_blocking'] + stylesheets['render_blocking']
        }
        
        if render_blocking['total'] > 0:
            issues.append({
                'type': 'render_blocking_resources',
                'severity': 'critical',
                'message': f'{render_blocking["total"]} render-blocking resources found (affects FCP/LCP)'
            })
        
        # Check for resource optimization
        if scripts['total'] > 15:
            issues.append({
                'type': 'too_many_scripts',
                'severity': 'warning',
                'message': f'{scripts["total"]} JavaScript files - consider bundling'
            })
        
        if stylesheets['total'] > 5:
            issues.append({
                'type': 'too_many_stylesheets',
                'severity': 'warning',
                'message': f'{stylesheets["total"]} CSS files - consider bundling'
            })
        
        # Check for modern loading techniques
        if scripts['total'] > 0 and scripts['async'] + scripts['defer'] < scripts['total'] * 0.5:
            issues.append({
                'type': 'few_async_scripts',
                'severity': 'notice',
                'message': 'Most scripts are not loaded asynchronously'
            })
        
        # Check image optimization
        if images['total'] > 5 and images['lazy_loaded'] < images['total'] - 3:
            issues.append({
                'type': 'missing_lazy_loading',
                'severity': 'warning',
                'message': f'Only {images["lazy_loaded"]}/{images["total"]} images use lazy loading'
            })
        
        # Estimate resource sizes (based on typical sizes)
        estimated_sizes = {
            'scripts': scripts['total'] * 35,  # 35KB average per script
            'stylesheets': stylesheets['total'] * 20,  # 20KB average per stylesheet
            'images': images['total'] * 100,  # 100KB average per image
            'fonts': fonts['total'] * 50  # 50KB average per font
        }
        
        total_estimated_kb = sum(estimated_sizes.values())
        
        return {
            'summary': {
                'scripts': scripts,
                'stylesheets': stylesheets,
                'images': images,
                'fonts': fonts,
                'render_blocking': render_blocking,
                'estimated_total_kb': total_estimated_kb
            },
            'issues': issues
        }
    
    def _extract_scripts(self, content: str) -> Dict[str, int]:
        """Extract and analyze script tags"""
        all_scripts = re.findall(r'<script[^>]*>', content, re.IGNORECASE)
        
        return {
            'total': len(all_scripts),
            'inline': len(re.findall(r'<script(?![^>]*\ssrc=)', content, re.IGNORECASE)),
            'external': len(re.findall(r'<script[^>]*\ssrc=', content, re.IGNORECASE)),
            'async': len(re.findall(r'<script[^>]*\sasync', content, re.IGNORECASE)),
            'defer': len(re.findall(r'<script[^>]*\sdefer', content, re.IGNORECASE)),
            'render_blocking': len(re.findall(r'<script(?![^>]*\s(?:async|defer))[^>]*\ssrc=', content, re.IGNORECASE))
        }
    
    def _extract_stylesheets(self, content: str) -> Dict[str, int]:
        """Extract and analyze stylesheet links"""
        link_tags = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', content, re.IGNORECASE)
        style_tags = re.findall(r'<style[^>]*>', content, re.IGNORECASE)
        
        # All external stylesheets are render-blocking unless they have media queries
        render_blocking = len(re.findall(r'<link[^>]+rel=["\']stylesheet["\'](?![^>]*\smedia=["\'](?:print|[^"\']*and[^"\']*\))["\'])', content, re.IGNORECASE))
        
        return {
            'total': len(link_tags) + len(style_tags),
            'external': len(link_tags),
            'inline': len(style_tags),
            'render_blocking': render_blocking
        }
    
    def _extract_images(self, content: str) -> Dict[str, int]:
        """Extract and analyze image tags"""
        img_tags = re.findall(r'<img[^>]*>', content, re.IGNORECASE)
        
        return {
            'total': len(img_tags),
            'lazy_loaded': len(re.findall(r'<img[^>]+loading=["\']lazy["\']', content, re.IGNORECASE)),
            'with_dimensions': len(re.findall(r'<img[^>]+(?:width|height)=', content, re.IGNORECASE))
        }
    
    def _extract_fonts(self, content: str) -> Dict[str, int]:
        """Extract font references"""
        # Look for @font-face in styles and font links
        font_faces = len(re.findall(r'@font-face', content, re.IGNORECASE))
        font_links = len(re.findall(r'<link[^>]+href=[^>]*fonts?\.[^>]*>', content, re.IGNORECASE))
        google_fonts = len(re.findall(r'fonts\.googleapis\.com', content, re.IGNORECASE))
        
        return {
            'total': font_faces + font_links + google_fonts,
            'custom': font_faces,
            'google_fonts': google_fonts
        }
    
    def _analyze_compression(self, headers: Dict, content: str) -> Dict[str, Any]:
        """Analyze compression status"""
        content_encoding = headers.get('content_encoding', '').lower()
        
        is_compressed = content_encoding in ['gzip', 'br', 'deflate']
        compression_type = content_encoding if is_compressed else 'none'
        
        issues = []
        
        if not is_compressed and len(content) > 1024:  # Only flag if content > 1KB
            issues.append(create_issue('no_compression'))
        
        return {
            'enabled': is_compressed,
            'type': compression_type,
            'issues': issues
        }
    
    def _analyze_caching(self, headers: Dict) -> Dict[str, Any]:
        """Analyze caching headers"""
        cache_control = headers.get('cache_control', '')
        expires = headers.get('expires', '')
        etag = headers.get('etag', '')
        last_modified = headers.get('last_modified', '')
        
        issues = []
        cache_info = {
            'cache_control': cache_control,
            'has_expires': bool(expires),
            'has_etag': bool(etag),
            'has_last_modified': bool(last_modified)
        }
        
        # Parse cache-control
        cache_directives = {}
        if cache_control:
            for directive in cache_control.split(','):
                directive = directive.strip()
                if '=' in directive:
                    key, value = directive.split('=', 1)
                    cache_directives[key.strip()] = value.strip()
                else:
                    cache_directives[directive] = True
        
        # Check for caching issues
        if not cache_control:
            issues.append(create_issue('no_cache_control'))
        elif 'no-cache' in cache_directives or 'no-store' in cache_directives:
            # Not in IssueHelper, keep manual for now
            issues.append({
                'type': 'caching_disabled',
                'severity': 'notice',
                'message': 'Caching disabled - consider enabling for static resources'
            })
        elif 'max-age' in cache_directives:
            try:
                max_age = int(cache_directives['max-age'])
                if max_age < 3600:  # Less than 1 hour
                    # Not in IssueHelper, keep manual for now
                    issues.append({
                        'type': 'short_cache_duration',
                        'severity': 'notice',
                        'message': f'Short cache duration ({max_age}s) - consider longer caching for static resources'
                    })
            except:
                pass
        
        return {
            **cache_info,
            'directives': cache_directives,
            'issues': issues
        }
    
    def _estimate_core_web_vitals(self, load_time: float, resource_analysis: Dict, size_analysis: Dict) -> Dict[str, Any]:
        """Estimate Core Web Vitals based on available metrics"""
        issues = []
        
        # Base estimations
        render_blocking_impact = resource_analysis['summary']['render_blocking']['total'] * 0.1
        size_impact = min(size_analysis['compressed_size_kb'] / 100, 2.0)
        
        # First Contentful Paint (FCP) estimation
        fcp = load_time * 0.3 + render_blocking_impact
        
        # Largest Contentful Paint (LCP) estimation
        lcp = load_time * 0.7 + size_impact
        
        # Time to Interactive (TTI) estimation
        script_impact = resource_analysis['summary']['scripts']['total'] * 0.05
        tti = load_time + script_impact + render_blocking_impact
        
        # Cumulative Layout Shift (CLS) estimation
        # Based on images without dimensions and fonts
        images_without_dims = resource_analysis['summary']['images']['total'] - resource_analysis['summary']['images']['with_dimensions']
        cls = min(images_without_dims * 0.05 + resource_analysis['summary']['fonts']['total'] * 0.02, 0.5)
        
        # First Input Delay (FID) estimation
        # Based on JavaScript complexity
        fid = min(resource_analysis['summary']['scripts']['total'] * 10, 300)
        
        # Check against thresholds
        if fcp > 1.8:
            issues.append({
                'type': 'poor_fcp',
                'severity': 'warning',
                'message': f'Estimated FCP is {fcp:.1f}s (good: <1.8s)'
            })
        
        if lcp > 2.5:
            issues.append({
                'type': 'poor_lcp',
                'severity': 'critical',
                'message': f'Estimated LCP is {lcp:.1f}s (good: <2.5s)'
            })
        
        if cls > 0.1:
            issues.append({
                'type': 'poor_cls',
                'severity': 'warning',
                'message': f'Estimated CLS is {cls:.2f} (good: <0.1)'
            })
        
        if fid > 100:
            issues.append({
                'type': 'poor_fid',
                'severity': 'warning',
                'message': f'Estimated FID is {fid}ms (good: <100ms)'
            })
        
        return {
            'metrics': {
                'fcp': round(fcp, 2),
                'lcp': round(lcp, 2),
                'tti': round(tti, 2),
                'cls': round(cls, 3),
                'fid': round(fid, 0)
            },
            'issues': issues
        }
    
    def _calculate_performance_score_advanced(self, load_time: float, size_analysis: Dict, 
                                            resource_analysis: Dict, cwv_estimation: Dict) -> int:
        """Calculate comprehensive performance score"""
        score = 100
        
        # Load time impact (30% weight)
        if load_time > 5:
            score -= 30
        elif load_time > 3:
            score -= 20
        elif load_time > 2:
            score -= 10
        elif load_time > 1:
            score -= 5
        
        # Size impact (20% weight)
        compressed_kb = size_analysis['compressed_size_kb']
        if compressed_kb > 300:
            score -= 20
        elif compressed_kb > 150:
            score -= 10
        elif compressed_kb > 75:
            score -= 5
        
        # Core Web Vitals impact (40% weight)
        cwv = cwv_estimation['metrics']
        
        # LCP scoring
        if cwv['lcp'] > 4:
            score -= 20
        elif cwv['lcp'] > 2.5:
            score -= 10
        
        # CLS scoring
        if cwv['cls'] > 0.25:
            score -= 10
        elif cwv['cls'] > 0.1:
            score -= 5
        
        # FID scoring
        if cwv['fid'] > 300:
            score -= 10
        elif cwv['fid'] > 100:
            score -= 5
        
        # Resource optimization (10% weight)
        render_blocking = resource_analysis['summary']['render_blocking']['total']
        if render_blocking > 5:
            score -= 10
        elif render_blocking > 2:
            score -= 5
        
        return max(0, min(100, score))
    
    def _categorize_performance(self, performance_score: int) -> str:
        """Categorize performance based on score"""
        if performance_score >= 90:
            return 'excellent'
        elif performance_score >= 75:
            return 'good'
        elif performance_score >= 50:
            return 'needs improvement'
        else:
            return 'poor'
    
    def _identify_optimizations(self, resource_analysis: Dict, size_analysis: Dict, 
                               compression_analysis: Dict) -> List[Dict[str, str]]:
        """Identify specific optimization opportunities"""
        optimizations = []
        
        # Compression optimization
        if not compression_analysis.get('enabled'):
            optimizations.append({
                'category': 'compression',
                'priority': 'high',
                'recommendation': 'Enable gzip or Brotli compression',
                'impact': 'Can reduce transfer size by 60-80%'
            })
        
        # Resource optimization
        if resource_analysis['summary']['render_blocking']['total'] > 2:
            optimizations.append({
                'category': 'render_blocking',
                'priority': 'high',
                'recommendation': 'Eliminate render-blocking resources',
                'impact': f'Remove {resource_analysis["summary"]["render_blocking"]["total"]} blocking resources to improve FCP/LCP'
            })
        
        # Script optimization
        if resource_analysis['summary']['scripts']['total'] > 10:
            optimizations.append({
                'category': 'javascript',
                'priority': 'medium',
                'recommendation': 'Reduce JavaScript payload',
                'impact': 'Bundle scripts and remove unused code'
            })
        
        # Image optimization
        images = resource_analysis['summary']['images']
        if images['total'] > 0 and images['lazy_loaded'] < images['total'] * 0.5:
            optimizations.append({
                'category': 'images',
                'priority': 'medium',
                'recommendation': 'Implement lazy loading for images',
                'impact': 'Defer loading of off-screen images'
            })
        
        # Size optimization
        if size_analysis['raw_size_kb'] > 200:
            optimizations.append({
                'category': 'page_weight',
                'priority': 'medium',
                'recommendation': 'Reduce page weight',
                'impact': 'Minify HTML, CSS, and JavaScript'
            })
        
        return optimizations 