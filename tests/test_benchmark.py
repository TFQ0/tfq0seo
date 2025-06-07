import pytest
import asyncio
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime

from src.analyzers.modern_seo_analyzer import ModernSEOAnalyzer
from src.utils.types import AsyncAnalysisContext
from src.utils.performance import BatchProcessor, MemoryConfig

@dataclass
class BenchmarkResult:
    """Benchmark result data."""
    name: str
    start_time: str
    end_time: str
    duration_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    requests_per_second: Optional[float] = None
    latency_ms: Optional[float] = None
    throughput_mb: Optional[float] = None
    cache_hit_rate: Optional[float] = None

class BenchmarkRunner:
    """Benchmark test runner."""
    
    def __init__(self, context: AsyncAnalysisContext):
        self.context = context
        self.results: List[BenchmarkResult] = []
        self._start_time: float = 0
        self._end_time: float = 0
        self._start_memory: float = 0
        self._end_memory: float = 0
    
    def start(self) -> None:
        """Start benchmark measurement."""
        self._start_time = time.time()
        self._start_memory = self._get_memory_usage()
    
    def stop(self) -> None:
        """Stop benchmark measurement."""
        self._end_time = time.time()
        self._end_memory = self._get_memory_usage()
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        import psutil
        process = psutil.Process()
        return process.cpu_percent()
    
    def save_result(
        self,
        name: str,
        requests_per_second: Optional[float] = None,
        latency_ms: Optional[float] = None,
        throughput_mb: Optional[float] = None,
        cache_hit_rate: Optional[float] = None
    ) -> None:
        """Save benchmark result."""
        result = BenchmarkResult(
            name=name,
            start_time=datetime.fromtimestamp(self._start_time).isoformat(),
            end_time=datetime.fromtimestamp(self._end_time).isoformat(),
            duration_seconds=self._end_time - self._start_time,
            memory_usage_mb=self._end_memory - self._start_memory,
            cpu_usage_percent=self._get_cpu_usage(),
            requests_per_second=requests_per_second,
            latency_ms=latency_ms,
            throughput_mb=throughput_mb,
            cache_hit_rate=cache_hit_rate
        )
        self.results.append(result)
    
    def save_to_file(self, save_results) -> None:
        """Save all results to file."""
        for result in self.results:
            save_results({
                'benchmark': asdict(result)
            })

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_single_page_analysis(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Benchmark single page analysis performance."""
    runner = BenchmarkRunner(test_context)
    latencies: List[float] = []
    
    async def analyze_with_timing() -> float:
        start = time.time()
        async with ModernSEOAnalyzer(test_context) as analyzer:
            await analyzer.analyze('http://localhost:8080/valid')
        return (time.time() - start) * 1000  # Convert to ms
    
    # Warm up
    await analyze_with_timing()
    
    # Benchmark
    runner.start()
    for _ in range(10):
        latency = await analyze_with_timing()
        latencies.append(latency)
    runner.stop()
    
    avg_latency = statistics.mean(latencies)
    runner.save_result(
        name='single_page_analysis',
        latency_ms=avg_latency,
        requests_per_second=1000 / avg_latency  # Convert ms to RPS
    )
    runner.save_to_file(save_results)

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_batch_analysis_throughput(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Benchmark batch analysis throughput."""
    runner = BenchmarkRunner(test_context)
    
    # Create test batch
    urls = ['http://localhost:8080/valid'] * 100
    total_size_mb = 0
    
    async def measure_throughput() -> float:
        nonlocal total_size_mb
        async with ModernSEOAnalyzer(test_context) as analyzer:
            results = await analyzer.analyze_batch(urls)
            # Estimate size based on result JSON
            total_size_mb = len(json.dumps(results).encode()) / 1024 / 1024
    
    # Warm up
    await measure_throughput()
    
    # Benchmark
    runner.start()
    await measure_throughput()
    runner.stop()
    
    duration = runner.results[-1].duration_seconds if runner.results else 1
    runner.save_result(
        name='batch_analysis_throughput',
        requests_per_second=len(urls) / duration,
        throughput_mb=total_size_mb / duration
    )
    runner.save_to_file(save_results)

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_cache_performance_impact(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Benchmark cache performance impact."""
    runner = BenchmarkRunner(test_context)
    url = 'http://localhost:8080/valid'
    
    async def run_cached_requests() -> Dict[str, int]:
        async with ModernSEOAnalyzer(test_context) as analyzer:
            # First request (cache miss)
            await analyzer.analyze(url)
            
            # Cached requests
            for _ in range(19):  # 20 total requests
                await analyzer.analyze(url)
            
            return analyzer.cache.stats
    
    # Warm up
    await run_cached_requests()
    
    # Benchmark
    runner.start()
    cache_stats = await run_cached_requests()
    runner.stop()
    
    hit_rate = cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])
    runner.save_result(
        name='cache_performance_impact',
        cache_hit_rate=hit_rate,
        requests_per_second=20 / runner.results[-1].duration_seconds if runner.results else 0
    )
    runner.save_to_file(save_results)

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_memory_efficiency(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Benchmark memory efficiency."""
    runner = BenchmarkRunner(test_context)
    
    async def process_large_batch() -> None:
        urls = ['http://localhost:8080/valid'] * 500
        memory_config = MemoryConfig(
            max_memory_mb=200,
            gc_threshold=0.8,
            cleanup_interval=30
        )
        
        async with ModernSEOAnalyzer(test_context) as analyzer:
            processor = BatchProcessor(analyzer, memory_config)
            await processor.process_batch(urls)
    
    # Warm up
    await process_large_batch()
    
    # Benchmark
    runner.start()
    await process_large_batch()
    runner.stop()
    
    runner.save_result(
        name='memory_efficiency',
        throughput_mb=runner.results[-1].memory_usage_mb if runner.results else 0
    )
    runner.save_to_file(save_results)

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_concurrent_analysis_scaling(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Benchmark concurrent analysis scaling."""
    runner = BenchmarkRunner(test_context)
    concurrency_levels = [1, 2, 4, 8, 16]
    url = 'http://localhost:8080/valid'
    
    async def run_concurrent_analysis(concurrency: int) -> float:
        start = time.time()
        tasks = []
        
        async def analyze() -> None:
            async with ModernSEOAnalyzer(test_context) as analyzer:
                await analyzer.analyze(url)
        
        for _ in range(concurrency):
            tasks.append(analyze())
        
        await asyncio.gather(*tasks)
        return time.time() - start
    
    # Test each concurrency level
    for concurrency in concurrency_levels:
        # Warm up
        await run_concurrent_analysis(concurrency)
        
        # Benchmark
        runner.start()
        duration = await run_concurrent_analysis(concurrency)
        runner.stop()
        
        runner.save_result(
            name=f'concurrent_analysis_c{concurrency}',
            requests_per_second=concurrency / duration
        )
    
    runner.save_to_file(save_results)

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_error_handling_overhead(
    test_context: AsyncAnalysisContext,
    test_server,
    save_results
):
    """Benchmark error handling overhead."""
    runner = BenchmarkRunner(test_context)
    error_urls = [
        'http://localhost:8080/error',
        'http://localhost:8080/rate-limit',
        'not-a-url',
        'http://invalid.domain'
    ]
    
    async def measure_error_handling() -> None:
        async with ModernSEOAnalyzer(test_context) as analyzer:
            for url in error_urls:
                try:
                    await analyzer.analyze(url)
                except Exception:
                    pass  # Expected errors
    
    # Warm up
    await measure_error_handling()
    
    # Benchmark
    runner.start()
    await measure_error_handling()
    runner.stop()
    
    runner.save_result(
        name='error_handling_overhead',
        requests_per_second=len(error_urls) / runner.results[-1].duration_seconds if runner.results else 0
    )
    runner.save_to_file(save_results) 