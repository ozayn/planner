#!/usr/bin/env python3
"""
Check what events are in the database
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def check_events():
    """Check what events are in the database"""
    with app.app_context():
        total_events = Event.query.count()
        print(f"📊 Total events in database: {total_events}")
        
        if total_events > 0:
            print(f"\n📋 Recent events (last 10):")
            events = Event.query.order_by(Event.id.desc()).limit(10).all()
            for event in events:
                print(f"   ID {event.id}: {event.title[:60]}... ({event.start_date})")
            
            # Check for Landseer event specifically
            landseer_events = Event.query.filter(
                Event.title.like('%Landseer%')
            ).all()
            if landseer_events:
                print(f"\n🔍 Found {len(landseer_events)} Landseer event(s):")
                for event in landseer_events:
                    print(f"   ID {event.id}: {event.title}")
                    print(f"   Date: {event.start_date}")
                    print(f"   URL: {event.url}")
            
            # Check for Finding Awe events
            finding_awe_events = Event.query.filter(
                Event.title.like('%Finding Awe%')
            ).all()
            if finding_awe_events:
                print(f"\n🔍 Found {len(finding_awe_events)} Finding Awe event(s):")
                for event in finding_awe_events:
                    print(f"   ID {event.id}: {event.title}")
                    print(f"   Date: {event.start_date}")
        else:
            print("   Database is empty - no events found")

if __name__ == '__main__':
    check_events()


