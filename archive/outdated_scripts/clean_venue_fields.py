#!/usr/bin/env python3
"""
Clean Up Venue Fields Script
Removes redundant fields and fixes field structure issues
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def clean_venue_fields():
    """Clean up redundant and problematic fields in venues"""
    
    print("🧹 Cleaning up venue fields...")
    print("=" * 60)
    
    # Load predefined venues
    venues_file = Path("data/predefined_venues.json")
    if not venues_file.exists():
        print("❌ predefined_venues.json not found")
        return False
        
    with open(venues_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Found {data['metadata']['total_venues']} venues across {data['metadata']['total_cities']} cities")
    print("=" * 60)
    
    # Fields to remove (redundant or problematic)
    fields_to_remove = [
        'social_media',  # Redundant with individual social fields
        'seasonal_hours',  # Mostly empty (96.9% empty)
        'capacity',  # Mostly "N/A"
        'amenities',  # Duplicated in additional_info
        'accessibility',  # Duplicated in additional_info
        'parking_info',  # Duplicated in additional_info
        'public_transport',  # Duplicated in additional_info
        'tags',  # Duplicated in additional_info
        'rating',  # Duplicated in additional_info
        'price_range',  # Duplicated in additional_info
        'dress_code',  # Duplicated in additional_info
        'age_restrictions',  # Duplicated in additional_info
        'group_bookings',  # Duplicated in additional_info
        'special_events'  # Duplicated in additional_info
    ]
    
    cleaned_count = 0
    total_venues = 0
    
    # Process each city
    for city_id, city_data in data['cities'].items():
        city_name = city_data['name']
        venues = city_data['venues']
        
        print(f"\n🏙️ Processing {city_name} ({len(venues)} venues)...")
        print("-" * 50)
        
        for i, venue in enumerate(venues):
            total_venues += 1
            venue_name = venue['name']
            
            print(f"  [{i+1}/{len(venues)}] Venue: {venue_name}")
            
            # Remove redundant fields
            removed_fields = []
            for field in fields_to_remove:
                if field in venue:
                    del venue[field]
                    removed_fields.append(field)
            
            if removed_fields:
                cleaned_count += 1
                print(f"      ✅ Removed: {', '.join(removed_fields)}")
            else:
                print(f"      ⏭️  No redundant fields")
    
    # Update metadata
    data['metadata']['last_cleanup_update'] = "2025-09-10 18:00:00"
    data['metadata']['cleanup_status'] = "Redundant fields removed"
    
    # Save cleaned data
    with open(venues_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Field cleanup complete!")
    print(f"   Cleaned: {cleaned_count}/{total_venues} venues")
    print(f"   Removed fields: {', '.join(fields_to_remove)}")
    print(f"   Updated: {venues_file}")
    
    return True

if __name__ == "__main__":
    success = clean_venue_fields()
    if not success:
        sys.exit(1)
