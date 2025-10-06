"""
Main application module for tfq0seo - Optimized for speed and accuracy
"""
import asyncio
import re
import textstat
from typing import Dict, List, Optional, Callable, Any
from .crawler import WebCrawler
from .config import Config
from ..analyzers.seo import SEOAnalyzer
from ..analyzers.content import ContentAnalyzer
from ..analyzers.technical import TechnicalAnalyzer
from ..analyzers.performance import PerformanceAnalyzer
from ..analyzers.links import LinkAnalyzer
from bs4 import BeautifulSoup
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class SEOAnalyzerApp:
    """Main application class for SEO analysis - streamlined and fast"""
    
    def __init__(self, config: Config):
        self.config = config
        self.crawler = WebCrawler(config)
        self.seo_analyzer = SEOAnalyzer(config)
        self.content_analyzer = ContentAnalyzer(config)
        self.technical_analyzer = TechnicalAnalyzer(config)
        self.performance_analyzer = PerformanceAnalyzer(config)
        self.link_analyzer = LinkAnalyzer(config)
    
    def _create_soup(self, content: str) -> Optional[BeautifulSoup]:
        """Create BeautifulSoup object - optimized single parser"""
        if not content:
            return None
        
        try:
            # Use lxml if available (fastest), otherwise html.parser
            try:
                import lxml
                return BeautifulSoup(content, 'lxml')
            except ImportError:
                return BeautifulSoup(content, 'html.parser')
        except Exception as e:
            logger.warning(f"HTML parsing failed: {e}")
            return None
    

    
    async def crawl(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Crawl website and analyze all pages"""
        try:
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
                try:
                    # Validate page data
                    if not isinstance(page_data, dict):
                        logger.error(f"Invalid page data for {url}")
                        continue
                    
                    # Only analyze successful HTML pages
                    status_code = page_data.get('status_code', 0)
                    content_type = page_data.get('content_type', '')
                    
                    if status_code == 200 and 'text/html' in content_type:
                        analysis = await self._analyze_page(page_data)
                        if analysis:
                            analyzed_pages.append(analysis)
                            
                            # Count issues
                            for issue in analysis.get('issues', []):
                                severity = issue.get('severity', 'notice')
                                if severity == 'critical':
                                    issues['critical'] += 1
                                elif severity == 'warning':
                                    issues['warnings'] += 1
                                else:
                                    issues['notices'] += 1
                    else:
                        # Add non-HTML or error pages to results
                        analyzed_pages.append({
                            'url': url,
                            'final_url': page_data.get('final_url', url),
                            'status_code': status_code,
                            'error': page_data.get('error', ''),
                            'content_type': content_type,
                            'load_time': page_data.get('load_time', 0),
                            'issues': [{
                                'type': 'non_html_page' if status_code == 200 else 'http_error',
                                'severity': 'notice' if status_code == 200 else 'warning',
                                'message': f'Page returned {status_code} - {content_type}'
                            }] if status_code != 200 or 'text/html' not in content_type else [],
                            'score': 0
                        })
                        
                except Exception as e:
                    logger.error(f"Error analyzing {url}: {e}")
                    # Add error entry
                    analyzed_pages.append({
                        'url': url,
                        'error': str(e),
                        'status_code': page_data.get('status_code', 0),
                        'issues': [{
                            'type': 'analysis_error',
                            'severity': 'critical',
                            'message': f'Analysis failed: {str(e)}'
                        }],
                        'score': 0
                    })
            
            # Generate summary
            summary = self._generate_summary(analyzed_pages)
            
            return {
                'config': self.config.to_dict(),
                'pages': analyzed_pages,
                'issues': issues,
                'summary': summary,
                'crawl_stats': {
                    'total_urls_found': len(crawl_results),
                    'pages_analyzed': len([p for p in analyzed_pages if not p.get('error')]),
                    'pages_with_errors': len([p for p in analyzed_pages if p.get('error')]),
                    'crawl_depth': self.config.depth,
                    'respect_robots': self.config.respect_robots
                }
            }
            
        except Exception as e:
            logger.error(f"Critical error during crawl: {e}")
            raise
    
    
    @asynccontextmanager
    async def _crawler_session(self):
        """Context manager for crawler session"""
        await self.crawler.initialize()
        try:
            yield
        finally:
            if self.crawler.session and not self.crawler.session.closed:
                await self.crawler.session.close()
    
    async def analyze_single(self, url: str) -> Dict[str, Any]:
        """Analyze a single URL"""
        try:
            # Fetch page
            async with self._crawler_session():
                page_data = await self.crawler._fetch_page(url)
            
            if not page_data:
                return {
                    'url': url,
                    'error': 'Failed to fetch page',
                    'status_code': 0
                }
            
            if page_data.get('status_code') != 200:
                return {
                    'url': url,
                    'error': f"HTTP {page_data.get('status_code', 0)}: {page_data.get('error', 'Unknown error')}",
                    'status_code': page_data.get('status_code', 0)
                }
            
            # Analyze page
            analysis = await self._analyze_page(page_data)
            
            if not analysis:
                return {
                    'url': url,
                    'error': 'Failed to analyze page',
                    'status_code': page_data.get('status_code', 0)
                }
            
            # Add competitor analysis if requested
            if self.config.competitors:
                try:
                    analysis['competitive_analysis'] = await self._analyze_competitors(analysis)
                except Exception as e:
                    logger.error(f"Error in competitive analysis: {e}")
                    analysis['competitive_analysis'] = {'error': str(e)}
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing single URL {url}: {e}")
            return {
                'url': url,
                'error': f"Analysis failed: {str(e)}",
                'status_code': 0
            }
    
    async def _analyze_page(self, page_data: Dict) -> Dict[str, Any]:
        """Analyze a single page"""
        try:
            # Validate page_data structure
            if not isinstance(page_data, dict):
                logger.error(f"Invalid page_data type: {type(page_data)}")
                return None
            
            url = page_data.get('url', 'unknown')
            content = page_data.get('content', '')
            soup = self._create_soup(content)
            
            # Initialize empty results in case analyzers fail
            meta_analysis = {}
            content_analysis = {}
            technical_analysis = {}
            performance_analysis = {}
            link_analysis = {}
            
            # Run all analyzers - fast and simple error handling
            try:
                meta_analysis = self.seo_analyzer.analyze_meta_tags(soup) if soup else {'issues': []}
            except Exception as e:
                logger.warning(f"SEO analyzer failed for {url}: {e}")
                meta_analysis = {'issues': [], 'title': '', 'description': ''}
            
            try:
                content_analysis = self.content_analyzer.analyze(soup, content) if soup else {'issues': []}
            except Exception as e:
                logger.warning(f"Content analyzer failed for {url}: {e}")
                content_analysis = {'issues': [], 'word_count': 0}
            
            try:
                technical_analysis = self.technical_analyzer.analyze(page_data, soup) if soup else {'issues': []}
            except Exception as e:
                logger.warning(f"Technical analyzer failed for {url}: {e}")
                technical_analysis = {'issues': []}
            
            try:
                performance_analysis = self.performance_analyzer.analyze(page_data)
            except Exception as e:
                logger.warning(f"Performance analyzer failed for {url}: {e}")
                performance_analysis = {'issues': [], 'load_time': page_data.get('load_time', 0)}
            
            try:
                link_analysis = self.link_analyzer.analyze(page_data, soup) if soup else {'issues': []}
            except Exception as e:
                logger.warning(f"Link analyzer failed for {url}: {e}")
                link_analysis = {'issues': []}
            
            # Combine results
            issues = []
            issues.extend(meta_analysis.get('issues', []))
            issues.extend(content_analysis.get('issues', []))
            issues.extend(technical_analysis.get('issues', []))
            issues.extend(performance_analysis.get('issues', []))
            issues.extend(link_analysis.get('issues', []))
            
            # Calculate comprehensive SEO score
            seo_score = self._calculate_comprehensive_seo_score(
                meta_analysis, content_analysis, technical_analysis,
                performance_analysis, link_analysis, issues
            )
            
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
                'score': seo_score['total'],
                'score_breakdown': seo_score
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Critical error analyzing page {page_data.get('url', 'unknown') if isinstance(page_data, dict) else 'unknown'}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _calculate_comprehensive_seo_score(self, meta_analysis: Dict, content_analysis: Dict,
                                         technical_analysis: Dict, performance_analysis: Dict,
                                         link_analysis: Dict, issues: List[Dict]) -> Dict[str, float]:
        """Calculate comprehensive SEO score based on weighted factors"""
        # Initialize scores for each category
        scores = {
            'meta_tags': 100.0,
            'content': 100.0,
            'technical': 100.0,
            'performance': 100.0,
            'links': 100.0
        }
        
        # Weights for each category (total = 100%)
        weights = {
            'meta_tags': 0.25,
            'content': 0.25,
            'technical': 0.20,
            'performance': 0.20,
            'links': 0.10
        }
        
        # Meta tags scoring
        if not meta_analysis.get('title'):
            scores['meta_tags'] -= 30  # Missing title is critical
        else:
            title_len = meta_analysis.get('title_length', 0)
            if title_len < self.config.title_min_length:
                scores['meta_tags'] -= 15
            elif title_len > self.config.title_max_length:
                scores['meta_tags'] -= 10
        
        if not meta_analysis.get('description'):
            scores['meta_tags'] -= 20  # Missing description is important
        else:
            desc_len = meta_analysis.get('description_length', 0)
            if desc_len < self.config.description_min_length:
                scores['meta_tags'] -= 10
            elif desc_len > self.config.description_max_length:
                scores['meta_tags'] -= 5
        
        if meta_analysis.get('h1_count', 0) == 0:
            scores['meta_tags'] -= 15
        elif meta_analysis.get('h1_count', 0) > 1:
            scores['meta_tags'] -= 5
        
        if not meta_analysis.get('has_viewport'):
            scores['meta_tags'] -= 20  # Mobile-friendliness issue
        
        # Content scoring
        word_count = content_analysis.get('word_count', 0)
        if word_count < self.config.min_content_words:
            penalty = min(30, (self.config.min_content_words - word_count) / 10)
            scores['content'] -= penalty
        
        readability = content_analysis.get('readability_score', 0)
        if readability < self.config.min_readability_score and word_count > 50:
            scores['content'] -= 15
        
        # Check for keyword optimization if target keyword specified
        if self.config.target_keyword and content_analysis.get('keyword_analysis'):
            keyword_density = content_analysis['keyword_analysis'].get('density', 0)
            if keyword_density > self.config.max_keyword_density:
                scores['content'] -= 20  # Keyword stuffing
            elif keyword_density < 0.5:
                scores['content'] -= 10  # Under-optimized
        
        # Technical scoring
        if not technical_analysis.get('https'):
            scores['technical'] -= 30  # HTTPS is critical
        
        if not technical_analysis.get('compression'):
            scores['technical'] -= 10
        
        if not technical_analysis.get('mobile_friendly'):
            scores['technical'] -= 25
        
        security_headers = technical_analysis.get('security_headers', {})
        missing_headers = 6 - len(security_headers)
        scores['technical'] -= (missing_headers * 2)  # -2 points per missing header
        
        # Performance scoring
        load_time = performance_analysis.get('load_time', 0)
        if load_time > self.config.max_page_load_time:
            scores['performance'] -= min(40, (load_time - self.config.max_page_load_time) * 10)
        elif load_time > 2:
            scores['performance'] -= 15
        
        performance_score = performance_analysis.get('performance_score', 100)
        scores['performance'] = min(scores['performance'], performance_score)
        
        # Links scoring
        broken_links = link_analysis.get('broken_links', 0)
        if broken_links > 0:
            scores['links'] -= min(30, broken_links * 5)
        
        internal_links = link_analysis.get('internal_links', 0)
        if internal_links < 3:
            scores['links'] -= 15
        
        # Ensure scores don't go below 0
        for category in scores:
            scores[category] = max(0, scores[category])
        
        # Calculate weighted total
        total = sum(scores[cat] * weights[cat] for cat in scores)
        
        return {
            'total': round(total, 1),
            'meta_tags': round(scores['meta_tags'], 1),
            'content': round(scores['content'], 1),
            'technical': round(scores['technical'], 1),
            'performance': round(scores['performance'], 1),
            'links': round(scores['links'], 1)
        }
    
    def _generate_summary(self, pages: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics"""
        if not pages:
            return {}
        
        # Filter out error pages for statistics
        valid_pages = [p for p in pages if not p.get('error') and p.get('status_code') == 200]
        
        if not valid_pages:
            return {
                'total_pages': len(pages),
                'valid_pages': 0,
                'error_pages': len(pages),
                'average_load_time': 0,
                'average_word_count': 0,
                'average_seo_score': 0
            }
        
        total_pages = len(pages)
        valid_count = len(valid_pages)
        
        # Calculate averages for valid pages only
        avg_load_time = sum(p.get('load_time', 0) for p in valid_pages) / valid_count
        avg_word_count = sum(p.get('content', {}).get('word_count', 0) for p in valid_pages) / valid_count
        avg_score = sum(p.get('score', 0) for p in valid_pages) / valid_count
        
        # Score breakdown averages
        score_breakdowns = [p.get('score_breakdown', {}) for p in valid_pages if p.get('score_breakdown')]
        avg_score_breakdown = {}
        if score_breakdowns:
            for category in ['meta_tags', 'content', 'technical', 'performance', 'links']:
                avg_score_breakdown[category] = round(
                    sum(s.get(category, 0) for s in score_breakdowns) / len(score_breakdowns), 1
                )
        
        # Count issues by type
        missing_titles = sum(1 for p in valid_pages if not p.get('title'))
        missing_descriptions = sum(1 for p in valid_pages if not p.get('meta_description'))
        slow_pages = sum(1 for p in valid_pages if p.get('load_time', 0) > self.config.max_page_load_time)
        thin_content = sum(1 for p in valid_pages if p.get('content', {}).get('word_count', 0) < self.config.min_content_words)
        
        # HTTPS pages
        https_pages = sum(1 for p in valid_pages if p.get('technical', {}).get('https', False))
        
        # Mobile friendly pages
        mobile_friendly = sum(1 for p in valid_pages if p.get('technical', {}).get('mobile_friendly', False))
        
        return {
            'total_pages': total_pages,
            'valid_pages': valid_count,
            'error_pages': total_pages - valid_count,
            'average_load_time': round(avg_load_time, 2),
            'average_word_count': int(avg_word_count),
            'average_seo_score': round(avg_score, 1),
            'score_breakdown': avg_score_breakdown,
            'pages_missing_title': missing_titles,
            'pages_missing_description': missing_descriptions,
            'slow_loading_pages': slow_pages,
            'thin_content_pages': thin_content,
            'https_pages': https_pages,
            'mobile_friendly_pages': mobile_friendly,
            'top_issues': self._get_top_issues(valid_pages),
            'performance_summary': {
                'fast': sum(1 for p in valid_pages if p.get('load_time', 0) < 1.5),
                'moderate': sum(1 for p in valid_pages if 1.5 <= p.get('load_time', 0) < 3),
                'slow': sum(1 for p in valid_pages if p.get('load_time', 0) >= 3)
            }
        }
    
    def _get_top_issues(self, pages: List[Dict]) -> List[Dict]:
        """Get most common issues across all pages"""
        issue_counts = {}
        
        for page in pages:
            for issue in page.get('issues', []):
                key = (issue.get('type', ''), issue.get('severity', ''))
                if key not in issue_counts:
                    issue_counts[key] = {
                        'type': issue.get('type', ''),
                        'message': issue.get('message', ''),
                        'severity': issue.get('severity', ''),
                        'count': 0,
                        'pages_affected': []
                    }
                issue_counts[key]['count'] += 1
                issue_counts[key]['pages_affected'].append(page.get('url', ''))
        
        # Sort by count and severity
        severity_weight = {'critical': 3, 'warning': 2, 'notice': 1}
        sorted_issues = sorted(
            issue_counts.values(),
            key=lambda x: (severity_weight.get(x['severity'], 0), x['count']),
            reverse=True
        )
        
        # Return top 10 with limited page examples
        for issue in sorted_issues[:10]:
            issue['example_pages'] = issue['pages_affected'][:3]
            del issue['pages_affected']
        
        return sorted_issues[:10]
    
    
    async def _analyze_competitors(self, analysis: Dict) -> Dict[str, Any]:
        """Analyze competitors and compare"""
        competitor_data = []
        
        for competitor_url in self.config.competitors:
            try:
                comp_analysis = await self.analyze_single(competitor_url)
                if not comp_analysis.get('error'):
                    competitor_data.append({
                        'url': competitor_url,
                        'score': comp_analysis.get('score', 0),
                        'score_breakdown': comp_analysis.get('score_breakdown', {}),
                        'load_time': comp_analysis.get('load_time', 0),
                        'word_count': comp_analysis.get('content', {}).get('word_count', 0),
                        'title_length': len(comp_analysis.get('title', '')),
                        'description_length': len(comp_analysis.get('meta_description', '')),
                        'issues_count': len(comp_analysis.get('issues', []))
                    })
            except Exception as e:
                logger.error(f"Error analyzing competitor {competitor_url}: {e}")
        
        if not competitor_data:
            return {'error': 'No competitor data available'}
        
        # Compare with current site
        comparison = {
            'competitors': competitor_data,
            'comparison': {
                'score_rank': self._get_rank(
                    analysis.get('score', 0), 
                    [c['score'] for c in competitor_data]
                ),
                'speed_rank': self._get_rank(
                    analysis.get('load_time', 0), 
                    [c['load_time'] for c in competitor_data], 
                    reverse=True
                ),
                'content_rank': self._get_rank(
                    analysis.get('content', {}).get('word_count', 0), 
                    [c['word_count'] for c in competitor_data]
                ),
                'issues_rank': self._get_rank(
                    len(analysis.get('issues', [])),
                    [c['issues_count'] for c in competitor_data],
                    reverse=True
                )
            },
            'advantages': [],
            'disadvantages': []
        }
        
        # Identify advantages and disadvantages
        avg_competitor_score = sum(c['score'] for c in competitor_data) / len(competitor_data)
        if analysis.get('score', 0) > avg_competitor_score:
            comparison['advantages'].append(f"Higher SEO score ({analysis.get('score', 0)} vs {avg_competitor_score:.1f})")
        else:
            comparison['disadvantages'].append(f"Lower SEO score ({analysis.get('score', 0)} vs {avg_competitor_score:.1f})")
        
        avg_load_time = sum(c['load_time'] for c in competitor_data) / len(competitor_data)
        if analysis.get('load_time', 0) < avg_load_time:
            comparison['advantages'].append(f"Faster load time ({analysis.get('load_time', 0):.2f}s vs {avg_load_time:.2f}s)")
        else:
            comparison['disadvantages'].append(f"Slower load time ({analysis.get('load_time', 0):.2f}s vs {avg_load_time:.2f}s)")
        
        return comparison
    
    def _get_rank(self, value: float, competitor_values: List[float], reverse: bool = False) -> int:
        """Get rank compared to competitors (1 = best)"""
        all_values = [value] + competitor_values
        all_values.sort(reverse=not reverse)
        try:
            return all_values.index(value) + 1
        except ValueError:
            return len(all_values)
    
    def analyze_content(self, content: str, keyword: str) -> Dict[str, Any]:
        """Analyze content for SEO optimization"""
        if not content:
            return {'error': 'No content provided'}
        
        try:
            # Clean content (remove HTML if present)
            soup = self._create_soup(content)
            if soup:
                clean_content = soup.get_text()
            else:
                clean_content = content
            
            # Calculate basic metrics
            word_count = len(clean_content.split())
            sentences = re.split(r'[.!?]+', clean_content)
            sentence_count = len([s for s in sentences if s.strip()])
            paragraphs = clean_content.split('\n\n')
            paragraph_count = len([p for p in paragraphs if p.strip()])
            
            # Keyword analysis
            keyword_lower = keyword.lower()
            content_lower = clean_content.lower()
            
            # Find all keyword occurrences (including partial matches)
            keyword_count = content_lower.count(keyword_lower)
            keyword_density = (keyword_count / word_count * 100) if word_count > 0 else 0
            
            # Find keyword variations (simple stemming)
            variations = [keyword_lower, keyword_lower + 's', keyword_lower + 'ing', 
                         keyword_lower + 'ed', keyword_lower.rstrip('s')]
            variation_count = sum(content_lower.count(var) for var in variations if var != keyword_lower)
            
            # Readability scores
            try:
                flesch_score = textstat.flesch_reading_ease(clean_content)
                gunning_fog = textstat.gunning_fog(clean_content)
                reading_time = round(word_count / 200)  # Average reading speed
            except:
                flesch_score = 0
                gunning_fog = 0
                reading_time = 0
            
            # Generate recommendations
            recommendations = []
            
            if word_count < self.config.min_content_words:
                recommendations.append({
                    'type': 'content_length',
                    'priority': 'high',
                    'message': f"Add more content. Current: {word_count} words, recommended: {self.config.min_content_words}+"
                })
            
            if keyword_density > self.config.max_keyword_density:
                recommendations.append({
                    'type': 'keyword_density',
                    'priority': 'high',
                    'message': f"Reduce keyword density. Current: {keyword_density:.1f}%, recommended: <{self.config.max_keyword_density}%"
                })
            elif keyword_density < 0.5:
                recommendations.append({
                    'type': 'keyword_density',
                    'priority': 'medium',
                    'message': "Consider using your target keyword more frequently (0.5-2.5% density recommended)"
                })
            
            if flesch_score < self.config.min_readability_score:
                recommendations.append({
                    'type': 'readability',
                    'priority': 'medium',
                    'message': f"Simplify your writing. Flesch score: {flesch_score:.1f}, recommended: {self.config.min_readability_score}+"
                })
            
            if sentence_count > 0 and word_count / sentence_count > 20:
                recommendations.append({
                    'type': 'sentence_length',
                    'priority': 'low',
                    'message': "Consider breaking up long sentences for better readability"
                })
            
            return {
                'word_count': word_count,
                'sentence_count': sentence_count,
                'paragraph_count': paragraph_count,
                'keyword': keyword,
                'keyword_count': keyword_count,
                'keyword_variations': variation_count,
                'keyword_density': round(keyword_density, 2),
                'readability_score': round(flesch_score, 1),
                'gunning_fog_index': round(gunning_fog, 1),
                'reading_time_minutes': reading_time,
                'recommendations': recommendations,
                'metrics': {
                    'average_words_per_sentence': round(word_count / sentence_count, 1) if sentence_count > 0 else 0,
                    'average_words_per_paragraph': round(word_count / paragraph_count, 1) if paragraph_count > 0 else 0,
                    'lexical_diversity': round(len(set(clean_content.lower().split())) / word_count * 100, 1) if word_count > 0 else 0
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return {'error': f'Content analysis failed: {str(e)}'}
    
    async def extract_sitemap_urls(self, sitemap_url: str) -> List[Dict[str, str]]:
        """Extract URLs from sitemap.xml"""
        try:
            async with self._crawler_session() as session:
                # Fetch sitemap
                response = await self.crawler.fetch_page(session, sitemap_url)
                
                if response.get('error'):
                    logger.error(f"Failed to fetch sitemap: {response['error']}")
                    return []
                
                content = response.get('content', '')
                if not content:
                    return []
                
                # Parse sitemap XML
                try:
                    from xml.etree import ElementTree as ET
                    root = ET.fromstring(content)
                    
                    # Handle different sitemap namespaces
                    namespaces = {
                        '': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                        'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                        'xhtml': 'http://www.w3.org/1999/xhtml',
                        'image': 'http://www.google.com/schemas/sitemap-image/1.1',
                        'video': 'http://www.google.com/schemas/sitemap-video/1.1'
                    }
                    
                    urls = []
                    
                    # Check if this is a sitemap index
                    if root.tag.endswith('sitemapindex'):
                        # Extract sitemap URLs from index
                        for sitemap in root.findall('.//sitemap:sitemap', namespaces):
                            loc_elem = sitemap.find('sitemap:loc', namespaces)
                            if loc_elem is not None and loc_elem.text:
                                # Recursively fetch URLs from each sitemap
                                sub_urls = await self.extract_sitemap_urls(loc_elem.text.strip())
                                urls.extend(sub_urls)
                    else:
                        # Regular sitemap - extract URLs
                        for url_elem in root.findall('.//sitemap:url', namespaces):
                            loc_elem = url_elem.find('sitemap:loc', namespaces)
                            if loc_elem is not None and loc_elem.text:
                                url_data = {'url': loc_elem.text.strip()}
                                
                                # Extract optional elements
                                lastmod_elem = url_elem.find('sitemap:lastmod', namespaces)
                                if lastmod_elem is not None and lastmod_elem.text:
                                    url_data['lastmod'] = lastmod_elem.text.strip()
                                
                                priority_elem = url_elem.find('sitemap:priority', namespaces)
                                if priority_elem is not None and priority_elem.text:
                                    url_data['priority'] = priority_elem.text.strip()
                                
                                changefreq_elem = url_elem.find('sitemap:changefreq', namespaces)
                                if changefreq_elem is not None and changefreq_elem.text:
                                    url_data['changefreq'] = changefreq_elem.text.strip()
                                
                                urls.append(url_data)
                    
                    return urls
                    
                except ET.ParseError as e:
                    logger.error(f"Failed to parse sitemap XML: {e}")
                    
                    # Try to handle plain text sitemap (one URL per line)
                    lines = content.strip().split('\n')
                    urls = []
                    for line in lines:
                        line = line.strip()
                        if line and (line.startswith('http://') or line.startswith('https://')):
                            urls.append({'url': line})
                    return urls
                    
        except Exception as e:
            logger.error(f"Error extracting sitemap URLs: {e}")
            return [] 