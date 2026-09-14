"""Technical, performance, and link analyzers consume one shared page snapshot."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from bs4 import BeautifulSoup

from tfq0seo.analyzers import analyze_links, analyze_performance, analyze_technical
from tfq0seo.analyzers.common import is_nonblocking_script
from tfq0seo.page_facts import extract_page_facts


URL = 'https://example.test/start/'
HEADERS = {'Content-Type': 'text/html; charset=utf-8',
           'X-Robots-Tag': ['googlebot: noindex', 'bingbot: nofollow'],
           'Content-Security-Policy': ["script-src 'none'", "script-src 'unsafe-eval'; frame-ancestors 'none'"]}


def document():
    return BeautifulSoup('''<!doctype html><html lang="fr"><head><title>Example</title>
        <base href="/assets/"><meta name="viewport" content="width=device-width">
        <meta name="robots" content="nosnippet"><link rel="canonical" href="canonical">
        <link rel="stylesheet" href="main.css"><link rel="preload" as="font" href="font.woff2">
        <script src="blocking.js"></script><script src="async.js" async></script>
        <script type="module" src="module.js"></script><script>location.href = '/next';</script>
        </head><body><h1>Heading</h1><p id="name">Destination label</p>
        <nav><a href="a//b?key=&key=Two" aria-labelledby="name">Fallback</a></nav>
        <p><a href="https://outside.test/" rel="nofollow sponsored">Outside</a></p>
        <a href="image"><img src="hero.webp" alt="Hero" width="10" height="20"></a>
        <img src="small.svg" loading="lazy"><a href="javascript:void(0)">Action</a>
        <video src="video.mp4"><source src="video.webm"></video></body></html>''', 'html.parser')


def run(analyzer, soup, facts=None):
    kwargs = {'facts': facts} if facts is not None else {}
    if analyzer is analyze_technical:
        return analyzer(soup, URL, headers=HEADERS, **kwargs)
    if analyzer is analyze_performance:
        return analyzer(soup, URL, load_time=0.25, content_length=2048, **kwargs)
    return analyzer(soup, URL, **kwargs)


@pytest.mark.parametrize('analyzer', [analyze_technical, analyze_performance, analyze_links])
def test_shared_snapshot_matches_standalone_public_api(analyzer):
    soup = document()
    facts = extract_page_facts(soup, URL, HEADERS)
    standalone = run(analyzer, soup)
    shared = run(analyzer, soup, facts)
    assert shared == standalone
    json.dumps(shared, allow_nan=False)


def test_supplied_snapshot_prevents_common_reextraction(monkeypatch):
    soup = document()
    facts = extract_page_facts(soup, URL, HEADERS)
    original_find_all = soup.find_all

    def no_common_scan(name=None, *args, **kwargs):
        if isinstance(name, str) and name in ('a', 'img', 'script', 'meta', 'link'):
            raise AssertionError('Shared HTML collection was scanned again: ' + name)
        return original_find_all(name, *args, **kwargs)

    def no_snapshot(*args, **kwargs):
        raise AssertionError('A second PageFacts snapshot was extracted')

    monkeypatch.setattr(soup, 'find_all', no_common_scan)
    monkeypatch.setattr('tfq0seo.page_facts.extract_page_facts', no_snapshot)
    for analyzer in (analyze_technical, analyze_performance, analyze_links):
        result = run(analyzer, soup, facts)
        assert 'error' not in result


@pytest.mark.parametrize('analyzer', [analyze_technical, analyze_performance, analyze_links])
def test_standalone_analyzer_builds_exactly_one_snapshot(analyzer, monkeypatch):
    import tfq0seo.page_facts as module
    original = module.extract_page_facts
    calls = []

    def counted(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, 'extract_page_facts', counted)
    run(analyzer, document())
    assert len(calls) == 1


def test_parallel_analyzers_do_not_modify_soup_snapshot_or_each_other():
    soup = document()
    before = str(soup)
    facts = extract_page_facts(soup, URL, HEADERS)
    original_snapshot = facts.to_dict(include_content=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        outputs = list(pool.map(lambda analyzer: run(analyzer, soup, facts),
                                (analyze_technical, analyze_performance, analyze_links)))
    outputs[2]['data']['internal_links'][0]['rel'].append('changed')
    outputs[0]['data']['crawlability']['robots_analysis']['evidence'].clear()
    assert str(soup) == before
    assert facts.to_dict(include_content=True) == original_snapshot
    repeated = run(analyze_links, soup, facts)
    assert 'changed' not in repeated['data']['internal_links'][0]['rel']


@pytest.mark.parametrize('headers,expected', [(None, 'unknown'), ({}, 'informational')])
def test_technical_respects_snapshot_header_observation_state(headers, expected):
    soup = document()
    facts = extract_page_facts(soup, URL, headers)
    result = analyze_technical(soup, URL, facts=facts)
    rules = {item['rule_id']: item for item in result['rule_results']}
    assert rules['security.hsts_missing']['status'] == expected
    assert rules['security.hsts_missing']['evidence']['headers_checked'] is (headers is not None)


def test_technical_adopts_snapshot_user_agent_and_preserves_repeated_headers():
    soup = document()
    facts = extract_page_facts(soup, URL, HEADERS, user_agent='bingbot')
    result = analyze_technical(soup, URL, facts=facts)
    robots = result['data']['crawlability']['robots_analysis']
    assert robots['user_agent'] == 'bingbot'
    assert robots['nofollow'] is True
    assert robots['noindex'] is False
    csp = next(item for item in result['rule_results'] if item['rule_id'] == 'security.csp_unsafe_eval')
    assert len(csp['evidence']['policies']) == 2


@pytest.mark.parametrize('analyzer', [analyze_technical, analyze_performance, analyze_links])
def test_supplied_snapshot_rejects_different_source_or_url(analyzer):
    soup = document()
    facts = extract_page_facts(soup, URL, HEADERS)
    with pytest.raises(ValueError, match='URL and soup'):
        analyzer(document(), URL, facts=facts)
    with pytest.raises(ValueError, match='URL and soup'):
        analyzer(soup, URL + 'other', facts=facts)


def test_technical_rejects_conflicting_explicit_context():
    soup = document()
    facts = extract_page_facts(soup, URL, HEADERS)
    with pytest.raises(ValueError, match='response headers'):
        analyze_technical(soup, URL, headers={}, facts=facts)
    with pytest.raises(ValueError, match='user agent'):
        analyze_technical(soup, URL, user_agent='bingbot', facts=facts)


def test_shared_link_names_context_and_url_identity_are_preserved():
    soup = document()
    facts = extract_page_facts(soup, URL, HEADERS)
    result = analyze_links(soup, URL, facts=facts)
    links = result['data']['internal_links']
    assert links[0]['url'] == 'https://example.test/assets/a//b?key=&key=Two'
    assert links[0]['anchor_text'] == 'Destination label'
    assert links[0]['type'] == 'navigation'
    assert links[1]['anchor_text'] == 'Hero'
    assert all(isinstance(item, list) for item in result['data']['anchor_analysis']['most_common'])


@pytest.mark.parametrize('attributes,expected', [({}, False), ({'async': ''}, True),
                                               ({'defer': 'false'}, True), ({'type': 'module'}, True)])
def test_nonblocking_script_helper_accepts_primitive_attributes(attributes, expected):
    assert is_nonblocking_script(copy.deepcopy(attributes)) is expected
