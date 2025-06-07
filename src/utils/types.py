from typing import TypedDict, Literal, Dict, List, Optional, Union
from datetime import datetime

# Configuration Types
class LoggingConfig(TypedDict):
    file: str
    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    max_size: int
    backup_count: int

class CacheConfig(TypedDict):
    enabled: bool
    expiration: int
    max_entries: int
    max_memory_mb: int

class SEOThresholds(TypedDict):
    title_length: Dict[Literal['min', 'max'], int]
    meta_description_length: Dict[Literal['min', 'max'], int]
    keyword_density: Dict[Literal['min', 'max'], float]
    content_length: Dict[Literal['min', 'max'], int]

class AppConfig(TypedDict):
    logging: LoggingConfig
    cache: CacheConfig
    seo_thresholds: SEOThresholds
    crawling: Dict[str, str]

# Analysis Result Types
class MetaTagAnalysis(TypedDict):
    title: Optional[str]
    description: Optional[str]
    robots: Optional[str]
    viewport: Optional[str]
    canonical: Optional[str]
    og_tags: Dict[str, str]
    twitter_cards: Dict[str, str]
    schema_markup: List[Dict]
    favicon: Optional[str]
    lang: Optional[str]

class ContentMetrics(TypedDict):
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    paragraph_count: int

class ReadabilityScores(TypedDict):
    flesch_reading_ease: float
    sentiment: Dict[Literal['polarity', 'subjectivity'], float]
    avg_word_length: float

class KeywordAnalysis(TypedDict):
    count: int
    density: float
    top_keywords: List[Dict[str, Union[str, int, float]]]
    top_phrases: Dict[str, List[tuple]]

class ContentStructure(TypedDict):
    paragraph_lengths: List[int]
    sentence_lengths: List[int]
    avg_paragraph_length: float
    content_sections: int

class ContentQuality(TypedDict):
    duplicate_sentences: List[str]
    sentence_starters: Dict[str, int]
    transition_words: int
    passive_voice: Dict[str, Union[int, float]]

class ContentAnalysis(TypedDict):
    basic_metrics: ContentMetrics
    readability: ReadabilityScores
    keyword_analysis: KeywordAnalysis
    content_structure: ContentStructure
    content_quality: ContentQuality

class PerformanceMetrics(TypedDict):
    load_time: float
    resource_count: Dict[Literal['images', 'scripts', 'styles'], int]
    total_size: int
    compression_enabled: bool
    cache_headers: bool

class SecurityChecks(TypedDict):
    https: bool
    hsts: bool
    xss_protection: bool
    content_security: bool
    mixed_content: bool

class ModernSEOAnalysis(TypedDict):
    mobile_friendly: Dict[str, bool]
    performance: PerformanceMetrics
    security: SecurityChecks
    structured_data: Dict[str, Union[int, List[str]]]
    social_signals: Dict[str, Dict[str, str]]

class AnalysisResult(TypedDict):
    url: str
    target_keyword: Optional[str]
    meta_analysis: MetaTagAnalysis
    content_analysis: ContentAnalysis
    modern_seo_analysis: ModernSEOAnalysis
    combined_report: Dict[str, List[str]]
    error: Optional[Dict[str, Union[bool, str, Dict]]]

# Cache Types
class CacheEntry(TypedDict):
    data: Any
    expiration: datetime
    last_accessed: datetime
    access_count: int

class CacheStats(TypedDict):
    hits: int
    misses: int
    hit_ratio: float
    evictions: int
    current_size: int
    memory_usage_mb: float
    max_size: int
    max_memory_mb: float

# Error Types
class ErrorDetails(TypedDict):
    error_code: str
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]]
    recovery_attempted: bool
    stack_trace: Optional[str]

# HTTP Types
class RequestHeaders(TypedDict):
    User_Agent: str
    Accept: str
    Accept_Language: str
    Accept_Encoding: str
    Connection: Literal['keep-alive', 'close']

class ResponseHeaders(TypedDict):
    Content_Type: str
    Content_Length: int
    Cache_Control: str
    ETag: str
    Last_Modified: str

# Async Types
class AsyncAnalysisContext(TypedDict):
    url: str
    headers: RequestHeaders
    timeout: float
    max_retries: int
    backoff_factor: float
    concurrent_limit: int 