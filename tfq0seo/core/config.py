"""Advanced configuration management with validation, presets, and dynamic profiles."""

import os
import json
import yaml
import math
import re
import copy
from dataclasses import dataclass, field, asdict, fields
from typing import Dict, Optional, List, Any, Union, Tuple, get_args, get_origin, get_type_hints
from enum import Enum
from pathlib import Path


class ConfigProfile(Enum):
    """Predefined configuration profiles."""
    QUICK = "quick"          # Fast, minimal analysis
    STANDARD = "standard"    # Balanced, default
    DEEP = "deep"           # Comprehensive analysis
    ENTERPRISE = "enterprise"  # Large-scale, optimized
    DEVELOPMENT = "dev"     # Testing/development
    CUSTOM = "custom"       # User-defined


class OutputFormat(Enum):
    """Supported output formats."""
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CrawlerConfig:
    """Advanced crawler configuration with validation."""
    PROFILE_FIELDS = ('max_concurrent', 'concurrent_requests', 'max_pages', 'max_depth',
                      'timeout', 'max_retries', 'cache_enabled', 'use_connection_pooling',
                      'adaptive_delay')
    # Concurrency and request timeouts
    max_concurrent: int = 20
    concurrent_requests: Optional[int] = None  # Legacy alias; max_concurrent is canonical.
    max_connections_per_host: int = 5
    timeout: int = 30
    connect_timeout: int = 10
    read_timeout: int = 30

    # Request headers and redirects
    user_agent: str = "tfq0seo/3.0.0 (+https://github.com/TFQ0/tfq0seo)"
    custom_headers: Dict[str, str] = field(default_factory=dict)
    follow_redirects: bool = True
    max_redirects: int = 10

    # Crawl limits and rate limiting
    max_pages: int = 500
    max_depth: int = 5
    max_page_size: int = 10485760  # 10MB
    max_crawl_time: int = 3600  # 1 hour
    delay_between_requests: float = 0.0
    adaptive_delay: bool = True
    min_delay: float = 0.0
    max_delay: float = 5.0
    rate_limit_per_second: Optional[float] = None

    # Robots and URL filtering
    respect_robots_txt: bool = True
    robots_cache_ttl: int = 86400  # 24 hours
    crawl_delay_factor: float = 1.0  # Multiplier for robots.txt delay
    allowed_domains: List[str] = field(default_factory=list)
    allowed_schemes: List[str] = field(default_factory=lambda: ['http', 'https'])
    excluded_patterns: List[str] = field(default_factory=lambda: [
        r'\.pdf$', r'\.zip$', r'\.exe$', r'\.dmg$',
        r'/wp-admin', r'/admin', r'/login',
        r'\?.*session', r'\?.*utm_'
    ])

    # Response storage, retries, and cache
    store_html: bool = False
    max_retries: int = 3
    retry_on_status: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retry_backoff_factor: float = 2.0
    cache_enabled: bool = True
    cache_ttl: int = 3600
    cache_size_mb: int = 100

    # Discovery and connections
    use_sitemap: bool = True
    discover_sitemaps: bool = True
    use_connection_pooling: bool = True
    dns_cache_ttl: int = 300
    verify_ssl: bool = True
    proxy: Optional[str] = None

    @property
    def effective_concurrency(self) -> int:
        return self.concurrent_requests if self.concurrent_requests is not None else self.max_concurrent

    def as_dict(self) -> Dict[str, Any]:
        errors = _unexpected_field_issues(self, 'crawler')
        if errors:
            raise ValueError('; '.join(errors))
        values = asdict(self)
        values['max_concurrent'] = self.effective_concurrency
        values.pop('concurrent_requests', None)
        return values

    def validate(self) -> List[str]:
        issues = []
        for name in ('max_concurrent', 'max_connections_per_host', 'timeout', 'connect_timeout',
                     'read_timeout', 'max_pages', 'max_page_size', 'max_crawl_time', 'cache_size_mb'):
            if getattr(self, name) <= 0:
                issues.append(f"{name} must be positive")
        if self.concurrent_requests is not None and self.concurrent_requests <= 0:
            issues.append('concurrent_requests must be positive')
        for name in ('max_depth', 'max_redirects', 'max_retries', 'delay_between_requests',
                     'retry_backoff_factor', 'min_delay', 'max_delay', 'cache_ttl', 'robots_cache_ttl'):
            if getattr(self, name) < 0:
                issues.append(f"{name} must be non-negative")
        if self.rate_limit_per_second is not None and self.rate_limit_per_second <= 0:
            issues.append('rate_limit_per_second must be positive')
        if self.max_delay < self.min_delay:
            issues.append('max_delay must be at least min_delay')
        if not self.allowed_schemes or set(self.allowed_schemes) - {'http', 'https'}:
            issues.append('allowed_schemes must contain only http and/or https')
        for index, pattern in enumerate(self.excluded_patterns):
            try:
                re.compile(pattern)
            except re.error:
                issues.append(f'excluded_patterns[{index}] is not a valid regular expression')
        if any(code < 400 or code > 599 for code in self.retry_on_status):
            issues.append('retry_on_status must contain HTTP error status codes')
        return issues

    def apply_profile(self, profile: ConfigProfile) -> None:
        """Replace preset-controlled values; CUSTOM leaves current values intact."""
        profile = ConfigProfile(profile)
        if profile == ConfigProfile.CUSTOM:
            return
        defaults = CrawlerConfig()
        for name in self.PROFILE_FIELDS:
            setattr(self, name, getattr(defaults, name))
        if profile == ConfigProfile.QUICK:
            self.max_concurrent = 30
            self.max_pages = 50
            self.max_depth = 2
            self.timeout = 10
            self.max_retries = 1
            self.cache_enabled = True
        elif profile == ConfigProfile.DEEP:
            self.max_concurrent = 10
            self.max_pages = 1000
            self.max_depth = 10
            self.timeout = 60
            self.max_retries = 5
        elif profile == ConfigProfile.ENTERPRISE:
            self.max_concurrent = 50
            self.max_pages = 10000
            self.max_depth = 20
            self.use_connection_pooling = True
            self.adaptive_delay = True
        elif profile == ConfigProfile.DEVELOPMENT:
            self.max_concurrent = 5
            self.max_pages = 10
            self.max_depth = 2


@dataclass
class AnalysisConfig:
    """Advanced analysis configuration."""
    enabled_analyzers: List[str] = field(default_factory=lambda: [
        'seo', 'content', 'technical', 'performance', 'links'
    ])
    analysis_mode: str = "standard"  # quick, standard, deep
    parallel_analysis: bool = True
    max_analysis_threads: int = 4

    # Link and content analysis
    check_external_links: bool = False
    check_internal_links: bool = True
    check_broken_links: bool = True
    max_external_links_per_page: int = 100
    external_link_timeout: int = 10
    target_keywords: List[str] = field(default_factory=list)
    check_content_uniqueness: bool = True

    score_weights: Dict[str, float] = field(default_factory=lambda: {
        'seo': 0.30,
        'content': 0.25,
        'technical': 0.20,
        'performance': 0.15,
        'links': 0.10
    })

    def validate(self) -> List[str]:
        issues = []
        known = {'seo', 'content', 'technical', 'performance', 'links'}
        if not self.enabled_analyzers or set(self.enabled_analyzers) - known:
            issues.append('enabled_analyzers must select known analyzers')
        if len(set(self.enabled_analyzers)) != len(self.enabled_analyzers):
            issues.append('enabled_analyzers must not contain duplicates')
        if self.analysis_mode not in {'quick', 'standard', 'deep', 'custom'}:
            issues.append('Unknown analysis_mode')
        if set(self.score_weights) - known or any(v < 0 for v in self.score_weights.values()):
            issues.append('score_weights must use known analyzers and non-negative values')
        if not math.isclose(sum(self.score_weights.values()), 1.0, abs_tol=1e-9):
            issues.append('Score weights must sum to 1.0')
        if not any(self.score_weights.get(name, 0) > 0 for name in self.enabled_analyzers):
            issues.append('At least one enabled analyzer must have positive weight')
        if self.max_analysis_threads <= 0:
            issues.append('max_analysis_threads must be positive')
        if self.max_external_links_per_page <= 0 or self.external_link_timeout <= 0:
            issues.append('External link limits must be positive')
        return issues


@dataclass
class ExportConfig:
    """Advanced export configuration."""
    formats: List[str] = field(default_factory=lambda: ['html'])
    primary_format: str = 'html'
    html_template: str = "optimized"  # report, enhanced, optimized
    output_directory: str = "./reports"
    filename_pattern: str = "{domain}_{timestamp}_{format}"

    def validate(self) -> List[str]:
        issues = []
        if not self.formats or set(self.formats) - {'html', 'json', 'csv', 'xlsx'}:
            issues.append('Supported export formats are html, json, csv, xlsx')
        if self.primary_format not in self.formats:
            issues.append('primary_format must be present in formats')
        if self.html_template not in {'report', 'enhanced', 'optimized'}:
            issues.append('Unknown html_template')
        return issues


def _matches_type(value: Any, expected: Any) -> bool:
    if expected is Any:
        return True
    origin, args = get_origin(expected), get_args(expected)
    if origin is Union:
        return any(_matches_type(value, option) for option in args)
    if origin is list:
        return isinstance(value, list) and all(_matches_type(item, args[0]) for item in value)
    if origin is dict:
        return isinstance(value, dict) and all(
            _matches_type(k, args[0]) and _matches_type(v, args[1]) for k, v in value.items())
    if expected is float:
        try:
            return type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            return False
    if expected in (bool, int):
        return type(value) is expected
    return isinstance(value, expected)


def _type_issues(obj: Any) -> List[str]:
    annotations = get_type_hints(type(obj))
    return [f"{item.name} has an invalid type or non-finite value"
            for item in fields(obj)
            if not _matches_type(getattr(obj, item.name), annotations[item.name])]


# Retired settings are migration metadata only, never active configuration fields.
# These historical defaults let explicit migration distinguish inert saved values
# from unsupported behavior that a caller deliberately requested.
_RETIRED_DEFAULTS = {
    'crawler': {
        'semaphore_limit': 30,
        'total_timeout': 300,
        'rotate_user_agents': False,
        'user_agent_list': [],
        'redirect_cache_ttl': 3600,
        'include_query_strings': True,
        'normalize_urls': True,
        'parse_javascript': False,
        'execute_javascript': False,
        'wait_for_javascript': 0.0,
        'compress_stored_html': True,
        'prioritize_sitemap_urls': True,
        'use_http2': False,
    },
    'analysis': {
        'validate_anchors': True,
        'check_images': True,
        'check_image_optimization': True,
        'check_alt_text': True,
        'check_image_dimensions': True,
        'max_image_size_kb': 500,
        'min_content_length': 100,
        'max_content_length': 100000,
        'optimal_content_length': 1500,
        'check_readability': True,
        'target_reading_level': 8,
        'check_keyword_density': True,
        'keyword_variations': True,
        'min_unique_content_ratio': 0.7,
        'check_meta_tags': True,
        'check_structured_data': True,
        'validate_structured_data': True,
        'check_open_graph': True,
        'check_twitter_cards': True,
        'check_canonical_urls': True,
        'check_hreflang': True,
        'check_sitemaps': True,
        'check_robots_txt': True,
        'check_https': True,
        'check_security_headers': True,
        'check_mixed_content': True,
        'check_mobile_friendly': True,
        'check_page_speed': True,
        'check_core_web_vitals': True,
        'check_compression': True,
        'check_caching': True,
        'check_minification': True,
        'check_http2': True,
        'max_page_load_time': 3.0,
        'max_ttfb': 0.8,
        'max_fcp': 1.8,
        'max_lcp': 2.5,
        'max_fid': 100.0,
        'max_cls': 0.1,
        'max_page_size_mb': 3.0,
        'check_accessibility': True,
        'wcag_level': 'AA',
    },
    'export': {
        'include_inline_css': True,
        'include_inline_js': True,
        'minify_html': True,
        'html_theme': 'light',
        'include_charts': True,
        'charts_library': 'chartjs',
        'include_raw_data': False,
        'include_page_content': False,
        'include_screenshots': False,
        'include_har_files': False,
        'data_sampling_rate': 1.0,
        'max_issues_per_page': 100,
        'max_pages_in_report': 1000,
        'create_subdirectories': True,
        'compress_output': False,
        'compression_format': 'zip',
        'split_large_reports': True,
        'split_threshold_mb': 50,
        'generate_summary': True,
        'generate_executive_report': True,
        'send_email': False,
        'email_recipients': [],
        'email_subject_template': 'SEO Report for {domain}',
        'smtp_server': None,
        'smtp_port': 587,
        'smtp_username': None,
        'smtp_password': None,
        'upload_to_cloud': False,
        'cloud_provider': None,
        'cloud_bucket': None,
        'cloud_path_prefix': None,
        'send_to_api': False,
        'api_endpoint': None,
        'api_key': None,
        'api_method': 'POST',
    },
    'monitoring': {
        'enabled': False,
        'collect_metrics': True,
        'metrics_interval': 60,
        'metrics_retention_days': 30,
        'enable_alerts': False,
        'alert_thresholds': {
            'error_rate': 0.05, 'avg_response_time': 5.0,
            'memory_usage_mb': 500.0, 'broken_links_ratio': 0.1,
        },
        'log_level': 'info',
        'log_to_file': True,
        'log_file_path': './logs/tfq0seo.log',
        'log_rotation': 'daily',
        'log_retention_days': 7,
        'log_format': 'json',
        'show_progress': True,
        'progress_update_interval': 1.0,
        'detailed_progress': False,
        'webhook_enabled': False,
        'webhook_url': None,
        'webhook_events': ['analysis_complete', 'error', 'threshold_exceeded'],
    },
    'global': {
        'dry_run': False,
        'temp_directory': './temp',
        'features': {},
        'metadata': {},
    },
}

_COMPONENT_TYPES = {'crawler': CrawlerConfig, 'analysis': AnalysisConfig, 'export': ExportConfig}
_CRAWLER_ALIASES = {
    'concurrent_requests': 'max_concurrent', 'max_content_length': 'max_page_size',
    'retry_attempts': 'max_retries', 'adaptive_throttle': 'adaptive_delay',
    'follow_sitemap': 'use_sitemap',
}


def _key_issues(keys, allowed, section: str) -> List[str]:
    """Describe keys, never supplied values (which may contain credentials)."""
    if any(not isinstance(key, str) for key in keys):
        return [f'{section} configuration keys must be strings']
    prefix = '' if section == 'global' else section + '.'
    retired = set(_RETIRED_DEFAULTS.get(section, {}))
    if section == 'global':
        retired.add('monitoring')
    issues = []
    for key in sorted(set(keys) - set(allowed)):
        if key in retired:
            issues.append(f'{prefix}{key} was retired in 3.0.0; use Config.migrate_dict() for legacy defaults '
                          'or remove this unsupported setting after reviewing docs/configuration-migration.md')
        else:
            issues.append(f'Unknown {section} configuration key: {key}')
    return issues


def _unexpected_field_issues(obj: Any, section: str) -> List[str]:
    allowed = {item.name for item in fields(obj)}
    # Config tracks explicit overrides privately; component settings have no private state.
    if section == 'global':
        allowed.add('_explicit_values')
    return _key_issues(vars(obj), allowed, section)


def _same_legacy_default(value: Any, default: Any) -> bool:
    """Use historical configuration types; bool and numeric equality are distinct."""
    if isinstance(default, dict):
        return (isinstance(value, dict) and value.keys() == default.keys() and
                all(_same_legacy_default(value[key], item) for key, item in default.items()))
    if isinstance(default, list):
        return (isinstance(value, list) and len(value) == len(default) and
                all(_same_legacy_default(item, expected) for item, expected in zip(value, default)))
    if type(default) is float:
        return _matches_type(value, float) and value == default
    return type(value) is type(default) and value == default


@dataclass
class Config:
    """Resolve profiles first, then explicit overrides; reject invalid input."""
    crawler: Optional[CrawlerConfig] = None
    analysis: Optional[AnalysisConfig] = None
    export: Optional[ExportConfig] = None
    profile: ConfigProfile = ConfigProfile.STANDARD
    version: str = '3.0.0'
    debug: bool = False  # Profile metadata only; configure Python logging separately.
    continue_on_error: bool = True
    max_memory_mb: int = 1024

    SUPPORTED_FIELDS = {
        name: frozenset(item.name for item in fields(component))
        for name, component in _COMPONENT_TYPES.items()
    }

    def __post_init__(self):
        supplied = {name: getattr(self, name) for name in _COMPONENT_TYPES}
        supplied_debug = self.debug
        self.crawler = CrawlerConfig()
        self.analysis = AnalysisConfig()
        self.export = ExportConfig()
        try:
            self.profile = ConfigProfile(self.profile)
        except (ValueError, TypeError):
            raise ValueError('profile must be quick, standard, deep, enterprise, dev, or custom') from None
        self.apply_profile(self.profile)
        if self.profile != ConfigProfile.DEVELOPMENT:
            self.debug = supplied_debug
        for name, component in supplied.items():
            if component is not None:
                setattr(self, name, component)

    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> 'Config':
        filepath = Path(filepath)
        with filepath.open(encoding='utf-8') as handle:
            if filepath.suffix.lower() == '.json':
                data = json.load(handle)
            elif filepath.suffix.lower() in ('.yaml', '.yml'):
                data = yaml.safe_load(handle)
            else:
                raise ValueError(f'Unsupported config format: {filepath.suffix}')
        return cls.from_dict({} if data is None else data)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Config':
        if not isinstance(data, dict):
            raise ValueError('Configuration must be an object')
        data = cls._canonical_overrides(data)
        errors = _key_issues(data, {item.name for item in fields(cls)}, 'global')
        if errors:
            raise ValueError('; '.join(errors))
        config = cls(profile=data.get('profile', 'standard'))
        for section in _COMPONENT_TYPES:
            values = data.get(section, {})
            if not isinstance(values, dict):
                raise ValueError(f'{section} must be an object')
            values = dict(values)
            target = getattr(config, section)
            allowed = {item.name for item in fields(target)}
            errors = _key_issues(values, allowed, section)
            if errors:
                raise ValueError('; '.join(errors))
            for name, value in values.items():
                setattr(target, name, value)
        for name, value in data.items():
            if name not in _COMPONENT_TYPES and name != 'profile':
                setattr(config, name, value)
        config._explicit_values = copy.deepcopy(data)
        config.require_valid()
        return config

    @staticmethod
    def _canonical_overrides(data: Dict) -> Dict:
        data = copy.deepcopy(data)
        values = data.get('crawler')
        if isinstance(values, dict):
            annotations = get_type_hints(CrawlerConfig)
            for alias, name in _CRAWLER_ALIASES.items():
                if alias in values:
                    value = values.pop(alias)
                    if value is None and alias == 'concurrent_requests':
                        continue
                    if not _matches_type(value, annotations[name]):
                        raise ValueError(f'crawler.{alias} has an invalid type or non-finite value')
                    if name in values and not _matches_type(values[name], annotations[name]):
                        raise ValueError(f'crawler.{name} has an invalid type or non-finite value')
                    if name in values and values[name] != value:
                        raise ValueError(f'Conflicting crawler settings: {alias} and {name}')
                    values[name] = value
        return data

    @classmethod
    def migrate_dict(cls, data: Dict) -> Tuple[Dict[str, Any], List[str]]:
        """Explicitly remove retired historical defaults and canonicalize aliases.

        Return validated, sparse overrides and value-free migration warnings.
        Unsupported non-default values, malformed input, and unknown keys fail;
        the original mapping remains untouched and no files or networks are used.
        """
        if not isinstance(data, dict):
            raise ValueError('Configuration must be an object')
        canonical = cls._canonical_overrides(data)
        allowed_global = {item.name for item in fields(cls)} | set(_RETIRED_DEFAULTS['global']) | {'monitoring'}
        errors = _key_issues(canonical, allowed_global, 'global')
        warnings = []
        for section in ('crawler', 'analysis', 'export', 'monitoring', 'global'):
            if section != 'global' and section not in canonical:
                continue
            values = canonical if section == 'global' else canonical[section]
            if not isinstance(values, dict):
                errors.append(f'{section} must be an object')
                continue
            defaults = _RETIRED_DEFAULTS[section]
            if section != 'global':
                errors.extend(_key_issues(values, set(cls.SUPPORTED_FIELDS.get(section, ())) | set(defaults), section))
            for name, default in defaults.items():
                if name not in values:
                    continue
                path = name if section == 'global' else section + '.' + name
                if not _same_legacy_default(values[name], default):
                    errors.append(f'{path} cannot be migrated automatically: it requests an unsupported non-default '
                                  'value or has an invalid type; review docs/configuration-migration.md and remove it explicitly')
                else:
                    del values[name]
                    warnings.append(f'Removed retired setting {path} at its historical default.')
            if section == 'monitoring' and not values:
                del canonical[section]
                warnings.append('Removed the retired monitoring section.')
        if errors:
            raise ValueError('; '.join(errors))
        for alias, target in _CRAWLER_ALIASES.items():
            if isinstance(data.get('crawler'), dict) and alias in data['crawler']:
                warnings.append(f'Canonicalized crawler.{alias} to crawler.{target}.'
                                if data['crawler'][alias] is not None else
                                f'Removed empty crawler.{alias} alias; crawler.{target} is unchanged.')
        if isinstance(canonical.get('profile'), ConfigProfile):
            canonical['profile'] = canonical['profile'].value
        cls.from_dict(canonical)  # Check active types, constraints, and profile overrides without expanding them.
        return canonical, warnings

    @classmethod
    def from_env(cls, prefix: str = 'TFQ0SEO_') -> 'Config':
        return cls.from_dict(cls.environment_overrides(prefix))

    @classmethod
    def environment_overrides(cls, prefix: str = 'TFQ0SEO_') -> Dict:
        data = {}
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            key = key[len(prefix):].lower()
            section = next((s for s in ('crawler', 'analysis', 'export', 'monitoring')
                            if key.startswith(s + '_')), None)
            if section:
                name = key[len(section) + 1:]
                canonical_name = _CRAWLER_ALIASES.get(name, name) if section == 'crawler' else name
                annotation = (get_type_hints(_COMPONENT_TYPES[section]).get(canonical_name)
                              if section in _COMPONENT_TYPES else None)
                if section == 'crawler' and name == 'concurrent_requests':
                    annotation = Optional[int]
                data.setdefault(section, {})[name] = cls._parse_env_value(value, annotation)
            else:
                data[key] = cls._parse_env_value(value, get_type_hints(cls).get(key))
        return data

    @staticmethod
    def _parse_env_value(value: str, annotation: Any = None) -> Any:
        if annotation is str or annotation is ConfigProfile:
            return value
        if get_origin(annotation) is Union and str in get_args(annotation):
            return None if value == 'null' else value
        if annotation is bool:
            if value.lower() in ('true', '1', 'yes'):
                return True
            if value.lower() in ('false', '0', 'no'):
                return False
            raise ValueError('Boolean environment settings must be true or false')
        if get_origin(annotation) is list:
            if value.strip().startswith('['):
                return json.loads(value)
            item_type = get_args(annotation)[0]
            return [Config._parse_env_value(item.strip(), item_type) for item in value.split(',')] if value else []
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            if ',' in value:
                return [v.strip() for v in value.split(',')]
            return value

    def apply_profile(self, profile: ConfigProfile) -> None:
        """Apply a preset in place, replacing its controlled values.

        Unrelated settings survive. CUSTOM only changes the profile label.
        Use merge({'profile': ...}) to retain explicit overrides while changing
        preset defaults instead.
        """
        self.profile = ConfigProfile(profile)
        if self.profile != ConfigProfile.CUSTOM:
            self.crawler.apply_profile(self.profile)
            defaults = AnalysisConfig()
            self.analysis.analysis_mode = defaults.analysis_mode
            self.analysis.enabled_analyzers = defaults.enabled_analyzers
            self.debug = False
            if self.profile == ConfigProfile.QUICK:
                self.analysis.analysis_mode = 'quick'
                self.analysis.enabled_analyzers = ['seo', 'technical']
            elif self.profile == ConfigProfile.DEEP:
                self.analysis.analysis_mode = 'deep'
            elif self.profile == ConfigProfile.DEVELOPMENT:
                self.debug = True
            # An explicit in-place preset supersedes older overrides for these
            # fields, so a later merge must not resurrect their previous values.
            if hasattr(self, '_explicit_values'):
                for section, names in (
                    ('crawler', CrawlerConfig.PROFILE_FIELDS),
                    ('analysis', ('analysis_mode', 'enabled_analyzers')),
                ):
                    for name in names:
                        self._explicit_values.get(section, {}).pop(name, None)
                self._explicit_values.pop('debug', None)
        if hasattr(self, '_explicit_values'):
            self._explicit_values['profile'] = self.profile.value

    def validate(self) -> Dict[str, List[str]]:
        issues = {}
        for name, expected in _COMPONENT_TYPES.items():
            obj = getattr(self, name)
            if not isinstance(obj, expected):
                issues[name] = [f'{name} must be a {expected.__name__}']
                continue
            errors = _type_issues(obj) + _unexpected_field_issues(obj, name)
            if not errors and hasattr(obj, 'validate'):
                errors.extend(obj.validate())
            if errors:
                issues[name] = errors
        global_errors = _type_issues(self) + _unexpected_field_issues(self, 'global')
        if type(self.max_memory_mb) is int and self.max_memory_mb <= 0:
            global_errors.append('max_memory_mb must be positive')
        if global_errors:
            issues['global'] = global_errors
        return issues

    def require_valid(self) -> None:
        issues = self.validate()
        if issues:
            raise ValueError('; '.join(f'{section}: {message}' for section, messages in issues.items()
                                       for message in messages))

    def to_dict(self) -> Dict:
        self.require_valid()
        data = asdict(self)
        data['profile'] = self.profile.value
        data['crawler'] = self.crawler.as_dict()
        return data

    def save(self, filepath: Union[str, Path]) -> None:
        self.require_valid()
        filepath = Path(filepath)
        if filepath.suffix.lower() not in ('.json', '.yaml', '.yml'):
            raise ValueError(f'Unsupported config format: {filepath.suffix}')
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with filepath.open('w', encoding='utf-8') as handle:
            if filepath.suffix.lower() == '.json':
                json.dump(self.to_dict(), handle, indent=2, allow_nan=False)
            else:
                yaml.safe_dump(self.to_dict(), handle, sort_keys=False)

    def get_effective_config(self) -> Dict:
        self.require_valid()
        return self.to_dict()

    def merge(self, other: Union[Dict, 'Config']) -> 'Config':
        override = other.to_dict() if isinstance(other, Config) else other
        if not isinstance(override, dict):
            raise ValueError('Configuration overrides must be an object')
        override = self._canonical_overrides(override)
        def merge_values(base, changes):
            result = dict(base)
            for name, value in changes.items():
                result[name] = merge_values(result[name], value) if (
                    name in result and isinstance(result[name], dict) and isinstance(value, dict)
                ) else value
            return result
        base = self.to_dict()
        if 'profile' in override and override['profile'] != self.profile.value:
            # A new profile supplies defaults, not overrides for every field.
            previous_defaults = Config(profile=self.profile).to_dict()
            def differences(current, defaults):
                changed = {}
                for name, value in current.items():
                    if isinstance(value, dict) and isinstance(defaults.get(name), dict):
                        nested = differences(value, defaults[name])
                        if nested:
                            changed[name] = nested
                    elif value != defaults.get(name):
                        changed[name] = value
                return changed
            base = merge_values(getattr(self, '_explicit_values', {}), differences(base, previous_defaults))
            base.pop('profile', None)
        return Config.from_dict(merge_values(base, override))
