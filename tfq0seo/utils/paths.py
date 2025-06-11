"""Path definitions for tfq0seo."""

from pathlib import Path

# Get user's home directory and create tfq0seo directory
TFQSEO_HOME = Path.home() / '.tfq0seo'
TFQSEO_HOME.mkdir(exist_ok=True) 