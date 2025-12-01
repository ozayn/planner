#!/usr/bin/env python3
"""
Create sample events for Washington DC to test the application
"""

import sys
import os
from datetime import datetime, date, time, timedelta

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Event, City, Venue

def create_sample_events():
    """Create sample events for Washington DC"""
    
    with app.app_context():
        # Get Washington DC city
        dc_city = City.query.filter_by(name='Washington').first()
        if not dc_city:
            print("❌ Washington DC city not found in database")
            return False
        
        # Get some venues
        venues = Venue.query.filter_by(city_id=dc_city.id).limit(5).all()
        if not venues:
            print("❌ No venues found for Washington DC")
            return False
        
        print(f"🏙️ Creating sample events for {dc_city.name}, {dc_city.state}")
        print(f"🏛️ Found {len(venues)} venues to use")
        
        # Sample events data
        sample_events = [
            {
                'title': 'Capitol Building Tour',
                'description': 'Guided tour of the historic Capitol Building including the Rotunda, Statuary Hall, and Crypt.',
                'event_type': 'tour',
                'start_time': '10:00',
                'end_time': '11:30',
                'start_location': 'Capitol Visitor Center',
                'venue_name': 'Capitol Building'
            },
            {
                'title': 'National Mall Walking Tour',
                'description': 'Explore the monuments and memorials along the National Mall with a knowledgeable guide.',
                'event_type': 'tour',
                'start_time': '14:00',
                'end_time': '16:00',
                'start_location': 'Lincoln Memorial',
                'venue_name': 'National Mall'
            },
            {
                'title': 'Smithsonian Natural History Exhibition',
                'description': 'Discover the wonders of natural history including dinosaur fossils and gem collections.',
                'event_type': 'exhibition',
                'start_time': '11:00',
                'end_time': '17:00',
                'start_location': 'Hall of Fossils',
                'venue_name': 'Smithsonian National Museum of Natural History'
            },
            {
                'title': 'Georgetown Photography Walk',
                'description': 'Capture the historic charm of Georgetown through photography with professional tips.',
                'event_type': 'photowalk',
                'start_time': '09:00',
                'end_time': '11:00',
                'start_location': 'Georgetown Waterfront',
                'venue_name': 'Georgetown'
            },
            {
                'title': 'White House Garden Tour',
                'description': 'Special spring tour of the White House gardens and grounds (advance registration required).',
                'event_type': 'tour',
                'start_time': '10:00',
                'end_time': '12:00',
                'start_location': 'White House Visitor Center',
                'venue_name': 'White House'
            }
        ]
        
        events_created = 0
        
        for event_data in sample_events:
            try:
                # Find the venue
                venue = None
                for v in venues:
                    if v.name == event_data['venue_name']:
                        venue = v
                        break
                
                if not venue:
                    print(f"⚠️ Venue '{event_data['venue_name']}' not found, using first available venue")
                    venue = venues[0]
                
                # Create the event
                event = Event()
                event.title = event_data['title']
                event.description = event_data['description']
                event.event_type = event_data['event_type']
                event.city_id = dc_city.id
                event.venue_id = venue.id
                event.source = 'sample'
                
                # Set dates (today and next few days)
                event.start_date = date.today() + timedelta(days=events_created)
                event.end_date = event.start_date
                
                # Set times
                event.start_time = datetime.strptime(event_data['start_time'], '%H:%M').time()
                event.end_time = datetime.strptime(event_data['end_time'], '%H:%M').time()
                
                # Set location
                event.start_location = event_data['start_location']
                
                # Add event-specific fields
                if event.event_type == 'tour':
                    event.tour_duration = 90  # minutes
                    event.meeting_point = event.start_location
                elif event.event_type == 'exhibition':
                    event.exhibition_location = event.start_location
                    event.admission_price = 0  # Free
                elif event.event_type == 'photowalk':
                    event.difficulty_level = 'Easy'
                    event.organizer = 'DC Photography Club'
                
                # Add to database
                db.session.add(event)
                events_created += 1
                
                print(f"✅ Created: {event.title} at {venue.name}")
                
            except Exception as e:
                print(f"❌ Error creating event '{event_data['title']}': {e}")
                continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n🎉 Successfully created {events_created} sample events for Washington DC!")
        return True

def main():
    """Main function"""
    success = create_sample_events()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

