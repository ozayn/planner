#!/usr/bin/env python3
"""
Comprehensive Data Management Script
Handles loading, updating, and syncing JSON data with database
Consolidates functionality from multiple obsolete scripts
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
from app import app, db, Venue, City, Source

def sanitize_json_file_for_backup(source_file, backup_file):
    """
    Create a sanitized backup of a JSON file, removing API keys and sensitive data
    
    Args:
        source_file: Path to source JSON file
        backup_file: Path to backup JSON file
    """
    try:
        # Read the source file
        with open(source_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Sanitize the data recursively
        sanitized_data = sanitize_data_recursive(data)
        
        # Write the sanitized backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ Error creating sanitized backup: {e}")
        # Fallback: just copy the file without sanitization
        import shutil
        shutil.copy2(source_file, backup_file)

def sanitize_data_recursive(data):
    """
    Recursively sanitize data by replacing API keys with placeholders
    
    Args:
        data: Data structure to sanitize (dict, list, or string)
    
    Returns:
        Sanitized data structure
    """
    if isinstance(data, dict):
        return {key: sanitize_data_recursive(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_data_recursive(item) for item in data]
    elif isinstance(data, str):
        # Replace Google Maps API keys with placeholders
        import re
        # Pattern to match Google Maps API keys in URLs
        api_key_pattern = r'key=AIza[a-zA-Z0-9_-]{35}'
        sanitized = re.sub(api_key_pattern, 'key=YOUR_GOOGLE_MAPS_API_KEY', data)
        return sanitized
    else:
        return data

def load_cities_from_json():
    """Load cities from cities.json into database"""
    print("🏙️ Loading cities from cities.json...")
    print("=" * 60)
    
    cities_file = Path("data/cities.json")
    if not cities_file.exists():
        print("❌ cities.json not found")
        return False
        
    with open(cities_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Found {data['metadata']['total_cities']} cities")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Clear existing cities
            print("🧹 Clearing existing cities...")
            City.query.delete()
            db.session.commit()
            print("✅ Existing cities cleared")
            
            total_cities_added = 0
            
            for city_id, city_data in data['cities'].items():
                city_name = city_data['name']
                print(f"  Adding city: {city_name}")
                
                # Create city object with correct ID
                city = City(
                    id=int(city_id),  # Use the JSON city ID
                    name=city_name,
                    state=city_data.get('state', ''),
                    country=city_data.get('country', ''),
                    timezone=city_data.get('timezone', ''),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Add to database
                db.session.add(city)
                total_cities_added += 1
                print(f"    ✅ Added to database (ID: {city_id})")
            
            # Commit all changes
            print(f"\n💾 Committing {total_cities_added} cities to database...")
            db.session.commit()
            print("✅ All cities committed successfully!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading cities: {e}")
            db.session.rollback()
            return False

def load_venues_from_json():
    """Load venues from venues.json into database"""
    print("\n🏛️ Loading venues from venues.json...")
    print("=" * 60)
    
    import json  # Import at function level
    
    venues_file = Path("data/venues.json")
    if not venues_file.exists():
        print("❌ venues.json not found")
        return False
        
    with open(venues_file, 'r') as f:
        data = json.load(f)
    
    # Get venues data (handle both old and new JSON structure)
    venues_data = data.get('venues', data)  # Try 'venues' key first, fallback to root
    
    # Count total venues
    total_venues = sum(len(city_data['venues']) for city_data in venues_data.values() if isinstance(city_data, dict) and 'venues' in city_data)
    total_cities = len([k for k, v in venues_data.items() if isinstance(v, dict) and 'venues' in v])
    
    print(f"📊 Found {total_venues} venues across {total_cities} cities")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Clear existing venues
            print("🧹 Clearing existing venues...")
            Venue.query.delete()
            db.session.commit()
            print("✅ Existing venues cleared")
            
            # Process each city
            total_venues_added = 0
            
            for city_id, city_data in venues_data.items():
                if not isinstance(city_data, dict) or 'venues' not in city_data:
                    continue
                    
                city_name = city_data['name']
                venues = city_data['venues']
                
                print(f"\n🏙️ Processing {city_name} ({len(venues)} venues)...")
                print("-" * 50)
                
                # Get city from database
                city = City.query.get(int(city_id))
                if not city:
                    print(f"      ⚠️  City '{city_name}' (ID: {city_id}) not found in database, skipping...")
                    continue
                
                for i, venue_data in enumerate(venues):
                    venue_name = venue_data['name']
                    print(f"  [{i+1}/{len(venues)}] Adding venue: {venue_name}")
                    
                    # Create venue object
                    # Handle image_url - convert photo data to JSON string for database storage
                    image_url_data = venue_data.get('image_url', '')
                    if isinstance(image_url_data, dict):
                        # Convert photo data to JSON string for database storage
                        image_url = json.dumps(image_url_data)
                    else:
                        # Keep as string if it's already a string
                        image_url = image_url_data
                    
                    venue = Venue(
                        name=venue_name,
                        venue_type=venue_data.get('venue_type', 'museum'),
                        description=venue_data.get('description', ''),
                        address=venue_data.get('address', ''),
                        opening_hours=venue_data.get('opening_hours', ''),
                        phone_number=venue_data.get('phone_number', ''),
                        email=venue_data.get('email', ''),
                        tour_info=venue_data.get('tour_info', ''),
                        admission_fee=venue_data.get('admission_fee', ''),
                        website_url=venue_data.get('website_url', ''),
                        image_url=image_url,
                        latitude=venue_data.get('latitude'),
                        longitude=venue_data.get('longitude'),
                        facebook_url=venue_data.get('facebook_url', ''),
                        instagram_url=venue_data.get('instagram_url', ''),
                        twitter_url=venue_data.get('twitter_url', ''),
                        youtube_url=venue_data.get('youtube_url', ''),
                        tiktok_url=venue_data.get('tiktok_url', ''),
                        holiday_hours=venue_data.get('holiday_hours', ''),
                        additional_info=venue_data.get('additional_info', ''),
                        city_id=int(city_id),  # Use the correct city ID
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Add to database
                    db.session.add(venue)
                    total_venues_added += 1
                    print(f"      ✅ Added to database (city_id: {city_id})")
            
            # Commit all changes
            print(f"\n💾 Committing {total_venues_added} venues to database...")
            db.session.commit()
            print("✅ All venues committed successfully!")
            
            # Verify the data
            print(f"\n🔍 Verifying data...")
            venue_count = Venue.query.count()
            city_count = City.query.count()
            print(f"   Total cities in database: {city_count}")
            print(f"   Total venues in database: {venue_count}")
            
            if venue_count == total_venues_added:
                print("✅ Data verification successful!")
            else:
                print("⚠️ Data verification failed - count mismatch")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading venues: {e}")
            db.session.rollback()
            return False

def load_sources_from_json():
    """Load sources from sources.json into database"""
    print("\n📰 Loading sources from sources.json...")
    print("=" * 60)
    
    sources_file = Path("data/sources.json")
    if not sources_file.exists():
        print("❌ sources.json not found")
        return False
        
    with open(sources_file, 'r') as f:
        data = json.load(f)
    
    # Handle the new structure with 'sources' key
    if 'sources' in data:
        sources_data = data['sources']
        total_sources = len(sources_data)
        # Count unique cities
        city_ids = set(source.get('city_id') for source in sources_data.values() if source.get('city_id'))
        total_cities = len(city_ids)
    else:
        # Fallback to old structure (organized by cities)
        total_sources = sum(len(city_data['sources']) for city_data in data.values() if isinstance(city_data, dict) and 'sources' in city_data)
        total_cities = len([k for k, v in data.items() if isinstance(v, dict) and 'sources' in v])
    
    print(f"📊 Found {total_sources} sources across {total_cities} cities")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Clear existing sources
            print("🧹 Clearing existing sources...")
            Source.query.delete()
            db.session.commit()
            print("✅ Existing sources cleared")
            
            # Process sources
            total_sources_added = 0
            
            if 'sources' in data:
                # New structure: all sources in 'sources' key
                sources_data = data['sources']
                print(f"\n🏙️ Processing {len(sources_data)} sources...")
                print("-" * 50)
                
                for i, (source_id, source_data) in enumerate(sources_data.items()):
                    source_name = source_data['name']
                    city_id = source_data.get('city_id')
                    print(f"  [{i+1}/{len(sources_data)}] Adding source: {source_name}")
                    
                    # Get city from database
                    city = City.query.get(int(city_id)) if city_id else None
                    if not city:
                        print(f"      ⚠️  City ID {city_id} not found in database, skipping...")
                        continue
            else:
                # Old structure: organized by cities
                for city_id, city_data in data.items():
                    if not isinstance(city_data, dict) or 'sources' not in city_data:
                        continue
                        
                    city_name = city_data['name']
                    sources = city_data['sources']
                    
                    print(f"\n🏙️ Processing {city_name} ({len(sources)} sources)...")
                    print("-" * 50)
                    
                    # Get city from database
                    city = City.query.get(int(city_id))
                    if not city:
                        print(f"      ⚠️  City '{city_name}' (ID: {city_id}) not found in database, skipping...")
                        continue
                    
                    for i, source_data in enumerate(sources):
                        source_name = source_data['name']
                        print(f"  [{i+1}/{len(sources)}] Adding source: {source_name}")
                    
                    # Handle datetime fields properly
                    last_checked = source_data.get('last_checked')
                    if last_checked == '' or last_checked is None:
                        last_checked = None
                    
                    last_event_found = source_data.get('last_event_found')
                    if last_event_found == '' or last_event_found is None:
                        last_event_found = None
                    
                    # Handle list fields (convert to JSON string for SQLite)
                    event_types = source_data.get('event_types', [])
                    if isinstance(event_types, list):
                        event_types = json.dumps(event_types)
                    
                    covered_cities = source_data.get('covered_cities')
                    if isinstance(covered_cities, list):
                        covered_cities = json.dumps(covered_cities)
                    
                    # Create source object
                    source = Source(
                        name=source_name,
                        handle=source_data.get('handle', ''),
                        source_type=source_data.get('source_type', 'website'),
                        url=source_data.get('url', ''),
                        description=source_data.get('description', ''),
                        city_id=int(city_id),
                        covers_multiple_cities=source_data.get('covers_multiple_cities', False),
                        covered_cities=covered_cities,
                        event_types=event_types,
                        is_active=source_data.get('is_active', True),
                        last_checked=last_checked,
                        last_event_found=last_event_found,
                        events_found_count=source_data.get('events_found_count', 0),
                        reliability_score=source_data.get('reliability_score', 0.0),
                        posting_frequency=source_data.get('posting_frequency', ''),
                        notes=source_data.get('notes', ''),
                        scraping_pattern=source_data.get('scraping_pattern', ''),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Add to database
                    db.session.add(source)
                    total_sources_added += 1
                    print(f"      ✅ Added to database (city_id: {city_id})")
            
            # Commit all changes
            print(f"\n💾 Committing {total_sources_added} sources to database...")
            db.session.commit()
            print("✅ All sources committed successfully!")
            
            # Verify the data
            print(f"\n🔍 Verifying sources data...")
            source_count = Source.query.count()
            print(f"   Total sources in database: {source_count}")
            
            if source_count == total_sources_added:
                print("✅ Sources data verification successful!")
            else:
                print("⚠️ Sources data verification failed - count mismatch")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading sources: {e}")
            db.session.rollback()
            return False

def export_cities_to_json():
    """Export cities from database to cities.json"""
    print("\n📤 Exporting cities from database to cities.json...")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Get all cities from database
            cities = City.query.order_by(City.id).all()
            
            print(f"📊 Found {len(cities)} cities in database")
            print("=" * 60)
            
            # Create the JSON structure
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
                print(f"  Exported: {city.name} (ID: {city.id})")
            
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
                
                # Sanitize API keys before creating backup
                sanitize_json_file_for_backup(cities_file, backup_file)
                print(f"📦 Created sanitized backup: {backup_file}")
            
            # Write the new cities.json
            with open(cities_file, 'w') as f:
                json.dump(final_data, f, indent=2)
            
            print(f"✅ Successfully exported {len(cities)} cities to cities.json")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting cities: {e}")
            return False

def export_venues_to_json():
    """Export venues from database to venues.json"""
    print("\n📤 Exporting venues from database to venues.json...")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Get all venues from database with their cities
            venues = Venue.query.join(City).order_by(City.id, Venue.name).all()
            
            print(f"📊 Found {len(venues)} venues in database")
            print("=" * 60)
            
            # Create the JSON structure (same format as current venues.json)
            venues_data = {}
            
            # Group venues by city
            for venue in venues:
                city_id = str(venue.city_id)
                
                if city_id not in venues_data:
                    venues_data[city_id] = {
                        "name": venue.city.name,
                        "venues": []
                    }
                
                # Create venue entry
                venue_entry = {
                    "name": venue.name,
                    "venue_type": venue.venue_type or "museum",
                    "address": venue.address or "",
                    "opening_hours": venue.opening_hours or "",
                    "phone_number": venue.phone_number or "",
                    "email": venue.email or "",
                    "description": venue.description or "",
                    "tour_info": venue.tour_info or "",
                    "admission_fee": venue.admission_fee or "",
                    "website_url": venue.website_url or "",
                    "latitude": venue.latitude,
                    "longitude": venue.longitude,
                    "image_url": venue.image_url or "",
                    "instagram_url": venue.instagram_url or "",
                    "facebook_url": venue.facebook_url or "",
                    "twitter_url": venue.twitter_url or "",
                    "youtube_url": venue.youtube_url or "",
                    "tiktok_url": venue.tiktok_url or "",
                    "holiday_hours": venue.holiday_hours or "",
                    "additional_info": venue.additional_info or ""
                }
                
                venues_data[city_id]["venues"].append(venue_entry)
            
            # Create backup of existing venues.json if it exists
            venues_file = Path("data/venues.json")
            if venues_file.exists():
                backup_file = f"data/backups/venues.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Sanitize API keys before creating backup
                sanitize_json_file_for_backup(venues_file, backup_file)
                print(f"📦 Created sanitized backup: {backup_file}")
            
            # Write the new venues.json (sanitized)
            sanitized_venues_data = sanitize_data_recursive(venues_data)
            with open(venues_file, 'w') as f:
                json.dump(sanitized_venues_data, f, indent=2)
            
            print(f"✅ Successfully exported {len(venues)} venues to venues.json")
            print(f"   Cities with venues: {len(venues_data)}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting venues: {e}")
            return False

def load_all_data():
    """Load all data from JSON files into database"""
    print("🚀 Starting comprehensive data loading...")
    print("=" * 60)
    
    # Load cities first
    if not load_cities_from_json():
        return False
    
    # Then load venues
    if not load_venues_from_json():
        return False
    
    # Then load sources
    if not load_sources_from_json():
        return False
    
    print("\n🎉 All data loaded successfully!")
    return True

def sync_all_data():
    """Sync all data from database to JSON files"""
    print("🔄 Starting comprehensive data sync...")
    print("=" * 60)
    
    # Export cities
    if not export_cities_to_json():
        return False
    
    # Export venues
    if not export_venues_to_json():
        return False
    
    print("\n🎉 All data synced successfully!")
    return True

def main():
    """Main function with command line interface"""
    if len(sys.argv) < 2:
        print("Usage: python data_manager.py <command>")
        print("Commands:")
        print("  load        - Load all data from JSON files to database")
        print("  sync        - Sync all data from database to JSON files")
        print("  load-cities - Load only cities from JSON to database")
        print("  load-venues - Load only venues from JSON to database")
        print("  load-sources - Load only sources from JSON to database")
        print("  export-cities - Export only cities from database to JSON")
        print("  export-venues - Export only venues from database to JSON")
        return
    
    command = sys.argv[1].lower()
    
    if command == "load":
        success = load_all_data()
    elif command == "sync":
        success = sync_all_data()
    elif command == "load-cities":
        success = load_cities_from_json()
    elif command == "load-venues":
        success = load_venues_from_json()
    elif command == "load-sources":
        success = load_sources_from_json()
    elif command == "export-cities":
        success = export_cities_to_json()
    elif command == "export-venues":
        success = export_venues_to_json()
    else:
        print(f"❌ Unknown command: {command}")
        return
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
