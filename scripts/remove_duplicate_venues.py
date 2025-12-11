#!/usr/bin/env python3
"""
Remove duplicate venues, keeping the one with events or most complete data
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, Event
from collections import defaultdict

def remove_duplicate_venues():
    """Remove duplicate venues, keeping the best one"""
    with app.app_context():
        # Find duplicates by name
        venues_by_name = defaultdict(list)
        all_venues = Venue.query.all()
        
        for venue in all_venues:
            venues_by_name[venue.name.lower().strip()].append(venue)
        
        duplicates = {name: venues for name, venues in venues_by_name.items() if len(venues) > 1}
        
        print(f"Found {len(duplicates)} duplicate venue names:\n")
        
        deleted_count = 0
        events_transferred = 0
        
        for name, venues in duplicates.items():
            print(f"Processing: {name}")
            
            # Find which venue to keep
            # Priority: 1) Has events, 2) Has more complete data, 3) Lower ID (older)
            venue_event_counts = {}
            for venue in venues:
                event_count = Event.query.filter_by(venue_id=venue.id).count()
                venue_event_counts[venue.id] = event_count
                print(f"  ID {venue.id}: {event_count} events, city_id={venue.city_id}")
            
            # Sort by: event count (desc), then by data completeness, then by ID
            def venue_score(venue):
                event_count = venue_event_counts[venue.id]
                # Data completeness score (more fields = better)
                completeness = sum([
                    1 if venue.address else 0,
                    1 if venue.website_url else 0,
                    1 if venue.description else 0,
                    1 if venue.phone_number else 0,
                    1 if venue.email else 0,
                ])
                return (event_count, completeness, -venue.id)  # Negative ID so lower ID is better
            
            venues_sorted = sorted(venues, key=venue_score, reverse=True)
            venue_to_keep = venues_sorted[0]
            venues_to_delete = venues_sorted[1:]
            
            print(f"  ✅ Keeping: ID {venue_to_keep.id} ({venue_event_counts[venue_to_keep.id]} events)")
            
            # Transfer events from duplicates to the kept venue
            for venue_to_delete in venues_to_delete:
                events = Event.query.filter_by(venue_id=venue_to_delete.id).all()
                if events:
                    print(f"  🔄 Transferring {len(events)} events from ID {venue_to_delete.id} to ID {venue_to_keep.id}")
                    for event in events:
                        event.venue_id = venue_to_keep.id
                    events_transferred += len(events)
                
                # Delete the duplicate venue
                print(f"  🗑️  Deleting duplicate venue ID {venue_to_delete.id}")
                db.session.delete(venue_to_delete)
                deleted_count += 1
            
            print()
        
        # Commit all changes
        if deleted_count > 0:
            db.session.commit()
            print(f"✅ Successfully removed {deleted_count} duplicate venues")
            if events_transferred > 0:
                print(f"✅ Transferred {events_transferred} events to kept venues")
        else:
            print("✅ No duplicates to remove")
        
        return True

if __name__ == '__main__':
    try:
        remove_duplicate_venues()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
