"""SEO analyzer for meta tags, Open Graph, and structured data."""

import json
import re
from typing import Dict, List, Any, Optional
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


def analyze_seo(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Analyze SEO elements of a page."""
    issues = []
    score = 100
    data = {}
    
    # Meta title
    title_tag = soup.find('title')
    if not title_tag or not title_tag.text.strip():
        issues.append(create_issue('SEO', 'critical', 'Missing page title'))
        score -= 15
        data['title'] = None
    else:
        title = title_tag.text.strip()
        data['title'] = title
        
        # Check title length
        if len(title) < 30:
            issues.append(create_issue('SEO', 'warning', f'Title too short ({len(title)} chars, recommended 30-60)'))
            score -= 5
        elif len(title) > 60:
            issues.append(create_issue('SEO', 'warning', f'Title too long ({len(title)} chars, recommended 30-60)'))
            score -= 5
    
    # Meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if not meta_desc or not meta_desc.get('content', '').strip():
        issues.append(create_issue('SEO', 'critical', 'Missing meta description'))
        score -= 15
        data['description'] = None
    else:
        description = meta_desc.get('content', '').strip()
        data['description'] = description
        
        # Check description length
        if len(description) < 120:
            issues.append(create_issue('SEO', 'warning', f'Meta description too short ({len(description)} chars, recommended 120-160)'))
            score -= 5
        elif len(description) > 160:
            issues.append(create_issue('SEO', 'warning', f'Meta description too long ({len(description)} chars, recommended 120-160)'))
            score -= 5
    
    # Meta keywords (deprecated but still check)
    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
    if meta_keywords:
        data['keywords'] = meta_keywords.get('content', '')
        issues.append(create_issue('SEO', 'notice', 'Meta keywords tag is deprecated and ignored by search engines'))
    
    # Canonical URL
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    if not canonical:
        issues.append(create_issue('SEO', 'warning', 'Missing canonical URL'))
        score -= 10
    else:
        data['canonical'] = canonical.get('href')
    
    # Open Graph tags
    og_tags = {}
    og_required = ['og:title', 'og:description', 'og:image', 'og:url']
    
    for tag in soup.find_all('meta', property=re.compile('^og:')):
        prop = tag.get('property')
        content = tag.get('content')
        if prop and content:
            og_tags[prop] = content
    
    data['open_graph'] = og_tags
    
    # Check required OG tags
    missing_og = [tag for tag in og_required if tag not in og_tags]
    if missing_og:
        issues.append(create_issue('SEO', 'warning', f'Missing Open Graph tags: {', '.join(missing_og)}'))
        score -= 5 * len(missing_og)
    
    # Twitter Card tags
    twitter_tags = {}
    for tag in soup.find_all('meta', attrs={'name': re.compile('^twitter:')}):
        name = tag.get('name')
        content = tag.get('content')
        if name and content:
            twitter_tags[name] = content
    
    data['twitter_card'] = twitter_tags
    
    if not twitter_tags:
        issues.append(create_issue('SEO', 'notice', 'Missing Twitter Card tags for better social sharing'))
        score -= 3
    
    # Structured data (JSON-LD)
    structured_data = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            json_data = json.loads(script.string)
            structured_data.append(json_data)
        except:
            issues.append(create_issue('SEO', 'warning', 'Invalid JSON-LD structured data found'))
            score -= 5
    
    data['structured_data'] = structured_data
    
    if not structured_data:
        issues.append(create_issue('SEO', 'warning', 'No structured data (JSON-LD) found'))
        score -= 10
    
    # Robots meta tag
    robots = soup.find('meta', attrs={'name': 'robots'})
    if robots:
        content = robots.get('content', '').lower()
        data['robots'] = content
        if 'noindex' in content:
            issues.append(create_issue('SEO', 'critical', 'Page is set to noindex (will not appear in search results)'))
            score -= 20
        if 'nofollow' in content:
            issues.append(create_issue('SEO', 'warning', 'Page is set to nofollow (links will not pass PageRank)'))
            score -= 10
    
    # Language declaration
    html_tag = soup.find('html')
    if html_tag:
        lang = html_tag.get('lang')
        if not lang:
            issues.append(create_issue('SEO', 'warning', 'Missing language declaration (lang attribute)'))
            score -= 5
        else:
            data['language'] = lang
    
    # Viewport meta tag (mobile)
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if not viewport:
        issues.append(create_issue('SEO', 'critical', 'Missing viewport meta tag (not mobile-friendly)'))
        score -= 15
    else:
        data['viewport'] = viewport.get('content')
    
    # Favicon
    favicon = soup.find('link', rel=re.compile('icon'))
    if not favicon:
        issues.append(create_issue('SEO', 'notice', 'Missing favicon'))
        score -= 2
    
    # H1 tags
    h1_tags = soup.find_all('h1')
    if not h1_tags:
        issues.append(create_issue('SEO', 'critical', 'Missing H1 tag'))
        score -= 15
    elif len(h1_tags) > 1:
        issues.append(create_issue('SEO', 'warning', f'Multiple H1 tags found ({len(h1_tags)}), should have only one'))
        score -= 10
    else:
        data['h1'] = h1_tags[0].text.strip()
    
    # Alt text for images
    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt')]
    if images_without_alt:
        issues.append(create_issue('SEO', 'warning', f'{len(images_without_alt)} images missing alt text'))
        score -= min(15, len(images_without_alt) * 2)
    
    return {
        'score': max(0, score),
        'issues': issues,
        'data': data
    }
