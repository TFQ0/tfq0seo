import asyncio
import time
import gc
import weakref
from typing import Dict, Any, Optional, List, Set, TypeVar, Generic, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
import lxml
import cachetools
from functools import lru_cache, wraps
import psutil
import resource
from .types import CacheConfig, CacheStats, CacheEntry
from .error_handler import create_error

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

@dataclass
class MemoryConfig:
    """Memory management configuration.
    
    Attributes:
        max_memory_mb: Maximum memory usage in MB
        gc_threshold: Memory threshold for GC trigger
        cleanup_interval: Cleanup interval in seconds
    """
    max_memory_mb: int = 1024  # 1GB
    gc_threshold: float = 0.8  # 80% of max memory
    cleanup_interval: int = 300  # 5 minutes

class AdvancedCache(Generic[K, V]):
    """Advanced caching system with memory management.
    
    Features:
    - LRU and TTL eviction
    - Memory-aware caching
    - Automatic cleanup
    - Statistics tracking
    - Concurrent access
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: cachetools.TTLCache[K, CacheEntry[V]] = cachetools.TTLCache(
            maxsize=config['max_entries'],
            ttl=config['expiration']
        )
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_usage_mb': 0.0
        }
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger('tfq0seo.performance')

    async def get(self, key: K) -> Optional[V]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if exists and valid, None otherwise
        """
        async with self.lock:
            try:
                entry = self.cache[key]
                self.stats['hits'] += 1
                entry['last_accessed'] = datetime.now()
                entry['access_count'] += 1
                return entry['data']
            except KeyError:
                self.stats['misses'] += 1
                return None

    async def set(self, key: K, value: V) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        async with self.lock:
            # Check memory usage
            if self._should_cleanup():
                await self._cleanup()
            
            entry: CacheEntry[V] = {
                'data': value,
                'expiration': datetime.now() + timedelta(seconds=self.config['expiration']),
                'last_accessed': datetime.now(),
                'access_count': 0
            }
            
            self.cache[key] = entry
            self._update_stats()

    async def _cleanup(self) -> None:
        """Clean up expired and least used entries."""
        # Remove expired entries
        self.cache.expire()
        
        # If still above threshold, remove least accessed entries
        if self._should_cleanup():
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: (x[1]['access_count'], x[1]['last_accessed'])
            )
            
            # Remove bottom 20% of entries
            entries_to_remove = len(sorted_entries) // 5
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.cache[key]
                self.stats['evictions'] += 1

    def _should_cleanup(self) -> bool:
        """Check if cleanup is needed."""
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        return memory_usage > self.config['max_memory_mb']

    def _update_stats(self) -> None:
        """Update cache statistics."""
        self.stats['memory_usage_mb'] = psutil.Process().memory_info().rss / 1024 / 1024

class ConnectionPool:
    """HTTP connection pool with optimized settings.
    
    Features:
    - Connection reuse
    - Keep-alive management
    - DNS caching
    - Automatic retries
    - Connection limiting
    """
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            ttl_dns_cache=300,  # 5 minutes DNS cache
            use_dns_cache=True,
            force_close=False,
            enable_cleanup_closed=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger('tfq0seo.performance')

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create client session.
        
        Returns:
            aiohttp ClientSession
        """
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'Connection': 'keep-alive',
                    'Keep-Alive': '300'
                }
            )
        return self.session

    async def close(self) -> None:
        """Close all connections."""
        if self.session and not self.session.closed:
            await self.session.close()
        await self.connector.close()

class HTMLParser:
    """Optimized HTML parsing with memory management.
    
    Features:
    - Partial parsing with SoupStrainer
    - LXML parser usage
    - Memory-efficient parsing
    - Garbage collection integration
    """
    
    def __init__(self):
        """Initialize parser."""
        self.logger = logging.getLogger('tfq0seo.performance')
        self._setup_gc()

    def _setup_gc(self) -> None:
        """Configure garbage collection."""
        gc.enable()
        gc.set_threshold(700, 10, 5)  # Aggressive GC

    def parse(self, html: str, targets: Optional[List[str]] = None) -> BeautifulSoup:
        """Parse HTML efficiently.
        
        Args:
            html: HTML content to parse
            targets: List of target tags to parse
            
        Returns:
            BeautifulSoup object
        """
        # Use SoupStrainer for partial parsing if targets specified
        strainer = SoupStrainer(targets) if targets else None
        
        # Parse with lxml for better performance
        return BeautifulSoup(
            html,
            'lxml',
            parse_only=strainer,
            element_classes={
                'NavigableString': weakref.proxy
            }
        )

class BatchProcessor:
    """Batch processing for large-scale analysis.
    
    Features:
    - Chunked processing
    - Memory monitoring
    - Progress tracking
    - Result aggregation
    """
    
    def __init__(
        self,
        chunk_size: int = 100,
        memory_config: MemoryConfig = MemoryConfig()
    ):
        self.chunk_size = chunk_size
        self.memory_config = memory_config
        self.logger = logging.getLogger('tfq0seo.performance')

    async def process_batch(
        self,
        items: List[T],
        processor: Callable[[T], Any],
        max_concurrent: int = 10
    ) -> List[Any]:
        """Process items in batches.
        
        Args:
            items: Items to process
            processor: Processing function
            max_concurrent: Maximum concurrent tasks
            
        Returns:
            List of processing results
        """
        results = []
        chunks = [
            items[i:i + self.chunk_size]
            for i in range(0, len(items), self.chunk_size)
        ]
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_chunk(chunk: List[T]) -> List[Any]:
            async with semaphore:
                # Check memory before processing
                if self._should_limit_memory():
                    await self._wait_for_memory()
                
                tasks = [
                    asyncio.create_task(processor(item))
                    for item in chunk
                ]
                
                chunk_results = await asyncio.gather(*tasks)
                self.logger.info(f"Processed chunk of {len(chunk)} items")
                return chunk_results
        
        for chunk in chunks:
            chunk_results = await process_chunk(chunk)
            results.extend(chunk_results)
        
        return results

    def _should_limit_memory(self) -> bool:
        """Check if memory usage should be limited."""
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        return memory_usage > (self.memory_config.max_memory_mb * self.memory_config.gc_threshold)

    async def _wait_for_memory(self) -> None:
        """Wait for memory to be freed."""
        while self._should_limit_memory():
            gc.collect()
            await asyncio.sleep(1)

def memory_efficient(limit_mb: int = 100) -> Callable:
    """Decorator for memory-efficient function execution.
    
    Args:
        limit_mb: Memory limit in MB
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Set memory limit
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(
                resource.RLIMIT_AS,
                (limit_mb * 1024 * 1024, hard)
            )
            
            try:
                return await func(*args, **kwargs)
            finally:
                # Reset memory limit
                resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
        return wrapper
    return decorator 