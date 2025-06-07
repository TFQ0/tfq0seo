import pytest
import asyncio
import aiohttp
from aiohttp import web
import logging
from typing import Dict, Any, AsyncGenerator, Generator
from pathlib import Path
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime

from src.utils.types import AsyncAnalysisContext, CacheConfig, MemoryConfig
from src.utils.performance import HTMLParser
from src.analyzers.modern_seo_analyzer import ModernSEOAnalyzer

# Configure logging for tests
logging.basicConfig(level=logging.INFO)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / 'test_data'
TEST_DATA_DIR.mkdir(exist_ok=True)

@pytest.fixture
def test_html() -> str:
    """Sample HTML for testing."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Page</title>
        <meta name="description" content="Test description">
        <meta property="og:title" content="Test Page">
        <meta name="twitter:card" content="summary">
        <link rel="stylesheet" href="style.css">
        <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": "Test Page",
                "description": "Test description"
            }
        </script>
    </head>
    <body>
        <h1>Welcome to Test Page</h1>
        <p>This is a test paragraph with some content.</p>
        <img src="test.jpg" width="800" height="600" alt="Test Image">
        <a href="#" style="width: 44px; height: 44px">Click me</a>
        <div itemscope itemtype="http://schema.org/Product">
            <span itemprop="name">Test Product</span>
            <span itemprop="price">$19.99</span>
        </div>
    </body>
    </html>
    """

@pytest.fixture
def test_context() -> AsyncAnalysisContext:
    """Test analysis context."""
    return {
        'headers': {
            'User_Agent': 'tfq0seo-test/1.0',
            'Accept': '*/*',
            'Accept_Language': 'en-US,en;q=0.9',
            'Accept_Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        },
        'timeout': 10.0,
        'max_retries': 3,
        'backoff_factor': 1.0,
        'concurrent_limit': 5,
        'secret_key': 'test-key'
    }

@pytest.fixture
def cache_config() -> CacheConfig:
    """Test cache configuration."""
    return {
        'enabled': True,
        'expiration': 300,
        'max_entries': 1000,
        'max_memory_mb': 100
    }

@pytest.fixture
def memory_config() -> MemoryConfig:
    """Test memory configuration."""
    return MemoryConfig(
        max_memory_mb=100,
        gc_threshold=0.8,
        cleanup_interval=60
    )

class TestServer:
    """Test HTTP server for integration testing."""
    
    def __init__(self):
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup test routes."""
        self.app.router.add_get('/', self.handle_home)
        self.app.router.add_get('/valid', self.handle_valid)
        self.app.router.add_get('/rate-limit', self.handle_rate_limit)
        self.app.router.add_get('/error', self.handle_error)
        self.app.router.add_get('/robots.txt', self.handle_robots)
        self.app.router.add_get('/sitemap.xml', self.handle_sitemap)

    async def handle_home(self, request: web.Request) -> web.Response:
        """Handle home page request."""
        return web.Response(text='Test Server')

    async def handle_valid(self, request: web.Request) -> web.Response:
        """Handle valid page request."""
        return web.Response(
            text=TEST_HTML,
            headers={
                'Content-Type': 'text/html',
                'Strict-Transport-Security': 'max-age=31536000',
                'X-XSS-Protection': '1; mode=block',
                'Content-Security-Policy': "default-src 'self'"
            }
        )

    async def handle_rate_limit(self, request: web.Request) -> web.Response:
        """Handle rate-limited request."""
        return web.Response(status=429)

    async def handle_error(self, request: web.Request) -> web.Response:
        """Handle error page request."""
        return web.Response(status=500)

    async def handle_robots(self, request: web.Request) -> web.Response:
        """Handle robots.txt request."""
        return web.Response(
            text="""
            User-agent: *
            Allow: /
            Sitemap: http://localhost:8080/sitemap.xml
            """,
            content_type='text/plain'
        )

    async def handle_sitemap(self, request: web.Request) -> web.Response:
        """Handle sitemap.xml request."""
        return web.Response(
            text="""
            <?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url>
                    <loc>http://localhost:8080/</loc>
                    <lastmod>2024-01-01</lastmod>
                </url>
            </urlset>
            """,
            content_type='application/xml'
        )

    async def start(self) -> None:
        """Start test server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', 8080)
        await self.site.start()

    async def stop(self) -> None:
        """Stop test server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

@pytest.fixture
async def test_server() -> AsyncGenerator[TestServer, None]:
    """Create and manage test server."""
    server = TestServer()
    await server.start()
    yield server
    await server.stop()

@pytest.fixture
def html_parser(memory_config: MemoryConfig) -> HTMLParser:
    """Create HTML parser."""
    return HTMLParser(memory_config)

@pytest.fixture
async def analyzer(test_context: AsyncAnalysisContext) -> AsyncGenerator[ModernSEOAnalyzer, None]:
    """Create and manage SEO analyzer."""
    analyzer = ModernSEOAnalyzer(test_context)
    async with analyzer:
        yield analyzer

class PerformanceMetrics:
    """Performance metrics collection."""
    
    def __init__(self):
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.memory_start: float = 0.0
        self.memory_end: float = 0.0
        self.operation: str = ''

    def start(self, operation: str) -> None:
        """Start measuring."""
        self.operation = operation
        self.start_time = asyncio.get_event_loop().time()
        self.memory_start = self._get_memory_usage()

    def stop(self) -> None:
        """Stop measuring."""
        self.end_time = asyncio.get_event_loop().time()
        self.memory_end = self._get_memory_usage()

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def get_results(self) -> Dict[str, Any]:
        """Get performance results."""
        return {
            'operation': self.operation,
            'duration_seconds': self.end_time - self.start_time,
            'memory_usage_mb': self.memory_end - self.memory_start
        }

@pytest.fixture
def performance_metrics() -> PerformanceMetrics:
    """Create performance metrics collector."""
    return PerformanceMetrics()

def save_performance_results(results: Dict[str, Any]) -> None:
    """Save performance results to file."""
    results_file = TEST_DATA_DIR / 'performance_results.json'
    
    # Load existing results
    if results_file.exists():
        with open(results_file, 'r') as f:
            existing_results = json.load(f)
    else:
        existing_results = []
    
    # Add new results
    existing_results.append({
        **results,
        'timestamp': str(datetime.now())
    })
    
    # Save updated results
    with open(results_file, 'w') as f:
        json.dump(existing_results, f, indent=2)

@pytest.fixture
def save_results(request):
    """Fixture to save test results."""
    def _save_results(results: Dict[str, Any]) -> None:
        save_performance_results(results)
    return _save_results 