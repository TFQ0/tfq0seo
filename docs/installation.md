# Installation Guide

This guide will help you install and set up TFQ0SEO on your system.

## System Requirements

- Python 3.9 or higher
- 2GB RAM minimum (4GB recommended)
- 1GB free disk space
- Operating Systems:
  - Linux (Ubuntu 20.04+, CentOS 8+)
  - macOS (10.15+)
  - Windows 10/11

## Installation Methods

### Method 1: Using pip (Recommended)

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install tfq0seo
pip install tfq0seo
```

### Method 2: From Source

```bash
# Clone the repository
git clone https://github.com/tfq66/tfq0seo.git
cd tfq0seo

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Method 3: Using Docker

```bash
# Pull the Docker image
docker pull tfq66/tfq0seo:latest

# Run the container
docker run -d -p 8000:8000 tfq66/tfq0seo:latest
```

## Dependencies

Core dependencies are automatically installed with the package:

```
aiohttp>=3.9.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
httpx>=0.24.0
pydantic>=2.0.0
```

Optional dependencies for additional features:

```bash
# Install all optional dependencies
pip install tfq0seo[all]

# Install specific feature sets
pip install tfq0seo[pdf]      # PDF export support
pip install tfq0seo[nlp]      # Natural language processing
pip install tfq0seo[monitor]  # Monitoring tools
```

## Post-Installation Setup

1. Create configuration file:
```bash
tfq0seo init
```

2. Configure settings in `config.yaml`:
```yaml
api:
  port: 8000
  host: "0.0.0.0"
  workers: 4

security:
  rate_limit: 100
  token_expiry: 3600
  allowed_origins: ["*"]

cache:
  enabled: true
  max_size: 1000
  ttl: 3600

logging:
  level: "INFO"
  file: "tfq0seo.log"
```

3. Initialize the database:
```bash
tfq0seo db init
```

4. Verify installation:
```bash
tfq0seo --version
tfq0seo check
```

## Environment Variables

Configure these environment variables if needed:

```bash
# API Configuration
export TFQ0SEO_API_KEY="your-api-key"
export TFQ0SEO_HOST="0.0.0.0"
export TFQ0SEO_PORT="8000"

# Security
export TFQ0SEO_SECRET_KEY="your-secret-key"
export TFQ0SEO_ALLOWED_ORIGINS="domain1.com,domain2.com"

# Performance
export TFQ0SEO_WORKERS="4"
export TFQ0SEO_MAX_CONNECTIONS="100"
export TFQ0SEO_TIMEOUT="30"

# Logging
export TFQ0SEO_LOG_LEVEL="INFO"
export TFQ0SEO_LOG_FILE="/var/log/tfq0seo.log"
```

## Troubleshooting

### Common Issues

1. **Installation fails with dependency conflicts**
   ```bash
   pip install --no-deps tfq0seo
   pip install -r <(tfq0seo deps)
   ```

2. **Port already in use**
   ```bash
   # Change port in config.yaml or use environment variable
   export TFQ0SEO_PORT="8001"
   ```

3. **Memory issues**
   ```bash
   # Adjust memory limits in config.yaml
   memory:
     max_mb: 2048
     gc_threshold: 0.8
   ```

### Verification

Run the test suite to verify installation:

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Run tests
pytest

# Run specific test categories
pytest -m integration
pytest -m benchmark
```

## Next Steps

- Read the [Quick Start Guide](./quickstart.md)
- Configure [Security Settings](./technical/security.md)
- Set up [Monitoring](./technical/monitoring.md)
- Check [Best Practices](./user_guides/best_practices.md) 