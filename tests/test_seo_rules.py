"""Reviewed SEO rules distinguish observed failures from optional metadata."""

import json

import pytest
from bs4 import BeautifulSoup
from multidict import CIMultiDict

from tfq0seo.analyzers.seo import SEO_RULES, analyze_seo, create_issue
from tfq0seo.rules import get_rule, recommendations_for, score_findings


URL = 'https://example.test/article/'


def document(head='', body='<h1>Example</h1>', title='Example', lang='en', viewport=True, charset=True):
    return BeautifulSoup(
        '<!doctype html><html' + (f' lang="{lang}"' if lang is not None else '') + '><head>'
        + (f'<title>{title}</title>' if title is not None else '')
        + ('<meta name="viewport" content="width=device-width, initial-scale=1">' if viewport else '')
        + ('<meta charset="utf-8">' if charset else '')
        + head + '</head><body>' + body + '</body></html>', 'html.parser')


def by_id(result):
    return {rule['rule_id']: rule for rule in result['rule_results']}


def test_every_seo_evaluation_has_registered_metadata_evidence_and_an_explicit_outcome():
    result = analyze_seo(document(), URL)
    rules = by_id(result)
    assert set(rule.rule_id for rule in SEO_RULES) <= rules.keys()
    assert len(rules) == len(result['rule_results'])
    for rule in rules.values():
        definition = get_rule(rule['rule_id'])
        assert rule['evidence'] is not None
        assert rule['fix'] == definition.recommendation
        assert rule['references'] == list(definition.references)
        assert rule['reviewed_on'] == '2026-09-14'
        assert rule['rule_applicability']
        if rule['status'] in ('unknown', 'not_applicable'):
            assert rule['reason']
    assert result['coverage']['counts']['unknown'] > 0
    assert result['coverage']['counts']['not_applicable'] > 0
    assert result['score'] == score_findings(result['issues'])
    assert result['recommendations'] == recommendations_for(result['issues'])
    json.dumps(result, allow_nan=False)


def test_optional_metadata_absence_is_not_a_ranking_failure():
    result = analyze_seo(document(), URL)
    rules = by_id(result)
    assert result['score'] == 100
    assert rules['seo.description_missing']['status'] == 'informational'
    assert rules['seo.canonical_preference']['status'] == 'unknown'
    assert rules['seo.jsonld_eligibility']['status'] == 'unknown'
    assert rules['seo.og_incomplete']['status'] == 'not_applicable'
    assert rules['seo.favicon_missing']['status'] == 'not_applicable'
    assert not any('Twitter' in issue['message'] for issue in result['issues'])


@pytest.mark.parametrize('title,description', [
    ('短い', '説明'),
    ('نص عربي قصير', 'وصف الصفحة.'),
    ('A descriptive title that is longer than sixty characters can still identify its subject', 'summary ' * 100),
])
def test_title_and_description_have_no_universal_length_or_english_cta_requirement(title, description):
    result = analyze_seo(document(title=title, head=f'<meta name="description" content="{description}">'), URL)
    assert result['score'] == 100
    assert not any('too short' in issue['message'] or 'too long' in issue['message']
                   or 'call-to-action' in issue['message'] or 'too wide' in issue['message']
                   for issue in result['issues'])
    assert result['data']['serp_preview']['status'] == 'illustrative'


def test_repetition_is_an_editorial_hint_and_does_not_change_title_fix_selection():
    result = analyze_seo(document(title='Example Example Example'), URL)
    repetition = by_id(result)['seo.title_repetition']
    assert repetition['status'] == 'informational'
    assert repetition['evidence']['repeated_words'] == {'example': 3}
    assert result['score'] == 100
    issue = create_issue('Meta Tags', 'critical', 'Description canonical heading arbitrary words',
                         rule_id='seo.title_missing', evidence={'title': None})
    assert issue['fix'] == get_rule('seo.title_missing').recommendation
    with pytest.raises(ValueError, match='rule_id'):
        create_issue('Meta Tags', 'critical', 'Missing title')


@pytest.mark.parametrize('href', ['http://[', 'mailto:info@example.test', 'javascript:alert(1)'])
def test_invalid_canonical_has_stable_id_and_retains_href_evidence(href):
    rule = by_id(analyze_seo(document(head=f'<link rel="canonical" href="{href}">'), URL))['seo.canonical_invalid']
    assert rule['status'] == 'fail'
    assert rule['evidence']['href'] == href


def test_relative_canonical_preserves_query_and_duplicate_slash_semantics():
    result = analyze_seo(document(head='<link rel="canonical" href="child//item/?x=1&amp;x=2&amp;empty=">'), URL)
    assert result['data']['canonical'] == URL + 'child//item/?x=1&x=2&empty='
    assert by_id(result)['seo.canonical_invalid']['status'] == 'pass'


def test_open_graph_description_is_optional_and_partial_objects_are_contextual():
    head = ''.join(f'<meta property="{name}" content="{value}">' for name, value in (
        ('og:title', 'Example'), ('og:type', 'website'), ('og:image', '/image.png'), ('og:url', URL)))
    result = analyze_seo(document(head=head), URL)
    assert by_id(result)['seo.og_incomplete']['status'] == 'pass'
    assert by_id(result)['seo.og_image_dimensions']['status'] == 'informational'
    partial = by_id(analyze_seo(document(head='<meta property="og:title" content="Example">'), URL))
    assert partial['seo.og_incomplete']['status'] == 'informational'
    assert partial['seo.og_incomplete']['evidence']['missing'] == ['og:type', 'og:image', 'og:url']


@pytest.mark.parametrize('payload', [
    {'@context': 'https://schema.org', '@type': 'Article'},
    {'@context': 'https://schema.org', '@type': 'Product', 'offers': {'@type': 'AggregateOffer'}},
    {'@id': 'https://example.test/entity'},
    {'@context': 'https://schema.org', '@graph': [{'@type': 'Organization'}, {'@id': '#person'}]},
    [{'@type': ['https://schema.org/Thing']}],
])
def test_jsonld_shapes_do_not_invent_required_properties_or_rich_result_eligibility(payload):
    result = analyze_seo(document(head='<script type="application/ld+json">' + json.dumps(payload) + '</script>'), URL)
    assert by_id(result)['seo.jsonld_shape']['status'] == 'pass'
    assert all(node['valid'] and not node['errors'] for node in result['data']['structured_data'])
    assert all(node['rich_snippet_eligible'] is None for node in result['data']['structured_data'])
    assert by_id(result)['seo.jsonld_eligibility']['status'] == 'unknown'


@pytest.mark.parametrize('payload,rule_id', [
    ('{bad json', 'seo.jsonld_syntax'),
    ('{"price":NaN}', 'seo.jsonld_syntax'),
    ('{"@graph":42}', 'seo.jsonld_shape'),
    ('{"@type":["Thing",42]}', 'seo.jsonld_shape'),
])
def test_jsonld_failures_keep_structured_parser_evidence(payload, rule_id):
    result = analyze_seo(document(head='<script type="APPLICATION/LD+JSON">' + payload + '</script>'), URL)
    rule = by_id(result)[rule_id]
    assert rule['status'] == 'fail'
    assert rule['evidence']['errors'][0]['script_index'] == 0
    json.dumps(result, allow_nan=False)


def test_empty_jsonld_is_valid_but_has_no_entity_to_assess():
    rules = by_id(analyze_seo(document(head='<script type="application/ld+json">[]</script>'), URL))
    assert rules['seo.jsonld_syntax']['status'] == 'pass'
    assert rules['seo.jsonld_shape']['status'] == 'pass'
    assert rules['seo.jsonld_empty']['status'] == 'informational'


def test_encoding_absence_is_unknown_and_http_charset_prevents_false_missing_declaration():
    soup = document(charset=False)
    assert by_id(analyze_seo(soup, URL))['seo.charset_missing']['status'] == 'unknown'
    headers = {'content-type': 'text/html; charset="UTF-8"'}
    rules = by_id(analyze_seo(soup, URL, headers=headers))
    assert rules['seo.charset_missing']['status'] == 'pass'
    assert rules['seo.charset_non_utf8']['status'] == 'pass'


@pytest.mark.parametrize('language', ['fr-CA', 'zh-Hant', 'i-klingon', 'x-private'])
def test_language_shape_check_does_not_reject_private_or_grandfathered_tags(language):
    rules = by_id(analyze_seo(document(lang=language), URL))
    assert rules['seo.language_format']['status'] == 'pass'
    assert rules['seo.language_format']['evidence']['registry_checked'] is False


def test_malformed_language_has_a_distinct_registered_rule():
    assert by_id(analyze_seo(document(lang='en_US'), URL))['seo.language_format']['status'] == 'fail'
    assert by_id(analyze_seo(document(lang=None), URL))['language.missing']['status'] == 'fail'


@pytest.mark.parametrize('viewport', ['width = device-width, USER-SCALABLE = NO', 'width=device-width, maximum-scale=1'])
def test_viewport_zoom_check_parses_whitespace_case_and_numeric_limits(viewport):
    soup = document(viewport=False, head=f'<meta name="viewport" content="{viewport}">')
    rules = by_id(analyze_seo(soup, URL))
    assert rules['mobile.viewport_zoom_disabled']['status'] == 'fail'
    assert rules['seo.viewport_width']['status'] == 'pass'


def test_robots_restrictions_are_observed_without_assuming_publisher_intent():
    headers = CIMultiDict([('X-Robots-Tag', 'otherbot: noindex'), ('X-Robots-Tag', 'googlebot: nofollow')])
    result = analyze_seo(document(head='<meta name="robots" content="nosnippet">'), URL, headers=headers)
    rules = by_id(result)
    assert rules['robots.noindex']['status'] == 'pass'
    assert rules['robots.nofollow']['status'] == 'informational'
    assert rules['robots.nosnippet']['status'] == 'informational'
    assert result['score'] == 100


def test_repeated_heading_failures_are_one_rule_penalty_with_all_evidence():
    result = analyze_seo(document(body='<h1></h1><h2></h2><h4>Later</h4>'), URL)
    empty = by_id(result)['headings.empty']
    assert len(empty['evidence']['findings']) == 2
    assert result['score'] == 93
    assert by_id(result)['headings.skipped_level']['status'] == 'informational'


def test_filename_extensions_do_not_claim_image_optimization_was_measured():
    result = analyze_seo(document(body='<h1>Example</h1><img src="/image.png" alt="">'), URL)
    assert result['data']['images']['non_optimized'] is None
    assert result['data']['images']['non_modern_filename_references'] == 1
    assert by_id(result)['images.missing_dimensions']['status'] == 'informational'
