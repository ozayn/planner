#!/usr/bin/env python3
"""
Cronjob script to scrape Washington DC museums, embassies, and standalone venue scrapers.

Operational buckets (see scripts/cron_bucket_config.py):
- stable (default): Eventbrite, Meetup, reliable venue scrapers — main cron
- protected: Asian Art, NPG, Hirshhorn — separate cron (403/Cloudflare/proxy-sensitive)

Per-scraper run rules (always vs seasonal) are in scripts/cron_scheduler_config.py.

Usage:
    source venv/bin/activate && python scripts/cron_run_scheduled_scrapers.py
    source venv/bin/activate && python scripts/cron_run_protected_scrapers.py

Cronjob examples:
    python scripts/cron_run_scheduled_scrapers.py --bucket stable
    python scripts/cron_run_protected_scrapers.py
"""

import argparse
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

from scripts.cron_bucket_config import (
    BUCKET_STABLE,
    BUCKET_PROTECTED,
    bucket_display_name,
    bucket_runs_stable_sections,
    get_venue_scraper_bucket,
)
from scripts.cron_scheduler_config import (
    should_run,
    get_venue_schedule_rule,
    get_standalone_schedule_rule,
)


def configure_logging(bucket: str) -> None:
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'cron_{bucket}_{datetime.now().strftime("%Y%m%d")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

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
    """See scripts.eventbrite_scraper.is_diplomatic_eventbrite_venue (embassy + cultural_center + Eventbrite URL)."""
    from scripts.eventbrite_scraper import is_diplomatic_eventbrite_venue
    return is_diplomatic_eventbrite_venue(venue)


# Non-embassy DC venues with Eventbrite organizer on ticketing_url (museums, theaters; not cultural_center).
EVENTBRITE_EXTRA_VENUE_NAME_FRAGMENTS = (
    'washington improv theater',
    'smithsonian national museum of american history',
)


def get_eventbrite_extra_venues(all_venues):
    """DC museums/venues using shared Eventbrite scraper (not embassy cron bucket)."""
    extra = []
    seen_ids = set()
    for venue in all_venues:
        name_lower = (venue.name or '').lower()
        if not any(frag in name_lower for frag in EVENTBRITE_EXTRA_VENUE_NAME_FRAGMENTS):
            continue
        if not venue.ticketing_url or 'eventbrite' not in venue.ticketing_url.lower():
            logger.debug(f"   ⚠️  Eventbrite extra skipped (no Eventbrite ticketing_url): {venue.name}")
            continue
        if venue.id in seen_ids:
            continue
        seen_ids.add(venue.id)
        extra.append(venue)
        logger.debug(f"✅ Eventbrite extra venue: {venue.name}")
    return extra


def run_scheduled_scrapers(bucket: str = BUCKET_STABLE) -> int:
    """Run scheduled scrapers for the given operational bucket."""
    if bucket not in (BUCKET_STABLE, BUCKET_PROTECTED):
        raise ValueError(f"Unknown cron bucket: {bucket}")

    configure_logging(bucket)
    start_time = datetime.now()
    logger.info(
        f"🏛️  {bucket_display_name(bucket)} ({bucket}): scheduled scrapers — "
        f"{start_time.strftime('%Y-%m-%d %H:%M')}"
    )
    
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
                    if get_venue_scraper_bucket(venue.website_url, venue.name) == bucket:
                        museums.append(venue)
                        logger.debug(f"✅ Museum with specialized scraper [{bucket}]: {venue.name}")
            
            # Embassies + Eventbrite extras + standalone scrapers: stable cron only
            embassies = []
            eventbrite_extra_venues = []
            if bucket_runs_stable_sections(bucket):
                for venue in all_venues:
                    if is_embassy_with_eventbrite(venue):
                        embassies.append(venue)
                        logger.debug(f"✅ Diplomatic/cultural Eventbrite: {venue.name}")
                eventbrite_extra_venues = get_eventbrite_extra_venues(all_venues)

            total_venues = len(museums) + len(embassies) + len(eventbrite_extra_venues)
            logger.info(
                f"📋 Bucket={bucket}: {len(museums)} museum scrapers, "
                f"{len(embassies)} Eventbrite embassies, {len(eventbrite_extra_venues)} Eventbrite extras"
            )
            
            if total_venues == 0 and not bucket_runs_stable_sections(bucket):
                logger.warning(f"⚠️  No {bucket} museum scrapers matched for this run")
                return 0
            if total_venues == 0 and bucket_runs_stable_sections(bucket):
                logger.warning("⚠️  No venues found to scrape in stable bucket")
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
                    
                    elif ('africa.si.edu' in venue_url_lower or
                          ('african art' in (museum.name or '').lower() and 'si.edu' in venue_url_lower and 'african-art' in venue_url_lower)):
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
                        rule, months = get_venue_schedule_rule(museum.website_url or '')
                        if not should_run(rule, months):
                            logger.info(f"⏭️  Tulip Day | skipped (out of season, runs Mar–Apr)")
                            continue
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
            
            # Scrape embassies with Eventbrite (stable cron only)
            if bucket_runs_stable_sections(bucket) and embassies:
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

            # Scrape non-embassy Eventbrite venues (stable cron only)
            if not bucket_runs_stable_sections(bucket):
                eventbrite_extra_venues = []
            for eb_venue in eventbrite_extra_venues:
                logger.info(f"🏛️  Eventbrite | {eb_venue.name}")
                try:
                    eb_events = eventbrite_scraper.scrape_venue_events(
                        venue=eb_venue,
                        time_range=time_range
                    )
                    if eb_events:
                        events_count = len(eb_events)
                        total_events_found += events_count
                        from scripts.event_database_handler import create_events_in_database as shared_create_events
                        venue_name = eb_venue.name
                        created, updated, skipped = shared_create_events(
                            events=eb_events,
                            venue_id=eb_venue.id,
                            city_id=eb_venue.city_id,
                            venue_name=venue_name,
                            db=db,
                            Event=Event,
                            Venue=Venue,
                            batch_size=5,
                            logger_instance=logger,
                            source_url=eb_venue.ticketing_url or eb_venue.website_url,
                            custom_event_processor=lambda e, vn=venue_name: e.update({'source': 'eventbrite', 'organizer': vn})
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

            if not bucket_runs_stable_sections(bucket):
                end_time = datetime.now()
                duration = end_time - start_time
                logger.info(
                    f"📊 {bucket_display_name(bucket)} summary: venues {venues_processed} "
                    f"(with events: {venues_with_events}, failed: {venues_failed}) | "
                    f"found {total_events_found} | saved {total_events_saved} | {duration}"
                )
                return 0 if venues_failed == 0 else 1

            # --- Stable-only standalone scrapers below ---

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

            # DC Urban Walkers (Meetup)
            logger.info(f"🚶 DC Urban Walkers | Meetup")
            try:
                from scripts.dc_urban_walkers_scraper import (
                    scrape_dc_urban_walkers_events,
                    create_events_in_database_wrapper as save_dc_urban_walkers_events,
                )
                duw_events = scrape_dc_urban_walkers_events()
                if duw_events:
                    created, updated, skipped = save_dc_urban_walkers_events(duw_events)
                    total_events_saved += created
                    total_events_found += len(duw_events)
                    logger.info(f"   → found {len(duw_events)}, saved {created}, updated {updated}, skipped {skipped}")
                else:
                    logger.info(f"   → found 0")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())

            # Austrian Cultural Forum Washington (acfdc.org — shared VenueEventScraper + event_paths.events)
            rule, months = get_standalone_schedule_rule("acfdc_dc")
            if not should_run(rule, months):
                logger.info(f"⏭️  ACF DC | skipped (scheduler)")
            else:
                logger.info(f"🏛️  ACF DC | Austrian Cultural Forum Washington")
                try:
                    acf = Venue.query.filter(
                        (Venue.website_url.ilike('%acfdc.org%'))
                        | (Venue.name.ilike('%austrian cultural forum%washington%'))
                    ).first()
                    if acf:
                        scraped_events = venue_scraper.scrape_venue_events(
                            venue_ids=[acf.id],
                            event_type=None,
                            time_range=time_range,
                            max_exhibitions_per_venue=max_exhibitions_per_venue,
                            max_events_per_venue=max_events_per_venue,
                        )
                        if scraped_events:
                            from scripts.event_database_handler import create_events_in_database as shared_create_events
                            created, updated, skipped = shared_create_events(
                                events=scraped_events,
                                venue_id=acf.id,
                                city_id=acf.city_id,
                                venue_name=acf.name,
                                db=db,
                                Event=Event,
                                Venue=Venue,
                                batch_size=5,
                                logger_instance=logger,
                                source_url='https://www.acfdc.org/events',
                                custom_event_processor=lambda e: e.update({'source': 'website', 'organizer': acf.name}),
                            )
                            total_events_saved += created
                            total_events_found += len(scraped_events)
                            logger.info(
                                f"   → found {len(scraped_events)}, saved {created}, updated {updated}, skipped {skipped}"
                            )
                        else:
                            logger.info(f"   → found 0")
                    else:
                        logger.warning(f"   ⚠️  ACF DC venue not found, skipping")
                except Exception as e:
                    logger.error(f"   ❌ {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Shoot New York City (NYC workshops)
            logger.info(f"📷 Shoot NYC | Shoot New York City")
            try:
                from scripts.shoot_nyc_scraper import scrape_shoot_nyc_events, create_events_in_database_wrapper
                shoot_nyc_events = scrape_shoot_nyc_events()
                if shoot_nyc_events:
                    created, updated, skipped = create_events_in_database_wrapper(shoot_nyc_events)
                    total_events_saved += created
                    total_events_found += len(shoot_nyc_events)
                    logger.info(f"   → found {len(shoot_nyc_events)}, saved {created}, updated {updated}, skipped {skipped}")
                else:
                    logger.info(f"   → found 0")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())

            # The Metropolitan Museum of Art (NYC — met-tours & programs)
            rule, months = get_standalone_schedule_rule("metmuseum")
            if not should_run(rule, months):
                logger.info(f"⏭️  The Met | skipped (scheduler)")
            else:
                logger.info(f"🏛️  The Met | The Metropolitan Museum of Art")
                try:
                    from scripts.metmuseum_scraper import scrape_metmuseum_events, create_events_in_database_wrapper
                    met_events = scrape_metmuseum_events()
                    if met_events:
                        created, updated, skipped = create_events_in_database_wrapper(met_events)
                        total_events_saved += created
                        total_events_found += len(met_events)
                        logger.info(f"   → found {len(met_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.info(f"   → found 0")
                except Exception as e:
                    logger.error(f"   ❌ {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Tenement Museum (NYC — tours & programs)
            rule, months = get_standalone_schedule_rule("tenement_museum")
            if not should_run(rule, months):
                logger.info(f"⏭️  Tenement Museum | skipped (scheduler)")
            else:
                logger.info(f"🏠  Tenement Museum | Tenement Museum")
                try:
                    from scripts.tenement_museum_scraper import (
                        create_events_in_database_wrapper,
                        scrape_tenement_museum_events,
                    )
                    tenement_events = scrape_tenement_museum_events()
                    if tenement_events:
                        created, updated, skipped = create_events_in_database_wrapper(tenement_events)
                        total_events_saved += created
                        total_events_found += len(tenement_events)
                        logger.info(f"   → found {len(tenement_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.info(f"   → found 0")
                except Exception as e:
                    logger.error(f"   ❌ {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Big Onion Walking Tours (NYC)
            rule, months = get_standalone_schedule_rule("big_onion")
            if not should_run(rule, months):
                logger.info(f"⏭️  Big Onion | skipped (scheduler)")
            else:
                logger.info(f"🧅  Big Onion | Big Onion Walking Tours")
                try:
                    from scripts.big_onion_scraper import (
                        create_events_in_database_wrapper,
                        scrape_big_onion_events,
                    )
                    big_onion_events = scrape_big_onion_events()
                    if big_onion_events:
                        created, updated, skipped = create_events_in_database_wrapper(big_onion_events)
                        total_events_saved += created
                        total_events_found += len(big_onion_events)
                        logger.info(f"   → found {len(big_onion_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.info(f"   → found 0")
                except Exception as e:
                    logger.error(f"   ❌ {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # de Young Museum (SF exhibitions)
            logger.info(f"🏛️  de Young Museum | de Young Museum")
            try:
                from scripts.deyoung_scraper import scrape_all_deyoung_events
                from scripts.event_database_handler import create_events_in_database as shared_create_events
                deyoung_events = scrape_all_deyoung_events()
                if deyoung_events:
                    venue = Venue.query.filter(
                        (Venue.website_url.ilike('%deyoung.famsf.org%')) |
                        (Venue.name.ilike('%de young%'))
                    ).first()
                    if venue:
                        created, updated, skipped = shared_create_events(
                            events=deyoung_events,
                            venue_id=venue.id,
                            city_id=venue.city_id,
                            venue_name=venue.name,
                            db=db,
                            Event=Event,
                            Venue=Venue,
                            batch_size=5,
                            logger_instance=logger,
                            source_url='https://www.famsf.org/exhibitions?where=de-young',
                            custom_event_processor=lambda e: e.update({'source': 'website', 'organizer': venue.name})
                        )
                        total_events_saved += created
                        total_events_found += len(deyoung_events)
                        logger.info(f"   → found {len(deyoung_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.warning(f"   ⚠️  de Young Museum venue not found, skipping")
                else:
                    logger.info(f"   → found 0")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())

            # Hammer Museum (LA programs and events)
            logger.info(f"🏛️  Hammer Museum | Hammer Museum")
            try:
                from scripts.hammer_scraper import scrape_all_hammer_events
                from scripts.event_database_handler import create_events_in_database as shared_create_events
                hammer_events = scrape_all_hammer_events()
                if hammer_events:
                    venue = Venue.query.filter(
                        (Venue.website_url.ilike('%hammer.ucla.edu%')) |
                        (Venue.name.ilike('%hammer museum%'))
                    ).first()
                    if venue:
                        created, updated, skipped = shared_create_events(
                            events=hammer_events,
                            venue_id=venue.id,
                            city_id=venue.city_id,
                            venue_name=venue.name,
                            db=db,
                            Event=Event,
                            Venue=Venue,
                            batch_size=5,
                            logger_instance=logger,
                            source_url='https://hammer.ucla.edu/programs-events',
                            custom_event_processor=lambda e: e.update({'source': 'website', 'organizer': venue.name})
                        )
                        total_events_saved += created
                        total_events_found += len(hammer_events)
                        logger.info(f"   → found {len(hammer_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.warning(f"   ⚠️  Hammer Museum venue not found, skipping")
                else:
                    logger.info(f"   → found 0")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())

            # OCMA (Orange County Museum of Art, Irvine/Costa Mesa)
            logger.info(f"🏛️  OCMA | Orange County Museum of Art")
            try:
                ocma = Venue.query.filter(
                    (Venue.website_url.ilike('%ocma.art%')) |
                    (Venue.name.ilike('%orange county museum%'))
                ).first()
                if ocma:
                    scraped_events = venue_scraper.scrape_venue_events(
                        venue_ids=[ocma.id],
                        event_type=None,
                        time_range=time_range,
                        max_exhibitions_per_venue=max_exhibitions_per_venue,
                        max_events_per_venue=max_events_per_venue
                    )
                    if scraped_events:
                        from scripts.event_database_handler import create_events_in_database as shared_create_events
                        created, updated, skipped = shared_create_events(
                            events=scraped_events,
                            venue_id=ocma.id,
                            city_id=ocma.city_id,
                            venue_name=ocma.name,
                            db=db,
                            Event=Event,
                            Venue=Venue,
                            batch_size=5,
                            logger_instance=logger,
                            source_url=ocma.website_url or 'https://ocma.art',
                            custom_event_processor=lambda e: e.update({'source': 'website', 'organizer': ocma.name})
                        )
                        total_events_saved += created
                        total_events_found += len(scraped_events)
                        logger.info(f"   → found {len(scraped_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.info(f"   → found 0")
                else:
                    logger.warning(f"   ⚠️  OCMA venue not found, skipping")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())

            # University Park Library (Irvine) - PDF program guide
            logger.info(f"📚 University Park Library | Irvine")
            try:
                upl = Venue.query.filter(Venue.name.ilike('%university park library%')).first()
                if upl:
                    from scripts.university_park_library_scraper import scrape_all_university_park_library_events
                    from scripts.event_database_handler import create_events_in_database as shared_create_events
                    upl_events = scrape_all_university_park_library_events()
                    if upl_events:
                        created, updated, skipped = shared_create_events(
                            events=upl_events,
                            venue_id=upl.id,
                            city_id=upl.city_id,
                            venue_name=upl.name,
                            db=db,
                            Event=Event,
                            Venue=Venue,
                            batch_size=5,
                            logger_instance=logger,
                            source_url='https://legacy.cityofirvine.org/civica/filebank/blobdload.asp?BlobID=36797',
                            custom_event_processor=lambda e: e.update({'source': 'website', 'organizer': upl.name})
                        )
                        total_events_saved += created
                        total_events_found += len(upl_events)
                        logger.info(f"   → found {len(upl_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.info(f"   → found 0")
                else:
                    logger.warning(f"   ⚠️  University Park Library venue not found, skipping")
            except Exception as e:
                logger.error(f"   ❌ {e}")
                import traceback
                logger.error(traceback.format_exc())

            # DC Chinese New Year Parade (seasonal: Jan–Feb)
            rule, months = get_standalone_schedule_rule("dcparade")
            if not should_run(rule, months):
                logger.info(f"⏭️  DC Parade | skipped (out of season, runs Jan–Feb)")
            else:
                logger.info(f"🏮 DC Parade | DC Chinese New Year Parade")
                try:
                    from scripts.dcparade_scraper import scrape_dcparade_events, create_events_in_database_wrapper
                    dcparade_events = scrape_dcparade_events()
                    if dcparade_events:
                        created, updated, skipped = create_events_in_database_wrapper(dcparade_events)
                        total_events_saved += created
                        total_events_found += len(dcparade_events)
                        logger.info(f"   → found {len(dcparade_events)}, saved {created}, updated {updated}, skipped {skipped}")
                    else:
                        logger.info(f"   → found 0")
                except Exception as e:
                    logger.error(f"   ❌ {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Final summary
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(
                f"📊 {bucket_display_name(bucket)} summary: venues {venues_processed} "
                f"(with events: {venues_with_events}, failed: {venues_failed}) | "
                f"found {total_events_found} | saved {total_events_saved} | {duration}"
            )
            
            return 0 if venues_failed == 0 else 1
    
    except Exception as e:
        logger.error(f"❌ Fatal error in {bucket_display_name(bucket)}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Run scheduled venue scrapers by operational bucket')
    parser.add_argument(
        '--bucket',
        choices=[BUCKET_STABLE, BUCKET_PROTECTED],
        default=BUCKET_STABLE,
        help='stable = main cron; protected = Cloudflare/403-sensitive scrapers',
    )
    args = parser.parse_args()
    return run_scheduled_scrapers(args.bucket)


if __name__ == '__main__':
    sys.exit(main())
