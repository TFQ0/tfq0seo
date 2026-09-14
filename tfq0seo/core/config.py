"""Advanced configuration management with validation, presets, and dynamic profiles."""

import os
import json
import yaml
import math
import re
import copy
from dataclasses import dataclass, field, asdict, fields
from typing import Dict, Optional, List, Any, Union, get_args, get_origin, get_type_hints
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
    PDF = "pdf"
    MARKDOWN = "markdown"
    XML = "xml"


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
    # Concurrency settings
    max_concurrent: int = 20
    concurrent_requests: Optional[int] = None  # Legacy alias; max_concurrent is canonical.
    max_connections_per_host: int = 5
    semaphore_limit: int = 30
    
    # Timeout settings
    timeout: int = 30
    connect_timeout: int = 10
    read_timeout: int = 30
    total_timeout: int = 300
    
    # User agent and headers
    user_agent: str = "tfq0seo/2.3.2 (+https://github.com/TFQ0/tfq0seo)"
    custom_headers: Dict[str, str] = field(default_factory=dict)
    rotate_user_agents: bool = False
    user_agent_list: List[str] = field(default_factory=list)
    
    # Redirect handling
    follow_redirects: bool = True
    max_redirects: int = 10
    redirect_cache_ttl: int = 3600
    
    # Crawl limits
    max_pages: int = 500
    max_depth: int = 5
    max_page_size: int = 10485760  # 10MB
    max_crawl_time: int = 3600  # 1 hour
    
    # Rate limiting
    delay_between_requests: float = 0.0
    adaptive_delay: bool = True
    min_delay: float = 0.0
    max_delay: float = 5.0
    rate_limit_per_second: Optional[float] = None
    
    # Robots.txt handling
    respect_robots_txt: bool = True
    robots_cache_ttl: int = 86400  # 24 hours
    crawl_delay_factor: float = 1.0  # Multiplier for robots.txt delay
    
    # URL filtering
    allowed_domains: List[str] = field(default_factory=list)
    allowed_schemes: List[str] = field(default_factory=lambda: ['http', 'https'])
    excluded_patterns: List[str] = field(default_factory=lambda: [
        r'\.pdf$', r'\.zip$', r'\.exe$', r'\.dmg$',
        r'/wp-admin', r'/admin', r'/login',
        r'\?.*session', r'\?.*utm_'
    ])
    include_query_strings: bool = True
    normalize_urls: bool = True
    
    # Content handling
    parse_javascript: bool = False
    execute_javascript: bool = False
    wait_for_javascript: float = 0.0
    store_html: bool = False
    compress_stored_html: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_on_status: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retry_backoff_factor: float = 2.0
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl: int = 3600
    cache_size_mb: int = 100
    
    # Advanced features
    use_sitemap: bool = True
    discover_sitemaps: bool = True
    prioritize_sitemap_urls: bool = True
    use_http2: bool = False
    use_connection_pooling: bool = True
    dns_cache_ttl: int = 300
    verify_ssl: bool = True
    proxy: Optional[str] = None
    
    @property
    def effective_concurrency(self) -> int:
        return self.concurrent_requests if self.concurrent_requests is not None else self.max_concurrent

    def as_dict(self) -> Dict[str, Any]:
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
        for pattern in self.excluded_patterns:
            try:
                re.compile(pattern)
            except re.error:
                issues.append(f"Invalid excluded pattern: {pattern}")
        if any(code < 400 or code > 599 for code in self.retry_on_status):
            issues.append('retry_on_status must contain HTTP error status codes')
        for name in ('parse_javascript', 'execute_javascript', 'use_http2'):
            if getattr(self, name):
                issues.append(f"{name} is not supported by the static HTTP crawler")
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
    # Analysis scope
    enabled_analyzers: List[str] = field(default_factory=lambda: [
        'seo', 'content', 'technical', 'performance', 'links'
    ])
    analysis_mode: str = "standard"  # quick, standard, deep
    parallel_analysis: bool = True
    max_analysis_threads: int = 4
    
    # Link analysis
    check_external_links: bool = False
    check_internal_links: bool = True
    validate_anchors: bool = True
    check_broken_links: bool = True
    max_external_links_per_page: int = 100
    external_link_timeout: int = 10
    
    # Image analysis
    check_images: bool = True
    check_image_optimization: bool = True
    check_alt_text: bool = True
    check_image_dimensions: bool = True
    max_image_size_kb: int = 500
    
    # Content analysis
    min_content_length: int = 100
    max_content_length: int = 100000
    optimal_content_length: int = 1500
    check_readability: bool = True
    target_reading_level: int = 8  # Grade level
    check_keyword_density: bool = True
    target_keywords: List[str] = field(default_factory=list)
    keyword_variations: bool = True
    check_content_uniqueness: bool = True
    min_unique_content_ratio: float = 0.7
    
    # SEO analysis
    check_meta_tags: bool = True
    check_structured_data: bool = True
    validate_structured_data: bool = True
    check_open_graph: bool = True
    check_twitter_cards: bool = True
    check_canonical_urls: bool = True
    check_hreflang: bool = True
    check_sitemaps: bool = True
    check_robots_txt: bool = True
    
    # Technical analysis
    check_https: bool = True
    check_security_headers: bool = True
    check_mixed_content: bool = True
    check_mobile_friendly: bool = True
    check_page_speed: bool = True
    check_core_web_vitals: bool = True
    check_compression: bool = True
    check_caching: bool = True
    check_minification: bool = True
    check_http2: bool = True
    
    # Performance thresholds
    max_page_load_time: float = 3.0
    max_ttfb: float = 0.8
    max_fcp: float = 1.8
    max_lcp: float = 2.5
    max_fid: float = 100
    max_cls: float = 0.1
    max_page_size_mb: float = 3.0
    
    # Accessibility
    check_accessibility: bool = True
    wcag_level: str = "AA"  # A, AA, AAA
    
    # Scoring weights
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
    # Output formats
    formats: List[str] = field(default_factory=lambda: ['html'])
    primary_format: str = 'html'
    
    # HTML settings
    html_template: str = "optimized"  # report, enhanced, optimized
    include_inline_css: bool = True
    include_inline_js: bool = True
    minify_html: bool = True
    html_theme: str = "light"  # light, dark, auto
    include_charts: bool = True
    charts_library: str = "chartjs"  # chartjs, d3, highcharts
    
    # Data inclusion
    include_raw_data: bool = False
    include_page_content: bool = False
    include_screenshots: bool = False
    include_har_files: bool = False
    data_sampling_rate: float = 1.0  # For large datasets
    max_issues_per_page: int = 100
    max_pages_in_report: int = 1000
    
    # File settings
    output_directory: str = "./reports"
    filename_pattern: str = "{domain}_{timestamp}_{format}"
    create_subdirectories: bool = True
    compress_output: bool = False
    compression_format: str = "zip"  # zip, tar, gz
    
    # Export options
    split_large_reports: bool = True
    split_threshold_mb: int = 50
    generate_summary: bool = True
    generate_executive_report: bool = True
    
    # Email settings
    send_email: bool = False
    email_recipients: List[str] = field(default_factory=list)
    email_subject_template: str = "SEO Report for {domain}"
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # Cloud storage
    upload_to_cloud: bool = False
    cloud_provider: Optional[str] = None  # s3, gcs, azure
    cloud_bucket: Optional[str] = None
    cloud_path_prefix: Optional[str] = None
    
    # API export
    send_to_api: bool = False
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    api_method: str = "POST"
    
    def validate(self) -> List[str]:
        issues = []
        if not self.formats or set(self.formats) - {'html', 'json', 'csv', 'xlsx'}:
            issues.append('Supported export formats are html, json, csv, xlsx')
        if self.primary_format not in self.formats:
            issues.append('primary_format must be present in formats')
        if self.html_template not in {'report', 'enhanced', 'optimized'}:
            issues.append('Unknown html_template')
        for name in ('send_email', 'upload_to_cloud', 'send_to_api', 'include_screenshots', 'include_har_files'):
            if getattr(self, name):
                issues.append(f"{name} is not implemented")
        return issues


@dataclass
class MonitoringConfig:
    """Configuration for monitoring and alerting."""
    enabled: bool = False
    
    # Metrics collection
    collect_metrics: bool = True
    metrics_interval: int = 60  # seconds
    metrics_retention_days: int = 30
    
    # Alerting
    enable_alerts: bool = False
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'error_rate': 0.05,  # 5% error rate
        'avg_response_time': 5.0,  # 5 seconds
        'memory_usage_mb': 500,
        'broken_links_ratio': 0.10
    })
    
    # Logging
    log_level: str = "info"
    log_to_file: bool = True
    log_file_path: str = "./logs/tfq0seo.log"
    log_rotation: str = "daily"  # daily, size, time
    log_retention_days: int = 7
    log_format: str = "json"  # json, text
    
    # Progress tracking
    show_progress: bool = True
    progress_update_interval: float = 1.0
    detailed_progress: bool = False
    
    # Webhooks
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_events: List[str] = field(default_factory=lambda: [
        'analysis_complete', 'error', 'threshold_exceeded'
    ])


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
        return type(value) in (int, float) and math.isfinite(value)
    if expected in (bool, int):
        return type(value) is expected
    return isinstance(value, expected)


def _type_issues(obj: Any) -> List[str]:
    annotations = get_type_hints(type(obj))
    return [f"{item.name} has an invalid type or non-finite value"
            for item in fields(obj)
            if not _matches_type(getattr(obj, item.name), annotations[item.name])]


@dataclass
class Config:
    """Resolve profiles first, then explicit overrides; reject invalid input."""
    crawler: Optional[CrawlerConfig] = None
    analysis: Optional[AnalysisConfig] = None
    export: Optional[ExportConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    profile: ConfigProfile = ConfigProfile.STANDARD
    version: str = '2.3.2'
    debug: bool = False
    dry_run: bool = False
    continue_on_error: bool = True
    max_memory_mb: int = 1024
    temp_directory: str = './temp'
    features: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Legacy fields remain readable for compatibility. Changing an inert field
    # must fail explicitly instead of silently promising unsupported behavior.
    SUPPORTED_FIELDS = {
        'crawler': set(('max_concurrent concurrent_requests max_connections_per_host timeout connect_timeout '
                        'read_timeout user_agent custom_headers follow_redirects max_redirects max_pages max_depth '
                        'max_page_size max_crawl_time delay_between_requests adaptive_delay min_delay max_delay '
                        'rate_limit_per_second respect_robots_txt robots_cache_ttl crawl_delay_factor allowed_domains '
                        'allowed_schemes excluded_patterns store_html max_retries retry_on_status retry_backoff_factor '
                        'cache_enabled cache_ttl cache_size_mb use_sitemap discover_sitemaps dns_cache_ttl verify_ssl '
                        'proxy use_connection_pooling').split()),
        'analysis': set(('enabled_analyzers analysis_mode parallel_analysis max_analysis_threads target_keywords '
                         'check_broken_links check_internal_links check_external_links max_external_links_per_page '
                         'external_link_timeout check_content_uniqueness score_weights').split()),
        'export': {'formats', 'primary_format', 'html_template', 'output_directory', 'filename_pattern'},
        'monitoring': set(),
    }

    def __post_init__(self):
        supplied = {name: getattr(self, name) for name in ('crawler', 'analysis', 'export', 'monitoring')}
        supplied_debug = self.debug
        self.crawler = CrawlerConfig()
        self.analysis = AnalysisConfig()
        self.export = ExportConfig()
        self.monitoring = MonitoringConfig()
        self.profile = ConfigProfile(self.profile)
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
        unknown = set(data) - {item.name for item in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
        config = cls(profile=ConfigProfile(data.get('profile', 'standard')))
        for section in ('crawler', 'analysis', 'export', 'monitoring'):
            values = data.get(section, {})
            if not isinstance(values, dict):
                raise ValueError(f'{section} must be an object')
            values = dict(values)
            target = getattr(config, section)
            allowed = {item.name for item in fields(target)}
            unknown = set(values) - allowed
            if unknown:
                raise ValueError(f"Unknown {section} keys: {', '.join(sorted(unknown))}")
            for name, value in values.items():
                setattr(target, name, value)
        for name, value in data.items():
            if name not in ('crawler', 'analysis', 'export', 'monitoring', 'profile'):
                setattr(config, name, value)
        config._explicit_values = copy.deepcopy(data)
        config.require_valid()
        return config

    @staticmethod
    def _canonical_overrides(data: Dict) -> Dict:
        data = copy.deepcopy(data)
        values = data.get('crawler')
        if isinstance(values, dict):
            aliases = {'concurrent_requests': 'max_concurrent', 'max_content_length': 'max_page_size',
                       'retry_attempts': 'max_retries', 'adaptive_throttle': 'adaptive_delay',
                       'follow_sitemap': 'use_sitemap'}
            for alias, name in aliases.items():
                if alias in values:
                    value = values.pop(alias)
                    if value is None and alias == 'concurrent_requests':
                        continue
                    if name in values and values[name] != value:
                        raise ValueError(f'Conflicting crawler settings: {alias} and {name}')
                    values[name] = value
        return data

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
                annotation = get_type_hints({'crawler': CrawlerConfig, 'analysis': AnalysisConfig,
                                            'export': ExportConfig, 'monitoring': MonitoringConfig}[section]).get(name)
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
        for name in ('crawler', 'analysis', 'export', 'monitoring'):
            obj = getattr(self, name)
            expected = {'crawler': CrawlerConfig, 'analysis': AnalysisConfig,
                        'export': ExportConfig, 'monitoring': MonitoringConfig}[name]
            if not isinstance(obj, expected):
                issues[name] = [f'{name} must be a {expected.__name__}']
                continue
            errors = _type_issues(obj)
            if not errors and hasattr(obj, 'validate'):
                errors.extend(obj.validate())
            defaults = expected()
            for item in fields(obj):
                if item.name not in self.SUPPORTED_FIELDS[name] and getattr(obj, item.name) != getattr(defaults, item.name):
                    errors.append(f'{item.name} is not supported; use the documented component settings')
            if errors:
                issues[name] = errors
        global_errors = _type_issues(self)
        if type(self.max_memory_mb) is int and self.max_memory_mb <= 0:
            global_errors.append('max_memory_mb must be positive')
        if self.dry_run:
            global_errors.append('dry_run is not implemented; no network request was started')
        if isinstance(self.monitoring, MonitoringConfig) and (self.monitoring.enabled or self.monitoring.webhook_enabled):
            global_errors.append('Background monitoring and webhooks are not implemented')
        if self.features:
            global_errors.append('Legacy feature flags are unsupported; use explicit component settings')
        if global_errors:
            issues['global'] = global_errors
        return issues

    def require_valid(self) -> None:
        issues = self.validate()
        if issues:
            raise ValueError('; '.join(f'{section}: {message}' for section, messages in issues.items()
                                       for message in messages))

    def to_dict(self) -> Dict:
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
