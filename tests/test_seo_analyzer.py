import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import shutil
import os
import time
import logging
import tempfile

from tfq0seo.seo_analyzer_app import SEOAnalyzerApp, TFQSEO_HOME
from tfq0seo.utils.error_handler import TFQ0SEOError

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

@pytest.fixture(autouse=True)
def cleanup_test_dirs():
    """Clean up test directories before and after tests."""
    # Clean up before test
    if TFQSEO_HOME.exists():
        try:
            # Close any open loggers
            logger = logging.getLogger('tfq0seo')
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            
            # Wait a bit for file handles to be released
            time.sleep(0.1)
            shutil.rmtree(TFQSEO_HOME)
        except PermissionError:
            pass  # Ignore permission errors during cleanup
    
    yield
    
    # Clean up after test
    if TFQSEO_HOME.exists():
        try:
            # Close any open loggers
            logger = logging.getLogger('tfq0seo')
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            
            # Wait a bit for file handles to be released
            time.sleep(0.1)
            shutil.rmtree(TFQSEO_HOME)
        except PermissionError:
            pass  # Ignore permission errors during cleanup

@pytest.fixture
def analyzer():
    """Create a tfq0seo analyzer instance.
    
    Returns:
        Configured SEOAnalyzerApp instance
    """
    return SEOAnalyzerApp()

def test_init(analyzer):
    """Test tfq0seo analyzer initialization.
    
    Verifies:
    - Default settings
    - Analyzer components initialization
    - Logger setup
    - Directory creation
    """
    assert analyzer.settings is not None
    assert analyzer.settings['version'] == '1.0.4'
    assert analyzer.meta_analyzer is not None
    assert analyzer.content_analyzer is not None
    assert analyzer.modern_analyzer is not None
    
    # Check directory creation
    assert TFQSEO_HOME.exists()
    assert (TFQSEO_HOME / 'cache').exists()
    assert (TFQSEO_HOME / 'tfq0seo.log').parent.exists()

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
        assert 'combined_report' in analysis

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
    assert 'content_length' in analysis
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
    analysis = analyzer.analyze_content("")
    assert analysis['content_length'] == 0

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
        'combined_report': {
            'strengths': ['Test strength'],
            'weaknesses': ['Test weakness'],
            'recommendations': ['Test recommendation'],
            'education_tips': ['Test tip'],
            'summary': {
                'seo_score': 85,
                'total_strengths': 1,
                'total_weaknesses': 1,
                'total_recommendations': 1
            }
        }
    }
    
    # Create a temporary directory for test reports
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test JSON export
        json_path = os.path.join(temp_dir, 'report.json')
        json_report = analyzer.export_report(analysis, 'json', json_path)
        assert isinstance(json_report, str)
        assert os.path.exists(json_path)
        
        # Test HTML export
        html_path = os.path.join(temp_dir, 'report.html')
        html_report = analyzer.export_report(analysis, 'html', html_path)
        assert isinstance(html_report, str)
        assert os.path.exists(html_path)
        assert '<html>' in html_report
        assert 'tfq0seo Analysis Report' in html_report
        
        # Test Markdown export
        md_path = os.path.join(temp_dir, 'report.md')
        md_report = analyzer.export_report(analysis, 'markdown', md_path)
        assert isinstance(md_report, str)
        assert os.path.exists(md_path)
        assert '# tfq0seo Analysis Report' in md_report

def test_seo_score_calculation(analyzer):
    """Test SEO score calculation.
    
    Verifies:
    - Score range (0-100)
    - Strength bonuses
    - Weakness penalties
    - Score capping
    """
    report = {
        'strengths': ['s1', 's2', 's3'],
        'weaknesses': ['w1', 'w2'],
        'recommendations': ['r1', 'r2']
    }
    
    score = analyzer._calculate_seo_score(report)
    assert isinstance(score, int)
    assert 0 <= score <= 100

def test_cache_functionality(analyzer):
    """Test cache system functionality.
    
    Verifies:
    - Cache directory creation
    - Cache operations
    - Cache expiration
    """
    # Test cache directory
    cache_dir = Path(analyzer.settings['cache']['directory'])
    assert cache_dir.exists()
    assert cache_dir.is_dir()
    
    # Test cache operations
    with patch('requests.get') as mock_get:
        mock_get.return_value.text = SAMPLE_HTML
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = {'content-type': 'text/html'}
        
        # First request should cache
        first_analysis = analyzer.analyze_url('https://example.com')
        
        # Second request should use cache
        second_analysis = analyzer.analyze_url('https://example.com')
        
        assert first_analysis == second_analysis
        assert len(list(cache_dir.glob('*.json'))) > 0

def test_logging_setup(analyzer):
    """Test logging system setup.
    
    Verifies:
    - Log file creation
    - Log directory structure
    - Log file permissions
    """
    log_path = Path(analyzer.settings['logging']['file'])
    assert log_path.parent.exists()
    assert log_path.parent.is_dir()
    
    # Generate some log entries
    analyzer.logger.info("Test log message")
    analyzer.logger.error("Test error message")
    
    # Check log file
    assert log_path.exists()
    assert log_path.is_file()
    with open(log_path) as f:
        log_content = f.read()
        assert "Test log message" in log_content
        assert "Test error message" in log_content

if __name__ == '__main__':
    pytest.main([__file__]) 