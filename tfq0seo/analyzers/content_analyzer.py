from typing import Dict, List, Tuple
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.util import ngrams
from collections import Counter
from textblob import TextBlob
import re
from ..utils.error_handler import handle_analysis_error

class ContentAnalyzer:
    """TFQ0SEO Content Analyzer - Analyzes content for SEO optimization"""
    def __init__(self, config: dict):
        self.config = config
        self.thresholds = config['seo_thresholds']
        self.stop_words = set(stopwords.words('english'))
        
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')

    @handle_analysis_error
    def analyze(self, text: str, target_keyword: str = None) -> Dict:
        """Analyze content using TFQ0SEO optimization algorithms.
        
        Performs comprehensive content analysis including:
        - Basic metrics (word count, sentence count)
        - Readability analysis
        - Keyword optimization
        - Content structure
        - Semantic analysis
        - Quality assessment
        """
        # Basic text metrics
        word_count = self._count_words(text)
        sentence_count = len(sent_tokenize(text))
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        analysis = {
            'basic_metrics': {
                'word_count': word_count,
                'sentence_count': sentence_count,
                'avg_sentence_length': avg_sentence_length,
                'paragraph_count': self._count_paragraphs(text)
            },
            'readability': self._analyze_readability(text),
            'keyword_analysis': self._analyze_keywords(text, target_keyword),
            'content_structure': self._analyze_structure(text),
            'semantic_analysis': self._analyze_semantics(text),
            'content_quality': self._analyze_quality(text)
        }
        
        return self._evaluate_content(analysis)

    def _count_words(self, text: str) -> int:
        """Count meaningful words in text with improved accuracy."""
        if not text:
            return 0
        
        # Use the same logic as the main app for consistency
        import re
        
        # Clean the text first
        cleaned_text = self._clean_text_for_analysis(text)
        
        # Split into words and filter
        words = cleaned_text.split()
        meaningful_words = []
        
        for word in words:
            # Remove punctuation and convert to lowercase
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # Skip if empty, too short, or looks like code/CSS/technical terms
            if (len(clean_word) >= 2 and 
                not clean_word.isdigit() and 
                not re.match(r'^(px|em|rem|vh|vw|deg|ms|s)$', clean_word) and
                not re.match(r'^(var|function|return|if|else|for|while|class|id)$', clean_word) and
                clean_word not in self.stop_words):
                meaningful_words.append(clean_word)
        
        return len(meaningful_words)

    def _count_paragraphs(self, text: str) -> int:
        """Count paragraphs in text"""
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        return len(paragraphs)

    def _analyze_readability(self, text: str) -> Dict:
        """Analyze text readability with improved accuracy."""
        if not text or len(text.strip()) == 0:
            return {
                'flesch_reading_ease': 0,
                'sentiment': {'polarity': 0, 'subjectivity': 0},
                'avg_word_length': 0,
                'readability_issues': ['No content to analyze']
            }
        
        blob = TextBlob(text)
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        # Calculate various readability metrics with validation
        word_count = len([w for w in words if w.isalnum()])
        sentence_count = len(sentences)
        
        if sentence_count == 0 or word_count == 0:
            return {
                'flesch_reading_ease': 0,
                'sentiment': {'polarity': 0, 'subjectivity': 0},
                'avg_word_length': 0,
                'readability_issues': ['Insufficient content for analysis']
            }
        
        # Improved syllable counting for accuracy
        syllable_count = sum(self._count_syllables_accurate(word) for word in words if word.isalnum())
        
        # Flesch Reading Ease with validation
        avg_sentence_length = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count
        
        flesch = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        # Validate flesch score
        flesch = max(0, min(100, flesch))
        
        # Identify readability issues
        readability_issues = []
        if avg_sentence_length > 25:
            readability_issues.append("Sentences are too long")
        if avg_syllables_per_word > 2.0:
            readability_issues.append("Words are too complex")
        if flesch < 30:
            readability_issues.append("Text is very difficult to read")
        
        return {
            'flesch_reading_ease': flesch,
            'avg_sentence_length': avg_sentence_length,
            'avg_syllables_per_word': avg_syllables_per_word,
            'sentiment': {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            },
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0,
            'readability_issues': readability_issues
        }

    def _count_syllables_accurate(self, word: str) -> int:
        """Count syllables in a word with improved accuracy."""
        word = word.lower().strip()
        if not word:
            return 0
        
        # Handle common exceptions first
        exceptions = {
            'the': 1, 'a': 1, 'an': 1, 'and': 1, 'or': 1, 'but': 1, 'in': 1, 'on': 1, 'at': 1, 'to': 1, 'for': 1, 'of': 1, 'with': 1, 'by': 1,
            'some': 1, 'time': 1, 'use': 1, 'page': 1, 'make': 1, 'here': 1, 'more': 1, 'code': 1, 'like': 1, 'site': 1
        }
        
        if word in exceptions:
            return exceptions[word]
        
        count = 0
        vowels = 'aeiouy'
        prev_was_vowel = False
        
        for i, char in enumerate(word):
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent e
        if word.endswith('e') and count > 1:
            count -= 1
        
        # Handle special cases
        if word.endswith('le') and len(word) > 2 and word[-3] not in vowels:
            count += 1
        
        # Ensure at least one syllable
        return max(1, count)

    def _analyze_keywords(self, text: str, target_keyword: str = None) -> Dict:
        """Analyze keyword usage and density with improved accuracy."""
        if not text or len(text.strip()) == 0:
            return {
                'top_keywords': [],
                'top_phrases': {'bigrams': [], 'trigrams': []},
                'keyword_stuffing_detected': [],
                'total_meaningful_words': 0,
                'keyword_analysis_issues': ['No content to analyze']
            }
        
        # Clean text first - remove technical terms and code
        cleaned_text = self._clean_text_for_analysis(text)
        
        words = word_tokenize(cleaned_text.lower())
        words = [word for word in words if word.isalnum() and word not in self.stop_words and len(word) >= 2]
        
        # Enhanced technical terms filtering
        technical_terms = {
            'var', 'function', 'return', 'if', 'else', 'for', 'while', 'class', 'id',
            'px', 'em', 'rem', 'vh', 'vw', 'deg', 'ms', 'transform', 'translate3d',
            'webkit', 'moz', 'opacity', 'rgba', 'href', 'src', 'alt', 'title',
            'div', 'span', 'img', 'link', 'script', 'style', 'html', 'body', 'head',
            'css', 'js', 'javascript', 'jquery', 'api', 'url', 'http', 'https',
            'www', 'com', 'org', 'net', 'edu', 'gov'
        }
        
        # Filter out technical terms and common web terms
        words = [word for word in words if word not in technical_terms]
        
        # Get keyword frequency
        word_freq = Counter(words)
        total_words = len(words)
        
        if total_words == 0:
            return {
                'top_keywords': [],
                'top_phrases': {'bigrams': [], 'trigrams': []},
                'keyword_stuffing_detected': [],
                'total_meaningful_words': 0,
                'keyword_analysis_issues': ['No meaningful words found after filtering']
            }
        
        # Analyze keyword phrases (2-3 words) with filtering
        bigrams = list(ngrams(words, 2))
        trigrams = list(ngrams(words, 3))
        
        # Enhanced keyword stuffing detection with better thresholds
        keyword_stuffing_candidates = []
        analysis_issues = []
        
        for word, count in word_freq.most_common(20):
            density = (count / total_words) * 100
            
            # Adjust thresholds based on content length
            if total_words < 100:
                threshold = 5.0  # Higher threshold for short content
            elif total_words < 300:
                threshold = 4.0
            else:
                threshold = 3.0
            
            if density > threshold and count > max(3, total_words // 50):
                keyword_stuffing_candidates.append({
                    'keyword': word,
                    'count': count,
                    'density': density,
                    'severity': 'high' if density > threshold * 1.5 else 'medium'
                })
        
        # Check for overall keyword stuffing patterns
        if len(keyword_stuffing_candidates) > 5:
            analysis_issues.append("Multiple keywords show stuffing patterns")
        
        keyword_analysis = {
            'top_keywords': [
                {
                    'keyword': kw,
                    'count': count,
                    'density': (count / total_words) * 100,
                    'relevance_score': self._calculate_keyword_relevance(kw, text)
                }
                for kw, count in word_freq.most_common(10)
            ],
            'top_phrases': {
                'bigrams': [
                    {
                        'phrase': ' '.join(phrase),
                        'count': count,
                        'density': (count / len(bigrams)) * 100 if bigrams else 0
                    }
                    for phrase, count in Counter(bigrams).most_common(5)
                ],
                'trigrams': [
                    {
                        'phrase': ' '.join(phrase),
                        'count': count,
                        'density': (count / len(trigrams)) * 100 if trigrams else 0
                    }
                    for phrase, count in Counter(trigrams).most_common(5)
                ]
            },
            'keyword_stuffing_detected': keyword_stuffing_candidates,
            'total_meaningful_words': total_words,
            'keyword_analysis_issues': analysis_issues,
            'keyword_diversity': len(word_freq) / total_words if total_words > 0 else 0
        }
        
        # Target keyword analysis with improved accuracy
        if target_keyword:
            target_variations = self._get_keyword_variations(target_keyword.lower())
            target_count = sum(word_freq.get(variation, 0) for variation in target_variations)
            target_density = (target_count / total_words) * 100 if total_words > 0 else 0
            
            keyword_analysis['target_keyword'] = {
                'keyword': target_keyword,
                'count': target_count,
                'density': target_density,
                'variations_found': [var for var in target_variations if word_freq.get(var, 0) > 0],
                'optimization_status': self._assess_keyword_optimization(target_density, total_words)
            }
        
        return keyword_analysis

    def _get_keyword_variations(self, keyword: str) -> List[str]:
        """Get variations of a keyword for more accurate analysis."""
        variations = [keyword]
        
        # Add plural/singular forms
        if keyword.endswith('s'):
            variations.append(keyword[:-1])
        else:
            variations.append(keyword + 's')
        
        # Add common variations
        if keyword.endswith('ing'):
            variations.append(keyword[:-3])
        elif keyword.endswith('ed'):
            variations.append(keyword[:-2])
        
        return variations

    def _calculate_keyword_relevance(self, keyword: str, text: str) -> float:
        """Calculate keyword relevance score based on context."""
        # Simple relevance score based on keyword position and context
        text_lower = text.lower()
        keyword_positions = []
        
        start = 0
        while True:
            pos = text_lower.find(keyword, start)
            if pos == -1:
                break
            keyword_positions.append(pos)
            start = pos + 1
        
        if not keyword_positions:
            return 0.0
        
        # Higher score for keywords appearing early in text
        relevance = sum(1 / (1 + pos / len(text_lower)) for pos in keyword_positions[:5])
        return min(100.0, relevance * 20)

    def _assess_keyword_optimization(self, density: float, total_words: int) -> str:
        """Assess keyword optimization status."""
        if density == 0:
            return "not_optimized"
        elif density < 0.5:
            return "under_optimized"
        elif density <= 2.5:
            return "well_optimized"
        elif density <= 4.0:
            return "over_optimized"
        else:
            return "keyword_stuffing"

    def _clean_text_for_analysis(self, text: str) -> str:
        """Clean text for meaningful content analysis."""
        import re
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove CSS-like patterns
        text = re.sub(r'[a-zA-Z-]+:\s*[^;]+;', '', text)
        
        # Remove JavaScript-like patterns
        text = re.sub(r'function\s*\([^)]*\)\s*{[^}]*}', '', text)
        text = re.sub(r'var\s+\w+\s*=\s*[^;]+;', '', text)
        
        # Remove HTML-like patterns that might have been missed
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text

    def _analyze_structure(self, text: str) -> Dict:
        """Analyze content structure"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        sentences = sent_tokenize(text)
        
        return {
            'paragraph_lengths': [len(word_tokenize(p)) for p in paragraphs],
            'sentence_lengths': [len(word_tokenize(s)) for s in sentences],
            'avg_paragraph_length': sum(len(word_tokenize(p)) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            'content_sections': len(paragraphs)
        }

    def _analyze_semantics(self, text: str) -> Dict:
        """Analyze semantic aspects of the content"""
        blob = TextBlob(text)
        
        return {
            'language_complexity': {
                'unique_words': len(set(word.lower() for word in blob.words)),
                'lexical_density': len(set(word.lower() for word in blob.words)) / len(blob.words) if blob.words else 0
            },
            'sentiment': {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
        }

    def _analyze_quality(self, text: str) -> Dict:
        """Analyze content quality indicators"""
        # Check for common content quality issues
        sentences = sent_tokenize(text)
        
        quality_checks = {
            'duplicate_sentences': self._find_duplicates(sentences),
            'sentence_starters': self._analyze_sentence_starters(sentences),
            'transition_words': self._count_transition_words(text),
            'passive_voice': self._detect_passive_voice(text)
        }
        
        return quality_checks

    def _find_duplicates(self, sentences: List[str]) -> List[str]:
        """Find duplicate sentences"""
        seen = set()
        duplicates = []
        for sentence in sentences:
            normalized = sentence.lower().strip()
            if normalized in seen:
                duplicates.append(sentence)
            seen.add(normalized)
        return duplicates

    def _analyze_sentence_starters(self, sentences: List[str]) -> Dict:
        """Analyze sentence beginnings for variety"""
        starters = [sentence.strip().split()[0].lower() for sentence in sentences if sentence.strip()]
        return dict(Counter(starters).most_common(5))

    def _count_transition_words(self, text: str) -> int:
        """Count transition words and phrases"""
        transition_words = {
            'however', 'therefore', 'furthermore', 'moreover', 'nevertheless',
            'in addition', 'consequently', 'as a result', 'for example'
        }
        count = 0
        for word in transition_words:
            count += len(re.findall(r'\b' + re.escape(word) + r'\b', text.lower()))
        return count

    def _detect_passive_voice(self, text: str) -> Dict:
        """Detect passive voice usage"""
        passive_pattern = r'\b(am|is|are|was|were|be|been|being)\s+(\w+ed|\w+en)\b'
        matches = re.findall(passive_pattern, text.lower())
        return {
            'count': len(matches),
            'examples': matches[:3]  # Return first 3 examples
        }

    def _evaluate_content(self, analysis: Dict) -> Dict:
        """Evaluate content and generate TFQ0SEO recommendations.
        
        Analyzes the content metrics and provides:
        - Content strengths
        - Areas for improvement
        - Actionable recommendations
        - Educational SEO tips
        """
        evaluation = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'education_tips': []
        }
        
        # Evaluate word count
        word_count = analysis['basic_metrics']['word_count']
        if word_count >= self.thresholds['content_length']['min']:
            evaluation['strengths'].append(f"Content length is good ({word_count} words)")
        else:
            evaluation['weaknesses'].append(f"Content length is too short ({word_count} words)")
            evaluation['recommendations'].append(
                f"Increase content length to at least {self.thresholds['content_length']['min']} words"
            )
            evaluation['education_tips'].append(
                "Longer, comprehensive content tends to rank better in search results"
            )

        # Evaluate readability
        flesch_score = analysis['readability']['flesch_reading_ease']
        if flesch_score >= 60:
            evaluation['strengths'].append("Content is easy to read")
        else:
            evaluation['weaknesses'].append("Content might be too difficult to read")
            evaluation['recommendations'].append("Simplify language and sentence structure")
            evaluation['education_tips'].append(
                "Clear, readable content improves user engagement and SEO performance"
            )

        # Evaluate keyword usage
        for keyword_data in analysis['keyword_analysis']['top_keywords']:
            if keyword_data['density'] > self.thresholds['keyword_density']['max']:
                evaluation['weaknesses'].append(
                    f"Possible keyword stuffing detected for '{keyword_data['keyword']}'"
                )
                evaluation['recommendations'].append(
                    f"Reduce usage of '{keyword_data['keyword']}' to avoid over-optimization"
                )
                evaluation['education_tips'].append(
                    "Natural keyword usage is better than forced optimization"
                )

        # Evaluate content structure
        avg_paragraph_length = analysis['content_structure']['avg_paragraph_length']
        if avg_paragraph_length > 150:
            evaluation['weaknesses'].append("Paragraphs are too long")
            evaluation['recommendations'].append("Break down long paragraphs into smaller chunks")
            evaluation['education_tips'].append(
                "Shorter paragraphs improve readability and user experience"
            )

        # Evaluate content quality
        if analysis['content_quality']['duplicate_sentences']:
            evaluation['weaknesses'].append("Found duplicate sentences")
            evaluation['recommendations'].append("Remove or rephrase duplicate content")

        passive_voice = analysis['content_quality']['passive_voice']['count']
        if passive_voice > 5:
            evaluation['weaknesses'].append("High usage of passive voice")
            evaluation['recommendations'].append("Convert passive voice to active voice where possible")
            evaluation['education_tips'].append(
                "Active voice makes content more engaging and easier to understand"
            )

        transition_words = analysis['content_quality']['transition_words']
        if transition_words < 3:
            evaluation['weaknesses'].append("Low usage of transition words")
            evaluation['recommendations'].append("Add more transition words to improve flow")
            evaluation['education_tips'].append(
                "Transition words help create better content flow and readability"
            )

        return evaluation 