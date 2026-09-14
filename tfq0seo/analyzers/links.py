"""Static link evidence extraction and local accessibility checks."""

import re
import math
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, parse_qs
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup, Tag
from .common import (classify_url, document_base_url, is_internal_url,
                     make_issue, resolve_url)
from ..rules import RuleDefinition, RuleCollector, register_rules, score_findings, recommendations_for
from ..page_facts import PageFacts, ensure_page_facts


_LINK_REFERENCE = 'https://developers.google.com/search/docs/crawling-indexing/links-crawlable'
_SPAM_REFERENCE = 'https://developers.google.com/search/docs/essentials/spam-policies'
LINK_RULES = (
    RuleDefinition('links.missing_anchor', 'links', 'warning',
        'Give the link an accessible name using meaningful text, a suitable image alternative, or an appropriate accessible label.',
        'HTTP(S) links have no text, image alternative, aria-label, resolvable aria-labelledby, or title in the supplied HTML; CSS-generated and script-generated names are not assessed.',
        ('https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html', _LINK_REFERENCE), '2026-09-14'),
    RuleDefinition('links.invalid_url', 'links', 'warning',
        'Replace the invalid href with a valid destination, or use a button for an action.',
        'An anchor href cannot be resolved as a valid URL reference in this document.',
        (_LINK_REFERENCE,), '2026-09-14'),
    RuleDefinition('links.javascript_url', 'links', 'warning',
        'Use a real href for navigation; use a button for an action that has no URL.',
        'An anchor uses a javascript URL rather than a crawlable destination.',
        (_LINK_REFERENCE, 'https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/a'), '2026-09-14'),
    RuleDefinition('links.broken', 'links', 'critical',
        'Verify the failed destination, update the link to a working URL, or remove it if it no longer serves a purpose.',
        'The supplied destination checks identify failed linked URLs; unchecked destinations are unknown, and transient failures require verification.',
        ('https://developers.google.com/crawling/docs/troubleshooting/http-status-codes',), '2026-09-14'),
    RuleDefinition('links.repeated_anchor', 'links', 'notice',
        'Review repeated anchor text in context; consistent navigation labels may be appropriate.',
        'A multiword anchor exceeds 10% of the sample; this local threshold does not establish over-optimization.',
        (_LINK_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('links.generic_anchor', 'links', 'notice',
        'Check whether link purpose is clear from its accessible name and surrounding context.',
        'A known English generic anchor exceeds a combined 20% of the sample; purpose can still be provided by context.',
        (_LINK_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('links.short_anchor', 'links', 'notice',
        'Review short anchor labels in their context; length does not establish keyword targeting or manipulation.',
        'Anchors matching the legacy 2-4 character pattern exceed 30% of the sample; descriptive observation only.',
        (_LINK_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('links.repeated_external_domain', 'links', 'notice',
        'Review whether repeated references to this destination help readers; there is no universal maximum link count.',
        'More than five references point to one external domain; repeated references do not establish a link scheme.',
        (_LINK_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('links.reciprocal_wording', 'links', 'notice',
        'Review the relationship and purpose of the link; wording alone does not establish an excessive link exchange.',
        'External link wording contains exchange, partner, reciprocal, or link-to-us; a low-confidence text heuristic.',
        (_SPAM_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('links.paid_wording', 'links', 'notice',
        'If the link is paid or sponsored, qualify it with sponsored or nofollow. First verify the commercial relationship.',
        'Link text or context contains a commercial keyword without sponsored/nofollow; the relationship is not verified.',
        (_LINK_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('links.hidden', 'links', 'notice',
        'Review the hidden link in context; navigation and interactive interfaces can legitimately hide links until needed.',
        'Caller-supplied or inline HTML evidence marks a link hidden; this does not establish manipulative intent.',
        (_SPAM_REFERENCE,), '2026-09-14', scored=False),
)
register_rules(LINK_RULES)


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
    quality: Optional[LinkQuality] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    position: str = "body"
    depth: int = 0
    is_image_link: bool = False
    has_title: bool = False
    opens_new_tab: bool = False
    is_javascript: bool = False
    domain_authority_estimate: Optional[int] = None


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None,
                 rule_id: Optional[str] = None, evidence: Any = None,
                 confidence: str = 'high') -> Dict[str, Any]:
    """Compatibility helper; registered rule identity supplies the guidance."""
    return make_issue(category, severity, message, details, rule_id, evidence,
                      confidence=confidence)


def normalize_url(url: str, base_url: str) -> str:
    """Resolve links while preserving paths, query order, and fragments."""
    return resolve_url(url, base_url) or url


def is_internal_link(url: str, base_url: str) -> bool:
    return is_internal_url(url, base_url)


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


def detect_link_type(link_element: Any, href: str) -> LinkType:
    """Detect the type/purpose of a link based on context."""
    # Check link location in page structure
    if isinstance(link_element, dict):
        parent_chain = link_element['parent_tags'][:5]
        parent_roles = link_element['parent_roles']
        parent_classes = link_element['parent_classes']
    else:
        parents = list(link_element.parents)
        parent_chain = [parent.name for parent in parents[:5]]
        parent_roles = [parent.get('role') for parent in parents if hasattr(parent, 'get')]
        parent_classes = [str(parent.get('class', [])) for parent in parents if hasattr(parent, 'get')]
    
    # Navigation links
    if 'nav' in parent_chain or 'navigation' in parent_roles:
        return LinkType.NAVIGATION
    
    # Footer links
    if 'footer' in parent_chain:
        return LinkType.FOOTER
    
    # Sidebar links
    if 'aside' in parent_chain or any('sidebar' in classes.lower() for classes in parent_classes):
        return LinkType.SIDEBAR
    
    # Breadcrumb links
    if any('breadcrumb' in classes.lower() for classes in parent_classes):
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


def assess_link_quality(link_profile: LinkProfile, is_internal: bool) -> Optional[LinkQuality]:
    """Destination quality cannot be established from this page's markup."""
    return None


def estimate_domain_authority(domain: str) -> Optional[int]:
    """No authority dataset is available; domain spelling is not a measure."""
    return None


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
                **create_issue('Links', 'notice', 'A repeated anchor label is common in the sample',
                               rule_id='links.repeated_anchor', evidence={'anchor': text, 'percentage': percentage, 'threshold': 10}, confidence='low'),
                'type': 'over_optimization',
                'anchor': text,
                'percentage': percentage
            })
    
    # Generic anchor text check
    generic_anchors = ['click here', 'here', 'read more', 'more', 'link', 'this']
    generic_percentage = sum(distribution.get(anchor, 0) for anchor in generic_anchors)
    if generic_percentage > 20:
        issues.append({
            **create_issue('Links', 'notice', 'Generic English labels are common in the anchor sample',
                           rule_id='links.generic_anchor', evidence={'percentage': generic_percentage, 'threshold': 20, 'labels': generic_anchors}, confidence='low'),
            'type': 'generic_overuse',
            'percentage': generic_percentage
        })
    
    # Exact match check
    exact_match_pattern = r'^[\w\s]{2,4}$'  # 2-4 word phrases
    exact_matches = [text for text in distribution.keys() if re.match(exact_match_pattern, text)]
    exact_match_percentage = sum(distribution[text] for text in exact_matches)
    if exact_match_percentage > 30:
        issues.append({
            **create_issue('Links', 'notice', 'Short labels are common in the anchor sample',
                           rule_id='links.short_anchor', evidence={'percentage': exact_match_percentage, 'threshold': 30, 'labels': exact_matches}, confidence='low'),
            'type': 'exact_match_overuse',
            'percentage': exact_match_percentage
        })
    
    return {
        'diversity_score': round(diversity_score, 2),
        'distribution': distribution,
        'issues': issues,
        'unique_anchors': len(counter),
        'most_common': [list(item) for item in counter.most_common(10)]
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
                    **create_issue('Links', 'notice', 'Multiple links reference the same external domain',
                                   rule_id='links.repeated_external_domain', evidence={'domain': domain, 'count': count, 'threshold': 5}, confidence='low'),
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
                **create_issue('Links', 'notice', 'Link wording suggests reviewing the relationship with the destination',
                               rule_id='links.reciprocal_wording', evidence={'url': link.get('url', ''), 'anchor': anchor,
                                   'matched_terms': [term for term in reciprocal_indicators if term in url or term in anchor]}, confidence='low'),
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
                    **create_issue('Links', 'notice', 'Commercial wording appears without a sponsored or nofollow qualifier',
                                   rule_id='links.paid_wording', evidence={'url': link.get('url', ''), 'anchor': anchor, 'context': context,
                                       'rel': rel, 'matched_terms': [term for term in paid_indicators if term in anchor or term in context]}, confidence='low'),
                    'type': 'untagged_paid_link',
                    'url': link.get('url', '')
                })
    
    # Check for hidden links
    for link in links:
        if link.get('is_hidden', False):
            schemes.append({
                **create_issue('Links', 'notice', 'A link is marked hidden; review its interface context',
                               rule_id='links.hidden', evidence={'url': link.get('url', ''), 'is_hidden': True}, confidence='low'),
                'type': 'hidden_link',
                'url': link.get('url', '')
            })
    
    return schemes


def analyze_link_velocity(links: List[Dict], timeframe_days: int = 30) -> Dict[str, Any]:
    """A single page snapshot provides no evidence of link growth."""
    return {
        'total_links': len(links), 'timeframe_days': None, 'links_per_day': None,
        'assessment': 'unknown', 'status': 'not_measured', 'source': 'requires_history',
    }


def analyze_internal_link_structure(internal_links: List[Dict], soup: BeautifulSoup) -> Dict[str, Any]:
    """Full graph conclusions are deferred to the post-crawl aggregation."""
    return {
        'total_internal': len(internal_links), 'orphan_pages': None,
        'link_depth_distribution': None, 'hub_pages': None,
        'cornerstone_candidates': None, 'siloing_score': None,
        'status': 'not_assessed', 'source': 'page_links_only',
    }


def analyze_links(soup: BeautifulSoup, url: str, broken_links: Optional[Set[str]] = None, *,
                  facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Extract complete link evidence; defer destination health to the crawler."""
    facts = ensure_page_facts(soup, url, facts=facts)
    collector = RuleCollector('links')
    internal_links, external_links, non_http_links = [], [], []
    anchor_texts, missing_anchors = [], []
    for record in facts.anchors:
        element = record['attrs']
        href = element.get('href', '')
        kind, resolved = record['url_kind'], record['url']
        anchor = record['labelled_text'] or record['text']
        if not anchor:
            anchor = str(element.get('aria-label', '')).strip()
        if not anchor:
            anchor = record['image_alt_text']
        if not anchor:
            anchor = str(element.get('title', '')).strip()
        rel = element.get('rel', [])
        rel = rel if isinstance(rel, list) else str(rel).split()
        rel = [str(value).lower() for value in rel]
        position = record['position']
        style = re.sub(r'\s+', '', element.get('style', '').lower())
        link_data = {
            'url': resolved, 'href': href, 'anchor_text': anchor, 'text': anchor,
            'rel': rel, 'target': element.get('target', ''),
            'context': record['context'],
            'type': detect_link_type(record, href).value, 'type_status': 'heuristic',
            'quality': None, 'quality_status': 'not_assessed',
            'position': position, 'is_internal': kind == 'internal',
            'is_hidden': 'hidden' in element or 'display:none' in style or 'visibility:hidden' in style,
            'from_url': url, 'url_kind': kind,
        }
        if kind == 'internal':
            internal_links.append(link_data)
        elif kind == 'external':
            external_links.append(link_data)
        else:
            non_http_links.append(link_data)
        if kind in ('internal', 'external'):
            if anchor:
                anchor_texts.append(anchor)
            else:
                missing_anchors.append(link_data)
    links = internal_links + external_links
    words = facts.text.split()
    domains = sorted({urlparse(link['url']).netloc for link in external_links})
    nofollow = sum('nofollow' in link['rel'] for link in links)
    metrics = {
        'total_links': len(links), 'internal_links': len(internal_links),
        'external_links': len(external_links), 'non_http_links': len(non_http_links),
        'dofollow_links': len(links) - nofollow, 'nofollow_links': nofollow,
        'sponsored_links': sum('sponsored' in link['rel'] for link in links),
        'ugc_links': sum('ugc' in link['rel'] for link in links),
        'link_density': round(len(links) / len(words) * 100, 2) if words else None,
        'internal_external_ratio': round(len(internal_links) / len(external_links), 2) if external_links else None,
        'avg_anchor_length': round(sum(len(anchor.split()) for anchor in anchor_texts) / len(anchor_texts), 2) if anchor_texts else None,
        'unique_domains': len(domains),
    }
    collector.check('links.missing_anchor', bool(missing_anchors),
        evidence={'links': missing_anchors, 'http_link_count': len(links)}, category='Links',
        applicable=bool(links), reason='Requires HTTP(S) links.',
        message=f'{len(missing_anchors)} web links have no accessible name in the supplied HTML')
    invalid = [link for link in non_http_links if link['url_kind'] == 'invalid']
    collector.check('links.invalid_url', bool(invalid), evidence={'links': invalid}, category='Links',
        applicable=bool(links or non_http_links), reason='Requires anchor elements with href.',
        message=f'{len(invalid)} links have empty or invalid URL references')
    javascript = [link for link in non_http_links if link['url_kind'] == 'javascript']
    collector.check('links.javascript_url', bool(javascript), evidence={'links': javascript}, category='Links',
        applicable=bool(links or non_http_links), reason='Requires anchor elements with href.',
        message=f'{len(javascript)} JavaScript links have no crawlable URL destination')
    found_broken = [link['url'] for link in links if broken_links is not None and link['url'] in broken_links]
    broken_result = collector.check('links.broken', True if found_broken else None,
        evidence={'urls': found_broken, 'http_link_count': len(links), 'known_failures_supplied': broken_links is not None,
                  'unchecked_urls': sorted({link['url'] for link in links} - set(found_broken))},
        applicable=bool(links), category='Links', source='supplied_destination_checks',
        reason='No HTTP(S) links to check.' if not links else 'Only known failed URLs are available; other destination health is unknown.',
        message=f'{len(found_broken)} broken links found' if found_broken else 'Destination health has not been established')
    if found_broken:
        broken_result['details'] = {'broken_links': found_broken}
    anchor_analysis = analyze_anchor_text_distribution(anchor_texts)
    # Distribution describes the sample; it does not establish over-optimization.
    anchor_analysis['issues'] = []
    anchor_analysis['status'] = 'descriptive_statistics'
    data = {
        'score_scope': 'static_link_checks', 'metrics': metrics,
        'internal_links': internal_links, 'external_links': external_links,
        'non_http_links': non_http_links, 'external_domains': domains,
        'anchor_analysis': anchor_analysis,
        'internal_structure': analyze_internal_link_structure(internal_links, soup),
        'link_velocity': analyze_link_velocity(links),
        'authority_status': 'not_measured', 'quality_distribution': {'unknown': len(links)},
        'type_distribution': dict(Counter(link['type'] for link in links)),
        'position_distribution': dict(Counter(link['position'] for link in links)),
        'broken_links': found_broken if broken_links is not None else None,
        'link_health_status': 'partial' if broken_links is not None else 'not_checked',
    }
    issues = collector.issues
    score = score_findings(issues)
    recommendations = recommendations_for(issues)
    data['recommendations'] = recommendations
    return {'score': score, 'issues': issues, 'data': data, 'recommendations': recommendations,
            'rule_results': collector.results, 'rule_coverage': collector.coverage}
