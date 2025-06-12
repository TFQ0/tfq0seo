"""
tfq0seo - Enhanced SEO analysis and site crawling toolkit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A comprehensive SEO analysis toolkit with professional crawling capabilities.

Enhanced Features:
- Complete site crawling with configurable depth
- Comprehensive SEO analysis and recommendations
- Content optimization and duplicate detection
- Technical SEO validation and monitoring
- Link analysis (internal/external/broken)
- Image optimization analysis
- Performance and Core Web Vitals measurement
- Mobile-friendly and accessibility testing
- Security and certificate validation
- Rich results and structured data analysis
- Site structure and URL optimization
- Multiple export formats (JSON, CSV, XLSX, HTML)
- Real-time progress tracking
- Professional reporting dashboard

Competitive with Screaming Frog SEO Spider but open source and extensible.

For more information, visit: https://github.com/tfq0/tfq0seo
"""

__title__ = 'tfq0seo'
__version__ = '2.0.0'
__author__ = 'tfq0'
__license__ = 'MIT'
__copyright__ = 'Copyright 2024 tfq0'

from .utils.paths import TFQSEO_HOME
from .seo_analyzer_app import SEOAnalyzerApp, CrawlConfig, CrawlResult
from .utils.error_handler import TFQ0SEOError, TFQ0SEOException

__all__ = [
    'SEOAnalyzerApp', 
    'CrawlConfig', 
    'CrawlResult',
    'TFQ0SEOError', 
    'TFQ0SEOException', 
    'TFQSEO_HOME'
] 