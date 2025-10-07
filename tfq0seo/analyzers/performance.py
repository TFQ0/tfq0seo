"""Advanced performance analyzer with Core Web Vitals, resource optimization, and network analysis."""

import re
import math
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup, Tag


class ResourceType(Enum):
    """Types of web resources."""
    DOCUMENT = "document"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    IMAGE = "image"
    FONT = "font"
    VIDEO = "video"
    AUDIO = "audio"
    FETCH = "fetch"
    XHR = "xhr"
    OTHER = "other"


class PerformanceLevel(Enum):
    """Performance level categories."""
    FAST = "fast"
    MODERATE = "moderate"
    SLOW = "slow"
    CRITICAL = "critical"


@dataclass
class ResourceProfile:
    """Detailed resource information."""
    url: str
    type: ResourceType
    size: int = 0
    load_time: float = 0.0
    is_render_blocking: bool = False
    is_async: bool = False
    is_deferred: bool = False
    is_lazy: bool = False
    is_critical: bool = False
    is_third_party: bool = False
    is_cached: bool = False
    priority: str = "auto"
    compression: Optional[str] = None
    cache_duration: int = 0


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    load_time: float = 0.0
    dom_content_loaded: float = 0.0
    time_to_first_byte: float = 0.0
    first_contentful_paint: float = 0.0
    largest_contentful_paint: float = 0.0
    first_input_delay: float = 0.0
    cumulative_layout_shift: float = 0.0
    time_to_interactive: float = 0.0
    speed_index: float = 0.0
    total_blocking_time: float = 0.0
    max_potential_fid: float = 0.0
    total_byte_weight: int = 0
    dom_size: int = 0


@dataclass
class NetworkMetrics:
    """Network performance metrics."""
    total_requests: int = 0
    total_size: int = 0
    cached_requests: int = 0
    cached_size: int = 0
    third_party_requests: int = 0
    third_party_size: int = 0
    domains: Set[str] = field(default_factory=set)
    protocols: Dict[str, int] = field(default_factory=dict)
    compression_savings: int = 0


@dataclass
class OptimizationOpportunity:
    """Performance optimization opportunity."""
    title: str
    impact: str  # high, medium, low
    category: str
    estimated_savings_ms: float = 0
    estimated_savings_bytes: int = 0
    description: str = ""
    implementation: str = ""


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create an enhanced issue with optimization guidance."""
    issue = {
        'category': category,
        'severity': severity,
        'message': message
    }
    if details:
        issue['details'] = details
    
    # Add specific optimization recommendations
    if 'image' in message.lower():
        issue['fix'] = "Optimize images: Use WebP/AVIF formats, implement lazy loading, serve responsive images with srcset"
    elif 'script' in message.lower() or 'javascript' in message.lower():
        issue['fix'] = "Optimize scripts: Minify, bundle, use async/defer, implement code splitting, remove unused code"
    elif 'css' in message.lower() or 'stylesheet' in message.lower():
        issue['fix'] = "Optimize CSS: Extract critical CSS, minify, remove unused rules, implement CSS-in-JS for components"
    elif 'cache' in message.lower():
        issue['fix'] = "Implement caching: Set proper Cache-Control headers, use CDN, implement service worker caching"
    elif 'font' in message.lower():
        issue['fix'] = "Optimize fonts: Use font-display: swap, preload critical fonts, subset fonts, use variable fonts"
    else:
        issue['fix'] = "Review performance best practices and implement appropriate optimizations"
    
    return issue


def detect_resource_type(element: Tag, url: str = "") -> ResourceType:
    """Detect the type of a resource from element and URL."""
    if element.name == 'script':
        return ResourceType.SCRIPT
    elif element.name == 'link' and element.get('rel') == ['stylesheet']:
        return ResourceType.STYLESHEET
    elif element.name == 'img':
        return ResourceType.IMAGE
    elif element.name == 'video':
        return ResourceType.VIDEO
    elif element.name == 'audio':
        return ResourceType.AUDIO
    elif element.name == 'link' and 'font' in element.get('as', ''):
        return ResourceType.FONT
    
    # Check by file extension
    if url:
        url_lower = url.lower()
        if any(ext in url_lower for ext in ['.js', '.mjs', '.ts']):
            return ResourceType.SCRIPT
        elif any(ext in url_lower for ext in ['.css', '.scss', '.sass']):
            return ResourceType.STYLESHEET
        elif any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.svg']):
            return ResourceType.IMAGE
        elif any(ext in url_lower for ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']):
            return ResourceType.FONT
        elif any(ext in url_lower for ext in ['.mp4', '.webm', '.ogg', '.mov']):
            return ResourceType.VIDEO
        elif any(ext in url_lower for ext in ['.mp3', '.wav', '.ogg']):
            return ResourceType.AUDIO
    
    return ResourceType.OTHER


def is_third_party(resource_url: str, page_url: str) -> bool:
    """Check if a resource is from a third-party domain."""
    if not resource_url or resource_url.startswith(('data:', 'blob:', '#')):
        return False
    
    try:
        resource_domain = urlparse(resource_url).netloc
        page_domain = urlparse(page_url).netloc
        
        # Remove www prefix for comparison
        resource_domain = resource_domain.replace('www.', '')
        page_domain = page_domain.replace('www.', '')
        
        # Check if same domain or subdomain
        if resource_domain == page_domain:
            return False
        
        # Check if subdomain of main domain
        if resource_domain.endswith('.' + page_domain) or page_domain.endswith('.' + resource_domain):
            return False
        
        return True
    except:
        return False


def calculate_resource_priority(resource: ResourceProfile) -> str:
    """Calculate resource loading priority."""
    if resource.type in [ResourceType.DOCUMENT, ResourceType.STYLESHEET]:
        return "high"
    elif resource.type == ResourceType.SCRIPT and resource.is_render_blocking:
        return "high"
    elif resource.type == ResourceType.FONT:
        return "high"
    elif resource.type == ResourceType.IMAGE and resource.is_critical:
        return "high"
    elif resource.type == ResourceType.SCRIPT and (resource.is_async or resource.is_deferred):
        return "low"
    elif resource.type in [ResourceType.VIDEO, ResourceType.AUDIO]:
        return "low"
    
    return "auto"


def estimate_compression_savings(content: str, content_type: str) -> int:
    """Estimate potential compression savings."""
    if not content:
        return 0
    
    original_size = len(content.encode('utf-8'))
    
    # Estimate compression ratio based on content type
    compression_ratios = {
        'html': 0.3,
        'css': 0.25,
        'js': 0.35,
        'json': 0.2,
        'svg': 0.3,
        'xml': 0.25
    }
    
    ratio = 0.5  # Default
    for type_key, type_ratio in compression_ratios.items():
        if type_key in content_type.lower():
            ratio = type_ratio
            break
    
    estimated_compressed = int(original_size * ratio)
    return original_size - estimated_compressed


def analyze_critical_rendering_path(soup: BeautifulSoup) -> Dict[str, Any]:
    """Analyze the critical rendering path."""
    critical_path = {
        'render_blocking_resources': [],
        'critical_request_chains': [],
        'estimated_savings_ms': 0
    }
    
    # Find render-blocking resources
    # CSS in head without media queries
    for link in soup.find_all('link', rel='stylesheet'):
        media = link.get('media', 'all')
        if media in ['all', 'screen', '']:
            critical_path['render_blocking_resources'].append({
                'type': 'stylesheet',
                'url': link.get('href', ''),
                'impact': 'high'
            })
    
    # Scripts in head without async/defer
    head = soup.find('head')
    if head:
        for script in head.find_all('script', src=True):
            if not script.get('async') and not script.get('defer'):
                critical_path['render_blocking_resources'].append({
                    'type': 'script',
                    'url': script.get('src', ''),
                    'impact': 'high'
                })
    
    # Estimate impact (100ms per blocking resource as rough estimate)
    critical_path['estimated_savings_ms'] = len(critical_path['render_blocking_resources']) * 100
    
    return critical_path


def detect_performance_patterns(soup: BeautifulSoup) -> Dict[str, Any]:
    """Detect common performance patterns and anti-patterns."""
    patterns = {
        'good_patterns': [],
        'bad_patterns': [],
        'opportunities': []
    }
    
    # Good patterns
    if soup.find('link', rel='preconnect'):
        patterns['good_patterns'].append('Uses preconnect for third-party origins')
    
    if soup.find('link', rel='dns-prefetch'):
        patterns['good_patterns'].append('Uses DNS prefetching')
    
    if soup.find('link', rel='preload'):
        patterns['good_patterns'].append('Uses resource preloading')
    
    if soup.find('script', attrs={'type': 'module'}):
        patterns['good_patterns'].append('Uses ES6 modules')
    
    if soup.find('img', loading='lazy'):
        patterns['good_patterns'].append('Implements lazy loading for images')
    
    # Check for service worker
    if soup.find('script', string=re.compile(r'serviceWorker|navigator\.serviceWorker')):
        patterns['good_patterns'].append('Has service worker for offline support')
    
    # Bad patterns
    inline_scripts = soup.find_all('script', src=False)
    large_inline_scripts = [s for s in inline_scripts if s.string and len(s.string) > 1000]
    if large_inline_scripts:
        patterns['bad_patterns'].append(f'Large inline scripts ({len(large_inline_scripts)} found)')
    
    # Multiple jQuery versions
    jquery_scripts = soup.find_all('script', src=re.compile(r'jquery[\.-]'))
    if len(jquery_scripts) > 1:
        patterns['bad_patterns'].append('Multiple jQuery versions detected')
    
    # Inline styles on many elements
    elements_with_style = soup.find_all(style=True)
    if len(elements_with_style) > 20:
        patterns['bad_patterns'].append(f'Excessive inline styles ({len(elements_with_style)} elements)')
    
    # document.write usage
    if soup.find('script', string=re.compile(r'document\.write')):
        patterns['bad_patterns'].append('Uses document.write() which blocks parsing')
    
    # Opportunities
    if not soup.find('link', rel='modulepreload'):
        patterns['opportunities'].append('Consider modulepreload for ES6 modules')
    
    if not soup.find('meta', attrs={'http-equiv': 'Accept-CH'}):
        patterns['opportunities'].append('Consider Client Hints for responsive images')
    
    if not soup.find('link', attrs={'as': 'font', 'crossorigin': True}):
        patterns['opportunities'].append('Preload fonts with crossorigin attribute')
    
    return patterns


def analyze_image_optimization(soup: BeautifulSoup) -> Dict[str, Any]:
    """Analyze image optimization opportunities."""
    image_analysis = {
        'total_images': 0,
        'optimized_formats': 0,
        'lazy_loaded': 0,
        'with_dimensions': 0,
        'responsive_images': 0,
        'issues': [],
        'savings_potential_kb': 0
    }
    
    images = soup.find_all('img')
    image_analysis['total_images'] = len(images)
    
    for img in images:
        src = img.get('src', '')
        
        # Check for modern formats
        if any(fmt in src.lower() for fmt in ['.webp', '.avif']):
            image_analysis['optimized_formats'] += 1
        
        # Check for lazy loading
        if img.get('loading') == 'lazy':
            image_analysis['lazy_loaded'] += 1
        
        # Check for dimensions
        if img.get('width') and img.get('height'):
            image_analysis['with_dimensions'] += 1
        
        # Check for responsive images
        if img.get('srcset') or img.get('sizes'):
            image_analysis['responsive_images'] += 1
    
    # Calculate issues and savings
    if image_analysis['total_images'] > 0:
        # Estimate 30% savings with WebP/AVIF
        unoptimized = image_analysis['total_images'] - image_analysis['optimized_formats']
        image_analysis['savings_potential_kb'] = unoptimized * 50  # Assume 50KB average savings per image
        
        if image_analysis['lazy_loaded'] < image_analysis['total_images'] * 0.5:
            image_analysis['issues'].append('Most images are not lazy loaded')
        
        if image_analysis['with_dimensions'] < image_analysis['total_images'] * 0.8:
            image_analysis['issues'].append('Many images missing width/height attributes')
        
        if image_analysis['responsive_images'] < image_analysis['total_images'] * 0.3:
            image_analysis['issues'].append('Few responsive images implemented')
    
    return image_analysis


def analyze_javascript_optimization(soup: BeautifulSoup) -> Dict[str, Any]:
    """Analyze JavaScript optimization opportunities."""
    js_analysis = {
        'total_scripts': 0,
        'async_scripts': 0,
        'defer_scripts': 0,
        'module_scripts': 0,
        'inline_scripts': 0,
        'minified_scripts': 0,
        'render_blocking': 0,
        'third_party_scripts': [],
        'bundle_analysis': {}
    }
    
    scripts = soup.find_all('script')
    js_analysis['total_scripts'] = len(scripts)
    
    for script in scripts:
        src = script.get('src', '')
        
        if src:
            # External script
            if script.get('async'):
                js_analysis['async_scripts'] += 1
            elif script.get('defer'):
                js_analysis['defer_scripts'] += 1
            else:
                # Check if in head (render-blocking)
                if script.find_parent('head'):
                    js_analysis['render_blocking'] += 1
            
            # Check for modules
            if script.get('type') == 'module':
                js_analysis['module_scripts'] += 1
            
            # Check for minification
            if '.min.js' in src or '-min.js' in src or '.prod.js' in src:
                js_analysis['minified_scripts'] += 1
            
            # Detect third-party scripts
            third_party_patterns = [
                'google-analytics', 'googletagmanager', 'facebook', 
                'twitter', 'linkedin', 'hotjar', 'mixpanel', 'segment',
                'intercom', 'drift', 'hubspot', 'zendesk'
            ]
            
            for pattern in third_party_patterns:
                if pattern in src.lower():
                    js_analysis['third_party_scripts'].append({
                        'name': pattern,
                        'url': src,
                        'async': bool(script.get('async')),
                        'defer': bool(script.get('defer'))
                    })
                    break
        else:
            # Inline script
            js_analysis['inline_scripts'] += 1
            
            # Check size of inline script
            if script.string:
                size = len(script.string)
                if size > 10000:  # 10KB
                    if 'large_inline' not in js_analysis['bundle_analysis']:
                        js_analysis['bundle_analysis']['large_inline'] = []
                    js_analysis['bundle_analysis']['large_inline'].append(size)
    
    return js_analysis


def calculate_performance_score(metrics: PerformanceMetrics, resource_count: int) -> Tuple[int, str]:
    """Calculate overall performance score and grade."""
    score = 100
    
    # Core Web Vitals weights (40% of score)
    # LCP
    if metrics.largest_contentful_paint > 4.0:
        score -= 15
    elif metrics.largest_contentful_paint > 2.5:
        score -= 8
    
    # FID
    if metrics.first_input_delay > 300:
        score -= 15
    elif metrics.first_input_delay > 100:
        score -= 8
    
    # CLS
    if metrics.cumulative_layout_shift > 0.25:
        score -= 10
    elif metrics.cumulative_layout_shift > 0.1:
        score -= 5
    
    # Other metrics (60% of score)
    # Load time
    if metrics.load_time > 5.0:
        score -= 20
    elif metrics.load_time > 3.0:
        score -= 10
    elif metrics.load_time > 2.0:
        score -= 5
    
    # Page weight
    mb_size = metrics.total_byte_weight / (1024 * 1024)
    if mb_size > 5.0:
        score -= 15
    elif mb_size > 3.0:
        score -= 10
    elif mb_size > 2.0:
        score -= 5
    
    # Resource count
    if resource_count > 100:
        score -= 10
    elif resource_count > 70:
        score -= 5
    
    # Time to Interactive
    if metrics.time_to_interactive > 7.3:
        score -= 10
    elif metrics.time_to_interactive > 5.2:
        score -= 5
    
    # Total Blocking Time
    if metrics.total_blocking_time > 600:
        score -= 10
    elif metrics.total_blocking_time > 300:
        score -= 5
    
    # Determine grade
    score = max(0, min(100, score))
    
    if score >= 90:
        grade = 'A'
    elif score >= 80:
        grade = 'B'
    elif score >= 70:
        grade = 'C'
    elif score >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    return score, grade


def generate_performance_budget(metrics: PerformanceMetrics, resources: Dict) -> Dict[str, Any]:
    """Generate a performance budget recommendation."""
    budget = {
        'metrics': {
            'load_time': {'target': 3.0, 'current': metrics.load_time},
            'lcp': {'target': 2.5, 'current': metrics.largest_contentful_paint},
            'fid': {'target': 100, 'current': metrics.first_input_delay},
            'cls': {'target': 0.1, 'current': metrics.cumulative_layout_shift},
            'tti': {'target': 5.0, 'current': metrics.time_to_interactive}
        },
        'resources': {
            'total_size': {'target': 2000000, 'current': metrics.total_byte_weight},  # 2MB
            'images': {'target': 1000000, 'current': 0},  # 1MB for images
            'scripts': {'target': 500000, 'current': 0},  # 500KB for JS
            'stylesheets': {'target': 200000, 'current': 0},  # 200KB for CSS
            'fonts': {'target': 300000, 'current': 0}  # 300KB for fonts
        },
        'counts': {
            'total_requests': {'target': 50, 'current': resources.get('total', 0) if isinstance(resources.get('total'), int) else len(resources.get('total', []))},
            'third_party_requests': {'target': 10, 'current': 0}
        }
    }
    
    # Calculate if budget is met
    for category in budget:
        for metric in budget[category]:
            target = budget[category][metric]['target']
            current = budget[category][metric]['current']
            budget[category][metric]['status'] = 'pass' if current <= target else 'fail'
            if current > 0:
                budget[category][metric]['ratio'] = round(current / target, 2)
    
    return budget


def detect_caching_strategy(soup: BeautifulSoup) -> Dict[str, Any]:
    """Detect caching and CDN usage."""
    caching = {
        'has_service_worker': False,
        'uses_cdn': False,
        'cdn_providers': [],
        'cache_control_hints': [],
        'estimated_cache_hit_rate': 0
    }
    
    # Check for service worker
    if soup.find('script', string=re.compile(r'serviceWorker|navigator\.serviceWorker')):
        caching['has_service_worker'] = True
    
    # Check for CDN usage
    cdn_patterns = {
        'cloudflare': ['cloudflare', 'cdnjs'],
        'cloudfront': ['cloudfront', 'amazonaws'],
        'fastly': ['fastly'],
        'akamai': ['akamai'],
        'maxcdn': ['maxcdn'],
        'jsdelivr': ['jsdelivr'],
        'unpkg': ['unpkg'],
        'staticaly': ['staticaly']
    }
    
    all_resources = soup.find_all(['link', 'script', 'img'], src=True) + \
                   soup.find_all(['link', 'script', 'img'], href=True)
    
    for element in all_resources:
        url = element.get('src', '') or element.get('href', '')
        for provider, patterns in cdn_patterns.items():
            if any(pattern in url.lower() for pattern in patterns):
                if provider not in caching['cdn_providers']:
                    caching['cdn_providers'].append(provider)
                    caching['uses_cdn'] = True
    
    # Estimate cache hit rate based on resource types
    static_resources = len([e for e in all_resources 
                           if any(ext in str(e.get('src', '') or e.get('href', ''))
                                 for ext in ['.css', '.js', '.jpg', '.png', '.woff'])])
    
    if static_resources > 0:
        # Assume 70% cache hit rate for static resources with proper caching
        caching['estimated_cache_hit_rate'] = 70 if caching['uses_cdn'] else 30
    
    return caching


def analyze_performance(soup: BeautifulSoup, url: str, load_time: float = 0, content_length: int = 0) -> Dict[str, Any]:
    """Advanced performance analysis with comprehensive metrics and optimization detection."""
    issues = []
    data = {}
    
    # Initialize performance metrics
    metrics = PerformanceMetrics(
        load_time=load_time,
        total_byte_weight=content_length,
        dom_size=len(soup.find_all())
    )
    
    # Estimate Core Web Vitals based on available data
    # LCP estimate (based on load time and content)
    metrics.largest_contentful_paint = load_time * 0.8 if load_time > 0 else 2.5
    
    # FID estimate (based on JavaScript complexity)
    scripts = soup.find_all('script')
    if len(scripts) > 15:
        metrics.first_input_delay = 300
    elif len(scripts) > 8:
        metrics.first_input_delay = 150
    else:
        metrics.first_input_delay = 50
    
    # CLS estimate (based on layout stability factors)
    cls_factors = 0
    images_without_dimensions = len([img for img in soup.find_all('img') 
                                    if not (img.get('width') and img.get('height'))])
    if images_without_dimensions > 3:
        cls_factors += 2
    
    fonts_loaded = len(soup.find_all('link', rel='preload', as_='font'))
    if fonts_loaded > 4:
        cls_factors += 1
    
    if not soup.find('style'):  # No critical CSS
        cls_factors += 1
    
    metrics.cumulative_layout_shift = min(0.5, cls_factors * 0.1)
    
    # Estimate other metrics
    metrics.time_to_interactive = load_time * 1.5 if load_time > 0 else 3.8
    metrics.first_contentful_paint = load_time * 0.3 if load_time > 0 else 1.8
    metrics.total_blocking_time = len(scripts) * 50  # Rough estimate
    metrics.time_to_first_byte = load_time * 0.2 if load_time > 0 else 0.8
    
    # Store basic metrics
    data['metrics'] = {
        'load_time': round(metrics.load_time, 2),
        'dom_size': metrics.dom_size,
        'content_size_mb': round(content_length / (1024 * 1024), 2),
        'lcp': round(metrics.largest_contentful_paint, 2),
        'fid': round(metrics.first_input_delay),
        'cls': round(metrics.cumulative_layout_shift, 3),
        'fcp': round(metrics.first_contentful_paint, 2),
        'tti': round(metrics.time_to_interactive, 2),
        'tbt': round(metrics.total_blocking_time),
        'ttfb': round(metrics.time_to_first_byte, 2)
    }
    
    # Analyze resources in detail
    resources = defaultdict(list)
    resource_profiles = []
    
    # Scripts
    scripts = soup.find_all('script')
    for script in scripts:
        src = script.get('src', '')
        if src:
            profile = ResourceProfile(
                url=src,
                type=ResourceType.SCRIPT,
                is_async=bool(script.get('async')),
                is_deferred=bool(script.get('defer')),
                is_render_blocking=not (script.get('async') or script.get('defer')),
                is_third_party=is_third_party(src, url)
            )
            profile.priority = calculate_resource_priority(profile)
            resource_profiles.append(profile)
            resources['scripts'].append(src)
    
    # Stylesheets
    stylesheets = soup.find_all('link', rel='stylesheet')
    for link in stylesheets:
        href = link.get('href', '')
        if href:
            profile = ResourceProfile(
                url=href,
                type=ResourceType.STYLESHEET,
                is_render_blocking=True,
                is_third_party=is_third_party(href, url),
                is_critical=(link.find_parent('head') is not None)
            )
            profile.priority = calculate_resource_priority(profile)
            resource_profiles.append(profile)
            resources['stylesheets'].append(href)
    
    # Images
    images = soup.find_all('img')
    for img in images:
        src = img.get('src', '') or img.get('data-src', '')
        if src:
            profile = ResourceProfile(
                url=src,
                type=ResourceType.IMAGE,
                is_lazy=img.get('loading') == 'lazy',
                is_third_party=is_third_party(src, url)
            )
            # Check if above the fold (simplified check)
            parent = img.find_parent(['header', 'nav', 'hero', 'banner'])
            profile.is_critical = parent is not None
            profile.priority = calculate_resource_priority(profile)
            resource_profiles.append(profile)
            resources['images'].append(src)
    
    # Fonts
    font_links = soup.find_all('link', rel='preload', as_='font')
    for link in font_links:
        href = link.get('href', '')
        if href:
            profile = ResourceProfile(
                url=href,
                type=ResourceType.FONT,
                is_critical=True,
                is_third_party=is_third_party(href, url)
            )
            profile.priority = calculate_resource_priority(profile)
            resource_profiles.append(profile)
            resources['fonts'].append(href)
    
    # Videos
    videos = soup.find_all(['video', 'iframe'])
    for video in videos:
        if video.name == 'video':
            src = video.get('src', '')
        else:  # iframe
            src = video.get('src', '')
            if not ('youtube' in src or 'vimeo' in src or 'video' in src):
                continue
        
        if src:
            profile = ResourceProfile(
                url=src,
                type=ResourceType.VIDEO,
                is_lazy=video.get('loading') == 'lazy',
                is_third_party=is_third_party(src, url)
            )
            profile.priority = 'low'
            resource_profiles.append(profile)
            resources['videos'].append(src)
    
    # Calculate total resources
    resources['total'] = len(resource_profiles)
    data['total_resources'] = resources['total']
    
    # Network metrics
    network = NetworkMetrics(
        total_requests=len(resource_profiles),
        total_size=content_length
    )
    
    third_party_resources = [r for r in resource_profiles if r.is_third_party]
    network.third_party_requests = len(third_party_resources)
    
    # Extract unique domains
    for profile in resource_profiles:
        try:
            domain = urlparse(profile.url).netloc
            if domain:
                network.domains.add(domain)
        except:
            pass
    
    data['network_metrics'] = {
        'total_requests': network.total_requests,
        'third_party_requests': network.third_party_requests,
        'unique_domains': len(network.domains),
        'domains': list(network.domains)[:10]  # Top 10 domains
    }
    
    # Analyze critical rendering path
    critical_path = analyze_critical_rendering_path(soup)
    data['critical_rendering_path'] = critical_path
    
    if len(critical_path['render_blocking_resources']) > 3:
        issues.append(create_issue('Performance', 'critical',
            f"{len(critical_path['render_blocking_resources'])} render-blocking resources found",
            {'resources': critical_path['render_blocking_resources'][:5]}))
    
    # Detect performance patterns
    patterns = detect_performance_patterns(soup)
    data['performance_patterns'] = patterns
    
    for bad_pattern in patterns['bad_patterns']:
        issues.append(create_issue('Performance', 'warning', bad_pattern))
    
    # Image optimization analysis
    image_analysis = analyze_image_optimization(soup)
    data['image_optimization'] = image_analysis
    
    if image_analysis['total_images'] > 0:
        if image_analysis['optimized_formats'] < image_analysis['total_images'] * 0.3:
            issues.append(create_issue('Performance', 'warning',
                f"Only {image_analysis['optimized_formats']}/{image_analysis['total_images']} images use modern formats (WebP/AVIF)"))
        
        if image_analysis['lazy_loaded'] < image_analysis['total_images'] * 0.5:
            issues.append(create_issue('Performance', 'warning',
                f"Only {image_analysis['lazy_loaded']}/{image_analysis['total_images']} images are lazy loaded"))
    
    # JavaScript optimization analysis
    js_analysis = analyze_javascript_optimization(soup)
    data['javascript_optimization'] = js_analysis
    
    if js_analysis['render_blocking'] > 2:
        issues.append(create_issue('Performance', 'critical',
            f"{js_analysis['render_blocking']} render-blocking scripts in head"))
    
    if js_analysis['third_party_scripts']:
        issues.append(create_issue('Performance', 'notice',
            f"{len(js_analysis['third_party_scripts'])} third-party scripts detected",
            {'scripts': [s['name'] for s in js_analysis['third_party_scripts']]}))
    
    # Caching strategy detection
    caching = detect_caching_strategy(soup)
    data['caching_strategy'] = caching
    
    if not caching['has_service_worker']:
        issues.append(create_issue('Performance', 'notice',
            'No service worker detected for offline support and caching'))
    
    if not caching['uses_cdn']:
        issues.append(create_issue('Performance', 'warning',
            'Not using CDN for static assets delivery'))
    
    # Generate performance budget
    budget = generate_performance_budget(metrics, resources)
    data['performance_budget'] = budget
    
    # Count budget violations
    budget_violations = 0
    for category in budget:
        for metric in budget[category]:
            if budget[category][metric].get('status') == 'fail':
                budget_violations += 1
    
    if budget_violations > 3:
        issues.append(create_issue('Performance', 'warning',
            f'{budget_violations} performance budget violations detected'))
    
    # Resource priorities
    high_priority = [r for r in resource_profiles if calculate_resource_priority(r) == 'high']
    data['high_priority_resources'] = len(high_priority)
    
    # Check for resource hints
    preconnect = soup.find_all('link', rel='preconnect')
    dns_prefetch = soup.find_all('link', rel='dns-prefetch')
    preload = soup.find_all('link', rel='preload')
    prefetch = soup.find_all('link', rel='prefetch')
    
    data['resource_hints'] = {
        'preconnect': len(preconnect),
        'dns_prefetch': len(dns_prefetch),
        'preload': len(preload),
        'prefetch': len(prefetch)
    }
    
    if len(preconnect) == 0 and network.third_party_requests > 5:
        issues.append(create_issue('Performance', 'warning',
            f'No preconnect hints but {network.third_party_requests} third-party requests'))
    
    # Optimization opportunities
    opportunities = []
    
    # Image optimization
    if image_analysis['savings_potential_kb'] > 100:
        opportunities.append(OptimizationOpportunity(
            title="Optimize images",
            impact="high" if image_analysis['savings_potential_kb'] > 500 else "medium",
            category="images",
            estimated_savings_bytes=image_analysis['savings_potential_kb'] * 1024,
            description=f"Convert {image_analysis['total_images'] - image_analysis['optimized_formats']} images to WebP/AVIF",
            implementation="Use image CDN or build process to automatically convert images"
        ))
    
    # JavaScript optimization
    if js_analysis['render_blocking'] > 0:
        opportunities.append(OptimizationOpportunity(
            title="Eliminate render-blocking scripts",
            impact="high",
            category="javascript",
            estimated_savings_ms=js_analysis['render_blocking'] * 100,
            description=f"Make {js_analysis['render_blocking']} scripts non-blocking",
            implementation="Add async or defer attributes, or move scripts to bottom of body"
        ))
    
    # Bundle size
    if len(resources['scripts']) > 10:
        opportunities.append(OptimizationOpportunity(
            title="Reduce JavaScript bundles",
            impact="medium",
            category="javascript",
            description=f"Consolidate {len(resources['scripts'])} script files",
            implementation="Use webpack or rollup to bundle and tree-shake JavaScript"
        ))
    
    # Critical CSS
    if len(resources['stylesheets']) > 3 and not soup.find('style'):
        opportunities.append(OptimizationOpportunity(
            title="Extract critical CSS",
            impact="high",
            category="css",
            estimated_savings_ms=200,
            description="Inline critical CSS and defer non-critical styles",
            implementation="Use critical CSS tools to extract above-the-fold styles"
        ))
    
    data['optimization_opportunities'] = [
        {
            'title': o.title,
            'impact': o.impact,
            'category': o.category,
            'savings_ms': o.estimated_savings_ms,
            'savings_kb': round(o.estimated_savings_bytes / 1024),
            'description': o.description,
            'implementation': o.implementation
        }
        for o in opportunities
    ]
    
    # Calculate final score and grade
    score, grade = calculate_performance_score(metrics, resources['total'])
    
    # Additional score adjustments based on issues
    for issue in issues:
        if issue['severity'] == 'critical':
            score -= 10
        elif issue['severity'] == 'warning':
            score -= 5
        elif issue['severity'] == 'notice':
            score -= 2
    
    score = max(0, min(100, score))
    
    # Performance level classification
    if metrics.load_time <= 1.0:
        performance_level = PerformanceLevel.FAST
    elif metrics.load_time <= 3.0:
        performance_level = PerformanceLevel.MODERATE
    elif metrics.load_time <= 5.0:
        performance_level = PerformanceLevel.SLOW
    else:
        performance_level = PerformanceLevel.CRITICAL
    
    data['performance_level'] = performance_level.value
    data['grade'] = grade
    
    # Summary recommendations
    recommendations = []
    
    if grade in ['D', 'F']:
        recommendations.append("Critical performance issues detected. Prioritize render-blocking resource elimination.")
    
    if metrics.largest_contentful_paint > 2.5:
        recommendations.append("Improve LCP: Optimize server response time, use CDN, preload critical resources.")
    
    if metrics.cumulative_layout_shift > 0.1:
        recommendations.append("Reduce CLS: Add size attributes to images/videos, avoid inserting content above existing content.")
    
    if metrics.first_input_delay > 100:
        recommendations.append("Improve FID: Break up long tasks, optimize JavaScript execution, use web workers.")
    
    if network.third_party_requests > 10:
        recommendations.append("Reduce third-party impact: Lazy load third-party scripts, use facades for embeds.")
    
    if not caching['uses_cdn']:
        recommendations.append("Implement CDN for global content delivery and improved caching.")
    
    data['recommendations'] = recommendations
    
    return {
        'score': score,
        'grade': grade,
        'issues': issues,
        'data': data,
        'resources': dict(resources)
    }