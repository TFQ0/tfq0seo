# tfq0seo 🕷️

[![PyPI version](https://img.shields.io/pypi/v/tfq0seo.svg)](https://pypi.org/project/tfq0seo/)
[![Python Versions](https://img.shields.io/pypi/pyversions/tfq0seo.svg)](https://pypi.org/project/tfq0seo/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Enhanced SEO analysis and site crawling toolkit** - A comprehensive, professional-grade SEO analysis tool with full site crawling capabilities. Competitive with Screaming Frog SEO Spider but open source and extensible! 🚀

**Complete Site Crawling** - Now includes professional website crawling capabilities:
- 🕷️ **Full Site Crawling** with configurable depth (1-10 levels)
- ⚡ **Concurrent Processing** (1-50 simultaneous requests)
- 🔗 **Comprehensive Link Analysis** (internal/external/broken links)
- 📊 **Advanced Reporting** (JSON, CSV, XLSX, HTML exports)
- 🎯 **Duplicate Content Detection** across entire sites
- 📈 **Site Structure Analysis** and optimization recommendations
- 🖼️ **Image Optimization Analysis** (alt text, compression, formats)
- 🤖 **Robots.txt & Sitemap Integration**
- 📱 **Real-time Progress Tracking** with rich console output


## 🛠️ Installation

```bash
pip install tfq0seo
```

## 🚀 Quick Start

### 🕷️ Crawl an Entire Website (NEW!)

```bash
# Basic site crawl
tfq0seo crawl https://example.com

# Advanced crawl with custom settings
tfq0seo crawl https://example.com --depth 5 --max-pages 1000 --concurrent 20

# Export crawl results to different formats
tfq0seo crawl https://example.com --format csv --output site_audit.csv
tfq0seo crawl https://example.com --format xlsx --output comprehensive_report.xlsx

# Crawl with exclusions and custom settings
tfq0seo crawl https://example.com \
  --depth 3 \
  --max-pages 500 \
  --exclude "/admin/" "/private/" \
  --delay 1.0 \
  --format html
```

### 🔍 Analyze Individual URLs

```bash
# Basic URL analysis
tfq0seo analyze https://example.com

# Analysis with multiple URLs
tfq0seo analyze https://example.com https://another-site.com --format html

# Advanced analysis with custom options
tfq0seo analyze https://example.com --depth 3 --competitors 5 --format json
```

### 📊 Export and Insights

```bash
# Export previous crawl results
tfq0seo export --format csv --output results.csv

# Get quick insights from crawl
tfq0seo insights --summary --recommendations

# View available features
tfq0seo list
```

## 🚀 Powerful SEO Testing Capabilities

### 🔍 Large-Scale Site Crawling Tests

**E-commerce Site Analysis:**
```bash
# Comprehensive e-commerce site audit
tfq0seo crawl https://example-store.com --depth 5 --max-pages 1000 --concurrent 20 --format xlsx
```

**Performance Results:**
-  **Concurrent Processing**: Handles 10-50 simultaneous requests efficiently
-  **Robots.txt Compliance**: Respects crawling restrictions automatically
-  **Progress Tracking**: Real-time updates with rich console output
-  **Speed**: ~0.3-0.4 pages/second depending on site response time

**Multi-language Content Analysis:**
```bash
# Test international SEO capabilities
tfq0seo analyze https://multilingual-site.com --format json
```

### ⚡ Content Analysis Performance

**Processing Speed Benchmarks:**
- Small content (50 chars): 42,547 chars/second
- Medium content (500 chars): 127,139 chars/second  
- Large content (5,000 chars): 146,166 chars/second
- Very large content (25,000 chars): 146,604 chars/second

### 📊 Export & Data Analysis

**Comprehensive Export Testing:**
```bash
# Test all export formats with real data
tfq0seo crawl https://test-site.com --format json --output detailed.json
tfq0seo export --format csv --output spreadsheet.csv
tfq0seo export --format xlsx --output professional.xlsx
```

### 🎯 Real-World Site Analysis Results

**Live Site Crawl Example (httpbin.org):**
```bash
tfq0seo crawl https://httpbin.org --depth 2 --max-pages 20 --format json
```

**Actual Performance:**
- 📊 **Pages Crawled**: 2 pages in 4.54 seconds
- 🔍 **Analysis Quality**: Detected missing meta descriptions, missing H1 tags, thin content
- 📈 **Site Structure**: Max depth 1, average depth 0.5
- 🔗 **Link Analysis**: 1 internal link, 3 external links identified
- ⚠️ **Content Issues**: 2 pages with thin content, 2 missing meta descriptions

### 💪 Most Powerful Test Commands

**1. Comprehensive Site Audit:**
```bash
# Full professional site audit
tfq0seo crawl https://your-site.com  --depth 5 --max-pages 1000 --concurrent 15 --format xlsx --output comprehensive_audit --include-external
```

**2. Performance Stress Test:**
```bash
# Test tool limits and performance
tfq0seo crawl https://large-site.com \
  --depth 10 \
  --max-pages 5000 \
  --concurrent 50 \
  --delay 0.1
```

**3. Multi-Format Analysis Pipeline:**
```bash
# Generate multiple report formats for different stakeholders
tfq0seo crawl https://site.com --format json --output data.json
tfq0seo export --format csv --output spreadsheet.csv
tfq0seo insights --summary --recommendations
```

**4. Edge Case Testing:**
```bash
# Test problematic URLs and content
tfq0seo analyze "https://site.com/very-long-url-that-exceeds-recommended-length"
tfq0seo analyze "https://site.com/page?param1=value1&param2=value2&param3=value3"
```

## 📋 Command Reference

### 🕷️ Crawl Commands

```bash
# Basic crawl
tfq0seo crawl <URL>

# Advanced crawl options
tfq0seo crawl <URL> [OPTIONS]
  --depth INTEGER          Maximum crawl depth (1-10, default: 3)
  --max-pages INTEGER      Maximum pages to crawl (default: 500)
  --concurrent INTEGER     Concurrent requests (1-50, default: 10)
  --delay FLOAT           Delay between requests in seconds (default: 0.5)
  --format [json|csv|xlsx|html]  Output format (default: html)
  --output PATH           Output file path
  --exclude TEXT          Path patterns to exclude (repeatable)
  --no-robots             Ignore robots.txt restrictions
  --include-external      Include external links in analysis
```

### 🔍 Analysis Commands

```bash
# Single URL analysis
tfq0seo analyze <URL> [OPTIONS]
  --format [html|json|csv]  Output format (default: html)
  --output PATH            Output file or directory
  --depth INTEGER          Analysis depth (default: 2)
  --competitors INTEGER    Number of competitors to analyze (default: 3)
  --quiet                  Suppress progress output

# Content analysis
tfq0seo analyze-content --file <FILE> --keyword <KEYWORD>
tfq0seo analyze-content --text <TEXT> --keyword <KEYWORD>
```

### 📊 Export & Insights Commands

```bash
# Export crawl results
tfq0seo export --format [json|csv|xlsx] --output <PATH>

# Get insights
tfq0seo insights [--summary] [--recommendations]

# List features
tfq0seo list [--format [plain|rich]]
```

### Analyze Content

```bash
# From a file
tfq0seo analyze-content --file content.txt --keyword "your keyword"

# Direct text input
tfq0seo analyze-content --text "Your content here" --keyword "your keyword"
```

### Access Educational Resources

```bash
# Get all resources
tfq0seo education

# Get specific topic
tfq0seo education --topic meta_tags
```

### Comprehensive Analysis
```bash
# Run comprehensive analysis with all features
tfq0seo analyze --url https://example.com --comprehensive

# Run analysis with custom options
tfq0seo analyze --url https://example.com --comprehensive \
  --target-keyword "your keyword" \
  --competitors "https://competitor1.com,https://competitor2.com" \
  --depth complete \
  --format json
```

The comprehensive analysis includes:

#### Analysis Modules
- **Basic SEO**
  - Meta tags analysis
  - Content optimization
  - HTML structure
  - Keyword optimization
- **Modern SEO Features**
  - Schema markup
  - Social media integration
  - Mobile optimization
  - Rich snippets
- **Competitive Analysis**
  - Content comparison
  - Feature comparison
  - Market positioning
  - Competitive advantages
- **Advanced SEO**
  - User experience
  - Content clustering
  - Link architecture
  - Progressive features
- **Performance**
  - Load time metrics
  - Resource optimization
  - Caching implementation
  - Compression analysis
- **Security**
  - SSL implementation
  - Security headers
  - Content security
  - Vulnerability checks
- **Mobile Optimization**
  - Responsive design
  - Touch elements
  - Viewport configuration
  - Mobile performance

#### Analysis Results
The comprehensive analysis provides:

1. **Detailed Insights**
   - Critical issues
   - Major improvements
   - Minor improvements
   - Positive aspects
   - Competitive edges
   - Market opportunities

2. **Scoring**
   - Overall SEO score
   - Category-specific scores
   - Comparative metrics
   - Performance indicators

3. **Action Plan**
   - Critical actions
   - High priority tasks
   - Medium priority tasks
   - Low priority tasks
   - Monitoring tasks

4. **Impact Analysis**
   - Traffic impact estimates
   - Conversion impact
   - Implementation complexity
   - Resource requirements
   - Timeline estimates

#### Configuration Options
- **depth**: Analysis depth level
  - `basic`: Core SEO elements
  - `advanced`: Including modern features
  - `complete`: All analysis modules
- **format**: Output format
  - `json`: Detailed JSON report
  - `html`: Interactive HTML report
  - `markdown`: Formatted markdown
- **cache_results**: Enable/disable caching
- **custom_thresholds**: Custom analysis thresholds



## 🎯 Default Settings

tfq0seo comes with carefully tuned default settings for optimal SEO analysis:

### SEO Thresholds
- **Title Length**: 30-60 characters
- **Meta Description**: 120-160 characters
- **Minimum Content Length**: 300 words
- **Maximum Sentence Length**: 20 words
- **Keyword Density**: Maximum 3%

### Readability Standards
- **Flesch Reading Ease**: Minimum score of 60
- **Gunning Fog Index**: Maximum score of 12

### System Settings
- **Cache Location**: `~/.tfq0seo/cache`
- **Log Files**: `~/.tfq0seo/tfq0seo.log`
- **Cache Expiration**: 1 hour
- **Log Rotation**: 10MB max file size, keeps 5 backups

## 📋 Analysis Areas

### Meta Analysis
- Title tag optimization
- Meta description validation
- Open Graph meta tags
- Canonical URL verification
- Language declaration

### Content Analysis
- Keyword optimization and placement
- Content structure analysis
- Readability metrics
- Heading hierarchy check
- Image alt text validation

### Technical SEO
- Mobile responsiveness
- HTML structure validation
- Security implementation
- Schema markup validation
- Robots.txt and sitemap checks

### Competitive Analysis
- Content comparison metrics
- Feature set comparison
- Semantic keyword analysis
- Technical implementation comparison
- Market positioning insights
- Framework and technology detection
- Performance feature analysis
- SEO feature implementation check

### Advanced SEO Features
- User Experience Analysis
  - Navigation structure
  - Accessibility implementation
  - Interactive elements
  - Content layout optimization
- Content Clustering
  - Topic hierarchy analysis
  - Related content detection
  - Semantic structure
  - Content relationships
- Link Architecture
  - Internal linking patterns
  - Link depth analysis
  - Anchor text quality
  - Link distribution
- Rich Results Optimization
  - Schema.org implementation
  - Rich snippet potential
  - Meta enhancements
  - Structured data types
- Progressive Enhancement
  - Offline support
  - Performance features
  - Enhancement layers
  - Progressive loading


- 🐛 **Bug Reports**: Help us identify and fix issues
- 💡 **Feature Requests**: Suggest new capabilities and improvements
- 🧪 **Testing**: Help expand our test coverage and scenarios

**tfq0seo** - Empowering SEO professionals with open-source, extensible, and powerful analysis tools. 🚀