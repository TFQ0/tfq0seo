"""Run with python -I after installing a built wheel, not an editable checkout."""

import asyncio
import csv
import importlib.util
import json
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

import tfq0seo
from tfq0seo.core.config import Config
from tfq0seo.core.report_contracts import validate_page_result, validate_site_report
from tfq0seo.exporters.base import ExportManager
from tfq0seo.page_facts import FACTS_VERSION
from tfq0seo.rules import RULESET_VERSION, SCORING_VERSION
from tfq0seo.site_analysis import SITE_ANALYSIS_VERSION


async def main():
    source_root = Path(__file__).resolve().parents[1]
    if Path(tfq0seo.__file__).resolve().parent == source_root / 'tfq0seo':
        raise AssertionError('Smoke test imported the source checkout instead of the installed wheel')
    legacy = {'profile': 'quick', 'crawler': {'use_http2': False, 'max_pages': 2, 'concurrent_requests': 2},
              'analysis': {'min_content_length': 100}}
    before = json.loads(json.dumps(legacy))
    try:
        Config.from_dict(legacy)
    except ValueError as error:
        assert 'Config.migrate_dict()' in str(error)
    else:
        raise AssertionError('Retired settings must require explicit migration')
    migrated, warnings = Config.migrate_dict(legacy)
    assert legacy == before
    assert migrated == {'profile': 'quick', 'crawler': {'max_pages': 2, 'max_concurrent': 2}, 'analysis': {}}
    assert any('crawler.use_http2' in warning for warning in warnings)
    assert any('analysis.min_content_length' in warning for warning in warnings)
    try:
        Config.migrate_dict({'crawler': {'use_http2': True}})
    except ValueError as error:
        assert 'cannot be migrated automatically' in str(error)
    else:
        raise AssertionError('Migration must reject unsupported non-default behavior')
    cfg = Config.from_dict(migrated)
    assert cfg.crawler.max_pages == 2 and cfg.crawler.max_concurrent == 2
    analyzer = tfq0seo.SEOAnalyzer(cfg)
    result = await analyzer.analyze_page({
        'url': 'https://example.test/', 'status_code': 200,
        'soup': BeautifulSoup('<!doctype html><html lang="en"><head><title>Example</title>'
                              '<link rel="canonical" href="/old"></head><body><h1>Example</h1>'
                              '<a href="/old">Final page</a><img src="/image.png"></body></html>', 'html.parser'),
        'headers': {},
    })
    assert not result.get('error') and not result.get('analyzer_errors'), result
    assert validate_page_result(result, strict=True) is result
    assert result['page_facts']['facts_version'] == FACTS_VERSION
    assert result['page_facts']['headers_observed'] is True
    assert 'headers' not in result['page_facts']
    assert result['scoring']['version'] == SCORING_VERSION
    assert result['scoring']['ruleset_version'] == RULESET_VERSION
    assert result['rule_coverage']['counts']['fail'] > 0
    deductions = [item for item in result['scoring']['deductions'] if item['rule_id'] == 'images.missing_alt']
    assert len(deductions) == 1 and deductions[0]['penalty'] == 7
    final = await analyzer.analyze_page({
        'url': 'https://example.test/final', 'requested_url': 'https://example.test/old', 'status_code': 200,
        'redirect_chain': [{'url': 'https://example.test/old', 'status_code': 301,
                            'location': 'https://example.test/final'}],
        'soup': BeautifulSoup('<!doctype html><html lang="en"><head><title>Final</title></head>'
                              '<body><h1>Final</h1></body></html>', 'html.parser'),
        'headers': {'Link': '<https://example.test/final>; rel="canonical"'},
    })
    assert not final.get('error') and not final.get('analyzer_errors'), final
    assert validate_page_result(final, strict=True) is final
    canonical = final['page_facts']['canonical']
    assert canonical['headers_checked'] is True and canonical['parse_errors'] == 0
    assert canonical['declarations'][0]['source'] == 'http_link'
    assert canonical['declarations'][0]['eligible'] is True
    with tempfile.TemporaryDirectory(prefix='tfq0seo-wheel-') as directory:
        exporter = ExportManager({'output_directory': directory})
        report = analyzer.generate_site_report([result, final])
        assert validate_site_report(report, strict=True) is report
        site = report['site_analysis']
        assert site['version'] == SITE_ANALYSIS_VERSION
        indexed = {row['url']: row for row in site['pages']}
        assert indexed[result['url']]['canonical_status'] == 'chain'
        assert indexed[result['url']]['canonical_hops'] == 2
        assert indexed[result['url']]['canonical_terminal'] == final['url']
        assert indexed[final['url']]['canonical_status'] == 'self'
        assert indexed[final['url']]['incoming_links'] == 1
        assert indexed[final['url']]['link_depth'] == 1
        assert site['links']['node_count'] == 2 and site['links']['edge_count'] == 1
        assert {'site.canonical_chain', 'site.canonical_target_redirect'} <= {
            item['rule_id'] for item in site['findings']}
        for filename in ('rule_metadata.html', 'site_analysis.html'):
            assert (Path(tfq0seo.__file__).resolve().parent / 'templates' / filename).is_file()
            exporter.jinja_env.get_template(filename)
        templates = {'report': 'report.html', 'enhanced': 'enhanced_report.html', 'optimized': 'optimized_report.html'}
        for template, filename in templates.items():
            packaged_template = Path(tfq0seo.__file__).resolve().parent / 'templates' / filename
            assert packaged_template.is_file(), 'Missing packaged template: ' + filename
            exporter.jinja_env.get_template(filename)  # Do not permit the exporter's inline fallback.
            exporter.config['html_template'] = template
            output = Path(exporter.export(report, 'html', str(Path(directory) / filename)))
            assert output.is_file() and output.stat().st_size > 0
            rendered = BeautifulSoup(output.read_text(encoding='utf-8'), 'html.parser')
            assert rendered.select_one('.rule-metadata[data-rule-id="images.missing_alt"]')
            assert SCORING_VERSION in rendered.select_one('.rule-assessment').get_text()
            section = rendered.select_one('section[aria-label="Site-wide analysis"]')
            assert section and 'Canonical and internal-link observations' in section.get_text()
            assert len(section.select('tbody tr')) == 2
            assert 'chain' in section.get_text() and final['url'] in section.get_text()
        formats = ['json', 'html', 'csv']
        if importlib.util.find_spec('openpyxl'):
            formats.append('xlsx')
        for format in formats:
            output = Path(exporter.export(report, format))
            assert output.is_file() and output.stat().st_size > 0
        exported = json.loads(next(Path(directory).glob('*.json')).read_text(encoding='utf-8'))
        assert exported['schema_version'] == '1.0'
        assert exported['site_analysis'] == site
        with next(Path(directory).glob('*.csv')).open(encoding='utf-8', newline='') as stream:
            csv_rows = list(csv.DictReader(stream))
        assert len(csv_rows) == 2 and csv_rows[0]['canonical_hops'] == '2'
    print('Installed wheel smoke test passed:', tfq0seo.__version__)


if __name__ == '__main__':
    asyncio.run(main())
