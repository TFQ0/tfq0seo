import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import shutil
import os
import time
import logging
import tempfile
import requests
from bs4 import BeautifulSoup

from tfq0seo.seo_analyzer_app import SEOAnalyzerApp, CrawlConfig, CrawlResult, TFQSEO_HOME
from tfq0seo.utils.error_handler import TFQ0SEOError, validate_url, sanitize_url
from tfq0seo.analyzers.content_analyzer import ContentAnalyzer
from tfq0seo.analyzers.modern_seo_analyzer import ModernSEOAnalyzer

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

# HTML with JavaScript and CSS for testing content extraction
COMPLEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Complex Page</title>
    <style>
        .test { color: red; transform: translate3d(0,0,0); }
        var { font-size: 12px; }
    </style>
    <script>
        var test = function() { return 'test'; };
        if (true) { console.log('test'); }
    </script>
</head>
<body>
    <h1>Real Content Heading</h1>
    <p>This is meaningful content that should be counted.</p>
    <p>Another paragraph with real words for analysis.</p>
    <script>
        var more = 'javascript';
        function transform() { return 'code'; }
    </script>
    <div>More meaningful content here.</div>
</body>
</html>
"""

# HTML with keyword stuffing
KEYWORD_STUFFING_HTML = """
<!DOCTYPE html>
<html>
<head><title>SEO Test Page</title></head>
<body>
    <h1>SEO SEO SEO Best Practices</h1>
    <p>SEO is important. SEO helps websites. SEO optimization is key. 
       SEO techniques matter. SEO strategies work. SEO tools help.
       SEO analysis shows SEO problems. SEO fixes improve SEO rankings.</p>
    <p>This paragraph has normal content without excessive repetition.</p>
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

@pytest.fixture
def content_analyzer():
    """Create a content analyzer instance."""
    config = {
        'seo_thresholds': {
            'content_length': {'min': 300}
        }
    }
    return ContentAnalyzer(config)

@pytest.fixture
def modern_seo_analyzer():
    """Create a modern SEO analyzer instance."""
    config = {
        'crawling': {
            'user_agent': 'TFQ0SEO-Test/2.0'
        }
    }
    return ModernSEOAnalyzer(config)

# ============================================================================
# ROOT CAUSE FIX TESTS
# ============================================================================

def test_meaningful_content_extraction(analyzer):
    """Test that meaningful content is properly extracted, excluding JS/CSS."""
    soup = BeautifulSoup(COMPLEX_HTML, 'html.parser')
    
    # Test the new meaningful content extraction
    meaningful_content = analyzer._extract_meaningful_content(soup)
    
    # Should contain real content
    assert "Real Content Heading" in meaningful_content
    assert "meaningful content that should be counted" in meaningful_content
    assert "Another paragraph with real words" in meaningful_content
    
    # Should NOT contain JavaScript/CSS
    assert "var test = function" not in meaningful_content
    assert "transform: translate3d" not in meaningful_content
    assert "console.log" not in meaningful_content
    assert "font-size: 12px" not in meaningful_content

def test_meaningful_word_count(analyzer):
    """Test that word count excludes technical terms and counts real words."""
    # Test with complex HTML containing JS/CSS
    soup = BeautifulSoup(COMPLEX_HTML, 'html.parser')
    meaningful_content = analyzer._extract_meaningful_content(soup)
    word_count = analyzer._count_meaningful_words(meaningful_content)
    
    # Should count real words, not technical terms
    assert word_count > 0
    assert word_count < 50  # Should be reasonable count, not inflated by JS/CSS
    
    # Test with pure content
    pure_content = "This is a test with exactly ten meaningful words here."
    pure_word_count = analyzer._count_meaningful_words(pure_content)
    assert pure_word_count == 10

def test_https_detection_fix(modern_seo_analyzer):
    """Test that HTTPS detection properly verifies SSL certificates."""
    
    # Mock successful HTTPS response
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.url = 'https://example.com'
        mock_response.headers = {
            'strict-transport-security': 'max-age=31536000',
            'x-xss-protection': '1; mode=block'
        }
        mock_response.text = '<html></html>'
        mock_get.return_value = mock_response
        
        # Mock SSL verification
        with patch('socket.create_connection'), patch('ssl.create_default_context'):
            analysis = modern_seo_analyzer._analyze_security('https://example.com')
            
            assert analysis['https'] == True
            assert analysis['ssl_certificate_valid'] == True
            assert analysis['original_url_https'] == True
            assert analysis['hsts'] == True

def test_https_ssl_error_handling(modern_seo_analyzer):
    """Test SSL error handling in HTTPS detection."""
    
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.SSLError("SSL verification failed")
        
        analysis = modern_seo_analyzer._analyze_security('https://badssl.example')
        
        assert analysis['https'] == True  # URL starts with https
        assert analysis['ssl_certificate_valid'] == False
        assert analysis['ssl_error'] == True
        assert 'error' in analysis

def test_keyword_stuffing_detection(content_analyzer):
    """Test that keyword stuffing is properly detected."""
    soup = BeautifulSoup(KEYWORD_STUFFING_HTML, 'html.parser')
    
    # Extract meaningful content (should exclude technical terms)
    meaningful_content = content_analyzer._clean_text_for_analysis(soup.get_text())
    
    # Analyze keywords
    keyword_analysis = content_analyzer._analyze_keywords(meaningful_content)
    
    # Should detect keyword stuffing
    stuffing_detected = keyword_analysis.get('keyword_stuffing_detected', [])
    assert len(stuffing_detected) > 0
    
    # 'SEO' should be flagged as stuffed
    seo_stuffing = next((item for item in stuffing_detected if item['keyword'] == 'seo'), None)
    assert seo_stuffing is not None
    assert seo_stuffing['density'] > 3.0  # More than 3% density
    assert seo_stuffing['count'] > 5  # Appears more than 5 times

def test_keyword_analysis_excludes_technical_terms(content_analyzer):
    """Test that keyword analysis excludes technical/code terms."""
    # Content with technical terms that should be filtered out
    technical_content = """
    var function return if else for while class id px em rem vh vw deg ms
    transform translate3d webkit moz opacity rgba href src alt title
    div span img link script style html body head
    This is real content that should be analyzed properly.
    """
    
    keyword_analysis = content_analyzer._analyze_keywords(technical_content)
    
    # Check that technical terms are not in top keywords
    top_keywords = [kw['keyword'] for kw in keyword_analysis['top_keywords']]
    
    technical_terms = ['var', 'function', 'transform', 'translate3d', 'webkit', 'px', 'div', 'span']
    for term in technical_terms:
        assert term not in top_keywords, f"Technical term '{term}' should be filtered out"
    
    # Real content words should be present
    assert any(kw in ['real', 'content', 'analyzed', 'properly'] for kw in top_keywords)

def test_dynamic_seo_scoring(analyzer):
    """Test that SEO scoring is dynamic and based on actual analysis."""
    
    # Test with good SEO elements
    good_report = {
        'analysis_modules': {
            'modern_seo': {
                'security': {
                    'https': True,
                    'ssl_certificate_valid': True,
                    'hsts': True,
                    'xss_protection': True,
                    'content_security': True
                },
                'structured_data': {
                    'schema_types': ['Organization', 'WebPage']
                },
                'mobile_friendly': {
                    'responsive_viewport': True,
                    'viewport_meta': True,
                    'touch_elements_spacing': {'potentially_small': 0}
                },
                'html_structure': {
                    'optimizations': {
                        'image_optimization': {'missing_alt': 0}
                    }
                }
            },
            'basic_seo': {
                'title': 'Perfect SEO Title Length Here',  # 30-60 chars
                'meta_description': 'This is a perfect meta description that is between 120 and 160 characters long for optimal SEO performance and click rates.',  # 120-160 chars
                'headings': {'h1': ['Single H1 Tag']}
            },
            'content': {
                'basic_metrics': {'word_count': 1200},
                'readability': {'flesch_reading_ease': 70},
                'keyword_analysis': {
                    'total_meaningful_words': 1200,
                    'keyword_stuffing_detected': []
                },
                'content_structure': {
                    'content_sections': 5,
                    'avg_paragraph_length': 50
                }
            },
            'advanced_seo': {
                'url_analysis': {
                    'is_seo_friendly': True,
                    'seo_score': 85
                }
            }
        }
    }
    
    good_score = analyzer._calculate_seo_score(good_report)
    assert good_score >= 80, f"Good SEO should score high, got {good_score}"
    
    # Test with poor SEO elements
    poor_report = {
        'analysis_modules': {
            'modern_seo': {
                'security': {'https': False},
                'structured_data': {'schema_types': []},
                'mobile_friendly': {'responsive_viewport': False, 'viewport_meta': False},
                'html_structure': {'optimizations': {'image_optimization': {'missing_alt': 10}}}
            },
            'basic_seo': {
                'title': '',  # Missing title
                'meta_description': '',  # Missing meta description
                'headings': {'h1': []}  # No H1 tags
            },
            'content': {
                'basic_metrics': {'word_count': 50},  # Too short
                'readability': {'flesch_reading_ease': 0},
                'keyword_analysis': {
                    'total_meaningful_words': 50,
                    'keyword_stuffing_detected': [{'keyword': 'spam', 'density': 10}]
                },
                'content_structure': {'content_sections': 1, 'avg_paragraph_length': 0}
            },
            'advanced_seo': {
                'url_analysis': {'is_seo_friendly': False, 'seo_score': 20}
            }
        }
    }
    
    poor_score = analyzer._calculate_seo_score(poor_report)
    assert poor_score <= 30, f"Poor SEO should score low, got {poor_score}"
    
    # Ensure good score is significantly higher than poor score
    assert good_score - poor_score >= 50, "Score difference should be significant"

def test_real_time_analysis_insights(analyzer):
    """Test that real-time insights are generated based on actual analysis."""
    
    # Mock analysis modules with various issues
    analysis_modules = {
        'modern_seo': {
            'security': {
                'https': False,  # Critical issue
                'ssl_certificate_valid': False
            },
            'mobile_friendly': {
                'viewport_meta': False  # Critical issue
            },
            'structured_data': {
                'schema_types': []  # Opportunity
            }
        },
        'content': {
            'basic_metrics': {'word_count': 150},  # Thin content
            'keyword_analysis': {
                'keyword_stuffing_detected': [
                    {'keyword': 'seo', 'density': 8.5, 'count': 12}
                ]
            }
        },
        'basic_seo': {
            'title': '',  # Missing title
            'meta_description': 'This meta description is way too long and exceeds the recommended 160 character limit which can cause truncation in search results',  # Too long
            'headings': {'h1': ['H1 One', 'H1 Two']}  # Multiple H1s
        }
    }
    
    insights = analyzer._generate_real_time_insights(analysis_modules)
    
    # Check critical issues are detected
    critical_issues = insights['critical_issues']
    assert any('HTTPS' in issue for issue in critical_issues)
    assert any('viewport' in issue for issue in critical_issues)
    assert any('keyword stuffing' in issue for issue in critical_issues)
    assert any('title tag' in issue for issue in critical_issues)
    
    # Check opportunities are identified
    opportunities = insights['opportunities']
    assert any('thin' in opp and '150 words' in opp for opp in opportunities)
    assert any('meta description too long' in opp for opp in opportunities)
    assert any('Multiple H1 tags' in opp for opp in opportunities)
    assert any('structured data' in opp for opp in opportunities)
    
    # Check recommendations are provided
    recommendations = insights['recommendations']
    assert any('HTTPS' in rec for rec in recommendations)
    assert any('keyword density' in rec for rec in recommendations)

def test_url_validation_and_sanitization():
    """Test URL validation and sanitization functions."""
    
    # Valid URLs
    assert validate_url('https://example.com') == True
    assert validate_url('http://example.com') == True
    assert validate_url('https://sub.example.com/path') == True
    assert validate_url('https://example.com:8080') == True
    
    # Invalid URLs
    assert validate_url('not-a-url') == False
    assert validate_url('ftp://example.com') == False
    assert validate_url('') == False
    assert validate_url('https://') == False
    
    # URL sanitization
    assert sanitize_url('example.com') == 'https://example.com'
    assert sanitize_url('http://example.com/') == 'http://example.com'
    assert sanitize_url('  https://example.com/  ') == 'https://example.com'
    assert sanitize_url('https://example.com/path/') == 'https://example.com/path'

def test_enhanced_error_handling(analyzer):
    """Test enhanced error handling with detailed context."""
    
    # Test SSL error handling
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.SSLError("SSL verification failed")
        
        result = analyzer.analyze_url('https://badssl.example')
        
        assert 'error' in result
        assert 'SSL' in result['error'] or 'ssl' in result['error'].lower()
        assert 'timestamp' in result

    # Test connection error handling
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        result = analyzer.analyze_url('https://nonexistent.example')
        
        assert 'error' in result
        assert 'connect' in result['error'].lower() or 'connection' in result['error'].lower()

    # Test timeout error handling
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = analyzer.analyze_url('https://slow.example')
        
        assert 'error' in result
        assert 'timeout' in result['error'].lower() or 'timed out' in result['error'].lower()

def test_content_cleaning_for_analysis(content_analyzer):
    """Test that content is properly cleaned before analysis."""
    
    dirty_content = """
    Check out https://example.com and email us at test@example.com
    Our CSS: .class { color: red; font-size: 12px; }
    JavaScript: function test() { var x = 5; return x; }
    <div>HTML tags should be removed</div>
    This is clean content that should remain.
    """
    
    cleaned = content_analyzer._clean_text_for_analysis(dirty_content)
    
    # Should remove URLs, emails, CSS, JavaScript, HTML
    assert 'https://example.com' not in cleaned
    assert 'test@example.com' not in cleaned
    assert 'color: red' not in cleaned
    assert 'function test()' not in cleaned
    assert '<div>' not in cleaned
    
    # Should keep clean content
    assert 'clean content that should remain' in cleaned

# ============================================================================
# EXISTING TESTS (Enhanced)
# ============================================================================

def test_init(analyzer):
    """Test tfq0seo analyzer initialization.
    
    Verifies:
    - Default settings
    - Analyzer components initialization
    - Logger setup
    - Directory creation
    """
    assert analyzer.settings is not None
    assert analyzer.settings['version'] == '2.0.0'
    assert analyzer.meta_analyzer is not None
    assert analyzer.content_analyzer is not None
    assert analyzer.modern_analyzer is not None
    
    # Check directory creation
    assert TFQSEO_HOME.exists()
    assert (TFQSEO_HOME / 'cache').exists()
    assert (TFQSEO_HOME / 'tfq0seo.log').parent.exists()

def test_analyze_url_with_real_time_analysis(analyzer):
    """Test URL analysis with real-time analysis engine."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.text = SAMPLE_HTML
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.url = 'https://example.com'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock the analyzers
        with patch.object(analyzer, 'analyzers') as mock_analyzers:
            mock_analyzers.__getitem__ = Mock(return_value=Mock(analyze=Mock(return_value={})))
            
            analysis = analyzer.analyze_url('https://example.com')
            
            assert analysis is not None
            assert 'analysis_modules' in analysis
            assert 'seo_score' in analysis
            assert 'insights' in analysis
            assert 'timestamp' in analysis

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

def test_invalid_url_handling(analyzer):
    """Test invalid URL handling with enhanced error reporting."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Invalid URL")
        
        result = analyzer.analyze_url('invalid-url')
        
        # Should return error dict instead of raising exception
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'url' in result
        assert 'timestamp' in result

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

def test_seo_score_calculation_range(analyzer):
    """Test SEO score calculation stays within valid range."""
    # Test with empty report
    empty_report = {'analysis_modules': {}}
    score = analyzer._calculate_seo_score(empty_report)
    assert 0 <= score <= 100
    
    # Test with minimal data
    minimal_report = {
        'analysis_modules': {
            'basic_seo': {'title': 'Test'},
            'content': {'basic_metrics': {'word_count': 100}},
            'modern_seo': {'security': {'https': False}}
        }
    }
    score = analyzer._calculate_seo_score(minimal_report)
    assert 0 <= score <= 100

def test_crawl_config():
    """Test CrawlConfig dataclass initialization and defaults."""
    config = CrawlConfig()
    assert config.max_depth == 3
    assert config.max_pages == 500
    assert config.concurrent_requests == 10
    assert config.respect_robots_txt == True
    
    # Test custom configuration
    custom_config = CrawlConfig(
        max_depth=5,
        max_pages=1000,
        concurrent_requests=20
    )
    assert custom_config.max_depth == 5
    assert custom_config.max_pages == 1000
    assert custom_config.concurrent_requests == 20

def test_crawl_result():
    """Test CrawlResult dataclass initialization."""
    result = CrawlResult(
        url="https://example.com",
        status_code=200,
        title="Test Page",
        meta_description="Test description"
    )
    assert result.url == "https://example.com"
    assert result.status_code == 200
    assert result.title == "Test Page"
    assert result.meta_description == "Test description"
    assert result.internal_links == []
    assert result.external_links == []

def test_url_structure_analysis(analyzer):
    """Test URL structure analysis functionality."""
    url = "https://example.com/very/deep/path/structure/page.html?param=value"
    
    analysis = analyzer._analyze_url_structure(url)
    
    assert analysis['url'] == url
    assert analysis['protocol'] == 'https'
    assert analysis['domain'] == 'example.com'
    assert analysis['has_query_parameters'] == True
    assert len(analysis['path_segments']) > 0
    assert 'seo_issues' in analysis
    assert 'recommendations' in analysis

def test_duplicate_content_detection(analyzer):
    """Test duplicate content detection across pages."""
    pages = {
        'https://example.com/page1': {
            'status_code': 200,
            'title': 'Same Title',
            'meta_description': 'Same Description',
            'h1_tags': ['Same H1']
        },
        'https://example.com/page2': {
            'status_code': 200,
            'title': 'Same Title',
            'meta_description': 'Same Description',
            'h1_tags': ['Same H1']
        },
        'https://example.com/page3': {
            'status_code': 200,
            'title': 'Different Title',
            'meta_description': 'Different Description',
            'h1_tags': ['Different H1']
        }
    }
    
    duplicates = analyzer._find_duplicate_content(pages)
    
    assert len(duplicates) == 1  # One group of duplicates
    assert len(duplicates[0]) == 2  # Two pages in the duplicate group

def test_broken_links_detection(analyzer):
    """Test broken links detection."""
    pages = {
        'https://example.com/page1': {
            'status_code': 200,
            'parent_url': None
        },
        'https://example.com/broken': {
            'status_code': 404,
            'parent_url': 'https://example.com/page1'
        },
        'https://example.com/server-error': {
            'status_code': 500,
            'parent_url': 'https://example.com/page1'
        }
    }
    
    broken_links = analyzer._find_broken_links(pages)
    
    assert len(broken_links) == 2
    assert any(link['status_code'] == 404 for link in broken_links)
    assert any(link['status_code'] == 500 for link in broken_links)

def test_export_crawl_results_csv(analyzer):
    """Test CSV export functionality."""
    # Add some mock crawl results
    analyzer.crawl_results = {
        'https://example.com': CrawlResult(
            url='https://example.com',
            status_code=200,
            title='Example Title',
            meta_description='Example description',
            word_count=500,
            response_time=1.5
        )
    }
    
    csv_output = analyzer.export_crawl_results('csv')
    assert 'URL,Status Code,Title' in csv_output
    assert 'https://example.com,200,Example Title' in csv_output

def test_crawl_insights(analyzer):
    """Test crawl insights generation."""
    # Add some mock crawl results
    analyzer.crawl_results = {
        'https://example.com': CrawlResult(
            url='https://example.com',
            status_code=200
        )
    }
    
    insights = analyzer.get_crawl_insights()
    
    assert 'overview' in insights
    assert 'critical_issues' in insights
    assert 'crawl_summary' in insights
    
    # Test empty results
    analyzer.crawl_results = {}
    empty_insights = analyzer.get_crawl_insights()
    assert empty_insights == {}

def test_should_crawl_url(analyzer):
    """Test URL crawling eligibility checks."""
    config = CrawlConfig(
        allowed_domains=['example.com'],
        excluded_paths=['/admin/', '/private/']
    )
    
    # Should crawl
    assert analyzer._should_crawl_url('https://example.com/page', config) == True
    
    # Should not crawl - different domain
    assert analyzer._should_crawl_url('https://other.com/page', config) == False
    
    # Should not crawl - excluded path
    assert analyzer._should_crawl_url('https://example.com/admin/page', config) == False
    
    # Should not crawl - file extension
    assert analyzer._should_crawl_url('https://example.com/file.pdf', config) == False

def test_site_structure_analysis(analyzer):
    """Test site structure analysis."""
    pages = {
        'https://example.com/': {'crawl_depth': 0},
        'https://example.com/page1': {'crawl_depth': 1},
        'https://example.com/page2': {'crawl_depth': 1},
        'https://example.com/deep/page': {'crawl_depth': 2}
    }
    
    structure = analyzer._analyze_site_structure(pages)
    
    assert structure['max_depth'] == 2
    assert structure['total_pages'] == 4
    assert structure['pages_by_depth'][0] == 1
    assert structure['pages_by_depth'][1] == 2
    assert structure['pages_by_depth'][2] == 1

def test_get_error_type(analyzer):
    """Test HTTP error type mapping."""
    assert analyzer._get_error_type(404) == "Not Found"
    assert analyzer._get_error_type(500) == "Internal Server Error"
    assert analyzer._get_error_type(999) == "HTTP 999"

@pytest.mark.asyncio
async def test_extract_seo_data(analyzer):
    """Test SEO data extraction from HTML."""
    from bs4 import BeautifulSoup
    
    result = CrawlResult(url="https://example.com", status_code=200)
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    
    await analyzer._extract_seo_data(result, soup, "https://example.com")
    
    assert result.title == "Test Page Title"
    assert result.meta_description == "This is a test page description"
    assert len(result.h1_tags) > 0
    assert len(result.images) > 0
    # Test that word count is now meaningful (not inflated by JS/CSS)
    assert result.word_count > 0

if __name__ == '__main__':
    pytest.main([__file__]) 