#!/usr/bin/env python3
"""
Export National Gallery of Art events to JSON for comparison
Usage:
  Local: python scripts/export_nga_events.py local
  Remote: railway run python scripts/export_nga_events.py remote
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def export_events(mode='local'):
    """Export National Gallery of Art events to JSON"""
    if mode == 'local':
        # Temporarily unset DATABASE_URL to use local SQLite
        original_db_url = os.environ.get('DATABASE_URL')
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        output_file = 'nga_events_local.json'
    else:
        output_file = 'nga_events_remote.json'
    
    from app import app, db, Event, Venue
    
    with app.app_context():
        # Find National Gallery of Art venue
        nga_venues = Venue.query.filter(
            Venue.name.ilike('%National Gallery%')
        ).all()
        
        print(f"📊 Found {len(nga_venues)} National Gallery venue(s):")
        for venue in nga_venues:
            print(f"   - {venue.name} (ID: {venue.id})")
        
        # Get events from all NGA venues (eagerly load venue relationship)
        venue_ids = [v.id for v in nga_venues]
        events = Event.query.options(db.joinedload(Event.venue)).filter(
            Event.venue_id.in_(venue_ids)
        ).all() if venue_ids else []
        
        # Also check by source URL
        nga_events_by_source = Event.query.options(db.joinedload(Event.venue)).filter(
            Event.source_url.like('%nga.gov%')
        ).all()
        
        # Combine and deduplicate
        all_events = {e.id: e for e in events + nga_events_by_source}.values()
        
        # Convert to list of dictionaries
        events_data = []
        for event in all_events:
            try:
                venue_name = event.venue.name if event.venue else None
            except:
                venue_name = None
            
            events_data.append({
                'id': event.id,
                'title': event.title,
                'event_type': event.event_type,
                'start_date': str(event.start_date) if event.start_date else None,
                'end_date': str(event.end_date) if event.end_date else None,
                'start_time': str(event.start_time) if event.start_time else None,
                'venue_id': event.venue_id,
                'venue_name': venue_name,
                'source_url': event.source_url,
                'is_selected': event.is_selected,
                'is_baby_friendly': event.is_baby_friendly,
                'description': (event.description or '')[:200] if event.description else None,
            })
        
        # Restore DATABASE_URL if needed
        if mode == 'local' and original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'mode': mode,
                'venue_count': len(nga_venues),
                'event_count': len(events_data),
                'events': events_data
            }, f, indent=2)
        
        print(f"✅ Exported {len(events_data)} events to {output_file}")
        return output_file

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'local'
    if mode not in ['local', 'remote']:
        print("Usage: python scripts/export_nga_events.py [local|remote]")
        sys.exit(1)
    
    export_events(mode)

