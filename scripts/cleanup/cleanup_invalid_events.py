#!/usr/bin/env python3
"""
Clean up invalid events with generic/navigation titles
"""

import os
import sys
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def cleanup_invalid_events():
    """Remove events with generic/navigation titles"""
    
    # Generic titles to filter out
    generic_titles = [
        'tour', 'tours', 'visit', 'admission', 'hours', 
        'tickets', 'information', 'about', 'overview', 'home',
        'location', 'contact', 'directions', 'address',
        'exhibitions & events', 'exhibitions and events', 'exhibitions',
        "today's events", 'todays events', 'today events',
        'results', 'calendar', 'events calendar', 'event calendar',
        'resources for groups', 'resources', 'groups',
        'search', 'filter', 'browse', 'explore',
        'upcoming events', 'past events', 'all events',
        'event listings', 'event list', 'event schedule',
        "what's on", 'whats on', 'what is on',
        'programs', 'program', 'activities',
        'visit us', 'plan your visit', 'getting here',
        'news', 'press', 'media', 'blog',
        'support', 'donate', 'membership', 'join',
        'shop', 'store', 'gift shop', 'cafe', 'restaurant',
        'education', 'learn', 'schools', 'teachers',
        'collections', 'collection', 'artworks', 'artwork',
        'exhibitions', 'current exhibitions', 'past exhibitions',
        'virtual tour', 'virtual tours', 'online tour',
        'accessibility', 'access', 'wheelchair',
        'faq', 'frequently asked questions', 'help'
    ]
    
    # Navigation patterns
    navigation_patterns = [
        r'^(exhibitions?\s*[&]?\s*events?)$',
        r'^(today\'?s?\s*events?)$',
        r'^(results?)$',
        r'^(calendar)$',
        r'^(resources?\s*(for|about)?\s*(groups?|visitors?)?)$',
        r'^(event\s*(list|listing|schedule|calendar|search))$',
        r'^(what\'?s?\s*on)$',
        r'^(upcoming|past|all)\s*events?$',
        r'^(plan\s*your\s*visit)$',
        r'^(visit\s*us)$',
        r'^(getting\s*here)$',
        r'^(current|past|upcoming)\s*exhibitions?$'
    ]
    
    with app.app_context():
        all_events = Event.query.all()
        print(f"📋 Found {len(all_events)} total events")
        
        events_to_delete = []
        
        for event in all_events:
            title_lower = event.title.lower().strip() if event.title else ''
            
            # Check against generic titles
            if title_lower in generic_titles:
                events_to_delete.append(event)
                print(f"❌ Marked for deletion: '{event.title}' (generic title)")
                continue
            
            # Check against navigation patterns
            for pattern in navigation_patterns:
                if re.match(pattern, title_lower, re.IGNORECASE):
                    events_to_delete.append(event)
                    print(f"❌ Marked for deletion: '{event.title}' (navigation pattern)")
                    break
        
        if events_to_delete:
            print(f"\n🗑️  Deleting {len(events_to_delete)} invalid events...")
            for event in events_to_delete:
                print(f"   - {event.id}: {event.title}")
                db.session.delete(event)
            
            db.session.commit()
            print(f"\n✅ Successfully deleted {len(events_to_delete)} invalid events")
            print(f"📊 Remaining events: {Event.query.count()}")
        else:
            print("\n✅ No invalid events found")

if __name__ == "__main__":
    cleanup_invalid_events()

