#!/usr/bin/env python3
"""
Compare National Gallery of Art events between local and remote databases
"""

import os
import sys
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def get_local_events():
    """Get National Gallery of Art events from local SQLite database"""
    # Temporarily unset DATABASE_URL to use local SQLite
    original_db_url = os.environ.get('DATABASE_URL')
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
    
    from app import app, db, Event, Venue
    
    with app.app_context():
        # Find National Gallery of Art venue
        nga_venues = Venue.query.filter(
            Venue.name.ilike('%National Gallery%')
        ).all()
        
        print(f"📊 Found {len(nga_venues)} National Gallery venue(s) in local DB:")
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
        
        # Convert to list and access venue names while still in context
        events_list = list(all_events)
        for event in events_list:
            # Access venue to load it into session
            _ = event.venue
        
        # Restore DATABASE_URL
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        
        return events_list, nga_venues

def get_remote_events():
    """Get National Gallery of Art events from remote PostgreSQL database"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url or 'sqlite' in db_url.lower():
        print("❌ DATABASE_URL not set or points to SQLite. Cannot connect to remote database.")
        print("💡 Set DATABASE_URL environment variable to PostgreSQL connection string")
        print("💡 Or use Railway CLI: railway run python scripts/compare_nga_events.py")
        return [], []
    
    from app import app, db, Event, Venue
    
    with app.app_context():
        # Find National Gallery of Art venue
        nga_venues = Venue.query.filter(
            Venue.name.ilike('%National Gallery%')
        ).all()
        
        print(f"📊 Found {len(nga_venues)} National Gallery venue(s) in remote DB:")
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
        
        # Convert to list and access venue names while still in context
        events_list = list(all_events)
        for event in events_list:
            # Access venue to load it into session
            _ = event.venue
        
        return events_list, nga_venues

def event_to_dict(event):
    """Convert event to comparable dictionary"""
    # Safely get venue name
    venue_name = None
    try:
        if hasattr(event, 'venue') and event.venue:
            venue_name = event.venue.name
    except:
        pass
    
    return {
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
        'description': (event.description or '')[:100] if event.description else None,
    }

def compare_events(local_events, remote_events):
    """Compare local and remote events"""
    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80)
    
    local_dict = {e.id: event_to_dict(e) for e in local_events}
    remote_dict = {e.id: event_to_dict(e) for e in remote_events}
    
    local_ids = set(local_dict.keys())
    remote_ids = set(remote_dict.keys())
    
    only_local = local_ids - remote_ids
    only_remote = remote_ids - local_ids
    in_both = local_ids & remote_ids
    
    print(f"\n📊 Summary:")
    print(f"   Local events:  {len(local_events)}")
    print(f"   Remote events: {len(remote_events)}")
    print(f"   In both:       {len(in_both)}")
    print(f"   Only local:    {len(only_local)}")
    print(f"   Only remote:   {len(only_remote)}")
    
    if only_local:
        print(f"\n🔵 Events only in LOCAL database ({len(only_local)}):")
        for event_id in sorted(only_local):
            event = local_dict[event_id]
            print(f"   [{event_id}] {event['title'][:60]}")
            print(f"       Type: {event['event_type']}, Date: {event['start_date']}, Selected: {event['is_selected']}")
            print(f"       URL: {event['source_url']}")
    
    if only_remote:
        print(f"\n🔴 Events only in REMOTE database ({len(only_remote)}):")
        for event_id in sorted(only_remote):
            event = remote_dict[event_id]
            print(f"   [{event_id}] {event['title'][:60]}")
            print(f"       Type: {event['event_type']}, Date: {event['start_date']}, Selected: {event['is_selected']}")
            print(f"       URL: {event['source_url']}")
    
    # Compare events that exist in both
    if in_both:
        differences = []
        for event_id in sorted(in_both):
            local = local_dict[event_id]
            remote = remote_dict[event_id]
            
            diff_fields = []
            for key in ['title', 'event_type', 'start_date', 'end_date', 'start_time', 
                       'is_selected', 'is_baby_friendly', 'venue_id', 'source_url']:
                if local.get(key) != remote.get(key):
                    diff_fields.append(f"{key}: '{local.get(key)}' vs '{remote.get(key)}'")
            
            if diff_fields:
                differences.append((event_id, local['title'], diff_fields))
        
        if differences:
            print(f"\n⚠️  Events with differences ({len(differences)}):")
            for event_id, title, diff_fields in differences[:20]:  # Show first 20
                print(f"   [{event_id}] {title[:60]}")
                for diff in diff_fields:
                    print(f"       - {diff}")
            if len(differences) > 20:
                print(f"   ... and {len(differences) - 20} more")
        else:
            print(f"\n✅ All {len(in_both)} events in both databases are identical")
    
    # Group by date range
    print(f"\n📅 Events by date range:")
    today = datetime.now().date()
    
    def count_by_range(events_dict):
        past = 0
        this_week = 0
        future = 0
        no_date = 0
        
        for event in events_dict.values():
            if not event['start_date']:
                no_date += 1
                continue
            
            try:
                event_date = datetime.strptime(event['start_date'], '%Y-%m-%d').date()
                if event_date < today:
                    past += 1
                elif event_date <= (today + timedelta(days=6)):
                    this_week += 1
                else:
                    future += 1
            except:
                no_date += 1
        
        return {'past': past, 'this_week': this_week, 'future': future, 'no_date': no_date}
    
    from datetime import timedelta
    local_ranges = count_by_range(local_dict)
    remote_ranges = count_by_range(remote_dict)
    
    print(f"   LOCAL:  Past: {local_ranges['past']}, This week: {local_ranges['this_week']}, Future: {local_ranges['future']}, No date: {local_ranges['no_date']}")
    print(f"   REMOTE: Past: {remote_ranges['past']}, This week: {remote_ranges['this_week']}, Future: {remote_ranges['future']}, No date: {remote_ranges['no_date']}")
    
    # Group by event type
    print(f"\n📋 Events by type:")
    local_types = defaultdict(int)
    remote_types = defaultdict(int)
    
    for event in local_dict.values():
        local_types[event['event_type'] or 'None'] += 1
    for event in remote_dict.values():
        remote_types[event['event_type'] or 'None'] += 1
    
    all_types = set(local_types.keys()) | set(remote_types.keys())
    for event_type in sorted(all_types):
        local_count = local_types.get(event_type, 0)
        remote_count = remote_types.get(event_type, 0)
        if local_count != remote_count:
            print(f"   {event_type}: LOCAL={local_count}, REMOTE={remote_count} ⚠️")
        else:
            print(f"   {event_type}: {local_count} (both)")
    
    # Selected status
    local_selected = sum(1 for e in local_dict.values() if e['is_selected'])
    remote_selected = sum(1 for e in remote_dict.values() if e['is_selected'])
    print(f"\n✅ Selected events: LOCAL={local_selected}, REMOTE={remote_selected}")

def main():
    print("="*80)
    print("NATIONAL GALLERY OF ART EVENTS COMPARISON")
    print("="*80)
    
    print("\n🔵 Loading LOCAL events...")
    try:
        local_events, local_venues = get_local_events()
        print(f"✅ Found {len(local_events)} events in local database")
    except Exception as e:
        print(f"❌ Error loading local events: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n🔴 Loading REMOTE events...")
    try:
        remote_events, remote_venues = get_remote_events()
        print(f"✅ Found {len(remote_events)} events in remote database")
    except Exception as e:
        print(f"❌ Error loading remote events: {e}")
        import traceback
        traceback.print_exc()
        return
    
    compare_events(local_events, remote_events)

if __name__ == '__main__':
    main()

