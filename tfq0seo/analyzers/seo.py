"""
SEO meta tags analyzer
"""
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import re

class SEOAnalyzer:
    """Analyzer for SEO meta tags and structured data"""
    
    def __init__(self, config):
        self.config = config
    
    def analyze_meta_tags(self, soup: Optional[BeautifulSoup]) -> Dict[str, Any]:
        """Analyze meta tags and return issues"""
        if not soup:
            return {
                'issues': [{
                    'type': 'no_content',
                    'severity': 'critical',
                    'message': 'No HTML content to analyze'
                }]
            }
        
        issues = []
        
        # Title tag
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        if not title:
            issues.append({
                'type': 'missing_title',
                'severity': 'critical',
                'message': 'Missing title tag'
            })
        else:
            title_length = len(title)
            if title_length < self.config.title_min_length:
                issues.append({
                    'type': 'short_title',
                    'severity': 'warning',
                    'message': f'Title too short ({title_length} chars, recommended: {self.config.title_min_length}+)'
                })
            elif title_length > self.config.title_max_length:
                issues.append({
                    'type': 'long_title',
                    'severity': 'warning',
                    'message': f'Title too long ({title_length} chars, recommended: <{self.config.title_max_length})'
                })
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '').strip() if meta_desc else ''
        
        if not description:
            issues.append({
                'type': 'missing_description',
                'severity': 'critical',
                'message': 'Missing meta description'
            })
        else:
            desc_length = len(description)
            if desc_length < self.config.description_min_length:
                issues.append({
                    'type': 'short_description',
                    'severity': 'warning',
                    'message': f'Description too short ({desc_length} chars, recommended: {self.config.description_min_length}+)'
                })
            elif desc_length > self.config.description_max_length:
                issues.append({
                    'type': 'long_description',
                    'severity': 'warning',
                    'message': f'Description too long ({desc_length} chars, recommended: <{self.config.description_max_length})'
                })
        
        # Canonical URL
        canonical = soup.find('link', {'rel': 'canonical'})
        canonical_url = canonical.get('href', '') if canonical else ''
        
        # Meta robots
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        robots_content = meta_robots.get('content', '') if meta_robots else ''
        
        if 'noindex' in robots_content:
            issues.append({
                'type': 'noindex',
                'severity': 'warning',
                'message': 'Page has noindex directive'
            })
        
        # Open Graph tags
        og_tags = self._analyze_open_graph(soup)
        
        # Twitter Card tags  
        twitter_tags = self._analyze_twitter_cards(soup)
        
        # Structured data
        structured_data = self._analyze_structured_data(soup)
        
        # Viewport
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            issues.append({
                'type': 'missing_viewport',
                'severity': 'critical',
                'message': 'Missing viewport meta tag (mobile-friendliness issue)'
            })
        
        # H1 tags
        h1_tags = soup.find_all('h1')
        if not h1_tags:
            issues.append({
                'type': 'missing_h1',
                'severity': 'warning',
                'message': 'No H1 tag found'
            })
        elif len(h1_tags) > 1:
            issues.append({
                'type': 'multiple_h1',
                'severity': 'warning',
                'message': f'Multiple H1 tags found ({len(h1_tags)})'
            })
        
        return {
            'title': title,
            'title_length': len(title),
            'description': description,
            'description_length': len(description),
            'canonical_url': canonical_url,
            'robots': robots_content,
            'h1_count': len(h1_tags),
            'h1_text': [h1.get_text(strip=True) for h1 in h1_tags],
            'open_graph': og_tags,
            'twitter_card': twitter_tags,
            'structured_data': structured_data,
            'has_viewport': viewport is not None,
            'issues': issues
        }
    
    def _analyze_open_graph(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Analyze Open Graph meta tags"""
        og_tags = {}
        og_properties = ['title', 'description', 'image', 'url', 'type', 'site_name']
        
        for prop in og_properties:
            tag = soup.find('meta', property=f'og:{prop}')
            if tag:
                og_tags[prop] = tag.get('content', '')
        
        return og_tags
    
    def _analyze_twitter_cards(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Analyze Twitter Card meta tags"""
        twitter_tags = {}
        twitter_names = ['card', 'site', 'creator', 'title', 'description', 'image']
        
        for name in twitter_names:
            tag = soup.find('meta', attrs={'name': f'twitter:{name}'})
            if tag:
                twitter_tags[name] = tag.get('content', '')
        
        return twitter_tags
    
    def _analyze_structured_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Analyze JSON-LD structured data"""
        structured_data = []
        
        # Find all JSON-LD scripts
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                structured_data.append({
                    'type': data.get('@type', 'Unknown'),
                    'data': data
                })
            except:
                pass
        
        return structured_data 