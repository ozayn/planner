#!/usr/bin/env python3
"""
Clean event descriptions that have malformed date formatting.
Fixes patterns like "DatesApril 27, 2024–April 29, 2029" to "Dates: April 27, 2024–April 29, 2029"
or removes "Dates" prefix entirely if it's redundant.
"""

import os
import sys
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def clean_description(description):
    """Clean malformed date patterns in description"""
    if not description:
        return description
    
    # Pattern 1: "Dates" followed immediately by a month name (no space)
    # e.g., "DatesApril 27, 2024–April 29, 2029"
    pattern1 = r'Dates([A-Z][a-z]+ \d{1,2}, \d{4})'
    replacement1 = r'Dates: \1'
    description = re.sub(pattern1, replacement1, description)
    
    # Pattern 2: "Description: Dates" followed immediately by a month name
    # e.g., "Description: DatesApril 27, 2024–April 29, 2029"
    pattern2 = r'Description:\s*Dates([A-Z][a-z]+ \d{1,2}, \d{4})'
    replacement2 = r'Description:\n\nDates: \1'
    description = re.sub(pattern2, replacement2, description)
    
    # Pattern 3: "Dates" at the start of description followed by month
    # e.g., "DatesApril 27, 2024–April 29, 2029"
    pattern3 = r'^Dates([A-Z][a-z]+ \d{1,2}, \d{4})'
    replacement3 = r'Dates: \1'
    description = re.sub(pattern3, replacement3, description)
    
    # Clean up any double spaces or newlines
    description = re.sub(r'\n\n+', '\n\n', description)
    description = re.sub(r'  +', ' ', description)
    
    return description.strip()

def clean_all_descriptions():
    """Clean all event descriptions with malformed date patterns"""
    with app.app_context():
        # Find all events with the malformed pattern
        patterns = [
            '%DatesApril%',
            '%DatesMarch%',
            '%DatesJuly%',
            '%DatesJanuary%',
            '%DatesFebruary%',
            '%DatesMay%',
            '%DatesJune%',
            '%DatesAugust%',
            '%DatesSeptember%',
            '%DatesOctober%',
            '%DatesNovember%',
            '%DatesDecember%',
        ]
        
        event_ids = set()
        for pattern in patterns:
            events = Event.query.filter(Event.description.like(pattern)).all()
            for e in events:
                event_ids.add(e.id)
        
        print(f"Found {len(event_ids)} events with malformed date descriptions")
        
        if not event_ids:
            print("No events to clean!")
            return
        
        updated_count = 0
        for event_id in event_ids:
            event = Event.query.get(event_id)
            if not event or not event.description:
                continue
            
            original_desc = event.description
            cleaned_desc = clean_description(original_desc)
            
            if cleaned_desc != original_desc:
                event.description = cleaned_desc
                updated_count += 1
                print(f"✅ Updated ID {event.id}: {event.title[:50]}")
                print(f"   Before: {original_desc[:80]}...")
                print(f"   After:  {cleaned_desc[:80]}...")
                print()
        
        if updated_count > 0:
            db.session.commit()
            print(f"✅ Successfully cleaned {updated_count} event descriptions")
        else:
            print("No descriptions needed cleaning")

if __name__ == '__main__':
    clean_all_descriptions()
