"""Legacy files require an explicit, loss-aware configuration migration."""

import copy
import json
import math
from dataclasses import fields

import pytest

from tfq0seo.core.config import (
    AnalysisConfig, Config, ConfigProfile, CrawlerConfig, ExportConfig,
    OutputFormat, _RETIRED_DEFAULTS,
)


def test_serialization_contains_only_active_settings():
    cfg = Config()
    saved = cfg.to_dict()
    assert set(saved) == {
        'crawler', 'analysis', 'export', 'profile', 'version', 'debug',
        'continue_on_error', 'max_memory_mb',
    }
    assert set(Config.SUPPORTED_FIELDS) == {'crawler', 'analysis', 'export'}
    for section, component in (
        ('crawler', CrawlerConfig), ('analysis', AnalysisConfig), ('export', ExportConfig),
    ):
        active = {item.name for item in fields(component)}
        assert Config.SUPPORTED_FIELDS[section] == active
        assert not active.intersection(_RETIRED_DEFAULTS[section])
        assert set(saved[section]) == active - {'concurrent_requests'}
    assert {item.value for item in OutputFormat} == {'html', 'json', 'csv', 'xlsx'}


def test_all_known_historical_defaults_can_be_explicitly_migrated():
    legacy = copy.deepcopy(_RETIRED_DEFAULTS)
    legacy.update(legacy.pop('global'))
    legacy.update({'profile': 'deep', 'debug': True})
    legacy['crawler'].update({'max_pages': 17, 'concurrent_requests': 3})
    legacy['analysis']['target_keywords'] = ['migration']
    legacy['export']['formats'] = ['html', 'json']
    before = copy.deepcopy(legacy)

    migrated, warnings = Config.migrate_dict(legacy)

    assert legacy == before
    assert migrated == {
        'profile': 'deep', 'debug': True,
        'crawler': {'max_pages': 17, 'max_concurrent': 3},
        'analysis': {'target_keywords': ['migration']},
        'export': {'formats': ['html', 'json']},
    }
    for section, defaults in _RETIRED_DEFAULTS.items():
        for name in defaults:
            path = name if section == 'global' else section + '.' + name
            assert any(path in warning for warning in warnings)
    assert any('monitoring section' in warning for warning in warnings)
    assert any('concurrent_requests to crawler.max_concurrent' in warning for warning in warnings)
    resolved = Config.from_dict(migrated)
    assert resolved.crawler.max_depth == 10
    assert resolved.crawler.max_pages == 17
    assert resolved.debug is True


def test_migration_preserves_sparse_profile_overrides_and_copies_nested_values():
    original = {'profile': ConfigProfile.QUICK, 'crawler': {'max_pages': 17},
                'analysis': {'target_keywords': ['initial']}}
    migrated, warnings = Config.migrate_dict(original)
    assert migrated['profile'] == 'quick'
    assert set(migrated) == {'profile', 'crawler', 'analysis'}
    assert warnings == []
    resolved = Config.from_dict(migrated).merge({'profile': 'deep'})
    assert resolved.crawler.max_pages == 17
    assert resolved.crawler.max_depth == 10
    migrated['analysis']['target_keywords'].append('changed')
    assert original['analysis']['target_keywords'] == ['initial']
    assert Config.migrate_dict({}) == ({}, [])


@pytest.mark.parametrize('section,name,value', [
    ('crawler', 'execute_javascript', True),
    ('crawler', 'normalize_urls', False),
    ('analysis', 'check_alt_text', False),
    ('analysis', 'max_lcp', 5.0),
    ('export', 'send_email', True),
    ('export', 'html_theme', 'dark'),
    ('monitoring', 'enabled', True),
    ('monitoring', 'log_to_file', False),
    ('global', 'dry_run', True),
    ('global', 'temp_directory', '/custom'),
    ('global', 'features', {'custom': True}),
    ('global', 'metadata', {'custom': 'value'}),
])
def test_migration_rejects_requested_unsupported_behavior(section, name, value):
    data = {name: value} if section == 'global' else {section: {name: value}}
    before = copy.deepcopy(data)
    with pytest.raises(ValueError, match='cannot be migrated automatically') as caught:
        Config.migrate_dict(data)
    assert name in str(caught.value)
    assert 'docs/configuration-migration.md' in str(caught.value)
    assert data == before


@pytest.mark.parametrize('section,name,value', [
    ('crawler', 'parse_javascript', 0),
    ('crawler', 'include_query_strings', 1),
    ('crawler', 'semaphore_limit', 30.0),
    ('crawler', 'wait_for_javascript', False),
    ('crawler', 'user_agent_list', ()),
    ('analysis', 'validate_anchors', 1),
    ('analysis', 'max_image_size_kb', 500.0),
    ('export', 'data_sampling_rate', True),
    ('export', 'include_har_files', 0),
    ('export', 'smtp_port', '587'),
    ('export', 'smtp_password', ''),
    ('monitoring', 'enabled', 0),
    ('monitoring', 'metrics_interval', 60.0),
    ('monitoring', 'progress_update_interval', math.inf),
    ('global', 'dry_run', 0),
    ('global', 'features', []),
    ('global', 'metadata', None),
])
def test_invalid_legacy_types_are_not_silently_dropped(section, name, value):
    data = {name: value} if section == 'global' else {section: {name: value}}
    with pytest.raises(ValueError, match='invalid type'):
        Config.migrate_dict(data)


@pytest.mark.parametrize('number', [math.nan, math.inf, -math.inf, 10 ** 400])
def test_nonfinite_or_unrepresentable_legacy_numbers_fail_cleanly(number):
    with pytest.raises(ValueError, match='invalid type'):
        Config.migrate_dict({'analysis': {'max_fid': number}})


def test_declared_legacy_float_defaults_accept_finite_integer_equivalents():
    migrated, _ = Config.migrate_dict({
        'crawler': {'wait_for_javascript': 0},
        'analysis': {'max_fid': 100.0, 'max_page_load_time': 3},
        'monitoring': {'alert_thresholds': {
            'error_rate': 0.05, 'avg_response_time': 5,
            'memory_usage_mb': 500.0, 'broken_links_ratio': 0.10,
        }},
    })
    assert migrated == {'crawler': {}, 'analysis': {}}


@pytest.mark.parametrize('data', [
    {'export': {'send_email': False, 'smtp_password': 'PRIVATE-VALUE'}},
    {'export': {'send_to_api': False, 'api_key': 'PRIVATE-VALUE'}},
    {'monitoring': {'webhook_enabled': False, 'webhook_url': 'PRIVATE-VALUE'}},
    {'profile': 'PRIVATE-VALUE'},
    {'crawler': {'excluded_patterns': ['[PRIVATE-VALUE']}},
    {'crawler': {'concurrent_requests': 'PRIVATE-VALUE'}},
    {'analysis': {'score_weights': 'PRIVATE-VALUE'}},
])
def test_migration_errors_never_echo_supplied_values(data):
    with pytest.raises(ValueError) as caught:
        Config.migrate_dict(data)
    assert 'PRIVATE-VALUE' not in str(caught.value)


@pytest.mark.parametrize('data', [
    [], None, {'unknown': 'value'}, {'crawler': {'unknown': 'value'}},
    {'monitoring': {'unknown': 'value'}}, {'crawler': None},
    {'analysis': []}, {'export': 'value'}, {'monitoring': False},
    {3: 'value'}, {'crawler': {3: 'value'}},
    {'crawler': {'max_pages': 0}}, {'debug': 1},
])
def test_migration_also_validates_active_settings_and_mapping_structure(data):
    with pytest.raises(ValueError):
        Config.migrate_dict(data)


@pytest.mark.parametrize('alias,canonical,value', [
    ('concurrent_requests', 'max_concurrent', 3),
    ('max_content_length', 'max_page_size', 1000),
    ('retry_attempts', 'max_retries', 1),
    ('adaptive_throttle', 'adaptive_delay', False),
    ('follow_sitemap', 'use_sitemap', False),
])
def test_migration_keeps_functional_aliases_and_rejects_conflicts(alias, canonical, value):
    data, warnings = Config.migrate_dict({'crawler': {alias: value}})
    assert data == {'crawler': {canonical: value}}
    assert len(warnings) == 1
    assert alias in warnings[0] and canonical in warnings[0]
    conflict = not value if isinstance(value, bool) else value + 1
    with pytest.raises(ValueError, match='Conflicting'):
        Config.migrate_dict({'crawler': {alias: value, canonical: conflict}})


@pytest.mark.parametrize('values', [
    {'concurrent_requests': True, 'max_concurrent': 1},
    {'concurrent_requests': 1, 'max_concurrent': True},
    {'adaptive_throttle': 0, 'adaptive_delay': False},
    {'follow_sitemap': True, 'use_sitemap': 1},
])
def test_alias_equality_cannot_hide_invalid_boolean_numeric_types(values):
    for constructor in (Config.from_dict, Config.migrate_dict):
        with pytest.raises(ValueError, match='invalid type'):
            constructor({'crawler': values})


def test_null_concurrency_alias_is_still_explicitly_empty():
    migrated, warnings = Config.migrate_dict({
        'crawler': {'concurrent_requests': None, 'max_concurrent': 7},
    })
    assert migrated == {'crawler': {'max_concurrent': 7}}
    assert 'empty crawler.concurrent_requests' in warnings[0]


@pytest.mark.parametrize('data', [
    {'crawler': {'parse_javascript': False}},
    {'analysis': {'check_images': True}},
    {'export': {'send_email': False}},
    {'monitoring': {}}, {'dry_run': False}, {'temp_directory': './temp'},
])
def test_regular_loading_and_merging_require_explicit_migration(data):
    for constructor in (Config.from_dict, Config().merge):
        with pytest.raises(ValueError, match=r'Config\.migrate_dict\(\)'):
            constructor(data)


@pytest.mark.parametrize('suffix', ['.json', '.yaml'])
def test_saved_legacy_files_migrate_then_roundtrip(tmp_path, suffix):
    legacy = {'profile': 'quick', 'crawler': {'max_pages': 7, 'use_http2': False},
              'monitoring': {}, 'export': {'send_email': False}}
    old = tmp_path / 'legacy.json'
    old.write_text(json.dumps(legacy), encoding='utf-8')
    with pytest.raises(ValueError, match='retired'):
        Config.from_file(old)
    canonical, warnings = Config.migrate_dict(json.loads(old.read_text(encoding='utf-8')))
    assert warnings
    cfg = Config.from_dict(canonical)
    new = tmp_path / ('migrated' + suffix)
    cfg.save(new)
    assert Config.from_file(new).to_dict() == cfg.to_dict()
    assert 'monitoring' not in cfg.to_dict()
    assert old.read_text(encoding='utf-8') == json.dumps(legacy)


@pytest.mark.parametrize('key,value', [
    ('CRAWLER_PARSE_JAVASCRIPT', 'false'), ('ANALYSIS_CHECK_IMAGES', 'true'),
    ('EXPORT_SEND_EMAIL', 'false'), ('MONITORING_ENABLED', 'false'), ('DRY_RUN', 'false'),
])
def test_retired_environment_keys_require_explicit_removal(monkeypatch, key, value):
    monkeypatch.setenv('CONFIG_MIGRATION_TEST_' + key, value)
    with pytest.raises(ValueError, match='retired'):
        Config.from_env('CONFIG_MIGRATION_TEST_')


def test_environment_aliases_keep_canonical_type_parsing(monkeypatch):
    prefix = 'CONFIG_MIGRATION_TEST_'
    monkeypatch.setenv(prefix + 'CRAWLER_FOLLOW_SITEMAP', 'no')
    monkeypatch.setenv(prefix + 'CRAWLER_ADAPTIVE_THROTTLE', 'yes')
    monkeypatch.setenv(prefix + 'CRAWLER_CONCURRENT_REQUESTS', 'null')
    monkeypatch.setenv(prefix + 'CRAWLER_MAX_CONCURRENT', '3')
    cfg = Config.from_env(prefix)
    assert cfg.crawler.use_sitemap is False
    assert cfg.crawler.adaptive_delay is True
    assert cfg.crawler.effective_concurrency == 3


@pytest.mark.parametrize('section,name,value', [
    ('crawler', 'execute_javascript', False),
    ('analysis', 'check_images', True),
    ('export', 'send_email', False),
    ('global', 'temp_directory', './temp'),
    ('global', 'monitoring', {}),
])
def test_attached_retired_attributes_cannot_be_silently_serialized(section, name, value):
    cfg = Config()
    target = cfg if section == 'global' else getattr(cfg, section)
    setattr(target, name, value)
    assert cfg.validate()
    with pytest.raises(ValueError, match='retired'):
        cfg.to_dict()
    if section == 'crawler':
        with pytest.raises(ValueError, match='retired'):
            cfg.crawler.as_dict()


def test_migration_has_no_filesystem_side_effects(tmp_path):
    output = tmp_path / 'not-created'
    canonical, _ = Config.migrate_dict({
        'export': {'output_directory': str(output), 'send_email': False},
        'temp_directory': './temp',
    })
    assert canonical == {'export': {'output_directory': str(output)}}
    assert not output.exists()
