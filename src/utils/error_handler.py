import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TFQ0SEOError:
    """tfq0seo error data structure.
    
    Stores comprehensive error information for logging and handling.
    
    Attributes:
        error_code: Unique identifier for the error type
        message: Human-readable error description
        timestamp: When the error occurred
        details: Optional dictionary with additional error context
    """
    error_code: str
    message: str
    timestamp: datetime = datetime.now()
    details: Optional[dict] = None

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

class ConfigurationError(TFQ0SEOException):
    """tfq0seo configuration error.
    
    Raised when configuration is invalid or missing.
    Common causes:
    - Missing required settings
    - Invalid configuration values
    - File access issues
    - Format errors
    """
    pass

def setup_logging(config: dict) -> None:
    """Configure tfq0seo logging system.
    
    Sets up logging with specified configuration:
    - Log file location
    - Logging level
    - Message format
    
    Args:
        config: Dictionary containing logging configuration:
            - file: Path to log file
            - level: Logging level (DEBUG, INFO, etc.)
    """
    logging.basicConfig(
        filename=config['logging']['file'],
        level=getattr(logging, config['logging']['level']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

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
    """Decorator for handling tfq0seo analysis errors.
    
    Provides consistent error handling across analysis functions:
    - Catches and logs specific tfq0seo exceptions
    - Handles unexpected errors
    - Returns structured error responses
    
    Returns:
        Dictionary containing:
        - error: Boolean indicating error status
        - message: Human-readable error description
        - code: Error code for programmatic handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TFQ0SEOException as e:
            log_error(e.error)
            return {
                'error': True,
                'message': str(e),
                'code': e.error.error_code
            }
        except Exception as e:
            error = TFQ0SEOError(
                error_code='UNEXPECTED_ERROR',
                message=str(e),
                details={'type': type(e).__name__}
            )
            log_error(error)
            return {
                'error': True,
                'message': 'An unexpected error occurred',
                'code': 'UNEXPECTED_ERROR'
            }
    return wrapper 