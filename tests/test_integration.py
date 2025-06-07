import pytest
import asyncio
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from src.analyzers.modern_seo_analyzer import ModernSEOAnalyzer
from src.utils.performance import BatchProcessor, MemoryConfig
from src.utils.types import AsyncAnalysisContext

@pytest.mark.asyncio
async def test_full_analysis_pipeline(
    analyzer: ModernSEOAnalyzer,
    test_server,
    performance_metrics,
    save_results
):
    """Test complete analysis pipeline."""
    performance_metrics.start('full_analysis_pipeline')
    
    # Analyze test page
    result = await analyzer.analyze('http://localhost:8080/valid')
    
    # Verify mobile-friendly analysis
    assert result['mobile_friendly']['has_viewport']
    assert result['mobile_friendly']['responsive_images']
    assert result['mobile_friendly']['touch_friendly']
    
    # Verify performance analysis
    assert result['performance']['resource_count']['images'] == 1
    assert result['performance']['resource_count']['scripts'] == 1
    assert result['performance']['resource_count']['styles'] == 1
    
    # Verify security checks
    assert not result['security']['https']  # Local test server
    assert result['security']['hsts']
    assert result['security']['xss_protection']
    assert result['security']['content_security']
    
    # Verify structured data
    assert result['structured_data']['count'] == 2  # WebPage and Product
    assert 'WebPage' in result['structured_data']['types']
    assert 'Product' in result['structured_data']['types']
    
    # Verify social signals
    assert 'og:title' in result['social_signals']['facebook']
    assert 'twitter:card' in result['social_signals']['twitter']
    
    performance_metrics.stop()
    save_results(performance_metrics.get_results())

@pytest.mark.asyncio
async def test_batch_analysis(
    analyzer: ModernSEOAnalyzer,
    test_server,
    performance_metrics,
    save_results
):
    """Test batch analysis capabilities."""
    performance_metrics.start('batch_analysis')
    
    # Create test URLs
    urls = [
        'http://localhost:8080/valid',
        'http://localhost:8080/valid',  # Test caching
        'http://localhost:8080/valid'
    ]
    
    # Perform batch analysis
    results = await analyzer.analyze_batch(urls)
    
    # Verify results
    assert len(results) == len(urls)
    for url, result in results.items():
        assert result['mobile_friendly']['has_viewport']
        assert result['structured_data']['count'] > 0
    
    # Verify cache hits
    assert analyzer.cache.stats['hits'] >= 1
    
    performance_metrics.stop()
    save_results(performance_metrics.get_results())

@pytest.mark.asyncio
async def test_error_handling(
    analyzer: ModernSEOAnalyzer,
    test_server,
    performance_metrics,
    save_results
):
    """Test error handling in analysis pipeline."""
    performance_metrics.start('error_handling')
    
    # Test rate limiting
    with pytest.raises(Exception) as exc_info:
        await analyzer.analyze('http://localhost:8080/rate-limit')
    assert 'RATE_LIMIT' in str(exc_info.value)
    
    # Test server error
    with pytest.raises(Exception) as exc_info:
        await analyzer.analyze('http://localhost:8080/error')
    assert '500' in str(exc_info.value)
    
    # Test invalid URL
    with pytest.raises(Exception) as exc_info:
        await analyzer.analyze('not-a-url')
    assert 'INVALID_URL' in str(exc_info.value)
    
    performance_metrics.stop()
    save_results(performance_metrics.get_results())

@pytest.mark.asyncio
async def test_concurrent_analysis(
    test_context: AsyncAnalysisContext,
    test_server,
    performance_metrics,
    save_results
):
    """Test concurrent analysis capabilities."""
    performance_metrics.start('concurrent_analysis')
    
    async def analyze_url(url: str) -> Dict[str, Any]:
        async with ModernSEOAnalyzer(test_context) as analyzer:
            return await analyzer.analyze(url)
    
    # Create multiple analysis tasks
    urls = ['http://localhost:8080/valid'] * 5
    tasks = [analyze_url(url) for url in urls]
    
    # Run analyses concurrently
    results = await asyncio.gather(*tasks)
    
    # Verify results
    assert len(results) == len(urls)
    for result in results:
        assert result['mobile_friendly']['has_viewport']
        assert result['structured_data']['count'] > 0
    
    performance_metrics.stop()
    save_results(performance_metrics.get_results())

@pytest.mark.asyncio
async def test_memory_management(
    analyzer: ModernSEOAnalyzer,
    test_server,
    performance_metrics,
    save_results
):
    """Test memory management during analysis."""
    performance_metrics.start('memory_management')
    
    # Create large test data
    large_urls = ['http://localhost:8080/valid'] * 20
    
    # Monitor memory during batch analysis
    initial_memory = performance_metrics._get_memory_usage()
    
    results = await analyzer.analyze_batch(large_urls)
    
    final_memory = performance_metrics._get_memory_usage()
    memory_increase = final_memory - initial_memory
    
    # Verify results and memory usage
    assert len(results) == len(large_urls)
    assert memory_increase < 100  # Less than 100MB increase
    
    performance_metrics.stop()
    save_results(performance_metrics.get_results())

@pytest.mark.asyncio
async def test_cache_efficiency(
    analyzer: ModernSEOAnalyzer,
    test_server,
    performance_metrics,
    save_results
):
    """Test cache efficiency."""
    performance_metrics.start('cache_efficiency')
    
    url = 'http://localhost:8080/valid'
    
    # First request (cache miss)
    start_time = asyncio.get_event_loop().time()
    result1 = await analyzer.analyze(url)
    first_request_time = asyncio.get_event_loop().time() - start_time
    
    # Second request (cache hit)
    start_time = asyncio.get_event_loop().time()
    result2 = await analyzer.analyze(url)
    second_request_time = asyncio.get_event_loop().time() - start_time
    
    # Verify cache performance
    assert second_request_time < first_request_time
    assert analyzer.cache.stats['hits'] >= 1
    assert analyzer.cache.stats['misses'] >= 1
    
    # Verify results are identical
    assert result1 == result2
    
    performance_metrics.stop()
    save_results(performance_metrics.get_results())

@pytest.mark.asyncio
async def test_resource_cleanup(
    test_context: AsyncAnalysisContext,
    test_server,
    performance_metrics,
    save_results
):
    """Test resource cleanup after analysis."""
    performance_metrics.start('resource_cleanup')
    
    analyzer = ModernSEOAnalyzer(test_context)
    
    # Use analyzer in context manager
    async with analyzer:
        result = await analyzer.analyze('http://localhost:8080/valid')
        assert result['mobile_friendly']['has_viewport']
    
    # Verify resources are cleaned up
    assert analyzer.session is None or analyzer.session.closed
    assert not analyzer.cache.cache  # Cache should be empty
    
    performance_metrics.stop()
    save_results(performance_metrics.get_results()) 