#!/usr/bin/env python3
"""
Smart Import Module
Automatically handles virtual environment activation for imports
"""

import sys
import os
from pathlib import Path

def setup_venv_path():
    """Setup virtual environment path if not already active"""
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return True  # Already in virtual environment
    
    # Find project root (where this script is located)
    project_root = Path(__file__).parent.parent
    venv_path = project_root / 'venv'
    
    if venv_path.exists():
        # Find the correct Python version site-packages
        lib_path = venv_path / 'lib'
        if lib_path.exists():
            # Look for python3.x directories
            for python_dir in lib_path.iterdir():
                if python_dir.is_dir() and python_dir.name.startswith('python'):
                    site_packages = python_dir / 'site-packages'
                    if site_packages.exists():
                        sys.path.insert(0, str(site_packages))
                        return True
    
    return False

def safe_import(module_name, fromlist=None):
    """Safely import a module with automatic venv setup"""
    try:
        if fromlist:
            return __import__(module_name, fromlist=fromlist)
        return __import__(module_name)
    except ImportError as e:
        # Try to setup venv and import again
        if setup_venv_path():
            try:
                if fromlist:
                    return __import__(module_name, fromlist=fromlist)
                return __import__(module_name)
            except ImportError:
                pass
        raise e

# Auto-setup on import
setup_venv_path()

# Common imports that often fail
try:
    dotenv = safe_import('dotenv')
    load_dotenv = dotenv.load_dotenv
except ImportError:
    load_dotenv = None

try:
    flask = safe_import('flask')
    Flask = flask.Flask
    render_template = flask.render_template
    request = flask.request
    jsonify = flask.jsonify
except ImportError:
    Flask = None
    render_template = None
    request = None
    jsonify = None

try:
    sqlalchemy = safe_import('flask_sqlalchemy')
    SQLAlchemy = sqlalchemy.SQLAlchemy
except ImportError:
    SQLAlchemy = None

