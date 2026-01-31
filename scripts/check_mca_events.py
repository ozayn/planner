#!/usr/bin/env python3
"""
Check MCA Chicago events in the database to see what dates were extracted
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue

def check_mca_events():
    """Check MCA Chicago events in the database"""
    with app.app_context():
        # Find MCA Chicago venue
        mca_venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%museum of contemporary art%chicago%')
        ).first()
        
        if not mca_venue:
            print("❌ MCA Chicago venue not found in database")
            return
        
        print(f"✅ Found venue: {mca_venue.name} (ID: {mca_venue.id})")
        print(f"   URL: {mca_venue.website_url}")
        
        # Find events for this venue
        mca_events = Event.query.filter_by(venue_id=mca_venue.id).order_by(Event.start_date).all()
        
        print(f"\n📊 Found {len(mca_events)} MCA Chicago events:\n")
        
        for event in mca_events:
            print(f"   Title: {event.title}")
            print(f"   Start Date: {event.start_date}")
            print(f"   End Date: {event.end_date}")
            print(f"   Start Time: {event.start_time}")
            print(f"   URL: {event.url}")
            print(f"   Source URL: {event.source_url}")
            print(f"   Event Type: {event.event_type}")
            print(f"   Created: {event.created_at}")
            print(f"   Updated: {event.updated_at}")
            print("   ---")
        
        # Check for Alex Tatarsky event specifically
        alex_events = Event.query.filter(
            Event.title.like('%Alex Tatarsky%'),
            Event.venue_id == mca_venue.id
        ).all()
        
        if alex_events:
            print(f"\n🔍 Found {len(alex_events)} Alex Tatarsky event(s):")
            for event in alex_events:
                print(f"   ID {event.id}: {event.title}")
                print(f"   Date: {event.start_date}")
                print(f"   URL: {event.url}")

if __name__ == '__main__':
    check_mca_events()







