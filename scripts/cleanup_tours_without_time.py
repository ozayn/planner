#!/usr/bin/env python3
"""
Clean up tour events that don't have a start time
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def cleanup_tours_without_time():
    """Remove tour events that don't have a start time"""
    
    with app.app_context():
        # Find all tour events
        tour_events = Event.query.filter_by(event_type='tour').all()
        print(f"📋 Found {len(tour_events)} tour events")
        
        events_to_delete = []
        
        for event in tour_events:
            if not event.start_time:
                events_to_delete.append(event)
                print(f"❌ Marked for deletion: '{event.title}' (ID: {event.id}) - no start time")
        
        if events_to_delete:
            print(f"\n🗑️  Deleting {len(events_to_delete)} tour events without start times...")
            for event in events_to_delete:
                print(f"   - {event.id}: {event.title}")
                db.session.delete(event)
            
            db.session.commit()
            print(f"\n✅ Successfully deleted {len(events_to_delete)} tour events without start times")
            print(f"📊 Remaining tour events: {Event.query.filter_by(event_type='tour').count()}")
        else:
            print("\n✅ All tour events have start times")

if __name__ == "__main__":
    cleanup_tours_without_time()

