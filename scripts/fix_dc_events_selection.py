#!/usr/bin/env python3
"""
Quick script to set is_selected = True for all Washington DC events
This fixes the issue where events exist but aren't showing on the main page
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Event, City

def fix_dc_events():
    """Set is_selected = True for all Washington DC events"""
    with app.app_context():
        # Find Washington DC
        dc_city = City.query.filter_by(name='Washington', state='District of Columbia').first()
        if not dc_city:
            print("❌ Washington DC not found in database")
            return False
        
        print(f"✅ Found Washington DC (ID: {dc_city.id})")
        
        # Get all events for DC
        events = Event.query.filter_by(city_id=dc_city.id).all()
        print(f"📊 Found {len(events)} events for Washington DC")
        
        # Count how many need updating
        unselected = [e for e in events if not e.is_selected]
        print(f"🔍 Found {len(unselected)} events with is_selected=False")
        
        if len(unselected) == 0:
            print("✅ All events are already selected!")
            return True
        
        # Update all events to is_selected = True
        updated_count = 0
        for event in unselected:
            event.is_selected = True
            updated_count += 1
        
        # Commit changes
        db.session.commit()
        print(f"✅ Updated {updated_count} events to is_selected=True")
        print(f"🎉 All {len(events)} Washington DC events are now visible on the main page!")
        
        return True

if __name__ == '__main__':
    try:
        fix_dc_events()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
