"""Shared snapshots retain HTML semantics and isolate analyzer observations."""

import asyncio
import copy
import json
from dataclasses import FrozenInstanceError, replace

import pytest
from bs4 import BeautifulSoup
from multidict import CIMultiDict

from tfq0seo.analyzers.content import analyze_content, extract_text_content
from tfq0seo.analyzers.seo import analyze_seo
from tfq0seo.page_facts import FACTS_VERSION, ensure_page_facts, extract_page_facts


URL = 'https://example.test/articles/'


def document(body='', head='', lang='en'):
    return BeautifulSoup(f'<!doctype html><html lang="{lang}"><head><title>Example</title>{head}</head>'
                         f'<body>{body}</body></html>', 'html.parser')


def test_snapshot_collections_and_nested_storage_are_isolated_from_mutation():
    soup = document('<h1>Heading</h1><img src="/image.png" class="one two">')
    headers = {'X-Robots-Tag': ['nofollow']}
    facts = extract_page_facts(soup, URL, headers)
    before = facts.to_dict()
    images = facts.images
    images[0]['attrs']['class'].append('changed')
    facts.headers['x-robots-tag'].append('noindex')
    facts.headings['headings']['h1'].clear()
    headers['X-Robots-Tag'].append('noindex')
    soup.img['src'] = '/changed.png'
    assert facts.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        facts.base_url = 'https://other.test/'
    with pytest.raises(TypeError):
        facts._snapshot['images'][0]['attrs']['src'] = '/changed.png'
    assert copy.deepcopy(facts) is facts


def test_declarations_preserve_order_boolean_presence_and_empty_attributes():
    soup = document('<h1>Main</h1><h3>Subsection</h3><img src="/a.png" alt=""><img src="/b.png">',
                    '<meta name="viewport" content=""><meta name="viewport" content="width=device-width">'
                    '<script async src="/async.js"></script><script defer src="/defer.js"></script>'
                    '<script type="module">export default 1;</script>')
    facts = extract_page_facts(soup, URL)
    assert [meta['attrs']['content'] for meta in facts.meta] == ['', 'width=device-width']
    assert 'alt' in facts.images[0]['attrs'] and facts.images[0]['attrs']['alt'] == ''
    assert 'alt' not in facts.images[1]['attrs']
    assert 'async' in facts.scripts[0]['attrs']
    assert 'defer' in facts.scripts[1]['attrs']
    assert facts.scripts[2]['text'] == 'export default 1;'
    assert all(script['in_head'] for script in facts.scripts)
    assert facts.doctype == ('html',)
    assert facts.headings['findings'][0]['rule_id'] == 'headings.skipped_level'
    assert facts.dom_size == len(soup.find_all(True))


def test_anchor_snapshot_keeps_accessible_name_inputs_and_reference_semantics():
    soup = document('<nav><a href="child//?x=1&amp;x=2&amp;empty=" aria-labelledby="label">'
                    '<span>Go</span><span>now</span><img alt="Picture"></a></nav>'
                    '<span id="label">Accessible label</span>', '<base href="https://outside.test/base/">')
    facts = extract_page_facts(soup, URL)
    anchor = facts.anchors[0]
    assert anchor['text'] == 'Go now'
    assert anchor['text_compact'] == 'Gonow'
    assert anchor['labelled_text'] == 'Accessible label'
    assert anchor['image_alt_text'] == 'Picture'
    assert anchor['position'] == 'nav'
    assert anchor['parent_tags'][0] == 'nav'
    assert anchor['url'] == 'https://outside.test/base/child//?x=1&x=2&empty='
    assert anchor['url_kind'] == 'external'
    assert anchor['attrs']['href'] == 'child//?x=1&x=2&empty='


@pytest.mark.parametrize('headers,observed', [(None, False), ({}, True)])
def test_unknown_headers_are_distinct_from_observed_empty_headers(headers, observed):
    facts = extract_page_facts(document(), URL, headers)
    assert facts.headers == headers
    assert facts.robots['headers_checked'] is observed
    assert facts.to_dict()['headers_observed'] is observed


def test_repeated_headers_and_bot_scope_survive_extraction():
    headers = CIMultiDict([('X-Robots-Tag', 'otherbot: noindex'),
                          ('x-robots-tag', 'googlebot: nofollow'),
                          ('Content-Security-Policy', "default-src 'self'"),
                          ('Content-Security-Policy', "script-src 'none'")])
    facts = extract_page_facts(document(), URL, headers, 'OtherBot')
    assert facts.user_agent == 'otherbot'
    assert facts.robots['noindex'] is True
    assert facts.robots['nofollow'] is False
    assert facts.headers['content-security-policy'] == ["default-src 'self'", "script-src 'none'"]
    assert len(facts.headers['x-robots-tag']) == 2


def test_default_export_omits_bulk_text_scripts_and_raw_response_headers():
    soup = document('<p>LONG_BODY_MARKER</p>', '<script>PRIVATE_SCRIPT_MARKER</script>')
    facts = extract_page_facts(soup, URL, {'Set-Cookie': 'session=COOKIE_SECRET'})
    exported = facts.to_dict()
    encoded = json.dumps(exported, allow_nan=False)
    assert exported['facts_version'] == FACTS_VERSION
    assert exported['header_names'] == ['set-cookie']
    assert 'headers' not in exported
    assert 'COOKIE_SECRET' not in encoded
    assert 'LONG_BODY_MARKER' not in encoded
    assert 'PRIVATE_SCRIPT_MARKER' not in encoded
    assert 'html' not in exported and 'content_text' not in exported and 'text' not in exported
    assert exported['paragraph_count'] == 1
    assert exported['scripts'][0]['text_length'] == len('PRIVATE_SCRIPT_MARKER')
    full = facts.to_dict(include_content=True)
    assert full['html'] == str(soup)
    assert full['paragraphs'] == ['LONG_BODY_MARKER']
    assert full['scripts'][0]['text'] == 'PRIVATE_SCRIPT_MARKER'


@pytest.mark.parametrize('body,plain,structured', [
    ('<p>First  words</p><p>Second\nwords</p>', 'Example First words Second words', 'Example\nFirst words\nSecond\nwords'),
    ('<div hidden><div hidden>Invisible</div></div><p>Visible</p>', 'Example Visible', 'Example\nVisible'),
    ('<script>Code</script><style>Style</style><noscript>Fallback</noscript><svg>Vector</svg>'
     '<iframe>Frame</iframe><p style="display: none">Hidden</p><p>Shown</p>', 'Example Shown', 'Example\nShown'),
])
def test_shared_content_text_preserves_existing_cleaning_behavior(body, plain, structured):
    soup = document(body)
    before = str(soup)
    facts = extract_page_facts(soup, URL)
    assert facts.content_text == plain
    assert extract_text_content(soup, preserve_structure=True) == structured
    assert str(soup) == before


@pytest.mark.parametrize('analyzer', [analyze_seo, analyze_content])
def test_supplied_snapshot_avoids_reextraction_and_matches_standalone_output(monkeypatch, analyzer):
    soup = document('<h1>Heading</h1><p>Some content.</p><img src="/img.png"><a href="next/">Next page</a>')
    expected = analyzer(soup, URL)
    facts = extract_page_facts(soup, URL)

    def no_extraction(*args, **kwargs):
        raise AssertionError('Shared facts were extracted twice')

    monkeypatch.setattr('tfq0seo.page_facts.extract_page_facts', no_extraction)
    monkeypatch.setattr('tfq0seo.analyzers.common.heading_facts', no_extraction)
    monkeypatch.setattr('tfq0seo.analyzers.common.parse_robots', no_extraction)
    actual = analyzer(soup, URL, facts=facts)
    assert actual == expected
    assert json.loads(json.dumps(actual, allow_nan=False)) == actual


def test_seo_uses_supplied_snapshot_bot_and_headers_when_arguments_are_omitted():
    soup = document()
    facts = extract_page_facts(soup, URL, {'X-Robots-Tag': 'otherbot: noindex'}, 'otherbot')
    result = analyze_seo(soup, URL, facts=facts)
    assert result['data']['robots_analysis']['noindex'] is True
    assert result['data']['robots_analysis']['headers_checked'] is True


def test_supplied_snapshots_reject_mismatched_input_context():
    soup = document()
    facts = extract_page_facts(soup, URL, {'X-Robots-Tag': 'nofollow'}, 'otherbot')
    with pytest.raises(ValueError, match='URL and soup'):
        ensure_page_facts(soup, URL + 'different', facts=facts)
    with pytest.raises(ValueError, match='URL and soup'):
        ensure_page_facts(document(), URL, facts=facts)
    with pytest.raises(ValueError, match='headers'):
        ensure_page_facts(soup, URL, headers={}, facts=facts)
    with pytest.raises(ValueError, match='agent'):
        analyze_seo(soup, URL, user_agent='googlebot', facts=facts)
    with pytest.raises(TypeError, match='PageFacts'):
        ensure_page_facts(soup, URL, facts={})


@pytest.mark.parametrize('value', [object(), float('nan'), ['valid', object()]])
def test_nonportable_parser_attributes_are_rejected_instead_of_stringified(value):
    soup = document('<img src="/image.png">')
    soup.img['data-custom'] = value
    with pytest.raises(TypeError, match='attribute value'):
        extract_page_facts(soup, URL)


@pytest.mark.parametrize('headers', [{'X-Value': object()}, {'X-Value': [1]}, {1: 'value'}])
def test_invalid_header_values_are_rejected_without_implicit_conversion(headers):
    with pytest.raises(TypeError, match='header'):
        extract_page_facts(document(), URL, headers)


def test_direct_constructor_rejects_incomplete_or_nonportable_snapshots():
    facts = extract_page_facts(document(), URL)
    with pytest.raises(ValueError, match='complete snapshot'):
        replace(facts, _snapshot={})
    with pytest.raises(TypeError, match='language'):
        replace(facts, language=object())
    malformed = dict(facts._snapshot)
    malformed['extra'] = object()
    with pytest.raises(TypeError, match='finite JSON primitives'):
        replace(facts, _snapshot=malformed)


def test_application_extracts_one_snapshot_and_passes_it_to_all_five_analyzers(monkeypatch):
    from tfq0seo.core import app
    from tfq0seo import page_facts as module

    extracted, received = [], {}
    original_extract = module.extract_page_facts

    def counted_extract(*args, **kwargs):
        facts = original_extract(*args, **kwargs)
        extracted.append(facts)
        return facts

    monkeypatch.setattr(module, 'extract_page_facts', counted_extract)
    monkeypatch.setattr(app, 'extract_page_facts', counted_extract)
    for name in ('seo', 'content', 'technical', 'performance', 'links'):
        function = getattr(app, 'analyze_' + name)

        def observe(*args, _name=name, _function=function, **kwargs):
            received[_name] = kwargs.get('facts')
            return _function(*args, **kwargs)

        monkeypatch.setattr(app, 'analyze_' + name, observe)
    soup = document('<h1>Example</h1><p>Content.</p><a href="next/">Next page</a><img src="/image.png">')
    before = str(soup)
    result = asyncio.run(app.SEOAnalyzer().analyze_page({'url': URL, 'soup': soup, 'headers': {}, 'status_code': 200}))
    assert result['status'] == 'complete', result.get('analyzer_errors')
    assert len(extracted) == 1
    assert len(received) == 5 and all(facts is extracted[0] for facts in received.values())
    assert result['page_facts'] == extracted[0].to_dict()
    assert str(soup) == before
    assert json.loads(json.dumps(result, allow_nan=False)) == result
