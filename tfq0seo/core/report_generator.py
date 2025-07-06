"""
Enhanced Report Generator for tfq0seo

This module transforms analysis results into actionable improvement plans
with prioritized recommendations, timelines, and expected outcomes.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from collections import defaultdict
from .recommendations import RecommendationEngine
from .data_quality import DataQualityScorer
from .issue_helper import IssueHelper


logger = logging.getLogger(__name__)


class EnhancedReportGenerator:
    """Generate enhanced reports with actionable improvement plans"""
    
    def __init__(self):
        self.recommendation_engine = RecommendationEngine()
        self.quality_scorer = DataQualityScorer()
        
        # Impact scoring weights
        self.impact_weights = {
            'user_experience': 0.25,
            'search_visibility': 0.35,
            'conversion_potential': 0.20,
            'technical_health': 0.20
        }
        
        # Effort estimation rules
        self.effort_estimates = {
            'easy': {'hours': 0.5, 'skill': 'beginner'},
            'medium': {'hours': 2, 'skill': 'intermediate'},
            'hard': {'hours': 8, 'skill': 'advanced'}
        }
    
    def generate_action_plan(self, analysis_results: Dict) -> Dict:
        """Generate prioritized action plan from analysis results"""
        
        # Extract all issues from analysis
        all_issues = self._extract_all_issues(analysis_results)
        
        # Enhance issues with context and confidence
        enhanced_issues = []
        for issue in all_issues:
            # Add confidence scoring
            confidence = self.quality_scorer.calculate_recommendation_confidence(
                issue, 
                analysis_results
            )
            issue['confidence'] = confidence
            
            # Add contextual recommendations
            contextual = self.recommendation_engine.generate_contextual_recommendation(
                issue,
                analysis_results
            )
            issue.update(contextual)
            
            # Calculate impact score
            issue['impact_score'] = self._calculate_impact_score(issue)
            
            # Calculate effort score
            issue['effort_score'] = self._calculate_effort_score(issue)
            
            enhanced_issues.append(issue)
        
        # Group issues by implementation effort and impact
        action_groups = self._group_by_effort_impact(enhanced_issues)
        
        # Generate implementation timeline
        timeline = self._generate_implementation_timeline(action_groups)
        
        # Calculate expected results
        expected_results = self._project_improvements(action_groups)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            analysis_results, 
            action_groups,
            expected_results
        )
        
        return {
            'executive_summary': executive_summary,
            'action_plan': action_groups,
            'detailed_recommendations': enhanced_issues,
            'implementation_timeline': timeline,
            'expected_results': expected_results,
            'resources_needed': self._estimate_resources(action_groups),
            'success_metrics': self._define_success_metrics(action_groups),
            'follow_up_actions': self._suggest_follow_up_actions(analysis_results)
        }
    
    def _extract_all_issues(self, analysis_results: Dict) -> List[Dict]:
        """Extract all issues from various analyzers"""
        
        all_issues = []
        
        # Handle single page vs multi-page analysis
        if 'pages' in analysis_results:
            # Multi-page crawl
            for page in analysis_results.get('pages', []):
                page_issues = self._extract_page_issues(page)
                for issue in page_issues:
                    issue['page_url'] = page.get('url', '')
                all_issues.extend(page_issues)
        else:
            # Single page analysis
            all_issues = self._extract_page_issues(analysis_results)
        
        # Deduplicate and aggregate similar issues
        aggregated_issues = self._aggregate_similar_issues(all_issues)
        
        return aggregated_issues
    
    def _extract_page_issues(self, page_data: Dict) -> List[Dict]:
        """Extract issues from a single page analysis"""
        
        issues = []
        
        # Direct issues array
        if 'issues' in page_data:
            issues.extend(page_data['issues'])
        
        # Extract from analyzer sections
        for section in ['meta_tags', 'content', 'technical', 'performance', 'links']:
            if section in page_data and isinstance(page_data[section], dict):
                if 'issues' in page_data[section]:
                    section_issues = page_data[section]['issues']
                    # Add source information
                    for issue in section_issues:
                        issue['source'] = section
                    issues.extend(section_issues)
        
        return issues
    
    def _aggregate_similar_issues(self, issues: List[Dict]) -> List[Dict]:
        """Aggregate similar issues across multiple pages"""
        
        issue_groups = defaultdict(list)
        
        # Group by issue type
        for issue in issues:
            key = issue.get('type', 'unknown')
            issue_groups[key].append(issue)
        
        aggregated = []
        
        for issue_type, group in issue_groups.items():
            if len(group) == 1:
                # Single instance
                aggregated.append(group[0])
            else:
                # Multiple instances - aggregate
                aggregated_issue = group[0].copy()
                aggregated_issue['occurrences'] = len(group)
                aggregated_issue['affected_pages'] = list(set(
                    issue.get('page_url', '') for issue in group if issue.get('page_url')
                ))
                
                # Aggregate confidence scores
                confidence_scores = [
                    issue.get('confidence', {}).get('score', 0.5) 
                    for issue in group
                ]
                aggregated_issue['aggregate_confidence'] = sum(confidence_scores) / len(confidence_scores)
                
                aggregated.append(aggregated_issue)
        
        return aggregated
    
    def _calculate_impact_score(self, issue: Dict) -> float:
        """Calculate the potential impact of fixing an issue"""
        
        base_impact = {
            'high': 0.9,
            'medium': 0.6,
            'low': 0.3
        }
        
        # Start with estimated impact
        score = base_impact.get(issue.get('estimated_impact', 'medium'), 0.5)
        
        # Adjust based on issue type
        critical_issues = ['missing_title', 'missing_description', 'no_https', 'missing_h1']
        if issue.get('type') in critical_issues:
            score += 0.2
        
        # Adjust based on occurrences
        occurrences = issue.get('occurrences', 1)
        if occurrences > 10:
            score += 0.15
        elif occurrences > 5:
            score += 0.1
        elif occurrences > 1:
            score += 0.05
        
        # Adjust based on confidence
        confidence = issue.get('confidence', {}).get('score', 0.5)
        score *= (0.8 + 0.2 * confidence)  # 80-100% of score based on confidence
        
        return min(1.0, score)
    
    def _calculate_effort_score(self, issue: Dict) -> float:
        """Calculate the effort required to fix an issue"""
        
        difficulty_scores = {
            'easy': 0.2,
            'medium': 0.5,
            'hard': 0.8
        }
        
        # Base effort on difficulty
        difficulty = issue.get('implementation_difficulty', 'medium')
        score = difficulty_scores.get(difficulty, 0.5)
        
        # Adjust based on occurrences
        occurrences = issue.get('occurrences', 1)
        if occurrences > 10:
            score += 0.2  # More effort for widespread issues
        elif occurrences > 5:
            score += 0.1
        
        # Adjust based on estimated time
        estimated_time = issue.get('estimated_time', '1 hour')
        if 'day' in estimated_time:
            score += 0.2
        elif 'hours' in estimated_time:
            try:
                hours = int(estimated_time.split()[0])
                if hours > 4:
                    score += 0.1
            except:
                pass
        
        return min(1.0, score)
    
    def _group_by_effort_impact(self, issues: List[Dict]) -> Dict:
        """Group issues by effort and impact quadrants"""
        
        groups = {
            'quick_wins': [],      # High impact, low effort
            'major_projects': [],  # High impact, high effort
            'fill_ins': [],        # Low impact, low effort
            'questionable': []     # Low impact, high effort
        }
        
        for issue in issues:
            impact = issue.get('impact_score', 0.5)
            effort = issue.get('effort_score', 0.5)
            
            if impact >= 0.6 and effort <= 0.4:
                groups['quick_wins'].append(issue)
            elif impact >= 0.6 and effort > 0.4:
                groups['major_projects'].append(issue)
            elif impact < 0.6 and effort <= 0.4:
                groups['fill_ins'].append(issue)
            else:
                groups['questionable'].append(issue)
        
        # Sort each group by priority
        for group_name, group_issues in groups.items():
            if group_name == 'quick_wins':
                # Sort by impact (highest first)
                group_issues.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
            elif group_name == 'major_projects':
                # Sort by impact/effort ratio
                group_issues.sort(
                    key=lambda x: x.get('impact_score', 0) / max(0.1, x.get('effort_score', 1)), 
                    reverse=True
                )
            else:
                # Sort by priority score
                group_issues.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        return groups
    
    def _generate_implementation_timeline(self, action_groups: Dict) -> Dict:
        """Generate a realistic implementation timeline"""
        
        timeline = {
            'immediate': {
                'timeframe': 'Next 7 days',
                'focus': 'Critical issues and quick wins',
                'tasks': [],
                'estimated_hours': 0,
                'expected_impact': 'Address critical SEO issues, improve user experience'
            },
            'short_term': {
                'timeframe': 'Next 30 days',
                'focus': 'High-impact improvements',
                'tasks': [],
                'estimated_hours': 0,
                'expected_impact': 'Noticeable improvement in search visibility'
            },
            'medium_term': {
                'timeframe': 'Next 90 days',
                'focus': 'Major projects and optimizations',
                'tasks': [],
                'estimated_hours': 0,
                'expected_impact': 'Significant SEO improvements, competitive positioning'
            },
            'long_term': {
                'timeframe': 'Ongoing',
                'focus': 'Continuous optimization',
                'tasks': [],
                'estimated_hours': 0,
                'expected_impact': 'Maintain and improve search rankings'
            }
        }
        
        # Assign tasks to timeline phases
        # Immediate: Critical issues and top quick wins
        critical_issues = [
            issue for issue in action_groups.get('quick_wins', [])
            if issue.get('severity') == 'critical'
        ]
        timeline['immediate']['tasks'] = critical_issues[:5]
        
        # Short term: Remaining quick wins
        remaining_quick_wins = [
            issue for issue in action_groups.get('quick_wins', [])
            if issue not in critical_issues
        ]
        timeline['short_term']['tasks'] = remaining_quick_wins[:10]
        
        # Medium term: Major projects
        timeline['medium_term']['tasks'] = action_groups.get('major_projects', [])[:5]
        
        # Long term: Fill-ins and ongoing optimization
        timeline['long_term']['tasks'] = action_groups.get('fill_ins', [])[:10]
        
        # Calculate estimated hours for each phase
        for phase, data in timeline.items():
            total_hours = 0
            for task in data['tasks']:
                difficulty = task.get('implementation_difficulty', 'medium')
                hours = self.effort_estimates.get(difficulty, {}).get('hours', 2)
                occurrences = task.get('occurrences', 1)
                total_hours += hours * min(occurrences, 10)  # Cap at 10 occurrences
            
            data['estimated_hours'] = round(total_hours, 1)
        
        return timeline
    
    def _project_improvements(self, action_groups: Dict) -> Dict:
        """Project expected improvements from implementing recommendations"""
        
        # Count issues by severity
        severity_counts = defaultdict(int)
        impact_sum = 0
        
        for group_issues in action_groups.values():
            for issue in group_issues:
                severity_counts[issue.get('severity', 'notice')] += 1
                impact_sum += issue.get('impact_score', 0.5)
        
        total_issues = sum(severity_counts.values())
        avg_impact = impact_sum / total_issues if total_issues > 0 else 0
        
        # Project improvements
        improvements = {
            'seo_score_improvement': self._estimate_score_improvement(severity_counts, avg_impact),
            'traffic_potential': self._estimate_traffic_improvement(action_groups),
            'user_experience_gains': self._estimate_ux_improvement(action_groups),
            'technical_health': self._estimate_technical_improvement(action_groups),
            'timeline_to_results': self._estimate_timeline_to_results(action_groups)
        }
        
        return improvements
    
    def _estimate_score_improvement(self, severity_counts: Dict, avg_impact: float) -> Dict:
        """Estimate SEO score improvement"""
        
        # Base improvement on fixing issues
        base_improvement = (
            severity_counts.get('critical', 0) * 5 +
            severity_counts.get('warning', 0) * 2 +
            severity_counts.get('notice', 0) * 0.5
        )
        
        # Adjust by average impact
        adjusted_improvement = base_improvement * (0.5 + avg_impact * 0.5)
        
        return {
            'estimated_points': round(min(adjusted_improvement, 40), 1),
            'confidence': 'high' if avg_impact > 0.7 else 'medium',
            'timeframe': '30-60 days after implementation'
        }
    
    def _estimate_traffic_improvement(self, action_groups: Dict) -> Dict:
        """Estimate potential traffic improvement"""
        
        # Check for high-impact SEO fixes
        high_impact_fixes = 0
        for issue in action_groups.get('quick_wins', []) + action_groups.get('major_projects', []):
            if issue.get('type') in ['missing_title', 'missing_description', 'missing_h1', 'thin_content']:
                high_impact_fixes += 1
        
        if high_impact_fixes >= 5:
            return {
                'range': '20-50%',
                'confidence': 'medium',
                'factors': ['Multiple critical SEO issues will be fixed', 'Content improvements will increase relevance']
            }
        elif high_impact_fixes >= 2:
            return {
                'range': '10-20%',
                'confidence': 'medium',
                'factors': ['Key SEO elements will be optimized', 'Better search visibility expected']
            }
        else:
            return {
                'range': '5-10%',
                'confidence': 'low',
                'factors': ['Incremental improvements across various factors']
            }
    
    def _estimate_ux_improvement(self, action_groups: Dict) -> List[str]:
        """Estimate user experience improvements"""
        
        improvements = []
        
        # Check for specific UX-related fixes
        for issue in action_groups.get('quick_wins', []) + action_groups.get('major_projects', []):
            issue_type = issue.get('type', '')
            
            if issue_type == 'slow_page':
                improvements.append('Faster page load times')
            elif issue_type == 'missing_viewport':
                improvements.append('Better mobile experience')
            elif issue_type == 'broken_internal_links':
                improvements.append('Improved navigation')
            elif issue_type == 'missing_alt_text':
                improvements.append('Better accessibility')
            elif issue_type == 'poor_readability':
                improvements.append('Easier to read content')
        
        return list(set(improvements))[:5]  # Top 5 unique improvements
    
    def _estimate_technical_improvement(self, action_groups: Dict) -> Dict:
        """Estimate technical health improvements"""
        
        technical_fixes = 0
        for issue in action_groups.get('quick_wins', []) + action_groups.get('major_projects', []):
            if issue.get('source') == 'technical' or issue.get('type') in ['no_https', 'invalid_html', 'missing_viewport']:
                technical_fixes += 1
        
        if technical_fixes >= 5:
            health_score = 'Excellent'
        elif technical_fixes >= 3:
            health_score = 'Good'
        elif technical_fixes >= 1:
            health_score = 'Fair'
        else:
            health_score = 'Minimal change'
        
        return {
            'expected_health': health_score,
            'fixes_planned': technical_fixes,
            'key_improvements': self._get_key_technical_improvements(action_groups)
        }
    
    def _get_key_technical_improvements(self, action_groups: Dict) -> List[str]:
        """Get key technical improvements from action groups"""
        
        improvements = []
        improvement_map = {
            'no_https': 'Secure HTTPS implementation',
            'missing_viewport': 'Mobile responsiveness',
            'slow_page': 'Performance optimization',
            'invalid_html': 'Valid HTML structure',
            'missing_structured_data': 'Rich snippets support'
        }
        
        for issue in action_groups.get('quick_wins', []) + action_groups.get('major_projects', []):
            issue_type = issue.get('type', '')
            if issue_type in improvement_map:
                improvements.append(improvement_map[issue_type])
        
        return list(set(improvements))[:5]
    
    def _estimate_timeline_to_results(self, action_groups: Dict) -> Dict:
        """Estimate when results will be visible"""
        
        return {
            'immediate_improvements': '1-7 days (user experience, technical fixes)',
            'search_visibility': '2-4 weeks (search engines need time to recrawl)',
            'ranking_improvements': '1-3 months (competitive keywords take time)',
            'full_impact': '3-6 months (cumulative effect of all improvements)'
        }
    
    def _generate_executive_summary(self, analysis_results: Dict, action_groups: Dict, expected_results: Dict) -> Dict:
        """Generate executive summary of findings and recommendations"""
        
        # Count issues by severity
        total_issues = sum(len(issues) for issues in action_groups.values())
        critical_count = sum(
            1 for issues in action_groups.values() 
            for issue in issues 
            if issue.get('severity') == 'critical'
        )
        
        # Calculate overall health score
        if 'score' in analysis_results:
            current_score = analysis_results['score']
        else:
            # Calculate from issues
            current_score = max(0, 100 - (critical_count * 10 + total_issues * 2))
        
        projected_score = min(100, current_score + expected_results['seo_score_improvement']['estimated_points'])
        
        return {
            'current_state': {
                'seo_score': current_score,
                'total_issues': total_issues,
                'critical_issues': critical_count,
                'main_concerns': self._identify_main_concerns(action_groups)
            },
            'projected_state': {
                'seo_score': projected_score,
                'traffic_increase': expected_results['traffic_potential']['range'],
                'key_improvements': expected_results['user_experience_gains']
            },
            'investment_required': {
                'total_hours': sum(
                    phase['estimated_hours'] 
                    for phase in self._generate_implementation_timeline(action_groups).values()
                ),
                'skill_level': self._determine_required_skill_level(action_groups),
                'tools_needed': self._identify_required_tools(action_groups)
            },
            'roi_summary': self._calculate_roi_summary(action_groups, expected_results),
            'next_steps': self._generate_next_steps(action_groups)
        }
    
    def _identify_main_concerns(self, action_groups: Dict) -> List[str]:
        """Identify the main concerns from issues"""
        
        concerns = []
        concern_map = {
            'missing_title': 'Missing page titles affecting search visibility',
            'missing_description': 'No meta descriptions to attract clicks',
            'thin_content': 'Insufficient content for good rankings',
            'slow_page': 'Poor page performance affecting user experience',
            'no_https': 'Security issues with missing HTTPS',
            'missing_h1': 'Poor content structure without H1 tags'
        }
        
        # Check quick wins and major projects for concerns
        for issue in action_groups.get('quick_wins', [])[:5] + action_groups.get('major_projects', [])[:5]:
            issue_type = issue.get('type', '')
            if issue_type in concern_map:
                concerns.append(concern_map[issue_type])
        
        return concerns[:3]  # Top 3 concerns
    
    def _determine_required_skill_level(self, action_groups: Dict) -> str:
        """Determine the required skill level for implementations"""
        
        all_difficulties = []
        for issues in action_groups.values():
            for issue in issues:
                all_difficulties.append(issue.get('implementation_difficulty', 'medium'))
        
        if 'hard' in all_difficulties:
            return 'Advanced (may need developer assistance)'
        elif 'medium' in all_difficulties:
            return 'Intermediate (some technical knowledge required)'
        else:
            return 'Beginner (can be done through CMS/admin panels)'
    
    def _identify_required_tools(self, action_groups: Dict) -> List[str]:
        """Identify tools needed for implementation"""
        
        tools = set()
        
        for issues in action_groups.values():
            for issue in issues:
                issue_tools = issue.get('tools', [])
                if isinstance(issue_tools, list):
                    tools.update(issue_tools)
        
        # Add common tools based on issue types
        issue_types = {issue.get('type') for issues in action_groups.values() for issue in issues}
        
        if any(t in issue_types for t in ['slow_page', 'large_images']):
            tools.add('Image optimization tools')
        
        if any(t in issue_types for t in ['poor_readability', 'thin_content']):
            tools.add('Content editing tools')
        
        return list(tools)[:5]
    
    def _calculate_roi_summary(self, action_groups: Dict, expected_results: Dict) -> Dict:
        """Calculate ROI summary"""
        
        total_hours = sum(
            self.effort_estimates.get(issue.get('implementation_difficulty', 'medium'), {}).get('hours', 2)
            for issues in action_groups.values()
            for issue in issues
        )
        
        return {
            'effort_hours': round(total_hours, 1),
            'expected_traffic_gain': expected_results['traffic_potential']['range'],
            'payback_period': '2-4 months',
            'long_term_value': 'High - improvements compound over time'
        }
    
    def _generate_next_steps(self, action_groups: Dict) -> List[str]:
        """Generate immediate next steps"""
        
        next_steps = []
        
        # Always start with critical issues
        critical_issues = [
            issue for issues in action_groups.values() 
            for issue in issues 
            if issue.get('severity') == 'critical'
        ]
        
        if critical_issues:
            next_steps.append(f"Fix {len(critical_issues)} critical issues immediately")
        
        # Add quick wins
        if action_groups.get('quick_wins'):
            next_steps.append(f"Implement {min(5, len(action_groups['quick_wins']))} quick wins this week")
        
        # Add planning step for major projects
        if action_groups.get('major_projects'):
            next_steps.append("Plan resources for major improvement projects")
        
        # Always include monitoring
        next_steps.append("Set up monitoring to track improvement progress")
        
        return next_steps[:4]
    
    def _estimate_resources(self, action_groups: Dict) -> Dict:
        """Estimate resources needed for implementation"""
        
        resources = {
            'time': {
                'quick_wins': 0,
                'major_projects': 0,
                'total': 0
            },
            'team': [],
            'budget_considerations': [],
            'external_help_needed': []
        }
        
        # Calculate time for each group
        for group_name, issues in action_groups.items():
            if group_name in ['quick_wins', 'major_projects']:
                group_hours = sum(
                    self.effort_estimates.get(
                        issue.get('implementation_difficulty', 'medium'), 
                        {}
                    ).get('hours', 2)
                    for issue in issues
                )
                resources['time'][group_name] = round(group_hours, 1)
        
        resources['time']['total'] = round(
            resources['time']['quick_wins'] + resources['time']['major_projects'], 
            1
        )
        
        # Determine team needs
        skills_needed = set()
        for issues in action_groups.values():
            for issue in issues:
                difficulty = issue.get('implementation_difficulty', 'medium')
                if difficulty == 'hard':
                    skills_needed.add('developer')
                elif difficulty == 'medium':
                    skills_needed.add('webmaster')
                
                # Check specific issue types
                if issue.get('type') in ['thin_content', 'poor_readability']:
                    skills_needed.add('content writer')
                elif issue.get('type') in ['slow_page', 'large_images']:
                    skills_needed.add('web developer')
        
        resources['team'] = list(skills_needed)
        
        # Budget considerations
        if 'developer' in skills_needed:
            resources['budget_considerations'].append('May need developer hours ($50-150/hour)')
        
        if 'content writer' in skills_needed:
            resources['budget_considerations'].append('Content creation costs ($0.10-0.50/word)')
        
        # External help
        if resources['time']['total'] > 40:
            resources['external_help_needed'].append('Consider hiring SEO consultant')
        
        if any(issue.get('type') == 'no_https' for issues in action_groups.values() for issue in issues):
            resources['external_help_needed'].append('SSL certificate installation')
        
        return resources
    
    def _define_success_metrics(self, action_groups: Dict) -> Dict:
        """Define success metrics for the implementation"""
        
        metrics = {
            'primary_kpis': [],
            'secondary_kpis': [],
            'monitoring_schedule': {
                'weekly': [],
                'monthly': [],
                'quarterly': []
            },
            'tools_for_tracking': []
        }
        
        # Define KPIs based on issues being fixed
        issue_types = {issue.get('type') for issues in action_groups.values() for issue in issues}
        
        # Primary KPIs
        metrics['primary_kpis'] = [
            'Organic search traffic',
            'Average search position',
            'Click-through rate from search'
        ]
        
        # Secondary KPIs based on fixes
        if any(t in issue_types for t in ['slow_page', 'large_images']):
            metrics['secondary_kpis'].append('Page load time')
            metrics['secondary_kpis'].append('Core Web Vitals scores')
        
        if any(t in issue_types for t in ['thin_content', 'missing_h1']):
            metrics['secondary_kpis'].append('Average time on page')
            metrics['secondary_kpis'].append('Bounce rate')
        
        if 'broken_internal_links' in issue_types:
            metrics['secondary_kpis'].append('404 error rate')
        
        # Monitoring schedule
        metrics['monitoring_schedule']['weekly'] = [
            'Check Google Search Console for errors',
            'Monitor page load times',
            'Review organic traffic trends'
        ]
        
        metrics['monitoring_schedule']['monthly'] = [
            'Analyze ranking changes',
            'Review user engagement metrics',
            'Check technical SEO health'
        ]
        
        metrics['monitoring_schedule']['quarterly'] = [
            'Comprehensive SEO audit',
            'Competitor analysis',
            'ROI assessment'
        ]
        
        # Tracking tools
        metrics['tools_for_tracking'] = [
            'Google Analytics',
            'Google Search Console',
            'PageSpeed Insights',
            'SEO monitoring tool (Ahrefs, SEMrush, etc.)'
        ]
        
        return metrics
    
    def _suggest_follow_up_actions(self, analysis_results: Dict) -> List[Dict]:
        """Suggest follow-up actions after initial implementation"""
        
        follow_ups = []
        
        # Always include re-analysis
        follow_ups.append({
            'action': 'Re-run SEO analysis',
            'timing': '30 days after implementation',
            'purpose': 'Measure improvement and identify remaining issues'
        })
        
        # Content expansion
        if any('thin_content' in str(analysis_results)):
            follow_ups.append({
                'action': 'Develop content strategy',
                'timing': 'After fixing technical issues',
                'purpose': 'Build authority with comprehensive content'
            })
        
        # Link building
        follow_ups.append({
            'action': 'Start link building campaign',
            'timing': 'After on-page optimization',
            'purpose': 'Improve domain authority and rankings'
        })
        
        # Advanced optimizations
        follow_ups.append({
            'action': 'Implement advanced SEO tactics',
            'timing': '3-6 months',
            'purpose': 'Schema markup, featured snippets optimization, etc.'
        })
        
        return follow_ups 