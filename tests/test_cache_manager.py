import pytest
from datetime import datetime, timedelta
import time
from src.utils.cache_manager import CacheManager, CacheEntry, CacheStats

@pytest.fixture
def cache_manager():
    """Create a fresh cache manager instance for each test."""
    manager = CacheManager()
    manager.clear()  # Ensure clean state
    
    # Configure with test settings
    config = {
        'cache': {
            'enabled': True,
            'expiration': 60,  # 60 seconds
            'max_entries': 5,  # Small size for testing
            'max_memory_mb': 1  # 1MB limit
        }
    }
    manager.configure(config)
    return manager

def test_basic_cache_operations(cache_manager):
    """Test basic cache get/set operations."""
    # Test set and get
    cache_manager.set('test_key', 'test_value')
    assert cache_manager.get('test_key') == 'test_value'
    
    # Test missing key
    assert cache_manager.get('nonexistent_key') is None
    
    # Test cache hit/miss statistics
    stats = cache_manager.get_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 1

def test_cache_expiration(cache_manager):
    """Test cache entry expiration."""
    # Configure with short expiration
    config = {
        'cache': {
            'enabled': True,
            'expiration': 1,  # 1 second
            'max_entries': 5,
            'max_memory_mb': 1
        }
    }
    cache_manager.configure(config)
    
    # Set cache entry
    cache_manager.set('test_key', 'test_value')
    assert cache_manager.get('test_key') == 'test_value'
    
    # Wait for expiration
    time.sleep(1.1)
    assert cache_manager.get('test_key') is None
    
    # Check eviction count
    stats = cache_manager.get_stats()
    assert stats['evictions'] >= 1

def test_cache_size_limit(cache_manager):
    """Test cache size limiting."""
    # Add more entries than the limit
    for i in range(10):
        cache_manager.set(f'key_{i}', f'value_{i}')
    
    # Check cache size
    stats = cache_manager.get_stats()
    assert stats['current_size'] <= 5  # max_entries limit
    
    # Check LRU eviction
    assert cache_manager.get('key_0') is None  # Should be evicted
    assert cache_manager.get('key_9') == 'value_9'  # Should still exist

def test_cache_memory_limit(cache_manager):
    """Test cache memory limiting."""
    # Add large entries
    large_data = 'x' * 500000  # 500KB
    cache_manager.set('large_key_1', large_data)
    cache_manager.set('large_key_2', large_data)
    
    # Check memory usage
    stats = cache_manager.get_stats()
    assert stats['memory_usage_mb'] <= 1  # max_memory_mb limit

def test_cache_statistics(cache_manager):
    """Test cache statistics tracking."""
    # Generate some cache activity
    cache_manager.set('key1', 'value1')
    cache_manager.get('key1')  # Hit
    cache_manager.get('key2')  # Miss
    
    # Check statistics
    stats = cache_manager.get_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 1
    assert 0 <= stats['hit_ratio'] <= 1
    assert stats['current_size'] == 1

def test_cache_clear(cache_manager):
    """Test cache clearing."""
    # Add some entries
    cache_manager.set('key1', 'value1')
    cache_manager.set('key2', 'value2')
    
    # Clear cache
    cache_manager.clear()
    
    # Check if cache is empty
    assert cache_manager.get('key1') is None
    assert cache_manager.get('key2') is None
    
    # Check statistics reset
    stats = cache_manager.get_stats()
    assert stats['hits'] == 0
    assert stats['misses'] == 2
    assert stats['current_size'] == 0

def test_cache_thread_safety(cache_manager):
    """Test cache thread safety."""
    import threading
    
    def cache_operation():
        for i in range(100):
            cache_manager.set(f'thread_key_{i}', f'value_{i}')
            cache_manager.get(f'thread_key_{i}')
    
    # Create multiple threads
    threads = [
        threading.Thread(target=cache_operation)
        for _ in range(3)
    ]
    
    # Run threads
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # Check no errors occurred
    stats = cache_manager.get_stats()
    assert stats['hits'] > 0
    assert stats['current_size'] <= cache_manager.max_entries

def test_lru_behavior(cache_manager):
    """Test Least Recently Used (LRU) behavior."""
    # Fill cache
    for i in range(5):
        cache_manager.set(f'key_{i}', f'value_{i}')
    
    # Access some entries to update their LRU status
    cache_manager.get('key_0')
    cache_manager.get('key_2')
    
    # Add new entry to trigger eviction
    cache_manager.set('new_key', 'new_value')
    
    # Check LRU eviction
    assert cache_manager.get('key_1') is None  # Should be evicted (least recently used)
    assert cache_manager.get('key_0') == 'value_0'  # Should exist (recently accessed)
    assert cache_manager.get('key_2') == 'value_2'  # Should exist (recently accessed)
    assert cache_manager.get('new_key') == 'new_value'  # Should exist (most recent) 