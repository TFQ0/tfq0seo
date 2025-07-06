"""
Data Quality Scoring and Confidence Level Calculator for tfq0seo

This module provides confidence scoring for recommendations based on
data completeness, issue clarity, and analyzer reliability.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class DataQualityLevel(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INSUFFICIENT = "insufficient"


class ConfidenceLevel(Enum):
    """Confidence levels for recommendations"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataQualityScorer:
    """Calculate data quality scores and confidence levels"""
    
    def __init__(self):
        self.quality_thresholds = {
            'excellent': 0.9,
            'good': 0.75,
            'fair': 0.5,
            'poor': 0.25
        }
        
        self.analyzer_reliability = {
            'seo': 0.95,
            'content': 0.90,
            'technical': 0.85,
            'performance': 0.80,
            'links': 0.88
        }
        
        self.issue_clarity_scores = {
            # High clarity issues
            'missing_title': 1.0,
            'missing_description': 1.0,
            'missing_h1': 0.95,
            'no_https': 1.0,
            'missing_viewport': 1.0,
            
            # Medium clarity issues
            'thin_content': 0.75,
            'poor_readability': 0.70,
            'slow_page': 0.80,
            'broken_internal_links': 0.85,
            
            # Lower clarity issues
            'heading_hierarchy_skip': 0.60,
            'low_text_to_html_ratio': 0.65,
            'generic_anchor_text': 0.70
        }
    
    def calculate_recommendation_confidence(self, issue: Dict, page_data: Dict) -> Dict:
        """Calculate confidence level for a recommendation"""
        
        # Get component scores
        data_completeness = self._assess_data_completeness(page_data)
        issue_clarity = self._assess_issue_clarity(issue)
        pattern_frequency = self._check_pattern_frequency(issue.get('type', ''))
        analyzer_reliability = self._get_analyzer_reliability(issue.get('source', 'unknown'))
        
        # Weight factors
        weights = {
            'data_completeness': 0.4,
            'issue_clarity': 0.3,
            'pattern_frequency': 0.2,
            'analyzer_reliability': 0.1
        }
        
        # Calculate weighted confidence score
        confidence_factors = {
            'data_completeness': data_completeness,
            'issue_clarity': issue_clarity,
            'pattern_frequency': pattern_frequency,
            'analyzer_reliability': analyzer_reliability
        }
        
        confidence_score = sum(
            confidence_factors[factor] * weights[factor]
            for factor in weights
        )
        
        # Determine confidence level
        if confidence_score > 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_score > 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW
        
        return {
            'score': round(confidence_score, 2),
            'level': confidence_level.value,
            'factors': {k: round(v, 2) for k, v in confidence_factors.items()},
            'explanation': self._generate_confidence_explanation(confidence_level, confidence_factors)
        }
    
    def _assess_data_completeness(self, page_data: Dict) -> float:
        """Assess how complete the page data is"""
        
        required_fields = [
            'url',
            'status_code',
            'title',
            'meta_description',
            'content',
            'technical',
            'performance',
            'links'
        ]
        
        optional_fields = [
            'structured_data',
            'images',
            'scripts',
            'stylesheets',
            'headers',
            'cookies'
        ]
        
        # Check required fields
        required_present = sum(
            1 for field in required_fields
            if field in page_data and page_data[field] is not None
        )
        required_score = required_present / len(required_fields)
        
        # Check optional fields (bonus points)
        optional_present = sum(
            1 for field in optional_fields
            if field in page_data and page_data[field] is not None
        )
        optional_score = optional_present / len(optional_fields) * 0.2  # Max 0.2 bonus
        
        # Check for error indicators
        has_errors = page_data.get('errors', []) or page_data.get('parsing_errors', False)
        error_penalty = 0.2 if has_errors else 0
        
        # Check data quality within fields
        quality_score = self._assess_field_quality(page_data)
        
        # Calculate final score
        completeness_score = min(1.0, (required_score * 0.7 + quality_score * 0.3 + optional_score - error_penalty))
        
        return max(0.0, completeness_score)
    
    def _assess_field_quality(self, page_data: Dict) -> float:
        """Assess the quality of data within fields"""
        
        quality_indicators = []
        
        # Content quality
        content = page_data.get('content', {})
        if isinstance(content, dict):
            word_count = content.get('word_count', 0)
            if word_count > 0:
                quality_indicators.append(1.0)
            else:
                quality_indicators.append(0.0)
        
        # Technical data quality
        technical = page_data.get('technical', {})
        if isinstance(technical, dict):
            has_ssl_info = 'https' in technical
            has_mobile_info = 'mobile_friendly' in technical
            quality_indicators.append(1.0 if has_ssl_info and has_mobile_info else 0.5)
        
        # Performance data quality
        performance = page_data.get('performance', {})
        if isinstance(performance, dict):
            has_metrics = any(key in performance for key in ['load_time', 'size', 'requests'])
            quality_indicators.append(1.0 if has_metrics else 0.0)
        
        # Links data quality
        links = page_data.get('links', {})
        if isinstance(links, dict):
            has_link_data = any(key in links for key in ['internal_links', 'external_links', 'total_links'])
            quality_indicators.append(1.0 if has_link_data else 0.0)
        
        return sum(quality_indicators) / len(quality_indicators) if quality_indicators else 0.5
    
    def _assess_issue_clarity(self, issue: Dict) -> float:
        """Assess how clear and definitive the issue is"""
        
        issue_type = issue.get('type', '')
        
        # Use predefined clarity scores
        if issue_type in self.issue_clarity_scores:
            base_clarity = self.issue_clarity_scores[issue_type]
        else:
            # Default clarity based on severity
            severity = issue.get('severity', 'notice')
            severity_clarity = {
                'critical': 0.9,
                'warning': 0.7,
                'notice': 0.5
            }
            base_clarity = severity_clarity.get(severity, 0.5)
        
        # Adjust based on additional context
        adjustments = 0.0
        
        # Has specific values?
        if issue.get('current_value') and issue.get('recommended_value'):
            adjustments += 0.1
        
        # Has implementation steps?
        if issue.get('implementation_steps'):
            adjustments += 0.05
        
        # Has examples?
        if issue.get('example') or issue.get('examples'):
            adjustments += 0.05
        
        return min(1.0, base_clarity + adjustments)
    
    def _check_pattern_frequency(self, issue_type: str) -> float:
        """Check how common this issue pattern is"""
        
        # Common SEO issues (high confidence)
        very_common_issues = [
            'missing_title', 'missing_description', 'missing_h1',
            'missing_alt_text', 'slow_page', 'no_https'
        ]
        
        common_issues = [
            'thin_content', 'poor_readability', 'long_title',
            'short_description', 'multiple_h1', 'broken_links'
        ]
        
        uncommon_issues = [
            'heading_hierarchy_skip', 'generic_anchor_text',
            'excessive_internal_links', 'nav_without_list'
        ]
        
        if issue_type in very_common_issues:
            return 0.95
        elif issue_type in common_issues:
            return 0.80
        elif issue_type in uncommon_issues:
            return 0.60
        else:
            return 0.50  # Unknown pattern
    
    def _get_analyzer_reliability(self, source: str) -> float:
        """Get reliability score for the analyzer that detected the issue"""
        
        # Extract analyzer name from source
        analyzer = source.lower().split('_')[0] if '_' in source else source.lower()
        
        return self.analyzer_reliability.get(analyzer, 0.75)
    
    def _generate_confidence_explanation(self, level: ConfidenceLevel, factors: Dict) -> str:
        """Generate human-readable explanation of confidence level"""
        
        if level == ConfidenceLevel.HIGH:
            return "We're very confident about this recommendation based on complete data and clear issue detection."
        elif level == ConfidenceLevel.MEDIUM:
            weak_factors = [k for k, v in factors.items() if v < 0.7]
            if weak_factors:
                return f"Moderate confidence. Consider: {', '.join(weak_factors).replace('_', ' ')}."
            return "Moderate confidence in this recommendation."
        else:
            return "Lower confidence - recommendation based on limited data. Manual verification suggested."
    
    def calculate_page_data_quality(self, page_data: Dict) -> Dict:
        """Calculate overall data quality for a page"""
        
        completeness = self._assess_data_completeness(page_data)
        
        # Assess individual components
        component_scores = {
            'meta_data': self._assess_meta_data_quality(page_data),
            'content': self._assess_content_data_quality(page_data),
            'technical': self._assess_technical_data_quality(page_data),
            'performance': self._assess_performance_data_quality(page_data),
            'links': self._assess_links_data_quality(page_data)
        }
        
        # Calculate overall score
        overall_score = sum(component_scores.values()) / len(component_scores)
        
        # Determine quality level
        if overall_score >= self.quality_thresholds['excellent']:
            quality_level = DataQualityLevel.EXCELLENT
        elif overall_score >= self.quality_thresholds['good']:
            quality_level = DataQualityLevel.GOOD
        elif overall_score >= self.quality_thresholds['fair']:
            quality_level = DataQualityLevel.FAIR
        elif overall_score >= self.quality_thresholds['poor']:
            quality_level = DataQualityLevel.POOR
        else:
            quality_level = DataQualityLevel.INSUFFICIENT
        
        return {
            'overall_score': round(overall_score, 2),
            'quality_level': quality_level.value,
            'completeness': round(completeness, 2),
            'component_scores': {k: round(v, 2) for k, v in component_scores.items()},
            'warnings': self._generate_quality_warnings(component_scores, page_data),
            'recommendations': self._generate_quality_recommendations(component_scores, quality_level)
        }
    
    def _assess_meta_data_quality(self, page_data: Dict) -> float:
        """Assess quality of meta data"""
        
        score = 0.0
        checks = 0
        
        # Title check
        title = page_data.get('title', '')
        if title:
            score += 1.0
            if 10 < len(title) < 70:
                score += 0.5
        checks += 1.5
        
        # Description check
        description = page_data.get('meta_description', '')
        if description:
            score += 1.0
            if 50 < len(description) < 160:
                score += 0.5
        checks += 1.5
        
        # Meta tags check
        meta_tags = page_data.get('meta_tags', {})
        if isinstance(meta_tags, dict) and meta_tags:
            score += 0.5
            if 'canonical_url' in meta_tags:
                score += 0.5
        checks += 1.0
        
        return score / checks if checks > 0 else 0.0
    
    def _assess_content_data_quality(self, page_data: Dict) -> float:
        """Assess quality of content data"""
        
        content = page_data.get('content', {})
        if not isinstance(content, dict):
            return 0.0
        
        score = 0.0
        checks = 0
        
        # Word count
        if content.get('word_count', 0) > 0:
            score += 1.0
        checks += 1.0
        
        # Readability scores
        if content.get('readability'):
            score += 0.5
            if isinstance(content['readability'], dict) and content['readability'].get('flesch_score'):
                score += 0.5
        checks += 1.0
        
        # Heading structure
        if content.get('heading_structure'):
            score += 1.0
        checks += 1.0
        
        # Images data
        if 'images' in content:
            score += 0.5
        checks += 0.5
        
        return score / checks if checks > 0 else 0.0
    
    def _assess_technical_data_quality(self, page_data: Dict) -> float:
        """Assess quality of technical data"""
        
        technical = page_data.get('technical', {})
        if not isinstance(technical, dict):
            return 0.0
        
        essential_checks = ['https', 'mobile_friendly', 'canonical_url', 'robots_directives']
        present = sum(1 for check in essential_checks if check in technical)
        
        return present / len(essential_checks)
    
    def _assess_performance_data_quality(self, page_data: Dict) -> float:
        """Assess quality of performance data"""
        
        performance = page_data.get('performance', {})
        if not isinstance(performance, dict):
            return 0.0
        
        score = 0.0
        
        # Basic metrics
        if performance.get('load_time') is not None:
            score += 0.4
        
        if performance.get('size') is not None:
            score += 0.3
        
        if performance.get('requests') is not None:
            score += 0.3
        
        return score
    
    def _assess_links_data_quality(self, page_data: Dict) -> float:
        """Assess quality of links data"""
        
        links = page_data.get('links', {})
        if not isinstance(links, dict):
            return 0.0
        
        essential_metrics = ['internal_links', 'external_links', 'total_links']
        present = sum(1 for metric in essential_metrics if metric in links)
        
        base_score = present / len(essential_metrics)
        
        # Bonus for additional link quality metrics
        if links.get('broken_links') is not None:
            base_score += 0.1
        
        if links.get('redirect_chains') is not None:
            base_score += 0.1
        
        return min(1.0, base_score)
    
    def _generate_quality_warnings(self, component_scores: Dict, page_data: Dict) -> List[str]:
        """Generate warnings about data quality issues"""
        
        warnings = []
        
        # Check for low component scores
        for component, score in component_scores.items():
            if score < 0.5:
                warnings.append(f"{component.replace('_', ' ').title()} data is incomplete or missing")
        
        # Check for specific issues
        if page_data.get('errors'):
            warnings.append("Errors occurred during page analysis")
        
        if page_data.get('status_code', 200) != 200:
            warnings.append(f"Page returned status code {page_data.get('status_code')}")
        
        return warnings
    
    def _generate_quality_recommendations(self, component_scores: Dict, quality_level: DataQualityLevel) -> List[str]:
        """Generate recommendations for improving data quality"""
        
        recommendations = []
        
        if quality_level in [DataQualityLevel.POOR, DataQualityLevel.INSUFFICIENT]:
            recommendations.append("Re-analyze this page to get more complete data")
        
        # Component-specific recommendations
        low_scores = {k: v for k, v in component_scores.items() if v < 0.7}
        for component, score in sorted(low_scores.items(), key=lambda x: x[1]):
            if component == 'performance':
                recommendations.append("Enable performance monitoring for better insights")
            elif component == 'technical':
                recommendations.append("Check technical SEO settings and server configuration")
            elif component == 'content':
                recommendations.append("Ensure page has sufficient content for analysis")
        
        return recommendations[:3]  # Top 3 recommendations 