"""
Content analyzer for text analysis and readability
"""
from typing import Dict, List, Optional, Any, Set, Tuple
from bs4 import BeautifulSoup, NavigableString, Comment
import textstat
import re
from collections import Counter
import html
import unicodedata
import logging
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
import nltk

logger = logging.getLogger(__name__)

# Download required NLTK data if not present
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords', quiet=True)
    except:
        logger.warning("Could not download NLTK stopwords")

class ContentAnalyzer:
    """Analyzer for content quality and readability"""
    
    def __init__(self, config):
        self.config = config
        self.stemmer = PorterStemmer()
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            # Fallback to basic stop words if NLTK data not available
            self.stop_words = {
                'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
                'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how'
            }
    
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
        
        # Extract text content with improved method
        text_data = self._extract_text_advanced(soup)
        text_content = text_data['main_content']
        all_text = text_data['all_text']
        
        # Basic metrics
        word_count = len(text_content.split())
        sentence_count = self._count_sentences(text_content)
        
        # Check content length
        if word_count < self.config.min_content_words:
            issues.append({
                'type': 'thin_content',
                'severity': 'warning',
                'message': f'Content too short ({word_count} words, recommended: {self.config.min_content_words}+)'
            })
        elif word_count > 5000:
            issues.append({
                'type': 'very_long_content',
                'severity': 'notice',
                'message': f'Very long content ({word_count} words) - consider breaking into multiple pages'
            })
        
        # Enhanced readability scores
        readability_data = self._calculate_readability_scores(text_content)
        
        if readability_data['flesch_score'] < self.config.min_readability_score and word_count > 50:
            issues.append({
                'type': 'poor_readability',
                'severity': 'warning',
                'message': f'Poor readability (Flesch: {readability_data["flesch_score"]:.1f}, recommended: {self.config.min_readability_score}+)'
            })
        
        # Analyze heading structure
        heading_data = self._analyze_headings(soup)
        issues.extend(heading_data['issues'])
        
        # Analyze images with enhanced checks
        image_data = self._analyze_images_enhanced(soup)
        issues.extend(image_data['issues'])
        
        # Semantic HTML analysis
        semantic_data = self._analyze_semantic_html(soup)
        issues.extend(semantic_data['issues'])
        
        # Keyword analysis with stemming and variations
        keyword_data = {}
        if self.config.target_keyword:
            keyword_data = self._analyze_keyword_advanced(
                text_content, all_text, self.config.target_keyword, soup
            )
            issues.extend(keyword_data.get('issues', []))
        
        # Content structure and quality metrics
        structure_data = self._analyze_content_structure(soup, text_content)
        
        # Link analysis within content
        link_data = self._analyze_content_links(soup)
        issues.extend(link_data['issues'])
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'paragraph_count': structure_data['paragraph_count'],
            'list_count': structure_data['list_count'],
            'readability': readability_data,
            'heading_structure': heading_data['structure'],
            'images': image_data['summary'],
            'keyword_analysis': keyword_data,
            'semantic_html': semantic_data['summary'],
            'content_structure': structure_data,
            'internal_links': link_data['internal_count'],
            'external_links': link_data['external_count'],
            'content_preview': text_content[:200] + '...' if len(text_content) > 200 else text_content,
            'lexical_diversity': self._calculate_lexical_diversity(text_content),
            'estimated_reading_time': max(1, round(word_count / 200)),  # Minutes
            'issues': issues
        }
    
    def _extract_text_advanced(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract text content from HTML with improved handling"""
        # Clone soup to avoid modifying original
        soup_copy = BeautifulSoup(str(soup), 'html.parser')
        
        # Remove script, style, and other non-content elements
        for element in soup_copy(['script', 'style', 'noscript', 'iframe']):
            element.decompose()
        
        # Remove comments
        for comment in soup_copy.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Extract main content (try to identify article/main content area)
        main_content = ''
        content_areas = soup_copy.find_all(['main', 'article', 'div'], class_=re.compile(r'content|article|main|body', re.I))
        
        if content_areas:
            # Use the largest content area
            main_content = max(content_areas, key=lambda x: len(x.get_text())).get_text()
        else:
            # Fall back to body or full content
            body = soup_copy.find('body')
            main_content = body.get_text() if body else soup_copy.get_text()
        
        # Get all text for keyword analysis
        all_text = soup_copy.get_text()
        
        # Clean up text - handle HTML entities and Unicode
        main_content = html.unescape(main_content)
        all_text = html.unescape(all_text)
        
        # Normalize whitespace
        main_content = ' '.join(main_content.split())
        all_text = ' '.join(all_text.split())
        
        # Remove zero-width spaces and other invisible characters
        main_content = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', main_content)
        all_text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', all_text)
        
        return {
            'main_content': main_content,
            'all_text': all_text
        }
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences with improved accuracy"""
        if not text:
            return 0
        
        # Use textstat for base count
        count = textstat.sentence_count(text)
        
        # Additional validation for edge cases
        if count == 0 and len(text) > 20:
            # Fallback: count periods, exclamations, and questions
            count = len(re.findall(r'[.!?]+', text))
        
        return max(1, count)  # At least 1 sentence if there's text
    
    def _calculate_readability_scores(self, text: str) -> Dict[str, float]:
        """Calculate comprehensive readability scores"""
        if not text or len(text.split()) < 10:
            return {
                'flesch_score': 0,
                'gunning_fog_index': 0,
                'automated_readability_index': 0,
                'coleman_liau_index': 0
            }
        
        try:
            flesch = textstat.flesch_reading_ease(text)
            fog = textstat.gunning_fog(text)
            ari = textstat.automated_readability_index(text)
            coleman = textstat.coleman_liau_index(text)
        except:
            # Fallback for calculation errors
            flesch = fog = ari = coleman = 0
        
        return {
            'flesch_score': round(flesch, 1),
            'gunning_fog_index': round(fog, 1),
            'automated_readability_index': round(ari, 1),
            'coleman_liau_index': round(coleman, 1)
        }
    
    def _calculate_lexical_diversity(self, text: str) -> float:
        """Calculate lexical diversity (unique words / total words)"""
        if not text:
            return 0
        
        words = text.lower().split()
        if not words:
            return 0
        
        # Remove punctuation from words
        words = [re.sub(r'[^\w\s]', '', word) for word in words]
        words = [word for word in words if word]  # Remove empty strings
        
        unique_words = set(words)
        return round(len(unique_words) / len(words), 3) if words else 0
    
    def _analyze_headings(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze heading structure and hierarchy"""
        headings = {
            'h1': [],
            'h2': [],
            'h3': [],
            'h4': [],
            'h5': [],
            'h6': []
        }
        
        issues = []
        
        # Extract all headings
        for level in range(1, 7):
            tags = soup.find_all(f'h{level}')
            headings[f'h{level}'] = [tag.get_text(strip=True) for tag in tags]
        
        # Check heading hierarchy
        all_headings = []
        for tag in soup.find_all(re.compile(r'^h[1-6]$')):
            all_headings.append({
                'level': int(tag.name[1]),
                'text': tag.get_text(strip=True),
                'tag': tag
            })
        
        # Check for hierarchy issues
        prev_level = 0
        for i, heading in enumerate(all_headings):
            current_level = heading['level']
            
            # Check for skipped levels
            if current_level > prev_level + 1 and prev_level > 0:
                issues.append({
                    'type': 'heading_hierarchy_skip',
                    'severity': 'warning',
                    'message': f'Heading hierarchy skip: H{prev_level} to H{current_level} "{heading["text"][:50]}..."'
                })
            
            # Check for empty headings
            if not heading['text']:
                issues.append({
                    'type': 'empty_heading',
                    'severity': 'warning',
                    'message': f'Empty H{current_level} tag found'
                })
            
            prev_level = current_level
        
        # Check if H1 appears after H2
        h1_found = False
        h2_found = False
        for heading in all_headings:
            if heading['level'] == 2 and not h1_found:
                h2_found = True
            if heading['level'] == 1 and h2_found:
                issues.append({
                    'type': 'h1_after_h2',
                    'severity': 'warning',
                    'message': 'H1 appears after H2 - fix heading order'
                })
                break
        
        return {
            'structure': {
                'counts': {k: len(v) for k, v in headings.items()},
                'headings': headings,
                'total': len(all_headings)
            },
            'issues': issues
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
    
    def _analyze_images_enhanced(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze images for SEO optimization with enhanced checks"""
        images = soup.find_all('img')
        issues = []
        
        stats = {
            'missing_alt': 0,
            'empty_alt': 0,
            'long_alt': 0,
            'missing_dimensions': 0,
            'large_dimensions': 0,
            'non_descriptive_filename': 0,
            'missing_title': 0
        }
        
        image_details = []
        
        for img in images:
            img_data = {
                'src': img.get('src', ''),
                'alt': img.get('alt', None),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', ''),
                'loading': img.get('loading', '')
            }
            
            # Check alt text
            if img_data['alt'] is None:
                stats['missing_alt'] += 1
            elif not img_data['alt'].strip():
                stats['empty_alt'] += 1
            elif len(img_data['alt']) > 125:
                stats['long_alt'] += 1
            
            # Check title attribute
            if not img_data['title']:
                stats['missing_title'] += 1
            
            # Check dimensions
            if not img_data['width'] or not img_data['height']:
                stats['missing_dimensions'] += 1
            else:
                try:
                    w = int(img_data['width'])
                    h = int(img_data['height'])
                    if w > 1920 or h > 1080:
                        stats['large_dimensions'] += 1
                except:
                    pass
            
            # Check filename
            if img_data['src']:
                filename = img_data['src'].split('/')[-1].split('?')[0].lower()
                if re.match(r'^(img|image|photo|pic)[\d_-]*\.(jpg|jpeg|png|gif|webp)$', filename):
                    stats['non_descriptive_filename'] += 1
            
            image_details.append(img_data)
        
        # Generate issues based on stats
        if stats['missing_alt'] > 0:
            issues.append({
                'type': 'missing_alt_text',
                'severity': 'critical',
                'message': f'{stats["missing_alt"]} images missing alt text - critical for accessibility and SEO'
            })
        
        if stats['empty_alt'] > 0:
            issues.append({
                'type': 'empty_alt_text',
                'severity': 'warning',
                'message': f'{stats["empty_alt"]} images have empty alt text'
            })
        
        if stats['long_alt'] > 0:
            issues.append({
                'type': 'long_alt_text',
                'severity': 'notice',
                'message': f'{stats["long_alt"]} images have alt text > 125 characters'
            })
        
        if stats['missing_dimensions'] > 0:
            issues.append({
                'type': 'missing_image_dimensions',
                'severity': 'warning',
                'message': f'{stats["missing_dimensions"]} images missing width/height - can cause layout shift'
            })
        
        if stats['non_descriptive_filename'] > 0:
            issues.append({
                'type': 'non_descriptive_filenames',
                'severity': 'notice',
                'message': f'{stats["non_descriptive_filename"]} images have non-descriptive filenames'
            })
        
        # Check for lazy loading
        lazy_count = sum(1 for img in image_details if img['loading'] == 'lazy')
        if len(images) > 3 and lazy_count < len(images) - 3:  # First 3 images shouldn't be lazy
            issues.append({
                'type': 'missing_lazy_loading',
                'severity': 'notice',
                'message': f'Only {lazy_count}/{len(images)} images use lazy loading'
            })
        
        return {
            'summary': {
                'total': len(images),
                **stats,
                'lazy_loading': lazy_count
            },
            'issues': issues
        }
    
    def _analyze_semantic_html(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze semantic HTML5 usage"""
        issues = []
        
        # Check for semantic elements
        semantic_elements = {
            'header': soup.find_all('header'),
            'nav': soup.find_all('nav'),
            'main': soup.find_all('main'),
            'article': soup.find_all('article'),
            'section': soup.find_all('section'),
            'aside': soup.find_all('aside'),
            'footer': soup.find_all('footer'),
            'figure': soup.find_all('figure'),
            'figcaption': soup.find_all('figcaption'),
            'time': soup.find_all('time')
        }
        
        # Count usage
        usage_count = sum(len(elements) for elements in semantic_elements.values())
        
        # Check for common issues
        if not semantic_elements['main']:
            issues.append({
                'type': 'missing_main_element',
                'severity': 'warning',
                'message': 'No <main> element found - important for accessibility'
            })
        elif len(semantic_elements['main']) > 1:
            issues.append({
                'type': 'multiple_main_elements',
                'severity': 'warning',
                'message': 'Multiple <main> elements found - only one allowed per page'
            })
        
        if not semantic_elements['header']:
            issues.append({
                'type': 'missing_header_element',
                'severity': 'notice',
                'message': 'No <header> element found'
            })
        
        if not semantic_elements['nav']:
            issues.append({
                'type': 'missing_nav_element',
                'severity': 'notice',
                'message': 'No <nav> element found for navigation'
            })
        
        # Check for figures without figcaption
        figures_without_caption = 0
        for figure in semantic_elements['figure']:
            if not figure.find('figcaption'):
                figures_without_caption += 1
        
        if figures_without_caption > 0:
            issues.append({
                'type': 'figure_without_caption',
                'severity': 'notice',
                'message': f'{figures_without_caption} <figure> elements without <figcaption>'
            })
        
        # Check time elements for datetime attribute
        time_without_datetime = 0
        for time_elem in semantic_elements['time']:
            if not time_elem.get('datetime'):
                time_without_datetime += 1
        
        if time_without_datetime > 0:
            issues.append({
                'type': 'time_without_datetime',
                'severity': 'notice',
                'message': f'{time_without_datetime} <time> elements without datetime attribute'
            })
        
        return {
            'summary': {
                'total_semantic_elements': usage_count,
                'elements_used': {k: len(v) for k, v in semantic_elements.items()},
                'semantic_score': min(100, usage_count * 10)  # Simple scoring
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
    
    def _analyze_keyword_advanced(self, text: str, all_text: str, keyword: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Advanced keyword analysis with stemming and semantic variations"""
        if not text or not keyword:
            return {}
        
        issues = []
        
        # Basic keyword analysis
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        keyword_count = text_lower.count(keyword_lower)
        
        # Word counting
        words = re.findall(r'\b\w+\b', text_lower)
        word_count = len(words)
        
        # Calculate basic density
        density = (keyword_count / word_count * 100) if word_count > 0 else 0
        
        # Stemming analysis
        keyword_stem = self.stemmer.stem(keyword_lower)
        keyword_words = keyword_lower.split()
        keyword_stems = [self.stemmer.stem(word) for word in keyword_words]
        
        # Find variations
        variations = set()
        stem_matches = 0
        
        for word in words:
            word_stem = self.stemmer.stem(word)
            
            # Single keyword stemming
            if len(keyword_words) == 1 and word_stem == keyword_stem and word != keyword_lower:
                variations.add(word)
                stem_matches += 1
            
            # Multi-word keyword partial matches
            elif len(keyword_words) > 1:
                for kw_stem in keyword_stems:
                    if word_stem == kw_stem and word not in keyword_words:
                        variations.add(word)
                        stem_matches += 1
        
        # Calculate total occurrences including variations
        total_occurrences = keyword_count + stem_matches
        total_density = (total_occurrences / word_count * 100) if word_count > 0 else 0
        
        # Analyze keyword placement
        placement = self._analyze_keyword_placement(keyword_lower, soup)
        
        # Check for issues
        if total_density > self.config.max_keyword_density:
            issues.append({
                'type': 'keyword_stuffing',
                'severity': 'warning',
                'message': f'Keyword density too high ({total_density:.1f}% including variations, recommended: <{self.config.max_keyword_density}%)'
            })
        elif total_density < 0.5 and word_count > 100:
            issues.append({
                'type': 'low_keyword_density',
                'severity': 'notice',
                'message': f'Low keyword density ({total_density:.1f}%, recommended: 0.5-{self.config.max_keyword_density}%)'
            })
        
        # Check keyword placement
        if not placement['in_title']:
            issues.append({
                'type': 'keyword_not_in_title',
                'severity': 'warning',
                'message': 'Target keyword not found in title tag'
            })
        
        if not placement['in_h1']:
            issues.append({
                'type': 'keyword_not_in_h1',
                'severity': 'notice',
                'message': 'Target keyword not found in H1 tag'
            })
        
        if not placement['in_first_paragraph']:
            issues.append({
                'type': 'keyword_not_early',
                'severity': 'notice',
                'message': 'Target keyword not found in first paragraph'
            })
        
        # Find keyword positions
        positions = []
        start = 0
        while start < len(text_lower):
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        return {
            'keyword': keyword,
            'exact_count': keyword_count,
            'variation_count': stem_matches,
            'total_count': total_occurrences,
            'density': round(density, 2),
            'total_density': round(total_density, 2),
            'variations': list(variations)[:10],  # Top 10 variations
            'positions': positions[:10],  # First 10 positions
            'placement': placement,
            'word_count': word_count,
            'issues': issues
        }
    
    def _analyze_keyword_placement(self, keyword: str, soup: BeautifulSoup) -> Dict[str, bool]:
        """Analyze where keyword appears in important places"""
        placement = {
            'in_title': False,
            'in_meta_description': False,
            'in_h1': False,
            'in_h2': False,
            'in_first_paragraph': False,
            'in_url': False,
            'in_image_alt': False
        }
        
        # Check title
        title = soup.find('title')
        if title and keyword in title.get_text().lower():
            placement['in_title'] = True
        
        # Check meta description
        meta_desc = soup.find('meta', attrs={'name': re.compile(r'description', re.I)})
        if meta_desc and keyword in meta_desc.get('content', '').lower():
            placement['in_meta_description'] = True
        
        # Check H1
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            if keyword in h1.get_text().lower():
                placement['in_h1'] = True
                break
        
        # Check H2
        h2_tags = soup.find_all('h2')
        for h2 in h2_tags:
            if keyword in h2.get_text().lower():
                placement['in_h2'] = True
                break
        
        # Check first paragraph
        paragraphs = soup.find_all('p')
        if paragraphs and keyword in paragraphs[0].get_text().lower():
            placement['in_first_paragraph'] = True
        
        # Check image alt text
        images = soup.find_all('img', alt=True)
        for img in images:
            if keyword in img.get('alt', '').lower():
                placement['in_image_alt'] = True
                break
        
        return placement
    
    def _analyze_content_structure(self, soup: BeautifulSoup, text_content: str) -> Dict[str, Any]:
        """Analyze content structure and quality metrics"""
        # Count various elements
        paragraphs = soup.find_all('p')
        lists = soup.find_all(['ul', 'ol'])
        tables = soup.find_all('table')
        blockquotes = soup.find_all('blockquote')
        
        # Calculate paragraph metrics
        paragraph_lengths = [len(p.get_text().split()) for p in paragraphs]
        avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0
        
        # Check for content variety
        has_lists = len(lists) > 0
        has_images = len(soup.find_all('img')) > 0
        has_videos = len(soup.find_all(['video', 'iframe'])) > 0
        has_tables = len(tables) > 0
        
        # Content variety score
        variety_score = sum([has_lists, has_images, has_videos, has_tables]) * 25
        
        return {
            'paragraph_count': len(paragraphs),
            'list_count': len(lists),
            'table_count': len(tables),
            'blockquote_count': len(blockquotes),
            'avg_paragraph_length': round(avg_paragraph_length, 1),
            'content_variety_score': variety_score,
            'has_multimedia': has_images or has_videos
        }
    
    def _analyze_content_links(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze links within content"""
        issues = []
        
        # Find all links
        all_links = soup.find_all('a', href=True)
        
        # Separate content links from navigation
        content_links = []
        nav_elements = soup.find_all(['nav', 'header', 'footer'])
        nav_links = []
        
        for nav in nav_elements:
            nav_links.extend(nav.find_all('a', href=True))
        
        # Get content links (not in navigation)
        for link in all_links:
            if link not in nav_links:
                content_links.append(link)
        
        # Analyze content links
        internal_count = 0
        external_count = 0
        nofollow_count = 0
        broken_anchors = 0
        
        for link in content_links:
            href = link.get('href', '')
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = [rel]
            
            # Check if internal or external
            if href.startswith(('http://', 'https://')):
                external_count += 1
            elif href.startswith(('#', '/', './')):
                internal_count += 1
            
            # Check for nofollow
            if 'nofollow' in rel:
                nofollow_count += 1
            
            # Check for broken anchors
            if not link.get_text(strip=True):
                broken_anchors += 1
        
        # Generate issues
        if internal_count == 0 and len(content_links) > 0:
            issues.append({
                'type': 'no_internal_links',
                'severity': 'warning',
                'message': 'No internal links in content - missing opportunity for site navigation'
            })
        
        if external_count > internal_count * 2 and external_count > 5:
            issues.append({
                'type': 'too_many_external_links',
                'severity': 'notice',
                'message': f'High ratio of external links ({external_count} external vs {internal_count} internal)'
            })
        
        if broken_anchors > 0:
            issues.append({
                'type': 'empty_link_anchors',
                'severity': 'warning',
                'message': f'{broken_anchors} links with empty anchor text'
            })
        
        return {
            'internal_count': internal_count,
            'external_count': external_count,
            'nofollow_count': nofollow_count,
            'total_content_links': len(content_links),
            'issues': issues
        } 