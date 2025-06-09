"""
tfq0seo
=======

A comprehensive SEO analysis tool that helps you analyze websites and content
while learning SEO best practices.

Features:
- Modern SEO analysis and recommendations
- Content optimization guidance
- Technical SEO validation
- Mobile-friendly testing
- Performance analysis
- Security checks
- Social media optimization
- Educational insights

For more information, visit: https://github.com/tfq66/tfq0seo
"""

__version__ = '1.0.4'
__author__ = 'TFQ0'
__license__ = 'MIT'

from .seo_analyzer_app import SEOAnalyzerApp
from .utils.error_handler import TFQ0SEOError

__all__ = ['SEOAnalyzerApp', 'TFQ0SEOError'] 