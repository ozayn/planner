#!/usr/bin/env python3
"""
Check if Landseer event is linked to venue and what data it has
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue

def check_event():
    """Check event venue relationship"""
    with app.app_context():
        # Find the Landseer event
        event = Event.query.filter(
            Event.title.like('%Landseer%')
        ).first()
        
        if not event:
            print("❌ Landseer event not found")
            return
        
        print(f"✅ Found event: {event.title}")
        print(f"   ID: {event.id}")
        print(f"   Venue ID: {event.venue_id}")
        print(f"   City ID: {event.city_id}")
        print(f"   Start Location: {event.start_location}")
        
        # Check venue relationship
        print(f"\n🏛️  Venue relationship:")
        if event.venue_id:
            venue = Venue.query.get(event.venue_id)
            if venue:
                print(f"   ✅ Venue found: {venue.name}")
                print(f"   Venue address: {venue.address or 'NO ADDRESS'}")
            else:
                print(f"   ❌ Venue ID {event.venue_id} not found in database!")
        else:
            print(f"   ❌ Event has NO venue_id!")
        
        # Check what to_dict() returns
        print(f"\n📋 Event.to_dict() output:")
        event_dict = event.to_dict()
        print(f"   venue_address: {repr(event_dict.get('venue_address'))}")
        print(f"   venue_name: {repr(event_dict.get('venue_name'))}")
        print(f"   city_name: {repr(event_dict.get('city_name'))}")
        print(f"   start_location: {repr(event_dict.get('start_location'))}")
        
        # Check if venue_address is actually None or missing
        if 'venue_address' not in event_dict:
            print(f"   ❌ venue_address key NOT in dict!")
        elif event_dict['venue_address'] is None:
            print(f"   ⚠️  venue_address is None")
            if event.venue_id:
                print(f"   Event has venue_id={event.venue_id}, but venue_address is None")
                print(f"   This means event.venue is None or venue.address is None")
        elif not event_dict['venue_address']:
            print(f"   ⚠️  venue_address is empty string")
        else:
            print(f"   ✅ venue_address has value: {event_dict['venue_address']}")

if __name__ == '__main__':
    check_event()


