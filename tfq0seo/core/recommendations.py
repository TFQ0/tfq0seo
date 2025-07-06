"""
Contextual Recommendations Engine for tfq0seo

This module provides sophisticated, context-aware recommendations
based on website type, industry, and specific issues detected.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import re
from urllib.parse import urlparse


class WebsiteType(Enum):
    """Types of websites for contextual recommendations"""
    ECOMMERCE = "e-commerce"
    BLOG = "blog"
    CORPORATE = "corporate"
    PORTFOLIO = "portfolio"
    NEWS = "news"
    EDUCATIONAL = "educational"
    SAAS = "saas"
    LOCAL_BUSINESS = "local_business"
    UNKNOWN = "unknown"


class RecommendationEngine:
    """Generate contextual recommendations based on website type and issues"""
    
    def __init__(self):
        self.page_type_patterns = {
            'product': ['/product/', '/item/', '/p/', 'product-', '-product'],
            'category': ['/category/', '/c/', '/shop/', '/products/'],
            'blog_post': ['/blog/', '/post/', '/article/', '/news/'],
            'home': ['/', '/index', '/home'],
            'about': ['/about', '/about-us', '/who-we-are'],
            'contact': ['/contact', '/contact-us', '/get-in-touch'],
            'service': ['/service/', '/services/'],
            'checkout': ['/checkout', '/cart', '/basket'],
            'search': ['/search', 'search?', 'q=']
        }
    
    def detect_website_type(self, page_data: Dict) -> WebsiteType:
        """Detect the type of website based on content and structure"""
        
        if not isinstance(page_data, dict):
            return WebsiteType.UNKNOWN
        
        url = page_data.get('url', '')
        content = page_data.get('content', {})
        if not isinstance(content, dict):
            content = {}
        
        technical = page_data.get('technical', {})
        if not isinstance(technical, dict):
            technical = {}
        
        structured_data = technical.get('structured_data', [])
        if not isinstance(structured_data, list):
            structured_data = []
        
        # Check structured data for clues
        for item in structured_data:
            schema_type = item.get('type', '').lower()
            if 'product' in schema_type or 'offer' in schema_type:
                return WebsiteType.ECOMMERCE
            elif 'article' in schema_type or 'blogposting' in schema_type:
                return WebsiteType.BLOG
            elif 'localbusiness' in schema_type:
                return WebsiteType.LOCAL_BUSINESS
            elif 'organization' in schema_type:
                return WebsiteType.CORPORATE
        
        # Check URL patterns
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in ['/shop', '/store', '/products', '/cart']):
            return WebsiteType.ECOMMERCE
        elif any(pattern in url_lower for pattern in ['/blog', '/news', '/article']):
            return WebsiteType.BLOG
        elif any(pattern in url_lower for pattern in ['/portfolio', '/work', '/projects']):
            return WebsiteType.PORTFOLIO
        
        # Check content indicators
        word_count = content.get('word_count', 0)
        if word_count > 800:
            return WebsiteType.BLOG
        
        return WebsiteType.UNKNOWN
    
    def detect_page_type(self, url: str) -> str:
        """Detect the type of page based on URL patterns"""
        url_lower = url.lower()
        
        for page_type, patterns in self.page_type_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                return page_type
        
        return 'general'
    
    def generate_contextual_recommendation(self, issue: Dict, page_context: Dict) -> Dict:
        """Generate highly specific, contextual recommendations"""
        
        # Validate inputs
        if not isinstance(issue, dict):
            return issue if isinstance(issue, dict) else {'type': 'unknown', 'message': 'Invalid issue data'}
        
        if not isinstance(page_context, dict):
            page_context = {}
        
        issue_type = issue.get('type', '')
        website_type = self.detect_website_type(page_context)
        page_type = self.detect_page_type(page_context.get('url', ''))
        
        # Get base recommendation from issue
        recommendation = issue.copy()
        
        # Enhance based on context
        enhanced = self._get_contextual_enhancement(issue_type, website_type, page_type)
        
        if enhanced:
            # Merge enhanced recommendations
            recommendation.update({
                'contextual_recommendation': enhanced.get('recommendation'),
                'specific_steps': enhanced.get('steps', []),
                'examples': enhanced.get('examples', []),
                'tools': enhanced.get('tools', []),
                'estimated_time': enhanced.get('time', 'Unknown'),
                'website_type': website_type.value,
                'page_type': page_type
            })
        
        return recommendation
    
    def _get_contextual_enhancement(self, issue_type: str, website_type: WebsiteType, page_type: str) -> Optional[Dict]:
        """Get context-specific enhancements for recommendations"""
        
        # Comprehensive contextual recommendations
        context_map = {
            'thin_content': {
                WebsiteType.ECOMMERCE: {
                    'product': {
                        'recommendation': 'Expand product descriptions to 300+ words with unique content',
                        'steps': [
                            'Add a detailed "Features & Benefits" section',
                            'Include technical specifications in a table format',
                            'Answer common customer questions in the description',
                            'Add usage instructions or care guidelines',
                            'Include size guides or compatibility information',
                            'Add customer reviews and Q&A sections'
                        ],
                        'examples': [
                            'Features: List 5-7 key features with benefits',
                            'Specs: Material, dimensions, weight, etc.',
                            'Usage: "How to use" or "Best for" sections'
                        ],
                        'tools': ['Product description templates', 'Customer review plugins'],
                        'time': '30-45 minutes per product'
                    },
                    'category': {
                        'recommendation': 'Add category descriptions of 200+ words',
                        'steps': [
                            'Write an intro paragraph about the category',
                            'Add buying guides or selection tips',
                            'Include popular brands or subcategories',
                            'Add FAQ section for the category'
                        ],
                        'time': '20-30 minutes per category'
                    }
                },
                WebsiteType.BLOG: {
                    'blog_post': {
                        'recommendation': 'Expand article to 1,000+ words with comprehensive coverage',
                        'steps': [
                            'Add more examples and case studies',
                            'Include relevant statistics and data',
                            'Break down complex topics into clear steps',
                            'Add expert quotes or interviews',
                            'Include actionable takeaways',
                            'Add related images, charts, or infographics'
                        ],
                        'examples': [
                            'Case study: Real-world application of your topic',
                            'Statistics: Industry data supporting your points',
                            'Expert quote: Interview or cite industry leaders'
                        ],
                        'tools': ['Grammarly', 'Hemingway Editor', 'Canva for graphics'],
                        'time': '2-4 hours per article'
                    }
                },
                WebsiteType.LOCAL_BUSINESS: {
                    'service': {
                        'recommendation': 'Expand service pages to 500+ words',
                        'steps': [
                            'Describe the service process step-by-step',
                            'List what\'s included and what\'s not',
                            'Add pricing information or ranges',
                            'Include service area information',
                            'Add testimonials or case studies',
                            'Answer common questions about the service'
                        ],
                        'time': '1-2 hours per service page'
                    }
                }
            },
            
            'missing_title': {
                WebsiteType.ECOMMERCE: {
                    'product': {
                        'recommendation': 'Create product-focused title tags',
                        'steps': [
                            'Start with the product name',
                            'Add key attributes (color, size, model)',
                            'Include category if relevant',
                            'End with brand name',
                            'Keep under 60 characters'
                        ],
                        'examples': [
                            'Blue Cotton T-Shirt - Men\'s Large | BrandName',
                            'iPhone 13 Pro Case - Leather, Black | YourStore',
                            'Organic Green Tea - 100 Bags | TeaBrand'
                        ],
                        'time': '5 minutes per page'
                    }
                },
                WebsiteType.BLOG: {
                    'blog_post': {
                        'recommendation': 'Create compelling article titles',
                        'steps': [
                            'Include primary keyword naturally',
                            'Make it compelling and clickable',
                            'Use numbers or power words when relevant',
                            'Keep under 60 characters',
                            'Match search intent'
                        ],
                        'examples': [
                            '10 Proven SEO Strategies for 2024 | YourBlog',
                            'How to Fix Common WordPress Errors | TechBlog',
                            'Complete Guide to Content Marketing | MarketingPro'
                        ],
                        'time': '5-10 minutes per article'
                    }
                }
            },
            
            'missing_alt_text': {
                WebsiteType.ECOMMERCE: {
                    'product': {
                        'recommendation': 'Add descriptive alt text to product images',
                        'steps': [
                            'Describe what\'s in the image',
                            'Include product name and key features',
                            'Mention color, size, or variant shown',
                            'Keep under 125 characters',
                            'Don\'t keyword stuff'
                        ],
                        'examples': [
                            'Red leather handbag with gold buckle detail',
                            'Men\'s navy blue running shoes, side view',
                            'Stainless steel water bottle, 32oz, with handle'
                        ],
                        'time': '2-3 minutes per image'
                    }
                }
            },
            
            'slow_page': {
                WebsiteType.ECOMMERCE: {
                    'general': {
                        'recommendation': 'Optimize for e-commerce performance',
                        'steps': [
                            'Compress product images to under 100KB',
                            'Implement lazy loading for product galleries',
                            'Use WebP format for images',
                            'Enable browser caching for static assets',
                            'Consider a CDN for global customers',
                            'Optimize JavaScript loading'
                        ],
                        'tools': [
                            'TinyPNG for image compression',
                            'Cloudflare for CDN',
                            'GTmetrix for performance testing'
                        ],
                        'time': '2-4 hours initial setup'
                    }
                }
            }
        }
        
        # Try to find matching context
        if issue_type in context_map:
            if website_type in context_map[issue_type]:
                if page_type in context_map[issue_type][website_type]:
                    return context_map[issue_type][website_type][page_type]
                elif 'general' in context_map[issue_type][website_type]:
                    return context_map[issue_type][website_type]['general']
        
        return None
    
    def prioritize_recommendations(self, recommendations: List[Dict], resources: Dict) -> List[Dict]:
        """Prioritize recommendations based on available resources"""
        
        # Validate input
        if not isinstance(recommendations, list):
            return []
        
        if not isinstance(resources, dict):
            resources = {}
        
        time_available = resources.get('time_hours_per_week', 10)
        skill_level = resources.get('skill_level', 'intermediate')
        budget = resources.get('budget', 'medium')
        
        # Score each recommendation
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            score = rec.get('priority_score', 5)
            
            # Adjust based on implementation difficulty
            difficulty = rec.get('implementation_difficulty', 'medium')
            if skill_level == 'beginner' and difficulty == 'hard':
                score -= 3
            elif skill_level == 'expert' and difficulty == 'easy':
                score += 1
            
            # Adjust based on impact
            impact = rec.get('estimated_impact', 'medium')
            if impact == 'high':
                score += 2
            elif impact == 'low':
                score -= 1
            
            # Adjust based on time requirements
            estimated_time = rec.get('estimated_time', '1 hour')
            if 'days' in estimated_time and time_available < 20:
                score -= 2
            
            rec['adjusted_priority_score'] = max(1, score)
        
        # Sort by adjusted priority score
        recommendations.sort(key=lambda x: x['adjusted_priority_score'], reverse=True)
        
        # Group into action categories
        quick_wins = []
        major_improvements = []
        long_term = []
        
        for rec in recommendations:
            difficulty = rec.get('implementation_difficulty', 'medium')
            impact = rec.get('estimated_impact', 'medium')
            
            if difficulty == 'easy' and impact in ['high', 'medium']:
                quick_wins.append(rec)
            elif impact == 'high':
                major_improvements.append(rec)
            else:
                long_term.append(rec)
        
        # Return prioritized list - combine in order of priority
        return quick_wins[:5] + major_improvements[:5] + long_term[:10]
    
    def generate_implementation_timeline(self, prioritized_recs: List[Dict]) -> Dict:
        """Generate a suggested implementation timeline"""
        
        # Validate input
        if not isinstance(prioritized_recs, list):
            prioritized_recs = []
        
        # Categorize recommendations by difficulty/impact
        quick_wins = []
        major_improvements = []
        long_term = []
        
        for rec in prioritized_recs:
            if not isinstance(rec, dict):
                continue
                
            difficulty = rec.get('implementation_difficulty', 'medium')
            impact = rec.get('estimated_impact', 'medium')
            
            if difficulty == 'easy' and impact in ['high', 'medium']:
                quick_wins.append(rec)
            elif impact == 'high':
                major_improvements.append(rec)
            else:
                long_term.append(rec)
        
        timeline = {
            'week_1': {
                'focus': 'Quick Wins - Immediate Impact',
                'tasks': quick_wins[:3],
                'estimated_time': '5-10 hours',
                'expected_results': 'Improved user experience, basic SEO fixes'
            },
            'week_2_4': {
                'focus': 'Major Improvements - High Impact',
                'tasks': major_improvements[:3],
                'estimated_time': '15-25 hours',
                'expected_results': 'Significant SEO improvements, better rankings'
            },
            'month_2_3': {
                'focus': 'Ongoing Optimization',
                'tasks': long_term[:5],
                'estimated_time': '10-15 hours/week',
                'expected_results': 'Sustained growth, competitive advantage'
            }
        }
        
        return timeline 