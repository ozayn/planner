#!/usr/bin/env python3
"""
Fix Asian Art Museum events that are marked as 'event' but should be 'tour'
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Event

def fix_asian_art_event_types():
    """Fix event types for Asian Art Museum events"""
    with app.app_context():
        # Find Asian Art events with type='event' that should be 'tour'
        asian_art_events = Event.query.filter(
            Event.source_url.like('%asia.si.edu%'),
            Event.event_type == 'event'
        ).all()
        
        print(f"📊 Found {len(asian_art_events)} Asian Art events with type='event'")
        print()
        
        tour_keywords = ['tour', 'tours', 'guided tour', 'walking tour', 'collection tour', 'docent-led', 'docent led', 'permanent collection tour']
        
        fixed_count = 0
        for event in asian_art_events:
            title_lower = (event.title or '').lower()
            desc_lower = (event.description or '').lower()
            combined_text = f"{title_lower} {desc_lower}"
            
            # Check if it should be a tour
            if any(keyword in combined_text for keyword in tour_keywords):
                event.event_type = 'tour'
                fixed_count += 1
                print(f"  ✅ Fixed: '{event.title[:50]}' → type='tour'")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ Fixed {fixed_count} events to type='tour'")
        else:
            print("\n✅ No events needed fixing")
        
        return True

if __name__ == '__main__':
    try:
        fix_asian_art_event_types()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

