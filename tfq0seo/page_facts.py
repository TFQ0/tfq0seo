"""Reusable snapshots of observed HTML, independent of scoring and transport."""

import hashlib
import math
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional

from bs4 import BeautifulSoup, Doctype

FACTS_VERSION = '1.1'


def _freeze(value):
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError('PageFacts mappings require string keys')
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError('PageFacts observations must contain finite JSON primitives')


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _headers_snapshot(headers):
    if headers is None:
        return None
    if not isinstance(headers, Mapping):
        raise TypeError('PageFacts headers must be a mapping or None')
    result = {}
    for name in headers:
        if not isinstance(name, str):
            raise TypeError('PageFacts header names must be strings')
        values = headers.getall(name) if hasattr(headers, 'getall') else headers[name]
        values = values if isinstance(values, (list, tuple)) else [values]
        if any(not isinstance(value, str) for value in values):
            raise TypeError('PageFacts header values must be strings or lists of strings')
        key = name.lower()
        if hasattr(headers, 'getall'):
            result[key] = list(values)
        else:
            result.setdefault(key, []).extend(values)
    return result


def extract_content_text(soup: BeautifulSoup, preserve_structure: bool = False, *, html: Optional[str] = None) -> str:
    """Preserve the existing content extractor's exclusions without mutating input."""
    clean = BeautifulSoup(str(soup) if html is None else html, 'html.parser')
    for element in clean(['script', 'style', 'noscript', 'iframe', 'svg']):
        element.decompose()
    for element in clean.find_all(style=re.compile(r'(display\s*:\s*none|visibility\s*:\s*hidden)', re.I)):
        element.decompose()
    for element in clean.find_all(attrs={'hidden': True}):
        element.decompose()
    if preserve_structure:
        text = clean.get_text(separator='\n', strip=True)
    else:
        text = re.sub(r'\s+', ' ', clean.get_text(separator=' '))
    text = re.sub(r'[\r\n]+', '\n', text)
    return re.sub(r'[^\S\n]+', ' ', text).strip()


@dataclass(frozen=True)
class PageFacts:
    """A frozen snapshot; collection properties return independent JSON primitives.

    Construct snapshots with extract_page_facts. The source soup is never cached on or modified. Callers supplying this
    snapshot must keep that soup unchanged while specialized DOM checks run.
    """

    url: str
    base_url: str
    html: str
    text: str
    content_text: str
    language: Optional[str]
    is_xml: bool
    doctype: tuple
    dom_size: int
    user_agent: str
    _source_id: int = field(repr=False)
    _snapshot: Mapping[str, Any] = field(repr=False)
    version: str = field(default=FACTS_VERSION, init=False)

    def __post_init__(self):
        required = {'headers', 'robots', 'headings', 'meta', 'link_tags', 'images',
                    'scripts', 'anchors', 'tag_counts', 'paragraphs', 'title', 'canonical'}
        if not isinstance(self._snapshot, Mapping) or not required <= self._snapshot.keys():
            raise ValueError('PageFacts requires the complete snapshot produced by extract_page_facts')
        if any(not isinstance(value, str) for value in
               (self.url, self.base_url, self.html, self.text, self.content_text, self.user_agent)):
            raise TypeError('PageFacts URL, text, and user agent fields must be strings')
        if self.language is not None and not isinstance(self.language, str):
            raise TypeError('PageFacts language must be a string or None')
        if type(self.is_xml) is not bool or type(self.dom_size) is not int or self.dom_size < 0:
            raise TypeError('PageFacts requires a parser flag and a nonnegative DOM element count')
        if type(self._source_id) is not int or not isinstance(self.doctype, (list, tuple)) or any(
                not isinstance(value, str) for value in self.doctype):
            raise TypeError('PageFacts requires a source identity and string DOCTYPE observations')
        object.__setattr__(self, 'doctype', tuple(self.doctype))
        object.__setattr__(self, '_snapshot', _freeze(self._snapshot))

    def __deepcopy__(self, memo):
        return self

    @property
    def headers(self):
        return _thaw(self._snapshot['headers'])

    @property
    def robots(self):
        return _thaw(self._snapshot['robots'])

    @property
    def headings(self):
        return _thaw(self._snapshot['headings'])

    @property
    def meta(self):
        return _thaw(self._snapshot['meta'])

    @property
    def link_tags(self):
        return _thaw(self._snapshot['link_tags'])

    @property
    def canonical(self):
        return _thaw(self._snapshot['canonical'])

    @property
    def images(self):
        return _thaw(self._snapshot['images'])

    @property
    def scripts(self):
        return _thaw(self._snapshot['scripts'])

    @property
    def anchors(self):
        return _thaw(self._snapshot['anchors'])

    @property
    def tag_counts(self):
        return _thaw(self._snapshot['tag_counts'])

    @property
    def paragraphs(self):
        return tuple(self._snapshot['paragraphs'])

    @property
    def title(self):
        return self._snapshot['title']

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Export provenance and structured observations; omit bulk text by default."""
        result = {
            'facts_version': self.version, 'url': self.url, 'base_url': self.base_url,
            'source': 'parsed_html_and_optional_response_headers', 'is_xml': self.is_xml,
            'language': self.language, 'doctype': list(self.doctype), 'dom_size': self.dom_size,
            'user_agent': self.user_agent, 'headers_observed': self._snapshot['headers'] is not None,
            'text_sha256': hashlib.sha256(self.text.encode('utf-8')).hexdigest(),
            'text_length': len(self.text), 'content_text_length': len(self.content_text),
            'html_length': len(self.html), 'content_text_method': 'markup_exclusions_and_inline_hidden_attributes',
            **_thaw(self._snapshot),
        }
        result['header_names'] = list((result.pop('headers') or {}).keys())
        # Raw script bodies are intentionally excluded from the default report.
        for script in result['scripts']:
            script_text = script.pop('text')
            script['text_length'] = len(script_text)
            script['text_sha256'] = hashlib.sha256(script_text.encode('utf-8')).hexdigest()
        result['paragraph_count'] = len(result.pop('paragraphs'))
        if include_content:
            result.update(html=self.html, text=self.text, content_text=self.content_text,
                          scripts=self.scripts, paragraphs=list(self.paragraphs))
        return result


def _attrs(element):
    result = {}
    for name, value in element.attrs.items():
        if not isinstance(name, str):
            raise TypeError('HTML attribute names must be strings')
        if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
            result[name] = list(value)
        elif isinstance(value, str) or value is None:
            result[name] = value
        else:
            raise TypeError(f'Unsupported parsed HTML attribute value at {element.name}[{name}]')
    return result


def extract_page_facts(soup: BeautifulSoup, url: str, headers: Any = None,
                       user_agent: str = 'googlebot') -> PageFacts:
    """Extract shared observations once per page; retain declaration order and absence."""
    from .analyzers.common import canonical_facts, document_base_url, heading_facts, parse_robots
    from .urls import classify_url, resolve_url

    if not isinstance(soup, BeautifulSoup) or not isinstance(url, str) or not isinstance(user_agent, str):
        raise TypeError('Page facts require BeautifulSoup and a URL string')
    elements = soup.find_all(True)
    attributes = [_attrs(element) for element in elements]
    html = str(soup)
    base_url = document_base_url(soup, url)
    indexed_ids = {}
    for element in elements:
        if element.get('id') is not None:
            indexed_ids.setdefault(str(element['id']), element)
    label_text_cache, context_text_cache = {}, {}

    def label_text(identifier):
        if identifier not in label_text_cache:
            label_text_cache[identifier] = indexed_ids[identifier].get_text(' ', strip=True)
        return label_text_cache[identifier]

    snapshot = {'headers': _headers_snapshot(headers), 'meta': [], 'link_tags': [], 'images': [],
                'scripts': [], 'anchors': [], 'tag_counts': {}, 'paragraphs': [], 'title': None}
    language = None
    for index, (element, attrs) in enumerate(zip(elements, attributes)):
        tag = element.name
        snapshot['tag_counts'][tag] = snapshot['tag_counts'].get(tag, 0) + 1
        if tag == 'html' and snapshot['tag_counts'][tag] == 1:
            language = element.get('lang')
        if tag == 'title' and snapshot['title'] is None:
            snapshot['title'] = element.get_text().strip()
        if tag == 'p':
            snapshot['paragraphs'].append(element.get_text())
        if tag in ('meta', 'link', 'img', 'script'):
            record = {'attrs': attrs, 'index': index}
            if tag in ('meta', 'link', 'script'):
                record['text'] = element.get_text()
            if tag in ('script', 'link'):
                record['in_head'] = element.find_parent('head') is not None
            snapshot[{'meta': 'meta', 'link': 'link_tags', 'img': 'images', 'script': 'scripts'}[tag]].append(record)
        if tag == 'a' and element.has_attr('href'):
            text = element.get_text(' ', strip=True)
            compact = element.get_text(strip=True)
            labelled = ' '.join(label_text(identifier)
                                for identifier in str(element.get('aria-labelledby', '')).split()
                                if identifier in indexed_ids).strip()
            parents = list(element.parents)
            position = next((parent.name for parent in parents if parent.name in ('header', 'footer', 'nav', 'aside')), 'body')
            context = ''
            parent = element.parent
            if parent and parent.name in ('p', 'div', 'li', 'td', 'article', 'section'):
                if id(parent) not in context_text_cache:
                    context_text_cache[id(parent)] = parent.get_text(strip=True)
                parent_text = context_text_cache[id(parent)]
                if compact in parent_text:
                    start = max(0, parent_text.index(compact) - 50)
                    end = min(len(parent_text), parent_text.index(compact) + len(compact) + 50)
                    context = ('...' if start else '') + parent_text[start:end] + ('...' if end < len(parent_text) else '')
            href = element.get('href', '')
            snapshot['anchors'].append({
                'attrs': attrs, 'index': index, 'text': text, 'text_compact': compact,
                'labelled_text': labelled,
                'image_alt_text': ' '.join(image.get('alt', '') for image in element.find_all('img')).strip(),
                'context': context, 'position': position,
                'parent_tags': [parent.name for parent in parents],
                'parent_roles': [parent.get('role') for parent in parents],
                'parent_classes': [str(parent.get('class', [])) for parent in parents],
                'url': resolve_url(href, base_url), 'url_kind': classify_url(href, url, base_url),
            })
    snapshot['headings'] = heading_facts(soup)
    snapshot['robots'] = parse_robots(soup, snapshot['headers'], user_agent)
    snapshot['canonical'] = canonical_facts(snapshot['link_tags'], url, base_url, snapshot['headers'])
    return PageFacts(url=url, base_url=base_url, html=html, text=soup.get_text(' ', strip=True),
                     content_text=extract_content_text(soup, html=html), language=language,
                     is_xml=bool(soup.is_xml), doctype=tuple(str(node) for node in soup.contents if isinstance(node, Doctype)),
                     dom_size=len(elements), user_agent=user_agent.lower(), _source_id=id(soup), _snapshot=snapshot)


def ensure_page_facts(soup: BeautifulSoup, url: str, headers: Any = None,
                      user_agent: Optional[str] = None, facts: Optional[PageFacts] = None) -> PageFacts:
    """Reuse a matching snapshot or build one for a standalone analyzer call."""
    if facts is None:
        return extract_page_facts(soup, url, headers, user_agent or 'googlebot')
    if not isinstance(facts, PageFacts):
        raise TypeError('facts must be a PageFacts snapshot')
    if facts.url != url or facts._source_id != id(soup):
        raise ValueError('PageFacts does not belong to this URL and soup')
    if user_agent is not None and facts.user_agent != user_agent.lower():
        raise ValueError('PageFacts was extracted for a different user agent')
    if headers is not None and _headers_snapshot(headers) != facts.headers:
        raise ValueError('PageFacts was extracted with different response headers')
    return facts
