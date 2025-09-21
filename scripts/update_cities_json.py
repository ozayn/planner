#!/usr/bin/env python3
"""
Update cities.json from database
Automatically called when cities are added through admin interface
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import Flask app and models
from app import app, db, City

def update_cities_json():
    """Export cities from database to cities.json file"""
    print("🔄 Updating cities.json from database...")
    
    with app.app_context():
        try:
            # Get all cities from database
            cities = City.query.order_by(City.id).all()
            
            print(f"📊 Found {len(cities)} cities in database")
            
            # Create the JSON structure (matches cities.json format)
            cities_data = {}
            
            for city in cities:
                city_data = {
                    "name": city.name,
                    "state": city.state or "",
                    "country": city.country,
                    "timezone": city.timezone or "UTC"
                }
                
                # Use city ID as key (convert to string for JSON compatibility)
                cities_data[str(city.id)] = city_data
                print(f"  Added: {city.name} (ID: {city.id})")
            
            # Create the final JSON structure with metadata
            final_data = {
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "description": "Cities exported from database - always most updated version",
                    "total_cities": len(cities),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "cities": cities_data
            }
            
            # Create backup of existing cities.json if it exists
            cities_file = Path("data/cities.json")
            if cities_file.exists():
                backup_file = f"data/backups/cities.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Create backup
                import shutil
                shutil.copy2(cities_file, backup_file)
                print(f"📦 Created backup: {backup_file}")
            
            # Write the new cities.json
            with open(cities_file, 'w') as f:
                json.dump(final_data, f, indent=2)
            
            print(f"✅ Successfully updated cities.json with {len(cities)} cities")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cities.json: {e}")
            return False

if __name__ == "__main__":
    update_cities_json()






