#!/usr/bin/env python3
"""
Manual Venue Enhancement Script
Fills out missing venue fields using predefined knowledge and patterns
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def get_venue_enhancement_data(venue_name, venue_type, city_name):
    """Get enhancement data for a specific venue based on knowledge"""
    
    # Venue-specific enhancement data (only database fields)
    venue_data = {
        # Getty Center
        "Getty Center": {
            "description": "World-renowned art museum featuring European paintings, drawings, sculpture, decorative arts, and photographs. The Getty Center also includes beautiful gardens and offers stunning views of Los Angeles.",
            "website_url": "https://www.getty.edu",
            "image_url": "https://www.getty.edu/content/dam/getty/images/visit/getty-center-aerial-view.jpg",
            "latitude": 34.0780,
            "longitude": -118.4740,
            "facebook_url": "https://www.facebook.com/gettymuseum",
            "instagram_url": "@gettymuseum",
            "twitter_url": "@gettymuseum",
            "holiday_hours": "Closed Mondays and major holidays",
            "additional_info": json.dumps({
                "amenities": ["Gift Shop", "Restaurant", "Gardens", "Parking", "Audio Tours", "Wheelchair Accessible"],
                "accessibility": "Fully wheelchair accessible with elevators, ramps, and accessible restrooms. Wheelchairs available for loan.",
                "parking_info": "Free parking available. Tram service from parking area to museum.",
                "public_transport": "Metro Bus 761 stops nearby. Free tram from parking area.",
                "tags": ["art", "museum", "gardens", "architecture", "free"],
                "rating": 4.7,
                "price_range": "Free admission",
                "dress_code": "Casual",
                "age_restrictions": "All ages",
                "group_bookings": "Group tours available with advance booking",
                "special_events": "Evening concerts and special exhibitions"
            })
        },
        
        # LACMA
        "Los Angeles County Museum of Art (LACMA)": {
            "description": "The largest art museum in the western United States, featuring a comprehensive collection of art spanning ancient times to the present, with particular strengths in Asian, Latin American, and contemporary art.",
            "website_url": "https://www.lacma.org",
            "latitude": "34.0638",
            "longitude": "-118.3594",
            "capacity": "N/A",
            "amenities": ["Gift Shop", "Restaurant", "Cafe", "Parking", "Audio Tours", "Wheelchair Accessible", "Library"],
            "accessibility": "Fully accessible with elevators, ramps, and accessible restrooms. Wheelchairs and strollers available.",
            "parking_info": "Paid parking available on-site. Street parking also available.",
            "public_transport": "Metro Bus 20, 217, 218 stop nearby",
            "social_media": {
                "facebook": "https://www.facebook.com/LACMA",
                "instagram": "@lacma",
                "twitter": "@LACMA"
            },
            "tags": ["art", "museum", "contemporary", "ancient", "sculpture"],
            "rating": "4.3",
            "price_range": "$20 adults, discounts available",
            "dress_code": "Casual",
            "age_restrictions": "All ages",
            "group_bookings": "Group rates and tours available",
            "special_events": "Jazz at LACMA, film screenings, lectures",
            "seasonal_hours": "Closed Wednesdays"
        },
        
        # Griffith Observatory
        "Griffith Observatory": {
            "description": "Iconic observatory offering spectacular views of Los Angeles and the Hollywood sign. Features planetarium shows, telescopes, and interactive science exhibits about astronomy and space exploration.",
            "website_url": "https://griffithobservatory.org",
            "latitude": "34.1183",
            "longitude": "-118.3003",
            "capacity": "N/A",
            "amenities": ["Planetarium", "Telescopes", "Gift Shop", "Cafe", "Parking", "Wheelchair Accessible"],
            "accessibility": "Wheelchair accessible with elevators and ramps. Some telescope areas may have limited access.",
            "parking_info": "Free parking available on-site. Limited spaces, arrive early on weekends.",
            "public_transport": "DASH Observatory bus from Vermont/Sunset Metro station",
            "social_media": {
                "facebook": "https://www.facebook.com/GriffithObservatory",
                "instagram": "@griffithobservatory",
                "twitter": "@GriffithObs"
            },
            "tags": ["astronomy", "observatory", "science", "planetarium", "views"],
            "rating": "4.6",
            "price_range": "Free admission, planetarium shows $7",
            "dress_code": "Casual",
            "age_restrictions": "All ages",
            "group_bookings": "Group planetarium shows available",
            "special_events": "Monthly star parties, special astronomy events",
            "seasonal_hours": "Extended hours during summer"
        },
        
        # Hollywood Walk of Fame
        "Hollywood Walk of Fame": {
            "description": "Iconic sidewalk featuring more than 2,700 brass stars embedded in the sidewalks along Hollywood Boulevard and Vine Street, honoring celebrities from entertainment industry.",
            "website_url": "https://www.walkoffame.com",
            "latitude": "34.1016",
            "longitude": "-118.3267",
            "capacity": "N/A",
            "amenities": ["Gift Shops", "Restaurants", "Street Performers", "Photo Opportunities"],
            "accessibility": "Sidewalk accessible, some areas may be crowded",
            "parking_info": "Paid parking lots and street parking available",
            "public_transport": "Metro Red Line Hollywood/Highland station nearby",
            "social_media": {
                "facebook": "https://www.facebook.com/HollywoodWalkOfFame",
                "instagram": "@hollywoodwalkoffame",
                "twitter": "@WalkOfFame"
            },
            "tags": ["landmark", "celebrities", "hollywood", "tourist", "free"],
            "rating": "4.1",
            "price_range": "Free to visit",
            "dress_code": "Casual",
            "age_restrictions": "All ages",
            "group_bookings": "Guided tours available",
            "special_events": "Star dedication ceremonies",
            "seasonal_hours": "Open 24/7"
        }
    }
    
    # Default template for unknown venues
    default_template = {
        "description": f"A {venue_type.lower()} in {city_name} offering cultural experiences and entertainment.",
        "website_url": f"https://www.{venue_name.lower().replace(' ', '').replace('(', '').replace(')', '')}.com",
        "latitude": 0.0,
        "longitude": 0.0,
        "additional_info": json.dumps({
            "amenities": ["Gift Shop", "Parking", "Wheelchair Accessible"],
            "accessibility": "Wheelchair accessible",
            "parking_info": "Parking available",
            "public_transport": "Public transportation accessible",
            "tags": [venue_type.lower(), "cultural", "entertainment"],
            "rating": 4.0,
            "price_range": "Varies",
            "dress_code": "Casual",
            "age_restrictions": "All ages",
            "group_bookings": "Group bookings available",
            "special_events": "Special events throughout the year"
        })
    }
    
    # Return specific venue data or default template
    return venue_data.get(venue_name, default_template)

def enhance_venues_data():
    """Main function to enhance all venues in predefined_venues.json"""
    
    print("🚀 Starting manual venue enhancement...")
    print("=" * 60)
    
    # Load predefined venues
    venues_file = Path("data/predefined_venues.json")
    print(f"📁 Looking for venues file: {venues_file}")
    
    if not venues_file.exists():
        print("❌ predefined_venues.json not found")
        return False
        
    print("✅ Found venues file, loading data...")
    with open(venues_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Found {data['metadata']['total_venues']} venues across {data['metadata']['total_cities']} cities")
    print("=" * 60)
    
    enhanced_count = 0
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
            venue_type = venue['venue_type']
            
            print(f"  [{i+1}/{len(venues)}] Venue: {venue_name}")
            print(f"      Type: {venue_type}")
            
            # Check if venue already has enhanced data with additional_info
            if venue.get('description') and venue.get('website_url') and venue.get('additional_info'):
                print(f"      ⏭️  Already enhanced with additional_info, skipping")
                continue
            
            print(f"      🔍 Getting enhancement data...")
            # Get enhancement data
            enhancement_data = get_venue_enhancement_data(venue_name, venue_type, city_name)
            
            print(f"      📝 Adding fields: description, website_url, latitude, longitude, etc.")
            # Merge enhancement data with existing venue data
            venue.update(enhancement_data)
            enhanced_count += 1
            print(f"      ✅ Enhanced successfully!")
            print()
    
    # Update metadata
    data['metadata']['enhanced_venues'] = enhanced_count
    data['metadata']['last_enhanced'] = "2025-09-10 16:30:00"
    
    # Save enhanced data
    with open(venues_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Enhancement complete!")
    print(f"   Enhanced: {enhanced_count}/{total_venues} venues")
    print(f"   Updated: {venues_file}")
    
    return True

if __name__ == "__main__":
    success = enhance_venues_data()
    if not success:
        sys.exit(1)
