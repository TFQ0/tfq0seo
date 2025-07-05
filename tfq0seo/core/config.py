"""
Configuration module for tfq0seo
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

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
    
    # User agent
    user_agent: Optional[str] = None
    default_user_agent: str = "tfq0seo/2.1.0 (https://github.com/tfq0/tfq0seo)"
    
    # Analysis settings
    comprehensive: bool = False
    target_keyword: Optional[str] = None
    competitors: List[str] = field(default_factory=list)
    analysis_depth: str = "advanced"  # basic, advanced, complete
    
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
    
    # Performance settings
    check_core_web_vitals: bool = True
    check_mobile_friendly: bool = True
    check_https: bool = True
    check_security_headers: bool = True
    
    # Output settings
    output_format: str = "json"
    output_path: Optional[str] = None
    verbose: bool = False
    
    def __post_init__(self):
        """Validate and normalize configuration"""
        if self.url:
            # Ensure URL has protocol
            parsed = urlparse(self.url)
            if not parsed.scheme:
                self.url = f"https://{self.url}"
        
        # Set user agent
        if not self.user_agent:
            self.user_agent = self.default_user_agent
        
        # Validate ranges
        self.depth = max(1, min(10, self.depth))
        self.concurrent_requests = max(1, min(50, self.concurrent_requests))
        self.delay = max(0, self.delay)
        
        # Default exclude patterns
        default_excludes = [
            r'\.pdf$', r'\.zip$', r'\.exe$', r'\.dmg$',
            r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$',
            r'\.mp4$', r'\.avi$', r'\.mov$', r'\.mp3$',
            r'/wp-admin/', r'/admin/', r'/logout',
            r'\?', r'#', r'mailto:', r'tel:', r'javascript:'
        ]
        
        if not self.exclude_patterns:
            self.exclude_patterns = default_excludes
        else:
            self.exclude_patterns.extend(default_excludes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'url': self.url,
            'depth': self.depth,
            'max_pages': self.max_pages,
            'concurrent_requests': self.concurrent_requests,
            'delay': self.delay,
            'timeout': self.timeout,
            'exclude_patterns': self.exclude_patterns,
            'respect_robots': self.respect_robots,
            'include_external': self.include_external,
            'user_agent': self.user_agent,
            'comprehensive': self.comprehensive,
            'target_keyword': self.target_keyword,
            'competitors': self.competitors,
            'analysis_depth': self.analysis_depth,
            'output_format': self.output_format
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary"""
        return cls(**data) 