#!/usr/bin/env python3
"""
Update cities.json with current database cities
This function will be imported and used in app.py
"""

import json
import os
from pathlib import Path
from datetime import datetime

def update_cities_json():
    """Update cities.json with current database cities"""
    try:
        from app import app, City
        
        with app.app_context():
            # Get all cities from database
            cities = City.query.order_by(City.name).all()
            
            # Create the JSON structure (same as predefined_cities.json)
            cities_data = {}
            
            for city in cities:
                city_data = {
                    "name": city.name,
                    "state": city.state,
                    "country": city.country,
                    "timezone": city.timezone
                }
                
                # Use city ID as key (convert to string for JSON compatibility)
                cities_data[str(city.id)] = city_data
            
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
                os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                
                import shutil
                shutil.copy2(cities_file, backup_file)
                print(f"📋 Backup created: {backup_file}")
            
            # Save to cities.json
            with open(cities_file, 'w') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Cities.json updated successfully!")
            print(f"   Total cities: {len(cities)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating cities.json: {e}")
        return False

if __name__ == "__main__":
    success = update_cities_json()
    if not success:
        exit(1)
