#!/usr/bin/env python3
"""
Load Venues from venues.json Script
Loads all venue data from venues.json into the database
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

def load_venues_from_json():
    """Load venue data from venues.json into the database"""
    
    print("🏛️ Loading venues from venues.json...")
    print("=" * 60)
    
    # Load venues from venues.json
    venues_file = Path("data/venues.json")
    if not venues_file.exists():
        print("❌ venues.json not found")
        return False
        
    with open(venues_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Found {data['metadata']['total_venues']} venues across {data['metadata']['total_cities']} cities")
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
            
            for city_id, city_data in data['cities'].items():
                city_name = city_data['name']
                venues = city_data['venues']
                
                print(f"\n🏙️ Processing {city_name} ({len(venues)} venues)...")
                print("-" * 50)
                
                # Get city from database
                city = City.query.filter_by(name=city_name).first()
                if not city:
                    print(f"      ⚠️  City '{city_name}' not found in database, skipping...")
                    continue
                
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
                        city_id=city.id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Add to database
                    db.session.add(venue)
                    total_venues_added += 1
                    print(f"      ✅ Added to database")
            
            # Commit all changes
            print(f"\n💾 Committing {total_venues_added} venues to database...")
            db.session.commit()
            print("✅ All venues committed successfully!")
            
            # Verify the data
            print(f"\n🔍 Verifying data...")
            venue_count = Venue.query.count()
            print(f"   Total venues in database: {venue_count}")
            
            if venue_count == total_venues_added:
                print("✅ Data verification successful!")
            else:
                print("⚠️ Data verification failed - count mismatch")
            
            # Show sample venues
            print(f"\n📋 Sample venues in database:")
            print("-" * 50)
            sample_venues = Venue.query.limit(5).all()
            for venue in sample_venues:
                print(f"  - {venue.name} ({venue.venue_type}) - {venue.city.name}")
            
            print(f"\n🎉 Venue loading complete!")
            print(f"   Added: {total_venues_added} venues")
            print(f"   Cities: {data['metadata']['total_cities']}")
            print(f"   Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading venues: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = load_venues_from_json()
    if not success:
        sys.exit(1)
