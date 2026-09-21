"""Advanced content analyzer with comprehensive quality assessment and SEO optimization checks."""

import re
import math
import hashlib
from zipfile import BadZipFile
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter, defaultdict
from bs4 import BeautifulSoup, NavigableString, Tag
import textstat
from dataclasses import dataclass, field
from enum import Enum
import unicodedata
from .common import heading_facts, make_issue
from ..page_facts import PageFacts, ensure_page_facts, extract_content_text
from ..rules import RuleDefinition, RuleCollector, register_rules, score_findings, recommendations_for


_CONTENT_REFERENCE = 'https://developers.google.com/search/docs/fundamentals/creating-helpful-content'
_READABILITY_REFERENCE = 'https://www.w3.org/WAI/WCAG22/Understanding/reading-level.html'
CONTENT_RULES = (
    RuleDefinition('content.readability_difficult', 'content', 'notice',
        'Review the reading difficulty for the intended audience; offer a simpler explanation or supplemental content when useful.',
        'English text with at least 100 whitespace-delimited words and an available Flesch estimate; editorial review only.',
        (_READABILITY_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('content.readability_grade', 'content', 'notice',
        'Check whether specialist vocabulary suits the intended readers and explain unfamiliar concepts when needed.',
        'English text with at least 100 whitespace-delimited words and an available estimated grade; this is not a WCAG conformance test.',
        (_READABILITY_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('content.target_keywords_headings', 'content', 'notice',
        'Review whether headings describe their sections clearly. Include supplied topic terms only when natural and relevant.',
        'A caller supplied target keywords; exact phrase absence does not establish a search ranking problem.',
        (_CONTENT_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('content.placeholder_content', 'content', 'notice',
        'Review the matched text in context and replace it only if it is unfinished copy rather than intentional content.',
        'Static text contains a known English placeholder phrase; page intent requires human review.',
        (_CONTENT_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('content.passive_voice', 'content', 'notice',
        'Review the matched sentences for clarity. Passive voice may be appropriate for the subject and audience.',
        'English text matches a simple passive-voice pattern in more than 30% of sampled sentences; a local editorial heuristic.',
        (_READABILITY_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('content.similar_h1', 'content', 'notice',
        'Check whether the similar headings identify distinct sections. Similar headings alone do not establish keyword cannibalization.',
        'At least two H1 elements have high token overlap; the 70% threshold is a local review heuristic.',
        ('https://www.w3.org/WAI/tutorials/page-structure/headings/',), '2026-09-14', scored=False),
    RuleDefinition('content.short_sections', 'content', 'notice',
        'Review whether each section fulfills its purpose; there is no minimum section word count for search rankings.',
        'More than three section, article, or div elements contain fewer than 50 whitespace-delimited words; local descriptive heuristic only.',
        (_CONTENT_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('content.historical_years', 'content', 'notice',
        'Verify dates only if the page is intended to describe current information. Preserve accurate historical references.',
        'Text contains at least three references to years before 2016; historical dates do not establish outdated content.',
        (_CONTENT_REFERENCE,), '2026-09-14', scored=False),
    RuleDefinition('content.repeated_sentences', 'content', 'notice',
        'Review repeated sentences in context and remove only unintended repetition.',
        'The same sentence longer than 30 characters appears more than once in this document; quotations and repeated interface text may be intentional.',
        (_CONTENT_REFERENCE,), '2026-09-14', scored=False),
)
register_rules(CONTENT_RULES)


class ContentQuality(Enum):
    """Content quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    VERY_POOR = "very_poor"


@dataclass
class ContentMetrics:
    """Container for content metrics."""
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    unique_words: int = 0
    lexical_diversity: float = 0.0
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0
    reading_time_minutes: float = 0.0
    speaking_time_minutes: float = 0.0


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None,
                 rule_id: Optional[str] = None, evidence: Any = None,
                 confidence: str = 'high') -> Dict[str, Any]:
    """Compatibility helper; registered rule identity supplies the guidance."""
    return make_issue(category, severity, message, details, rule_id, evidence,
                      confidence=confidence)


def extract_text_content(soup: BeautifulSoup, preserve_structure: bool = False) -> str:
    """Compatibility entry point for the shared nonmutating text extractor."""
    return extract_content_text(soup, preserve_structure)


def detect_language(text: str, declared_language: Optional[str] = None) -> str:
    """Prefer the document language; return und when the evidence is insufficient."""
    if declared_language and re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', declared_language.strip()):
        return declared_language.strip().split('-')[0].lower()
    letters = sum(unicodedata.category(char).startswith('L') for char in text)
    if not letters:
        return 'und'
    kana = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF]', text))
    han = len(re.findall(r'[\u4E00-\u9FFF]', text))
    if kana and (kana + han) / letters > 0.5:
        return 'ja'
    if han / letters > 0.5:
        return 'zh'
    if len(re.findall(r'[\u0600-\u06FF]', text)) / letters > 0.5:
        return 'ar'
    if len(re.findall(r'[\uAC00-\uD7AF]', text)) / letters > 0.5:
        return 'ko'
    # Latin and Cyrillic scripts do not identify a language by themselves.
    return 'und'


def analyze_content_structure(soup: BeautifulSoup, language: str = 'und',
                              plain_text: Optional[str] = None, *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Analyze the structural elements of content."""
    structure = {
        'has_introduction': False,
        'has_conclusion': False,
        'has_call_to_action': False,
        'content_blocks': [],
        'media_elements': {
            'images': 0,
            'videos': 0,
            'audio': 0,
            'infographics': 0
        },
        'interactive_elements': {
            'forms': 0,
            'buttons': 0,
            'links': 0,
            'tables': 0
        },
        'semantic_elements': {
            'article': 0,
            'section': 0,
            'aside': 0,
            'nav': 0,
            'main': 0,
            'figure': 0
        }
    }
    
    counts = facts.tag_counts if facts is not None else None
    images = [record['attrs'] for record in facts.images] if facts is not None else soup.find_all('img')

    def count(tag):
        return counts.get(tag, 0) if counts is not None else len(soup.find_all(tag))

    # Check for semantic HTML5 elements
    for element in ['article', 'section', 'aside', 'nav', 'main', 'figure']:
        structure['semantic_elements'][element] = count(element)
    
    # Media elements
    structure['media_elements']['images'] = len(images)
    structure['media_elements']['videos'] = count('video') + count('iframe')
    structure['media_elements']['audio'] = count('audio')
    
    # Check for infographics (images with certain patterns)
    for img in images:
        alt_text = img.get('alt', '').lower()
        src = img.get('src', '').lower()
        if any(word in alt_text or word in src for word in ['infographic', 'chart', 'graph', 'diagram']):
            structure['media_elements']['infographics'] += 1
    
    # Interactive elements
    structure['interactive_elements']['forms'] = count('form')
    structure['interactive_elements']['buttons'] = len(soup.select('button, input[type="submit"]'))
    structure['interactive_elements']['links'] = len(facts.anchors) if facts is not None else len(soup.find_all('a', href=True))
    structure['interactive_elements']['tables'] = count('table')
    
    # Detect introduction and conclusion
    paragraphs = facts.paragraphs if facts is not None else [paragraph.get_text() for paragraph in soup.find_all('p')]
    if paragraphs and language == 'en':
        first_para_text = paragraphs[0].lower()
        intro_keywords = ['introduction', 'welcome', 'this article', 'this post', 'we will', 'let\'s explore']
        structure['has_introduction'] = any(keyword in first_para_text for keyword in intro_keywords)
        
        if len(paragraphs) > 1:
            last_para_text = paragraphs[-1].lower()
            conclusion_keywords = ['conclusion', 'summary', 'in conclusion', 'to sum up', 'finally', 'in summary']
            structure['has_conclusion'] = any(keyword in last_para_text for keyword in conclusion_keywords)
    
    # Detect call-to-action
    cta_patterns = [
        r'(sign up|subscribe|download|get started|learn more|contact us|buy now|shop now|register)',
        r'(click here|find out|discover|explore|try it)',
        r'(limited time|don\'t miss|act now|today only)'
    ]
    
    text = (plain_text if plain_text is not None else extract_text_content(soup)).lower()
    for pattern in cta_patterns if language == 'en' else []:
        if re.search(pattern, text):
            structure['has_call_to_action'] = True
            break
    if language != 'en':
        for key in ('has_introduction', 'has_conclusion', 'has_call_to_action'):
            structure[key] = None
    structure['editorial_detection_status'] = 'heuristic' if language == 'en' else 'not_applicable'
    
    return structure


_READABILITY_VALUES = (
    'flesch_reading_ease', 'flesch_kincaid_grade', 'gunning_fog', 'smog_index',
    'ari', 'coleman_liau', 'linsear_write', 'dale_chall', 'consensus_grade',
    'reading_time_seconds', 'speaking_time_seconds', 'lexical_diversity',
    'syllable_count', 'polysyllable_count', 'sentence_count', 'average_sentence_length',
    'reading_level',
)


def _readability_resource_error() -> Optional[str]:
    """Check local corpus availability before textstat's automatic download path.

    Older textstat releases use packaged Pyphen/CMU dictionaries. Releases with
    the backend package call nltk.download when corpora/cmudict is absent;
    nltk.data.find itself only checks local paths and archives.
    """
    if getattr(textstat, 'backend', None) is None:
        return None
    try:
        import nltk.data
        nltk.data.find('corpora/cmudict')
    except (ImportError, LookupError, OSError, BadZipFile):
        return ('Readability is unavailable because the installed textstat backend requires '
                'local NLTK corpora/cmudict data. Runtime resource downloads are disabled.')
    return None


def calculate_advanced_readability(text: str, language: str = 'en') -> Dict[str, Any]:
    """Calculate readability estimates using installed, local resources only."""
    metrics = {}
    
    if language != 'en':
        # For non-English content, use basic metrics
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        metrics['word_count'] = len(words)
        metrics['sentence_count'] = len([s for s in sentences if s.strip()])
        metrics['average_sentence_length'] = len(words) / max(1, len(sentences))
        metrics.update(status='not_applicable', source='local_text_statistics',
                       reason='English readability formulas are not applicable to this language.')
        return metrics

    metrics = dict.fromkeys(_READABILITY_VALUES)
    metrics.update(status='unavailable', source='textstat', resource_policy='local_only')
    resource_error = _readability_resource_error()
    if resource_error:
        metrics.update(error=resource_error, reason=resource_error,
                       missing_resources=['nltk:corpora/cmudict'])
        return metrics

    try:
        # Standard readability scores
        metrics['flesch_reading_ease'] = round(textstat.flesch_reading_ease(text), 1)
        metrics['flesch_kincaid_grade'] = round(textstat.flesch_kincaid_grade(text), 1)
        metrics['gunning_fog'] = round(textstat.gunning_fog(text), 1)
        metrics['smog_index'] = round(textstat.smog_index(text), 1)
        metrics['ari'] = round(textstat.automated_readability_index(text), 1)
        metrics['coleman_liau'] = round(textstat.coleman_liau_index(text), 1)
        metrics['linsear_write'] = round(textstat.linsear_write_formula(text), 1)
        metrics['dale_chall'] = round(textstat.dale_chall_readability_score(text), 1)
        
        # Consensus grade level
        metrics['consensus_grade'] = round(textstat.text_standard(text, float_output=True), 1)
        
        # Reading and speaking time
        metrics['reading_time_seconds'] = round(textstat.reading_time(text, ms_per_char=14.69))
        metrics['speaking_time_seconds'] = round(len(text.split()) / 150 * 60)  # 150 words per minute
        
        # Lexical diversity
        words = text.lower().split()
        unique_words = set(words)
        metrics['lexical_diversity'] = round(len(unique_words) / max(1, len(words)), 3)
        
        # Syllable statistics
        metrics['syllable_count'] = textstat.syllable_count(text)
        metrics['polysyllable_count'] = textstat.polysyllabcount(text)
        
        # Sentence complexity
        metrics['sentence_count'] = textstat.sentence_count(text)
        metrics['average_sentence_length'] = round(len(words) / max(1, metrics['sentence_count']), 1)
        
        # Determine reading level
        fre = metrics['flesch_reading_ease']
        if fre >= 90:
            metrics['reading_level'] = 'Very Easy (5th grade)'
        elif fre >= 80:
            metrics['reading_level'] = 'Easy (6th grade)'
        elif fre >= 70:
            metrics['reading_level'] = 'Fairly Easy (7th grade)'
        elif fre >= 60:
            metrics['reading_level'] = 'Standard (8-9th grade)'
        elif fre >= 50:
            metrics['reading_level'] = 'Fairly Difficult (10-12th grade)'
        elif fre >= 30:
            metrics['reading_level'] = 'Difficult (College)'
        else:
            metrics['reading_level'] = 'Very Difficult (Graduate)'

        metrics.update(status='estimate', missing_resources=[])
    except Exception as e:
        metrics.update(dict.fromkeys(_READABILITY_VALUES))
        metrics.update(error=str(e), reason='The local readability calculation could not be completed.')
    
    return metrics


def analyze_keyword_optimization(text: str, target_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """Advanced keyword analysis with semantic understanding."""
    analysis = {
        'keyword_density': {},
        'keyword_prominence': {},
        'keyword_consistency': {},
        'lsi_keywords': [],
        'keyword_variations': {},
        'keyword_placement': {
            'in_first_100_words': [],
            'in_headings': [],
            'in_last_100_words': []
        }
    }
    
    # Clean and tokenize text
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    word_positions = {i: word for i, word in enumerate(words)}
    total_words = len(words)
    
    if not words:
        return analysis
    
    # Remove stop words for meaningful analysis
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
        'shall', 'if', 'then', 'else', 'when', 'where', 'why', 'how', 'all',
        'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'this',
        'that', 'these', 'those', 'what', 'which', 'who', 'whom', 'whose', 'i',
        'me', 'my', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its',
        'we', 'us', 'our', 'they', 'them', 'their', 'am', 'as', 'there', 'here'
    }
    
    meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Calculate keyword density for top keywords
    word_freq = Counter(meaningful_words)
    for word, count in word_freq.most_common(20):
        density = (count / total_words) * 100
        analysis['keyword_density'][word] = round(density, 2)
    
    # Analyze target keywords if provided
    if target_keywords:
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            keyword_words = keyword_lower.split()
            
            # Single word keyword
            if len(keyword_words) == 1:
                count = words.count(keyword_lower)
                if count > 0:
                    density = (count / total_words) * 100
                    analysis['keyword_density'][keyword] = round(density, 2)
                    
                    # Find positions for prominence
                    positions = [i for i, w in word_positions.items() if w == keyword_lower]
                    if positions:
                        # Calculate prominence (earlier = better)
                        avg_position = sum(positions) / len(positions)
                        prominence = 1 - (avg_position / total_words)
                        analysis['keyword_prominence'][keyword] = round(prominence, 3)
            
            # Multi-word keyword (phrase)
            else:
                phrase_count = text.lower().count(keyword_lower)
                if phrase_count > 0:
                    # Approximate density for phrases
                    density = (phrase_count * len(keyword_words) / total_words) * 100
                    analysis['keyword_density'][keyword] = round(density, 2)
            
            # Check placement
            first_100 = ' '.join(words[:100])
            last_100 = ' '.join(words[-100:])
            
            if keyword_lower in first_100:
                analysis['keyword_placement']['in_first_100_words'].append(keyword)
            if keyword_lower in last_100:
                analysis['keyword_placement']['in_last_100_words'].append(keyword)
            
            # Find variations (stemming, plurals, etc.)
            keyword_stem = keyword_lower.rstrip('s').rstrip('ing').rstrip('ed')
            variations = []
            for word in set(meaningful_words):
                if word.startswith(keyword_stem) and word != keyword_lower:
                    variations.append(word)
            if variations:
                analysis['keyword_variations'][keyword] = variations[:5]
    
    # Identify LSI (Latent Semantic Indexing) keywords
    # These are related words that often appear together
    bigrams = Counter(zip(meaningful_words, meaningful_words[1:]))
    trigrams = Counter(zip(meaningful_words, meaningful_words[1:], meaningful_words[2:]))
    
    # Find common phrases
    common_bigrams = [' '.join(gram) for gram, count in bigrams.most_common(10) if count > 2]
    common_trigrams = [' '.join(gram) for gram, count in trigrams.most_common(5) if count > 2]
    
    analysis['lsi_keywords'] = common_bigrams + common_trigrams
    
    return analysis


def detect_content_issues(text: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Return registered editorial observations with the legacy type keys."""
    collector = RuleCollector('content')
    html = soup.find('html')
    language = detect_language(text, html.get('lang') if html else None)
    _detect_content_rules(text, soup, collector, language)
    return collector.issues


def _detect_content_rules(text: str, soup: BeautifulSoup, collector: RuleCollector,
                          language: str, *, facts: Optional[PageFacts] = None) -> None:
    patterns = ('lorem ipsum', 'coming soon', 'under construction', 'placeholder', 'sample text', 'test content')
    matches = [phrase for phrase in patterns if phrase in text.lower()]
    result = collector.check('content.placeholder_content', bool(matches),
        evidence={'matched_phrases': matches}, category='Content', confidence='low',
        message=f'Possible placeholder phrases found: {", ".join(matches)}')
    result['type'] = 'placeholder_content'

    sentences = [sentence.strip() for sentence in re.split(r'[.!?]+', text) if sentence.strip()]
    passive_patterns = (r'was \w+ed by', r'were \w+ed by', r'is being \w+ed', r'has been \w+ed', r'will be \w+ed')
    passive = [sentence for sentence in sentences if any(re.search(pattern, sentence.lower()) for pattern in passive_patterns)]
    passive_ratio = len(passive) / len(sentences) if sentences else 0
    result = collector.check('content.passive_voice', passive_ratio > 0.3,
        evidence={'sentences': passive, 'sentence_count': len(sentences), 'ratio': passive_ratio, 'threshold': 0.3, 'language': language},
        applicable=language == 'en' and bool(sentences), reason='Requires English text with identifiable sentences.',
        category='Content', confidence='low',
        message=f'Passive-voice patterns found in {len(passive)} sentences ({passive_ratio * 100:.1f}% of the sample)')
    result['type'] = 'passive_voice'

    h1_texts = ([heading['text'].lower() for heading in facts.headings['headings']['h1']] if facts is not None
                else [heading.get_text(' ', strip=True).lower() for heading in soup.find_all('h1')])
    similar = []
    for index, first in enumerate(h1_texts):
        for second in h1_texts[index + 1:]:
            similarity = len(set(first.split()) & set(second.split())) / max(1, len(first.split()), len(second.split()))
            if similarity > 0.7:
                similar.append({'first': first, 'second': second, 'token_overlap': similarity})
    result = collector.check('content.similar_h1', bool(similar),
        evidence={'pairs': similar, 'h1_count': len(h1_texts), 'threshold': 0.7}, applicable=len(h1_texts) > 1,
        reason='Requires at least two H1 headings.', category='Content', confidence='low',
        message=f'{len(similar)} H1 pairs share similar wording; review whether this is intentional')
    result['type'] = 'keyword_cannibalization'

    sections = soup.find_all(['section', 'article', 'div'])
    short_sections = []
    for index, section in enumerate(sections):
        section_text = section.get_text(' ', strip=True)
        count = len(section_text.split())
        if section_text and count < 50:
            short_sections.append({'index': index, 'element': section.name, 'word_count': count})
    result = collector.check('content.short_sections', len(short_sections) > 3,
        evidence={'sections': short_sections, 'count': len(short_sections), 'word_threshold': 50, 'language': language},
        applicable=bool(sections) and language not in ('zh', 'ja'), reason='Requires sections and a supported whitespace word count.',
        category='Content', confidence='low', message=f'{len(short_sections)} sections contain fewer than 50 whitespace-delimited words; length alone is not a quality problem')
    result['type'] = 'thin_content_sections'

    years = re.findall(r'\b(19[0-9]{2}|200[0-9]|201[0-5])\b', text)
    result = collector.check('content.historical_years', len(years) > 2,
        evidence={'years': years, 'cutoff_year': 2016}, category='Content', confidence='low',
        message=f'Historical year references found: {", ".join(sorted(set(years))[:5])}; review only if this page should describe current events')
    result['type'] = 'potentially_outdated'


def calculate_content_score(metrics: Dict[str, Any], issues: List[Dict[str, Any]]) -> Tuple[float, str]:
    """Calculate overall content score and quality level."""
    score = score_findings(issues)
    
    # Determine quality level
    if score >= 90:
        quality = ContentQuality.EXCELLENT
    elif score >= 75:
        quality = ContentQuality.GOOD
    elif score >= 60:
        quality = ContentQuality.AVERAGE
    elif score >= 40:
        quality = ContentQuality.POOR
    else:
        quality = ContentQuality.VERY_POOR
    
    return score, quality.value


def analyze_content(soup: BeautifulSoup, url: str, target_keywords: Optional[List[str]] = None,
                    *, facts: Optional[PageFacts] = None) -> Dict[str, Any]:
    """Enhanced content analysis with comprehensive quality assessment."""
    page_facts = ensure_page_facts(soup, url, facts=facts)
    collector = RuleCollector('content')
    data = {}
    
    # Extract text with structure preservation
    plain_text = page_facts.content_text
    
    # Detect language
    declared_language = page_facts.language
    language = detect_language(plain_text, declared_language)
    data['language'] = language
    data['language_source'] = 'html_lang' if declared_language and language != 'und' else 'script_heuristic' if language != 'und' else 'unknown'
    data['score_scope'] = 'static_content_checks'
    
    # Basic metrics
    words = plain_text.split()
    word_count = len(words)
    sentences = re.split(r'[.!?]+', plain_text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    # Calculate comprehensive metrics
    metrics = ContentMetrics(
        word_count=word_count,
        sentence_count=sentence_count,
        paragraph_count=len(page_facts.paragraphs),
        unique_words=len(set(words)),
        lexical_diversity=len(set(words)) / max(1, word_count),
        avg_sentence_length=word_count / max(1, sentence_count),
        avg_paragraph_length=word_count / max(1, len(page_facts.paragraphs)),
        reading_time_minutes=word_count / 200,  # Average reading speed
        speaking_time_minutes=word_count / 150  # Average speaking speed
    )
    
    data['metrics'] = {
        'word_count': metrics.word_count,
        'sentence_count': metrics.sentence_count,
        'paragraph_count': metrics.paragraph_count,
        'unique_words': metrics.unique_words,
        'lexical_diversity': round(metrics.lexical_diversity, 3),
        'avg_sentence_length': round(metrics.avg_sentence_length, 1),
        'avg_paragraph_length': round(metrics.avg_paragraph_length, 1),
        'reading_time_minutes': round(metrics.reading_time_minutes, 1),
        'speaking_time_minutes': round(metrics.speaking_time_minutes, 1)
    }
    data['metrics']['word_count_method'] = 'whitespace'
    data['metrics']['reading_time_status'] = 'estimate'
    if language in ('zh', 'ja'):
        data['metrics'].update(word_count=None, unique_words=None, lexical_diversity=None,
                               avg_sentence_length=None, avg_paragraph_length=None,
                               reading_time_minutes=None, speaking_time_minutes=None,
                               word_count_method='unavailable', reading_time_status='unknown')
    
    # Readability analysis
    readability = {}
    if word_count >= 100:
        readability = calculate_advanced_readability(plain_text, language)
        data['readability'] = readability
    fre = readability.get('flesch_reading_ease')
    grade = readability.get('consensus_grade')
    readability_applies = language == 'en' and word_count >= 100
    for rule_id, value, failed, label, threshold in (
        ('content.readability_difficult', fre, fre < 50 if fre is not None else None, 'Flesch reading ease', 50),
        ('content.readability_grade', grade, grade > 12 if grade is not None else None, 'Estimated reading grade', 12),
    ):
        collector.check(rule_id, failed,
            evidence={'metric': label, 'value': value, 'threshold': threshold, 'language': language,
                      'word_count': word_count, 'error': readability.get('error'),
                      'measurement_status': readability.get('status'), 'source': readability.get('source')},
            applicable=readability_applies, reason=(readability.get('reason') if readability_applies and value is None
                else None) or 'Requires English text with at least 100 words and a readability estimate.',
            category='Content', confidence='low', message=f'{label}: {value}; review suitability for the intended audience')
    
    # Content structure analysis
    structure = analyze_content_structure(soup, language, plain_text, facts=page_facts)
    data['structure'] = structure
    
    # Heading observations are shared with the SEO analyzer.
    heading_data = page_facts.headings
    headings = heading_data['headings']
    data['heading_structure'] = {level: len(records) for level, records in headings.items()}

    for rule_id in ('headings.missing_h1', 'headings.empty', 'headings.skipped_level'):
        matches = [finding for finding in heading_data['findings'] if finding['rule_id'] == rule_id]
        collector.check(rule_id, bool(matches), category='Content',
            message='; '.join(finding['message'] for finding in matches),
            evidence={'headings': heading_data['headings'], 'findings': matches})
    
    # Keyword optimization analysis
    keyword_analysis = analyze_keyword_optimization(plain_text, target_keywords)
    data['keyword_analysis'] = keyword_analysis
    
    keyword_analysis['status'] = 'descriptive_statistics'
    if language in ('zh', 'ja'):
        keyword_analysis['keyword_density'] = {}
        keyword_analysis['status'] = 'not_applicable'
    
    # Check keyword placement in headings
    keywords_in_headings = []
    if target_keywords:
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            for level, tags in headings.items():
                for tag in tags:
                    if keyword_lower in tag['text'].lower():
                        keywords_in_headings.append(keyword)
                        break
        
        keyword_analysis['keyword_placement']['in_headings'] = keywords_in_headings
        
    collector.check('content.target_keywords_headings', not keywords_in_headings,
        evidence={'target_keywords': target_keywords or [], 'matched_keywords': keywords_in_headings,
                  'headings': heading_data['headings']}, applicable=bool(target_keywords),
        reason='Requires caller-supplied target keywords.', category='Content', confidence='low',
        message='Target keyword phrases not found in headings; assess relevance in context')
    
    # Media optimization
    images = [record['attrs'] for record in page_facts.images]
    data['image_analysis'] = {
        'total_images': len(images),
        'images_with_alt': 0,
        'images_with_title': 0,
        'lazy_loaded_images': 0,
        'responsive_images': 0
    }
    
    for img in images:
        if 'alt' in img:
            data['image_analysis']['images_with_alt'] += 1
        if img.get('title'):
            data['image_analysis']['images_with_title'] += 1
        if img.get('loading') == 'lazy':
            data['image_analysis']['lazy_loaded_images'] += 1
        if img.get('srcset') or 'responsive' in img.get('class', []):
            data['image_analysis']['responsive_images'] += 1
    
    missing_alt = [dict(index=index, src=image.get('src', '')) for index, image in enumerate(images) if 'alt' not in image]
    collector.check('images.missing_alt', bool(missing_alt), applicable=bool(images),
        reason='Requires image elements.', category='Content',
        message=f'{len(missing_alt)} images missing alt attributes',
        evidence={'count': len(missing_alt), 'images': missing_alt})
    
    # Lists and formatting
    tag_counts = page_facts.tag_counts
    ul_count = tag_counts.get('ul', 0)
    ol_count = tag_counts.get('ol', 0)
    data['list_usage'] = {
        'unordered_lists': ul_count,
        'ordered_lists': ol_count,
        'total_lists': ul_count + ol_count
    }
    
    # Detect content issues
    _detect_content_rules(plain_text, soup, collector, language, facts=page_facts)
    
    # Check for duplicate content
    sentences_list = [s.strip() for s in sentences if len(s.strip()) > 30]
    sentence_counts = Counter(sentences_list)
    repeated = [sentence for sentence, count in sentence_counts.items() if count > 1]
    collector.check('content.repeated_sentences', bool(repeated), applicable=bool(sentences_list),
        reason='Requires sentences longer than 30 characters.', category='Content', confidence='low',
        message=f'Found {len(repeated)} repeated sentences; review whether repetition is intentional',
        evidence={'sentences': [{'text': sentence, 'count': sentence_counts[sentence]} for sentence in repeated],
                  'minimum_characters': 30})
    if repeated:
        data['repeated_sentences'] = repeated[:3]
    
    # Schema markup suggestions
    schema_suggestions = []
    
    # Detect content type for schema suggestions
    if any(word in plain_text.lower() for word in ['recipe', 'ingredients', 'cook', 'prep time']):
        schema_suggestions.append('Recipe')
    if any(word in plain_text.lower() for word in ['review', 'rating', 'stars', 'pros and cons']):
        schema_suggestions.append('Review')
    if any(word in plain_text.lower() for word in ['article', 'author', 'published', 'written by']):
        schema_suggestions.append('Article')
    
    if schema_suggestions and language == 'en':
        data['schema_suggestions'] = schema_suggestions
    
    # Calculate overall content score
    all_metrics = {
        'word_count': word_count,
        'readability': data.get('readability', {}),
        'structure': structure
    }
    
    issues = collector.issues
    score, quality = calculate_content_score(all_metrics, issues)
    
    # Add quality assessment
    data['quality_assessment'] = {
        'score': round(score, 1),
        'quality_level': quality,
        'strengths': [],
        'weaknesses': []
    }
    
    # Identify strengths
    if structure['has_call_to_action']:
        data['quality_assessment']['strengths'].append('Has call-to-action')
    if len(images) > 0:
        data['quality_assessment']['strengths'].append('Includes visual content')
    if metrics.lexical_diversity > 0.5:
        data['quality_assessment']['strengths'].append('Good vocabulary diversity')
    
    # Identify weaknesses
    if fre is not None and fre < 40:
        data['quality_assessment']['weaknesses'].append('Difficult to read')
    if heading_data['issues']:
        data['quality_assessment']['weaknesses'].append('H1 issues')
    
    return {
        'score': max(0, score),
        'issues': issues,
        'data': data,
        'recommendations': recommendations_for(issues),
        'rule_results': collector.results,
        'rule_coverage': collector.coverage,
    }
