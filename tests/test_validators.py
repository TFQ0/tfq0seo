import pytest
from pathlib import Path
from src.utils.validators import InputValidator
from src.utils.error_handler import TFQ0SEOError, URLFetchError, ConfigurationError

def test_url_validation():
    """Test URL validation functionality."""
    # Test valid URL
    valid_url = "https://www.example.com"
    assert InputValidator.validate_url(valid_url) == valid_url
    
    # Test empty URL
    with pytest.raises(URLFetchError) as exc_info:
        InputValidator.validate_url("")
    assert exc_info.value.error.error_code == 'EMPTY_URL'
    
    # Test invalid URL
    with pytest.raises(URLFetchError) as exc_info:
        InputValidator.validate_url("not-a-url")
    assert exc_info.value.error.error_code == 'INVALID_URL'

def test_config_validation():
    """Test configuration validation functionality."""
    # Test valid config
    valid_config = {
        'seo_thresholds': {
            'title_length': {'min': 10, 'max': 60},
            'meta_description_length': {'min': 50, 'max': 160}
        },
        'cache': {'enabled': True, 'expiration': 3600},
        'logging': {'level': 'INFO', 'file': 'seo.log'}
    }
    assert InputValidator.validate_config(valid_config) == valid_config
    
    # Test missing required field
    invalid_config = {
        'seo_thresholds': {},
        'cache': {}
        # missing logging
    }
    with pytest.raises(ConfigurationError) as exc_info:
        InputValidator.validate_config(invalid_config)
    assert exc_info.value.error.error_code == 'MISSING_CONFIG'
    
    # Test invalid field type
    invalid_config = {
        'seo_thresholds': [],  # should be dict
        'cache': {},
        'logging': {}
    }
    with pytest.raises(ConfigurationError) as exc_info:
        InputValidator.validate_config(invalid_config)
    assert exc_info.value.error.error_code == 'INVALID_CONFIG_TYPE'
    
    # Test missing threshold
    invalid_config = {
        'seo_thresholds': {
            'title_length': {'min': 10, 'max': 60}
            # missing meta_description_length
        },
        'cache': {},
        'logging': {}
    }
    with pytest.raises(ConfigurationError) as exc_info:
        InputValidator.validate_config(invalid_config)
    assert exc_info.value.error.error_code == 'MISSING_THRESHOLD'

def test_file_path_validation():
    """Test file path validation functionality."""
    # Test valid path
    valid_path = "config/seo_config.yaml"
    assert isinstance(InputValidator.validate_file_path(valid_path), Path)
    
    # Test with Path object
    path_obj = Path("config/seo_config.yaml")
    assert InputValidator.validate_file_path(path_obj) == path_obj

def test_parameter_validation():
    """Test parameter validation functionality."""
    # Test valid parameter
    assert InputValidator.validate_parameter("test", 5, int, 0, 10) == 5
    
    # Test invalid type
    with pytest.raises(ValueError) as exc_info:
        InputValidator.validate_parameter("test", "5", int)
    assert "Invalid type" in str(exc_info.value)
    
    # Test value below minimum
    with pytest.raises(ValueError) as exc_info:
        InputValidator.validate_parameter("test", 5, int, min_value=10)
    assert "must be greater than or equal to" in str(exc_info.value)
    
    # Test value above maximum
    with pytest.raises(ValueError) as exc_info:
        InputValidator.validate_parameter("test", 15, int, max_value=10)
    assert "must be less than or equal to" in str(exc_info.value) 