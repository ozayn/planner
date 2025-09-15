#!/usr/bin/env python3
"""
Replace all fake image URLs with honest placeholder images
"""

import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def replace_with_placeholders():
    """Replace all image URLs with honest placeholder images"""
    print("🖼️  Replacing all image URLs with honest placeholder images...")
    
    # Load predefined venues
    try:
        with open('data/predefined_venues.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading predefined venues: {e}")
        return
    
    venues = []
    for city_data in data['cities'].values():
        venues.extend(city_data['venues'])
    
    print(f"📊 Found {len(venues)} venues to update")
    
    updated_count = 0
    
    for venue in venues:
        venue_name = venue.get('name', 'Unknown')
        
        # Create a placeholder image URL with the venue name
        placeholder_url = f"https://via.placeholder.com/800x600/cccccc/666666?text={venue_name.replace(' ', '+')}"
        venue['image_url'] = placeholder_url
        print(f"✅ Updated {venue_name}")
        updated_count += 1
    
    # Save updated data
    try:
        with open('data/predefined_venues.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Updated JSON file")
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return
    
    print(f"\n📈 Results:")
    print(f"✅ Images updated: {updated_count}")
    print(f"📊 Total venues: {len(venues)}")
    print(f"ℹ️  All images are now honest placeholder images")

if __name__ == "__main__":
    replace_with_placeholders()
