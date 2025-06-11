"""
tfq0seo - Modern SEO analysis and optimization toolkit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A comprehensive SEO analysis toolkit with advanced reporting capabilities.

Features:
- Modern SEO analysis and recommendations
- Content optimization guidance
- Technical SEO validation
- Mobile-friendly testing
- Performance analysis
- Security checks
- Social media optimization
- Educational insights

For more information, visit: https://github.com/tfq0/tfq0seo
"""

__title__ = 'tfq0seo'
__version__ = '1.0.8'
__author__ = 'tfq0'
__license__ = 'MIT'
__copyright__ = 'Copyright 2024 tfq0'

from .utils.paths import TFQSEO_HOME
from .seo_analyzer_app import SEOAnalyzerApp
from .utils.error_handler import TFQ0SEOError, TFQ0SEOException

__all__ = ['SEOAnalyzerApp', 'TFQ0SEOError', 'TFQ0SEOException', 'TFQSEO_HOME'] 