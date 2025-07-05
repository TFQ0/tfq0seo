"""
Main application module for tfq0seo
"""
import asyncio
from typing import Dict, List, Optional, Callable, Any
from .crawler import WebCrawler
from .config import Config
from ..analyzers.seo import SEOAnalyzer
from ..analyzers.content import ContentAnalyzer
from ..analyzers.technical import TechnicalAnalyzer
from ..analyzers.performance import PerformanceAnalyzer
from ..analyzers.links import LinkAnalyzer
import textstat
import re
from bs4 import BeautifulSoup

class SEOAnalyzerApp:
    """Main application class for SEO analysis"""
    
    def __init__(self, config: Config):
        self.config = config
        self.crawler = WebCrawler(config)
        self.seo_analyzer = SEOAnalyzer(config)
        self.content_analyzer = ContentAnalyzer(config)
        self.technical_analyzer = TechnicalAnalyzer(config)
        self.performance_analyzer = PerformanceAnalyzer(config)
        self.link_analyzer = LinkAnalyzer(config)
    
    async def crawl(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Crawl website and analyze all pages"""
        # Crawl pages
        crawl_results = await self.crawler.crawl(progress_callback)
        
        # Analyze each page
        analyzed_pages = []
        issues = {
            'critical': 0,
            'warnings': 0,
            'notices': 0
        }
        
        for url, page_data in crawl_results.items():
            if page_data.get('status_code') == 200 and 'text/html' in page_data.get('content_type', ''):
                analysis = await self._analyze_page(page_data)
                analyzed_pages.append(analysis)
                
                # Count issues
                for issue in analysis.get('issues', []):
                    if issue['severity'] == 'critical':
                        issues['critical'] += 1
                    elif issue['severity'] == 'warning':
                        issues['warnings'] += 1
                    else:
                        issues['notices'] += 1
        
        # Generate summary
        summary = self._generate_summary(analyzed_pages)
        
        return {
            'config': self.config.to_dict(),
            'pages': analyzed_pages,
            'issues': issues,
            'summary': summary,
            'crawl_stats': {
                'total_urls_found': len(crawl_results),
                'pages_analyzed': len(analyzed_pages),
                'crawl_depth': self.config.depth,
                'respect_robots': self.config.respect_robots
            }
        }
    
    async def analyze_single(self, url: str) -> Dict[str, Any]:
        """Analyze a single URL"""
        # Fetch page
        await self.crawler.initialize()
        page_data = await self.crawler._fetch_page(url)
        await self.crawler.session.close()
        
        if page_data.get('status_code') != 200:
            return {
                'url': url,
                'error': f"Failed to fetch page: {page_data.get('error', 'Unknown error')}",
                'status_code': page_data.get('status_code', 0)
            }
        
        # Analyze page
        analysis = await self._analyze_page(page_data)
        
        # Add competitor analysis if requested
        if self.config.competitors:
            analysis['competitive_analysis'] = await self._analyze_competitors(analysis)
        
        return analysis
    
    async def _analyze_page(self, page_data: Dict) -> Dict[str, Any]:
        """Analyze a single page"""
        url = page_data['url']
        content = page_data.get('content', '')
        soup = BeautifulSoup(content, 'lxml') if content else None
        
        # Run all analyzers
        meta_analysis = self.seo_analyzer.analyze_meta_tags(soup) if soup else {}
        content_analysis = self.content_analyzer.analyze(soup, content) if soup else {}
        technical_analysis = self.technical_analyzer.analyze(page_data, soup) if soup else {}
        performance_analysis = self.performance_analyzer.analyze(page_data)
        link_analysis = self.link_analyzer.analyze(page_data, soup) if soup else {}
        
        # Combine results
        issues = []
        issues.extend(meta_analysis.get('issues', []))
        issues.extend(content_analysis.get('issues', []))
        issues.extend(technical_analysis.get('issues', []))
        issues.extend(performance_analysis.get('issues', []))
        issues.extend(link_analysis.get('issues', []))
        
        return {
            'url': url,
            'final_url': page_data.get('final_url', url),
            'title': meta_analysis.get('title', ''),
            'meta_description': meta_analysis.get('description', ''),
            'status_code': page_data.get('status_code', 0),
            'load_time': page_data.get('load_time', 0),
            'meta_tags': meta_analysis,
            'content': content_analysis,
            'technical': technical_analysis,
            'performance': performance_analysis,
            'links': link_analysis,
            'issues': issues,
            'recommendations': self._generate_recommendations(issues),
            'score': self._calculate_seo_score(issues)
        }
    
    def _generate_summary(self, pages: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics"""
        if not pages:
            return {}
        
        total_pages = len(pages)
        
        # Calculate averages
        avg_load_time = sum(p.get('load_time', 0) for p in pages) / total_pages
        avg_word_count = sum(p.get('content', {}).get('word_count', 0) for p in pages) / total_pages
        avg_score = sum(p.get('score', 0) for p in pages) / total_pages
        
        # Count issues by type
        missing_titles = sum(1 for p in pages if not p.get('title'))
        missing_descriptions = sum(1 for p in pages if not p.get('meta_description'))
        slow_pages = sum(1 for p in pages if p.get('load_time', 0) > self.config.max_page_load_time)
        thin_content = sum(1 for p in pages if p.get('content', {}).get('word_count', 0) < self.config.min_content_words)
        
        return {
            'total_pages': total_pages,
            'average_load_time': round(avg_load_time, 2),
            'average_word_count': int(avg_word_count),
            'average_seo_score': round(avg_score, 1),
            'pages_missing_title': missing_titles,
            'pages_missing_description': missing_descriptions,
            'slow_loading_pages': slow_pages,
            'thin_content_pages': thin_content,
            'top_issues': self._get_top_issues(pages),
            'performance_summary': {
                'fast': sum(1 for p in pages if p.get('load_time', 0) < 1.5),
                'moderate': sum(1 for p in pages if 1.5 <= p.get('load_time', 0) < 3),
                'slow': sum(1 for p in pages if p.get('load_time', 0) >= 3)
            }
        }
    
    def _get_top_issues(self, pages: List[Dict]) -> List[Dict]:
        """Get most common issues across all pages"""
        issue_counts = {}
        
        for page in pages:
            for issue in page.get('issues', []):
                key = issue['type']
                if key not in issue_counts:
                    issue_counts[key] = {
                        'type': issue['type'],
                        'message': issue['message'],
                        'severity': issue['severity'],
                        'count': 0
                    }
                issue_counts[key]['count'] += 1
        
        # Sort by count and return top 10
        return sorted(issue_counts.values(), key=lambda x: x['count'], reverse=True)[:10]
    
    def _generate_recommendations(self, issues: List[Dict]) -> List[Dict]:
        """Generate actionable recommendations based on issues"""
        recommendations = []
        
        # Group issues by type
        issue_types = {}
        for issue in issues:
            issue_type = issue['type']
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        # Generate recommendations
        if 'missing_title' in issue_types:
            recommendations.append({
                'priority': 'high',
                'category': 'meta_tags',
                'action': 'Add a unique, descriptive title tag',
                'impact': 'Critical for SEO and user experience'
            })
        
        if 'short_title' in issue_types or 'long_title' in issue_types:
            recommendations.append({
                'priority': 'medium',
                'category': 'meta_tags',
                'action': f'Optimize title length to {self.config.title_min_length}-{self.config.title_max_length} characters',
                'impact': 'Improves click-through rates in search results'
            })
        
        if 'missing_description' in issue_types:
            recommendations.append({
                'priority': 'high',
                'category': 'meta_tags',
                'action': 'Add a compelling meta description',
                'impact': 'Improves click-through rates from search results'
            })
        
        if 'thin_content' in issue_types:
            recommendations.append({
                'priority': 'high',
                'category': 'content',
                'action': f'Expand content to at least {self.config.min_content_words} words',
                'impact': 'Better rankings and user engagement'
            })
        
        if 'slow_load_time' in issue_types:
            recommendations.append({
                'priority': 'high',
                'category': 'performance',
                'action': 'Optimize page load time to under 3 seconds',
                'impact': 'Critical for user experience and rankings'
            })
        
        return recommendations
    
    def _calculate_seo_score(self, issues: List[Dict]) -> float:
        """Calculate overall SEO score (0-100)"""
        score = 100.0
        
        # Deduct points based on issue severity
        for issue in issues:
            if issue['severity'] == 'critical':
                score -= 10
            elif issue['severity'] == 'warning':
                score -= 5
            else:  # notice
                score -= 2
        
        return max(0, score)
    
    async def _analyze_competitors(self, analysis: Dict) -> Dict[str, Any]:
        """Analyze competitors and compare"""
        competitor_data = []
        
        for competitor_url in self.config.competitors:
            comp_analysis = await self.analyze_single(competitor_url)
            competitor_data.append({
                'url': competitor_url,
                'score': comp_analysis.get('score', 0),
                'load_time': comp_analysis.get('load_time', 0),
                'word_count': comp_analysis.get('content', {}).get('word_count', 0),
                'title_length': len(comp_analysis.get('title', '')),
                'description_length': len(comp_analysis.get('meta_description', ''))
            })
        
        # Compare with current site
        comparison = {
            'competitors': competitor_data,
            'comparison': {
                'score_rank': self._get_rank(analysis.get('score', 0), 
                                            [c['score'] for c in competitor_data]),
                'speed_rank': self._get_rank(analysis.get('load_time', 0), 
                                            [c['load_time'] for c in competitor_data], 
                                            reverse=True),
                'content_rank': self._get_rank(analysis.get('content', {}).get('word_count', 0), 
                                              [c['word_count'] for c in competitor_data])
            }
        }
        
        return comparison
    
    def _get_rank(self, value: float, competitor_values: List[float], reverse: bool = False) -> int:
        """Get rank compared to competitors"""
        all_values = [value] + competitor_values
        all_values.sort(reverse=not reverse)
        return all_values.index(value) + 1
    
    def analyze_content(self, content: str, keyword: str) -> Dict[str, Any]:
        """Analyze content for SEO optimization"""
        # Calculate basic metrics
        word_count = len(content.split())
        sentence_count = textstat.sentence_count(content)
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        
        # Keyword analysis
        keyword_lower = keyword.lower()
        content_lower = content.lower()
        keyword_count = content_lower.count(keyword_lower)
        keyword_density = (keyword_count / word_count * 100) if word_count > 0 else 0
        
        # Readability scores
        flesch_score = textstat.flesch_reading_ease(content)
        gunning_fog = textstat.gunning_fog(content)
        
        # Generate recommendations
        recommendations = []
        
        if word_count < self.config.min_content_words:
            recommendations.append(f"Add more content. Current: {word_count} words, recommended: {self.config.min_content_words}+")
        
        if keyword_density > self.config.max_keyword_density:
            recommendations.append(f"Reduce keyword density. Current: {keyword_density:.1f}%, recommended: <{self.config.max_keyword_density}%")
        elif keyword_density < 0.5:
            recommendations.append("Consider using your target keyword more frequently")
        
        if flesch_score < self.config.min_readability_score:
            recommendations.append(f"Simplify your writing. Flesch score: {flesch_score:.1f}, recommended: {self.config.min_readability_score}+")
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
            'keyword': keyword,
            'keyword_count': keyword_count,
            'keyword_density': round(keyword_density, 2),
            'readability_score': round(flesch_score, 1),
            'gunning_fog_index': round(gunning_fog, 1),
            'recommendations': recommendations,
            'metrics': {
                'average_words_per_sentence': round(word_count / sentence_count, 1) if sentence_count > 0 else 0,
                'average_words_per_paragraph': round(word_count / paragraph_count, 1) if paragraph_count > 0 else 0
            }
        } 