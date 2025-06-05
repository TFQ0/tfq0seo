# SEO Analyzer Tool

A comprehensive SEO analysis tool that helps you analyze websites and content while learning SEO best practices. This tool provides detailed insights into various SEO aspects and teaches you the principles behind each recommendation.

## Features

### URL Analysis
- Meta tags evaluation
  - Title and description optimization
  - Open Graph and Twitter Cards
  - Schema.org markup validation
- HTML structure analysis
  - Heading hierarchy
  - Content structure
  - Internal linking
- Mobile-friendliness checks
  - Viewport configuration
  - Touch element spacing
  - Font size validation
- Performance analysis
  - Resource optimization
  - Load time metrics
  - Compression checks
- Security assessment
  - HTTPS implementation
  - Security headers
  - Mixed content detection

### Content Analysis
- Keyword optimization
  - Density and distribution
  - Natural language processing
  - Semantic analysis
- Readability assessment
  - Multiple readability scores
  - Sentence structure analysis
  - Content complexity metrics
- Content quality checks
  - Duplicate content detection
  - Grammar and style analysis
  - Transition word usage
- Structure evaluation
  - Paragraph length
  - Content sectioning
  - Formatting consistency

### Educational Components
- Detailed explanations for each recommendation
- Current SEO best practices
- Implementation guides
- Topic-specific resources
- Interactive learning elements

## Installation

### Using pip
```bash
pip install seo-analyzer
```

### From source
1. Clone this repository
```bash
git clone https://github.com/yourusername/seo-analyzer.git
cd seo-analyzer
```

2. Install dependencies
```bash
pip install -e .
```

## Usage

### Command Line Interface

1. Analyze a URL:
```bash
seo-analyzer analyze-url https://example.com --keyword "target keyword" --format markdown
```

2. Analyze text content:
```bash
seo-analyzer analyze-content --file content.txt --keyword "target keyword"
# or
seo-analyzer analyze-content --text "Your content here" --keyword "target keyword"
```

3. Get educational resources:
```bash
seo-analyzer education --topic meta_tags
```

### Python API

```python
from seo_analyzer import SEOAnalyzerApp

# Initialize the analyzer
analyzer = SEOAnalyzerApp()

# Analyze a URL
analysis = analyzer.analyze_url('https://example.com', target_keyword='keyword')

# Analyze content
content_analysis = analyzer.analyze_content('Your content here', target_keyword='keyword')

# Get educational resources
resources = analyzer.get_educational_resources(topic='meta_tags')

# Export report
report = analyzer.export_report(analysis, format='markdown')
```

## Configuration

The tool can be configured using a YAML file. Default configuration is in `config/seo_config.yaml`:

```yaml
seo_thresholds:
  title_length:
    min: 30
    max: 60
  meta_description_length:
    min: 120
    max: 160
  content_length:
    min: 300
  sentence_length:
    max: 20
  keyword_density:
    max: 3.0

# ... more configuration options
```

## Analysis Report Sections

The tool provides a comprehensive report with these main sections:

1. **Strengths** ✅
   - What's working well
   - SEO best practices in place
   - Positive metrics

2. **Weaknesses** ⚠️
   - Areas needing improvement
   - Missing SEO elements
   - Performance issues

3. **Recommendations** 📝
   - Actionable improvement steps
   - Prioritized suggestions
   - Implementation guidance

4. **SEO Education** 📚
   - Explanations of SEO principles
   - Best practices
   - Learning resources

## Development

### Running Tests
```bash
pytest tests/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Requirements

- Python 3.7+
- Internet connection (for URL analysis)
- Required Python packages (see requirements.txt)

## License

MIT License - see LICENSE file for details 