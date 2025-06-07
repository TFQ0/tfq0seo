import pytest
import time
from src.utils.security import (
    InputSanitizer,
    SecurityHeaders,
    RequestValidator,
    RateLimitConfig,
    RateLimiter
)
from src.utils.error_handler import URLFetchError
from src.utils.types import RequestHeaders

def test_input_sanitizer_url():
    """Test URL sanitization."""
    sanitizer = InputSanitizer()
    
    # Valid URLs
    assert sanitizer.sanitize_url('https://example.com') == 'https://example.com'
    assert sanitizer.sanitize_url('http://test.com/path?q=1') == 'http://test.com/path?q=1'
    
    # Invalid URLs
    with pytest.raises(URLFetchError):
        sanitizer.sanitize_url('not-a-url')
    
    # Malicious URLs
    malicious_urls = [
        'javascript:alert(1)',
        'data:text/html,<script>alert(1)</script>',
        'vbscript:msgbox("test")',
        'file:///etc/passwd',
        'about:blank'
    ]
    
    for url in malicious_urls:
        with pytest.raises(URLFetchError):
            sanitizer.sanitize_url(url)

def test_input_sanitizer_html():
    """Test HTML sanitization."""
    sanitizer = InputSanitizer()
    
    # Test removing dangerous tags
    html = """
    <div>Safe content</div>
    <script>alert(1)</script>
    <iframe src="evil.com"></iframe>
    <object data="malware.exe"></object>
    """
    
    sanitized = sanitizer.sanitize_html(html)
    assert '<script>' not in sanitized
    assert '<iframe' not in sanitized
    assert '<object' not in sanitized
    assert 'Safe content' in sanitized
    
    # Test removing dangerous attributes
    html = """
    <div onclick="evil()">Click me</div>
    <img onload="hack()" src="test.jpg">
    <a onmouseover="steal()">Hover me</a>
    """
    
    sanitized = sanitizer.sanitize_html(html)
    assert 'onclick' not in sanitized
    assert 'onload' not in sanitized
    assert 'onmouseover' not in sanitized
    assert 'Click me' in sanitized
    assert 'Hover me' in sanitized

def test_input_sanitizer_query():
    """Test SQL query sanitization."""
    sanitizer = InputSanitizer()
    
    # Test removing SQL injection patterns
    queries = [
        "SELECT * FROM users--",
        "1; DROP TABLE users;",
        "1 UNION SELECT password FROM users",
        "1 OR 1=1",
        "admin' --",
        "admin' /*comment*/ OR '1'='1"
    ]
    
    for query in queries:
        sanitized = sanitizer.sanitize_query(query)
        assert '--' not in sanitized
        assert ';' not in sanitized
        assert 'UNION' not in sanitized.upper()
        assert 'SELECT' not in sanitized.upper()
        assert 'DROP' not in sanitized.upper()

def test_security_headers():
    """Test security headers."""
    headers = SecurityHeaders()
    
    # Test recommended headers
    recommended = headers.get_security_headers()
    assert 'Strict-Transport-Security' in recommended
    assert 'X-Content-Type-Options' in recommended
    assert 'X-Frame-Options' in recommended
    assert 'X-XSS-Protection' in recommended
    assert 'Content-Security-Policy' in recommended
    
    # Test header validation
    valid_headers: RequestHeaders = {
        'User_Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Accept_Language': 'en-US',
        'Accept_Encoding': 'gzip',
        'Connection': 'keep-alive'
    }
    
    headers.validate_headers(valid_headers)  # Should not raise
    
    # Test suspicious headers
    suspicious_headers: RequestHeaders = {
        'User_Agent': 'python-requests/2.25.1',
        'Accept': '*/*',
        'Accept_Language': 'en-US',
        'Accept_Encoding': 'gzip',
        'Connection': 'keep-alive'
    }
    
    with pytest.raises(URLFetchError):
        headers.validate_headers(suspicious_headers)

def test_request_validator():
    """Test request validation."""
    validator = RequestValidator('test-key')
    
    # Test request signing
    params = {
        'action': 'test',
        'id': '123',
        'timestamp': '1234567890'
    }
    
    signature = validator.sign_request(params)
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA-256 hex digest length
    
    # Test signature validation
    assert validator.validate_signature(params, signature)
    assert not validator.validate_signature(params, 'wrong-signature')
    
    # Test CSRF token
    token = validator.generate_csrf_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    
    # Test CSRF validation
    session_token = token
    assert validator.validate_csrf_token(token, session_token)
    assert not validator.validate_csrf_token(token, 'wrong-token')

def test_rate_limiter():
    """Test rate limiting."""
    config = RateLimitConfig(
        requests_per_minute=60,
        burst_size=5
    )
    
    limiter = RateLimiter(config)
    
    # Test normal rate
    for _ in range(5):
        assert limiter.check_rate_limit('test-key')
    
    # Test burst limit
    assert not limiter.check_rate_limit('test-key')
    
    # Test rate recovery
    time.sleep(1.0)  # Wait for token regeneration
    assert limiter.check_rate_limit('test-key')
    
    # Test multiple keys
    assert limiter.check_rate_limit('key1')
    assert limiter.check_rate_limit('key2')
    
    # Test rate limit decorator
    @RateLimiter.rate_limit(lambda: 'test-func')
    def test_func():
        return True
    
    # Should work within rate limit
    assert test_func()
    
    # Should raise when rate limited
    for _ in range(10):
        try:
            test_func()
        except URLFetchError as e:
            assert 'RATE_LIMIT' in str(e)
            break
    else:
        pytest.fail("Rate limit was not enforced") 