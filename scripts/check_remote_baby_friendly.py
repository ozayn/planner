#!/usr/bin/env python3
"""
Check if remote database has baby-friendly events
"""

import requests
import json

def check_remote_baby_friendly():
    """Check remote database for baby-friendly events"""
    production_url = "https://planner.ozayn.com"
    
    try:
        # Get all events from admin endpoint
        response = requests.get(f"{production_url}/api/admin/events", timeout=30)
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}: {response.text[:200]}")
            return
        
        all_events = response.json()
        print(f"📊 Total events in remote database: {len(all_events)}")
        
        # Filter for baby-friendly events
        baby_friendly = [e for e in all_events if isinstance(e, dict) and e.get('is_baby_friendly')]
        print(f"👶 Baby-friendly events: {len(baby_friendly)}")
        
        if baby_friendly:
            print("\n✅ Baby-friendly events found:")
            for event in baby_friendly[:10]:
                print(f"   - {event.get('title', 'Unknown')[:60]}")
                print(f"     Venue: {event.get('venue_name', 'Unknown')}")
                print(f"     is_baby_friendly: {event.get('is_baby_friendly')}")
                print()
        else:
            print("\n❌ No baby-friendly events found in remote database")
            print("   This is why the filter shows no results!")
        
        # Check events API response
        print("\n🔍 Checking /api/events endpoint...")
        response2 = requests.get(f"{production_url}/api/events?city_id=1&time_range=this_week", timeout=30)
        if response2.status_code == 200:
            events = response2.json()
            baby_friendly_api = [e for e in events if isinstance(e, dict) and e.get('is_baby_friendly')]
            print(f"   Events API: {len(events)} total, {len(baby_friendly_api)} baby-friendly")
        else:
            print(f"   ❌ Events API returned status {response2.status_code}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_remote_baby_friendly()

