"""
Issue Helper Module for Enhanced SEO Issue Reporting

This module provides a centralized way to create enhanced issue objects
with user-friendly messages, actionable recommendations, and examples.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class IssueSeverity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    NOTICE = "notice"


class ImplementationDifficulty(Enum):
    """Implementation difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EstimatedImpact(Enum):
    """Estimated impact levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueHelper:
    """Helper class for creating enhanced issue objects"""
    
    # Issue definitions with enhanced metadata
    ISSUE_DEFINITIONS = {
        # Title tag issues
        "missing_title": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Your page needs a title tag",
            "user_impact": "Without a title, your page won't appear properly in Google search results",
            "recommendation": "Add a 50-60 character title that describes what this page is about",
            "example": '<title>Your Product Name - Key Benefit | Your Brand</title>',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 10,
            "estimated_impact": EstimatedImpact.HIGH,
            "implementation_steps": [
                "Open your HTML file or CMS page editor",
                "Add a <title> tag in the <head> section",
                "Write a descriptive title between 50-60 characters",
                "Include your main keyword naturally",
                "End with your brand name"
            ]
        },
        
        "empty_title": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Your title tag is empty",
            "user_impact": "Search engines can't understand what your page is about",
            "recommendation": "Add meaningful text to your title tag",
            "example": '<title>Professional SEO Analysis Tool - tfq0seo</title>',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 10,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        "short_title": {
            "severity": IssueSeverity.WARNING,
            "message": "Your title is too short",
            "user_impact": "You're missing an opportunity to include relevant keywords",
            "recommendation": "Expand your title to 50-60 characters with more descriptive text",
            "example": 'Instead of "Products", use "Eco-Friendly Home Products - Shop Sustainable | Brand"',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "long_title": {
            "severity": IssueSeverity.WARNING,
            "message": "Your title is too long",
            "user_impact": "Google will cut off your title in search results, making it less clickable",
            "recommendation": "Shorten your title to under 60 characters while keeping important keywords",
            "example": 'Reduce "Complete Guide to Professional SEO Analysis Tools and Techniques for Beginners and Experts" to "SEO Analysis Tools Guide - From Beginner to Expert"',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Meta description issues
        "missing_description": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Your page needs a meta description",
            "user_impact": "Google will create its own snippet, which might not attract clicks",
            "recommendation": "Add a compelling 150-160 character description that summarizes your page",
            "example": '<meta name="description" content="Discover our professional SEO analysis tool. Get detailed reports, actionable recommendations, and improve your search rankings. Try free today!">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 9,
            "estimated_impact": EstimatedImpact.HIGH,
            "implementation_steps": [
                "Add a meta description tag in your HTML head section",
                "Write a compelling summary of your page content",
                "Include a call-to-action",
                "Keep it between 150-160 characters",
                "Make each page's description unique"
            ]
        },
        
        "empty_description": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Your meta description is empty",
            "user_impact": "You're missing the chance to control how your page appears in search results",
            "recommendation": "Write a compelling description that encourages clicks",
            "example": '<meta name="description" content="Learn how to optimize your website for search engines. Free guide covers keywords, content, technical SEO, and more.">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 9,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        # Content issues
        "thin_content": {
            "severity": IssueSeverity.WARNING,
            "message": "Your page has very little content",
            "user_impact": "Pages with minimal content rarely rank well in search results",
            "recommendation": "Add more valuable content to reach at least 300 words",
            "example": "Expand product descriptions, add FAQs, include usage instructions, or share expert tips",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.HIGH,
            "implementation_steps": [
                "Identify key questions your audience has",
                "Add detailed product/service information",
                "Include relevant examples or case studies",
                "Add an FAQ section",
                "Consider user-generated content like reviews"
            ]
        },
        
        "poor_readability": {
            "severity": IssueSeverity.WARNING,
            "message": "Your content is difficult to read",
            "user_impact": "Visitors may leave your page quickly, hurting your rankings",
            "recommendation": "Simplify your writing with shorter sentences and common words",
            "example": "Break long paragraphs into smaller ones, use bullet points, and write at an 8th-grade reading level",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM,
            "tips": [
                "Use shorter sentences (15-20 words)",
                "Choose simple words over complex ones",
                "Break content into scannable sections",
                "Use bullet points and numbered lists",
                "Add subheadings every 2-3 paragraphs"
            ]
        },
        
        # Image issues
        "missing_alt_text": {
            "severity": IssueSeverity.WARNING,
            "message": "Images are missing alt text",
            "user_impact": "Search engines can't understand your images, and screen readers can't describe them",
            "recommendation": "Add descriptive alt text to all images",
            "example": '<img src="product.jpg" alt="Blue cotton t-shirt with vintage logo design">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.MEDIUM,
            "implementation_steps": [
                "Review all images on your page",
                "Write descriptive alt text for each",
                "Include relevant keywords naturally",
                "Keep alt text under 125 characters",
                "Leave decorative images with empty alt=\"\""
            ]
        },
        
        # Technical issues
        "slow_page": {
            "severity": IssueSeverity.WARNING,
            "message": "Your page loads slowly",
            "user_impact": "Slow pages frustrate users and rank lower in search results",
            "recommendation": "Optimize images, enable caching, and minimize code",
            "example": "Compress images with tools like TinyPNG, enable browser caching, and use a CDN",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 8,
            "estimated_impact": EstimatedImpact.HIGH,
            "quick_wins": [
                "Compress and resize images",
                "Enable GZIP compression",
                "Minify CSS and JavaScript",
                "Use browser caching",
                "Consider a Content Delivery Network (CDN)"
            ]
        },
        
        "no_https": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Your site doesn't use HTTPS",
            "user_impact": "Browsers show 'Not Secure' warnings, scaring away visitors",
            "recommendation": "Install an SSL certificate to enable HTTPS",
            "example": "Contact your hosting provider for SSL installation, or use free Let's Encrypt certificates",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 10,
            "estimated_impact": EstimatedImpact.HIGH,
            "implementation_steps": [
                "Obtain an SSL certificate (free from Let's Encrypt)",
                "Install the certificate on your server",
                "Update all internal links to HTTPS",
                "Set up 301 redirects from HTTP to HTTPS",
                "Update your sitemap and Google Search Console"
            ]
        },
        
        # Structured data issues
        "missing_structured_data": {
            "severity": IssueSeverity.NOTICE,
            "message": "Your page lacks structured data",
            "user_impact": "You're missing rich snippets that make your search results stand out",
            "recommendation": "Add Schema.org markup for your content type",
            "example": 'For a product: {"@type": "Product", "name": "Your Product", "price": "99.99"}',
            "implementation_difficulty": ImplementationDifficulty.HARD,
            "priority_score": 4,
            "estimated_impact": EstimatedImpact.MEDIUM,
            "resources": [
                "Use Google's Structured Data Testing Tool",
                "Reference Schema.org for proper markup",
                "Start with basic Organization or Product schema",
                "Test implementation with Rich Results Test"
            ]
        },
        
        # Additional title issues
        "multiple_titles": {
            "severity": IssueSeverity.WARNING,
            "message": "Multiple title tags found",
            "user_impact": "Search engines will be confused about which title to use",
            "recommendation": "Keep only one title tag per page",
            "example": "Remove duplicate <title> tags and keep only the most relevant one",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "title_truncated": {
            "severity": IssueSeverity.NOTICE,
            "message": "Title may be truncated in search results",
            "user_impact": "Important information at the end of your title might not be visible",
            "recommendation": "Keep your title under 580 pixels wide (approximately 55-60 characters)",
            "example": "Move important keywords to the beginning of your title",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 4,
            "estimated_impact": EstimatedImpact.LOW
        },
        
        "generic_title": {
            "severity": IssueSeverity.WARNING,
            "message": "Title is too generic",
            "user_impact": "Generic titles don't attract clicks or rank well",
            "recommendation": "Make your title more specific and descriptive",
            "example": 'Instead of "Home" use "Professional SEO Tools & Analysis | YourBrand"',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "title_keyword_stuffing": {
            "severity": IssueSeverity.WARNING,
            "message": "Possible keyword stuffing in title",
            "user_impact": "Over-optimized titles can be penalized by search engines",
            "recommendation": "Use keywords naturally, avoid repetition",
            "example": 'Instead of "SEO Tools | SEO Software | SEO Analysis | SEO" use "Professional SEO Analysis Tools | YourBrand"',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Additional description issues
        "short_description": {
            "severity": IssueSeverity.WARNING,
            "message": "Meta description is too short",
            "user_impact": "You're not using the full space available to attract clicks",
            "recommendation": "Expand your description to 150-160 characters",
            "example": "Add more details about what makes your page valuable or unique",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "long_description": {
            "severity": IssueSeverity.WARNING,
            "message": "Meta description is too long",
            "user_impact": "Google will cut off your description, potentially losing your call-to-action",
            "recommendation": "Shorten your description to under 160 characters",
            "example": "Put the most important information and call-to-action first",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "multiple_descriptions": {
            "severity": IssueSeverity.WARNING,
            "message": "Multiple meta description tags found",
            "user_impact": "Search engines may ignore all descriptions when multiple are present",
            "recommendation": "Keep only one meta description tag",
            "example": "Remove duplicate description tags and keep the most compelling one",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # H1 and heading issues
        "missing_h1": {
            "severity": IssueSeverity.WARNING,
            "message": "No H1 heading found",
            "user_impact": "H1 helps search engines understand your page's main topic",
            "recommendation": "Add one H1 tag with your main keyword",
            "example": '<h1>Professional SEO Analysis Tools for Better Rankings</h1>',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        "multiple_h1": {
            "severity": IssueSeverity.WARNING,
            "message": "Multiple H1 tags found",
            "user_impact": "Multiple H1s can confuse search engines about your main topic",
            "recommendation": "Use only one H1 tag per page",
            "example": "Keep the most important H1 and change others to H2 or H3",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "empty_h1": {
            "severity": IssueSeverity.WARNING,
            "message": "H1 tag is empty",
            "user_impact": "An empty H1 provides no value for SEO",
            "recommendation": "Add descriptive text to your H1 tag",
            "example": '<h1>Your Main Page Topic Here</h1>',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        # Canonical and indexing issues
        "noindex": {
            "severity": IssueSeverity.WARNING,
            "message": "Page has noindex directive",
            "user_impact": "This page will not appear in search results",
            "recommendation": "Remove noindex if you want this page to be found in search",
            "example": 'Remove <meta name="robots" content="noindex"> or change to "index"',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 9,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        "nofollow": {
            "severity": IssueSeverity.NOTICE,
            "message": "Page has nofollow directive",
            "user_impact": "Search engines won't follow links on this page",
            "recommendation": "Remove nofollow unless you specifically don't want links followed",
            "example": 'Change <meta name="robots" content="nofollow"> to "follow"',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 4,
            "estimated_impact": EstimatedImpact.LOW
        },
        
        "multiple_canonicals": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Multiple canonical URLs found",
            "user_impact": "Conflicting canonicals can cause indexing problems",
            "recommendation": "Use only one canonical URL per page",
            "example": '<link rel="canonical" href="https://example.com/page">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 9,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        "invalid_canonical": {
            "severity": IssueSeverity.WARNING,
            "message": "Canonical URL should be absolute",
            "user_impact": "Relative canonical URLs may not work properly",
            "recommendation": "Use full URLs starting with https://",
            "example": '<link rel="canonical" href="https://example.com/page">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Open Graph issues
        "incomplete_open_graph": {
            "severity": IssueSeverity.WARNING,
            "message": "Missing required Open Graph tags",
            "user_impact": "Your content won't display properly when shared on social media",
            "recommendation": "Add missing Open Graph tags for better social sharing",
            "example": '<meta property="og:title" content="Your Title">\n<meta property="og:image" content="image.jpg">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Mobile and technical issues
        "missing_viewport": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Missing viewport meta tag",
            "user_impact": "Your site won't display properly on mobile devices",
            "recommendation": "Add viewport meta tag for mobile responsiveness",
            "example": '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 9,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        # Link issues
        "broken_internal_links": {
            "severity": IssueSeverity.WARNING,
            "message": "Broken internal links found",
            "user_impact": "Broken links frustrate users and waste search engine crawl budget",
            "recommendation": "Fix or remove all broken internal links",
            "example": "Check that all linked pages exist and return 200 status codes",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "redirect_chains": {
            "severity": IssueSeverity.WARNING,
            "message": "Redirect chains detected",
            "user_impact": "Multiple redirects slow down page loading and can lose link equity",
            "recommendation": "Update links to point directly to the final destination",
            "example": "Instead of A→B→C, update links to point directly to C",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Security header issues
        "missing_security_header": {
            "severity": IssueSeverity.NOTICE,
            "message": "Important security header is missing",
            "user_impact": "Your site may be vulnerable to certain attacks",
            "recommendation": "Add recommended security headers to protect users",
            "example": "Add headers like X-Frame-Options, X-Content-Type-Options, etc.",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "server_version_exposed": {
            "severity": IssueSeverity.NOTICE,
            "message": "Server version information exposed",
            "user_impact": "Attackers can use version info to find vulnerabilities",
            "recommendation": "Hide server version information in headers",
            "example": "Configure your server to not reveal version numbers",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 3,
            "estimated_impact": EstimatedImpact.LOW
        },
        
        # Compression issues
        "no_compression": {
            "severity": IssueSeverity.WARNING,
            "message": "Content is not compressed",
            "user_impact": "Larger file sizes mean slower page loads",
            "recommendation": "Enable GZIP or Brotli compression on your server",
            "example": "Enable compression in your server configuration",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        # Caching issues
        "no_cache_control": {
            "severity": IssueSeverity.WARNING,
            "message": "No Cache-Control header found",
            "user_impact": "Browsers can't cache resources efficiently, causing repeated downloads",
            "recommendation": "Add Cache-Control headers for static resources",
            "example": 'Cache-Control: public, max-age=31536000',
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Mobile issues
        "no_viewport": {
            "severity": IssueSeverity.CRITICAL,
            "message": "Missing viewport meta tag",
            "user_impact": "Your site won't display properly on mobile devices",
            "recommendation": "Add viewport meta tag for mobile responsiveness",
            "example": '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 9,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        "viewport_zoom_disabled": {
            "severity": IssueSeverity.WARNING,
            "message": "Viewport disables user zoom",
            "user_impact": "Users with visual impairments can't zoom your content",
            "recommendation": "Remove zoom restrictions for better accessibility",
            "example": '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Canonical issues
        "missing_canonical": {
            "severity": IssueSeverity.WARNING,
            "message": "No canonical URL specified",
            "user_impact": "Search engines might index duplicate versions of your page",
            "recommendation": "Add a canonical link tag to specify the preferred URL",
            "example": '<link rel="canonical" href="https://example.com/page">',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Structured data issues
        "invalid_structured_data": {
            "severity": IssueSeverity.WARNING,
            "message": "Invalid structured data found",
            "user_impact": "Search engines can't understand your structured data",
            "recommendation": "Fix structured data syntax errors",
            "example": "Validate your JSON-LD at Google's Structured Data Testing Tool",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Performance issues (already defined slow_page)
        "large_page_size": {
            "severity": IssueSeverity.WARNING,
            "message": "Page size is too large",
            "user_impact": "Large pages take longer to download, especially on mobile",
            "recommendation": "Optimize images and reduce page weight",
            "example": "Compress images, minify code, remove unnecessary resources",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 7,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        # Additional security issues
        "missing_https_redirect": {
            "severity": IssueSeverity.WARNING,
            "message": "HTTP version doesn't redirect to HTTPS",
            "user_impact": "Users might access the insecure version of your site",
            "recommendation": "Set up automatic redirects from HTTP to HTTPS",
            "example": "Configure 301 redirects on your server",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 8,
            "estimated_impact": EstimatedImpact.HIGH
        },
        
        # Heading structure issues
        "heading_hierarchy_skip": {
            "severity": IssueSeverity.WARNING,
            "message": "Heading hierarchy skip detected",
            "user_impact": "Skipping heading levels confuses screen readers and document structure",
            "recommendation": "Use headings in sequential order (H1→H2→H3, not H1→H3)",
            "example": "If you need smaller text, use CSS instead of skipping heading levels",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        "empty_heading": {
            "severity": IssueSeverity.WARNING,
            "message": "Empty heading tag found",
            "user_impact": "Empty headings provide no value and confuse document structure",
            "recommendation": "Either add text to the heading or remove it",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.LOW
        },
        
        "h1_after_h2": {
            "severity": IssueSeverity.WARNING,
            "message": "H1 appears after H2",
            "user_impact": "Incorrect heading order confuses both users and search engines",
            "recommendation": "Place your H1 tag before any H2 tags",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 6,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Semantic HTML issues
        "missing_main_element": {
            "severity": IssueSeverity.NOTICE,
            "message": "No <main> element found",
            "user_impact": "The <main> element helps screen readers and search engines identify primary content",
            "recommendation": "Wrap your main content in a <main> element",
            "example": '<main>\n  <h1>Page Title</h1>\n  <p>Main content here...</p>\n</main>',
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 4,
            "estimated_impact": EstimatedImpact.LOW
        },
        
        "low_text_to_html_ratio": {
            "severity": IssueSeverity.WARNING,
            "message": "Low text-to-HTML ratio",
            "user_impact": "Too much code compared to content can indicate poor content quality to search engines",
            "recommendation": "Add more valuable content or reduce excessive HTML/JavaScript",
            "implementation_difficulty": ImplementationDifficulty.MEDIUM,
            "priority_score": 5,
            "estimated_impact": EstimatedImpact.MEDIUM
        },
        
        # Link analysis issues
        "excessive_internal_links": {
            "severity": IssueSeverity.NOTICE,
            "message": "Too many internal links on page",
            "user_impact": "Excessive links can dilute page authority and overwhelm users",
            "recommendation": "Focus on linking to your most important pages",
            "example": "Aim for 100-150 internal links maximum per page",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 4,
            "estimated_impact": EstimatedImpact.LOW
        },
        
        "no_external_links": {
            "severity": IssueSeverity.NOTICE,
            "message": "No external links found",
            "user_impact": "Linking to authoritative external sources can improve content credibility",
            "recommendation": "Consider linking to relevant, authoritative external resources",
            "implementation_difficulty": ImplementationDifficulty.EASY,
            "priority_score": 3,
            "estimated_impact": EstimatedImpact.LOW
        }
    }
    
    @classmethod
    def create_issue(cls, issue_type: str, **kwargs) -> Dict[str, Any]:
        """
        Create an enhanced issue object
        
        Args:
            issue_type: Type of issue from ISSUE_DEFINITIONS
            **kwargs: Additional context (e.g., current_value, recommended_value)
            
        Returns:
            Enhanced issue dictionary
        """
        if issue_type not in cls.ISSUE_DEFINITIONS:
            # Fallback for undefined issues
            return {
                "type": issue_type,
                "severity": kwargs.get("severity", "warning"),
                "message": kwargs.get("message", f"Issue detected: {issue_type}"),
                "user_impact": kwargs.get("user_impact", "This may affect your SEO performance"),
                "recommendation": kwargs.get("recommendation", "Review and fix this issue"),
                "implementation_difficulty": "medium",
                "priority_score": 5,
                "estimated_impact": "medium"
            }
        
        # Get base definition
        base_issue = cls.ISSUE_DEFINITIONS[issue_type].copy()
        
        # Convert enums to strings
        for key, value in base_issue.items():
            if isinstance(value, Enum):
                base_issue[key] = value.value
        
        # Add type
        base_issue["type"] = issue_type
        
        # Customize message with context if provided
        if kwargs:
            base_issue = cls._customize_issue_with_context(base_issue, kwargs)
        
        return base_issue
    
    @classmethod
    def _customize_issue_with_context(cls, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Customize issue messages with specific context"""
        
        # Replace placeholders in messages
        for key in ["message", "user_impact", "recommendation"]:
            if key in issue and isinstance(issue[key], str):
                try:
                    issue[key] = issue[key].format(**context)
                except KeyError:
                    pass  # Keep original if placeholders don't match
        
        # Add context data
        if "current_value" in context:
            issue["current_value"] = context["current_value"]
        
        if "recommended_value" in context:
            issue["recommended_value"] = context["recommended_value"]
        
        if "additional_info" in context:
            issue["additional_info"] = context["additional_info"]
        
        return issue
    
    @classmethod
    def batch_create_issues(cls, issue_list: List[tuple]) -> List[Dict[str, Any]]:
        """
        Create multiple issues at once
        
        Args:
            issue_list: List of tuples (issue_type, context_dict)
            
        Returns:
            List of enhanced issue dictionaries
        """
        return [cls.create_issue(issue_type, **context) for issue_type, context in issue_list]
    
    @classmethod
    def get_issue_category(cls, issue_type: str) -> str:
        """Get the category of an issue for grouping"""
        categories = {
            "missing_title": "Meta Tags",
            "empty_title": "Meta Tags",
            "short_title": "Meta Tags",
            "long_title": "Meta Tags",
            "missing_description": "Meta Tags",
            "empty_description": "Meta Tags",
            "thin_content": "Content Quality",
            "poor_readability": "Content Quality",
            "missing_alt_text": "Images",
            "slow_page": "Performance",
            "no_https": "Security",
            "missing_structured_data": "Structured Data",
            "multiple_titles": "Meta Tags",
            "title_truncated": "Meta Tags",
            "generic_title": "Meta Tags",
            "title_keyword_stuffing": "Meta Tags",
            "short_description": "Meta Tags",
            "long_description": "Meta Tags",
            "multiple_descriptions": "Meta Tags",
            "missing_h1": "Headings",
            "multiple_h1": "Headings",
            "empty_h1": "Headings",
            "noindex": "Canonical and Indexing",
            "nofollow": "Canonical and Indexing",
            "multiple_canonicals": "Canonical and Indexing",
            "invalid_canonical": "Canonical and Indexing",
            "incomplete_open_graph": "Open Graph",
            "missing_viewport": "Mobile and Technical",
            "broken_internal_links": "Links",
            "redirect_chains": "Links",
            "heading_hierarchy_skip": "Headings",
            "empty_heading": "Headings",
            "h1_after_h2": "Headings",
            "missing_main_element": "Semantic HTML",
            "low_text_to_html_ratio": "Semantic HTML",
            "excessive_internal_links": "Links",
            "no_external_links": "Links",
            "missing_security_header": "Security",
            "server_version_exposed": "Security",
            "no_compression": "Performance",
            "no_cache_control": "Performance",
            "no_viewport": "Mobile",
            "viewport_zoom_disabled": "Mobile",
            "missing_canonical": "Canonical",
            "invalid_structured_data": "Structured Data",
            "large_page_size": "Performance",
            "missing_https_redirect": "Security"
        }
        return categories.get(issue_type, "Other") 