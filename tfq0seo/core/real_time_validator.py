"""
Real-Time Validator for tfq0seo

This module provides real-time validation during crawling to catch issues early
and provide immediate feedback on data quality.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import html


logger = logging.getLogger(__name__)


class RealTimeValidator:
    """Validate page data in real-time during crawl"""
    
    def __init__(self):
        self.validation_rules = {
            'html_validity': {
                'critical': False,
                'check_func': self._check_html_validity
            },
            'encoding_issues': {
                'critical': False,
                'check_func': self._detect_encoding_problems
            },
            'truncated_content': {
                'critical': True,
                'check_func': self._check_content_completeness
            },
            'resource_availability': {
                'critical': False,
                'check_func': self._verify_resources
            },
            'javascript_dependency': {
                'critical': False,
                'check_func': self._check_javascript_dependency
            },
            'mobile_readiness': {
                'critical': False,
                'check_func': self._validate_mobile_readiness
            },
            'seo_basics': {
                'critical': False,
                'check_func': self._validate_seo_basics
            }
        }
        
        # Common HTML errors that indicate problems
        self.html_error_patterns = [
            (r'<([^/>]+)>(?!.*?</\1>)', 'Unclosed tags detected'),
            (r'</([^>]+)>(?!.*?<\1[^>]*>)', 'Closing tag without opening tag'),
            (r'<[^>]*<[^>]*>', 'Nested opening brackets'),
            (r'&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)', 'Invalid HTML entities'),
            (r'<(?!/?[a-zA-Z])[^>]*>', 'Invalid tag syntax')
        ]
        
        # Encoding detection patterns
        self.encoding_indicators = {
            'utf-8': b'\xef\xbb\xbf',  # UTF-8 BOM
            'utf-16': b'\xff\xfe',      # UTF-16 LE BOM
            'utf-16-be': b'\xfe\xff',   # UTF-16 BE BOM
        }
    
    def validate_page_data(self, page_data: Dict) -> Dict:
        """Validate page data in real-time during crawl"""
        
        validations = {}
        warnings = []
        critical_issues = []
        
        # Run all validation checks
        for check_name, config in self.validation_rules.items():
            try:
                result = config['check_func'](page_data)
                validations[check_name] = result
                
                if not result['passed']:
                    if config['critical']:
                        critical_issues.append({
                            'type': check_name,
                            'message': result['message'],
                            'impact': result['impact_on_analysis'],
                            'suggestion': result['remediation']
                        })
                    else:
                        warnings.append({
                            'type': check_name,
                            'message': result['message'],
                            'impact': result['impact_on_analysis'],
                            'suggestion': result['remediation']
                        })
            except Exception as e:
                logger.debug(f"Validation check {check_name} failed: {e}")
        
        # Calculate overall data quality score
        quality_score = self._calculate_quality_score(validations)
        
        # Determine if we should proceed with analysis
        proceed = len(critical_issues) == 0 and quality_score > 0.3
        
        return {
            'data_quality_score': quality_score,
            'warnings': warnings,
            'critical_issues': critical_issues,
            'proceed_with_analysis': proceed,
            'validation_details': validations,
            'recommendations': self._generate_recommendations(validations, warnings, critical_issues)
        }
    
    def _check_html_validity(self, page_data: Dict) -> Dict:
        """Check HTML validity"""
        
        content = page_data.get('content', '')
        if not content:
            return {
                'passed': False,
                'message': 'No HTML content to validate',
                'impact_on_analysis': 'Cannot perform any content analysis',
                'remediation': 'Ensure page content is properly fetched'
            }
        
        # Check for common HTML errors
        errors_found = []
        for pattern, error_type in self.html_error_patterns:
            matches = re.findall(pattern, content[:10000])  # Check first 10KB
            if matches:
                errors_found.append(f"{error_type}: {len(matches)} instances")
        
        # Check for proper DOCTYPE
        has_doctype = content.strip().lower().startswith('<!doctype') or content.strip().lower().startswith('<html')
        if not has_doctype:
            errors_found.append("Missing DOCTYPE declaration")
        
        # Check for basic structure
        has_html_tag = '<html' in content.lower() and '</html>' in content.lower()
        has_head_tag = '<head' in content.lower() and '</head>' in content.lower()
        has_body_tag = '<body' in content.lower() and '</body>' in content.lower()
        
        if not all([has_html_tag, has_head_tag, has_body_tag]):
            errors_found.append("Missing basic HTML structure (html/head/body tags)")
        
        if errors_found:
            return {
                'passed': False,
                'message': f'HTML validation issues: {"; ".join(errors_found[:3])}',
                'impact_on_analysis': 'Parsing errors may cause incomplete analysis',
                'remediation': 'Fix HTML syntax errors for accurate analysis',
                'errors': errors_found
            }
        
        return {
            'passed': True,
            'message': 'HTML structure appears valid',
            'impact_on_analysis': 'None',
            'remediation': 'No action needed'
        }
    
    def _detect_encoding_problems(self, page_data: Dict) -> Dict:
        """Detect encoding issues"""
        
        content = page_data.get('content', '')
        if not content:
            return {
                'passed': True,
                'message': 'No content to check',
                'impact_on_analysis': 'None',
                'remediation': 'No action needed'
            }
        
        # Check for common encoding issues
        encoding_issues = []
        
        # Check for mojibake (garbled text)
        mojibake_patterns = [
            'Ã¢â‚¬â„¢',  # Common UTF-8 interpreted as Latin-1
            'â€™', 'â€œ', 'â€',  # Smart quotes issues
            'Ã©', 'Ã¨', 'Ã ',  # Accented characters issues
            '�',  # Replacement character
        ]
        
        for pattern in mojibake_patterns:
            if pattern in content:
                encoding_issues.append(f"Possible encoding issue: '{pattern}' found")
        
        # Check for BOM in content (shouldn't be visible)
        if content.startswith('\ufeff'):
            encoding_issues.append("UTF-8 BOM detected in content")
        
        # Check declared encoding vs detected
        declared_encoding = self._get_declared_encoding(page_data)
        if declared_encoding and declared_encoding.lower() not in ['utf-8', 'utf8']:
            encoding_issues.append(f"Non-UTF-8 encoding declared: {declared_encoding}")
        
        if encoding_issues:
            return {
                'passed': False,
                'message': f'Encoding issues detected: {"; ".join(encoding_issues[:2])}',
                'impact_on_analysis': 'Text content may be garbled or misinterpreted',
                'remediation': 'Ensure all pages use UTF-8 encoding',
                'issues': encoding_issues
            }
        
        return {
            'passed': True,
            'message': 'No encoding issues detected',
            'impact_on_analysis': 'None',
            'remediation': 'No action needed'
        }
    
    def _check_content_completeness(self, page_data: Dict) -> Dict:
        """Check if content appears to be truncated"""
        
        content = page_data.get('content', '')
        if not content:
            return {
                'passed': False,
                'message': 'No content received',
                'impact_on_analysis': 'Cannot analyze empty content',
                'remediation': 'Check server response and network issues'
            }
        
        # Check for signs of truncation
        truncation_signs = []
        
        # Check if HTML tags are properly closed
        open_tags = len(re.findall(r'<[^/][^>]*>', content))
        close_tags = len(re.findall(r'</[^>]+>', content))
        
        if open_tags > close_tags * 1.5:  # Significant imbalance
            truncation_signs.append("Many unclosed HTML tags")
        
        # Check if content ends abruptly
        content_end = content.strip()[-100:] if len(content) > 100 else content
        if not any(content_end.endswith(tag) for tag in ['</html>', '</body>', '</div>', '</p>']):
            if '<' in content_end and '>' not in content_end[content_end.rfind('<'):]:
                truncation_signs.append("Content ends mid-tag")
        
        # Check content size vs declared size
        declared_length = page_data.get('headers', {}).get('Content-Length')
        if declared_length:
            try:
                declared_bytes = int(declared_length)
                actual_bytes = len(content.encode('utf-8'))
                if actual_bytes < declared_bytes * 0.9:  # More than 10% missing
                    truncation_signs.append(f"Content shorter than declared ({actual_bytes} vs {declared_bytes} bytes)")
            except:
                pass
        
        if truncation_signs:
            return {
                'passed': False,
                'critical': True,
                'message': f'Content appears truncated: {"; ".join(truncation_signs)}',
                'impact_on_analysis': 'Analysis will be incomplete',
                'remediation': 'Increase timeout or check for server issues',
                'signs': truncation_signs
            }
        
        return {
            'passed': True,
            'message': 'Content appears complete',
            'impact_on_analysis': 'None',
            'remediation': 'No action needed'
        }
    
    def _verify_resources(self, page_data: Dict) -> Dict:
        """Verify that key resources are available"""
        
        content = page_data.get('content', '')
        if not content:
            return {
                'passed': True,
                'message': 'No content to verify',
                'impact_on_analysis': 'None',
                'remediation': 'No action needed'
            }
        
        # Parse content to check resources
        try:
            soup = BeautifulSoup(content, 'html.parser')
        except:
            return {
                'passed': False,
                'message': 'Cannot parse HTML to verify resources',
                'impact_on_analysis': 'Resource verification skipped',
                'remediation': 'Fix HTML parsing errors'
            }
        
        issues = []
        
        # Check for resources with error indicators
        error_patterns = [
            '404', 'not found', 'error', 'missing',
            'undefined', 'null', 'failed to load'
        ]
        
        # Check inline scripts for errors
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                script_lower = script.string.lower()
                for pattern in error_patterns:
                    if pattern in script_lower and 'console' in script_lower:
                        issues.append("Possible JavaScript errors detected")
                        break
        
        # Check for common CDN failures
        cdn_patterns = [
            'cdnjs.cloudflare.com',
            'ajax.googleapis.com',
            'maxcdn.bootstrapcdn.com'
        ]
        
        external_resources = soup.find_all(['script', 'link'], src=True) + soup.find_all(['script', 'link'], href=True)
        failed_cdn_count = 0
        
        for resource in external_resources:
            url = resource.get('src') or resource.get('href', '')
            if any(cdn in url for cdn in cdn_patterns):
                # This is a simple check - in real implementation you'd verify accessibility
                failed_cdn_count += 1 if '404' in url or 'error' in url else 0
        
        if failed_cdn_count > 0:
            issues.append(f"{failed_cdn_count} CDN resources might be unavailable")
        
        if issues:
            return {
                'passed': False,
                'message': f'Resource issues detected: {"; ".join(issues)}',
                'impact_on_analysis': 'Some features may not work correctly',
                'remediation': 'Verify all external resources are accessible',
                'issues': issues
            }
        
        return {
            'passed': True,
            'message': 'Resources appear to be available',
            'impact_on_analysis': 'None',
            'remediation': 'No action needed'
        }
    
    def _check_javascript_dependency(self, page_data: Dict) -> Dict:
        """Check if page heavily depends on JavaScript"""
        
        content = page_data.get('content', '')
        if not content:
            return {
                'passed': True,
                'message': 'No content to check',
                'impact_on_analysis': 'None',
                'remediation': 'No action needed'
            }
        
        # Quick heuristics for JS dependency
        indicators = []
        
        # Check for common SPA indicators
        spa_patterns = [
            '<div id="root"></div>',
            '<div id="app"></div>',
            '<div id="__next"></div>',
            'ng-app',
            'data-reactroot',
            'v-cloak'
        ]
        
        content_lower = content.lower()
        for pattern in spa_patterns:
            if pattern.lower() in content_lower:
                indicators.append(f"SPA pattern detected: {pattern}")
        
        # Check for minimal text content
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # Remove script and style tags
            for tag in soup(['script', 'style']):
                tag.decompose()
            
            text_content = soup.get_text(strip=True)
            if len(text_content) < 100 and len(content) > 1000:
                indicators.append("Very little text content without JavaScript")
            
            # Check for loading indicators
            loading_patterns = ['loading...', 'please wait', 'javascript required', 'enable javascript']
            for pattern in loading_patterns:
                if pattern in text_content.lower():
                    indicators.append(f"Loading indicator found: '{pattern}'")
        except:
            pass
        
        if indicators:
            return {
                'passed': False,
                'message': f'Heavy JavaScript dependency detected: {indicators[0]}',
                'impact_on_analysis': 'SEO analysis may be limited without JS execution',
                'remediation': 'Ensure critical content is available without JavaScript',
                'indicators': indicators
            }
        
        return {
            'passed': True,
            'message': 'Page content accessible without JavaScript',
            'impact_on_analysis': 'None',
            'remediation': 'No action needed'
        }
    
    def _validate_mobile_readiness(self, page_data: Dict) -> Dict:
        """Quick validation of mobile readiness"""
        
        content = page_data.get('content', '')
        if not content:
            return {
                'passed': True,
                'message': 'No content to validate',
                'impact_on_analysis': 'None',
                'remediation': 'No action needed'
            }
        
        issues = []
        
        # Check for viewport meta tag
        if '<meta name="viewport"' not in content.lower():
            issues.append("Missing viewport meta tag")
        
        # Check for deprecated mobile approaches
        deprecated_patterns = [
            ('handheld.css', 'Deprecated handheld stylesheet'),
            ('mobile.css', 'Separate mobile stylesheet (use responsive design)'),
            ('m.', 'Possible separate mobile subdomain')
        ]
        
        for pattern, description in deprecated_patterns:
            if pattern in content.lower():
                issues.append(description)
        
        # Check for fixed widths in inline styles (basic check)
        fixed_width_count = len(re.findall(r'width:\s*\d{3,}px', content))
        if fixed_width_count > 5:
            issues.append(f"Multiple fixed-width elements ({fixed_width_count}) may cause mobile issues")
        
        if issues:
            return {
                'passed': False,
                'message': f'Mobile readiness issues: {"; ".join(issues[:2])}',
                'impact_on_analysis': 'Mobile SEO scores may be affected',
                'remediation': 'Implement responsive design best practices',
                'issues': issues
            }
        
        return {
            'passed': True,
            'message': 'Basic mobile readiness checks passed',
            'impact_on_analysis': 'None',
            'remediation': 'No action needed'
        }
    
    def _validate_seo_basics(self, page_data: Dict) -> Dict:
        """Quick validation of basic SEO elements"""
        
        content = page_data.get('content', '')
        if not content:
            return {
                'passed': True,
                'message': 'No content to validate',
                'impact_on_analysis': 'None',
                'remediation': 'No action needed'
            }
        
        missing_elements = []
        
        # Quick checks for essential SEO elements
        essential_patterns = [
            ('<title>', 'title tag'),
            ('<meta name="description"', 'meta description'),
            ('<h1', 'H1 heading'),
            ('<meta name="robots"', 'robots meta tag (optional)'),
            ('<link rel="canonical"', 'canonical link (optional)')
        ]
        
        content_lower = content.lower()
        for pattern, element_name in essential_patterns:
            if pattern not in content_lower:
                if 'optional' not in element_name:
                    missing_elements.append(element_name)
        
        if missing_elements:
            return {
                'passed': False,
                'message': f'Missing essential SEO elements: {", ".join(missing_elements)}',
                'impact_on_analysis': 'SEO scores will be significantly impacted',
                'remediation': 'Add missing SEO elements before analysis',
                'missing': missing_elements
            }
        
        return {
            'passed': True,
            'message': 'Basic SEO elements present',
            'impact_on_analysis': 'None',
            'remediation': 'No action needed'
        }
    
    def _get_declared_encoding(self, page_data: Dict) -> Optional[str]:
        """Get declared encoding from headers or meta tags"""
        
        # Check HTTP headers first
        content_type = page_data.get('headers', {}).get('Content-Type', '')
        if 'charset=' in content_type:
            return content_type.split('charset=')[-1].strip()
        
        # Check meta tags
        content = page_data.get('content', '')
        if content:
            # Check for charset meta tag
            charset_match = re.search(r'<meta[^>]+charset=["\']*([^"\'>\s]+)', content[:1000], re.I)
            if charset_match:
                return charset_match.group(1)
            
            # Check for http-equiv content-type
            equiv_match = re.search(r'<meta[^>]+content=["\']*[^"\']*charset=([^"\'>\s;]+)', content[:1000], re.I)
            if equiv_match:
                return equiv_match.group(1)
        
        return None
    
    def _calculate_quality_score(self, validations: Dict) -> float:
        """Calculate overall data quality score"""
        
        if not validations:
            return 0.0
        
        # Weight different validation types
        weights = {
            'html_validity': 0.25,
            'encoding_issues': 0.15,
            'truncated_content': 0.25,
            'resource_availability': 0.10,
            'javascript_dependency': 0.10,
            'mobile_readiness': 0.10,
            'seo_basics': 0.05
        }
        
        total_weight = 0
        weighted_score = 0
        
        for check_name, weight in weights.items():
            if check_name in validations:
                passed = validations[check_name].get('passed', False)
                weighted_score += weight if passed else 0
                total_weight += weight
        
        return round(weighted_score / total_weight if total_weight > 0 else 0, 2)
    
    def _generate_recommendations(self, validations: Dict, warnings: List[Dict], critical_issues: List[Dict]) -> List[str]:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        # Critical issues first
        if critical_issues:
            recommendations.append("Fix critical issues before proceeding with full analysis")
            for issue in critical_issues[:2]:
                recommendations.append(f"• {issue['suggestion']}")
        
        # High-priority warnings
        high_priority_warnings = [w for w in warnings if w['type'] in ['html_validity', 'seo_basics', 'truncated_content']]
        for warning in high_priority_warnings[:2]:
            recommendations.append(f"• {warning['suggestion']}")
        
        # General quality improvement
        quality_score = self._calculate_quality_score(validations)
        if quality_score < 0.7:
            recommendations.append("Consider re-crawling with adjusted settings for better data quality")
        
        return recommendations[:5]  # Top 5 recommendations 