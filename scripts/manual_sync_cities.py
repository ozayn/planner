#!/usr/bin/env python3
"""
Manual sync script to update cities.json with all cities from database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, sync_cities_to_predefined_json

if __name__ == "__main__":
    print("🔄 Manually syncing cities from database to cities.json...")
    
    with app.app_context():
        success = sync_cities_to_predefined_json()
    
    if success:
        print("✅ Manual sync completed successfully!")
    else:
        print("❌ Manual sync failed!")
        sys.exit(1)
