"""App orchestrator module - coordinates analyzers and manages the analysis flow."""

import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional, AsyncIterator
from urllib.parse import urlparse

from .config import Config
from .crawler import Crawler
from .report_optimizer import (
    aggregate_issues,
    generate_specific_recommendations,
    create_executive_summary,
    generate_performance_metrics
)
from ..analyzers import (
    analyze_seo,
    analyze_content,
    analyze_technical,
    analyze_performance,
    analyze_links
)


class SEOAnalyzer:
    """Main SEO analyzer that orchestrates all analysis modules."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the SEO analyzer with configuration."""
        self.config = config or Config()
        self.crawler = None
        self.results = []
        self.broken_links = set()
        
    async def analyze_page(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single page using all analyzers."""
        if 'error' in page_data:
            return {
                'url': page_data['url'],
                'error': page_data.get('error'),
                'status_code': page_data.get('status_code', 0)
            }
        
        url = page_data['url']
        soup = page_data.get('soup')
        
        if not soup:
            return {
                'url': url,
                'error': 'No content to analyze',
                'status_code': page_data.get('status_code', 0)
            }
        
        # Track broken links
        if page_data.get('status_code', 200) >= 400:
            self.broken_links.add(url)
        
        # Run all analyzers
        results = {
            'url': url,
            'status_code': page_data.get('status_code', 200),
            'load_time': page_data.get('load_time', 0),
            'timestamp': page_data.get('timestamp', time.time())
        }
        
        try:
            # SEO analysis
            seo_results = analyze_seo(soup, url)
            results['seo'] = seo_results
            
            # Content analysis
            content_results = analyze_content(
                soup, url, 
                target_keywords=self.config.analysis.target_keywords
            )
            results['content'] = content_results
            
            # Technical analysis
            technical_results = analyze_technical(
                soup, url,
                headers=page_data.get('headers'),
                status_code=page_data.get('status_code', 200)
            )
            results['technical'] = technical_results
            
            # Performance analysis
            performance_results = analyze_performance(
                soup, url,
                load_time=page_data.get('load_time', 0),
                content_length=page_data.get('content_length', 0)
            )
            results['performance'] = performance_results
            
            # Links analysis
            links_results = analyze_links(
                soup, url,
                broken_links=self.broken_links if self.config.analysis.check_external_links else None
            )
            results['links'] = links_results
            
            # Calculate overall score
            scores = [
                seo_results['score'] * 0.25,        # 25% weight
                content_results['score'] * 0.25,    # 25% weight
                technical_results['score'] * 0.20,  # 20% weight
                performance_results['score'] * 0.20, # 20% weight
                links_results['score'] * 0.10       # 10% weight
            ]
            results['overall_score'] = sum(scores)
            
            # Aggregate all issues
            all_issues = []
            for analyzer in ['seo', 'content', 'technical', 'performance', 'links']:
                if analyzer in results and 'issues' in results[analyzer]:
                    all_issues.extend(results[analyzer]['issues'])
            
            results['issues'] = all_issues
            results['issue_counts'] = {
                'critical': sum(1 for i in all_issues if i.get('severity') == 'critical'),
                'warning': sum(1 for i in all_issues if i.get('severity') == 'warning'),
                'notice': sum(1 for i in all_issues if i.get('severity') == 'notice')
            }
            
            # Generate recommendations
            results['recommendations'] = self.generate_recommendations(results)
            
        except Exception as e:
            results['error'] = f"Analysis error: {str(e)}"
            results['overall_score'] = 0
            results['issues'] = []
        
        return results
    
    def generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis results."""
        recommendations = []
        issues = results.get('issues', [])
        
        # Priority 1: Critical issues
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        
        for issue in critical_issues[:3]:  # Top 3 critical
            if 'Missing page title' in issue.get('message', ''):
                recommendations.append("Add a unique, descriptive <title> tag (30-60 characters)")
            elif 'Missing meta description' in issue.get('message', ''):
                recommendations.append("Add a compelling meta description (120-160 characters)")
            elif 'not using HTTPS' in issue.get('message', ''):
                recommendations.append("Enable HTTPS with an SSL certificate for security and SEO")
            elif 'Missing viewport' in issue.get('message', ''):
                recommendations.append('Add <meta name="viewport" content="width=device-width, initial-scale=1">')
            elif 'No H1' in issue.get('message', ''):
                recommendations.append("Add a single, descriptive H1 heading to structure your content")
            elif 'broken links' in issue.get('message', '').lower():
                recommendations.append("Fix or remove broken links to improve user experience")
        
        # Priority 2: Performance issues
        if 'performance' in results and results['performance']['data'].get('load_time', 0) > 3:
            recommendations.append("Optimize images and enable lazy loading to improve page load time")
        
        if 'performance' in results and results['performance']['data'].get('total_resources', 0) > 50:
            recommendations.append("Reduce the number of resources by bundling CSS/JS files")
        
        # Priority 3: Content improvements
        if 'content' in results and results['content']['data'].get('word_count', 0) < 300:
            recommendations.append("Expand content to at least 300 words for better SEO visibility")
        
        if 'content' in results and results['content']['data'].get('flesch_reading_ease', 100) < 50:
            recommendations.append("Simplify content for better readability (aim for 8th-grade level)")
        
        # Priority 4: SEO enhancements
        seo_data = results.get('seo', {}).get('data', {})
        if not seo_data.get('structured_data'):
            recommendations.append("Add JSON-LD structured data for rich snippets in search results")
        
        if not seo_data.get('open_graph'):
            recommendations.append("Add Open Graph meta tags for better social media sharing")
        
        # Limit to top 10 recommendations
        return recommendations[:10]
    
    async def analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze a single URL."""
        async with Crawler(self.config.crawler.__dict__) as crawler:
            page_data = await crawler.fetch_page(url)
            
            if not page_data:
                return {'url': url, 'error': 'Failed to fetch page'}
            
            return await self.analyze_page(page_data)
    
    async def crawl_site(self, start_url: str) -> AsyncIterator[Dict[str, Any]]:
        """Crawl and analyze a website, yielding results as they complete."""
        async with Crawler(self.config.crawler.__dict__) as crawler:
            self.crawler = crawler
            
            # Start crawling
            crawl_task = asyncio.create_task(
                crawler.crawl_site(start_url, self.config.crawler.max_pages)
            )
            
            # Process pages as they're crawled
            processed = 0
            while not crawl_task.done() or processed < len(crawler.results):
                if processed < len(crawler.results):
                    page_data = crawler.results[processed]
                    processed += 1
                    
                    # Analyze the page
                    analysis = await self.analyze_page(page_data)
                    self.results.append(analysis)
                    yield analysis
                else:
                    # Wait a bit for more results
                    await asyncio.sleep(0.1)
            
            # Ensure crawl task completes
            await crawl_task
    
    async def analyze_urls(self, urls: List[str]) -> AsyncIterator[Dict[str, Any]]:
        """Analyze a list of URLs, yielding results as they complete."""
        async with Crawler(self.config.crawler.__dict__) as crawler:
            self.crawler = crawler
            
            # Start crawling
            crawl_task = asyncio.create_task(crawler.crawl_urls(urls))
            
            # Process pages as they're crawled
            processed = 0
            while not crawl_task.done() or processed < len(crawler.results):
                if processed < len(crawler.results):
                    page_data = crawler.results[processed]
                    processed += 1
                    
                    # Analyze the page
                    analysis = await self.analyze_page(page_data)
                    self.results.append(analysis)
                    yield analysis
                else:
                    # Wait a bit for more results
                    await asyncio.sleep(0.1)
            
            # Ensure crawl task completes
            await crawl_task
    
    async def analyze_sitemap(self, sitemap_url: str) -> List[Dict[str, Any]]:
        """Analyze all URLs from a sitemap."""
        async with Crawler(self.config.crawler.__dict__) as crawler:
            self.crawler = crawler
            
            # Crawl sitemap
            crawl_results = await crawler.crawl_sitemap(sitemap_url)
            
            # Analyze all pages
            results = []
            for page_data in crawl_results:
                analysis = await self.analyze_page(page_data)
                results.append(analysis)
                self.results.append(analysis)
            
            return results
    
    def generate_site_report(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate an aggregate report for multiple pages."""
        if not page_results:
            return {'error': 'No pages to analyze'}
        
        # Calculate aggregate scores
        total_score = 0
        category_scores = {
            'seo': [],
            'content': [],
            'technical': [],
            'performance': [],
            'links': []
        }
        
        all_issues = []
        successful_pages = []
        failed_pages = []
        
        for page in page_results:
            if 'error' in page:
                failed_pages.append(page['url'])
                continue
            
            successful_pages.append(page['url'])
            total_score += page.get('overall_score', 0)
            
            # Collect category scores
            for category in category_scores:
                if category in page and 'score' in page[category]:
                    category_scores[category].append(page[category]['score'])
            
            # Collect all issues with URL context
            page_issues = page.get('issues', [])
            for issue in page_issues:
                issue['url'] = page['url']  # Add URL context to each issue
            all_issues.extend(page_issues)
        
        # Calculate averages
        num_successful = len(successful_pages)
        
        report = {
            'summary': {
                'total_pages': len(page_results),
                'successful_pages': num_successful,
                'failed_pages': len(failed_pages),
                'analysis_timestamp': time.time()
            },
            'overall_score': total_score / num_successful if num_successful > 0 else 0,
            'category_scores': {}
        }
        
        # Average category scores
        for category, scores in category_scores.items():
            if scores:
                report['category_scores'][category] = sum(scores) / len(scores)
        
        # Aggregate issues to prevent duplication
        aggregated_issues, aggregation_stats = aggregate_issues(all_issues)
        report['aggregated_issues'] = aggregated_issues
        report['aggregation_stats'] = aggregation_stats
        
        # Keep original issues for backward compatibility but limit them
        report['issues'] = aggregated_issues  # Use aggregated issues instead of all
        
        # Update issue counts based on aggregated issues
        report['issue_counts'] = {
            'critical': sum(i.get('count', 1) for i in aggregated_issues if i.get('severity') == 'critical'),
            'warning': sum(i.get('count', 1) for i in aggregated_issues if i.get('severity') == 'warning'),
            'notice': sum(i.get('count', 1) for i in aggregated_issues if i.get('severity') == 'notice'),
            'total': sum(i.get('count', 1) for i in aggregated_issues),
            'unique': len(aggregated_issues)
        }
        
        # Top issues from aggregated data
        report['top_issues'] = aggregated_issues[:10] if aggregated_issues else []
        
        # Generate performance metrics
        report['performance_metrics'] = generate_performance_metrics(page_results)
        
        # Basic performance stats (for backward compatibility)
        load_times = [p.get('load_time', 0) for p in page_results if 'error' not in p and p.get('load_time', 0) > 0]
        if load_times:
            report['performance'] = {
                'average_load_time': sum(load_times) / len(load_times),
                'min_load_time': min(load_times),
                'max_load_time': max(load_times)
            }
        
        # Generate enhanced recommendations
        report['enhanced_recommendations'] = generate_specific_recommendations(report)
        
        # Keep simple recommendations for backward compatibility
        report['recommendations'] = self.generate_site_recommendations(report)
        
        # Create executive summary
        report['executive_summary'] = create_executive_summary(report)
        
        # Include page results but limit to prevent huge reports
        # Only include summary data for each page, not full analysis
        report['pages_summary'] = [
            {
                'url': p.get('url'),
                'score': p.get('overall_score', 0),
                'status_code': p.get('status_code'),
                'load_time': p.get('load_time', 0),
                'issue_count': len(p.get('issues', [])),
                'timestamp': p.get('timestamp')
            } for p in page_results[:100]  # Limit to first 100 pages
        ]
        
        # Keep full page results but limit size
        if len(page_results) <= 50:
            report['pages'] = page_results
        else:
            # For large crawls, only include pages with issues
            report['pages'] = [p for p in page_results if len(p.get('issues', [])) > 0][:50]
            report['pages_truncated'] = True
            report['pages_truncated_count'] = len(page_results) - 50
        
        return report
    
    def generate_batch_report(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a report for batch URL analysis."""
        return self.generate_site_report(page_results)
    
    def generate_site_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate site-wide recommendations."""
        recommendations = []
        
        # Based on overall score
        overall_score = report.get('overall_score', 0)
        if overall_score < 50:
            recommendations.append("Major SEO improvements needed - focus on critical issues first")
        elif overall_score < 70:
            recommendations.append("Good foundation, but significant optimization opportunities exist")
        elif overall_score < 85:
            recommendations.append("Strong SEO presence with room for fine-tuning")
        else:
            recommendations.append("Excellent SEO health - maintain current practices")
        
        # Based on issue counts
        issue_counts = report.get('issue_counts', {})
        if issue_counts.get('critical', 0) > 5:
            recommendations.append(f"Address {issue_counts['critical']} critical issues immediately")
        
        # Based on category scores
        category_scores = report.get('category_scores', {})
        lowest_category = min(category_scores.items(), key=lambda x: x[1]) if category_scores else None
        
        if lowest_category and lowest_category[1] < 60:
            category_name = lowest_category[0].title()
            recommendations.append(f"Focus on improving {category_name} (currently {lowest_category[1]:.0f}/100)")
        
        # Performance recommendations
        perf = report.get('performance', {})
        if perf.get('average_load_time', 0) > 3:
            recommendations.append(f"Average load time is {perf['average_load_time']:.1f}s - implement caching and optimization")
        
        # Top issues
        top_issues = report.get('top_issues', [])
        if top_issues:
            most_common = top_issues[0]
            if most_common['count'] > 5:
                recommendations.append(f"Fix widespread issue: {most_common['message']} (affects {most_common['count']} pages)")
        
        return recommendations[:10]
    
    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get current crawl statistics."""
        stats = {}
        
        if self.crawler:
            stats.update(self.crawler.get_statistics())
        
        # Memory usage
        process = psutil.Process()
        stats['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
        
        # Analysis statistics
        stats['pages_analyzed'] = len(self.results)
        stats['broken_links_found'] = len(self.broken_links)
        
        if self.results:
            scores = [r.get('overall_score', 0) for r in self.results if 'error' not in r]
            if scores:
                stats['average_score'] = sum(scores) / len(scores)
        
        return stats
