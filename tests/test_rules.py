"""Behavioral guarantees for reviewed rules and shared scoring."""

import asyncio
import copy
import dataclasses
from datetime import date

import pytest
from bs4 import BeautifulSoup

from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.core.report_optimizer import aggregate_issues, generate_specific_recommendations
from tfq0seo.rules import (RULES, RuleCollector, get_rule, register_rules, rule_result,
                           merge_rule_results, rule_coverage, score_findings, recommendations_for)


def test_registered_rules_have_reviewed_metadata():
    for rule_id, definition in RULES.items():
        assert rule_id == definition.rule_id
        assert definition.applicability and definition.recommendation
        assert definition.references and all(reference.startswith('https://') for reference in definition.references)
        assert date.fromisoformat(definition.reviewed_on) <= date.today()
    with pytest.raises(TypeError):
        RULES['new.rule'] = get_rule('headings.empty')
    with pytest.raises(dataclasses.FrozenInstanceError):
        get_rule('headings.empty').severity = 'notice'


def test_conflicting_registration_is_atomic():
    original = dict(RULES)
    with pytest.raises(ValueError, match='Conflicting'):
        register_rules([dataclasses.replace(get_rule('headings.empty'), rule_id='test.atomic'),
                        dataclasses.replace(get_rule('headings.empty'), severity='critical')])
    assert dict(RULES) == original


@pytest.mark.parametrize('failed,applicable,expected', [
    (True, True, 'fail'), (False, True, 'pass'), (None, True, 'unknown'),
    (True, None, 'unknown'), (True, False, 'not_applicable'),
])
def test_applicability_and_observation_control_status(failed, applicable, expected):
    collector = RuleCollector('content')
    result = collector.check('headings.empty', failed, {'text': ''}, applicable=applicable,
                             reason='Fixture provides context for unavailable or inapplicable checks.')
    assert result['status'] == expected
    assert score_findings(collector.issues) == (93 if expected == 'fail' else 100)


def test_errors_and_advisories_do_not_penalize_a_site():
    collector = RuleCollector('seo')
    collector.check('robots.noindex', True, {'directives': ['noindex']})
    collector.check('headings.empty', None, {'text': None}, status='error', reason='Fixture extraction error')
    assert collector.issues[0]['status'] == 'informational'
    assert collector.coverage['counts']['error'] == 1
    assert score_findings(collector.results) == 100


@pytest.mark.parametrize('evidence', [None, 'message only', {'duration': float('nan')}, {'element': object()}])
def test_nonportable_or_unstructured_evidence_is_rejected(evidence):
    with pytest.raises((ValueError, TypeError)):
        rule_result('headings.empty', evidence)


def test_unknown_results_need_an_explanation():
    with pytest.raises(ValueError, match='explanation'):
        rule_result('headings.empty', {}, status='unknown')
    with pytest.raises(ValueError, match='Unregistered'):
        rule_result('unknown.rule', {'text': ''})


def test_message_changes_cannot_change_fix_severity_or_score():
    first = rule_result('headings.empty', {'text': ''}, message='Missing title or cache or font')
    second = rule_result('headings.empty', {'text': ''}, message='Translated description of the same finding')
    assert first['fix'] == second['fix'] == get_rule('headings.empty').recommendation
    assert score_findings([first]) == score_findings([second]) == 93
    assert recommendations_for([first, second]) == [first['fix']]


def test_duplicate_rule_evidence_is_retained_with_one_penalty():
    seo = RuleCollector('seo')
    content = RuleCollector('content')
    seo.check('headings.empty', True, {'positions': [0]})
    content.check('headings.empty', True, {'positions': [0, 3]})
    results = seo.results + content.results
    merged = merge_rule_results(results)
    assert len(merged) == 1 and len(merged[0]['observations']) == 2
    assert merged[0]['reported_by'] == ['content', 'seo']
    assert score_findings(results) == 93
    assert rule_coverage(results)['counts']['fail'] == 1
    assert merge_rule_results(merged) == merged


def synthetic_categories():
    result = {}
    for name in ('seo', 'content'):
        collector = RuleCollector(name)
        collector.check('images.missing_alt', True, {'urls': ['/image.png']})
        result[name] = {'score': score_findings(collector.issues), 'issues': collector.issues,
                        'rule_results': collector.results}
    return result


def test_category_ownership_prevents_cross_category_penalties():
    analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'score_weights': {'seo': 0.5, 'content': 0.5}}}))
    result = synthetic_categories()
    analyzer._apply_rule_scoring(result)
    assert result['seo']['score'] == 100
    assert result['content']['score'] == 93
    assert analyzer._calculate_weighted_score(result) == 96.5
    assert len(result['scoring']['deductions']) == 1
    assert result['scoring']['deductions'][0]['score_owner'] == 'content'
    snapshot = copy.deepcopy(result)
    analyzer._apply_rule_scoring(result)
    assert result == snapshot


def test_disabled_owner_uses_one_observer_and_zero_weights_are_respected():
    analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'score_weights': {'seo': 1.0, 'content': 0.0}}}))
    result = synthetic_categories()
    analyzer._apply_rule_scoring(result)
    assert analyzer._calculate_weighted_score(result) == 100
    del result['content']
    analyzer._apply_rule_scoring(result)
    assert result['seo']['score'] == 93
    assert analyzer._calculate_weighted_score(result) == 93


def test_site_aggregation_groups_by_id_and_keeps_each_pages_evidence():
    issues = [dict(rule_result('headings.empty', {'position': i}, category=category), url=url)
              for i, category, url in ((0, 'SEO', 'https://example.test/a'), (2, 'Content', 'https://example.test/b'))]
    grouped, _ = aggregate_issues(issues)
    assert len(grouped) == 1 and grouped[0]['pages_affected'] == 2
    assert len(grouped[0]['evidence_by_page']) == 2
    grouped[0]['fix'] = 'Incorrect cached text'
    recs = generate_specific_recommendations({'issues': {'aggregated': grouped}})
    assert recs[0]['description'] == get_rule('headings.empty').recommendation


def test_ruleset_version_participates_in_cache_identity(monkeypatch):
    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'profile': 'quick'}))
        raw = {'url': 'https://example.test/', 'status_code': 200, 'headers': {},
               'soup': BeautifulSoup('<!doctype html><html lang="en"><title>Fixture</title><h1>Fixture</h1></html>', 'html.parser')}
        first = await analyzer.analyze_page(raw)
        assert not first.get('analyzer_errors'), first
        assert (await analyzer.analyze_page(raw)).get('cached')
        monkeypatch.setattr('tfq0seo.core.app.RULESET_VERSION', 'fixture-next')
        assert not (await analyzer.analyze_page(raw)).get('cached')
    asyncio.run(run())


def test_failed_canonical_owner_does_not_hide_a_valid_observer_deduction():
    analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'score_weights': {'seo': 0.5, 'content': 0.5}}}))
    result = synthetic_categories()
    result['content'] = {'score': None, 'status': 'error', 'error': 'Content extraction failed', 'issues': []}
    analyzer._apply_rule_scoring(result)
    assert result['content']['score'] is None
    assert result['seo']['score'] == 93
    assert result['scoring']['deductions'][0]['score_owner'] == 'seo'
    assert analyzer._calculate_weighted_score(result) == 93


def test_unknown_and_error_rule_coverage_survives_page_scoring():
    analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'score_weights': {'content': 1.0}}}))
    collector = RuleCollector('content')
    collector.check('headings.empty', None, {'headings': None}, reason='HTML unavailable')
    collector.check('images.missing_alt', None, {'images': None}, status='error', reason='Image extraction failed')
    result = {'content': {'score': 100, 'issues': [], 'rule_results': collector.results}}
    analyzer._apply_rule_scoring(result)
    assert result['rule_coverage']['counts']['pass'] == 0
    assert result['rule_coverage']['counts']['unknown'] == 1
    assert result['rule_coverage']['counts']['error'] == 1
    assert result['rule_coverage']['ratio'] == 0
    assert result['scoring']['deductions'] == []


def test_rule_error_marks_analyzer_and_page_partial_without_penalty(monkeypatch):
    def partial_content(*args, **kwargs):
        collector = RuleCollector('content')
        collector.check('headings.empty', None, {'headings': None}, status='error', reason='Fixture extraction error')
        collector.check('images.missing_alt', False, {'images': []})
        return {'score': 100, 'issues': [], 'rule_results': collector.results, 'data': {}}

    monkeypatch.setattr('tfq0seo.core.app.analyze_content', partial_content)

    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['content'], 'score_weights': {'content': 1.0}}}))
        raw = {'url': 'https://example.test/', 'status_code': 200,
               'soup': BeautifulSoup('<h1>Fixture</h1>', 'html.parser')}
        page = await analyzer.analyze_page(raw)
        assert page['status'] == 'partial'
        assert page['content']['status'] == 'partial'
        assert page['coverage']['partial_analyzers'] == ['content']
        assert page['rule_coverage']['counts']['error'] == 1
        assert page['overall_score'] == 100
        assert not (await analyzer.analyze_page(raw)).get('cached')
    asyncio.run(run())


def test_scoring_version_invalidates_analyzer_cache(monkeypatch):
    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['links'], 'score_weights': {'links': 1.0}}}))
        raw = {'url': 'https://example.test/', 'status_code': 200,
               'soup': BeautifulSoup('<a href="/next">Next</a>', 'html.parser')}
        await analyzer.analyze_page(raw)
        assert (await analyzer.analyze_page(raw)).get('cached')
        monkeypatch.setattr('tfq0seo.core.app.SCORING_VERSION', 'fixture-new-scoring')
        assert not (await analyzer.analyze_page(raw)).get('cached')
    asyncio.run(run())


def test_postcrawl_rule_resolution_replaces_outcomes_and_is_idempotent():
    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['links'], 'score_weights': {'links': 1.0}}}))
        raw = {'url': 'https://example.test/', 'status_code': 200,
               'soup': BeautifulSoup('<a href="/next">Next</a>', 'html.parser')}
        source = await analyzer.analyze_page(raw)
        for status_code, outcome, score in ((None, 'unknown', 100), (200, 'pass', 100), (404, 'fail', 85), (200, 'pass', 100)):
            targets = [] if status_code is None else [{'url': 'https://example.test/next', 'status_code': status_code}]
            analyzer._resolve_site_links([source] + targets)
            broken = [item for item in source['rule_results'] if item['rule_id'] == 'links.broken']
            assert len(broken) == 1 and broken[0]['status'] == outcome
            assert source['overall_score'] == score
            assert len(source['scoring']['deductions']) == (1 if outcome == 'fail' else 0)
            assert bool(source['recommendations']) == (outcome == 'fail')
            snapshot = copy.deepcopy(source)
            analyzer._resolve_site_links([source] + targets)
            assert source == snapshot
    asyncio.run(run())


def test_legacy_page_link_resolution_does_not_promote_an_incomplete_ruleset():
    analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['links'], 'score_weights': {'links': 1.0}}}))
    legacy_issue = {'category': 'Links', 'severity': 'warning', 'message': 'Legacy accessible-name issue', 'fix': 'Add link text'}
    source = {'url': 'https://example.test/', 'status_code': 200, 'overall_score': 93,
              'issues': [copy.deepcopy(legacy_issue)],
              'links': {'score': 93, 'issues': [copy.deepcopy(legacy_issue)],
                        'data': {'internal_links': [{'url': 'https://example.test/next'}]}}}
    analyzer._resolve_site_links([source, {'url': 'https://example.test/next', 'status_code': 200}])
    assert source['overall_score'] == 93
    assert any(issue['message'] == legacy_issue['message'] for issue in source['issues'])


def test_real_analyzers_charge_missing_alt_only_once():
    async def run():
        analyzer = SEOAnalyzer(Config())
        template = ('<!doctype html><html lang="en"><head><title>Useful fixture</title>'
                    '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
                    '<body><h1>Useful fixture</h1><img src="/photo.png" width="200" height="100" {alt}></body></html>')
        results = []
        for alt in ('alt="A photo"', ''):
            result = await analyzer.analyze_page({'url': 'https://example.test/', 'status_code': 200,
                'headers': {}, 'soup': BeautifulSoup(template.format(alt=alt), 'html.parser')})
            assert not result['analyzer_errors']
            results.append(result)
        good, missing = results
        assert {name: good[name]['score'] - missing[name]['score'] for name in
                ('seo', 'content', 'technical', 'performance', 'links')} == {
                    'seo': 0, 'content': 7, 'technical': 0, 'performance': 0, 'links': 0}
        assert good['overall_score'] - missing['overall_score'] == 1.75
        deductions = [item for item in missing['scoring']['deductions'] if item['rule_id'] == 'images.missing_alt']
        assert len(deductions) == 1
        assert deductions[0]['reported_by'] == ['content', 'seo']
        assert missing['seo']['data']['scores']['total'] == missing['seo']['score']
        assert missing['content']['data']['quality_assessment']['score'] == missing['content']['score']
    asyncio.run(run())


def test_merged_confirmed_failure_does_not_hide_an_evaluation_error():
    collector = RuleCollector('content')
    collector.check('headings.empty', True, {'text': ''})
    collector.check('headings.empty', None, {'text': None}, status='error', reason='Fixture extraction failed')
    assert collector.coverage['counts']['fail'] == 1
    assert collector.coverage['has_errors']
    assert score_findings(collector.results) == 93


def test_resolved_link_health_updates_legacy_data_fields():
    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'analysis': {'enabled_analyzers': ['links'], 'score_weights': {'links': 1.0}}}))
        source = await analyzer.analyze_page({'url': 'https://example.test/', 'status_code': 200,
            'soup': BeautifulSoup('<a href="/next">Next</a>', 'html.parser')})
        analyzer._resolve_site_links([source, {'url': 'https://example.test/next', 'status_code': 404}])
        data = source['links']['data']
        assert data['link_health_status'] == data['link_health']['status'] == 'complete'
        assert data['recommendations'] == source['links']['recommendations']
        assert data['broken_links'] == ['https://example.test/next']
    asyncio.run(run())
