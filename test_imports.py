#!/usr/bin/env python3
"""
Test script to identify import issues
"""

import sys
import os

print("Testing imports step by step...")

try:
    print("1. Testing basic imports...")
    from flask import Flask
    print("   ✅ Flask imported successfully")
except Exception as e:
    print(f"   ❌ Flask import failed: {e}")
    sys.exit(1)

try:
    print("2. Testing environment config...")
    from scripts.env_config import ensure_env_loaded, get_app_config
    print("   ✅ env_config imported successfully")
except Exception as e:
    print(f"   ❌ env_config import failed: {e}")
    sys.exit(1)

try:
    print("3. Testing utils cleaning functions...")
    from scripts.utils import clean_text_field, clean_url_field
    print("   ✅ utils cleaning functions imported successfully")
except Exception as e:
    print(f"   ❌ utils cleaning functions import failed: {e}")
    sys.exit(1)

try:
    print("4. Testing Flask app creation...")
    from flask import Flask
    app = Flask(__name__)
    print("   ✅ Flask app created successfully")
except Exception as e:
    print(f"   ❌ Flask app creation failed: {e}")
    sys.exit(1)

print("✅ All basic imports successful!")

