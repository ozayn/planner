#!/usr/bin/env python3
"""
Create the National Gallery of Art Finding Awe event with correct description
"""
import os
import sys
from datetime import datetime, date, time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

# Event details
EVENT_URL = 'https://www.nga.gov/calendar/finding-awe/finding-awe-giovanni-paolo-paninis-rome?evd=202512051915'
EVENT_TITLE = "Finding Awe: Giovanni Paolo Panini's Rome"
EVENT_DESCRIPTION = "Look closely at Giovanni Paolo Panini's paintings of the Interior of Saint Peter's and Interior of the Pantheon. Explore the role of awe and architecture in tourism from the 18th century to the present. Consider where, when, and how architecture elicits awe in your own life."
EVENT_DATE = date(2025, 12, 5)  # Friday, December 5, 2025
EVENT_START_TIME = time(14, 15)  # 2:15 p.m.
EVENT_END_TIME = time(16, 0)  # 4:00 p.m.
EVENT_LOCATION = "West Building Main Floor, Gallery 31"
VENUE_NAME = "National Gallery of Art"
CITY_NAME = "Washington, DC"

def create_event():
    """Create the event in the database"""
    with app.app_context():
        # Find the venue
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like(f'%{VENUE_NAME.lower()}%')
        ).first()
        
        if not venue:
            print(f"❌ Venue '{VENUE_NAME}' not found in database")
            print("Available venues with 'gallery' or 'national':")
            venues = Venue.query.filter(
                (db.func.lower(Venue.name).like('%gallery%')) |
                (db.func.lower(Venue.name).like('%national%'))
            ).limit(10).all()
            for v in venues:
                print(f"  - {v.name} (ID: {v.id})")
            return False
        
        # Find the city
        city = City.query.filter(
            db.func.lower(City.name).like(f'%{CITY_NAME.lower().split(",")[0]}%')
        ).first()
        
        if not city:
            print(f"❌ City '{CITY_NAME}' not found in database")
            return False
        
        # Check if event already exists
        existing = Event.query.filter_by(
            url=EVENT_URL,
            start_date=EVENT_DATE,
            city_id=city.id
        ).first()
        
        if existing:
            print(f"⚠️  Event already exists (ID: {existing.id})")
            print(f"   Title: {existing.title}")
            print(f"   Date: {existing.start_date}")
            
            # Update description if different
            if existing.description != EVENT_DESCRIPTION:
                print(f"   Updating description...")
                existing.description = EVENT_DESCRIPTION
                db.session.commit()
                print(f"✅ Description updated")
            return True
        
        # Create the event
        event = Event(
            title=EVENT_TITLE,
            description=EVENT_DESCRIPTION,
            start_date=EVENT_DATE,
            end_date=EVENT_DATE,
            start_time=EVENT_START_TIME,
            end_time=EVENT_END_TIME,
            start_location=EVENT_LOCATION,
            venue_id=venue.id,
            city_id=city.id,
            event_type='talk',  # Talks & Conversations
            url=EVENT_URL,
            source='website',
            source_url=EVENT_URL,
            is_selected=False
        )
        
        db.session.add(event)
        db.session.commit()
        
        print(f"✅ Event created successfully!")
        print(f"   ID: {event.id}")
        print(f"   Title: {event.title}")
        print(f"   Date: {event.start_date}")
        print(f"   Time: {event.start_time} - {event.end_time}")
        print(f"   Venue: {venue.name}")
        print(f"   City: {city.name}")
        print(f"   Location: {event.start_location}")
        
        return True

if __name__ == '__main__':
    try:
        success = create_event()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


