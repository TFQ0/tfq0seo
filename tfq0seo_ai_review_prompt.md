# AI Review Prompt for tfq0seo - Professional SEO Analysis Toolkit

## Context
You are reviewing tfq0seo, an open-source SEO analysis toolkit that serves as an alternative to Screaming Frog SEO Spider. The tool is designed to crawl websites, analyze SEO factors, and generate reports. It's built with Python using asyncio for concurrent crawling and various libraries for analysis.

## Your Task
Please conduct a comprehensive review of the tfq0seo codebase and:

### 1. Identify and Fix Critical Errors
- Review all Python modules for syntax errors, logic bugs, and runtime exceptions
- Check for proper error handling and edge cases
- Verify all imports and dependencies are correctly specified
- Fix any broken functionality or incorrect implementations
- Ensure the tool can actually run without crashing

### 2. Improve SEO Analysis Accuracy
Review and enhance the accuracy of SEO analysis components:

**Meta Tags Analysis:**
- Ensure proper extraction of all meta tags (title, description, keywords, Open Graph, Twitter Cards, Schema.org)
- Fix character encoding issues
- Handle edge cases like multiple title tags or missing tags
- Implement proper length calculations considering pixel width, not just character count

**Content Analysis:**
- Improve keyword density calculations to consider stemming and variations
- Enhance readability metrics (Flesch score, Gunning Fog) accuracy
- Fix word count to properly handle HTML entities and special characters
- Add missing content quality signals (semantic HTML usage, content structure)

**Technical SEO:**
- Verify correct detection of canonical URLs, hreflang tags, and alternate versions
- Improve mobile-friendliness detection beyond basic viewport checks
- Add Core Web Vitals approximation based on page characteristics
- Fix robots.txt and sitemap.xml parsing edge cases

**Performance Metrics:**
- Enhance load time measurements to be more accurate
- Add resource size tracking (images, CSS, JS)
- Implement proper redirect chain following
- Calculate page weight and optimization opportunities

**Link Analysis:**
- Fix internal/external link classification
- Properly handle relative URLs and edge cases
- Detect broken links accurately with proper status code handling
- Analyze anchor text distribution and over-optimization

### 3. Code Quality Improvements
- Add comprehensive input validation
- Implement proper async/await patterns throughout
- Fix memory leaks in the crawler (proper session cleanup)
- Add rate limiting to prevent overwhelming target servers
- Implement retry logic with exponential backoff
- Add proper logging instead of just console prints

### 4. Feature Completeness
Ensure these advertised features actually work:
- CSV, XLSX, HTML, and JSON export formats
- Competitive analysis functionality
- Respect for robots.txt
- Crawl depth limiting
- Concurrent request handling
- Progress tracking

### 5. Security Fixes
- Sanitize all user inputs
- Prevent SSRF attacks in the crawler
- Add proper SSL/TLS verification
- Implement safe HTML parsing to prevent XSS in reports

### 6. Specific Areas Requiring Attention

**In crawler.py:**
- The URL normalization logic needs improvement (trailing slashes, parameters, fragments)
- Session management could leak resources
- Robots.txt parsing is too simplistic
- Need to handle JavaScript-rendered pages

**In analyzers/:**
- SEO scoring algorithm is too simplistic
- Missing many modern SEO factors (Core Web Vitals, E-E-A-T signals)
- Content analysis doesn't consider semantic HTML properly
- Performance analysis is based only on load time

**In exporters/:**
- Need to verify all export formats actually work
- HTML reports might have XSS vulnerabilities
- Excel exports might fail with large datasets

**In cli.py:**
- Command-line argument parsing might have bugs
- Progress display could break with certain terminal types
- Error messages need to be more helpful

### 7. Testing Requirements
After making improvements:
- Test with various website types (SPA, static, e-commerce)
- Verify it handles large sites (10,000+ pages) efficiently
- Test with sites having various technical configurations
- Ensure it works across different Python versions (3.8-3.11)
- Test all export formats with real data

### 8. Performance Optimization
- Optimize BeautifulSoup parsing (consider lxml strategies)
- Implement connection pooling properly
- Add caching for repeated requests
- Optimize memory usage for large crawls

### 9. Accuracy Benchmarks
Compare results with established tools:
- Screaming Frog SEO Spider
- Google PageSpeed Insights
- Google Search Console
- Manual verification

## Expected Deliverables
1. Fixed and improved code with inline comments explaining changes
2. List of all bugs found and how they were fixed
3. Accuracy improvement report comparing before/after
4. Recommendations for future enhancements
5. Updated tests to prevent regression

## Additional Notes
- The tool currently uses textstat for readability - verify its accuracy
- The SEO scoring system (0-100) needs to be based on actual SEO impact
- Many modern SEO factors are missing (Core Web Vitals, mobile-first indexing, etc.)
- The competitor analysis feature seems incomplete
- Error handling is minimal throughout the codebase

Please review the entire codebase systematically, starting with the core modules (crawler, app) and then moving to analyzers and exporters. Focus on making this a production-ready tool that SEO professionals can rely on for accurate analysis. 