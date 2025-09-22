#!/usr/bin/env python3
"""
Seed DC Event Data
Loads scraped events into the database
"""

import json
import os
import sys
from datetime import datetime, time
import random

# Add the parent directory to the path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Event, City, Venue

def load_scraped_events():
    """Load events from scraped data file into database"""
    
    # Check if scraped data file exists
    if not os.path.exists('dc_scraped_data.json'):
        print("❌ No scraped data file found. Run dc_scraper_progress.py first.")
        return False
    
    try:
        # Load scraped data
        with open('dc_scraped_data.json', 'r') as f:
            scraped_data = json.load(f)
        
        events_data = scraped_data.get('events', [])
        print(f"📊 Found {len(events_data)} events to load")
        
        # Get Washington DC city
        dc_city = City.query.filter_by(name='Washington').first()
        if not dc_city:
            print("❌ Washington DC city not found in database")
            return False
        
        city_display = f"{dc_city.name}, {dc_city.state}" if dc_city.state else f"{dc_city.name}, {dc_city.country}"
        print(f"🏙️ Loading events for {city_display}")
        
        # Get available venues for this city
        available_venues = Venue.query.filter_by(city_id=dc_city.id).all()
        print(f"🏛️ Found {len(available_venues)} venues in database")
        
        if not available_venues:
            print("⚠️ No venues found. Events will be created without venue associations.")
        
        events_loaded = 0
        events_skipped = 0
        
        # Clear existing events for DC (optional - comment out to keep existing events)
        existing_events = Event.query.filter_by(city_id=dc_city.id).count()
        if existing_events > 0:
            print(f"🗑️ Clearing {existing_events} existing events for DC...")
            Event.query.filter_by(city_id=dc_city.id).delete()
            db.session.commit()
        
        for event_data in events_data:
            try:
                # Create new event
                event = Event()
                
                # Basic fields
                event.title = event_data.get('title', 'Untitled Event')
                event.description = event_data.get('description', '')
                event.event_type = event_data.get('event_type', 'tour')
                event.url = event_data.get('url', '')
                event.image_url = event_data.get('image_url', '')
                
                # Dates and times
                start_date_str = event_data.get('start_date')
                end_date_str = event_data.get('end_date')
                
                if start_date_str:
                    event.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                else:
                    event.start_date = datetime.now().date()
                
                if end_date_str:
                    event.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                else:
                    event.end_date = event.start_date
                
                # Times
                start_time_str = event_data.get('start_time')
                end_time_str = event_data.get('end_time')
                
                if start_time_str:
                    event.start_time = datetime.strptime(start_time_str, '%H:%M').time()
                
                if end_time_str:
                    event.end_time = datetime.strptime(end_time_str, '%H:%M').time()
                
                # Location
                event.start_location = event_data.get('start_location', '')
                event.end_location = event_data.get('end_location', '')
                
                # Associate with city
                event.city_id = dc_city.id
                
                # Associate with venue if available
                venue_id = event_data.get('venue_id')
                if venue_id and available_venues:
                    # Find a venue with this ID or pick a random one
                    venue = next((v for v in available_venues if v.id == venue_id), None)
                    if not venue:
                        venue = random.choice(available_venues)
                    event.venue_id = venue.id
                    event.start_location = venue.name if not event.start_location else event.start_location
                
                # Event type specific fields
                if event.event_type == 'tour':
                    event.tour_type = event_data.get('tour_type', 'Guided')
                    event.max_participants = event_data.get('max_participants')
                    event.price = event_data.get('price')
                    event.language = event_data.get('language', 'English')
                    
                elif event.event_type == 'exhibition':
                    event.exhibition_location = event_data.get('exhibition_location', '')
                    event.curator = event_data.get('curator', '')
                    event.admission_price = event_data.get('admission_price')
                    
                elif event.event_type == 'festival':
                    event.festival_type = event_data.get('festival_type', 'Cultural')
                    event.multiple_locations = event_data.get('multiple_locations', False)
                    
                elif event.event_type == 'photowalk':
                    event.difficulty_level = event_data.get('difficulty_level', 'Easy')
                    event.equipment_needed = event_data.get('equipment_needed', '')
                    event.organizer = event_data.get('organizer', '')
                
                # Add to database
                db.session.add(event)
                events_loaded += 1
                
                if events_loaded % 10 == 0:
                    print(f"📝 Loaded {events_loaded} events...")
                
            except Exception as e:
                print(f"⚠️ Error loading event '{event_data.get('title', 'Unknown')}': {e}")
                events_skipped += 1
                continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"✅ Successfully loaded {events_loaded} events")
        if events_skipped > 0:
            print(f"⚠️ Skipped {events_skipped} events due to errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading events: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False

def main():
    """Main seeding function"""
    with app.app_context():
        success = load_scraped_events()
        return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
