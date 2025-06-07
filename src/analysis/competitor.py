"""Competitor analysis and market position tracking."""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse

from .base import BaseAnalyzer
from ..utils.metrics import calculate_similarity_score
from ..utils.html import extract_text_from_html
from ..monitoring.metrics import AnalysisMetrics

@dataclass
class CompetitorMetrics:
    """Competitor website metrics."""
    domain: str
    page_count: int
    avg_word_count: float
    keyword_density: Dict[str, float]
    ssl_enabled: bool
    mobile_friendly: bool

class CompetitorAnalyzer(BaseAnalyzer):
    """Analyzes competitor websites and tracks market position."""
    
    def __init__(self, metrics: Optional[AnalysisMetrics] = None):
        """Initialize analyzer."""
        super().__init__(metrics)
    
    async def analyze_website(self, url: str) -> CompetitorMetrics:
        """Analyze a competitor website.
        
        Args:
            url: Website URL to analyze
            
        Returns:
            CompetitorMetrics object with analysis results
        """
        try:
            # Fetch and analyze main page
            async with self.session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract text content
                text = extract_text_from_html(soup)
                words = text.split()
                
                # Calculate keyword density
                keyword_density = self._calculate_keyword_density(text)
                
                # Check SSL
                ssl_enabled = response.url.scheme == 'https'
                
                # Check mobile-friendly (basic check)
                viewport_meta = soup.find(
                    'meta',
                    attrs={'name': 'viewport'}
                )
                mobile_friendly = viewport_meta is not None
                
                return CompetitorMetrics(
                    domain=urlparse(url).netloc,
                    page_count=await self._get_page_count(url),
                    avg_word_count=len(words),
                    keyword_density=keyword_density,
                    ssl_enabled=ssl_enabled,
                    mobile_friendly=mobile_friendly
                )
                
        except Exception as e:
            self.logger.error(f"Error analyzing website {url}: {e}")
            raise
    
    async def analyze_market_position(
        self,
        target_metrics: CompetitorMetrics,
        competitor_metrics: List[CompetitorMetrics]
    ) -> Dict[str, Any]:
        """Analyze market position relative to competitors."""
        position = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': []
        }
        
        # Compare metrics
        avg_word_count = sum(c.avg_word_count for c in competitor_metrics) / len(competitor_metrics)
        if target_metrics.avg_word_count > avg_word_count:
            position['strengths'].append('Above average content length')
        else:
            position['weaknesses'].append('Below average content length')
            position['opportunities'].append('Increase content depth')
        
        # Compare technical aspects
        if target_metrics.ssl_enabled:
            position['strengths'].append('SSL enabled')
        else:
            position['weaknesses'].append('SSL not enabled')
            position['opportunities'].append('Enable SSL')
        
        if target_metrics.mobile_friendly:
            position['strengths'].append('Mobile friendly')
        else:
            position['weaknesses'].append('Not mobile friendly')
            position['opportunities'].append('Improve mobile experience')
        
        # Identify threats
        stronger_competitors = [
            c for c in competitor_metrics
            if c.avg_word_count > target_metrics.avg_word_count
            and c.ssl_enabled
            and c.mobile_friendly
        ]
        
        if stronger_competitors:
            position['threats'].extend([
                f"Competitor {c.domain} has better overall metrics"
                for c in stronger_competitors
            ])
        
        return position
    
    async def _get_page_count(self, url: str) -> int:
        """Get approximate page count from sitemap."""
        try:
            sitemap_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/sitemap.xml"
            async with self.session.get(sitemap_url) as response:
                if response.status == 200:
                    text = await response.text()
                    soup = BeautifulSoup(text, 'xml')
                    return len(soup.find_all('url'))
                return 0
        except:
            return 0
    
    def _calculate_keyword_density(self, text: str) -> Dict[str, float]:
        """Calculate keyword density in text."""
        words = text.lower().split()
        total_words = len(words)
        if total_words == 0:
            return {}
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            if len(word) > 2:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Calculate density
        return {
            word: count / total_words
            for word, count in word_freq.items()
        } 