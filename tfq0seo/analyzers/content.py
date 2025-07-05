"""
Content analyzer for text analysis and readability
"""
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import textstat
import re
from collections import Counter

class ContentAnalyzer:
    """Analyzer for content quality and readability"""
    
    def __init__(self, config):
        self.config = config
    
    def analyze(self, soup: Optional[BeautifulSoup], raw_html: str = '') -> Dict[str, Any]:
        """Analyze content quality and structure"""
        if not soup:
            return {
                'issues': [{
                    'type': 'no_content',
                    'severity': 'critical',
                    'message': 'No content to analyze'
                }]
            }
        
        issues = []
        
        # Extract text content
        text_content = self._extract_text(soup)
        
        # Basic metrics
        word_count = len(text_content.split())
        sentence_count = textstat.sentence_count(text_content)
        
        # Check content length
        if word_count < self.config.min_content_words:
            issues.append({
                'type': 'thin_content',
                'severity': 'warning',
                'message': f'Content too short ({word_count} words, recommended: {self.config.min_content_words}+)'
            })
        
        # Readability scores
        flesch_score = textstat.flesch_reading_ease(text_content) if text_content else 0
        gunning_fog = textstat.gunning_fog(text_content) if text_content else 0
        
        if flesch_score < self.config.min_readability_score and word_count > 50:
            issues.append({
                'type': 'poor_readability',
                'severity': 'warning',
                'message': f'Poor readability (Flesch: {flesch_score:.1f}, recommended: {self.config.min_readability_score}+)'
            })
        
        # Analyze heading structure
        heading_structure = self._analyze_headings(soup)
        
        # Analyze images
        image_analysis = self._analyze_images(soup)
        issues.extend(image_analysis['issues'])
        
        # Keyword density (if target keyword provided)
        keyword_analysis = {}
        if self.config.target_keyword:
            keyword_analysis = self._analyze_keyword_density(text_content, self.config.target_keyword)
            if keyword_analysis['density'] > self.config.max_keyword_density:
                issues.append({
                    'type': 'keyword_stuffing',
                    'severity': 'warning',
                    'message': f'Keyword density too high ({keyword_analysis["density"]:.1f}%, recommended: <{self.config.max_keyword_density}%)'
                })
        
        # Content structure
        paragraphs = soup.find_all('p')
        lists = soup.find_all(['ul', 'ol'])
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'paragraph_count': len(paragraphs),
            'list_count': len(lists),
            'readability_score': round(flesch_score, 1),
            'gunning_fog_index': round(gunning_fog, 1),
            'heading_structure': heading_structure,
            'images': image_analysis['summary'],
            'keyword_analysis': keyword_analysis,
            'content_preview': text_content[:200] + '...' if len(text_content) > 200 else text_content,
            'issues': issues
        }
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from HTML"""
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _analyze_headings(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze heading structure"""
        headings = {
            'h1': [],
            'h2': [],
            'h3': [],
            'h4': [],
            'h5': [],
            'h6': []
        }
        
        for level in range(1, 7):
            tags = soup.find_all(f'h{level}')
            headings[f'h{level}'] = [tag.get_text(strip=True) for tag in tags]
        
        # Check heading hierarchy
        hierarchy_issues = []
        
        # Check if H2 appears before H1
        h1_tags = soup.find_all('h1')
        h2_tags = soup.find_all('h2')
        
        if h2_tags and h1_tags:
            first_h2_pos = str(soup).find(str(h2_tags[0]))
            first_h1_pos = str(soup).find(str(h1_tags[0]))
            
            if first_h2_pos < first_h1_pos:
                hierarchy_issues.append('H2 appears before H1')
        
        return {
            'counts': {k: len(v) for k, v in headings.items()},
            'headings': headings,
            'hierarchy_issues': hierarchy_issues
        }
    
    def _analyze_images(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze images for SEO optimization"""
        images = soup.find_all('img')
        issues = []
        
        missing_alt = 0
        empty_alt = 0
        large_images = 0
        
        for img in images:
            # Check alt text
            alt = img.get('alt', None)
            if alt is None:
                missing_alt += 1
            elif not alt.strip():
                empty_alt += 1
            
            # Check file size (if width/height attributes present)
            width = img.get('width')
            height = img.get('height')
            
            if width and height:
                try:
                    w = int(width)
                    h = int(height)
                    if w > 1920 or h > 1080:
                        large_images += 1
                except:
                    pass
        
        if missing_alt > 0:
            issues.append({
                'type': 'missing_alt_text',
                'severity': 'warning',
                'message': f'{missing_alt} images missing alt text'
            })
        
        if empty_alt > 0:
            issues.append({
                'type': 'empty_alt_text',
                'severity': 'notice',
                'message': f'{empty_alt} images have empty alt text'
            })
        
        return {
            'summary': {
                'total': len(images),
                'missing_alt': missing_alt,
                'empty_alt': empty_alt,
                'large_images': large_images
            },
            'issues': issues
        }
    
    def _analyze_keyword_density(self, text: str, keyword: str) -> Dict[str, Any]:
        """Analyze keyword density in content"""
        if not text or not keyword:
            return {}
        
        # Convert to lowercase for analysis
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Count occurrences
        keyword_count = text_lower.count(keyword_lower)
        word_count = len(text.split())
        
        # Calculate density
        density = (keyword_count / word_count * 100) if word_count > 0 else 0
        
        # Find keyword positions
        positions = []
        start = 0
        while True:
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        return {
            'keyword': keyword,
            'count': keyword_count,
            'density': round(density, 2),
            'positions': positions[:10],  # First 10 positions
            'word_count': word_count
        } 