from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass
from ..utils.error_handler import handle_analysis_error
import json

@dataclass
class MetaAnalysis:
    """tfq0seo meta tag analysis data structure.
    
    Stores comprehensive analysis results for:
    - Basic meta tags (title, description)
    - Technical tags (robots, viewport)
    - Canonical URLs
    - Social media tags (Open Graph, Twitter Cards)
    - Structured data markup
    - Site identity (favicon, language)
    """
    title: Optional[str]
    description: Optional[str]
    robots: Optional[str]
    viewport: Optional[str]
    canonical: Optional[str]
    og_tags: Dict[str, str]
    twitter_cards: Dict[str, str]
    schema_markup: List[Dict]
    favicon: Optional[str]
    lang: Optional[str]

class MetaAnalyzer:
    """tfq0seo Meta Tag Analyzer - Analyzes meta tags and SEO-critical HTML elements"""
    def __init__(self, config: dict):
        self.config = config
        self.thresholds = config['seo_thresholds']

    @handle_analysis_error
    def analyze(self, soup: BeautifulSoup) -> Dict:
        """Perform comprehensive tfq0seo meta tag analysis.
        
        Analyzes all critical SEO elements including:
        - Title and meta description optimization
        - Technical SEO elements
        - Social media optimization
        - Structured data implementation
        - Internationalization settings
        """
        analysis = MetaAnalysis(
            title=self._get_title(soup),
            description=self._get_meta_content(soup, 'description'),
            robots=self._get_meta_content(soup, 'robots'),
            viewport=self._get_meta_content(soup, 'viewport'),
            canonical=self._get_canonical(soup),
            og_tags=self._get_og_tags(soup),
            twitter_cards=self._get_twitter_cards(soup),
            schema_markup=self._get_schema_markup(soup),
            favicon=self._get_favicon(soup),
            lang=self._get_language(soup)
        )
        
        return self._evaluate_meta_tags(analysis)

    def _get_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract and validate page title for tfq0seo compliance"""
        title_tag = soup.title
        return title_tag.string.strip() if title_tag else None

    def _get_meta_content(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        """Extract meta tag content for tfq0seo analysis"""
        meta_tag = soup.find('meta', attrs={'name': name})
        return meta_tag.get('content') if meta_tag else None

    def _get_canonical(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract canonical URL for duplicate content analysis"""
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        return canonical.get('href') if canonical else None

    def _get_og_tags(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract Open Graph tags for social media optimization"""
        og_tags = {}
        for tag in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
            og_tags[tag['property']] = tag.get('content', '')
        return og_tags

    def _get_twitter_cards(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract Twitter Card tags for social media optimization"""
        twitter_cards = {}
        for tag in soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
            twitter_cards[tag['name']] = tag.get('content', '')
        return twitter_cards

    def _get_schema_markup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract Schema.org markup for tfq0seo structured data analysis"""
        schema_tags = soup.find_all('script', type='application/ld+json')
        schema_data = []
        for tag in schema_tags:
            try:
                schema_data.append(json.loads(tag.string))
            except (json.JSONDecodeError, AttributeError):
                continue
        return schema_data

    def _get_favicon(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract favicon URL for tfq0seo brand identity analysis"""
        favicon = soup.find('link', attrs={'rel': lambda x: x and 'icon' in x.lower()})
        return favicon.get('href') if favicon else None

    def _get_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract document language for tfq0seo internationalization analysis"""
        html_tag = soup.find('html')
        return html_tag.get('lang') if html_tag else None

    def _evaluate_meta_tags(self, analysis: MetaAnalysis) -> Dict:
        """Evaluate meta tags and generate tfq0seo recommendations.
        
        Performs comprehensive analysis of:
        - Title and meta description optimization
        - Technical SEO elements
        - Social media optimization
        - Structured data implementation
        - Internationalization settings
        
        Returns:
            Dict containing:
            - strengths: List of identified SEO strengths
            - weaknesses: List of SEO issues found
            - recommendations: List of actionable improvements
            - education_tips: List of SEO best practices
        """
        evaluation = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }

        # Title evaluation
        if analysis.title:
            title_length = len(analysis.title)
            if self.thresholds['title_length']['min'] <= title_length <= self.thresholds['title_length']['max']:
                evaluation['strengths'].append("Title tag length is optimal")
            else:
                evaluation['weaknesses'].append(
                    f"Title length ({title_length} chars) is "
                    f"{'too short' if title_length < self.thresholds['title_length']['min'] else 'too long'}"
                )
                evaluation['recommendations'].append(
                    f"Adjust title length to between {self.thresholds['title_length']['min']}-"
                    f"{self.thresholds['title_length']['max']} characters"
                )
                evaluation['education_tips'].append(
                    "Title tags are crucial for SEO and user experience - they should be descriptive yet concise"
                )

        # Meta description evaluation
        if analysis.description:
            desc_length = len(analysis.description)
            if self.thresholds['meta_description_length']['min'] <= desc_length <= self.thresholds['meta_description_length']['max']:
                evaluation['strengths'].append("Meta description length is optimal")
            else:
                evaluation['weaknesses'].append(
                    f"Meta description length ({desc_length} chars) is "
                    f"{'too short' if desc_length < self.thresholds['meta_description_length']['min'] else 'too long'}"
                )
                evaluation['recommendations'].append(
                    f"Adjust meta description length to between {self.thresholds['meta_description_length']['min']}-"
                    f"{self.thresholds['meta_description_length']['max']} characters"
                )
        else:
            evaluation['weaknesses'].append("Missing meta description")
            evaluation['recommendations'].append("Add a meta description tag")
            evaluation['education_tips'].append(
                "Meta descriptions improve click-through rates from search results"
            )

        # Canonical URL evaluation
        if not analysis.canonical:
            evaluation['weaknesses'].append("Missing canonical URL")
            evaluation['recommendations'].append("Add a canonical URL tag")
            evaluation['education_tips'].append(
                "Canonical URLs help prevent duplicate content issues"
            )

        # Open Graph and Twitter Card evaluation
        if not analysis.og_tags:
            evaluation['weaknesses'].append("Missing Open Graph tags")
            evaluation['recommendations'].append("Add Open Graph tags for better social media sharing")
            evaluation['education_tips'].append(
                "Open Graph tags control how your content appears when shared on social media"
            )

        if not analysis.twitter_cards:
            evaluation['weaknesses'].append("Missing Twitter Card tags")
            evaluation['recommendations'].append("Add Twitter Card tags for better Twitter sharing")

        # Schema markup evaluation
        if not analysis.schema_markup:
            evaluation['weaknesses'].append("Missing Schema.org markup")
            evaluation['recommendations'].append("Add relevant Schema.org markup")
            evaluation['education_tips'].append(
                "Schema.org markup helps search engines better understand your content"
            )

        # Language declaration evaluation
        if not analysis.lang:
            evaluation['weaknesses'].append("Missing language declaration")
            evaluation['recommendations'].append("Add lang attribute to the HTML tag")
            evaluation['education_tips'].append(
                "Language declaration helps search engines serve content to the right audience"
            )

        return evaluation 