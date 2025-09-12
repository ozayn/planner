#!/usr/bin/env python3
"""
Script to clean venues database and reload from updated predefined_venues.json
This will clear existing venues and reload all venues including the new National Portrait Gallery
"""

import json
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask app and database models
from app import app, db, City, Venue, Event

def clean_and_reload_venues():
    """
    Clean the venues database and reload from predefined_venues.json
    """
    
    try:
        with app.app_context():
            print("🧹 Starting database clean and reload process...")
            print("=" * 60)
            
            # Step 1: Backup current counts
            current_cities = City.query.count()
            current_venues = Venue.query.count()
            current_events = Event.query.count()
            
            print(f"📊 Current database state:")
            print(f"   Cities: {current_cities}")
            print(f"   Venues: {current_venues}")
            print(f"   Events: {current_events}")
            print()
            
            # Step 2: Clear existing data (in correct order due to foreign keys)
            print("🗑️  Clearing existing data...")
            
            # Clear events first (they reference venues)
            events_deleted = Event.query.delete()
            print(f"   ✅ Deleted {events_deleted} events")
            
            # Clear venues (they reference cities)
            venues_deleted = Venue.query.delete()
            print(f"   ✅ Deleted {venues_deleted} venues")
            
            # Clear cities
            cities_deleted = City.query.delete()
            print(f"   ✅ Deleted {cities_deleted} cities")
            
            # Commit the deletions
            db.session.commit()
            print("   ✅ Database cleared successfully")
            print()
            
            # Step 3: Load predefined venues JSON
            print("📂 Loading predefined venues JSON...")
            json_file_path = '/Users/oz/Dropbox/2025/planner/data/predefined_venues.json'
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"   ✅ Loaded JSON with {data['metadata']['total_venues']} venues")
            print(f"   ✅ Processing {data['metadata']['total_cities']} cities")
            print()
            
            # Step 4: Create cities and venues
            cities_created = 0
            venues_created = 0
            
            for city_id, city_data in data['cities'].items():
                city_name = city_data['name']
                venues = city_data['venues']
                
                print(f"🏙️  Processing {city_name} ({len(venues)} venues)...")
                
                # Create city
                city = City(
                    id=int(city_id),
                    name=city_name,
                    state=city_data.get('state', ''),
                    country=city_data.get('country', 'USA'),
                    timezone=city_data.get('timezone', 'America/New_York'),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                db.session.add(city)
                cities_created += 1
                
                # Create venues for this city
                for venue_data in venues:
                    venue = Venue(
                        name=venue_data['name'],
                        venue_type=venue_data.get('venue_type', 'Museum'),
                        address=venue_data.get('address', ''),
                        opening_hours=venue_data.get('opening_hours', ''),
                        phone_number=venue_data.get('phone_number', ''),
                        email=venue_data.get('email', ''),
                        description=venue_data.get('description', ''),
                        tour_info=venue_data.get('tour_info', ''),
                        admission_fee=venue_data.get('admission_fee', ''),
                        website_url=venue_data.get('website_url', ''),
                        latitude=venue_data.get('latitude'),
                        longitude=venue_data.get('longitude'),
                        additional_info=venue_data.get('additional_info', ''),
                        image_url=venue_data.get('image_url', ''),
                        facebook_url=venue_data.get('facebook_url', ''),
                        instagram_url=venue_data.get('instagram_url', ''),
                        twitter_url=venue_data.get('twitter_url', ''),
                        youtube_url=venue_data.get('youtube_url', ''),
                        tiktok_url=venue_data.get('tiktok_url', ''),
                        holiday_hours=venue_data.get('holiday_hours', ''),
                        city_id=int(city_id),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    db.session.add(venue)
                    venues_created += 1
                
                print(f"   ✅ Added {len(venues)} venues to {city_name}")
            
            # Step 5: Commit all changes
            print("\n💾 Committing changes to database...")
            db.session.commit()
            
            # Step 6: Verify the reload
            print("\n🔍 Verifying database reload...")
            final_cities = City.query.count()
            final_venues = Venue.query.count()
            final_events = Event.query.count()
            
            print(f"📊 Final database state:")
            print(f"   Cities: {final_cities}")
            print(f"   Venues: {final_venues}")
            print(f"   Events: {final_events}")
            
            # Check specifically for National Portrait Gallery
            portrait_gallery = Venue.query.filter_by(name='National Portrait Gallery').first()
            if portrait_gallery:
                print(f"\n✅ National Portrait Gallery found in database!")
                print(f"   ID: {portrait_gallery.id}")
                print(f"   City: {portrait_gallery.city.name if portrait_gallery.city else 'Unknown'}")
                print(f"   Image URL: {portrait_gallery.image_url[:100]}..." if portrait_gallery.image_url else "No image")
            else:
                print(f"\n❌ National Portrait Gallery not found in database!")
            
            print("\n" + "=" * 60)
            print("🎉 Database clean and reload completed successfully!")
            print(f"✅ Created {cities_created} cities")
            print(f"✅ Created {venues_created} venues")
            print(f"✅ Database is ready with updated venue data")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during database clean and reload: {e}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    print("🚀 Starting venues database clean and reload...")
    print("⚠️  This will clear all existing venues and reload from JSON")
    print()
    
    success = clean_and_reload_venues()
    
    if success:
        print("\n🎉 Database successfully cleaned and reloaded!")
        print("🏛️ All venues including National Portrait Gallery are now in the database")
    else:
        print("\n❌ Database clean and reload failed!")
