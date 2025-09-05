#!/usr/bin/env python3
"""
DC Data Seeder
Seeds the database with scraped data from dc_scraped_data.json
"""

import json
import sys
import os
from datetime import datetime, date, time, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from app import City, Venue, Event, Tour, Exhibition, Festival, Photowalk

def load_scraped_data():
    """Load scraped data from JSON file"""
    try:
        with open('dc_scraped_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: dc_scraped_data.json not found. Run the scraper first.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None

def create_dc_city():
    """Create Washington DC city"""
    dc_city = City(
        name='Washington',
        state='DC',
        country='United States',
        timezone='America/New_York'
    )
    db.session.add(dc_city)
    db.session.commit()
    print(f"Created DC city: {dc_city.id}")
    return dc_city

def create_venues(dc_city, venues_data):
    """Create venue records from real data"""
    created_venues = {}
    
    for venue_data in venues_data:
        venue = Venue(
            name=venue_data['name'],
            venue_type=venue_data.get('venue_type', 'museum'),
            address=venue_data['address'],
            latitude=venue_data.get('latitude', 38.9072),  # Default DC coordinates
            longitude=venue_data.get('longitude', -77.0369),
            image_url=venue_data.get('image_url', ''),
            website_url=venue_data['url'],
            description=venue_data['description'],
            instagram_url=venue_data.get('instagram_url', ''),
            city_id=dc_city.id
        )
        db.session.add(venue)
        created_venues[venue_data['name']] = venue
        print(f"Created venue: {venue_data['name']}")
    
    db.session.commit()
    return created_venues

def create_events_from_scraped_data(venues, events_data):
    """Create event records from scraped data"""
    created_events = []
    
    for event_data in events_data:
        print(f"Processing event data: {event_data}")
        venue_name = event_data.get('venue_name', 'Unknown Venue')
        
        if venue_name not in venues:
            print(f"Warning: Venue '{venue_name}' not found for event '{event_data.get('title', 'Unknown')}'")
            continue
        
        venue = venues[venue_name]
        
        # Determine event type based on source or content
        event_type = 'tour'  # Default to tour
        if 'exhibition' in event_data.get('title', '').lower():
            event_type = 'exhibition'
        elif 'performance' in event_data.get('description', '').lower():
            event_type = 'festival'
        
        # Create specific event type directly
        if event_type == 'tour':
            event = Tour(
                title=event_data['title'],
                description=event_data['description'],
                start_date=datetime.strptime(event_data['start_date'], '%Y-%m-%d').date(),
                start_time=time(10, 0),  # Default time
                end_time=time(11, 0),    # Default time
                image_url=venue.image_url,
                url=event_data.get('event_url', ''),
                event_type=event_type,
                venue_id=venue.id,
                meeting_location=venue.address,
                tour_type='general',
                max_participants=25,
                price=0.0,
                language='English'
            )
        elif event_type == 'exhibition':
            event = Exhibition(
                title=event_data['title'],
                description=event_data['description'],
                start_date=datetime.strptime(event_data['start_date'], '%Y-%m-%d').date(),
                start_time=time(10, 0),  # Default time
                end_time=time(11, 0),    # Default time
                image_url=venue.image_url,
                url=event_data.get('event_url', ''),
                event_type=event_type,
                venue_id=venue.id,
                exhibition_location='Main Gallery',
                curator='Museum Staff',
                admission_price=0.0
            )
        else:
            # Default to Tour for other types
            event = Tour(
                title=event_data['title'],
                description=event_data['description'],
                start_date=datetime.strptime(event_data['start_date'], '%Y-%m-%d').date(),
                start_time=time(10, 0),  # Default time
                end_time=time(11, 0),    # Default time
                image_url=venue.image_url,
                url=event_data.get('event_url', ''),
                event_type=event_type,
                venue_id=venue.id,
                meeting_location=venue.address,
                tour_type='general',
                max_participants=25,
                price=0.0,
                language='English'
            )
        
        db.session.add(event)
        created_events.append(event)
        print(f"Created event: {event_data['title']}")
    
    db.session.commit()
    return created_events

def main():
    """Main seeding function"""
    print("Starting DC data seeding...")
    
    # Load scraped data
    scraped_data = load_scraped_data()
    if not scraped_data:
        return
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Clear existing data for Washington DC
        print("Clearing existing DC data...")
        dc_city = City.query.filter_by(name='Washington').first()
        if dc_city:
            # Delete all events for DC venues
            for venue in dc_city.venues:
                # Delete tours
                tours = Tour.query.filter_by(venue_id=venue.id).all()
                for tour in tours:
                    Event.query.filter_by(id=tour.id).delete()
                    db.session.delete(tour)
                
                # Delete exhibitions
                exhibitions = Exhibition.query.filter_by(venue_id=venue.id).all()
                for exhibition in exhibitions:
                    Event.query.filter_by(id=exhibition.id).delete()
                    db.session.delete(exhibition)
                
                db.session.delete(venue)
            db.session.delete(dc_city)
            db.session.commit()
            print("Cleared existing DC data")
        
        # Create DC city
        dc_city = create_dc_city()
        
        # Create venues
        venues = create_venues(dc_city, scraped_data['venues'])
        
        # Create events from scraped data
        events = create_events_from_scraped_data(venues, scraped_data['events'])
        
        print(f"\nData seeding complete!")
        print(f"Created {len(venues)} venues")
        print(f"Created {len(events)} events")

if __name__ == "__main__":
    main()
