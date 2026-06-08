#!/usr/bin/env python3
"""
Check if the Landseer event exists in the database
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

EVENT_URL = 'https://www.nga.gov/calendar/finding-awe/finding-awe-sir-edwin-landseers-alpine-mastiffs-reanimating-distressed-traveler?evd=202601241915'

def check_event():
    """Check if the event exists in the database"""
    with app.app_context():
        # Check by URL
        events = Event.query.filter(Event.url == EVENT_URL).all()
        
        if events:
            print(f"✅ Found {len(events)} event(s) with this URL:")
            for event in events:
                print(f"\n   ID: {event.id}")
                print(f"   Title: {event.title}")
                print(f"   Date: {event.start_date}")
                print(f"   Time: {event.start_time} - {event.end_time}")
                print(f"   Location: {event.start_location}")
                print(f"   Venue ID: {event.venue_id}")
                print(f"   City ID: {event.city_id}")
                print(f"   URL: {event.url}")
        else:
            print(f"❌ No events found with URL: {EVENT_URL}")
            
            # Check by title
            title_search = "Landseer"
            events_by_title = Event.query.filter(Event.title.like(f'%{title_search}%')).all()
            if events_by_title:
                print(f"\n   Found {len(events_by_title)} event(s) with 'Landseer' in title:")
                for event in events_by_title:
                    print(f"   - ID {event.id}: {event.title} ({event.start_date})")
            else:
                print(f"\n   No events found with 'Landseer' in title")
        
        # Show total event count
        total_events = Event.query.count()
        print(f"\n📊 Total events in database: {total_events}")

if __name__ == '__main__':
    check_event()


