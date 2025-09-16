#!/usr/bin/env python3
"""
Railway Data Loading Script
Automatically loads JSON data into Railway database during deployment
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import Flask app and database
from app import app, db, Event, Venue, City, Source
from datetime import datetime

def load_cities_data():
    """Load cities from cities.json into Railway database"""
    print("🏙️ Loading cities data for Railway...")
    
    cities_file = Path("data/cities.json")
    if not cities_file.exists():
        print("❌ cities.json not found")
        return False
    
    try:
        with open(cities_file, 'r') as f:
            data = json.load(f)
        
        cities_data = data.get('cities', {})
        if not cities_data:
            print("❌ No cities data found in JSON file")
            return False
        
        with app.app_context():
            # Check if cities already exist
            existing_cities = City.query.count()
            if existing_cities > 0:
                print(f"✅ Cities already loaded ({existing_cities} cities)")
                return True
            
            # Add cities to database
            cities_added = 0
            for city_id, city_info in cities_data.items():
                try:
                    city = City(
                        id=int(city_id),  # Use the JSON city ID
                        name=city_info['name'],
                        state=city_info.get('state'),
                        country=city_info['country'],
                        timezone=city_info.get('timezone', 'UTC'),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(city)
                    cities_added += 1
                except Exception as e:
                    print(f"⚠️  Error adding city {city_info.get('name', 'Unknown')}: {e}")
            
            db.session.commit()
            print(f"✅ Successfully loaded {cities_added} cities for Railway")
            return True
            
    except Exception as e:
        print(f"❌ Error loading cities: {e}")
        return False

def load_venues_data():
    """Load venues from venues.json into Railway database"""
    print("🏛️ Loading venues data for Railway...")
    
    venues_file = Path("data/venues.json")
    if not venues_file.exists():
        print("❌ venues.json not found")
        return False
    
    try:
        with open(venues_file, 'r') as f:
            data = json.load(f)
        
        with app.app_context():
            # Check if venues already exist
            existing_venues = Venue.query.count()
            if existing_venues > 0:
                print(f"✅ Venues already loaded ({existing_venues} venues)")
                return True
            
            venues_added = 0
            for city_id, city_data in data.items():
                if not isinstance(city_data, dict) or 'venues' not in city_data:
                    continue
                
                city_name = city_data.get('name', 'Unknown')
                venues = city_data.get('venues', [])
                
                print(f"  📍 Processing {city_name} ({len(venues)} venues)")
                
                for venue_data in venues:
                    try:
                        # Handle image_url - convert photo reference to Google Maps URL
                        image_url = None
                        if venue_data.get('image_url'):
                            if isinstance(venue_data['image_url'], dict):
                                photo_ref = venue_data['image_url'].get('photo_reference')
                                if photo_ref:
                                    # Note: In Railway, we'll need to add the API key
                                    image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}"
                            else:
                                image_url = venue_data['image_url']
                        
                        # Create new venue
                        venue = Venue(
                            name=venue_data.get('name', ''),
                            venue_type=venue_data.get('venue_type', 'museum'),
                            address=venue_data.get('address', ''),
                            latitude=venue_data.get('latitude'),
                            longitude=venue_data.get('longitude'),
                            image_url=image_url,
                            instagram_url=venue_data.get('instagram_url', ''),
                            facebook_url=venue_data.get('facebook_url', ''),
                            twitter_url=venue_data.get('twitter_url', ''),
                            youtube_url=venue_data.get('youtube_url', ''),
                            tiktok_url=venue_data.get('tiktok_url', ''),
                            website_url=venue_data.get('website_url', ''),
                            description=venue_data.get('description', ''),
                            city_id=int(city_id),
                            opening_hours=venue_data.get('opening_hours', ''),
                            holiday_hours=venue_data.get('holiday_hours', ''),
                            phone_number=venue_data.get('phone_number', ''),
                            email=venue_data.get('email', ''),
                            tour_info=venue_data.get('tour_info', ''),
                            admission_fee=venue_data.get('admission_fee', ''),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        db.session.add(venue)
                        venues_added += 1
                        
                    except Exception as e:
                        print(f"    ⚠️  Error adding venue {venue_data.get('name', 'Unknown')}: {e}")
                        continue
            
            db.session.commit()
            print(f"✅ Successfully loaded {venues_added} venues for Railway")
            return True
            
    except Exception as e:
        print(f"❌ Error loading venues: {e}")
        return False

def load_sources_data():
    """Load sources from sources.json into Railway database"""
    print("📰 Loading sources data for Railway...")
    
    sources_file = Path("data/sources.json")
    if not sources_file.exists():
        print("❌ sources.json not found")
        return False
    
    try:
        with open(sources_file, 'r') as f:
            data = json.load(f)
        
        with app.app_context():
            # Check if sources already exist
            existing_sources = Source.query.count()
            if existing_sources > 0:
                print(f"✅ Sources already loaded ({existing_sources} sources)")
                return True
            
            sources_added = 0
            for city_id, city_data in data.items():
                if not isinstance(city_data, dict) or 'sources' not in city_data:
                    continue
                
                city_name = city_data.get('name', 'Unknown')
                sources = city_data.get('sources', [])
                
                print(f"  📍 Processing {city_name} ({len(sources)} sources)")
                
                for source_data in sources:
                    try:
                        # Handle list fields (convert to JSON string for database)
                        event_types = source_data.get('event_types', [])
                        if isinstance(event_types, list):
                            event_types = json.dumps(event_types)
                        
                        covered_cities = source_data.get('covered_cities')
                        if isinstance(covered_cities, list):
                            covered_cities = json.dumps(covered_cities)
                        
                        # Create new source
                        source = Source(
                            name=source_data.get('name', ''),
                            handle=source_data.get('handle', ''),
                            source_type=source_data.get('source_type', 'website'),
                            url=source_data.get('url', ''),
                            description=source_data.get('description', ''),
                            city_id=int(city_id),
                            covers_multiple_cities=source_data.get('covers_multiple_cities', False),
                            covered_cities=covered_cities,
                            event_types=event_types,
                            is_active=source_data.get('is_active', True),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        db.session.add(source)
                        sources_added += 1
                        
                    except Exception as e:
                        print(f"    ⚠️  Error adding source {source_data.get('name', 'Unknown')}: {e}")
                        continue
            
            db.session.commit()
            print(f"✅ Successfully loaded {sources_added} sources for Railway")
            return True
            
    except Exception as e:
        print(f"❌ Error loading sources: {e}")
        return False

def main():
    """Main function for Railway data loading"""
    print("🚀 RAILWAY DATA LOADING")
    print("=" * 50)
    print("Loading JSON data into Railway database...")
    print("=" * 50)
    
    # Create database tables first
    print("🔧 Creating database tables...")
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            return 1
    
    # Load cities first
    if not load_cities_data():
        print("❌ Failed to load cities!")
        return 1
    
    # Load venues
    if not load_venues_data():
        print("❌ Failed to load venues!")
        return 1
    
    # Load sources
    if not load_sources_data():
        print("❌ Failed to load sources!")
        return 1
    
    # Show final stats
    with app.app_context():
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        sources_count = Source.query.count()
        
        print("\n📊 Railway Database Statistics:")
        print("=" * 40)
        print(f"   Cities: {cities_count}")
        print(f"   Venues: {venues_count}")
        print(f"   Sources: {sources_count}")
        print("=" * 40)
    
    print("\n🎉 Railway data loading completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())

