import asyncio
import aiohttp
from typing import Optional, Dict, Any, List, Callable, TypeVar, cast
from functools import wraps
import logging
from .types import (
    AsyncAnalysisContext,
    RequestHeaders,
    ResponseHeaders,
    ErrorDetails
)
from .error_handler import (
    URLFetchError,
    RateLimitError,
    NetworkError,
    TimeoutError,
    create_error
)

T = TypeVar('T')

class AsyncRequestManager:
    """Manages async HTTP requests with rate limiting and retries.
    
    Features:
    - Concurrent request limiting
    - Rate limiting
    - Automatic retries with exponential backoff
    - Request pooling
    - Connection management
    """
    
    def __init__(self, context: AsyncAnalysisContext):
        self.context = context
        self.semaphore = asyncio.Semaphore(context['concurrent_limit'])
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger('tfq0seo.async')

    async def __aenter__(self):
        """Initialize aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers=self.context['headers']
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch(self, url: str) -> str:
        """Fetch URL content with retries and rate limiting.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response content as string
            
        Raises:
            URLFetchError: On fetch failure after retries
        """
        async with self.semaphore:
            for attempt in range(self.context['max_retries']):
                try:
                    if not self.session:
                        raise NetworkError(create_error(
                            'NO_SESSION',
                            'HTTP session not initialized'
                        ))
                    
                    async with self.session.get(
                        url,
                        timeout=self.context['timeout']
                    ) as response:
                        if response.status == 429:  # Too Many Requests
                            raise RateLimitError(create_error(
                                'RATE_LIMIT',
                                'Rate limit exceeded'
                            ))
                        
                        response.raise_for_status()
                        return await response.text()
                        
                except aiohttp.ClientError as e:
                    if attempt == self.context['max_retries'] - 1:
                        raise NetworkError(create_error(
                            'NETWORK_ERROR',
                            f'Network error after {attempt + 1} attempts: {str(e)}'
                        ))
                    
                    # Calculate backoff delay
                    delay = self.context['backoff_factor'] * (2 ** attempt)
                    self.logger.warning(
                        f"Request failed, retrying in {delay:.1f} seconds..."
                    )
                    await asyncio.sleep(delay)
                    
                except asyncio.TimeoutError:
                    if attempt == self.context['max_retries'] - 1:
                        raise TimeoutError(create_error(
                            'TIMEOUT',
                            f'Request timed out after {self.context["timeout"]} seconds'
                        ))
                    continue

    async def fetch_many(self, urls: List[str]) -> Dict[str, str]:
        """Fetch multiple URLs concurrently.
        
        Args:
            urls: List of URLs to fetch
            
        Returns:
            Dictionary mapping URLs to their content
        """
        async with asyncio.TaskGroup() as group:
            tasks = {
                url: group.create_task(self.fetch(url))
                for url in urls
            }
        
        return {
            url: task.result()
            for url, task in tasks.items()
        }

def async_retry(
    max_retries: int = 3,
    backoff_factor: float = 1.0
) -> Callable:
    """Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Base delay multiplier for backoff
        
    Returns:
        Decorated async function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = backoff_factor * (2 ** attempt)
                        await asyncio.sleep(delay)
            
            raise last_error
        return wrapper
    return decorator

class AsyncAnalyzer:
    """Base class for async analyzers.
    
    Provides common async functionality:
    - Request management
    - Concurrent analysis
    - Resource cleanup
    """
    
    def __init__(self, context: AsyncAnalysisContext):
        self.context = context
        self.request_manager: Optional[AsyncRequestManager] = None
        self.logger = logging.getLogger('tfq0seo.async')

    async def __aenter__(self):
        """Initialize async resources."""
        self.request_manager = AsyncRequestManager(self.context)
        await self.request_manager.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up async resources."""
        if self.request_manager:
            await self.request_manager.__aexit__(exc_type, exc_val, exc_tb)

    @async_retry()
    async def analyze(self, url: str) -> Dict[str, Any]:
        """Perform async analysis.
        
        To be implemented by subclasses.
        
        Args:
            url: URL to analyze
            
        Returns:
            Analysis results
        """
        raise NotImplementedError() 