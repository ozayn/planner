#!/usr/bin/env python3
"""
Export Cities from Database to Predefined JSON
Updates the predefined_cities.json file with current database cities
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def export_cities_to_json():
    """Export all cities from database to predefined_cities.json"""
    try:
        from app import app, db, City
        
        with app.app_context():
            # Get all cities from database
            cities = City.query.all()
            
            if not cities:
                print("❌ No cities found in database")
                return False
            
            # Prepare cities data
            cities_data = {}
            for city in cities:
                cities_data[str(city.id)] = {
                    "name": city.name,
                    "state": city.state,
                    "country": city.country,
                    "timezone": city.timezone
                }
            
            # Prepare metadata
            metadata = {
                "version": "1.2",
                "created": "2025-09-10",
                "description": "Predefined cities database for event planner - core data only",
                "total_cities": len(cities),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "exported_from": "database"
            }
            
            # Prepare final JSON structure
            json_data = {
                "metadata": metadata,
                "cities": cities_data
            }
            
            # Write to predefined_cities.json
            json_file = Path("data/predefined_cities.json")
            json_file.parent.mkdir(exist_ok=True)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Successfully exported {len(cities)} cities to predefined_cities.json")
            print(f"   File: {json_file.absolute()}")
            print(f"   Last updated: {metadata['last_updated']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error exporting cities: {e}")
        return False

def sync_new_cities_to_json():
    """Sync only new cities (not in predefined JSON) to the file"""
    try:
        from app import app, db, City
        
        # Load existing predefined cities
        json_file = Path("data/predefined_cities.json")
        if not json_file.exists():
            print("❌ predefined_cities.json not found")
            return False
        
        with open(json_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        existing_cities = existing_data.get('cities', {})
        existing_names = {city_data['name'].lower(): city_data for city_data in existing_cities.values()}
        
        with app.app_context():
            # Get all cities from database
            db_cities = City.query.all()
            
            new_cities = []
            updated_cities = []
            
            for city in db_cities:
                city_key = city.name.lower()
                
                if city_key not in existing_names:
                    # New city
                    new_cities.append(city)
                else:
                    # Check if city data has changed
                    existing_city = existing_names[city_key]
                    if (existing_city.get('state') != city.state or 
                        existing_city.get('country') != city.country or 
                        existing_city.get('timezone') != city.timezone):
                        updated_cities.append(city)
            
            if not new_cities and not updated_cities:
                print("✅ No new or updated cities found")
                return True
            
            # Add new cities to existing data
            next_id = max([int(k) for k in existing_cities.keys()], default=0) + 1
            
            for city in new_cities:
                existing_cities[str(next_id)] = {
                    "name": city.name,
                    "state": city.state,
                    "country": city.country,
                    "timezone": city.timezone
                }
                next_id += 1
            
            # Update existing cities
            for city in updated_cities:
                # Find the city in existing data
                for city_id, city_data in existing_cities.items():
                    if city_data['name'].lower() == city.name.lower():
                        existing_cities[city_id] = {
                            "name": city.name,
                            "state": city.state,
                            "country": city.country,
                            "timezone": city.timezone
                        }
                        break
            
            # Update metadata
            existing_data['metadata']['version'] = "1.2"
            existing_data['metadata']['total_cities'] = len(existing_cities)
            existing_data['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            existing_data['metadata']['new_cities_added'] = len(new_cities)
            existing_data['metadata']['cities_updated'] = len(updated_cities)
            
            # Write updated data
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Successfully synced cities to predefined_cities.json")
            print(f"   New cities added: {len(new_cities)}")
            print(f"   Cities updated: {len(updated_cities)}")
            print(f"   Total cities: {len(existing_cities)}")
            
            if new_cities:
                print("   New cities:")
                for city in new_cities:
                    print(f"     - {city.name}, {city.country}")
            
            if updated_cities:
                print("   Updated cities:")
                for city in updated_cities:
                    print(f"     - {city.name}, {city.country}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error syncing cities: {e}")
        return False

def get_city_sync_status():
    """Check sync status between database and predefined JSON"""
    try:
        from app import app, db, City
        
        # Load existing predefined cities
        json_file = Path("data/predefined_cities.json")
        if not json_file.exists():
            print("❌ predefined_cities.json not found")
            return False
        
        with open(json_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        existing_cities = existing_data.get('cities', {})
        existing_names = {city_data['name'].lower(): city_data for city_data in existing_cities.values()}
        
        with app.app_context():
            # Get all cities from database
            db_cities = City.query.all()
            
            db_names = {city.name.lower() for city in db_cities}
            json_names = set(existing_names.keys())
            
            new_in_db = db_names - json_names
            new_in_json = json_names - db_names
            
            print(f"📊 City Sync Status:")
            print(f"   Database cities: {len(db_cities)}")
            print(f"   JSON cities: {len(existing_cities)}")
            print(f"   New in database: {len(new_in_db)}")
            print(f"   New in JSON: {len(new_in_json)}")
            
            if new_in_db:
                print("   Cities in database but not in JSON:")
                for name in new_in_db:
                    city = next(c for c in db_cities if c.name.lower() == name)
                    print(f"     - {city.name}, {city.country}")
            
            if new_in_json:
                print("   Cities in JSON but not in database:")
                for name in new_in_json:
                    city_data = existing_names[name]
                    print(f"     - {city_data['name']}, {city_data['country']}")
            
            return len(new_in_db) > 0 or len(new_in_json) > 0
            
    except Exception as e:
        print(f"❌ Error checking sync status: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export cities from database to predefined JSON")
    parser.add_argument("--sync", action="store_true", help="Sync only new cities")
    parser.add_argument("--status", action="store_true", help="Check sync status")
    parser.add_argument("--export", action="store_true", help="Export all cities (default)")
    
    args = parser.parse_args()
    
    if args.sync:
        success = sync_new_cities_to_json()
    elif args.status:
        success = get_city_sync_status()
    else:
        success = export_cities_to_json()
    
    sys.exit(0 if success else 1)

