"""Benchmark script for tfq0seo performance testing."""

import asyncio
import time
import json
import psutil
from datetime import datetime
from typing import Dict, Any

from .core.app import SEOAnalyzer
from .core.config import Config


async def benchmark_single_page(url: str = "https://example.com") -> Dict[str, Any]:
    """Benchmark single page analysis."""
    print(f"🔍 Benchmarking single page analysis: {url}")
    
    config = Config()
    analyzer = SEOAnalyzer(config)
    
    # Memory before
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Time the analysis
    start_time = time.time()
    result = await analyzer.analyze_url(url)
    end_time = time.time()
    
    # Memory after
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    
    duration = end_time - start_time
    mem_used = mem_after - mem_before
    
    benchmark = {
        'type': 'single_page',
        'url': url,
        'duration_seconds': round(duration, 3),
        'memory_used_mb': round(mem_used, 2),
        'score': result.get('overall_score', 0) if result else 0,
        'issues_found': len(result.get('issues', [])) if result else 0,
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"✅ Completed in {duration:.2f}s, Memory: {mem_used:.2f}MB")
    print(f"   Score: {benchmark['score']:.1f}/100, Issues: {benchmark['issues_found']}")
    
    return benchmark


async def benchmark_crawl(start_url: str = "https://example.com", max_pages: int = 10) -> Dict[str, Any]:
    """Benchmark website crawl."""
    print(f"🕷️ Benchmarking crawl: {start_url} (max {max_pages} pages)")
    
    config = Config()
    config.crawler.max_pages = max_pages
    config.crawler.max_concurrent = 10
    analyzer = SEOAnalyzer(config)
    
    # Memory before
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Time the crawl
    start_time = time.time()
    pages_analyzed = 0
    
    async for result in analyzer.crawl_site(start_url):
        pages_analyzed += 1
        if pages_analyzed % 5 == 0:
            print(f"   Analyzed {pages_analyzed} pages...")
    
    end_time = time.time()
    
    # Memory after
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    
    duration = end_time - start_time
    mem_used = mem_after - mem_before
    pages_per_second = pages_analyzed / duration if duration > 0 else 0
    
    benchmark = {
        'type': 'crawl',
        'start_url': start_url,
        'pages_analyzed': pages_analyzed,
        'max_pages': max_pages,
        'duration_seconds': round(duration, 3),
        'memory_used_mb': round(mem_used, 2),
        'pages_per_second': round(pages_per_second, 2),
        'avg_time_per_page': round(duration / pages_analyzed, 3) if pages_analyzed > 0 else 0,
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"✅ Completed {pages_analyzed} pages in {duration:.2f}s")
    print(f"   Speed: {pages_per_second:.2f} pages/sec, Memory: {mem_used:.2f}MB")
    
    return benchmark


async def benchmark_batch(urls: list, concurrent: int = 10) -> Dict[str, Any]:
    """Benchmark batch URL analysis."""
    print(f"📦 Benchmarking batch analysis: {len(urls)} URLs")
    
    config = Config()
    config.crawler.max_concurrent = concurrent
    analyzer = SEOAnalyzer(config)
    
    # Memory before
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Time the batch
    start_time = time.time()
    pages_analyzed = 0
    
    async for result in analyzer.analyze_urls(urls):
        pages_analyzed += 1
    
    end_time = time.time()
    
    # Memory after
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    
    duration = end_time - start_time
    mem_used = mem_after - mem_before
    pages_per_second = pages_analyzed / duration if duration > 0 else 0
    
    benchmark = {
        'type': 'batch',
        'urls_count': len(urls),
        'pages_analyzed': pages_analyzed,
        'concurrent': concurrent,
        'duration_seconds': round(duration, 3),
        'memory_used_mb': round(mem_used, 2),
        'pages_per_second': round(pages_per_second, 2),
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"✅ Completed {pages_analyzed} URLs in {duration:.2f}s")
    print(f"   Speed: {pages_per_second:.2f} pages/sec, Memory: {mem_used:.2f}MB")
    
    return benchmark


def compare_with_targets() -> Dict[str, Any]:
    """Compare benchmark results with target metrics."""
    targets = {
        'single_page': {
            'duration_seconds': 2.0,
            'memory_mb': 50
        },
        'crawl_100': {
            'duration_seconds': 120,  # 2 minutes for 100 pages
            'memory_mb': 200,
            'pages_per_second': 1.0
        },
        'crawl_500': {
            'duration_seconds': 480,  # 8 minutes for 500 pages
            'memory_mb': 500,
            'pages_per_second': 1.0
        }
    }
    
    return targets


async def run_all_benchmarks():
    """Run all benchmarks and save results."""
    print("=" * 60)
    print("🚀 TFQ0SEO Performance Benchmark Suite")
    print("=" * 60)
    print()
    
    results = {
        'benchmarks': [],
        'system_info': {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'python_version': __import__('sys').version,
            'timestamp': datetime.now().isoformat()
        }
    }
    
    # Test URLs
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://www.python.org",
        "https://docs.python.org",
        "https://pypi.org"
    ]
    
    try:
        # Single page benchmark
        single_result = await benchmark_single_page(test_urls[0])
        results['benchmarks'].append(single_result)
        print()
        
        # Batch benchmark
        batch_result = await benchmark_batch(test_urls[:3], concurrent=3)
        results['benchmarks'].append(batch_result)
        print()
        
        # Small crawl benchmark
        crawl_result = await benchmark_crawl(test_urls[0], max_pages=5)
        results['benchmarks'].append(crawl_result)
        print()
        
    except Exception as e:
        print(f"❌ Benchmark error: {e}")
        results['error'] = str(e)
    
    # Performance comparison
    print("=" * 60)
    print("📊 Performance vs Targets")
    print("=" * 60)
    
    targets = compare_with_targets()
    
    for benchmark in results['benchmarks']:
        if benchmark['type'] == 'single_page':
            target = targets['single_page']
            speed_ratio = target['duration_seconds'] / benchmark['duration_seconds']
            status = "✅" if speed_ratio >= 1 else "⚠️"
            print(f"{status} Single Page: {benchmark['duration_seconds']}s (target: {target['duration_seconds']}s)")
            print(f"   Speed ratio: {speed_ratio:.2f}x")
    
    # Save results
    output_file = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print()
    print(f"💾 Results saved to: {output_file}")
    
    return results


def main():
    """Main entry point for benchmark script."""
    try:
        results = asyncio.run(run_all_benchmarks())
        
        # Summary
        print()
        print("=" * 60)
        print("✨ Benchmark Summary")
        print("=" * 60)
        
        total_time = sum(b['duration_seconds'] for b in results['benchmarks'])
        total_pages = sum(b.get('pages_analyzed', 1) for b in results['benchmarks'])
        avg_speed = total_pages / total_time if total_time > 0 else 0
        
        print(f"Total pages analyzed: {total_pages}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average speed: {avg_speed:.2f} pages/sec")
        
        # Performance grade
        if avg_speed >= 2.0:
            grade = "A+ (Excellent)"
        elif avg_speed >= 1.5:
            grade = "A (Very Good)"
        elif avg_speed >= 1.0:
            grade = "B (Good)"
        elif avg_speed >= 0.5:
            grade = "C (Acceptable)"
        else:
            grade = "D (Needs Improvement)"
        
        print(f"Performance Grade: {grade}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
