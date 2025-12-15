#!/usr/bin/env python3
"""
Cronjob script to scrape Washington DC museums and embassies

This script is designed to be run from a cronjob and will:
- Scrape museums with specialized scrapers (NGA, SAAM, NPG, Asian Art, African Art, Hirshhorn)
- Scrape embassies with Eventbrite ticketing URLs
- Save events to the database
- Log results for monitoring

Usage:
    # Run from project root with virtual environment activated
    source venv/bin/activate && python scripts/cron_scrape_dc_museums.py

Cronjob example (runs every Monday at 2 AM):
    0 2 * * 1 cd /path/to/planner && source venv/bin/activate && python scripts/cron_scrape_dc_museums.py >> logs/cron_scrape_dc_museums.log 2>&1
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

log_file = log_dir / f'cron_scrape_dc_museums_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def has_specialized_scraper(venue):
    """Check if a venue has a specialized scraper"""
    venue_name_lower = venue.name.lower() if venue.name else ''
    venue_url_lower = (venue.website_url or '').lower()
    
    # Museums with specialized scrapers
    specialized_museums = [
        # NGA
        ('national gallery of art', 'nga.gov'),
        # SAAM
        ('smithsonian american art', 'americanart.si.edu'),
        # NPG
        ('national portrait gallery', 'npg.si.edu'),
        # Asian Art
        ('asian art', 'asia.si.edu'),
        ('freer', 'asia.si.edu'),
        ('sackler', 'asia.si.edu'),
        # African Art
        ('african art', 'africa.si.edu'),
        # Hirshhorn
        ('hirshhorn', 'hirshhorn.si.edu'),
    ]
    
    for name_keyword, url_keyword in specialized_museums:
        if name_keyword in venue_name_lower or url_keyword in venue_url_lower:
            return True
    
    return False

def is_embassy_with_eventbrite(venue):
    """Check if a venue is an embassy with Eventbrite ticketing URL"""
    venue_type_lower = (venue.venue_type or '').lower()
    ticketing_url_lower = (venue.ticketing_url or '').lower()
    
    # Check if it's an embassy
    if 'embassy' not in venue_type_lower:
        return False
    
    # Check if it has an Eventbrite URL
    if 'eventbrite' in ticketing_url_lower:
        return True
    
    return False

def main():
    """Main function to scrape DC museum events"""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"🏛️  Starting DC Museums & Embassies weekly scraping cronjob - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        from app import app, db, Venue, City, Event
        
        with app.app_context():
            # Find Washington DC city (city_id = 1)
            dc_city = City.query.filter(
                db.func.lower(City.name).like('%washington%')
            ).first()
            
            if not dc_city:
                logger.error("❌ Washington DC city not found in database")
                return 1
            
            logger.info(f"📍 Found city: {dc_city.name} (ID: {dc_city.id})")
            
            # Get all venues in DC
            all_venues = Venue.query.filter_by(city_id=dc_city.id).all()
            
            # Filter to museums with specialized scrapers
            museums = []
            for venue in all_venues:
                # Skip closed museums
                if 'newseum' in venue.name.lower():
                    continue
                
                # Skip venues without working websites
                if not venue.website_url or 'example.com' in venue.website_url:
                    continue
                
                # Check if it has a specialized scraper
                if has_specialized_scraper(venue):
                    museums.append(venue)
                    logger.debug(f"✅ Museum with specialized scraper: {venue.name}")
            
            # Filter to embassies with Eventbrite links
            embassies = []
            for venue in all_venues:
                if is_embassy_with_eventbrite(venue):
                    embassies.append(venue)
                    logger.debug(f"✅ Embassy with Eventbrite: {venue.name}")
            
            total_venues = len(museums) + len(embassies)
            logger.info(f"🏛️  Found {len(museums)} museums with specialized scrapers")
            logger.info(f"🏛️  Found {len(embassies)} embassies with Eventbrite links")
            logger.info(f"📊 Total venues to scrape: {total_venues}")
            
            if total_venues == 0:
                logger.warning("⚠️  No venues found to scrape")
                return 0
            
            # Log venue names
            if museums:
                logger.info("📋 Museums with specialized scrapers:")
                for i, museum in enumerate(museums, 1):
                    logger.info(f"   {i}. {museum.name}")
            
            if embassies:
                logger.info("📋 Embassies with Eventbrite links:")
                for i, embassy in enumerate(embassies, 1):
                    logger.info(f"   {i}. {embassy.name} ({embassy.ticketing_url})")
            
            # Import scrapers
            from scripts.venue_event_scraper import VenueEventScraper
            from scripts.eventbrite_scraper import EventbriteScraper
            
            # Initialize scrapers
            venue_scraper = VenueEventScraper()
            eventbrite_scraper = EventbriteScraper()
            
            # Scraping settings for weekly run
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
            venues_with_events = 0
            
            # Scrape museums one by one and save immediately after each museum
            # Each scraper's create_events_in_database function already handles deduplication
            # and correct venue assignment (we fixed the wrong assignment issue)
            logger.info(f"🔍 Starting to scrape {len(museums)} museums...")
            
            for museum in museums:
                saved_count = 0  # Initialize outside try block
                skipped_count = 0
                updated_count = 0
                try:
                    logger.info("")
                    logger.info(f"🏛️  Scraping: {museum.name}")
                    logger.info(f"   URL: {museum.website_url}")
                    
                    scraped_events = venue_scraper.scrape_venue_events(
                        venue_ids=[museum.id],
                        city_id=dc_city.id,
                        event_type=None,  # All event types
                        time_range=time_range,
                        max_exhibitions_per_venue=max_exhibitions_per_venue,
                        max_events_per_venue=max_events_per_venue
                    )
                    
                    if scraped_events:
                        events_count = len(scraped_events)
                        total_events_found += events_count
                        logger.info(f"   ✅ Found {events_count} events")
                        
                        # Ensure venue_id and city_id are set for all events
                        for event in scraped_events:
                            if not event.get('venue_id'):
                                event['venue_id'] = museum.id
                            if not event.get('city_id'):
                                event['city_id'] = museum.city_id
                        
                        # Save events immediately using the appropriate scraper's save function
                        logger.info(f"   💾 Saving {events_count} events to database...")
                        venue_url_lower = (museum.website_url or '').lower()
                        use_specialized_save = False
                        
                        if 'nga.gov' in venue_url_lower:
                            from scripts.nga_comprehensive_scraper import create_events_in_database
                            try:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                                logger.info(f"   ✅ Saved {saved_count} new events, updated {updated_count}, skipped {skipped_count} duplicates (using NGA create_events_in_database)")
                                use_specialized_save = True
                            except Exception as e:
                                logger.warning(f"   ⚠️  Error using NGA create_events_in_database: {e}, falling back to manual save")
                                import traceback
                                logger.error(traceback.format_exc())
                        
                        elif 'americanart.si.edu' in venue_url_lower:
                            from scripts.saam_scraper import create_events_in_database
                            try:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                                logger.info(f"   ✅ Saved {saved_count} new events, updated {updated_count}, skipped {skipped_count} duplicates (using SAAM create_events_in_database)")
                                use_specialized_save = True
                            except Exception as e:
                                logger.warning(f"   ⚠️  Error using SAAM create_events_in_database: {e}, falling back to manual save")
                                import traceback
                                logger.error(traceback.format_exc())
                        
                        elif 'npg.si.edu' in venue_url_lower:
                            from scripts.npg_scraper import create_events_in_database
                            try:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                                logger.info(f"   ✅ Saved {saved_count} new events, updated {updated_count}, skipped {skipped_count} duplicates (using NPG create_events_in_database)")
                                use_specialized_save = True
                            except Exception as e:
                                logger.warning(f"   ⚠️  Error using NPG create_events_in_database: {e}, falling back to manual save")
                                import traceback
                                logger.error(traceback.format_exc())
                        
                        elif 'asia.si.edu' in venue_url_lower:
                            from scripts.asian_art_scraper import create_events_in_database
                            try:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                                logger.info(f"   ✅ Saved {saved_count} new events, updated {updated_count}, skipped {skipped_count} duplicates (using Asian Art create_events_in_database)")
                                use_specialized_save = True
                            except Exception as e:
                                logger.warning(f"   ⚠️  Error using Asian Art create_events_in_database: {e}, falling back to manual save")
                                import traceback
                                logger.error(traceback.format_exc())
                        
                        elif 'africa.si.edu' in venue_url_lower:
                            from scripts.african_art_scraper import create_events_in_database
                            try:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                                logger.info(f"   ✅ Saved {saved_count} new events, updated {updated_count}, skipped {skipped_count} duplicates (using African Art create_events_in_database)")
                                use_specialized_save = True
                            except Exception as e:
                                logger.warning(f"   ⚠️  Error using African Art create_events_in_database: {e}, falling back to manual save")
                                import traceback
                                logger.error(traceback.format_exc())
                        
                        # Manual save for museums without specialized create_events_in_database (Hirshhorn, Renwick, etc.)
                        # Use shared handler for generic scraper events
                        if not use_specialized_save:
                            from scripts.event_database_handler import create_events_in_database as shared_create_events
                            
                            logger.info(f"   💾 Saving {len(scraped_events)} events using shared handler...")
                            
                            # Custom processor for generic scraper events
                            def generic_event_processor(event_data):
                                """Add generic scraper-specific fields"""
                                event_data['source'] = 'website'
                                if not event_data.get('organizer'):
                                    event_data['organizer'] = museum.name
                            
                            created, updated, skipped = shared_create_events(
                                events=scraped_events,
                                venue_id=museum.id,
                                city_id=museum.city_id,
                                venue_name=museum.name,
                                db=db,
                                Event=Event,
                                Venue=Venue,
                                batch_size=5,
                                logger_instance=logger,
                                source_url=museum.website_url,
                                custom_event_processor=generic_event_processor
                            )
                            
                            saved_count = created
                            updated_count = updated
                            skipped_count = skipped
                            total_events_saved += saved_count
                            logger.info(f"   💾 Saved {saved_count} new events, updated {updated_count}, skipped {skipped_count} duplicates (using shared handler)")
                    else:
                        logger.info(f"   ⚠️  No events found")
                    
                    venues_processed += 1
                    if saved_count > 0:
                        venues_with_events += 1
                
                except Exception as e:
                    logger.error(f"   ❌ Error scraping {museum.name}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    venues_failed += 1
                    db.session.rollback()
                    continue
            
            # Scrape embassies with Eventbrite
            if embassies:
                logger.info("")
                logger.info(f"🔍 Starting to scrape {len(embassies)} embassies with Eventbrite...")
                
                for embassy in embassies:
                    saved_count = 0  # Initialize outside try block
                    skipped_count = 0
                    try:
                        logger.info("")
                        logger.info(f"🏛️  Scraping: {embassy.name}")
                        logger.info(f"   Eventbrite URL: {embassy.ticketing_url}")
                        
                        embassy_events = eventbrite_scraper.scrape_venue_events(
                            venue=embassy,
                            time_range=time_range
                        )
                        
                        if embassy_events:
                            events_count = len(embassy_events)
                            total_events_found += events_count
                            logger.info(f"   ✅ Found {events_count} events")
                            
                            # Save events to database immediately (as soon as we have all info)
                            saved_count = 0
                            skipped_count = 0
                            batch_size = 5  # Commit in small batches of 5 for immediate saving
                            
                            for event_data in embassy_events:
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
                                    
                                    # Commit in small batches of 5 for immediate saving (as soon as we have all info)
                                    # This ensures events are saved quickly while maintaining good database performance
                                    if saved_count % batch_size == 0:
                                        db.session.commit()
                                        logger.info(f"   ✅ Created batch: {saved_count} events saved so far...")
                                    else:
                                        # Commit immediately for events not in a batch (ensures immediate saving)
                                        db.session.commit()
                                
                                except Exception as e:
                                    logger.error(f"   ❌ Error saving event '{event_data.get('title', 'N/A')}': {e}")
                                    db.session.rollback()
                                    continue
                            
                            # Final commit for any remaining events (safety net, though they should already be committed)
                            try:
                                db.session.commit()
                            except Exception as e:
                                logger.error(f"   ❌ Error in final commit: {e}")
                                db.session.rollback()
                            
                            total_events_saved += saved_count
                            logger.info(f"   💾 Saved {saved_count} new events, skipped {skipped_count} duplicates")
                        else:
                            logger.info(f"   ⚠️  No events found")
                        
                        venues_processed += 1
                        if saved_count > 0:
                            venues_with_events += 1
                    
                    except Exception as e:
                        logger.error(f"   ❌ Error scraping {embassy.name}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        venues_failed += 1
                        db.session.rollback()
                        continue
            
            # Final summary
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("📊 SCRAPING SUMMARY")
            logger.info("=" * 80)
            logger.info(f"   Museums processed: {len(museums)}")
            logger.info(f"   Embassies processed: {len(embassies)}")
            logger.info(f"   Total venues processed: {venues_processed}")
            logger.info(f"   Venues with events: {venues_with_events}")
            logger.info(f"   Venues failed: {venues_failed}")
            logger.info(f"   Total events found: {total_events_found}")
            logger.info(f"   Total events saved: {total_events_saved}")
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
