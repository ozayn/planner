#!/usr/bin/env python3
"""
Test script to debug LLM JSON parsing
"""

import json

def test_json_parsing():
    """Test the JSON parsing logic from fetch_venue_details.py"""
    
    # This is the actual response we got from the LLM
    content = '''```json
{
  "additional_info": {
    "parking": "Limited street parking available",
    "accessibility": "Wheelchair accessible"
  },
  "address": "1600 21st St NW, Washington, DC 20009",
  "admission_fee": "Free, though some special exhibitions may have a fee",
  "city_id": "Washington_D.C.",
  "description": "The Phillips Collection is a modern art museum located in the Dupont Circle neighborhood of Washington, D.C. It was founded by Duncan Phillips and Marjorie Acker Phillips in 1921 and is known for its impressive collection of modern and contemporary art, including works by Renoir, Rothko, and O'Keeffe.",
  "email": "info@phillipscollection.org",
  "facebook_url": "https://www.facebook.com/phillipscollection",
  "holiday_hours": "Closed on Thanksgiving Day and Christmas Day",
  "image_url": "",
  "instagram_url": "@phillipscollection",
  "latitude": 38.9103,
  "longitude": -77.0467,
  "name": "The Phillips Collection",
  "opening_hours": "Tuesday - Sunday: 12PM - 5PM, Closed on Mondays",
  "phone_number": "(202) 387-2151",
  "tiktok_url": "@phillipscollection",
  "tour_info": "Guided tours available, including audio guides and group tours",
  "twitter_url": "@phillipscollection",
  "venue_type": "museum",
  "website_url": "https://www.phillipscollection.org",
  "youtube_url": "https://www.youtube.com/user/phillipscollection"
}
```'''
    
    print("🔍 Testing JSON parsing...")
    print(f"Original content length: {len(content)}")
    print(f"First 100 chars: {repr(content[:100])}")
    print()
    
    # Apply the same parsing logic as in fetch_venue_details.py
    try:
        # Remove markdown code blocks if present
        content = content.strip()
        print(f"After strip: {len(content)} chars")
        
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
            print("Removed ```json prefix")
        if content.startswith('```'):
            content = content[3:]   # Remove ```
            print("Removed ``` prefix")
        if content.endswith('```'):
            content = content[:-3]  # Remove trailing ```
            print("Removed ``` suffix")
        
        print(f"After markdown cleanup: {len(content)} chars")
        print(f"First 100 chars: {repr(content[:100])}")
        print()
        
        # Try to find JSON object in the content
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        print(f"JSON bounds - Start: {start_idx}, End: {end_idx}")
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_content = content[start_idx:end_idx + 1]
            print("Extracted JSON from bounds")
        else:
            json_content = content
            print("Using full content as JSON")
        
        print(f"JSON content length: {len(json_content)}")
        print(f"First 100 chars: {repr(json_content[:100])}")
        print()
        
        # Try to parse JSON
        details = json.loads(json_content.strip())
        print("✅ Successfully parsed JSON!")
        print(f"Venue name: {details.get('name')}")
        print(f"Address: {details.get('address')}")
        print(f"Venue type: {details.get('venue_type')}")
        return details
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"Raw JSON content: {json_content[:200]}...")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

if __name__ == '__main__':
    test_json_parsing()


