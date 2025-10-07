"""Advanced SEO analyzer with comprehensive search optimization analysis and recommendations."""

import json
import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from bs4 import BeautifulSoup, Tag


class SEOPriority(Enum):
    """SEO priority levels for issues."""
    CRITICAL = "critical"  # Will prevent indexing or ranking
    HIGH = "high"         # Significant ranking impact
    MEDIUM = "medium"     # Moderate ranking impact
    LOW = "low"          # Minor optimization opportunity


class SchemaType(Enum):
    """Common Schema.org types."""
    ARTICLE = "Article"
    PRODUCT = "Product"
    ORGANIZATION = "Organization"
    PERSON = "Person"
    LOCAL_BUSINESS = "LocalBusiness"
    EVENT = "Event"
    RECIPE = "Recipe"
    FAQ = "FAQPage"
    HOW_TO = "HowTo"
    BREADCRUMB = "BreadcrumbList"
    VIDEO = "VideoObject"
    REVIEW = "Review"
    WEBSITE = "WebSite"
    WEBPAGE = "WebPage"


class RichSnippetType(Enum):
    """Types of rich snippets."""
    BREADCRUMBS = "breadcrumbs"
    FAQ = "faq"
    HOW_TO = "how_to"
    RECIPE = "recipe"
    REVIEW = "review"
    PRODUCT = "product"
    EVENT = "event"
    VIDEO = "video"
    ARTICLE = "article"
    SITELINKS_SEARCHBOX = "sitelinks_searchbox"


@dataclass
class MetaTagProfile:
    """Comprehensive meta tag information."""
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    author: Optional[str] = None
    robots: Optional[str] = None
    googlebot: Optional[str] = None
    canonical: Optional[str] = None
    alternate_languages: Dict[str, str] = field(default_factory=dict)
    viewport: Optional[str] = None
    charset: Optional[str] = None
    og_tags: Dict[str, str] = field(default_factory=dict)
    twitter_tags: Dict[str, str] = field(default_factory=dict)
    article_tags: Dict[str, str] = field(default_factory=dict)
    dublin_core: Dict[str, str] = field(default_factory=dict)
    custom_meta: Dict[str, str] = field(default_factory=dict)


@dataclass
class StructuredDataItem:
    """Structured data item with validation."""
    type: str
    properties: Dict[str, Any]
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    rich_snippet_eligible: bool = False
    snippet_type: Optional[RichSnippetType] = None


@dataclass
class SEOScore:
    """Detailed SEO scoring breakdown."""
    total: int = 100
    technical: int = 100
    content: int = 100
    meta_tags: int = 100
    structured_data: int = 100
    social: int = 100
    mobile: int = 100
    international: int = 100
    accessibility: int = 100
    security: int = 100


@dataclass
class SERPPreview:
    """Search Engine Results Page preview."""
    title: str
    url: str
    description: str
    title_pixels: int = 0
    description_pixels: int = 0
    breadcrumbs: Optional[str] = None
    rich_snippets: List[str] = field(default_factory=list)
    sitelinks_eligible: bool = False


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create an enhanced SEO issue with recommendations."""
    issue = {
        'category': category,
        'severity': severity,
        'message': message
    }
    if details:
        issue['details'] = details
    
    # Add specific SEO recommendations
    if 'title' in message.lower():
        issue['fix'] = "Optimize title: Include primary keyword, keep under 60 chars, make unique and compelling"
        issue['impact'] = "High - Title tags are a primary ranking factor"
    elif 'description' in message.lower():
        issue['fix'] = "Write compelling meta description: 150-160 chars, include keywords, add call-to-action"
        issue['impact'] = "Medium - Affects click-through rate from search results"
    elif 'structured data' in message.lower() or 'schema' in message.lower():
        issue['fix'] = "Implement Schema.org markup for rich snippets and better SERP visibility"
        issue['impact'] = "High - Enables rich snippets and improves click-through rates"
    elif 'canonical' in message.lower():
        issue['fix'] = "Add canonical URL to prevent duplicate content issues"
        issue['impact'] = "High - Prevents duplicate content penalties"
    elif 'h1' in message.lower() or 'heading' in message.lower():
        issue['fix'] = "Use single H1 with primary keyword, follow proper heading hierarchy"
        issue['impact'] = "High - H1 tags signal main topic to search engines"
    else:
        issue['fix'] = "Review SEO best practices for this element"
        issue['impact'] = "Varies based on implementation"
    
    return issue


def calculate_text_pixel_width(text: str, font_size: int = 16) -> int:
    """Estimate pixel width for SERP preview (simplified)."""
    # Rough approximation: average character width is about 0.5em
    # For 16px font, average char width is ~8px
    char_widths = {
        'i': 4, 'l': 4, 't': 5, 'f': 5, 'r': 5, '1': 6,
        'a': 7, 'c': 7, 'e': 7, 'n': 7, 'o': 7, 's': 7, 'u': 7, 'v': 7, 'x': 7, 'z': 7,
        'b': 8, 'd': 8, 'g': 8, 'h': 8, 'k': 8, 'p': 8, 'q': 8, 'y': 8,
        'A': 9, 'B': 9, 'C': 9, 'D': 9, 'E': 8, 'F': 8, 'G': 9, 'H': 9, 'I': 4,
        'J': 7, 'K': 9, 'L': 7, 'M': 11, 'N': 9, 'O': 10, 'P': 8, 'Q': 10, 'R': 9,
        'S': 8, 'T': 8, 'U': 9, 'V': 9, 'W': 12, 'X': 9, 'Y': 9, 'Z': 8,
        'm': 11, 'w': 11, 'M': 11, 'W': 12,
        ' ': 4, '.': 4, ',': 4, ':': 4, ';': 4, '!': 4, '?': 7,
        '-': 5, '_': 7, '(': 5, ')': 5, '[': 5, ']': 5
    }
    
    total_width = 0
    for char in text:
        total_width += char_widths.get(char, 7)  # Default to 7px
    
    return total_width


def extract_meta_tags(soup: BeautifulSoup) -> MetaTagProfile:
    """Extract comprehensive meta tag information."""
    profile = MetaTagProfile()
    
    # Basic meta tags
    title_tag = soup.find('title')
    if title_tag:
        profile.title = title_tag.text.strip()
    
    # Standard meta tags
    meta_mappings = {
        'description': 'description',
        'keywords': 'keywords',
        'author': 'author',
        'robots': 'robots',
        'googlebot': 'googlebot',
        'viewport': 'viewport'
    }
    
    for name, attr in meta_mappings.items():
        tag = soup.find('meta', attrs={'name': name})
        if tag and tag.get('content'):
            setattr(profile, attr, tag.get('content').strip())
    
    # Charset
    charset_tag = soup.find('meta', charset=True)
    if charset_tag:
        profile.charset = charset_tag.get('charset')
    else:
        charset_tag = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        if charset_tag:
            content = charset_tag.get('content', '')
            if 'charset=' in content:
                profile.charset = content.split('charset=')[-1].strip()
    
    # Canonical URL
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    if canonical:
        profile.canonical = canonical.get('href')
    
    # Alternate languages (hreflang)
    for link in soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True}):
        lang = link.get('hreflang')
        href = link.get('href')
        if lang and href:
            profile.alternate_languages[lang] = href
    
    # Open Graph tags
    for tag in soup.find_all('meta', property=re.compile('^og:')):
        prop = tag.get('property')
        content = tag.get('content')
        if prop and content:
            profile.og_tags[prop] = content
    
    # Twitter Card tags
    for tag in soup.find_all('meta', attrs={'name': re.compile('^twitter:')}):
        name = tag.get('name')
        content = tag.get('content')
        if name and content:
            profile.twitter_tags[name] = content
    
    # Article meta tags
    for tag in soup.find_all('meta', property=re.compile('^article:')):
        prop = tag.get('property')
        content = tag.get('content')
        if prop and content:
            profile.article_tags[prop] = content
    
    # Dublin Core metadata
    for tag in soup.find_all('meta', attrs={'name': re.compile(r'^dc\.')}):
        name = tag.get('name')
        content = tag.get('content')
        if name and content:
            profile.dublin_core[name] = content
    
    # Custom meta tags
    for tag in soup.find_all('meta'):
        name = tag.get('name', '')
        property = tag.get('property', '')
        content = tag.get('content', '')
        
        # Skip already processed tags
        if (name and not any(name.startswith(p) for p in ['description', 'keywords', 'author', 'robots', 'viewport', 'twitter', 'dc.']) 
            and content):
            profile.custom_meta[name] = content
        elif (property and not property.startswith(('og:', 'article:')) and content):
            profile.custom_meta[property] = content
    
    return profile


def validate_structured_data(data: Dict[str, Any]) -> StructuredDataItem:
    """Validate structured data against Schema.org requirements."""
    item = StructuredDataItem(
        type=data.get('@type', 'Unknown'),
        properties=data
    )
    
    # Basic validation
    if '@context' not in data:
        item.validation_errors.append("Missing @context")
        item.is_valid = False
    
    if '@type' not in data:
        item.validation_errors.append("Missing @type")
        item.is_valid = False
    
    # Type-specific validation
    schema_type = data.get('@type', '')
    
    # Product validation
    if schema_type == 'Product':
        required = ['name', 'image']
        recommended = ['description', 'sku', 'offers', 'aggregateRating', 'review']
        
        for field in required:
            if field not in data:
                item.validation_errors.append(f"Product missing required field: {field}")
                item.is_valid = False
        
        if 'offers' in data:
            offer = data['offers'] if isinstance(data['offers'], dict) else data['offers'][0]
            offer_required = ['priceCurrency', 'price']
            for field in offer_required:
                if field not in offer:
                    item.validation_errors.append(f"Product offer missing: {field}")
        
        if 'aggregateRating' in data or 'review' in data:
            item.rich_snippet_eligible = True
            item.snippet_type = RichSnippetType.PRODUCT
    
    # Article validation
    elif schema_type in ['Article', 'NewsArticle', 'BlogPosting']:
        required = ['headline', 'datePublished', 'author']
        recommended = ['image', 'dateModified', 'publisher']
        
        for field in required:
            if field not in data:
                item.validation_errors.append(f"Article missing required field: {field}")
                item.is_valid = False
        
        item.rich_snippet_eligible = True
        item.snippet_type = RichSnippetType.ARTICLE
    
    # Organization validation
    elif schema_type == 'Organization':
        required = ['name', 'url']
        recommended = ['logo', 'sameAs', 'contactPoint']
        
        for field in required:
            if field not in data:
                item.validation_errors.append(f"Organization missing required field: {field}")
                item.is_valid = False
    
    # LocalBusiness validation
    elif 'LocalBusiness' in schema_type:
        required = ['name', 'address']
        recommended = ['telephone', 'openingHours', 'geo', 'review']
        
        for field in required:
            if field not in data:
                item.validation_errors.append(f"LocalBusiness missing required field: {field}")
                item.is_valid = False
        
        if 'address' in data:
            address_required = ['streetAddress', 'addressLocality', 'addressRegion', 'postalCode']
            address = data['address'] if isinstance(data['address'], dict) else {}
            for field in address_required:
                if field not in address:
                    item.validation_errors.append(f"Address missing: {field}")
    
    # FAQ validation
    elif schema_type == 'FAQPage':
        if 'mainEntity' not in data:
            item.validation_errors.append("FAQPage missing mainEntity")
            item.is_valid = False
        else:
            item.rich_snippet_eligible = True
            item.snippet_type = RichSnippetType.FAQ
    
    # Recipe validation
    elif schema_type == 'Recipe':
        required = ['name', 'image', 'recipeIngredient', 'recipeInstructions']
        recommended = ['prepTime', 'cookTime', 'totalTime', 'recipeYield', 'nutrition', 'aggregateRating']
        
        for field in required:
            if field not in data:
                item.validation_errors.append(f"Recipe missing required field: {field}")
                item.is_valid = False
        
        if all(field in data for field in required):
            item.rich_snippet_eligible = True
            item.snippet_type = RichSnippetType.RECIPE
    
    # Event validation
    elif schema_type == 'Event':
        required = ['name', 'startDate', 'location']
        
        for field in required:
            if field not in data:
                item.validation_errors.append(f"Event missing required field: {field}")
                item.is_valid = False
        
        if all(field in data for field in required):
            item.rich_snippet_eligible = True
            item.snippet_type = RichSnippetType.EVENT
    
    # BreadcrumbList validation
    elif schema_type == 'BreadcrumbList':
        if 'itemListElement' not in data:
            item.validation_errors.append("BreadcrumbList missing itemListElement")
            item.is_valid = False
        else:
            item.rich_snippet_eligible = True
            item.snippet_type = RichSnippetType.BREADCRUMBS
    
    # VideoObject validation
    elif schema_type == 'VideoObject':
        required = ['name', 'description', 'thumbnailUrl', 'uploadDate']
        
        for field in required:
            if field not in data:
                item.validation_errors.append(f"VideoObject missing required field: {field}")
                item.is_valid = False
        
        if all(field in data for field in required):
            item.rich_snippet_eligible = True
            item.snippet_type = RichSnippetType.VIDEO
    
    return item


def analyze_heading_structure(soup: BeautifulSoup) -> Dict[str, Any]:
    """Analyze heading hierarchy and structure."""
    headings = {
        'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []
    }
    
    issues = []
    hierarchy_valid = True
    
    # Extract all headings
    for level in range(1, 7):
        tag_name = f'h{level}'
        for heading in soup.find_all(tag_name):
            text = heading.get_text(strip=True)
            if text:
                headings[tag_name].append({
                    'text': text,
                    'length': len(text),
                    'has_keywords': False  # Would need keyword list to check
                })
    
    # Check H1
    if len(headings['h1']) == 0:
        issues.append("No H1 tag found")
        hierarchy_valid = False
    elif len(headings['h1']) > 1:
        issues.append(f"Multiple H1 tags found ({len(headings['h1'])})")
        hierarchy_valid = False
    
    # Check hierarchy
    prev_level = 0
    for level in range(1, 7):
        tag_name = f'h{level}'
        if headings[tag_name]:
            if prev_level == 0:
                prev_level = level
            elif level > prev_level + 1:
                issues.append(f"Heading hierarchy broken: H{prev_level} followed by H{level}")
                hierarchy_valid = False
            prev_level = level
    
    # Calculate metrics
    total_headings = sum(len(h) for h in headings.values())
    avg_length = 0
    if total_headings > 0:
        all_lengths = [h['length'] for heading_list in headings.values() for h in heading_list]
        avg_length = sum(all_lengths) / len(all_lengths)
    
    return {
        'headings': headings,
        'total_count': total_headings,
        'hierarchy_valid': hierarchy_valid,
        'average_length': round(avg_length, 1),
        'issues': issues
    }


def analyze_internal_linking_seo(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Analyze internal linking from SEO perspective."""
    internal_links = []
    external_links = []
    
    # Parse base URL
    base_domain = urlparse(url).netloc
    
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Skip empty or anchor-only links
        if not href or href.startswith('#'):
            continue
        
        # Determine if internal
        is_internal = True
        if href.startswith(('http://', 'https://')):
            link_domain = urlparse(href).netloc
            is_internal = link_domain == base_domain or link_domain.endswith('.' + base_domain)
        
        link_data = {
            'url': href,
            'anchor_text': text,
            'is_follow': 'nofollow' not in (link.get('rel', []) if isinstance(link.get('rel'), list) else [link.get('rel', '')])
        }
        
        if is_internal:
            internal_links.append(link_data)
        else:
            external_links.append(link_data)
    
    # Analyze anchor text diversity
    internal_anchors = [l['anchor_text'].lower() for l in internal_links if l['anchor_text']]
    anchor_diversity = len(set(internal_anchors)) / max(1, len(internal_anchors))
    
    return {
        'internal_count': len(internal_links),
        'external_count': len(external_links),
        'follow_ratio': sum(1 for l in external_links if l['is_follow']) / max(1, len(external_links)),
        'anchor_diversity': round(anchor_diversity, 2),
        'top_anchors': Counter(internal_anchors).most_common(5)
    }


def generate_serp_preview(meta_profile: MetaTagProfile, url: str) -> SERPPreview:
    """Generate a SERP preview with pixel calculations."""
    # Use meta title or fallback
    title = meta_profile.title or 'Untitled Page'
    
    # Truncate title if too long (600px limit on desktop)
    title_pixels = calculate_text_pixel_width(title)
    if title_pixels > 600:
        # Truncate and add ellipsis
        while title_pixels > 580 and len(title) > 10:
            title = title[:-1]
            title_pixels = calculate_text_pixel_width(title + '...')
        title += '...'
    
    # Use meta description or generate
    description = meta_profile.description or ''
    
    # Truncate description if too long (920px limit on desktop)
    desc_pixels = calculate_text_pixel_width(description)
    if desc_pixels > 920:
        while desc_pixels > 900 and len(description) > 10:
            description = description[:-1]
            desc_pixels = calculate_text_pixel_width(description + '...')
        description += '...'
    
    # Format URL for display
    parsed_url = urlparse(url)
    display_url = parsed_url.netloc + parsed_url.path
    if display_url.endswith('/'):
        display_url = display_url[:-1]
    
    # Create breadcrumbs from URL path
    path_parts = parsed_url.path.strip('/').split('/')
    if path_parts and path_parts[0]:
        breadcrumbs = ' › '.join([parsed_url.netloc] + path_parts)
    else:
        breadcrumbs = parsed_url.netloc
    
    preview = SERPPreview(
        title=title,
        url=display_url,
        description=description,
        title_pixels=title_pixels,
        description_pixels=desc_pixels,
        breadcrumbs=breadcrumbs
    )
    
    # Check sitelinks eligibility (simplified)
    if meta_profile.og_tags and 'og:site_name' in meta_profile.og_tags:
        preview.sitelinks_eligible = True
    
    return preview


def detect_seo_opportunities(soup: BeautifulSoup, meta_profile: MetaTagProfile, structured_data: List[StructuredDataItem]) -> List[Dict[str, Any]]:
    """Detect SEO optimization opportunities."""
    opportunities = []
    
    # Rich snippet opportunities
    rich_snippet_types = [item.snippet_type for item in structured_data if item.rich_snippet_eligible]
    
    potential_snippets = {
        RichSnippetType.FAQ: "FAQ rich snippets can increase CTR by 50%+",
        RichSnippetType.HOW_TO: "How-To rich snippets provide step-by-step visibility",
        RichSnippetType.RECIPE: "Recipe cards get prominent SERP placement",
        RichSnippetType.PRODUCT: "Product rich snippets show price and ratings",
        RichSnippetType.REVIEW: "Review stars increase CTR significantly",
        RichSnippetType.VIDEO: "Video thumbnails attract more clicks"
    }
    
    for snippet_type, benefit in potential_snippets.items():
        if snippet_type not in rich_snippet_types:
            # Check if content suggests this type could be implemented
            content = soup.get_text().lower()
            
            if snippet_type == RichSnippetType.FAQ and ('frequently asked' in content or 'faq' in content):
                opportunities.append({
                    'type': 'rich_snippet',
                    'opportunity': f"Add FAQ structured data",
                    'benefit': benefit,
                    'priority': 'high'
                })
            elif snippet_type == RichSnippetType.HOW_TO and ('how to' in content or 'step' in content):
                opportunities.append({
                    'type': 'rich_snippet',
                    'opportunity': f"Add How-To structured data",
                    'benefit': benefit,
                    'priority': 'medium'
                })
            elif snippet_type == RichSnippetType.PRODUCT and ('price' in content or '$' in content):
                opportunities.append({
                    'type': 'rich_snippet',
                    'opportunity': f"Add Product structured data",
                    'benefit': benefit,
                    'priority': 'high'
                })
    
    # Featured snippet opportunities
    # Check for definition-style content
    if soup.find(string=re.compile(r'(what is|definition of|meaning of)', re.I)):
        opportunities.append({
            'type': 'featured_snippet',
            'opportunity': "Optimize for definition featured snippet",
            'benefit': "Position 0 placement above organic results",
            'priority': 'high'
        })
    
    # Check for list content
    if len(soup.find_all(['ul', 'ol'])) > 2:
        opportunities.append({
            'type': 'featured_snippet',
            'opportunity': "Optimize for list featured snippet",
            'benefit': "Prominent list display in search results",
            'priority': 'medium'
        })
    
    # Check for table content
    if soup.find('table'):
        opportunities.append({
            'type': 'featured_snippet',
            'opportunity': "Optimize for table featured snippet",
            'benefit': "Table display directly in SERP",
            'priority': 'medium'
        })
    
    # International SEO opportunities
    if not meta_profile.alternate_languages:
        opportunities.append({
            'type': 'international',
            'opportunity': "Add hreflang tags for international targeting",
            'benefit': "Serve correct language version to users",
            'priority': 'high' if 'lang' not in str(soup.find('html')) else 'low'
        })
    
    # E-commerce opportunities
    if 'add to cart' in soup.get_text().lower() or 'buy now' in soup.get_text().lower():
        if not any(item.type == 'Product' for item in structured_data):
            opportunities.append({
                'type': 'ecommerce',
                'opportunity': "Add Product schema for e-commerce pages",
                'benefit': "Show price, availability, and ratings in SERP",
                'priority': 'critical'
            })
    
    # Local SEO opportunities
    if any(word in soup.get_text().lower() for word in ['address', 'location', 'hours', 'directions']):
        if not any('LocalBusiness' in item.type for item in structured_data):
            opportunities.append({
                'type': 'local',
                'opportunity': "Add LocalBusiness schema",
                'benefit': "Appear in local pack and maps",
                'priority': 'high'
            })
    
    return opportunities


def calculate_seo_scores(issues: List[Dict], data: Dict[str, Any]) -> SEOScore:
    """Calculate detailed SEO scores by category."""
    scores = SEOScore()
    
    # Calculate individual category scores
    for issue in issues:
        penalty = 0
        if issue['severity'] == 'critical':
            penalty = 20
        elif issue['severity'] == 'warning':
            penalty = 10
        elif issue['severity'] == 'notice':
            penalty = 5
        
        # Categorize and apply penalties
        if 'meta' in issue['category'].lower() or 'title' in issue['message'].lower() or 'description' in issue['message'].lower():
            scores.meta_tags -= penalty
        elif 'structured' in issue['message'].lower() or 'schema' in issue['message'].lower():
            scores.structured_data -= penalty
        elif 'mobile' in issue['message'].lower() or 'viewport' in issue['message'].lower():
            scores.mobile -= penalty
        elif 'social' in issue['message'].lower() or 'open graph' in issue['message'].lower() or 'twitter' in issue['message'].lower():
            scores.social -= penalty
        elif 'heading' in issue['message'].lower() or 'h1' in issue['message'].lower():
            scores.content -= penalty
        elif 'lang' in issue['message'].lower() or 'hreflang' in issue['message'].lower():
            scores.international -= penalty
        elif 'alt' in issue['message'].lower():
            scores.accessibility -= penalty
        elif 'https' in issue['message'].lower() or 'security' in issue['message'].lower():
            scores.security -= penalty
        else:
            scores.technical -= penalty
    
    # Ensure scores don't go negative
    for attr in ['technical', 'content', 'meta_tags', 'structured_data', 'social', 'mobile', 'international', 'accessibility', 'security']:
        value = getattr(scores, attr)
        setattr(scores, attr, max(0, min(100, value)))
    
    # Calculate weighted total
    weights = {
        'meta_tags': 0.20,
        'content': 0.20,
        'structured_data': 0.15,
        'technical': 0.15,
        'mobile': 0.10,
        'social': 0.05,
        'accessibility': 0.05,
        'international': 0.05,
        'security': 0.05
    }
    
    scores.total = sum(getattr(scores, category) * weight for category, weight in weights.items())
    scores.total = round(scores.total)
    
    return scores


def analyze_seo(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Advanced SEO analysis with comprehensive optimization detection."""
    issues = []
    data = {}
    
    # Extract meta tags comprehensively
    meta_profile = extract_meta_tags(soup)
    
    # Analyze meta title
    if not meta_profile.title:
        issues.append(create_issue('Meta Tags', 'critical', 'Missing page title'))
    else:
        title_length = len(meta_profile.title)
        title_pixels = calculate_text_pixel_width(meta_profile.title)
        
        data['title'] = {
            'text': meta_profile.title,
            'length': title_length,
            'pixels': title_pixels
        }
        
        if title_length < 30:
            issues.append(create_issue('Meta Tags', 'warning', 
                f'Title too short ({title_length} chars, recommended 30-60)'))
        elif title_length > 60:
            issues.append(create_issue('Meta Tags', 'warning',
                f'Title too long ({title_length} chars, recommended 30-60)'))
        
        if title_pixels > 600:
            issues.append(create_issue('Meta Tags', 'warning',
                f'Title too wide ({title_pixels}px, max 600px on desktop)'))
        
        # Check for keyword stuffing
        words = meta_profile.title.lower().split()
        word_counts = Counter(words)
        if any(count > 2 for word, count in word_counts.items() if len(word) > 3):
            issues.append(create_issue('Meta Tags', 'warning', 'Possible keyword stuffing in title'))
    
    # Analyze meta description
    if not meta_profile.description:
        issues.append(create_issue('Meta Tags', 'critical', 'Missing meta description'))
    else:
        desc_length = len(meta_profile.description)
        desc_pixels = calculate_text_pixel_width(meta_profile.description)
        
        data['description'] = {
            'text': meta_profile.description,
            'length': desc_length,
            'pixels': desc_pixels
        }
        
        if desc_length < 120:
            issues.append(create_issue('Meta Tags', 'warning',
                f'Meta description too short ({desc_length} chars, recommended 120-160)'))
        elif desc_length > 160:
            issues.append(create_issue('Meta Tags', 'warning',
                f'Meta description too long ({desc_length} chars, recommended 120-160)'))
        
        if desc_pixels > 920:
            issues.append(create_issue('Meta Tags', 'warning',
                f'Description too wide ({desc_pixels}px, max 920px on desktop)'))
        
        # Check for call-to-action
        cta_words = ['learn', 'discover', 'find', 'get', 'shop', 'buy', 'read', 'download', 'sign up', 'try']
        if not any(word in meta_profile.description.lower() for word in cta_words):
            issues.append(create_issue('Meta Tags', 'notice',
                'Meta description lacks call-to-action'))
    
    # Check meta keywords
    if meta_profile.keywords:
        issues.append(create_issue('Meta Tags', 'notice',
            'Meta keywords tag is deprecated and ignored by search engines'))
    
    # Analyze canonical URL
    if not meta_profile.canonical:
        issues.append(create_issue('Technical SEO', 'warning', 'Missing canonical URL'))
    else:
        data['canonical'] = meta_profile.canonical
        # Check if canonical matches current URL (simplified check)
        if meta_profile.canonical != url and not url.endswith('/'):
            if meta_profile.canonical != url + '/':
                issues.append(create_issue('Technical SEO', 'notice',
                    'Canonical URL differs from current URL'))
    
    # Analyze robots directives
    if meta_profile.robots:
        data['robots'] = meta_profile.robots
        robots_lower = meta_profile.robots.lower()
        
        if 'noindex' in robots_lower:
            issues.append(create_issue('Technical SEO', 'critical',
                'Page is set to noindex (will not appear in search results)'))
        
        if 'nofollow' in robots_lower:
            issues.append(create_issue('Technical SEO', 'warning',
                'Page is set to nofollow (links will not pass PageRank)'))
        
        if 'nosnippet' in robots_lower:
            issues.append(create_issue('Technical SEO', 'warning',
                'Page is set to nosnippet (no text snippet in SERP)'))
        
        if 'noarchive' in robots_lower:
            issues.append(create_issue('Technical SEO', 'notice',
                'Page is set to noarchive (no cached version)'))
    
    # Analyze Open Graph tags
    og_required = ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']
    og_missing = [tag for tag in og_required if tag not in meta_profile.og_tags]
    
    if og_missing:
        issues.append(create_issue('Social SEO', 'warning',
            f'Missing Open Graph tags: {", ".join(og_missing)}'))
    
    if 'og:image' in meta_profile.og_tags:
        # Check for high-res image
        if 'og:image:width' not in meta_profile.og_tags or 'og:image:height' not in meta_profile.og_tags:
            issues.append(create_issue('Social SEO', 'notice',
                'Open Graph image missing dimensions'))
    
    data['open_graph'] = meta_profile.og_tags
    
    # Analyze Twitter Card tags
    if not meta_profile.twitter_tags:
        issues.append(create_issue('Social SEO', 'warning',
            'Missing Twitter Card tags for better social sharing'))
    else:
        twitter_type = meta_profile.twitter_tags.get('twitter:card', 'summary')
        
        if twitter_type == 'summary_large_image':
            required = ['twitter:title', 'twitter:description', 'twitter:image']
            twitter_missing = [tag for tag in required if tag not in meta_profile.twitter_tags]
            if twitter_missing:
                issues.append(create_issue('Social SEO', 'warning',
                    f'Missing Twitter Card tags: {", ".join(twitter_missing)}'))
    
    data['twitter_card'] = meta_profile.twitter_tags
    
    # Analyze structured data
    structured_data_items = []
    
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            json_data = json.loads(script.string)
            
            # Handle @graph arrays
            if '@graph' in json_data:
                for item in json_data['@graph']:
                    validated = validate_structured_data(item)
                    structured_data_items.append(validated)
            else:
                validated = validate_structured_data(json_data)
                structured_data_items.append(validated)
                
        except json.JSONDecodeError:
            issues.append(create_issue('Structured Data', 'critical',
                'Invalid JSON-LD structured data found'))
        except Exception as e:
            issues.append(create_issue('Structured Data', 'warning',
                f'Error parsing structured data: {str(e)}'))
    
    if not structured_data_items:
        issues.append(create_issue('Structured Data', 'warning',
            'No structured data (JSON-LD) found'))
    else:
        # Report validation errors
        for item in structured_data_items:
            if not item.is_valid:
                for error in item.validation_errors[:3]:  # Limit to 3 errors per item
                    issues.append(create_issue('Structured Data', 'warning',
                        f'{item.type}: {error}'))
        
        # Check for rich snippet eligibility
        eligible_snippets = [item for item in structured_data_items if item.rich_snippet_eligible]
        if eligible_snippets:
            data['rich_snippets'] = [
                {'type': item.snippet_type.value, 'schema': item.type}
                for item in eligible_snippets
            ]
    
    data['structured_data'] = [
        {
            'type': item.type,
            'valid': item.is_valid,
            'rich_snippet_eligible': item.rich_snippet_eligible,
            'errors': item.validation_errors[:3]  # Limit errors in output
        }
        for item in structured_data_items
    ]
    
    # Analyze language and international SEO
    html_tag = soup.find('html')
    if html_tag:
        lang = html_tag.get('lang')
        if not lang:
            issues.append(create_issue('International SEO', 'warning',
                'Missing language declaration (lang attribute)'))
        else:
            data['language'] = lang
            
            # Check for proper language code format
            if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', lang):
                issues.append(create_issue('International SEO', 'notice',
                    f'Non-standard language code format: {lang}'))
    
    # Check hreflang tags
    if meta_profile.alternate_languages:
        data['hreflang'] = meta_profile.alternate_languages
        
        # Check for x-default
        if 'x-default' not in meta_profile.alternate_languages:
            issues.append(create_issue('International SEO', 'notice',
                'Missing x-default hreflang tag'))
    
    # Mobile SEO
    if not meta_profile.viewport:
        issues.append(create_issue('Mobile SEO', 'critical',
            'Missing viewport meta tag (not mobile-friendly)'))
    else:
        data['viewport'] = meta_profile.viewport
        
        # Check for proper viewport settings
        if 'width=device-width' not in meta_profile.viewport:
            issues.append(create_issue('Mobile SEO', 'warning',
                'Viewport not set to device-width'))
        
        if 'user-scalable=no' in meta_profile.viewport:
            issues.append(create_issue('Mobile SEO', 'warning',
                'Viewport prevents user scaling (accessibility issue)'))
    
    # Analyze heading structure
    heading_analysis = analyze_heading_structure(soup)
    data['heading_structure'] = heading_analysis
    
    for heading_issue in heading_analysis['issues']:
        severity = 'critical' if 'No H1' in heading_issue else 'warning'
        issues.append(create_issue('Content SEO', severity, heading_issue))
    
    # Analyze images for SEO
    images = soup.find_all('img')
    images_without_alt = []
    images_without_dimensions = []
    large_images = []
    
    for img in images:
        src = img.get('src', '')
        
        # Check alt text
        if not img.get('alt'):
            images_without_alt.append(src)
        
        # Check dimensions
        if not (img.get('width') and img.get('height')):
            images_without_dimensions.append(src)
        
        # Check for WebP/modern formats
        if src and not any(fmt in src.lower() for fmt in ['.webp', '.avif']):
            large_images.append(src)
    
    if images_without_alt:
        issues.append(create_issue('Accessibility SEO', 'warning',
            f'{len(images_without_alt)} images missing alt text'))
    
    if images_without_dimensions:
        issues.append(create_issue('Technical SEO', 'warning',
            f'{len(images_without_dimensions)} images missing dimensions (causes CLS)'))
    
    data['images'] = {
        'total': len(images),
        'missing_alt': len(images_without_alt),
        'missing_dimensions': len(images_without_dimensions),
        'non_optimized': len(large_images)
    }
    
    # Internal linking analysis
    internal_linking = analyze_internal_linking_seo(soup, url)
    data['internal_linking'] = internal_linking
    
    if internal_linking['internal_count'] < 3:
        issues.append(create_issue('Content SEO', 'warning',
            'Too few internal links (less than 3)'))
    
    if internal_linking['anchor_diversity'] < 0.5:
        issues.append(create_issue('Content SEO', 'notice',
            'Low internal anchor text diversity'))
    
    # Generate SERP preview
    serp_preview = generate_serp_preview(meta_profile, url)
    data['serp_preview'] = {
        'title': serp_preview.title,
        'description': serp_preview.description,
        'url': serp_preview.url,
        'breadcrumbs': serp_preview.breadcrumbs,
        'title_pixels': serp_preview.title_pixels,
        'description_pixels': serp_preview.description_pixels
    }
    
    # Detect SEO opportunities
    opportunities = detect_seo_opportunities(soup, meta_profile, structured_data_items)
    data['opportunities'] = opportunities
    
    # Check for common SEO issues
    # Check charset
    if not meta_profile.charset:
        issues.append(create_issue('Technical SEO', 'warning',
            'Missing charset declaration'))
    elif meta_profile.charset.lower() != 'utf-8':
        issues.append(create_issue('Technical SEO', 'notice',
            f'Non-UTF-8 charset: {meta_profile.charset}'))
    
    # Check for favicon
    if not soup.find('link', rel=re.compile('icon')):
        issues.append(create_issue('Technical SEO', 'notice',
            'Missing favicon'))
    
    # Check for sitemap link
    if not soup.find('link', rel='sitemap'):
        issues.append(create_issue('Technical SEO', 'notice',
            'No sitemap link in HTML'))
    
    # Check for RSS/Atom feeds
    if not soup.find('link', type=re.compile(r'application/(rss|atom)\+xml')):
        issues.append(create_issue('Technical SEO', 'notice',
            'No RSS/Atom feed detected'))
    
    # Calculate comprehensive SEO scores
    seo_scores = calculate_seo_scores(issues, data)
    
    data['scores'] = {
        'total': seo_scores.total,
        'technical': seo_scores.technical,
        'content': seo_scores.content,
        'meta_tags': seo_scores.meta_tags,
        'structured_data': seo_scores.structured_data,
        'social': seo_scores.social,
        'mobile': seo_scores.mobile,
        'international': seo_scores.international,
        'accessibility': seo_scores.accessibility,
        'security': seo_scores.security
    }
    
    # Generate recommendations based on scores
    recommendations = []
    
    if seo_scores.meta_tags < 70:
        recommendations.append("Priority: Optimize meta tags (title, description) for better SERP visibility")
    
    if seo_scores.structured_data < 70:
        recommendations.append("Priority: Implement structured data for rich snippets")
    
    if seo_scores.mobile < 70:
        recommendations.append("Priority: Fix mobile SEO issues for mobile-first indexing")
    
    if seo_scores.content < 70:
        recommendations.append("Priority: Improve content structure and heading hierarchy")
    
    if opportunities:
        high_priority = [o for o in opportunities if o.get('priority') in ['critical', 'high']]
        if high_priority:
            recommendations.append(f"Opportunity: {high_priority[0]['opportunity']}")
    
    data['recommendations'] = recommendations
    
    # Store meta profile data
    data['meta_profile'] = {
        'title': meta_profile.title,
        'description': meta_profile.description,
        'canonical': meta_profile.canonical,
        'robots': meta_profile.robots,
        'charset': meta_profile.charset,
        'og_tags': dict(list(meta_profile.og_tags.items())[:10]),  # Limit output
        'twitter_tags': meta_profile.twitter_tags,
        'hreflang_count': len(meta_profile.alternate_languages)
    }
    
    return {
        'score': seo_scores.total,
        'issues': issues,
        'data': data
    }