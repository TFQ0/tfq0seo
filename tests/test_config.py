import math

import pytest

from tfq0seo.core.config import Config, ConfigProfile, CrawlerConfig


def test_profile_precedes_explicit_values():
    cfg = Config.from_dict({'profile': 'quick', 'crawler': {'max_pages': 17}})
    assert cfg.crawler.max_pages == 17
    assert cfg.analysis.analysis_mode == 'quick'
    assert cfg.analysis.enabled_analyzers == ['seo', 'technical']
    assert Config(profile=ConfigProfile.DEVELOPMENT).crawler.verify_ssl is True


@pytest.mark.parametrize('first', ['quick', 'standard', 'deep', 'enterprise', 'dev'])
@pytest.mark.parametrize('second', ['quick', 'standard', 'deep', 'enterprise', 'dev'])
def test_reapplying_profiles_matches_fresh_profile_defaults(first, second):
    cfg = Config(profile=first)
    cfg.apply_profile(second)
    assert cfg.to_dict() == Config(profile=second).to_dict()


def test_apply_profile_replaces_controlled_overrides_and_keeps_unrelated_values():
    cfg = Config.from_dict({
        'profile': 'quick', 'crawler': {'max_pages': 17, 'user_agent': 'CustomAgent/1.0'},
        'analysis': {'target_keywords': ['example']},
    })
    cfg.apply_profile('standard')
    assert cfg.crawler.max_pages == 500
    assert cfg.analysis.analysis_mode == 'standard'
    assert cfg.crawler.user_agent == 'CustomAgent/1.0'
    assert cfg.analysis.target_keywords == ['example']
    # Applying a preset explicitly must not resurrect the old max_pages later.
    assert cfg.merge({'profile': 'deep'}).crawler.max_pages == 1000


def test_merge_profile_still_preserves_explicit_overrides():
    cfg = Config.from_dict({'profile': 'quick', 'crawler': {'max_pages': 17}})
    merged = cfg.merge({'profile': 'standard'})
    assert merged.crawler.max_pages == 17
    assert merged.analysis.analysis_mode == 'standard'
    assert merged.analysis.enabled_analyzers == Config().analysis.enabled_analyzers


def test_custom_profile_preserves_current_settings():
    cfg = Config(profile='quick')
    before = cfg.to_dict()
    cfg.apply_profile('custom')
    before['profile'] = 'custom'
    assert cfg.to_dict() == before


def test_constructor_debug_override_survives_initial_profile_application():
    cfg = Config(profile='quick', debug=True)
    assert cfg.debug is True
    cfg.apply_profile('standard')
    assert cfg.debug is False


def test_crawler_profile_clears_stale_concurrency_alias():
    cfg = CrawlerConfig(concurrent_requests=2, max_pages=17, user_agent='CustomAgent/1.0')
    cfg.apply_profile('standard')
    assert cfg.concurrent_requests is None
    assert cfg.effective_concurrency == CrawlerConfig().effective_concurrency
    assert cfg.max_pages == CrawlerConfig().max_pages
    assert cfg.user_agent == 'CustomAgent/1.0'


def test_merge_does_not_reset_unrelated_values():
    cfg = Config()
    cfg.crawler.max_pages = 123
    cfg.analysis.target_keywords = ['example']
    merged = cfg.merge({'debug': True})
    assert merged.debug
    assert merged.crawler.max_pages == 123
    assert merged.analysis.target_keywords == ['example']
    assert cfg.debug is False


@pytest.mark.parametrize('data', [
    {'crawler': {'max_pages': 0}}, {'crawler': {'max_depth': -1}},
    {'crawler': {'max_concurrent': 0}}, {'crawler': {'timeout': '30'}},
    {'crawler': {'rate_limit_per_second': 0}}, {'crawler': {'retry_backoff_factor': math.nan}},
    {'crawler': {'excluded_patterns': ['[']}}, {'crawler': {'max_pages': True}},
    {'crawler': {'execute_javascript': True}}, {'crawler': {'use_http2': True}},
    {'analysis': {'enabled_analyzers': ['missing']}}, {'analysis': {'enabled_analyzers': []}},
    {'analysis': {'score_weights': {'seo': -1.0, 'content': 2.0}}},
    {'analysis': {'score_weights': {'seo': math.inf}}},
    {'export': {'formats': ['pdf']}}, {'export': {'send_email': True}},
    {'dry_run': True}, {'crawler': {'typo': 1}}, {'typo': 1}, [],
])
def test_invalid_settings_fail(data):
    with pytest.raises((ValueError, TypeError)):
        Config.from_dict(data)


def test_concurrency_alias_and_conflict():
    cfg = Config.from_dict({'crawler': {'concurrent_requests': 1}})
    assert cfg.crawler.effective_concurrency == 1
    assert cfg.crawler.as_dict()['max_concurrent'] == 1
    assert 'concurrent_requests' not in cfg.crawler.as_dict()
    with pytest.raises(ValueError, match='Conflicting'):
        Config.from_dict({'crawler': {'concurrent_requests': 2, 'max_concurrent': 3}})


@pytest.mark.parametrize('alias,canonical,value', [
    ('max_content_length', 'max_page_size', 1024),
    ('retry_attempts', 'max_retries', 2),
    ('adaptive_throttle', 'adaptive_delay', False),
    ('follow_sitemap', 'use_sitemap', False),
])
def test_legacy_aliases_are_canonicalized_without_mutating_input(alias, canonical, value):
    data = {'crawler': {alias: value}}
    cfg = Config.from_dict(data)
    assert getattr(cfg.crawler, canonical) == value
    assert data == {'crawler': {alias: value}}
    with pytest.raises(ValueError, match='Conflicting'):
        Config.from_dict({'crawler': {alias: value, canonical: not value if isinstance(value, bool) else value + 1}})


def test_null_concurrency_alias_does_not_override_canonical_value():
    cfg = Config.from_dict({'crawler': {'concurrent_requests': None, 'max_concurrent': 7}})
    assert cfg.crawler.effective_concurrency == 7


@pytest.mark.parametrize('suffix', ['.json', '.yaml'])
def test_config_roundtrip(tmp_path, suffix):
    cfg = Config.from_dict({'profile': 'quick', 'crawler': {'max_pages': 7}})
    path = tmp_path / ('config' + suffix)
    cfg.save(path)
    assert Config.from_file(path).to_dict() == cfg.to_dict()


def test_bad_file_is_not_silently_replaced(tmp_path):
    with pytest.raises(FileNotFoundError):
        Config.from_file(tmp_path / 'missing.json')
    path = tmp_path / 'broken.json'
    path.write_text('{bad', encoding='utf-8')
    with pytest.raises(ValueError):
        Config.from_file(path)


def test_environment_uses_the_same_types_and_profiles(monkeypatch):
    monkeypatch.setenv('TFQ0SEO_PROFILE', 'quick')
    monkeypatch.setenv('TFQ0SEO_CRAWLER_MAX_PAGES', '12')
    monkeypatch.setenv('TFQ0SEO_ANALYSIS_TARGET_KEYWORDS', 'one')
    monkeypatch.setenv('TFQ0SEO_CRAWLER_VERIFY_SSL', 'true')
    cfg = Config.from_env()
    assert cfg.analysis.analysis_mode == 'quick'
    assert cfg.crawler.max_pages == 12
    assert cfg.analysis.target_keywords == ['one']
    assert cfg.crawler.verify_ssl is True


def test_validation_has_no_filesystem_side_effects(tmp_path):
    cfg = Config()
    cfg.export.output_directory = str(tmp_path / 'unused')
    assert cfg.validate() == {}
    assert not (tmp_path / 'unused').exists()
