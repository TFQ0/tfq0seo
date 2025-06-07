"""Backlink analysis and quality assessment."""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup

from .base import BaseAnalyzer
from ..utils.html import extract_text_from_html
from ..monitoring.metrics import AnalysisMetrics

@dataclass
class BacklinkMetrics:
    """Backlink metrics."""
    url: str
    domain: str
    anchor_text: str
    link_type: str  # 'dofollow', 'nofollow', 'ugc', 'sponsored'
    context_relevance: float

class BacklinkAnalyzer(BaseAnalyzer):
    """Analyzes backlink profile and quality."""
    
    def __init__(self, metrics: Optional[AnalysisMetrics] = None):
        """Initialize analyzer."""
        super().__init__(metrics)
    
    async def analyze_backlink(
        self,
        url: str,
        anchor: str,
        link_type: str
    ) -> BacklinkMetrics:
        """Analyze a single backlink.
        
        Args:
            url: Backlink URL
            anchor: Anchor text
            link_type: Link type (dofollow, nofollow, etc.)
            
        Returns:
            BacklinkMetrics object with analysis results
        """
        try:
            domain = urlparse(url).netloc
            
            # Calculate context relevance
            context_relevance = await self._calculate_context_relevance(url)
            
            return BacklinkMetrics(
                url=url,
                domain=domain,
                anchor_text=anchor,
                link_type=link_type,
                context_relevance=context_relevance
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing backlink {url}: {e}")
            raise
    
    async def analyze_backlinks(
        self,
        backlinks: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Analyze multiple backlinks.
        
        Args:
            backlinks: List of backlink dictionaries with url, anchor, and type
            
        Returns:
            Analysis results including metrics and recommendations
        """
        try:
            # Analyze each backlink
            metrics = []
            for backlink in backlinks:
                metric = await self.analyze_backlink(
                    backlink['url'],
                    backlink['anchor'],
                    backlink.get('type', 'dofollow')
                )
                metrics.append(metric)
            
            # Calculate aggregate metrics
            total_backlinks = len(metrics)
            dofollow_count = len([m for m in metrics if m.link_type == 'dofollow'])
            nofollow_count = len([m for m in metrics if m.link_type == 'nofollow'])
            avg_relevance = sum(m.context_relevance for m in metrics) / total_backlinks if total_backlinks > 0 else 0
            
            # Group by domain
            domains = {}
            for metric in metrics:
                if metric.domain not in domains:
                    domains[metric.domain] = []
                domains[metric.domain].append(metric)
            
            # Analyze anchor text diversity
            anchor_texts = {}
            for metric in metrics:
                anchor = metric.anchor_text.lower()
                anchor_texts[anchor] = anchor_texts.get(anchor, 0) + 1
            
            # Generate recommendations
            recommendations = []
            
            if nofollow_count / total_backlinks > 0.7:
                recommendations.append("High proportion of nofollow links")
            
            if avg_relevance < 0.5:
                recommendations.append("Low average contextual relevance")
            
            if len(domains) < total_backlinks * 0.3:
                recommendations.append("Low domain diversity")
            
            if len(anchor_texts) < total_backlinks * 0.4:
                recommendations.append("Low anchor text diversity")
            
            return {
                'metrics': {
                    'total_backlinks': total_backlinks,
                    'unique_domains': len(domains),
                    'dofollow_ratio': dofollow_count / total_backlinks if total_backlinks > 0 else 0,
                    'avg_relevance': avg_relevance,
                    'anchor_diversity': len(anchor_texts) / total_backlinks if total_backlinks > 0 else 0
                },
                'recommendations': recommendations,
                'backlinks': [metric.__dict__ for metric in metrics]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing backlinks: {e}")
            raise
    
    async def _calculate_context_relevance(self, url: str) -> float:
        """Calculate contextual relevance of a link."""
        try:
            # Fetch page content
            async with self.session.get(url) as response:
                html = await response.text()
                
            # Extract text
            text = extract_text_from_html(BeautifulSoup(html, 'html.parser'))
            
            # Calculate relevance score (simple implementation)
            # In practice, you would use NLP techniques here
            relevant_keywords = ['seo', 'search', 'engine', 'optimization']
            words = text.lower().split()
            matches = sum(1 for word in words if word in relevant_keywords)
            
            # Return normalized score
            return min(matches / 10, 1.0)  # Cap at 1.0
            
        except Exception:
            return 0.0 