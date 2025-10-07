"""TFQ0SEO -  SEO analysis tool with reports."""

__version__ = "2.3.0"
__author__ = "TFQ0 SEO Team"

from .core.app import SEOAnalyzer
from .core.config import Config

__all__ = ["SEOAnalyzer", "Config", "__version__"]
