#!/usr/bin/env python3
"""
Cronjob script to scrape Washington DC museums and embassies

This script is designed to be run from a cronjob and will:
- Scrape museums with specialized scrapers (NGA, SAAM, NPG, Asian Art, African Art, Hirshhorn)
- Scrape embassies with Eventbrite ticketing URLs
- Scrape Webster's Bookstore Cafe (State College, PA)
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
        # Suns Cinema
        ('suns cinema', 'sunscinema.com'),
        # Culture DC
        ('culture dc', 'culturedc.com'),
        # Tulip Day
        ('tulip day', 'tulipday.eu'),
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
    logger.info(f"🏛️  Cron: DC Museums & Embassies — {start_time.strftime('%Y-%m-%d %H:%M')}")
    
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
            
            logger.debug(f"📍 Found city: {dc_city.name} (ID: {dc_city.id})")

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

            # Washington Improv Theater (Eventbrite organizer)
            wit_venue = None
            for venue in all_venues:
                if 'washington improv theater' in (venue.name or '').lower():
                    wit_venue = venue
                    break
            
            total_venues = len(museums) + len(embassies) + (1 if wit_venue else 0)
            logger.debug(f"Found {len(museums)} museums, {len(embassies)} embassies, total {total_venues} venues")
            
            if total_venues == 0:
                logger.warning("⚠️  No venues found to scrape")
                return 0
            
            if museums:
                for i, museum in enumerate(museums, 1):
                    logger.debug(f"   {i}. {museum.name}")
            if embassies:
                for i, embassy in enumerate(embassies, 1):
                    logger.debug(f"   {i}. {embassy.name}")
            
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
            
            logger.debug(f"Settings: time_range={time_range}, max_events={max_events_per_venue}, max_exhibitions={max_exhibitions_per_venue}")
            
            # Track statistics
            total_events_found = 0
            total_events_saved = 0
            venues_processed = 0
            venues_failed = 0
            venues_with_events = 0
            
            # Scrape museums one by one using specialized scrapers directly (like admin buttons)
            # This ensures venue_id is determined from event content, not from which venue is being scraped
            for museum in museums:
                saved_count = 0  # Initialize outside try block
                skipped_count = 0
                updated_count = 0
                try:
                    venue_url_lower = (museum.website_url or '').lower()
                    scraped_events = []
                    scraper_name = None
                    
                    # Call specialized scrapers directly (same as admin buttons)
                    # This bypasses venue_event_scraper.py which was assigning venue_id incorrectly
                    if 'nga.gov' in venue_url_lower:
                        scraper_name = "NGA"
                        logger.info(f"🏛️  {scraper_name} | {museum.name}")
                        from scripts.nga_comprehensive_scraper import scrape_all_nga_events, create_events_in_database
                        try:
                            scraped_events = scrape_all_nga_events()
                            if scraped_events:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}, updated {updated_count}, skipped {skipped_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    elif 'americanart.si.edu' in venue_url_lower:
                        logger.info(f"🏛️  SAAM | {museum.name}")
                        from scripts.saam_scraper import scrape_all_saam_events, create_events_in_database
                        try:
                            scraped_events = scrape_all_saam_events()
                            if scraped_events:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}, updated {updated_count}, skipped {skipped_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    elif 'npg.si.edu' in venue_url_lower:
                        logger.info(f"🏛️  NPG | {museum.name}")
                        from scripts.npg_scraper import scrape_all_npg_events, create_events_in_database
                        try:
                            scraped_events = scrape_all_npg_events()
                            if scraped_events:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}, updated {updated_count}, skipped {skipped_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    elif 'asia.si.edu' in venue_url_lower:
                        logger.info(f"🏛️  Asian Art | {museum.name}")
                        from scripts.asian_art_scraper import scrape_all_asian_art_events, create_events_in_database
                        try:
                            scraped_events = scrape_all_asian_art_events()
                            if scraped_events:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}, updated {updated_count}, skipped {skipped_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    elif 'africa.si.edu' in venue_url_lower:
                        logger.info(f"🏛️  African Art | {museum.name}")
                        from scripts.african_art_scraper import scrape_all_african_art_events, create_events_in_database
                        try:
                            scraped_events = scrape_all_african_art_events()
                            if scraped_events:
                                created, updated = create_events_in_database(scraped_events)
                                saved_count = created
                                updated_count = updated
                                skipped_count = len(scraped_events) - created - updated
                                total_events_saved += saved_count
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}, updated {updated_count}, skipped {skipped_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    elif 'hirshhorn.si.edu' in venue_url_lower:
                        logger.info(f"🏛️  Hirshhorn | {museum.name}")
                        scraped_events = venue_scraper.scrape_venue_events(
                            venue_ids=[museum.id],
                            city_id=dc_city.id,
                            event_type=None,
                            time_range=time_range,
                            max_exhibitions_per_venue=max_exhibitions_per_venue,
                            max_events_per_venue=max_events_per_venue
                        )
                        if scraped_events:
                            from scripts.event_database_handler import create_events_in_database as shared_create_events
                            def generic_event_processor(event_data):
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
                        logger.info(f"   → found {len(scraped_events)}, saved {saved_count}, updated {updated_count}, skipped {skipped_count}")
                    
                    elif 'sunscinema.com' in venue_url_lower:
                        logger.info(f"🏛️  Suns Cinema | {museum.name}")
                        try:
                            from scripts.suns_cinema_scraper import scrape_all_suns_cinema_events
                            scraped_events = scrape_all_suns_cinema_events()
                            saved_count = len(scraped_events)
                            total_events_saved += saved_count
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    elif 'culturedc.com' in venue_url_lower:
                        logger.info(f"🏛️  Culture DC | {museum.name}")
                        try:
                            from scripts.culture_dc_scraper import scrape_all_culture_dc_events
                            scraped_events = scrape_all_culture_dc_events()
                            saved_count = len(scraped_events)
                            total_events_saved += saved_count
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    elif 'tulipday.eu' in venue_url_lower:
                        logger.info(f"🏛️  Tulip Day | {museum.name}")
                        try:
                            from scripts.tulipday_scraper import scrape_all_tulipday_events
                            scraped_events = scrape_all_tulipday_events()
                            if scraped_events:
                                from scripts.event_database_handler import create_events_in_database as shared_create_events
                                def tulip_event_processor(event_data):
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
                                    custom_event_processor=tulip_event_processor
                                )
                                saved_count = created
                                updated_count = updated
                                skipped_count = skipped
                                total_events_saved += saved_count
                            else:
                                saved_count = updated_count = skipped_count = 0
                            logger.info(f"   → found {len(scraped_events)}, saved {saved_count}, updated {updated_count}, skipped {skipped_count}")
                        except Exception as e:
                            logger.error(f"   ❌ {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    else:
                        logger.warning(f"   ⚠️  No specialized scraper for {museum.name}, skipping")
                    
                    if scraped_events:
                        total_events_found += len(scraped_events)
                    
                    venues_processed += 1
                    if saved_count > 0:
                        venues_with_events += 1
                
                except Exception as e:
                    logger.error(f"   ❌ {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    venues_failed += 1
                    db.session.rollback()
                    continue
            
            # Scrape embassies with Eventbrite
            if embassies:
                for embassy in embassies:
                    saved_count = 0
                    skipped_count = 0
                    try:
                        logger.info(f"🏛️  Eventbrite | {embassy.name}")
                        embassy_events = eventbrite_scraper.scrape_venue_events(
                            venue=embassy,
                            time_range=time_range
                        )
                        
                        if embassy_events:
                            events_count = len(embassy_events)
                            total_events_found += events_count
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
                            logger.info(f"   → found {events_count}, saved {saved_count}, skipped {skipped_count}")
                        else:
                            logger.info(f"   → found 0")

                        venues_processed += 1
                        if saved_count > 0:
                            venues_with_events += 1

                    except Exception as e:
                        logger.error(f"   ❌ {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        venues_failed += 1
                        db.session.rollback()
                        continue

            # Scrape Washington Improv Theater via Eventbrite
            if wit_venue:
                logger.info(f"🏛️  Eventbrite (WIT) | {wit_venue.name}")
                try:
                    wit_events = eventbrite_scraper.scrape_venue_events(
                        venue=wit_venue,
                        time_range=time_range
                    )
                    if wit_events:
                        events_count = len(wit_events)
                        total_events_found += events_count
                        from scripts.event_database_handler import create_events_in_database as shared_create_events
                        created, updated, skipped = shared_create_events(
                            events=wit_events,
                            venue_id=wit_venue.id,
                            city_id=wit_venue.city_id,
                            venue_name=wit_venue.name,
                            db=db,
                            Event=Event,
                            Venue=Venue,
                            batch_size=5,
                            logger_instance=logger,
                            source_url=wit_venue.ticketing_url or wit_venue.website_url,
                            custom_event_processor=lambda e: e.update({'source': 'eventbrite', 'organizer': wit_venue.name})
                        )
                        total_events_saved += created
                        if created > 0:
                            venues_with_events += 1
                        logger.info(f"   → found {events_count}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.info(f"   → found 0")
                except Exception as e:
                    logger.error(f"   ❌ {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Webster's Bookstore Cafe (State College, PA)
            logger.info(f"🏛️  Webster's | Webster's Bookstore Cafe")
            try:
                from scripts.websters_scraper import scrape_websters_events, create_events_in_database
                websters_events = scrape_websters_events()
                if websters_events:
                    created = create_events_in_database(websters_events)
                    total_events_saved += created
                    total_events_found += len(websters_events)
                    logger.info(f"   → found {len(websters_events)}, saved {created}")
                else:
                    logger.info(f"   → found 0")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())

            # The Wharf DC
            logger.info(f"🏛️  Wharf DC | The Wharf DC")
            try:
                from scripts.wharf_dc_scraper import scrape_wharf_dc_events, create_events_in_database_wrapper
                wharf_events = scrape_wharf_dc_events()
                if wharf_events:
                    created, updated, skipped = create_events_in_database_wrapper(wharf_events)
                    total_events_saved += created
                    total_events_found += len(wharf_events)
                    logger.info(f"   → found {len(wharf_events)}, saved {created}, updated {updated}, skipped {skipped}")
                else:
                    logger.info(f"   → found 0")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Final summary
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"📊 Summary: venues {venues_processed} (with events: {venues_with_events}, failed: {venues_failed}) | found {total_events_found} | saved {total_events_saved} | {duration}")
            
            return 0 if venues_failed == 0 else 1
    
    except Exception as e:
        logger.error(f"❌ Fatal error in cronjob: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
