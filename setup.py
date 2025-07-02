from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tfq0seo",
    version="2.1.0",
    author="tfq0",
    author_email="tfq0@example.com",
    description="Professional SEO Analysis Toolkit - Open source alternative to Screaming Frog",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tfq0/tfq0seo",
    packages=find_packages(),
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
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
        "requests>=2.28.0",
        "rich>=12.6.0",
        "click>=8.1.0",
        "pandas>=1.5.0",
        "openpyxl>=3.0.0",
        "jinja2>=3.1.0",
        "validators>=0.20.0",
        "urllib3>=1.26.0",
        "aiofiles>=23.0.0",
        "textstat>=0.7.3",
        "jsonschema>=4.17.0",
        "httpx>=0.24.0",
        "user-agents>=2.2.0",
    ],
    entry_points={
        "console_scripts": [
            "tfq0seo=tfq0seo.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        'tfq0seo': ['templates/*.html', 'templates/*.css'],
    },
) 