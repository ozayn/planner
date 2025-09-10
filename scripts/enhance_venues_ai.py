#!/usr/bin/env python3
"""
AI-Powered Venue Enhancement Script
Fetches additional venue details using AI to enrich predefined venues data
"""

import json
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from scripts.env_config import get_api_keys, ensure_env_loaded
    import openai
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[:3]}")
    sys.exit(1)

def enhance_venue_with_ai(venue_data, city_name):
    """Use AI to enhance venue data with additional fields"""
    
    # Prepare the prompt for AI enhancement
    prompt = f"""
You are a cultural venue expert. Please provide detailed information about this venue:

Venue: {venue_data['name']}
Type: {venue_data['venue_type']}
Address: {venue_data['address']}
City: {city_name}
Current Hours: {venue_data['opening_hours']}
Phone: {venue_data['phone_number']}
Email: {venue_data['email']}
Admission: {venue_data['admission_fee']}
Current Info: {venue_data.get('tour_info', 'N/A')}

Please provide the following information in JSON format:

{{
    "description": "Detailed description of the venue (2-3 sentences)",
    "website_url": "Official website URL",
    "latitude": "GPS latitude coordinate",
    "longitude": "GPS longitude coordinate", 
    "capacity": "Maximum capacity or 'N/A' if not applicable",
    "amenities": ["List", "of", "key", "amenities"],
    "accessibility": "Accessibility information",
    "parking_info": "Parking availability and details",
    "public_transport": "Public transportation options",
    "social_media": {{
        "facebook": "Facebook page URL or null",
        "instagram": "Instagram handle or null",
        "twitter": "Twitter handle or null"
    }},
    "tags": ["cultural", "tags", "that", "describe", "this", "venue"],
    "rating": "Average rating out of 5 or null",
    "price_range": "Price range description",
    "dress_code": "Dress code requirements or 'Casual'",
    "age_restrictions": "Age restrictions or 'All ages'",
    "group_bookings": "Group booking information or null",
    "special_events": "Information about special events or null",
    "seasonal_hours": "Seasonal hours variations or null"
}}

Please be accurate and provide realistic information. If you don't know specific details, use null or appropriate defaults.
"""

    try:
        # Get API keys
        api_keys = get_api_keys()
        
        # Try OpenAI first
        if api_keys.get('OPENAI_API_KEY'):
            print("🤖 Using OpenAI")
            client = openai.OpenAI(api_key=api_keys['OPENAI_API_KEY'])
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful cultural venue expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content.strip()
            
        else:
            print("❌ No OpenAI API key available")
            return None
        
        # Parse JSON response
        try:
            enhanced_data = json.loads(ai_response)
            return enhanced_data
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse AI response as JSON: {e}")
            print(f"Raw response: {ai_response[:200]}...")
            return None
            
    except Exception as e:
        print(f"❌ AI enhancement failed: {e}")
        return None

def enhance_venues_data():
    """Main function to enhance all venues in predefined_venues.json"""
    
    print("🚀 Starting AI-powered venue enhancement...")
    
    # Load environment
    ensure_env_loaded()
    
    # Load predefined venues
    venues_file = Path("data/predefined_venues.json")
    if not venues_file.exists():
        print("❌ predefined_venues.json not found")
        return False
        
    with open(venues_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Found {data['metadata']['total_venues']} venues across {data['metadata']['total_cities']} cities")
    
    enhanced_count = 0
    total_venues = 0
    
    # Process each city
    for city_id, city_data in data['cities'].items():
        city_name = city_data['name']
        venues = city_data['venues']
        
        print(f"\n🏙️ Processing {city_name} ({len(venues)} venues)...")
        
        for i, venue in enumerate(venues):
            total_venues += 1
            venue_name = venue['name']
            
            print(f"  [{i+1}/{len(venues)}] Enhancing: {venue_name}")
            
            # Check if venue already has enhanced data
            if venue.get('description') and venue.get('website_url'):
                print(f"    ⏭️  Already enhanced, skipping")
                continue
            
            # Enhance venue with AI
            enhanced_data = enhance_venue_with_ai(venue, city_name)
            
            if enhanced_data:
                # Merge enhanced data with existing venue data
                venue.update(enhanced_data)
                enhanced_count += 1
                print(f"    ✅ Enhanced successfully")
                
                # Add a small delay to avoid rate limiting
                time.sleep(1)
            else:
                print(f"    ❌ Enhancement failed")
    
    # Update metadata
    data['metadata']['enhanced_venues'] = enhanced_count
    data['metadata']['last_enhanced'] = time.strftime("%Y-%m-%d %H:%M:%S")
    
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
