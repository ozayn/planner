#!/usr/bin/env python3
"""
Check if National Gallery of Art has an address in the database
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue, Event

def check_venue():
    """Check venue address"""
    with app.app_context():
        # Find National Gallery of Art
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%national gallery%')
        ).first()
        
        if not venue:
            print("❌ National Gallery of Art not found")
            return
        
        print(f"✅ Found venue: {venue.name}")
        print(f"   ID: {venue.id}")
        print(f"   Address: {venue.address or 'NO ADDRESS'}")
        print(f"   City ID: {venue.city_id}")
        
        if venue.city:
            print(f"   City: {venue.city.name}")
        
        # Check events for this venue
        events = Event.query.filter_by(venue_id=venue.id).limit(5).all()
        print(f"\n📅 Sample events for this venue ({len(events)} shown):")
        for event in events:
            print(f"   - {event.title} ({event.start_date})")
            event_dict = event.to_dict()
            print(f"     venue_address: {event_dict.get('venue_address')}")
            print(f"     venue_name: {event_dict.get('venue_name')}")
            print(f"     city_name: {event_dict.get('city_name')}")
            print(f"     start_location: {event_dict.get('start_location')}")

if __name__ == '__main__':
    check_venue()


