import json
from unittest.mock import AsyncMock

from click.testing import CliRunner

from tfq0seo.cli import cli


def write_config(tmp_path, **crawler):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps({'profile': 'quick', 'crawler': {
        'respect_robots_txt': False, 'use_sitemap': False, 'max_retries': 0, **crawler}}), encoding='utf-8')
    return str(path)


def test_failed_analyze_has_nonzero_exit_and_visible_error(monkeypatch):
    monkeypatch.setattr('tfq0seo.cli.SEOAnalyzer.analyze_url', AsyncMock(return_value={
        'url': 'https://example.test', 'status': 'error', 'status_code': 0,
        'error': 'Fixture timeout', 'overall_score': None, 'issues': []}))
    result = CliRunner().invoke(cli, ['analyze', 'https://example.test'])
    assert result.exit_code == 1
    assert 'Fixture timeout' in result.output
    assert 'Unavailable' in result.output


def test_partial_analysis_exports_evidence_then_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr('tfq0seo.cli.SEOAnalyzer.analyze_url', AsyncMock(return_value={
        'url': 'https://example.test', 'status': 'partial', 'overall_score': 80,
        'analyzer_errors': {'content': 'Fixture analyzer failure'}, 'issues': []}))
    output = tmp_path / 'partial.json'
    result = CliRunner().invoke(cli, ['analyze', 'https://example.test', '-f', 'json', '-o', str(output)])
    assert result.exit_code == 1
    assert json.loads(output.read_text(encoding='utf-8'))['analyzer_errors']['content'] == 'Fixture analyzer failure'


def test_config_values_survive_unspecified_cli_defaults(tmp_path, monkeypatch):
    captured = {}
    async def crawl(self, url):
        captured.update(self.config.crawler.as_dict())
        yield {'url': url, 'status_code': 200, 'status': 'complete', 'overall_score': 90,
               'issues': [], 'seo': {'score': 90}}
    monkeypatch.setattr('tfq0seo.cli.SEOAnalyzer.crawl_site', crawl)
    result = CliRunner().invoke(cli, ['crawl', 'https://example.test', '-c', write_config(
        tmp_path, max_depth=1, max_pages=7, max_concurrent=2), '-o', str(tmp_path / 'report.json'), '-f', 'json'])
    assert result.exit_code == 0, result.output
    assert captured['max_depth'] == 1
    assert captured['max_pages'] == 7
    assert captured['max_concurrent'] == 2
    assert captured['respect_robots_txt'] is False


def test_explicit_cli_value_overrides_config(tmp_path, monkeypatch):
    captured = {}
    async def crawl(self, url):
        captured.update(self.config.crawler.as_dict())
        yield {'url': url, 'status_code': 200, 'overall_score': 90, 'issues': []}
    monkeypatch.setattr('tfq0seo.cli.SEOAnalyzer.crawl_site', crawl)
    result = CliRunner().invoke(cli, ['crawl', 'https://example.test', '-c', write_config(tmp_path, max_pages=7),
                                     '--max-pages', '3', '-o', str(tmp_path / 'report.json'), '-f', 'json'])
    assert result.exit_code == 0, result.output
    assert captured['max_pages'] == 3


def test_invalid_cli_concurrency_rejected_before_network(tmp_path):
    result = CliRunner().invoke(cli, ['crawl', 'https://example.test', '--concurrent', '0', '-o', str(tmp_path / 'x.json')])
    assert result.exit_code == 2


def test_all_cli_workflows_against_local_http(http_site, tmp_path):
    base, routes, _ = http_site
    for path in ('/one', '/two'):
        routes[path] = (200, {'Content-Type': 'text/html'}, f'<html lang="en"><title>{path}</title><h1>{path}</h1></html>')
    routes['/sitemap.xml'] = (200, {'Content-Type': 'application/xml'},
                             f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{base}/one</loc></url><url><loc>{base}/two</loc></url></urlset>')
    cfg = write_config(tmp_path)
    runner = CliRunner()
    single = runner.invoke(cli, ['analyze', base + '/one', '-c', cfg, '-f', 'json'])
    assert single.exit_code == 0, single.output
    assert json.loads(single.output)['url'] == base + '/one'
    urls = tmp_path / 'urls.txt'
    urls.write_text(f' # comment\n{base}/one\n\n{base}/two\n', encoding='utf-8')
    for command, target in [('batch', str(urls)), ('sitemap', base + '/sitemap.xml')]:
        output = tmp_path / (command + '.json')
        result = runner.invoke(cli, [command, target, '-c', cfg, '-f', 'json', '-o', str(output)])
        assert result.exit_code == 0, result.output
        report = json.loads(output.read_text(encoding='utf-8'))
        assert report['summary']['total_pages'] == 2
        assert len(report['pages']['detailed']) == 2
        csv_output = output.with_suffix('.csv')
        converted = runner.invoke(cli, ['export', '-i', str(output), '-f', 'csv', '-o', str(csv_output)])
        assert converted.exit_code == 0, converted.output
        assert csv_output.exists()


def test_empty_batch_and_malformed_json_export_fail(tmp_path):
    urls = tmp_path / 'empty.txt'
    urls.write_text(' # comment\n', encoding='utf-8')
    result = CliRunner().invoke(cli, ['batch', str(urls), '-o', str(tmp_path / 'report.json')])
    assert result.exit_code == 1 and 'no URLs' in result.output
    invalid = tmp_path / 'invalid.json'
    invalid.write_text('[]', encoding='utf-8')
    result = CliRunner().invoke(cli, ['export', '-i', str(invalid), '-f', 'csv', '-o', str(tmp_path / 'x.csv')])
    assert result.exit_code == 1 and 'JSON object' in result.output


def test_500_page_crawl_keeps_complete_json(http_site, tmp_path):
    base, routes, _ = http_site
    links = ''.join(f'<a href="/page/{i}">Page {i}</a>' for i in range(499))
    routes['/'] = (200, {'Content-Type': 'text/html'}, f'<html lang="en"><title>Home</title><h1>Home</h1>{links}</html>')
    for i in range(499):
        routes[f'/page/{i}'] = (200, {'Content-Type': 'text/html'}, f'<html lang="en"><title>Page {i}</title><h1>Page {i}</h1></html>')
    cfg = write_config(tmp_path, max_pages=500, max_depth=1)
    output = tmp_path / 'full.json'
    result = CliRunner().invoke(cli, ['crawl', base + '/', '-c', cfg, '-f', 'json', '-o', str(output)])
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['summary']['total_pages'] == report['summary']['successful_pages'] == 500
    assert len(report['pages']['detailed']) == 500
    assert len({page['url'] for page in report['pages']['detailed']}) == 500
