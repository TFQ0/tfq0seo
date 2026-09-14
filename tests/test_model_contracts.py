"""Live contracts reject malformed observations before scoring or aggregation."""

import asyncio
import copy
import json

import pytest
from bs4 import BeautifulSoup
from multidict import CIMultiDict

from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.core.crawler import Crawler
from tfq0seo.core.models import (ContractError, PageFacts, normalize_fetch_result,
                                 validate_analyzer_result, validate_json_value,
                                 validate_rule_result)
from tfq0seo.rules import RuleCollector, merge_rule_results, rule_result


def raw_page(**overrides):
    return {'url': 'https://example.test/', 'status_code': 200,
            'soup': BeautifulSoup('<html lang="en"><title>Fixture</title><h1>Fixture</h1></html>', 'html.parser'),
            **overrides}


def only_seo():
    return SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['seo'], 'score_weights': {'seo': 1}}}))


@pytest.mark.parametrize(('field', 'value'), [
    ('url', None), ('status_code', '200'), ('status_code', True), ('status_code', 99),
    ('status_code', 600), ('headers', []), ('headers', {'X-Test': 7}),
    ('headers', {'X-Test': ['one', None]}), ('load_time', float('nan')),
    ('load_time', -1), ('timings', {'total_seconds': float('inf')}), ('timings', None),
    ('content_length', 1.5), ('truncated', 'false'), ('depth', -1),
    ('soup', '<p>Unparsed</p>'), ('redirect_chain', ['https://example.test/old']),
    ('redirect_chain', [{'url': 'https://example.test/old', 'status_code': 200, 'location': '/'}]),
    ('outcome', 'unknown'), ('extra', object()),
])
def test_invalid_fetch_fields_fail_with_a_path_before_any_analysis(field, value):
    analyzer = only_seo()
    with pytest.raises(ContractError) as error:
        asyncio.run(analyzer.analyze_page(raw_page(**{field: value})))
    assert error.value.path.startswith('$.fetch.' + field)
    assert analyzer.stats.successful_analyses == 0
    assert not analyzer.cache.cache


def test_fetch_normalization_preserves_unavailable_and_repeated_observations():
    headers = CIMultiDict([('Content-Security-Policy', "default-src 'self'"),
                           ('content-security-policy', "script-src 'none'")])
    raw = raw_page(headers=headers, load_time=None, timings={'network_seconds': 0.2, 'headers_seconds': None},
                   redirect_chain=[{'url': 'https://example.test/old', 'status_code': 301,
                                    'location': 'https://example.test/'}], extra={'retained': [1]})
    value = normalize_fetch_result(raw)
    assert value['soup'] is raw['soup']
    assert value['load_time'] is None
    assert value['timings'] == raw['timings']
    assert value['headers']['Content-Security-Policy'] == ["default-src 'self'", "script-src 'none'"]
    value['redirect_chain'][0]['location'] = '/changed'
    value['extra']['retained'].append(2)
    assert raw['redirect_chain'][0]['location'] == 'https://example.test/'
    assert raw['extra']['retained'] == [1]
    assert normalize_fetch_result(raw_page())['headers'] is None
    assert normalize_fetch_result(raw_page(headers={}))['headers'] == {}


def test_crawler_preserves_every_header_instance_without_duplicate_case_keys():
    headers = CIMultiDict([('Content-Security-Policy', "default-src 'self'"),
                           ('content-security-policy', "script-src 'none'"),
                           ('X-Robots-Tag', 'noindex'), ('x-robots-tag', 'nofollow'),
                           ('Content-Type', 'text/html')])
    result = Crawler._response_headers(headers)
    assert len(result) == 3
    assert result['Content-Security-Policy'] == ["default-src 'self'", "script-src 'none'"]
    assert result['X-Robots-Tag'] == ['noindex', 'nofollow']
    assert result['Content-Type'] == 'text/html'


def test_transport_failure_keeps_headers_unavailable_and_has_no_dom():
    failure = Crawler({})._failure('https://example.test/', 'Connection unavailable')
    normalized = normalize_fetch_result(failure)
    assert normalized['headers'] is None
    assert normalized['load_time'] is None
    assert normalized['status_code'] == 0
    assert 'soup' not in normalized


@pytest.mark.parametrize(('outcome', 'expected'), [('failed', 'error'), ('skipped', 'skipped')])
def test_fetch_outcome_cannot_be_promoted_to_a_successful_analysis(outcome, expected):
    result = asyncio.run(only_seo().analyze_page(raw_page(outcome=outcome)))
    assert result['status'] == expected
    assert result['overall_score'] is None
    assert 'seo' not in result
    assert result.get('error') or result.get('reason')


def test_contradictory_fetch_outcomes_are_rejected():
    with pytest.raises(ContractError, match='outcome'):
        normalize_fetch_result(raw_page(outcome='success', error='failed'))
    with pytest.raises(ContractError, match='outcome'):
        normalize_fetch_result(raw_page(outcome='failed', skipped=True))


@pytest.mark.parametrize(('field', 'value'), [
    ('evidence', None), ('source', ''), ('confidence', 'guessed'), ('references', []),
    ('reviewed_on', 'yesterday'), ('applicability', 'unknown'), ('owner', 'seo'),
    ('severity', 'critical'), ('penalty', -1), ('reported_by', ['missing']),
    ('details', {'timing': float('nan')}), ('observations', [{'status': 'pass', 'evidence': None}]),
])
def test_complete_rule_contract_rejects_invalid_metadata_and_nested_values(field, value):
    rule = rule_result('images.missing_alt', {'images': ['/photo.png']})
    rule[field] = value
    with pytest.raises(ContractError):
        validate_rule_result(rule)
    with pytest.raises(ContractError):
        merge_rule_results([rule])


def test_rule_builder_validates_details_and_measurement_source():
    with pytest.raises(ContractError, match='details'):
        rule_result('images.missing_alt', {}, details={'unsupported': object()})
    with pytest.raises(ContractError, match='source'):
        rule_result('images.missing_alt', {}, source='')


@pytest.mark.parametrize('invalid', [
    {'score': 100, 'issues': [None]}, {'score': 100, 'issues': [], 'data': None},
    {'score': 100, 'issues': [], 'data': {'metric': float('inf')}},
    {'score': 100, 'issues': [], 'rule_results': [{'rule_id': 'images.missing_alt', 'status': 'fail'}]},
])
def test_bad_analyzer_output_is_an_explicit_uncached_error(monkeypatch, invalid):
    monkeypatch.setattr('tfq0seo.core.app.analyze_seo', lambda *args, **kwargs: copy.deepcopy(invalid))
    analyzer = only_seo()
    result = asyncio.run(analyzer.analyze_page(raw_page()))
    assert result['status'] == 'error'
    assert result['seo']['score'] is None
    assert result['overall_score'] is None
    assert result['coverage']['failed_analyzers'] == ['seo']
    assert '$.seo' in result['analyzer_errors']['seo']
    assert not analyzer.cache.cache


def test_missing_headers_remain_unknown_in_rule_evidence():
    analyzer = only_seo()
    result = asyncio.run(analyzer.analyze_page(raw_page()))
    rule = next(item for item in result['rule_results'] if item['rule_id'] == 'robots.noindex')
    assert rule['status'] == 'unknown'
    assert rule['evidence']['headers_checked'] is False
    assert result['page_facts']['headers_observed'] is False


def test_valid_rule_and_analyzer_contract_round_trip():
    collector = RuleCollector('content')
    collector.check('images.missing_alt', None, {'images': None}, reason='Image extraction unavailable')
    result = {'score': 100, 'issues': collector.issues, 'rule_results': collector.results, 'data': {}}
    assert validate_analyzer_result(result) is result
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert PageFacts.__name__ == 'PageFacts'


def test_json_validation_rejects_cycles_without_rejecting_shared_values():
    shared = {'value': [1, None]}
    assert validate_json_value([shared, shared]) == [shared, shared]
    shared['cycle'] = shared
    with pytest.raises(ContractError, match='circular'):
        validate_json_value(shared)


def test_archived_rules_retain_recorded_guidance_and_scores_during_aggregation():
    async def run():
        analyzer = SEOAnalyzer(Config())
        page = await analyzer.analyze_page(raw_page(headers={}))
        page['scoring']['ruleset_version'] = 'archived-policy'
        for collection in [page['rule_results'], page['issues'], page['links']['rule_results']]:
            for item in collection:
                item['rule_version'] = 'archived-policy'
        issue = rule_result('images.missing_alt', {'images': ['/photo.png']})
        issue.update(rule_id='archived.removed_rule', rule_version='archived-policy', fix='Recorded archive advice')
        page['issues'] = [issue]
        recorded_score = page['overall_score']
        report = analyzer.generate_site_report([page])
        assert report['scores']['overall'] == recorded_score
        assert report['pages']['detailed'][0]['issues'] == [issue]
        assert report['recommendations']['specific'][0]['description'] == 'Recorded archive advice'
        assert report['scoring']['version'] == 'legacy_or_mixed'
    asyncio.run(run())


def test_different_rule_versions_keep_separate_evidence_groups():
    from tfq0seo.core.report_optimizer import aggregate_issues
    first = rule_result('images.missing_alt', {'images': ['/first.png']})
    second = dict(first, rule_version='archived', evidence={'images': ['/second.png']})
    groups, _ = aggregate_issues([first, second])
    assert len(groups) == 2
    assert groups[0]['evidence'] != groups[1]['evidence']


def test_site_aggregation_rejects_missing_identity_and_summary_only_findings():
    with pytest.raises(ContractError) as error:
        only_seo().generate_site_report([{}])
    assert error.value.path == '$.pages[0].url'
    with pytest.raises(ContractError) as error:
        only_seo().generate_site_report([{'url': 'https://example.test/', 'issues': {'warning': 2}}])
    assert error.value.path == '$.pages[0].issues'


def test_archived_null_http_status_stays_unavailable_during_aggregation():
    report = only_seo().generate_site_report([{'url': 'https://example.test/', 'status_code': None,
                                              'overall_score': 95, 'issues': []}])
    assert report['pages']['detailed'][0]['status_code'] is None
    assert report['performance_metrics']['status_codes'] == {0: 1}
    assert report['technical_health']['broken_links'] == []


def test_facts_version_invalidates_analysis_cache(monkeypatch):
    async def run():
        analyzer = only_seo()
        raw = raw_page()
        await analyzer.analyze_page(raw)
        assert (await analyzer.analyze_page(raw)).get('cached')
        monkeypatch.setattr('tfq0seo.core.app.FACTS_VERSION', 'next-facts')
        assert not (await analyzer.analyze_page(raw)).get('cached')
    asyncio.run(run())


@pytest.mark.parametrize('change', ['missing_evaluation', 'missing_issue', 'legacy_issue', 'missing_error'])
def test_inconsistent_live_results_never_disappear_into_success(monkeypatch, change):
    rule = rule_result('images.missing_alt', {'images': ['/photo.png']})
    invalid = {'score': 93, 'issues': [rule], 'rule_results': [rule], 'data': {}}
    if change == 'missing_evaluation':
        invalid['rule_results'] = []
    elif change == 'missing_issue':
        invalid['issues'] = []
    elif change == 'legacy_issue':
        invalid['issues'] = [{'message': 'A legacy finding', 'category': 'SEO', 'severity': 'warning'}]
        invalid['rule_results'] = []
    else:
        invalid = {'status': 'error', 'score': None, 'issues': [], 'data': {}}
    monkeypatch.setattr('tfq0seo.core.app.analyze_seo', lambda *args, **kwargs: invalid)
    page = asyncio.run(only_seo().analyze_page(raw_page()))
    assert page['status'] == 'error'
    assert page['overall_score'] is None
    assert page['seo']['error']


@pytest.mark.parametrize(('field', 'value'), [
    ('penalty', 999), ('fix', 'Unregistered advice'), ('references', ['unreviewed reference']),
    ('rule_version', 'outdated'), ('reviewed_on', '2020-01-01'),
    ('rule_applicability', 'All websites'),
])
def test_live_registry_metadata_cannot_be_replaced(field, value):
    rule = rule_result('images.missing_alt', {})
    rule[field] = value
    with pytest.raises(ContractError) as error:
        validate_rule_result(rule)
    assert error.value.path == '$.' + field


@pytest.mark.parametrize('changes', [
    {'status': 'pass', 'applicability': 'not_applicable'}, {'reported_by': 7},
    {'reported_by': ['unknown_analyzer']}, {'status': 'error', 'reason': ''},
])
def test_nested_observations_obey_the_outcome_contract(changes):
    rule = merge_rule_results([rule_result('images.missing_alt', {})])[0]
    rule['observations'][0].update(changes)
    with pytest.raises(ContractError) as error:
        validate_rule_result(rule)
    assert error.value.path.startswith('$.observations[0].')


@pytest.mark.parametrize('parallel', [False, True])
def test_application_extracts_one_snapshot_for_all_five_analyzers(monkeypatch, parallel):
    import tfq0seo.core.app as app
    import tfq0seo.page_facts as extraction
    calls, snapshots = [], []
    original = extraction.extract_page_facts

    def extract(*args, **kwargs):
        calls.append(args[1])
        return original(*args, **kwargs)

    monkeypatch.setattr(app, 'extract_page_facts', extract)
    monkeypatch.setattr(extraction, 'extract_page_facts', extract)
    for name in ('seo', 'content', 'technical', 'performance', 'links'):
        analyze = getattr(app, 'analyze_' + name)

        def observe(*args, _analyze=analyze, **kwargs):
            snapshots.append(kwargs['facts'])
            return _analyze(*args, **kwargs)

        monkeypatch.setattr(app, 'analyze_' + name, observe)
    analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'parallel_analysis': parallel}}))
    page = asyncio.run(analyzer.analyze_page(raw_page(headers={})))
    assert not page['analyzer_errors']
    assert calls == [page['url']]
    assert len(snapshots) == 5
    assert all(snapshot is snapshots[0] for snapshot in snapshots)
    json.dumps(page, allow_nan=False)
