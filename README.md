# TFQ0SEO - Fast SEO Analysis Tool

![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)

A high-performance SEO analysis tool that generates professional reports comparable to  in quality and presentation.

## Features

- **Comprehensive analysis** covering SEO, content, technical, performance, and links
- **Handles 500+ pages** 
- **Beautiful reports** with score gauges, color-coded issues, and actionable recommendations
- **Concurrent processing** support (20 requests)
- **Simple CLI** with rich progress display

## Installation

```bash
pip install tfq0seo
```

For full features including Excel export:
```bash
pip install tfq0seo[full]
```

## Quick Start

### Single Page Analysis
```bash
tfq0seo analyze https://example.com
```

### Full Site Crawl
```bash
tfq0seo crawl https://example.com --depth 5 --max-pages 500 --concurrent 20 --format html --output full-report.html
```

### Batch Analysis
```bash
tfq0seo batch urls.txt --concurrent 10
```

### Sitemap Analysis
```bash
tfq0seo sitemap https://example.com/sitemap.xml --format html
```

## Analysis Categories

1. **SEO Analysis**

2. **Content Quality**

3. **Technical SEO**

4. **Performance**

5. **Link Analysis**
