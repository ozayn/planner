#!/usr/bin/env python3
"""
Script to clear and reload cities and venues from predefined JSON files
"""

import sys
import os
import json
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue

def clear_all_tables():
    """Clear all cities and venues from the database"""
    print("🗑️  Clearing all tables...")
    
    with app.app_context():
        # Count before deletion
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        print(f"   Found {cities_count} cities and {venues_count} venues to delete")
        
        # Delete all venues first (due to foreign key constraints)
        if venues_count > 0:
            Venue.query.delete()
            print(f"   ✅ Deleted {venues_count} venues")
        
        # Delete all cities
        if cities_count > 0:
            City.query.delete()
            print(f"   ✅ Deleted {cities_count} cities")
        
        db.session.commit()
        print("   ✅ All tables cleared")

def reload_cities_from_json():
    """Reload cities from predefined_cities.json"""
    print("\n📥 Reloading cities from predefined_cities.json...")
    
    json_file = 'data/predefined_cities.json'
    
    if not os.path.exists(json_file):
        print(f"   ❌ Error: {json_file} not found")
        return False
    
    with open(json_file, 'r') as f:
        cities_data = json.load(f)
    
    print(f"   📊 JSON contains {len(cities_data['cities'])} cities")
    
    with app.app_context():
        loaded_count = 0
        skipped_count = 0
        
        for city_id, city_data in cities_data['cities'].items():
            try:
                # Create city object
                city = City(
                    name=city_data['name'],
                    state=city_data.get('state') or None,  # Convert empty string or null to None
                    country=city_data['country'],
                    timezone=city_data.get('timezone', '')
                )
                
                # Add to database
                db.session.add(city)
                loaded_count += 1
                
            except Exception as e:
                print(f"   ❌ Error loading city '{city_data.get('name', 'Unknown')}': {e}")
                skipped_count += 1
                continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n📊 Cities Reload Summary:")
        print(f"   ✅ Successfully loaded: {loaded_count} cities")
        print(f"   ⚠️  Skipped: {skipped_count} cities")
        
        return True

def reload_venues_from_json():
    """Reload venues from predefined_venues.json"""
    print("\n📥 Reloading venues from predefined_venues.json...")
    
    json_file = 'data/predefined_venues.json'
    
    if not os.path.exists(json_file):
        print(f"   ❌ Error: {json_file} not found")
        return False
    
    with open(json_file, 'r') as f:
        venues_data = json.load(f)
    
    print(f"   📊 JSON contains {venues_data['metadata']['total_venues']} venues")
    
    with app.app_context():
        loaded_count = 0
        skipped_count = 0
        
        # Iterate through cities
        for city_id, city_data in venues_data['cities'].items():
            city_id = int(city_id)
            city_name = city_data['name']
            
            # Find the city in database
            city = City.query.filter_by(name=city_name).first()
            if not city:
                print(f"   ⚠️  City {city_name} not found in database, skipping venues")
                continue
            
            print(f"   🏙️  Loading venues for {city_name}...")
            
            # Load venues for this city
            for venue_data in city_data['venues']:
                try:
                    # Create venue object
                    venue = Venue(
                        name=venue_data['name'],
                        venue_type=venue_data.get('venue_type', 'museum'),
                        city_id=city.id,
                        address=venue_data.get('address', ''),
                        description=venue_data.get('description', ''),
                        website_url=venue_data.get('website_url', ''),
                        phone_number=venue_data.get('phone_number', ''),
                        email=venue_data.get('email', ''),
                        opening_hours=venue_data.get('opening_hours', ''),
                        holiday_hours=venue_data.get('holiday_hours', ''),
                        admission_fee=venue_data.get('admission_fee', ''),
                        tour_info=venue_data.get('tour_info', ''),
                        instagram_url=venue_data.get('instagram_url', ''),
                        facebook_url=venue_data.get('facebook_url', ''),
                        twitter_url=venue_data.get('twitter_url', ''),
                        youtube_url=venue_data.get('youtube_url', ''),
                        tiktok_url=venue_data.get('tiktok_url', ''),
                        image_url=venue_data.get('image_url', ''),
                        latitude=venue_data.get('latitude'),
                        longitude=venue_data.get('longitude')
                    )
                    
                    # Handle additional_info as JSON string
                    if venue_data.get('additional_info'):
                        if isinstance(venue_data['additional_info'], str):
                            venue.additional_info = venue_data['additional_info']
                        else:
                            # Convert dict/list to JSON string
                            venue.additional_info = json.dumps(venue_data['additional_info'])
                    
                    # Add to database
                    db.session.add(venue)
                    loaded_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Error loading venue '{venue_data.get('name', 'Unknown')}': {e}")
                    skipped_count += 1
                    continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n📊 Venues Reload Summary:")
        print(f"   ✅ Successfully loaded: {loaded_count} venues")
        print(f"   ⚠️  Skipped: {skipped_count} venues")
        
        return True

def verify_data():
    """Verify the reload was successful"""
    print("\n🔍 Verifying reload...")
    
    with app.app_context():
        total_cities = City.query.count()
        total_venues = Venue.query.count()
        print(f"   📊 Total cities in database: {total_cities}")
        print(f"   📊 Total venues in database: {total_venues}")
        
        # Check cities with state data
        cities_with_state = City.query.filter(City.state != '').count()
        print(f"   🏙️  Cities with state data: {cities_with_state}")
        
        # Show some sample cities
        sample_cities = City.query.limit(5).all()
        print(f"\n   📋 Sample cities:")
        for city in sample_cities:
            state_info = f", {city.state}" if city.state else ""
            print(f"      - {city.name}{state_info}, {city.country}")

def main():
    """Main function"""
    print("🔄 Database Reload from Predefined JSON Files")
    print("=" * 60)
    
    try:
        # Step 1: Clear all tables
        clear_all_tables()
        
        # Step 2: Reload cities
        if reload_cities_from_json():
            # Step 3: Reload venues
            if reload_venues_from_json():
                # Step 4: Verify
                verify_data()
                print("\n✅ Database reload completed successfully!")
            else:
                print("\n❌ Venues reload failed!")
                return False
        else:
            print("\n❌ Cities reload failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during reload: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

