#!/usr/bin/env python3
"""
Update events.json from database
Syncs the events.json file with the current database state
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Event

def sanitize_json_file_for_backup(source_file, backup_file):
    """Create a sanitized backup of the JSON file"""
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Sanitize any sensitive data if needed
        sanitized_data = data  # No specific sanitization needed for events.json
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error creating sanitized backup: {e}")
        import shutil
        shutil.copy2(source_file, backup_file)

def update_events_json():
    """Update events.json from database"""
    print("🔄 Updating events.json from database...")
    
    with app.app_context():
        try:
            events = Event.query.order_by(Event.id).all()
            print(f"📊 Found {len(events)} events in database")

            events_data = {}
            for event in events:
                event_data = {
                    "title": event.title,
                    "description": event.description or "",
                    "start_date": event.start_date.isoformat() if event.start_date else None,
                    "start_time": event.start_time.isoformat() if event.start_time else None,
                    "end_time": event.end_time.isoformat() if event.end_time else None,
                    "event_type": event.event_type or "",
                    "venue_id": event.venue_id,
                    "venue_name": event.venue.name if event.venue else "",
                    "city_name": event.venue.city.name if event.venue and event.venue.city else "",
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "updated_at": event.updated_at.isoformat() if event.updated_at else None
                }
                events_data[str(event.id)] = event_data
                print(f"  Added: {event.title} (ID: {event.id}) - {event_data['city_name']}")

            final_data = {
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "description": "Events exported from database - always most updated version",
                    "total_events": len(events),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "events": events_data
            }

            events_file = Path("data/events.json")
            if events_file.exists():
                backup_dir = Path("data/backups")
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / f"events.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                sanitize_json_file_for_backup(events_file, backup_file)
                print(f"📦 Created backup: {backup_file}")

            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Successfully updated events.json with {len(events)} events")
            
            # Show some statistics
            event_types = {}
            cities = {}
            venues = {}
            for event in events:
                # Count event types
                event_type = event.event_type or "Unknown"
                event_types[event_type] = event_types.get(event_type, 0) + 1
                
                # Count cities
                city_name = event.venue.city.name if event.venue and event.venue.city else "Unknown"
                cities[city_name] = cities.get(city_name, 0) + 1
                
                # Count venues
                venue_name = event.venue.name if event.venue else "Unknown"
                venues[venue_name] = venues.get(venue_name, 0) + 1
            
            print(f"\n📊 Event Statistics:")
            print(f"  Total Events: {len(events)}")
            print(f"  Event Types: {len(event_types)}")
            print(f"  Cities: {len(cities)}")
            print(f"  Venues: {len(venues)}")
            
            if event_types:
                print(f"\n🎭 Top Event Types:")
                for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"    {event_type}: {count}")
            
            if cities:
                print(f"\n🏙️ Top Cities:")
                for city_name, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"    {city_name}: {count}")
            
            return True

        except Exception as e:
            print(f"❌ Error updating events.json: {e}")
            return False

if __name__ == '__main__':
    with app.app_context():
        sys.exit(0 if update_events_json() else 1)




