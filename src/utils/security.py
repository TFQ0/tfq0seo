import re
import time
from typing import Optional, Dict, Any, Callable, TypeVar, cast
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from functools import wraps
import logging
import hashlib
import hmac
import secrets
from urllib.parse import urlparse, urlencode
from .error_handler import create_error, URLFetchError, RateLimitError
from .types import RequestHeaders, AsyncAnalysisContext

T = TypeVar('T')

@dataclass
class RateLimitConfig:
    """Rate limiting configuration.
    
    Attributes:
        requests_per_minute: Maximum requests allowed per minute
        burst_size: Maximum burst size allowed
        key_prefix: Prefix for rate limit keys
    """
    requests_per_minute: int
    burst_size: int
    key_prefix: str = 'ratelimit'

class RateLimiter:
    """Thread-safe rate limiter with token bucket algorithm.
    
    Features:
    - Token bucket algorithm
    - Burst handling
    - Thread safety
    - Per-key limiting
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.buckets: Dict[str, Dict[str, float]] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger('tfq0seo.security')

    def _get_bucket(self, key: str) -> Dict[str, float]:
        """Get or create token bucket for key."""
        now = time.time()
        if key not in self.buckets:
            self.buckets[key] = {
                'tokens': self.config.burst_size,
                'last_update': now
            }
        return self.buckets[key]

    def check_rate_limit(self, key: str) -> bool:
        """Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key
            
        Returns:
            True if request is allowed, False otherwise
        """
        with self.lock:
            now = time.time()
            bucket = self._get_bucket(key)
            
            # Calculate tokens to add based on time passed
            time_passed = now - bucket['last_update']
            tokens_to_add = time_passed * (self.config.requests_per_minute / 60.0)
            
            # Update bucket
            bucket['tokens'] = min(
                bucket['tokens'] + tokens_to_add,
                self.config.burst_size
            )
            bucket['last_update'] = now
            
            # Check if request can be allowed
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            
            return False

def rate_limit(key_func: Callable[..., str]) -> Callable:
    """Decorator for rate limiting functions.
    
    Args:
        key_func: Function to generate rate limit key from arguments
        
    Returns:
        Rate limited function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            key = key_func(*args, **kwargs)
            if not RateLimiter.check_rate_limit(key):
                raise RateLimitError(create_error(
                    'RATE_LIMIT',
                    f'Rate limit exceeded for key: {key}'
                ))
            return func(*args, **kwargs)
        return wrapper
    return decorator

class InputSanitizer:
    """Input sanitization and validation.
    
    Features:
    - URL validation
    - HTML sanitization
    - SQL injection prevention
    - XSS prevention
    """
    
    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize and validate URL.
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL
            
        Raises:
            URLFetchError: If URL is invalid or malicious
        """
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                raise URLFetchError(create_error(
                    'INVALID_URL',
                    'Invalid URL format'
                ))
        except Exception as e:
            raise URLFetchError(create_error(
                'INVALID_URL',
                f'URL parsing failed: {str(e)}'
            ))
        
        # Check for malicious patterns
        malicious_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'file:',
            r'about:',
        ]
        
        lower_url = url.lower()
        for pattern in malicious_patterns:
            if pattern in lower_url:
                raise URLFetchError(create_error(
                    'MALICIOUS_URL',
                    f'URL contains malicious pattern: {pattern}'
                ))
        
        return url

    @staticmethod
    def sanitize_html(html: str) -> str:
        """Sanitize HTML content.
        
        Args:
            html: HTML content to sanitize
            
        Returns:
            Sanitized HTML
        """
        # Remove potentially dangerous tags and attributes
        dangerous_tags = [
            'script',
            'iframe',
            'object',
            'embed',
            'base',
            'form',
            'input',
            'button',
            'link',
            'meta'
        ]
        
        dangerous_attrs = [
            'onload',
            'onerror',
            'onclick',
            'onmouseover',
            'onmouseout',
            'onkeydown',
            'onkeyup',
            'onkeypress'
        ]
        
        # Simple tag removal (for demonstration - in production use a proper HTML parser)
        for tag in dangerous_tags:
            html = re.sub(
                f'<{tag}.*?</{tag}>',
                '',
                html,
                flags=re.IGNORECASE | re.DOTALL
            )
            html = re.sub(
                f'<{tag}.*?>',
                '',
                html,
                flags=re.IGNORECASE | re.DOTALL
            )
        
        # Remove dangerous attributes
        for attr in dangerous_attrs:
            html = re.sub(
                f'{attr}=["\'](.*?)["\']',
                '',
                html,
                flags=re.IGNORECASE
            )
        
        return html

    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize SQL query parameters.
        
        Args:
            query: Query string to sanitize
            
        Returns:
            Sanitized query string
        """
        # Remove SQL injection patterns
        sql_patterns = [
            r'--',
            r';',
            r'\/\*',
            r'\*\/',
            r'UNION',
            r'SELECT',
            r'DROP',
            r'DELETE',
            r'UPDATE',
            r'INSERT',
            r'EXEC',
            r'EXECUTE'
        ]
        
        sanitized = query
        for pattern in sql_patterns:
            sanitized = re.sub(
                pattern,
                '',
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized

class SecurityHeaders:
    """Security header management.
    
    Features:
    - HTTPS enforcement
    - XSS protection
    - Content security policy
    - Frame options
    """
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers.
        
        Returns:
            Dictionary of security headers
        """
        return {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=()'
        }

    @staticmethod
    def validate_headers(headers: RequestHeaders) -> None:
        """Validate request headers for security.
        
        Args:
            headers: Request headers to validate
            
        Raises:
            URLFetchError: If headers are invalid or suspicious
        """
        # Check for suspicious user agents
        user_agent = headers.get('User_Agent', '').lower()
        suspicious_agents = ['curl', 'wget', 'python', 'java', 'bot']
        
        for agent in suspicious_agents:
            if agent in user_agent:
                raise URLFetchError(create_error(
                    'SUSPICIOUS_AGENT',
                    f'Suspicious user agent detected: {agent}'
                ))

class RequestValidator:
    """Request validation and sanitization.
    
    Features:
    - Parameter validation
    - Request signing
    - CSRF protection
    """
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()

    def sign_request(self, params: Dict[str, Any]) -> str:
        """Sign request parameters.
        
        Args:
            params: Request parameters to sign
            
        Returns:
            Request signature
        """
        # Sort parameters and create string
        sorted_params = sorted(params.items())
        param_string = urlencode(sorted_params)
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key,
            param_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    def validate_signature(self, params: Dict[str, Any], signature: str) -> bool:
        """Validate request signature.
        
        Args:
            params: Request parameters
            signature: Request signature to validate
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = self.sign_request(params)
        return hmac.compare_digest(signature, expected_signature)

    def generate_csrf_token(self) -> str:
        """Generate CSRF token.
        
        Returns:
            CSRF token
        """
        return secrets.token_urlsafe(32)

    def validate_csrf_token(self, token: str, session_token: str) -> bool:
        """Validate CSRF token.
        
        Args:
            token: CSRF token to validate
            session_token: Token from session
            
        Returns:
            True if token is valid, False otherwise
        """
        return hmac.compare_digest(token, session_token) 