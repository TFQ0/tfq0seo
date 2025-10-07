# TFQ0SEO - Fast SEO Analysis Tool

A high-performance SEO analysis tool that generates professional reports comparable to Google Lighthouse in quality and presentation.

## Features

- ⚡ **2-3x faster** than traditional SEO tools
- 📊 **Lighthouse-quality HTML reports** with interactive visualizations
- 🔍 **Comprehensive analysis** covering SEO, content, technical, performance, and links
- 🚀 **Handles 500+ pages** with minimal memory usage (<500MB)
- 📈 **Multiple export formats**: JSON, CSV, XLSX, HTML
- 🎨 **Beautiful reports** with score gauges, color-coded issues, and actionable recommendations
- ⚙️ **Concurrent processing** support (10-50 requests)
- 🔧 **Simple CLI** with rich progress display

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
tfq0seo crawl https://example.com --depth 5 --max-pages 500 --format html --output report.html
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
   - Meta tags (title, description, keywords)
   - Open Graph tags
   - Structured data (JSON-LD, microdata)
   - Canonical URLs
   - Robots directives

2. **Content Quality**
   - Readability scores
   - Word count
   - Heading structure
   - Keyword density
   - Content uniqueness

3. **Technical SEO**
   - HTTPS status
   - Mobile-friendliness
   - Security headers
   - Compression
   - Response codes

4. **Performance**
   - Page load time
   - Resource optimization
   - Core Web Vitals estimates
   - Resource counts

5. **Link Analysis**
   - Internal/external links
   - Broken link detection
   - Anchor text quality
   - Link distribution

## Report Features

- Interactive score gauges with color coding
- Expandable issue cards with severity levels
- Actionable recommendations with implementation steps
- Search and filter functionality
- Print-friendly design
- Dark mode support

## Configuration

Create a `config.yaml` file:

```yaml
crawler:
  max_concurrent: 20
  timeout: 30
  user_agent: "tfq0seo/2.3.0"
  follow_redirects: true
  max_redirects: 5

analysis:
  check_external_links: true
  check_images: true
  min_content_length: 100
  
export:
  html_template: "default"
  include_raw_data: false
```

## Performance

- Single page analysis: <2 seconds
- 100 pages crawl: <2 minutes (with 10 concurrent)
- 500 pages crawl: <8 minutes
- Memory usage: <500MB for 500 pages
- Report generation: <1 second

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/

# Run benchmarks
python -m tfq0seo.benchmark
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please visit our [GitHub repository](https://github.com/tfq0seo/tfq0seo).