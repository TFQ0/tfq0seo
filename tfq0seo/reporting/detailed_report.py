from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

class DetailedReport:
    """Generates comprehensive and detailed SEO analysis reports.
    
    Features:
    - Detailed problem explanations
    - Impact assessment
    - Implementation guides
    - Priority scoring
    - Visual representations
    - Educational resources
    """
    
    def __init__(self, analysis_data: Dict):
        self.analysis = analysis_data
        self.timestamp = datetime.now()
        
    def generate_report(self, format: str = 'markdown') -> str:
        """Generate detailed report in specified format."""
        if format == 'markdown':
            return self._generate_markdown_report()
        elif format == 'html':
            return self._generate_html_report()
        elif format == 'json':
            return self._generate_json_report()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_markdown_report(self) -> str:
        """Generate detailed markdown report."""
        sections = [
            self._generate_executive_summary(),
            self._generate_technical_analysis(),
            self._generate_content_analysis(),
            self._generate_user_experience_analysis(),
            self._generate_performance_analysis(),
            self._generate_security_analysis(),
            self._generate_mobile_analysis(),
            self._generate_competitive_analysis(),
            self._generate_action_plan(),
            self._generate_resource_requirements(),
            self._generate_educational_resources()
        ]
        
        return "\n\n".join(sections)

    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        summary = self.analysis.get('summary', {})
        scores = self.analysis.get('scores', {})
        
        return f"""# SEO Analysis Report
Generated on: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

### Overview
- **Overall SEO Score**: {scores.get('overall_score', 0):.1f}/100
- **Total Issues**: {summary.get('overview', {}).get('total_issues', 0)}
- **Critical Issues**: {summary.get('overview', {}).get('critical_issues', 0)}
- **Strongest Category**: {summary.get('overview', {}).get('strongest_category', 'N/A')}
- **Weakest Category**: {summary.get('overview', {}).get('weakest_category', 'N/A')}

### Key Findings
{self._format_list(summary.get('key_findings', []))}

### Impact Assessment
{self._format_impact_assessment(self.analysis.get('insights', {}))}
"""

    def _generate_technical_analysis(self) -> str:
        """Generate technical analysis section."""
        tech_score = self.analysis.get('scores', {}).get('category_scores', {}).get('technical_seo', 0)
        basic_seo = self.analysis.get('analysis_modules', {}).get('basic_seo', {})
        
        return f"""## Technical SEO Analysis
Score: {tech_score:.1f}/100

### Meta Tags Implementation
{self._analyze_meta_tags(basic_seo.get('meta_tags', {}))}

### URL Structure
{self._analyze_url_structure(basic_seo.get('url_analysis', {}))}

### Indexation Status
{self._analyze_indexation(basic_seo.get('indexation', {}))}

### Technical Issues
{self._format_technical_issues(self.analysis.get('insights', {}).get('technical_issues', []))}
"""

    def _generate_content_analysis(self) -> str:
        """Generate content analysis section."""
        content_score = self.analysis.get('scores', {}).get('category_scores', {}).get('content_quality', 0)
        content = self.analysis.get('analysis_modules', {}).get('basic_seo', {}).get('content', {})
        
        return f"""## Content Analysis
Score: {content_score:.1f}/100

### Content Quality Metrics
{self._analyze_content_quality(content)}

### Keyword Analysis
{self._analyze_keyword_usage(content)}

### Content Structure
{self._analyze_content_structure(content)}

### Content Issues and Recommendations
{self._format_content_recommendations(content)}
"""

    def _generate_user_experience_analysis(self) -> str:
        """Generate user experience analysis section."""
        ux_score = self.analysis.get('scores', {}).get('category_scores', {}).get('user_experience', 0)
        ux = self.analysis.get('analysis_modules', {}).get('advanced', {}).get('user_experience', {})
        
        return f"""## User Experience Analysis
Score: {ux_score:.1f}/100

### Navigation Analysis
{self._analyze_navigation(ux.get('navigation', {}))}

### Accessibility Assessment
{self._analyze_accessibility(ux.get('accessibility', {}))}

### Interaction Elements
{self._analyze_interaction_elements(ux.get('interaction', {}))}

### UX Recommendations
{self._format_ux_recommendations(ux)}
"""

    def _generate_performance_analysis(self) -> str:
        """Generate performance analysis section."""
        perf_score = self.analysis.get('scores', {}).get('category_scores', {}).get('performance', 0)
        perf = self.analysis.get('analysis_modules', {}).get('performance', {})
        
        return f"""## Performance Analysis
Score: {perf_score:.1f}/100

### Load Time Analysis
{self._analyze_load_time(perf.get('load_time', {}))}

### Resource Optimization
{self._analyze_resource_optimization(perf.get('resource_optimization', {}))}

### Performance Recommendations
{self._format_performance_recommendations(perf)}

### Impact on User Experience
{self._analyze_performance_impact()}
"""

    def _generate_security_analysis(self) -> str:
        """Generate security analysis section."""
        security_score = self.analysis.get('scores', {}).get('category_scores', {}).get('security', 0)
        security = self.analysis.get('analysis_modules', {}).get('security', {})
        
        return f"""## Security Analysis
Score: {security_score:.1f}/100

### SSL Implementation
{self._analyze_ssl(security.get('ssl_certificate', {}))}

### Security Headers
{self._analyze_security_headers(security.get('security_headers', {}))}

### Content Security
{self._analyze_content_security(security)}

### Security Recommendations
{self._format_security_recommendations(security)}
"""

    def _generate_mobile_analysis(self) -> str:
        """Generate mobile analysis section."""
        mobile_score = self.analysis.get('scores', {}).get('category_scores', {}).get('mobile_optimization', 0)
        mobile = self.analysis.get('analysis_modules', {}).get('mobile', {})
        
        return f"""## Mobile Optimization Analysis
Score: {mobile_score:.1f}/100

### Mobile Friendliness
{self._analyze_mobile_friendliness(mobile)}

### Responsive Design
{self._analyze_responsive_design(mobile)}

### Mobile Performance
{self._analyze_mobile_performance(mobile)}

### Mobile Optimization Recommendations
{self._format_mobile_recommendations(mobile)}
"""

    def _generate_competitive_analysis(self) -> str:
        """Generate competitive analysis section."""
        competitive = self.analysis.get('analysis_modules', {}).get('competitive', {})
        position = self.analysis.get('summary', {}).get('competitive_position', {})
        
        return f"""## Competitive Analysis

### Market Position
**Current Position**: {position.get('overall_status', 'N/A').title()}

### Strengths
{self._format_list(position.get('strengths', []))}

### Areas for Improvement
{self._format_list(position.get('weaknesses', []))}

### Opportunities
{self._format_list(position.get('opportunities', []))}

### Competitive Recommendations
{self._format_competitive_recommendations(competitive)}
"""

    def _generate_action_plan(self) -> str:
        """Generate action plan section."""
        action_plan = self.analysis.get('action_plan', {})
        impact = self.analysis.get('summary', {}).get('estimated_impact', {})
        
        return f"""## Action Plan

### Critical Actions (Immediate)
{self._format_list(action_plan.get('critical_actions', []), with_priority=True)}

### High Priority Actions (Next 30 Days)
{self._format_list(action_plan.get('high_priority', []), with_priority=True)}

### Medium Priority Actions (60-90 Days)
{self._format_list(action_plan.get('medium_priority', []), with_priority=True)}

### Low Priority Actions (90+ Days)
{self._format_list(action_plan.get('low_priority', []), with_priority=True)}

### Expected Impact
- Estimated Traffic Increase: {impact.get('estimated_traffic_increase', 0)}%
- Estimated Conversion Impact: {impact.get('estimated_conversion_impact', 0)}%
- Implementation Timeframe: {impact.get('timeframe', 'N/A')}
"""

    def _generate_resource_requirements(self) -> str:
        """Generate resource requirements section."""
        resources = self.analysis.get('summary', {}).get('resource_requirements', {})
        
        return f"""## Resource Requirements

### Development Resources
- Developer Hours: {resources.get('developer_hours', 0)}
- Technical Complexity: {resources.get('technical_complexity', 'N/A')}

### Content Resources
- Content Creation Hours: {resources.get('content_hours', 0)}
- Content Types Required: {', '.join(resources.get('content_types', []))}

### SEO Resources
- SEO Specialist Hours: {resources.get('seo_hours', 0)}
- Ongoing Monitoring: {resources.get('monitoring_hours', 0)} hours/month
"""

    def _generate_educational_resources(self) -> str:
        """Generate educational resources section."""
        return """## Educational Resources

### SEO Best Practices
- [Google's SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Moz's Beginner's Guide to SEO](https://moz.com/beginners-guide-to-seo)
- [Search Console Help](https://support.google.com/webmasters)

### Technical Implementation Guides
- [Schema.org Implementation](https://schema.org/docs/gs.html)
- [Mobile-First Indexing](https://developers.google.com/search/mobile-sites)
- [Web Vitals](https://web.dev/vitals/)

### Tools and Resources
- [Google Search Console](https://search.google.com/search-console)
- [Google PageSpeed Insights](https://pagespeed.web.dev/)
- [Mobile-Friendly Test](https://search.google.com/test/mobile-friendly)
"""

    def _analyze_meta_tags(self, meta_tags: Dict) -> str:
        """Analyze meta tags implementation."""
        issues = []
        recommendations = []
        
        # Title tag analysis
        title_length = meta_tags.get('title_length', 0)
        if title_length < 30:
            issues.append("Title tag is too short")
            recommendations.append("Increase title length to 30-60 characters for better visibility")
        elif title_length > 60:
            issues.append("Title tag is too long")
            recommendations.append("Reduce title length to 30-60 characters to prevent truncation")
            
        # Meta description analysis
        desc_length = meta_tags.get('meta_description_length', 0)
        if desc_length < 120:
            issues.append("Meta description is too short")
            recommendations.append("Expand meta description to 120-160 characters")
        elif desc_length > 160:
            issues.append("Meta description is too long")
            recommendations.append("Reduce meta description to 120-160 characters")
            
        return f"""#### Current Implementation
- Title Length: {title_length} characters
- Meta Description Length: {desc_length} characters
- Has Canonical: {'Yes' if meta_tags.get('has_canonical') else 'No'}
- Has Robots Meta: {'Yes' if meta_tags.get('has_robots') else 'No'}

#### Issues Identified
{self._format_list(issues)}

#### Recommendations
{self._format_list(recommendations)}

#### Best Practices
- Use unique, descriptive titles for each page
- Include target keywords naturally in meta tags
- Ensure meta description accurately summarizes page content
- Implement proper canonical tags to prevent duplicate content
"""

    def _analyze_content_quality(self, content: Dict) -> str:
        """Analyze content quality metrics."""
        word_count = content.get('word_count', 0)
        readability = content.get('readability_score', 0)
        
        quality_assessment = "Excellent" if word_count >= 1000 and readability >= 60 else \
                           "Good" if word_count >= 500 and readability >= 50 else \
                           "Needs Improvement"
        
        return f"""#### Content Metrics
- Word Count: {word_count}
- Readability Score: {readability}/100
- Overall Quality: {quality_assessment}

#### Content Assessment
{self._assess_content_quality(content)}

#### Quality Factors
{self._analyze_quality_factors(content)}

#### Improvement Opportunities
{self._identify_content_opportunities(content)}
"""

    def _format_list(self, items: List[str], with_priority: bool = False) -> str:
        """Format list items with optional priority."""
        if not items:
            return "No items identified."
            
        if with_priority:
            return "\n".join(f"- **Priority {i+1}**: {item}" for i, item in enumerate(items))
        return "\n".join(f"- {item}" for item in items)

    def _format_impact_assessment(self, insights: Dict) -> str:
        """Format impact assessment details."""
        return f"""#### Potential Impact
- **Traffic Impact**: {insights.get('traffic_impact', 'N/A')}
- **Conversion Impact**: {insights.get('conversion_impact', 'N/A')}
- **Competitive Impact**: {insights.get('competitive_impact', 'N/A')}

#### Implementation Effort
- **Technical Complexity**: {insights.get('technical_complexity', 'N/A')}
- **Resource Requirements**: {insights.get('resource_requirements', 'N/A')}
- **Timeline**: {insights.get('timeline', 'N/A')}
"""

    def _assess_content_quality(self, content: Dict) -> str:
        """Provide detailed content quality assessment."""
        assessment = []
        
        # Assess content length
        word_count = content.get('word_count', 0)
        if word_count < 300:
            assessment.append("Content length is significantly below recommended minimum (300 words)")
        elif word_count < 500:
            assessment.append("Content length meets minimum requirements but could be expanded")
        else:
            assessment.append("Content length is good, providing comprehensive coverage")
            
        # Assess readability
        readability = content.get('readability_score', 0)
        if readability < 50:
            assessment.append("Content may be too complex for general audience")
        elif readability > 80:
            assessment.append("Content is very accessible but might need more depth for technical topics")
            
        return "\n".join(f"- {item}" for item in assessment)

    def _analyze_quality_factors(self, content: Dict) -> str:
        """Analyze content quality factors."""
        factors = [
            f"- Keyword Usage: {self._assess_keyword_usage(content)}",
            f"- Content Structure: {self._assess_content_structure(content)}",
            f"- Media Integration: {self._assess_media_usage(content)}",
            f"- Internal Linking: {self._assess_internal_linking(content)}"
        ]
        return "\n".join(factors)

    def _identify_content_opportunities(self, content: Dict) -> str:
        """Identify content improvement opportunities."""
        opportunities = []
        
        # Check content length
        if content.get('word_count', 0) < 1000:
            opportunities.append("Expand content depth to provide more comprehensive coverage")
            
        # Check media usage
        if not content.get('has_images', False):
            opportunities.append("Add relevant images to improve engagement")
            
        # Check heading structure
        if not content.get('has_proper_hierarchy', False):
            opportunities.append("Improve content structure with proper heading hierarchy")
            
        return self._format_list(opportunities)

    def _assess_keyword_usage(self, content: Dict) -> str:
        """Assess keyword usage in content."""
        keyword_density = content.get('keyword_density', 0)
        return f"{'Optimal' if 0.5 <= keyword_density <= 2.5 else 'Needs optimization'} ({keyword_density:.1f}%)"

    def _assess_content_structure(self, content: Dict) -> str:
        """Assess content structure."""
        has_structure = content.get('has_proper_hierarchy', False)
        return "Well-structured" if has_structure else "Needs improvement"

    def _assess_media_usage(self, content: Dict) -> str:
        """Assess media usage in content."""
        has_media = content.get('has_images', False) or content.get('has_videos', False)
        return "Good integration" if has_media else "Could be improved"

    def _assess_internal_linking(self, content: Dict) -> str:
        """Assess internal linking."""
        internal_links = content.get('internal_links_count', 0)
        return "Good" if internal_links >= 3 else "Could be improved" 