from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="tfq0seo",
    version="1.0.1",
    author="tfq0",
    description="Modern SEO analysis and optimization toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tfq0/tfq0seo",
    project_urls={
        "Bug Tracker": "https://github.com/tfq0/tfq0seo/issues",
        "Documentation": "https://github.com/tfq0/tfq0seo/wiki",
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
    ],
    keywords="seo, analysis, optimization, web, content, meta tags, technical seo",
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "tfq0seo=src.cli:main",
        ],
    },
    include_package_data=True,
) 