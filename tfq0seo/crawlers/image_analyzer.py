"""
tfq0seo Image Analyzer
~~~~~~~~~~~~~~~~~~~~~

Comprehensive image analysis for SEO optimization.
Analyzes image optimization, accessibility, and performance.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from PIL import Image
import io
import hashlib
from bs4 import BeautifulSoup
import re

@dataclass
class ImageAnalysis:
    """Comprehensive image analysis results."""
    url: str
    src: str
    alt_text: str
    title: str
    width: Optional[int]
    height: Optional[int]
    file_size: int
    file_format: str
    loading_attribute: str
    srcset: str
    sizes: str
    
    # Context information
    context_page_url: str
    parent_element: str
    surrounding_text: str
    
    # SEO Analysis
    has_alt_text: bool
    alt_text_length: int
    is_decorative: bool
    alt_text_quality_score: float
    filename_seo_score: float
    
    # Technical Analysis
    is_optimized: bool
    estimated_load_time: float
    compression_ratio: float
    is_responsive: bool
    
    # Issues and Recommendations
    seo_issues: List[str]
    technical_issues: List[str]
    accessibility_issues: List[str]
    recommendations: List[str]
    overall_score: float

class ImageAnalyzer:
    """
    Professional image analyzer for SEO and performance optimization.
    
    Features:
    - Alt text analysis and optimization
    - Image optimization detection
    - Performance impact assessment
    - Accessibility compliance
    - SEO best practices validation
    - Bulk image analysis
    """
    
    def __init__(self):
        self.optimal_formats = {
            'photos': ['jpg', 'jpeg', 'webp', 'avif'],
            'graphics': ['png', 'svg', 'webp'],
            'icons': ['svg', 'ico', 'png']
        }
        
        self.max_file_sizes = {
            'hero': 500000,    # 500KB for hero images
            'content': 200000,  # 200KB for content images
            'thumbnail': 50000, # 50KB for thumbnails
            'icon': 10000      # 10KB for icons
        }

    async def analyze_images_from_html(self, html_content: str, base_url: str, 
                                     fetch_details: bool = True) -> List[ImageAnalysis]:
        """
        Analyze all images found in HTML content.
        
        Args:
            html_content: HTML content to analyze
            base_url: Base URL for resolving relative image URLs
            fetch_details: Whether to fetch image details (size, dimensions)
            
        Returns:
            List of ImageAnalysis objects
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')
        
        results = []
        
        # Process images concurrently if fetching details
        if fetch_details:
            tasks = [
                self._analyze_single_image(img, base_url, soup) 
                for img in images
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            results = [r for r in results if not isinstance(r, Exception)]
        else:
            # Analyze without fetching external details
            for img in images:
                analysis = await self._analyze_single_image(img, base_url, soup, fetch_details=False)
                results.append(analysis)
        
        return results

    async def _analyze_single_image(self, img_element, base_url: str, soup: BeautifulSoup, 
                                  fetch_details: bool = True) -> ImageAnalysis:
        """Analyze a single image element."""
        src = img_element.get('src', '')
        if not src:
            src = img_element.get('data-src', '')  # Lazy loading
        
        # Resolve relative URLs
        absolute_url = urljoin(base_url, src) if src else ''
        
        # Extract basic attributes
        alt_text = img_element.get('alt', '')
        title = img_element.get('title', '')
        width = self._parse_dimension(img_element.get('width'))
        height = self._parse_dimension(img_element.get('height'))
        loading_attribute = img_element.get('loading', '')
        srcset = img_element.get('srcset', '')
        sizes = img_element.get('sizes', '')
        
        # Get context information
        context_info = self._get_image_context(img_element, soup)
        
        # Initialize analysis object
        analysis = ImageAnalysis(
            url=absolute_url,
            src=src,
            alt_text=alt_text,
            title=title,
            width=width,
            height=height,
            file_size=0,
            file_format='',
            loading_attribute=loading_attribute,
            srcset=srcset,
            sizes=sizes,
            context_page_url=base_url,
            parent_element=context_info['parent_element'],
            surrounding_text=context_info['surrounding_text'],
            has_alt_text=bool(alt_text),
            alt_text_length=len(alt_text),
            is_decorative=self._is_decorative_image(img_element),
            alt_text_quality_score=0.0,
            filename_seo_score=0.0,
            is_optimized=False,
            estimated_load_time=0.0,
            compression_ratio=0.0,
            is_responsive=bool(srcset or sizes),
            seo_issues=[],
            technical_issues=[],
            accessibility_issues=[],
            recommendations=[],
            overall_score=0.0
        )
        
        # Fetch image details if requested
        if fetch_details and absolute_url:
            await self._fetch_image_details(analysis)
        
        # Perform SEO analysis
        self._analyze_seo_aspects(analysis)
        
        # Perform technical analysis
        self._analyze_technical_aspects(analysis)
        
        # Perform accessibility analysis
        self._analyze_accessibility_aspects(analysis)
        
        # Calculate overall score
        analysis.overall_score = self._calculate_overall_score(analysis)
        
        return analysis

    async def _fetch_image_details(self, analysis: ImageAnalysis):
        """Fetch image file details (size, format, dimensions)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(analysis.url) as response:
                    # Get file size from headers
                    content_length = response.headers.get('content-length')
                    if content_length:
                        analysis.file_size = int(content_length)
                    
                    # Get file format from content-type or URL
                    content_type = response.headers.get('content-type', '')
                    if 'image/' in content_type:
                        analysis.file_format = content_type.split('/')[-1]
                    else:
                        # Extract from URL
                        parsed_url = urlparse(analysis.url)
                        if '.' in parsed_url.path:
                            analysis.file_format = parsed_url.path.split('.')[-1].lower()
                
                # For more detailed analysis, fetch the actual image
                if analysis.file_size < 1000000:  # Only for images < 1MB
                    try:
                        async with session.get(analysis.url) as img_response:
                            if img_response.status == 200:
                                image_data = await img_response.read()
                                await self._analyze_image_data(analysis, image_data)
                    except:
                        pass  # Skip detailed analysis if fetch fails
        
        except Exception as e:
            analysis.technical_issues.append(f"Could not fetch image details: {str(e)}")

    async def _analyze_image_data(self, analysis: ImageAnalysis, image_data: bytes):
        """Analyze actual image data for optimization insights."""
        try:
            # Get actual dimensions using PIL
            with Image.open(io.BytesIO(image_data)) as img:
                actual_width, actual_height = img.size
                
                # Compare with HTML dimensions if specified
                if analysis.width and analysis.height:
                    if (actual_width != analysis.width or 
                        actual_height != analysis.height):
                        analysis.technical_issues.append(
                            f"Image dimensions ({actual_width}x{actual_height}) don't match HTML attributes ({analysis.width}x{analysis.height})"
                        )
                
                # Update actual dimensions
                if not analysis.width:
                    analysis.width = actual_width
                if not analysis.height:
                    analysis.height = actual_height
                
                # Analyze compression
                uncompressed_size = actual_width * actual_height * 3  # RGB
                if analysis.file_size > 0:
                    analysis.compression_ratio = analysis.file_size / uncompressed_size
                
                # Check for optimization opportunities
                self._check_optimization_opportunities(analysis, img)
        
        except Exception as e:
            analysis.technical_issues.append(f"Could not analyze image data: {str(e)}")

    def _get_image_context(self, img_element, soup: BeautifulSoup) -> Dict[str, str]:
        """Get contextual information about the image."""
        context = {
            'parent_element': '',
            'surrounding_text': ''
        }
        
        # Get parent element
        parent = img_element.parent
        if parent:
            context['parent_element'] = parent.name
        
        # Get surrounding text (from parent paragraph or nearby elements)
        surrounding_elements = []
        
        # Check parent paragraph
        parent_p = img_element.find_parent('p')
        if parent_p:
            surrounding_elements.append(parent_p.get_text().strip())
        
        # Check nearby siblings
        for sibling in img_element.find_previous_siblings(['p', 'h1', 'h2', 'h3'], limit=2):
            surrounding_elements.append(sibling.get_text().strip())
        
        for sibling in img_element.find_next_siblings(['p', 'h1', 'h2', 'h3'], limit=2):
            surrounding_elements.append(sibling.get_text().strip())
        
        context['surrounding_text'] = ' '.join(surrounding_elements)[:200]  # Limit to 200 chars
        
        return context

    def _is_decorative_image(self, img_element) -> bool:
        """Check if image is decorative (doesn't need alt text)."""
        # Check for role="presentation" or aria-hidden="true"
        if (img_element.get('role') == 'presentation' or 
            img_element.get('aria-hidden') == 'true'):
            return True
        
        # Check for empty alt attribute (intentionally decorative)
        alt = img_element.get('alt')
        if alt == '':  # Empty alt (not None) indicates decorative
            return True
        
        # Check if image is in background or used for layout
        css_classes = img_element.get('class', [])
        decorative_classes = ['background', 'decoration', 'divider', 'spacer']
        if any(cls in ' '.join(css_classes).lower() for cls in decorative_classes):
            return True
        
        return False

    def _analyze_seo_aspects(self, analysis: ImageAnalysis):
        """Analyze SEO aspects of the image."""
        # Alt text analysis
        if not analysis.has_alt_text and not analysis.is_decorative:
            analysis.seo_issues.append("Missing alt text")
            analysis.recommendations.append("Add descriptive alt text for better SEO and accessibility")
        
        elif analysis.has_alt_text:
            # Alt text quality analysis
            analysis.alt_text_quality_score = self._evaluate_alt_text_quality(analysis.alt_text, analysis.surrounding_text)
            
            if analysis.alt_text_length < 10:
                analysis.seo_issues.append("Alt text is too short")
                analysis.recommendations.append("Use more descriptive alt text (10+ characters)")
            
            elif analysis.alt_text_length > 125:
                analysis.seo_issues.append("Alt text is too long")
                analysis.recommendations.append("Shorten alt text to under 125 characters")
            
            # Check for keyword stuffing
            words = analysis.alt_text.lower().split()
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            if any(count > 2 for count in word_counts.values()):
                analysis.seo_issues.append("Potential keyword stuffing in alt text")
                analysis.recommendations.append("Use natural language in alt text")
        
        # Filename analysis
        analysis.filename_seo_score = self._evaluate_filename_seo(analysis.url)
        
        if analysis.filename_seo_score < 50:
            analysis.seo_issues.append("Non-descriptive filename")
            analysis.recommendations.append("Use descriptive, keyword-rich filenames")

    def _analyze_technical_aspects(self, analysis: ImageAnalysis):
        """Analyze technical aspects of the image."""
        # File size analysis
        if analysis.file_size > 0:
            image_category = self._categorize_image(analysis)
            max_size = self.max_file_sizes.get(image_category, 200000)
            
            if analysis.file_size > max_size:
                analysis.technical_issues.append(f"File size too large ({analysis.file_size} bytes)")
                analysis.recommendations.append(f"Optimize image size (target: <{max_size} bytes)")
            
            # Estimate load time (assuming average 5 Mbps connection)
            analysis.estimated_load_time = (analysis.file_size * 8) / (5 * 1024 * 1024)
        
        # Format optimization
        if analysis.file_format:
            optimal_formats = self._get_optimal_formats(analysis)
            if analysis.file_format.lower() not in optimal_formats:
                analysis.technical_issues.append(f"Non-optimal format: {analysis.file_format}")
                analysis.recommendations.append(f"Consider using: {', '.join(optimal_formats)}")
        
        # Responsive image analysis
        if not analysis.is_responsive and analysis.width and analysis.width > 800:
            analysis.technical_issues.append("Large image without responsive attributes")
            analysis.recommendations.append("Add srcset and sizes attributes for responsive images")
        
        # Lazy loading analysis
        if not analysis.loading_attribute and analysis.width and analysis.width > 400:
            analysis.technical_issues.append("Missing lazy loading attribute")
            analysis.recommendations.append("Add loading='lazy' for below-the-fold images")

    def _analyze_accessibility_aspects(self, analysis: ImageAnalysis):
        """Analyze accessibility aspects of the image."""
        if not analysis.is_decorative:
            if not analysis.has_alt_text:
                analysis.accessibility_issues.append("Missing alt text affects screen readers")
                analysis.recommendations.append("Add alt text for accessibility compliance")
            
            elif analysis.alt_text:
                # Check for poor alt text practices
                poor_alt_patterns = [
                    'image of', 'picture of', 'photo of', 'graphic of',
                    'click here', 'read more', 'image', 'picture', 'photo'
                ]
                
                alt_lower = analysis.alt_text.lower()
                if any(pattern in alt_lower for pattern in poor_alt_patterns):
                    analysis.accessibility_issues.append("Alt text uses redundant phrases")
                    analysis.recommendations.append("Remove redundant phrases like 'image of' from alt text")
        
        # Check for text in images
        if self._likely_contains_text(analysis):
            analysis.accessibility_issues.append("Image may contain text")
            analysis.recommendations.append("Ensure text in images is also available as HTML text")

    def _evaluate_alt_text_quality(self, alt_text: str, context: str) -> float:
        """Evaluate the quality of alt text (0-100 score)."""
        if not alt_text:
            return 0.0
        
        score = 50.0  # Base score
        
        # Length appropriateness
        length = len(alt_text)
        if 25 <= length <= 100:
            score += 20
        elif 10 <= length <= 125:
            score += 10
        else:
            score -= 10
        
        # Descriptiveness (word count)
        words = alt_text.split()
        if 3 <= len(words) <= 15:
            score += 15
        elif len(words) < 3:
            score -= 15
        
        # Avoid redundant phrases
        redundant_phrases = ['image of', 'picture of', 'photo of']
        if not any(phrase in alt_text.lower() for phrase in redundant_phrases):
            score += 10
        else:
            score -= 10
        
        # Context relevance (basic keyword overlap)
        if context:
            alt_words = set(alt_text.lower().split())
            context_words = set(context.lower().split())
            overlap = len(alt_words.intersection(context_words))
            if overlap > 0:
                score += min(overlap * 5, 15)
        
        return max(0.0, min(100.0, score))

    def _evaluate_filename_seo(self, url: str) -> float:
        """Evaluate SEO-friendliness of image filename."""
        if not url:
            return 0.0
        
        # Extract filename from URL
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]
        
        if not filename:
            return 0.0
        
        # Remove extension
        if '.' in filename:
            filename = filename.rsplit('.', 1)[0]
        
        score = 50.0
        
        # Check for descriptive naming
        if len(filename) > 3:
            score += 20
        
        # Check for hyphens (good)
        if '-' in filename:
            score += 15
        
        # Check for underscores (less good)
        if '_' in filename:
            score -= 5
        
        # Check for generic names
        generic_names = ['image', 'img', 'picture', 'pic', 'photo', 'untitled', 'default']
        if any(generic in filename.lower() for generic in generic_names):
            score -= 20
        
        # Check for numbers only
        if filename.isdigit():
            score -= 15
        
        return max(0.0, min(100.0, score))

    def _categorize_image(self, analysis: ImageAnalysis) -> str:
        """Categorize image based on context and dimensions."""
        # Check parent elements and classes for context
        parent = analysis.parent_element.lower()
        
        if 'hero' in parent or (analysis.width and analysis.width > 1200):
            return 'hero'
        elif 'thumb' in parent or (analysis.width and analysis.width < 200):
            return 'thumbnail'
        elif 'icon' in parent or (analysis.width and analysis.width < 100):
            return 'icon'
        else:
            return 'content'

    def _get_optimal_formats(self, analysis: ImageAnalysis) -> List[str]:
        """Get optimal formats for the image type."""
        category = self._categorize_image(analysis)
        
        if category == 'icon':
            return self.optimal_formats['icons']
        elif category in ['hero', 'content']:
            # Assume photos for large images
            return self.optimal_formats['photos']
        else:
            return self.optimal_formats['graphics']

    def _check_optimization_opportunities(self, analysis: ImageAnalysis, img):
        """Check for specific optimization opportunities."""
        try:
            # Check if image could be compressed more
            if analysis.compression_ratio > 0.5:  # High compression ratio
                analysis.technical_issues.append("Image may be under-compressed")
                analysis.recommendations.append("Increase compression to reduce file size")
            
            # Check for unnecessarily large dimensions
            if analysis.width and analysis.height:
                pixel_count = analysis.width * analysis.height
                if pixel_count > 2000000:  # > 2 megapixels
                    analysis.technical_issues.append("Very high resolution image")
                    analysis.recommendations.append("Consider reducing image dimensions")
            
            # Check color mode
            if hasattr(img, 'mode'):
                if img.mode == 'RGBA' and analysis.file_format.lower() in ['jpg', 'jpeg']:
                    analysis.technical_issues.append("RGBA image saved as JPEG")
                    analysis.recommendations.append("Use PNG for images with transparency")
        
        except Exception:
            pass  # Skip if analysis fails

    def _likely_contains_text(self, analysis: ImageAnalysis) -> bool:
        """Heuristic to determine if image likely contains text."""
        # Check filename for text indicators
        filename = analysis.url.lower()
        text_indicators = ['text', 'title', 'heading', 'banner', 'logo', 'button']
        
        if any(indicator in filename for indicator in text_indicators):
            return True
        
        # Check alt text for text-related words
        alt_text = analysis.alt_text.lower()
        if any(indicator in alt_text for indicator in text_indicators):
            return True
        
        return False

    def _calculate_overall_score(self, analysis: ImageAnalysis) -> float:
        """Calculate overall image optimization score."""
        base_score = 100.0
        
        # Deduct for issues
        base_score -= len(analysis.seo_issues) * 10
        base_score -= len(analysis.technical_issues) * 8
        base_score -= len(analysis.accessibility_issues) * 12
        
        # Add bonuses for good practices
        if analysis.has_alt_text and not analysis.is_decorative:
            base_score += 10
        
        if analysis.is_responsive:
            base_score += 10
        
        if analysis.loading_attribute == 'lazy':
            base_score += 5
        
        if analysis.filename_seo_score > 70:
            base_score += 5
        
        return max(0.0, min(100.0, base_score))

    def _parse_dimension(self, dimension_str: Optional[str]) -> Optional[int]:
        """Parse dimension string to integer."""
        if not dimension_str:
            return None
        
        try:
            # Remove 'px' if present and convert to int
            return int(dimension_str.replace('px', ''))
        except (ValueError, AttributeError):
            return None

    def get_image_summary(self, analyses: List[ImageAnalysis]) -> Dict[str, Any]:
        """Generate summary statistics for a list of image analyses."""
        if not analyses:
            return {}
        
        total_images = len(analyses)
        
        return {
            'total_images': total_images,
            'images_with_alt_text': sum(1 for a in analyses if a.has_alt_text),
            'decorative_images': sum(1 for a in analyses if a.is_decorative),
            'responsive_images': sum(1 for a in analyses if a.is_responsive),
            'lazy_loaded_images': sum(1 for a in analyses if a.loading_attribute == 'lazy'),
            'total_file_size': sum(a.file_size for a in analyses if a.file_size > 0),
            'average_score': sum(a.overall_score for a in analyses) / total_images,
            'images_with_issues': sum(1 for a in analyses if a.seo_issues or a.technical_issues or a.accessibility_issues),
            'most_common_issues': self._get_most_common_issues(analyses),
            'format_distribution': self._get_format_distribution(analyses)
        }

    def _get_most_common_issues(self, analyses: List[ImageAnalysis]) -> List[Tuple[str, int]]:
        """Get most common issues across all images."""
        issue_counts = {}
        
        for analysis in analyses:
            all_issues = (analysis.seo_issues + 
                         analysis.technical_issues + 
                         analysis.accessibility_issues)
            
            for issue in all_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        return sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def _get_format_distribution(self, analyses: List[ImageAnalysis]) -> Dict[str, int]:
        """Get distribution of image formats."""
        formats = {}
        
        for analysis in analyses:
            if analysis.file_format:
                format_key = analysis.file_format.lower()
                formats[format_key] = formats.get(format_key, 0) + 1
        
        return formats 