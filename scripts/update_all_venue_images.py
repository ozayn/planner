#!/usr/bin/env python3
"""
Script to update all venue images in predefined_venues.json using Google Maps API
Replaces placeholder images with real Google Maps images
"""

import json
import time
import os
import sys
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import get_google_maps_image_for_venue

def update_all_venue_images():
    """
    Update all venue images in predefined_venues.json with Google Maps images
    """
    # Your API key
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Load the predefined venues JSON
    json_file_path = '/Users/oz/Dropbox/2025/planner/data/predefined_venues.json'
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 Loaded {data['metadata']['total_venues']} venues from predefined_venues.json")
        print(f"🏙️ Processing {data['metadata']['total_cities']} cities")
        print("=" * 60)
        
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        total_venues = 0
        
        # Process each city and its venues
        for city_id, city_data in data['cities'].items():
            city_name = city_data['name']
            venues = city_data['venues']
            
            print(f"\n🏛️ Processing {len(venues)} venues in {city_name}")
            
            for venue in venues:
                total_venues += 1
                venue_name = venue['name']
                current_image = venue.get('image_url', '')
                
                # Skip if already has a real image (not placeholder)
                if current_image and not current_image.startswith('https://via.placeholder.com'):
                    print(f"   ⏭️  Skipping {venue_name} - already has real image")
                    skipped_count += 1
                    continue
                
                print(f"   🔍 Fetching image for {venue_name}")
                
                # Prepare venue data for the API call
                venue_data = {
                    'name': venue_name,
                    'city': city_name,
                    'state': '',  # We'll try to extract from address if needed
                    'country': 'USA'  # Assuming USA for now, could be enhanced
                }
                
                # Try to extract state from address if available
                address = venue.get('address', '')
                if address:
                    # Simple state extraction - look for common state patterns
                    state_patterns = ['CA', 'NY', 'FL', 'TX', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI', 
                                   'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI',
                                   'CO', 'MN', 'SC', 'AL', 'LA', 'KY', 'OR', 'OK', 'CT', 'UT',
                                   'IA', 'NV', 'AR', 'MS', 'KS', 'NM', 'NE', 'WV', 'ID', 'HI',
                                   'NH', 'ME', 'RI', 'MT', 'DE', 'SD', 'ND', 'AK', 'VT', 'WY']
                    
                    for state in state_patterns:
                        if f', {state}' in address or f' {state} ' in address:
                            venue_data['state'] = state
                            break
                
                # Fetch the Google Maps image
                try:
                    new_image_url = get_google_maps_image_for_venue(venue_data, api_key)
                    
                    if new_image_url:
                        venue['image_url'] = new_image_url
                        updated_count += 1
                        print(f"   ✅ Updated {venue_name}")
                    else:
                        print(f"   ❌ Failed to get image for {venue_name}")
                        failed_count += 1
                    
                    # Add delay to be respectful to the API
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"   ❌ Error fetching image for {venue_name}: {e}")
                    failed_count += 1
                    continue
        
        # Update metadata
        data['metadata']['venues_with_images'] = updated_count
        data['metadata']['last_image_update'] = time.strftime('%Y-%m-%d %H:%M:%S')
        data['metadata']['image_update_status'] = f"Updated {updated_count}, Skipped {skipped_count}, Failed {failed_count}"
        
        # Save the updated JSON
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print("📊 UPDATE SUMMARY:")
        print(f"   Total venues processed: {total_venues}")
        print(f"   ✅ Successfully updated: {updated_count}")
        print(f"   ⏭️  Skipped (already had images): {skipped_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   💰 Estimated API cost: ${(updated_count * 0.056):.2f}")
        print("\n✅ Updated predefined_venues.json with Google Maps images!")
        
        return {
            'success': True,
            'updated': updated_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'total': total_venues
        }
        
    except Exception as e:
        print(f"❌ Error updating venue images: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    print("🚀 Starting bulk venue image update...")
    print("⚠️  This will make API calls for each venue - estimated cost: ~$7.22")
    print()
    
    result = update_all_venue_images()
    
    if result['success']:
        print(f"\n🎉 Successfully processed {result['total']} venues!")
    else:
        print(f"\n❌ Update failed: {result['error']}")
