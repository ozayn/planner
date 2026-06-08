#!/usr/bin/env python3
"""
Script to clean venue image URLs in venues.json
Converts Google Maps URLs with API keys to photo reference data
"""

import json
import re
import sys
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def extract_photo_data_from_url(image_url):
    """
    Extract photo reference and parameters from Google Maps URL
    
    Args:
        image_url: Full Google Maps photo URL
    
    Returns:
        Photo data dict or None if not a Google Maps URL
    """
    if not image_url or not isinstance(image_url, str):
        return None
    
    # Check if it's a Google Maps photo URL
    if 'maps.googleapis.com/maps/api/place/photo' not in image_url:
        return None
    
    try:
        # Parse the URL
        parsed = urlparse(image_url)
        params = parse_qs(parsed.query)
        
        # Extract photo reference
        photo_reference = params.get('photoreference', [None])[0]
        if not photo_reference:
            return None
        
        # Extract maxwidth (default to 800 if not specified)
        maxwidth = params.get('maxwidth', ['800'])[0]
        
        return {
            'photo_reference': photo_reference,
            'maxwidth': int(maxwidth),
            'base_url': 'https://maps.googleapis.com/maps/api/place/photo'
        }
        
    except Exception as e:
        print(f"❌ Error parsing URL {image_url}: {e}")
        return None

def clean_venue_image_urls():
    """
    Clean image URLs in venues.json by converting Google Maps URLs to photo data
    """
    print("🧹 Cleaning venue image URLs in venues.json...")
    print("=" * 60)
    
    venues_file = Path("data/venues.json")
    if not venues_file.exists():
        print("❌ venues.json not found")
        return False
    
    # Read the venues data
    try:
        with open(venues_file, 'r', encoding='utf-8') as f:
            venues_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading venues.json: {e}")
        return False
    
    # Track statistics
    total_venues = 0
    google_maps_urls = 0
    cleaned_urls = 0
    other_urls = 0
    
    # Process each city
    for city_id, city_data in venues_data.items():
        if not isinstance(city_data, dict) or 'venues' not in city_data:
            continue
            
        venues = city_data['venues']
        for venue in venues:
            if not isinstance(venue, dict) or 'image_url' not in venue:
                continue
                
            total_venues += 1
            image_url = venue['image_url']
            
            if not image_url:
                continue
            
            # Check if it's a Google Maps URL
            if 'maps.googleapis.com/maps/api/place/photo' in image_url:
                google_maps_urls += 1
                
                # Extract photo data
                photo_data = extract_photo_data_from_url(image_url)
                if photo_data:
                    # Replace URL with photo data
                    venue['image_url'] = photo_data
                    cleaned_urls += 1
                    print(f"✅ Cleaned: {venue.get('name', 'Unknown')} - {city_data.get('name', 'Unknown City')}")
                else:
                    print(f"❌ Failed to parse: {venue.get('name', 'Unknown')} - {city_data.get('name', 'Unknown City')}")
            else:
                other_urls += 1
                # Keep other URLs as-is (they might be direct image URLs)
                print(f"ℹ️  Keeping non-Google URL: {venue.get('name', 'Unknown')} - {city_data.get('name', 'Unknown City')}")
    
    # Create backup before writing
    backup_file = f"data/backups/venues.json.backup.before_image_cleanup.{Path().cwd().name}"
    try:
        import shutil
        shutil.copy2(venues_file, backup_file)
        print(f"📦 Created backup: {backup_file}")
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
    
    # Write the cleaned data
    try:
        with open(venues_file, 'w', encoding='utf-8') as f:
            json.dump(venues_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully cleaned venues.json")
        print(f"📊 Statistics:")
        print(f"   Total venues processed: {total_venues}")
        print(f"   Google Maps URLs found: {google_maps_urls}")
        print(f"   URLs cleaned: {cleaned_urls}")
        print(f"   Other URLs kept: {other_urls}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error writing cleaned venues.json: {e}")
        return False

def main():
    """Main function"""
    print("🏛️  Venue Image URL Cleaner")
    print("=" * 60)
    print("This script will convert Google Maps URLs with API keys")
    print("to photo reference data for secure storage.")
    print()
    
    success = clean_venue_image_urls()
    
    if success:
        print("\n🎉 Image URL cleaning completed successfully!")
        print("💡 Next steps:")
        print("   1. Update your frontend to handle photo data format")
        print("   2. Inject API keys at runtime when displaying images")
        print("   3. Test image display functionality")
    else:
        print("\n❌ Image URL cleaning failed!")

if __name__ == "__main__":
    main()
