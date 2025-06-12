"""
tfq0seo Link Analyzer
~~~~~~~~~~~~~~~~~~~~

Comprehensive link analysis for SEO optimization.
Analyzes internal/external links, anchor text, and link structure.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import re
from collections import defaultdict, Counter

@dataclass
class LinkAnalysis:
    """Comprehensive link analysis results."""
    url: str
    anchor_text: str
    title: str
    target: str
    rel: str
    type: str  # 'internal', 'external', 'anchor', 'javascript', 'mailto', 'tel'
    
    # Context information
    source_page: str
    parent_element: str
    surrounding_text: str
    position_in_page: int
    
    # Link attributes
    is_nofollow: bool
    is_noopener: bool
    is_noreferrer: bool
    opens_new_window: bool
    
    # Status and validation
    status_code: Optional[int]
    response_time: Optional[float]
    final_url: Optional[str]  # After redirects
    redirect_chain: List[str]
    is_broken: bool
    
    # SEO Analysis
    anchor_text_quality_score: float
    passes_link_juice: bool
    is_navigational: bool
    keyword_relevance: float
    
    # Issues and recommendations
    issues: List[str]
    recommendations: List[str]
    priority: str  # 'high', 'medium', 'low'

@dataclass
class LinkStructureAnalysis:
    """Site-wide link structure analysis."""
    total_links: int
    internal_links: int
    external_links: int
    broken_links: int
    redirect_links: int
    
    # Link distribution
    navigation_links: int
    content_links: int
    footer_links: int
    
    # Anchor text analysis
    anchor_text_distribution: Dict[str, int]
    over_optimized_anchors: List[str]
    generic_anchors: List[str]
    
    # Link depth analysis
    max_depth: int
    average_depth: float
    orphaned_pages: List[str]
    
    # Authority distribution
    internal_linking_score: float
    link_equity_distribution: Dict[str, float]

class LinkAnalyzer:
    """
    Professional link analyzer for SEO optimization.
    
    Features:
    - Internal/external link analysis
    - Broken link detection
    - Anchor text optimization
    - Link structure analysis
    - Authority distribution mapping
    - Redirect chain analysis
    """
    
    def __init__(self):
        self.generic_anchor_patterns = [
            'click here', 'read more', 'learn more', 'more info', 'here',
            'this', 'link', 'website', 'page', 'continue', 'next'
        ]
        
        self.navigational_indicators = [
            'home', 'about', 'contact', 'services', 'products', 'blog',
            'menu', 'navigation', 'nav', 'breadcrumb'
        ]

    async def analyze_links_from_html(self, html_content: str, base_url: str, 
                                    validate_links: bool = True) -> List[LinkAnalysis]:
        """
        Analyze all links found in HTML content.
        
        Args:
            html_content: HTML content to analyze
            base_url: Base URL for resolving relative links
            validate_links: Whether to validate link status
            
        Returns:
            List of LinkAnalysis objects
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        results = []
        
        for i, link in enumerate(links):
            analysis = await self._analyze_single_link(link, base_url, soup, i)
            results.append(analysis)
        
        # Validate links if requested
        if validate_links:
            await self._validate_links(results)
        
        return results

    async def _analyze_single_link(self, link_element, base_url: str, 
                                 soup: BeautifulSoup, position: int) -> LinkAnalysis:
        """Analyze a single link element."""
        href = link_element.get('href', '')
        anchor_text = link_element.get_text().strip()
        title = link_element.get('title', '')
        target = link_element.get('target', '')
        rel = link_element.get('rel', '')
        
        # Resolve URL and determine type
        absolute_url, link_type = self._resolve_and_categorize_url(href, base_url)
        
        # Get context information
        context_info = self._get_link_context(link_element, soup)
        
        # Analyze attributes
        rel_list = rel.split() if rel else []
        is_nofollow = 'nofollow' in rel_list
        is_noopener = 'noopener' in rel_list
        is_noreferrer = 'noreferrer' in rel_list
        opens_new_window = target == '_blank'
        
        # Initialize analysis object
        analysis = LinkAnalysis(
            url=absolute_url,
            anchor_text=anchor_text,
            title=title,
            target=target,
            rel=rel,
            type=link_type,
            source_page=base_url,
            parent_element=context_info['parent_element'],
            surrounding_text=context_info['surrounding_text'],
            position_in_page=position,
            is_nofollow=is_nofollow,
            is_noopener=is_noopener,
            is_noreferrer=is_noreferrer,
            opens_new_window=opens_new_window,
            status_code=None,
            response_time=None,
            final_url=None,
            redirect_chain=[],
            is_broken=False,
            anchor_text_quality_score=0.0,
            passes_link_juice=not is_nofollow,
            is_navigational=False,
            keyword_relevance=0.0,
            issues=[],
            recommendations=[],
            priority='medium'
        )
        
        # Perform SEO analysis
        self._analyze_seo_aspects(analysis)
        
        # Determine priority
        analysis.priority = self._determine_link_priority(analysis)
        
        return analysis

    def _resolve_and_categorize_url(self, href: str, base_url: str) -> Tuple[str, str]:
        """Resolve URL and categorize link type."""
        if not href:
            return '', 'empty'
        
        href = href.strip()
        
        # Handle different URL schemes
        if href.startswith('mailto:'):
            return href, 'mailto'
        elif href.startswith('tel:'):
            return href, 'tel'
        elif href.startswith('javascript:'):
            return href, 'javascript'
        elif href.startswith('#'):
            return urljoin(base_url, href), 'anchor'
        elif href.startswith('//'):
            # Protocol-relative URL
            parsed_base = urlparse(base_url)
            return f"{parsed_base.scheme}:{href}", self._determine_domain_type(href, base_url)
        elif href.startswith(('http://', 'https://')):
            return href, self._determine_domain_type(href, base_url)
        else:
            # Relative URL
            absolute_url = urljoin(base_url, href)
            return absolute_url, 'internal'

    def _determine_domain_type(self, url: str, base_url: str) -> str:
        """Determine if URL is internal or external."""
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
        
        if parsed_url.netloc == parsed_base.netloc:
            return 'internal'
        else:
            return 'external'

    def _get_link_context(self, link_element, soup: BeautifulSoup) -> Dict[str, str]:
        """Get contextual information about the link."""
        context = {
            'parent_element': '',
            'surrounding_text': ''
        }
        
        # Get parent element
        parent = link_element.parent
        if parent:
            context['parent_element'] = parent.name
        
        # Determine if it's in navigation
        nav_parent = link_element.find_parent(['nav', 'header', 'footer'])
        if nav_parent:
            context['parent_element'] = f"{context['parent_element']} ({nav_parent.name})"
        
        # Get surrounding text
        surrounding_elements = []
        
        # Check parent paragraph
        parent_p = link_element.find_parent('p')
        if parent_p:
            text = parent_p.get_text().strip()
            surrounding_elements.append(text)
        
        # Check nearby siblings
        for sibling in link_element.find_previous_siblings(['p', 'h1', 'h2', 'h3'], limit=1):
            surrounding_elements.append(sibling.get_text().strip())
        
        context['surrounding_text'] = ' '.join(surrounding_elements)[:200]  # Limit to 200 chars
        
        return context

    def _analyze_seo_aspects(self, analysis: LinkAnalysis):
        """Analyze SEO aspects of the link."""
        # Anchor text analysis
        if not analysis.anchor_text:
            analysis.issues.append("Empty anchor text")
            analysis.recommendations.append("Add descriptive anchor text")
            analysis.anchor_text_quality_score = 0.0
        else:
            analysis.anchor_text_quality_score = self._evaluate_anchor_text_quality(
                analysis.anchor_text, analysis.url, analysis.surrounding_text
            )
            
            # Check for generic anchor text
            if analysis.anchor_text.lower() in self.generic_anchor_patterns:
                analysis.issues.append("Generic anchor text")
                analysis.recommendations.append("Use more descriptive anchor text")
            
            # Check for over-optimization
            if self._is_over_optimized_anchor(analysis.anchor_text):
                analysis.issues.append("Potentially over-optimized anchor text")
                analysis.recommendations.append("Use more natural anchor text")
        
        # Determine if navigational
        analysis.is_navigational = self._is_navigational_link(analysis)
        
        # External link analysis
        if analysis.type == 'external':
            if analysis.opens_new_window and not analysis.is_noopener:
                analysis.issues.append("External link opens in new window without noopener")
                analysis.recommendations.append("Add rel='noopener' for security")
            
            if not analysis.is_nofollow and not self._is_trusted_domain(analysis.url):
                analysis.recommendations.append("Consider adding rel='nofollow' for untrusted external links")
        
        # Internal link analysis
        elif analysis.type == 'internal':
            if analysis.is_nofollow:
                analysis.issues.append("Internal link has nofollow attribute")
                analysis.recommendations.append("Remove nofollow from internal links")
        
        # JavaScript link analysis
        elif analysis.type == 'javascript':
            analysis.issues.append("JavaScript link may not be crawlable")
            analysis.recommendations.append("Provide alternative navigation method")
        
        # Calculate keyword relevance
        analysis.keyword_relevance = self._calculate_keyword_relevance(analysis)

    def _evaluate_anchor_text_quality(self, anchor_text: str, url: str, context: str) -> float:
        """Evaluate the quality of anchor text (0-100 score)."""
        if not anchor_text:
            return 0.0
        
        score = 50.0  # Base score
        
        # Length appropriateness
        length = len(anchor_text)
        if 10 <= length <= 60:
            score += 20
        elif 5 <= length <= 100:
            score += 10
        else:
            score -= 10
        
        # Word count
        words = anchor_text.split()
        if 2 <= len(words) <= 8:
            score += 15
        elif len(words) == 1:
            score += 5
        else:
            score -= 10
        
        # Avoid generic phrases
        if anchor_text.lower() not in self.generic_anchor_patterns:
            score += 15
        else:
            score -= 20
        
        # Descriptiveness (contains meaningful words)
        meaningful_words = [w for w in words if len(w) > 3 and w.lower() not in ['the', 'and', 'for', 'with']]
        if meaningful_words:
            score += min(len(meaningful_words) * 5, 20)
        
        # URL relevance (basic check)
        if url and any(word.lower() in url.lower() for word in words):
            score += 10
        
        return max(0.0, min(100.0, score))

    def _is_over_optimized_anchor(self, anchor_text: str) -> bool:
        """Check if anchor text appears over-optimized."""
        # Check for exact match keywords repeated
        words = anchor_text.lower().split()
        word_counts = Counter(words)
        
        # If any word appears more than twice, likely over-optimized
        if any(count > 2 for count in word_counts.values()):
            return True
        
        # Check for commercial keywords
        commercial_keywords = ['buy', 'cheap', 'best', 'top', 'review', 'discount']
        if sum(1 for word in words if word in commercial_keywords) > 2:
            return True
        
        return False

    def _is_navigational_link(self, analysis: LinkAnalysis) -> bool:
        """Determine if link is navigational."""
        # Check parent element
        if 'nav' in analysis.parent_element.lower():
            return True
        
        # Check anchor text
        anchor_lower = analysis.anchor_text.lower()
        if any(indicator in anchor_lower for indicator in self.navigational_indicators):
            return True
        
        # Check if in header or footer
        if any(element in analysis.parent_element.lower() for element in ['header', 'footer']):
            return True
        
        return False

    def _is_trusted_domain(self, url: str) -> bool:
        """Check if domain is generally trusted (simplified)."""
        trusted_domains = [
            'wikipedia.org', 'gov', 'edu', 'mozilla.org', 'w3.org',
            'google.com', 'microsoft.com', 'apple.com', 'amazon.com'
        ]
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        return any(trusted in domain for trusted in trusted_domains)

    def _calculate_keyword_relevance(self, analysis: LinkAnalysis) -> float:
        """Calculate keyword relevance between anchor text and surrounding content."""
        if not analysis.anchor_text or not analysis.surrounding_text:
            return 0.0
        
        # Simple keyword overlap calculation
        anchor_words = set(analysis.anchor_text.lower().split())
        context_words = set(analysis.surrounding_text.lower().split())
        
        if not anchor_words:
            return 0.0
        
        overlap = len(anchor_words.intersection(context_words))
        return min((overlap / len(anchor_words)) * 100, 100.0)

    def _determine_link_priority(self, analysis: LinkAnalysis) -> str:
        """Determine the priority level for fixing link issues."""
        if analysis.type == 'javascript' or analysis.is_broken:
            return 'high'
        elif analysis.issues:
            critical_issues = ['Empty anchor text', 'Generic anchor text']
            if any(issue in critical_issues for issue in analysis.issues):
                return 'high'
            else:
                return 'medium'
        else:
            return 'low'

    async def _validate_links(self, analyses: List[LinkAnalysis]):
        """Validate link status codes and detect broken links."""
        # Filter links that need validation
        links_to_validate = [
            analysis for analysis in analyses
            if analysis.type in ['internal', 'external'] and analysis.url
        ]
        
        # Validate in batches to avoid overwhelming servers
        batch_size = 10
        for i in range(0, len(links_to_validate), batch_size):
            batch = links_to_validate[i:i + batch_size]
            tasks = [self._validate_single_link(analysis) for analysis in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches
            await asyncio.sleep(1)

    async def _validate_single_link(self, analysis: LinkAnalysis):
        """Validate a single link."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start_time = asyncio.get_event_loop().time()
                
                # Use HEAD request for faster validation
                async with session.head(analysis.url, allow_redirects=True) as response:
                    analysis.response_time = asyncio.get_event_loop().time() - start_time
                    analysis.status_code = response.status
                    analysis.final_url = str(response.url)
                    
                    # Track redirect chain
                    if str(response.url) != analysis.url:
                        analysis.redirect_chain = [analysis.url, str(response.url)]
                    
                    # Determine if broken
                    analysis.is_broken = response.status >= 400
                    
                    if analysis.is_broken:
                        analysis.issues.append(f"Broken link (HTTP {response.status})")
                        analysis.recommendations.append("Fix or remove broken link")
                        analysis.priority = 'high'
        
        except Exception as e:
            analysis.is_broken = True
            analysis.issues.append(f"Link validation failed: {str(e)}")
            analysis.recommendations.append("Check link accessibility")
            analysis.priority = 'high'

    def analyze_link_structure(self, link_analyses: List[LinkAnalysis], 
                             base_domain: str) -> LinkStructureAnalysis:
        """Analyze overall link structure of a site."""
        if not link_analyses:
            return LinkStructureAnalysis(
                total_links=0, internal_links=0, external_links=0,
                broken_links=0, redirect_links=0, navigation_links=0,
                content_links=0, footer_links=0, anchor_text_distribution={},
                over_optimized_anchors=[], generic_anchors=[], max_depth=0,
                average_depth=0.0, orphaned_pages=[], internal_linking_score=0.0,
                link_equity_distribution={}
            )
        
        # Basic counts
        total_links = len(link_analyses)
        internal_links = sum(1 for link in link_analyses if link.type == 'internal')
        external_links = sum(1 for link in link_analyses if link.type == 'external')
        broken_links = sum(1 for link in link_analyses if link.is_broken)
        redirect_links = sum(1 for link in link_analyses if link.redirect_chain)
        
        # Distribution analysis
        navigation_links = sum(1 for link in link_analyses if link.is_navigational)
        content_links = sum(1 for link in link_analyses if not link.is_navigational and 'content' in link.parent_element)
        footer_links = sum(1 for link in link_analyses if 'footer' in link.parent_element)
        
        # Anchor text analysis
        anchor_texts = [link.anchor_text for link in link_analyses if link.anchor_text]
        anchor_text_distribution = dict(Counter(anchor_texts).most_common(20))
        
        over_optimized_anchors = [
            text for text in anchor_texts 
            if self._is_over_optimized_anchor(text)
        ]
        
        generic_anchors = [
            text for text in anchor_texts 
            if text.lower() in self.generic_anchor_patterns
        ]
        
        # Link depth analysis (simplified)
        internal_link_analyses = [link for link in link_analyses if link.type == 'internal']
        depths = [len(urlparse(link.url).path.split('/')) - 1 for link in internal_link_analyses]
        max_depth = max(depths) if depths else 0
        average_depth = sum(depths) / len(depths) if depths else 0.0
        
        # Calculate internal linking score
        internal_linking_score = self._calculate_internal_linking_score(link_analyses)
        
        # Link equity distribution (simplified)
        link_equity_distribution = self._calculate_link_equity_distribution(internal_link_analyses)
        
        return LinkStructureAnalysis(
            total_links=total_links,
            internal_links=internal_links,
            external_links=external_links,
            broken_links=broken_links,
            redirect_links=redirect_links,
            navigation_links=navigation_links,
            content_links=content_links,
            footer_links=footer_links,
            anchor_text_distribution=anchor_text_distribution,
            over_optimized_anchors=list(set(over_optimized_anchors)),
            generic_anchors=list(set(generic_anchors)),
            max_depth=max_depth,
            average_depth=average_depth,
            orphaned_pages=[],  # Would need full site crawl to determine
            internal_linking_score=internal_linking_score,
            link_equity_distribution=link_equity_distribution
        )

    def _calculate_internal_linking_score(self, link_analyses: List[LinkAnalysis]) -> float:
        """Calculate overall internal linking score."""
        if not link_analyses:
            return 0.0
        
        internal_links = [link for link in link_analyses if link.type == 'internal']
        if not internal_links:
            return 0.0
        
        score = 50.0  # Base score
        
        # Bonus for good anchor text
        good_anchors = sum(1 for link in internal_links if link.anchor_text_quality_score > 70)
        score += min((good_anchors / len(internal_links)) * 30, 30)
        
        # Penalty for generic anchors
        generic_count = sum(1 for link in internal_links if link.anchor_text.lower() in self.generic_anchor_patterns)
        score -= min((generic_count / len(internal_links)) * 20, 20)
        
        # Bonus for distributing links throughout content
        content_links = sum(1 for link in internal_links if 'content' in link.parent_element)
        score += min((content_links / len(internal_links)) * 20, 20)
        
        return max(0.0, min(100.0, score))

    def _calculate_link_equity_distribution(self, internal_links: List[LinkAnalysis]) -> Dict[str, float]:
        """Calculate simplified link equity distribution."""
        if not internal_links:
            return {}
        
        # Count links to each page
        page_counts = Counter(link.url for link in internal_links)
        total_links = len(internal_links)
        
        # Calculate equity percentage
        equity_distribution = {
            url: (count / total_links) * 100 
            for url, count in page_counts.items()
        }
        
        return dict(sorted(equity_distribution.items(), key=lambda x: x[1], reverse=True)[:20])

    def get_link_recommendations(self, structure_analysis: LinkStructureAnalysis) -> List[Dict[str, Any]]:
        """Generate recommendations based on link structure analysis."""
        recommendations = []
        
        # Broken links
        if structure_analysis.broken_links > 0:
            recommendations.append({
                'category': 'Critical',
                'issue': f"{structure_analysis.broken_links} broken links found",
                'recommendation': "Fix or remove all broken links",
                'impact': "High - affects user experience and SEO",
                'priority': 'high'
            })
        
        # Generic anchor text
        if structure_analysis.generic_anchors:
            recommendations.append({
                'category': 'Content',
                'issue': f"{len(structure_analysis.generic_anchors)} generic anchor texts found",
                'recommendation': "Replace generic anchor text with descriptive text",
                'impact': "Medium - missed keyword opportunities",
                'priority': 'medium'
            })
        
        # Internal linking
        if structure_analysis.internal_linking_score < 70:
            recommendations.append({
                'category': 'Structure',
                'issue': f"Internal linking score: {structure_analysis.internal_linking_score:.1f}",
                'recommendation': "Improve internal linking strategy",
                'impact': "Medium - affects page authority distribution",
                'priority': 'medium'
            })
        
        # Link depth
        if structure_analysis.max_depth > 5:
            recommendations.append({
                'category': 'Structure',
                'issue': f"Maximum link depth: {structure_analysis.max_depth}",
                'recommendation': "Flatten site structure for better crawlability",
                'impact': "Medium - affects crawl efficiency",
                'priority': 'medium'
            })
        
        return recommendations 