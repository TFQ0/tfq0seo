"""Technical SEO analyzer for HTTPS, headers, mobile-friendliness, etc."""

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


def analyze_technical(soup: BeautifulSoup, url: str, headers: Dict[str, str] = None, status_code: int = 200) -> Dict[str, Any]:
    """Analyze technical SEO aspects."""
    issues = []
    score = 100
    data = {}
    
    parsed_url = urlparse(url)
    
    # HTTPS check
    data['https'] = parsed_url.scheme == 'https'
    if not data['https']:
        issues.append(create_issue('Technical', 'critical', 'Site not using HTTPS (insecure)'))
        score -= 20
    
    # Status code check
    data['status_code'] = status_code
    if status_code >= 400:
        issues.append(create_issue('Technical', 'critical', f'Page returns error status code {status_code}'))
        score -= 30
    elif status_code >= 300:
        issues.append(create_issue('Technical', 'warning', f'Page is redirecting (status {status_code})'))
        score -= 5
    
    # Check headers if provided
    if headers:
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        # Security headers
        security_headers = {
            'x-frame-options': 'Protects against clickjacking',
            'x-content-type-options': 'Prevents MIME type sniffing',
            'x-xss-protection': 'XSS protection (legacy)',
            'strict-transport-security': 'Forces HTTPS',
            'content-security-policy': 'Controls resource loading',
            'referrer-policy': 'Controls referrer information'
        }
        
        missing_security = []
        for header, description in security_headers.items():
            if header not in headers_lower:
                missing_security.append(header)
        
        data['security_headers_missing'] = missing_security
        
        if missing_security:
            if 'strict-transport-security' in missing_security and data['https']:
                issues.append(create_issue('Technical', 'warning', 'Missing HSTS header (Strict-Transport-Security)'))
                score -= 10
            
            if 'x-frame-options' in missing_security:
                issues.append(create_issue('Technical', 'notice', 'Missing X-Frame-Options header'))
                score -= 3
            
            if 'content-security-policy' in missing_security:
                issues.append(create_issue('Technical', 'notice', 'Missing Content-Security-Policy header'))
                score -= 3
        
        # Compression check
        content_encoding = headers_lower.get('content-encoding', '')
        data['compression'] = content_encoding
        if not content_encoding or 'gzip' not in content_encoding.lower():
            issues.append(create_issue('Technical', 'warning', 'Content not compressed (missing gzip)'))
            score -= 10
        
        # Cache headers
        cache_control = headers_lower.get('cache-control', '')
        data['cache_control'] = cache_control
        if not cache_control:
            issues.append(create_issue('Technical', 'notice', 'Missing Cache-Control header'))
            score -= 5
        elif 'no-cache' in cache_control or 'no-store' in cache_control:
            issues.append(create_issue('Technical', 'notice', 'Page not cacheable (no-cache/no-store)'))
            score -= 3
        
        # Server header (information disclosure)
        server = headers_lower.get('server', '')
        if server:
            data['server'] = server
            # Check for version disclosure
            if re.search(r'\d+\.\d+', server):
                issues.append(create_issue('Technical', 'notice', f'Server version disclosed: {server}'))
                score -= 2
    
    # Mobile-friendliness checks
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    data['has_viewport'] = viewport is not None
    
    if not viewport:
        issues.append(create_issue('Technical', 'critical', 'Missing viewport meta tag (not mobile-friendly)'))
        score -= 20
    else:
        viewport_content = viewport.get('content', '')
        data['viewport_content'] = viewport_content
        
        # Check viewport configuration
        if 'width=device-width' not in viewport_content:
            issues.append(create_issue('Technical', 'warning', 'Viewport not set to device-width'))
            score -= 10
        
        if 'maximum-scale=1' in viewport_content or 'user-scalable=no' in viewport_content:
            issues.append(create_issue('Technical', 'warning', 'Viewport prevents zooming (accessibility issue)'))
            score -= 5
    
    # Check for responsive images
    images = soup.find_all('img')
    responsive_images = 0
    for img in images:
        if img.get('srcset') or 'max-width' in img.get('style', ''):
            responsive_images += 1
    
    data['total_images'] = len(images)
    data['responsive_images'] = responsive_images
    
    if images and responsive_images < len(images) / 2:
        issues.append(create_issue('Technical', 'notice', f'Only {responsive_images}/{len(images)} images are responsive'))
        score -= 5
    
    # XML sitemap link
    sitemap_link = soup.find('link', rel='sitemap')
    data['has_sitemap_link'] = sitemap_link is not None
    
    # Charset declaration
    charset = soup.find('meta', charset=True)
    if not charset:
        charset = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
    
    if not charset:
        issues.append(create_issue('Technical', 'warning', 'Missing character encoding declaration'))
        score -= 5
    else:
        data['charset'] = charset.get('charset', 'detected')
    
    # Check for Flash content (deprecated)
    flash_embeds = soup.find_all(['embed', 'object'])
    flash_count = 0
    for embed in flash_embeds:
        if 'flash' in str(embed).lower() or '.swf' in str(embed):
            flash_count += 1
    
    if flash_count > 0:
        issues.append(create_issue('Technical', 'critical', f'Found {flash_count} Flash elements (deprecated technology)'))
        score -= 20
    
    # Check for iframes
    iframes = soup.find_all('iframe')
    data['iframe_count'] = len(iframes)
    
    if len(iframes) > 3:
        issues.append(create_issue('Technical', 'notice', f'Many iframes found ({len(iframes)}), may impact performance'))
        score -= 3
    
    # Check for inline styles and scripts (CSP compatibility)
    inline_styles = soup.find_all(style=True)
    inline_scripts = soup.find_all('script', src=False)
    
    data['inline_styles_count'] = len(inline_styles)
    data['inline_scripts_count'] = len(inline_scripts)
    
    if len(inline_styles) > 10:
        issues.append(create_issue('Technical', 'notice', f'Many inline styles ({len(inline_styles)}), consider external CSS'))
        score -= 3
    
    if len(inline_scripts) > 5:
        issues.append(create_issue('Technical', 'warning', f'Many inline scripts ({len(inline_scripts)}), security and performance concern'))
        score -= 5
    
    # Check for mixed content (if HTTPS)
    if data['https']:
        mixed_content = []
        
        # Check images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src.startswith('http://'):
                mixed_content.append(f"Image: {src[:50]}")
        
        # Check scripts
        for script in soup.find_all('script', src=True):
            src = script.get('src', '')
            if src.startswith('http://'):
                mixed_content.append(f"Script: {src[:50]}")
        
        # Check stylesheets
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if href.startswith('http://'):
                mixed_content.append(f"Stylesheet: {href[:50]}")
        
        if mixed_content:
            issues.append(create_issue('Technical', 'critical', f'Mixed content found (HTTP resources on HTTPS page): {len(mixed_content)} items'))
            score -= 15
            data['mixed_content'] = mixed_content[:5]  # Store first 5 for reference
    
    # Check doctype
    doctype = None
    for item in soup.contents:
        if isinstance(item, type(soup)) and item.name == '!doctype':
            doctype = str(item)
            break
    
    if not doctype:
        # Try alternative method
        if soup.contents and str(soup.contents[0]).startswith('<!DOCTYPE'):
            doctype = str(soup.contents[0])
    
    if not doctype:
        issues.append(create_issue('Technical', 'warning', 'Missing DOCTYPE declaration'))
        score -= 5
    elif 'html5' not in doctype.lower() and 'html' not in doctype.lower():
        issues.append(create_issue('Technical', 'notice', 'Non-HTML5 DOCTYPE detected'))
        score -= 2
    
    data['has_doctype'] = doctype is not None
    
    # URL structure
    url_length = len(url)
    data['url_length'] = url_length
    
    if url_length > 100:
        issues.append(create_issue('Technical', 'notice', f'Long URL ({url_length} chars), consider shorter URLs'))
        score -= 2
    
    # Check for URL parameters
    if '?' in url:
        params = url.split('?')[1] if '?' in url else ''
        param_count = len(params.split('&')) if params else 0
        data['url_parameters'] = param_count
        
        if param_count > 3:
            issues.append(create_issue('Technical', 'notice', f'Many URL parameters ({param_count}), consider cleaner URLs'))
            score -= 3
    
    return {
        'score': max(0, score),
        'issues': issues,
        'data': data
    }
