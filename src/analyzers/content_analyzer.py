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
        """Count meaningful words in text"""
        words = word_tokenize(text.lower())
        return len([w for w in words if w.isalnum()])

    def _count_paragraphs(self, text: str) -> int:
        """Count paragraphs in text"""
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        return len(paragraphs)

    def _analyze_readability(self, text: str) -> Dict:
        """Analyze text readability"""
        blob = TextBlob(text)
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        # Calculate various readability metrics
        word_count = len([w for w in words if w.isalnum()])
        sentence_count = len(sentences)
        syllable_count = sum(self._count_syllables(word) for word in words if word.isalnum())
        
        # Flesch Reading Ease
        if sentence_count > 0:
            flesch = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
        else:
            flesch = 0
            
        return {
            'flesch_reading_ease': flesch,
            'sentiment': {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            },
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0
        }

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word"""
        word = word.lower()
        count = 0
        vowels = 'aeiouy'
        if word[0] in vowels:
            count += 1
        for index in range(1, len(word)):
            if word[index] in vowels and word[index - 1] not in vowels:
                count += 1
        if word.endswith('e'):
            count -= 1
        if count == 0:
            count += 1
        return count

    def _analyze_keywords(self, text: str, target_keyword: str = None) -> Dict:
        """Analyze keyword usage and density"""
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalnum() and word not in self.stop_words]
        
        # Get keyword frequency
        word_freq = Counter(words)
        total_words = len(words)
        
        # Analyze keyword phrases (2-3 words)
        bigrams = list(ngrams(words, 2))
        trigrams = list(ngrams(words, 3))
        
        keyword_analysis = {
            'top_keywords': [
                {
                    'keyword': kw,
                    'count': count,
                    'density': (count / total_words) * 100
                }
                for kw, count in word_freq.most_common(10)
            ],
            'top_phrases': {
                'bigrams': Counter(bigrams).most_common(5),
                'trigrams': Counter(trigrams).most_common(5)
            }
        }
        
        if target_keyword:
            keyword_analysis['target_keyword'] = {
                'count': word_freq.get(target_keyword.lower(), 0),
                'density': (word_freq.get(target_keyword.lower(), 0) / total_words) * 100 if total_words > 0 else 0
            }
            
        return keyword_analysis

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