#!/usr/bin/env python3
"""
Update venues.json with current database venues
This function will be imported and used in other scripts
"""

import json
import os
from pathlib import Path
from datetime import datetime

def update_venues_json():
    """Update venues.json with current database venues"""
    try:
        from app import app, Venue, City
        
        with app.app_context():
            # Get all venues from database with their cities
            venues = Venue.query.join(City).order_by(City.name, Venue.name).all()
            
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
                os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                
                import shutil
                shutil.copy2(venues_file, backup_file)
                print(f"📋 Backup created: {backup_file}")
            
            # Save to venues.json
            with open(venues_file, 'w') as f:
                json.dump(venues_data, f, indent=2, ensure_ascii=False)
            
            total_venues = sum(len(city_data["venues"]) for city_data in venues_data.values())
            print(f"✅ venues.json updated successfully!")
            print(f"   Total venues: {total_venues}")
            print(f"   Cities: {len(venues_data)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating venues.json: {e}")
        return False

if __name__ == "__main__":
    success = update_venues_json()
    if not success:
        exit(1)
