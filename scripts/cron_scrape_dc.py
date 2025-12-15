#!/usr/bin/env python3
"""
Cronjob script to scrape Washington DC events weekly

This script is designed to be run from a cronjob and will:
- Scrape all venues in Washington DC
- Use specialized scrapers for museums (NGA, SAAM, NPG, etc.)
- Save events to the database
- Log results for monitoring

Usage:
    # Run from project root with virtual environment activated
    source venv/bin/activate && python scripts/cron_scrape_dc.py

Cronjob example (runs every Monday at 2 AM):
    0 2 * * 1 cd /path/to/planner && source venv/bin/activate && python scripts/cron_scrape_dc.py >> logs/cron_scrape_dc.log 2>&1
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging before importing app (to catch any import errors)
log_dir = project_root / 'logs'
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f'cron_scrape_dc_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to scrape DC events"""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"🚀 Starting DC weekly scraping cronjob - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        from app import app, db, Venue, City, Event, Source
        from scripts.venue_event_scraper import VenueEventScraper
        from scripts.source_event_scraper import SourceEventScraper
        
        with app.app_context():
            # Find Washington DC city (city_id = 1)
            dc_city = City.query.filter(
                db.func.lower(City.name).like('%washington%')
            ).first()
            
            if not dc_city:
                logger.error("❌ Washington DC city not found in database")
                return 1
            
            logger.info(f"📍 Found city: {dc_city.name} (ID: {dc_city.id})")
            
            # Get all active venues in DC
            venues = Venue.query.filter_by(city_id=dc_city.id).all()
            
            # Filter out closed/inactive venues
            active_venues = []
            for venue in venues:
                # Skip closed museums
                if 'newseum' in venue.name.lower():
                    logger.info(f"⏭️  Skipping closed venue: {venue.name}")
                    continue
                
                # Skip venues without working websites
                if not venue.website_url or 'example.com' in venue.website_url:
                    logger.info(f"⏭️  Skipping venue without website: {venue.name}")
                    continue
                
                active_venues.append(venue)
            
            logger.info(f"📊 Found {len(active_venues)} active venues to scrape")
            
            if not active_venues:
                logger.warning("⚠️  No active venues found to scrape")
                return 0
            
            # Initialize scrapers
            venue_scraper = VenueEventScraper()
            source_scraper = SourceEventScraper()
            
            # Scrape settings for weekly run
            # Use 'this_month' to get a good range of upcoming events
            time_range = 'this_month'
            max_events_per_venue = 50  # Higher limit for weekly scraping
            max_exhibitions_per_venue = 20
            
            logger.info(f"⚙️  Scraping settings:")
            logger.info(f"   - Time range: {time_range}")
            logger.info(f"   - Max events per venue: {max_events_per_venue}")
            logger.info(f"   - Max exhibitions per venue: {max_exhibitions_per_venue}")
            
            # Track statistics
            total_events_found = 0
            total_events_saved = 0
            venues_processed = 0
            venues_failed = 0
            
            # Scrape venues
            venue_ids = [v.id for v in active_venues]
            logger.info(f"🔍 Starting to scrape {len(venue_ids)} venues...")
            
            try:
                scraped_events = venue_scraper.scrape_venue_events(
                    venue_ids=venue_ids,
                    city_id=dc_city.id,
                    event_type=None,  # All event types
                    time_range=time_range,
                    max_exhibitions_per_venue=max_exhibitions_per_venue,
                    max_events_per_venue=max_events_per_venue
                )
                
                if scraped_events:
                    total_events_found = len(scraped_events)
                    logger.info(f"✅ Found {total_events_found} events from venues")
                    
                    # Save events to database
                    logger.info("💾 Saving events to database...")
                    saved_count = 0
                    skipped_count = 0
                    
                    for event_data in scraped_events:
                        try:
                            # Check for duplicates
                            existing = Event.query.filter_by(
                                title=event_data.get('title'),
                                start_date=event_data.get('start_date'),
                                venue_id=event_data.get('venue_id')
                            ).first()
                            
                            if existing:
                                skipped_count += 1
                                continue
                            
                            # Create new event
                            event = Event(**event_data)
                            db.session.add(event)
                            saved_count += 1
                            
                            # Commit in batches of 10
                            if saved_count % 10 == 0:
                                db.session.commit()
                                logger.debug(f"   Committed {saved_count} events so far...")
                        
                        except Exception as e:
                            logger.error(f"❌ Error saving event '{event_data.get('title', 'N/A')}': {e}")
                            db.session.rollback()
                            continue
                    
                    # Final commit
                    db.session.commit()
                    total_events_saved = saved_count
                    
                    logger.info(f"✅ Saved {total_events_saved} new events")
                    logger.info(f"⏭️  Skipped {skipped_count} duplicate events")
                else:
                    logger.warning("⚠️  No events found from venues")
            
            except Exception as e:
                logger.error(f"❌ Error during venue scraping: {e}")
                import traceback
                logger.error(traceback.format_exc())
                venues_failed = len(venue_ids)
            
            venues_processed = len(venue_ids) - venues_failed
            
            # Scrape sources (optional - for non-venue events)
            logger.info("🔍 Scraping event sources...")
            try:
                sources = db.session.query(Source).filter_by(city_id=dc_city.id).all()
                if sources:
                    source_ids = [s.id for s in sources]
                    logger.info(f"   Found {len(source_ids)} sources to scrape")
                    
                    source_events = source_scraper.scrape_source_events(
                        source_ids=source_ids,
                        city_id=dc_city.id,
                        time_range=time_range
                    )
                    
                    if source_events:
                        logger.info(f"✅ Found {len(source_events)} events from sources")
                        # Save source events (similar logic as above)
                        for event_data in source_events:
                            try:
                                existing = Event.query.filter_by(
                                    title=event_data.get('title'),
                                    start_date=event_data.get('start_date'),
                                    source_url=event_data.get('source_url')
                                ).first()
                                
                                if not existing:
                                    event = Event(**event_data)
                                    db.session.add(event)
                                    total_events_saved += 1
                            except Exception as e:
                                logger.error(f"❌ Error saving source event: {e}")
                                continue
                        
                        db.session.commit()
                        logger.info(f"✅ Saved {len(source_events)} events from sources")
            except Exception as e:
                logger.warning(f"⚠️  Error scraping sources: {e}")
            
            # Final summary
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("=" * 80)
            logger.info("📊 SCRAPING SUMMARY")
            logger.info("=" * 80)
            logger.info(f"   Venues processed: {venues_processed}")
            logger.info(f"   Venues failed: {venues_failed}")
            logger.info(f"   Events found: {total_events_found}")
            logger.info(f"   Events saved: {total_events_saved}")
            logger.info(f"   Duration: {duration}")
            logger.info(f"   Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
            
            return 0 if venues_failed == 0 else 1
    
    except Exception as e:
        logger.error(f"❌ Fatal error in cronjob: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
