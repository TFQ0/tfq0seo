"""Content analyzer for readability, keyword density, and content quality."""

import re
from typing import Dict, List, Any, Optional
from collections import Counter
from bs4 import BeautifulSoup
import textstat


def create_issue(category: str, severity: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a simple issue dictionary."""
    issue = {
        'category': category,
        'severity': severity,  # critical, warning, notice
        'message': message
    }
    if details:
        issue['details'] = details
    return issue


def extract_text_content(soup: BeautifulSoup) -> str:
    """Extract clean text content from HTML."""
    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()
    
    # Get text
    text = soup.get_text(separator=' ')
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def calculate_keyword_density(text: str, top_n: int = 10) -> Dict[str, float]:
    """Calculate keyword density for top N words."""
    # Remove punctuation and convert to lowercase
    words = re.findall(r'\b[a-z]+\b', text.lower())
    
    # Filter out common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
                  'before', 'after', 'above', 'below', 'between', 'under', 'is', 'are',
                  'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
                  'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
                  'shall', 'if', 'then', 'else', 'when', 'where', 'why', 'how', 'all',
                  'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
                  'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'}
    
    words = [w for w in words if w not in stop_words and len(w) > 2]
    
    if not words:
        return {}
    
    # Count word frequency
    word_count = Counter(words)
    total_words = len(words)
    
    # Calculate density for top N words
    keyword_density = {}
    for word, count in word_count.most_common(top_n):
        density = (count / total_words) * 100
        keyword_density[word] = round(density, 2)
    
    return keyword_density


def analyze_content(soup: BeautifulSoup, url: str, target_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """Analyze content quality and readability."""
    issues = []
    score = 100
    data = {}
    
    # Extract text content
    text = extract_text_content(soup)
    
    # Word count
    words = text.split()
    word_count = len(words)
    data['word_count'] = word_count
    
    if word_count < 300:
        issues.append(create_issue('Content', 'warning', f'Low word count ({word_count}), recommended minimum 300 words for SEO'))
        score -= 15
    elif word_count < 600:
        issues.append(create_issue('Content', 'notice', f'Moderate word count ({word_count}), consider expanding to 600+ words'))
        score -= 5
    
    # Character count
    char_count = len(text)
    data['character_count'] = char_count
    
    # Readability scores
    if word_count >= 100:  # Need minimum text for accurate scores
        try:
            # Flesch Reading Ease (0-100, higher is easier)
            flesch_score = textstat.flesch_reading_ease(text)
            data['flesch_reading_ease'] = round(flesch_score, 1)
            
            if flesch_score < 30:
                issues.append(create_issue('Content', 'warning', f'Very difficult to read (Flesch score: {flesch_score:.1f})'))
                score -= 10
            elif flesch_score < 50:
                issues.append(create_issue('Content', 'notice', f'Fairly difficult to read (Flesch score: {flesch_score:.1f})'))
                score -= 5
            
            # Flesch-Kincaid Grade Level
            fk_grade = textstat.flesch_kincaid_grade(text)
            data['flesch_kincaid_grade'] = round(fk_grade, 1)
            
            if fk_grade > 12:
                issues.append(create_issue('Content', 'notice', f'College-level reading required (grade {fk_grade:.1f})'))
                score -= 5
            
            # Automated Readability Index
            ari = textstat.automated_readability_index(text)
            data['automated_readability_index'] = round(ari, 1)
            
            # SMOG Index
            smog = textstat.smog_index(text)
            data['smog_index'] = round(smog, 1)
            
            # Coleman-Liau Index
            coleman = textstat.coleman_liau_index(text)
            data['coleman_liau_index'] = round(coleman, 1)
            
            # Average scores
            avg_grade = (fk_grade + ari + smog + coleman) / 4
            data['average_grade_level'] = round(avg_grade, 1)
            
        except Exception as e:
            issues.append(create_issue('Content', 'notice', f'Could not calculate readability scores: {str(e)}'))
    else:
        issues.append(create_issue('Content', 'warning', 'Content too short for readability analysis (minimum 100 words)'))
        score -= 10
    
    # Heading structure
    headings = {
        'h1': len(soup.find_all('h1')),
        'h2': len(soup.find_all('h2')),
        'h3': len(soup.find_all('h3')),
        'h4': len(soup.find_all('h4')),
        'h5': len(soup.find_all('h5')),
        'h6': len(soup.find_all('h6'))
    }
    data['heading_structure'] = headings
    
    # Check heading hierarchy
    if headings['h1'] == 0:
        issues.append(create_issue('Content', 'critical', 'No H1 heading found'))
        score -= 15
    elif headings['h1'] > 1:
        issues.append(create_issue('Content', 'warning', f'Multiple H1 headings ({headings['h1']}), should have only one'))
        score -= 10
    
    if headings['h2'] == 0 and word_count > 300:
        issues.append(create_issue('Content', 'warning', 'No H2 headings found, consider adding subheadings for better structure'))
        score -= 5
    
    # Check for heading hierarchy issues
    if headings['h3'] > 0 and headings['h2'] == 0:
        issues.append(create_issue('Content', 'notice', 'H3 headings found without H2 headings (improper hierarchy)'))
        score -= 3
    
    # Keyword density
    if word_count >= 50:
        keyword_density = calculate_keyword_density(text)
        data['keyword_density'] = keyword_density
        
        # Check for keyword stuffing
        for keyword, density in keyword_density.items():
            if density > 5.0:
                issues.append(create_issue('Content', 'warning', f'Possible keyword stuffing: "{keyword}" appears with {density}% density'))
                score -= 5
                break
    
    # Check target keywords if provided
    if target_keywords and text:
        text_lower = text.lower()
        keywords_found = {}
        keywords_missing = []
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            count = text_lower.count(keyword_lower)
            if count > 0:
                keywords_found[keyword] = count
            else:
                keywords_missing.append(keyword)
        
        data['target_keywords_found'] = keywords_found
        data['target_keywords_missing'] = keywords_missing
        
        if keywords_missing:
            issues.append(create_issue('Content', 'notice', f'Target keywords not found: {", ".join(keywords_missing)}'))
            score -= 3 * len(keywords_missing)
    
    # Paragraph structure
    paragraphs = soup.find_all('p')
    paragraph_count = len(paragraphs)
    data['paragraph_count'] = paragraph_count
    
    if paragraph_count > 0:
        # Average paragraph length
        paragraph_lengths = [len(p.get_text().split()) for p in paragraphs]
        avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths)
        data['average_paragraph_length'] = round(avg_paragraph_length, 1)
        
        # Check for very long paragraphs
        long_paragraphs = [l for l in paragraph_lengths if l > 150]
        if long_paragraphs:
            issues.append(create_issue('Content', 'notice', f'{len(long_paragraphs)} very long paragraphs (>150 words), consider breaking them up'))
            score -= 3
    
    # Lists (bullet points)
    ul_count = len(soup.find_all('ul'))
    ol_count = len(soup.find_all('ol'))
    data['unordered_lists'] = ul_count
    data['ordered_lists'] = ol_count
    
    if word_count > 500 and ul_count == 0 and ol_count == 0:
        issues.append(create_issue('Content', 'notice', 'No lists found, consider using bullet points for better readability'))
        score -= 3
    
    # Images
    images = soup.find_all('img')
    image_count = len(images)
    data['image_count'] = image_count
    
    if word_count > 500 and image_count == 0:
        issues.append(create_issue('Content', 'notice', 'No images found, consider adding visual content'))
        score -= 5
    
    # Check for duplicate content (simplified check)
    # In production, you'd want to check against other pages
    sentences = re.split(r'[.!?]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if sentences:
        # Check for repeated sentences
        sentence_counts = Counter(sentences)
        repeated = [s for s, count in sentence_counts.items() if count > 1]
        if repeated:
            issues.append(create_issue('Content', 'warning', f'Found {len(repeated)} repeated sentences'))
            score -= 5
    
    return {
        'score': max(0, score),
        'issues': issues,
        'data': data
    }
