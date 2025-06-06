# tfq0seo 🔍

[![PyPI version](https://badge.fury.io/py/tfq0seo.svg)](https://badge.fury.io/py/tfq0seo)
[![Python Versions](https://img.shields.io/pypi/pyversions/tfq0seo.svg)](https://pypi.org/project/tfq0seo/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://pepy.tech/badge/tfq0seo)](https://pepy.tech/project/tfq0seo)

A modern, comprehensive SEO analysis and optimization toolkit that helps you improve your website's search engine visibility and performance. 🚀

## ✨ Features

- 🌐 **URL Analysis**: Complete SEO audit of web pages
- 📝 **Content Analysis**: Text content optimization and recommendations
- 📱 **Mobile-Friendly Check**: Ensure your site works well on all devices
- 🏃 **Performance Metrics**: Speed and performance analysis
- 🔒 **Security Analysis**: Check for common security issues
- 📚 **Educational Resources**: Built-in SEO learning materials
- 💾 **Multiple Export Formats**: JSON, HTML, and Markdown support
- ⚡ **Caching Support**: For improved performance

## 🛠️ Installation

```bash
pip install tfq0seo
```

## 🚀 Quick Start

### Analyze a URL

```bash
tfq0seo analyze-url https://example.com --keyword "your target keyword"
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

## 📊 Output Formats

Choose your preferred output format with the `--format` flag:

```bash
tfq0seo analyze-url https://example.com --format json
tfq0seo analyze-url https://example.com --format html
tfq0seo analyze-url https://example.com --format markdown  # default
```

## 🔧 Configuration

Create a `seo_config.yaml` file to customize the analysis:

```yaml
cache:
  enabled: true
  directory: ".cache"
  expiration: 3600  # seconds

analysis:
  meta_tags:
    title_length: [30, 60]
    description_length: [120, 160]
  
  content:
    min_word_count: 300
    keyword_density: [1, 3]  # percentage
```

## 📋 Analysis Areas

### Meta Analysis
- Title tag optimization
- Meta description validation
- Robots directives
- Open Graph tags
- Twitter Cards

### Content Analysis
- Keyword optimization
- Content structure
- Readability metrics
- Internal linking
- Image optimization

### Modern SEO Features
- Mobile responsiveness
- Page speed insights
- Core Web Vitals
- Security headers
- Schema markup

## 🎯 Scoring System

The tool provides a comprehensive SEO score (0-100) based on:
- Technical SEO implementation (30%)
- Content optimization (40%)
- User experience factors (30%)

## 💻 API Usage

```python
from tfq0seo import SEOAnalyzerApp

# Initialize the analyzer
analyzer = SEOAnalyzerApp()

# Analyze a URL
results = analyzer.analyze_url(
    url="https://example.com",
    target_keyword="example keyword"
)

# Analyze content
content_results = analyzer.analyze_content(
    content="Your content here",
    target_keyword="example keyword"
)

# Get educational resources
resources = analyzer.get_educational_resources(topic="meta_tags")
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with modern Python best practices
- Inspired by the SEO community
- Powered by various open-source tools and libraries

## 📬 Contact

- GitHub: [Your GitHub Profile](https://github.com/TFQ0)

---

Made with ❤️ by [TFQ0] 