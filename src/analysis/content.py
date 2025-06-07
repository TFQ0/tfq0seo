"""Content quality analysis and optimization."""

import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from textblob import TextBlob
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.util import ngrams
import re
import math

from .base import BaseAnalyzer
from ..utils.nlp import (
    calculate_readability_scores,
    extract_entities,
    analyze_sentiment
)
from ..monitoring.metrics import AnalysisMetrics

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('maxent_ne_chunker')
nltk.download('words')

@dataclass
class ReadabilityMetrics:
    """Content readability metrics."""
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    gunning_fog: float
    smog_index: float
    automated_readability_index: float
    coleman_liau_index: float
    linsear_write: float
    dale_chall: float
    overall_score: float

@dataclass
class ContentMetrics:
    """Content quality metrics."""
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float
    avg_paragraph_length: float
    avg_word_length: float
    unique_words: int
    lexical_density: float
    readability: ReadabilityMetrics
    sentiment_score: float
    subjectivity_score: float

@dataclass
class TopicRelevance:
    """Topic relevance metrics."""
    topic: str
    relevance_score: float
    coverage_score: float
    missing_subtopics: List[str]
    suggested_subtopics: List[str]

@dataclass
class ContentOptimization:
    """Content optimization suggestions."""
    title_suggestions: List[str]
    meta_description_suggestions: List[str]
    heading_suggestions: List[Dict[str, str]]
    keyword_placement: Dict[str, List[str]]
    content_gaps: List[str]
    improvement_suggestions: List[str]

class ContentAnalyzer(BaseAnalyzer):
    """Analyzes content quality and provides optimization suggestions."""
    
    def __init__(
        self,
        content: str,
        target_keywords: List[str],
        language: str = "en",
        metrics: Optional[AnalysisMetrics] = None
    ):
        """Initialize content analyzer."""
        super().__init__(metrics)
        self.content = content
        self.target_keywords = target_keywords
        self.language = language
        self.stop_words = set(stopwords.words('english'))
        
        # Parse content
        self.soup = BeautifulSoup(content, 'html.parser')
        self.text = self.soup.get_text()
        self.sentences = sent_tokenize(self.text)
        self.words = word_tokenize(self.text)
        self.paragraphs = [p.strip() for p in self.text.split('\n\n') if p.strip()]
    
    def calculate_content_metrics(self) -> ContentMetrics:
        """Calculate content quality metrics."""
        try:
            # Basic metrics
            word_count = len(self.words)
            sentence_count = len(self.sentences)
            paragraph_count = len(self.paragraphs)
            
            # Average lengths
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            avg_paragraph_length = word_count / paragraph_count if paragraph_count > 0 else 0
            avg_word_length = sum(len(w) for w in self.words) / word_count if word_count > 0 else 0
            
            # Lexical diversity
            unique_words = len(set(w.lower() for w in self.words if w.lower() not in self.stop_words))
            lexical_density = unique_words / word_count if word_count > 0 else 0
            
            # Readability
            readability = self._calculate_readability()
            
            # Sentiment analysis
            blob = TextBlob(self.text)
            sentiment_score = blob.sentiment.polarity
            subjectivity_score = blob.sentiment.subjectivity
            
            return ContentMetrics(
                word_count=word_count,
                sentence_count=sentence_count,
                paragraph_count=paragraph_count,
                avg_sentence_length=avg_sentence_length,
                avg_paragraph_length=avg_paragraph_length,
                avg_word_length=avg_word_length,
                unique_words=unique_words,
                lexical_density=lexical_density,
                readability=readability,
                sentiment_score=sentiment_score,
                subjectivity_score=subjectivity_score
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating content metrics: {e}")
            raise
    
    def analyze_topic_relevance(self) -> List[TopicRelevance]:
        """Analyze topic relevance and coverage."""
        try:
            results = []
            
            for keyword in self.target_keywords:
                # Calculate relevance score
                relevance_score = self._calculate_topic_relevance(keyword)
                
                # Calculate coverage score
                coverage_score = self._calculate_topic_coverage(keyword)
                
                # Find missing and suggested subtopics
                missing, suggested = self._analyze_subtopics(keyword)
                
                result = TopicRelevance(
                    topic=keyword,
                    relevance_score=relevance_score,
                    coverage_score=coverage_score,
                    missing_subtopics=missing,
                    suggested_subtopics=suggested
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing topic relevance: {e}")
            raise
    
    def get_optimization_suggestions(self) -> ContentOptimization:
        """Get content optimization suggestions."""
        try:
            # Analyze current content structure
            title = self.soup.title.string if self.soup.title else ""
            meta_desc = self.soup.find(
                'meta',
                attrs={'name': 'description'}
            )
            meta_desc = meta_desc['content'] if meta_desc else ""
            headings = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            # Generate suggestions
            title_suggestions = self._suggest_titles(title)
            meta_suggestions = self._suggest_meta_descriptions(meta_desc)
            heading_suggestions = self._suggest_headings(headings)
            keyword_placement = self._analyze_keyword_placement()
            content_gaps = self._identify_content_gaps()
            improvements = self._suggest_improvements()
            
            return ContentOptimization(
                title_suggestions=title_suggestions,
                meta_description_suggestions=meta_suggestions,
                heading_suggestions=heading_suggestions,
                keyword_placement=keyword_placement,
                content_gaps=content_gaps,
                improvement_suggestions=improvements
            )
            
        except Exception as e:
            self.logger.error(f"Error generating optimization suggestions: {e}")
            raise
    
    async def analyze(self) -> Dict[str, Any]:
        """Perform complete content analysis."""
        try:
            # Calculate metrics
            metrics = self.calculate_content_metrics()
            
            # Analyze topic relevance
            topic_relevance = self.analyze_topic_relevance()
            
            # Get optimization suggestions
            optimization = self.get_optimization_suggestions()
            
            return {
                "metrics": metrics.__dict__,
                "topic_relevance": [t.__dict__ for t in topic_relevance],
                "optimization": optimization.__dict__
            }
            
        except Exception as e:
            self.logger.error(f"Error in content analysis: {e}")
            raise
    
    def _calculate_readability(self) -> ReadabilityMetrics:
        """Calculate various readability scores."""
        try:
            # Calculate basic text statistics
            word_count = len(self.words)
            sentence_count = len(self.sentences)
            syllable_count = sum(self._count_syllables(word) for word in self.words)
            complex_word_count = sum(
                1 for word in self.words
                if self._count_syllables(word) >= 3
            )
            
            # Flesch Reading Ease
            if sentence_count == 0 or word_count == 0:
                flesch_re = 0
            else:
                flesch_re = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
            
            # Flesch-Kincaid Grade Level
            if sentence_count == 0 or word_count == 0:
                flesch_kg = 0
            else:
                flesch_kg = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59
            
            # Gunning Fog Index
            if sentence_count == 0 or word_count == 0:
                gunning_fog = 0
            else:
                gunning_fog = 0.4 * ((word_count / sentence_count) + 100 * (complex_word_count / word_count))
            
            # SMOG Index
            if sentence_count < 30:
                smog = 0
            else:
                smog = 1.0430 * math.sqrt(complex_word_count * (30 / sentence_count)) + 3.1291
            
            # Automated Readability Index
            if sentence_count == 0 or word_count == 0:
                ari = 0
            else:
                char_count = sum(len(word) for word in self.words)
                ari = 4.71 * (char_count / word_count) + 0.5 * (word_count / sentence_count) - 21.43
            
            # Coleman-Liau Index
            if word_count == 0:
                cli = 0
            else:
                char_count = sum(len(word) for word in self.words)
                l = char_count / word_count * 100  # letters per 100 words
                s = sentence_count / word_count * 100  # sentences per 100 words
                cli = 0.0588 * l - 0.296 * s - 15.8
            
            # Linsear Write
            if sentence_count == 0:
                lw = 0
            else:
                easy_word = sum(1 for word in self.words if self._count_syllables(word) < 3)
                hard_word = len(self.words) - easy_word
                lw = (easy_word + hard_word * 3) / sentence_count
                if lw > 20:
                    lw = lw / 2
            
            # Dale-Chall Readability
            if sentence_count == 0 or word_count == 0:
                dc = 0
            else:
                difficult_words = sum(
                    1 for word in self.words
                    if word.lower() not in self._get_dale_chall_words()
                )
                dc = 0.1579 * (difficult_words / word_count * 100) + 0.0496 * (word_count / sentence_count)
                if difficult_words / word_count > 0.05:
                    dc += 3.6365
            
            # Calculate overall score (weighted average)
            weights = {
                'flesch_re': 0.2,
                'flesch_kg': 0.2,
                'gunning_fog': 0.15,
                'smog': 0.15,
                'ari': 0.1,
                'cli': 0.1,
                'lw': 0.05,
                'dc': 0.05
            }
            
            # Normalize scores to 0-100 scale
            normalized_scores = {
                'flesch_re': min(max(flesch_re, 0), 100),
                'flesch_kg': min(max(100 - (flesch_kg * 10), 0), 100),
                'gunning_fog': min(max(100 - (gunning_fog * 10), 0), 100),
                'smog': min(max(100 - (smog * 10), 0), 100),
                'ari': min(max(100 - (ari * 10), 0), 100),
                'cli': min(max(100 - (cli * 10), 0), 100),
                'lw': min(max(lw * 10, 0), 100),
                'dc': min(max(100 - (dc * 10), 0), 100)
            }
            
            overall_score = sum(
                score * weights[metric]
                for metric, score in normalized_scores.items()
            )
            
            return ReadabilityMetrics(
                flesch_reading_ease=flesch_re,
                flesch_kincaid_grade=flesch_kg,
                gunning_fog=gunning_fog,
                smog_index=smog,
                automated_readability_index=ari,
                coleman_liau_index=cli,
                linsear_write=lw,
                dale_chall=dc,
                overall_score=overall_score
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating readability scores: {e}")
            raise
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word."""
        word = word.lower()
        count = 0
        vowels = 'aeiouy'
        
        # Handle special cases
        if word.endswith('e'):
            word = word[:-1]
        
        # Count vowel groups
        prev_char = ''
        for char in word:
            if char in vowels and prev_char not in vowels:
                count += 1
            prev_char = char
        
        # Ensure at least one syllable
        return max(count, 1)
    
    def _get_dale_chall_words(self) -> Set[str]:
        """Get Dale-Chall list of simple words."""
        # This should be loaded from a file in practice
        return set()
    
    def _calculate_topic_relevance(self, topic: str) -> float:
        """Calculate topic relevance score."""
        try:
            # Calculate TF-IDF score
            tf = self.text.lower().count(topic.lower()) / len(self.words)
            # IDF would be calculated based on corpus statistics
            idf = 1.0
            tfidf = tf * idf
            
            # Calculate semantic similarity
            blob = TextBlob(self.text)
            topic_blob = TextBlob(topic)
            semantic_sim = blob.sentiment.polarity * topic_blob.sentiment.polarity
            
            # Combine scores
            relevance = (tfidf * 0.7 + semantic_sim * 0.3)
            return min(max(relevance, 0), 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating topic relevance: {e}")
            return 0.0
    
    def _calculate_topic_coverage(self, topic: str) -> float:
        """Calculate topic coverage score."""
        try:
            # This would use more sophisticated NLP techniques in practice
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating topic coverage: {e}")
            return 0.0
    
    def _analyze_subtopics(
        self,
        topic: str
    ) -> Tuple[List[str], List[str]]:
        """Analyze missing and suggested subtopics."""
        try:
            # This would use topic modeling and knowledge graphs in practice
            return [], []
            
        except Exception as e:
            self.logger.error(f"Error analyzing subtopics: {e}")
            return [], []
    
    def _suggest_titles(self, current_title: str) -> List[str]:
        """Suggest optimized titles."""
        try:
            # This would use more sophisticated NLP techniques in practice
            return []
            
        except Exception as e:
            self.logger.error(f"Error suggesting titles: {e}")
            return []
    
    def _suggest_meta_descriptions(
        self,
        current_meta: str
    ) -> List[str]:
        """Suggest optimized meta descriptions."""
        try:
            # This would use more sophisticated NLP techniques in practice
            return []
            
        except Exception as e:
            self.logger.error(f"Error suggesting meta descriptions: {e}")
            return []
    
    def _suggest_headings(
        self,
        current_headings: List[Any]
    ) -> List[Dict[str, str]]:
        """Suggest optimized headings."""
        try:
            # This would use more sophisticated NLP techniques in practice
            return []
            
        except Exception as e:
            self.logger.error(f"Error suggesting headings: {e}")
            return []
    
    def _analyze_keyword_placement(self) -> Dict[str, List[str]]:
        """Analyze keyword placement and suggest improvements."""
        try:
            # This would use more sophisticated NLP techniques in practice
            return {}
            
        except Exception as e:
            self.logger.error(f"Error analyzing keyword placement: {e}")
            return {}
    
    def _identify_content_gaps(self) -> List[str]:
        """Identify content gaps based on topic analysis."""
        try:
            # This would use more sophisticated NLP techniques in practice
            return []
            
        except Exception as e:
            self.logger.error(f"Error identifying content gaps: {e}")
            return []
    
    def _suggest_improvements(self) -> List[str]:
        """Suggest general content improvements."""
        try:
            suggestions = []
            
            # Word count suggestions
            if len(self.words) < 300:
                suggestions.append(
                    "Content is too short. Aim for at least 300 words for better coverage."
                )
            
            # Sentence length suggestions
            long_sentences = [
                s for s in self.sentences
                if len(word_tokenize(s)) > 20
            ]
            if long_sentences:
                suggestions.append(
                    f"Found {len(long_sentences)} long sentences. "
                    "Consider breaking them down for better readability."
                )
            
            # Paragraph length suggestions
            long_paragraphs = [
                p for p in self.paragraphs
                if len(word_tokenize(p)) > 150
            ]
            if long_paragraphs:
                suggestions.append(
                    f"Found {len(long_paragraphs)} long paragraphs. "
                    "Consider breaking them into smaller chunks."
                )
            
            # Keyword density suggestions
            for keyword in self.target_keywords:
                density = self.text.lower().count(keyword.lower()) / len(self.words)
                if density > 0.02:
                    suggestions.append(
                        f"Keyword '{keyword}' appears too frequently. "
                        "Consider reducing to avoid keyword stuffing."
                    )
                elif density == 0:
                    suggestions.append(
                        f"Keyword '{keyword}' not found in content. "
                        "Consider adding it naturally."
                    )
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error suggesting improvements: {e}")
            return [] 