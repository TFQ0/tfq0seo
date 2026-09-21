"""Cross-page checks use observed facts; absence is never a network failure."""

import asyncio
import copy
import csv
import json

import pytest
from bs4 import BeautifulSoup

from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.core.models import ContractError, validate_rule_result
from tfq0seo.core.report_contracts import validate_site_report
from tfq0seo.exporters.base import ExportManager
from tfq0seo.site_analysis import analyze_site


BASE = 'https://example.test'


def page(path, targets=(), links=(), status=200, noindex=False, truncated=False):
    url = BASE + path
    result = {'url': url, 'status_code': status, 'truncated': truncated}
    if status >= 400:
        result.update(error='Observed HTTP error', status='error')
        return result
    result['page_facts'] = {
        'canonical': {'declarations': [{'href': target, 'url': BASE + target if target.startswith('/') else target,
                                        'eligible': True, 'source': 'html', 'reason': ''} for target in targets],
                      'headers_checked': True, 'parse_errors': 0},
        'robots': {'noindex': noindex, 'nofollow': False},
        'anchors': [{'url': BASE + target, 'attrs': {'rel': []}} for target in links],
    }
    return result


def rows(report):
    return {item['url'][len(BASE):]: item for item in report['pages']}


def ids(report, path):
    return {item['rule_id'] for item in report['findings'] if item['url'] == BASE + path}


def test_canonical_chain_and_target_redirect_use_observed_aliases():
    final = page('/final', ['/final'])
    final.update(requested_url=BASE + '/old', redirect_chain=[{'url': BASE + '/old'}])
    result = analyze_site([page('/a', ['/b']), page('/b', ['/old']), final])
    indexed = rows(result)
    assert indexed['/a']['canonical_hops'] == 3
    assert indexed['/a']['canonical_terminal'] == BASE + '/final'
    assert indexed['/a']['canonical_status'] == 'chain'
    assert indexed['/final']['canonical_status'] == 'self'
    assert 'site.canonical_target_redirect' in ids(result, '/b')
    assert 'site.canonical_chain' in ids(result, '/a')


def test_cycles_are_stored_once_and_self_canonicals_are_not_cycles():
    result = analyze_site([page('/a', ['/b']), page('/b', ['/a']), page('/before', ['/a']), page('/self', ['/self'])])
    indexed = rows(result)
    assert result['canonicals']['cycles'] == [{'id': 0, 'urls': [BASE + '/a', BASE + '/b']}]
    for path in ('/a', '/b', '/before'):
        assert indexed[path]['canonical_status'] == 'cycle'
        assert indexed[path]['canonical_hops'] is None
        assert indexed[path]['canonical_cycle_id'] == 0
    assert 'site.canonical_cycle' not in ids(result, '/self')


def test_conflicting_and_duplicate_canonical_declarations():
    result = analyze_site([page('/conflict', ['/a', '/b']), page('/same', ['/a', '/a']), page('/a', ['/a'])])
    assert rows(result)['/conflict']['canonical_status'] == 'conflict'
    assert rows(result)['/same']['canonical_status'] == 'resolved'
    assert 'site.canonical_conflict' in ids(result, '/conflict')
    assert 'site.canonical_conflict' not in ids(result, '/same')


def test_only_observed_http_errors_and_noindex_produce_target_findings():
    unavailable = page('/unavailable')
    unavailable.pop('page_facts')
    unavailable.update(status_code=0, error='Connection refused')
    result = analyze_site([page('/a', ['/404']), page('/b', ['/private']), page('/c', ['/missing']),
                           page('/d', ['/unavailable']), page('/e', ['https://other.test/']),
                           page('/404', status=404), page('/private', ['/private'], noindex=True), unavailable])
    assert 'site.canonical_target_error' in ids(result, '/a')
    assert 'site.canonical_target_noindex' in ids(result, '/b')
    assert 'site.canonical_target_error' not in ids(result, '/c') | ids(result, '/d') | ids(result, '/e')
    assert rows(result)['/c']['canonical_status'] == 'unchecked'
    assert rows(result)['/d']['canonical_status'] == 'unknown'
    assert result['canonicals']['unchecked_targets'] == [BASE + '/missing', 'https://other.test/']


def test_missing_partial_and_malformed_facts_do_not_prove_canonical_absence():
    legacy = {'url': BASE + '/legacy', 'status_code': 200}
    malformed = page('/malformed')
    malformed['page_facts']['canonical']['parse_errors'] = 1
    headers_unknown = page('/headers')
    headers_unknown['page_facts']['canonical']['headers_checked'] = False
    result = analyze_site([legacy, malformed, headers_unknown, page('/partial', truncated=True), page('/none')])
    for path in ('/legacy', '/malformed', '/headers', '/partial'):
        assert rows(result)[path]['canonical_status'] == 'unknown'
    assert rows(result)['/none']['canonical_status'] == 'none'
    assert result['coverage']['crawl_complete'] is False


def test_directed_link_depth_components_and_candidates_are_conservative():
    pages = [page('/', links=['/a', '/a#fragment', '/outside']), page('/a', links=['/b']),
             page('/b'), page('/self', links=['/self']), page('/island1', links=['/island2']),
             page('/island2', links=['/island1'])]
    pages[0]['page_facts']['anchors'][0]['attrs']['rel'] = ['nofollow']
    result = analyze_site(pages, start_url=BASE + '/', crawl_complete=False)
    indexed = rows(result)
    assert result['links']['edge_count'] == 6
    assert len(result['links']['components']) == 3
    assert indexed['/a']['incoming_links'] == 1
    assert indexed['/b']['link_depth'] == 2
    assert indexed['/self']['incoming_links'] == 0
    assert indexed['/self']['reachable'] is False
    assert 'site.links_no_incoming' in ids(result, '/self')
    assert 'site.links_unreachable' in ids(result, '/island1')
    assert 'site.links_no_incoming' not in ids(result, '/')
    assert result['links']['unfetched_targets'] == [BASE + '/outside']
    assert next(item for item in result['links']['edges'] if item['target'] == BASE + '/a')['nofollow'] is False
    for item in result['findings']:
        validate_rule_result(item)
        assert item['scope'] == 'site' and item['penalty'] == 0 and item['status'] == 'informational'


def test_batch_without_an_entry_page_does_not_invent_depth():
    result = analyze_site([page('/a', links=['/b']), page('/b')])
    assert result['links']['roots'] == []
    assert all(item['link_depth'] is None and item['reachable'] is None for item in result['pages'])


def test_queries_remain_distinct_and_redirect_aliases_coalesce_link_targets():
    final = page('/final')
    final['requested_url'] = BASE + '/old'
    result = analyze_site([page('/', links=['/old', '/final', '/?a=1', '/?a=2', '/#top']), final,
                           page('/?a=1'), page('/?a=2')])
    assert rows(result)['/final']['incoming_links'] == 1
    assert result['links']['node_count'] == 4
    assert result['links']['edge_count'] == 4


def test_results_are_order_independent_and_inputs_are_unchanged():
    pages = [page('/', ['/a'], ['/a']), page('/a', ['/b']), page('/b', ['/b'])]
    before = copy.deepcopy(pages)
    assert analyze_site(pages) == analyze_site(list(reversed(pages)))
    assert pages == before


def test_long_canonical_chain_does_not_recurse_or_copy_all_path_suffixes():
    count = 2200
    pages = [page('/' + str(index), ['/' + str(min(index + 1, count - 1))]) for index in range(count)]
    result = analyze_site(pages)
    assert rows(result)['/0']['canonical_hops'] == count - 1
    assert rows(result)['/0']['canonical_terminal'] == BASE + '/' + str(count - 1)
    assert len(json.dumps(result)) < count * 6000


def analyzed_report():
    async def run():
        analyzer = SEOAnalyzer(Config.from_dict({'crawler': {'cache_enabled': False}}))
        pages = []
        for path, head, links in [('/', '<link rel="canonical" href="/a">', '<a href="/a">A</a>'),
                                  ('/a', '<link rel="canonical" href="/b">', '<a href="/b">B</a>'),
                                  ('/b', '<link rel="canonical" href="/b">', '')]:
            html = '<!doctype html><html lang="en"><head><title>Page</title>' + head + '</head><body><h1>Page</h1>' + links + '</body></html>'
            pages.append(await analyzer.analyze_page({'url': BASE + path, 'status_code': 200,
                                                      'headers': {}, 'soup': BeautifulSoup(html, 'html.parser')}))
        before = copy.deepcopy(pages)
        result = analyzer.generate_site_report(pages)
        assert pages == before
        assert [item['overall_score'] for item in result['pages']['detailed']] == [item['overall_score'] for item in pages]
        return result
    return asyncio.run(run())


def test_site_findings_reach_recommendations_and_all_export_formats(tmp_path):
    report = analyzed_report()
    validate_site_report(report, strict=True)
    assert any(item['rule_id'] == 'site.canonical_chain' for item in report['recommendations']['specific'])
    for template in ('report', 'enhanced', 'optimized'):
        exporter = ExportManager({'output_directory': str(tmp_path), 'html_template': template})
        html = tmp_path / (template + '.html')
        exporter.export(report, 'html', str(html))
        assert 'Site-wide analysis' in html.read_text(encoding='utf-8')
        assert 'Canonical and internal-link observations' in html.read_text(encoding='utf-8')
    exporter.export(report, 'csv', str(tmp_path / 'site.csv'))
    with (tmp_path / 'site.csv').open(encoding='utf-8', newline='') as stream:
        exported = list(csv.DictReader(stream))
    assert exported[0]['canonical_hops'] == '2'
    assert exported[2]['link_depth'] == '2'
    exporter.export(report, 'xlsx', str(tmp_path / 'site.xlsx'))
    from openpyxl import load_workbook
    workbook = load_workbook(tmp_path / 'site.xlsx', read_only=True)
    assert 'Canonical Targets' in next(workbook['Pages'].values)
    workbook.close()


@pytest.mark.parametrize('mutate', [
    lambda report: report['site_analysis']['links'].update(edge_count=-1),
    lambda report: report['site_analysis']['links']['edges'][0].update(nofollow='false'),
    lambda report: report['site_analysis']['pages'][0].update(canonical_hops=True),
    lambda report: report['site_analysis']['pages'][0].update(canonical_targets='invalid'),
    lambda report: report['pages']['detailed'][0]['site_analysis'].update(incoming_links=-1),
])
def test_malformed_site_contract_is_rejected_before_export(tmp_path, mutate):
    report = analyzed_report()
    mutate(report)
    path = tmp_path / 'protected.html'
    path.write_text('Keep me', encoding='utf-8')
    with pytest.raises(ContractError):
        ExportManager({'output_directory': str(tmp_path)}).export(report, 'html', str(path))
    assert path.read_text(encoding='utf-8') == 'Keep me'


def test_html_site_observations_escape_untrusted_urls(tmp_path):
    report = analyzed_report()
    row = report['site_analysis']['pages'][0]
    row.update(url='javascript:alert(1)', canonical_terminal='<script>alert(1)</script>')
    path = tmp_path / 'escaped.html'
    ExportManager({'output_directory': str(tmp_path)}).export(report, 'html', str(path))
    html = path.read_text(encoding='utf-8')
    assert 'href="javascript:' not in html
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
