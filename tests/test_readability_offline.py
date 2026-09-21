"""Readability must not download optional dictionaries during analysis."""

import json
import socket
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from tfq0seo.analyzers import content
from tfq0seo.core.models import validate_analyzer_result


TEXT = ('This simple guide explains how people can read and understand a useful article. ' * 12).strip()


@pytest.fixture
def forbid_network(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError('Readability must not request network access or dictionary downloads')

    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    nltk = pytest.importorskip('nltk')
    monkeypatch.setattr(nltk, 'download', forbidden)
    yield calls
    assert calls == []


def test_missing_local_dictionary_returns_null_estimates_without_downloading(monkeypatch, tmp_path, forbid_network):
    nltk = pytest.importorskip('nltk')
    monkeypatch.setattr(nltk.data, 'path', [str(tmp_path)])
    for _ in range(2):
        result = content.calculate_advanced_readability(TEXT, 'en')
        assert result['status'] == 'unavailable'
        assert result['source'] == 'textstat'
        assert result['resource_policy'] == 'local_only'
        assert result['missing_resources'] == ['nltk:corpora/cmudict']
        assert 'Runtime resource downloads are disabled' in result['reason']
        assert all(result[key] is None for key in content._READABILITY_VALUES)
        assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_corrupt_local_dictionary_archive_is_unavailable_without_downloading(monkeypatch, tmp_path, forbid_network):
    nltk = pytest.importorskip('nltk')
    archive = tmp_path / 'corpora' / 'cmudict.zip'
    archive.parent.mkdir()
    archive.write_bytes(b'Not a ZIP archive')
    monkeypatch.setattr(nltk.data, 'path', [str(tmp_path)])
    result = content.calculate_advanced_readability(TEXT, 'en')
    assert result['status'] == 'unavailable'
    assert result['consensus_grade'] is None


def test_english_analyzer_marks_readability_unknown_when_local_dictionary_is_missing(monkeypatch, tmp_path, forbid_network):
    nltk = pytest.importorskip('nltk')
    monkeypatch.setattr(nltk.data, 'path', [str(tmp_path)])
    soup = BeautifulSoup('<html lang="en"><head><title>Guide</title></head><body><h1>Guide</h1><p>' +
                         TEXT + '</p></body></html>', 'html.parser')
    result = content.analyze_content(soup, 'https://example.test/guide')
    validate_analyzer_result(result)
    assert result['data']['language'] == 'en'
    assert result['data']['readability']['status'] == 'unavailable'
    assert 'Difficult to read' not in result['data']['quality_assessment']['weaknesses']
    for rule_id in ('content.readability_difficult', 'content.readability_grade'):
        rule = next(item for item in result['rule_results'] if item['rule_id'] == rule_id)
        assert rule['status'] == 'unknown'
        assert rule['evidence']['value'] is None
        assert rule['evidence']['measurement_status'] == 'unavailable'
        assert 'local NLTK' in rule['reason']
        assert rule['penalty'] == 0


def test_installed_local_dictionary_allows_real_textstat_estimates(monkeypatch, tmp_path, forbid_network):
    nltk = pytest.importorskip('nltk')
    from nltk.corpus.reader import CMUDictCorpusReader
    from textstat.backend.utils._get_cmudict import get_cmudict
    from textstat.backend.counts._count_syllables import count_syllables

    dictionary = tmp_path / 'corpora' / 'cmudict'
    dictionary.mkdir(parents=True)
    (dictionary / 'cmudict').write_text('GUIDE 1 G AY1 D\nARTICLE 1 AA1 R T IH0 K AH0 L\n', encoding='utf-8')
    monkeypatch.setattr(nltk.data, 'path', [str(tmp_path)])
    monkeypatch.setattr(nltk.corpus, 'cmudict', CMUDictCorpusReader(str(dictionary), ['cmudict']))
    get_cmudict.cache_clear()
    count_syllables.cache_clear()
    try:
        result = content.calculate_advanced_readability(TEXT, 'en')
        assert result['status'] == 'estimate', result
        assert result['resource_policy'] == 'local_only'
        assert result['missing_resources'] == []
        assert isinstance(result['flesch_reading_ease'], (int, float))
        assert isinstance(result['consensus_grade'], (int, float))
        assert result['syllable_count'] > 0
        assert 'error' not in result
        assert json.loads(json.dumps(result, allow_nan=False)) == result
    finally:
        get_cmudict.cache_clear()
        count_syllables.cache_clear()


def test_legacy_packaged_resource_backend_does_not_require_nltk_corpus(monkeypatch, forbid_network):
    nltk = pytest.importorskip('nltk')

    def unexpected_lookup(*args, **kwargs):
        raise AssertionError('Legacy textstat uses packaged dictionaries')

    monkeypatch.setattr(nltk.data, 'find', unexpected_lookup)
    # textstat 0.7.3-0.7.5 expose these metric methods without a backend package.
    method_names = ('flesch_reading_ease', 'flesch_kincaid_grade', 'gunning_fog', 'smog_index',
                    'automated_readability_index', 'coleman_liau_index', 'linsear_write_formula',
                    'dale_chall_readability_score', 'text_standard', 'reading_time',
                    'syllable_count', 'polysyllabcount', 'sentence_count')
    legacy = SimpleNamespace(**{name: (lambda *args, **kwargs: 12.0) for name in method_names})
    monkeypatch.setattr(content, 'textstat', legacy)
    result = content.calculate_advanced_readability(TEXT, 'en')
    assert result['status'] == 'estimate'
    assert result['consensus_grade'] == 12.0


def test_non_english_readability_does_not_check_or_download_english_resources(monkeypatch, forbid_network):
    def unexpected_check():
        raise AssertionError('English resource checks are not applicable')

    monkeypatch.setattr(content, '_readability_resource_error', unexpected_check)
    result = content.calculate_advanced_readability('هذا نص عربي للاختبار.', 'ar')
    assert result['status'] == 'not_applicable'
    assert 'flesch_reading_ease' not in result


def test_local_metric_failure_does_not_leave_partial_or_fabricated_estimates(monkeypatch, forbid_network):
    monkeypatch.setattr(content, '_readability_resource_error', lambda: None)
    monkeypatch.setattr(content.textstat, 'flesch_reading_ease', lambda text: 73.0)

    def failed_metric(text):
        raise LookupError('Local dictionary file cannot be read')

    monkeypatch.setattr(content.textstat, 'flesch_kincaid_grade', failed_metric)
    result = content.calculate_advanced_readability(TEXT, 'en')
    assert result['status'] == 'unavailable'
    assert 'cannot be read' in result['error']
    assert all(result[key] is None for key in content._READABILITY_VALUES)
