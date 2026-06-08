#!/usr/bin/env python3
"""
Fix City ID Consistency Script
Recreates cities with correct IDs to match JSON files
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
from app import app, db, Venue, City

def fix_city_id_consistency():
    """Fix city ID consistency by recreating cities with correct IDs"""
    
    print("🔧 Fixing city ID consistency...")
    print("=" * 60)
    
    # Load city IDs from JSON
    cities_file = Path("data/cities.json")
    if not cities_file.exists():
        print("❌ cities.json not found")
        return False
        
    with open(cities_file, 'r') as f:
        cities_data = json.load(f)
    
    print(f"📊 Found {cities_data['metadata']['total_cities']} cities in JSON")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Create mapping of city names to their JSON IDs
            json_city_mapping = {}
            for city_id, city_info in cities_data['cities'].items():
                city_name = city_info['name']
                json_city_mapping[city_name] = int(city_id)
            
            print("🏙️ Target city ID mapping:")
            print("-" * 50)
            for city_name, json_id in json_city_mapping.items():
                print(f"  {city_name}: Target ID {json_id}")
            
            # Get current cities and venues from database
            db_cities = City.query.all()
            db_venues = Venue.query.all()
            
            print(f"\n📊 Current database state:")
            print(f"  Cities: {len(db_cities)}")
            print(f"  Venues: {len(db_venues)}")
            
            # Create mapping of old city IDs to city names
            old_city_mapping = {}
            for city in db_cities:
                old_city_mapping[city.id] = city.name
            
            # Clear existing data
            print(f"\n🧹 Clearing existing data...")
            Venue.query.delete()
            City.query.delete()
            db.session.commit()
            print("✅ Existing data cleared")
            
            # Recreate cities with correct IDs
            print(f"\n🏙️ Recreating cities with correct IDs...")
            print("-" * 50)
            
            new_cities = {}
            for city_name, target_id in json_city_mapping.items():
                # Find the original city data
                original_city = None
                for old_id, old_name in old_city_mapping.items():
                    if old_name == city_name:
                        original_city = next((c for c in db_cities if c.id == old_id), None)
                        break
                
                if original_city:
                    # Create new city with correct ID
                    new_city = City(
                        id=target_id,
                        name=city_name,
                        state=original_city.state,
                        country=original_city.country,
                        timezone=original_city.timezone,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(new_city)
                    new_cities[city_name] = new_city
                    print(f"  ✅ {city_name}: ID {target_id}")
                else:
                    print(f"  ⚠️  {city_name}: Original data not found")
            
            # Commit cities first
            db.session.commit()
            print(f"\n💾 Cities committed to database")
            
            # Recreate venues with correct city references
            print(f"\n🏛️ Recreating venues with correct city references...")
            print("-" * 50)
            
            # Load venues from JSON to get the correct city references
            venues_file = Path("data/venues.json")
            with open(venues_file, 'r') as f:
                venues_data = json.load(f)
            
            total_venues_added = 0
            
            for city_id_str, city_data in venues_data.items():
                if not isinstance(city_data, dict) or 'venues' not in city_data:
                    continue
                    
                city_name = city_data['name']
                venues = city_data['venues']
                city_id = int(city_id_str)
                
                # Get the city from our new cities
                city = new_cities.get(city_name)
                if not city:
                    print(f"  ⚠️  City '{city_name}' not found, skipping {len(venues)} venues")
                    continue
                
                print(f"\n🏙️ Processing {city_name} ({len(venues)} venues)...")
                
                for i, venue_data in enumerate(venues):
                    venue_name = venue_data['name']
                    print(f"  [{i+1}/{len(venues)}] Adding venue: {venue_name}")
                    
                    # Create venue object
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
                        image_url=venue_data.get('image_url', ''),
                        latitude=venue_data.get('latitude'),
                        longitude=venue_data.get('longitude'),
                        facebook_url=venue_data.get('facebook_url', ''),
                        instagram_url=venue_data.get('instagram_url', ''),
                        twitter_url=venue_data.get('twitter_url', ''),
                        youtube_url=venue_data.get('youtube_url', ''),
                        tiktok_url=venue_data.get('tiktok_url', ''),
                        holiday_hours=venue_data.get('holiday_hours', ''),
                        additional_info=venue_data.get('additional_info', ''),
                        city_id=city_id,  # Use the correct city ID
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Add to database
                    db.session.add(venue)
                    total_venues_added += 1
                    print(f"      ✅ Added to database (city_id: {city_id})")
            
            # Commit all venues
            print(f"\n💾 Committing {total_venues_added} venues to database...")
            db.session.commit()
            print("✅ All venues committed successfully!")
            
            # Verify the consistency
            print(f"\n🔍 Verifying consistency...")
            print("-" * 50)
            
            # Check cities
            final_cities = City.query.order_by(City.id).all()
            for city in final_cities:
                expected_id = json_city_mapping.get(city.name, 'N/A')
                status = "✅" if city.id == expected_id else "❌"
                print(f"  {status} {city.name}: DB ID {city.id}, Expected {expected_id}")
            
            # Check venues
            final_venues = Venue.query.all()
            inconsistent_venues = []
            for venue in final_venues:
                city = City.query.get(venue.city_id)
                if not city:
                    inconsistent_venues.append(venue)
            
            if inconsistent_venues:
                print(f"\n⚠️  Found {len(inconsistent_venues)} venues with invalid city references:")
                for venue in inconsistent_venues:
                    print(f"    {venue.name}: city_id={venue.city_id} (city not found)")
            else:
                print(f"\n✅ All {len(final_venues)} venues have valid city references")
            
            # Show final summary
            print(f"\n📋 Final Summary:")
            print("-" * 50)
            print(f"  Cities: {len(final_cities)}")
            print(f"  Venues: {len(final_venues)}")
            print(f"  Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            print(f"\n🎉 City ID consistency fix complete!")
            return True
            
        except Exception as e:
            print(f"❌ Error fixing city ID consistency: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = fix_city_id_consistency()
    if not success:
        sys.exit(1)