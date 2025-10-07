"""Advanced configuration management with validation, presets, and dynamic profiles."""

import os
import json
import yaml
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List, Any, Union, Set
from enum import Enum
from pathlib import Path
from datetime import timedelta

logger = logging.getLogger(__name__)


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
    # Concurrency settings
    max_concurrent: int = 20
    concurrent_requests: int = 10  # Alias for compatibility
    max_connections_per_host: int = 5
    semaphore_limit: int = 30
    
    # Timeout settings
    timeout: int = 30
    connect_timeout: int = 10
    read_timeout: int = 30
    total_timeout: int = 300
    
    # User agent and headers
    user_agent: str = "tfq0seo/3.0.0 (Advanced SEO Bot; +https://github.com/tfq0seo)"
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
    use_http2: bool = True
    use_connection_pooling: bool = True
    dns_cache_ttl: int = 300
    verify_ssl: bool = True
    proxy: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if self.max_concurrent <= 0:
            issues.append("max_concurrent must be positive")
        if self.max_concurrent > 100:
            issues.append("max_concurrent > 100 may cause issues")
        
        if self.timeout <= 0:
            issues.append("timeout must be positive")
        
        if self.max_pages <= 0:
            issues.append("max_pages must be positive")
        
        if self.max_depth < 0:
            issues.append("max_depth must be non-negative")
        
        if self.delay_between_requests < 0:
            issues.append("delay_between_requests must be non-negative")
        
        if self.rate_limit_per_second and self.rate_limit_per_second <= 0:
            issues.append("rate_limit_per_second must be positive")
        
        return issues
    
    def apply_profile(self, profile: ConfigProfile) -> None:
        """Apply a configuration profile."""
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
            self.parse_javascript = True
        elif profile == ConfigProfile.ENTERPRISE:
            self.max_concurrent = 50
            self.max_pages = 10000
            self.max_depth = 20
            self.use_http2 = True
            self.use_connection_pooling = True
            self.adaptive_delay = True
        elif profile == ConfigProfile.DEVELOPMENT:
            self.max_concurrent = 5
            self.max_pages = 10
            self.max_depth = 2
            self.verify_ssl = False


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
    check_external_links: bool = True
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
        """Validate analysis configuration."""
        issues = []
        
        if not self.enabled_analyzers:
            issues.append("No analyzers enabled")
        
        if sum(self.score_weights.values()) != 1.0:
            issues.append("Score weights must sum to 1.0")
        
        if self.min_content_length < 0:
            issues.append("min_content_length must be non-negative")
        
        if self.target_reading_level < 1 or self.target_reading_level > 20:
            issues.append("target_reading_level should be between 1-20")
        
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
        """Validate export configuration."""
        issues = []
        
        if not self.formats:
            issues.append("No export formats specified")
        
        if self.primary_format not in self.formats:
            issues.append("primary_format not in formats list")
        
        if self.send_email and not self.email_recipients:
            issues.append("Email enabled but no recipients specified")
        
        if self.upload_to_cloud and not self.cloud_bucket:
            issues.append("Cloud upload enabled but no bucket specified")
        
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


@dataclass
class Config:
    """Main configuration container with advanced features."""
    # Core configurations
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Global settings
    profile: ConfigProfile = ConfigProfile.STANDARD
    version: str = "3.0.0"
    debug: bool = False
    dry_run: bool = False
    continue_on_error: bool = True
    max_memory_mb: int = 1024
    temp_directory: str = "./temp"
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        'parallel_crawling': True,
        'intelligent_sampling': True,
        'auto_retry': True,
        'smart_caching': True,
        'predictive_crawling': False,
        'ai_recommendations': False
    })
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Apply profile after initialization."""
        if self.profile != ConfigProfile.CUSTOM:
            self.apply_profile(self.profile)
    
    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> "Config":
        """Load configuration from file with validation."""
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}, using defaults")
            return cls()
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if filepath.suffix == '.json':
                    data = json.load(f)
                elif filepath.suffix in ['.yml', '.yaml']:
                    data = yaml.safe_load(f) or {}
                else:
                    raise ValueError(f"Unsupported config format: {filepath.suffix}")
            
            config = cls.from_dict(data)
            config.validate()
            return config
            
        except Exception as e:
            logger.error(f"Error loading config from {filepath}: {e}")
            return cls()
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Config":
        """Create config from dictionary with validation."""
        config = cls()
        
        # Load profile first
        if 'profile' in data:
            try:
                config.profile = ConfigProfile(data['profile'])
            except ValueError:
                logger.warning(f"Invalid profile: {data['profile']}, using STANDARD")
                config.profile = ConfigProfile.STANDARD
        
        # Load sub-configurations
        if 'crawler' in data:
            for key, value in data['crawler'].items():
                if hasattr(config.crawler, key):
                    setattr(config.crawler, key, value)
        
        if 'analysis' in data:
            for key, value in data['analysis'].items():
                if hasattr(config.analysis, key):
                    setattr(config.analysis, key, value)
        
        if 'export' in data:
            for key, value in data['export'].items():
                if hasattr(config.export, key):
                    setattr(config.export, key, value)
        
        if 'monitoring' in data:
            for key, value in data['monitoring'].items():
                if hasattr(config.monitoring, key):
                    setattr(config.monitoring, key, value)
        
        # Load global settings
        for key in ['debug', 'dry_run', 'continue_on_error', 'max_memory_mb', 'temp_directory']:
            if key in data:
                setattr(config, key, data[key])
        
        # Load features
        if 'features' in data:
            config.features.update(data['features'])
        
        # Load metadata
        if 'metadata' in data:
            config.metadata = data['metadata']
        
        return config
    
    @classmethod
    def from_env(cls, prefix: str = "TFQ0SEO_") -> "Config":
        """Load configuration from environment variables."""
        config = cls()
        
        # Parse environment variables
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            
            # Remove prefix and convert to lowercase
            config_key = key[len(prefix):].lower()
            
            # Map to configuration paths
            if config_key.startswith('crawler_'):
                attr = config_key[8:]  # Remove 'crawler_'
                if hasattr(config.crawler, attr):
                    setattr(config.crawler, attr, cls._parse_env_value(value))
            
            elif config_key.startswith('analysis_'):
                attr = config_key[9:]  # Remove 'analysis_'
                if hasattr(config.analysis, attr):
                    setattr(config.analysis, attr, cls._parse_env_value(value))
            
            elif config_key.startswith('export_'):
                attr = config_key[7:]  # Remove 'export_'
                if hasattr(config.export, attr):
                    setattr(config.export, attr, cls._parse_env_value(value))
            
            elif config_key.startswith('monitoring_'):
                attr = config_key[11:]  # Remove 'monitoring_'
                if hasattr(config.monitoring, attr):
                    setattr(config.monitoring, attr, cls._parse_env_value(value))
            
            elif config_key == 'profile':
                try:
                    config.profile = ConfigProfile(value.lower())
                except ValueError:
                    logger.warning(f"Invalid profile from env: {value}")
            
            elif config_key == 'debug':
                config.debug = value.lower() in ['true', '1', 'yes']
        
        return config
    
    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Boolean
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        # List (comma-separated)
        if ',' in value:
            return [v.strip() for v in value.split(',')]
        
        # String
        return value
    
    def apply_profile(self, profile: ConfigProfile) -> None:
        """Apply a configuration profile to all sub-configs."""
        self.profile = profile
        
        if profile == ConfigProfile.QUICK:
            # Quick scan settings
            self.crawler.max_concurrent = 30
            self.crawler.max_pages = 50
            self.crawler.max_depth = 2
            self.crawler.timeout = 10
            self.analysis.analysis_mode = "quick"
            self.analysis.enabled_analyzers = ['seo', 'technical']
            self.analysis.check_external_links = False
            self.export.formats = ['html']
            self.export.include_raw_data = False
            
        elif profile == ConfigProfile.STANDARD:
            # Default balanced settings (already set)
            pass
            
        elif profile == ConfigProfile.DEEP:
            # Comprehensive analysis
            self.crawler.max_concurrent = 10
            self.crawler.max_pages = 1000
            self.crawler.max_depth = 10
            self.crawler.timeout = 60
            self.crawler.parse_javascript = True
            self.analysis.analysis_mode = "deep"
            self.analysis.enabled_analyzers = [
                'seo', 'content', 'technical', 'performance', 'links'
            ]
            self.analysis.check_external_links = True
            self.analysis.validate_structured_data = True
            self.analysis.check_content_uniqueness = True
            self.export.include_raw_data = True
            self.export.generate_executive_report = True
            
        elif profile == ConfigProfile.ENTERPRISE:
            # Large-scale optimized
            self.crawler.max_concurrent = 50
            self.crawler.max_pages = 10000
            self.crawler.max_depth = 20
            self.crawler.use_http2 = True
            self.crawler.use_connection_pooling = True
            self.crawler.adaptive_delay = True
            self.crawler.cache_enabled = True
            self.analysis.parallel_analysis = True
            self.analysis.max_analysis_threads = 8
            self.export.split_large_reports = True
            self.monitoring.enabled = True
            self.features['intelligent_sampling'] = True
            self.features['predictive_crawling'] = True
            
        elif profile == ConfigProfile.DEVELOPMENT:
            # Testing/development settings
            self.crawler.max_concurrent = 5
            self.crawler.max_pages = 10
            self.crawler.max_depth = 2
            self.crawler.verify_ssl = False
            self.debug = True
            self.monitoring.log_level = "debug"
            self.monitoring.detailed_progress = True
    
    def validate(self) -> Dict[str, List[str]]:
        """Validate entire configuration and return issues by component."""
        issues = {
            'crawler': self.crawler.validate(),
            'analysis': self.analysis.validate(),
            'export': self.export.validate()
        }
        
        # Global validations
        global_issues = []
        
        if self.max_memory_mb <= 0:
            global_issues.append("max_memory_mb must be positive")
        
        if self.max_memory_mb < 256:
            global_issues.append("max_memory_mb < 256MB may cause issues")
        
        temp_dir = Path(self.temp_directory)
        if not temp_dir.exists():
            try:
                temp_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                global_issues.append(f"Cannot create temp directory: {e}")
        
        if global_issues:
            issues['global'] = global_issues
        
        # Log issues if any
        for component, component_issues in issues.items():
            if component_issues:
                for issue in component_issues:
                    logger.warning(f"Config validation ({component}): {issue}")
        
        return issues
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'profile': self.profile.value,
            'version': self.version,
            'crawler': asdict(self.crawler),
            'analysis': asdict(self.analysis),
            'export': asdict(self.export),
            'monitoring': asdict(self.monitoring),
            'debug': self.debug,
            'dry_run': self.dry_run,
            'continue_on_error': self.continue_on_error,
            'max_memory_mb': self.max_memory_mb,
            'temp_directory': self.temp_directory,
            'features': self.features,
            'metadata': self.metadata
        }
    
    def save(self, filepath: Union[str, Path]) -> None:
        """Save configuration to file."""
        filepath = Path(filepath)
        data = self.to_dict()
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                if filepath.suffix == '.json':
                    json.dump(data, f, indent=2, default=str)
                elif filepath.suffix in ['.yml', '.yaml']:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                else:
                    raise ValueError(f"Unsupported config format: {filepath.suffix}")
            
            logger.info(f"Configuration saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving config to {filepath}: {e}")
            raise
    
    def get_effective_config(self) -> Dict:
        """Get the effective configuration after all overrides."""
        config = self.to_dict()
        
        # Add computed values
        config['computed'] = {
            'total_timeout': self.crawler.total_timeout,
            'max_memory_bytes': self.max_memory_mb * 1024 * 1024,
            'cache_size_bytes': self.crawler.cache_size_mb * 1024 * 1024,
            'effective_max_concurrent': min(
                self.crawler.max_concurrent,
                self.crawler.semaphore_limit
            )
        }
        
        return config
    
    def merge(self, other: Union[Dict, 'Config']) -> 'Config':
        """Merge with another configuration, with other taking precedence."""
        if isinstance(other, dict):
            other = Config.from_dict(other)
        
        # Create a new config with merged values
        merged_dict = self.to_dict()
        other_dict = other.to_dict()
        
        # Deep merge
        def deep_merge(base: Dict, override: Dict) -> Dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        merged_data = deep_merge(merged_dict, other_dict)
        return Config.from_dict(merged_data)