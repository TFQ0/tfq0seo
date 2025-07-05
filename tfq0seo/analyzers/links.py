"""
Link analyzer for internal/external links and broken links
"""
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

class LinkAnalyzer:
    """Analyzer for link structure and quality"""
    
    def __init__(self, config):
        self.config = config
    
    def analyze(self, page_data: Dict, soup: Optional[BeautifulSoup]) -> Dict[str, Any]:
        """Analyze links on the page"""
        if not soup:
            return {
                'issues': [{
                    'type': 'no_content',
                    'severity': 'critical',
                    'message': 'No content to analyze links'
                }]
            }
        
        issues = []
        
        # Get all links from page data
        links_data = page_data.get('links', [])
        
        # Analyze link structure
        link_analysis = self._analyze_link_structure(links_data, page_data['url'])
        
        # Check for broken links (based on crawl data)
        broken_links = self._identify_broken_links(links_data, page_data)
        if broken_links:
            issues.append({
                'type': 'broken_links',
                'severity': 'critical',
                'message': f'{len(broken_links)} broken links found'
            })
        
        # Analyze anchor text
        anchor_analysis = self._analyze_anchor_text(links_data)
        issues.extend(anchor_analysis['issues'])
        
        # Check for link attributes
        link_attributes = self._analyze_link_attributes(soup)
        issues.extend(link_attributes['issues'])
        
        # Check internal link structure
        if link_analysis['internal_count'] < 3:
            issues.append({
                'type': 'few_internal_links',
                'severity': 'warning',
                'message': 'Page has very few internal links'
            })
        
        # Check for excessive external links
        if link_analysis['external_count'] > link_analysis['internal_count'] * 2:
            issues.append({
                'type': 'too_many_external_links',
                'severity': 'notice',
                'message': 'More external links than internal links'
            })
        
        return {
            'total_links': link_analysis['total_count'],
            'internal_links': link_analysis['internal_count'],
            'external_links': link_analysis['external_count'],
            'unique_links': link_analysis['unique_count'],
            'broken_links': len(broken_links),
            'nofollow_links': link_attributes['nofollow_count'],
            'link_details': {
                'internal': link_analysis['internal_links'][:10],  # Top 10
                'external': link_analysis['external_links'][:10],  # Top 10
                'broken': broken_links[:10]  # Top 10
            },
            'anchor_text_analysis': anchor_analysis['summary'],
            'issues': issues
        }
    
    def _analyze_link_structure(self, links_data: List[Dict], current_url: str) -> Dict[str, Any]:
        """Analyze link structure and categorize links"""
        current_domain = urlparse(current_url).netloc
        
        internal_links = []
        external_links = []
        unique_urls = set()
        
        for link in links_data:
            url = link.get('url', '')
            if not url:
                continue
            
            parsed = urlparse(url)
            unique_urls.add(url)
            
            if parsed.netloc == current_domain or not parsed.netloc:
                internal_links.append({
                    'url': url,
                    'text': link.get('text', ''),
                    'tag': link.get('tag', 'a')
                })
            else:
                external_links.append({
                    'url': url,
                    'text': link.get('text', ''),
                    'tag': link.get('tag', 'a'),
                    'domain': parsed.netloc
                })
        
        return {
            'total_count': len(links_data),
            'internal_count': len(internal_links),
            'external_count': len(external_links),
            'unique_count': len(unique_urls),
            'internal_links': internal_links,
            'external_links': external_links
        }
    
    def _identify_broken_links(self, links_data: List[Dict], page_data: Dict) -> List[Dict]:
        """Identify potentially broken links"""
        broken_links = []
        
        # For now, we can't check actual HTTP status without making requests
        # This would need to be done during crawling
        # Here we can check for obvious issues
        
        for link in links_data:
            url = link.get('url', '')
            
            # Check for obviously broken patterns
            if any(pattern in url for pattern in ['404', 'error', 'not-found']):
                broken_links.append({
                    'url': url,
                    'text': link.get('text', ''),
                    'reason': 'URL contains error pattern'
                })
        
        return broken_links
    
    def _analyze_anchor_text(self, links_data: List[Dict]) -> Dict[str, Any]:
        """Analyze anchor text quality"""
        issues = []
        
        generic_anchors = ['click here', 'here', 'read more', 'more', 'link', 'this']
        empty_anchors = 0
        generic_count = 0
        
        anchor_texts = []
        
        for link in links_data:
            text = link.get('text', '').strip().lower()
            anchor_texts.append(text)
            
            if not text:
                empty_anchors += 1
            elif text in generic_anchors:
                generic_count += 1
        
        if empty_anchors > 0:
            issues.append({
                'type': 'empty_anchor_text',
                'severity': 'warning',
                'message': f'{empty_anchors} links with empty anchor text'
            })
        
        if generic_count > 3:
            issues.append({
                'type': 'generic_anchor_text',
                'severity': 'notice',
                'message': f'{generic_count} links with generic anchor text'
            })
        
        return {
            'summary': {
                'total_anchors': len(anchor_texts),
                'empty_anchors': empty_anchors,
                'generic_anchors': generic_count,
                'unique_anchors': len(set(anchor_texts))
            },
            'issues': issues
        }
    
    def _analyze_link_attributes(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze link attributes like nofollow, target, etc."""
        issues = []
        
        all_links = soup.find_all('a', href=True)
        
        nofollow_count = 0
        target_blank_count = 0
        missing_rel_opener = 0
        
        for link in all_links:
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = [rel]
            
            if 'nofollow' in rel:
                nofollow_count += 1
            
            target = link.get('target', '')
            if target == '_blank':
                target_blank_count += 1
                
                # Check for security issue
                if 'noopener' not in rel and 'noreferrer' not in rel:
                    missing_rel_opener += 1
        
        if missing_rel_opener > 0:
            issues.append({
                'type': 'security_target_blank',
                'severity': 'warning',
                'message': f'{missing_rel_opener} links with target="_blank" missing rel="noopener"'
            })
        
        return {
            'nofollow_count': nofollow_count,
            'target_blank_count': target_blank_count,
            'issues': issues
        } 