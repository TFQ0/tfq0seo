"""
tfq0seo - Professional SEO Analysis Toolkit (Optimized)
Open source alternative to Screaming Frog SEO Spider
"""

__version__ = "2.2.0"  # Optimized version
__author__ = "tfq0"

# Core imports
try:
    from .core.app import SEOAnalyzerApp
    from .core.crawler import WebCrawler
    from .core.config import Config
    from .analyzers.seo import SEOAnalyzer
    from .exporters.base import ExportManager
except ImportError as e:
    import warnings
    warnings.warn(f"tfq0seo: Failed to import core modules: {e}", ImportWarning)
    SEOAnalyzerApp = None
    WebCrawler = None
    Config = None
    SEOAnalyzer = None
    ExportManager = None

__all__ = [
    "SEOAnalyzerApp",
    "WebCrawler",
    "Config",
    "SEOAnalyzer",
    "ExportManager"
] 


