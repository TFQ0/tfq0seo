"""Test suite for tfq0seo analyzers."""

import pytest
from bs4 import BeautifulSoup

from tfq0seo.analyzers import (
    analyze_seo,
    analyze_content,
    analyze_technical,
    analyze_performance,
    analyze_links
)


class TestSEOAnalyzer:
    """Test SEO analyzer functions."""
    
    def test_analyze_seo_with_complete_page(self):
        """Test SEO analysis with a complete HTML page."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Test Page Title - Example Site</title>
            <meta name="description" content="This is a test description that should be between 120 and 160 characters long for optimal SEO performance">
            <link rel="canonical" href="https://example.com/test-page">
            <meta property="og:title" content="Test Page Title">
            <meta property="og:description" content="Test description">
            <meta property="og:image" content="https://example.com/image.jpg">
            <meta property="og:url" content="https://example.com/test-page">
        </head>
        <body>
            <h1>Main Heading</h1>
            <img src="test.jpg" alt="Test image">
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_seo(soup, "https://example.com/test-page")
        
        assert 'score' in result
        assert 'issues' in result
        assert 'data' in result
        assert result['score'] > 70  # Should have decent score with basic elements
        assert result['data']['title'] == 'Test Page Title - Example Site'
    
    def test_analyze_seo_missing_critical_elements(self):
        """Test SEO analysis with missing critical elements."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <p>Content without proper SEO elements</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_seo(soup, "https://example.com/bad-page")
        
        assert result['score'] < 50  # Should have low score
        assert len(result['issues']) > 0
        
        # Check for critical issues
        critical_issues = [i for i in result['issues'] if i['severity'] == 'critical']
        assert len(critical_issues) > 0


class TestContentAnalyzer:
    """Test content analyzer functions."""
    
    def test_analyze_content_with_good_content(self):
        """Test content analysis with good content."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Main Title</h1>
            <h2>Subtitle</h2>
            <p>This is a paragraph with enough content to analyze. It contains multiple sentences
            that should provide enough text for readability analysis. The content should be
            analyzed for various metrics including word count, readability scores, and structure.
            We need at least 100 words for proper analysis, so let's add more content here.
            This paragraph discusses various topics and includes different types of sentences.
            Some sentences are short. Others are much longer and include multiple clauses,
            which affects the readability score of the overall content being analyzed.</p>
            <ul>
                <li>List item 1</li>
                <li>List item 2</li>
            </ul>
            <p>Another paragraph to increase content length and provide variety in the structure.
            This helps create a more realistic test case for our content analyzer.</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_content(soup, "https://example.com/content-page")
        
        assert 'score' in result
        assert 'data' in result
        assert result['data']['word_count'] > 100
        assert result['data']['heading_structure']['h1'] == 1
        assert result['data']['heading_structure']['h2'] == 1
    
    def test_analyze_content_too_short(self):
        """Test content analysis with insufficient content."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Title</h1>
            <p>Very short content.</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_content(soup, "https://example.com/short-page")
        
        assert result['score'] < 100
        assert result['data']['word_count'] < 50
        assert len(result['issues']) > 0


class TestTechnicalAnalyzer:
    """Test technical analyzer functions."""
    
    def test_analyze_technical_https(self):
        """Test technical analysis for HTTPS."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>Secure Page</h1>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Test HTTPS
        result = analyze_technical(soup, "https://example.com/page", {}, 200)
        assert result['data']['https'] == True
        
        # Test HTTP
        result = analyze_technical(soup, "http://example.com/page", {}, 200)
        assert result['data']['https'] == False
        assert result['score'] < 100
    
    def test_analyze_technical_mobile_friendly(self):
        """Test technical analysis for mobile friendliness."""
        # Without viewport
        html_no_viewport = """
        <!DOCTYPE html>
        <html><body>Content</body></html>
        """
        soup = BeautifulSoup(html_no_viewport, 'html.parser')
        result = analyze_technical(soup, "https://example.com", {}, 200)
        assert result['data']['has_viewport'] == False
        
        # With viewport
        html_with_viewport = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>Content</body>
        </html>
        """
        soup = BeautifulSoup(html_with_viewport, 'html.parser')
        result = analyze_technical(soup, "https://example.com", {}, 200)
        assert result['data']['has_viewport'] == True


class TestPerformanceAnalyzer:
    """Test performance analyzer functions."""
    
    def test_analyze_performance_fast_page(self):
        """Test performance analysis for a fast page."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="styles.css">
            <script src="script.js" async></script>
        </head>
        <body>
            <h1>Fast Page</h1>
            <img src="image.jpg" loading="lazy" width="100" height="100">
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_performance(soup, "https://example.com", 1.5, 50000)
        
        assert 'score' in result
        assert 'data' in result
        assert result['data']['load_time'] == 1.5
        assert result['data']['content_size'] == 50000
    
    def test_analyze_performance_slow_page(self):
        """Test performance analysis for a slow page."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            """ + ''.join([f'<script src="script{i}.js"></script>' for i in range(15)]) + """
            """ + ''.join([f'<link rel="stylesheet" href="style{i}.css">' for i in range(10)]) + """
        </head>
        <body>
            <h1>Slow Page</h1>
            """ + ''.join([f'<img src="image{i}.jpg">' for i in range(20)]) + """
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_performance(soup, "https://example.com", 6.0, 5000000)
        
        assert result['score'] < 50  # Should have poor score
        assert len(result['issues']) > 0
        assert result['data']['total_resources'] > 40


class TestLinksAnalyzer:
    """Test links analyzer functions."""
    
    def test_analyze_links_internal_external(self):
        """Test link analysis for internal and external links."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <nav>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
                <a href="https://example.com/page">Internal Full URL</a>
            </nav>
            <a href="https://external.com">External Site</a>
            <a href="https://another.com" target="_blank" rel="noopener">Another External</a>
            <footer>
                <a href="/privacy">Privacy</a>
            </footer>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_links(soup, "https://example.com")
        
        assert 'data' in result
        assert result['data']['internal_links_count'] > 0
        assert result['data']['external_links_count'] > 0
        assert result['data']['navigation_links_count'] > 0
        assert result['data']['footer_links_count'] > 0
    
    def test_analyze_links_no_links(self):
        """Test link analysis with no links."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Page without links</h1>
            <p>Content here</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = analyze_links(soup, "https://example.com")
        
        assert result['data']['total_links'] == 0
        assert result['score'] < 100
        assert len(result['issues']) > 0


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for the complete analysis flow."""
    
    async def test_full_page_analysis(self):
        """Test complete page analysis with all analyzers."""
        from tfq0seo.core.app import SEOAnalyzer
        
        analyzer = SEOAnalyzer()
        
        # Create mock page data
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Complete Test Page</title>
            <meta name="description" content="A complete test page for integration testing of all SEO analyzers">
        </head>
        <body>
            <h1>Main Heading</h1>
            <p>This is a test page with enough content to properly test all analyzers.
            The content needs to be substantial enough for readability analysis.</p>
            <h2>Subheading</h2>
            <p>More content here to increase word count and provide structure.</p>
            <a href="/internal">Internal Link</a>
            <a href="https://example.com">External Link</a>
        </body>
        </html>
        """
        
        page_data = {
            'url': 'https://example.com/test',
            'status_code': 200,
            'load_time': 2.0,
            'content_length': len(html),
            'headers': {'content-type': 'text/html'},
            'html': html,
            'soup': BeautifulSoup(html, 'html.parser'),
            'timestamp': 1234567890
        }
        
        result = await analyzer.analyze_page(page_data)
        
        assert 'overall_score' in result
        assert 'issues' in result
        assert 'recommendations' in result
        assert all(key in result for key in ['seo', 'content', 'technical', 'performance', 'links'])
        assert result['overall_score'] > 0
        assert result['overall_score'] <= 100
