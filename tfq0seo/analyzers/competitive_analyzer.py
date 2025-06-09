from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse
from collections import Counter
from ..utils.error_handler import handle_analysis_error

class CompetitiveAnalyzer:
    """tfq0seo Competitive Analyzer - Analyzes competitive SEO aspects.
    
    Provides comprehensive competitive analysis including:
    - Semantic keyword analysis
    - Content gap analysis
    - Competitor feature detection
    - Market positioning analysis
    """
    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            'User-Agent': config['crawling']['user_agent']
        }

    @handle_analysis_error
    def analyze(self, url: str, competitor_urls: List[str]) -> Dict:
        """Perform comprehensive competitive SEO analysis.
        
        Analyzes:
        - Content comparison
        - Feature comparison
        - Semantic keyword analysis
        - Market positioning
        
        Args:
            url: The main URL to analyze
            competitor_urls: List of competitor URLs to compare against
            
        Returns:
            Dict containing competitive analysis results
        """
        analysis = {
            'main_site': self._analyze_site(url),
            'competitors': {
                competitor: self._analyze_site(competitor)
                for competitor in competitor_urls
            },
            'comparative_analysis': self._compare_sites(url, competitor_urls)
        }
        
        return self._evaluate_competitive_analysis(analysis)

    def _analyze_site(self, url: str) -> Dict:
        """Analyze a single site for competitive comparison."""
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'content_metrics': self._analyze_content_metrics(soup),
                'feature_set': self._analyze_feature_set(soup),
                'semantic_keywords': self._extract_semantic_keywords(soup),
                'technical_implementation': self._analyze_technical_impl(soup, url)
            }
        except Exception as e:
            return {'error': str(e)}

    def _analyze_content_metrics(self, soup: BeautifulSoup) -> Dict:
        """Analyze content metrics for competitive comparison."""
        text_content = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
        words = text_content.split()
        
        return {
            'word_count': len(words),
            'heading_count': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            'paragraph_count': len(soup.find_all('p')),
            'image_count': len(soup.find_all('img')),
            'link_count': len(soup.find_all('a')),
            'list_count': len(soup.find_all(['ul', 'ol'])),
            'table_count': len(soup.find_all('table'))
        }

    def _analyze_feature_set(self, soup: BeautifulSoup) -> Dict:
        """Analyze implemented features for competitive comparison."""
        return {
            'has_schema': bool(soup.find_all('script', type='application/ld+json')),
            'has_opengraph': bool(soup.find_all('meta', property=lambda x: x and x.startswith('og:'))),
            'has_analytics': bool(soup.find_all('script', string=lambda x: x and ('gtag' in x or 'analytics' in x))),
            'has_amp': bool(soup.find('link', rel='amphtml')),
            'has_rss': bool(soup.find('link', type='application/rss+xml')),
            'has_search': bool(soup.find('form', attrs={'role': 'search'})) or bool(soup.find('input', attrs={'type': 'search'})),
            'has_social_links': bool(soup.find_all('a', href=lambda x: x and any(platform in x.lower() for platform in ['facebook', 'twitter', 'linkedin', 'instagram']))),
            'has_newsletter': bool(soup.find_all(['form', 'input'], string=lambda x: x and 'newsletter' in x.lower() if x else False)),
            'has_comments': bool(soup.find_all(['div', 'section'], id=lambda x: x and 'comment' in x.lower() if x else False))
        }

    def _extract_semantic_keywords(self, soup: BeautifulSoup) -> Dict:
        """Extract and analyze semantic keywords."""
        # Get text from important elements
        text_content = ' '.join([
            ' '.join([tag.get_text() for tag in soup.find_all(element)])
            for element in ['h1', 'h2', 'h3', 'title', 'meta']
        ])
        
        # Extract potential keywords (2-3 word phrases)
        words = text_content.lower().split()
        two_word_phrases = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        three_word_phrases = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        
        # Count frequencies
        two_word_freq = Counter(two_word_phrases).most_common(5)
        three_word_freq = Counter(three_word_phrases).most_common(5)
        
        return {
            'two_word_phrases': dict(two_word_freq),
            'three_word_phrases': dict(three_word_freq)
        }

    def _analyze_technical_impl(self, soup: BeautifulSoup, url: str) -> Dict:
        """Analyze technical implementation details."""
        return {
            'frameworks': self._detect_frameworks(soup),
            'technologies': self._detect_technologies(soup),
            'performance_features': self._detect_performance_features(soup),
            'seo_features': self._detect_seo_features(soup, url)
        }

    def _detect_frameworks(self, soup: BeautifulSoup) -> List[str]:
        """Detect web frameworks in use."""
        frameworks = []
        
        # React detection
        if soup.find_all('div', id='root') or soup.find_all(attrs={'data-reactroot': True}):
            frameworks.append('React')
        
        # Vue detection
        if soup.find_all(attrs={'data-v-': True}) or soup.find_all(id=lambda x: x and x.startswith('__NUXT_')):
            frameworks.append('Vue.js')
        
        # Angular detection
        if soup.find_all(attrs={'ng-': True}) or soup.find_all(attrs={'data-ng-': True}):
            frameworks.append('Angular')
        
        # Bootstrap detection
        if soup.find_all(class_=lambda x: x and 'bootstrap' in x.lower()):
            frameworks.append('Bootstrap')
        
        return frameworks

    def _detect_technologies(self, soup: BeautifulSoup) -> List[str]:
        """Detect technologies in use."""
        technologies = []
        
        # jQuery detection
        if soup.find_all('script', src=lambda x: x and 'jquery' in x.lower()):
            technologies.append('jQuery')
        
        # Font Awesome detection
        if soup.find_all('link', href=lambda x: x and 'font-awesome' in x.lower()):
            technologies.append('Font Awesome')
        
        # Google Fonts detection
        if soup.find_all('link', href=lambda x: x and 'fonts.googleapis.com' in x.lower()):
            technologies.append('Google Fonts')
        
        # CDN usage detection
        if soup.find_all(['script', 'link'], src=lambda x: x and any(cdn in x.lower() for cdn in ['cloudflare', 'jsdelivr', 'unpkg'])):
            technologies.append('CDN Usage')
        
        return technologies

    def _detect_performance_features(self, soup: BeautifulSoup) -> Dict:
        """Detect performance optimization features."""
        return {
            'lazy_loading': bool(soup.find_all(['img', 'iframe'], loading='lazy')),
            'resource_hints': bool(soup.find_all('link', rel=lambda x: x and x in ['preload', 'prefetch', 'preconnect'])),
            'async_scripts': bool(soup.find_all('script', attrs={'async': True})),
            'defer_scripts': bool(soup.find_all('script', attrs={'defer': True})),
            'minified_resources': bool(soup.find_all(['script', 'link'], href=lambda x: x and '.min.' in x if x else False))
        }

    def _detect_seo_features(self, soup: BeautifulSoup, url: str) -> Dict:
        """Detect SEO optimization features."""
        return {
            'semantic_html5': bool(soup.find_all(['header', 'nav', 'main', 'article', 'footer'])),
            'breadcrumbs': bool(soup.find_all(['nav'], attrs={'aria-label': 'breadcrumb'})) or bool(soup.find_all(class_=lambda x: x and 'breadcrumb' in x.lower())),
            'pagination': bool(soup.find_all(class_=lambda x: x and 'pagination' in x.lower())),
            'image_optimization': bool(soup.find_all('img', srcset=True)),
            'hreflang': bool(soup.find_all('link', rel='alternate', hreflang=True)),
            'canonical': bool(soup.find('link', rel='canonical')),
            'meta_robots': bool(soup.find('meta', attrs={'name': 'robots'})),
            'xml_sitemap': self._check_sitemap(url)
        }

    def _check_sitemap(self, url: str) -> bool:
        """Check for XML sitemap existence."""
        try:
            sitemap_url = f"{url.rstrip('/')}/sitemap.xml"
            response = requests.get(sitemap_url, headers=self.headers)
            return response.status_code == 200
        except Exception:
            return False

    def _compare_sites(self, main_url: str, competitor_urls: List[str]) -> Dict:
        """Compare main site against competitors."""
        try:
            main_response = requests.get(main_url, headers=self.headers)
            main_soup = BeautifulSoup(main_response.text, 'html.parser')
            main_metrics = self._analyze_content_metrics(main_soup)
            
            competitor_metrics = {}
            for url in competitor_urls:
                try:
                    response = requests.get(url, headers=self.headers)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    competitor_metrics[url] = self._analyze_content_metrics(soup)
                except Exception:
                    continue
            
            # Calculate averages
            avg_metrics = {}
            for metric in main_metrics:
                competitor_values = [metrics[metric] for metrics in competitor_metrics.values()]
                avg_metrics[metric] = sum(competitor_values) / len(competitor_values) if competitor_values else 0
            
            return {
                'content_comparison': {
                    'main_site': main_metrics,
                    'competitor_average': avg_metrics,
                    'relative_position': {
                        metric: {
                            'value': main_metrics[metric],
                            'avg': avg_metrics[metric],
                            'difference': main_metrics[metric] - avg_metrics[metric],
                            'percentage': (main_metrics[metric] / avg_metrics[metric] * 100) if avg_metrics[metric] else 0
                        }
                        for metric in main_metrics
                    }
                }
            }
        except Exception as e:
            return {'error': str(e)}

    def _evaluate_competitive_analysis(self, analysis: Dict) -> Dict:
        """Evaluate competitive analysis and generate recommendations."""
        evaluation = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }
        
        # Evaluate content metrics
        if 'comparative_analysis' in analysis and 'content_comparison' in analysis['comparative_analysis']:
            comparison = analysis['comparative_analysis']['content_comparison']
            relative = comparison['relative_position']
            
            # Word count evaluation
            word_count_diff = relative['word_count']['difference']
            if word_count_diff >= 0:
                evaluation['strengths'].append(f"Content length is above competitor average by {word_count_diff} words")
            else:
                evaluation['weaknesses'].append(f"Content length is below competitor average by {abs(word_count_diff)} words")
                evaluation['recommendations'].append("Increase content length to match or exceed competitor average")
            
            # Content structure evaluation
            for metric in ['heading_count', 'paragraph_count', 'image_count']:
                diff = relative[metric]['difference']
                if diff < 0:
                    evaluation['weaknesses'].append(f"{metric.replace('_', ' ').title()} is below competitor average")
                    evaluation['recommendations'].append(f"Consider adding more {metric.replace('_', ' ')} to match competitors")
        
        # Evaluate feature implementation
        if 'main_site' in analysis and 'feature_set' in analysis['main_site']:
            features = analysis['main_site']['feature_set']
            
            # Check important features
            if not features['has_schema']:
                evaluation['weaknesses'].append("Missing Schema.org markup")
                evaluation['recommendations'].append("Implement relevant Schema.org markup")
            
            if not features['has_analytics']:
                evaluation['weaknesses'].append("Analytics not detected")
                evaluation['recommendations'].append("Implement analytics tracking")
            
            if not features['has_search']:
                evaluation['recommendations'].append("Consider adding search functionality")
        
        # Add educational tips
        evaluation['education_tips'] = [
            "Regular competitive analysis helps maintain market position",
            "Focus on unique value proposition while matching competitor strengths",
            "Monitor competitor content strategies for industry trends",
            "Implement missing features strategically based on business goals"
        ]
        
        return evaluation 