# tfq0seo 🔍

[![PyPI version](https://badge.fury.io/py/tfq0seo.svg)](https://badge.fury.io/py/tfq0seo)
[![Python Versions](https://img.shields.io/pypi/pyversions/tfq0seo.svg)](https://pypi.org/project/tfq0seo/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, comprehensive SEO analysis and optimization toolkit that helps you improve your website's search engine visibility and performance. 🚀

## ✨ Features

- 🌐 **URL Analysis**: Complete SEO audit of web pages
- 📝 **Content Analysis**: Text content optimization and recommendations
- 📱 **Mobile-Friendly Check**: Ensure your site works well on all devices
- 🏃 **Performance Metrics**: Speed and performance analysis
- 💾 **Multiple Export Formats**: JSON, HTML, and Markdown support


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

### Content Analysis
- Keyword optimization
- Content structure
- Readability metrics

### Modern SEO Features
- Mobile responsiveness
- Page speed insights
- Schema markup




## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 📬 Contact

- GitHub: [Your GitHub Profile](https://github.com/TFQ0)

---

Made with ❤️ by [TFQ0] 