from typing import Any, Optional, Union
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass
import logging
import shutil
import time
import os

from .paths import TFQSEO_HOME

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
    """Manages tfq0seo caching system."""
    
    def __init__(self, cache_dir: Union[str, Path], expiration: int = 3600):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            expiration: Cache expiration time in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.expiration = expiration
        self.enabled = True
        self.memory_cache = {}
        self.logger = logging.getLogger('tfq0seo.cache')
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        self.logger.info(f"Cache directory set to: {self.cache_dir}")
        
    def _get_cache_key(self, data: str) -> str:
        """Generate a unique cache key from input data.
        
        Args:
            data: Input data to generate key from
            
        Returns:
            Unique cache key string
        """
        # Use MD5 for fast, fixed-length keys
        return hashlib.md5(data.encode()).hexdigest()
        
    def set(self, key: str, value: Any) -> None:
        """Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if not self.enabled:
            return
            
        try:
            cache_key = self._get_cache_key(key)
            
            # Store in memory cache
            self.memory_cache[cache_key] = {
                'value': value,
                'timestamp': time.time()
            }
            
            # Store in file cache
            os.makedirs(self.cache_dir, exist_ok=True)
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'value': value,
                    'timestamp': time.time()
                }, f, indent=2)
                
            self.logger.debug(f"Cached value for key: {key}")
        except Exception as e:
            self.logger.error(f"Failed to cache value: {e}")
            
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        if not self.enabled:
            return None
            
        try:
            cache_key = self._get_cache_key(key)
            
            # Check memory cache first
            if cache_key in self.memory_cache:
                cache_entry = self.memory_cache[cache_key]
                if time.time() - cache_entry['timestamp'] < self.expiration:
                    return cache_entry['value']
                del self.memory_cache[cache_key]
            
            # Check file cache
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)
                    if time.time() - cache_entry['timestamp'] < self.expiration:
                        # Update memory cache
                        self.memory_cache[cache_key] = cache_entry
                        return cache_entry['value']
                    cache_file.unlink()  # Remove expired cache file
                    
            return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve cached value: {e}")
            return None
            
    def clear(self) -> None:
        """Clear all cached data."""
        try:
            # Clear memory cache
            self.memory_cache.clear()
            
            # Clear file cache
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
                
            self.logger.info("Cache cleared successfully")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}") 