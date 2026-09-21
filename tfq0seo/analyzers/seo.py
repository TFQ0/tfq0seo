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
from .common import classify_url, document_base_url, header_values, heading_facts, make_issue, parse_robots, resolve_url
from ..page_facts import PageFacts, ensure_page_facts
from ..rules import RuleDefinition, RuleCollector, register_rules, score_findings, recommendations_for


_SEARCH_DOCS = 'https://developers.google.com/search/docs/'
_TITLE_REFERENCE = _SEARCH_DOCS + 'appearance/title-link'
_SNIPPET_REFERENCE = _SEARCH_DOCS + 'appearance/snippet'
_CANONICAL_REFERENCE = _SEARCH_DOCS + 'crawling-indexing/consolidate-duplicate-urls'
_JSONLD_REFERENCE = 'https://www.w3.org/TR/json-ld11/'
_ENCODING_REFERENCE = 'https://html.spec.whatwg.org/multipage/semantics.html#charset'
_REVIEWED_ON = '2026-09-14'

# References were reviewed on the recorded date. These are bounded HTML checks,
# not a prediction of rankings, search appearance, or complete standards conformance.
SEO_RULES = (
    RuleDefinition('seo.title_missing', 'seo', 'warning',
        'Provide a descriptive title that identifies the subject of this page.',
        'HTML documents intended to have a descriptive page title.',
        (_TITLE_REFERENCE,), _REVIEWED_ON),
    RuleDefinition('seo.title_repetition', 'seo', 'notice',
        'Review repeated title words in context; keep necessary names and natural phrasing.',
        'A whitespace-delimited title repeats a word; repetition alone does not establish keyword stuffing.',
        (_TITLE_REFERENCE,), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.description_missing', 'seo', 'notice',
        'For pages you want to promote in search, consider a relevant summary in the meta description; snippets may use page content.',
        'A meta description is optional; its usefulness depends on the page and search intent.',
        (_SNIPPET_REFERENCE,), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.meta_keywords', 'seo', 'notice',
        'Do not rely on meta keywords for Google Search; keep them only if another consumer needs them.',
        'An observed meta keywords tag; other consumers are not assessed.',
        (_SEARCH_DOCS + 'crawling-indexing/special-tags',), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.canonical_preference', 'seo', 'notice',
        'If duplicate or similar URLs exist, choose a consistent canonical preference using supported signals.',
        'A canonical preference is optional and requires knowledge of duplicate or similar pages.',
        (_CANONICAL_REFERENCE,), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.canonical_invalid', 'seo', 'warning',
        'Correct the declared canonical href so it resolves to the intended HTTP or HTTPS URL.',
        'An HTML canonical link is declared; HTTP Link headers and destination content are assessed separately.',
        (_CANONICAL_REFERENCE,), _REVIEWED_ON),
    RuleDefinition('seo.og_incomplete', 'seo', 'notice',
        'Complete the Open Graph object with og:title, og:type, og:image, and og:url when Open Graph sharing is intended.',
        'The page already declares at least one Open Graph property.',
        ('https://ogp.me/',), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.og_image_dimensions', 'seo', 'notice',
        'Consider describing the Open Graph image dimensions for consumers that use them; these properties are optional.',
        'An Open Graph image is declared; its dimensions have not been fetched.',
        ('https://ogp.me/',), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.jsonld_syntax', 'seo', 'warning',
        'Correct the recorded JSON syntax error in the JSON-LD script.',
        'Scripts explicitly declared as application/ld+json; only JSON syntax is checked here.',
        (_JSONLD_REFERENCE,), _REVIEWED_ON),
    RuleDefinition('seo.jsonld_shape', 'seo', 'warning',
        'Correct the recorded JSON-LD node, graph, or @type shape and validate with a JSON-LD processor.',
        'Locally inspected JSON-LD structures; remote contexts, keyword aliases, and vocabulary rules are not expanded.',
        (_JSONLD_REFERENCE,), _REVIEWED_ON),
    RuleDefinition('seo.jsonld_empty', 'seo', 'notice',
        'Review the empty JSON-LD script if it was intended to describe an entity.',
        'A valid JSON-LD script contains no locally extractable nodes; empty graphs are not syntax failures.',
        (_JSONLD_REFERENCE,), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.jsonld_eligibility', 'seo', 'notice',
        'Check the relevant search feature documentation and validation tools if enhanced search appearance is intended.',
        'Search feature eligibility needs page purpose, content, vocabulary-specific requirements, and search-engine validation.',
        (_SEARCH_DOCS + 'appearance/structured-data/sd-policies',), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.language_format', 'seo', 'notice',
        'Use a BCP 47 language tag for the document language; validate the complete tag against the language subtag registry.',
        'A nonempty lang attribute; this check catches only obviously malformed separators and characters.',
        ('https://www.w3.org/International/articles/language-tags/',), _REVIEWED_ON),
    RuleDefinition('seo.viewport_width', 'seo', 'notice',
        'Review the viewport configuration and test the actual layout on narrow screens.',
        'A viewport declaration is present; absence of device-width alone does not prove an unusable layout.',
        ('https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport',), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.charset_missing', 'seo', 'notice',
        'Verify that the response or document declares its character encoding, accounting for any byte-order mark.',
        'Parsed HTML and optional response headers; original bytes and byte-order marks may be unavailable.',
        (_ENCODING_REFERENCE,), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.charset_non_utf8', 'seo', 'notice',
        'Use UTF-8 consistently in the document bytes and declaration when updating the encoding.',
        'An encoding is explicitly declared; the actual original byte encoding is not verified.',
        (_ENCODING_REFERENCE,), _REVIEWED_ON, scored=False),
    RuleDefinition('seo.favicon_missing', 'seo', 'notice',
        'If a Google Search favicon is desired, declare an appropriate icon on the site homepage and verify crawl access.',
        'Homepage HTML only; a default favicon or other platform-specific icon may still exist.',
        (_SEARCH_DOCS + 'appearance/favicon-in-search',), _REVIEWED_ON, scored=False),
)
register_rules(SEO_RULES)


class SEOPriority(Enum):
    """Legacy presentation priorities; these do not predict ranking impact."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


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
    rich_snippet_eligible: Optional[bool] = None
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
    sitelinks_eligible: Optional[bool] = None


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None,
                 rule_id: Optional[str] = None, evidence: Any = None,
                 confidence: str = 'high') -> Dict[str, Any]:
    """Compatibility wrapper; findings require an explicit registered rule."""
    if not rule_id or evidence is None:
        raise ValueError('SEO findings require a registered rule_id and observed evidence')
    return make_issue(category, severity, message, details, rule_id, evidence,
                      confidence=confidence)


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


def extract_meta_tags(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> MetaTagProfile:
    """Build the legacy metadata profile from shared declaration records."""
    profile = MetaTagProfile()
    title_tag = soup.find('title') if facts is None else None
    profile.title = facts.title if facts is not None else title_tag.get_text().strip() if title_tag else None
    metas = facts.meta if facts is not None else [{'attrs': tag.attrs} for tag in soup.find_all('meta')]
    links = facts.link_tags if facts is not None else [{'attrs': tag.attrs} for tag in soup.find_all('link')]
    mappings = {'description': 'description', 'keywords': 'keywords', 'author': 'author',
                'robots': 'robots', 'googlebot': 'googlebot', 'viewport': 'viewport'}
    seen = set()
    for record in metas:
        attrs = record['attrs']
        name = str(attrs.get('name', ''))
        key = name.casefold()
        prop = str(attrs.get('property', ''))
        content = str(attrs.get('content') or '').strip()
        if key in mappings and key not in seen:
            seen.add(key)
            if content:
                setattr(profile, mappings[key], content)
        if 'charset' in attrs and profile.charset is None:
            profile.charset = attrs['charset']
        if content:
            if prop.startswith('og:'):
                profile.og_tags[prop] = content
            elif prop.startswith('article:'):
                profile.article_tags[prop] = content
            elif prop:
                profile.custom_meta[prop] = content
            if name.startswith('twitter:'):
                profile.twitter_tags[name] = content
            elif name.startswith('dc.'):
                profile.dublin_core[name] = content
            elif name and not any(name.startswith(prefix) for prefix in
                                  ('description', 'keywords', 'author', 'robots', 'viewport', 'twitter', 'dc.')):
                profile.custom_meta[name] = content
    if profile.charset is None:
        for record in metas:
            attrs = record['attrs']
            if str(attrs.get('http-equiv', '')).casefold() == 'content-type':
                match = re.search(r"charset\s*=\s*[\"']?([^;\s\"']+)", str(attrs.get('content', '')), re.I)
                if match:
                    profile.charset = match.group(1)
                    break
    canonical_seen = False
    for record in links:
        attrs = record['attrs']
        rel = attrs.get('rel', [])
        rel = rel if isinstance(rel, list) else str(rel).split()
        if 'canonical' in rel and not canonical_seen:
            profile.canonical = attrs.get('href')
            canonical_seen = True
        if 'alternate' in rel and attrs.get('hreflang') and attrs.get('href'):
            profile.alternate_languages[attrs['hreflang']] = attrs['href']
    return profile


def validate_structured_data(data: Dict[str, Any]) -> StructuredDataItem:
    """Check the local @type shape without inventing required schema properties.

    A context or type need not occur on every node. Context expansion, vocabulary
    validation, and search feature requirements require a separate validator.
    """
    raw_type = data.get('@type')
    types = raw_type if isinstance(raw_type, list) else [raw_type]
    schema_types = [value for value in types if isinstance(value, str)]
    item = StructuredDataItem(type=schema_types[0] if schema_types else 'Unknown', properties=data)
    if '@type' in data and (not isinstance(raw_type, (str, list))
                           or any(not isinstance(value, str) for value in types)):
        item.validation_errors.append('@type must be a string or an array of strings')
        item.is_valid = False
    return item


def iter_structured_data(data: Any, context: Any = None):
    """Yield nodes from top-level arrays/graphs, retaining inherited context."""
    if isinstance(data, list):
        for node in data:
            yield from iter_structured_data(node, context)
    elif isinstance(data, dict):
        local_context = data.get('@context', context)
        if '@type' in data or '@graph' not in data:
            node = dict(data)
            if '@context' not in node and local_context is not None:
                node['@context'] = local_context
            yield node
        if '@graph' in data:
            graph = data['@graph']
            if not isinstance(graph, (dict, list)):
                raise ValueError('@graph must contain a node object or array')
            yield from iter_structured_data(graph, local_context)
    else:
        raise ValueError('JSON-LD must contain node objects or arrays')


def analyze_heading_structure(soup: BeautifulSoup, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Return shared heading facts in document order."""
    return facts.headings if facts is not None else heading_facts(soup)


def analyze_internal_linking_seo(soup: BeautifulSoup, url: str, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Describe link counts using the shared URL classification and anchor records."""
    page_facts = ensure_page_facts(soup, url, facts=facts)
    internal_links, external_links = [], []
    for record in page_facts.anchors:
        kind = record['url_kind']
        if kind not in ('internal', 'external'):
            continue
        rel = record['attrs'].get('rel', [])
        rel = rel if isinstance(rel, list) else str(rel).split()
        link_data = {'url': record['url'], 'anchor_text': record['text_compact'],
                     'is_follow': 'nofollow' not in [str(value).casefold() for value in rel]}
        (internal_links if kind == 'internal' else external_links).append(link_data)
    anchors = [link['anchor_text'].lower() for link in internal_links if link['anchor_text']]
    return {'internal_count': len(internal_links), 'external_count': len(external_links),
            'follow_ratio': sum(link['is_follow'] for link in external_links) / max(1, len(external_links)),
            'anchor_diversity': round(len(set(anchors)) / max(1, len(anchors)), 2),
            'top_anchors': [list(item) for item in Counter(anchors).most_common(5)]}


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
    
    return preview


def detect_seo_opportunities(soup: BeautifulSoup, meta_profile: MetaTagProfile, structured_data: List[StructuredDataItem]) -> List[Dict[str, Any]]:
    """Return no content-type guesses from language-dependent keyword matches."""
    return []


def calculate_seo_scores(issues: List[Dict], data: Dict[str, Any]) -> SEOScore:
    """Retain score dimensions while using the shared, deduplicated rule policy."""
    scores = SEOScore()
    dimensions = {'meta_tags': 'Meta Tags', 'structured_data': 'Structured Data',
                  'mobile': 'Mobile SEO', 'social': 'Social SEO', 'content': 'Content SEO',
                  'international': 'International SEO', 'accessibility': 'Accessibility SEO',
                  'security': 'Security', 'technical': 'Technical SEO'}
    for dimension, category in dimensions.items():
        setattr(scores, dimension, score_findings([issue for issue in issues if issue.get('category') == category]))
    scores.total = score_findings(issues)
    return scores


def analyze_seo(soup: BeautifulSoup, url: str, headers: Any = None,
                user_agent: Optional[str] = None, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Evaluate explicit SEO rules over observed HTML and optional headers."""
    page_facts = ensure_page_facts(soup, url, headers, user_agent, facts)
    headers = page_facts.headers
    user_agent = page_facts.user_agent
    collector = RuleCollector('seo')
    data = {'score_scope': 'static_html_rules'}
    meta_profile = extract_meta_tags(soup, facts=page_facts)

    def check(rule_id, failed, evidence, message, category='Technical SEO', **kwargs):
        if kwargs.get('applicable') is False and not kwargs.get('reason'):
            kwargs['reason'] = 'The element required by this rule is not declared in the observed HTML.'
        return collector.check(rule_id, failed, evidence, message=message, category=category, **kwargs)

    check('seo.title_missing', not bool(meta_profile.title), {'title': meta_profile.title},
          'Missing page title', 'Meta Tags')
    words = Counter((meta_profile.title or '').casefold().split())
    repeated = {word: count for word, count in words.items() if count > 2 and len(word) > 3}
    check('seo.title_repetition', bool(repeated), {'repeated_words': repeated},
          'Review repeated words in the page title', 'Meta Tags', applicable=bool(meta_profile.title),
          reason='Whitespace repetition is an editorial hint, not a keyword-stuffing diagnosis.', confidence='low')
    for name, value in (('title', meta_profile.title), ('description', meta_profile.description)):
        if value:
            data[name] = {'text': value, 'length': len(value), 'pixels': calculate_text_pixel_width(value),
                          'pixel_source': 'approximate_character_widths', 'length_requirement': None}
    check('seo.description_missing', not bool(meta_profile.description), {'description': meta_profile.description},
          'No meta description is declared', 'Meta Tags',
          reason='Google may generate snippets from page content; this is an optional editorial improvement.')
    check('seo.meta_keywords', bool(meta_profile.keywords), {'keywords': meta_profile.keywords},
          'Meta keywords are not used by Google Search', 'Meta Tags')

    base_url = page_facts.base_url
    link_records = page_facts.link_tags
    canonical_declared = any('canonical' in record['attrs'].get('rel', []) for record in link_records)
    canonical_url = resolve_url(meta_profile.canonical, base_url) if canonical_declared else None
    if canonical_url and urlparse(canonical_url).scheme not in ('http', 'https'):
        canonical_url = None
    check('seo.canonical_preference', False if canonical_url else None,
          {'html_canonical': meta_profile.canonical, 'resolved_url': canonical_url},
          'Canonical preference needs duplicate-page context',
          reason='HTML observation only; a preference is optional and may also be expressed by other signals.')
    check('seo.canonical_invalid', canonical_url is None,
          {'href': meta_profile.canonical, 'base_url': base_url},
          'The declared canonical does not resolve to an HTTP or HTTPS URL', applicable=canonical_declared)
    if canonical_declared:
        data['canonical'] = canonical_url
        data['canonical_is_self_referencing'] = canonical_url == resolve_url(url, url)

    robots = page_facts.robots
    data['robots'] = ', '.join(robots['directives'])
    data['robots_analysis'] = robots
    for directive in ('noindex', 'nofollow', 'nosnippet'):
        observed = robots[directive]
        check('robots.' + directive, observed if observed or headers is not None else None,
              {'directives': robots['directives'], 'observations': robots['evidence'],
               'user_agent': user_agent, 'headers_checked': headers is not None},
              'Page is set to ' + directive, source='html_and_headers',
              reason='Review the directive against the intended publishing policy; absent headers leave coverage incomplete.')

    og_required = ('og:title', 'og:type', 'og:image', 'og:url')
    og_missing = [name for name in og_required if name not in meta_profile.og_tags]
    check('seo.og_incomplete', bool(og_missing), {'missing': og_missing, 'declared': meta_profile.og_tags},
          'Open Graph object is missing basic properties', 'Social SEO', applicable=bool(meta_profile.og_tags))
    missing_og_dimensions = [name for name in ('og:image:width', 'og:image:height') if name not in meta_profile.og_tags]
    check('seo.og_image_dimensions', bool(missing_og_dimensions), {'missing': missing_og_dimensions},
          'Open Graph image dimensions are not declared', 'Social SEO', applicable='og:image' in meta_profile.og_tags)
    data['open_graph'] = meta_profile.og_tags
    data['twitter_card'] = meta_profile.twitter_tags
    data['social_preview_status'] = 'not_measured'

    structured_data_items = []
    syntax_errors, shape_errors, empty_scripts = [], [], []
    scripts = [record for record in page_facts.scripts
               if str(record['attrs'].get('type', '')).casefold() == 'application/ld+json']
    parsed_scripts = 0

    def reject_constant(value):
        raise ValueError('Non-JSON numeric constant: ' + value)

    for index, script in enumerate(scripts):
        try:
            json_data = json.loads(script['text'], parse_constant=reject_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            syntax_errors.append({'script_index': index, 'error': str(exc),
                                  'line': getattr(exc, 'lineno', None), 'column': getattr(exc, 'colno', None)})
            continue
        parsed_scripts += 1
        try:
            nodes = list(iter_structured_data(json_data))
        except ValueError as exc:
            shape_errors.append({'script_index': index, 'error': str(exc)})
            continue
        if not nodes:
            empty_scripts.append(index)
        for node_index, node in enumerate(nodes):
            item = validate_structured_data(node)
            structured_data_items.append(item)
            if not item.is_valid:
                shape_errors.append({'script_index': index, 'node_index': node_index,
                                     'type': item.type, 'errors': item.validation_errors})
    check('seo.jsonld_syntax', bool(syntax_errors), {'scripts': len(scripts), 'errors': syntax_errors},
          'Invalid JSON syntax in declared JSON-LD', 'Structured Data', applicable=bool(scripts))
    check('seo.jsonld_shape', bool(shape_errors), {'parsed_scripts': parsed_scripts, 'errors': shape_errors},
          'Unsupported JSON-LD node or type shape', 'Structured Data', applicable=bool(parsed_scripts),
          reason='Only local node, graph and @type shapes are checked; this is not full JSON-LD validation.')
    check('seo.jsonld_empty', bool(empty_scripts), {'script_indices': empty_scripts},
          'JSON-LD scripts contain no locally extractable nodes', 'Structured Data', applicable=bool(parsed_scripts))
    check('seo.jsonld_eligibility', None,
          {'jsonld_script_count': len(scripts), 'types': [item.type for item in structured_data_items],
           'other_syntax_checked': False}, 'Structured-data search eligibility is not assessed', 'Structured Data',
          applicable=None, reason='Page purpose and feature-specific validation are unavailable; JSON-LD is optional.')
    data['structured_data'] = [
        {'type': item.type, 'valid': item.is_valid, 'rich_snippet_eligible': None,
         'eligibility_status': 'unknown', 'validation_scope': 'local_shape_checks', 'errors': item.validation_errors}
        for item in structured_data_items
    ]

    lang = page_facts.language
    check('language.missing', not bool(lang), {'lang': lang},
          'Missing document language declaration', 'International SEO')
    if lang:
        data['language'] = lang
    malformed_lang = bool(lang) and not bool(re.fullmatch(r'[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*', lang))
    check('seo.language_format', malformed_lang, {'lang': lang, 'registry_checked': False},
          'Document language has a malformed language-tag shape', 'International SEO', applicable=bool(lang),
          reason='This check does not validate registered subtags, tag ordering, or agreement with the text language.')
    if meta_profile.alternate_languages:
        data['hreflang'] = meta_profile.alternate_languages
    data['hreflang_status'] = 'site_validation_required' if meta_profile.alternate_languages else 'not_declared'

    viewport = meta_profile.viewport
    settings = {}
    for entry in re.split(r'[,;]', viewport or ''):
        key, separator, value = entry.partition('=')
        if separator:
            settings[key.strip().casefold()] = value.strip().casefold()
    check('mobile.viewport_missing', not bool(viewport), {'viewport': viewport},
          'Missing viewport meta tag', 'Mobile SEO')
    check('seo.viewport_width', settings.get('width') != 'device-width', {'viewport': viewport, 'settings': settings},
          'Review the viewport width on narrow screens', 'Mobile SEO', applicable=bool(viewport), confidence='low')
    zoom_disabled = settings.get('user-scalable') in ('no', '0')
    try:
        max_scale = float(settings.get('maximum-scale', 'nan'))
        zoom_disabled = zoom_disabled or 0 < max_scale < 2
    except ValueError:
        pass
    check('mobile.viewport_zoom_disabled', zoom_disabled, {'viewport': viewport, 'settings': settings},
          'Viewport requests restrictions on user zoom', 'Mobile SEO', applicable=bool(viewport),
          reason='Browser enforcement varies; verify that users can enlarge text without loss of functionality.')
    if viewport:
        data['viewport'] = viewport

    heading_analysis = analyze_heading_structure(soup, facts=page_facts)
    data['heading_structure'] = heading_analysis
    for rule_id in ('headings.missing_h1', 'headings.empty', 'headings.skipped_level'):
        findings = [finding for finding in heading_analysis['findings'] if finding['rule_id'] == rule_id]
        check(rule_id, bool(findings), {'findings': findings, 'headings': heading_analysis['headings']},
              '; '.join(finding['message'] for finding in findings) or 'Heading check passed', 'Content SEO')

    images = [record['attrs'] for record in page_facts.images]
    missing_alt = [img.get('src', '') for img in images if 'alt' not in img]
    missing_dimensions = [img.get('src', '') for img in images if not (img.get('width') and img.get('height'))]
    non_modern_references = [img.get('src', '') for img in images
                             if img.get('src') and not re.search(r'\.(?:webp|avif)(?:[?#]|$)', img['src'], re.I)]
    check('images.missing_alt', bool(missing_alt), {'urls': missing_alt, 'total_images': len(images)},
          f'{len(missing_alt)} images missing alt attributes', 'Accessibility SEO', applicable=bool(images))
    check('images.missing_dimensions', bool(missing_dimensions), {'urls': missing_dimensions},
          'Images lack HTML dimensions; verify that layout space is reserved in CSS',
          applicable=bool(images), confidence='low')
    data['images'] = {'total': len(images), 'missing_alt': len(missing_alt),
                      'missing_dimensions': len(missing_dimensions), 'non_optimized': None,
                      'non_modern_filename_references': len(non_modern_references),
                      'optimization_status': 'requires_resource_measurement'}
    data['internal_linking'] = analyze_internal_linking_seo(soup, url, facts=page_facts)

    preview = generate_serp_preview(meta_profile, url)
    data['serp_preview'] = {name: getattr(preview, name) for name in
                           ('title', 'description', 'url', 'breadcrumbs', 'title_pixels', 'description_pixels')}
    data['serp_preview'].update({'status': 'illustrative', 'source': 'approximate_character_widths',
                                 'search_appearance_verified': False})
    data['opportunities'] = detect_seo_opportunities(soup, meta_profile, structured_data_items)

    response_types = header_values(headers, 'Content-Type')
    header_charsets = []
    for content_type in response_types:
        match = re.search(r"charset\s*=\s*[\"']?([^;\s\"']+)", content_type, re.I)
        if match:
            header_charsets.append(match.group(1))
    charset = header_charsets[0] if header_charsets else meta_profile.charset
    encoding_evidence = {'html_charset': meta_profile.charset, 'header_charsets': header_charsets,
                         'headers_checked': headers is not None, 'original_bytes_checked': False}
    check('seo.charset_missing', False if charset else None, encoding_evidence,
          'Character encoding declaration needs verification', source='html_and_headers',
          reason='No declaration observed does not exclude a byte-order mark in the original response.')
    check('seo.charset_non_utf8', str(charset).casefold() not in ('utf-8', 'utf8'), encoding_evidence,
          'A non-UTF-8 encoding is declared', applicable=bool(charset), source='html_and_headers')
    icon_links = [record['attrs'] for record in link_records if 'icon' in record['attrs'].get('rel', [])]
    check('seo.favicon_missing', not bool(icon_links), {'icon_hrefs': [tag.get('href') for tag in icon_links]},
          'No explicit homepage favicon link is declared', applicable=urlparse(url).path in ('', '/'),
          reason='Default icon paths and image responses have not been requested.')

    issues = collector.issues
    seo_scores = calculate_seo_scores(issues, data)
    data['scores'] = {name: getattr(seo_scores, name) for name in
                      ('total', 'technical', 'content', 'meta_tags', 'structured_data', 'social',
                       'mobile', 'international', 'accessibility', 'security')}
    data['score_dimensions_scope'] = (
        'Non-additive diagnostic subsets of rules observed by the SEO analyzer. '
        'The page pipeline assigns each shared rule to one analyzer for aggregate scoring.'
    )
    recommendations = recommendations_for(issues)
    data['recommendations'] = recommendations
    data['meta_profile'] = {
        'title': meta_profile.title, 'description': meta_profile.description,
        'canonical': meta_profile.canonical, 'robots': meta_profile.robots, 'charset': meta_profile.charset,
        'og_tags': meta_profile.og_tags, 'twitter_tags': meta_profile.twitter_tags,
        'hreflang_count': len(meta_profile.alternate_languages),
    }
    return {'score': seo_scores.total, 'issues': issues, 'data': data, 'recommendations': recommendations,
            'rule_results': collector.results, 'rule_coverage': collector.coverage, 'coverage': collector.coverage}
