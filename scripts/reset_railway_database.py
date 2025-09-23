#!/usr/bin/env python3
"""
Reset Railway Database
Clears all data and repopulates from JSON files
"""

import json
import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue, Event, Source

def clear_all_data():
    """Clear all data from database"""
    print("🗑️ Clearing all data from database...")
    
    try:
        # Clear in order to respect foreign key constraints
        Event.query.delete()
        Venue.query.delete()
        Source.query.delete()
        City.query.delete()
        
        db.session.commit()
        print("✅ All data cleared successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing data: {e}")
        db.session.rollback()
        return False

def load_cities_from_json():
    """Load cities from cities.json"""
    print("🏙️ Loading cities from cities.json...")
    
    try:
        with open('data/cities.json', 'r') as f:
            cities_data = json.load(f)
        
        cities_loaded = 0
        for city_data in cities_data:
            city = City(
                name=city_data['name'],
                state=city_data.get('state'),
                country=city_data['country'],
                latitude=city_data.get('latitude'),
                longitude=city_data.get('longitude'),
                timezone=city_data.get('timezone', 'America/New_York')
            )
            db.session.add(city)
            cities_loaded += 1
        
        db.session.commit()
        print(f"✅ Loaded {cities_loaded} cities")
        return True
        
    except Exception as e:
        print(f"❌ Error loading cities: {e}")
        db.session.rollback()
        return False

def load_venues_from_json():
    """Load venues from venues.json"""
    print("🏛️ Loading venues from venues.json...")
    
    try:
        with open('data/venues.json', 'r') as f:
            venues_data = json.load(f)
        
        venues_loaded = 0
        for city_name, city_venues in venues_data.items():
            # Find the city
            city = City.query.filter_by(name=city_name.split(',')[0].strip()).first()
            if not city:
                print(f"⚠️ City not found: {city_name}")
                continue
            
            for venue_data in city_venues:
                venue = Venue(
                    name=venue_data['name'],
                    venue_type=venue_data['venue_type'],
                    address=venue_data.get('address'),
                    latitude=venue_data.get('latitude'),
                    longitude=venue_data.get('longitude'),
                    image_url=venue_data.get('image_url'),
                    instagram_url=venue_data.get('instagram_url'),
                    facebook_url=venue_data.get('facebook_url'),
                    twitter_url=venue_data.get('twitter_url'),
                    youtube_url=venue_data.get('youtube_url'),
                    tiktok_url=venue_data.get('tiktok_url'),
                    website_url=venue_data.get('website_url'),
                    description=venue_data.get('description'),
                    opening_hours=venue_data.get('opening_hours'),
                    holiday_hours=venue_data.get('holiday_hours'),
                    phone_number=venue_data.get('phone_number'),
                    maps_link=venue_data.get('maps_link'),
                    city_id=city.id
                )
                db.session.add(venue)
                venues_loaded += 1
        
        db.session.commit()
        print(f"✅ Loaded {venues_loaded} venues")
        return True
        
    except Exception as e:
        print(f"❌ Error loading venues: {e}")
        db.session.rollback()
        return False

def load_sources_from_json():
    """Load sources from sources.json"""
    print("📱 Loading sources from sources.json...")
    
    try:
        with open('data/sources.json', 'r') as f:
            sources_data = json.load(f)
        
        sources_loaded = 0
        for city_name, city_sources in sources_data.items():
            # Find the city
            city = City.query.filter_by(name=city_name.split(',')[0].strip()).first()
            if not city:
                print(f"⚠️ City not found: {city_name}")
                continue
            
            for source_data in city_sources:
                source = Source(
                    name=source_data['name'],
                    source_type=source_data['source_type'],
                    handle=source_data.get('handle'),
                    url=source_data.get('url'),
                    description=source_data.get('description'),
                    city_id=city.id
                )
                db.session.add(source)
                sources_loaded += 1
        
        db.session.commit()
        print(f"✅ Loaded {sources_loaded} sources")
        return True
        
    except Exception as e:
        print(f"❌ Error loading sources: {e}")
        db.session.rollback()
        return False

def main():
    """Main reset function"""
    print("🔄 Starting Railway database reset...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    with app.app_context():
        # Step 1: Clear all data
        if not clear_all_data():
            print("❌ Failed to clear data. Aborting.")
            return False
        
        # Step 2: Load cities
        if not load_cities_from_json():
            print("❌ Failed to load cities. Aborting.")
            return False
        
        # Step 3: Load venues
        if not load_venues_from_json():
            print("❌ Failed to load venues. Aborting.")
            return False
        
        # Step 4: Load sources
        if not load_sources_from_json():
            print("❌ Failed to load sources. Aborting.")
            return False
        
        # Final stats
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        sources_count = Source.query.count()
        events_count = Event.query.count()
        
        print("=" * 50)
        print("🎉 Railway database reset completed successfully!")
        print(f"📊 Final counts:")
        print(f"   Cities: {cities_count}")
        print(f"   Venues: {venues_count}")
        print(f"   Sources: {sources_count}")
        print(f"   Events: {events_count}")
        print("=" * 50)
        
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
