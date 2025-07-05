"""
Configuration module for tfq0seo
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse
import os
import json
import yaml
from pathlib import Path
import validators
import logging

logger = logging.getLogger(__name__)

# Default profiles for different site types
PROFILES = {
    'blog': {
        'min_content_words': 500,
        'title_min_length': 30,
        'title_max_length': 65,
        'description_min_length': 120,
        'description_max_length': 160,
        'max_keyword_density': 2.5,
        'check_readability': True,
        'min_readability_score': 60
    },
    'ecommerce': {
        'min_content_words': 150,
        'title_min_length': 25,
        'title_max_length': 60,
        'description_min_length': 100,
        'description_max_length': 155,
        'max_keyword_density': 3.0,
        'check_structured_data': True,
        'check_image_optimization': True
    },
    'corporate': {
        'min_content_words': 300,
        'title_min_length': 30,
        'title_max_length': 60,
        'description_min_length': 120,
        'description_max_length': 160,
        'check_security_headers': True,
        'check_mobile_friendly': True
    },
    'news': {
        'min_content_words': 400,
        'title_min_length': 40,
        'title_max_length': 70,
        'check_amp': True,
        'check_structured_data': True,
        'max_page_load_time': 2.0
    }
}

@dataclass
class Config:
    """Configuration for SEO analysis"""
    # Basic settings
    url: Optional[str] = None
    depth: int = 3
    max_pages: int = 500
    concurrent_requests: int = 10
    delay: float = 0.5
    timeout: int = 30
    
    # Crawling settings
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    respect_robots: bool = True
    include_external: bool = False
    follow_redirects: bool = True
    max_redirects: int = 5
    sitemap_only: bool = False
    
    # User agent and headers
    user_agent: Optional[str] = None
    default_user_agent: str = "tfq0seo/2.1.1 (https://github.com/tfq0/tfq0seo)"
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Authentication
    auth_type: Optional[str] = None  # 'basic', 'bearer', 'cookie'
    auth_credentials: Optional[Dict[str, str]] = None  # username/password, token, or cookies
    
    # Proxy settings
    proxy: Optional[str] = None  # http://proxy.example.com:8080
    proxy_auth: Optional[Dict[str, str]] = None  # username/password for proxy
    
    # Rate limiting
    rate_limit_per_second: Optional[float] = None  # Global rate limit
    domain_rate_limits: Dict[str, float] = field(default_factory=dict)  # Per-domain limits
    
    # Analysis settings
    comprehensive: bool = False
    target_keyword: Optional[str] = None
    competitors: List[str] = field(default_factory=list)
    analysis_depth: str = "advanced"  # basic, advanced, complete
    profile: Optional[str] = None  # blog, ecommerce, corporate, news
    
    # SEO thresholds
    title_min_length: int = 30
    title_max_length: int = 60
    description_min_length: int = 120
    description_max_length: int = 160
    min_content_words: int = 300
    max_keyword_density: float = 3.0
    min_readability_score: int = 60
    max_page_load_time: float = 3.0
    
    # Image optimization
    check_image_alt: bool = True
    check_image_compression: bool = True
    max_image_size_kb: int = 200
    recommended_image_formats: List[str] = field(default_factory=lambda: ['webp', 'jpg', 'png', 'svg'])
    
    # Performance settings
    check_core_web_vitals: bool = True
    check_mobile_friendly: bool = True
    check_https: bool = True
    check_security_headers: bool = True
    check_compression: bool = True
    check_caching: bool = True
    
    # Technical SEO
    check_canonical: bool = True
    check_structured_data: bool = True
    check_robots_meta: bool = True
    check_sitemap: bool = True
    check_hreflang: bool = True
    check_amp: bool = False
    check_pwa: bool = False
    
    # Output settings
    output_format: str = "json"
    output_path: Optional[str] = None
    verbose: bool = False
    quiet: bool = False
    
    # Advanced settings
    javascript_rendering: bool = False
    screenshot: bool = False
    har_export: bool = False
    
    def __post_init__(self):
        """Validate and normalize configuration"""
        # Load from environment variables
        self._load_from_env()
        
        # Apply profile if specified
        if self.profile and self.profile in PROFILES:
            self._apply_profile(PROFILES[self.profile])
        
        # Validate URL
        if self.url:
            self.url = self._validate_url(self.url)
        
        # Validate competitors
        if self.competitors:
            self.competitors = [self._validate_url(url) for url in self.competitors]
        
        # Set user agent
        if not self.user_agent:
            self.user_agent = self.default_user_agent
        
        # Validate ranges
        self.depth = max(1, min(10, self.depth))
        self.concurrent_requests = max(1, min(50, self.concurrent_requests))
        self.delay = max(0, self.delay)
        self.timeout = max(5, min(300, self.timeout))
        
        # Validate proxy
        if self.proxy:
            self.proxy = self._validate_proxy(self.proxy)
        
        # Set up default exclude patterns
        self._setup_default_patterns()
        
        # Validate authentication
        if self.auth_type:
            self._validate_auth()
        
        # Set rate limits
        if not self.rate_limit_per_second:
            self.rate_limit_per_second = 1 / self.delay if self.delay > 0 else 10
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        env_mappings = {
            'TFQ0SEO_URL': 'url',
            'TFQ0SEO_DEPTH': ('depth', int),
            'TFQ0SEO_MAX_PAGES': ('max_pages', int),
            'TFQ0SEO_CONCURRENT': ('concurrent_requests', int),
            'TFQ0SEO_DELAY': ('delay', float),
            'TFQ0SEO_USER_AGENT': 'user_agent',
            'TFQ0SEO_PROXY': 'proxy',
            'TFQ0SEO_PROFILE': 'profile',
            'TFQ0SEO_VERBOSE': ('verbose', bool),
            'TFQ0SEO_QUIET': ('quiet', bool),
        }
        
        for env_var, config_attr in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                if isinstance(config_attr, tuple):
                    attr_name, converter = config_attr
                    try:
                        if converter == bool:
                            value = value.lower() in ('true', '1', 'yes', 'on')
                        else:
                            value = converter(value)
                        setattr(self, attr_name, value)
                    except ValueError:
                        logger.warning(f"Invalid value for {env_var}: {value}")
                else:
                    setattr(self, config_attr, value)
    
    def _apply_profile(self, profile_settings: Dict[str, Any]):
        """Apply profile settings"""
        for key, value in profile_settings.items():
            if hasattr(self, key):
                # Only apply if not already set by user
                current_value = getattr(self, key)
                if current_value == self.__class__.__annotations__[key].__args__[0]():
                    setattr(self, key, value)
    
    def _validate_url(self, url: str) -> str:
        """Validate and normalize URL"""
        # Ensure URL has protocol
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
            parsed = urlparse(url)
        
        # Validate URL format
        if not validators.url(url):
            raise ValueError(f"Invalid URL: {url}")
        
        # Ensure trailing slash for root URLs
        if not parsed.path or parsed.path == '/':
            url = url.rstrip('/') + '/'
        
        return url
    
    def _validate_proxy(self, proxy: str) -> str:
        """Validate proxy URL"""
        if not proxy.startswith(('http://', 'https://', 'socks5://')):
            proxy = f"http://{proxy}"
        
        parsed = urlparse(proxy)
        if not parsed.netloc:
            raise ValueError(f"Invalid proxy URL: {proxy}")
        
        return proxy
    
    def _setup_default_patterns(self):
        """Set up default exclude patterns"""
        default_excludes = [
            # File extensions
            r'\.pdf$', r'\.zip$', r'\.exe$', r'\.dmg$', r'\.doc[x]?$',
            r'\.xls[x]?$', r'\.ppt[x]?$', r'\.odt$', r'\.ods$', r'\.odp$',
            
            # Media files
            r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', r'\.webp$', r'\.bmp$',
            r'\.mp4$', r'\.avi$', r'\.mov$', r'\.wmv$', r'\.flv$', r'\.webm$',
            r'\.mp3$', r'\.wav$', r'\.flac$', r'\.aac$', r'\.ogg$',
            
            # System/admin paths
            r'/wp-admin/', r'/admin/', r'/administrator/', r'/backend/',
            r'/cpanel/', r'/phpmyadmin/', r'/.git/', r'/.svn/',
            
            # Common non-content URLs
            r'/logout', r'/login', r'/signin', r'/signup', r'/register',
            r'/cart/', r'/checkout/', r'/account/', r'/profile/',
            
            # URL parameters to avoid
            r'\?.*session', r'\?.*sid=', r'\?.*utm_', r'\?.*fbclid=',
            r'#', r'mailto:', r'tel:', r'javascript:', r'ftp:', r'file:',
            
            # Print/mobile versions
            r'/print/', r'\.print$', r'/amp/', r'/mobile/',
            
            # API endpoints
            r'/api/', r'/v1/', r'/v2/', r'/graphql', r'\.json$', r'\.xml$'
        ]
        
        # Add defaults only if no patterns specified
        if not self.exclude_patterns:
            self.exclude_patterns = default_excludes
        else:
            # Merge with defaults, avoiding duplicates
            for pattern in default_excludes:
                if pattern not in self.exclude_patterns:
                    self.exclude_patterns.append(pattern)
    
    def _validate_auth(self):
        """Validate authentication configuration"""
        if not self.auth_credentials:
            raise ValueError(f"auth_credentials required for auth_type: {self.auth_type}")
        
        if self.auth_type == 'basic':
            if 'username' not in self.auth_credentials or 'password' not in self.auth_credentials:
                raise ValueError("Basic auth requires 'username' and 'password'")
        elif self.auth_type == 'bearer':
            if 'token' not in self.auth_credentials:
                raise ValueError("Bearer auth requires 'token'")
        elif self.auth_type == 'cookie':
            if not self.auth_credentials:
                raise ValueError("Cookie auth requires cookie dictionary")
        else:
            raise ValueError(f"Unknown auth_type: {self.auth_type}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        data = asdict(self)
        # Remove sensitive information
        if 'auth_credentials' in data and data['auth_credentials']:
            data['auth_credentials'] = '***REDACTED***'
        if 'proxy_auth' in data and data['proxy_auth']:
            data['proxy_auth'] = '***REDACTED***'
        return data
    
    def to_json(self, path: Optional[str] = None) -> str:
        """Export configuration to JSON"""
        data = self.to_dict()
        if path:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        return json.dumps(data, indent=2)
    
    def to_yaml(self, path: Optional[str] = None) -> str:
        """Export configuration to YAML"""
        data = self.to_dict()
        if path:
            with open(path, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        return yaml.safe_dump(data, default_flow_style=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary"""
        # Filter out unknown fields
        valid_fields = set(cls.__annotations__.keys())
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    @classmethod
    def from_file(cls, path: str) -> 'Config':
        """Load configuration from file (JSON or YAML)"""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r') as f:
            if path.endswith('.json'):
                data = json.load(f)
            elif path.endswith(('.yml', '.yaml')):
                data = yaml.safe_load(f)
            else:
                raise ValueError("Configuration file must be JSON or YAML")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create config entirely from environment variables"""
        config = cls()
        config._load_from_env()
        return config
    
    def merge(self, other: Union['Config', Dict[str, Any]]) -> 'Config':
        """Merge another config or dict into this one"""
        if isinstance(other, dict):
            other_dict = other
        else:
            other_dict = other.to_dict()
        
        # Create new config with merged values
        current_dict = self.to_dict()
        current_dict.update(other_dict)
        
        return Config.from_dict(current_dict)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if not self.url:
            issues.append("URL is required")
        
        if self.depth > 5 and self.max_pages > 1000:
            issues.append("High depth with many pages may take very long")
        
        if self.concurrent_requests > 20 and not self.delay:
            issues.append("High concurrency without delay may overwhelm target server")
        
        if self.javascript_rendering and self.concurrent_requests > 5:
            issues.append("JavaScript rendering with high concurrency may be resource intensive")
        
        if self.auth_type and not self.auth_credentials:
            issues.append("Authentication type specified but no credentials provided")
        
        if self.proxy and self.proxy_auth and 'username' not in self.proxy_auth:
            issues.append("Proxy authentication specified but username missing")
        
        return issues
    
    def get_headers(self) -> Dict[str, str]:
        """Get all headers including custom and auth headers"""
        headers = {
            'User-Agent': self.user_agent
        }
        
        # Add custom headers
        headers.update(self.custom_headers)
        
        # Add authentication headers
        if self.auth_type == 'bearer' and self.auth_credentials:
            headers['Authorization'] = f"Bearer {self.auth_credentials.get('token', '')}"
        
        return headers
    
    def get_auth(self) -> Optional[tuple]:
        """Get authentication tuple for requests"""
        if self.auth_type == 'basic' and self.auth_credentials:
            return (
                self.auth_credentials.get('username', ''),
                self.auth_credentials.get('password', '')
            )
        return None
    
    def get_cookies(self) -> Optional[Dict[str, str]]:
        """Get cookies for requests"""
        if self.auth_type == 'cookie' and self.auth_credentials:
            return self.auth_credentials
        return None
    
    def get_rate_limit_for_domain(self, domain: str) -> float:
        """Get rate limit for specific domain"""
        if domain in self.domain_rate_limits:
            return self.domain_rate_limits[domain]
        return self.rate_limit_per_second or 10.0
    
    def __str__(self) -> str:
        """String representation"""
        return f"Config(url={self.url}, depth={self.depth}, max_pages={self.max_pages})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"Config({', '.join(f'{k}={v}' for k, v in self.to_dict().items() if v)})" 