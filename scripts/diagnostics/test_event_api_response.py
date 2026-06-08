#!/usr/bin/env python3
"""
Test what the API actually returns for an event
"""
import os
import sys
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def test_api_response():
    """Test what the API returns for an event"""
    with app.app_context():
        # Find the Landseer event
        event = Event.query.filter(
            Event.title.like('%Landseer%')
        ).first()
        
        if not event:
            print("❌ Landseer event not found")
            # Try any Finding Awe event
            event = Event.query.filter(
                Event.title.like('%Finding Awe%')
            ).first()
            
            if not event:
                print("❌ No Finding Awe events found")
                return
        
        print(f"✅ Found event: {event.title}")
        print(f"   ID: {event.id}")
        print(f"   Venue ID: {event.venue_id}")
        
        # Get the event as dict (what the API returns)
        event_dict = event.to_dict()
        
        print(f"\n📋 Event data (to_dict() output):")
        print(f"   venue_address: {repr(event_dict.get('venue_address'))}")
        print(f"   venue_name: {repr(event_dict.get('venue_name'))}")
        print(f"   city_name: {repr(event_dict.get('city_name'))}")
        print(f"   start_location: {repr(event_dict.get('start_location'))}")
        
        # Check if venue_address is actually in the dict
        if 'venue_address' in event_dict:
            print(f"\n✅ venue_address key exists in event_dict")
            if event_dict['venue_address']:
                print(f"   Value: {event_dict['venue_address']}")
            else:
                print(f"   ⚠️  Value is None/empty")
        else:
            print(f"\n❌ venue_address key NOT in event_dict!")
            print(f"   Available keys: {list(event_dict.keys())}")
        
        # Check venue directly
        if event.venue:
            print(f"\n🏛️  Venue details:")
            print(f"   Name: {event.venue.name}")
            print(f"   Address: {event.venue.address or 'NO ADDRESS'}")
            print(f"   Address type: {type(event.venue.address)}")
            print(f"   Address length: {len(event.venue.address) if event.venue.address else 0}")
        
        # Simulate what should happen in JavaScript
        print(f"\n🗓️  Calendar location logic:")
        venue_address = event_dict.get('venue_address')
        venue_name = event_dict.get('venue_name')
        city_name = event_dict.get('city_name')
        start_location = event_dict.get('start_location')
        
        if venue_address and isinstance(venue_address, str) and venue_address.strip():
            print(f"   ✅ Should use venue_address: {venue_address}")
        elif venue_name and isinstance(venue_name, str) and venue_name.strip():
            location = venue_name
            if city_name:
                location += f", {city_name}"
            print(f"   ⚠️  Should use venue_name: {location}")
        elif start_location:
            print(f"   ❌ Would fall back to start_location: {start_location}")

if __name__ == '__main__':
    test_api_response()


