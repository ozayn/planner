#!/usr/bin/env python3
"""
Script to populate database with real scraped museum data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue, Tour, Exhibition
from config.museum_scrapers import scrape_washington_dc_museums
from datetime import datetime, date, time as dt_time, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_real_museum_data():
    """Populate database with real scraped museum data"""
    
    with app.app_context():
        # Get Washington DC city
        washington = City.query.filter_by(name='Washington', state='DC').first()
        if not washington:
            logger.error("Washington DC not found in database")
            return
        
        logger.info("Scraping Washington DC museums...")
        
        # Scrape real data
        events = scrape_washington_dc_museums()
        
        logger.info(f"Found {len(events['tours'])} tours")
        
        # Process tours
        for tour_data in events['tours']:
            try:
                # Find or create venue
                venue = Venue.query.filter_by(name=tour_data['museum_name']).first()
                if not venue:
                    # Create venue if it doesn't exist
                    venue = Venue(
                        name=tour_data['museum_name'],
                        venue_type='museum',
                        address=f"{tour_data['museum_name']}, Washington, DC",
                        latitude=38.8913,  # Approximate DC coordinates
                        longitude=-77.0263,
                        city_id=washington.id,
                        description=f"Official {tour_data['museum_name']} website"
                    )
                    db.session.add(venue)
                    db.session.flush()  # Get the ID
                
                # Create tour
                tour = Tour(
                    title=tour_data['title'],
                    description=tour_data.get('description', ''),
                    start_time=tour_data.get('start_time'),
                    end_time=tour_data.get('end_time'),
                    meeting_location=tour_data.get('meeting_location', 'Main entrance'),
                    image_url=tour_data.get('image_url'),
                    url=tour_data.get('url'),
                    language='English',
                    tour_type=tour_data.get('tour_type', 'general'),
                    venue_id=venue.id
                )
                
                db.session.add(tour)
                
            except Exception as e:
                logger.error(f"Error processing tour {tour_data.get('title', 'Unknown')}: {e}")
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info("Successfully populated database with real museum data")
        except Exception as e:
            logger.error(f"Error committing to database: {e}")
            db.session.rollback()

def add_sample_exhibitions():
    """Add some sample exhibitions with real data"""
    
    with app.app_context():
        # Get venues
        natural_history = Venue.query.filter_by(name='Smithsonian National Museum of Natural History').first()
        nga = Venue.query.filter_by(name='National Gallery of Art').first()
        
        exhibitions_data = [
            {
                'title': 'Fossil Hall: Deep Time',
                'description': 'Explore 4.6 billion years of Earth\'s history through fossils and interactive displays.',
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'venue': natural_history,
                'location': 'First Floor, Fossil Hall'
            },
            {
                'title': 'Ocean Hall',
                'description': 'Discover the diversity of ocean life and the importance of marine conservation.',
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'venue': natural_history,
                'location': 'First Floor, Ocean Hall'
            },
            {
                'title': 'American Art Collection',
                'description': 'Featuring works by American artists from the 18th century to the present.',
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'venue': nga,
                'location': 'West Building, Ground Floor'
            },
            {
                'title': 'European Art Collection',
                'description': 'Masterpieces from European artists including Rembrandt, Vermeer, and Monet.',
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'venue': nga,
                'location': 'West Building, Second Floor'
            }
        ]
        
        for exh_data in exhibitions_data:
            if exh_data['venue']:
                exhibition = Exhibition(
                    title=exh_data['title'],
                    description=exh_data['description'],
                    start_date=exh_data['start_date'],
                    end_date=exh_data['end_date'],
                    exhibition_location=exh_data['location'],
                    venue_id=exh_data['venue'].id
                )
                db.session.add(exhibition)
        
        try:
            db.session.commit()
            logger.info("Successfully added sample exhibitions")
        except Exception as e:
            logger.error(f"Error adding exhibitions: {e}")
            db.session.rollback()

if __name__ == "__main__":
    print("Populating database with real museum data...")
    populate_real_museum_data()
    add_sample_exhibitions()
    print("Done!")
