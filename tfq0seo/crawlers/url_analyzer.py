"""
tfq0seo URL Analyzer
~~~~~~~~~~~~~~~~~~~

Comprehensive URL analysis for SEO optimization.
Analyzes URL structure, parameters, and SEO implications.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs, unquote
from dataclasses import dataclass
import tldextract

@dataclass
class URLAnalysis:
    """Comprehensive URL analysis results."""
    url: str
    protocol: str
    domain: str
    subdomain: str
    tld: str
    path: str
    filename: str
    extension: str
    query_params: Dict[str, List[str]]
    fragment: str
    port: Optional[int]
    
    # SEO Analysis
    is_seo_friendly: bool
    url_length: int
    path_segments: List[str]
    has_uppercase: bool
    has_underscores: bool
    has_spaces: bool
    has_non_ascii: bool
    has_query_parameters: bool
    has_fragment: bool
    
    # Recommendations
    seo_issues: List[str]
    recommendations: List[str]
    seo_score: float

class URLAnalyzer:
    """
    Professional URL analyzer for SEO optimization.
    
    Features:
    - URL structure analysis
    - SEO-friendly URL validation
    - Parameter analysis
    - Internationalization support
    - Best practices recommendations
    """
    
    def __init__(self):
        self.seo_patterns = {
            'good_separators': ['-', '/'],
            'bad_separators': ['_', '%20', '+'],
            'common_stop_words': ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'],
            'dynamic_indicators': ['?', '&', '=', 'id=', 'page=', 'category='],
            'seo_friendly_extensions': ['.html', '.htm', '', '/'],
            'non_seo_extensions': ['.php', '.asp', '.aspx', '.jsp', '.cgi']
        }

    def analyze_url(self, url: str) -> URLAnalysis:
        """
        Perform comprehensive URL analysis.
        
        Args:
            url: The URL to analyze
            
        Returns:
            URLAnalysis object with comprehensive analysis results
        """
        # Parse URL components
        parsed = urlparse(url)
        extracted = tldextract.extract(url)
        
        # Basic components
        protocol = parsed.scheme
        domain = extracted.domain
        subdomain = extracted.subdomain
        tld = extracted.suffix
        path = parsed.path
        query_params = parse_qs(parsed.query)
        fragment = parsed.fragment
        port = parsed.port
        
        # Path analysis
        path_segments = [seg for seg in path.split('/') if seg]
        filename = path_segments[-1] if path_segments else ''
        extension = self._get_file_extension(filename)
        
        # SEO Analysis
        seo_issues = []
        recommendations = []
        
        # URL length check
        url_length = len(url)
        if url_length > 100:
            seo_issues.append(f"URL is too long ({url_length} characters)")
            recommendations.append("Shorten URL to under 100 characters")
        
        # Character analysis
        has_uppercase = any(c.isupper() for c in url)
        has_underscores = '_' in url
        has_spaces = ' ' in url or '%20' in url
        has_non_ascii = not url.isascii()
        has_query_parameters = bool(query_params)
        has_fragment = bool(fragment)
        
        # SEO issues detection
        if has_uppercase:
            seo_issues.append("URL contains uppercase characters")
            recommendations.append("Use lowercase characters in URLs")
        
        if has_underscores:
            seo_issues.append("URL contains underscores")
            recommendations.append("Replace underscores with hyphens")
        
        if has_spaces:
            seo_issues.append("URL contains spaces")
            recommendations.append("Replace spaces with hyphens")
        
        if has_non_ascii and not self._is_valid_international_url(url):
            seo_issues.append("URL contains non-ASCII characters")
            recommendations.append("Use ASCII characters or proper URL encoding")
        
        # Path structure analysis
        if len(path_segments) > 5:
            seo_issues.append(f"URL has deep path structure ({len(path_segments)} segments)")
            recommendations.append("Reduce URL depth to improve crawlability")
        
        # Dynamic URL detection
        if self._is_dynamic_url(url):
            seo_issues.append("URL appears to be dynamically generated")
            recommendations.append("Consider using URL rewriting for SEO-friendly URLs")
        
        # Extension analysis
        if extension and extension not in self.seo_patterns['seo_friendly_extensions']:
            seo_issues.append(f"URL has non-SEO-friendly extension: {extension}")
            recommendations.append("Consider removing file extensions or using .html")
        
        # Stop words in URL
        stop_words_found = self._find_stop_words_in_url(path)
        if stop_words_found:
            seo_issues.append(f"URL contains stop words: {', '.join(stop_words_found)}")
            recommendations.append("Remove unnecessary stop words from URL")
        
        # Calculate SEO score
        seo_score = self._calculate_url_seo_score(url, seo_issues)
        
        # Determine if SEO friendly
        is_seo_friendly = seo_score >= 80 and len(seo_issues) <= 2
        
        return URLAnalysis(
            url=url,
            protocol=protocol,
            domain=domain,
            subdomain=subdomain,
            tld=tld,
            path=path,
            filename=filename,
            extension=extension,
            query_params=query_params,
            fragment=fragment,
            port=port,
            is_seo_friendly=is_seo_friendly,
            url_length=url_length,
            path_segments=path_segments,
            has_uppercase=has_uppercase,
            has_underscores=has_underscores,
            has_spaces=has_spaces,
            has_non_ascii=has_non_ascii,
            has_query_parameters=has_query_parameters,
            has_fragment=has_fragment,
            seo_issues=seo_issues,
            recommendations=recommendations,
            seo_score=seo_score
        )

    def bulk_analyze_urls(self, urls: List[str]) -> Dict[str, URLAnalysis]:
        """
        Analyze multiple URLs at once.
        
        Args:
            urls: List of URLs to analyze
            
        Returns:
            Dictionary mapping URLs to their analysis results
        """
        results = {}
        for url in urls:
            try:
                results[url] = self.analyze_url(url)
            except Exception as e:
                # Create error result
                results[url] = URLAnalysis(
                    url=url,
                    protocol='',
                    domain='',
                    subdomain='',
                    tld='',
                    path='',
                    filename='',
                    extension='',
                    query_params={},
                    fragment='',
                    port=None,
                    is_seo_friendly=False,
                    url_length=len(url),
                    path_segments=[],
                    has_uppercase=False,
                    has_underscores=False,
                    has_spaces=False,
                    has_non_ascii=False,
                    has_query_parameters=False,
                    has_fragment=False,
                    seo_issues=[f"Error analyzing URL: {str(e)}"],
                    recommendations=["Fix URL format and try again"],
                    seo_score=0.0
                )
        
        return results

    def generate_seo_friendly_url(self, title: str, base_path: str = "/") -> str:
        """
        Generate SEO-friendly URL from a title.
        
        Args:
            title: Page title or content title
            base_path: Base path for the URL
            
        Returns:
            SEO-friendly URL
        """
        # Convert to lowercase
        url_slug = title.lower()
        
        # Remove special characters
        url_slug = re.sub(r'[^\w\s-]', '', url_slug)
        
        # Replace spaces and multiple hyphens with single hyphen
        url_slug = re.sub(r'[\s_-]+', '-', url_slug)
        
        # Remove stop words
        words = url_slug.split('-')
        words = [w for w in words if w not in self.seo_patterns['common_stop_words']]
        url_slug = '-'.join(words)
        
        # Trim hyphens from start and end
        url_slug = url_slug.strip('-')
        
        # Limit length
        if len(url_slug) > 60:
            words = url_slug.split('-')
            url_slug = ''
            for word in words:
                if len(url_slug + '-' + word) <= 60:
                    url_slug += ('-' + word if url_slug else word)
                else:
                    break
        
        # Combine with base path
        return f"{base_path.rstrip('/')}/{url_slug}/"

    def find_url_patterns(self, urls: List[str]) -> Dict[str, List[str]]:
        """
        Find common URL patterns in a list of URLs.
        
        Args:
            urls: List of URLs to analyze
            
        Returns:
            Dictionary of patterns and matching URLs
        """
        patterns = {
            'dynamic_urls': [],
            'long_urls': [],
            'urls_with_underscores': [],
            'urls_with_uppercase': [],
            'urls_with_parameters': [],
            'urls_with_fragments': [],
            'deep_urls': [],
            'non_seo_extensions': []
        }
        
        for url in urls:
            analysis = self.analyze_url(url)
            
            if self._is_dynamic_url(url):
                patterns['dynamic_urls'].append(url)
            
            if analysis.url_length > 100:
                patterns['long_urls'].append(url)
            
            if analysis.has_underscores:
                patterns['urls_with_underscores'].append(url)
            
            if analysis.has_uppercase:
                patterns['urls_with_uppercase'].append(url)
            
            if analysis.has_query_parameters:
                patterns['urls_with_parameters'].append(url)
            
            if analysis.has_fragment:
                patterns['urls_with_fragments'].append(url)
            
            if len(analysis.path_segments) > 4:
                patterns['deep_urls'].append(url)
            
            if (analysis.extension and 
                analysis.extension not in self.seo_patterns['seo_friendly_extensions']):
                patterns['non_seo_extensions'].append(url)
        
        return patterns

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        if '.' in filename:
            return '.' + filename.split('.')[-1]
        return ''

    def _is_dynamic_url(self, url: str) -> bool:
        """Check if URL appears to be dynamically generated."""
        dynamic_indicators = ['?', '&', '=', 'id=', 'page=', 'category=', 'product=']
        return any(indicator in url.lower() for indicator in dynamic_indicators)

    def _is_valid_international_url(self, url: str) -> bool:
        """Check if non-ASCII URL is properly formatted for international use."""
        try:
            # Try to encode/decode the URL
            encoded = url.encode('utf-8')
            decoded = encoded.decode('utf-8')
            return url == decoded
        except:
            return False

    def _find_stop_words_in_url(self, path: str) -> List[str]:
        """Find stop words in URL path."""
        words_in_path = re.findall(r'\b\w+\b', path.lower())
        return [word for word in words_in_path if word in self.seo_patterns['common_stop_words']]

    def _calculate_url_seo_score(self, url: str, issues: List[str]) -> float:
        """Calculate SEO score for URL (0-100)."""
        base_score = 100.0
        
        # Deduct points for each issue
        issue_penalties = {
            'too long': 15,
            'uppercase': 10,
            'underscores': 10,
            'spaces': 15,
            'non-ASCII': 5,
            'deep path': 10,
            'dynamic': 20,
            'non-SEO extension': 10,
            'stop words': 5
        }
        
        for issue in issues:
            for penalty_key, penalty_value in issue_penalties.items():
                if penalty_key in issue.lower():
                    base_score -= penalty_value
                    break
        
        # Bonus points for good practices
        if len(url) <= 60:
            base_score += 5
        
        if '-' in url:  # Uses hyphens as separators
            base_score += 5
        
        parsed = urlparse(url)
        if not parsed.query:  # No query parameters
            base_score += 5
        
        return max(0.0, min(100.0, base_score))

    def get_url_recommendations(self, analysis: URLAnalysis) -> Dict[str, Any]:
        """
        Get detailed recommendations for URL optimization.
        
        Args:
            analysis: URLAnalysis object
            
        Returns:
            Dictionary with categorized recommendations
        """
        recommendations = {
            'immediate_fixes': [],
            'structural_improvements': [],
            'best_practices': [],
            'technical_optimizations': []
        }
        
        # Immediate fixes
        if analysis.has_spaces:
            recommendations['immediate_fixes'].append({
                'issue': 'URL contains spaces',
                'fix': 'Replace spaces with hyphens (-)',
                'priority': 'high',
                'impact': 'Prevents crawling issues'
            })
        
        if analysis.has_uppercase:
            recommendations['immediate_fixes'].append({
                'issue': 'URL contains uppercase characters',
                'fix': 'Convert all characters to lowercase',
                'priority': 'high',
                'impact': 'Prevents duplicate content issues'
            })
        
        # Structural improvements
        if analysis.url_length > 100:
            recommendations['structural_improvements'].append({
                'issue': f'URL is too long ({analysis.url_length} characters)',
                'fix': 'Shorten URL to under 100 characters',
                'priority': 'medium',
                'impact': 'Improves user experience and sharing'
            })
        
        if len(analysis.path_segments) > 4:
            recommendations['structural_improvements'].append({
                'issue': f'URL has deep structure ({len(analysis.path_segments)} levels)',
                'fix': 'Flatten URL structure to 3-4 levels maximum',
                'priority': 'medium',
                'impact': 'Improves crawlability and user understanding'
            })
        
        # Best practices
        if analysis.has_underscores:
            recommendations['best_practices'].append({
                'issue': 'URL uses underscores as separators',
                'fix': 'Replace underscores with hyphens',
                'priority': 'low',
                'impact': 'Hyphens are preferred by search engines'
            })
        
        if analysis.has_query_parameters:
            recommendations['best_practices'].append({
                'issue': 'URL contains query parameters',
                'fix': 'Consider URL rewriting to create clean URLs',
                'priority': 'medium',
                'impact': 'Improves SEO and user experience'
            })
        
        return recommendations 