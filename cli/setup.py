"""
Solvigo CLI - Internal tool for managing client projects on GCP
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="solvigo-cli",
    version="0.1.0",
    author="Solvigo Team",
    author_email="tech@solvigo.ai",
    description="CLI tool for managing Solvigo client projects on GCP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/solvigo/platform",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.7.0",
        "questionary>=2.0.0",
        "google-cloud-resource-manager>=1.12.0",
        "google-cloud-run>=0.10.0",
        "cloud-sql-python-connector>=1.18.5",
        "google-cloud-storage>=2.14.0",
        "google-cloud-secret-manager>=2.18.0",
        "pyyaml>=6.0",
        "jinja2>=3.1.0",
        "cookiecutter>=2.5.0",
    ],
    entry_points={
        "console_scripts": [
            "solvigo=solvigo.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "solvigo": [
            "templates/**/*",
            "terraform_templates/**/*",
            "terraform_templates/**/*.tf",
            "terraform_templates/**/*.md",
        ],
    },
)
