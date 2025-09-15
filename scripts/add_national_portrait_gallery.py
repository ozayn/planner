#!/usr/bin/env python3
"""
Script to add National Portrait Gallery to Washington DC venues
"""

import json
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import get_google_maps_image

def add_national_portrait_gallery():
    """Add National Portrait Gallery to Washington DC venues"""
    
    # Your API key
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Load the predefined venues JSON
    json_file_path = '/Users/oz/Dropbox/2025/planner/data/predefined_venues.json'
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("🏛️ Adding National Portrait Gallery to Washington DC venues...")
        
        # Find Washington DC in the cities
        washington_city = None
        washington_city_id = None
        
        for city_id, city_data in data['cities'].items():
            if city_data['name'] == 'Washington':
                washington_city = city_data
                washington_city_id = city_id
                break
        
        if not washington_city:
            print("❌ Washington DC not found in cities")
            return False
        
        print(f"✅ Found Washington DC (ID: {washington_city_id})")
        
        # Check if National Portrait Gallery already exists
        existing_venues = washington_city['venues']
        for venue in existing_venues:
            if 'Portrait Gallery' in venue['name']:
                print("⚠️ National Portrait Gallery already exists!")
                return True
        
        # Fetch Google Maps image for National Portrait Gallery
        print("🔍 Fetching Google Maps image for National Portrait Gallery...")
        image_url = get_google_maps_image(
            venue_name="National Portrait Gallery",
            city="Washington",
            state="DC",
            country="USA",
            api_key=api_key
        )
        
        if not image_url:
            print("❌ Could not fetch Google Maps image")
            return False
        
        print("✅ Successfully fetched Google Maps image")
        
        # Create the new venue entry
        new_venue = {
            "name": "National Portrait Gallery",
            "venue_type": "Museum",
            "address": "8th St NW & F St NW, Washington, DC 20001",
            "opening_hours": "11:30 AM - 7:00 PM",
            "phone_number": "(202) 633-8300",
            "email": "info@si.edu",
            "description": "A museum in Washington offering cultural experiences and entertainment.",
            "tour_info": "Free. Guided tours daily. Audio tours available.",
            "admission_fee": "Free",
            "website_url": "https://www.npg.si.edu",
            "latitude": 38.8977,
            "longitude": -77.0263,
            "additional_info": "{\"amenities\": [\"Gift Shop\", \"Parking\", \"Wheelchair Accessible\"], \"accessibility\": \"Wheelchair accessible\", \"parking_info\": \"Parking available\", \"public_transport\": \"Public transportation accessible\", \"tags\": [\"museum\", \"cultural\", \"entertainment\"], \"rating\": 4.0, \"price_range\": \"Varies\", \"dress_code\": \"Casual\", \"age_restrictions\": \"All ages\", \"group_bookings\": \"Group bookings available\", \"special_events\": \"Special events throughout the year\"}",
            "image_url": image_url,
            "facebook_url": "https://www.facebook.com/NationalPortraitGallery",
            "instagram_url": "@smithsoniannpg",
            "twitter_url": "@smithsoniannpg",
            "holiday_hours": "Check website for hours"
        }
        
        # Add the new venue to Washington DC
        washington_city['venues'].append(new_venue)
        
        # Update metadata
        data['metadata']['total_venues'] = data['metadata']['total_venues'] + 1
        data['metadata']['venues_with_images'] = data['metadata']['venues_with_images'] + 1
        data['metadata']['last_image_update'] = "2025-01-09 20:00:00"
        data['metadata']['last_update'] = "Added National Portrait Gallery"
        
        # Save the updated JSON
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print("✅ Successfully added National Portrait Gallery to Washington DC venues!")
        print(f"📊 Total venues in Washington DC: {len(washington_city['venues'])}")
        print(f"📊 Total venues in database: {data['metadata']['total_venues']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding National Portrait Gallery: {e}")
        return False

if __name__ == "__main__":
    success = add_national_portrait_gallery()
    
    if success:
        print("\n🎉 National Portrait Gallery successfully added!")
    else:
        print("\n❌ Failed to add National Portrait Gallery")
