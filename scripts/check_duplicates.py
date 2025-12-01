#!/usr/bin/env python3
"""
Duplicate Checker for Cities, Venues, and Events
Always run this before committing data changes to ensure no duplicates exist.
"""

import os
import sys
import json
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.append('.')

def check_cities_duplicates():
    """Check for duplicate cities in both JSON and database"""
    print("\n🏙️  Checking for duplicate cities...")
    print("=" * 60)
    
    duplicates_found = False
    
    # Check JSON file
    cities_file = Path("data/cities.json")
    if cities_file.exists():
        try:
            with open(cities_file, 'r') as f:
                data = json.load(f)
            
            city_keys = defaultdict(list)
            for city_id, city_info in data.get('cities', {}).items():
                key = (
                    city_info['name'].lower().strip(),
                    city_info.get('state', '').lower().strip(),
                    city_info.get('country', '').lower().strip()
                )
                city_keys[key].append((city_id, city_info))
            
            json_duplicates = {k: v for k, v in city_keys.items() if len(v) > 1}
            
            if json_duplicates:
                duplicates_found = True
                print("❌ Found duplicates in cities.json:")
                for key, entries in json_duplicates.items():
                    name, state, country = key
                    print(f"\n   📍 {name.title()}, {state.title() if state else 'N/A'}, {country.title()}")
                    for city_id, city_info in entries:
                        print(f"      - ID {city_id}: {city_info['name']}, {city_info.get('state', 'N/A')}")
            else:
                print("✅ No duplicates found in cities.json")
        except Exception as e:
            print(f"⚠️  Error checking cities.json: {e}")
    
    # Check database
    try:
        from app import app, db, City
        
        with app.app_context():
            cities = City.query.all()
            city_keys = defaultdict(list)
            
            for city in cities:
                key = (
                    city.name.lower().strip(),
                    (city.state or '').lower().strip(),
                    city.country.lower().strip()
                )
                city_keys[key].append(city)
            
            db_duplicates = {k: v for k, v in city_keys.items() if len(v) > 1}
            
            if db_duplicates:
                duplicates_found = True
                print("\n❌ Found duplicates in database:")
                for key, cities_list in db_duplicates.items():
                    name, state, country = key
                    print(f"\n   📍 {name.title()}, {state.title() if state else 'N/A'}, {country.title()}")
                    for city in cities_list:
                        venues_count = len(city.venues) if hasattr(city, 'venues') else 0
                        events_count = len(city.events) if hasattr(city, 'events') else 0
                        print(f"      - ID {city.id}: {city.name} (venues: {venues_count}, events: {events_count})")
            else:
                print("✅ No duplicates found in database")
                
    except Exception as e:
        print(f"⚠️  Error checking database: {e}")
    
    return not duplicates_found

def check_venues_duplicates():
    """Check for duplicate venues in both JSON and database"""
    print("\n🏛️  Checking for duplicate venues...")
    print("=" * 60)
    
    duplicates_found = False
    
    # Check JSON file
    venues_file = Path("data/venues.json")
    if venues_file.exists():
        try:
            with open(venues_file, 'r') as f:
                data = json.load(f)
            
            # Check within each city
            for city_id, city_data in data.items():
                if not isinstance(city_data, dict) or 'venues' not in city_data:
                    continue
                
                venue_keys = defaultdict(list)
                for venue_id, venue_info in city_data['venues'].items():
                    key = venue_info.get('name', '').lower().strip()
                    if key:
                        venue_keys[key].append((venue_id, venue_info))
                
                city_duplicates = {k: v for k, v in venue_keys.items() if len(v) > 1}
                
                if city_duplicates:
                    duplicates_found = True
                    print(f"❌ Found duplicates in venues.json for city_id {city_id}:")
                    for key, entries in city_duplicates.items():
                        print(f"\n   📍 {key.title()}")
                        for venue_id, venue_info in entries:
                            print(f"      - ID {venue_id}: {venue_info.get('name')}")
            
            if not duplicates_found:
                print("✅ No duplicates found in venues.json")
        except Exception as e:
            print(f"⚠️  Error checking venues.json: {e}")
    
    # Check database
    try:
        from app import app, db, Venue
        
        with app.app_context():
            venues = Venue.query.all()
            venue_keys = defaultdict(list)
            
            for venue in venues:
                key = (
                    venue.name.lower().strip(),
                    venue.city_id
                )
                venue_keys[key].append(venue)
            
            db_duplicates = {k: v for k, v in venue_keys.items() if len(v) > 1}
            
            if db_duplicates:
                duplicates_found = True
                print("\n❌ Found duplicates in database:")
                for key, venues_list in db_duplicates.items():
                    name, city_id = key
                    print(f"\n   📍 {name.title()} (city_id: {city_id})")
                    for venue in venues_list:
                        print(f"      - ID {venue.id}: {venue.name}")
            else:
                print("✅ No duplicates found in database")
                
    except Exception as e:
        print(f"⚠️  Error checking database: {e}")
    
    return not duplicates_found

def check_events_duplicates():
    """Check for duplicate events in database"""
    print("\n📅 Checking for duplicate events...")
    print("=" * 60)
    
    duplicates_found = False
    
    try:
        from app import app, db, Event
        from datetime import datetime
        
        with app.app_context():
            events = Event.query.all()
            event_keys = defaultdict(list)
            
            for event in events:
                # Check for duplicates based on title, city, and start date
                start_date = event.start_date.strftime('%Y-%m-%d') if event.start_date else None
                key = (
                    event.title.lower().strip() if event.title else '',
                    event.city_id,
                    start_date
                )
                if key[0]:  # Only check if title exists
                    event_keys[key].append(event)
            
            db_duplicates = {k: v for k, v in event_keys.items() if len(v) > 1}
            
            if db_duplicates:
                duplicates_found = True
                print("❌ Found duplicates in database:")
                for key, events_list in db_duplicates.items():
                    title, city_id, start_date = key
                    print(f"\n   📍 {title.title()} (city_id: {city_id}, date: {start_date})")
                    for event in events_list:
                        print(f"      - ID {event.id}: {event.title}")
            else:
                print("✅ No duplicates found in database")
                
    except Exception as e:
        print(f"⚠️  Error checking database: {e}")
    
    return not duplicates_found

def main():
    """Run all duplicate checks"""
    print("🔍 DUPLICATE CHECKER")
    print("=" * 60)
    print("Checking for duplicates in cities, venues, and events...")
    
    results = {
        'cities': check_cities_duplicates(),
        'venues': check_venues_duplicates(),
        'events': check_events_duplicates(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DUPLICATE CHECK SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{check_name.capitalize()}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 ALL DUPLICATE CHECKS PASSED!")
        return 0
    else:
        print("🚨 DUPLICATES FOUND!")
        print("⚠️  Please remove duplicates before proceeding")
        return 1

if __name__ == '__main__':
    sys.exit(main())


