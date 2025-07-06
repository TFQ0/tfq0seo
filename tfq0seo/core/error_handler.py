"""
Enhanced Error Handler for tfq0seo

This module provides comprehensive error handling with user-friendly messages,
recovery strategies, and partial result extraction.
"""

from typing import Dict, Any, Optional, List, Union
import logging
import traceback
from enum import Enum
import re
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can occur during analysis"""
    TIMEOUT = "timeout"
    PARSING_ERROR = "parsing_error"
    CONNECTION_ERROR = "connection_error"
    ENCODING_ERROR = "encoding_error"
    MEMORY_ERROR = "memory_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT = "rate_limit"
    INVALID_HTML = "invalid_html"
    JAVASCRIPT_REQUIRED = "javascript_required"
    BLOCKED_BY_ROBOTS = "blocked_by_robots"
    SSL_ERROR = "ssl_error"
    UNKNOWN = "unknown"


class SmartErrorHandler:
    """Intelligent error handler that provides user-friendly feedback and recovery"""
    
    def __init__(self):
        self.error_patterns = {
            ErrorType.TIMEOUT: {
                'user_message': 'This page took too long to load.',
                'impact': 'We couldn\'t analyze all aspects of this page',
                'recommendation': 'Check with your hosting provider about server response times',
                'recovery_actions': ['partial_content_analysis', 'basic_meta_extraction'],
                'technical_details': 'Connection timeout after {timeout}s',
                'severity': 'warning'
            },
            
            ErrorType.PARSING_ERROR: {
                'user_message': 'We had trouble reading this page\'s HTML structure.',
                'impact': 'Some SEO checks may be incomplete',
                'recommendation': 'Validate your HTML at validator.w3.org to find and fix markup errors',
                'recovery_actions': ['partial_analysis', 'regex_fallback'],
                'technical_details': 'HTML parsing failed: {error}',
                'severity': 'warning'
            },
            
            ErrorType.CONNECTION_ERROR: {
                'user_message': 'We couldn\'t connect to this page.',
                'impact': 'This page couldn\'t be analyzed',
                'recommendation': 'Check if the URL is correct and the server is running',
                'recovery_actions': ['retry_with_different_method'],
                'technical_details': 'Connection failed: {error}',
                'severity': 'critical'
            },
            
            ErrorType.ENCODING_ERROR: {
                'user_message': 'This page uses an unusual character encoding.',
                'impact': 'Some text content might not display correctly',
                'recommendation': 'Ensure your pages use UTF-8 encoding',
                'recovery_actions': ['force_utf8', 'encoding_detection'],
                'technical_details': 'Encoding error: {error}',
                'severity': 'notice'
            },
            
            ErrorType.JAVASCRIPT_REQUIRED: {
                'user_message': 'This page requires JavaScript to display content.',
                'impact': 'SEO analysis is limited because search engines may have similar issues',
                'recommendation': 'Ensure critical content is available without JavaScript',
                'recovery_actions': ['analyze_static_content', 'check_noscript_tags'],
                'technical_details': 'Page appears to be a JavaScript SPA',
                'severity': 'warning'
            },
            
            ErrorType.SSL_ERROR: {
                'user_message': 'There\'s an SSL/HTTPS security issue with this page.',
                'impact': 'Browsers will show security warnings to visitors',
                'recommendation': 'Fix SSL certificate issues immediately',
                'recovery_actions': ['try_http_fallback'],
                'technical_details': 'SSL error: {error}',
                'severity': 'critical'
            },
            
            ErrorType.RATE_LIMIT: {
                'user_message': 'The website is limiting our analysis speed.',
                'impact': 'Analysis is proceeding slowly to respect server limits',
                'recommendation': 'This is normal - we\'re being respectful of the server',
                'recovery_actions': ['slow_down_requests', 'implement_backoff'],
                'technical_details': 'Rate limit detected',
                'severity': 'notice'
            },
            
            ErrorType.BLOCKED_BY_ROBOTS: {
                'user_message': 'This page is blocked by robots.txt.',
                'impact': 'Search engines are also blocked from accessing this page',
                'recommendation': 'Review your robots.txt file if you want this page indexed',
                'recovery_actions': ['check_robots_txt'],
                'technical_details': 'Blocked by robots.txt',
                'severity': 'warning'
            }
        }
        
        self.recovery_strategies = {
            'partial_content_analysis': self._partial_content_analysis,
            'basic_meta_extraction': self._basic_meta_extraction,
            'regex_fallback': self._regex_fallback,
            'force_utf8': self._force_utf8_encoding,
            'analyze_static_content': self._analyze_static_content,
            'try_http_fallback': self._try_http_fallback
        }
    
    def handle_analyzer_error(self, error: Exception, context: Dict) -> Dict:
        """Convert technical errors into user-friendly feedback with recovery attempts"""
        
        error_type = self._classify_error(error)
        error_info = self.error_patterns.get(error_type, self._get_default_error_info())
        
        # Format error message with context
        user_message = error_info['user_message']
        technical_details = error_info['technical_details'].format(
            error=str(error),
            timeout=context.get('timeout', 30),
            url=context.get('url', 'unknown')
        )
        
        # Attempt recovery actions
        partial_results = {}
        recovery_success = False
        
        for action in error_info.get('recovery_actions', []):
            if action in self.recovery_strategies:
                try:
                    result = self.recovery_strategies[action](context)
                    if result:
                        partial_results.update(result)
                        recovery_success = True
                except Exception as recovery_error:
                    logger.debug(f"Recovery action {action} failed: {recovery_error}")
        
        # Calculate confidence level based on recovery success
        confidence_level = self._calculate_confidence(error_type, recovery_success, partial_results)
        
        return {
            'error_handled': True,
            'error_type': error_type.value,
            'severity': error_info['severity'],
            'user_message': user_message,
            'impact': error_info['impact'],
            'recommendation': error_info['recommendation'],
            'partial_results': partial_results,
            'recovery_attempted': len(error_info.get('recovery_actions', [])) > 0,
            'recovery_success': recovery_success,
            'confidence_level': confidence_level,
            'technical_details': technical_details if context.get('debug', False) else None
        }
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify the error type based on exception details"""
        
        error_str = str(error).lower()
        error_type_name = type(error).__name__
        
        # Timeout errors
        if 'timeout' in error_str or 'timed out' in error_str:
            return ErrorType.TIMEOUT
        
        # Connection errors
        if any(term in error_str for term in ['connection', 'refused', 'reset', 'unreachable']):
            return ErrorType.CONNECTION_ERROR
        
        # SSL errors
        if 'ssl' in error_str or 'certificate' in error_str:
            return ErrorType.SSL_ERROR
        
        # Parsing errors
        if any(term in error_str for term in ['parse', 'syntax', 'malformed', 'invalid html']):
            return ErrorType.PARSING_ERROR
        
        # Encoding errors
        if any(term in error_str for term in ['decode', 'encode', 'charset', 'unicode']):
            return ErrorType.ENCODING_ERROR
        
        # Rate limiting
        if any(term in error_str for term in ['rate limit', '429', 'too many requests']):
            return ErrorType.RATE_LIMIT
        
        # Memory errors
        if 'memory' in error_str or error_type_name == 'MemoryError':
            return ErrorType.MEMORY_ERROR
        
        # Authentication errors
        if any(term in error_str for term in ['401', '403', 'forbidden', 'unauthorized']):
            return ErrorType.AUTHENTICATION_ERROR
        
        return ErrorType.UNKNOWN
    
    def _calculate_confidence(self, error_type: ErrorType, recovery_success: bool, partial_results: Dict) -> float:
        """Calculate confidence level for results after error"""
        
        base_confidence = {
            ErrorType.TIMEOUT: 0.7,
            ErrorType.PARSING_ERROR: 0.6,
            ErrorType.CONNECTION_ERROR: 0.0,
            ErrorType.ENCODING_ERROR: 0.8,
            ErrorType.JAVASCRIPT_REQUIRED: 0.5,
            ErrorType.SSL_ERROR: 0.3,
            ErrorType.RATE_LIMIT: 0.9,
            ErrorType.BLOCKED_BY_ROBOTS: 0.0,
            ErrorType.UNKNOWN: 0.4
        }
        
        confidence = base_confidence.get(error_type, 0.5)
        
        # Adjust based on recovery success
        if recovery_success:
            confidence += 0.2
        
        # Adjust based on partial results
        if partial_results:
            results_completeness = len(partial_results) / 10  # Assume 10 key metrics
            confidence += results_completeness * 0.1
        
        return min(1.0, max(0.0, confidence))
    
    def _partial_content_analysis(self, context: Dict) -> Optional[Dict]:
        """Attempt to analyze whatever content was retrieved"""
        
        content = context.get('partial_content', '')
        if not content:
            return None
        
        results = {}
        
        # Try to extract basic metrics
        try:
            # Word count
            words = len(content.split())
            if words > 0:
                results['word_count'] = words
            
            # Basic readability
            sentences = len(re.findall(r'[.!?]+', content))
            if sentences > 0:
                results['sentence_count'] = sentences
                results['avg_sentence_length'] = words / sentences
        except:
            pass
        
        return results if results else None
    
    def _basic_meta_extraction(self, context: Dict) -> Optional[Dict]:
        """Extract basic meta tags using regex as fallback"""
        
        content = context.get('raw_html', '') or context.get('partial_content', '')
        if not content:
            return None
        
        results = {}
        
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        if title_match:
            results['title'] = title_match.group(1).strip()
        
        # Extract meta description
        desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
        if desc_match:
            results['meta_description'] = desc_match.group(1).strip()
        
        # Extract canonical
        canonical_match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', content, re.IGNORECASE)
        if canonical_match:
            results['canonical_url'] = canonical_match.group(1).strip()
        
        return results if results else None
    
    def _regex_fallback(self, context: Dict) -> Optional[Dict]:
        """Use regex patterns to extract data when parsing fails"""
        
        content = context.get('raw_html', '')
        if not content:
            return None
        
        results = {}
        
        # Count images
        img_tags = re.findall(r'<img[^>]+>', content, re.IGNORECASE)
        results['image_count'] = len(img_tags)
        
        # Count headings
        for i in range(1, 7):
            h_tags = re.findall(f'<h{i}[^>]*>.*?</h{i}>', content, re.IGNORECASE | re.DOTALL)
            if h_tags:
                results[f'h{i}_count'] = len(h_tags)
        
        # Check for viewport
        viewport_match = re.search(r'<meta\s+name=["\']viewport["\']', content, re.IGNORECASE)
        results['has_viewport'] = bool(viewport_match)
        
        return results if results else None
    
    def _force_utf8_encoding(self, context: Dict) -> Optional[Dict]:
        """Force UTF-8 encoding on content"""
        
        raw_content = context.get('raw_bytes', b'')
        if not raw_content:
            return None
        
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    decoded = raw_content.decode(encoding)
                    return {'decoded_content': decoded, 'detected_encoding': encoding}
                except:
                    continue
        except:
            pass
        
        return None
    
    def _analyze_static_content(self, context: Dict) -> Optional[Dict]:
        """Analyze static content when JavaScript is required"""
        
        content = context.get('raw_html', '')
        if not content:
            return None
        
        results = {'requires_javascript': True}
        
        # Check for noscript tags
        noscript_matches = re.findall(r'<noscript[^>]*>(.*?)</noscript>', content, re.IGNORECASE | re.DOTALL)
        if noscript_matches:
            results['has_noscript'] = True
            results['noscript_content_length'] = sum(len(match) for match in noscript_matches)
        
        # Check for common SPA frameworks
        if 'react' in content.lower():
            results['framework'] = 'React'
        elif 'angular' in content.lower():
            results['framework'] = 'Angular'
        elif 'vue' in content.lower():
            results['framework'] = 'Vue'
        
        return results
    
    def _try_http_fallback(self, context: Dict) -> Optional[Dict]:
        """Suggest HTTP fallback for SSL errors"""
        
        url = context.get('url', '')
        if url.startswith('https://'):
            http_url = url.replace('https://', 'http://', 1)
            return {
                'suggestion': f'Try accessing via HTTP: {http_url}',
                'warning': 'Using HTTP is not recommended for production sites'
            }
        
        return None
    
    def _get_default_error_info(self) -> Dict:
        """Get default error information for unknown errors"""
        
        return {
            'user_message': 'An unexpected error occurred during analysis.',
            'impact': 'Some features may not work correctly',
            'recommendation': 'Try again later or contact support if the issue persists',
            'recovery_actions': ['basic_meta_extraction', 'regex_fallback'],
            'technical_details': 'Unknown error: {error}',
            'severity': 'warning'
        }
    
    def create_error_report(self, errors: List[Dict]) -> Dict:
        """Create a summary report of all errors encountered"""
        
        if not errors:
            return {
                'has_errors': False,
                'error_count': 0,
                'summary': 'No errors encountered'
            }
        
        # Group errors by type
        error_groups = {}
        for error in errors:
            error_type = error.get('error_type', 'unknown')
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)
        
        # Calculate overall impact
        severity_scores = {'critical': 3, 'warning': 2, 'notice': 1}
        total_severity = sum(
            severity_scores.get(error.get('severity', 'notice'), 1)
            for error in errors
        )
        
        # Generate recommendations
        all_recommendations = list(set(
            error.get('recommendation', '')
            for error in errors
            if error.get('recommendation')
        ))
        
        return {
            'has_errors': True,
            'error_count': len(errors),
            'error_types': list(error_groups.keys()),
            'grouped_errors': error_groups,
            'overall_severity': 'critical' if total_severity > 6 else 'warning' if total_severity > 3 else 'notice',
            'recovery_success_rate': sum(1 for e in errors if e.get('recovery_success', False)) / len(errors),
            'recommendations': all_recommendations[:3],  # Top 3 recommendations
            'summary': self._generate_error_summary(error_groups)
        }
    
    def _generate_error_summary(self, error_groups: Dict) -> str:
        """Generate a human-readable error summary"""
        
        if len(error_groups) == 1:
            error_type = list(error_groups.keys())[0]
            count = len(error_groups[error_type])
            return f"Encountered {count} {error_type.replace('_', ' ')} error{'s' if count > 1 else ''}"
        else:
            return f"Encountered {sum(len(errors) for errors in error_groups.values())} errors across {len(error_groups)} different types" 