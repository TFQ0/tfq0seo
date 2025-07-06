# tfq0seo - Professional SEO Analysis Toolkit

![Version](https://img.shields.io/badge/version-2.1.3-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)

**tfq0seo** is a comprehensive, open-source SEO analysis and site crawling toolkit that provides professional-grade website auditing capabilities. It's a powerful alternative to commercial tools like Screaming Frog SEO Spider, but fully open-source and extensible.

## 🚀 Features

### Site Crawling
- Full website crawling with configurable depth (1-10 levels)
- Concurrent processing (1-50 simultaneous requests)
- Respects robots.txt and sitemap.xml
- Real-time progress tracking with rich console output
- Configurable delays to avoid overwhelming servers

### SEO Analysis
- **Meta tags analysis**: Title, description, Open Graph, canonical URLs
- **Content analysis**: Readability, keyword density, content length, structure
- **Technical SEO**: Mobile-friendliness, HTTPS, security headers, schema markup
- **Performance metrics**: Load times, Core Web Vitals, resource optimization
- **Link analysis**: Internal/external/broken links, anchor text quality
- **Image optimization**: Alt text, compression, formats, dimensions

### Reporting & Export
- Multiple export formats: JSON, CSV, XLSX, HTML
- Professional reports with insights and recommendations
- Competitive analysis with side-by-side comparisons
- Action plans with priority levels and impact estimates

##  Installation

```bash
pip install tfq0seo
```

## 🎯 Quick Start

### Basic Usage

```bash
# Crawl entire website
tfq0seo crawl https://example.com

# Analyze single URL
tfq0seo analyze https://example.com

# Advanced crawl with options
tfq0seo crawl https://example.com --depth 5 --max-pages 1000 --concurrent 20 --format xlsx

# Batch analysis from file
tfq0seo batch urls.txt --format html --output batch_report.html

# Sitemap analysis
tfq0seo sitemap https://example.com/sitemap.xml --analyze
```

### Export Results

```bash
# Export to different formats
tfq0seo export --format csv --output results.csv
tfq0seo export --format xlsx --output report.xlsx
tfq0seo export --format html --output report.html
```

## 🔧 CLI Commands & Options

### `crawl` - Website Crawling
```bash
tfq0seo crawl [URL] [OPTIONS]
```
- `--depth, -d`: Crawl depth (1-10, default: 3)
- `--max-pages, -m`: Maximum pages to crawl (default: 500)
- `--concurrent, -c`: Concurrent requests (1-50, default: 10)
- `--delay`: Delay between requests in seconds (default: 0.5)
- `--format, -f`: Output format (json|csv|xlsx|html, default: json)
- `--output, -o`: Output file path
- `--exclude`: Path patterns to exclude (multiple allowed)
- `--no-robots`: Ignore robots.txt
- `--include-external`: Include external links
- `--user-agent`: Custom user agent
- `--config, -C`: Configuration file (JSON/YAML)
- `--resume`: Resume from previous crawl state
- `--dry-run`: Show what would be crawled without actually crawling
- `--sitemap-only`: Only crawl URLs from sitemap.xml

### `analyze` - Single URL Analysis
```bash
tfq0seo analyze [URL] [OPTIONS]
```
- `--comprehensive, -c`: Run all analysis modules
- `--target-keyword, -k`: Primary keyword for optimization
- `--competitors`: Comma-separated competitor URLs
- `--depth`: Analysis depth (basic|advanced|complete, default: advanced)
- `--format, -f`: Output format (json|csv|xlsx|html, default: json)
- `--output, -o`: Output file path

### `batch` - Batch URL Analysis
```bash
tfq0seo batch [URLS_FILE] [OPTIONS]
```
- `--format, -f`: Output format (json|csv|xlsx|html, default: json)
- `--output, -o`: Output file path
- `--concurrent, -c`: Concurrent analyses (1-20, default: 5)

### `sitemap` - Sitemap Analysis
```bash
tfq0seo sitemap [SITEMAP_URL] [OPTIONS]
```
- `--format, -f`: Output format (json|csv|txt, default: json)
- `--output, -o`: Output file path
- `--analyze`: Analyze URLs from sitemap

### `export` - Export Results
```bash
tfq0seo export [OPTIONS]
```
- `--format, -f`: Output format (json|csv|xlsx|html) **required**
- `--output, -o`: Output file path **required**
- `--input, -i`: Input file (if converting formats)

### Global Options
- `--verbose, -v`: Verbose output
- `--quiet, -q`: Quiet mode (errors only)
- `--version`: Show version information

## 📊 SEO Metrics & Scoring

### Content Guidelines
- **Title Length**: 30-60 characters (optimal)
- **Meta Description**: 120-160 characters
- **Minimum Content**: 300 words
- **Keyword Density**: Maximum 3%
- **Readability**: Flesch score ≥ 60, Gunning Fog ≤ 12

### Technical Requirements
- **Page Load Time**: < 3 seconds
- **Mobile-Friendly**: Responsive design required
- **HTTPS**: SSL certificate required
- **Structured Data**: Valid schema.org markup

## 🔍 Use Cases

### 1. Complete Site Audit
```bash
tfq0seo crawl https://yoursite.com --depth 5 --max-pages 1000 --format html --comprehensive
```

### 2. Competitive Analysis
```bash
tfq0seo analyze https://yoursite.com --competitors "https://competitor1.com,https://competitor2.com" --comprehensive
```

### 3. Batch URL Analysis
```bash
# Create urls.txt with one URL per line
tfq0seo batch urls.txt --format xlsx --output batch_analysis.xlsx
```

### 4. Technical SEO Audit
```bash
tfq0seo analyze https://yoursite.com --depth complete --format html --output technical_audit.html
```

### 5. Sitemap Analysis
```bash
tfq0seo sitemap https://yoursite.com/sitemap.xml --analyze --format html
```
