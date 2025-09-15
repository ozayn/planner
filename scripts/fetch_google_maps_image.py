#!/usr/bin/env python3
"""
Script to fetch Google Maps first location image for a specific venue
Uses Google Places API to get photo reference and construct image URL
"""

import requests
import json
import os
import sys
from urllib.parse import quote
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.env_config import ensure_env_loaded, get_api_keys

def get_google_maps_image(venue_name, address=None, city=None, state=None):
    """
    Fetch Google Maps first location image for a venue
    
    Args:
        venue_name: Name of the venue
        address: Full address (optional)
        city: City name (optional)
        state: State name (optional)
    
    Returns:
        Image URL or None if not found
    """
    # Ensure environment is loaded
    ensure_env_loaded()
    api_keys = get_api_keys()
    
    # Use the provided API key directly
    google_maps_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    try:
        # Step 1: Search for the place using Places API
        search_query = venue_name
        if address:
            search_query += f" {address}"
        elif city and state:
            search_query += f" {city}, {state}"
        
        print(f"🔍 Searching Google Places for: {search_query}")
        
        # Places API Text Search
        places_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        places_params = {
            'query': search_query,
            'key': google_maps_key
        }
        
        places_response = requests.get(places_url, params=places_params, timeout=10)
        places_response.raise_for_status()
        
        places_data = places_response.json()
        
        if places_data.get('status') != 'OK' or not places_data.get('results'):
            print(f"❌ No results found for {venue_name}")
            return None
        
        # Get the first result
        place = places_data['results'][0]
        place_id = place['place_id']
        place_name = place['name']
        
        print(f"✅ Found place: {place_name} (ID: {place_id})")
        
        # Step 2: Get place details including photos
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            'place_id': place_id,
            'fields': 'photos,name,formatted_address',
            'key': google_maps_key
        }
        
        details_response = requests.get(details_url, params=details_params, timeout=10)
        details_response.raise_for_status()
        
        details_data = details_response.json()
        
        if details_data.get('status') != 'OK':
            print(f"❌ Could not get details for place {place_id}")
            return None
        
        place_details = details_data['result']
        
        # Check if there are photos
        if not place_details.get('photos'):
            print(f"❌ No photos found for {place_name}")
            return None
        
        # Get the first photo
        first_photo = place_details['photos'][0]
        photo_reference = first_photo['photo_reference']
        
        print(f"✅ Found photo reference: {photo_reference}")
        
        # Step 3: Return the photo reference instead of full URL
        # The API key should be injected at runtime, not stored in the database
        photo_data = {
            'photo_reference': photo_reference,
            'maxwidth': 800,
            'base_url': 'https://maps.googleapis.com/maps/api/place/photo'
        }
        
        print(f"✅ Generated photo data: {photo_data}")
        
        return photo_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error fetching Google Maps image: {e}")
        return None

def test_image_url(photo_data):
    """
    Test if the photo data can be used to construct a working image URL
    """
    if not photo_data or not isinstance(photo_data, dict):
        return False
    
    try:
        # Construct the full URL for testing
        google_maps_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not google_maps_key:
            return False
            
        image_url = f"{photo_data['base_url']}?maxwidth={photo_data['maxwidth']}&photoreference={photo_data['photo_reference']}&key={google_maps_key}"
        
        response = requests.head(image_url, timeout=10)
        return response.status_code == 200
    except:
        return False

def main():
    """Main function to fetch image for National Gallery of Art"""
    
    # National Gallery of Art details
    venue_name = "National Gallery of Art"
    address = "Constitution Ave NW, Washington, DC 20565"
    city = "Washington"
    state = "DC"
    
    print(f"🏛️  Fetching Google Maps image for {venue_name}")
    print(f"📍 Address: {address}")
    print()
    
    # Fetch the photo data
    photo_data = get_google_maps_image(venue_name, address, city, state)
    
    if photo_data:
        print()
        print("🧪 Testing photo data accessibility...")
        
        if test_image_url(photo_data):
            print("✅ Photo data is valid!")
            print()
            print("📸 Google Maps Photo Data:")
            print(json.dumps(photo_data, indent=2))
            print()
            print("🔗 You can store this photo_data in the venue's image_url field")
            print("   The API key will be injected at runtime when displaying images")
        else:
            print("❌ Photo data is not valid")
    else:
        print("❌ Could not fetch Google Maps photo data")

if __name__ == "__main__":
    main()
