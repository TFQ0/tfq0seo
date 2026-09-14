"""Run with python -I after installing a built wheel, not an editable checkout."""

import asyncio
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


async def main():
    source_root = Path(__file__).resolve().parents[1]
    if Path(tfq0seo.__file__).resolve().parent == source_root / 'tfq0seo':
        raise AssertionError('Smoke test imported the source checkout instead of the installed wheel')
    cfg = Config.from_dict({'profile': 'quick'})
    analyzer = tfq0seo.SEOAnalyzer(cfg)
    result = await analyzer.analyze_page({
        'url': 'https://example.test/', 'status_code': 200,
        'soup': BeautifulSoup('<!doctype html><html lang="en"><title>Example</title><h1>Example</h1><img src="/image.png"></html>', 'html.parser'),
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
    with tempfile.TemporaryDirectory(prefix='tfq0seo-wheel-') as directory:
        exporter = ExportManager({'output_directory': directory})
        report = analyzer.generate_site_report([result])
        assert validate_site_report(report, strict=True) is report
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
        formats = ['json', 'html', 'csv']
        if importlib.util.find_spec('openpyxl'):
            formats.append('xlsx')
        for format in formats:
            output = Path(exporter.export(report, format))
            assert output.is_file() and output.stat().st_size > 0
        assert json.loads(next(Path(directory).glob('*.json')).read_text(encoding='utf-8'))['schema_version'] == '1.0'
    print('Installed wheel smoke test passed:', tfq0seo.__version__)


if __name__ == '__main__':
    asyncio.run(main())
