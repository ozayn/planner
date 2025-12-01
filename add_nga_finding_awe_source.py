#!/usr/bin/env python3
"""
Add National Gallery of Art - Finding Awe source to database
"""
import urllib.request
import urllib.parse
import json
import sys

def add_source():
    """Add the Finding Awe source to the database"""
    url = 'http://localhost:5001/api/admin/add-source'
    
    data = {
        "name": "National Gallery of Art - Finding Awe",
        "handle": "nga.gov/calendar/finding-awe",
        "source_type": "website",
        "url": "https://www.nga.gov/calendar/finding-awe",
        "description": "National Gallery of Art's Finding Awe series: Interactive workshops exploring where artists have found awe and how it has inspired their work. 90-minute sessions to breathe deeply and look mindfully at works of art. Includes awe practices based on research by Dacher Keltner. Ages 18 and up.",
        "city_id": 1,  # Washington DC
        "event_types": json.dumps(["talks", "conversations", "workshops", "educational_events", "art_events", "cultural_events", "museum_events"]),
        "is_active": True,
        "reliability_score": 5.0,
        "posting_frequency": "weekly",
        "notes": "Finding Awe series runs October 3, 2025 - March 14, 2026. Workshops focus on specific artworks with registration required. Three workshops offered per artwork topic. Check calendar for dates and times.",
        "scraping_pattern": "Scrape the calendar page for Finding Awe workshops. Look for event dates, times, artwork topics, and registration links. Events are typically 90 minutes long and require registration."
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            if response.status == 200:
                print("✅ Source added successfully!")
                print(f"   Source ID: {result.get('source', {}).get('id')}")
                print(f"   Name: {result.get('source', {}).get('name')}")
                return 0
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                return 1
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ HTTP Error {e.code}: {error_body}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(add_source())


