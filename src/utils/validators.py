from typing import Optional, Dict, Any, Union, Type
from urllib.parse import urlparse
import validators
from pathlib import Path
from .error_handler import TFQ0SEOError, URLFetchError, ConfigurationError

class InputValidator:
    """Input validation utilities."""

    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError('URL cannot be empty')
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            raise ValidationError('URL must start with http:// or https://')
        
        return url

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dictionary.
        
        Checks for:
        - Required fields
        - Valid value types
        - Value ranges
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Validated configuration dictionary
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        required_fields = {
            'seo_thresholds': dict,
            'cache': dict,
            'logging': dict
        }
        
        # Check required fields and their types
        for field, expected_type in required_fields.items():
            if field not in config:
                raise ConfigurationError(
                    TFQ0SEOError(
                        error_code='MISSING_CONFIG',
                        message=f'Missing required configuration: {field}'
                    )
                )
            if not isinstance(config[field], expected_type):
                raise ConfigurationError(
                    TFQ0SEOError(
                        error_code='INVALID_CONFIG_TYPE',
                        message=f'Invalid type for {field}: expected {expected_type.__name__}'
                    )
                )
        
        # Validate SEO thresholds
        thresholds = config['seo_thresholds']
        required_thresholds = ['title_length', 'meta_description_length']
        for threshold in required_thresholds:
            if threshold not in thresholds:
                raise ConfigurationError(
                    TFQ0SEOError(
                        error_code='MISSING_THRESHOLD',
                        message=f'Missing required threshold: {threshold}'
                    )
                )
            if not isinstance(thresholds[threshold], dict):
                raise ConfigurationError(
                    TFQ0SEOError(
                        error_code='INVALID_THRESHOLD_TYPE',
                        message=f'Invalid threshold type for {threshold}'
                    )
                )
            if 'min' not in thresholds[threshold] or 'max' not in thresholds[threshold]:
                raise ConfigurationError(
                    TFQ0SEOError(
                        error_code='INVALID_THRESHOLD_RANGE',
                        message=f'Missing min/max values for threshold: {threshold}'
                    )
                )
        
        return config

    @staticmethod
    def validate_file_path(path: Union[str, Path]) -> Path:
        """Validate file path.
        
        Args:
            path: File path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ConfigurationError: If path is invalid
        """
        try:
            path_obj = Path(path)
            return path_obj
        except Exception as e:
            raise ConfigurationError(
                TFQ0SEOError(
                    error_code='INVALID_PATH',
                    message=f'Invalid file path: {str(e)}'
                )
            )

    @staticmethod
    def validate_parameter(name: str, value: Any, expected_type: Type,
                         min_value: Optional[int] = None,
                         max_value: Optional[int] = None) -> Any:
        """Validate parameter value.
        
        Args:
            name: Parameter name
            value: Parameter value
            expected_type: Expected value type
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, expected_type):
            raise ValidationError(
                f'Parameter {name} must be of type {expected_type.__name__}'
            )
        
        if min_value is not None and len(value) < min_value:
            raise ValidationError(
                f'Parameter {name} must be at least {min_value} characters long'
            )
        
        if max_value is not None and len(value) > max_value:
            raise ValidationError(
                f'Parameter {name} must be at most {max_value} characters long'
            )
        
        return value 