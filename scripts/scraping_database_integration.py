#!/usr/bin/env python3
"""
Database Integration for Event Scraping System
Saves scraped events to the database with proper validation and deduplication.
"""

import os
import sys
from datetime import datetime, date
from typing import List, Optional
import logging

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Import our app and models
from app import app, db, Event, Venue, City

class EventDatabaseManager:
    """Manages saving scraped events to the database."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def save_scraped_events(self, scraped_events: List, city_id: int = 1) -> int:
        """Save scraped events to the database."""
        saved_count = 0
        
        with app.app_context():
            for scraped_event in scraped_events:
                try:
                    # Check if event already exists
                    if self._event_exists(scraped_event):
                        self.logger.info(f"Event already exists: {scraped_event.title}")
                        continue
                    
                    # Create new event
                    event = self._create_event_from_scraped(scraped_event, city_id)
                    
                    if event:
                        db.session.add(event)
                        db.session.commit()
                        saved_count += 1
                        self.logger.info(f"Saved event: {event.title}")
                    
                except Exception as e:
                    self.logger.error(f"Error saving event {scraped_event.title}: {e}")
                    db.session.rollback()
        
        return saved_count
    
    def _event_exists(self, scraped_event) -> bool:
        """Check if event already exists in database."""
        # Check by title and start_date
        query = Event.query.filter(
            Event.title.ilike(f"%{scraped_event.title}%")
        )
        
        if scraped_event.start_date:
            query = query.filter(Event.start_date == scraped_event.start_date)
        
        return query.first() is not None
    
    def _create_event_from_scraped(self, scraped_event, city_id: int) -> Optional[Event]:
        """Create Event model from scraped event data."""
        try:
            # Parse dates
            start_date = None
            end_date = None
            start_time = None
            end_time = None
            
            if scraped_event.start_date:
                try:
                    start_date = datetime.strptime(scraped_event.start_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        start_date = datetime.strptime(scraped_event.start_date, '%m/%d/%Y').date()
                    except ValueError:
                        self.logger.warning(f"Could not parse start_date: {scraped_event.start_date}")
            
            if scraped_event.end_date:
                try:
                    end_date = datetime.strptime(scraped_event.end_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        end_date = datetime.strptime(scraped_event.end_date, '%m/%d/%Y').date()
                    except ValueError:
                        self.logger.warning(f"Could not parse end_date: {scraped_event.end_date}")
            
            if scraped_event.start_time:
                try:
                    start_time = datetime.strptime(scraped_event.start_time, '%H:%M').time()
                except ValueError:
                    try:
                        start_time = datetime.strptime(scraped_event.start_time, '%I:%M %p').time()
                    except ValueError:
                        self.logger.warning(f"Could not parse start_time: {scraped_event.start_time}")
            
            if scraped_event.end_time:
                try:
                    end_time = datetime.strptime(scraped_event.end_time, '%H:%M').time()
                except ValueError:
                    try:
                        end_time = datetime.strptime(scraped_event.end_time, '%I:%M %p').time()
                    except ValueError:
                        self.logger.warning(f"Could not parse end_time: {scraped_event.end_time}")
            
            # Parse price
            price = None
            if scraped_event.price:
                try:
                    # Extract numeric value from price string
                    import re
                    price_match = re.search(r'(\d+(?:\.\d{2})?)', scraped_event.price)
                    if price_match:
                        price = float(price_match.group(1))
                except ValueError:
                    pass
            
            # Create event
            event = Event(
                title=scraped_event.title[:200],  # Truncate to fit database field
                description=scraped_event.description,
                start_date=start_date,
                end_date=end_date,
                start_time=start_time,
                end_time=end_time,
                start_location=scraped_event.location,
                end_location=scraped_event.location,
                price=price,
                event_type=scraped_event.event_type or 'scraped',
                source='scraped',
                source_url=scraped_event.source_url,
                organizer=scraped_event.organizer,
                social_media_platform=scraped_event.social_media_platform,
                social_media_handle=scraped_event.social_media_handle,
                social_media_url=scraped_event.social_media_url,
                image_url=scraped_event.image_url,
                city_id=city_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"Error creating event from scraped data: {e}")
            return None

class VenueDatabaseManager:
    """Manages venue data for scraping."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_venues_for_scraping(self, city_id: int = 1, venue_types: List[str] = None) -> List:
        """Get venues that should be scraped for events."""
        if venue_types is None:
            venue_types = ['museum', 'historic_site', 'landmark', 'gallery', 'theater', 'theatre']
        
        with app.app_context():
            venues = Venue.query.filter(
                Venue.city_id == city_id,
                Venue.venue_type.in_(venue_types)
            ).all()
            
            # Convert to VenueInfo objects
            venue_infos = []
            for venue in venues:
                venue_info = VenueInfo(
                    id=venue.id,
                    name=venue.name,
                    venue_type=venue.venue_type,
                    website_url=venue.website_url,
                    instagram_url=venue.instagram_url,
                    facebook_url=venue.facebook_url,
                    twitter_url=venue.twitter_url,
                    youtube_url=venue.youtube_url,
                    tiktok_url=venue.tiktok_url
                )
                venue_infos.append(venue_info)
            
            return venue_infos
    
    def get_venues_with_websites(self, city_id: int = 1) -> List:
        """Get venues that have websites for scraping."""
        with app.app_context():
            venues = Venue.query.filter(
                Venue.city_id == city_id,
                Venue.website_url.isnot(None),
                Venue.website_url != ''
            ).all()
            
            venue_infos = []
            for venue in venues:
                venue_info = VenueInfo(
                    id=venue.id,
                    name=venue.name,
                    venue_type=venue.venue_type,
                    website_url=venue.website_url,
                    instagram_url=venue.instagram_url,
                    facebook_url=venue.facebook_url,
                    twitter_url=venue.twitter_url,
                    youtube_url=venue.youtube_url,
                    tiktok_url=venue.tiktok_url
                )
                venue_infos.append(venue_info)
            
            return venue_infos

class ScrapingScheduler:
    """Schedules and manages automated scraping."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.venue_manager = VenueDatabaseManager()
        self.event_manager = EventDatabaseManager()
    
    def run_daily_scraping(self, city_id: int = 1) -> dict:
        """Run daily scraping for all venues."""
        self.logger.info(f"Starting daily scraping for city_id {city_id}")
        
        # Get venues to scrape
        venues = self.venue_manager.get_venues_with_websites(city_id)
        self.logger.info(f"Found {len(venues)} venues with websites")
        
        # Import scraping system
        from event_scraping_system import EventScrapingOrchestrator
        
        # Create orchestrator and scrape
        orchestrator = EventScrapingOrchestrator()
        scraped_events = orchestrator.scrape_all_venues(venues)
        
        # Save to database
        saved_count = self.event_manager.save_scraped_events(scraped_events, city_id)
        
        result = {
            'venues_scraped': len(venues),
            'events_found': len(scraped_events),
            'events_saved': saved_count,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Daily scraping completed: {result}")
        return result
    
    def run_museum_scraping(self, city_id: int = 1) -> dict:
        """Run specialized museum scraping."""
        self.logger.info(f"Starting museum scraping for city_id {city_id}")
        
        # Get museum venues
        museums = self.venue_manager.get_venues_for_scraping(
            city_id, 
            ['museum', 'gallery']
        )
        
        self.logger.info(f"Found {len(museums)} museums to scrape")
        
        # Import scraping system
        from event_scraping_system import EventScrapingOrchestrator
        
        # Create orchestrator and scrape
        orchestrator = EventScrapingOrchestrator()
        scraped_events = orchestrator.scrape_all_venues(museums)
        
        # Save to database
        saved_count = self.event_manager.save_scraped_events(scraped_events, city_id)
        
        result = {
            'museums_scraped': len(museums),
            'events_found': len(scraped_events),
            'events_saved': saved_count,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Museum scraping completed: {result}")
        return result

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create scheduler
    scheduler = ScrapingScheduler()
    
    # Run museum scraping
    result = scheduler.run_museum_scraping(city_id=1)
    print(f"Museum scraping result: {result}")
    
    # Run daily scraping
    result = scheduler.run_daily_scraping(city_id=1)
    print(f"Daily scraping result: {result}")
