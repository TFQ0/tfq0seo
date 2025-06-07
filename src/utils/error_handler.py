import logging
import traceback
from typing import Optional, Dict, Any, Callable, TypeVar, cast
from dataclasses import dataclass
from datetime import datetime
from functools import wraps

# Type variable for generic function return type
T = TypeVar('T')

@dataclass
class TFQ0SEOError:
    """tfq0seo error data structure.
    
    Stores comprehensive error information for logging and handling.
    
    Attributes:
        error_code: Unique identifier for the error type
        message: Human-readable error description
        timestamp: When the error occurred
        details: Optional dictionary with additional error context
        recovery_attempted: Whether recovery was attempted
        stack_trace: Stack trace if available
    """
    error_code: str
    message: str
    timestamp: datetime = datetime.now()
    details: Optional[Dict[str, Any]] = None
    recovery_attempted: bool = False
    stack_trace: Optional[str] = None

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
    - Rate limiting
    """
    pass

class RateLimitError(URLFetchError):
    """Raised when API rate limits are hit."""
    pass

class NetworkError(URLFetchError):
    """Raised for network connectivity issues."""
    pass

class TimeoutError(URLFetchError):
    """Raised when requests timeout."""
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

class InvalidHTMLError(ContentAnalysisError):
    """Raised when HTML cannot be parsed."""
    pass

class EncodingError(ContentAnalysisError):
    """Raised for character encoding issues."""
    pass

class MissingContentError(ContentAnalysisError):
    """Raised when required content elements are missing."""
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

class CacheError(TFQ0SEOException):
    """tfq0seo cache operation error.
    
    Raised for cache-related issues.
    Common causes:
    - Storage access problems
    - Memory limits exceeded
    - Serialization errors
    """
    pass

def setup_logging(config: dict) -> None:
    """Configure tfq0seo logging system.
    
    Sets up logging with specified configuration:
    - Log file location
    - Logging level
    - Message format
    - Log rotation
    
    Args:
        config: Dictionary containing logging configuration:
            - file: Path to log file
            - level: Logging level (DEBUG, INFO, etc.)
            - max_size: Maximum log file size
            - backup_count: Number of backup files to keep
    """
    from logging.handlers import RotatingFileHandler
    
    log_config = config['logging']
    handler = RotatingFileHandler(
        filename=log_config['file'],
        maxBytes=log_config.get('max_size', 1024 * 1024),  # Default 1MB
        backupCount=log_config.get('backup_count', 5)
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('tfq0seo')
    logger.setLevel(getattr(logging, log_config['level']))
    logger.addHandler(handler)

def log_error(error: TFQ0SEOError) -> None:
    """Log a tfq0seo error with detailed formatting.
    
    Creates a structured log entry containing:
    - Error code and message
    - Timestamp
    - Stack trace
    - Additional error details
    - Recovery attempt status
    
    Args:
        error: TFQ0SEOError instance to log
    """
    logger = logging.getLogger('tfq0seo')
    
    # Build detailed error message
    error_message = [
        f"Error {error.error_code}: {error.message}",
        f"Timestamp: {error.timestamp}",
        f"Recovery Attempted: {error.recovery_attempted}"
    ]
    
    if error.details:
        error_message.append(f"Details: {error.details}")
    
    if error.stack_trace:
        error_message.append(f"Stack Trace:\n{error.stack_trace}")
    
    logger.error('\n'.join(error_message))

def handle_analysis_error(func: Callable[..., T]) -> Callable[..., Dict[str, Any]]:
    """Decorator for handling tfq0seo analysis errors.
    
    Provides consistent error handling across analysis functions:
    - Catches and logs specific tfq0seo exceptions
    - Attempts recovery strategies
    - Handles unexpected errors
    - Returns structured error responses
    
    Recovery strategies:
    1. Retry failed operations
    2. Use alternative methods
    3. Fall back to simplified analysis
    
    Returns:
        Dictionary containing:
        - error: Boolean indicating error status
        - message: Human-readable error description
        - code: Error code for programmatic handling
        - details: Additional error context
        - recovery_attempted: Whether recovery was tried
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        try:
            return cast(Dict[str, Any], func(*args, **kwargs))
        except URLFetchError as e:
            # Try URL fetch recovery strategies
            try:
                if isinstance(e, RateLimitError):
                    # Wait and retry
                    import time
                    time.sleep(5)
                    e.error.recovery_attempted = True
                    return cast(Dict[str, Any], func(*args, **kwargs))
                elif isinstance(e, NetworkError):
                    # Try alternative user agent
                    if 'headers' in kwargs:
                        kwargs['headers']['User-Agent'] = 'Alternative User Agent'
                        e.error.recovery_attempted = True
                        return cast(Dict[str, Any], func(*args, **kwargs))
            except Exception:
                pass
            
            log_error(e.error)
            return {
                'error': True,
                'message': str(e),
                'code': e.error.error_code,
                'details': e.error.details,
                'recovery_attempted': e.error.recovery_attempted
            }
        except ContentAnalysisError as e:
            # Try content analysis recovery
            try:
                if isinstance(e, InvalidHTMLError):
                    # Try alternative parser
                    if 'parser' in kwargs:
                        kwargs['parser'] = 'html5lib'
                        e.error.recovery_attempted = True
                        return cast(Dict[str, Any], func(*args, **kwargs))
                elif isinstance(e, EncodingError):
                    # Try different encoding
                    if 'encoding' in kwargs:
                        kwargs['encoding'] = 'utf-8'
                        e.error.recovery_attempted = True
                        return cast(Dict[str, Any], func(*args, **kwargs))
            except Exception:
                pass
            
            log_error(e.error)
            return {
                'error': True,
                'message': str(e),
                'code': e.error.error_code,
                'details': e.error.details,
                'recovery_attempted': e.error.recovery_attempted
            }
        except Exception as e:
            # Handle unexpected errors
            error = TFQ0SEOError(
                error_code='UNEXPECTED_ERROR',
                message=str(e),
                details={'type': type(e).__name__},
                stack_trace=traceback.format_exc()
            )
            log_error(error)
            return {
                'error': True,
                'message': 'An unexpected error occurred',
                'code': 'UNEXPECTED_ERROR',
                'details': error.details,
                'recovery_attempted': False
            }
    return wrapper

def create_error(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> TFQ0SEOError:
    """Create a tfq0seo error with stack trace.
    
    Helper function to create error instances with current stack trace.
    
    Args:
        error_code: Unique identifier for the error
        message: Human-readable error description
        details: Optional additional error context
        
    Returns:
        TFQ0SEOError instance with stack trace
    """
    return TFQ0SEOError(
        error_code=error_code,
        message=message,
        details=details,
        stack_trace=traceback.format_exc()
    ) 