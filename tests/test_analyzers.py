"""Regression fixtures for analyzer correctness and measurement provenance."""

import json

import pytest
from bs4 import BeautifulSoup
from multidict import CIMultiDict

from tfq0seo.analyzers import (
    analyze_content, analyze_links, analyze_performance, analyze_seo, analyze_technical,
)
from tfq0seo.analyzers.common import parse_robots
from tfq0seo.analyzers.content import detect_language, extract_text_content
from tfq0seo.analyzers.links import estimate_domain_authority, normalize_url
from tfq0seo.analyzers.performance import analyze_javascript_optimization, is_third_party
from tfq0seo.analyzers.seo import analyze_heading_structure, analyze_internal_linking_seo
from tfq0seo.analyzers.technical import analyze_crawlability, analyze_performance_indicators
from tfq0seo.urls import classify_url, resolve_url


URL = 'https://example.com/articles/'


def document(body='', head='', lang='en'):
    return BeautifulSoup(
        f'<!DOCTYPE html><html lang="{lang}"><head><title>Example page title for testing</title>'
        f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'{head}</head><body>{body}</body></html>', 'html.parser')


def rule_ids(result):
    return {issue.get('rule_id') for issue in result['issues']}


@pytest.mark.parametrize('body', [
    '<h1>Historical information</h1><p>Records for 2001 2002 2003.</p>',
    '<h1></h1><h1> </h1>',
    '<div hidden><div hidden>Hidden</div></div><h1>Visible heading</h1>',
])
def test_content_accepts_previously_crashing_markup(body):
    result = analyze_content(document(body), URL)
    assert 'error' not in result
    assert 0 <= result['score'] <= 100
    json.dumps(result, allow_nan=False)


def test_content_extraction_preserves_original_and_does_not_hide_arbitrary_classes():
    soup = document('<div class="unhidden">Visible words</div><div hidden>Secret</div>')
    before = str(soup)
    content = extract_text_content(soup)
    assert 'Visible words' in content
    assert 'Secret' not in content
    assert str(soup) == before


def test_content_length_and_keyword_density_are_not_ranking_requirements():
    short = document('<h1>Informations sur le produit</h1><p>Produit utile.</p>', lang='fr')
    long = document('<h1>Informations sur le produit</h1><p>' + 'produit ' * 3500 + '</p>', lang='fr')
    short_result = analyze_content(short, URL, ['produit'])
    long_result = analyze_content(long, URL, ['produit'])
    assert short_result['score'] == long_result['score']
    assert not any('word count' in issue['message'].lower() or 'stuffing' in issue['message'].lower()
                   for result in (short_result, long_result) for issue in result['issues'])


def test_empty_alt_is_valid_for_decorative_images():
    soup = document('<h1>Accessible page heading</h1><img src="/decoration.png" alt="" width="1" height="1">')
    assert 'images.missing_alt' not in rule_ids(analyze_content(soup, URL))
    assert 'images.missing_alt' not in rule_ids(analyze_seo(soup, URL))


def test_missing_alt_reports_a_stable_rule_and_evidence():
    soup = document('<h1>Accessible page heading</h1><img src="/important.png">')
    for analyzer in (analyze_content, analyze_seo):
        issue = next(issue for issue in analyzer(soup, URL)['issues'] if issue.get('rule_id') == 'images.missing_alt')
        assert issue['evidence']


def test_language_prefers_declaration_and_does_not_assume_latin_text_is_english():
    assert detect_language('Bonjour le monde, nous sommes ici.') == 'und'
    assert detect_language('Bonjour le monde', 'fr-CA') == 'fr'
    assert detect_language('私は日本語を話します') == 'ja'
    result = analyze_content(document('<h1>日本語のページです</h1><p>内容を説明します。</p>', lang='ja'), URL)
    assert result['data']['metrics']['word_count'] is None
    assert result['data']['metrics']['word_count_method'] == 'unavailable'
    assert result['data']['structure']['has_call_to_action'] is None
    assert not any('introduction' in issue['message'] or 'call-to-action' in issue['message'] for issue in result['issues'])


@pytest.mark.parametrize('meta,headers,expected_index,expected_follow', [
    ('<meta name="robots" content="none">', None, True, True),
    ('<meta name="GOOGLEBOT" content="NOINDEX">', None, True, False),
    ('<meta name="robots" content="index"><meta name="robots" content="noindex">', None, True, False),
    ('<meta name="otherbot" content="noindex">', None, False, False),
    ('<meta name="robots" content="notnoindex">', None, False, False),
    ('', {'X-Robots-Tag': ['otherbot: noindex', 'nofollow', 'googlebot: noindex']}, True, True),
    ('', {'X-Robots-Tag': 'googlebot: noindex, otherbot: nofollow'}, True, False),
    ('', {'X-Robots-Tag': 'otherbot: noindex, googlebot: nofollow'}, False, True),
    ('', {'X-Robots-Tag': 'all, none'}, True, True),
])
def test_robots_combines_applicable_directives(meta, headers, expected_index, expected_follow):
    soup = document(head=meta)
    parsed = parse_robots(soup, headers)
    assert parsed['noindex'] is expected_index
    assert parsed['nofollow'] is expected_follow
    technical = analyze_crawlability(soup, headers)
    assert technical.noindex is expected_index
    assert technical.nofollow is expected_follow
    seo = analyze_seo(soup, URL, headers=headers)
    assert ('robots.noindex' in rule_ids(seo)) is expected_index


def test_repeated_headers_and_restrictive_snippet_values_are_preserved():
    headers = CIMultiDict([('X-Robots-Tag', 'max-snippet: -1'),
                          ('X-Robots-Tag', 'googlebot: noindex, max-snippet: 20')])
    parsed = parse_robots(document(), headers)
    assert parsed['noindex'] is True
    assert parsed['max_snippet'] == 20
    assert len(parsed['evidence']) == 2


def test_indexability_does_not_claim_robots_txt_crawl_access():
    result = analyze_technical(document(head='<meta name="robots" content="noindex">'), URL)
    assert result['data']['crawlability']['indexability'] == 'blocked_by_robots'
    assert result['data']['crawlability']['crawl_access'] == 'unknown'
    assert result['data']['crawlability']['status'] == 'unknown'


@pytest.mark.parametrize('doctype', ['<!DOCTYPE html>', '<!doctype HTML>'])
def test_valid_html5_doctype_is_recognized(doctype):
    soup = BeautifulSoup(doctype + '<html lang="en"><h1>Heading</h1></html>', 'html.parser')
    ids = rule_ids(analyze_technical(soup, URL))
    assert 'html.doctype_missing' not in ids
    assert 'html.doctype_legacy' not in ids


def test_missing_doctype_is_reported():
    soup = BeautifulSoup('<html><h1>Heading</h1></html>', 'html.parser')
    assert 'html.doctype_missing' in rule_ids(analyze_technical(soup, URL))


@pytest.mark.parametrize('attribute', ['async', 'defer', 'async=""', 'defer="defer"', 'type="module"'])
def test_nonblocking_scripts_use_html_boolean_attribute_semantics(attribute):
    soup = document(head=f'<script src="/app.js" {attribute}></script>')
    result = analyze_performance(soup, URL)
    assert analyze_javascript_optimization(soup)['render_blocking'] == 0
    assert 'performance.blocking_scripts' not in rule_ids(result)
    assert not result['data']['critical_rendering_path']['render_blocking_resources']


def test_blocking_script_finding_and_font_preloads():
    soup = document(head='<script src="/app.js"></script><link rel="preload" as="font" href="/font.woff2">')
    result = analyze_performance(soup, URL)
    assert 'performance.blocking_scripts' in rule_ids(result)
    assert result['resources']['fonts'] == ['https://example.com/font.woff2']
    assert result['grade'] == ('A' if result['score'] >= 90 else 'B' if result['score'] >= 80 else 'C' if result['score'] >= 70 else 'D' if result['score'] >= 60 else 'F')


def test_script_origin_checks_use_resolved_urls_instead_of_brand_substrings():
    soup = document(head='<script defer src="/facebook.min.js"></script>'
                    '<script async src="//assets.other.test/a.js"></script>')
    scripts = analyze_performance(soup, URL)['data']['javascript_optimization']
    assert [script['url'] for script in scripts['third_party_scripts']] == ['https://assets.other.test/a.js']
    assert scripts['minified_scripts'] is None
    assert scripts['minified_filename_references'] == 1


@pytest.mark.parametrize('fetch_time', [None, 0, 1.25])
def test_no_fabricated_browser_timings_or_passing_resource_budgets(fetch_time):
    soup = document('<img src="/large.jpg">', head='<script defer src="/app.js"></script>')
    result = analyze_performance(soup, URL, load_time=fetch_time, content_length=500)
    data = result['data']
    for key in ('load_time', 'lcp', 'inp', 'fid', 'cls', 'fcp', 'tti', 'tbt', 'ttfb'):
        assert data['metrics'][key] is None
        assert data['metric_sources'][key] == 'not_measured'
    assert data['metrics']['html_fetch_time'] == (fetch_time or None)
    assert data['metrics']['html_content_bytes'] == 500
    assert data['performance_level'] is None
    for category in data['performance_budget'].values():
        for metric in category.values():
            assert metric['current'] is None
            assert metric['status'] == 'unknown'
    assert data['image_optimization']['savings_potential_kb'] is None
    assert data['caching_strategy']['estimated_cache_hit_rate'] is None
    assert data['network_metrics']['total_requests'] is None
    assert data['network_metrics']['referenced_resources'] == 2
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('payload', [
    {'@context': 'https://schema.org', '@graph': [{'@type': 'Organization', 'name': 'Example', 'url': 'https://example.com'}]},
    [{'@context': 'https://schema.org', '@type': 'Organization', 'name': 'Example', 'url': 'https://example.com'}],
    {'@context': 'https://schema.org', '@type': ['Organization', 'Thing'], 'name': 'Example', 'url': 'https://example.com'},
])
def test_valid_jsonld_graphs_arrays_and_type_arrays(payload):
    result = analyze_seo(document(head='<script type="application/ld+json">' + json.dumps(payload) + '</script>'), URL)
    nodes = result['data']['structured_data']
    assert len(nodes) == 1
    assert nodes[0]['valid'] is True
    assert nodes[0]['errors'] == []
    assert nodes[0]['rich_snippet_eligible'] is None
    assert nodes[0]['eligibility_status'] == 'unknown'


@pytest.mark.parametrize('payload', ['[null]', '[]', '{"@graph": 42}', '{bad json'])
def test_invalid_or_empty_jsonld_does_not_crash_analyzer(payload):
    result = analyze_seo(document(head='<script type="application/ld+json">' + payload + '</script>'), URL)
    assert any(issue['category'] == 'Structured Data' for issue in result['issues'])
    json.dumps(result, allow_nan=False)


def test_heading_order_is_checked_in_document_order():
    skipped = analyze_heading_structure(document('<h1>Main</h1><h3>Skipped</h3><h2>Later</h2>'))
    valid = analyze_heading_structure(document('<h1>Main</h1><h2>A</h2><h3>A1</h3><h2>B</h2><h3>B1</h3>'))
    assert skipped['hierarchy_valid'] is False
    assert valid['hierarchy_valid'] is True


def test_url_resolution_preserves_meaningful_url_components():
    reference = '/path//item/?source=a&ref=b&utm_source=c&empty=&x=1&x=2#section'
    assert normalize_url(reference, URL) == 'https://example.com' + reference
    soup = document(f'<a href="{reference}">Item details</a>')
    result = analyze_links(soup, URL)
    assert result['data']['internal_links'][0]['url'] == 'https://example.com' + reference
    assert result['data']['internal_links'][0]['href'] == reference


@pytest.mark.parametrize('reference,expected', [
    ('child//leaf/', 'https://example.com/articles/child//leaf/'),
    ('../child//leaf/?ref=a&empty=&q=2&q=1#x', 'https://example.com/child//leaf/?ref=a&empty=&q=2&q=1#x'),
    ('a/./b/../c//d', 'https://example.com/articles/a/c//d'),
    ('/a//b/../c/', 'https://example.com/a//c/'),
    ('//EXAMPLE.COM:443/a//b/', 'https://example.com/a//b/'),
    ('?', 'https://example.com/articles/?'),
    ('#part', 'https://example.com/articles/#part'),
    ('', 'https://example.com/articles/'),
    ('https://BÜCHER.example:443/a', 'https://xn--bcher-kva.example/a'),
])
def test_shared_resolver_preserves_uri_reference_semantics(reference, expected):
    assert resolve_url(reference, URL) == expected


@pytest.mark.parametrize('reference', ['http://[', 'https://example.com:99999/', 'https://bad host/', None])
def test_shared_resolver_rejects_malformed_authorities_without_raising(reference):
    assert resolve_url(reference, URL) is None


def test_shared_classifier_matches_standard_protocol_transitions_and_exact_hosts():
    assert classify_url('http://EXAMPLE.com:80/', URL) == 'internal'
    assert classify_url('https://example.com:8443/', URL) == 'external'
    assert classify_url('https://sub.example.com/', URL) == 'external'
    assert classify_url('https://example.com.attacker.test/', URL) == 'external'


def test_link_classification_is_consistent_and_honors_html_base():
    soup = document('<a href="page/">Relative</a><a href="//outside.test/x">External</a>'
                    '<a href="https://example.com/">Home</a><a href="mailto:info@example.com">Email</a>'
                    '<a href="tel:+123">Telephone</a>', head='<base href="https://outside.test/">')
    seo = analyze_internal_linking_seo(soup, URL)
    links = analyze_links(soup, URL)['data']
    assert seo['internal_count'] == links['metrics']['internal_links'] == 1
    assert seo['external_count'] == links['metrics']['external_links'] == 2
    assert len(links['non_http_links']) == 2
    assert links['external_links'][0]['url'] == 'https://outside.test/page/'
    assert is_third_party('/relative.js', URL) is False
    assert is_third_party('//outside.test/app.js', URL) is True


def test_malformed_link_is_reported_without_losing_other_link_evidence():
    result = analyze_links(document('<a href="http://[">Bad</a><a href="/good/">Good</a>'), URL)
    assert 'links.invalid_url' in rule_ids(result)
    assert len(result['data']['internal_links']) == 1


def test_no_authority_velocity_or_incomplete_graph_claims_and_no_link_truncation():
    assert estimate_domain_authority('google.com.attacker.example') is None
    assert estimate_domain_authority('google.com') is None
    body = ''.join(f'<a href="/page/{index}/">Page {index}</a>' for index in range(220))
    result = analyze_links(document(body), URL)
    assert len(result['data']['internal_links']) == 220
    assert result['data']['link_velocity']['links_per_day'] is None
    assert result['data']['internal_structure']['orphan_pages'] is None
    assert result['data']['link_health_status'] == 'not_checked'
    assert result['data']['broken_links'] is None
    assert not any('toxic' in issue['message'] or 'velocity' in issue['message'] for issue in result['issues'])


def test_header_hints_do_not_fabricate_protocol_caching_or_security_failures():
    headers = {'Alt-Svc': 'h3=":443"', 'Cache-Control': 'no-cache, max-age=600',
               'Content-Security-Policy': "default-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'"}
    indicators = analyze_performance_indicators(headers)
    assert indicators.protocol_version.value == 'Unknown'
    assert indicators.cache_ttl == 600
    assert indicators.compression_ratio is None
    assert indicators.server_push_enabled is None
    result = analyze_technical(document(), URL, headers=headers)
    messages = [issue['message'] for issue in result['issues']]
    assert 'No caching configured' not in messages
    assert 'CSP allows unsafe-inline scripts' not in messages
    assert 'Missing X-Frame-Options header' not in messages


def test_absent_header_measurement_is_unknown():
    result = analyze_technical(document(), URL, headers=None)
    assert result['data']['security']['hsts'] is None
    assert result['data']['security']['source'] == 'not_measured'
    assert not any('Missing HSTS' in issue['message'] or 'Content not compressed' in issue['message'] for issue in result['issues'])


def test_no_deprecated_rich_result_recommendations():
    soup = document('<h1>FAQ and how to guide</h1><p>Frequently asked questions and step by step answers.</p>')
    seo = analyze_seo(soup, URL)
    content = analyze_content(soup, URL)
    suggested = json.dumps(seo['data']['opportunities']) + json.dumps(content['data'].get('schema_suggestions', []))
    assert 'FAQPage' not in suggested
    assert 'How-To' not in suggested
    assert '50%' not in suggested


@pytest.mark.parametrize('analyzer', [analyze_content, analyze_seo, analyze_technical, analyze_performance, analyze_links])
def test_analyzer_result_is_strict_json_and_input_is_not_mutated(analyzer):
    soup = document('<h1>Page heading for this example</h1><a href="/next/?empty=">Next page</a>')
    before = str(soup)
    result = analyzer(soup, URL)
    assert set(('score', 'issues', 'data', 'recommendations')) <= result.keys()
    json.dumps(result, allow_nan=False)
    assert str(soup) == before
