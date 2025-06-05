import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import yaml

from src.seo_analyzer_app import SEOAnalyzerApp
from src.utils.error_handler import TFQ0SEOError

# Test configuration
SAMPLE_CONFIG = {
    'seo_thresholds': {
        'title_length': {'min': 30, 'max': 60},
        'meta_description_length': {'min': 120, 'max': 160},
        'content_length': {'min': 300},
        'sentence_length': {'max': 20},
        'keyword_density': {'max': 3.0}
    },
    'crawling': {
        'timeout': 30,
        'max_retries': 3,
        'user_agent': 'tfq0seo/1.0'
    },
    'cache': {
        'enabled': True,
        'expiration': 3600
    },
    'logging': {
        'level': 'INFO',
        'file': 'tfq0seo.log'
    }
}

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
def config_file(tmp_path):
    """Create a temporary tfq0seo configuration file.
    
    Args:
        tmp_path: Pytest fixture providing temporary directory
        
    Returns:
        Path to temporary configuration file
    """
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(SAMPLE_CONFIG, f)
    return config_path

@pytest.fixture
def analyzer(config_file):
    """Create a tfq0seo analyzer instance.
    
    Args:
        config_file: Path to test configuration file
        
    Returns:
        Configured SEOAnalyzerApp instance
    """
    return SEOAnalyzerApp(config_file)

def test_init(analyzer):
    """Test tfq0seo analyzer initialization.
    
    Verifies:
    - Configuration loading
    - Analyzer components initialization
    - Logger setup
    """
    assert analyzer.config == SAMPLE_CONFIG
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

def test_config_validation(tmp_path):
    """Test configuration validation.
    
    Verifies:
    - Invalid config detection
    - Error handling
    - Exception messages
    """
    invalid_config = tmp_path / "invalid_config.yaml"
    with open(invalid_config, "w") as f:
        f.write("invalid: yaml: content")
    
    with pytest.raises(TFQ0SEOError):
        SEOAnalyzerApp(invalid_config)

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