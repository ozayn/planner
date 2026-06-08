#!/usr/bin/env python3
"""
Test script to debug San Francisco venue scraping
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue
from scripts.venue_event_scraper import VenueEventScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_sf_scraping():
    """Test scraping for San Francisco venues"""
    with app.app_context():
        # Get San Francisco venues (city_id == 4)
        sf_venues = Venue.query.filter_by(city_id=4).all()
        
        logger.info(f"Found {len(sf_venues)} San Francisco venues")
        
        scraper = VenueEventScraper()
        
        # Test SFMOMA and de Young specifically (they should have events)
        test_venue_names = ['SFMOMA', 'de Young Museum', 'San Francisco Museum of Modern Art']
        test_venues = [v for v in sf_venues if any(name.lower() in v.name.lower() for name in test_venue_names)]
        
        if not test_venues:
            test_venues = sf_venues[:3]  # Fallback to first 3
        
        for venue in test_venues:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing venue: {venue.name}")
            logger.info(f"URL: {venue.website_url}")
            logger.info(f"{'='*60}")
            
            try:
                events = scraper._scrape_venue_website(
                    venue=venue,
                    event_type=None,  # No filter
                    time_range='all',  # Changed to 'all' to include future exhibitions like "Art of Manga"
                    max_events_per_venue=20,
                    max_exhibitions_per_venue=10  # Increased from default 5 to 10 to include more exhibitions
                )
                
                logger.info(f"\n✅ Found {len(events)} events for {venue.name}")
                
                if events:
                    for i, event in enumerate(events[:5], 1):
                        logger.info(f"\n  Event {i}:")
                        logger.info(f"    Title: {event.get('title', 'N/A')}")
                        logger.info(f"    Date: {event.get('start_date', 'N/A')}")
                        logger.info(f"    Time: {event.get('start_time', 'N/A')}")
                        logger.info(f"    Type: {event.get('event_type', 'N/A')}")
                        logger.info(f"    URL: {event.get('url', 'N/A')[:80]}")
                else:
                    logger.warning(f"⚠️  No events found for {venue.name}")
                    
            except Exception as e:
                logger.error(f"❌ Error scraping {venue.name}: {e}")
                import traceback
                logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_sf_scraping()
