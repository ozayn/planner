#!/usr/bin/env python3
"""
Update venues.json from database
Syncs the venues.json file with the current database state
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Venue

def sanitize_json_file_for_backup(source_file, backup_file):
    """Create a sanitized backup of the JSON file"""
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Sanitize any sensitive data if needed
        sanitized_data = data  # No specific sanitization needed for venues.json
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error creating sanitized backup: {e}")
        import shutil
        shutil.copy2(source_file, backup_file)

def update_venues_json():
    """Update venues.json from database"""
    print("🔄 Updating venues.json from database...")
    
    with app.app_context():
        try:
            venues = Venue.query.order_by(Venue.id).all()
            print(f"📊 Found {len(venues)} venues in database")

            venues_data = {}
            for venue in venues:
                venue_data = {
                    "name": venue.name,
                    "venue_type": venue.venue_type or "",
                    "address": venue.address or "",
                    "city_id": venue.city_id,
                    "city_name": venue.city.name if venue.city else "",
                    "description": venue.description or "",
                    "opening_hours": venue.opening_hours or "",
                    "phone_number": venue.phone_number or "",
                    "email": venue.email or "",
                    "website_url": venue.website_url or "",
                    "instagram_url": venue.instagram_url or "",
                    "facebook_url": venue.facebook_url or "",
                    "twitter_url": venue.twitter_url or "",
                    "youtube_url": venue.youtube_url or "",
                    "tiktok_url": venue.tiktok_url or "",
                    "admission_fee": venue.admission_fee or "",
                    "image_url": venue.image_url or "",
                    "latitude": venue.latitude,
                    "longitude": venue.longitude,
                    "created_at": venue.created_at.isoformat() if venue.created_at else None,
                    "updated_at": venue.updated_at.isoformat() if venue.updated_at else None
                }
                venues_data[str(venue.id)] = venue_data
                print(f"  Added: {venue.name} (ID: {venue.id}) - {venue_data['city_name']}")

            final_data = {
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "description": "Venues exported from database - always most updated version",
                    "total_venues": len(venues),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "venues": venues_data
            }

            venues_file = Path("data/venues.json")
            if venues_file.exists():
                backup_dir = Path("data/backups")
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / f"venues.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                sanitize_json_file_for_backup(venues_file, backup_file)
                print(f"📦 Created backup: {backup_file}")

            with open(venues_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Successfully updated venues.json with {len(venues)} venues")
            
            # Show some statistics
            venue_types = {}
            cities = {}
            for venue in venues:
                # Count venue types
                venue_type = venue.venue_type or "Unknown"
                venue_types[venue_type] = venue_types.get(venue_type, 0) + 1
                
                # Count cities
                city_name = venue.city.name if venue.city else "Unknown"
                cities[city_name] = cities.get(city_name, 0) + 1
            
            print(f"\n📊 Venue Statistics:")
            print(f"  Total Venues: {len(venues)}")
            print(f"  Venue Types: {len(venue_types)}")
            print(f"  Cities: {len(cities)}")
            
            if venue_types:
                print(f"\n🏛️ Top Venue Types:")
                for venue_type, count in sorted(venue_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"    {venue_type}: {count}")
            
            if cities:
                print(f"\n🏙️ Top Cities:")
                for city_name, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"    {city_name}: {count}")
            
            return True

        except Exception as e:
            print(f"❌ Error updating venues.json: {e}")
            return False

if __name__ == '__main__':
    with app.app_context():
        sys.exit(0 if update_venues_json() else 1)




