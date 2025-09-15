#!/usr/bin/env python3
"""
Example usage of the Google Maps image fetching utility
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import get_google_maps_image, get_google_maps_image_for_venue

def example_usage():
    """Example of how to use the Google Maps image fetching utility"""
    
    # Your API key
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    print("📸 Google Maps Image Fetching Examples")
    print("=" * 40)
    
    # Example 1: Get image for a specific venue
    print("\n🏛️ Example 1: Metropolitan Museum of Art")
    image_url = get_google_maps_image(
        venue_name="Metropolitan Museum of Art",
        city="New York",
        state="NY",
        country="USA",
        api_key=api_key
    )
    
    if image_url:
        print(f"✅ Image URL: {image_url}")
    else:
        print("❌ Could not fetch image")
    
    # Example 2: Using venue dictionary
    print("\n🏛️ Example 2: Using venue dictionary")
    venue = {
        'name': 'Louvre Museum',
        'city': 'Paris',
        'country': 'France'
    }
    
    image_url2 = get_google_maps_image_for_venue(venue, api_key)
    
    if image_url2:
        print(f"✅ Image URL: {image_url2}")
    else:
        print("❌ Could not fetch image")
    
    # Example 3: Minimal information
    print("\n🏛️ Example 3: Minimal information")
    image_url3 = get_google_maps_image(
        venue_name="Tate Modern",
        city="London",
        api_key=api_key
    )
    
    if image_url3:
        print(f"✅ Image URL: {image_url3}")
    else:
        print("❌ Could not fetch image")

if __name__ == "__main__":
    example_usage()
