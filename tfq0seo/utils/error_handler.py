import logging
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging.handlers
import os
import traceback
from functools import wraps
import re
from urllib.parse import urlparse
import requests

@dataclass
class TFQ0SEOError(Exception):
    """Enhanced TFQ0SEO Error with detailed context."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Initialize the exception with proper message."""
        super().__init__(self.message)
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class TFQ0SEOException(Exception):
    """Base exception class for tfq0seo errors.
    
    Wraps error information in a structured format for consistent handling.
    
    Args:
        error: TFQ0SEOError instance containing error details
    """
    def __init__(self, error: TFQ0SEOError):
        self.error = error
        super().__init__(self.error.message)

class URLFetchError(TFQ0SEOException):
    """tfq0seo URL fetching error.
    
    Raised when unable to fetch or access a target URL.
    Common causes:
    - Network connectivity issues
    - Invalid URLs
    - Server errors
    - Timeout issues
    """
    pass

class ContentAnalysisError(TFQ0SEOException):
    """tfq0seo content analysis error.
    
    Raised during content parsing or analysis failures.
    Common causes:
    - Invalid HTML structure
    - Missing required elements
    - Encoding issues
    - Resource access problems
    """
    pass

def setup_logging(log_file: Union[str, Path]) -> None:
    """Set up tfq0seo logging configuration.
    
    Args:
        log_file: Path to log file
    """
    log_file = Path(log_file)
    os.makedirs(log_file.parent, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Configure tfq0seo logger
    logger = logging.getLogger('tfq0seo')
    logger.setLevel(logging.INFO)
    
    # Add file handler if not already present
    has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    if not has_file_handler:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    logger.info("Logging system initialized successfully")

def log_error(error: TFQ0SEOError) -> None:
    """Log a tfq0seo error with detailed formatting.
    
    Creates a structured log entry containing:
    - Error code and message
    - Timestamp
    - Additional error details
    
    Args:
        error: TFQ0SEOError instance to log
    """
    logger = logging.getLogger('tfq0seo')
    error_message = (
        f"Error {error.error_code}: {error.message}\n"
        f"Timestamp: {error.timestamp}\n"
        f"Details: {error.details if error.details else 'None'}"
    )
    logger.error(error_message)

def handle_analysis_error(func):
    """Enhanced decorator for handling analysis errors with detailed logging."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TFQ0SEOError:
            # Re-raise TFQ0SEO errors as-is
            raise
        except requests.exceptions.SSLError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"SSL Error in {func.__name__}: {str(e)}")
            return {
                'error': 'SSL certificate verification failed',
                'error_type': 'SSL_ERROR',
                'details': str(e),
                'recommendations': [
                    'Check if the SSL certificate is valid and properly configured',
                    'Verify the certificate chain is complete',
                    'Consider using a different SSL certificate provider'
                ]
            }
        except requests.exceptions.ConnectionError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Connection Error in {func.__name__}: {str(e)}")
            return {
                'error': 'Failed to connect to the website',
                'error_type': 'CONNECTION_ERROR',
                'details': str(e),
                'recommendations': [
                    'Check if the website is accessible',
                    'Verify the URL is correct',
                    'Check your internet connection'
                ]
            }
        except requests.exceptions.Timeout as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Timeout Error in {func.__name__}: {str(e)}")
            return {
                'error': 'Request timed out',
                'error_type': 'TIMEOUT_ERROR',
                'details': str(e),
                'recommendations': [
                    'The website is taking too long to respond',
                    'Try again later',
                    'Check if the website is experiencing high load'
                ]
            }
        except requests.exceptions.RequestException as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Request Error in {func.__name__}: {str(e)}")
            return {
                'error': 'HTTP request failed',
                'error_type': 'REQUEST_ERROR',
                'details': str(e),
                'recommendations': [
                    'Check if the URL is valid and accessible',
                    'Verify the website is online',
                    'Check for any network restrictions'
                ]
            }
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'error': f'Analysis failed: {str(e)}',
                'error_type': 'ANALYSIS_ERROR',
                'function': func.__name__,
                'traceback': traceback.format_exc(),
                'recommendations': [
                    'This appears to be an unexpected error',
                    'Please report this issue with the URL and error details',
                    'Try analyzing a different URL to see if the issue persists'
                ]
            }
    return wrapper

def validate_url(url: str) -> bool:
    """Validate URL format and accessibility."""
    # Basic URL format validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False
    
    # Parse URL components
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except Exception:
        return False

def sanitize_url(url: str) -> str:
    """Sanitize and normalize URL."""
    url = url.strip()
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash for consistency
    if url.endswith('/') and len(url) > 8:  # Don't remove from root URLs
        url = url.rstrip('/')
    
    return url

def log_analysis_start(url: str, analysis_type: str):
    """Log the start of an analysis."""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {analysis_type} analysis for: {url}")

def log_analysis_complete(url: str, analysis_type: str, duration: float):
    """Log the completion of an analysis."""
    logger = logging.getLogger(__name__)
    logger.info(f"Completed {analysis_type} analysis for: {url} in {duration:.2f}s")

def create_error_report(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
    """Create a detailed error report."""
    return {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'timestamp': datetime.now().isoformat(),
        'traceback': traceback.format_exc() if hasattr(error, '__traceback__') else None
    } 