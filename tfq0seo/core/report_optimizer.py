"""Report optimization utilities for aggregating and enhancing report data."""

from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
import hashlib


def aggregate_issues(issues: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Aggregate duplicate issues across multiple pages.
    
    Returns:
        - Aggregated unique issues with occurrence counts
        - Statistics about the aggregation
    """
    # Create issue signatures for deduplication
    issue_map = defaultdict(lambda: {'count': 0, 'pages': [], 'first_seen': None})
    
    for issue in issues:
        # Create a unique signature for each issue type
        signature = f"{issue.get('severity')}:{issue.get('category')}:{issue.get('message')}"
        
        issue_map[signature]['count'] += 1
        issue_map[signature]['severity'] = issue.get('severity')
        issue_map[signature]['category'] = issue.get('category')
        issue_map[signature]['message'] = issue.get('message')
        
        # Track which pages have this issue
        if 'url' in issue:
            issue_map[signature]['pages'].append(issue['url'])
        
        if not issue_map[signature]['first_seen']:
            issue_map[signature]['first_seen'] = issue
            if 'details' in issue:
                issue_map[signature]['details'] = issue['details']
    
    # Convert to list of aggregated issues
    aggregated = []
    for signature, data in issue_map.items():
        aggregated_issue = {
            'severity': data['severity'],
            'category': data['category'],
            'message': data['message'],
            'count': data['count'],
            'pages_affected': len(set(data['pages'])),
            'example_pages': list(set(data['pages'][:5])),  # First 5 unique pages
        }
        if 'details' in data:
            aggregated_issue['details'] = data['details']
        aggregated.append(aggregated_issue)
    
    # Sort by severity and count
    severity_order = {'critical': 0, 'warning': 1, 'notice': 2}
    aggregated.sort(key=lambda x: (severity_order.get(x['severity'], 3), -x['count']))
    
    # Calculate statistics
    stats = {
        'total_issues': len(issues),
        'unique_issues': len(aggregated),
        'reduction_ratio': 1 - (len(aggregated) / len(issues)) if issues else 0,
        'most_common': aggregated[0] if aggregated else None,
        'pages_with_issues': len(set(issue.get('url', '') for issue in issues if 'url' in issue))
    }
    
    return aggregated, stats


def generate_specific_recommendations(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate specific, actionable recommendations based on the analysis."""
    recommendations = []
    
    # Analyze aggregated issues
    if 'aggregated_issues' in report:
        issues = report['aggregated_issues']
    else:
        issues = report.get('issues', [])
    
    # Priority 1: Critical SEO issues
    critical_seo = [i for i in issues if i.get('severity') == 'critical' and i.get('category') == 'SEO']
    
    for issue in critical_seo[:3]:
        if 'Missing page title' in issue.get('message', ''):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'SEO',
                'title': 'Add Page Titles',
                'description': f"Add unique, descriptive title tags to {issue.get('count', 'multiple')} pages",
                'implementation': """
                    <title>Your Page Title - Brand Name</title>
                    - Keep titles between 50-60 characters
                    - Include primary keywords naturally
                    - Make each page title unique
                    - Place important keywords near the beginning
                """.strip(),
                'impact': 'Critical for search rankings and click-through rates',
                'effort': 'Low',
                'affected_pages': issue.get('count', 0)
            })
        
        elif 'Missing meta description' in issue.get('message', ''):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'SEO',
                'title': 'Add Meta Descriptions',
                'description': f"Write compelling meta descriptions for {issue.get('count', 'multiple')} pages",
                'implementation': """
                    <meta name="description" content="Your description here">
                    - Keep between 150-160 characters
                    - Include a call-to-action
                    - Use active voice
                    - Include target keywords naturally
                """.strip(),
                'impact': 'Improves click-through rates from search results',
                'effort': 'Medium',
                'affected_pages': issue.get('count', 0)
            })
        
        elif 'Missing H1' in issue.get('message', ''):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Content',
                'title': 'Add H1 Headings',
                'description': f"Add single, descriptive H1 tags to {issue.get('count', 'multiple')} pages",
                'implementation': """
                    <h1>Main Page Heading</h1>
                    - Use only one H1 per page
                    - Include primary keyword
                    - Make it descriptive and unique
                    - Keep it under 70 characters
                """.strip(),
                'impact': 'Essential for content hierarchy and SEO',
                'effort': 'Low',
                'affected_pages': issue.get('count', 0)
            })
    
    # Priority 2: Mobile and Technical issues
    technical_issues = [i for i in issues if i.get('category') == 'Technical']
    
    for issue in technical_issues[:2]:
        if 'viewport' in issue.get('message', '').lower():
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Technical',
                'title': 'Make Site Mobile-Friendly',
                'description': f"Add viewport meta tag to {issue.get('count', 'all')} pages",
                'implementation': """
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    - Add to the <head> section of all pages
                    - Essential for mobile responsiveness
                    - Required for mobile-first indexing
                """.strip(),
                'impact': 'Critical for mobile users and Google rankings',
                'effort': 'Low',
                'affected_pages': issue.get('count', 0)
            })
        
        elif 'HTTPS' in issue.get('message', ''):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Technical',
                'title': 'Enable HTTPS',
                'description': 'Secure your website with SSL certificate',
                'implementation': """
                    1. Obtain SSL certificate (Let's Encrypt for free)
                    2. Install certificate on server
                    3. Update all internal links to HTTPS
                    4. Set up 301 redirects from HTTP to HTTPS
                    5. Update sitemap and robots.txt
                """.strip(),
                'impact': 'Required for security and SEO rankings',
                'effort': 'Medium',
                'affected_pages': issue.get('count', 0)
            })
    
    # Priority 3: Performance issues
    if 'performance' in report:
        perf_data = report['performance']
        if perf_data.get('average_load_time', 0) > 3:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Performance',
                'title': 'Improve Page Load Speed',
                'description': f"Average load time is {perf_data.get('average_load_time', 0):.1f}s (target <3s)",
                'implementation': """
                    1. Enable gzip compression
                    2. Optimize and compress images
                    3. Minify CSS and JavaScript
                    4. Enable browser caching
                    5. Use a Content Delivery Network (CDN)
                    6. Implement lazy loading for images
                """.strip(),
                'impact': 'Improves user experience and SEO rankings',
                'effort': 'High',
                'affected_pages': report.get('summary', {}).get('total_pages', 0)
            })
    
    # Priority 4: Structured Data
    structured_data_missing = [i for i in issues if 'structured data' in i.get('message', '').lower()]
    if structured_data_missing:
        issue = structured_data_missing[0]
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'SEO',
            'title': 'Implement Structured Data',
            'description': f"Add JSON-LD structured data to {issue.get('count', 'multiple')} pages",
            'implementation': """
                <script type="application/ld+json">
                {
                  "@context": "https://schema.org",
                  "@type": "WebPage",
                  "name": "Page Title",
                  "description": "Page description",
                  "url": "https://yoursite.com/page"
                }
                </script>
                - Add appropriate schema types (Article, Product, etc.)
                - Validate with Google's Rich Results Test
            """.strip(),
            'impact': 'Enables rich snippets in search results',
            'effort': 'Medium',
            'affected_pages': issue.get('count', 0)
        })
    
    # Priority 5: Content improvements
    content_issues = [i for i in issues if i.get('category') == 'Content']
    word_count_issues = [i for i in content_issues if 'word count' in i.get('message', '').lower()]
    
    if word_count_issues:
        issue = word_count_issues[0]
        recommendations.append({
            'priority': 'LOW',
            'category': 'Content',
            'title': 'Expand Thin Content',
            'description': f"Increase content length on {issue.get('count', 'multiple')} pages",
            'implementation': """
                - Target minimum 300 words per page
                - Add valuable, relevant information
                - Include related keywords naturally
                - Break content into scannable sections
                - Add supporting images and media
            """.strip(),
            'impact': 'Improves content quality and rankings',
            'effort': 'High',
            'affected_pages': issue.get('count', 0)
        })
    
    # Sort by priority
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'LOW'), 3))
    
    return recommendations[:10]  # Return top 10 recommendations


def create_executive_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    """Create an executive summary for the report."""
    summary = {
        'overview': {},
        'key_metrics': {},
        'top_issues': [],
        'quick_wins': [],
        'action_items': []
    }
    
    # Overview
    summary['overview'] = {
        'total_pages_analyzed': report.get('summary', {}).get('total_pages', 0),
        'successful_pages': report.get('summary', {}).get('successful_pages', 0),
        'failed_pages': report.get('summary', {}).get('failed_pages', 0),
        'overall_health': 'Good' if report.get('overall_score', 0) >= 80 else 
                         'Average' if report.get('overall_score', 0) >= 60 else 'Poor',
        'overall_score': report.get('overall_score', 0)
    }
    
    # Key metrics
    summary['key_metrics'] = {
        'seo_score': report.get('category_scores', {}).get('seo', 0),
        'content_score': report.get('category_scores', {}).get('content', 0),
        'technical_score': report.get('category_scores', {}).get('technical', 0),
        'performance_score': report.get('category_scores', {}).get('performance', 0),
        'links_score': report.get('category_scores', {}).get('links', 0),
        'critical_issues': report.get('issue_counts', {}).get('critical', 0),
        'total_issues': report.get('issue_counts', {}).get('total', 0)
    }
    
    # Top issues (from aggregated data)
    if 'aggregated_issues' in report:
        summary['top_issues'] = report['aggregated_issues'][:5]
    elif 'top_issues' in report:
        summary['top_issues'] = report['top_issues'][:5]
    
    # Quick wins (low effort, high impact)
    if 'enhanced_recommendations' in report:
        quick_wins = [r for r in report['enhanced_recommendations'] 
                     if r.get('effort') == 'Low' and r.get('priority') == 'HIGH']
        summary['quick_wins'] = quick_wins[:3]
    
    # Action items
    summary['action_items'] = [
        'Fix all critical issues immediately',
        'Implement mobile-friendly design',
        'Add missing SEO elements (titles, descriptions, H1s)',
        'Improve page load speed',
        'Add structured data markup'
    ]
    
    return summary


def generate_performance_metrics(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate detailed performance metrics from page data."""
    metrics = {
        'load_times': [],
        'resource_counts': [],
        'status_codes': Counter(),
        'content_sizes': [],
        'issues_per_page': [],
        'scores_per_page': []
    }
    
    for page in pages:
        if 'error' not in page:
            # Load times
            if 'load_time' in page:
                metrics['load_times'].append({
                    'url': page.get('url', ''),
                    'time': page.get('load_time', 0)
                })
            
            # Status codes
            metrics['status_codes'][page.get('status_code', 0)] += 1
            
            # Scores
            if 'overall_score' in page:
                metrics['scores_per_page'].append({
                    'url': page.get('url', ''),
                    'score': page.get('overall_score', 0)
                })
            
            # Issues
            if 'issues' in page:
                metrics['issues_per_page'].append({
                    'url': page.get('url', ''),
                    'count': len(page['issues'])
                })
    
    # Calculate aggregates
    if metrics['load_times']:
        times = [t['time'] for t in metrics['load_times']]
        metrics['load_time_stats'] = {
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'median': sorted(times)[len(times)//2]
        }
    
    if metrics['scores_per_page']:
        scores = [s['score'] for s in metrics['scores_per_page']]
        metrics['score_stats'] = {
            'average': sum(scores) / len(scores),
            'min': min(scores),
            'max': max(scores),
            'median': sorted(scores)[len(scores)//2]
        }
    
    # Identify problem pages
    metrics['slowest_pages'] = sorted(metrics['load_times'], 
                                     key=lambda x: x['time'], 
                                     reverse=True)[:10]
    metrics['lowest_scoring_pages'] = sorted(metrics['scores_per_page'], 
                                            key=lambda x: x['score'])[:10]
    
    return metrics
