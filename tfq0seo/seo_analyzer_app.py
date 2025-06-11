import logging
import json
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
import os
import time
import requests
from bs4 import BeautifulSoup

from .analyzers.meta_analyzer import MetaAnalyzer
from .analyzers.content_analyzer import ContentAnalyzer
from .analyzers.modern_seo_analyzer import ModernSEOAnalyzer
from .analyzers.competitive_analyzer import CompetitiveAnalyzer
from .analyzers.advanced_analyzer import AdvancedSEOAnalyzer
from .reporting.report_formatter import ReportFormatter
from .reporting.detailed_report import DetailedReport
from .utils.cache_manager import CacheManager
from .utils.error_handler import setup_logging, handle_analysis_error, TFQ0SEOError
from .utils.paths import TFQSEO_HOME

# Setup logging
setup_logging(TFQSEO_HOME / 'tfq0seo.log')

# Default settings that were previously in config
DEFAULT_SETTINGS = {
    'version': '1.0.8',  # Track settings version
    'seo_thresholds': {
        'title_length': {'min': 30, 'max': 60},
        'meta_description_length': {'min': 120, 'max': 160},
        'content_length': {'min': 300},
        'sentence_length': {'max': 20},
        'keyword_density': {'max': 3.0}
    },
    'readability_thresholds': {
        'flesch_reading_ease': {'min': 60},
        'gunning_fog': {'max': 12}
    },
    'crawling': {
        'timeout': 30,
        'max_retries': 3,
        'user_agent': 'TFQ0SEO/1.0'
    },
    'cache': {
        'enabled': True,
        'expiration': 3600,
        'directory': str(TFQSEO_HOME / 'cache')  # Absolute path in user's home
    },
    'logging': {
        'level': 'INFO',
        'file': str(TFQSEO_HOME / 'tfq0seo.log'),  # Absolute path in user's home
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'max_size': 10485760,  # 10MB
        'backup_count': 5
    }
}

class SEOAnalyzerApp:
    """tfq0seo main application class.
    
    Provides comprehensive SEO analysis capabilities:
    - URL analysis
    - Content optimization
    - Meta tag validation
    - Modern SEO features
    - Competitive analysis
    - Advanced SEO features
    - Educational resources
    
    Features:
    - Caching support
    - Multiple export formats
    - Detailed recommendations
    - Educational content
    """
    
    def __init__(self):
        """Initialize the tfq0seo application."""
        self.settings = DEFAULT_SETTINGS
        
        # Set up logging
        log_file = TFQSEO_HOME / 'tfq0seo.log'
        setup_logging(log_file)
        self.logger = logging.getLogger('tfq0seo')
        
        # Initialize analyzers
        self.meta_analyzer = MetaAnalyzer(self.settings)
        self.content_analyzer = ContentAnalyzer(self.settings)
        self.modern_analyzer = ModernSEOAnalyzer(self.settings)
        self.competitive_analyzer = CompetitiveAnalyzer(self.settings)
        self.advanced_analyzer = AdvancedSEOAnalyzer(self.settings)
        
        # Initialize cache
        self.cache = CacheManager(
            self.settings['cache']['directory'], 
            self.settings['cache']['expiration']
        )

    def analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze a URL for SEO optimization.
        
        Args:
            url: URL to analyze
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            TFQ0SEOError: If URL analysis fails
        """
        self.logger.info(f"Starting analysis for URL: {url}")
        
        # Check cache first
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.logger.info(f"Retrieved cached analysis for URL: {url}")
            return cached_result
        
        # Fetch URL content
        try:
            response = requests.get(url, timeout=self.settings['crawling']['timeout'])
            response.raise_for_status()
        except Exception as e:
            raise TFQ0SEOError(
                error_code="URL_ERROR",
                message=f"Failed to fetch URL: {url}",
                details={'error': str(e)}
            )
        
        if not response.headers.get('content-type', '').startswith('text/html'):
            raise TFQ0SEOError(
                error_code="INVALID_CONTENT_TYPE",
                message=f"URL does not return HTML content: {url}",
                details={'content_type': response.headers.get('content-type')}
            )
        
        # Analyze content
        content = response.text
        soup = BeautifulSoup(content, 'html.parser')
        
        analysis = {
            'url': url,
            'meta_analysis': self.meta_analyzer.analyze(soup),
            'content_analysis': self.content_analyzer.analyze(content),
            'modern_seo_analysis': self.modern_analyzer.analyze(soup),
            'combined_report': self._combine_reports({
                'meta_analysis': self.meta_analyzer.analyze(soup),
                'content_analysis': self.content_analyzer.analyze(content),
                'modern_seo_analysis': self.modern_analyzer.analyze(soup)
            })
        }
        
        # Cache results
        self.cache.set(cache_key, analysis)
        
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
        - Competitive analysis (if available)
        - Advanced analysis (if available)
        
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
        for key in ['meta_analysis', 'content_analysis', 'modern_seo_analysis', 'competitive_analysis', 'advanced_analysis']:
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
        """Calculate overall SEO score based on analysis results.
        
        The score is calculated using:
        - Number of strengths vs weaknesses
        - Implementation of critical SEO elements
        - Content optimization level
        - Technical implementation quality
        
        Args:
            report: Dictionary containing analysis results
            
        Returns:
            Integer score from 0-100
        """
        base_score = 100
        
        # Deduct points for each weakness
        weakness_penalty = min(50, len(report['weaknesses']) * 5)
        base_score -= weakness_penalty
        
        # Add points for strengths
        strength_bonus = min(20, len(report['strengths']) * 2)
        base_score += strength_bonus
        
        # Ensure score stays within 0-100 range
        return max(0, min(100, base_score))

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

    def generate_report(self, analysis: Dict, format: str = 'markdown', output_path: Optional[str] = None) -> str:
        """Generate detailed analysis report.
        
        Args:
            analysis: Analysis results dictionary
            format: Output format ('markdown', 'html', 'json', 'csv')
            output_path: Optional path to save report
            
        Returns:
            Formatted report string
        """
        # Generate detailed report
        detailed_report = DetailedReport(analysis)
        report_data = detailed_report.generate_report(format)
        
        # Format report
        formatter = ReportFormatter(report_data)
        return formatter.format_report(format, output_path)

    def export_report(self, analysis: Dict[str, Any], format: str = 'markdown', output_path: Optional[str] = None) -> str:
        """Export analysis report in specified format.
        
        Args:
            analysis: Analysis results to export
            format: Report format ('markdown', 'html', or 'json')
            output_path: Optional path to save report to
        
        Returns:
            Formatted report string
        """
        # Generate detailed report
        detailed_report = DetailedReport(analysis)
        report = detailed_report.generate_report(format)
        
        # Save to file if path provided
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report

    @handle_analysis_error
    def comprehensive_analysis(self, url: str, options: Dict = None) -> Dict:
        """Perform a comprehensive SEO analysis with all available features.
        
        This function combines all analyzers to provide the most detailed analysis:
        - Basic SEO elements
        - Content optimization
        - Technical implementation
        - User experience
        - Competitive positioning
        - Advanced SEO features
        - Performance metrics
        
        Args:
            url: The URL to analyze
            options: Optional configuration dictionary with the following keys:
                - target_keyword: Focus keyword for analysis
                - competitor_urls: List of competitor URLs
                - depth: Analysis depth ('basic', 'advanced', 'complete')
                - custom_thresholds: Custom analysis thresholds
                - export_format: Desired export format
                - cache_results: Whether to cache results
        
        Returns:
            Dictionary containing comprehensive analysis results
        """
        # Set default options
        default_options = {
            'target_keyword': None,
            'competitor_urls': None,
            'depth': 'complete',
            'custom_thresholds': None,
            'export_format': 'json',
            'cache_results': True
        }
        options = {**default_options, **(options or {})}
        
        # Generate cache key based on options
        cache_key = f"comprehensive_analysis_{url}_{hash(str(options))}"
        
        # Check cache if enabled
        if options['cache_results']:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Retrieved cached comprehensive analysis for URL: {url}")
                return cached_result

        self.logger.info(f"Starting comprehensive analysis for URL: {url}")
        
        # Initialize analysis dictionary
        analysis = {
            'url': url,
            'analysis_options': options,
            'timestamp': time.time(),
            'analysis_modules': {}
        }
        
        try:
            # Basic SEO Analysis
            analysis['analysis_modules']['basic_seo'] = {
                'meta_tags': self.meta_analyzer.analyze(url),
                'content': self.content_analyzer.analyze(url, options['target_keyword'])
            }
            
            # Modern SEO Features
            analysis['analysis_modules']['modern_seo'] = self.modern_analyzer.analyze(url)
            
            # Competitive Analysis (if competitor URLs provided)
            if options['competitor_urls']:
                analysis['analysis_modules']['competitive'] = self.competitive_analyzer.analyze(
                    url, 
                    options['competitor_urls']
                )
            
            # Advanced Analysis (for 'advanced' and 'complete' depth)
            if options['depth'] in ['advanced', 'complete']:
                analysis['analysis_modules']['advanced'] = self.advanced_analyzer.analyze(url)
            
            # Performance Analysis
            analysis['analysis_modules']['performance'] = self._analyze_performance(url)
            
            # Security Analysis
            analysis['analysis_modules']['security'] = self._analyze_security(url)
            
            # Mobile Optimization
            analysis['analysis_modules']['mobile'] = self._analyze_mobile_optimization(url)
            
            # Generate Insights
            analysis['insights'] = self._generate_comprehensive_insights(analysis)
            
            # Calculate Overall Scores
            analysis['scores'] = self._calculate_comprehensive_scores(analysis)
            
            # Generate Action Plan
            analysis['action_plan'] = self._generate_action_plan(analysis)
            
            # Add Summary
            analysis['summary'] = self._generate_comprehensive_summary(analysis)
            
        except Exception as e:
            self.logger.error(f"Error during comprehensive analysis: {str(e)}")
            analysis['error'] = str(e)
        
        # Cache results if enabled
        if options['cache_results']:
            self.cache.set(cache_key, analysis)
        
        return analysis

    def _analyze_performance(self, url: str) -> Dict:
        """Analyze website performance metrics."""
        return {
            'load_time': self._measure_load_time(url),
            'resource_optimization': self._check_resource_optimization(url),
            'caching_implementation': self._check_caching(url),
            'compression': self._check_compression(url),
            'cdn_usage': self._check_cdn_usage(url)
        }

    def _analyze_security(self, url: str) -> Dict:
        """Analyze website security implementation."""
        return {
            'ssl_certificate': self._check_ssl(url),
            'security_headers': self._check_security_headers(url),
            'content_security_policy': self._check_csp(url),
            'xss_protection': self._check_xss_protection(url),
            'mixed_content': self._check_mixed_content(url)
        }

    def _analyze_mobile_optimization(self, url: str) -> Dict:
        """Analyze mobile optimization implementation."""
        return {
            'viewport_configuration': self._check_viewport(url),
            'responsive_design': self._check_responsive_design(url),
            'touch_elements': self._check_touch_elements(url),
            'mobile_performance': self._check_mobile_performance(url),
            'app_integration': self._check_app_integration(url)
        }

    def _generate_comprehensive_insights(self, analysis: Dict) -> Dict:
        """Generate insights from comprehensive analysis results."""
        insights = {
            'critical_issues': [],
            'major_improvements': [],
            'minor_improvements': [],
            'positive_aspects': [],
            'competitive_edges': [],
            'market_opportunities': []
        }
        
        # Analyze basic SEO elements
        if 'basic_seo' in analysis['analysis_modules']:
            self._analyze_basic_seo_insights(analysis['analysis_modules']['basic_seo'], insights)
        
        # Analyze modern SEO features
        if 'modern_seo' in analysis['analysis_modules']:
            self._analyze_modern_seo_insights(analysis['analysis_modules']['modern_seo'], insights)
        
        # Analyze competitive positioning
        if 'competitive' in analysis['analysis_modules']:
            self._analyze_competitive_insights(analysis['analysis_modules']['competitive'], insights)
        
        # Analyze advanced features
        if 'advanced' in analysis['analysis_modules']:
            self._analyze_advanced_insights(analysis['analysis_modules']['advanced'], insights)
        
        return insights

    def _calculate_comprehensive_scores(self, analysis: Dict) -> Dict:
        """Calculate comprehensive SEO scores."""
        scores = {
            'overall_score': 0,
            'category_scores': {
                'technical_seo': self._calculate_technical_score(analysis),
                'content_quality': self._calculate_content_score(analysis),
                'user_experience': self._calculate_ux_score(analysis),
                'performance': self._calculate_performance_score(analysis),
                'mobile_optimization': self._calculate_mobile_score(analysis),
                'security': self._calculate_security_score(analysis)
            }
        }
        
        # Calculate weighted overall score
        weights = {
            'technical_seo': 0.25,
            'content_quality': 0.25,
            'user_experience': 0.15,
            'performance': 0.15,
            'mobile_optimization': 0.1,
            'security': 0.1
        }
        
        scores['overall_score'] = sum(
            scores['category_scores'][category] * weight
            for category, weight in weights.items()
        )
        
        return scores

    def _generate_action_plan(self, analysis: Dict) -> Dict:
        """Generate prioritized action plan based on analysis results."""
        return {
            'critical_actions': self._get_critical_actions(analysis),
            'high_priority': self._get_high_priority_actions(analysis),
            'medium_priority': self._get_medium_priority_actions(analysis),
            'low_priority': self._get_low_priority_actions(analysis),
            'monitoring_tasks': self._get_monitoring_tasks(analysis)
        }

    def _generate_comprehensive_summary(self, analysis: Dict) -> Dict:
        """Generate executive summary of comprehensive analysis."""
        return {
            'overview': {
                'total_issues': len(analysis['insights']['critical_issues']) + len(analysis['insights']['major_improvements']),
                'critical_issues': len(analysis['insights']['critical_issues']),
                'overall_score': analysis['scores']['overall_score'],
                'strongest_category': max(analysis['scores']['category_scores'].items(), key=lambda x: x[1])[0],
                'weakest_category': min(analysis['scores']['category_scores'].items(), key=lambda x: x[1])[0]
            },
            'key_findings': self._get_key_findings(analysis),
            'competitive_position': self._get_competitive_position(analysis),
            'estimated_impact': self._estimate_improvement_impact(analysis)
        }

    def _measure_load_time(self, url: str) -> Dict:
        """Measure page load time metrics."""
        try:
            start_time = time.time()
            response = requests.get(url, headers=self.settings['crawling']['user_agent'])
            end_time = time.time()
            
            return {
                'total_time': end_time - start_time,
                'time_to_first_byte': response.elapsed.total_seconds(),
                'download_time': (end_time - start_time) - response.elapsed.total_seconds()
            }
        except Exception as e:
            self.logger.error(f"Error measuring load time: {str(e)}")
            return {'error': str(e)}

    def _check_resource_optimization(self, url: str) -> Dict:
        """Check resource optimization implementation."""
        try:
            response = requests.get(url, headers=self.settings['crawling']['user_agent'])
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'minified_resources': self._check_minification(soup),
                'image_optimization': self._check_image_optimization(soup),
                'resource_hints': self._check_resource_hints(soup),
                'async_loading': self._check_async_loading(soup)
            }
        except Exception as e:
            self.logger.error(f"Error checking resource optimization: {str(e)}")
            return {'error': str(e)}

    def _check_minification(self, soup: BeautifulSoup) -> Dict:
        """Check resource minification status."""
        scripts = soup.find_all('script', src=True)
        styles = soup.find_all('link', rel='stylesheet')
        
        return {
            'js_minified': len([s for s in scripts if '.min.js' in s['src']]) / max(len(scripts), 1),
            'css_minified': len([s for s in styles if '.min.css' in s['href']]) / max(len(styles), 1),
            'total_resources': len(scripts) + len(styles),
            'minification_opportunities': [
                s['src'] for s in scripts if '.min.js' not in s['src']
            ] + [
                s['href'] for s in styles if '.min.css' not in s['href']
            ]
        }

    def _check_image_optimization(self, soup: BeautifulSoup) -> Dict:
        """Check image optimization implementation."""
        images = soup.find_all('img')
        
        return {
            'total_images': len(images),
            'responsive_images': len([img for img in images if img.get('srcset') or img.get('sizes')]),
            'lazy_loading': len([img for img in images if img.get('loading') == 'lazy']),
            'alt_texts': len([img for img in images if img.get('alt')]),
            'optimization_opportunities': [
                img['src'] for img in images 
                if not img.get('srcset') and not img.get('loading') == 'lazy'
            ]
        }

    def _check_resource_hints(self, soup: BeautifulSoup) -> Dict:
        """Check implementation of resource hints."""
        hints = soup.find_all('link', rel=lambda x: x in ['preload', 'prefetch', 'preconnect', 'dns-prefetch'])
        
        return {
            'total_hints': len(hints),
            'by_type': {
                'preload': len([h for h in hints if h['rel'] == ['preload']]),
                'prefetch': len([h for h in hints if h['rel'] == ['prefetch']]),
                'preconnect': len([h for h in hints if h['rel'] == ['preconnect']]),
                'dns-prefetch': len([h for h in hints if h['rel'] == ['dns-prefetch']])
            },
            'optimization_opportunities': bool(len(hints) < 3)
        }

    def _check_async_loading(self, soup: BeautifulSoup) -> Dict:
        """Check asynchronous resource loading."""
        scripts = soup.find_all('script', src=True)
        
        return {
            'total_scripts': len(scripts),
            'async_scripts': len([s for s in scripts if s.get('async')]),
            'defer_scripts': len([s for s in scripts if s.get('defer')]),
            'optimization_opportunities': [
                s['src'] for s in scripts 
                if not s.get('async') and not s.get('defer')
            ]
        }

    def _check_caching(self, url: str) -> Dict:
        # Implementation of _check_caching method
        pass

    def _check_compression(self, url: str) -> Dict:
        # Implementation of _check_compression method
        pass

    def _check_cdn_usage(self, url: str) -> Dict:
        # Implementation of _check_cdn_usage method
        pass

    def _check_ssl(self, url: str) -> Dict:
        # Implementation of _check_ssl method
        pass

    def _check_security_headers(self, url: str) -> Dict:
        # Implementation of _check_security_headers method
        pass

    def _check_csp(self, url: str) -> Dict:
        # Implementation of _check_csp method
        pass

    def _check_xss_protection(self, url: str) -> Dict:
        # Implementation of _check_xss_protection method
        pass

    def _check_mixed_content(self, url: str) -> Dict:
        # Implementation of _check_mixed_content method
        pass

    def _check_viewport(self, url: str) -> Dict:
        # Implementation of _check_viewport method
        pass

    def _check_responsive_design(self, url: str) -> Dict:
        # Implementation of _check_responsive_design method
        pass

    def _check_touch_elements(self, url: str) -> Dict:
        # Implementation of _check_touch_elements method
        pass

    def _check_mobile_performance(self, url: str) -> Dict:
        # Implementation of _check_mobile_performance method
        pass

    def _check_app_integration(self, url: str) -> Dict:
        # Implementation of _check_app_integration method
        pass

    def _analyze_basic_seo_insights(self, basic_seo: Dict, insights: Dict) -> None:
        """Analyze basic SEO elements and generate insights."""
        meta = basic_seo.get('meta_tags', {})
        content = basic_seo.get('content', {})
        
        # Check title and meta description
        if meta.get('title_length', 0) < 30 or meta.get('title_length', 0) > 60:
            insights['major_improvements'].append(
                "Title tag length is not optimal (should be 30-60 characters)"
            )
        else:
            insights['positive_aspects'].append("Title tag length is optimal")
            
        if meta.get('meta_description_length', 0) < 120 or meta.get('meta_description_length', 0) > 160:
            insights['major_improvements'].append(
                "Meta description length is not optimal (should be 120-160 characters)"
            )
        else:
            insights['positive_aspects'].append("Meta description length is optimal")
        
        # Check content quality
        if content.get('word_count', 0) < 300:
            insights['major_improvements'].append(
                "Content length is too short (minimum 300 words recommended)"
            )
        else:
            insights['positive_aspects'].append("Content length is sufficient")
            
        if content.get('keyword_density', 0) > 3.0:
            insights['major_improvements'].append(
                "Keyword density is too high (maximum 3% recommended)"
            )
        else:
            insights['positive_aspects'].append("Keyword density is optimal")

    def _analyze_modern_seo_insights(self, modern_seo: Dict, insights: Dict) -> None:
        """Analyze modern SEO features and generate insights."""
        # Check schema markup
        if not modern_seo.get('has_schema'):
            insights['major_improvements'].append(
                "Missing Schema.org markup for rich results"
            )
        else:
            insights['positive_aspects'].append("Implemented Schema.org markup")
        
        # Check social meta tags
        if not modern_seo.get('has_social_meta'):
            insights['minor_improvements'].append(
                "Missing social media meta tags (Open Graph, Twitter Cards)"
            )
        else:
            insights['positive_aspects'].append("Social media meta tags implemented")
        
        # Check mobile optimization
        if not modern_seo.get('mobile_friendly'):
            insights['critical_issues'].append(
                "Page is not mobile-friendly"
            )
        else:
            insights['positive_aspects'].append("Page is mobile-friendly")

    def _analyze_competitive_insights(self, competitive: Dict, insights: Dict) -> None:
        """Analyze competitive positioning and generate insights."""
        relative_position = competitive.get('relative_position', {})
        
        # Analyze content length compared to competitors
        if relative_position.get('content_length', {}).get('difference', 0) < 0:
            insights['major_improvements'].append(
                f"Content length is below competitor average by {abs(relative_position['content_length']['difference'])} words"
            )
        else:
            insights['competitive_edges'].append(
                f"Content length is above competitor average by {relative_position['content_length']['difference']} words"
            )
        
        # Analyze feature implementation
        features = competitive.get('feature_comparison', {})
        missing_features = [
            feature for feature, implemented in features.items()
            if not implemented and any(comp.get(feature) for comp in competitive.get('competitor_features', []))
        ]
        
        if missing_features:
            insights['market_opportunities'].extend([
                f"Implement {feature.replace('_', ' ')} to match competitors"
                for feature in missing_features
            ])

    def _analyze_advanced_insights(self, advanced: Dict, insights: Dict) -> None:
        """Analyze advanced SEO features and generate insights."""
        # Analyze user experience
        ux = advanced.get('user_experience', {})
        if not ux.get('navigation', {}).get('has_clear_structure'):
            insights['major_improvements'].append(
                "Navigation structure needs improvement for better user experience"
            )
        
        # Analyze accessibility
        acc = ux.get('accessibility', {})
        if acc.get('image_alts', 0) < 0.9:
            insights['major_improvements'].append(
                "Add alt text to images for better accessibility"
            )
        
        # Analyze content clustering
        clusters = advanced.get('content_clusters', {})
        if not clusters.get('topic_hierarchy', {}).get('has_proper_hierarchy'):
            insights['major_improvements'].append(
                "Improve content hierarchy with proper heading structure"
            )
        
        # Analyze rich results potential
        rich = advanced.get('rich_results', {})
        if not rich.get('schema_types'):
            insights['market_opportunities'].append(
                "Implement structured data for rich results in search"
            )

    def _calculate_technical_score(self, analysis: Dict) -> float:
        """Calculate technical SEO score."""
        score = 100.0
        deductions = {
            'missing_meta_tags': 10,
            'invalid_robots_txt': 5,
            'missing_sitemap': 5,
            'poor_url_structure': 5,
            'missing_canonical': 5,
            'missing_security_headers': 10,
            'slow_loading_speed': 10
        }
        
        # Check meta tags
        if not analysis['analysis_modules'].get('basic_seo', {}).get('meta_tags', {}).get('has_all_meta'):
            score -= deductions['missing_meta_tags']
        
        # Check security
        if not analysis['analysis_modules'].get('security', {}).get('security_headers', {}).get('has_all_headers'):
            score -= deductions['missing_security_headers']
        
        # Check performance
        if analysis['analysis_modules'].get('performance', {}).get('load_time', {}).get('total_time', 0) > 3:
            score -= deductions['slow_loading_speed']
        
        return max(0, score)

    def _calculate_content_score(self, analysis: Dict) -> float:
        """Calculate content quality score."""
        score = 100.0
        deductions = {
            'short_content': 15,
            'keyword_density_issues': 10,
            'poor_readability': 10,
            'thin_content': 15,
            'duplicate_content': 20,
            'missing_media': 5
        }
        
        content = analysis['analysis_modules'].get('basic_seo', {}).get('content', {})
        
        # Check content length
        if content.get('word_count', 0) < 300:
            score -= deductions['short_content']
        
        # Check keyword density
        if content.get('keyword_density', 0) > 3.0:
            score -= deductions['keyword_density_issues']
        
        # Check readability
        if content.get('readability_score', 0) < 60:
            score -= deductions['poor_readability']
        
        return max(0, score)

    def _calculate_ux_score(self, analysis: Dict) -> float:
        # Implementation of _calculate_ux_score method
        pass

    def _calculate_performance_score(self, analysis: Dict) -> float:
        # Implementation of _calculate_performance_score method
        pass

    def _calculate_mobile_score(self, analysis: Dict) -> float:
        # Implementation of _calculate_mobile_score method
        pass

    def _calculate_security_score(self, analysis: Dict) -> float:
        # Implementation of _calculate_security_score method
        pass

    def _get_critical_actions(self, analysis: Dict) -> List[str]:
        """Get list of critical actions based on analysis."""
        actions = []
        
        # Add critical issues from insights
        actions.extend(analysis.get('insights', {}).get('critical_issues', []))
        
        # Check security issues
        security = analysis['analysis_modules'].get('security', {})
        if not security.get('ssl_certificate', {}).get('is_valid'):
            actions.append("Fix SSL certificate issues")
        
        # Check critical performance issues
        performance = analysis['analysis_modules'].get('performance', {})
        if performance.get('load_time', {}).get('total_time', 0) > 5:
            actions.append("Address critical performance issues - page load time > 5s")
        
        return actions

    def _get_high_priority_actions(self, analysis: Dict) -> List[str]:
        # Implementation of _get_high_priority_actions method
        pass

    def _get_medium_priority_actions(self, analysis: Dict) -> List[str]:
        # Implementation of _get_medium_priority_actions method
        pass

    def _get_low_priority_actions(self, analysis: Dict) -> List[str]:
        # Implementation of _get_low_priority_actions method
        pass

    def _get_monitoring_tasks(self, analysis: Dict) -> List[str]:
        # Implementation of _get_monitoring_tasks method
        pass

    def _get_key_findings(self, analysis: Dict) -> List[str]:
        """Get key findings from analysis results."""
        findings = []
        
        # Add strongest aspects
        findings.extend([
            f"Strength: {aspect}"
            for aspect in analysis.get('insights', {}).get('positive_aspects', [])[:3]
        ])
        
        # Add major improvement areas
        findings.extend([
            f"Improvement: {improvement}"
            for improvement in analysis.get('insights', {}).get('major_improvements', [])[:3]
        ])
        
        # Add competitive insights
        findings.extend([
            f"Competition: {insight}"
            for insight in analysis.get('insights', {}).get('market_opportunities', [])[:2]
        ])
        
        return findings

    def _get_competitive_position(self, analysis: Dict) -> str:
        # Implementation of _get_competitive_position method
        pass

    def _estimate_improvement_impact(self, analysis: Dict) -> Dict:
        """Estimate potential impact of implementing improvements."""
        return {
            'estimated_traffic_increase': self._calculate_traffic_impact(analysis),
            'estimated_conversion_impact': self._calculate_conversion_impact(analysis),
            'implementation_complexity': self._assess_implementation_complexity(analysis),
            'priority_score': self._calculate_priority_score(analysis)
        }

    def _calculate_traffic_impact(self, analysis: Dict) -> float:
        # Implementation of _calculate_traffic_impact method
        pass

    def _calculate_conversion_impact(self, analysis: Dict) -> float:
        # Implementation of _calculate_conversion_impact method
        pass

    def _assess_implementation_complexity(self, analysis: Dict) -> str:
        # Implementation of _assess_implementation_complexity method
        pass

    def _calculate_priority_score(self, analysis: Dict) -> float:
        # Implementation of _calculate_priority_score method
        pass 