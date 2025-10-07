"""Setup configuration for tfq0seo package."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tfq0seo",
    version="2.3.0",
    author="TFQ0 SEO Team",
    description="Fast SEO analysis tool with reports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tfq0seo/tfq0seo",
    packages=find_packages(),
    package_data={
        "tfq0seo": ["templates/*.html"],
    },
    install_requires=[
        "aiohttp>=3.8.0",
        "beautifulsoup4>=4.11.0",
        "click>=8.1.0",
        "jinja2>=3.1.0",
        "rich>=12.6.0",
        "textstat>=0.7.3",
        "validators>=0.20.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8.0",
        "urllib3>=1.26.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "full": ["lxml>=4.9.0", "openpyxl>=3.0.0", "pandas>=1.5.0"],
    },
    entry_points={
        "console_scripts": ["tfq0seo=tfq0seo.cli:main"],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
