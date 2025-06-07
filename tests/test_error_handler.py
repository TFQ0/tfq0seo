import pytest
import logging
from datetime import datetime
from src.utils.error_handler import (
    TFQ0SEOError,
    TFQ0SEOException,
    URLFetchError,
    RateLimitError,
    NetworkError,
    ContentAnalysisError,
    InvalidHTMLError,
    EncodingError,
    handle_analysis_error,
    create_error,
    setup_logging
)

@pytest.fixture
def error_config():
    """Create test logging configuration."""
    return {
        'logging': {
            'file': 'test.log',
            'level': 'DEBUG',
            'max_size': 1024,
            'backup_count': 1
        }
    }

def test_error_creation():
    """Test error creation and attributes."""
    error = create_error(
        error_code='TEST_ERROR',
        message='Test error message',
        details={'test': 'detail'}
    )
    
    assert error.error_code == 'TEST_ERROR'
    assert error.message == 'Test error message'
    assert error.details == {'test': 'detail'}
    assert isinstance(error.timestamp, datetime)
    assert error.stack_trace is not None
    assert not error.recovery_attempted

def test_exception_hierarchy():
    """Test exception class hierarchy."""
    # Create test errors
    url_error = URLFetchError(create_error('URL_ERROR', 'URL error'))
    rate_limit_error = RateLimitError(create_error('RATE_LIMIT', 'Rate limit'))
    network_error = NetworkError(create_error('NETWORK', 'Network error'))
    
    # Test inheritance
    assert isinstance(url_error, TFQ0SEOException)
    assert isinstance(rate_limit_error, URLFetchError)
    assert isinstance(network_error, URLFetchError)

def test_error_handling_decorator():
    """Test error handling decorator functionality."""
    
    @handle_analysis_error
    def test_function(should_fail: bool = False):
        if should_fail:
            raise URLFetchError(create_error('TEST_ERROR', 'Test error'))
        return {'success': True}
    
    # Test successful execution
    result = test_function(should_fail=False)
    assert result == {'success': True}
    
    # Test error handling
    result = test_function(should_fail=True)
    assert result['error'] is True
    assert result['code'] == 'TEST_ERROR'
    assert not result['recovery_attempted']

def test_error_recovery():
    """Test error recovery mechanisms."""
    
    @handle_analysis_error
    def test_function(headers=None):
        if headers and headers.get('User-Agent') == 'Alternative User Agent':
            return {'success': True}
        raise NetworkError(create_error('NETWORK', 'Network error'))
    
    # Test recovery with alternative user agent
    result = test_function(headers={'User-Agent': 'Original'})
    assert result['error'] is True
    assert result['recovery_attempted'] is True

def test_content_analysis_recovery():
    """Test content analysis error recovery."""
    
    @handle_analysis_error
    def test_function(parser=None):
        if parser == 'html5lib':
            return {'success': True}
        raise InvalidHTMLError(create_error('INVALID_HTML', 'Invalid HTML'))
    
    # Test recovery with alternative parser
    result = test_function(parser='default')
    assert result['error'] is True
    assert result['recovery_attempted'] is True

def test_unexpected_error_handling():
    """Test handling of unexpected errors."""
    
    @handle_analysis_error
    def test_function():
        raise ValueError('Unexpected error')
    
    result = test_function()
    assert result['error'] is True
    assert result['code'] == 'UNEXPECTED_ERROR'
    assert 'type' in result['details']
    assert not result['recovery_attempted']

def test_logging_setup(tmp_path, error_config):
    """Test logging configuration."""
    # Update log file path for test
    error_config['logging']['file'] = str(tmp_path / 'test.log')
    
    # Setup logging
    setup_logging(error_config)
    logger = logging.getLogger('tfq0seo')
    
    # Test log level
    assert logger.level == logging.DEBUG
    
    # Test handler configuration
    handler = logger.handlers[0]
    assert handler.maxBytes == error_config['logging']['max_size']
    assert handler.backupCount == error_config['logging']['backup_count']

def test_error_logging(tmp_path, error_config):
    """Test error logging functionality."""
    # Update log file path for test
    log_file = tmp_path / 'test.log'
    error_config['logging']['file'] = str(log_file)
    
    # Setup logging
    setup_logging(error_config)
    
    # Create and log an error
    error = create_error(
        error_code='TEST_ERROR',
        message='Test error message',
        details={'test': 'detail'}
    )
    
    @handle_analysis_error
    def test_function():
        raise TFQ0SEOException(error)
    
    test_function()
    
    # Check log file contents
    assert log_file.exists()
    log_content = log_file.read_text()
    assert 'TEST_ERROR' in log_content
    assert 'Test error message' in log_content
    assert 'test: detail' in log_content
    assert 'Stack Trace' in log_content

def test_encoding_error_recovery():
    """Test encoding error recovery."""
    
    @handle_analysis_error
    def test_function(encoding=None):
        if encoding == 'utf-8':
            return {'success': True}
        raise EncodingError(create_error('ENCODING', 'Encoding error'))
    
    # Test recovery with UTF-8 encoding
    result = test_function(encoding='ascii')
    assert result['error'] is True
    assert result['recovery_attempted'] is True

def test_rate_limit_recovery():
    """Test rate limit error recovery."""
    import time
    
    @handle_analysis_error
    def test_function():
        if not hasattr(test_function, 'called'):
            test_function.called = True
            raise RateLimitError(create_error('RATE_LIMIT', 'Rate limit'))
        return {'success': True}
    
    # Test recovery after waiting
    start_time = time.time()
    result = test_function()
    elapsed_time = time.time() - start_time
    
    assert result['success'] is True
    assert elapsed_time >= 5  # Should have waited 5 seconds 