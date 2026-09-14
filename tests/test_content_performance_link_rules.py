"""Rule identities, evidence, coverage, and advisory boundaries of static checks."""

import json

import pytest
from bs4 import BeautifulSoup

from tfq0seo.analyzers import content, links, performance
from tfq0seo.rules import get_rule, recommendations_for, score_findings


URL = 'https://example.test/page/'


def document(body='<h1>A useful page</h1>', head='', lang='en'):
    return BeautifulSoup(f'<!doctype html><html lang="{lang}"><head>{head}</head><body>{body}</body></html>', 'html.parser')


def outcomes(result):
    return {item['rule_id']: item for item in result['rule_results']}


def assert_registered(item):
    rule = get_rule(item['rule_id'])
    assert item['fix'] == rule.recommendation
    assert item['owner'] == rule.owner
    assert item['references'] == list(rule.references)
    assert item['reviewed_on'] == '2026-09-14'
    assert isinstance(item['evidence'], (dict, list))
    assert item['rule_applicability']
    assert item['applicability'] in ('applicable', 'not_applicable', 'unknown')
    if item['status'] in ('unknown', 'not_applicable', 'error'):
        assert item['reason']
        assert item['penalty'] == 0
    json.dumps(item, allow_nan=False)


@pytest.mark.parametrize('module,rule_id', [
    (content, 'content.repeated_sentences'),
    (performance, 'performance.blocking_scripts'),
    (links, 'links.broken'),
])
def test_registry_guidance_and_scoring_do_not_depend_on_message(module, rule_id):
    first = module.create_issue('Changed category', 'notice', 'CSS image keyword cache readability',
                                rule_id=rule_id, evidence={'observed': True})
    second = module.create_issue('Changed category', 'critical', 'Entirely different wording',
                                 rule_id=rule_id, evidence={'observed': True})
    for item in (first, second):
        assert_registered(item)
    assert first['fix'] == second['fix']
    assert first['severity'] == second['severity']
    assert score_findings([first]) == score_findings([second])
    assert recommendations_for([first, second]) == [get_rule(rule_id).recommendation]


@pytest.mark.parametrize('analyzer', [content.analyze_content, performance.analyze_performance, links.analyze_links])
def test_active_findings_and_coverage_preserve_structured_provenance(analyzer):
    soup = document('<h1></h1><h3>Details</h3><img src="/picture.png"><a href="/next/"></a>',
                    '<script src="/app.js"></script>')
    before = str(soup)
    result = analyzer(soup, URL)
    assert result['rule_results']
    for item in result['rule_results']:
        assert_registered(item)
    assert result['issues'] == [item for item in result['rule_results'] if item['status'] in ('fail', 'informational')]
    assert result['score'] == score_findings(result['issues'])
    assert sum(result['rule_coverage']['counts'].values()) == result['rule_coverage']['total']
    assert str(soup) == before
    json.dumps(result, allow_nan=False)


def test_content_editorial_matches_are_advisory_with_evidence():
    sentence = 'This is an intentionally repeated sentence for our example'
    body = ('<h1>Example content overview</h1><h1>Example content overview</h1>'
            '<p>Lorem ipsum. It was prepared by an editor. Historical dates: 1999 2004 2010.</p>'
            + ''.join(f'<section>Small useful section {number}.</section>' for number in range(4))
            + f'<p>{sentence}. {sentence}.</p>')
    result = content.analyze_content(document(body), URL, ['unrelated'])
    findings = outcomes(result)
    for rule_id in ('content.placeholder_content', 'content.similar_h1', 'content.short_sections',
                    'content.historical_years', 'content.repeated_sentences', 'content.target_keywords_headings'):
        assert findings[rule_id]['status'] == 'informational'
        assert findings[rule_id]['penalty'] == 0
        assert findings[rule_id]['evidence']
    assert result['score'] == 100
    assert findings['content.placeholder_content']['evidence']['matched_phrases'] == ['lorem ipsum']
    assert findings['content.repeated_sentences']['evidence']['sentences'][0]['count'] == 2


def test_content_helper_retains_legacy_types_with_registered_rules():
    soup = document('<h1>Overview</h1><p>It was prepared by a person. It was prepared by another person.</p>')
    found = content.detect_content_issues(content.extract_text_content(soup), soup)
    passive = next(item for item in found if item['rule_id'] == 'content.passive_voice')
    assert passive['type'] == 'passive_voice'
    assert passive['status'] == 'informational'
    assert passive['evidence']['sentence_count'] == 2
    assert_registered(passive)


@pytest.mark.parametrize('fre,grade,expected', [(49, 13, 'informational'), (50, 12, 'pass')])
def test_readability_thresholds_are_explicit_and_unscored(monkeypatch, fre, grade, expected):
    monkeypatch.setattr(content, 'calculate_advanced_readability', lambda *args: {'flesch_reading_ease': fre, 'consensus_grade': grade})
    result = content.analyze_content(document('<h1>Overview</h1><p>' + 'word ' * 100 + '</p>'), URL)
    found = outcomes(result)
    for rule_id in ('content.readability_difficult', 'content.readability_grade'):
        assert found[rule_id]['status'] == expected
        assert found[rule_id]['evidence']['value'] is not None
    assert result['score'] == 100


def test_unavailable_readability_does_not_become_passing_or_penalized(monkeypatch):
    monkeypatch.setattr(content, 'calculate_advanced_readability', lambda *args: {'error': 'metric unavailable'})
    result = content.analyze_content(document('<h1>Overview</h1><p>' + 'word ' * 100 + '</p>'), URL)
    found = outcomes(result)
    assert found['content.readability_difficult']['status'] == 'unknown'
    assert found['content.readability_grade']['status'] == 'unknown'
    assert found['content.readability_difficult']['evidence']['error'] == 'metric unavailable'
    assert result['score'] == 100
    assert result['rule_coverage']['counts']['unknown'] == 2


def test_language_and_missing_target_keywords_control_applicability():
    result = content.analyze_content(document('<h1>日本語</h1><section>内容です。</section>', lang='ja'), URL)
    found = outcomes(result)
    for rule_id in ('content.readability_difficult', 'content.readability_grade', 'content.passive_voice',
                    'content.short_sections', 'content.target_keywords_headings'):
        assert found[rule_id]['status'] == 'not_applicable'
    assert result['data']['metrics']['word_count'] is None
    assert result['score'] == 100


def test_shared_heading_identity_does_not_parse_message_text(monkeypatch):
    soup = document('<h1></h1><h3>Details</h3><img src="/one.png"><img src="/two.png">')
    before = content.analyze_content(soup, URL)
    original = content.heading_facts

    def renamed_facts(soup):
        facts = original(soup)
        facts['issues'] = ['Translated text'] * len(facts['issues'])
        for item in facts['findings']:
            item['message'] = 'Translated text'
        return facts

    monkeypatch.setattr(content, 'heading_facts', renamed_facts)
    after = content.analyze_content(soup, URL)
    assert after['score'] == before['score'] == 86
    assert set(outcomes(after)) == set(outcomes(before))
    assert after['recommendations'] == before['recommendations']


@pytest.mark.parametrize('script_type', ['application/ld+json', 'application/json', 'importmap', 'speculationrules', 'module', ' MODULE ', ' ', 'text/javascript; charset=utf-8'])
def test_data_blocks_and_modules_are_not_classic_parser_blockers(script_type):
    result = performance.analyze_performance(document(head=f'<script type="{script_type}" src="/data"></script>'), URL)
    assert outcomes(result)['performance.blocking_scripts']['status'] == 'pass'
    assert result['data']['javascript_optimization']['render_blocking'] == 0
    assert result['score'] == 100


@pytest.mark.parametrize('attributes', ['type="text/javascript1.5"', 'type="application/x-ecmascript"',
                                       'type=" TEXT/X-JAVASCRIPT "', 'language="JavaScript"', 'type=""'])
def test_classic_javascript_mime_aliases_keep_their_parser_blocking_evidence(attributes):
    result = performance.analyze_performance(document(head=f'<script {attributes} src="/app.js"></script>'), URL)
    assert outcomes(result)['performance.blocking_scripts']['status'] == 'fail'


def test_blocking_script_rule_records_static_evidence_without_invented_metrics():
    result = performance.analyze_performance(document(head='<script src="/app.js"></script>'), URL, 1.5, 1000)
    finding = outcomes(result)['performance.blocking_scripts']
    assert finding['status'] == 'fail'
    assert finding['evidence']['urls'] == ['/app.js']
    assert finding['evidence']['browser_timing_measured'] is False
    assert result['score'] == 93
    assert result['data']['metrics']['html_fetch_time'] == 1.5
    assert result['data']['metrics']['lcp'] is None
    assert result['data']['metrics']['inp'] is None
    assert result['data']['metrics']['cls'] is None


def test_performance_legacy_observations_have_structured_advisory_findings():
    body = '<h1>Overview</h1><img src="/image.png">' + '<span style="color:red">Text</span>' * 21
    head = ('<script defer src="/jquery.one.js"></script><script defer src="/jquery.two.js"></script>'
            '<script>document.write("example");' + '/*padding*/' * 100 + '</script>')
    result = performance.analyze_performance(document(body, head), URL)
    for key in ('image_optimization', 'performance_patterns'):
        assert result['data'][key]['findings']
        for item in result['data'][key]['findings']:
            assert_registered(item)
            assert item['status'] == 'informational'
    assert result['data']['image_optimization']['issues']
    assert result['data']['performance_patterns']['bad_patterns']
    assert result['score'] == 100


@pytest.mark.parametrize('markup', [
    '<a href="/next" aria-label="Next page"></a>',
    '<a href="/next"><img alt="Next page" src="/arrow.png"></a>',
    '<a href="/next" title="Next page"></a>',
    '<span id="label">Next page</span><a href="/next" aria-labelledby="label"></a>',
])
def test_link_accessible_name_fallbacks_avoid_false_findings(markup):
    result = links.analyze_links(document(markup), URL)
    assert outcomes(result)['links.missing_anchor']['status'] == 'pass'
    assert result['data']['internal_links'][0]['anchor_text'] == 'Next page'


def test_link_checks_include_complete_evidence_and_explicit_successes():
    markup = '<a href="/empty"></a><a href="http://[">Invalid</a><a href="javascript:void(0)">Action</a>'
    result = links.analyze_links(document(markup), URL)
    found = outcomes(result)
    for rule_id in ('links.missing_anchor', 'links.invalid_url', 'links.javascript_url'):
        assert found[rule_id]['status'] == 'fail'
        assert len(found[rule_id]['evidence']['links']) == 1
    assert found['links.broken']['status'] == 'unknown'
    assert result['score'] == 79


@pytest.mark.parametrize('known_failures', [None, set(), {'https://example.test/other'}])
def test_absent_failure_evidence_does_not_imply_healthy_destinations(known_failures):
    result = links.analyze_links(document('<a href="/next">Next</a>'), URL, known_failures)
    finding = outcomes(result)['links.broken']
    assert finding['status'] == 'unknown'
    assert finding['evidence']['unchecked_urls'] == ['https://example.test/next']
    assert finding['penalty'] == 0
    assert result['score'] == 100


def test_broken_link_failure_and_inapplicable_link_health():
    result = links.analyze_links(document('<a href="/next">Next</a><a href="/next">Next again</a>'), URL, {'https://example.test/next'})
    finding = outcomes(result)['links.broken']
    assert finding['status'] == 'fail'
    assert finding['source'] == 'supplied_destination_checks'
    assert finding['evidence']['http_link_count'] == 2
    assert result['score'] == 85
    no_links = links.analyze_links(document(), URL)
    assert outcomes(no_links)['links.broken']['status'] == 'not_applicable'
    assert no_links['score'] == 100


def test_legacy_link_heuristics_retain_types_without_spam_verdicts():
    anchors = links.analyze_anchor_text_distribution(['click here'] * 4 + ['go'] * 6)['issues']
    sample = [{'url': 'https://other.test/partner', 'is_internal': False, 'anchor_text': 'Sponsored partner',
               'context': 'Advertisement', 'rel': [], 'is_hidden': True}] * 6
    schemes = links.detect_link_schemes(sample)
    assert anchors and schemes
    for item in anchors + schemes:
        assert item['type']
        assert_registered(item)
        assert item['status'] == 'informational'
        assert item['penalty'] == 0
    assert score_findings(anchors + schemes) == 100
