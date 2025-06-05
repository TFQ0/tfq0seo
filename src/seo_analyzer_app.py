import yaml
import logging
import json
from typing import Dict, Optional, Union
from pathlib import Path

from .analyzers.meta_analyzer import MetaAnalyzer
from .analyzers.content_analyzer import ContentAnalyzer
from .analyzers.modern_seo_analyzer import ModernSEOAnalyzer
from .utils.cache_manager import cache_manager
from .utils.error_handler import setup_logging, TFQ0SEOError, handle_analysis_error

class SEOAnalyzerApp:
    """tfq0seo main application class.
    
    Provides comprehensive SEO analysis capabilities:
    - URL analysis
    - Content optimization
    - Meta tag validation
    - Modern SEO features
    - Performance analysis
    - Educational resources
    
    Features:
    - Caching support
    - Multiple export formats
    - Detailed recommendations
    - Educational content
    """
    
    def __init__(self, config_path: Union[str, Path] = 'config/seo_config.yaml'):
        """Initialize the tfq0seo application.
        
        Args:
            config_path: Path to YAML configuration file
        
        Raises:
            TFQ0SEOError: If configuration loading fails
        """
        self.config = self._load_config(config_path)
        setup_logging(self.config)
        self.logger = logging.getLogger('tfq0seo')
        
        # Initialize cache
        cache_manager.configure(self.config)
        
        # Initialize analyzers
        self.meta_analyzer = MetaAnalyzer(self.config)
        self.content_analyzer = ContentAnalyzer(self.config)
        self.modern_analyzer = ModernSEOAnalyzer(self.config)

    def _load_config(self, config_path: Union[str, Path]) -> Dict:
        """Load tfq0seo configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Dictionary containing configuration settings
            
        Raises:
            TFQ0SEOError: If configuration file cannot be loaded
        """
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise TFQ0SEOError(
                error_code='CONFIG_ERROR',
                message=f"Failed to load configuration: {str(e)}"
            )

    @handle_analysis_error
    def analyze_url(self, url: str, target_keyword: Optional[str] = None) -> Dict:
        """Perform comprehensive tfq0seo analysis on a URL.
        
        Analyzes multiple aspects:
        - Meta tags and technical SEO
        - Content optimization
        - Modern SEO features
        - Performance metrics
        - Security implementation
        
        Args:
            url: The URL to analyze
            target_keyword: Optional focus keyword for analysis
            
        Returns:
            Dictionary containing analysis results and recommendations
        """
        # Check cache first
        cache_key = f"url_analysis_{url}_{target_keyword}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            self.logger.info(f"Retrieved cached analysis for URL: {url}")
            return cached_result

        self.logger.info(f"Starting analysis for URL: {url}")
        
        # Perform analysis
        analysis = {
            'url': url,
            'target_keyword': target_keyword,
            'meta_analysis': self.meta_analyzer.analyze(url),
            'content_analysis': self.content_analyzer.analyze(url, target_keyword),
            'modern_seo_analysis': self.modern_analyzer.analyze(url)
        }
        
        # Combine recommendations
        analysis['combined_report'] = self._combine_reports(analysis)
        
        # Cache the result
        cache_manager.set(cache_key, analysis)
        
        return analysis

    @handle_analysis_error
    def analyze_content(self, content: str, target_keyword: Optional[str] = None) -> Dict:
        """Analyze text content for tfq0seo optimization.
        
        Performs content analysis:
        - Keyword optimization
        - Content structure
        - Readability metrics
        - SEO best practices
        
        Args:
            content: Text content to analyze
            target_keyword: Optional focus keyword
            
        Returns:
            Dictionary containing content analysis results
        """
        self.logger.info("Starting content analysis")
        
        # Perform content analysis
        analysis = {
            'content_length': len(content),
            'target_keyword': target_keyword,
            'content_analysis': self.content_analyzer.analyze(content, target_keyword)
        }
        
        return analysis

    def _combine_reports(self, analysis: Dict) -> Dict:
        """Combine analyzer reports into unified tfq0seo report.
        
        Merges results from:
        - Meta analysis
        - Content analysis
        - Modern SEO analysis
        
        Args:
            analysis: Dictionary containing individual analysis results
            
        Returns:
            Combined report with unified recommendations
        """
        combined = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }
        
        # Collect all findings
        for key in ['meta_analysis', 'content_analysis', 'modern_seo_analysis']:
            if key in analysis and isinstance(analysis[key], dict):
                report = analysis[key]
                for category in combined.keys():
                    if category in report:
                        combined[category].extend(report[category])
        
        # Remove duplicates while preserving order
        for category in combined.keys():
            combined[category] = list(dict.fromkeys(combined[category]))
        
        # Add summary
        combined['summary'] = {
            'total_strengths': len(combined['strengths']),
            'total_weaknesses': len(combined['weaknesses']),
            'total_recommendations': len(combined['recommendations']),
            'seo_score': self._calculate_seo_score(combined)
        }
        
        return combined

    def _calculate_seo_score(self, report: Dict) -> int:
        """Calculate overall tfq0seo score.
        
        Scoring factors:
        - Number of strengths (+2 points each, max 20)
        - Number of weaknesses (-5 points each, max -70)
        - Base score of 100 points
        
        Args:
            report: Combined analysis report
            
        Returns:
            Integer score between 0 and 100
        """
        total_points = 100
        deductions = 0
        
        # Calculate deductions based on weaknesses
        weakness_count = len(report['weaknesses'])
        if weakness_count > 0:
            deductions = min(weakness_count * 5, 70)  # Cap deductions at 70 points
        
        # Add bonus points for strengths
        strength_bonus = min(len(report['strengths']) * 2, 20)  # Cap bonus at 20 points
        
        final_score = max(0, min(100, total_points - deductions + strength_bonus))
        return final_score

    def get_educational_resources(self, topic: Optional[str] = None) -> Dict:
        """Get tfq0seo educational resources.
        
        Provides learning materials on:
        - Meta tags optimization
        - Content SEO strategies
        - Technical SEO implementation
        
        Args:
            topic: Optional specific topic to retrieve
            
        Returns:
            Dictionary containing educational resources
        """
        resources = {
            'meta_tags': [
                {
                    'title': 'Understanding Meta Tags',
                    'description': 'Learn about the importance of meta tags in SEO',
                    'key_points': [
                        'Title tag best practices',
                        'Meta description optimization',
                        'Robots meta directives'
                    ]
                }
            ],
            'content_optimization': [
                {
                    'title': 'Content SEO Guide',
                    'description': 'Best practices for SEO-friendly content',
                    'key_points': [
                        'Keyword research and placement',
                        'Content structure and readability',
                        'Internal linking strategies'
                    ]
                }
            ],
            'technical_seo': [
                {
                    'title': 'Technical SEO Fundamentals',
                    'description': 'Understanding technical aspects of SEO',
                    'key_points': [
                        'Site structure and navigation',
                        'Mobile optimization',
                        'Page speed optimization'
                    ]
                }
            ]
        }
        
        if topic and topic in resources:
            return {topic: resources[topic]}
        return resources

    def get_recommendation_details(self, recommendation: str) -> Dict:
        """Get detailed tfq0seo recommendation information.
        
        Provides:
        - Implementation steps
        - Importance level
        - Resource links
        - Verification process
        
        Args:
            recommendation: The recommendation to get details for
            
        Returns:
            Dictionary containing detailed recommendation information
        """
        return {
            'recommendation': recommendation,
            'importance': 'high',
            'implementation_guide': [
                'Step 1: Understanding the issue',
                'Step 2: Implementation steps',
                'Step 3: Verification process'
            ],
            'resources': [
                'Documentation link 1',
                'Tutorial link 2'
            ]
        }

    def export_report(self, analysis: Dict, format: str = 'json') -> str:
        """Export tfq0seo analysis report.
        
        Supported formats:
        - JSON (detailed data)
        - HTML (formatted report)
        - Markdown (readable text)
        
        Args:
            analysis: Analysis results to export
            format: Output format (json, html, or markdown)
            
        Returns:
            Formatted report string
            
        Raises:
            ValueError: If format is not supported
        """
        if format == 'json':
            return json.dumps(analysis, indent=2)
        elif format == 'html':
            return self._generate_html_report(analysis)
        elif format == 'markdown':
            return self._generate_markdown_report(analysis)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _generate_html_report(self, analysis: Dict) -> str:
        """Generate HTML report for tfq0seo analysis.
        
        Creates a formatted HTML report with:
        - Styled sections
        - Color-coded results
        - Structured layout
        
        Args:
            analysis: Analysis results to format
            
        Returns:
            HTML formatted report
        """
        html = """
        <html>
            <head>
                <title>tfq0seo Analysis Report</title>
                <style>
                    body { font-family: Arial, sans-serif; }
                    .strength { color: green; }
                    .weakness { color: red; }
                    .recommendation { color: blue; }
                </style>
            </head>
            <body>
                <h1>tfq0seo Analysis Report</h1>
        """
        
        # Add sections
        for section, items in analysis['combined_report'].items():
            if isinstance(items, list):
                html += f"<h2>{section.title()}</h2><ul>"
                for item in items:
                    html += f"<li class='{section.lower()}'>{item}</li>"
                html += "</ul>"
        
        html += "</body></html>"
        return html

    def _generate_markdown_report(self, analysis: Dict) -> str:
        """Generate Markdown report for tfq0seo analysis.
        
        Creates a readable text report with:
        - Structured sections
        - Summary statistics
        - Formatted lists
        
        Args:
            analysis: Analysis results to format
            
        Returns:
            Markdown formatted report
        """
        md = "# tfq0seo Analysis Report\n\n"
        
        # Add summary
        if 'summary' in analysis['combined_report']:
            md += "## Summary\n"
            md += f"- SEO Score: {analysis['combined_report']['summary']['seo_score']}/100\n"
            md += f"- Total Strengths: {analysis['combined_report']['summary']['total_strengths']}\n"
            md += f"- Total Weaknesses: {analysis['combined_report']['summary']['total_weaknesses']}\n"
            md += f"- Total Recommendations: {analysis['combined_report']['summary']['total_recommendations']}\n\n"
        
        # Add sections
        for section, items in analysis['combined_report'].items():
            if isinstance(items, list) and items:
                md += f"## {section.title()}\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"
        
        return md 