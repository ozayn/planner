#!/usr/bin/env python3
"""
Test script to demonstrate the new Google Maps image fetching utility
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import get_google_maps_image, get_google_maps_image_for_venue, test_google_maps_image_url

def test_google_maps_utils():
    """Test the Google Maps image fetching utilities"""
    
    # Your API key
    api_key = "AIzaSyBJ0v90GfvkWSIjzceNk2uPbwdmlrDxkYw"
    
    print("🧪 Testing Google Maps Image Fetching Utilities")
    print("=" * 50)
    
    # Test 1: Using individual parameters
    print("\n1️⃣ Testing with individual parameters:")
    image_url = get_google_maps_image(
        venue_name="Metropolitan Museum of Art",
        city="New York",
        state="NY", 
        country="USA",
        api_key=api_key
    )
    
    if image_url:
        print(f"✅ Success! Image URL: {image_url[:100]}...")
        # Test if URL is accessible
        if test_google_maps_image_url(image_url):
            print("✅ Image URL is accessible!")
        else:
            print("❌ Image URL is not accessible")
    else:
        print("❌ Failed to get image URL")
    
    # Test 2: Using venue dictionary
    print("\n2️⃣ Testing with venue dictionary:")
    venue_data = {
        'name': 'Louvre Museum',
        'city': 'Paris',
        'state': '',  # No state for France
        'country': 'France'
    }
    
    image_url2 = get_google_maps_image_for_venue(venue_data, api_key)
    
    if image_url2:
        print(f"✅ Success! Image URL: {image_url2[:100]}...")
        if test_google_maps_image_url(image_url2):
            print("✅ Image URL is accessible!")
        else:
            print("❌ Image URL is not accessible")
    else:
        print("❌ Failed to get image URL")
    
    # Test 3: Test with minimal information
    print("\n3️⃣ Testing with minimal information:")
    image_url3 = get_google_maps_image(
        venue_name="British Museum",
        city="London",
        api_key=api_key
    )
    
    if image_url3:
        print(f"✅ Success! Image URL: {image_url3[:100]}...")
        if test_google_maps_image_url(image_url3):
            print("✅ Image URL is accessible!")
        else:
            print("❌ Image URL is not accessible")
    else:
        print("❌ Failed to get image URL")
    
    print("\n" + "=" * 50)
    print("🎉 Testing completed!")

if __name__ == "__main__":
    test_google_maps_utils()
