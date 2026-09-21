"""Regression cases found during independent cross-page analysis review."""

import pytest
from bs4 import BeautifulSoup

from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.models import ContractError
from tfq0seo.page_facts import extract_page_facts
from tfq0seo.site_analysis import analyze_site


BASE = 'https://example.test'


def source_page(path='/source', canonical='/old'):
    soup = BeautifulSoup('<html><head><link rel="canonical" href="' + canonical +
                         '"></head><body></body></html>', 'html.parser')
    return {'url': BASE + path, 'status_code': 200, 'issues': [],
            'page_facts': extract_page_facts(soup, BASE + path, {}).to_dict()}


def test_canonical_redirect_to_observed_http_error_retains_final_response_evidence():
    final = {'url': BASE + '/gone', 'requested_url': BASE + '/old', 'status_code': 404,
             'error': 'HTTP 404', 'status': 'error',
             'redirect_chain': [{'url': BASE + '/old', 'status_code': 301, 'location': BASE + '/gone'}]}
    report = analyze_site([source_page(), final])
    row = next(row for row in report['pages'] if row['url'] == BASE + '/source')
    assert row['canonical_terminal'] == BASE + '/gone'
    assert row['canonical_status'] == 'http_error'
    rules = {item['rule_id'] for item in report['findings'] if item['url'] == BASE + '/source'}
    assert {'site.canonical_target_redirect', 'site.canonical_target_error'} <= rules


def test_canonical_redirect_to_observed_non_html_response_retains_redirect_evidence():
    final = {'url': BASE + '/file.pdf', 'requested_url': BASE + '/old', 'status_code': 200,
             'error': 'Non-HTML content: application/pdf', 'status': 'skipped', 'skipped': True,
             'redirect_chain': [{'url': BASE + '/old', 'status_code': 302, 'location': BASE + '/file.pdf'}]}
    report = analyze_site([source_page(), final])
    row = next(row for row in report['pages'] if row['url'] == BASE + '/source')
    assert row['canonical_terminal'] == BASE + '/file.pdf'
    assert row['canonical_status'] == 'unknown'  # The target's own canonical remains unobserved.
    assert any(item['rule_id'] == 'site.canonical_target_redirect' for item in report['findings'])


@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
def test_observed_unfollowed_canonical_redirect_is_reported_without_inventing_its_destination(status):
    target = {'url': BASE + '/old', 'requested_url': BASE + '/old', 'status_code': status,
              'error': 'Redirect not followed', 'status': 'skipped', 'skipped': True, 'redirect_chain': []}
    report = analyze_site([source_page(), target])
    rules = {item['rule_id'] for item in report['findings'] if item['url'] == BASE + '/source'}
    assert 'site.canonical_target_redirect' in rules
    assert 'site.canonical_target_error' not in rules
    row = next(row for row in report['pages'] if row['url'] == BASE + '/source')
    assert row['canonical_terminal'] == BASE + '/old'
    assert row['canonical_status'] == 'unknown'


@pytest.mark.parametrize('page_facts', [
    {'robots': None},
    {'anchors': None},
    {'canonical': {'declarations': None}},
    {'canonical': {'declarations': [None]}},
])
def test_malformed_archived_fact_fields_are_rejected_at_the_report_boundary(page_facts):
    record = {'url': BASE + '/archive', 'status_code': 200, 'issues': [], 'page_facts': page_facts}
    with pytest.raises(ContractError, match='page_facts'):
        SEOAnalyzer().generate_site_report([record])


def test_incomplete_archived_fact_objects_do_not_establish_absence_or_html_coverage():
    record = {'url': BASE + '/archive', 'status_code': 200,
              'page_facts': {'canonical': {'headers_checked': True}}}
    report = analyze_site([record])
    row = report['pages'][0]
    assert row['canonical_status'] == 'unknown'
    assert row['outgoing_links'] is None
    assert row['content_complete'] is False
    assert report['coverage']['complete_html_pages'] == 0
