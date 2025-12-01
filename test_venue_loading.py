#!/usr/bin/env python3
"""
Test script to debug venue loading
"""
import urllib.request
import urllib.parse
import json

def test_venue_loading():
    print("🔍 Testing venue loading...")
    print("=" * 60)
    
    # First check what cities exist
    print("\n1. Checking cities in production...")
    try:
        req = urllib.request.Request('https://planner.ozayn.com/api/admin/cities')
        with urllib.request.urlopen(req, timeout=30) as response:
            cities = json.loads(response.read().decode())
            print(f"   Found {len(cities)} cities:")
            for city in cities[:5]:
                print(f"   - {city.get('name')}, {city.get('state')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Check current venue count
    print("\n2. Checking current venue count...")
    try:
        req = urllib.request.Request('https://planner.ozayn.com/api/admin/venues')
        with urllib.request.urlopen(req, timeout=30) as response:
            venues = json.loads(response.read().decode())
            print(f"   Found {len(venues)} venues")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Try loading all data
    print("\n3. Loading all data...")
    try:
        req = urllib.request.Request(
            'https://planner.ozayn.com/api/admin/load-all-data',
            method='POST',
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            print(f"   Response: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check venue count again
    print("\n4. Checking venue count after load...")
    try:
        req = urllib.request.Request('https://planner.ozayn.com/api/admin/venues')
        with urllib.request.urlopen(req, timeout=30) as response:
            venues = json.loads(response.read().decode())
            print(f"   Found {len(venues)} venues")
            if len(venues) > 0:
                print(f"   Sample venues:")
                for venue in venues[:3]:
                    print(f"   - {venue.get('name')} (city_id: {venue.get('city_id')})")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    test_venue_loading()


