"""
SEO meta tags analyzer - Optimized
"""
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup, Tag
import re
import json
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Simple issue creation - fast and lightweight
def create_issue(issue_type: str, severity: str = 'warning', message: str = '', **kwargs) -> Dict:
    """Create a simple issue dictionary"""
    issue = {
        'type': issue_type,
        'severity': severity,
        'message': message or issue_type.replace('_', ' ').title()
    }
    issue.update(kwargs)
    return issue

class SEOAnalyzer:
    """Analyzer for SEO meta tags and structured data"""
    
    # Approximate character widths for common fonts (in pixels)
    CHAR_WIDTHS = {
        'narrow': 5,    # i, l, f, t, r
        'medium': 7,    # a, c, e, n, o, s, u, v, x, z
        'wide': 9,      # m, w
        'upper': 8,     # Most uppercase letters
        'space': 3,
        'number': 7,
        'special': 6    # Default for other characters
    }
    
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
        
        # Title tag analysis
        title_data = self._analyze_title_tag(soup)
        title = title_data['title']
        issues.extend(title_data['issues'])
        
        # Meta description analysis
        desc_data = self._analyze_meta_description(soup)
        description = desc_data['description']
        issues.extend(desc_data['issues'])
        
        # Meta keywords (less important but still tracked)
        keywords = self._extract_meta_keywords(soup)
        
        # Canonical URL
        canonical_data = self._analyze_canonical(soup)
        canonical_url = canonical_data['url']
        issues.extend(canonical_data['issues'])
        
        # Meta robots
        robots_data = self._analyze_robots_meta(soup)
        robots_content = robots_data['content']
        issues.extend(robots_data['issues'])
        
        # Language and charset
        lang_data = self._analyze_language(soup)
        issues.extend(lang_data['issues'])
        
        # Open Graph tags
        og_data = self._analyze_open_graph(soup)
        issues.extend(og_data['issues'])
        
        # Twitter Card tags  
        twitter_data = self._analyze_twitter_cards(soup)
        issues.extend(twitter_data['issues'])
        
        # Structured data
        structured_data = self._analyze_structured_data(soup)
        issues.extend(structured_data['issues'])
        
        # Viewport
        viewport_data = self._analyze_viewport(soup)
        issues.extend(viewport_data['issues'])
        
        # H1 tags
        h1_data = self._analyze_h1_tags(soup)
        issues.extend(h1_data['issues'])
        
        # Hreflang tags
        hreflang_data = self._analyze_hreflang(soup)
        issues.extend(hreflang_data['issues'])
        
        # Alternative versions
        alternate_data = self._analyze_alternates(soup)
        
        return {
            'title': title,
            'title_length': len(title),
            'title_pixel_width': self._calculate_pixel_width(title),
            'description': description,
            'description_length': len(description),
            'description_pixel_width': self._calculate_pixel_width(description),
            'keywords': keywords,
            'canonical_url': canonical_url,
            'robots': robots_content,
            'language': lang_data['language'],
            'charset': lang_data['charset'],
            'h1_count': h1_data['count'],
            'h1_text': h1_data['texts'],
            'open_graph': og_data['tags'],
            'twitter_card': twitter_data['tags'],
            'structured_data': structured_data['data'],
            'has_viewport': viewport_data['has_viewport'],
            'viewport_content': viewport_data['content'],
            'hreflang': hreflang_data['tags'],
            'alternates': alternate_data,
            'duplicate_meta_descriptions': desc_data.get('duplicates', 0),
            'issues': issues
        }
    
    def _analyze_title_tag(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze title tag(s)"""
        issues = []
        title_tags = soup.find_all('title')
        
        if not title_tags:
            issues.append(create_issue('missing_title', 'critical', 'Page is missing a title tag'))
            return {'title': '', 'issues': issues}
        
        if len(title_tags) > 1:
            issues.append(create_issue('multiple_titles', 'warning', f'Page has {len(title_tags)} title tags'))
        
        # Get first title tag
        title = title_tags[0].get_text(strip=True)
        
        if not title:
            issues.append(create_issue('empty_title', 'critical', 'Title tag is empty'))
        else:
            # Check length
            title_length = len(title)
            pixel_width = self._calculate_pixel_width(title)
            
            if title_length < self.config.title_min_length:
                issues.append(create_issue(
                    'short_title',
                    current_value=f"{title_length} chars",
                    recommended_value=f"{self.config.title_min_length}-{self.config.title_max_length} chars",
                    pixel_width=pixel_width
                ))
            elif title_length > self.config.title_max_length:
                issues.append(create_issue(
                    'long_title',
                    current_value=f"{title_length} chars",
                    recommended_value=f"{self.config.title_min_length}-{self.config.title_max_length} chars",
                    pixel_width=pixel_width
                ))
            
            # Check pixel width (Google typically shows ~580px on desktop)
            if pixel_width > 580:
                issues.append(create_issue(
                    'title_truncated',
                    pixel_width=pixel_width,
                    max_width=580
                ))
            
            # Check for common issues
            if title.lower() == 'untitled' or title.lower() == 'home':
                issues.append(create_issue(
                    'generic_title',
                    current_title=title
                ))
            
            # Check for keyword stuffing
            words = title.lower().split()
            if len(words) > 0:
                word_freq = {}
                for word in words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                max_freq = max(word_freq.values())
                if max_freq > 2:
                    issues.append(create_issue(
                        'title_keyword_stuffing',
                        repeated_word_count=max_freq
                    ))
        
        return {'title': title, 'issues': issues}
    
    def _analyze_meta_description(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze meta description tag(s)"""
        issues = []
        
        # Find all meta descriptions (case-insensitive)
        desc_tags = []
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            if name == 'description':
                desc_tags.append(meta)
        
        if not desc_tags:
            issues.append(create_issue('missing_description'))
            return {'description': '', 'issues': issues, 'duplicates': 0}
        
        if len(desc_tags) > 1:
            issues.append(create_issue(
                'multiple_descriptions',
                count=len(desc_tags)
            ))
        
        # Get first description
        description = desc_tags[0].get('content', '').strip()
        
        if not description:
            issues.append(create_issue('empty_description'))
        else:
            desc_length = len(description)
            pixel_width = self._calculate_pixel_width(description)
            
            if desc_length < self.config.description_min_length:
                issues.append(create_issue(
                    'short_description',
                    current_value=f"{desc_length} chars",
                    recommended_value=f"{self.config.description_min_length}-{self.config.description_max_length} chars"
                ))
            elif desc_length > self.config.description_max_length:
                issues.append(create_issue(
                    'long_description',
                    current_value=f"{desc_length} chars",
                    recommended_value=f"{self.config.description_min_length}-{self.config.description_max_length} chars"
                ))
            
            # Check pixel width (Google shows ~920px on desktop)
            if pixel_width > 920:
                issues.append({
                    'type': 'description_truncated',
                    'severity': 'notice',
                    'message': f'Description may be truncated in search results (~{pixel_width}px, max ~920px)',
                    'user_impact': 'Your call-to-action or important information might be cut off',
                    'recommendation': 'Move important information to the beginning of your description',
                    'implementation_difficulty': 'easy',
                    'priority_score': 4,
                    'estimated_impact': 'low'
                })
            
            # Check for duplicate content
            if len(desc_tags) > 1:
                unique_descriptions = set(tag.get('content', '').strip() for tag in desc_tags)
                if len(unique_descriptions) < len(desc_tags):
                    issues.append({
                        'type': 'duplicate_descriptions',
                        'severity': 'warning',
                        'message': 'Duplicate meta descriptions found',
                        'user_impact': 'Search engines may be confused about which description to use',
                        'recommendation': 'Keep only one unique meta description per page',
                        'implementation_difficulty': 'easy',
                        'priority_score': 5,
                        'estimated_impact': 'medium'
                    })
        
        return {
            'description': description,
            'issues': issues,
            'duplicates': len(desc_tags) - 1
        }
    
    def _analyze_open_graph(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze Open Graph meta tags"""
        issues = []
        og_tags = {}
        
        # Find all OG tags
        og_metas = soup.find_all('meta', property=re.compile(r'^og:', re.I))
        
        for meta in og_metas:
            prop = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if prop and content:
                # Strip 'og:' prefix for cleaner keys
                key = prop[3:] if prop.startswith('og:') else prop
                og_tags[key] = content
        
        # Check for required OG tags
        required_tags = ['title', 'type', 'url', 'image']
        missing_required = [tag for tag in required_tags if tag not in og_tags]
        
        if og_tags and missing_required:
            issues.append(create_issue(
                'incomplete_open_graph',
                missing_tags=', '.join(missing_required)
            ))
        
        # Validate OG image if present
        if 'image' in og_tags:
            image_url = og_tags['image']
            parsed = urlparse(image_url)
            
            if not parsed.scheme:
                issues.append({
                    'type': 'og_relative_image',
                    'severity': 'warning',
                    'message': 'Open Graph image should use absolute URL',
                    'user_impact': 'Social media platforms may not be able to display your image',
                    'recommendation': 'Use full URL starting with https:// for your OG image',
                    'example': '<meta property="og:image" content="https://example.com/image.jpg">',
                    'implementation_difficulty': 'easy',
                    'priority_score': 5,
                    'estimated_impact': 'medium'
                })
            
            # Check for image dimensions
            if 'image:width' not in og_tags or 'image:height' not in og_tags:
                issues.append({
                    'type': 'og_image_dimensions_missing',
                    'severity': 'notice',
                    'message': 'Open Graph image dimensions not specified',
                    'user_impact': 'Social platforms may crop your image unexpectedly',
                    'recommendation': 'Add og:image:width and og:image:height tags',
                    'example': '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">',
                    'implementation_difficulty': 'easy',
                    'priority_score': 3,
                    'estimated_impact': 'low'
                })
            else:
                try:
                    width = int(og_tags.get('image:width', 0))
                    height = int(og_tags.get('image:height', 0))
                    
                    # Facebook recommends 1200x630 for best display
                    if width < 600 or height < 315:
                        issues.append({
                            'type': 'og_image_too_small',
                            'severity': 'notice',
                            'message': f'Open Graph image small ({width}x{height}), recommend 1200x630',
                            'user_impact': 'Your image may appear small or pixelated on social media',
                            'recommendation': 'Use images at least 1200x630 pixels for best results',
                            'implementation_difficulty': 'medium',
                            'priority_score': 4,
                            'estimated_impact': 'medium'
                        })
                except ValueError:
                    pass
        
        # Check for site_name
        if og_tags and 'site_name' not in og_tags:
            issues.append({
                'type': 'og_missing_site_name',
                'severity': 'notice',
                'message': 'Open Graph site_name not specified',
                'user_impact': 'Your brand name won\'t appear in social shares',
                'recommendation': 'Add og:site_name with your website or brand name',
                'example': '<meta property="og:site_name" content="Your Brand Name">',
                'implementation_difficulty': 'easy',
                'priority_score': 3,
                'estimated_impact': 'low'
            })
        
        return {'tags': og_tags, 'issues': issues}
    
    def _analyze_twitter_cards(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze Twitter Card meta tags"""
        issues = []
        twitter_tags = {}
        
        # Find all Twitter Card tags
        twitter_metas = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:', re.I)})
        
        for meta in twitter_metas:
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            
            if name and content:
                # Strip 'twitter:' prefix
                key = name[8:] if name.startswith('twitter:') else name
                twitter_tags[key] = content
        
        if twitter_tags:
            # Check card type
            card_type = twitter_tags.get('card', '')
            if not card_type:
                issues.append({
                    'type': 'twitter_card_missing_type',
                    'severity': 'warning',
                    'message': 'Twitter Card type not specified'
                })
            elif card_type not in ['summary', 'summary_large_image', 'app', 'player']:
                issues.append({
                    'type': 'twitter_card_invalid_type',
                    'severity': 'warning',
                    'message': f'Invalid Twitter Card type: {card_type}'
                })
            
            # Check required fields based on card type
            if card_type in ['summary', 'summary_large_image']:
                if 'title' not in twitter_tags:
                    issues.append({
                        'type': 'twitter_missing_title',
                        'severity': 'warning',
                        'message': 'Twitter Card missing title'
                    })
                
                if 'description' not in twitter_tags:
                    issues.append({
                        'type': 'twitter_missing_description',
                        'severity': 'notice',
                        'message': 'Twitter Card missing description'
                    })
                
                if 'image' not in twitter_tags and card_type == 'summary_large_image':
                    issues.append({
                        'type': 'twitter_missing_image',
                        'severity': 'warning',
                        'message': 'Twitter Card summary_large_image requires image'
                    })
        
        return {'tags': twitter_tags, 'issues': issues}
    
    def _analyze_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze JSON-LD structured data"""
        issues = []
        structured_data = []
        
        # Find all JSON-LD scripts
        scripts = soup.find_all('script', type='application/ld+json')
        
        for i, script in enumerate(scripts):
            try:
                if script.string:
                    data = json.loads(script.string)
                    
                    # Extract type(s)
                    schema_type = data.get('@type', 'Unknown')
                    if isinstance(schema_type, list):
                        schema_type = ', '.join(schema_type)
                    
                    structured_item = {
                        'type': schema_type,
                        'context': data.get('@context', ''),
                        'data': data,
                        'valid': True
                    }
                    
                    # Validate common schema types
                    validation_issues = self._validate_schema(data)
                    if validation_issues:
                        structured_item['valid'] = False
                        for issue in validation_issues:
                            issues.append({
                                'type': 'invalid_structured_data',
                                'severity': 'warning',
                                'message': f'Schema.org {schema_type}: {issue}'
                            })
                    
                    structured_data.append(structured_item)
                    
            except json.JSONDecodeError as e:
                issues.append({
                    'type': 'invalid_json_ld',
                    'severity': 'warning',
                    'message': f'Invalid JSON-LD in script {i+1}: {str(e)}'
                })
            except Exception as e:
                logger.error(f"Error parsing structured data: {e}")
        
        # Check for recommended structured data types
        types_found = [item['type'] for item in structured_data]
        
        # Common recommendations
        if not any('Organization' in t or 'Person' in t for t in types_found):
            issues.append({
                'type': 'missing_publisher_schema',
                'severity': 'notice',
                'message': 'Consider adding Organization or Person schema'
            })
        
        if not any('BreadcrumbList' in t for t in types_found):
            issues.append({
                'type': 'missing_breadcrumb_schema',
                'severity': 'notice',
                'message': 'Consider adding BreadcrumbList schema for better navigation'
            })
        
        return {'data': structured_data, 'issues': issues}
    
    def _validate_schema(self, data: Dict) -> List[str]:
        """Validate common schema.org types"""
        issues = []
        schema_type = data.get('@type', '')
        
        if isinstance(schema_type, list):
            # Handle multiple types
            for t in schema_type:
                issues.extend(self._validate_single_schema(data, t))
        else:
            issues.extend(self._validate_single_schema(data, schema_type))
        
        return issues
    
    def _validate_single_schema(self, data: Dict, schema_type: str) -> List[str]:
        """Validate a single schema type"""
        issues = []
        
        # Common required fields by type
        required_fields = {
            'Article': ['headline', 'datePublished', 'author'],
            'Product': ['name', 'image', 'description'],
            'LocalBusiness': ['name', 'address', '@type'],
            'Organization': ['name', 'url'],
            'Person': ['name'],
            'BreadcrumbList': ['itemListElement'],
            'FAQPage': ['mainEntity'],
            'Recipe': ['name', 'image', 'author', 'recipeIngredient', 'recipeInstructions'],
            'VideoObject': ['name', 'description', 'thumbnailUrl', 'uploadDate'],
            'Event': ['name', 'startDate', 'location']
        }
        
        # Check required fields
        if schema_type in required_fields:
            for field in required_fields[schema_type]:
                if field not in data:
                    issues.append(f'Missing required field: {field}')
        
        # Additional validations
        if schema_type == 'Article':
            # Check for recommended fields
            recommended = ['image', 'publisher', 'dateModified']
            for field in recommended:
                if field not in data:
                    issues.append(f'Missing recommended field: {field}')
        
        elif schema_type == 'Product':
            # Check for offers
            if 'offers' not in data:
                issues.append('Missing offers for Product schema')
            elif isinstance(data.get('offers'), dict):
                offer = data['offers']
                if 'price' not in offer:
                    issues.append('Missing price in Product offers')
                if 'priceCurrency' not in offer:
                    issues.append('Missing priceCurrency in Product offers')
        
        return issues
    
    def _calculate_pixel_width(self, text: str) -> int:
        """Calculate approximate pixel width of text"""
        if not text:
            return 0
        
        width = 0
        for char in text:
            if char == ' ':
                width += self.CHAR_WIDTHS['space']
            elif char.isdigit():
                width += self.CHAR_WIDTHS['number']
            elif char.isupper():
                width += self.CHAR_WIDTHS['upper']
            elif char in 'ilft':
                width += self.CHAR_WIDTHS['narrow']
            elif char in 'mw':
                width += self.CHAR_WIDTHS['wide']
            elif char.isalpha():
                width += self.CHAR_WIDTHS['medium']
            else:
                width += self.CHAR_WIDTHS['special']
        
        return width
    
    def _extract_meta_keywords(self, soup: BeautifulSoup) -> str:
        """Extract meta keywords (though less important for modern SEO)"""
        keywords_tag = soup.find('meta', attrs={'name': re.compile(r'keywords', re.I)})
        return keywords_tag.get('content', '').strip() if keywords_tag else ''
    
    def _analyze_canonical(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze canonical URL"""
        issues = []
        canonical_tags = soup.find_all('link', {'rel': 'canonical'})
        
        if not canonical_tags:
            return {'url': '', 'issues': issues}
        
        if len(canonical_tags) > 1:
            issues.append(create_issue(
                'multiple_canonicals',
                count=len(canonical_tags)
            ))
        
        canonical_url = canonical_tags[0].get('href', '')
        
        if canonical_url:
            # Validate canonical URL
            parsed = urlparse(canonical_url)
            if not parsed.scheme or not parsed.netloc:
                issues.append(create_issue('invalid_canonical'))
        
        return {'url': canonical_url, 'issues': issues}
    
    def _analyze_robots_meta(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze meta robots directives"""
        issues = []
        robots_tags = []
        
        # Find all robots meta tags (case-insensitive)
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            if name in ['robots', 'googlebot', 'bingbot']:
                robots_tags.append(meta)
        
        # Combine all directives
        all_directives = []
        for tag in robots_tags:
            content = tag.get('content', '').lower()
            all_directives.extend(content.split(','))
        
        # Clean and deduplicate directives
        directives = list(set(d.strip() for d in all_directives if d.strip()))
        robots_content = ', '.join(directives)
        
        # Check for problematic directives
        if 'noindex' in directives:
            issues.append(create_issue('noindex'))
        
        if 'nofollow' in directives:
            issues.append(create_issue('nofollow'))
        
        if 'nosnippet' in directives:
            issues.append({
                'type': 'nosnippet',
                'severity': 'notice',
                'message': 'Page has nosnippet directive - search snippets will not be shown',
                'user_impact': 'Your page won\'t show preview text in search results',
                'recommendation': 'Remove nosnippet unless you have a specific reason to hide snippets',
                'implementation_difficulty': 'easy',
                'priority_score': 3,
                'estimated_impact': 'low'
            })
        
        if 'noarchive' in directives:
            issues.append({
                'type': 'noarchive',
                'severity': 'notice',
                'message': 'Page has noarchive directive - cached version will not be available',
                'user_impact': 'Users won\'t be able to view cached versions of your page',
                'recommendation': 'Consider if noarchive is necessary for your content',
                'implementation_difficulty': 'easy',
                'priority_score': 2,
                'estimated_impact': 'low'
            })
        
        return {'content': robots_content, 'issues': issues}
    
    def _analyze_language(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze language and charset settings"""
        issues = []
        
        # Check HTML lang attribute
        html_tag = soup.find('html')
        lang = html_tag.get('lang', '') if html_tag else ''
        
        if not lang:
            issues.append({
                'type': 'missing_lang',
                'severity': 'warning',
                'message': 'Missing lang attribute on html tag - important for accessibility and SEO'
            })
        
        # Check charset
        charset = ''
        charset_tag = soup.find('meta', charset=True)
        if charset_tag:
            charset = charset_tag.get('charset', '')
        else:
            # Check http-equiv content-type
            content_type = soup.find('meta', attrs={'http-equiv': re.compile(r'content-type', re.I)})
            if content_type:
                content = content_type.get('content', '')
                match = re.search(r'charset=([^;]+)', content, re.I)
                if match:
                    charset = match.group(1).strip()
        
        if not charset:
            issues.append({
                'type': 'missing_charset',
                'severity': 'warning',
                'message': 'Missing charset declaration'
            })
        elif charset.lower() not in ['utf-8', 'utf8']:
            issues.append({
                'type': 'non_utf8_charset',
                'severity': 'notice',
                'message': f'Using {charset} charset instead of UTF-8'
            })
        
        return {'language': lang, 'charset': charset, 'issues': issues}
    
    def _analyze_viewport(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze viewport meta tag"""
        issues = []
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        
        if not viewport_tag:
            issues.append(create_issue('missing_viewport'))
            return {'has_viewport': False, 'content': '', 'issues': issues}
        
        content = viewport_tag.get('content', '')
        
        # Check for common viewport issues
        if 'width=device-width' not in content:
            issues.append({
                'type': 'viewport_not_responsive',
                'severity': 'warning',
                'message': 'Viewport not set to device width',
                'user_impact': 'Your site may not display correctly on mobile devices',
                'recommendation': 'Include width=device-width in your viewport tag',
                'example': '<meta name="viewport" content="width=device-width, initial-scale=1">',
                'implementation_difficulty': 'easy',
                'priority_score': 8,
                'estimated_impact': 'high'
            })
        
        if 'maximum-scale=1' in content or 'user-scalable=no' in content:
            issues.append({
                'type': 'viewport_prevents_zoom',
                'severity': 'warning',
                'message': 'Viewport prevents user zoom',
                'user_impact': 'Users with visual impairments cannot zoom your content',
                'recommendation': 'Remove maximum-scale=1 and user-scalable=no for better accessibility',
                'example': '<meta name="viewport" content="width=device-width, initial-scale=1">',
                'implementation_difficulty': 'easy',
                'priority_score': 6,
                'estimated_impact': 'medium'
            })
        
        return {
            'has_viewport': True,
            'content': content,
            'issues': issues
        }
    
    def _analyze_h1_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze H1 tags"""
        issues = []
        h1_tags = soup.find_all('h1')
        h1_texts = []
        
        if not h1_tags:
            issues.append(create_issue('missing_h1'))
        elif len(h1_tags) > 1:
            issues.append(create_issue(
                'multiple_h1',
                count=len(h1_tags)
            ))
        
        for h1 in h1_tags:
            text = h1.get_text(strip=True)
            if text:
                h1_texts.append(text)
            else:
                issues.append(create_issue('empty_h1'))
        
        # Check for excessively long H1
        for text in h1_texts:
            if len(text) > 70:
                issues.append({
                    'type': 'long_h1',
                    'severity': 'notice',
                    'message': f'H1 is quite long ({len(text)} characters)',
                    'user_impact': 'Long H1 tags may not display well on mobile devices',
                    'recommendation': 'Keep H1 tags concise, ideally under 70 characters',
                    'implementation_difficulty': 'easy',
                    'priority_score': 3,
                    'estimated_impact': 'low'
                })
        
        return {
            'count': len(h1_tags),
            'texts': h1_texts,
            'issues': issues
        }
    
    def _analyze_hreflang(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze hreflang tags for international SEO"""
        issues = []
        hreflang_tags = []
        
        links = soup.find_all('link', {'rel': 'alternate', 'hreflang': True})
        
        for link in links:
            hreflang = link.get('hreflang', '')
            href = link.get('href', '')
            
            if hreflang and href:
                hreflang_tags.append({
                    'lang': hreflang,
                    'url': href
                })
                
                # Validate hreflang value
                if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', hreflang) and hreflang != 'x-default':
                    issues.append({
                        'type': 'invalid_hreflang',
                        'severity': 'warning',
                        'message': f'Invalid hreflang value: {hreflang}'
                    })
        
        # Check for x-default
        has_default = any(tag['lang'] == 'x-default' for tag in hreflang_tags)
        if hreflang_tags and not has_default:
            issues.append({
                'type': 'missing_hreflang_default',
                'severity': 'notice',
                'message': 'No x-default hreflang tag found'
            })
        
        return {'tags': hreflang_tags, 'issues': issues}
    
    def _analyze_alternates(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze alternate versions (mobile, AMP, etc.)"""
        alternates = {}
        
        # Check for mobile alternate
        mobile_link = soup.find('link', {'rel': 'alternate', 'media': re.compile(r'handheld|mobile', re.I)})
        if mobile_link:
            alternates['mobile'] = mobile_link.get('href', '')
        
        # Check for AMP version
        amp_link = soup.find('link', {'rel': 'amphtml'})
        if amp_link:
            alternates['amp'] = amp_link.get('href', '')
        
        # Check for RSS/Atom feeds
        feed_links = soup.find_all('link', {'rel': 'alternate', 'type': re.compile(r'application/(rss|atom)', re.I)})
        if feed_links:
            alternates['feeds'] = [{'type': link.get('type', ''), 'url': link.get('href', '')} for link in feed_links]
        
        return alternates 