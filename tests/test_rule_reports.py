"""Rule provenance is readable and inert across the existing HTML layouts."""

import asyncio
import copy
import json
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.exporters.base import ExportManager


TEMPLATES = ('report', 'enhanced', 'optimized')


@pytest.fixture
def analyzed_page():
    config = Config.from_dict({'analysis': {'enabled_analyzers': ['seo'], 'score_weights': {'seo': 1.0}}})
    html = '<!doctype html><html lang="en"><title>Rule report</title><h1>Example</h1><img src="/image.png"></html>'
    return asyncio.run(SEOAnalyzer(config).analyze_page({
        'url': 'https://example.test/report/', 'status_code': 200, 'headers': {},
        'load_time': 0.1, 'soup': BeautifulSoup(html, 'html.parser'),
    }))


def render(tmp_path, template, data):
    exporter = ExportManager({'output_directory': str(tmp_path), 'html_template': template})
    path = Path(exporter.export(data, 'html'))
    html = path.read_text(encoding='utf-8')
    return BeautifulSoup(html, 'html.parser'), html, exporter


@pytest.mark.parametrize('template', TEMPLATES)
@pytest.mark.parametrize('kind', ('page', 'site'))
def test_rule_metadata_and_policy_render_from_application_results(tmp_path, analyzed_page, template, kind):
    data = analyzed_page if kind == 'page' else SEOAnalyzer().generate_site_report([analyzed_page])
    before = copy.deepcopy(data)
    soup, _, exporter = render(tmp_path, template, data)
    metadata = soup.select_one('.rule-metadata[data-rule-id="images.missing_alt"]')
    assert metadata is not None
    text = metadata.get_text(' ', strip=True)
    for expected in ('Rule:', 'Outcome: fail', 'Applicability: applicable', 'Observation source:', 'Rule reviewed: 2026-09-14'):
        assert expected in text
    assert metadata.select_one('details.rule-evidence summary').get_text() == 'Recorded evidence'
    evidence = json.loads(metadata.select_one('details.rule-evidence pre').get_text())
    assert '/image.png' in json.dumps(evidence)
    assert metadata.select_one('.rule-references a')['href'].startswith('https://')
    assert 'Rule deduction: 7 points' in text
    if kind == 'site':
        per_page = next(details for details in metadata.select('details')
                        if details.select_one('summary').get_text() == 'Evidence by affected page')
        assert json.loads(per_page.select_one('pre').get_text())[0]['url'] == analyzed_page['url']
    overview = soup.select_one('.rule-assessment')
    assert data['scoring']['version'] in overview.get_text()
    assert data['scoring']['policy'] in overview.get_text()
    assert 'not search ranking factors' in overview.get_text()
    assert 'unknown' in overview.select_one('.rule-coverage-counts').get_text()
    assert 'not passed checks' in overview.get_text()
    assert exporter._prepare_html_data(data)['rule_coverage'] == data['rule_coverage']
    assert data == before


@pytest.mark.parametrize('template', TEMPLATES)
def test_untrusted_rule_metadata_is_text_not_executable_markup(tmp_path, analyzed_page, template):
    payload = '</pre><img src=x onerror="alert(1)"><script>alert(2)</script>'
    issue = {
        'rule_id': payload, 'category': 'Imported rule', 'severity': 'warning', 'message': 'Imported finding',
        'status': payload, 'applicability': payload, 'rule_applicability': payload,
        'reason': payload, 'source': payload, 'reviewed_on': payload,
        'references': ['javascript:alert(1)', 'data:text/html,' + payload, '//example.test/path',
                       'https:\n//example.test', 'https://example.test/reference?q="' + payload],
        'evidence': {'observed': payload}, 'observations': [{'evidence': payload}],
    }
    data = copy.deepcopy(analyzed_page)
    data['issues'] = [issue]
    data['scoring'] = {'version': payload, 'ruleset_version': payload, 'policy': payload,
                       'scope': payload, 'weights': {'seo': payload}}
    data['rule_coverage'] = {'total': 1, 'assessed': 0, 'counts': {'unknown': 1}, 'scope': payload}
    soup, rendered, _ = render(tmp_path, template, data)
    assert not soup.find('img')
    assert not soup.select('[onerror]')
    assert not any('alert(2)' in (script.string or '') and '\\u003c' not in (script.string or '')
                   for script in soup.find_all('script'))
    assert 'innerHTML' not in rendered
    metadata = soup.select_one('.rule-metadata')
    assert metadata['data-rule-id'] == payload
    assert payload in metadata.get_text()
    assert json.loads(metadata.select_one('.rule-evidence pre').get_text()) == {'observed': payload}
    references = metadata.select('.rule-references a')
    assert len(references) == 1
    assert references[0]['href'].startswith('https://example.test/reference')
    assert payload in soup.select_one('.rule-assessment').get_text()


@pytest.mark.parametrize('template', TEMPLATES)
def test_legacy_reports_without_rule_metadata_still_render(tmp_path, template):
    data = {'url': 'https://example.test/legacy', 'overall_score': 70,
            'issues': [{'category': 'Legacy', 'severity': 'warning', 'message': 'Legacy observation'}]}
    soup, _, _ = render(tmp_path, template, data)
    assert 'Legacy observation' in soup.get_text()
    assert not soup.select('.rule-metadata')
    assert not soup.select('.rule-assessment')


@pytest.mark.parametrize('template', TEMPLATES)
def test_scoring_version_list_survives_older_site_adapter_shape(tmp_path, template):
    data = {'scores': {'overall': None, 'scoring_versions': ['older-policy', '2.0']}, 'pages': []}
    soup, _, _ = render(tmp_path, template, data)
    assert 'Scoring versions: older-policy, 2.0' in soup.select_one('.rule-assessment').get_text(' ', strip=True)


@pytest.mark.parametrize('template', TEMPLATES)
def test_rule_metadata_does_not_drop_paginated_pages(tmp_path, analyzed_page, template):
    pages = [dict(copy.deepcopy(analyzed_page), url=f'https://example.test/page-{index}') for index in range(25)]
    report = SEOAnalyzer().generate_site_report(pages)
    soup, html, exporter = render(tmp_path, template, report)
    assert len(exporter._prepare_html_data(report)['pages_summary']) == 25
    if template == 'optimized':
        embedded = re.search(r'const pagesData = (.*);', html).group(1)
        assert len(json.loads(embedded)) == 25
        assert 'Page 1 of 2' in soup.get_text()
    else:
        assert len(soup.select('.pages-table tbody tr')) == 25
    assert soup.select('.rule-metadata')
