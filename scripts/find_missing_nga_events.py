#!/usr/bin/env python3
"""
Find National Gallery of Art events that exist in local but not in remote
Compares by title, date, and other identifying information (not IDs)
"""

import json
from datetime import datetime

def normalize_event_key(event):
    """Create a normalized key for event comparison"""
    # Use title, start_date, and start_time as the unique identifier
    title = (event.get('title') or '').strip().lower()
    start_date = event.get('start_date') or ''
    start_time = event.get('start_time') or ''
    
    # Normalize time format (remove seconds if present)
    if start_time and ':' in start_time:
        time_parts = start_time.split(':')
        if len(time_parts) >= 2:
            start_time = f"{time_parts[0]}:{time_parts[1]}"
    
    return (title, start_date, start_time)

def load_events(filename):
    """Load events from JSON file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get('events', [])
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from {filename}: {e}")
        return []

def find_missing_events():
    """Find events in local that are missing in remote"""
    print("="*80)
    print("FINDING MISSING NATIONAL GALLERY OF ART EVENTS")
    print("="*80)
    
    local_events = load_events('nga_events_local.json')
    remote_events = load_events('nga_events_remote.json')
    
    if not local_events:
        print("❌ Could not load local events")
        return
    
    if not remote_events:
        print("❌ Could not load remote events")
        return
    
    print(f"\n📊 Loaded {len(local_events)} local events and {len(remote_events)} remote events")
    
    # Create normalized keys for remote events
    remote_keys = {normalize_event_key(e): e for e in remote_events}
    
    # Find events in local that don't exist in remote
    missing_events = []
    matched_events = []
    
    for local_event in local_events:
        key = normalize_event_key(local_event)
        if key in remote_keys:
            matched_events.append((local_event, remote_keys[key]))
        else:
            missing_events.append(local_event)
    
    print(f"\n✅ Matched: {len(matched_events)} events")
    print(f"❌ Missing in remote: {len(missing_events)} events")
    
    if missing_events:
        print(f"\n🔴 Events in LOCAL but NOT in REMOTE ({len(missing_events)}):")
        print()
        
        # Group by event type
        by_type = {}
        for event in missing_events:
            event_type = event.get('event_type', 'None')
            if event_type not in by_type:
                by_type[event_type] = []
            by_type[event_type].append(event)
        
        for event_type in sorted(by_type.keys()):
            events = by_type[event_type]
            print(f"  📋 {event_type.upper()} ({len(events)} events):")
            for event in sorted(events, key=lambda x: (x.get('start_date') or '', x.get('title') or '')):
                title = event.get('title', '')[:60]
                date = event.get('start_date', 'No date')
                time = event.get('start_time', '')
                if time:
                    time = time[:5]  # HH:MM format
                    print(f"     • {date} {time} - {title}")
                else:
                    print(f"     • {date} - {title}")
            print()
        
        # Summary by type
        print(f"\n📊 Summary by type:")
        for event_type in sorted(by_type.keys()):
            print(f"   {event_type}: {len(by_type[event_type])} missing")
        
        # Check for differences in matched events
        if matched_events:
            print(f"\n⚠️  Checking differences in matched events...")
            differences = []
            for local, remote in matched_events:
                diff_fields = []
                for key in ['is_selected', 'is_baby_friendly', 'event_type', 'venue_id']:
                    if local.get(key) != remote.get(key):
                        diff_fields.append(f"{key}: local={local.get(key)}, remote={remote.get(key)}")
                if diff_fields:
                    differences.append((local.get('title', '')[:50], diff_fields))
            
            if differences:
                print(f"   Found {len(differences)} matched events with differences:")
                for title, diffs in differences[:10]:
                    print(f"     • {title}")
                    for diff in diffs:
                        print(f"       - {diff}")
                if len(differences) > 10:
                    print(f"     ... and {len(differences) - 10} more")
            else:
                print(f"   ✅ All matched events are identical")
    
    # Also check for events in remote that aren't in local
    local_keys = {normalize_event_key(e): e for e in local_events}
    extra_remote = [e for e in remote_events if normalize_event_key(e) not in local_keys]
    
    if extra_remote:
        print(f"\n🔵 Events in REMOTE but NOT in LOCAL ({len(extra_remote)}):")
        for event in sorted(extra_remote, key=lambda x: (x.get('start_date') or '', x.get('title') or ''))[:10]:
            title = event.get('title', '')[:60]
            date = event.get('start_date', 'No date')
            print(f"     • {date} - {title}")
        if len(extra_remote) > 10:
            print(f"     ... and {len(extra_remote) - 10} more")

if __name__ == '__main__':
    find_missing_events()

