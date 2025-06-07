import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.seo_analyzer_app import SEOAnalyzerApp
from src.utils.error_handler import TFQ0SEOError

# Sample HTML for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Page Title</title>
    <meta name="description" content="This is a test page description">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta property="og:title" content="Test Page">
    <link rel="canonical" href="https://example.com">
</head>
<body>
    <h1>Main Heading</h1>
    <p>This is a test paragraph with some content.</p>
    <img src="test.jpg" alt="Test image">
    <a href="https://example.com">Link</a>
</body>
</html>
"""

@pytest.fixture
def analyzer():
    """Create a tfq0seo analyzer instance.
    
    Returns:
        SEOAnalyzerApp instance
    """
    return SEOAnalyzerApp()

def test_init(analyzer):
    """Test tfq0seo analyzer initialization.
    
    Verifies:
    - Analyzer components initialization
    - Logger setup
    """
    assert analyzer.meta_analyzer is not None
    assert analyzer.content_analyzer is not None
    assert analyzer.modern_analyzer is not None

def test_analyze_url(analyzer):
    """Test URL analysis functionality.
    
    Verifies:
    - URL fetching
    - HTML parsing
    - Meta tag analysis
    - Content analysis
    - Modern SEO features
    - Report generation
    """
    with patch('requests.get') as mock_get:
        mock_get.return_value.text = SAMPLE_HTML
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = {'content-type': 'text/html'}
        
        analysis = analyzer.analyze_url('https://example.com')
        
        assert analysis is not None
        assert 'meta_analysis' in analysis
        assert 'content_analysis' in analysis
        assert 'modern_seo_analysis' in analysis

def test_analyze_content(analyzer):
    """Test content analysis functionality.
    
    Verifies:
    - Content length calculation
    - Keyword analysis
    - Content optimization
    - Report generation
    """
    content = "This is a test content piece that should be analyzed for SEO optimization."
    analysis = analyzer.analyze_content(content, target_keyword="test")
    
    assert analysis is not None
    assert 'target_keyword' in analysis
    assert 'content_analysis' in analysis

def test_invalid_url(analyzer):
    """Test invalid URL handling.
    
    Verifies:
    - Error detection
    - Exception handling
    - Error reporting
    """
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Invalid URL")
        
        with pytest.raises(TFQ0SEOError):
            analyzer.analyze_url('invalid-url')

def test_empty_content(analyzer):
    """Test empty content handling.
    
    Verifies:
    - Empty content detection
    - Zero-length content handling
    - Report generation
    """
    with pytest.raises(TFQ0SEOError):
        analyzer.analyze_content("")

def test_educational_resources(analyzer):
    """Test educational resources functionality.
    
    Verifies:
    - Resource availability
    - Topic categorization
    - Content structure
    """
    resources = analyzer.get_educational_resources()
    
    assert resources is not None
    assert 'meta_tags' in resources
    assert 'content_optimization' in resources
    assert 'technical_seo' in resources

def test_export_report_formats(analyzer):
    """Test report export functionality.
    
    Verifies:
    - JSON export
    - HTML export
    - Markdown export
    - Report formatting
    """
    analysis = {
        'meta_analysis': {'title': 'Test'},
        'content_analysis': {'length': 100},
        'modern_seo_analysis': {'mobile_friendly': True}
    }
    
    # Test JSON export
    json_report = analyzer.export_report(analysis, 'json')
    assert isinstance(json_report, str)
    
    # Test HTML export
    html_report = analyzer.export_report(analysis, 'html')
    assert isinstance(html_report, str)
    assert '<html>' in html_report
    assert 'tfq0seo Analysis Report' in html_report
    
    # Test Markdown export
    md_report = analyzer.export_report(analysis, 'markdown')
    assert isinstance(md_report, str)
    assert '# tfq0seo Analysis Report' in md_report

def test_recommendation_details(analyzer):
    """Test recommendation details functionality.
    
    Verifies:
    - Detail structure
    - Implementation steps
    - Resource links
    - Importance levels
    """
    details = analyzer.get_recommendation_details("Test recommendation")
    
    assert details is not None
    assert 'recommendation' in details
    assert 'importance' in details
    assert 'implementation_guide' in details
    assert 'resources' in details

if __name__ == '__main__':
    pytest.main([__file__]) 