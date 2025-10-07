"""Configuration management for tfq0seo - simple dataclass-based, no complex validation."""

import os
import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List


@dataclass
class CrawlerConfig:
    """Configuration for the crawler."""
    max_concurrent: int = 20
    timeout: int = 30
    user_agent: str = "tfq0seo/2.2.0 (SEO Analysis Bot)"
    follow_redirects: bool = True
    max_redirects: int = 5
    max_pages: int = 500
    max_depth: int = 5
    delay_between_requests: float = 0.0
    respect_robots_txt: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    excluded_patterns: List[str] = field(default_factory=list)


@dataclass
class AnalysisConfig:
    """Configuration for analysis modules."""
    check_external_links: bool = True
    check_images: bool = True
    min_content_length: int = 100
    max_content_length: int = 100000  # 100KB limit for content
    check_readability: bool = True
    check_keyword_density: bool = True
    target_keywords: List[str] = field(default_factory=list)
    check_structured_data: bool = True
    check_mobile_friendly: bool = True
    check_page_speed: bool = True


@dataclass
class ExportConfig:
    """Configuration for export modules."""
    html_template: str = "default"
    include_raw_data: bool = False
    minify_html: bool = True
    include_screenshots: bool = False
    output_directory: str = "./reports"


@dataclass
class Config:
    """Main configuration container."""
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    
    @classmethod
    def from_file(cls, filepath: str) -> "Config":
        """Load configuration from JSON or YAML file."""
        if not os.path.exists(filepath):
            return cls()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            if filepath.endswith('.json'):
                data = json.load(f)
            elif filepath.endswith(('.yml', '.yaml')):
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file format: {filepath}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Config":
        """Create config from dictionary."""
        config = cls()
        
        if 'crawler' in data:
            config.crawler = CrawlerConfig(**data['crawler'])
        if 'analysis' in data:
            config.analysis = AnalysisConfig(**data['analysis'])
        if 'export' in data:
            config.export = ExportConfig(**data['export'])
        
        return config
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()
        
        # Load crawler settings from env
        if env_val := os.getenv('TFQ0SEO_MAX_CONCURRENT'):
            config.crawler.max_concurrent = int(env_val)
        if env_val := os.getenv('TFQ0SEO_TIMEOUT'):
            config.crawler.timeout = int(env_val)
        if env_val := os.getenv('TFQ0SEO_USER_AGENT'):
            config.crawler.user_agent = env_val
        if env_val := os.getenv('TFQ0SEO_MAX_PAGES'):
            config.crawler.max_pages = int(env_val)
        
        # Load analysis settings from env
        if env_val := os.getenv('TFQ0SEO_CHECK_EXTERNAL_LINKS'):
            config.analysis.check_external_links = env_val.lower() == 'true'
        if env_val := os.getenv('TFQ0SEO_MIN_CONTENT_LENGTH'):
            config.analysis.min_content_length = int(env_val)
        
        # Load export settings from env
        if env_val := os.getenv('TFQ0SEO_OUTPUT_DIR'):
            config.export.output_directory = env_val
        if env_val := os.getenv('TFQ0SEO_HTML_TEMPLATE'):
            config.export.html_template = env_val
        
        return config
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            'crawler': asdict(self.crawler),
            'analysis': asdict(self.analysis),
            'export': asdict(self.export)
        }
    
    def save(self, filepath: str):
        """Save configuration to file."""
        data = self.to_dict()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if filepath.endswith('.json'):
                json.dump(data, f, indent=2)
            elif filepath.endswith(('.yml', '.yaml')):
                yaml.safe_dump(data, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported config file format: {filepath}")
