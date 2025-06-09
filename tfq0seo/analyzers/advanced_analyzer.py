from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urlparse, urljoin
from ..utils.error_handler import handle_analysis_error

class AdvancedSEOAnalyzer:
    """tfq0seo Advanced SEO Analyzer - Analyzes advanced SEO aspects.
    
    Provides comprehensive analysis of advanced SEO features including:
    - User experience metrics
    - Content clustering
    - Internal linking structure
    - Rich snippets optimization
    - Progressive enhancement
    """
    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            'User-Agent': config['crawling']['user_agent']
        }

    @handle_analysis_error
    def analyze(self, url: str) -> Dict:
        """Perform comprehensive advanced SEO analysis.
        
        Analyzes:
        - User experience signals
        - Content relationships
        - Link architecture
        - Rich results potential
        - Progressive features
        
        Args:
            url: The URL to analyze
            
        Returns:
            Dict containing advanced analysis results
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            analysis = {
                'user_experience': self._analyze_user_experience(soup),
                'content_clusters': self._analyze_content_clusters(soup),
                'link_architecture': self._analyze_link_architecture(soup, url),
                'rich_results': self._analyze_rich_results(soup),
                'progressive_features': self._analyze_progressive_features(soup)
            }
            
            return self._evaluate_advanced_seo(analysis)
        except Exception as e:
            return {'error': str(e)}

    def _analyze_user_experience(self, soup: BeautifulSoup) -> Dict:
        """Analyze user experience signals."""
        return {
            'navigation': self._analyze_navigation(soup),
            'accessibility': self._analyze_accessibility(soup),
            'interaction': self._analyze_interaction_elements(soup),
            'content_layout': self._analyze_content_layout(soup)
        }

    def _analyze_navigation(self, soup: BeautifulSoup) -> Dict:
        """Analyze navigation structure and usability."""
        nav_elements = soup.find_all(['nav', 'header', 'menu'])
        return {
            'has_main_nav': bool(soup.find('nav', attrs={'role': 'navigation'}) or soup.find('nav', id=lambda x: x and 'main' in x.lower())),
            'has_breadcrumbs': bool(soup.find('nav', attrs={'aria-label': 'breadcrumb'}) or soup.find(class_=lambda x: x and 'breadcrumb' in x.lower())),
            'has_search': bool(soup.find('form', attrs={'role': 'search'})) or bool(soup.find('input', attrs={'type': 'search'})),
            'has_sitemap': bool(soup.find('a', href=lambda x: x and 'sitemap' in x.lower())),
            'mobile_nav': bool(soup.find(class_=lambda x: x and any(term in x.lower() for term in ['mobile-nav', 'navbar-toggle', 'menu-toggle'])))
        }

    def _analyze_accessibility(self, soup: BeautifulSoup) -> Dict:
        """Analyze accessibility implementation."""
        return {
            'aria_landmarks': bool(soup.find_all(attrs={'role': True})),
            'image_alts': len(soup.find_all('img', alt=True)) / max(len(soup.find_all('img')), 1),
            'skip_links': bool(soup.find('a', href='#main-content')),
            'form_labels': all(label.get('for') for label in soup.find_all('label')),
            'color_contrast': bool(soup.find_all(style=lambda x: x and ('color' in x or 'background' in x))),
            'keyboard_nav': bool(soup.find_all(tabindex=True))
        }

    def _analyze_interaction_elements(self, soup: BeautifulSoup) -> Dict:
        """Analyze interactive elements and their implementation."""
        return {
            'forms': self._analyze_forms(soup),
            'buttons': self._analyze_buttons(soup),
            'modals': bool(soup.find_all(class_=lambda x: x and 'modal' in x.lower())),
            'tooltips': bool(soup.find_all(attrs={'title': True})) or bool(soup.find_all(attrs={'data-tooltip': True})),
            'scroll_behavior': bool(soup.find_all(attrs={'data-scroll': True})) or bool(soup.find_all(class_=lambda x: x and 'scroll' in x.lower()))
        }

    def _analyze_forms(self, soup: BeautifulSoup) -> Dict:
        """Analyze form implementation and usability."""
        forms = soup.find_all('form')
        return {
            'has_validation': bool(soup.find_all('input', attrs={'required': True})),
            'has_autocomplete': bool(soup.find_all('input', attrs={'autocomplete': True})),
            'has_placeholders': bool(soup.find_all('input', attrs={'placeholder': True})),
            'has_error_handling': bool(soup.find_all(class_=lambda x: x and 'error' in x.lower())),
            'has_success_feedback': bool(soup.find_all(class_=lambda x: x and 'success' in x.lower()))
        }

    def _analyze_buttons(self, soup: BeautifulSoup) -> Dict:
        """Analyze button implementation and accessibility."""
        buttons = soup.find_all(['button', 'a', 'input'])
        return {
            'has_clear_labels': all(btn.string or btn.get('aria-label') for btn in buttons if btn.name == 'button'),
            'has_hover_states': bool(soup.find_all(style=lambda x: x and ':hover' in x if x else False)),
            'has_focus_states': bool(soup.find_all(style=lambda x: x and ':focus' in x if x else False))
        }

    def _analyze_content_layout(self, soup: BeautifulSoup) -> Dict:
        """Analyze content layout and structure."""
        return {
            'has_grid_system': bool(soup.find_all(class_=lambda x: x and ('grid' in x.lower() or 'row' in x.lower()))),
            'has_responsive_images': bool(soup.find_all('img', srcset=True)),
            'has_whitespace': bool(soup.find_all(style=lambda x: x and ('margin' in x or 'padding' in x))),
            'has_typography_hierarchy': bool(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
        }

    def _analyze_content_clusters(self, soup: BeautifulSoup) -> Dict:
        """Analyze content relationships and topic clusters."""
        return {
            'topic_hierarchy': self._analyze_topic_hierarchy(soup),
            'related_content': self._analyze_related_content(soup),
            'content_tags': self._extract_content_tags(soup),
            'semantic_structure': self._analyze_semantic_structure(soup)
        }

    def _analyze_topic_hierarchy(self, soup: BeautifulSoup) -> Dict:
        """Analyze topic hierarchy and structure."""
        headings = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}
        return {
            'heading_structure': headings,
            'has_proper_hierarchy': headings['h1'] <= 1 and all(headings[f'h{i}'] >= headings[f'h{i+1}'] for i in range(1, 5)),
            'section_count': len(soup.find_all('section')),
            'article_count': len(soup.find_all('article'))
        }

    def _analyze_related_content(self, soup: BeautifulSoup) -> Dict:
        """Analyze related content implementation."""
        return {
            'has_related_posts': bool(soup.find_all(class_=lambda x: x and 'related' in x.lower())),
            'has_categories': bool(soup.find_all(class_=lambda x: x and 'category' in x.lower())),
            'has_tags': bool(soup.find_all(class_=lambda x: x and 'tag' in x.lower())),
            'has_author_info': bool(soup.find_all(class_=lambda x: x and 'author' in x.lower()))
        }

    def _extract_content_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract content categorization tags."""
        tags = []
        for tag in soup.find_all(['a', 'span', 'div'], class_=lambda x: x and 'tag' in x.lower()):
            if tag.string:
                tags.append(tag.string.strip())
        return list(set(tags))

    def _analyze_semantic_structure(self, soup: BeautifulSoup) -> Dict:
        """Analyze semantic HTML structure."""
        return {
            'has_article': bool(soup.find('article')),
            'has_aside': bool(soup.find('aside')),
            'has_main': bool(soup.find('main')),
            'has_header': bool(soup.find('header')),
            'has_footer': bool(soup.find('footer')),
            'has_nav': bool(soup.find('nav')),
            'has_section': bool(soup.find('section'))
        }

    def _analyze_link_architecture(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Analyze internal linking structure."""
        links = soup.find_all('a', href=True)
        internal_links = [link for link in links if self._is_internal_link(link['href'], base_url)]
        
        return {
            'internal_link_count': len(internal_links),
            'link_depth': self._analyze_link_depth(internal_links),
            'link_distribution': self._analyze_link_distribution(internal_links),
            'anchor_text_quality': self._analyze_anchor_text(internal_links)
        }

    def _is_internal_link(self, href: str, base_url: str) -> bool:
        """Check if a link is internal."""
        if href.startswith('#') or href.startswith('javascript:'):
            return False
        try:
            url = urljoin(base_url, href)
            return urlparse(url).netloc == urlparse(base_url).netloc
        except:
            return False

    def _analyze_link_depth(self, links: List) -> Dict:
        """Analyze link depth and hierarchy."""
        depths = [len(link['href'].strip('/').split('/')) for link in links if not link['href'].startswith('#')]
        return {
            'max_depth': max(depths) if depths else 0,
            'avg_depth': sum(depths) / len(depths) if depths else 0,
            'depth_distribution': {i: depths.count(i) for i in range(1, max(depths) + 1)} if depths else {}
        }

    def _analyze_link_distribution(self, links: List) -> Dict:
        """Analyze link distribution in content."""
        return {
            'navigation_links': len([link for link in links if self._is_nav_link(link)]),
            'content_links': len([link for link in links if self._is_content_link(link)]),
            'footer_links': len([link for link in links if self._is_footer_link(link)])
        }

    def _is_nav_link(self, link) -> bool:
        """Check if link is in navigation."""
        return bool(link.find_parent(['nav', 'header']))

    def _is_content_link(self, link) -> bool:
        """Check if link is in main content."""
        return bool(link.find_parent(['article', 'main', 'section']))

    def _is_footer_link(self, link) -> bool:
        """Check if link is in footer."""
        return bool(link.find_parent('footer'))

    def _analyze_anchor_text(self, links: List) -> Dict:
        """Analyze anchor text quality."""
        anchor_texts = [link.string.strip() if link.string else '' for link in links]
        return {
            'descriptive_count': len([text for text in anchor_texts if len(text) > 5 and text.lower() not in ['click here', 'read more']]),
            'generic_count': len([text for text in anchor_texts if text.lower() in ['click here', 'read more', 'learn more']]),
            'empty_count': len([text for text in anchor_texts if not text])
        }

    def _analyze_rich_results(self, soup: BeautifulSoup) -> Dict:
        """Analyze rich results potential."""
        return {
            'schema_types': self._analyze_schema_types(soup),
            'rich_snippets': self._analyze_rich_snippets(soup),
            'meta_enhancements': self._analyze_meta_enhancements(soup)
        }

    def _analyze_schema_types(self, soup: BeautifulSoup) -> List[str]:
        """Analyze implemented schema types."""
        schema_types = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = script.string.strip()
                if '"@type"' in data:
                    schema_type = re.search(r'"@type"\s*:\s*"([^"]+)"', data)
                    if schema_type:
                        schema_types.append(schema_type.group(1))
            except:
                continue
        return list(set(schema_types))

    def _analyze_rich_snippets(self, soup: BeautifulSoup) -> Dict:
        """Analyze rich snippet implementation."""
        return {
            'has_ratings': bool(soup.find_all(attrs={'itemprop': 'ratingValue'})),
            'has_reviews': bool(soup.find_all(attrs={'itemprop': 'review'})),
            'has_prices': bool(soup.find_all(attrs={'itemprop': 'price'})),
            'has_availability': bool(soup.find_all(attrs={'itemprop': 'availability'})),
            'has_breadcrumbs': bool(soup.find_all(attrs={'itemtype': 'http://schema.org/BreadcrumbList'}))
        }

    def _analyze_meta_enhancements(self, soup: BeautifulSoup) -> Dict:
        """Analyze meta tag enhancements."""
        return {
            'has_article_meta': bool(soup.find_all('meta', property=lambda x: x and x.startswith('article:'))),
            'has_product_meta': bool(soup.find_all('meta', property=lambda x: x and x.startswith('product:'))),
            'has_video_meta': bool(soup.find_all('meta', property=lambda x: x and x.startswith('video:'))),
            'has_geo_meta': bool(soup.find_all('meta', property=lambda x: x and x.startswith('geo:')))
        }

    def _analyze_progressive_features(self, soup: BeautifulSoup) -> Dict:
        """Analyze progressive enhancement features."""
        return {
            'offline_support': self._analyze_offline_support(soup),
            'performance_features': self._analyze_performance_features(soup),
            'enhancement_layers': self._analyze_enhancement_layers(soup)
        }

    def _analyze_offline_support(self, soup: BeautifulSoup) -> Dict:
        """Analyze offline support implementation."""
        return {
            'has_service_worker': bool(soup.find('script', string=lambda x: x and 'serviceWorker' in x if x else False)),
            'has_manifest': bool(soup.find('link', rel='manifest')),
            'has_cache_control': bool(soup.find('meta', attrs={'http-equiv': 'Cache-Control'})),
            'has_offline_page': bool(soup.find('link', rel='offline'))
        }

    def _analyze_performance_features(self, soup: BeautifulSoup) -> Dict:
        """Analyze performance optimization features."""
        return {
            'resource_hints': bool(soup.find_all('link', rel=lambda x: x and x in ['preload', 'prefetch', 'preconnect'])),
            'image_optimization': bool(soup.find_all('img', srcset=True)) or bool(soup.find_all('picture')),
            'async_resources': bool(soup.find_all('script', attrs={'async': True})),
            'defer_resources': bool(soup.find_all('script', attrs={'defer': True}))
        }

    def _analyze_enhancement_layers(self, soup: BeautifulSoup) -> Dict:
        """Analyze progressive enhancement layers."""
        return {
            'has_base_html': bool(soup.find('html')),
            'has_enhanced_styles': bool(soup.find_all('link', attrs={'media': True})),
            'has_js_enhancement': bool(soup.find('script')),
            'has_fallbacks': bool(soup.find('noscript'))
        }

    def _evaluate_advanced_seo(self, analysis: Dict) -> Dict:
        """Evaluate advanced SEO features and generate recommendations."""
        evaluation = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }
        
        # Evaluate user experience
        if 'user_experience' in analysis:
            ux = analysis['user_experience']
            
            # Navigation evaluation
            nav = ux.get('navigation', {})
            if nav.get('has_main_nav') and nav.get('has_breadcrumbs'):
                evaluation['strengths'].append("Strong navigation structure implemented")
            else:
                evaluation['weaknesses'].append("Navigation structure needs improvement")
                evaluation['recommendations'].append("Implement clear navigation hierarchy with breadcrumbs")
            
            # Accessibility evaluation
            acc = ux.get('accessibility', {})
            if acc.get('aria_landmarks') and acc.get('image_alts', 0) > 0.9:
                evaluation['strengths'].append("Good accessibility implementation")
            else:
                evaluation['weaknesses'].append("Accessibility needs improvement")
                evaluation['recommendations'].append("Enhance accessibility with ARIA landmarks and image alts")
        
        # Evaluate content clusters
        if 'content_clusters' in analysis:
            clusters = analysis['content_clusters']
            
            # Topic hierarchy evaluation
            hierarchy = clusters.get('topic_hierarchy', {})
            if hierarchy.get('has_proper_hierarchy'):
                evaluation['strengths'].append("Well-structured content hierarchy")
            else:
                evaluation['weaknesses'].append("Content hierarchy needs improvement")
                evaluation['recommendations'].append("Implement proper heading hierarchy (H1 > H2 > H3)")
        
        # Evaluate rich results
        if 'rich_results' in analysis:
            rich = analysis['rich_results']
            
            # Schema implementation evaluation
            if rich.get('schema_types'):
                evaluation['strengths'].append("Implemented structured data markup")
            else:
                evaluation['weaknesses'].append("Missing structured data markup")
                evaluation['recommendations'].append("Add relevant Schema.org markup for rich results")
        
        # Add educational tips
        evaluation['education_tips'] = [
            "Progressive enhancement ensures functionality across all devices",
            "Semantic HTML improves accessibility and SEO",
            "Rich results increase visibility in search results",
            "Content clustering helps establish topic authority"
        ]
        
        return evaluation 