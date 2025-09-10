#!/usr/bin/env python3
"""
Image URL validation and fixing script
Checks if image URLs work and updates with correct ones
"""

import sys
import os
import json
import requests
from urllib.parse import urlparse

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_image_url(url, timeout=5):
    """Check if an image URL is accessible"""
    if not url or url.strip() == '':
        return False, "Empty URL"
    
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            if 'image' in content_type:
                return True, "OK"
            else:
                return False, f"Not an image (content-type: {content_type})"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"

def get_correct_image_urls():
    """Get correct image URLs for major venues"""
    return {
        "Getty Center": "https://www.getty.edu/images/visit/getty-center-aerial.jpg",
        "Los Angeles County Museum of Art (LACMA)": "https://www.lacma.org/sites/default/files/styles/hero_image/public/2020-03/LACMA_Exterior_2019.jpg",
        "Museum of Contemporary Art (MOCA)": "https://www.moca.org/sites/default/files/styles/hero_image/public/2020-03/MOCA_Grand_Avenue_Exterior.jpg",
        "Natural History Museum of Los Angeles County": "https://nhm.org/sites/default/files/styles/hero_image/public/2020-03/NHMLAC_Exterior.jpg",
        "Griffith Observatory": "https://griffithobservatory.org/wp-content/uploads/2020/03/Griffith_Observatory_Exterior.jpg",
        "Huntington Library": "https://www.huntington.org/sites/default/files/styles/hero_image/public/2020-03/Huntington_Library_Exterior.jpg",
        "Hammer Museum": "https://hammer.ucla.edu/sites/default/files/styles/hero_image/public/2020-03/Hammer_Museum_Exterior.jpg",
        "Norton Simon Museum": "https://www.nortonsimon.org/sites/default/files/styles/hero_image/public/2020-03/Norton_Simon_Museum_Exterior.jpg",
        "Skirball Cultural Center": "https://www.skirball.org/sites/default/files/styles/hero_image/public/2020-03/Skirball_Cultural_Center_Exterior.jpg",
        "Autry Museum": "https://theautry.org/sites/default/files/styles/hero_image/public/2020-03/Autry_Museum_Exterior.jpg"
    }

def fix_image_urls():
    """Fix broken image URLs in predefined venues"""
    print("🖼️  Checking and fixing image URLs...")
    
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
    
    print(f"📊 Found {len(venues)} venues to check")
    
    # Get correct URLs
    correct_urls = get_correct_image_urls()
    
    broken_count = 0
    fixed_count = 0
    
    for venue in venues:
        venue_name = venue.get('name', 'Unknown')
        current_url = venue.get('image_url', '')
        
        print(f"\n🔍 Checking: {venue_name}")
        print(f"   Current URL: {current_url}")
        
        # Check if current URL works
        is_valid, error = check_image_url(current_url)
        
        if is_valid:
            print(f"   ✅ Current URL works")
        else:
            print(f"   ❌ Current URL broken: {error}")
            broken_count += 1
            
            # Try to find a correct URL
            if venue_name in correct_urls:
                new_url = correct_urls[venue_name]
                print(f"   🔧 Trying correct URL: {new_url}")
                
                is_new_valid, new_error = check_image_url(new_url)
                if is_new_valid:
                    venue['image_url'] = new_url
                    print(f"   ✅ Fixed with correct URL")
                    fixed_count += 1
                else:
                    print(f"   ❌ Correct URL also broken: {new_error}")
                    # Use a generic placeholder
                    venue['image_url'] = "https://via.placeholder.com/400x300/cccccc/666666?text=No+Image"
                    print(f"   🔧 Using placeholder image")
            else:
                # Use a generic placeholder for unknown venues
                venue['image_url'] = "https://via.placeholder.com/400x300/cccccc/666666?text=No+Image"
                print(f"   🔧 Using placeholder image")
    
    # Save updated data
    try:
        with open('data/predefined_venues.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Updated JSON file")
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return
    
    print(f"\n📈 Results:")
    print(f"❌ Broken URLs found: {broken_count}")
    print(f"✅ URLs fixed: {fixed_count}")
    print(f"🔧 Placeholders added: {broken_count - fixed_count}")

if __name__ == "__main__":
    fix_image_urls()
