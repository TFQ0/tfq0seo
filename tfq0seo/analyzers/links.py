"""Links analyzer for internal/external links, broken links, and anchor text quality."""

import re
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse, urljoin
from collections import Counter
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


def normalize_url(url: str, base_url: str) -> str:
    """Normalize a URL relative to base URL."""
    # Make absolute
    absolute = urljoin(base_url, url)
    
    # Parse and normalize
    parsed = urlparse(absolute)
    
    # Remove fragment
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    
    # Remove trailing slash from paths (except root)
    if normalized.endswith('/') and len(parsed.path) > 1:
        normalized = normalized[:-1]
    
    return normalized


def is_internal_link(url: str, base_url: str) -> bool:
    """Check if a URL is internal to the base domain."""
    if not url or url.startswith('#'):
        return True
    
    if url.startswith('mailto:') or url.startswith('tel:') or url.startswith('javascript:'):
        return False
    
    base_parsed = urlparse(base_url)
    url_parsed = urlparse(urljoin(base_url, url))
    
    return base_parsed.netloc == url_parsed.netloc


def analyze_links(soup: BeautifulSoup, url: str, broken_links: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Analyze links on a page."""
    issues = []
    score = 100
    data = {}
    
    # Find all links
    all_links = soup.find_all('a', href=True)
    data['total_links'] = len(all_links)
    
    internal_links = []
    external_links = []
    anchor_texts = []
    nofollow_links = []
    blank_target_links = []
    
    # Analyze each link
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        rel = link.get('rel', [])
        target = link.get('target', '')
        
        # Skip empty hrefs
        if not href or href == '#':
            continue
        
        # Normalize URL
        try:
            normalized = normalize_url(href, url)
        except:
            normalized = href
        
        # Categorize link
        if is_internal_link(href, url):
            internal_links.append({
                'url': normalized,
                'text': text,
                'rel': rel,
                'target': target
            })
        else:
            external_links.append({
                'url': normalized,
                'text': text,
                'rel': rel,
                'target': target
            })
        
        # Collect anchor text
        if text:
            anchor_texts.append(text.lower())
        
        # Check for nofollow
        if isinstance(rel, list):
            rel_str = ' '.join(rel)
        else:
            rel_str = str(rel)
        
        if 'nofollow' in rel_str.lower():
            nofollow_links.append(normalized)
        
        # Check for target="_blank" without rel="noopener"
        if target == '_blank':
            blank_target_links.append(normalized)
            if 'noopener' not in rel_str.lower():
                issues.append(create_issue('Links', 'warning', 'target="_blank" without rel="noopener" (security risk)'))
                score -= 5
                break  # Only report once
    
    # Store link data
    data['internal_links_count'] = len(internal_links)
    data['external_links_count'] = len(external_links)
    data['nofollow_links_count'] = len(nofollow_links)
    data['blank_target_links_count'] = len(blank_target_links)
    
    # Check for broken links if provided
    if broken_links:
        found_broken = []
        for link_data in internal_links + external_links:
            if link_data['url'] in broken_links:
                found_broken.append(link_data['url'])
        
        if found_broken:
            issues.append(create_issue('Links', 'critical', f'{len(found_broken)} broken links found', 
                                     {'broken_links': found_broken[:10]}))
            score -= min(30, len(found_broken) * 5)
            data['broken_links'] = found_broken
    
    # Link distribution analysis
    if data['total_links'] == 0:
        issues.append(create_issue('Links', 'warning', 'No links found on page'))
        score -= 20
    else:
        # Check internal/external ratio
        if data['internal_links_count'] == 0:
            issues.append(create_issue('Links', 'warning', 'No internal links found'))
            score -= 15
        
        external_ratio = data['external_links_count'] / data['total_links']
        if external_ratio > 0.8:
            issues.append(create_issue('Links', 'warning', f'Too many external links ({data['external_links_count']}/{data['total_links']})'))
            score -= 10
        
        # Check for excessive links
        if data['total_links'] > 100:
            issues.append(create_issue('Links', 'warning', f'Too many links on page ({data['total_links']}), may dilute PageRank'))
            score -= 10
        elif data['total_links'] > 50:
            issues.append(create_issue('Links', 'notice', f'Many links on page ({data['total_links']}), consider reducing'))
            score -= 5
    
    # Anchor text analysis
    if anchor_texts:
        # Check for generic anchor text
        generic_anchors = ['click here', 'here', 'read more', 'more', 'link', 'this', 
                          'page', 'article', 'website', 'site', 'url']
        
        generic_count = sum(1 for text in anchor_texts if text in generic_anchors)
        if generic_count > len(anchor_texts) * 0.2:
            issues.append(create_issue('Links', 'warning', f'Too many generic anchor texts ({generic_count}), use descriptive text'))
            score -= 10
        elif generic_count > 0:
            issues.append(create_issue('Links', 'notice', f'{generic_count} generic anchor texts found, use descriptive text'))
            score -= 5
        
        # Check for empty anchor text
        empty_anchors = len(all_links) - len([a for a in anchor_texts if a])
        if empty_anchors > 0:
            issues.append(create_issue('Links', 'warning', f'{empty_anchors} links with empty anchor text'))
            score -= min(15, empty_anchors * 3)
        
        # Check for over-optimized anchor text (keyword stuffing)
        anchor_counter = Counter(anchor_texts)
        most_common = anchor_counter.most_common(1)
        if most_common and most_common[0][1] > 5:
            repeated_text, count = most_common[0]
            if len(repeated_text) > 3:  # Ignore very short text
                issues.append(create_issue('Links', 'warning', f'Anchor text "{repeated_text}" repeated {count} times (possible over-optimization)'))
                score -= 10
        
        # Store top anchor texts
        data['top_anchor_texts'] = dict(anchor_counter.most_common(10))
    
    # Check for orphan pages (no internal links pointing to important pages)
    # This is a simplified check - in production you'd analyze the entire site
    important_pages = ['/about', '/contact', '/products', '/services', '/blog']
    found_important = []
    
    for link_data in internal_links:
        link_path = urlparse(link_data['url']).path.lower()
        for important in important_pages:
            if important in link_path:
                found_important.append(important)
                break
    
    missing_important = [p for p in important_pages[:3] if p not in found_important]  # Check first 3
    if missing_important:
        issues.append(create_issue('Links', 'notice', f'No links to common pages: {", ".join(missing_important)}'))
        score -= 3
    
    # Check for reciprocal links (simplified - just check for same domain external links)
    self_referencing = 0
    base_domain = urlparse(url).netloc
    
    for ext_link in external_links:
        if base_domain in ext_link['url']:
            self_referencing += 1
    
    if self_referencing > 3:
        issues.append(create_issue('Links', 'notice', f'{self_referencing} links to same domain marked as external'))
        score -= 5
    
    # Check for affiliate/sponsored links without proper rel
    affiliate_keywords = ['affiliate', 'sponsor', 'partner', 'ad', 'promo']
    potential_affiliate = []
    
    for link_data in external_links:
        link_url = link_data['url'].lower()
        link_text = link_data['text'].lower()
        
        for keyword in affiliate_keywords:
            if keyword in link_url or keyword in link_text:
                rel_str = ' '.join(link_data['rel']) if isinstance(link_data['rel'], list) else str(link_data['rel'])
                if 'sponsored' not in rel_str.lower() and 'nofollow' not in rel_str.lower():
                    potential_affiliate.append(link_data['url'])
                    break
    
    if potential_affiliate:
        issues.append(create_issue('Links', 'warning', f'{len(potential_affiliate)} potential affiliate/sponsored links without proper rel attributes'))
        score -= 10
        data['potential_affiliate_links'] = potential_affiliate[:5]
    
    # Check for deep linking (links to specific sections)
    fragment_links = [l for l in all_links if '#' in l.get('href', '') and l.get('href') != '#']
    data['fragment_links_count'] = len(fragment_links)
    
    if len(fragment_links) == 0 and data['total_links'] > 20:
        issues.append(create_issue('Links', 'notice', 'No deep links (anchors) found, consider linking to page sections'))
        score -= 3
    
    # Check for file downloads
    download_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar']
    download_links = []
    
    for link in all_links:
        href = link.get('href', '').lower()
        for ext in download_extensions:
            if ext in href:
                download_links.append(href)
                # Check for download attribute
                if not link.get('download'):
                    issues.append(create_issue('Links', 'notice', f'Download link without download attribute: {ext}'))
                    score -= 2
                    break
                break
    
    data['download_links_count'] = len(download_links)
    
    # Check link hierarchy (navigation structure)
    nav_elements = soup.find_all(['nav', 'header'])
    nav_links = []
    for nav in nav_elements:
        nav_links.extend(nav.find_all('a', href=True))
    
    data['navigation_links_count'] = len(nav_links)
    
    if len(nav_links) == 0:
        issues.append(create_issue('Links', 'warning', 'No navigation links found in <nav> or <header>'))
        score -= 10
    elif len(nav_links) > 50:
        issues.append(create_issue('Links', 'notice', f'Too many navigation links ({len(nav_links)}), consider simplifying'))
        score -= 5
    
    # Footer links
    footer = soup.find('footer')
    footer_links = []
    if footer:
        footer_links = footer.find_all('a', href=True)
        data['footer_links_count'] = len(footer_links)
        
        if len(footer_links) > 100:
            issues.append(create_issue('Links', 'notice', f'Too many footer links ({len(footer_links)})'))
            score -= 3
    else:
        data['footer_links_count'] = 0
        issues.append(create_issue('Links', 'notice', 'No footer element found'))
        score -= 3
    
    return {
        'score': max(0, score),
        'issues': issues,
        'data': data
    }
