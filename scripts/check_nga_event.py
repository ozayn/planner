#!/usr/bin/env python3
"""Check if the NGA Finding Awe event exists in the database"""
import os
import sys
from datetime import date

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

EVENT_URL = 'https://www.nga.gov/calendar/finding-awe/finding-awe-giovanni-paolo-paninis-rome?evd=202512051915'
EVENT_DATE = date(2025, 12, 5)

def check_event():
    """Check if the event exists"""
    with app.app_context():
        # Check by URL and date
        event = Event.query.filter_by(
            url=EVENT_URL,
            start_date=EVENT_DATE
        ).first()
        
        if event:
            print(f"✅ Event found!")
            print(f"   ID: {event.id}")
            print(f"   Title: {event.title}")
            print(f"   Date: {event.start_date}")
            print(f"   Time: {event.start_time} - {event.end_time}")
            print(f"   Description: {event.description[:100]}..." if event.description else "   Description: None")
            
            if event.venue:
                print(f"   Venue: {event.venue.name}")
            if event.city:
                print(f"   City: {event.city.name}")
            print(f"   Location: {event.start_location}")
            return True
        else:
            print(f"❌ Event not found in database")
            print(f"   Searching for URL: {EVENT_URL}")
            print(f"   Date: {EVENT_DATE}")
            
            # Check if there are any events with similar title
            similar = Event.query.filter(
                Event.title.like('%Finding Awe%')
            ).all()
            
            if similar:
                print(f"\n   Found {len(similar)} similar events:")
                for e in similar:
                    print(f"     - {e.title} (ID: {e.id}, Date: {e.start_date})")
            
            return False

if __name__ == '__main__':
    try:
        exists = check_event()
        sys.exit(0 if exists else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


