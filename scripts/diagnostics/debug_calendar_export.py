#!/usr/bin/env python3
"""
Debug calendar export - check everything
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue

def debug_calendar_export():
    """Debug calendar export issue"""
    with app.app_context():
        # Find the Landseer event
        event = Event.query.filter(
            Event.title.like('%Landseer%')
        ).first()
        
        if not event:
            print("❌ Landseer event not found, looking for any Finding Awe event...")
            event = Event.query.filter(
                Event.title.like('%Finding Awe%')
            ).first()
            
            if not event:
                print("❌ No Finding Awe events found")
                return
        
        print(f"✅ Found event: {event.title}")
        print(f"   ID: {event.id}")
        print(f"   Venue ID: {event.venue_id}")
        print(f"   Start Location: {event.start_location}")
        
        # Check venue relationship
        print(f"\n🏛️  Venue relationship:")
        if event.venue:
            print(f"   ✅ Event has venue: {event.venue.name}")
            print(f"   Venue ID: {event.venue.id}")
            print(f"   Venue address: {event.venue.address or 'NO ADDRESS'}")
            print(f"   Venue address type: {type(event.venue.address)}")
        else:
            print(f"   ❌ Event has NO venue! (venue_id={event.venue_id})")
            if event.venue_id:
                # Try to find the venue
                venue = Venue.query.get(event.venue_id)
                if venue:
                    print(f"   But venue exists in DB: {venue.name}")
                else:
                    print(f"   Venue ID {event.venue_id} doesn't exist in database")
        
        # Get event as dict
        print(f"\n📋 Event.to_dict() output:")
        event_dict = event.to_dict()
        
        print(f"   venue_address: {repr(event_dict.get('venue_address'))}")
        print(f"   venue_name: {repr(event_dict.get('venue_name'))}")
        print(f"   city_name: {repr(event_dict.get('city_name'))}")
        print(f"   start_location: {repr(event_dict.get('start_location'))}")
        
        # Check if venue_address key exists
        if 'venue_address' in event_dict:
            print(f"   ✅ venue_address key exists")
            if event_dict['venue_address']:
                print(f"   ✅ venue_address has value: {event_dict['venue_address']}")
            else:
                print(f"   ⚠️  venue_address is None/empty")
        else:
            print(f"   ❌ venue_address key NOT in dict!")
        
        # Simulate JavaScript logic
        print(f"\n🔍 Simulating JavaScript logic:")
        venue_address = event_dict.get('venue_address')
        venue_name = event_dict.get('venue_name')
        city_name = event_dict.get('city_name')
        start_location = event_dict.get('start_location')
        
        has_venue_address = venue_address and isinstance(venue_address, str) and venue_address.strip()
        
        print(f"   has_venue_address check: {has_venue_address}")
        if has_venue_address:
            print(f"   ✅ Would use: {venue_address}")
        elif venue_name and isinstance(venue_name, str) and venue_name.strip():
            location = venue_name
            if city_name:
                location += f", {city_name}"
            print(f"   ⚠️  Would use: {location}")
        elif start_location:
            print(f"   ❌ Would use: {start_location}")

if __name__ == '__main__':
    debug_calendar_export()


