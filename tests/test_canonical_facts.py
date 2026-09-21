"""Canonical observations preserve context and uncertainty without raw headers."""

import json

import pytest
from bs4 import BeautifulSoup
from multidict import CIMultiDict

from tfq0seo.page_facts import FACTS_VERSION, extract_page_facts


URL = 'https://example.test/articles/page?view=all'


def facts(head='', body='', headers=None):
    soup = BeautifulSoup('<html><head>' + head + '</head><body>' + body + '</body></html>', 'html.parser')
    return extract_page_facts(soup, URL, headers)


def test_html_canonical_records_keep_all_declarations_and_head_placement():
    observed = facts('<base href="https://cdn.test/base/">'
                     '<link rel="CANONICAL alternate" href="child//?x=1&amp;x=2&amp;empty=#part">'
                     '<link rel="canonical" href="/second">',
                     '<link rel="Canonical" href="/body">')
    declarations = observed.canonical['declarations']
    assert [item['url'] for item in declarations] == [
        'https://cdn.test/base/child//?x=1&x=2&empty=#part',
        'https://cdn.test/second', 'https://cdn.test/body']
    assert [item['eligible'] for item in declarations] == [True, True, False]
    assert declarations[-1]['reason'] == 'HTML canonical declaration is outside the head.'
    assert [link['in_head'] for link in observed.link_tags] == [True, True, False]
    assert all(item['source'] == 'html' for item in declarations)
    assert observed.canonical['parse_errors'] == 0


@pytest.mark.parametrize('attribute', ['hreflang="en"', 'lang="en"', 'media="all"', 'type="text/html"',
                                      'hreflang', 'TYPE=""'])
def test_alternate_html_attributes_make_declaration_ineligible(attribute):
    declaration = facts('<link rel="canonical" href="/target" ' + attribute + '>').canonical['declarations'][0]
    assert declaration['url'] == 'https://example.test/target'
    assert declaration['eligible'] is False
    assert 'alternate-version attributes' in declaration['reason']


@pytest.mark.parametrize('href', [None, '', ' ', 'javascript:alert(1)', 'mailto:user@example.test',
                                 'https://[', 'https://example.test:wrong/', '/bad%xx', '/two words'])
def test_invalid_html_targets_keep_raw_evidence_without_graph_edges(href):
    soup = BeautifulSoup('<html><head><link rel="canonical"></head></html>', 'html.parser')
    if href is not None:
        soup.link['href'] = href
    observation = extract_page_facts(soup, URL).canonical
    assert observation['declarations'] == [{
        'href': href, 'url': None, 'source': 'html', 'eligible': False,
        'reason': 'Canonical target is missing or is not a valid HTTP(S) URL.'}]
    assert observation['parse_errors'] == 0  # Parsed HTML observation, not ambiguous HTTP syntax.


@pytest.mark.parametrize('headers,checked', [(None, False), ({}, True), ({'Link': ''}, True)])
def test_header_observation_state_distinguishes_unknown_and_no_declarations(headers, checked):
    assert facts(headers=headers).canonical == {'declarations': [], 'headers_checked': checked, 'parse_errors': 0}


def test_repeated_http_link_fields_use_response_base_and_preserve_reference_semantics():
    observed = facts('<base href="https://cdn.test/base/">', headers=CIMultiDict([
        ('Link', '<next//?x=1&x=2&empty=#part>; rel=canonical'),
        ('link', '<https://EXAMPLE.test:443/second>; ReL="alternate CANONICAL"'),
    ]))
    assert observed.canonical == {'declarations': [
        {'href': 'next//?x=1&x=2&empty=#part',
         'url': 'https://example.test/articles/next//?x=1&x=2&empty=#part',
         'source': 'http_link', 'eligible': True, 'reason': ''},
        {'href': 'https://EXAMPLE.test:443/second', 'url': 'https://example.test/second',
         'source': 'http_link', 'eligible': True, 'reason': ''}],
        'headers_checked': True, 'parse_errors': 0}


def test_http_commas_semicolons_and_escaped_quotes_do_not_split_link_values():
    header = ('</one,two;three?x=1,2>; rel="canonical alternate"; title="text, semi; '
              '\\"quote\\" and \\\\ slash"; x-flag, '
              '</preload.css>; rel=preload; title="canonical, unrelated", '
              '</last>; rel=canonical; title*=UTF-8\'en\'some%20title')
    observation = facts(headers={'Link': header}).canonical
    assert observation['parse_errors'] == 0
    assert [item['href'] for item in observation['declarations']] == ['/one,two;three?x=1,2', '/last']
    assert all(item['eligible'] for item in observation['declarations'])


@pytest.mark.parametrize('anchor,eligible', [
    ('', True), ('?view=all', True), ('https://EXAMPLE.test:443/articles/page?view=all', True),
    ('/other', False), ('#part', False), ('https://outside.test/', False),
    ('mailto:someone@example.test', False),
])
def test_anchor_context_is_resolved_against_response_and_never_silently_ignored(anchor, eligible):
    observation = facts('<base href="https://other.test/">',
                        headers={'Link': '</canonical>; rel=canonical; anchor="' + anchor + '"'}).canonical
    assert observation['parse_errors'] == 0
    assert observation['declarations'][0]['eligible'] is eligible
    assert observation['declarations'][0]['url'] == 'https://example.test/canonical'
    assert bool(observation['declarations'][0]['reason']) is not eligible


def test_empty_http_uri_reference_is_a_valid_self_reference():
    assert facts(headers={'Link': '<>; rel=canonical'}).canonical['declarations'] == [
        {'href': '', 'url': URL, 'source': 'http_link', 'eligible': True, 'reason': ''}]


@pytest.mark.parametrize('header', [
    '</target>; rel=canonical; rel=alternate',
    '</target>; rel=alternate; rel=canonical',
    '</target>; rel=canonical; anchor=""; anchor="/other"',
    '</target>; rel=canonical; anchor',
    '</target>; rel=canonical; anchor="http://["',
    '</target>; rel=canonical; anchor="http://example.test:bad"',
    '</target>; rel=canonical; title="unterminated',
    '</target>; rel=canonical; title="unterminated\\',
    '</target>; rel=canonical; title="control\x01character"',
    '</target>; rel=canonical stray',
    '</target>; rel=canonical;',
    '</target>; rel=canonical; =bad',
    '</target>; rel=canonical; title=',
    '</bad%xy>; rel=canonical',
    '<https://example.test:bad/>; rel=canonical',
    '<https://[>; rel=canonical',
])
def test_malformed_recognizable_http_canonicals_are_errors_and_never_edges(header):
    observation = facts(headers={'Link': header}).canonical
    assert observation['parse_errors'] == 1
    assert len(observation['declarations']) == 1
    assert observation['declarations'][0]['eligible'] is False
    assert observation['declarations'][0]['reason']


@pytest.mark.parametrize('header', ['not-a-link', '</target> rel=canonical', '</target>; rel',
                                  '</target>; rel=""', '</target>; rel=" "', '</target>; rel="invalid,relation"',
                                  '</target>; title="canonical"', '<unterminated; rel=canonical',
                                  '\r\n</target>; rel=canonical'])
def test_unparseable_link_fields_do_not_claim_reliable_canonical_absence(header):
    observation = facts(headers={'Link': header}).canonical
    assert observation['parse_errors'] == 1
    assert observation['declarations'] == []
    assert observation['headers_checked'] is True


def test_bad_field_does_not_discard_other_independently_parseable_fields():
    observation = facts(headers={'Link': [
        '</before>; rel=canonical, </broken>; rel=canonical; title="unclosed, </fake>; rel=canonical',
        'garbage, </after>; rel=canonical',
    ]}).canonical
    assert observation['parse_errors'] == 2
    assert [(item['href'], item['eligible']) for item in observation['declarations']] == [
        ('/before', True), ('/broken', False), ('/after', True)]


@pytest.mark.parametrize('parameter', ['hreflang=en', 'lang=en', 'media="screen, print"', 'type="text/html"'])
def test_http_alternate_parameters_are_retained_as_ignored_canonicals(parameter):
    observation = facts(headers={'Link': '</target>; rel=canonical; ' + parameter}).canonical
    assert observation['parse_errors'] == 0
    assert observation['declarations'][0]['eligible'] is False
    assert 'alternate-version attributes' in observation['declarations'][0]['reason']


def test_canonical_export_is_detached_json_and_excludes_unrelated_header_secrets():
    observed = facts('<link rel="canonical" href="/html">', headers={
        'Set-Cookie': 'COOKIE_SECRET', 'Authorization': 'AUTH_SECRET',
        'Link': '</header>; rel=canonical; title="LINK_TITLE_SECRET", '
                '</UNRELATED_TARGET_SECRET>; rel=preload',
    })
    expected = observed.canonical
    observed.canonical['declarations'][0]['href'] = '/changed'
    export = observed.to_dict()
    encoded = json.dumps(export, allow_nan=False)
    assert export['facts_version'] == FACTS_VERSION == '1.1'
    assert export['canonical'] == expected
    assert json.loads(encoded) == export
    assert 'COOKIE_SECRET' not in encoded and 'AUTH_SECRET' not in encoded
    assert 'LINK_TITLE_SECRET' not in encoded and 'UNRELATED_TARGET_SECRET' not in encoded
    export['canonical']['declarations'].clear()
    assert observed.canonical == expected
