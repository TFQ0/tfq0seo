# AI Prompt: Creating High-Performance SEO Analysis Tools with Lighthouse-Quality Reports

## 🎯 Objective
Build a fast, accurate SEO analysis tool (like tfq0seo) that generates professional reports comparable to Google Lighthouse in quality and presentation.

---

## 📋 Phase 1: Core Requirements Analysis

**Ask the AI:**

```
I need to create a high-performance SEO analysis tool called [TOOL_NAME] that:

1. **Performance Requirements:**
   - Analyzes websites 2-3x faster than competitors
   - Handles 500+ pages with minimal memory usage (<500MB)
   - Supports concurrent processing (10-50 requests)
   - Processes pages in <3 seconds average

2. **Analysis Scope (Core Only):**
   - SEO: Meta tags, Open Graph, structured data, canonical URLs
   - Content: Readability scores, word count, heading structure, keyword density
   - Technical: HTTPS, mobile-friendly, security headers, compression
   - Performance: Load time, Core Web Vitals estimates, resource optimization
   - Links: Internal/external links, broken link detection, anchor text quality

3. **Report Quality (Lighthouse-Level):**
   - Professional HTML/PDF reports with visual scoring
   - Color-coded severity levels (critical/warning/notice)
   - Actionable recommendations with implementation steps
   - Before/after comparison potential
   - Export formats: JSON, CSV, XLSX, HTML
   - Interactive charts and graphs
   - Mobile-responsive report design

4. **Architecture Principles:**
   - ❌ NO over-engineering (no complex abstraction layers)
   - ❌ NO bloated error recovery systems
   - ❌ NO verbose logging frameworks
   - ✅ Simple, direct implementations
   - ✅ Single responsibility per module
   - ✅ Efficient data structures (dicts, not objects)
   - ✅ Minimal dependencies

Please design the architecture with these constraints.
```

---

## 📐 Phase 2: Architecture Design

**Ask the AI:**

```
Design a lean architecture for [TOOL_NAME] with:

**Core Modules (Keep Minimal):**

1. **CLI Module (cli.py)**
   - Commands: crawl, analyze, batch, sitemap, export
   - Progress tracking with rich console output
   - Simple argument parsing (Click library)
   - NO complex configuration systems

2. **Crawler Module (crawler.py)**
   - Async crawler using aiohttp
   - Simple robots.txt parsing (urllib.robotparser)
   - Dictionary-based result storage
   - Content truncation for large pages (100KB limit)
   - NO memory managers, NO real-time validators

3. **Analyzers (5 separate modules):**
   - seo.py: Meta tags, OG tags, structured data
   - content.py: Readability (textstat), keyword analysis
   - technical.py: HTTPS, headers, mobile-friendliness
   - performance.py: Load time, resource counts
   - links.py: Link analysis, broken link detection
   
   **Each analyzer should:**
   - Have a simple create_issue() function (NOT a class)
   - Return plain dictionaries
   - NO complex inheritance
   - NO error recovery frameworks

4. **App Module (app.py)**
   - Orchestrate analyzers
   - Simple error handling (try/except, log & continue)
   - Calculate overall scores
   - NO recommendation engines
   - NO data quality scorers

5. **Exporter Module (exporters/base.py)**
   - JSON: Simple json.dump()
   - CSV: Flatten nested data
   - XLSX: Use openpyxl with basic formatting
   - HTML: Jinja2 templates with Lighthouse-style design

6. **Config Module (config.py)**
   - Dataclass-based configuration
   - Load from JSON/YAML
   - Environment variable support
   - NO complex validation frameworks

**What to AVOID:**
- ❌ Abstract base classes (unless truly needed)
- ❌ Complex error recovery systems
- ❌ Multiple HTML parser fallbacks (use lxml OR html.parser)
- ❌ Recommendation engines
- ❌ Data quality scoring systems
- ❌ Version managers
- ❌ Dependency injection frameworks
- ❌ Custom exception hierarchies

Design the class structure and module relationships.
```

---

## 🎨 Phase 3: Lighthouse-Quality Report Design

**Ask the AI:**

```
Create a Lighthouse-quality HTML report template for [TOOL_NAME] with:

**Visual Design Requirements:**

1. **Header Section:**
   - Tool logo and name
   - Analyzed URL and timestamp
   - Overall score (0-100) with circular gauge
   - Color coding: Red (<50), Orange (50-80), Green (80+)

2. **Score Breakdown:**
   - 5 category scores with mini gauges:
     * SEO (Meta Tags) - 25%
     * Content Quality - 25%
     * Technical SEO - 20%
     * Performance - 20%
     * Links - 10%
   - Each with color-coded score and trend indicators

3. **Issues Section:**
   - Tabbed interface: Critical | Warnings | Notices
   - Count badges for each severity
   - Expandable issue cards with:
     * Issue title and description
     * Affected URLs (if multiple)
     * Fix priority (High/Medium/Low)
     * Estimated fix time
     * Code examples (if applicable)

4. **Recommendations Section:**
   - Top 5-10 actionable items
   - Quick wins highlighted separately
   - Step-by-step implementation guides
   - Expected impact indicators

5. **Detailed Analysis Tabs:**
   - SEO Overview
   - Content Analysis
   - Technical Checks
   - Performance Metrics
   - Link Profile

6. **Charts & Visualizations:**
   - Page speed waterfall (if available)
   - Content distribution pie chart
   - Link distribution bar chart
   - Issue severity distribution
   - Score comparison (if multiple runs)

**Technical Implementation:**

Use Jinja2 template with:
- Embedded CSS (no external dependencies)
- Vanilla JavaScript for interactivity
- Chart.js for visualizations (CDN)
- Responsive design (mobile-friendly)
- Print-optimized CSS
- Dark mode support

**Template Structure:**
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Analysis Report - {{ url }}</title>
    <style>
        /* Lighthouse-inspired styles */
        /* Color scheme: Green (#0cce6b), Orange (#ffa400), Red (#ff4e42) */
    </style>
</head>
<body>
    <div class="report-container">
        <!-- Header with overall score -->
        <!-- Category scores -->
        <!-- Issues list -->
        <!-- Recommendations -->
        <!-- Detailed tabs -->
    </div>
    <script>
        /* Interactive elements */
        /* Chart rendering */
    </script>
</body>
</html>
```

Create the complete HTML template with CSS and JavaScript.
```

---

## ⚡ Phase 4: Performance Optimization

**Ask the AI:**

```
Optimize [TOOL_NAME] for maximum performance:

**Code Optimization:**

1. **HTML Parsing:**
   - Use lxml (fastest) as primary parser
   - Fallback to html.parser only if lxml unavailable
   - NO html5lib (too slow)
   - Parse once, extract all data in single pass

2. **Issue Creation:**
   - Simple function: create_issue(type, severity, message)
   - Returns plain dict: {'type': '', 'severity': '', 'message': ''}
   - NO classes, NO inheritance, NO complex objects

3. **Async Optimization:**
   - Use asyncio.Semaphore for concurrency control
   - Implement connection pooling (aiohttp connector)
   - Batch process URLs (10-50 at a time)
   - Use asyncio.gather with return_exceptions=True

4. **Memory Management:**
   - Store results in simple dictionaries
   - Truncate large content (>100KB) immediately
   - NO caching frameworks
   - Clean up after each batch

5. **Data Structures:**
   - Use dicts over custom classes
   - Use lists over custom collections
   - Avoid deep nesting (max 3 levels)
   - Flatten data for exports

**Performance Targets:**

- Single page analysis: <2 seconds
- 100 pages crawl: <2 minutes (with 10 concurrent)
- 500 pages crawl: <8 minutes
- Memory usage: <500MB for 500 pages
- Report generation: <1 second

**Benchmark and Profile:**

```python
import time
import psutil
import asyncio

async def benchmark():
    start = time.time()
    start_mem = psutil.Process().memory_info().rss / 1024 / 1024
    
    # Run analysis
    results = await app.crawl()
    
    end = time.time()
    end_mem = psutil.Process().memory_info().rss / 1024 / 1024
    
    print(f"Time: {end-start:.2f}s")
    print(f"Memory: {end_mem-start_mem:.2f}MB")
    print(f"Pages: {len(results)}")
    print(f"Speed: {len(results)/(end-start):.1f} pages/sec")
```

Show me the optimized implementation.
```

---

## 🧪 Phase 5: Testing & Validation

**Ask the AI:**

```
Create a comprehensive testing suite for [TOOL_NAME]:

**Test Categories:**

1. **Accuracy Tests:**
   - Test against known websites
   - Compare with Google Lighthouse
   - Validate meta tag extraction
   - Verify readability scores
   - Check link detection accuracy

2. **Performance Tests:**
   - Measure analysis speed
   - Track memory usage
   - Test concurrent processing
   - Verify resource cleanup

3. **Edge Cases:**
   - Malformed HTML
   - Very large pages (>1MB)
   - Redirects (301, 302, meta refresh)
   - JavaScript-heavy sites
   - Non-English content
   - Special characters (emoji, unicode)

4. **Integration Tests:**
   - Full crawl workflow
   - Export to all formats
   - Resume functionality
   - Configuration loading

**Test Structure:**

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_single_page_analysis_speed():
    """Should analyze a page in <2 seconds"""
    start = time.time()
    result = await app.analyze_single("https://example.com")
    duration = time.time() - start
    
    assert duration < 2.0
    assert result['score'] is not None
    assert len(result['issues']) >= 0

@pytest.mark.asyncio
async def test_accuracy_vs_lighthouse():
    """Should match Lighthouse scores within 10%"""
    url = "https://example.com"
    our_score = await app.analyze_single(url)
    # lighthouse_score = get_lighthouse_score(url)
    
    # assert abs(our_score['score'] - lighthouse_score) < 10
```

Create the complete test suite.
```

---

## 📊 Phase 6: Report Enhancement

**Ask the AI:**

```
Enhance the HTML report for [TOOL_NAME] to match Lighthouse quality:

**Advanced Features:**

1. **Interactive Score Gauge:**
   - SVG-based circular progress
   - Animated on page load
   - Color changes based on score
   - Percentage text in center

2. **Collapsible Sections:**
   - Expand/collapse all button
   - Individual section toggles
   - Remember state (localStorage)
   - Smooth animations

3. **Search & Filter:**
   - Search issues by keyword
   - Filter by severity
   - Filter by category
   - Clear filters button

4. **Export Options:**
   - Print-friendly view
   - Export to PDF (browser print)
   - Copy issue list
   - Share report URL

5. **Comparison Mode:**
   - Side-by-side comparison
   - Highlight improvements
   - Show score trends
   - Visual diff

**JavaScript Implementation:**

```javascript
// Gauge animation
function animateGauge(score) {
    const gauge = document.querySelector('.gauge-circle');
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (score / 100) * circumference;
    gauge.style.strokeDashoffset = offset;
}

// Filter issues
function filterIssues(severity) {
    document.querySelectorAll('.issue-card').forEach(card => {
        card.style.display = 
            card.dataset.severity === severity ? 'block' : 'none';
    });
}

// Search functionality
function searchIssues(query) {
    document.querySelectorAll('.issue-card').forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = 
            text.includes(query.toLowerCase()) ? 'block' : 'none';
    });
}
```

Create the enhanced template with all features.
```

---

## 🚀 Phase 7: CLI Optimization

**Ask the AI:**

```
Optimize the CLI for [TOOL_NAME] for better UX:

**Features:**

1. **Rich Progress Display:**
   ```
   Crawling: ████████░░ 45/100 pages (45%) | 2:30 elapsed
   Current: https://example.com/page-45
   Speed: 15.2 pages/min | Memory: 125MB
   ```

2. **Live Summary:**
   - Pages analyzed
   - Issues found (by severity)
   - Average score
   - Estimated time remaining

3. **Color-Coded Output:**
   - Green: Success messages
   - Yellow: Warnings
   - Red: Errors
   - Blue: Info

4. **Commands:**
   ```bash
   # Quick analyze
   tfq0seo analyze https://example.com
   
   # Full crawl with options
   tfq0seo crawl https://example.com \
       --depth 5 \
       --max-pages 500 \
       --concurrent 20 \
       --format html \
       --output report.html
   
   # Batch analysis
   tfq0seo batch urls.txt --concurrent 10
   
   # Export conversion
   tfq0seo export --input data.json --format html
   ```

5. **Progress Persistence:**
   - Save state every 50 pages
   - Resume on interruption
   - Show resume option on restart

Implement using:
- Click for CLI framework
- Rich for progress bars and styling
- Asyncio for concurrent operations

Create the optimized CLI implementation.
```

---

## 📦 Phase 8: Deployment & Distribution

**Ask the AI:**

```
Prepare [TOOL_NAME] for distribution:

**Package Structure:**

```
tfq0seo/
├── pyproject.toml
├── setup.py
├── requirements.txt
├── README.md
├── LICENSE
├── MANIFEST.in
├── .gitignore
├── tfq0seo/
│   ├── __init__.py
│   ├── cli.py
│   ├── analyzers/
│   ├── core/
│   ├── exporters/
│   └── templates/
└── tests/
    └── ...
```

**setup.py:**

```python
setup(
    name="tfq0seo",
    version="2.2.0",
    author="Your Name",
    description="Fast SEO analysis tool with Lighthouse-quality reports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/username/tfq0seo",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "beautifulsoup4>=4.11.0",
        "click>=8.1.0",
        "jinja2>=3.1.0",
        "rich>=12.6.0",
        "textstat>=0.7.3",
        "validators>=0.20.0",
    ],
    extras_require={
        "full": ["lxml>=4.9.0", "openpyxl>=3.0.0", "pandas>=1.5.0"],
    },
    entry_points={
        "console_scripts": ["tfq0seo=tfq0seo.cli:main"],
    },
    python_requires=">=3.8",
)
```

**Documentation:**

Create:
1. README.md with quickstart
2. CHANGELOG.md
3. CONTRIBUTING.md
4. API documentation
5. Example reports

**Distribution:**

```bash
# Build
python -m build

# Test locally
pip install -e .

# Upload to PyPI
twine upload dist/*
```

Prepare the complete distribution package.
```

---

## 🎯 Key Success Metrics

Track these to ensure quality:

1. **Performance:**
   - ✅ Analysis speed: <2s per page
   - ✅ Memory usage: <500MB for 500 pages
   - ✅ Report generation: <1s

2. **Accuracy:**
   - ✅ Match Lighthouse scores ±10%
   - ✅ 95%+ accurate link detection
   - ✅ Correct meta tag extraction

3. **Code Quality:**
   - ✅ <10,000 total lines of code
   - ✅ No linter errors
   - ✅ 80%+ test coverage
   - ✅ Clear, simple architecture

4. **User Experience:**
   - ✅ Professional HTML reports
   - ✅ Clear CLI progress
   - ✅ Actionable recommendations
   - ✅ Multiple export formats

---

## 💡 Pro Tips

1. **Start Simple:** Build core functionality first, optimize later
2. **Profile Early:** Use cProfile to find bottlenecks
3. **Test with Real Sites:** Use diverse websites for testing
4. **Iterate on Reports:** Get feedback on report design
5. **Document Decisions:** Explain why you kept things simple
6. **Avoid Premature Optimization:** Optimize only proven bottlenecks
7. **Keep Dependencies Minimal:** Each dependency adds complexity
8. **Use Standards:** Follow SEO best practices (Google guidelines)

---

## 🔄 Maintenance & Updates

**Regular Tasks:**

1. **Update Dependencies:** Monthly security updates
2. **Test Against New Sites:** Quarterly validation
3. **Compare with Lighthouse:** Ensure parity with latest version
4. **Monitor Performance:** Track speed regressions
5. **Collect User Feedback:** Improve based on real usage

---

## 📝 Example Prompt Flow

**Complete conversation with AI:**

```
USER: I want to create a fast SEO analysis tool like tfq0seo that generates 
Lighthouse-quality reports. It should analyze 500+ pages quickly and provide 
professional HTML reports.

AI: I'll help you create [TOOL_NAME]. Let's start with the architecture...

USER: Keep it simple - no over-engineering. I want speed and accuracy, 
not complex frameworks.

AI: Understood. Here's a lean architecture with 5 analyzers, simple issue 
creation, and efficient data structures...

USER: Show me the HTML report template that looks like Lighthouse.

AI: Here's a professional template with score gauges, color-coded issues...

USER: Optimize for speed - I need 2-3x faster than current tools.

AI: Here are the optimizations: single HTML parser, simple dicts, 
async batching...

USER: Create tests to validate accuracy against Lighthouse.

AI: Here's a test suite that compares scores and validates extraction...
```

---

## ✅ Final Checklist

Before considering the tool complete:

- [ ] All 5 analyzers implemented and tested
- [ ] HTML report matches Lighthouse quality
- [ ] Performance benchmarks met (2s/page, <500MB)
- [ ] CLI with rich progress display
- [ ] All export formats working (JSON, CSV, XLSX, HTML)
- [ ] Test coverage >80%
- [ ] Documentation complete
- [ ] PyPI package prepared
- [ ] Example reports generated
- [ ] Zero linter errors
- [ ] Simple, maintainable codebase

---

## 🎓 Learning Resources

- Google Lighthouse source code
- PageSpeed Insights documentation
- Web.dev SEO guides
- aiohttp documentation
- BeautifulSoup best practices
- Jinja2 template guide

---

*This prompt ensures you build a professional, fast, accurate SEO tool with beautiful Lighthouse-quality reports while maintaining a simple, maintainable codebase.*

