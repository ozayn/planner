#!/usr/bin/env python3
"""
Compare National Gallery of Art events from two JSON export files
Usage:
  1. Export local: python scripts/export_nga_events.py local
  2. Export remote: railway run python scripts/export_nga_events.py remote
  3. Compare: python scripts/compare_nga_json.py
"""

import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict

def load_json_file(filename):
    """Load JSON export file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from {filename}: {e}")
        return None

def compare_events():
    """Compare events from local and remote JSON files"""
    print("="*80)
    print("NATIONAL GALLERY OF ART EVENTS COMPARISON")
    print("="*80)
    
    local_data = load_json_file('nga_events_local.json')
    remote_data = load_json_file('nga_events_remote.json')
    
    if not local_data:
        print("\n❌ Could not load local events. Run: python scripts/export_nga_events.py local")
        return
    
    if not remote_data:
        print("\n❌ Could not load remote events. Run: railway run python scripts/export_nga_events.py remote")
        print("   (Make sure you're logged in: railway login)")
        return
    
    local_events = {e['id']: e for e in local_data.get('events', [])}
    remote_events = {e['id']: e for e in remote_data.get('events', [])}
    
    local_ids = set(local_events.keys())
    remote_ids = set(remote_events.keys())
    
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
        for event_id in sorted(only_local)[:20]:  # Show first 20
            event = local_events[event_id]
            print(f"   [{event_id}] {event['title'][:60]}")
            print(f"       Type: {event['event_type']}, Date: {event['start_date']}, Selected: {event['is_selected']}")
        if len(only_local) > 20:
            print(f"   ... and {len(only_local) - 20} more")
    
    if only_remote:
        print(f"\n🔴 Events only in REMOTE database ({len(only_remote)}):")
        for event_id in sorted(only_remote)[:20]:  # Show first 20
            event = remote_events[event_id]
            print(f"   [{event_id}] {event['title'][:60]}")
            print(f"       Type: {event['event_type']}, Date: {event['start_date']}, Selected: {event['is_selected']}")
        if len(only_remote) > 20:
            print(f"   ... and {len(only_remote) - 20} more")
    
    # Compare events that exist in both
    if in_both:
        differences = []
        for event_id in sorted(in_both):
            local = local_events[event_id]
            remote = remote_events[event_id]
            
            diff_fields = []
            for key in ['title', 'event_type', 'start_date', 'end_date', 'start_time', 
                       'is_selected', 'is_baby_friendly', 'venue_id', 'source_url']:
                if local.get(key) != remote.get(key):
                    diff_fields.append(f"{key}: '{local.get(key)}' vs '{remote.get(key)}'")
            
            if diff_fields:
                differences.append((event_id, local['title'], diff_fields))
        
        if differences:
            print(f"\n⚠️  Events with differences ({len(differences)}):")
            for event_id, title, diff_fields in differences[:10]:  # Show first 10
                print(f"   [{event_id}] {title[:60]}")
                for diff in diff_fields:
                    print(f"       - {diff}")
            if len(differences) > 10:
                print(f"   ... and {len(differences) - 10} more")
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
    
    local_ranges = count_by_range(local_events)
    remote_ranges = count_by_range(remote_events)
    
    print(f"   LOCAL:  Past: {local_ranges['past']}, This week: {local_ranges['this_week']}, Future: {local_ranges['future']}, No date: {local_ranges['no_date']}")
    print(f"   REMOTE: Past: {remote_ranges['past']}, This week: {remote_ranges['this_week']}, Future: {remote_ranges['future']}, No date: {remote_ranges['no_date']}")
    
    # Group by event type
    print(f"\n📋 Events by type:")
    local_types = defaultdict(int)
    remote_types = defaultdict(int)
    
    for event in local_events.values():
        local_types[event['event_type'] or 'None'] += 1
    for event in remote_events.values():
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
    local_selected = sum(1 for e in local_events.values() if e['is_selected'])
    remote_selected = sum(1 for e in remote_events.values() if e['is_selected'])
    print(f"\n✅ Selected events: LOCAL={local_selected}, REMOTE={remote_selected}")

if __name__ == '__main__':
    compare_events()

