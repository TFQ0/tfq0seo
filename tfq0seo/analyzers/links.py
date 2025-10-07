"""Advanced link analyzer with comprehensive link quality assessment and SEO optimization."""

import re
import math
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, parse_qs
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup, Tag


class LinkType(Enum):
    """Types of links for categorization."""
    NAVIGATION = "navigation"
    CONTENT = "content"
    FOOTER = "footer"
    SIDEBAR = "sidebar"
    BREADCRUMB = "breadcrumb"
    SOCIAL = "social"
    RESOURCE = "resource"
    AFFILIATE = "affiliate"
    ADVERTISEMENT = "advertisement"
    PAGINATION = "pagination"


class LinkQuality(Enum):
    """Link quality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TOXIC = "toxic"


@dataclass
class LinkMetrics:
    """Container for link metrics."""
    total_links: int = 0
    internal_links: int = 0
    external_links: int = 0
    dofollow_links: int = 0
    nofollow_links: int = 0
    ugc_links: int = 0
    sponsored_links: int = 0
    broken_links: int = 0
    redirected_links: int = 0
    link_density: float = 0.0
    internal_external_ratio: float = 0.0
    avg_anchor_length: float = 0.0
    unique_domains: int = 0
    link_velocity: float = 0.0


@dataclass
class LinkProfile:
    """Detailed link profile information."""
    url: str
    anchor_text: str
    context: str = ""
    type: LinkType = LinkType.CONTENT
    quality: LinkQuality = LinkQuality.MEDIUM
    attributes: Dict[str, Any] = field(default_factory=dict)
    position: str = "body"
    depth: int = 0
    is_image_link: bool = False
    has_title: bool = False
    opens_new_tab: bool = False
    is_javascript: bool = False
    domain_authority_estimate: int = 0


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create an enhanced issue dictionary with recommendations."""
    issue = {
        'category': category,
        'severity': severity,  # critical, warning, notice
        'message': message
    }
    if details:
        issue['details'] = details
    
    # Add fix recommendations based on issue type
    if 'broken' in message.lower():
        issue['fix'] = "Fix or remove broken links. Use 301 redirects for moved content."
    elif 'anchor text' in message.lower():
        issue['fix'] = "Use descriptive, keyword-rich anchor text that tells users what to expect."
    elif 'nofollow' in message.lower():
        issue['fix'] = "Use nofollow for untrusted content, sponsored for paid links, ugc for user content."
    elif 'external' in message.lower():
        issue['fix'] = "Balance external links with internal links. Link to authoritative sources."
    
    return issue


def normalize_url(url: str, base_url: str) -> str:
    """Advanced URL normalization for consistency."""
    if not url:
        return ""
    
    # Handle special protocols
    if url.startswith(('mailto:', 'tel:', 'javascript:', 'data:', '#')):
        return url
    
    # Make URL absolute
    absolute = urljoin(base_url, url)
    
    # Parse URL
    parsed = urlparse(absolute)
    
    # Normalize domain (remove www if present)
    netloc = parsed.netloc.lower()
    if netloc.startswith('www.'):
        netloc_no_www = netloc[4:]
    else:
        netloc_no_www = netloc
    
    # Normalize path
    path = parsed.path
    if path:
        # Remove duplicate slashes
        path = re.sub(r'/+', '/', path)
        # Remove trailing slash except for root
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
    else:
        path = '/'
    
    # Remove common tracking parameters
    if parsed.query:
        params = parse_qs(parsed.query)
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'track'
        }
        cleaned_params = {k: v for k, v in params.items() if k.lower() not in tracking_params}
        if cleaned_params:
            from urllib.parse import urlencode
            query = urlencode(cleaned_params, doseq=True)
        else:
            query = ''
    else:
        query = parsed.query
    
    # Reconstruct URL
    normalized = f"{parsed.scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    
    return normalized


def is_internal_link(url: str, base_url: str) -> bool:
    """Check if a URL is internal with subdomain handling."""
    if not url:
        return True
    
    # Special URLs are not internal
    if url.startswith(('mailto:', 'tel:', 'javascript:', 'data:')):
        return False
    
    # Fragment-only links are internal
    if url.startswith('#'):
        return True
    
    # Parse both URLs
    base_parsed = urlparse(base_url)
    url_parsed = urlparse(urljoin(base_url, url))
    
    # Get base domains (without www)
    base_domain = base_parsed.netloc.lower().replace('www.', '')
    url_domain = url_parsed.netloc.lower().replace('www.', '')
    
    # Check if same domain or subdomain
    if base_domain == url_domain:
        return True
    
    # Check for subdomain relationship
    if url_domain.endswith('.' + base_domain) or base_domain.endswith('.' + url_domain):
        return True
    
    return False


def extract_link_context(link_element: Tag, chars_before: int = 50, chars_after: int = 50) -> str:
    """Extract surrounding text context for a link."""
    try:
        # Get parent paragraph or container
        parent = link_element.parent
        if parent and parent.name in ['p', 'div', 'li', 'td', 'article', 'section']:
            text = parent.get_text(strip=True)
            link_text = link_element.get_text(strip=True)
            
            # Find link position in parent text
            if link_text in text:
                index = text.index(link_text)
                start = max(0, index - chars_before)
                end = min(len(text), index + len(link_text) + chars_after)
                
                context = text[start:end]
                if start > 0:
                    context = '...' + context
                if end < len(text):
                    context = context + '...'
                
                return context
    except:
        pass
    
    return ""


def detect_link_type(link_element: Tag, href: str) -> LinkType:
    """Detect the type/purpose of a link based on context."""
    # Check link location in page structure
    parent_chain = []
    current = link_element
    for _ in range(5):  # Check up to 5 parents
        if current.parent:
            current = current.parent
            parent_chain.append(current.name)
    
    # Navigation links
    if 'nav' in parent_chain or any(p.get('role') == 'navigation' for p in link_element.parents if hasattr(p, 'get')):
        return LinkType.NAVIGATION
    
    # Footer links
    if 'footer' in parent_chain:
        return LinkType.FOOTER
    
    # Sidebar links
    if 'aside' in parent_chain or any('sidebar' in str(p.get('class', [])).lower() for p in link_element.parents if hasattr(p, 'get')):
        return LinkType.SIDEBAR
    
    # Breadcrumb links
    if any('breadcrumb' in str(p.get('class', [])).lower() for p in link_element.parents if hasattr(p, 'get')):
        return LinkType.BREADCRUMB
    
    # Social media links
    social_domains = ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 
                     'youtube.com', 'pinterest.com', 'tiktok.com']
    if any(domain in href.lower() for domain in social_domains):
        return LinkType.SOCIAL
    
    # Affiliate links
    affiliate_patterns = ['amzn.to', 'affiliate', 'partner', 'ref=', 'click.linksynergy']
    if any(pattern in href.lower() for pattern in affiliate_patterns):
        return LinkType.AFFILIATE
    
    # Pagination links
    if re.search(r'[?&](page|p)=\d+', href) or re.search(r'/page/\d+', href):
        return LinkType.PAGINATION
    
    # Resource/download links
    resource_extensions = ['.pdf', '.doc', '.xls', '.zip', '.ppt', '.mp3', '.mp4']
    if any(ext in href.lower() for ext in resource_extensions):
        return LinkType.RESOURCE
    
    # Default to content link
    return LinkType.CONTENT


def assess_link_quality(link_profile: LinkProfile, is_internal: bool) -> LinkQuality:
    """Assess the quality of a link based on various factors."""
    score = 50  # Start with neutral score
    
    # Anchor text quality
    anchor = link_profile.anchor_text.lower()
    if not anchor or anchor in ['click here', 'here', 'link', 'this']:
        score -= 20
    elif len(anchor) > 60:
        score -= 10
    elif len(anchor.split()) >= 3:  # Good descriptive anchor
        score += 10
    
    # Link type scoring
    if link_profile.type == LinkType.NAVIGATION:
        score += 5
    elif link_profile.type == LinkType.AFFILIATE:
        score -= 10
    elif link_profile.type == LinkType.SOCIAL:
        score += 0  # Neutral
    
    # Attributes scoring
    if link_profile.opens_new_tab and not link_profile.attributes.get('rel', ''):
        score -= 15  # Security issue
    
    if link_profile.is_javascript:
        score -= 10  # Not crawlable
    
    if link_profile.has_title:
        score += 5  # Good for accessibility
    
    # Position scoring
    if link_profile.position == 'header':
        score += 10
    elif link_profile.position == 'footer':
        score -= 5
    
    # External link specific scoring
    if not is_internal:
        if link_profile.domain_authority_estimate > 50:
            score += 20
        elif link_profile.domain_authority_estimate < 20:
            score -= 15
    
    # Determine quality level
    if score >= 70:
        return LinkQuality.HIGH
    elif score >= 40:
        return LinkQuality.MEDIUM
    elif score >= 20:
        return LinkQuality.LOW
    else:
        return LinkQuality.TOXIC


def estimate_domain_authority(domain: str) -> int:
    """Estimate domain authority based on domain characteristics."""
    # This is a simplified estimation. In production, use APIs like Moz or Ahrefs
    score = 30  # Default score
    
    # Well-known high-authority domains
    high_authority = {
        'google.com': 100, 'youtube.com': 100, 'facebook.com': 100,
        'wikipedia.org': 100, 'amazon.com': 96, 'twitter.com': 94,
        'linkedin.com': 98, 'github.com': 96, 'microsoft.com': 95,
        'apple.com': 95, 'stackoverflow.com': 93, 'medium.com': 92,
        'reddit.com': 91, 'bbc.com': 94, 'cnn.com': 93, 'nytimes.com': 94,
        'forbes.com': 95, 'harvard.edu': 95, 'mit.edu': 94, 'stanford.edu': 95,
        '.gov': 90, '.edu': 70, '.org': 50
    }
    
    # Check exact matches
    domain_lower = domain.lower()
    for auth_domain, auth_score in high_authority.items():
        if auth_domain in domain_lower:
            return auth_score
    
    # TLD scoring
    if domain.endswith('.gov'):
        score = 90
    elif domain.endswith('.edu'):
        score = 70
    elif domain.endswith('.org'):
        score = 50
    elif domain.endswith(('.io', '.ai', '.app')):
        score = 40
    
    # Domain length (shorter is often better)
    domain_name = domain.split('.')[0]
    if len(domain_name) <= 10:
        score += 10
    elif len(domain_name) > 20:
        score -= 10
    
    # Hyphens in domain (often lower quality)
    if '-' in domain:
        score -= 10 * domain.count('-')
    
    return max(0, min(100, score))


def calculate_pagerank_flow(internal_links: List[Dict], max_iterations: int = 10) -> Dict[str, float]:
    """Calculate simplified PageRank-style link value flow."""
    if not internal_links:
        return {}
    
    # Build link graph
    graph = defaultdict(list)
    all_urls = set()
    
    for link in internal_links:
        from_url = link.get('from_url', '')
        to_url = link.get('url', '')
        if from_url and to_url:
            graph[from_url].append(to_url)
            all_urls.add(from_url)
            all_urls.add(to_url)
    
    # Initialize PageRank values
    pagerank = {url: 1.0 / len(all_urls) for url in all_urls}
    damping_factor = 0.85
    
    # Iterate to calculate PageRank
    for _ in range(max_iterations):
        new_pagerank = {}
        for url in all_urls:
            rank = (1 - damping_factor) / len(all_urls)
            
            # Add contributions from pages linking to this page
            for other_url, links in graph.items():
                if url in links:
                    rank += damping_factor * pagerank[other_url] / len(links)
            
            new_pagerank[url] = rank
        
        pagerank = new_pagerank
    
    return pagerank


def analyze_anchor_text_distribution(anchor_texts: List[str]) -> Dict[str, Any]:
    """Analyze anchor text distribution for over-optimization."""
    if not anchor_texts:
        return {
            'diversity_score': 0,
            'distribution': {},
            'issues': []
        }
    
    # Clean and normalize anchor texts
    cleaned = [text.lower().strip() for text in anchor_texts if text]
    
    # Calculate distribution
    total = len(cleaned)
    counter = Counter(cleaned)
    distribution = {text: count/total*100 for text, count in counter.most_common(20)}
    
    # Calculate diversity score (Shannon entropy)
    entropy = 0
    for count in counter.values():
        if count > 0:
            prob = count / total
            entropy -= prob * math.log2(prob)
    
    max_entropy = math.log2(total) if total > 1 else 1
    diversity_score = (entropy / max_entropy * 100) if max_entropy > 0 else 0
    
    # Detect issues
    issues = []
    
    # Over-optimization check
    for text, percentage in distribution.items():
        if percentage > 10 and len(text.split()) > 1:  # Multi-word anchor
            issues.append({
                'type': 'over_optimization',
                'anchor': text,
                'percentage': percentage
            })
    
    # Generic anchor text check
    generic_anchors = ['click here', 'here', 'read more', 'more', 'link', 'this']
    generic_percentage = sum(distribution.get(anchor, 0) for anchor in generic_anchors)
    if generic_percentage > 20:
        issues.append({
            'type': 'generic_overuse',
            'percentage': generic_percentage
        })
    
    # Exact match check
    exact_match_pattern = r'^[\w\s]{2,4}$'  # 2-4 word phrases
    exact_matches = [text for text in distribution.keys() if re.match(exact_match_pattern, text)]
    exact_match_percentage = sum(distribution[text] for text in exact_matches)
    if exact_match_percentage > 30:
        issues.append({
            'type': 'exact_match_overuse',
            'percentage': exact_match_percentage
        })
    
    return {
        'diversity_score': round(diversity_score, 2),
        'distribution': distribution,
        'issues': issues,
        'unique_anchors': len(counter),
        'most_common': counter.most_common(10)
    }


def detect_link_schemes(links: List[Dict]) -> List[Dict[str, Any]]:
    """Detect potential link schemes or manipulative patterns."""
    schemes = []
    
    if not links:
        return schemes
    
    # Extract domains
    external_links = [l for l in links if not l.get('is_internal', True)]
    external_domains = [urlparse(l.get('url', '')).netloc for l in external_links]
    
    # Check for excessive links to single domain
    if external_domains:
        domain_counts = Counter(external_domains)
        for domain, count in domain_counts.items():
            if count > 5:  # More than 5 links to same external domain
                schemes.append({
                    'type': 'excessive_linking',
                    'domain': domain,
                    'count': count
                })
    
    # Check for reciprocal linking patterns
    reciprocal_indicators = ['exchange', 'partner', 'reciprocal', 'link-to-us']
    for link in external_links:
        url = link.get('url', '').lower()
        anchor = link.get('anchor_text', '').lower()
        if any(indicator in url or indicator in anchor for indicator in reciprocal_indicators):
            schemes.append({
                'type': 'potential_reciprocal',
                'url': link.get('url', '')
            })
    
    # Check for paid link indicators
    paid_indicators = ['sponsored', 'advertisement', 'paid', 'promoted']
    for link in external_links:
        anchor = link.get('anchor_text', '').lower()
        context = link.get('context', '').lower()
        rel = str(link.get('rel', '')).lower()
        
        if any(indicator in anchor or indicator in context for indicator in paid_indicators):
            if 'sponsored' not in rel and 'nofollow' not in rel:
                schemes.append({
                    'type': 'untagged_paid_link',
                    'url': link.get('url', '')
                })
    
    # Check for hidden links
    for link in links:
        if link.get('is_hidden', False):
            schemes.append({
                'type': 'hidden_link',
                'url': link.get('url', '')
            })
    
    return schemes


def analyze_link_velocity(links: List[Dict], timeframe_days: int = 30) -> Dict[str, Any]:
    """Analyze link growth patterns and velocity."""
    # This is simplified - in production, you'd track link changes over time
    total_links = len(links)
    
    # Calculate estimated velocity
    links_per_day = total_links / max(1, timeframe_days)
    
    # Determine if velocity is suspicious
    velocity_assessment = 'normal'
    if links_per_day > 100:
        velocity_assessment = 'very_high'
    elif links_per_day > 50:
        velocity_assessment = 'high'
    elif links_per_day < 1:
        velocity_assessment = 'low'
    
    return {
        'total_links': total_links,
        'timeframe_days': timeframe_days,
        'links_per_day': round(links_per_day, 2),
        'assessment': velocity_assessment
    }


def analyze_internal_link_structure(internal_links: List[Dict], soup: BeautifulSoup) -> Dict[str, Any]:
    """Analyze internal linking structure and optimization."""
    structure = {
        'total_internal': len(internal_links),
        'orphan_pages': [],
        'link_depth_distribution': defaultdict(int),
        'hub_pages': [],
        'cornerstone_candidates': [],
        'siloing_score': 0
    }
    
    if not internal_links:
        return structure
    
    # Count links per page
    page_link_counts = defaultdict(int)
    for link in internal_links:
        to_url = link.get('url', '')
        page_link_counts[to_url] += 1
    
    # Identify hub pages (pages with many incoming links)
    avg_links = sum(page_link_counts.values()) / max(1, len(page_link_counts))
    for page, count in page_link_counts.items():
        if count > avg_links * 2:
            structure['hub_pages'].append({
                'url': page,
                'incoming_links': count
            })
    
    # Identify potential cornerstone content
    # (Pages with both many incoming and outgoing links)
    outgoing_counts = defaultdict(int)
    for link in internal_links:
        from_url = link.get('from_url', '')
        outgoing_counts[from_url] += 1
    
    for page in set(page_link_counts.keys()) & set(outgoing_counts.keys()):
        if page_link_counts[page] > avg_links and outgoing_counts[page] > avg_links:
            structure['cornerstone_candidates'].append({
                'url': page,
                'incoming': page_link_counts[page],
                'outgoing': outgoing_counts[page]
            })
    
    # Analyze link depth (simplified)
    for link in internal_links:
        depth = link.get('depth', 0)
        structure['link_depth_distribution'][depth] += 1
    
    # Calculate siloing score (how well topics are grouped)
    # This is simplified - proper siloing analysis would require content analysis
    category_patterns = ['/blog/', '/products/', '/services/', '/resources/']
    category_links = defaultdict(int)
    
    for link in internal_links:
        url = link.get('url', '')
        for pattern in category_patterns:
            if pattern in url:
                category_links[pattern] += 1
                break
    
    if category_links:
        # Higher score if links are well-distributed across categories
        total_categorized = sum(category_links.values())
        entropy = 0
        for count in category_links.values():
            if count > 0:
                prob = count / total_categorized
                entropy -= prob * math.log2(prob)
        
        max_entropy = math.log2(len(category_links))
        structure['siloing_score'] = round((entropy / max_entropy * 100) if max_entropy > 0 else 0, 2)
    
    return structure


def analyze_links(soup: BeautifulSoup, url: str, broken_links: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Advanced link analysis with comprehensive quality assessment."""
    issues = []
    data = {}
    
    # Extract word count for link density calculation
    text_content = soup.get_text(strip=True)
    word_count = len(text_content.split())
    
    # Find all links with detailed extraction
    all_links = soup.find_all('a')
    link_profiles = []
    
    internal_links = []
    external_links = []
    anchor_texts = []
    
    # Analyze each link in detail
    for link_element in all_links:
        href = link_element.get('href', '')
        if not href:
            continue
        
        # Extract comprehensive link information
        anchor_text = link_element.get_text(strip=True)
        title = link_element.get('title', '')
        rel = link_element.get('rel', [])
        target = link_element.get('target', '')
        link_class = link_element.get('class', [])
        
        # Normalize URL
        try:
            normalized_url = normalize_url(href, url)
        except:
            normalized_url = href
        
        # Determine if internal
        is_internal = is_internal_link(href, url)
        
        # Extract context
        context = extract_link_context(link_element)
        
        # Detect link type
        link_type = detect_link_type(link_element, href)
        
        # Determine position
        position = 'body'
        for parent in link_element.parents:
            if parent.name == 'header':
                position = 'header'
                break
            elif parent.name == 'footer':
                position = 'footer'
                break
            elif parent.name == 'nav':
                position = 'navigation'
                break
        
        # Check for hidden link
        is_hidden = False
        style = link_element.get('style', '')
        if 'display:none' in style.replace(' ', '') or 'visibility:hidden' in style:
            is_hidden = True
        
        # Check if image link
        is_image_link = bool(link_element.find('img'))
        
        # Create link profile
        profile = LinkProfile(
            url=normalized_url,
            anchor_text=anchor_text,
            context=context,
            type=link_type,
            attributes={
                'rel': rel,
                'target': target,
                'title': title,
                'class': link_class,
                'is_hidden': is_hidden
            },
            position=position,
            is_image_link=is_image_link,
            has_title=bool(title),
            opens_new_tab=(target == '_blank'),
            is_javascript=href.startswith('javascript:')
        )
        
        # Estimate domain authority for external links
        if not is_internal:
            domain = urlparse(normalized_url).netloc
            profile.domain_authority_estimate = estimate_domain_authority(domain)
        
        # Assess link quality
        profile.quality = assess_link_quality(profile, is_internal)
        
        # Store profile
        link_profiles.append(profile)
        
        # Categorize for basic analysis
        link_data = {
            'url': normalized_url,
            'anchor_text': anchor_text,
            'text': anchor_text,
            'rel': rel,
            'target': target,
            'context': context,
            'type': link_type.value,
            'quality': profile.quality.value,
            'position': position,
            'is_internal': is_internal,
            'is_hidden': is_hidden,
            'from_url': url
        }
        
        if is_internal:
            internal_links.append(link_data)
        else:
            external_links.append(link_data)
        
        if anchor_text:
            anchor_texts.append(anchor_text)
    
    # Calculate metrics
    metrics = LinkMetrics(
        total_links=len(link_profiles),
        internal_links=len(internal_links),
        external_links=len(external_links)
    )
    
    # Analyze rel attributes
    for profile in link_profiles:
        rel_values = profile.attributes.get('rel', [])
        if isinstance(rel_values, list):
            rel_str = ' '.join(rel_values)
        else:
            rel_str = str(rel_values)
        
        rel_lower = rel_str.lower()
        if 'nofollow' in rel_lower:
            metrics.nofollow_links += 1
        else:
            metrics.dofollow_links += 1
        
        if 'sponsored' in rel_lower:
            metrics.sponsored_links += 1
        if 'ugc' in rel_lower:
            metrics.ugc_links += 1
    
    # Calculate ratios and density
    if metrics.total_links > 0:
        metrics.internal_external_ratio = metrics.internal_links / max(1, metrics.external_links)
        metrics.link_density = (metrics.total_links / max(1, word_count)) * 100
    
    if anchor_texts:
        metrics.avg_anchor_length = sum(len(a.split()) for a in anchor_texts) / len(anchor_texts)
    
    # Count unique external domains
    external_domains = set()
    for link in external_links:
        domain = urlparse(link['url']).netloc
        if domain:
            external_domains.add(domain)
    metrics.unique_domains = len(external_domains)
    
    # Store metrics
    data['metrics'] = {
        'total_links': metrics.total_links,
        'internal_links': metrics.internal_links,
        'external_links': metrics.external_links,
        'dofollow_links': metrics.dofollow_links,
        'nofollow_links': metrics.nofollow_links,
        'sponsored_links': metrics.sponsored_links,
        'ugc_links': metrics.ugc_links,
        'link_density': round(metrics.link_density, 2),
        'internal_external_ratio': round(metrics.internal_external_ratio, 2),
        'avg_anchor_length': round(metrics.avg_anchor_length, 2),
        'unique_domains': metrics.unique_domains
    }
    
    # Check for broken links
    if broken_links:
        found_broken = []
        for link in internal_links + external_links:
            if link['url'] in broken_links:
                found_broken.append(link['url'])
                metrics.broken_links += 1
        
        if found_broken:
            issues.append(create_issue('Links', 'critical',
                f'{len(found_broken)} broken links found',
                {'broken_links': found_broken[:10]}))
            data['broken_links'] = found_broken
    
    # Analyze anchor text distribution
    anchor_analysis = analyze_anchor_text_distribution(anchor_texts)
    data['anchor_analysis'] = anchor_analysis
    
    if anchor_analysis['diversity_score'] < 50:
        issues.append(create_issue('Links', 'warning',
            f'Low anchor text diversity (score: {anchor_analysis["diversity_score"]}%)'))
    
    for issue in anchor_analysis['issues']:
        if issue['type'] == 'over_optimization':
            issues.append(create_issue('Links', 'warning',
                f'Anchor text "{issue["anchor"]}" is over-optimized ({issue["percentage"]:.1f}%)'))
        elif issue['type'] == 'generic_overuse':
            issues.append(create_issue('Links', 'warning',
                f'Too many generic anchor texts ({issue["percentage"]:.1f}%)'))
    
    # Analyze internal link structure
    internal_structure = analyze_internal_link_structure(internal_links, soup)
    data['internal_structure'] = internal_structure
    
    # Detect link schemes
    all_link_data = internal_links + external_links
    link_schemes = detect_link_schemes(all_link_data)
    if link_schemes:
        data['potential_schemes'] = link_schemes
        for scheme in link_schemes[:3]:  # Report top 3
            if scheme['type'] == 'excessive_linking':
                issues.append(create_issue('Links', 'warning',
                    f'Excessive links to {scheme["domain"]} ({scheme["count"]} links)'))
            elif scheme['type'] == 'untagged_paid_link':
                issues.append(create_issue('Links', 'critical',
                    f'Potential paid link without proper rel attributes'))
    
    # Analyze link velocity
    velocity_analysis = analyze_link_velocity(all_link_data)
    data['link_velocity'] = velocity_analysis
    
    if velocity_analysis['assessment'] == 'very_high':
        issues.append(create_issue('Links', 'warning',
            'Unusually high link velocity detected'))
    
    # Quality distribution
    quality_distribution = Counter(p.quality.value for p in link_profiles)
    data['quality_distribution'] = dict(quality_distribution)
    
    toxic_links = quality_distribution.get('toxic', 0)
    if toxic_links > 0:
        issues.append(create_issue('Links', 'critical',
            f'{toxic_links} potentially toxic links detected'))
    
    # Link type distribution
    type_distribution = Counter(p.type.value for p in link_profiles)
    data['type_distribution'] = dict(type_distribution)
    
    # Position distribution
    position_distribution = Counter(p.position for p in link_profiles)
    data['position_distribution'] = dict(position_distribution)
    
    # Navigation analysis
    nav_links = [p for p in link_profiles if p.type == LinkType.NAVIGATION]
    if len(nav_links) == 0:
        issues.append(create_issue('Links', 'warning',
            'No navigation links detected'))
    elif len(nav_links) > 50:
        issues.append(create_issue('Links', 'notice',
            f'Too many navigation links ({len(nav_links)}), consider simplifying'))
    
    # Footer link analysis
    footer_links = [p for p in link_profiles if p.position == 'footer']
    if len(footer_links) > 100:
        issues.append(create_issue('Links', 'notice',
            f'Excessive footer links ({len(footer_links)})'))
    
    # External link quality check
    low_quality_external = [p for p in link_profiles 
                           if not is_internal_link(p.url, url) and p.quality == LinkQuality.LOW]
    if len(low_quality_external) > 5:
        issues.append(create_issue('Links', 'warning',
            f'{len(low_quality_external)} low-quality external links detected'))
    
    # Check for nofollow on all external links
    external_dofollow = [l for l in external_links 
                        if 'nofollow' not in str(l.get('rel', '')).lower()]
    if len(external_dofollow) > 10:
        issues.append(create_issue('Links', 'notice',
            f'{len(external_dofollow)} external dofollow links - consider using nofollow for untrusted content'))
    
    # Check for security issues
    security_issues = [p for p in link_profiles 
                      if p.opens_new_tab and 'noopener' not in str(p.attributes.get('rel', '')).lower()]
    if security_issues:
        issues.append(create_issue('Links', 'warning',
            f'{len(security_issues)} links with target="_blank" missing rel="noopener"'))
    
    # JavaScript links
    js_links = [p for p in link_profiles if p.is_javascript]
    if js_links:
        issues.append(create_issue('Links', 'warning',
            f'{len(js_links)} JavaScript links are not crawlable by search engines'))
    
    # Calculate overall score
    score = 100
    
    # Score based on metrics
    if metrics.total_links == 0:
        score -= 30
    elif metrics.link_density > 10:
        score -= 15
    elif metrics.link_density > 5:
        score -= 5
    
    # Score based on balance
    if metrics.internal_external_ratio < 0.5:
        score -= 10
    elif metrics.internal_external_ratio > 10:
        score -= 5
    
    # Score based on quality
    high_quality_percentage = (quality_distribution.get('high', 0) / max(1, metrics.total_links)) * 100
    if high_quality_percentage < 20:
        score -= 10
    
    # Score based on issues
    for issue in issues:
        if issue['severity'] == 'critical':
            score -= 15
        elif issue['severity'] == 'warning':
            score -= 7
        elif issue['severity'] == 'notice':
            score -= 3
    
    # Add recommendations
    data['recommendations'] = []
    
    if metrics.internal_external_ratio < 1:
        data['recommendations'].append('Add more internal links to improve site navigation and SEO')
    
    if anchor_analysis['diversity_score'] < 70:
        data['recommendations'].append('Increase anchor text diversity for better SEO')
    
    if toxic_links > 0:
        data['recommendations'].append('Review and remove potentially toxic links')
    
    if len(internal_structure['hub_pages']) < 3:
        data['recommendations'].append('Create hub pages with comprehensive internal linking')
    
    return {
        'score': max(0, min(100, score)),
        'issues': issues,
        'data': data
    }