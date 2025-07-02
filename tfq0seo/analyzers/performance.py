"""
Performance analyzer for page speed and Core Web Vitals
"""
from typing import Dict, List, Optional, Any
import re

class PerformanceAnalyzer:
    """Analyzer for page performance metrics"""
    
    def __init__(self, config):
        self.config = config
    
    def analyze(self, page_data: Dict) -> Dict[str, Any]:
        """Analyze page performance metrics"""
        issues = []
        
        # Load time analysis
        load_time = page_data.get('load_time', 0)
        
        if load_time > self.config.max_page_load_time:
            issues.append({
                'type': 'slow_load_time',
                'severity': 'critical',
                'message': f'Page load time too slow ({load_time:.2f}s, recommended: <{self.config.max_page_load_time}s)'
            })
        elif load_time > 2:
            issues.append({
                'type': 'moderate_load_time',
                'severity': 'warning',
                'message': f'Page load time could be improved ({load_time:.2f}s)'
            })
        
        # Content size analysis
        content = page_data.get('content', '')
        content_size = len(content.encode('utf-8'))
        content_size_kb = content_size / 1024
        
        if content_size_kb > 500:
            issues.append({
                'type': 'large_page_size',
                'severity': 'warning',
                'message': f'Large page size ({content_size_kb:.0f}KB, consider optimization)'
            })
        
        # Resource analysis (basic)
        resource_analysis = self._analyze_resources(content)
        issues.extend(resource_analysis['issues'])
        
        # Performance score calculation
        performance_score = self._calculate_performance_score(load_time, content_size_kb)
        
        # Performance category
        if load_time < 1.5:
            category = 'fast'
        elif load_time < 3:
            category = 'moderate'
        else:
            category = 'slow'
        
        return {
            'load_time': round(load_time, 3),
            'content_size_kb': round(content_size_kb, 2),
            'performance_score': performance_score,
            'category': category,
            'resources': resource_analysis['summary'],
            'estimated_metrics': {
                'fcp': round(load_time * 0.3, 2),  # Rough estimate
                'lcp': round(load_time * 0.8, 2),  # Rough estimate
                'tti': round(load_time * 1.2, 2)   # Rough estimate
            },
            'issues': issues
        }
    
    def _analyze_resources(self, content: str) -> Dict[str, Any]:
        """Analyze page resources"""
        issues = []
        
        # Count resources
        script_tags = len(re.findall(r'<script', content))
        style_tags = len(re.findall(r'<style', content))
        link_css = len(re.findall(r'<link[^>]+rel=["\']stylesheet["\']', content))
        img_tags = len(re.findall(r'<img', content))
        
        # Check for excessive resources
        total_css = style_tags + link_css
        if script_tags > 20:
            issues.append({
                'type': 'too_many_scripts',
                'severity': 'warning',
                'message': f'Too many script tags ({script_tags}), consider bundling'
            })
        
        if total_css > 10:
            issues.append({
                'type': 'too_many_stylesheets',
                'severity': 'warning',
                'message': f'Too many stylesheets ({total_css}), consider bundling'
            })
        
        # Check for render-blocking resources
        render_blocking_scripts = len(re.findall(r'<script(?![^>]*\s(async|defer))', content))
        if render_blocking_scripts > 0:
            issues.append({
                'type': 'render_blocking_scripts',
                'severity': 'warning',
                'message': f'{render_blocking_scripts} render-blocking scripts found'
            })
        
        # Check for lazy loading
        lazy_images = len(re.findall(r'<img[^>]+loading=["\']lazy["\']', content))
        non_lazy_images = img_tags - lazy_images
        
        if img_tags > 5 and lazy_images < img_tags * 0.5:
            issues.append({
                'type': 'missing_lazy_loading',
                'severity': 'notice',
                'message': f'Only {lazy_images}/{img_tags} images use lazy loading'
            })
        
        return {
            'summary': {
                'scripts': script_tags,
                'stylesheets': total_css,
                'images': img_tags,
                'render_blocking_scripts': render_blocking_scripts,
                'lazy_loaded_images': lazy_images
            },
            'issues': issues
        }
    
    def _calculate_performance_score(self, load_time: float, content_size_kb: float) -> int:
        """Calculate performance score (0-100)"""
        score = 100
        
        # Deduct for load time
        if load_time > 5:
            score -= 40
        elif load_time > 3:
            score -= 25
        elif load_time > 2:
            score -= 15
        elif load_time > 1:
            score -= 5
        
        # Deduct for content size
        if content_size_kb > 1000:
            score -= 20
        elif content_size_kb > 500:
            score -= 10
        elif content_size_kb > 200:
            score -= 5
        
        return max(0, score) 