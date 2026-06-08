#!/usr/bin/env python3
"""
Script to retroactively mark baby-friendly events in the database
Scans all events and marks them as baby-friendly if they contain relevant keywords
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Event

def mark_baby_friendly_events():
    """Mark events as baby-friendly based on keywords in title/description"""
    with app.app_context():
        # Baby-friendly keywords (same as in app.py)
        baby_keywords = [
            'baby', 'babies', 'toddler', 'toddlers', 'infant', 'infants',
            'ages 0-2', 'ages 0–2', 'ages 0 to 2', '0-2 years', '0–2 years',
            'ages 0-3', 'ages 0–3', 'ages 0 to 3', '0-3 years', '0–3 years',
            'bring your own baby', 'byob', 'baby-friendly', 'baby friendly',
            'stroller', 'strollers', 'nursing', 'breastfeeding',
            'family program', 'family-friendly', 'family friendly',
            'art & play', 'art and play', 'play time', 'playtime',
            'children', 'kids', 'little ones', 'young families'
        ]
        
        # Get all events
        all_events = Event.query.all()
        print(f"📊 Scanning {len(all_events)} events...")
        
        marked_count = 0
        already_marked = 0
        
        for event in all_events:
            # Combine title and description for keyword search
            title = (event.title or '').lower()
            description = (event.description or '').lower()
            combined_text = f"{title} {description}"
            
            # Check if event contains baby-friendly keywords
            is_baby_friendly = any(keyword in combined_text for keyword in baby_keywords)
            
            if is_baby_friendly:
                if event.is_baby_friendly:
                    already_marked += 1
                else:
                    event.is_baby_friendly = True
                    marked_count += 1
                    print(f"   👶 Marked: '{event.title[:60]}' (ID: {event.id})")
        
        # Commit changes
        if marked_count > 0:
            db.session.commit()
            print(f"\n✅ Successfully marked {marked_count} events as baby-friendly")
        else:
            print(f"\n✅ No new events to mark (already marked: {already_marked})")
        
        total_baby_friendly = Event.query.filter_by(is_baby_friendly=True).count()
        print(f"📊 Total baby-friendly events in database: {total_baby_friendly}")
        
        return True

if __name__ == '__main__':
    try:
        mark_baby_friendly_events()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
