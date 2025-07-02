"""
tfq0seo - Enhanced SEO analysis and site crawling toolkit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A comprehensive SEO analysis toolkit with professional crawling capabilities
and industry-leading accuracy for reliable decision-making.

Enhanced Features (v2.1.0):
- Complete site crawling with configurable depth
- Comprehensive SEO analysis with validated accuracy
- Enhanced content optimization and duplicate detection
- Advanced technical SEO validation and monitoring
- Intelligent link analysis (internal/external/broken)
- Professional image optimization analysis
- Performance and Core Web Vitals measurement
- Mobile-friendly and accessibility testing
- Comprehensive security and certificate validation
- Rich results and structured data analysis
- Intelligent site structure and URL optimization
- Multiple export formats (JSON, CSV, XLSX, HTML)
- Real-time progress tracking with accuracy warnings
- Professional reporting dashboard with insights

Accuracy & Reliability Improvements (v2.1.0):
- Enhanced SEO scoring with dynamic algorithms
- Improved content analysis with technical term filtering
- Comprehensive HTTPS/SSL validation with certificate checking
- Advanced keyword analysis with adaptive thresholds
- Cross-module consistency validation and accuracy warnings
- Better mobile-friendly analysis with detailed assessments
- Robust error handling and data validation

Competitive with Screaming Frog SEO Spider but open source, extensible,
and designed for accuracy and reliability in professional environments.

For more information, visit: https://github.com/tfq0/tfq0seo
"""

__title__ = 'tfq0seo'
__version__ = '2.1.0'
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