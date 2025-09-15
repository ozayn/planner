#!/usr/bin/env python3
"""
Add Event from Instagram/Website Source Script
Creates events from Instagram posts, websites, or other online sources
"""

import sys
import os
from datetime import datetime, time
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, City, Venue

def add_event_from_source():
    """Add an event from an Instagram/website source"""
    print("📱 Adding Event from Instagram/Website Source...")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Example: Princeton Instagram photowalk
            print("🔍 Example: Adding Princeton Instagram photowalk...")
            
            # Find Princeton city
            princeton_city = City.query.filter_by(name="Princeton").first()
            if not princeton_city:
                print("❌ Princeton city not found in database")
                return False
            
            # Example event data (you would modify this for real sources)
            event_data = {
                "title": "Princeton University Architecture Photowalk",
                "description": "Join us for a photography walk around Princeton's stunning Gothic Revival architecture. Perfect for all skill levels!",
                "event_type": "photowalk",
                "start_date": datetime(2025, 9, 20).date(),
                "start_time": time(10, 0),
                "end_time": time(12, 0),
                "start_location": "Nassau Hall, Princeton University",
                "end_location": "Princeton University Chapel",
                "city_id": princeton_city.id,
                "url": "https://www.instagram.com/p/ABC123princetonphotowalk/",  # Instagram post URL
                "organizer": "@princetonphotoclub",  # Instagram handle
                "max_participants": 15,
                "price": 0.0,
                "language": "English",
                "difficulty_level": "Easy",
                "equipment_needed": "Camera or smartphone, comfortable walking shoes"
            }
            
            # Check if event already exists (by title and date)
            existing_event = Event.query.filter(
                Event.title == event_data['title'],
                Event.start_date == event_data['start_date'],
                Event.city_id == event_data['city_id']
            ).first()
            
            if existing_event:
                print(f"⚠️  Event already exists: {existing_event.title}")
                return True
            
            # Create new event
            event = Event(
                title=event_data['title'],
                description=event_data['description'],
                event_type=event_data['event_type'],
                start_date=event_data['start_date'],
                start_time=event_data['start_time'],
                end_time=event_data['end_time'],
                start_location=event_data['start_location'],
                end_location=event_data['end_location'],
                city_id=event_data['city_id'],
                url=event_data['url'],
                organizer=event_data['organizer'],
                max_participants=event_data['max_participants'],
                price=event_data['price'],
                language=event_data['language'],
                difficulty_level=event_data['difficulty_level'],
                equipment_needed=event_data['equipment_needed'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(event)
            db.session.commit()
            
            print(f"✅ Event created successfully!")
            print(f"   Title: {event.title}")
            print(f"   Source: {event.url}")
            print(f"   Organizer: {event.organizer}")
            print(f"   Date: {event.start_date} {event.start_time}-{event.end_time}")
            
            # Update events.json
            try:
                from scripts.update_events_json import update_events_json
                update_events_json()
                print("✅ events.json updated successfully!")
            except Exception as json_error:
                print(f"⚠️ Warning: Could not update events.json: {json_error}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating event: {e}")
            db.session.rollback()
            return False

def add_event_interactive():
    """Interactive function to add events from sources"""
    print("📱 Interactive Event Source Addition")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Get user input
            print("Enter event details:")
            title = input("Event title: ").strip()
            description = input("Description: ").strip()
            event_type = input("Event type (tour/exhibition/festival/photowalk): ").strip()
            city_name = input("City name: ").strip()
            start_date_str = input("Start date (YYYY-MM-DD): ").strip()
            start_time_str = input("Start time (HH:MM): ").strip()
            end_time_str = input("End time (HH:MM): ").strip()
            start_location = input("Start location: ").strip()
            source_url = input("Source URL (Instagram/website): ").strip()
            organizer = input("Organizer (@handle or name): ").strip()
            
            # Find city
            city = City.query.filter_by(name=city_name).first()
            if not city:
                print(f"❌ City '{city_name}' not found")
                return False
            
            # Parse date and time
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Create event
            event = Event(
                title=title,
                description=description,
                event_type=event_type,
                start_date=start_date,
                start_time=start_time,
                end_time=end_time,
                start_location=start_location,
                city_id=city.id,
                url=source_url,
                organizer=organizer,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(event)
            db.session.commit()
            
            print(f"✅ Event created successfully!")
            print(f"   ID: {event.id}")
            print(f"   Title: {event.title}")
            print(f"   Source: {event.url}")
            
            # Update events.json
            try:
                from scripts.update_events_json import update_events_json
                update_events_json()
                print("✅ events.json updated successfully!")
            except Exception as json_error:
                print(f"⚠️ Warning: Could not update events.json: {json_error}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating event: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Add example Princeton Instagram event")
    print("2. Interactive event addition")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        success = add_event_from_source()
    elif choice == "2":
        success = add_event_interactive()
    else:
        print("Invalid choice")
        success = False
    
    if not success:
        sys.exit(1)
