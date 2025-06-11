from setuptools import setup, find_packages
import os
from pathlib import Path

# Get the directory containing setup.py
here = Path(__file__).parent.resolve()

# Read the README file
try:
    long_description = (here / "README.md").read_text(encoding="utf-8")
except FileNotFoundError:
    long_description = "Modern SEO analysis and optimization toolkit with advanced reporting"

# Read requirements
try:
    requirements = [
        line.strip()
        for line in (here / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
except FileNotFoundError:
    requirements = [
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.2",
        "nltk>=3.8.1",
        "readability>=0.3.1",
        "certifi>=2024.2.2",
        "textblob>=0.17.1",
        "pyyaml>=6.0.1",
        "html5lib>=1.1",
        "lxml>=4.9.3",
        "colorama>=0.4.6",
        "rich>=13.7.0",
        "click>=8.1.7",
        "pytest>=8.0.0",
        "setuptools>=69.0.3"
    ]

setup(
    name="tfq0seo",
    version="1.0.6",
    author="tfq0",
    description="Modern SEO analysis and optimization toolkit with advanced reporting",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tfq0/tfq0seo",
    project_urls={
        "Bug Tracker": "https://github.com/tfq0/tfq0seo/issues",
        "Source Code": "https://github.com/tfq0/tfq0seo",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Internet :: WWW/HTTP :: Site Management :: Link Checking",
        "Topic :: Text Processing :: Markup :: HTML",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Environment :: Console",
        "Operating System :: OS Independent",
    ],
    keywords="seo, analysis, optimization, web, content, meta tags, technical seo, reporting, analytics",
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "tfq0seo=tfq0seo.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "tfq0seo": [
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
        ],
    },
) 