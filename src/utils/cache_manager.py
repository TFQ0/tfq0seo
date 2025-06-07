from typing import Any, Optional, Dict, List
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass
import logging
from collections import OrderedDict

@dataclass
class CacheEntry:
    """tfq0seo cache entry data structure.
    
    Stores cached data with expiration timestamp and access metadata.
    
    Attributes:
        data: The cached data of any type
        expiration: Timestamp when the cache entry expires
        last_accessed: Timestamp of last access
        access_count: Number of times this entry was accessed
    """
    data: Any
    expiration: datetime
    last_accessed: datetime = datetime.now()
    access_count: int = 0

@dataclass
class CacheStats:
    """tfq0seo cache statistics data structure.
    
    Tracks cache performance metrics.
    
    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of evicted entries
        size: Current number of entries
        memory_usage: Estimated memory usage in bytes
    """
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    memory_usage: int = 0

class CacheManager:
    """tfq0seo cache management system.
    
    Implements a two-level caching system with advanced features:
    - Memory cache for fast access to frequently used data
    - File-based cache for persistence across sessions
    - LRU (Least Recently Used) eviction policy
    - Size-based eviction
    - Automatic cleanup of expired entries
    - Cache statistics and monitoring
    
    Features:
    - Thread-safe singleton implementation
    - Configurable cache expiration
    - Automatic cache invalidation
    - Memory usage limits
    - Performance monitoring
    """
    _instance = None
    _lock = threading.Lock()
    
    # Default configuration
    DEFAULT_MAX_ENTRIES = 1000
    DEFAULT_MAX_MEMORY_MB = 100
    CLEANUP_THRESHOLD = 0.9  # Cleanup when 90% full

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        """Initialize the cache manager."""
        if not hasattr(self, '_initialized'):
            self.cache_dir = Path('.tfq0seo_cache')
            self.cache_dir.mkdir(exist_ok=True)
            self.memory_cache = OrderedDict()  # LRU cache
            self.config = None
            self.stats = CacheStats()
            self.logger = logging.getLogger('tfq0seo.cache')
            self._initialized = True

    def configure(self, config: dict) -> None:
        """Configure tfq0seo cache settings.
        
        Args:
            config: Dictionary containing cache configuration:
                - enabled: Boolean to enable/disable caching
                - expiration: Cache entry lifetime in seconds
                - max_entries: Maximum number of cache entries
                - max_memory_mb: Maximum memory usage in MB
        """
        self.config = config
        self.enabled = config['cache']['enabled']
        self.expiration = config['cache']['expiration']
        self.max_entries = config['cache'].get('max_entries', self.DEFAULT_MAX_ENTRIES)
        self.max_memory = config['cache'].get('max_memory_mb', self.DEFAULT_MAX_MEMORY_MB) * 1024 * 1024
        
        # Initial cleanup of expired entries
        self._cleanup_expired()

    def _get_cache_key(self, data: str) -> str:
        """Generate a unique cache key using MD5 hashing.
        
        Args:
            data: String data to generate key from
            
        Returns:
            MD5 hash of the input data
        """
        return hashlib.md5(data.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get the filesystem path for a cache entry.
        
        Args:
            key: Cache key to generate path for
            
        Returns:
            Path object pointing to the cache file location
        """
        return self.cache_dir / f"{key}.json"

    def get(self, key_data: str) -> Optional[Any]:
        """Retrieve data from tfq0seo cache.
        
        Implements a two-level cache lookup with statistics:
        1. Check memory cache for fast access
        2. Fall back to file cache if not in memory
        
        Args:
            key_data: String data to generate cache key from
            
        Returns:
            Cached data if found and valid, None otherwise
        """
        if not self.enabled:
            return None

        key = self._get_cache_key(key_data)
        
        # Check memory cache first
        with self._lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if datetime.now() < entry.expiration:
                    # Update access metadata
                    entry.last_accessed = datetime.now()
                    entry.access_count += 1
                    # Move to end (most recently used)
                    self.memory_cache.move_to_end(key)
                    self.stats.hits += 1
                    return entry.data
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
                    self.stats.evictions += 1

        # Check file cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                with cache_path.open('r') as f:
                    cached_data = json.load(f)
                    expiration = datetime.fromisoformat(cached_data['expiration'])
                    
                    if datetime.now() < expiration:
                        # Update memory cache
                        self._add_to_memory_cache(
                            key,
                            cached_data['data'],
                            expiration
                        )
                        self.stats.hits += 1
                        return cached_data['data']
                    else:
                        cache_path.unlink()
                        self.stats.evictions += 1
            except (json.JSONDecodeError, KeyError):
                cache_path.unlink()
        
        self.stats.misses += 1
        return None

    def set(self, key_data: str, value: Any) -> None:
        """Store data in tfq0seo cache.
        
        Implements two-level caching with size management:
        1. Store in memory cache for fast access
        2. Store in file cache for persistence
        
        Args:
            key_data: String data to generate cache key from
            value: Data to cache
        """
        if not self.enabled:
            return

        key = self._get_cache_key(key_data)
        expiration = datetime.now() + timedelta(seconds=self.expiration)
        
        # Update memory cache
        self._add_to_memory_cache(key, value, expiration)
        
        # Update file cache
        cache_path = self._get_cache_path(key)
        cache_data = {
            'data': value,
            'expiration': expiration.isoformat()
        }
        
        with cache_path.open('w') as f:
            json.dump(cache_data, f)

    def _add_to_memory_cache(self, key: str, value: Any, expiration: datetime) -> None:
        """Add entry to memory cache with size management.
        
        Args:
            key: Cache key
            value: Data to cache
            expiration: Expiration timestamp
        """
        with self._lock:
            # Check if cleanup is needed
            if (len(self.memory_cache) >= self.max_entries * self.CLEANUP_THRESHOLD or
                self._estimate_memory_usage() >= self.max_memory * self.CLEANUP_THRESHOLD):
                self._cleanup_cache()

            # Add new entry
            self.memory_cache[key] = CacheEntry(
                data=value,
                expiration=expiration
            )
            self.memory_cache.move_to_end(key)  # Move to end (most recently used)
            
            # Update statistics
            self.stats.size = len(self.memory_cache)
            self.stats.memory_usage = self._estimate_memory_usage()

    def _cleanup_cache(self) -> None:
        """Clean up cache based on size and memory limits.
        
        Implements cleanup strategies:
        1. Remove expired entries
        2. Remove least recently used entries if still over limit
        """
        # First, remove expired entries
        self._cleanup_expired()
        
        # If still over limit, remove LRU entries
        while (len(self.memory_cache) > self.max_entries or
               self._estimate_memory_usage() > self.max_memory):
            if not self.memory_cache:
                break
            self.memory_cache.popitem(last=False)  # Remove first item (least recently used)
            self.stats.evictions += 1
        
        # Update statistics
        self.stats.size = len(self.memory_cache)
        self.stats.memory_usage = self._estimate_memory_usage()

    def _cleanup_expired(self) -> None:
        """Remove expired entries from both memory and file cache."""
        now = datetime.now()
        
        # Clean memory cache
        with self._lock:
            expired_keys = [k for k, v in self.memory_cache.items() 
                          if now > v.expiration]
            for k in expired_keys:
                del self.memory_cache[k]
                self.stats.evictions += 1
        
        # Clean file cache
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with cache_file.open('r') as f:
                    cached_data = json.load(f)
                    expiration = datetime.fromisoformat(cached_data['expiration'])
                    if now > expiration:
                        cache_file.unlink()
                        self.stats.evictions += 1
            except (json.JSONDecodeError, KeyError):
                cache_file.unlink()

    def _estimate_memory_usage(self) -> int:
        """Estimate current memory usage of the cache in bytes."""
        total_size = 0
        for entry in self.memory_cache.values():
            # Rough estimation of object size
            try:
                total_size += len(json.dumps(entry.data)) * 2  # Unicode characters
            except (TypeError, ValueError):
                total_size += 1024  # Default size for non-serializable objects
        return total_size

    def get_stats(self) -> Dict:
        """Get current cache statistics.
        
        Returns:
            Dictionary containing:
            - Hit/miss counts and ratios
            - Current size and memory usage
            - Eviction count
            - Cache efficiency metrics
        """
        total_requests = self.stats.hits + self.stats.misses
        hit_ratio = self.stats.hits / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'hit_ratio': hit_ratio,
            'evictions': self.stats.evictions,
            'current_size': self.stats.size,
            'memory_usage_mb': self.stats.memory_usage / (1024 * 1024),
            'max_size': self.max_entries,
            'max_memory_mb': self.max_memory / (1024 * 1024)
        }

    def clear(self) -> None:
        """Clear all tfq0seo cached data and reset statistics."""
        with self._lock:
            self.memory_cache.clear()
            for cache_file in self.cache_dir.glob('*.json'):
                cache_file.unlink()
            self.stats = CacheStats()
            self.logger.info("Cache cleared and statistics reset")

cache_manager = CacheManager() 