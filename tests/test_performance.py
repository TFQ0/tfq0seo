import pytest
import asyncio
import time
import gc
from typing import Dict, Any, List
import aiohttp
from bs4 import BeautifulSoup
import psutil
from src.utils.performance import (
    MemoryConfig,
    AdvancedCache,
    ConnectionPool,
    HTMLParser,
    BatchProcessor,
    memory_efficient
)
from src.utils.types import CacheConfig

# Test data
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="Test description">
</head>
<body>
    <h1>Test Header</h1>
    <p>Test paragraph</p>
    <img src="test.jpg">
    <script>console.log('test');</script>
</body>
</html>
"""

@pytest.fixture
def memory_config() -> MemoryConfig:
    """Create test memory configuration."""
    return MemoryConfig(
        max_memory_mb=100,
        gc_threshold=0.8,
        cleanup_interval=60
    )

@pytest.fixture
def cache_config() -> CacheConfig:
    """Create test cache configuration."""
    return {
        'enabled': True,
        'expiration': 300,
        'max_entries': 1000,
        'max_memory_mb': 100
    }

@pytest.mark.asyncio
async def test_advanced_cache():
    """Test advanced caching system."""
    cache = AdvancedCache[str, Dict](cache_config())
    
    # Test setting and getting
    test_data = {'key': 'value'}
    await cache.set('test', test_data)
    result = await cache.get('test')
    assert result == test_data
    
    # Test cache hit counting
    result = await cache.get('test')
    assert result == test_data
    assert cache.stats['hits'] == 2
    
    # Test cache miss counting
    result = await cache.get('nonexistent')
    assert result is None
    assert cache.stats['misses'] == 1
    
    # Test memory-aware cleanup
    large_data = {'data': 'x' * 1000000}  # 1MB of data
    for i in range(200):  # Try to exceed memory limit
        await cache.set(f'large_{i}', large_data)
    
    assert cache.stats['evictions'] > 0

@pytest.mark.asyncio
async def test_connection_pool():
    """Test connection pooling."""
    pool = ConnectionPool(max_connections=10)
    
    try:
        # Test session creation
        session = await pool.get_session()
        assert isinstance(session, aiohttp.ClientSession)
        assert not session.closed
        
        # Test session reuse
        session2 = await pool.get_session()
        assert session is session2
        
        # Test concurrent connections
        async def make_request():
            session = await pool.get_session()
            try:
                async with session.get('http://httpbin.org/get') as response:
                    return response.status
            except:
                return None
        
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        successful = [r for r in results if r == 200]
        assert len(successful) > 0
    
    finally:
        await pool.close()

def test_html_parser(memory_config):
    """Test optimized HTML parsing."""
    parser = HTMLParser(memory_config)
    
    # Test full parsing
    soup = parser.parse(TEST_HTML)
    assert isinstance(soup, BeautifulSoup)
    assert soup.title.string == 'Test Page'
    
    # Test partial parsing
    soup = parser.parse(TEST_HTML, targets=['meta'])
    assert len(soup.find_all('meta')) == 1
    assert len(soup.find_all('script')) == 0  # Should not be included
    
    # Test memory management
    initial_memory = psutil.Process().memory_info().rss
    for _ in range(100):
        parser.parse(TEST_HTML * 100)  # Parse large HTML repeatedly
    final_memory = psutil.Process().memory_info().rss
    
    # Memory should be managed (not grow unbounded)
    assert final_memory < initial_memory * 2

@pytest.mark.asyncio
async def test_batch_processor(memory_config):
    """Test batch processing."""
    processor = BatchProcessor(chunk_size=10, memory_config=memory_config)
    
    # Test data
    items = list(range(100))
    
    # Test processing function
    async def process_item(item: int) -> int:
        await asyncio.sleep(0.01)  # Simulate work
        return item * 2
    
    # Test batch processing
    results = await processor.process_batch(
        items,
        process_item,
        max_concurrent=5
    )
    
    assert len(results) == len(items)
    assert all(r == i * 2 for r, i in zip(results, items))
    
    # Test memory management during processing
    initial_memory = psutil.Process().memory_info().rss
    large_items = ['x' * 1000000 for _ in range(100)]  # Large items
    
    async def process_large_item(item: str) -> int:
        await asyncio.sleep(0.01)
        return len(item)
    
    results = await processor.process_batch(
        large_items,
        process_large_item,
        max_concurrent=5
    )
    
    final_memory = psutil.Process().memory_info().rss
    assert final_memory < initial_memory * 2  # Memory should be managed

@pytest.mark.asyncio
async def test_memory_efficient_decorator():
    """Test memory-efficient decorator."""
    
    @memory_efficient(limit_mb=50)
    async def memory_intensive_function() -> int:
        # Try to allocate a lot of memory
        data = ['x' * 1000000 for _ in range(100)]
        return len(data)
    
    # Should run without memory errors
    result = await memory_intensive_function()
    assert result == 100
    
    # Test memory limit
    @memory_efficient(limit_mb=1)  # Very low limit
    async def exceed_memory_limit() -> None:
        data = ['x' * 1000000 for _ in range(1000)]  # Try to allocate 1GB
    
    with pytest.raises(Exception):  # Should raise memory error
        await exceed_memory_limit()

@pytest.mark.asyncio
async def test_concurrent_cache_access():
    """Test concurrent cache access."""
    cache = AdvancedCache[str, str](cache_config())
    
    async def cache_operation(key: str, value: str) -> None:
        await cache.set(key, value)
        result = await cache.get(key)
        assert result == value
    
    # Run multiple cache operations concurrently
    tasks = [
        cache_operation(f'key_{i}', f'value_{i}')
        for i in range(100)
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify all values were cached correctly
    for i in range(100):
        value = await cache.get(f'key_{i}')
        assert value == f'value_{i}'

@pytest.mark.asyncio
async def test_connection_pool_stress():
    """Test connection pool under stress."""
    pool = ConnectionPool(max_connections=20)
    
    try:
        async def make_requests(count: int) -> List[int]:
            session = await pool.get_session()
            results = []
            
            for _ in range(count):
                try:
                    async with session.get('http://httpbin.org/get') as response:
                        results.append(response.status)
                except:
                    results.append(0)
            
            return results
        
        # Run multiple clients concurrently
        tasks = [make_requests(5) for _ in range(10)]
        all_results = await asyncio.gather(*tasks)
        
        # Check results
        successful = sum(
            1
            for results in all_results
            for status in results
            if status == 200
        )
        
        assert successful > 0  # Some requests should succeed
        
    finally:
        await pool.close()

def test_html_parser_memory_leak(memory_config):
    """Test HTML parser for memory leaks."""
    parser = HTMLParser(memory_config)
    initial_memory = psutil.Process().memory_info().rss
    
    # Parse large HTML repeatedly
    large_html = TEST_HTML * 1000
    for _ in range(10):
        soup = parser.parse(large_html)
        del soup  # Force cleanup
        gc.collect()
    
    final_memory = psutil.Process().memory_info().rss
    memory_growth = final_memory - initial_memory
    
    # Memory growth should be limited
    assert memory_growth < 10 * 1024 * 1024  # Less than 10MB growth 