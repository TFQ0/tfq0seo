"""Static performance inspection with explicit measurement provenance."""

import re
import math
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup, Tag
from .common import (classify_url, document_base_url, is_nonblocking_script,
                     make_issue, resolve_url, score_grade)
from ..rules import RuleDefinition, RuleCollector, register_rules, score_findings, recommendations_for
from ..page_facts import PageFacts, ensure_page_facts


_SCRIPT_REFERENCE = 'https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/script'
PERFORMANCE_RULES = (
    RuleDefinition('performance.blocking_scripts', 'performance', 'warning',
        'Review parser-blocking scripts in a browser trace. Use defer for order-dependent scripts or async for independent scripts only when compatible with their behavior.',
        'External classic JavaScript in head lacks async/defer. Static attributes identify parser-blocking candidates; timing impact is not measured.',
        (_SCRIPT_REFERENCE, 'https://html.spec.whatwg.org/multipage/scripting.html#the-script-element',
         'https://mimesniff.spec.whatwg.org/#javascript-mime-type'), '2026-09-14'),
    RuleDefinition('performance.responsive_images', 'performance', 'notice',
        'Check image display sizes and transfer sizes across devices; supply responsive sources where they improve the actual image use case.',
        'Image elements lack srcset/sizes hints. Small fixed-size images and vector images may need no alternatives; the 30% threshold is a local review heuristic.',
        ('https://web.dev/articles/responsive-images',), '2026-09-14', scored=False),
    RuleDefinition('performance.large_inline_scripts', 'performance', 'notice',
        'Measure the cost of the inline JavaScript before changing its loading or caching strategy.',
        'Executable inline script text exceeds 1000 characters; this local review threshold does not measure transfer or execution cost.',
        (_SCRIPT_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('performance.jquery_references', 'performance', 'notice',
        'Inspect the referenced scripts for duplicate libraries before removing any dependency.',
        'Multiple script URLs contain a jQuery naming pattern; plugins and custom filenames may be legitimate.',
        (_SCRIPT_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('performance.inline_styles', 'performance', 'notice',
        'Review style maintenance and browser measurements before moving repeated styles into a stylesheet.',
        'More than 20 elements have inline style attributes; this local count does not establish a rendering problem.',
        ('https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/style',), '2026-09-14', scored=False),
    RuleDefinition('performance.document_write', 'performance', 'notice',
        'Review whether document.write is actually executed and replace it with DOM APIs when feasible.',
        'Executable inline JavaScript contains a document.write text reference; comments and unreachable code can match.',
        ('https://developer.mozilla.org/en-US/docs/Web/API/Document/write',), '2026-09-14', scored=False),
)
register_rules(PERFORMANCE_RULES)


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
    size: Optional[int] = None
    load_time: Optional[float] = None
    is_render_blocking: bool = False
    is_async: bool = False
    is_deferred: bool = False
    is_lazy: bool = False
    is_critical: bool = False
    is_third_party: bool = False
    is_cached: Optional[bool] = None
    priority: str = "auto"
    compression: Optional[str] = None
    cache_duration: Optional[int] = None


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    load_time: Optional[float] = None
    dom_content_loaded: Optional[float] = None
    time_to_first_byte: Optional[float] = None
    first_contentful_paint: Optional[float] = None
    largest_contentful_paint: Optional[float] = None
    first_input_delay: Optional[float] = None
    interaction_to_next_paint: Optional[float] = None
    cumulative_layout_shift: Optional[float] = None
    time_to_interactive: Optional[float] = None
    speed_index: Optional[float] = None
    total_blocking_time: Optional[float] = None
    max_potential_fid: Optional[float] = None
    total_byte_weight: Optional[int] = None
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
    estimated_savings_ms: Optional[float] = None
    estimated_savings_bytes: Optional[int] = None
    description: str = ""
    implementation: str = ""


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None,
                 rule_id: Optional[str] = None, evidence: Any = None,
                 confidence: str = 'high') -> Dict[str, Any]:
    """Compatibility helper; registered rule identity supplies the guidance."""
    return make_issue(category, severity, message, details, rule_id, evidence,
                      confidence=confidence)


def _is_classic_javascript(script: Tag) -> bool:
    """Exclude module scripts and data blocks from parser-blocking checks."""
    if not (script.has_attr('type') if isinstance(script, Tag) else 'type' in script):
        language = str(script.get('language', ''))
        script_type = ('text/' + language) if language else 'text/javascript'
    else:
        declared_type = str(script.get('type', ''))
        script_type = 'text/javascript' if declared_type == '' else declared_type.strip(' \t\n\r\f')
    script_type = script_type.lower()
    return script_type in (
        'application/ecmascript', 'application/javascript', 'application/x-ecmascript',
        'application/x-javascript', 'text/ecmascript', 'text/javascript', 'text/javascript1.0',
        'text/javascript1.1', 'text/javascript1.2', 'text/javascript1.3', 'text/javascript1.4',
        'text/javascript1.5', 'text/jscript', 'text/livescript', 'text/x-ecmascript', 'text/x-javascript',
    )


def _is_executable_script(script: Tag) -> bool:
    return _is_classic_javascript(script) or str(script.get('type', '')).strip().lower() == 'module'


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
    """Classify resource references using the same URL rules as link analysis."""
    return classify_url(resource_url, page_url) == 'external'


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


def estimate_compression_savings(content: str, content_type: str) -> Optional[int]:
    """Actual transfer savings require compressed and uncompressed byte counts."""
    return None


def analyze_critical_rendering_path(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Analyze the critical rendering path."""
    critical_path = {
        'render_blocking_resources': [],
        'critical_request_chains': [],
        'estimated_savings_ms': None,
        'status': 'static_candidates',
        'source': 'html',
        'critical_request_chains_status': 'unknown'
    }
    
    # Find render-blocking resources
    # CSS in head without media queries
    links = ([record['attrs'] for record in facts.link_tags if 'stylesheet' in record['attrs'].get('rel', [])]
             if facts is not None else soup.find_all('link', rel='stylesheet'))
    for link in links:
        media = link.get('media', 'all')
        if media in ['all', 'screen', '']:
            critical_path['render_blocking_resources'].append({
                'type': 'stylesheet',
                'url': link.get('href', ''),
                'impact': 'high'
            })
    
    # Scripts in head without async/defer
    if facts is not None:
        scripts = [record['attrs'] for record in facts.scripts if record['in_head'] and 'src' in record['attrs']]
    else:
        head = soup.find('head')
        scripts = head.find_all('script', src=True) if head else []
    for script in scripts:
        if _is_classic_javascript(script) and not is_nonblocking_script(script):
            critical_path['render_blocking_resources'].append({
                'type': 'script', 'url': script.get('src', ''), 'impact': 'high'
            })
    
    return critical_path


def _script_records(soup: BeautifulSoup, facts: Optional[PageFacts] = None) -> List[Dict[str, Any]]:
    if facts is not None:
        return facts.scripts
    return [{'attrs': dict(script.attrs), 'text': script.string or '',
             'in_head': script.find_parent('head') is not None, 'index': index}
            for index, script in enumerate(soup.find_all('script'))]


def detect_performance_patterns(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Describe source patterns using the shared attribute and script snapshot."""
    patterns = {'good_patterns': [], 'bad_patterns': [], 'opportunities': [],
                'status': 'heuristic', 'source': 'html'}
    links = [record['attrs'] for record in facts.link_tags] if facts is not None else soup.find_all('link')
    scripts = _script_records(soup, facts)
    images = [record['attrs'] for record in facts.images] if facts is not None else soup.find_all('img')
    metas = [record['attrs'] for record in facts.meta] if facts is not None else soup.find_all('meta')
    for relation, message in (
        ('preconnect', 'Declares preconnect hints'), ('dns-prefetch', 'Uses DNS prefetching'),
        ('preload', 'Uses resource preloading'),
    ):
        if any(relation in link.get('rel', []) for link in links):
            patterns['good_patterns'].append(message)
    if any(script['attrs'].get('type') == 'module' for script in scripts):
        patterns['good_patterns'].append('Uses ES6 modules')
    if any(image.get('loading') == 'lazy' for image in images):
        patterns['good_patterns'].append('Implements lazy loading for images')
    if any(re.search(r'serviceWorker|navigator\.serviceWorker', script['text']) for script in scripts):
        patterns['good_patterns'].append('Contains a service worker code reference; registration was not verified')
    inline_scripts = [script for script in scripts if 'src' not in script['attrs'] and _is_executable_script(script['attrs'])]
    large_inline_scripts = [script for script in inline_scripts if len(script['text']) > 1000]
    if large_inline_scripts:
        patterns['bad_patterns'].append(f'Large inline scripts ({len(large_inline_scripts)} found)')
    jquery_scripts = [script for script in scripts if re.search(r'jquery[\.-]', script['attrs'].get('src', ''))]
    if len(jquery_scripts) > 1:
        patterns['bad_patterns'].append('Multiple jQuery-named script references; review for duplicate loading')
    elements_with_style = soup.find_all(style=True)
    if len(elements_with_style) > 20:
        patterns['bad_patterns'].append(f'Excessive inline styles ({len(elements_with_style)} elements)')
    if any(re.search(r'document\.write', script['text']) for script in scripts):
        patterns['bad_patterns'].append('Uses document.write() which blocks parsing')
    if not any('modulepreload' in link.get('rel', []) for link in links):
        patterns['opportunities'].append('Consider modulepreload for ES6 modules')
    if not any(meta.get('http-equiv') == 'Accept-CH' for meta in metas):
        patterns['opportunities'].append('Consider Client Hints for responsive images')
    if not any(link.get('as') == 'font' and 'crossorigin' in link for link in links):
        patterns['opportunities'].append('Preload fonts with crossorigin attribute')
    collector = RuleCollector('performance')
    observations = (
        ('performance.large_inline_scripts', bool(large_inline_scripts),
         {'scripts': [{'characters': len(script['text'])} for script in large_inline_scripts], 'threshold_characters': 1000},
         f'Large inline script text ({len(large_inline_scripts)} found)', bool(inline_scripts)),
        ('performance.jquery_references', len(jquery_scripts) > 1,
         {'urls': [script['attrs'].get('src', '') for script in jquery_scripts]},
         'Multiple jQuery-named script references; review for duplicate loading', bool(jquery_scripts)),
        ('performance.inline_styles', len(elements_with_style) > 20,
         {'element_count': len(elements_with_style), 'threshold': 20},
         f'Inline styles found on {len(elements_with_style)} elements', bool(elements_with_style)),
        ('performance.document_write', any(re.search(r'document\.write', script['text']) for script in inline_scripts),
         {'matches': [script['text'] for script in inline_scripts if re.search(r'document\.write', script['text'])]},
         'Inline script text contains document.write; execution was not verified', bool(inline_scripts)),
    )
    for rule_id, failed, evidence, message, applicable in observations:
        collector.check(rule_id, failed, evidence=evidence, message=message, category='Performance',
                        applicable=applicable, reason='Requires matching HTML elements.', confidence='low')
    patterns['findings'] = collector.issues
    patterns['rule_results'] = collector.results
    return patterns


def analyze_image_optimization(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Analyze image optimization opportunities."""
    image_analysis = {
        'total_images': 0,
        'optimized_formats': 0,
        'lazy_loaded': 0,
        'with_dimensions': 0,
        'responsive_images': 0,
        'issues': [],
        'savings_potential_kb': None,
        'savings_status': 'unknown',
        'source': 'html_attributes'
    }
    
    images = [record['attrs'] for record in facts.images] if facts is not None else soup.find_all('img')
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
        if image_analysis['with_dimensions'] < image_analysis['total_images'] * 0.8:
            image_analysis['issues'].append('Many images missing width/height attributes')
        
        if image_analysis['responsive_images'] < image_analysis['total_images'] * 0.3:
            image_analysis['issues'].append('Few responsive images implemented')
    
    collector = RuleCollector('performance')
    missing_dimensions = [dict(index=index, src=img.get('src', '')) for index, img in enumerate(images)
                          if not (img.get('width') and img.get('height'))]
    collector.check('images.missing_dimensions', bool(missing_dimensions),
        evidence={'images': missing_dimensions, 'count': len(missing_dimensions), 'css_layout_checked': False},
        applicable=bool(images), reason='Requires image elements.', category='Performance', confidence='low',
        message=f'{len(missing_dimensions)} images lack width/height attributes; CSS may reserve their layout space')
    collector.check('performance.responsive_images', image_analysis['responsive_images'] < len(images) * 0.3,
        evidence={'image_count': len(images), 'with_responsive_attributes': image_analysis['responsive_images'], 'ratio_threshold': 0.3},
        applicable=bool(images), reason='Requires image elements.', category='Performance', confidence='low',
        message='Few image elements declare responsive sources; review whether variants are useful')
    image_analysis['findings'] = collector.issues
    image_analysis['rule_results'] = collector.results
    return image_analysis


def analyze_javascript_optimization(soup: BeautifulSoup, page_url: Optional[str] = None, *,
                                    facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Analyze JavaScript attributes using the shared script snapshot."""
    js_analysis = {
        'total_scripts': 0, 'async_scripts': 0, 'defer_scripts': 0, 'module_scripts': 0,
        'inline_scripts': 0, 'minified_scripts': None, 'minified_filename_references': 0,
        'minification_status': 'not_measured', 'render_blocking': 0,
        'third_party_scripts': [], 'third_party_status': 'observed_references', 'bundle_analysis': {}
    }
    scripts = _script_records(soup, facts)
    js_analysis['total_scripts'] = len(scripts)
    base_url = facts.base_url if facts is not None else document_base_url(soup, page_url) if page_url else None
    for record in scripts:
        script, text = record['attrs'], record['text']
        src = script.get('src', '')
        if src:
            if 'async' in script:
                js_analysis['async_scripts'] += 1
            if 'defer' in script:
                js_analysis['defer_scripts'] += 1
            if _is_classic_javascript(script) and not is_nonblocking_script(script) and record['in_head']:
                js_analysis['render_blocking'] += 1
            if script.get('type') == 'module':
                js_analysis['module_scripts'] += 1
            if '.min.js' in src or '-min.js' in src or '.prod.js' in src:
                js_analysis['minified_filename_references'] += 1
            if page_url and classify_url(src, page_url, base_url) == 'external':
                resolved = resolve_url(src, base_url)
                js_analysis['third_party_scripts'].append({
                    'name': urlparse(resolved).hostname, 'url': resolved,
                    'async': 'async' in script, 'defer': 'defer' in script
                })
        else:
            js_analysis['inline_scripts'] += 1
            if len(text) > 10000:
                js_analysis['bundle_analysis'].setdefault('large_inline', []).append(len(text))
    return js_analysis


def calculate_performance_score(metrics: PerformanceMetrics, resource_count: int) -> Tuple[int, str]:
    """Score only supplied measurements; missing values incur no penalty."""
    score = 100
    checks = (
        (metrics.largest_contentful_paint, 4.0, 15, 2.5, 8),
        (metrics.interaction_to_next_paint, 500, 15, 200, 8),
        (metrics.cumulative_layout_shift, 0.25, 10, 0.1, 5),
        (metrics.load_time, 5.0, 20, 3.0, 10),
        (metrics.total_byte_weight, 5 * 1024 * 1024, 15, 3 * 1024 * 1024, 10),
        (metrics.total_blocking_time, 600, 10, 300, 5),
    )
    for value, poor, poor_penalty, moderate, moderate_penalty in checks:
        if value is not None and math.isfinite(value):
            if value > poor:
                score -= poor_penalty
            elif value > moderate:
                score -= moderate_penalty
    score = max(0, min(100, score))
    return score, score_grade(score)


def generate_performance_budget(metrics: PerformanceMetrics, resources: Dict) -> Dict[str, Any]:
    """Budgets remain unknown until the corresponding quantity is measured."""
    budget = {
        'metrics': {
            'load_time': {'target': 3.0, 'current': metrics.load_time},
            'lcp': {'target': 2.5, 'current': metrics.largest_contentful_paint},
            'inp': {'target': 200, 'current': metrics.interaction_to_next_paint},
            'cls': {'target': 0.1, 'current': metrics.cumulative_layout_shift},
            'tti': {'target': 5.0, 'current': metrics.time_to_interactive},
        },
        'resources': {
            'total_size': {'target': 2000000, 'current': metrics.total_byte_weight},
            'images': {'target': 1000000, 'current': None},
            'scripts': {'target': 500000, 'current': None},
            'stylesheets': {'target': 200000, 'current': None},
            'fonts': {'target': 300000, 'current': None},
        },
        'counts': {
            'total_requests': {'target': 50, 'current': None},
            'third_party_requests': {'target': 10, 'current': None},
        },
    }
    for category in budget.values():
        for value in category.values():
            current = value['current']
            value['source'] = 'not_measured' if current is None else 'supplied_measurement'
            value['status'] = 'unknown' if current is None else 'pass' if current <= value['target'] else 'fail'
            if current is not None:
                value['ratio'] = round(current / value['target'], 2)
    return budget


def detect_caching_strategy(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Record HTML hints without inferring cache policy or cache hit rates."""
    providers = {
        'cloudflare': ('cdnjs.cloudflare.com',), 'cloudfront': ('cloudfront.net',),
        'fastly': ('fastly.net',), 'akamai': ('akamaihd.net',),
        'jsdelivr': ('jsdelivr.net',), 'unpkg': ('unpkg.com',),
    }
    found = set()
    if facts is not None:
        elements = [record['attrs'] for record in facts.link_tags + facts.scripts + facts.images]
    else:
        elements = soup.find_all(['link', 'script', 'img'])
    for element in elements:
        reference = element.get('src') or element.get('href') or ''
        try:
            hostname = urlparse(reference).hostname or ''
        except ValueError:
            continue
        for provider, domains in providers.items():
            if any(hostname == domain or hostname.endswith('.' + domain) for domain in domains):
                found.add(provider)
    registration_hint = any(re.search(r'navigator\.serviceWorker\.register', script['text'])
                            for script in _script_records(soup, facts))
    return {
        'has_service_worker': None, 'service_worker_registration_reference': registration_hint,
        'uses_cdn': None, 'cdn_providers': sorted(found), 'cache_control_hints': [],
        'estimated_cache_hit_rate': None, 'status': 'unknown', 'source': 'html_references_only',
    }


def analyze_performance(soup: BeautifulSoup, url: str, load_time: float = 0,
                        content_length: int = 0, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Inspect static HTML. Browser timing and network budgets are unavailable."""
    facts = ensure_page_facts(soup, url, facts=facts)
    collector = RuleCollector('performance')
    metrics = PerformanceMetrics(dom_size=facts.dom_size)
    fetch_time = load_time if isinstance(load_time, (int, float)) and math.isfinite(load_time) and load_time > 0 else None
    html_bytes = content_length if isinstance(content_length, int) and content_length >= 0 else None
    # A default zero does not establish that an HTTP response was observed.
    if html_bytes == 0 and fetch_time is None:
        html_bytes = None
    data = {
        'score_scope': 'static_html_checks',
        'measurement_status': 'browser_not_measured',
        'measurement_source': 'html_and_optional_document_fetch',
        'metrics': {
            'load_time': None, 'html_fetch_time': fetch_time,
            'dom_size': metrics.dom_size, 'html_content_bytes': html_bytes,
            'content_size_mb': round(html_bytes / (1024 * 1024), 4) if html_bytes is not None else None,
            'lcp': None, 'inp': None, 'fid': None, 'cls': None, 'fcp': None,
            'tti': None, 'tbt': None, 'ttfb': None,
        },
    }
    data['metric_sources'] = {
        key: ('html_document' if key == 'dom_size' else
              'document_fetch' if key in ('html_fetch_time', 'html_content_bytes', 'content_size_mb') and value is not None else
              'not_measured')
        for key, value in data['metrics'].items()
    }
    resources = {key: [] for key in ('scripts', 'stylesheets', 'images', 'fonts', 'videos')}
    resource_profiles = []
    base_url = facts.base_url

    def add_resource(element, attribute, resource_type, group, in_head=False):
        reference = element.get(attribute, '')
        resolved = resolve_url(reference, base_url)
        if not resolved:
            return
        resources[group].append(resolved)
        resource_profiles.append(ResourceProfile(
            url=resolved, type=resource_type,
            is_async='async' in element if resource_type == ResourceType.SCRIPT else False,
            is_deferred=('defer' in element or element.get('type') == 'module') if resource_type == ResourceType.SCRIPT else False,
            is_render_blocking=(_is_classic_javascript(element) and not is_nonblocking_script(element) and in_head) if resource_type == ResourceType.SCRIPT else False,
            is_lazy=element.get('loading') == 'lazy',
            is_third_party=classify_url(reference, url, base_url) == 'external',
        ))

    scripts, links = facts.scripts, facts.link_tags
    for script in scripts:
        if 'src' in script['attrs']:
            add_resource(script['attrs'], 'src', ResourceType.SCRIPT, 'scripts', script['in_head'])
    for link in links:
        if 'stylesheet' in link['attrs'].get('rel', []):
            add_resource(link['attrs'], 'href', ResourceType.STYLESHEET, 'stylesheets')
    for image in facts.images:
        img = image['attrs']
        add_resource(img, 'src' if img.get('src') else 'data-src', ResourceType.IMAGE, 'images')
    for link in links:
        if 'preload' in link['attrs'].get('rel', []) and link['attrs'].get('as') == 'font':
            add_resource(link['attrs'], 'href', ResourceType.FONT, 'fonts')
    for video in soup.find_all('video'):
        add_resource(video.attrs, 'src', ResourceType.VIDEO, 'videos')
        for source in video.find_all('source', src=True):
            add_resource(source.attrs, 'src', ResourceType.VIDEO, 'videos')
    resources['total'] = len(resource_profiles)
    data['total_resources'] = resources['total']
    domains = sorted({urlparse(profile.url).netloc for profile in resource_profiles
                      if urlparse(profile.url).scheme in ('http', 'https')})
    data['network_metrics'] = {
        'total_requests': None, 'third_party_requests': None,
        'referenced_resources': len(resource_profiles),
        'third_party_references': sum(profile.is_third_party for profile in resource_profiles),
        'unique_domains': len(domains), 'domains': domains,
        'status': 'not_measured', 'source': 'html_references_only',
    }
    critical_path = analyze_critical_rendering_path(soup, facts=facts)
    data['critical_rendering_path'] = critical_path
    data['performance_patterns'] = detect_performance_patterns(soup, facts=facts)
    data['image_optimization'] = analyze_image_optimization(soup, facts=facts)
    collector.results.extend(data['performance_patterns']['rule_results'])
    collector.results.extend(data['image_optimization']['rule_results'])
    javascript = analyze_javascript_optimization(soup, url, facts=facts)
    data['javascript_optimization'] = javascript
    blocking = [resource['url'] for resource in critical_path['render_blocking_resources'] if resource['type'] == 'script']
    collector.check('performance.blocking_scripts', bool(blocking),
        evidence={'urls': blocking, 'count': len(blocking), 'browser_timing_measured': False},
        applicable=any('src' in script['attrs'] for script in scripts), reason='Requires external script elements.',
        message=f'{len(blocking)} external classic scripts in head lack async or defer', category='Performance')
    issues = collector.issues
    data['caching_strategy'] = detect_caching_strategy(soup, facts=facts)
    data['performance_budget'] = generate_performance_budget(metrics, resources)
    data['high_priority_resources'] = None
    data['priority_status'] = 'requires_browser_trace'
    data['resource_hints'] = {
        name.replace('-', '_'): sum(name in link['attrs'].get('rel', []) for link in links)
        for name in ('preconnect', 'dns-prefetch', 'preload', 'prefetch')
    }
    data['optimization_opportunities'] = [
        {
            'title': issue['title'], 'impact': 'requires_measurement',
            'rule_id': issue['rule_id'], 'category': 'performance', 'savings_ms': None, 'savings_kb': None,
            'status': 'unmeasured', 'source': 'html_attributes',
            'description': issue['message'], 'implementation': issue['fix'],
        }
        for issue in issues
    ]
    score = score_findings(issues)
    grade = score_grade(score)
    data['performance_level'] = None
    data['grade'] = grade
    data['recommendations'] = recommendations_for(issues)
    return {
        'score': score, 'grade': grade, 'issues': issues, 'data': data,
        'resources': resources, 'recommendations': data['recommendations'],
        'rule_results': collector.results, 'rule_coverage': collector.coverage,
    }
