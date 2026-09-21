"""Technical rule evidence, applicability, and registry-only scoring regressions."""

import json

import pytest
from bs4 import BeautifulSoup
from multidict import CIMultiDict

from tfq0seo.analyzers.technical import (
    TECHNICAL_RULES, analyze_technical, analyze_mobile_optimization,
    analyze_security_headers, detect_javascript_seo_issues, create_issue,
)
from tfq0seo.rules import get_rule, recommendations_for, score_findings


URL = 'https://example.com/page'


def document(body='<p>Readable page content.</p>', head='', lang='en', viewport='width=device-width',
             doctype='<!DOCTYPE html>'):
    viewport_tag = f'<meta name="viewport" content="{viewport}">' if viewport is not None else ''
    return BeautifulSoup(f'{doctype}<html lang="{lang}"><head><meta charset="utf-8">{viewport_tag}'
                         f'{head}</head><body>{body}</body></html>', 'html.parser')


def evaluate(soup=None, *, headers=None, url=URL, status_code=200):
    result = analyze_technical(soup if soup is not None else document(), url,
                               headers=headers, status_code=status_code)
    return result, {item['rule_id']: item for item in result['rule_results']}


def test_every_active_rule_has_reviewed_metadata_and_structured_results():
    result, rules = evaluate(headers={})
    assert set(TECHNICAL_RULES) <= rules.keys()
    assert len(rules) == len(result['rule_results'])
    assert result['coverage'] == result['rule_coverage']
    assert result['coverage']['total'] == len(rules)
    for item in rules.values():
        definition = get_rule(item['rule_id'])
        assert item['reviewed_on'] == '2026-09-14'
        assert item['references'] == list(definition.references)
        assert isinstance(item['evidence'], (dict, list))
        assert item['fix'] == definition.recommendation
        if item['status'] in ('unknown', 'not_applicable'):
            assert item['reason']
    json.dumps(result, allow_nan=False)


def test_optional_header_policies_do_not_lower_score_or_claim_insecurity():
    result, rules = evaluate(headers={})
    assert result['score'] == 100
    for rule_id in ('security.hsts_missing', 'security.csp_missing', 'security.frame_policy_missing',
                    'technical.http_compression'):
        assert rules[rule_id]['status'] == 'informational'
        assert rules[rule_id]['penalty'] == 0
    assert result['data']['security']['level'] is None
    assert result['data']['security']['level_status'] == 'not_assessed'
    assert result['data']['security']['vulnerabilities'] == []
    assert 'heuristic' in result['data']['security']['header_configuration_level_method']


def test_missing_response_context_is_unknown_instead_of_a_pass_or_failure():
    result, rules = evaluate(headers=None, status_code=0)
    for rule_id in ('security.hsts_missing', 'security.hsts_invalid', 'security.csp_missing',
                    'security.frame_policy_missing', 'security.xfo_invalid',
                    'security.cors_wildcard_credentials', 'technical.http_compression',
                    'technical.http_server_error', 'technical.http_client_error', 'technical.http_redirect',
                    'robots.noindex', 'robots.nofollow', 'robots.nosnippet'):
        assert rules[rule_id]['status'] == 'unknown', rule_id
        assert rules[rule_id]['penalty'] == 0
    assert result['score'] == 100
    assert result['data']['security']['hsts'] is None


@pytest.mark.parametrize('status,rule_id,expected', [
    (503, 'technical.http_server_error', 'fail'), (404, 'technical.http_client_error', 'fail'),
    (302, 'technical.http_redirect', 'informational'), (301, 'technical.http_redirect', 'informational'),
    (307, 'technical.http_redirect', 'informational'), (308, 'technical.http_redirect', 'informational'),
    (304, 'technical.http_redirect', 'pass'), (200, 'technical.http_server_error', 'pass'),
])
def test_status_rules_use_observed_semantics(status, rule_id, expected):
    result, rules = evaluate(headers={}, status_code=status)
    assert rules[rule_id]['status'] == expected
    assert rules[rule_id]['evidence']['status_code'] == status
    if expected == 'informational':
        assert result['score'] == 100
        assert 'consider using 301' not in str(result)


@pytest.mark.parametrize('url,https_status,hsts_status', [
    ('http://example.com/', 'fail', 'not_applicable'),
    ('https://example.com/', 'pass', 'informational'),
    ('http://localhost:8000/', 'not_applicable', 'not_applicable'),
    ('http://127.0.0.1:8000/', 'not_applicable', 'not_applicable'),
    ('http://[::1]:8000/', 'not_applicable', 'not_applicable'),
    ('https://192.0.2.1/', 'pass', 'not_applicable'),
])
def test_transport_policy_scope(url, https_status, hsts_status):
    _, rules = evaluate(headers={}, url=url)
    assert rules['security.https_missing']['status'] == https_status
    assert rules['security.hsts_missing']['status'] == hsts_status


@pytest.mark.parametrize('policy,status', [
    ('max-age=86400', 'pass'), ('max-age=0', 'pass'), ('max-age="3600"', 'pass'),
    ('max-age = 3600 ; includeSubDomains', 'pass'),
    ('max-age="3\\600"; extension="one; max-age=1"', 'pass'),
    ('max-age=31536000; includeSubDomains', 'pass'),
    ('max-age=-1', 'fail'), ('max-age=12abc', 'fail'), ('max-age=1; max-age=2', 'fail'),
    ('notmax-age=3600', 'fail'), ('includeSubDomains', 'fail'),
    ('max-age=3600; includeSubDomains=1', 'fail'),
])
def test_hsts_validation_does_not_impose_one_year_on_every_site(policy, status):
    _, rules = evaluate(headers={'Strict-Transport-Security': policy})
    assert rules['security.hsts_invalid']['status'] == status
    assert rules['security.hsts_preload_incomplete']['status'] == 'not_applicable'
    assert not any('less than recommended' in text for text in analyze_security_headers(
        {'Strict-Transport-Security': policy}).vulnerabilities)


def test_repeated_hsts_fields_use_first_policy_and_preload_is_conditional():
    headers = CIMultiDict([('Strict-Transport-Security', 'max-age=3600'),
                           ('Strict-Transport-Security', 'max-age=-1')])
    _, rules = evaluate(headers=headers)
    assert rules['security.hsts_invalid']['status'] == 'pass'
    assert len(rules['security.hsts_invalid']['evidence']['values']) == 2
    _, partial = evaluate(headers={'Strict-Transport-Security': 'max-age=3600; preload'})
    assert partial['security.hsts_preload_incomplete']['status'] == 'informational'
    _, ready = evaluate(headers={'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload'})
    assert ready['security.hsts_preload_incomplete']['status'] == 'pass'


def test_large_hsts_duration_keeps_evidence_without_integer_conversion_failure():
    policy = 'max-age=' + '9' * 5000 + '; includeSubDomains; preload'
    result, rules = evaluate(headers={'Strict-Transport-Security': policy})
    assert rules['security.hsts_invalid']['status'] == 'pass'
    assert rules['security.hsts_preload_incomplete']['status'] == 'pass'
    assert rules['security.hsts_invalid']['evidence']['values'] == [policy]
    assert result['data']['security']['hsts_max_age'] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('policy,inline,eval_,wildcard', [
    ("default-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'", 'pass', 'pass', 'pass'),
    ("script-src 'unsafe-inline' 'unsafe-eval'; default-src *", 'informational', 'informational', 'informational'),
    ("script-src 'unsafe-inline' 'nonce-YWJjZA=='", 'pass', 'pass', 'pass'),
    ("script-src 'none'; script-src 'unsafe-inline'", 'pass', 'pass', 'pass'),
])
def test_csp_observations_respect_directives_and_do_not_claim_exploitability(policy, inline, eval_, wildcard):
    result, rules = evaluate(headers={'Content-Security-Policy': policy})
    assert rules['security.csp_unsafe_inline']['status'] == inline
    assert rules['security.csp_unsafe_eval']['status'] == eval_
    assert rules['security.csp_wildcard_default']['status'] == wildcard
    assert result['score'] == 100
    for item in result['issues']:
        assert item['penalty'] == 0


def test_separate_csp_policies_keep_provenance_and_frame_ancestors_alternative():
    headers = CIMultiDict([('Content-Security-Policy', "script-src 'unsafe-inline'"),
                           ('Content-Security-Policy', "script-src 'none'; frame-ancestors 'none'")])
    _, rules = evaluate(headers=headers)
    evidence = rules['security.csp_unsafe_inline']['evidence']
    assert len(evidence['policies']) == 2
    assert evidence['effective_browser_policy_checked'] is False
    assert rules['security.frame_policy_missing']['status'] == 'pass'


def test_meta_csp_is_observed_but_cannot_supply_frame_ancestors():
    soup = document(head='<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; frame-ancestors \'none\'">')
    _, rules = evaluate(soup, headers={})
    assert rules['security.csp_missing']['status'] == 'pass'
    assert rules['security.frame_policy_missing']['status'] == 'informational'


@pytest.mark.parametrize('value,status', [(' deny ', 'pass'), ('SAMEORIGIN', 'pass'),
                                         ('DENY,DENY', 'pass'), ('DENY,SAMEORIGIN', 'fail'),
                                         ('ALLOW-FROM https://example.com', 'fail'), ('invalid', 'fail')])
def test_configured_xfo_validation(value, status):
    _, rules = evaluate(headers={'X-Frame-Options': value})
    assert rules['security.xfo_invalid']['status'] == status


@pytest.mark.parametrize('origin,credentials,status', [('*', 'true', 'fail'), ('*', 'false', 'pass'),
                                                        ('*', 'TRUE', 'pass'), ('https://example.com', 'true', 'pass')])
def test_cors_wildcard_means_incompatible_credentials_not_data_exposure(origin, credentials, status):
    _, rules = evaluate(headers={'Access-Control-Allow-Origin': origin,
                                 'Access-Control-Allow-Credentials': credentials})
    item = rules['security.cors_wildcard_credentials']
    assert item['status'] == status
    assert item['evidence']['credentialed_request_tested'] is False
    assert 'expos' not in item['message']


@pytest.mark.parametrize('viewport,missing,zoom', [
    (None, 'fail', 'not_applicable'), ('  ', 'fail', 'not_applicable'),
    ('width=device-width', 'pass', 'pass'), ('user-scalable = NO', 'pass', 'fail'),
    ('user-scalable=0', 'pass', 'fail'), ('maximum-scale = 1.5', 'pass', 'fail'),
    ('maximum-scale=2', 'pass', 'pass'), ('maximum-scale=10', 'pass', 'pass'),
    ('maximum-scale=nan', 'pass', 'pass'), ('maximum-scale=invalid', 'pass', 'pass'),
])
def test_viewport_rules_use_authored_values_and_zoom_boundary(viewport, missing, zoom):
    _, rules = evaluate(document(viewport=viewport), headers={})
    assert rules['mobile.viewport_missing']['status'] == missing
    assert rules['mobile.viewport_zoom_disabled']['status'] == zoom


def test_markup_does_not_prove_layout_plugins_pwa_or_javascript_execution():
    soup = document('<div id="root"></div><table width="4000"><tr><td>Text</td></tr></table>'
                    '<object data="/picture.svg" type="image/svg+xml"></object>'
                    '<p style="font-size: 8px">Text</p><script>/* location.href = "/next"; */</script>',
                    head='<link rel="manifest" href="/manifest.json"><script>navigator.serviceWorker</script>')
    result, rules = evaluate(soup, headers={})
    assert result['data']['mobile']['readiness'] is None
    assert result['data']['mobile']['pwa_ready'] is None
    profile = analyze_mobile_optimization(soup)
    assert profile.uses_plugins is False
    assert profile.horizontal_scrolling is None
    assert profile.text_readability is None
    assert result['data']['javascript_seo']['spa_detected'] is None
    assert rules['technical.javascript_redirect_reference']['status'] == 'informational'
    assert rules['technical.javascript_redirect_reference']['evidence']['executed'] is None
    assert detect_javascript_seo_issues(soup)['recommendations'] == []
    assert result['score'] == 100


def test_url_name_advice_preserves_query_semantics_and_omits_session_values():
    result, rules = evaluate(url=URL + '?SID=private-token&sid=&a=1&a=2', headers={})
    item = rules['technical.url_session_parameter']
    assert item['status'] == 'informational'
    assert item['evidence']['parameter_names'] == ['SID', 'sid']
    assert 'private-token' not in json.dumps(item)
    assert result['data']['url']['parameters'] == 3
    assert result['score'] == 100


@pytest.mark.parametrize('lang,status', [('en', 'pass'), ('fr-CA', 'pass'), ('  ', 'fail')])
def test_language_declaration_has_explicit_evidence(lang, status):
    _, rules = evaluate(document(lang=lang), headers={})
    assert rules['language.missing']['status'] == status


def test_charset_prefers_transport_declaration_and_uses_shared_advisory_rule():
    result, rules = evaluate(headers={'Content-Type': 'text/html; charset="windows-1252"'})
    assert result['data']['international']['charset'] == 'windows-1252'
    assert rules['seo.charset_non_utf8']['status'] == 'informational'
    assert rules['seo.charset_non_utf8']['owner'] == 'seo'
    assert result['score'] == 100


def test_mixed_resource_references_use_document_base_without_claiming_network_requests():
    soup = document('<img src="picture.jpg"><a href="http://other.example/">Link</a>',
                    head='<base href="http://assets.example/a/"><link rel="canonical" href="http://example.com/a">')
    _, rules = evaluate(soup, headers={})
    item = rules['technical.http_resource_reference']
    assert item['status'] == 'informational'
    assert item['evidence']['count'] == 1
    assert item['evidence']['references'][0]['url'] == 'http://assets.example/a/picture.jpg'
    assert item['evidence']['effective_requests_checked'] is False


def test_obsolete_elements_are_advisory_and_doctype_is_syntax_specific():
    result, rules = evaluate(document('<center><font>Text</font></center>',
                                      doctype='<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">'), headers={})
    assert rules['technical.deprecated_elements']['status'] == 'informational'
    assert rules['html.doctype_legacy']['status'] == 'informational'
    assert result['score'] == 100
    _, xml_rules = evaluate(document(doctype=''), headers={'Content-Type': 'application/xhtml+xml'})
    assert xml_rules['html.doctype_missing']['status'] == 'not_applicable'
    _, missing = evaluate(document(doctype='<!-- <!DOCTYPE html> -->'), headers={})
    assert missing['html.doctype_missing']['status'] == 'fail'


def test_non_html_response_does_not_acquire_html_failures():
    _, rules = evaluate(BeautifulSoup('<p>JSON-looking content</p>', 'html.parser'),
                        headers={'Content-Type': 'application/json'})
    for rule_id in ('html.doctype_missing', 'mobile.viewport_missing', 'language.missing',
                    'technical.http_compression', 'security.csp_missing'):
        assert rules[rule_id]['status'] == 'not_applicable'


def test_scoring_and_guidance_are_only_registry_based_and_input_is_unchanged():
    soup = document('<p>Text</p>', lang='', viewport=None, doctype='')
    before = str(soup)
    result, _ = evaluate(soup, url='http://example.com/', headers={'X-Frame-Options': 'invalid'}, status_code=503)
    assert str(soup) == before
    assert result['score'] == score_findings(result['issues'], owner='technical')
    assert result['recommendations'] == recommendations_for(result['issues'])
    assert result['data']['recommendations'] == result['recommendations']
    # Changing words cannot choose advice or severity through a substring match.
    first = create_issue('Anything', 'notice', 'cache mobile security protocol URL',
                         rule_id='html.doctype_missing', evidence={'doctype': None})
    second = create_issue('Anything', 'critical', 'Completely different words',
                          rule_id='html.doctype_missing', evidence={'doctype': None})
    assert first['fix'] == second['fix'] == get_rule('html.doctype_missing').recommendation
    assert first['severity'] == second['severity'] == 'warning'
    json.dumps(result, allow_nan=False)
