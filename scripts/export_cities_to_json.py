#!/usr/bin/env python3
"""
Export Cities to cities.json Script
Exports all city data from database to cities.json file
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import Flask app and models
from app import app, db, City

def export_cities_to_json():
    """Export all city data from database to cities.json"""
    
    print("🏙️ Exporting cities from database to cities.json...")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Get all cities from database
            cities = City.query.order_by(City.name).all()
            
            print(f"📊 Found {len(cities)} cities in database")
            print("=" * 60)
            
            # Create the JSON structure
            cities_data = {}
            
            for i, city in enumerate(cities, 1):
                city_data = {
                    "name": city.name,
                    "state": city.state,
                    "country": city.country,
                    "timezone": city.timezone,
                    "latitude": city.latitude,
                    "longitude": city.longitude,
                    "created_at": city.created_at.isoformat() if city.created_at else None,
                    "updated_at": city.updated_at.isoformat() if city.updated_at else None
                }
                
                # Use city ID as key (convert to string for JSON compatibility)
                cities_data[str(city.id)] = city_data
                
                print(f"  [{i}/{len(cities)}] {city.name}, {city.state}, {city.country}")
            
            # Create the final JSON structure
            final_data = {
                "metadata": {
                    "total_cities": len(cities),
                    "export_date": datetime.utcnow().isoformat(),
                    "description": "Cities exported from database"
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
            print(f"\n💾 Saving cities to cities.json...")
            with open(cities_file, 'w') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            print("✅ Cities exported successfully!")
            print(f"   File: {cities_file.absolute()}")
            print(f"   Total cities: {len(cities)}")
            
            # Show sample cities
            print(f"\n📋 Sample cities exported:")
            print("-" * 50)
            sample_cities = list(cities_data.items())[:5]
            for city_id, city_info in sample_cities:
                print(f"  {city_id}: {city_info['name']}, {city_info['state']}, {city_info['country']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error exporting cities: {e}")
            return False

if __name__ == "__main__":
    success = export_cities_to_json()
    if not success:
        sys.exit(1)