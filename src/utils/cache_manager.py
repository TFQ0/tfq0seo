from typing import Any, Optional
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass
import logging
import shutil

@dataclass
class CacheEntry:
    """tfq0seo cache entry data structure.
    
    Stores cached data with expiration timestamp for memory caching.
    
    Attributes:
        data: The cached data of any type
        expiration: Timestamp when the cache entry expires
    """
    data: Any
    expiration: datetime

class CacheManager:
    """tfq0seo cache management system.
    
    Implements a two-level caching system:
    - Memory cache for fast access to frequently used data
    - File-based cache for persistence across sessions
    
    Features:
    - Thread-safe singleton implementation
    - Configurable cache expiration
    - Automatic cache invalidation
    - JSON-based file storage
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        self.logger = logging.getLogger('tfq0seo.cache')
        self.memory_cache = {}
        self.config = None
        self.cache_dir = None

    def configure(self, config: dict) -> None:
        """Configure tfq0seo cache settings.
        
        Args:
            config: Dictionary containing cache configuration:
                - enabled: Boolean to enable/disable caching
                - expiration: Cache entry lifetime in seconds
                - directory: Path to cache directory
        """
        self.config = config
        self.enabled = config['cache']['enabled']
        self.expiration = config['cache']['expiration']
        
        # Set up cache directory
        try:
            self.cache_dir = Path(config['cache']['directory'])
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Cache directory set to: {self.cache_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create cache directory: {e}")
            self.enabled = False  # Disable caching on error

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
        if not self.cache_dir:
            raise RuntimeError("Cache directory not configured")
        return self.cache_dir / f"{key}.json"

    def get(self, key_data: str) -> Optional[Any]:
        """Retrieve data from tfq0seo cache.
        
        Implements a two-level cache lookup:
        1. Check memory cache for fast access
        2. Fall back to file cache if not in memory
        
        Args:
            key_data: String data to generate cache key from
            
        Returns:
            Cached data if found and valid, None otherwise
        """
        if not self.enabled:
            return None

        try:
            key = self._get_cache_key(key_data)
            
            # Check memory cache first
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if datetime.now() < entry.expiration:
                    return entry.data
                else:
                    del self.memory_cache[key]

            # Check file cache
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                try:
                    with cache_path.open('r') as f:
                        cached_data = json.load(f)
                        expiration = datetime.fromisoformat(cached_data['expiration'])
                        
                        if datetime.now() < expiration:
                            # Update memory cache
                            self.memory_cache[key] = CacheEntry(
                                data=cached_data['data'],
                                expiration=expiration
                            )
                            return cached_data['data']
                        else:
                            cache_path.unlink(missing_ok=True)
                except (json.JSONDecodeError, KeyError, OSError) as e:
                    self.logger.warning(f"Cache read error: {e}")
                    cache_path.unlink(missing_ok=True)
        except Exception as e:
            self.logger.error(f"Cache get error: {e}")
        
        return None

    def set(self, key_data: str, value: Any) -> None:
        """Store data in tfq0seo cache.
        
        Implements two-level caching:
        1. Store in memory cache for fast access
        2. Store in file cache for persistence
        
        Args:
            key_data: String data to generate cache key from
            value: Data to cache
        """
        if not self.enabled:
            return

        try:
            key = self._get_cache_key(key_data)
            expiration = datetime.now() + timedelta(seconds=self.expiration)
            
            # Update memory cache
            self.memory_cache[key] = CacheEntry(
                data=value,
                expiration=expiration
            )
            
            # Update file cache
            cache_path = self._get_cache_path(key)
            cache_data = {
                'data': value,
                'expiration': expiration.isoformat()
            }
            
            with cache_path.open('w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            self.logger.error(f"Cache set error: {e}")

    def clear(self) -> None:
        """Clear all tfq0seo cached data.
        
        Removes all entries from:
        - Memory cache
        - File-based cache
        """
        self.memory_cache.clear()
        try:
            if self.cache_dir and self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                self.logger.info("Cache cleared successfully")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")

cache_manager = CacheManager() 