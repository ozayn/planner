#!/usr/bin/env python3
"""
Update events.json with current database events
This function will be imported and used in other scripts
"""

import json
import os
from pathlib import Path
from datetime import datetime

def update_events_json():
    """Update events.json with current database events"""
    try:
        from app import app, Event, City, Venue
        
        with app.app_context():
            # Get all events from database with their cities and venues
            events = Event.query.join(City).all()
            
            # Create the JSON structure (similar format to venues.json)
            events_data = {}
            
            # Group events by city
            for event in events:
                city_id = str(event.city_id)
                
                if city_id not in events_data:
                    events_data[city_id] = {
                        "name": event.city.name,
                        "events": []
                    }
                
                # Create event entry
                event_entry = {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description or "",
                    "event_type": event.event_type,
                    "start_date": event.start_date.isoformat(),
                    "end_date": event.end_date.isoformat() if event.end_date else "",
                    "start_time": event.start_time.strftime('%H:%M') if event.start_time else "",
                    "end_time": event.end_time.strftime('%H:%M') if event.end_time else "",
                    "start_location": event.start_location or "",
                    "end_location": event.end_location or "",
                    "venue_id": event.venue_id,
                    "venue_name": event.venue.name if event.venue else "",
                    "city_id": event.city_id,
                    "city_name": event.city.name,
                    "image_url": event.image_url or "",
                    "url": event.url or "",
                    "is_selected": event.is_selected,
                    
                    # Geographic coordinates
                    "start_latitude": event.start_latitude,
                    "start_longitude": event.start_longitude,
                    "end_latitude": event.end_latitude,
                    "end_longitude": event.end_longitude,
                    
                    # Tour-specific fields
                    "tour_type": event.tour_type or "",
                    "max_participants": event.max_participants,
                    "price": event.price,
                    "language": event.language or "English",
                    
                    # Exhibition-specific fields
                    "exhibition_location": event.exhibition_location or "",
                    "curator": event.curator or "",
                    "admission_price": event.admission_price,
                    
                    # Festival-specific fields
                    "festival_type": event.festival_type or "",
                    "multiple_locations": event.multiple_locations,
                    
                    # Photowalk-specific fields
                    "difficulty_level": event.difficulty_level or "",
                    "equipment_needed": event.equipment_needed or "",
                    "organizer": event.organizer or "",
                    
                    # Timestamps
                    "created_at": event.created_at.isoformat() if event.created_at else "",
                    "updated_at": event.updated_at.isoformat() if event.updated_at else ""
                }
                
                events_data[city_id]["events"].append(event_entry)
            
            # Create backup of existing events.json if it exists
            events_file = Path("data/events.json")
            if events_file.exists():
                backup_file = f"data/backups/events.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                
                import shutil
                shutil.copy2(events_file, backup_file)
                print(f"📋 Backup created: {backup_file}")
            
            # Save to events.json
            with open(events_file, 'w') as f:
                json.dump(events_data, f, indent=2, ensure_ascii=False)
            
            total_events = sum(len(city_data["events"]) for city_data in events_data.values())
            print(f"✅ events.json updated successfully!")
            print(f"   Total events: {total_events}")
            print(f"   Cities: {len(events_data)}")
            
            # Show breakdown by event type
            event_types = {}
            for city_data in events_data.values():
                for event in city_data["events"]:
                    event_type = event["event_type"]
                    event_types[event_type] = event_types.get(event_type, 0) + 1
            
            print(f"   Event types: {event_types}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating events.json: {e}")
        return False

if __name__ == "__main__":
    success = update_events_json()
    if not success:
        exit(1)
