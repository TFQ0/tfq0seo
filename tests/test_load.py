import pytest
import asyncio
import time
from typing import Dict, Any, List
from collections import defaultdict
import statistics
from src.analyzers.modern_seo_analyzer import ModernSEOAnalyzer
from src.utils.types import AsyncAnalysisContext

class LoadTestMetrics:
    """Load test metrics collection and analysis."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.start_time: float = 0
        self.end_time: float = 0
        self.total_requests: int = 0
        self.successful_requests: int = 0
    
    def start(self) -> None:
        """Start load test measurement."""
        self.start_time = time.time()
    
    def stop(self) -> None:
        """Stop load test measurement."""
        self.end_time = time.time()
    
    def add_response_time(self, duration: float) -> None:
        """Add response time measurement."""
        self.response_times.append(duration)
        self.total_requests += 1
        self.successful_requests += 1
    
    def add_error(self, error_type: str) -> None:
        """Add error count."""
        self.error_counts[error_type] += 1
        self.total_requests += 1
    
    def get_results(self) -> Dict[str, Any]:
        """Get load test results."""
        duration = self.end_time - self.start_time
        
        if not self.response_times:
            return {
                'duration_seconds': duration,
                'total_requests': self.total_requests,
                'successful_requests': 0,
                'error_counts': dict(self.error_counts),
                'error_rate': 1.0 if self.total_requests > 0 else 0.0
            }
        
        return {
            'duration_seconds': duration,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'requests_per_second': self.total_requests / duration,
            'error_counts': dict(self.error_counts),
            'error_rate': sum(self.error_counts.values()) / self.total_requests,
            'response_time_stats': {
                'min': min(self.response_times),
                'max': max(self.response_times),
                'mean': statistics.mean(self.response_times),
                'median': statistics.median(self.response_times),
                'p95': statistics.quantiles(self.response_times, n=20)[18],  # 95th percentile
                'p99': statistics.quantiles(self.response_times, n=100)[98]  # 99th percentile
            }
        }

@pytest.mark.asyncio
async def test_sustained_load(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Test sustained load on the analyzer."""
    metrics = LoadTestMetrics()
    metrics.start()
    
    async def analyze_with_metrics(url: str) -> None:
        try:
            start_time = time.time()
            async with ModernSEOAnalyzer(test_context) as analyzer:
                await analyzer.analyze(url)
            duration = time.time() - start_time
            metrics.add_response_time(duration)
        except Exception as e:
            metrics.add_error(type(e).__name__)
    
    # Create sustained load for 60 seconds
    end_time = time.time() + 60
    tasks = []
    
    while time.time() < end_time:
        # Launch 5 concurrent requests every second
        for _ in range(5):
            task = asyncio.create_task(
                analyze_with_metrics('http://localhost:8080/valid')
            )
            tasks.append(task)
        await asyncio.sleep(1)
    
    # Wait for remaining tasks
    await asyncio.gather(*tasks)
    metrics.stop()
    
    # Save results
    results = metrics.get_results()
    save_results({
        'test_name': 'sustained_load',
        'metrics': results
    })
    
    # Verify performance
    assert results['error_rate'] < 0.1  # Less than 10% errors
    assert results['requests_per_second'] >= 3  # At least 3 RPS
    assert results['response_time_stats']['p95'] < 2.0  # 95% under 2 seconds

@pytest.mark.asyncio
async def test_burst_load(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Test burst load handling."""
    metrics = LoadTestMetrics()
    metrics.start()
    
    async def analyze_with_metrics(url: str) -> None:
        try:
            start_time = time.time()
            async with ModernSEOAnalyzer(test_context) as analyzer:
                await analyzer.analyze(url)
            duration = time.time() - start_time
            metrics.add_response_time(duration)
        except Exception as e:
            metrics.add_error(type(e).__name__)
    
    # Create burst of 50 concurrent requests
    tasks = [
        analyze_with_metrics('http://localhost:8080/valid')
        for _ in range(50)
    ]
    
    await asyncio.gather(*tasks)
    metrics.stop()
    
    # Save results
    results = metrics.get_results()
    save_results({
        'test_name': 'burst_load',
        'metrics': results
    })
    
    # Verify performance
    assert results['error_rate'] < 0.2  # Less than 20% errors
    assert results['response_time_stats']['median'] < 5.0  # Median under 5 seconds

@pytest.mark.asyncio
async def test_error_recovery(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Test recovery from errors under load."""
    metrics = LoadTestMetrics()
    metrics.start()
    
    async def analyze_with_metrics(url: str) -> None:
        try:
            start_time = time.time()
            async with ModernSEOAnalyzer(test_context) as analyzer:
                await analyzer.analyze(url)
            duration = time.time() - start_time
            metrics.add_response_time(duration)
        except Exception as e:
            metrics.add_error(type(e).__name__)
    
    # Mix of valid and error-producing requests
    urls = [
        'http://localhost:8080/valid',
        'http://localhost:8080/error',
        'http://localhost:8080/rate-limit',
        'not-a-url'
    ] * 10  # 40 total requests
    
    tasks = [analyze_with_metrics(url) for url in urls]
    await asyncio.gather(*tasks)
    metrics.stop()
    
    # Save results
    results = metrics.get_results()
    save_results({
        'test_name': 'error_recovery',
        'metrics': results
    })
    
    # Verify error handling
    assert results['successful_requests'] >= len(urls) / 4  # At least 25% success
    assert all(count > 0 for count in results['error_counts'].values())  # All error types occurred

@pytest.mark.asyncio
async def test_memory_leak(
    test_context: AsyncAnalysisContext,
    test_server,
    performance_metrics,
    save_results
):
    """Test for memory leaks under sustained load."""
    performance_metrics.start('memory_leak_test')
    
    async def run_analysis_batch() -> None:
        async with ModernSEOAnalyzer(test_context) as analyzer:
            urls = ['http://localhost:8080/valid'] * 10
            await analyzer.analyze_batch(urls)
    
    # Run multiple batches
    initial_memory = performance_metrics._get_memory_usage()
    
    for _ in range(5):
        await run_analysis_batch()
        await asyncio.sleep(1)  # Allow for GC
    
    final_memory = performance_metrics._get_memory_usage()
    memory_increase = final_memory - initial_memory
    
    performance_metrics.stop()
    save_results({
        'test_name': 'memory_leak',
        'initial_memory_mb': initial_memory,
        'final_memory_mb': final_memory,
        'memory_increase_mb': memory_increase
    })
    
    # Verify no significant memory leak
    assert memory_increase < 50  # Less than 50MB increase

@pytest.mark.asyncio
async def test_cache_performance(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Test cache performance under load."""
    metrics = LoadTestMetrics()
    metrics.start()
    
    # Use same analyzer instance to test cache
    analyzer = ModernSEOAnalyzer(test_context)
    
    async def analyze_with_metrics(url: str, iteration: int) -> None:
        try:
            start_time = time.time()
            async with analyzer:
                await analyzer.analyze(url)
            duration = time.time() - start_time
            metrics.add_response_time(duration)
        except Exception as e:
            metrics.add_error(type(e).__name__)
    
    # Run same URL multiple times
    url = 'http://localhost:8080/valid'
    tasks = [
        analyze_with_metrics(url, i)
        for i in range(20)
    ]
    
    await asyncio.gather(*tasks)
    metrics.stop()
    
    # Save results
    results = metrics.get_results()
    cache_stats = analyzer.cache.stats
    
    save_results({
        'test_name': 'cache_performance',
        'metrics': results,
        'cache_stats': {
            'hits': cache_stats['hits'],
            'misses': cache_stats['misses'],
            'hit_rate': cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])
        }
    })
    
    # Verify cache effectiveness
    assert cache_stats['hits'] > 0
    assert results['response_time_stats']['p95'] < results['response_time_stats']['max'] 