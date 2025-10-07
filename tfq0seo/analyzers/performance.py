"""Performance analyzer for load time, resources, and Core Web Vitals estimates."""

import re
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a simple issue dictionary."""
    issue = {
        'category': category,
        'severity': severity,  # critical, warning, notice
        'message': message
    }
    if details:
        issue['details'] = details
    return issue


def analyze_performance(soup: BeautifulSoup, url: str, load_time: float = 0, content_length: int = 0) -> Dict[str, Any]:
    """Analyze performance aspects of a page."""
    issues = []
    score = 100
    data = {
        'load_time': round(load_time, 2),
        'content_size': content_length
    }
    
    # Page load time analysis
    if load_time > 0:
        if load_time > 5.0:
            issues.append(create_issue('Performance', 'critical', f'Very slow page load time ({load_time:.1f}s), target < 3s'))
            score -= 30
        elif load_time > 3.0:
            issues.append(create_issue('Performance', 'warning', f'Slow page load time ({load_time:.1f}s), target < 3s'))
            score -= 15
        elif load_time > 2.0:
            issues.append(create_issue('Performance', 'notice', f'Moderate page load time ({load_time:.1f}s), target < 2s'))
            score -= 5
    
    # Content size analysis
    content_size_mb = content_length / (1024 * 1024)
    data['content_size_mb'] = round(content_size_mb, 2)
    
    if content_size_mb > 5.0:
        issues.append(create_issue('Performance', 'critical', f'Very large page size ({content_size_mb:.1f}MB), target < 2MB'))
        score -= 25
    elif content_size_mb > 2.0:
        issues.append(create_issue('Performance', 'warning', f'Large page size ({content_size_mb:.1f}MB), target < 2MB'))
        score -= 15
    elif content_size_mb > 1.0:
        issues.append(create_issue('Performance', 'notice', f'Moderate page size ({content_size_mb:.1f}MB), target < 1MB'))
        score -= 5
    
    # Resource analysis
    resources = {
        'images': [],
        'scripts': [],
        'stylesheets': [],
        'fonts': [],
        'videos': [],
        'total': 0
    }
    
    # Images
    images = soup.find_all('img')
    for img in images:
        src = img.get('src', '')
        if src:
            resources['images'].append(src)
            # Check for missing dimensions
            if not img.get('width') or not img.get('height'):
                issues.append(create_issue('Performance', 'warning', 'Images without dimensions cause layout shift'))
                score -= 3
                break  # Only report once
    
    # Check for lazy loading
    lazy_images = [img for img in images if img.get('loading') == 'lazy']
    data['lazy_loaded_images'] = len(lazy_images)
    
    if len(images) > 5 and len(lazy_images) == 0:
        issues.append(create_issue('Performance', 'warning', f'{len(images)} images found but none use lazy loading'))
        score -= 10
    
    # Scripts
    scripts = soup.find_all('script', src=True)
    for script in scripts:
        src = script.get('src', '')
        resources['scripts'].append(src)
        
        # Check for async/defer
        if not script.get('async') and not script.get('defer'):
            if 'jquery' not in src.lower() and 'bootstrap' not in src.lower():  # Some exceptions
                issues.append(create_issue('Performance', 'notice', 'Found render-blocking JavaScript (missing async/defer)'))
                score -= 3
                break  # Only report once
    
    data['total_scripts'] = len(resources['scripts'])
    data['async_scripts'] = len([s for s in scripts if s.get('async')])
    data['defer_scripts'] = len([s for s in scripts if s.get('defer')])
    
    if len(resources['scripts']) > 10:
        issues.append(create_issue('Performance', 'warning', f'Too many JavaScript files ({len(resources['scripts'])}), consider bundling'))
        score -= 10
    
    # Stylesheets
    stylesheets = soup.find_all('link', rel='stylesheet')
    for link in stylesheets:
        href = link.get('href', '')
        resources['stylesheets'].append(href)
    
    data['total_stylesheets'] = len(resources['stylesheets'])
    
    if len(resources['stylesheets']) > 5:
        issues.append(create_issue('Performance', 'warning', f'Too many CSS files ({len(resources['stylesheets'])}), consider bundling'))
        score -= 10
    
    # Check for critical CSS
    inline_styles = soup.find_all('style')
    has_critical_css = len(inline_styles) > 0
    data['has_inline_css'] = has_critical_css
    
    if not has_critical_css and len(resources['stylesheets']) > 0:
        issues.append(create_issue('Performance', 'notice', 'No critical CSS found, consider inlining above-the-fold styles'))
        score -= 5
    
    # Fonts
    for link in soup.find_all('link', rel='preload'):
        if 'font' in link.get('as', ''):
            resources['fonts'].append(link.get('href', ''))
    
    # Also check for font-face in styles
    for style in soup.find_all('style'):
        if style.string and '@font-face' in style.string:
            resources['fonts'].append('inline-font-face')
    
    data['font_count'] = len(set(resources['fonts']))
    
    if len(resources['fonts']) > 5:
        issues.append(create_issue('Performance', 'notice', f'Many web fonts loaded ({len(resources['fonts'])}), may impact performance'))
        score -= 5
    
    # Videos
    videos = soup.find_all(['video', 'iframe'])
    for video in videos:
        if video.name == 'video':
            src = video.get('src', '')
            if src:
                resources['videos'].append(src)
        elif video.name == 'iframe':
            src = video.get('src', '')
            if 'youtube' in src or 'vimeo' in src or 'video' in src:
                resources['videos'].append(src)
    
    data['video_count'] = len(resources['videos'])
    
    if resources['videos']:
        # Check for lazy loading on videos/iframes
        lazy_videos = [v for v in videos if v.get('loading') == 'lazy']
        if not lazy_videos:
            issues.append(create_issue('Performance', 'warning', f'{len(resources['videos'])} videos/embeds found but not lazy loaded'))
            score -= 10
    
    # Total resource count
    resources['total'] = (
        len(resources['images']) +
        len(resources['scripts']) +
        len(resources['stylesheets']) +
        len(resources['fonts']) +
        len(resources['videos'])
    )
    data['total_resources'] = resources['total']
    
    if resources['total'] > 100:
        issues.append(create_issue('Performance', 'critical', f'Too many resources ({resources['total']}), target < 50'))
        score -= 20
    elif resources['total'] > 50:
        issues.append(create_issue('Performance', 'warning', f'Many resources ({resources['total']}), target < 50'))
        score -= 10
    
    # Check for preload/prefetch hints
    preload_links = soup.find_all('link', rel='preload')
    prefetch_links = soup.find_all('link', rel='prefetch')
    preconnect_links = soup.find_all('link', rel='preconnect')
    
    data['preload_count'] = len(preload_links)
    data['prefetch_count'] = len(prefetch_links)
    data['preconnect_count'] = len(preconnect_links)
    
    resource_hints_total = len(preload_links) + len(prefetch_links) + len(preconnect_links)
    if resource_hints_total == 0:
        issues.append(create_issue('Performance', 'notice', 'No resource hints found (preload/prefetch/preconnect)'))
        score -= 5
    
    # Check for minification hints
    unminified_resources = 0
    for script_src in resources['scripts']:
        if not any(ext in script_src for ext in ['.min.js', '-min.js', '.prod.js']):
            unminified_resources += 1
    
    for css_href in resources['stylesheets']:
        if not any(ext in css_href for ext in ['.min.css', '-min.css', '.prod.css']):
            unminified_resources += 1
    
    if unminified_resources > 3:
        issues.append(create_issue('Performance', 'warning', f'{unminified_resources} potentially unminified resources found'))
        score -= 10
    
    # Core Web Vitals estimates (simplified)
    # These are rough estimates based on resource counts and load time
    
    # Largest Contentful Paint (LCP) estimate
    lcp_estimate = load_time * 0.8  # Rough estimate
    data['lcp_estimate'] = round(lcp_estimate, 2)
    
    if lcp_estimate > 4.0:
        issues.append(create_issue('Performance', 'warning', f'Poor LCP estimate ({lcp_estimate:.1f}s), target < 2.5s'))
        score -= 10
    elif lcp_estimate > 2.5:
        issues.append(create_issue('Performance', 'notice', f'Needs improvement LCP estimate ({lcp_estimate:.1f}s), target < 2.5s'))
        score -= 5
    
    # First Input Delay (FID) estimate based on JS count
    if len(resources['scripts']) > 10:
        fid_estimate = 300  # Poor
    elif len(resources['scripts']) > 5:
        fid_estimate = 150  # Needs improvement
    else:
        fid_estimate = 50  # Good
    
    data['fid_estimate'] = fid_estimate
    
    if fid_estimate > 300:
        issues.append(create_issue('Performance', 'warning', f'Poor FID estimate ({fid_estimate}ms), target < 100ms'))
        score -= 10
    elif fid_estimate > 100:
        issues.append(create_issue('Performance', 'notice', f'Needs improvement FID estimate ({fid_estimate}ms), target < 100ms'))
        score -= 5
    
    # Cumulative Layout Shift (CLS) estimate
    cls_issues = 0
    if len([img for img in images if not img.get('width') or not img.get('height')]) > 0:
        cls_issues += 1
    if len(resources['fonts']) > 3:
        cls_issues += 1
    if not has_critical_css:
        cls_issues += 1
    
    if cls_issues >= 2:
        cls_estimate = 0.25  # Poor
    elif cls_issues == 1:
        cls_estimate = 0.15  # Needs improvement
    else:
        cls_estimate = 0.05  # Good
    
    data['cls_estimate'] = cls_estimate
    
    if cls_estimate > 0.25:
        issues.append(create_issue('Performance', 'warning', f'Poor CLS estimate ({cls_estimate}), target < 0.1'))
        score -= 10
    elif cls_estimate > 0.1:
        issues.append(create_issue('Performance', 'notice', f'Needs improvement CLS estimate ({cls_estimate}), target < 0.1'))
        score -= 5
    
    # Check for service worker
    service_worker_script = soup.find('script', string=re.compile(r'serviceWorker|navigator\.serviceWorker'))
    data['has_service_worker'] = service_worker_script is not None
    
    if not service_worker_script:
        issues.append(create_issue('Performance', 'notice', 'No service worker detected (consider for offline support)'))
        score -= 3
    
    return {
        'score': max(0, score),
        'issues': issues,
        'data': data,
        'resources': resources
    }
