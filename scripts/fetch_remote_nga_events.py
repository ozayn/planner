#!/usr/bin/env python3
"""
Fetch National Gallery of Art events from production API
"""

import json
import sys
import requests
from datetime import datetime

def fetch_from_api(api_url):
    """Fetch all events from API and filter for NGA"""
    try:
        # Try to get all events from admin endpoint
        response = requests.get(f"{api_url}/api/admin/events", timeout=30)
        if response.status_code == 200:
            all_events = response.json()
            # Filter for National Gallery events
            nga_events = [
                e for e in all_events 
                if 'National Gallery' in (e.get('venue_name') or '') or 
                   'nga.gov' in (e.get('source_url') or '')
            ]
            return nga_events
        else:
            print(f"❌ API returned status {response.status_code}: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching from API: {e}")
        return None

def export_to_json(events, output_file):
    """Export events to JSON"""
    events_data = []
    for event in events:
        events_data.append({
            'id': event.get('id'),
            'title': event.get('title'),
            'event_type': event.get('event_type'),
            'start_date': event.get('start_date'),
            'end_date': event.get('end_date'),
            'start_time': event.get('start_time'),
            'venue_id': event.get('venue_id'),
            'venue_name': event.get('venue_name'),
            'source_url': event.get('source_url'),
            'is_selected': event.get('is_selected'),
            'is_baby_friendly': event.get('is_baby_friendly'),
            'description': (event.get('description') or '')[:200] if event.get('description') else None,
        })
    
    with open(output_file, 'w') as f:
        json.dump({
            'exported_at': datetime.now().isoformat(),
            'mode': 'remote_api',
            'event_count': len(events_data),
            'events': events_data
        }, f, indent=2)
    
    print(f"✅ Exported {len(events_data)} events to {output_file}")

def main():
    # Check for URL in command line argument first
    production_url = None
    if len(sys.argv) > 1:
        production_url = sys.argv[1]
    
    # Try to get production URL from environment variables
    if not production_url:
        import os
        production_url = os.getenv('PRODUCTION_URL') or os.getenv('RAILWAY_PUBLIC_DOMAIN')
    
    if not production_url:
        print("❌ Production URL not found.")
        print("💡 Set PRODUCTION_URL environment variable")
        print("💡 Or provide URL as argument: python scripts/fetch_remote_nga_events.py https://your-app.railway.app")
        sys.exit(1)
    
    if not production_url.startswith('http'):
        production_url = f"https://{production_url}"
    
    print(f"🔗 Fetching events from: {production_url}")
    
    events = fetch_from_api(production_url)
    if events is None:
        sys.exit(1)
    
    print(f"📊 Found {len(events)} National Gallery events")
    
    export_to_json(events, 'nga_events_remote.json')
    print("✅ Done! Now run: python scripts/compare_nga_json.py")

if __name__ == '__main__':
    main()

