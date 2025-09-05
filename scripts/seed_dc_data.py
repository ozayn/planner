#!/usr/bin/env python3
"""
Seed DC data from scraped results
"""

import json
import sys
import os
from datetime import datetime, date, time, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from app import City, Venue, Event, Tour, Exhibition, Festival, Photowalk

def load_dc_data():
    """Load scraped DC data from JSON file"""
    try:
        with open('dc_scraped_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: dc_scraped_data.json not found. Run dc_scraper.py first.")
        return None

def create_dc_city():
    """Create Washington DC city record"""
    dc_city = City.query.filter_by(name='Washington').first()
    if not dc_city:
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
    """Create venue records"""
    created_venues = {}
    
    for venue_data in venues_data:
        venue = Venue.query.filter_by(name=venue_data['name']).first()
        if not venue:
            venue = Venue(
                name=venue_data['name'],
                venue_type=venue_data['venue_type'],
                address=venue_data['address'],
                latitude=venue_data['latitude'],
                longitude=venue_data['longitude'],
                image_url=venue_data['image_url'],
                instagram_url=venue_data['instagram_url'],
                website_url=venue_data['website_url'],
                description=venue_data['description'],
                city_id=dc_city.id
            )
            db.session.add(venue)
            db.session.commit()
            print(f"Created venue: {venue.name}")
        
        created_venues[venue_data['name']] = venue
    
    return created_venues

def create_tours(venues, tours_data):
    """Create tour records"""
    created_tours = []
    
    for tour_data in tours_data:
        venue_name = tour_data['venue_name']
        if venue_name not in venues:
            print(f"Warning: Venue '{venue_name}' not found for tour '{tour_data['title']}'")
            continue
        
        venue = venues[venue_name]
        
        # Create tour directly (inherits from Event)
        tour = Tour(
            title=tour_data['title'],
            description=tour_data['description'],
            start_date=date.today() + timedelta(days=1),  # Tomorrow
            start_time=time.fromisoformat(tour_data['start_time']),
            end_time=time.fromisoformat(tour_data['end_time']),
            image_url=venue.image_url,
            url=tour_data['url'],
            event_type='tour',
            venue_id=venue.id,
            meeting_location=tour_data['meeting_location'],
            tour_type=tour_data['tour_type'],
            max_participants=tour_data['max_participants'],
            price=tour_data['price'],
            language=tour_data['language']
        )
        db.session.add(tour)
        created_tours.append(tour)
        print(f"Created tour: {tour_data['title']}")
    
    db.session.commit()
    return created_tours

def create_exhibitions(venues, exhibitions_data):
    """Create exhibition records"""
    created_exhibitions = []
    
    for exhibition_data in exhibitions_data:
        venue_name = exhibition_data['venue_name']
        if venue_name not in venues:
            print(f"Warning: Venue '{venue_name}' not found for exhibition '{exhibition_data['title']}'")
            continue
        
        venue = venues[venue_name]
        
        # Create exhibition directly (inherits from Event)
        exhibition = Exhibition(
            title=exhibition_data['title'],
            description=exhibition_data['description'],
            start_date=datetime.strptime(exhibition_data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(exhibition_data['end_date'], '%Y-%m-%d').date(),
            image_url=venue.image_url,
            url=exhibition_data['url'],
            event_type='exhibition',
            venue_id=venue.id,
            exhibition_location=exhibition_data['exhibition_location'],
            curator=exhibition_data['curator'],
            admission_price=exhibition_data['admission_price']
        )
        db.session.add(exhibition)
        created_exhibitions.append(exhibition)
        print(f"Created exhibition: {exhibition_data['title']}")
    
    db.session.commit()
    return created_exhibitions

def main():
    """Main seeding function"""
    print("Starting DC data seeding...")
    
    # Load scraped data
    dc_data = load_dc_data()
    if not dc_data:
        return
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Create DC city
        dc_city = create_dc_city()
        
        # Create venues
        venues = create_venues(dc_city, dc_data['venues'])
        
        # Create tours
        tours = create_tours(venues, dc_data['tours'])
        
        # Create exhibitions
        exhibitions = create_exhibitions(venues, dc_data['exhibitions'])
        
        print(f"\nSeeding complete!")
        print(f"Created {len(venues)} venues")
        print(f"Created {len(tours)} tours")
        print(f"Created {len(exhibitions)} exhibitions")
        print(f"Total events: {len(tours) + len(exhibitions)}")

if __name__ == "__main__":
    main()
