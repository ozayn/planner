#!/usr/bin/env python3
"""
Setup script for Event Planner App
A minimal, artistic web and mobile app for discovering events in cities worldwide.
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Event Planner App - A minimal, artistic web app for discovering events in cities worldwide."

# Read requirements from requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="event-planner",
    version="1.0.0",
    author="Ozayn",
    author_email="your-email@example.com",
    description="A minimal, artistic web and mobile app for discovering events in cities worldwide",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/ozayn/planner",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-flask>=1.2.0",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.910",
        ],
        "deploy": [
            "gunicorn>=20.0",
            "psycopg2-binary>=2.8.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "planner=app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json", "*.html", "*.css", "*.js"],
    },
    project_urls={
        "Bug Reports": "https://github.com/ozayn/planner/issues",
        "Source": "https://github.com/ozayn/planner",
        "Documentation": "https://github.com/ozayn/planner/blob/main/docs/README.md",
    },
    keywords="events, cities, venues, flask, web-app, minimal-design, pastel-ui",
)

