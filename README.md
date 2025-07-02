# tfq0seo - Professional SEO Analysis Toolkit

![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)

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

## 📦 Installation

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
```

### Export Results

```bash
# Export to different formats
tfq0seo export --format csv --output results.csv
tfq0seo export --format xlsx --output report.xlsx
tfq0seo export --format html --output report.html
```

## 🔧 Configuration Options

### Crawl Command Options
- `--depth`: Crawl depth (1-10, default: 3)
- `--max-pages`: Maximum pages to crawl (default: 500)
- `--concurrent`: Concurrent requests (1-50, default: 10)
- `--delay`: Delay between requests in seconds (default: 0.5)
- `--format`: Output format (json|csv|xlsx|html)
- `--exclude`: Path patterns to exclude
- `--no-robots`: Ignore robots.txt
- `--include-external`: Include external links

### Analysis Options
- `--comprehensive`: Run all analysis modules
- `--target-keyword`: Primary keyword for optimization
- `--competitors`: Competitor URLs for comparison
- `--depth`: Analysis depth (basic|advanced|complete)

## 📊 SEO Metrics & Thresholds

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
tfq0seo crawl https://yoursite.com --depth 5 --max-pages 1000 --format html
```

### 2. Competitive Analysis
```bash
tfq0seo analyze https://yoursite.com --competitors "https://competitor1.com,https://competitor2.com" --comprehensive
```

### 3. Content Optimization
```bash
tfq0seo analyze-content --file blog-post.txt --keyword "target keyword"
```

### 4. Technical SEO Check
```bash
tfq0seo analyze https://yoursite.com --depth complete --format json
```

## 💻 Development

### Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

### License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

- **GitHub**: [https://github.com/tfq0/tfq0seo](https://github.com/tfq0/tfq0seo)
- **Issues**: Report bugs or request features
- **Author**: tfq0

## 🎉 Acknowledgments

Built with ❤️ by tfq0 as an open-source alternative to commercial SEO tools. 