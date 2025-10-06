"""
System Validator for tfq0seo

This module validates that all the comprehensive solutions are working correctly
and provides a unified interface for checking system health.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import sys
import json

logger = logging.getLogger(__name__)

class SystemValidator:
    """Comprehensive system validation"""
    
    def __init__(self):
        self.validation_results = {}
        self.test_results = []
        
    def validate_all_systems(self) -> Dict[str, Any]:
        """Validate all systems and return comprehensive report"""
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'systems': {},
            'overall_status': 'unknown',
            'critical_issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # 1. Validate Version Management
        results['systems']['version_management'] = self._validate_version_management()
        
        # 2. Validate Exception Handling
        results['systems']['exception_handling'] = self._validate_exception_handling()
        
        # 3. Validate Memory Management
        results['systems']['memory_management'] = self._validate_memory_management()
        
        # 4. Validate Dependencies
        results['systems']['dependencies'] = self._validate_dependencies()
        
        # 5. Run Integration Tests
        results['systems']['integration_tests'] = self._run_integration_tests()
        
        # Calculate overall status
        results['overall_status'] = self._calculate_overall_status(results['systems'])
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results['systems'])
        
        return results
    
    def _validate_version_management(self) -> Dict[str, Any]:
        """Validate version management system"""
        result = {
            'status': 'unknown',
            'details': {},
            'issues': []
        }
        
        try:
            from .version_manager import version_manager, get_version, validate_environment
            
            # Check version consistency
            version_check = version_manager.check_version_consistency()
            result['details']['version_consistency'] = version_check
            
            if not version_check['consistent']:
                result['issues'].extend(version_check['inconsistencies'])
            
            # Check environment
            env_validation = validate_environment()
            result['details']['environment'] = env_validation
            
            if env_validation['errors']:
                result['issues'].extend(env_validation['errors'])
            
            # Test safe import functionality
            test_import = version_manager.safe_import('lxml')
            result['details']['safe_import_test'] = {
                'success': test_import.success,
                'fallback_used': test_import.fallback_used,
                'version': test_import.version
            }
            
            result['status'] = 'healthy' if not result['issues'] else 'issues'
            
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"Version management system error: {str(e)}")
        
        return result
    
    def _validate_exception_handling(self) -> Dict[str, Any]:
        """Validate exception handling system"""
        result = {
            'status': 'unknown',
            'details': {},
            'issues': []
        }
        
        try:
            from .exceptions import error_handler, ErrorContext, FallbackStrategy
            
            # Test basic error handling
            context = ErrorContext(operation="test_operation")
            
            # Test with successful operation
            success_result = error_handler.handle_with_fallback(
                lambda: "success",
                context=context,
                fallback_value="fallback"
            )
            
            if not success_result.success or success_result.value != "success":
                result['issues'].append("Error handler failed for successful operation")
            
            # Test with failing operation
            def failing_operation():
                raise ValueError("Test error")
            
            failure_result = error_handler.handle_with_fallback(
                failing_operation,
                context=context,
                fallback_value="fallback",
                strategy=FallbackStrategy.GRACEFUL_DEGRADATION
            )
            
            if failure_result.success or failure_result.fallback_value != "fallback":
                result['issues'].append("Error handler failed for failing operation")
            
            result['details']['test_results'] = {
                'success_test': success_result.success,
                'failure_test': failure_result.fallback_used,
                'fallback_value': failure_result.fallback_value
            }
            
            result['status'] = 'healthy' if not result['issues'] else 'issues'
            
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"Exception handling system error: {str(e)}")
        
        return result
    
    def _validate_memory_management(self) -> Dict[str, Any]:
        """Validate memory management system"""
        result = {
            'status': 'unknown',
            'details': {},
            'issues': []
        }
        
        try:
            from .memory_manager import MemoryManager, ProcessingConfig, MemoryStats
            
            # Test memory stats
            stats = MemoryStats.current()
            result['details']['memory_stats'] = {
                'total_mb': stats.total_mb,
                'used_mb': stats.used_mb,
                'percentage': stats.percentage,
                'pressure_level': stats.pressure_level.value
            }
            
            # Test memory manager
            config = ProcessingConfig(
                max_memory_mb=100,
                batch_size=5,
                cache_size=10
            )
            
            memory_manager = MemoryManager(config)
            
            # Test storing and retrieving data
            test_data = {
                'url': 'https://example.com',
                'content': 'test content',
                'status_code': 200
            }
            
            async def test_memory_operations():
                key = await memory_manager.store_page_data('https://example.com', test_data)
                retrieved = await memory_manager.retrieve_page_data(key)
                await memory_manager.cleanup()
                return retrieved
            
            try:
                loop = asyncio.get_event_loop()
                retrieved_data = loop.run_until_complete(test_memory_operations())
                
                if not retrieved_data or retrieved_data['url'] != test_data['url']:
                    result['issues'].append("Memory manager failed to store/retrieve data correctly")
                
            except RuntimeError:
                # No event loop, create one
                retrieved_data = asyncio.run(test_memory_operations())
                
                if not retrieved_data or retrieved_data['url'] != test_data['url']:
                    result['issues'].append("Memory manager failed to store/retrieve data correctly")
            
            result['details']['memory_test'] = {
                'storage_successful': bool(retrieved_data),
                'data_integrity': retrieved_data.get('url') == test_data['url'] if retrieved_data else False
            }
            
            result['status'] = 'healthy' if not result['issues'] else 'issues'
            
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"Memory management system error: {str(e)}")
        
        return result
    
    def _validate_dependencies(self) -> Dict[str, Any]:
        """Validate dependency management"""
        result = {
            'status': 'unknown',
            'details': {},
            'issues': []
        }
        
        try:
            from .version_manager import version_manager
            
            # Get dependency status
            dep_status = version_manager.get_dependency_status()
            result['details'] = dep_status
            
            # Check for missing required dependencies
            if dep_status['missing']:
                result['issues'].extend([
                    f"Missing required dependency: {dep['name']}"
                    for dep in dep_status['missing']
                ])
            
            # Check for warnings
            if dep_status['warnings']:
                result['issues'].extend(dep_status['warnings'])
            
            result['status'] = 'healthy' if not result['issues'] else 'issues'
            
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"Dependency validation error: {str(e)}")
        
        return result
    
    def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        result = {
            'status': 'unknown',
            'details': {},
            'issues': []
        }
        
        try:
            # Test that all systems work together
            test_results = []
            
            # 1. Test version management with exception handling
            try:
                from .version_manager import safe_import
                from .exceptions import ImportStrategy
                
                import_result = safe_import('non_existent_module', ImportStrategy.SILENT_ON_MISSING)
                test_results.append({
                    'test': 'version_exception_integration',
                    'passed': not import_result.success,
                    'details': 'Safe import should fail for non-existent module'
                })
            except Exception as e:
                test_results.append({
                    'test': 'version_exception_integration',
                    'passed': False,
                    'error': str(e)
                })
            
            # 2. Test memory management with realistic data
            try:
                from .memory_manager import MemoryManager, ProcessingConfig
                
                async def test_realistic_scenario():
                    config = ProcessingConfig(max_memory_mb=50, batch_size=3)
                    manager = MemoryManager(config)
                    
                    # Simulate storing multiple pages
                    test_urls = [
                        'https://example.com/page1',
                        'https://example.com/page2',
                        'https://example.com/page3'
                    ]
                    
                    for url in test_urls:
                        await manager.store_page_data(url, {
                            'url': url,
                            'content': f'Content for {url}',
                            'status_code': 200
                        })
                    
                    # Retrieve all keys
                    keys = await manager.get_page_keys()
                    await manager.cleanup()
                    
                    return len(keys) == len(test_urls)
                
                try:
                    loop = asyncio.get_event_loop()
                    realistic_test_passed = loop.run_until_complete(test_realistic_scenario())
                except RuntimeError:
                    realistic_test_passed = asyncio.run(test_realistic_scenario())
                
                test_results.append({
                    'test': 'memory_realistic_scenario',
                    'passed': realistic_test_passed,
                    'details': 'Memory manager should handle multiple pages correctly'
                })
                
            except Exception as e:
                test_results.append({
                    'test': 'memory_realistic_scenario',
                    'passed': False,
                    'error': str(e)
                })
            
            result['details']['test_results'] = test_results
            failed_tests = [t for t in test_results if not t['passed']]
            
            if failed_tests:
                result['issues'].extend([
                    f"Integration test failed: {t['test']}"
                    for t in failed_tests
                ])
            
            result['status'] = 'healthy' if not failed_tests else 'issues'
            
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"Integration test error: {str(e)}")
        
        return result
    
    def _calculate_overall_status(self, systems: Dict[str, Any]) -> str:
        """Calculate overall system status"""
        statuses = [system['status'] for system in systems.values()]
        
        if any(status == 'error' for status in statuses):
            return 'error'
        elif any(status == 'issues' for status in statuses):
            return 'warning'
        elif all(status == 'healthy' for status in statuses):
            return 'healthy'
        else:
            return 'unknown'
    
    def _generate_recommendations(self, systems: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Version management recommendations
        if systems['version_management']['status'] != 'healthy':
            recommendations.append(
                "Update version references in setup.py and pyproject.toml to maintain consistency"
            )
        
        # Dependency recommendations
        if systems['dependencies']['status'] != 'healthy':
            recommendations.append(
                "Install missing dependencies or use 'pip install tfq0seo[full]' for all features"
            )
        
        # Memory management recommendations
        if systems['memory_management']['status'] != 'healthy':
            recommendations.append(
                "Consider reducing concurrent_requests or max_pages for better memory efficiency"
            )
        
        # Exception handling recommendations
        if systems['exception_handling']['status'] != 'healthy':
            recommendations.append(
                "Review and update any remaining bare except statements in custom code"
            )
        
        return recommendations
    
    def generate_health_report(self) -> str:
        """Generate a human-readable health report"""
        results = self.validate_all_systems()
        
        report = f"""
# tfq0seo System Health Report
Generated: {results['timestamp']}
Python Version: {results['python_version']}
Overall Status: {results['overall_status'].upper()}

## System Status Summary
"""
        
        for system_name, system_data in results['systems'].items():
            status_emoji = {
                'healthy': '✅',
                'warning': '⚠️',
                'issues': '⚠️',
                'error': '❌',
                'unknown': '❓'
            }.get(system_data['status'], '❓')
            
            report += f"- {system_name.replace('_', ' ').title()}: {status_emoji} {system_data['status'].upper()}\n"
        
        # Add critical issues
        if results['critical_issues']:
            report += "\n## Critical Issues\n"
            for issue in results['critical_issues']:
                report += f"- ❌ {issue}\n"
        
        # Add warnings
        all_warnings = []
        for system_data in results['systems'].values():
            all_warnings.extend(system_data.get('issues', []))
        
        if all_warnings:
            report += "\n## Warnings\n"
            for warning in all_warnings:
                report += f"- ⚠️ {warning}\n"
        
        # Add recommendations
        if results['recommendations']:
            report += "\n## Recommendations\n"
            for rec in results['recommendations']:
                report += f"- 💡 {rec}\n"
        
        return report
    
    def save_report(self, output_path: str = "system_health_report.json"):
        """Save validation report to file"""
        results = self.validate_all_systems()
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Also save human-readable version
        human_report_path = output_path.replace('.json', '.md')
        with open(human_report_path, 'w') as f:
            f.write(self.generate_health_report())
        
        return output_path, human_report_path

# Global instance
system_validator = SystemValidator()

# Convenience functions
def validate_system() -> Dict[str, Any]:
    """Validate entire system"""
    return system_validator.validate_all_systems()

def get_health_report() -> str:
    """Get human-readable health report"""
    return system_validator.generate_health_report()

def save_validation_report(output_path: str = "system_health_report.json") -> tuple:
    """Save validation report to files"""
    return system_validator.save_report(output_path) 