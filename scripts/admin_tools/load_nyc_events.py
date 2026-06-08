#!/usr/bin/env python3
"""
Load NYC Events into Database
Loads scraped NYC events from JSON file into the database
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Event, Venue, City

def load_nyc_events(json_file_path):
    """Load NYC events from JSON file into database"""
    
    with app.app_context():
        print(f"🏙️ Loading NYC events from {json_file_path}...")
        
        # Load JSON data
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {json_file_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON file: {e}")
            return False
        
        metadata = data.get('metadata', {})
        events_data = data.get('events', [])
        
        print(f"📊 Metadata: {metadata}")
        print(f"📋 Found {len(events_data)} events to load")
        
        # Get NYC city
        nyc_city = City.query.filter_by(name='New York').first()
        if not nyc_city:
            print("❌ NYC city not found in database")
            return False
        
        print(f"🏙️ Found NYC city: {nyc_city.name} (ID: {nyc_city.id})")
        
        # Get available venues for NYC
        available_venues = Venue.query.filter_by(city_id=nyc_city.id).all()
        print(f"🏛️ Found {len(available_venues)} venues in NYC")
        
        if not available_venues:
            print("⚠️ No venues found. Events will be created without venue associations.")
        
        events_loaded = 0
        events_skipped = 0
        
        # Check existing events for NYC (preserve existing events)
        existing_events = Event.query.filter_by(city_id=nyc_city.id).count()
        if existing_events > 0:
            print(f"📋 Found {existing_events} existing events for NYC - preserving them")
        
        # Only clear events from scraping sources to avoid duplicates
        scraped_source_events = Event.query.filter_by(city_id=nyc_city.id, source='scraped').count()
        if scraped_source_events > 0:
            print(f"🗑️ Clearing {scraped_source_events} existing scraped events for NYC...")
            Event.query.filter_by(city_id=nyc_city.id, source='scraped').delete()
            db.session.commit()
        
        # Create a set to track loaded event titles to prevent duplicates
        loaded_titles = set()
        
        for event_data in events_data:
            try:
                # Check for duplicate titles within this batch
                event_title = event_data.get('title', 'Untitled Event')
                if event_title in loaded_titles:
                    print(f"⚠️ Skipping duplicate event: {event_title}")
                    events_skipped += 1
                    continue
                
                # Create new event
                event = Event()
                
                # Basic fields
                event.title = event_title
                loaded_titles.add(event_title)
                event.description = event_data.get('description', '')
                event.event_type = event_data.get('event_type', 'tour')
                event.url = event_data.get('url', '')
                event.image_url = event_data.get('image_url', '')
                
                # Date handling
                start_date_str = event_data.get('start_date', '')
                if start_date_str:
                    try:
                        event.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        print(f"⚠️ Invalid start date format: {start_date_str}")
                        event.start_date = datetime.now().date()
                else:
                    event.start_date = datetime.now().date()
                
                end_date_str = event_data.get('end_date', '')
                if end_date_str and end_date_str != start_date_str:
                    try:
                        event.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        print(f"⚠️ Invalid end date format: {end_date_str}")
                        event.end_date = None
                else:
                    event.end_date = None
                
                # Time handling - convert string times to Python time objects
                from datetime import time
                start_time_str = event_data.get('start_time', '')
                if start_time_str:
                    try:
                        time_parts = start_time_str.split(':')
                        event.start_time = time(int(time_parts[0]), int(time_parts[1]))
                    except (ValueError, IndexError):
                        event.start_time = None
                else:
                    event.start_time = None
                
                end_time_str = event_data.get('end_time', '')
                if end_time_str:
                    try:
                        time_parts = end_time_str.split(':')
                        event.end_time = time(int(time_parts[0]), int(time_parts[1]))
                    except (ValueError, IndexError):
                        event.end_time = None
                else:
                    event.end_time = None
                
                # Location and venue
                event.location = event_data.get('venue_name', '')
                event.address = event_data.get('address', '')
                
                # Try to find matching venue
                venue_name = event_data.get('venue_name', '')
                if venue_name:
                    matching_venue = None
                    for venue in available_venues:
                        if venue_name.lower() in venue.name.lower() or venue.name.lower() in venue_name.lower():
                            matching_venue = venue
                            break
                    
                    if matching_venue:
                        event.venue_id = matching_venue.id
                        print(f"🔗 Linked to venue: {matching_venue.name}")
                    else:
                        print(f"⚠️ No matching venue found for: {venue_name}")
                
                # Additional fields
                # Note: price field expects float, so we'll skip it for now
                # event.price = event_data.get('price', '')
                event.organizer = event_data.get('organizer', '')
                event.contact_info = event_data.get('contact_info', '')
                event.accessibility = event_data.get('accessibility', '')
                event.age_restrictions = event_data.get('age_restrictions', '')
                event.registration_required = event_data.get('registration_required', False)
                event.capacity = event_data.get('capacity', None)
                
                # Tags as JSON string
                tags = event_data.get('tags', [])
                if tags:
                    event.tags = json.dumps(tags)
                
                # Set city and source
                event.city_id = nyc_city.id
                event.source = 'scraped'
                
                # Event type specific fields
                if event.event_type == 'tour':
                    event.meeting_location = event_data.get('meeting_location', '')
                    event.tour_duration = event_data.get('tour_duration', '')
                    event.tour_guide = event_data.get('tour_guide', '')
                elif event.event_type == 'exhibition':
                    event.exhibition_curator = event_data.get('exhibition_curator', '')
                    event.exhibition_theme = event_data.get('exhibition_theme', '')
                    event.artwork_count = event_data.get('artwork_count', None)
                elif event.event_type == 'workshop':
                    event.skill_level = event_data.get('skill_level', '')
                    event.materials_provided = event_data.get('materials_provided', '')
                    event.instructor = event_data.get('instructor', '')
                elif event.event_type == 'photowalk':
                    event.difficulty_level = event_data.get('difficulty_level', 'Easy')
                    event.equipment_needed = event_data.get('equipment_needed', '')
                    event.organizer = event_data.get('organizer', '')
                
                # Add to database
                db.session.add(event)
                events_loaded += 1
                
                if events_loaded % 5 == 0:
                    print(f"📝 Loaded {events_loaded} events...")
                
            except Exception as e:
                print(f"⚠️ Error loading event '{event_data.get('title', 'Unknown')}': {e}")
                events_skipped += 1
                continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"✅ Successfully loaded {events_loaded} NYC events")
        if events_skipped > 0:
            print(f"⚠️ Skipped {events_skipped} events due to errors")
        
        return True

def main():
    """Main function"""
    # Look for the most recent NYC events file (both real and sample)
    import glob
    nyc_files = glob.glob('nyc_*_events_*.json')
    if not nyc_files:
        print("❌ No NYC events files found. Run the scraper first.")
        return False
    
    # Use the most recent file
    latest_file = max(nyc_files, key=os.path.getctime)
    print(f"📄 Using latest file: {latest_file}")
    
    success = load_nyc_events(latest_file)
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
