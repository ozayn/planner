#!/usr/bin/env python3
"""
Test what data is being sent for calendar export
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def test_event_data():
    """Test what data is in the event for calendar export"""
    with app.app_context():
        # Find the Landseer event
        event = Event.query.filter(
            Event.title.like('%Landseer%')
        ).first()
        
        if not event:
            print("❌ Landseer event not found")
            # Try to find any Finding Awe event
            event = Event.query.filter(
                Event.title.like('%Finding Awe%')
            ).first()
            
            if not event:
                print("❌ No Finding Awe events found")
                return
        
        print(f"✅ Found event: {event.title}")
        print(f"   ID: {event.id}")
        print(f"   Date: {event.start_date}")
        
        # Get the event as dict (what the API returns)
        event_dict = event.to_dict()
        
        print(f"\n📋 Event data for calendar export:")
        print(f"   venue_address: {event_dict.get('venue_address')}")
        print(f"   venue_name: {event_dict.get('venue_name')}")
        print(f"   city_name: {event_dict.get('city_name')}")
        print(f"   start_location: {event_dict.get('start_location')}")
        print(f"   description (first 100 chars): {event_dict.get('description', '')[:100] if event_dict.get('description') else 'None'}")
        
        # Check venue directly
        if event.venue:
            print(f"\n🏛️  Venue details:")
            print(f"   Name: {event.venue.name}")
            print(f"   Address: {event.venue.address or 'NO ADDRESS'}")
            print(f"   City: {event.venue.city.name if event.venue.city else 'No city'}")
        
        # Simulate what the calendar export should do
        print(f"\n🗓️  Calendar export should use:")
        if event_dict.get('venue_address'):
            print(f"   Location: {event_dict['venue_address']}")
        elif event_dict.get('venue_name'):
            city = event_dict.get('city_name', '')
            location = event_dict['venue_name']
            if city:
                location += f", {city}"
            print(f"   Location: {location}")
        else:
            print(f"   Location: {event_dict.get('start_location', 'No location')}")
        
        if event_dict.get('start_location') and event_dict.get('venue_name'):
            start_loc = event_dict['start_location']
            venue = event_dict['venue_name']
            if start_loc.lower() != venue.lower():
                print(f"   Description should start with: 'Meeting Location: {start_loc}'")

if __name__ == '__main__':
    test_event_data()


