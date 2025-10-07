"""Advanced content analyzer with comprehensive quality assessment and SEO optimization checks."""

import re
import math
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter, defaultdict
from bs4 import BeautifulSoup, NavigableString, Tag
import textstat
from dataclasses import dataclass, field
from enum import Enum
import unicodedata


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


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create an enhanced issue dictionary with recommendations."""
    issue = {
        'category': category,
        'severity': severity,  # critical, warning, notice
        'message': message
    }
    if details:
        issue['details'] = details
    
    # Add fix recommendations based on issue type
    if 'word count' in message.lower():
        issue['fix'] = "Add more comprehensive content. Aim for 600-2000 words for blog posts, 300-500 for product pages."
    elif 'readability' in message.lower():
        issue['fix'] = "Simplify sentences, use shorter words, and break up long paragraphs."
    elif 'keyword' in message.lower():
        issue['fix'] = "Distribute keywords naturally throughout the content. Aim for 1-2% keyword density."
    elif 'heading' in message.lower() or 'h1' in message.lower():
        issue['fix'] = "Add proper heading structure: one H1, multiple H2s, and H3s as needed for hierarchy."
    
    return issue


def extract_text_content(soup: BeautifulSoup, preserve_structure: bool = False) -> str:
    """Extract clean text content with optional structure preservation."""
    # Clone soup to avoid modifying original
    soup_copy = BeautifulSoup(str(soup), 'html.parser')
    
    # Remove unwanted elements
    for element in soup_copy(['script', 'style', 'noscript', 'iframe', 'svg']):
        element.decompose()
    
    # Remove hidden elements
    for element in soup_copy.find_all(style=re.compile(r'display:\s*none')):
        element.decompose()
    
    for element in soup_copy.find_all(class_=re.compile(r'(hidden|invisible|hide)')):
        element.decompose()
    
    if preserve_structure:
        # Preserve paragraph and heading structure
        text_parts = []
        for element in soup_copy.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div']):
            text = element.get_text(separator=' ', strip=True)
            if text and len(text) > 20:  # Minimum meaningful text
                text_parts.append(text)
        text = '\n'.join(text_parts)
    else:
        # Get all text
        text = soup_copy.get_text(separator=' ')
    
    # Advanced cleaning
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'[\r\n]+', '\n', text)  # Normalize line breaks
    text = re.sub(r'[^\S\n]+', ' ', text)  # Remove extra spaces but keep line breaks
    text = text.strip()
    
    return text


def detect_language(text: str) -> str:
    """Detect the primary language of the content."""
    # Simple language detection based on character sets
    # In production, use langdetect or similar library
    
    # Check for Arabic
    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'
    
    # Check for Chinese
    if re.search(r'[\u4E00-\u9FFF]', text):
        return 'zh'
    
    # Check for Japanese
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        return 'ja'
    
    # Check for Korean
    if re.search(r'[\uAC00-\uD7AF]', text):
        return 'ko'
    
    # Check for Cyrillic (Russian, etc.)
    if re.search(r'[\u0400-\u04FF]', text):
        return 'ru'
    
    # Default to English
    return 'en'


def analyze_content_structure(soup: BeautifulSoup) -> Dict[str, Any]:
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
    
    # Check for semantic HTML5 elements
    for element in ['article', 'section', 'aside', 'nav', 'main', 'figure']:
        structure['semantic_elements'][element] = len(soup.find_all(element))
    
    # Media elements
    structure['media_elements']['images'] = len(soup.find_all('img'))
    structure['media_elements']['videos'] = len(soup.find_all(['video', 'iframe']))
    structure['media_elements']['audio'] = len(soup.find_all('audio'))
    
    # Check for infographics (images with certain patterns)
    for img in soup.find_all('img'):
        alt_text = img.get('alt', '').lower()
        src = img.get('src', '').lower()
        if any(word in alt_text or word in src for word in ['infographic', 'chart', 'graph', 'diagram']):
            structure['media_elements']['infographics'] += 1
    
    # Interactive elements
    structure['interactive_elements']['forms'] = len(soup.find_all('form'))
    structure['interactive_elements']['buttons'] = len(soup.find_all(['button', 'input[type="submit"]']))
    structure['interactive_elements']['links'] = len(soup.find_all('a', href=True))
    structure['interactive_elements']['tables'] = len(soup.find_all('table'))
    
    # Detect introduction and conclusion
    paragraphs = soup.find_all('p')
    if paragraphs:
        first_para_text = paragraphs[0].get_text().lower()
        intro_keywords = ['introduction', 'welcome', 'this article', 'this post', 'we will', 'let\'s explore']
        structure['has_introduction'] = any(keyword in first_para_text for keyword in intro_keywords)
        
        if len(paragraphs) > 1:
            last_para_text = paragraphs[-1].get_text().lower()
            conclusion_keywords = ['conclusion', 'summary', 'in conclusion', 'to sum up', 'finally', 'in summary']
            structure['has_conclusion'] = any(keyword in last_para_text for keyword in conclusion_keywords)
    
    # Detect call-to-action
    cta_patterns = [
        r'(sign up|subscribe|download|get started|learn more|contact us|buy now|shop now|register)',
        r'(click here|find out|discover|explore|try it)',
        r'(limited time|don\'t miss|act now|today only)'
    ]
    
    text = extract_text_content(soup).lower()
    for pattern in cta_patterns:
        if re.search(pattern, text):
            structure['has_call_to_action'] = True
            break
    
    return structure


def calculate_advanced_readability(text: str, language: str = 'en') -> Dict[str, Any]:
    """Calculate comprehensive readability metrics."""
    metrics = {}
    
    if language != 'en':
        # For non-English content, use basic metrics
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        metrics['word_count'] = len(words)
        metrics['sentence_count'] = len([s for s in sentences if s.strip()])
        metrics['average_sentence_length'] = len(words) / max(1, len(sentences))
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
            
    except Exception as e:
        metrics['error'] = str(e)
    
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
    """Detect various content quality issues."""
    issues = []
    
    # Check for Lorem Ipsum or placeholder text
    placeholder_patterns = [
        r'lorem ipsum',
        r'coming soon',
        r'under construction',
        r'placeholder',
        r'sample text',
        r'test content'
    ]
    
    text_lower = text.lower()
    for pattern in placeholder_patterns:
        if re.search(pattern, text_lower):
            issues.append({
                'type': 'placeholder_content',
                'severity': 'critical',
                'message': f'Placeholder content detected: "{pattern}"'
            })
    
    # Check for excessive use of passive voice
    passive_indicators = [
        r'was \w+ed by',
        r'were \w+ed by',
        r'is being \w+ed',
        r'has been \w+ed',
        r'will be \w+ed'
    ]
    
    passive_count = 0
    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences:
        for pattern in passive_indicators:
            if re.search(pattern, sentence.lower()):
                passive_count += 1
                break
    
    if len(sentences) > 0:
        passive_ratio = passive_count / len(sentences)
        if passive_ratio > 0.3:
            issues.append({
                'type': 'passive_voice',
                'severity': 'notice',
                'message': f'Excessive passive voice usage ({passive_count} sentences, {passive_ratio*100:.1f}%)'
            })
    
    # Check for keyword cannibalization
    h1_tags = soup.find_all('h1')
    h2_tags = soup.find_all('h2')
    
    if len(h1_tags) > 1:
        h1_texts = [h1.get_text().lower() for h1 in h1_tags]
        # Check for similar H1s
        for i, h1_1 in enumerate(h1_texts):
            for h1_2 in h1_texts[i+1:]:
                similarity = len(set(h1_1.split()) & set(h1_2.split())) / max(len(h1_1.split()), len(h1_2.split()))
                if similarity > 0.7:
                    issues.append({
                        'type': 'keyword_cannibalization',
                        'severity': 'warning',
                        'message': 'Multiple similar H1 tags may cause keyword cannibalization'
                    })
                    break
    
    # Check for thin content sections
    sections = soup.find_all(['section', 'article', 'div'])
    thin_sections = 0
    for section in sections:
        section_text = section.get_text(strip=True)
        if len(section_text) > 0 and len(section_text.split()) < 50:
            thin_sections += 1
    
    if thin_sections > 3:
        issues.append({
            'type': 'thin_content_sections',
            'severity': 'notice',
            'message': f'{thin_sections} sections with very little content (<50 words)'
        })
    
    # Check for outdated content indicators
    current_year = 2024  # Update this
    old_year_pattern = r'\b(19[0-9]{2}|200[0-9]|201[0-5])\b'
    old_years = re.findall(old_year_pattern, text)
    if old_years and len(old_years) > 2:
        issues.append({
            'type': 'potentially_outdated',
            'severity': 'notice',
            'message': f'Content contains old year references: {", ".join(set(old_years)[:5])}'
        })
    
    return issues


def calculate_content_score(metrics: Dict[str, Any], issues: List[Dict[str, Any]]) -> Tuple[float, str]:
    """Calculate overall content score and quality level."""
    score = 100.0
    
    # Word count scoring
    word_count = metrics.get('word_count', 0)
    if word_count < 100:
        score -= 25
    elif word_count < 300:
        score -= 15
    elif word_count < 600:
        score -= 5
    elif word_count > 2500:
        score -= 3  # Very long content may need splitting
    
    # Readability scoring
    if 'readability' in metrics:
        fre = metrics['readability'].get('flesch_reading_ease', 60)
        if fre < 30:
            score -= 15  # Very difficult
        elif fre < 50:
            score -= 7  # Difficult
        elif fre > 80:
            score += 5  # Easy to read
    
    # Structure scoring
    if 'structure' in metrics:
        structure = metrics['structure']
        if structure.get('semantic_elements', {}).get('article', 0) > 0:
            score += 3
        if structure.get('has_introduction'):
            score += 2
        if structure.get('has_conclusion'):
            score += 2
        if structure.get('has_call_to_action'):
            score += 3
    
    # Media scoring
    if 'structure' in metrics:
        media = metrics['structure'].get('media_elements', {})
        if media.get('images', 0) > 0:
            score += 5
        if media.get('videos', 0) > 0:
            score += 3
    
    # Deduct for issues
    for issue in issues:
        severity = issue.get('severity', 'notice')
        if severity == 'critical':
            score -= 15
        elif severity == 'warning':
            score -= 7
        elif severity == 'notice':
            score -= 2
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
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


def analyze_content(soup: BeautifulSoup, url: str, target_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """Enhanced content analysis with comprehensive quality assessment."""
    issues = []
    data = {}
    
    # Extract text with structure preservation
    text = extract_text_content(soup, preserve_structure=True)
    plain_text = extract_text_content(soup, preserve_structure=False)
    
    # Detect language
    language = detect_language(plain_text)
    data['language'] = language
    
    # Basic metrics
    words = plain_text.split()
    word_count = len(words)
    sentences = re.split(r'[.!?]+', plain_text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    # Calculate comprehensive metrics
    metrics = ContentMetrics(
        word_count=word_count,
        sentence_count=sentence_count,
        paragraph_count=len(soup.find_all('p')),
        unique_words=len(set(words)),
        lexical_diversity=len(set(words)) / max(1, word_count),
        avg_sentence_length=word_count / max(1, sentence_count),
        avg_paragraph_length=word_count / max(1, len(soup.find_all('p'))),
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
    
    # Word count analysis
    if word_count < 300:
        issues.append(create_issue('Content', 'warning', 
            f'Low word count ({word_count}), recommended minimum 300 words for SEO'))
    elif word_count < 600:
        issues.append(create_issue('Content', 'notice', 
            f'Moderate word count ({word_count}), consider expanding to 600+ words'))
    elif word_count > 3000:
        issues.append(create_issue('Content', 'notice',
            f'Very long content ({word_count} words), consider splitting into multiple pages'))
    
    # Readability analysis
    if word_count >= 100:
        readability = calculate_advanced_readability(plain_text, language)
        data['readability'] = readability
        
        if language == 'en' and 'flesch_reading_ease' in readability:
            fre = readability['flesch_reading_ease']
            if fre < 30:
                issues.append(create_issue('Content', 'warning', 
                    f'Very difficult to read (Flesch score: {fre})'))
            elif fre < 50:
                issues.append(create_issue('Content', 'notice',
                    f'Fairly difficult to read (Flesch score: {fre})'))
            
            # Check grade level
            grade = readability.get('consensus_grade', 12)
            if grade > 12:
                issues.append(create_issue('Content', 'notice',
                    f'College-level reading required (grade {grade})'))
    
    # Content structure analysis
    structure = analyze_content_structure(soup)
    data['structure'] = structure
    
    # Check for important structural elements
    if not structure['has_introduction']:
        issues.append(create_issue('Content', 'notice',
            'No clear introduction detected'))
    
    if word_count > 500 and not structure['has_conclusion']:
        issues.append(create_issue('Content', 'notice',
            'No clear conclusion detected for long-form content'))
    
    if not structure['has_call_to_action']:
        issues.append(create_issue('Content', 'notice',
            'No call-to-action detected'))
    
    # Heading analysis
    headings = {
        'h1': soup.find_all('h1'),
        'h2': soup.find_all('h2'),
        'h3': soup.find_all('h3'),
        'h4': soup.find_all('h4'),
        'h5': soup.find_all('h5'),
        'h6': soup.find_all('h6')
    }
    
    heading_structure = {k: len(v) for k, v in headings.items()}
    data['heading_structure'] = heading_structure
    
    # H1 analysis
    if heading_structure['h1'] == 0:
        issues.append(create_issue('Content', 'critical', 'No H1 heading found'))
    elif heading_structure['h1'] > 1:
        issues.append(create_issue('Content', 'warning',
            f'Multiple H1 headings ({heading_structure["h1"]}), should have only one'))
    else:
        h1_text = headings['h1'][0].get_text()
        h1_length = len(h1_text)
        if h1_length < 20:
            issues.append(create_issue('Content', 'notice',
                f'H1 heading too short ({h1_length} characters)'))
        elif h1_length > 70:
            issues.append(create_issue('Content', 'notice',
                f'H1 heading too long ({h1_length} characters), aim for 20-70'))
    
    # Check heading hierarchy
    if heading_structure['h3'] > 0 and heading_structure['h2'] == 0:
        issues.append(create_issue('Content', 'notice',
            'H3 headings found without H2 headings (improper hierarchy)'))
    
    if word_count > 300 and heading_structure['h2'] == 0:
        issues.append(create_issue('Content', 'warning',
            'No H2 headings found, consider adding subheadings for better structure'))
    
    # Keyword optimization analysis
    keyword_analysis = analyze_keyword_optimization(plain_text, target_keywords)
    data['keyword_analysis'] = keyword_analysis
    
    # Check for keyword stuffing
    for keyword, density in keyword_analysis['keyword_density'].items():
        if density > 3.0:
            issues.append(create_issue('Content', 'warning',
                f'Possible keyword stuffing: "{keyword}" appears with {density}% density'))
            break
    
    # Check keyword placement in headings
    if target_keywords:
        keywords_in_headings = []
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            for level, tags in headings.items():
                for tag in tags:
                    if keyword_lower in tag.get_text().lower():
                        keywords_in_headings.append(keyword)
                        break
        
        keyword_analysis['keyword_placement']['in_headings'] = keywords_in_headings
        
        if not keywords_in_headings:
            issues.append(create_issue('Content', 'notice',
                'Target keywords not found in any headings'))
    
    # Media optimization
    images = soup.find_all('img')
    data['image_analysis'] = {
        'total_images': len(images),
        'images_with_alt': 0,
        'images_with_title': 0,
        'lazy_loaded_images': 0,
        'responsive_images': 0
    }
    
    for img in images:
        if img.get('alt'):
            data['image_analysis']['images_with_alt'] += 1
        if img.get('title'):
            data['image_analysis']['images_with_title'] += 1
        if img.get('loading') == 'lazy':
            data['image_analysis']['lazy_loaded_images'] += 1
        if img.get('srcset') or 'responsive' in img.get('class', []):
            data['image_analysis']['responsive_images'] += 1
    
    if images and data['image_analysis']['images_with_alt'] < len(images):
        missing_alt = len(images) - data['image_analysis']['images_with_alt']
        issues.append(create_issue('Content', 'warning',
            f'{missing_alt} images missing alt text'))
    
    if word_count > 500 and len(images) == 0:
        issues.append(create_issue('Content', 'notice',
            'No images found in long-form content, consider adding visual elements'))
    
    # Lists and formatting
    ul_count = len(soup.find_all('ul'))
    ol_count = len(soup.find_all('ol'))
    data['list_usage'] = {
        'unordered_lists': ul_count,
        'ordered_lists': ol_count,
        'total_lists': ul_count + ol_count
    }
    
    if word_count > 500 and data['list_usage']['total_lists'] == 0:
        issues.append(create_issue('Content', 'notice',
            'No lists found, consider using bullet points for better readability'))
    
    # Detect content issues
    content_issues = detect_content_issues(plain_text, soup)
    for issue in content_issues:
        issues.append(create_issue('Content', issue['severity'], issue['message']))
    
    # Check for duplicate content
    sentences_list = [s.strip() for s in sentences if len(s.strip()) > 30]
    if sentences_list:
        sentence_counts = Counter(sentences_list)
        repeated = [s for s, count in sentence_counts.items() if count > 1]
        if repeated:
            issues.append(create_issue('Content', 'warning',
                f'Found {len(repeated)} repeated sentences'))
            data['repeated_sentences'] = repeated[:3]  # Store first 3 for reference
    
    # Schema markup suggestions
    schema_suggestions = []
    
    # Detect content type for schema suggestions
    if any(word in plain_text.lower() for word in ['recipe', 'ingredients', 'cook', 'prep time']):
        schema_suggestions.append('Recipe')
    if any(word in plain_text.lower() for word in ['faq', 'frequently asked', 'question', 'answer']):
        schema_suggestions.append('FAQPage')
    if any(word in plain_text.lower() for word in ['how to', 'step by step', 'tutorial', 'guide']):
        schema_suggestions.append('HowTo')
    if any(word in plain_text.lower() for word in ['review', 'rating', 'stars', 'pros and cons']):
        schema_suggestions.append('Review')
    if any(word in plain_text.lower() for word in ['article', 'author', 'published', 'written by']):
        schema_suggestions.append('Article')
    
    if schema_suggestions:
        data['schema_suggestions'] = schema_suggestions
        issues.append(create_issue('Content', 'notice',
            f'Consider adding schema markup: {", ".join(schema_suggestions)}'))
    
    # Calculate overall content score
    all_metrics = {
        'word_count': word_count,
        'readability': data.get('readability', {}),
        'structure': structure
    }
    
    score, quality = calculate_content_score(all_metrics, issues)
    
    # Add quality assessment
    data['quality_assessment'] = {
        'score': round(score, 1),
        'quality_level': quality,
        'strengths': [],
        'weaknesses': []
    }
    
    # Identify strengths
    if word_count >= 600:
        data['quality_assessment']['strengths'].append('Good content length')
    if structure['has_call_to_action']:
        data['quality_assessment']['strengths'].append('Has call-to-action')
    if len(images) > 0:
        data['quality_assessment']['strengths'].append('Includes visual content')
    if metrics.lexical_diversity > 0.5:
        data['quality_assessment']['strengths'].append('Good vocabulary diversity')
    
    # Identify weaknesses
    if word_count < 300:
        data['quality_assessment']['weaknesses'].append('Content too short')
    if 'readability' in data and data['readability'].get('flesch_reading_ease', 60) < 40:
        data['quality_assessment']['weaknesses'].append('Difficult to read')
    if heading_structure['h1'] != 1:
        data['quality_assessment']['weaknesses'].append('H1 issues')
    
    return {
        'score': max(0, score),
        'issues': issues,
        'data': data
    }