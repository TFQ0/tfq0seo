# tfq0seo 🔍

[![PyPI version](https://img.shields.io/pypi/v/tfq0seo.svg)](https://pypi.org/project/tfq0seo/)
[![Python Versions](https://img.shields.io/pypi/pyversions/tfq0seo.svg)](https://pypi.org/project/tfq0seo/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, comprehensive SEO analysis and optimization toolkit that helps you improve your website's search engine visibility and performance. 🚀

## ✨ Features

- 🌐 **URL Analysis**: Complete SEO audit of web pages
- 📝 **Content Analysis**: Text content optimization and recommendations
- 📱 **Mobile-Friendly Check**: Ensure your site works well on all devices
- 🔒 **Security Analysis**: HTTPS and security header validation
- 🏗️ **HTML Structure**: Comprehensive HTML validation and optimization
- 🎯 **SEO**: User experience and progressive enhancement analysis
- 💾 **Multiple Export Formats**: JSON, HTML, and Markdown support

## 🛠️ Installation

```bash
pip install tfq0seo
```

## 🚀 Quick Start

### Analyze a URL

```bash
# Basic analysis
tfq0seo analyze https://example.com

# Analysis with multiple URLs
tfq0seo analyze https://example.com https://another-site.com --format html

# Advanced analysis with custom options
tfq0seo analyze https://example.com --depth 3 --competitors 5 --format json
```

### View Available Features

```bash
# Show features in rich format (default)
tfq0seo list

# Show features in plain text
tfq0seo list --format plain
```

### Output Formats

Choose your preferred output format with the `--format` flag:

```bash
tfq0seo analyze https://example.com --format html  # Interactive HTML report (default)
tfq0seo analyze https://example.com --format json  # Structured JSON data
tfq0seo analyze https://example.com --format csv   # Tabular CSV format
```

### CLI Options

```bash
# Show help
tfq0seo --help

# Show command-specific help
tfq0seo analyze --help
tfq0seo list --help

# Suppress progress output
tfq0seo analyze https://example.com --quiet

# Specify output location
tfq0seo analyze https://example.com --output reports/
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

## 📊 Output Formats

The tool supports three output formats, each optimized for different use cases:

### HTML Report
- Interactive and visually appealing
- Clear visualization of metrics
- Color-coded status indicators
- Mobile-responsive design
- Easy to share and view in browsers

### JSON Format
- Structured data format
- Perfect for programmatic processing
- Complete analysis details
- Easy to parse and integrate
- Ideal for automation workflows

### CSV Format
- Tabular data representation
- Easy to import into spreadsheets
- Simple to analyze in tools like Excel
- Good for data aggregation
- Compatible with data analysis tools

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
