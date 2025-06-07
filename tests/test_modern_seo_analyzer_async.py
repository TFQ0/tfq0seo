import pytest
import asyncio
from bs4 import BeautifulSoup
from aiohttp import web
from typing import Dict, Any
from src.analyzers.modern_seo_analyzer import ModernSEOAnalyzer
from src.utils.types import AsyncAnalysisContext
from src.utils.error_handler import URLFetchError

# Test data
TEST_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Page</title>
    <meta property="og:title" content="Test Page">
    <meta name="twitter:card" content="summary">
    <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Test Page"
        }
    </script>
</head>
<body>
    <img src="test.jpg" width="100" height="100">
    <a href="#" style="width: 44px; height: 44px">Click me</a>
</body>
</html>
"""

@pytest.fixture
def test_context() -> AsyncAnalysisContext:
    """Create test context."""
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
async def test_server():
    """Create test HTTP server."""
    async def handler(request):
        """Handle test requests."""
        if request.path == '/valid':
            return web.Response(
                text=TEST_HTML,
                headers={
                    'Content-Type': 'text/html',
                    'Strict-Transport-Security': 'max-age=31536000',
                    'X-XSS-Protection': '1; mode=block',
                    'Content-Security-Policy': "default-src 'self'"
                }
            )
        elif request.path == '/rate-limit':
            return web.Response(status=429)
        else:
            return web.Response(status=404)

    app = web.Application()
    app.router.add_get('/valid', handler)
    app.router.add_get('/rate-limit', handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    try:
        yield site
    finally:
        await runner.cleanup()

@pytest.mark.asyncio
async def test_analyze_valid_url(test_context, test_server):
    """Test analyzing a valid URL."""
    analyzer = ModernSEOAnalyzer(test_context)
    async with analyzer:
        result = await analyzer.analyze('http://localhost:8080/valid')
    
    assert result['mobile_friendly']['has_viewport']
    assert result['mobile_friendly']['responsive_images']
    assert result['mobile_friendly']['touch_friendly']
    
    assert result['performance']['resource_count']['images'] == 1
    assert result['performance']['resource_count']['scripts'] == 1
    
    assert result['security']['https'] is False
    assert result['security']['hsts'] is True
    assert result['security']['xss_protection'] is True
    assert result['security']['content_security'] is True
    
    assert result['structured_data']['count'] == 1
    assert 'WebPage' in result['structured_data']['types']
    
    assert 'og:title' in result['social_signals']['facebook']
    assert 'twitter:card' in result['social_signals']['twitter']

@pytest.mark.asyncio
async def test_analyze_rate_limited(test_context, test_server):
    """Test handling rate limiting."""
    analyzer = ModernSEOAnalyzer(test_context)
    with pytest.raises(URLFetchError) as exc_info:
        async with analyzer:
            await analyzer.analyze('http://localhost:8080/rate-limit')
    assert 'RATE_LIMIT' in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_invalid_url(test_context, test_server):
    """Test handling invalid URL."""
    analyzer = ModernSEOAnalyzer(test_context)
    with pytest.raises(URLFetchError) as exc_info:
        async with analyzer:
            await analyzer.analyze('not-a-url')
    assert 'INVALID_URL' in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_malicious_url(test_context, test_server):
    """Test handling malicious URL."""
    analyzer = ModernSEOAnalyzer(test_context)
    with pytest.raises(URLFetchError) as exc_info:
        async with analyzer:
            await analyzer.analyze('javascript:alert(1)')
    assert 'MALICIOUS_URL' in str(exc_info.value)

@pytest.mark.asyncio
async def test_check_mobile_friendly():
    """Test mobile-friendly checks."""
    analyzer = ModernSEOAnalyzer(test_context())
    soup = BeautifulSoup(TEST_HTML, 'html.parser')
    result = await analyzer._check_mobile_friendly(soup)
    
    assert result['has_viewport']
    assert result['responsive_images']
    assert result['touch_friendly']
    assert result['no_horizontal_scroll']

@pytest.mark.asyncio
async def test_analyze_performance():
    """Test performance analysis."""
    analyzer = ModernSEOAnalyzer(test_context())
    soup = BeautifulSoup(TEST_HTML, 'html.parser')
    result = await analyzer._analyze_performance(soup)
    
    assert result['resource_count']['images'] == 1
    assert result['resource_count']['scripts'] == 1
    assert result['resource_count']['styles'] == 0
    assert result['total_size'] > 0
    assert result['compression_enabled']
    assert result['cache_headers']

@pytest.mark.asyncio
async def test_extract_structured_data():
    """Test structured data extraction."""
    analyzer = ModernSEOAnalyzer(test_context())
    soup = BeautifulSoup(TEST_HTML, 'html.parser')
    result = await analyzer._extract_structured_data(soup)
    
    assert result['count'] == 1
    assert 'WebPage' in result['types']

@pytest.mark.asyncio
async def test_analyze_social_signals():
    """Test social signals analysis."""
    analyzer = ModernSEOAnalyzer(test_context())
    soup = BeautifulSoup(TEST_HTML, 'html.parser')
    result = await analyzer._analyze_social_signals(soup)
    
    assert 'og:title' in result['facebook']
    assert 'twitter:card' in result['twitter']
    assert not result['linkedin']
    assert not result['pinterest'] 