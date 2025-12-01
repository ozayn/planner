#!/usr/bin/env python3
"""
Test extracting event data from National Gallery of Art Finding Awe URL
"""
import urllib.request
import urllib.parse
import json
import sys

def test_extraction():
    """Test extracting event data from the URL"""
    url = 'http://localhost:5001/api/admin/extract-event-from-url'
    event_url = 'https://www.nga.gov/calendar/finding-awe/finding-awe-giovanni-paolo-paninis-rome?evd=202512051915'
    
    data = {
        "url": event_url
    }
    
    print("🔍 Extracting event data from URL...")
    print(f"URL: {event_url}")
    print("=" * 60)
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
            
            print("\n✅ Extraction successful!")
            print("\nExtracted Data:")
            print(json.dumps(result, indent=2))
            
            # Show key fields
            print("\n" + "=" * 60)
            print("📋 Key Information:")
            print(f"   Title: {result.get('title', 'N/A')}")
            print(f"   Start Time: {result.get('start_time', 'N/A')}")
            print(f"   End Time: {result.get('end_time', 'N/A')}")
            print(f"   Location: {result.get('location', 'N/A')}")
            print(f"   Description: {result.get('description', 'N/A')[:100]}...")
            print(f"   Venue ID: {result.get('venue_id', 'N/A')}")
            print(f"   City ID: {result.get('city_id', 'N/A')}")
            
            return 0
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ HTTP Error {e.code}: {error_body}")
        try:
            error_json = json.loads(error_body)
            print(f"   Error: {error_json.get('error', 'Unknown error')}")
        except:
            pass
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(test_extraction())


