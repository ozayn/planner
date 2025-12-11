#!/usr/bin/env python3
"""
Real Venue Event Scraper

This script scrapes actual events from venue websites and social media.
It replaces the sample event generation with real web scraping.
"""

import os
import sys
import json
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
import logging
from datetime import datetime, timedelta, date, time as time_class
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re
import platform

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue, Event, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_progress(step, total_steps, message):
    """Update scraping progress"""
    progress = {
        'current_step': step,
        'total_steps': total_steps,
        'message': message,
        'percentage': int((step / total_steps) * 100),
        'timestamp': datetime.now().isoformat()
    }
    
    with open('scraping_progress.json', 'w') as f:
        json.dump(progress, f)
    
    print(f"Progress {progress['percentage']}%: {message}")

class VenueEventScraper:
    """Scrapes events from venue websites and social media"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Disable SSL verification for sites with certificate issues (like Hirshhorn)
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # Cache for NLP title validation to avoid repeated LLM calls
        self._title_validation_cache = {}
        # Configure adapter with longer timeouts, connection pooling, and retry logic
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=3,  # Increased from 2 to 3
            backoff_factor=1.0,  # Increased from 0.5 to 1.0 for exponential backoff
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            connect=3,  # Increased from 2 to 3 for connection errors
            read=3,     # Increased from 2 to 3 for read errors
            redirect=3  # Increased from 2 to 3 for redirect errors
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.scraped_events = []
        
    def scrape_venue_events(self, venue_ids=None, city_id=None, event_type=None, time_range='today', max_exhibitions_per_venue=5, max_events_per_venue=10):
        """Scrape events from selected venues - focused on TODAY
        
        Args:
            venue_ids: List of venue IDs to scrape
            city_id: City ID to scrape venues from
            event_type: Type of events to scrape (tour, exhibition, festival, photowalk)
            time_range: Time range for events (defaults to 'today')
            max_exhibitions_per_venue: Maximum number of exhibitions per venue (default: 5)
            max_events_per_venue: Maximum number of events per venue for all event types (default: 10)
        """
        logger.info(f"📊 Scraper: Received max_events_per_venue={max_events_per_venue}, max_exhibitions_per_venue={max_exhibitions_per_venue}")
        try:
            with app.app_context():
                # Get venues to scrape
                if venue_ids:
                    venues = Venue.query.filter(Venue.id.in_(venue_ids)).all()
                elif city_id:
                    venues = Venue.query.filter_by(city_id=city_id).all()
                else:
                    venues = Venue.query.limit(10).all()  # Default: first 10 venues
                
                # Filter out closed/inactive venues
                active_venues = []
                for venue in venues:
                    # Skip closed museums
                    if 'newseum' in venue.name.lower():
                        logger.info(f"Skipping closed venue: {venue.name}")
                        continue
                    
                    # Skip venues without working websites
                    if not venue.website_url or 'example.com' in venue.website_url:
                        logger.info(f"Skipping venue without website: {venue.name}")
                        continue
                    
                    active_venues.append(venue)
                
                venues = active_venues
                
                logger.info(f"Scraping TODAY'S events from {len(venues)} venues")
                
                # Track unique events to prevent duplicates
                unique_events = set()
                
                for venue in venues:
                    try:
                        logger.info(f"Scraping events for: {venue.name}")
                        update_progress(2, 4, f"Scraping {venue.name}...")
                        # Add per-venue timeout to prevent worker hangs (max 20 seconds per venue)
                        # Note: signal.SIGALRM only works in main thread, so we check before using it
                        import signal
                        import threading
                        use_signal_timeout = threading.current_thread() is threading.main_thread() and hasattr(signal, 'SIGALRM')
                        
                        old_handler = None
                        if use_signal_timeout:
                            def timeout_handler(signum, frame):
                                raise TimeoutError(f"Venue scraping timeout for {venue.name}")
                            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(20)
                        
                        try:
                            events = self._scrape_venue_website(venue, event_type=event_type, time_range=time_range, max_exhibitions_per_venue=max_exhibitions_per_venue, max_events_per_venue=max_events_per_venue)
                        finally:
                            # Cancel alarm (only if we set it)
                            if use_signal_timeout and old_handler:
                                signal.alarm(0)
                                signal.signal(signal.SIGALRM, old_handler)
                        
                        # Filter by event_type if specified
                        if event_type:
                            events = [e for e in events if e.get('event_type', '').lower() == event_type.lower()]
                            logger.info(f"   Filtered to {len(events)} {event_type} events")
                        
                        # Filter by time_range
                        events = self._filter_by_time_range(events, time_range)
                        logger.info(f"   After time_range filter: {len(events)} events")
                        
                        # Limit events per venue based on event type
                        # For exhibitions, use max_exhibitions_per_venue; for others, use max_events_per_venue
                        if event_type and event_type.lower() == 'exhibition':
                            # Limit exhibitions
                            exhibition_events = [e for e in events if e.get('event_type') == 'exhibition']
                            other_events = [e for e in events if e.get('event_type') != 'exhibition']
                            if len(exhibition_events) > max_exhibitions_per_venue:
                                logger.info(f"   Limiting exhibitions from {len(exhibition_events)} to {max_exhibitions_per_venue}")
                                events = exhibition_events[:max_exhibitions_per_venue] + other_events
                        else:
                            # Limit all events (or specific event type)
                            if len(events) > max_events_per_venue:
                                logger.info(f"   Limiting events from {len(events)} to {max_events_per_venue}")
                                events = events[:max_events_per_venue]
                        
                        # Add unique events only with better deduplication
                        for event in events:
                            # For exhibitions, check if we've reached the maximum for this venue BEFORE processing
                            if event.get('event_type') == 'exhibition':
                                venue_event_count = sum(1 for e in self.scraped_events if e.get('venue_id') == venue.id and e.get('event_type') == 'exhibition')
                                if venue_event_count >= max_exhibitions_per_venue:
                                    logger.info(f"Reached maximum of {max_exhibitions_per_venue} exhibitions for {venue.name} (already have {venue_event_count}) - skipping remaining events")
                                    break
                            
                            # Normalize URL for better deduplication (remove trailing slashes, query params, fragments)
                            def normalize_url(url):
                                if not url:
                                    return ''
                                from urllib.parse import urlparse, urlunparse
                                parsed = urlparse(url)
                                # Remove query params and fragments, normalize path
                                path = parsed.path.rstrip('/')
                                normalized = urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))
                                return normalized.lower()
                            
                            # Create a more comprehensive unique key
                            title_clean = event['title'].lower().strip()
                            url_normalized = normalize_url(event.get('url', ''))
                            url_key = url_normalized[:100] if url_normalized else ''  # Use normalized URL
                            event_key = f"{title_clean}_{url_key}_{venue.id}"
                            
                            # Check if this event is already in unique_events (from this scraping session)
                            if event_key in unique_events:
                                logger.debug(f"⚠️ Skipped duplicate event (in session): {event['title']}")
                                continue
                            
                            # Also check if this event already exists in self.scraped_events for this venue
                            # Compare by title and normalized URL
                            is_duplicate = False
                            for existing_event in self.scraped_events:
                                if (existing_event.get('venue_id') == venue.id and 
                                    existing_event.get('event_type') == event.get('event_type') and
                                    existing_event.get('title', '').lower().strip() == title_clean):
                                    existing_url = normalize_url(existing_event.get('url', ''))
                                    if url_normalized and existing_url:
                                        # If both have URLs, compare them
                                        if url_normalized == existing_url:
                                            is_duplicate = True
                                            logger.debug(f"⚠️ Skipped duplicate event (existing): {event['title']} (URL: {url_normalized})")
                                            break
                                    elif not url_normalized and not existing_url:
                                        # If neither has URL, compare by title only
                                        is_duplicate = True
                                        logger.debug(f"⚠️ Skipped duplicate event (existing, no URL): {event['title']}")
                                        break
                            
                            if is_duplicate:
                                continue
                            
                            # Add to unique_events and scraped_events
                            unique_events.add(event_key)
                            self.scraped_events.append(event)
                            current_count = sum(1 for e in self.scraped_events if e.get('venue_id') == venue.id and e.get('event_type') == 'exhibition')
                            logger.info(f"✅ Added unique event: {event['title']} (venue now has {current_count} exhibitions)")
                            
                            # For exhibitions, check again if we've reached the limit after adding
                            if event.get('event_type') == 'exhibition' and current_count >= max_exhibitions_per_venue:
                                logger.info(f"Reached maximum of {max_exhibitions_per_venue} exhibitions for {venue.name} - stopping")
                                break
                        
                        # Also try social media if available
                        if venue.instagram_url:
                            instagram_events = self._scrape_instagram_events(venue)
                            for event in instagram_events:
                                event_key = f"{event['title']}_{event['venue_id']}"
                                if event_key not in unique_events:
                                    unique_events.add(event_key)
                                    self.scraped_events.append(event)
                        
                        # Rate limiting
                        time.sleep(1)
                        
                    except Timeout:
                        logger.error(f"⏱️ Timeout error scraping {venue.name} ({venue.website_url}) - skipping")
                        continue
                    except ConnectionError as e:
                        logger.error(f"🔌 Connection error scraping {venue.name} ({venue.website_url}): {e} - skipping")
                        continue
                    except RequestException as e:
                        logger.error(f"❌ Request error scraping {venue.name} ({venue.website_url}): {e} - skipping")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error scraping {venue.name}: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        continue
                
                logger.info(f"Total unique events scraped: {len(self.scraped_events)}")
                return self.scraped_events
                
        except Timeout:
            logger.error(f"⏱️ Timeout error in scrape_venue_events - returning empty list")
            return []
        except ConnectionError as e:
            logger.error(f"🔌 Connection error in scrape_venue_events: {e} - returning empty list")
            return []
        except RequestException as e:
            logger.error(f"❌ Request error in scrape_venue_events: {e} - returning empty list")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error in scrape_venue_events: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _scrape_venue_website(self, venue, event_type=None, time_range='today', max_exhibitions_per_venue=5, max_events_per_venue=10):
        """Scrape events from venue's main website
        
        Args:
            venue: Venue object to scrape
            event_type: Optional filter for event type (tour, exhibition, etc.)
            time_range: Time range for events (today, this_week, this_month, etc.)
            max_exhibitions_per_venue: Maximum number of exhibitions to extract per venue (default: 5)
            max_events_per_venue: Maximum number of events per venue for all event types (default: 10)
        """
        events = []
        
        if not venue.website_url:
            return events
        
        # Check if this venue has a specialized scraper
        # Venues with specialized scrapers: Hirshhorn, OCMA, NGA, Met Museum, etc.
        has_specialized_scraper = False
        venue_url_lower = venue.website_url.lower() if venue.website_url else ''
        
        specialized_venues = [
            'hirshhorn.si.edu',
            'ocma.art',
            'nga.gov',
            'metmuseum.org',
            'si.edu',  # Smithsonian (has specialized scrapers)
        ]
        
        for specialized_venue in specialized_venues:
            if specialized_venue in venue_url_lower:
                has_specialized_scraper = True
                logger.debug(f"   🎯 Venue has specialized scraper: {specialized_venue}")
                break
        
        # For venues WITHOUT specialized scrapers, use generic scraper first
        if not has_specialized_scraper:
            logger.info(f"🔍 No specialized scraper for {venue.name}, using generic scraper...")
            logger.info(f"   URL: {venue.website_url}")
            
            # Validate URL before attempting to scrape
            if not venue.website_url or not venue.website_url.startswith('http'):
                logger.warning(f"   ⚠️  Invalid URL for {venue.name}, skipping...")
                return events
            
            # Use 'this_month' for generic scraper to be less restrictive (instead of 'today' or 'this_week')
            # This ensures we get more events, especially for recurring events
            adjusted_time_range = 'this_month' if time_range in ['today', 'this_week'] else time_range
            logger.info(f"   Using time_range: {adjusted_time_range} (original: {time_range})")
            try:
                from scripts.generic_venue_scraper import GenericVenueScraper
                generic_scraper = GenericVenueScraper()
                generic_events = generic_scraper.scrape_venue_events(
                    venue_url=venue.website_url,
                    venue_name=venue.name,
                    event_type=event_type,
                    time_range=adjusted_time_range
                )
                logger.info(f"   Generic scraper returned {len(generic_events)} raw events")
                # Convert generic events to our format and validate them
                valid_generic_events = []
                invalid_count = 0
                for event in generic_events:
                    event['venue_id'] = venue.id
                    event['city_id'] = venue.city_id
                    event['source'] = 'website'
                    event['source_url'] = venue.website_url
                    event['organizer'] = venue.name
                    # Add meeting_point if start_location exists
                    if event.get('start_location') and not event.get('meeting_point'):
                        event['meeting_point'] = event.get('start_location')
                    
                    # Validate the event before adding it
                    if self._is_valid_event(event):
                        valid_generic_events.append(event)
                        logger.debug(f"   ✅ Valid event: '{event.get('title', 'N/A')}' (date: {event.get('start_date', 'N/A')})")
                    else:
                        invalid_count += 1
                        logger.debug(f"   ⚠️  Invalid event filtered out: '{event.get('title', 'N/A')}' (date: {event.get('start_date', 'N/A')})")
                
                logger.info(f"   Validation: {len(valid_generic_events)} valid, {invalid_count} invalid events")
                
                events.extend(valid_generic_events)
                if valid_generic_events:
                    logger.info(f"✅ Generic scraper found {len(valid_generic_events)} valid events for {venue.name} (filtered {len(generic_events) - len(valid_generic_events)} invalid events)")
                    # Apply limits
                    if event_type and event_type.lower() == 'exhibition':
                        exhibition_events = [e for e in events if e.get('event_type') == 'exhibition']
                        other_events = [e for e in events if e.get('event_type') != 'exhibition']
                        limited_exhibitions = exhibition_events[:max_exhibitions_per_venue]
                        events = limited_exhibitions + other_events
                    else:
                        events = events[:max_events_per_venue]
                    return events
                elif generic_events:
                    logger.info(f"⚠️ Generic scraper found {len(generic_events)} events but all were filtered out by validation")
                else:
                    logger.info(f"⚠️ Generic scraper found no events for {venue.name}")
            except Exception as generic_error:
                logger.warning(f"⚠️ Generic scraper failed for {venue.name}: {generic_error}, falling back to standard methods...")
                # Continue with standard scraping methods below
        
        try:
            logger.info(f"Scraping website: {venue.website_url}")
            try:
                # Use shorter timeout to prevent worker hangs (10 seconds per venue)
                response = self.session.get(venue.website_url, timeout=10)
                response.raise_for_status()
            except Timeout:
                logger.error(f"⏱️ Timeout error accessing {venue.website_url} (10s timeout) - skipping")
                return events
            except ConnectionError as e:
                logger.error(f"🔌 Connection error accessing {venue.website_url}: {e} - skipping")
                return events
            except RequestException as e:
                # Check if it's a 403 Forbidden error - try cloudscraper as fallback
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
                    logger.warning(f"⚠️  403 Forbidden for {venue.website_url}, trying cloudscraper...")
                    try:
                        html_content = self._scrape_with_cloudscraper(venue.website_url)
                        if html_content:
                            soup = BeautifulSoup(html_content, 'html.parser')
                            logger.info(f"✅ Successfully bypassed 403 using cloudscraper for {venue.website_url}")
                            # Continue with scraping using the cloudscraper result - skip the normal soup creation below
                        else:
                            logger.warning(f"⚠️ Cloudscraper also failed for {venue.website_url} - skipping this venue (site may have strong bot protection)")
                            return events  # Return empty list, don't crash
                    except Exception as cloudscraper_error:
                        logger.warning(f"⚠️ Cloudscraper fallback failed for {venue.website_url}: {cloudscraper_error} - skipping this venue")
                        return events  # Return empty list, don't crash
                else:
                    logger.error(f"❌ Request error accessing {venue.website_url}: {e} - skipping")
                    return events
            else:
                # Only create soup from response if we didn't use cloudscraper fallback
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for Art Institute of Chicago events page (/events)
            # This page lists all events (tours, talks, workshops) with their types
            if 'artic.edu' in venue.website_url:
                events_page_url = urljoin(venue.website_url, '/events')
                try:
                    logger.info(f"🔍 Checking Art Institute events page: {events_page_url}")
                    events_response = self.session.get(events_page_url, timeout=10)
                    logger.info(f"   Response status: {events_response.status_code}")
                    if events_response.status_code == 200:
                        events_soup = BeautifulSoup(events_response.content, 'html.parser')
                        # Log a sample of the page to debug
                        page_text_sample = events_soup.get_text()[:500]
                        logger.info(f"   Page text sample: {page_text_sample}")
                        artic_events = self._extract_events_from_artic_listing_page(
                            events_soup, venue, events_page_url, event_type=event_type, time_range=time_range
                        )
                        logger.info(f"   _extract_events_from_artic_listing_page returned {len(artic_events)} events")
                        if artic_events:
                            logger.info(f"✅ Extracted {len(artic_events)} events from Art Institute events page")
                            # Log event types found
                            event_types_found = {}
                            for e in artic_events:
                                etype = e.get('event_type', 'unknown')
                                event_types_found[etype] = event_types_found.get(etype, 0) + 1
                            logger.info(f"   Event types found: {event_types_found}")
                            events.extend(artic_events)
                            # If we're looking for a specific non-exhibition event type (tour, talk, workshop, etc.),
                            # we can return early since the /events page has all those types.
                            # But if we're looking for "all types" (empty event_type) or "exhibition",
                            # we should continue to also scrape exhibitions from other pages.
                            if event_type and event_type.strip() and event_type.lower() not in ['exhibition']:
                                logger.info(f"   Found {len(artic_events)} {event_type} events from /events page, returning early")
                                return events
                            # If event_type is empty (All Types) or 'exhibition', continue to scrape exhibitions too
                        else:
                            logger.warning(f"⚠️ No events extracted from Art Institute events page")
                    else:
                        logger.warning(f"⚠️ Art Institute events page returned status {events_response.status_code}")
                except Exception as e:
                    logger.error(f"❌ Error accessing Art Institute events page: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Look for exhibition-specific pages (for museums like LACMA, Smithsonian, Hirshhorn)
            exhibition_links = soup.find_all('a', href=lambda href: href and (
                'exhibition' in href.lower() or 
                'exhibit' in href.lower() or
                '/art/exhibition/' in href.lower() or
                '/exhibitions/' in href.lower() or
                '/explore/exhibitions/' in href.lower() or  # Smithsonian museums
                '/exhibitions-events/' in href.lower()  # Hirshhorn
            ))
            
            # Also look for links in exhibition-related sections
            exhibition_sections = soup.find_all(['div', 'section', 'article'], 
                class_=lambda c: c and ('exhibition' in str(c).lower() or 'exhibit' in str(c).lower()))
            for section in exhibition_sections:
                section_links = section.find_all('a', href=True)
                exhibition_links.extend(section_links)
            
            # Remove duplicates and limit
            seen_urls = set()
            unique_exhibition_links = []
            for link in exhibition_links:
                href = link.get('href', '')
                if href:
                    full_url = urljoin(venue.website_url, href)
                    if full_url not in seen_urls and 'exhibition' in full_url.lower():
                        seen_urls.add(full_url)
                        unique_exhibition_links.append(link)
            
            logger.info(f"Found {len(unique_exhibition_links)} exhibition links")
            
            # Only scrape exhibition pages if event_type is 'exhibition' or None (all types)
            if not event_type or event_type.lower() == 'exhibition':
                for link in unique_exhibition_links:  # Process all links but stop when we reach the limit
                    # Check if we've already reached the maximum
                    if len(events) >= max_exhibitions_per_venue:
                        logger.info(f"Reached maximum of {max_exhibitions_per_venue} exhibitions for {venue.name}")
                        break
                    
                    try:
                        exhibition_url = urljoin(venue.website_url, link['href'])
                        logger.info(f"Scraping exhibition page: {exhibition_url}")
                        exhibition_response = self.session.get(exhibition_url, timeout=10)
                        exhibition_response.raise_for_status()
                        exhibition_soup = BeautifulSoup(exhibition_response.content, 'html.parser')
                        
                        # For exhibition pages, treat the page itself as an exhibition event
                        # Check if this is an individual exhibition page (not a listing page)
                        # Different museums use different URL patterns:
                        # - LACMA: /art/exhibition/name
                        # - NGA: /exhibitions/name
                        # - Air and Space: /whats-on/exhibitions/name
                        # - Spy Museum: /exhibition-experiences/name
                        # - Phillips: /exhibitions/name
                        url_lower = exhibition_url.lower()
                        url_path = urlparse(exhibition_url).path.lower()
                        
                        # More precise listing page detection - check for exact listing page patterns
                        is_listing_page = any([
                            url_path == '/exhibitions',
                            url_path == '/exhibitions/',
                            url_path.endswith('/exhibitions'),
                            url_path.endswith('/exhibitions/'),
                            '/exhibitions/calendar' in url_path,
                            '/exhibitions/past' in url_path,
                            '/exhibitions/current' in url_path,
                            '/exhibitions/upcoming' in url_path,
                            '/past-exhibitions' in url_path,
                            ('/exhibition-experiences/' in url_path and url_path.count('/') <= 3) or  # Spy Museum listing
                            '/explore/exhibitions/washington' in url_path or  # Smithsonian museums
                            '/explore/exhibitions/newyork' in url_path or
                            '/explore/exhibitions/online' in url_path or
                            '/explore/exhibitions/upcoming' in url_path or
                            '/explore/exhibitions/past' in url_path or
                            '/calendar' in url_path and 'tab=exhibitions' in url_lower or  # NGA calendar exhibitions page
                            '/exhibitions-events' in url_path or  # Hirshhorn exhibitions page
                            (url_path == '/exhibitions' or url_path == '/exhibitions/') and 'metmuseum.org' in url_lower  # Met Museum exhibitions listing
                        ])
                        
                        # Check if it's an individual exhibition page (has a specific name/slug after the exhibition path)
                        is_individual_page = False
                        if not is_listing_page and url_lower != venue.website_url.lower():
                            # Special case: Smithsonian National Museum of the American Indian uses /explore/exhibitions/item?id=XXX
                            if '/explore/exhibitions/item?id=' in url_lower:
                                is_individual_page = True
                                logger.info(f"✅ Detected Smithsonian NMAI individual exhibition page: {exhibition_url}")
                            else:
                                # Check for individual page patterns with slugs
                                individual_patterns = [
                                    ('/art/exhibition/', 3),  # LACMA: /art/exhibition/name (3 parts: art, exhibition, name)
                                    ('/exhibitions/', 2),  # NGA/Phillips: /exhibitions/name (2 parts: exhibitions, name)
                                    ('/exhibition/', 2),  # Field Museum: /exhibition/name (2 parts: exhibition, name)
                                    ('/exhibition-experiences/', 2),  # Spy Museum: /exhibition-experiences/name
                                    ('/whats-on/exhibitions/', 3),  # Air and Space: /whats-on/exhibitions/name
                                    ('/explore/exhibitions/', 3),  # Smithsonian: /explore/exhibitions/name (but not washington/newyork/online)
                                ]
                                
                                for pattern, min_parts in individual_patterns:
                                    if pattern in url_lower:
                                        # Extract the path after the pattern
                                        path_after = url_lower.split(pattern)[1].split('/')[0].split('?')[0]
                                        # Skip category pages (not individual exhibitions)
                                        category_pages = ['traveling', 'past', 'upcoming', 'washington', 'newyork', 'online', 'current', 'future']
                                        if path_after.lower() in category_pages:
                                            logger.debug(f"⚠️ Skipping category page: {exhibition_url}")
                                            continue
                                        # Check if there's a meaningful slug (not empty, has letters, reasonable length)
                                        if path_after and len(path_after) > 3 and any(c.isalpha() for c in path_after):
                                            # Count path parts to ensure it's not too nested (likely a listing page)
                                            path_parts = [p for p in url_path.split('/') if p]
                                            if len(path_parts) >= min_parts:
                                                is_individual_page = True
                                                logger.info(f"✅ Detected individual exhibition page: {exhibition_url}")
                                                break
                        
                        if not is_individual_page and not is_listing_page:
                            logger.info(f"⚠️ URL not recognized as individual or listing page: {exhibition_url} (path: {url_path})")
                        
                        if is_individual_page:
                            # Check if we've already reached the maximum before extracting
                            if len(events) >= max_exhibitions_per_venue:
                                logger.info(f"Reached maximum of {max_exhibitions_per_venue} exhibitions for {venue.name}")
                                break
                            
                            # This is an individual exhibition page - extract it as an event
                            logger.info(f"Extracting individual exhibition from: {exhibition_url}")
                            exhibition_event = self._extract_exhibition_from_page(exhibition_soup, venue, exhibition_url, event_type, time_range)
                            if exhibition_event:
                                # Only add if it's current or future (check is done in _extract_exhibition_from_page)
                                logger.info(f"✅ Successfully extracted exhibition: {exhibition_event.get('title')}")
                                events.append(exhibition_event)
                                # Stop if we've reached the maximum
                                if len(events) >= max_exhibitions_per_venue:
                                    break
                            else:
                                logger.debug(f"⚠️ Failed to extract exhibition from: {exhibition_url}")
                        else:
                            # This is a listing page - try to extract exhibitions directly from the listing page first
                            logger.info(f"Found listing page, trying to extract exhibitions directly...")
                            # Calculate how many more exhibitions we can extract
                            remaining_slots = max_exhibitions_per_venue - len(events)
                            if remaining_slots <= 0:
                                logger.info(f"Reached maximum of {max_exhibitions_per_venue} exhibitions for {venue.name}")
                                break
                            
                            logger.info(f"🔍 Calling _extract_exhibitions_from_listing_page with remaining_slots={remaining_slots}, max_exhibitions_per_venue={max_exhibitions_per_venue}")
                            listing_events = self._extract_exhibitions_from_listing_page(exhibition_soup, venue, exhibition_url, event_type, time_range, remaining_slots)
                            if listing_events:
                                logger.info(f"✅ _extract_exhibitions_from_listing_page returned {len(listing_events)} exhibitions (remaining_slots was {remaining_slots}, current events count: {len(events)})")
                                # CRITICAL: Only add up to remaining_slots to prevent exceeding the limit
                                events_to_add = listing_events[:remaining_slots]
                                if len(listing_events) > remaining_slots:
                                    logger.error(f"❌ ERROR: Function returned {len(listing_events)} but remaining_slots was {remaining_slots}!")
                                events.extend(events_to_add)
                                logger.info(f"   Added {len(events_to_add)} exhibitions (total now: {len(events)}/{max_exhibitions_per_venue})")
                                # Stop here - don't also follow individual links to avoid duplicates
                                # The listing page extraction already got the exhibitions we need
                                # Break out of the loop since we've extracted from the listing page
                                # Also check if we've reached the limit
                                if len(events) > max_exhibitions_per_venue:
                                    logger.error(f"❌ ERROR: After adding, events count ({len(events)}) exceeds limit ({max_exhibitions_per_venue})!")
                                if len(events) >= max_exhibitions_per_venue:
                                    logger.info(f"✅ Reached maximum of {max_exhibitions_per_venue} exhibitions for {venue.name} after listing page extraction")
                                break
                            else:
                                # Fallback: find links to individual exhibitions and follow them
                                logger.info(f"Could not extract from listing page, searching for individual exhibition links...")
                                # Find links to individual exhibitions on the listing page
                                listing_exhibition_links = exhibition_soup.find_all('a', href=lambda href: href and (
                                    '/exhibitions/' in href.lower() or
                                    '/exhibition/' in href.lower() or
                                    '/exhibition-experiences/' in href.lower() or
                                    '/whats-on/exhibitions/' in href.lower() or
                                    '/explore/exhibitions/' in href.lower()  # Smithsonian museums
                                ))
                            
                            # Filter out listing page links and get unique individual exhibition URLs
                            seen_individual_urls = set()
                            for listing_link in listing_exhibition_links:
                                href = listing_link.get('href', '')
                                if href:
                                    individual_url = urljoin(exhibition_url, href)
                                    individual_url_lower = individual_url.lower()
                                    individual_path = urlparse(individual_url).path.lower()
                                    
                                    # Check if this is an individual exhibition page (not a listing page)
                                    is_listing = any(
                                        individual_path == '/exhibitions' or individual_path == '/exhibitions/' or
                                        individual_path.endswith('/exhibitions') or individual_path.endswith('/exhibitions/') or
                                        '/exhibitions/calendar' in individual_path or
                                        '/exhibitions/past' in individual_path or
                                        '/past-exhibitions' in individual_path
                                    )
                                    
                                    if not is_listing and individual_url_lower not in seen_individual_urls:
                                        # Special case: Smithsonian NMAI uses /explore/exhibitions/item?id=XXX
                                        is_individual = False
                                        if '/explore/exhibitions/item?id=' in individual_url_lower:
                                            is_individual = True
                                        else:
                                            # Check if it has a slug after the exhibition path
                                            individual_patterns = [
                                                ('/art/exhibition/', 3),
                                                ('/exhibitions/', 2),
                                                ('/exhibition-experiences/', 2),
                                                ('/whats-on/exhibitions/', 3),
                                            ]
                                            
                                            for pattern, min_parts in individual_patterns:
                                                if pattern in individual_url_lower:
                                                    path_after = individual_url_lower.split(pattern)[1].split('/')[0].split('?')[0]
                                                    if path_after and len(path_after) > 3 and any(c.isalpha() for c in path_after):
                                                        path_parts = [p for p in individual_path.split('/') if p]
                                                        if len(path_parts) >= min_parts:
                                                            is_individual = True
                                                            break
                                        
                                        if is_individual:
                                            seen_individual_urls.add(individual_url_lower)
                                            # Follow the link and extract the exhibition
                                            try:
                                                logger.info(f"Following link to individual exhibition: {individual_url}")
                                                individual_response = self.session.get(individual_url, timeout=10)
                                                individual_response.raise_for_status()
                                                individual_soup = BeautifulSoup(individual_response.content, 'html.parser')
                                                individual_event = self._extract_exhibition_from_page(
                                                    individual_soup, venue, individual_url, event_type, time_range
                                                )
                                                if individual_event:
                                                    # Only add if it's current or future (check is done in _extract_exhibition_from_page)
                                                    events.append(individual_event)
                                                    # Stop if we've reached the maximum
                                                    if len(events) >= max_exhibitions_per_venue:
                                                        break
                                            except Exception as e:
                                                logger.debug(f"Error following exhibition link {individual_url}: {e}")
                                                continue
                                        
                                        # Stop if we've reached the maximum
                                        if len(events) >= max_exhibitions_per_venue:
                                            break
                            
                            # Only try to extract events directly from listing page if we haven't already extracted from it
                            # (This is a fallback for museums that don't have structured listing pages)
                            # Skip this if we already extracted exhibitions from the listing page above
                            if len(events) == 0:
                                listing_events = self._extract_events_from_html(
                                    exhibition_soup, venue, exhibition_url, event_type=event_type, time_range=time_range
                                )
                                events.extend(listing_events)
                    except Exception as e:
                        logger.debug(f"Error scraping exhibition page {link['href']}: {e}")
                        continue
            
            # Only scrape tour pages if event_type is 'tour' or None (all types)
            if not event_type or event_type.lower() == 'tour':
                # Special handling for Hirshhorn Museum tours page
                if 'hirshhorn.si.edu' in venue.website_url.lower():
                    tours_page_url = urljoin(venue.website_url, '/explore/tours/')
                    try:
                        logger.info(f"🔍 Checking Hirshhorn tours page: {tours_page_url}")
                        tours_response = self.session.get(tours_page_url, timeout=10)
                        if tours_response.status_code == 200:
                            tours_soup = BeautifulSoup(tours_response.content, 'html.parser')
                            hirshhorn_tours = self._extract_hirshhorn_tours(
                                tours_soup, venue, tours_page_url, event_type=event_type, time_range=time_range
                            )
                            events.extend(hirshhorn_tours)
                            logger.info(f"   Found {len(hirshhorn_tours)} Hirshhorn tours")
                    except Exception as e:
                        logger.debug(f"⚠️ Error scraping Hirshhorn tours page: {e}")
                
                # Look for tour-specific pages (general case)
                tour_links = soup.find_all('a', href=lambda href: href and 'tour' in href.lower())
                for link in tour_links[:5]:  # Check first 5 tour links
                    try:
                        tour_url = urljoin(venue.website_url, link['href'])
                        # Skip if we already scraped the Hirshhorn tours page
                        if 'hirshhorn.si.edu' in tour_url.lower() and '/explore/tours/' in tour_url.lower():
                            continue
                        
                        logger.info(f"Scraping tour page: {tour_url}")
                        tour_response = self.session.get(tour_url, timeout=10)
                        tour_response.raise_for_status()
                        tour_soup = BeautifulSoup(tour_response.content, 'html.parser')
                        
                        # Extract events from tour page with tour URL context
                        tour_events = self._extract_events_from_html(
                            tour_soup, venue, tour_url, event_type=event_type, time_range=time_range
                        )
                        events.extend(tour_events)
                    except Exception as e:
                        logger.debug(f"Error scraping tour page {link['href']}: {e}")
                        continue
            
            # Look for event pages (for performances, concerts, talks, etc.) - not exhibitions
            # Initialize event_links list first
            event_links = []
            # Only if event_type is not 'exhibition' or None (all types)
            if not event_type or event_type.lower() != 'exhibition':
                # Look for /event/ URLs (Hirshhorn, etc.)
                event_links = soup.find_all('a', href=lambda href: href and '/event/' in href.lower())
            # Also look for event calendar links
            event_calendar_links = soup.find_all('a', href=lambda href: href and ('events' in href.lower() or 'calendar' in href.lower()))
            event_links.extend(event_calendar_links)
            
            # Special handling for OCMA calendar page
            if 'ocma.art' in venue.website_url.lower():
                calendar_url = urljoin(venue.website_url, '/calendar/')
                try:
                    logger.info(f"🔍 Checking OCMA calendar page: {calendar_url}")
                    calendar_response = self.session.get(calendar_url, timeout=10)
                    if calendar_response.status_code == 200:
                        calendar_soup = BeautifulSoup(calendar_response.content, 'html.parser')
                        ocma_events = self._extract_ocma_calendar_events(calendar_soup, venue, calendar_url, event_type=event_type, time_range=time_range)
                        if ocma_events:
                            logger.info(f"✅ Extracted {len(ocma_events)} events from OCMA calendar page")
                            events.extend(ocma_events)
                except Exception as e:
                    logger.debug(f"Error accessing OCMA calendar page: {e}")
                
                # Remove duplicates
                seen_event_urls = set()
                unique_event_links = []
                for link in event_links:
                    event_url = urljoin(venue.website_url, link['href'])
                    if event_url not in seen_event_urls:
                        seen_event_urls.add(event_url)
                        unique_event_links.append(link)
                
                for link in unique_event_links[:10]:  # Check first 10 event links
                    try:
                        event_url = urljoin(venue.website_url, link['href'])
                        # Skip if it's an exhibition URL
                        if '/exhibition' in event_url.lower() or '/exhibit' in event_url.lower():
                            continue
                        
                        # Skip OCMA special-events page (it's a listing page, not individual events)
                        if 'ocma.art' in event_url.lower() and '/special-events' in event_url.lower():
                            continue
                        
                        logger.info(f"Scraping event page: {event_url}")
                        event_response = self.session.get(event_url, timeout=10)
                        event_response.raise_for_status()
                        event_soup = BeautifulSoup(event_response.content, 'html.parser')
                        
                        # Extract events from event page
                        event_events = self._extract_events_from_html(
                            event_soup, venue, event_url, event_type=event_type, time_range=time_range
                        )
                        events.extend(event_events)
                    except Exception as e:
                        logger.debug(f"Error scraping event page {link['href']}: {e}")
                        continue
            
            # For LACMA, look for exhibition links in the exhibitions section
            # Only if event_type is 'exhibition' or None (all types)
            if 'lacma.org' in venue.website_url and (not event_type or event_type.lower() == 'exhibition'):
                # Try to find the exhibitions page
                exhibitions_page_url = urljoin(venue.website_url, '/art/exhibitions')
                try:
                    logger.info(f"Scraping LACMA exhibitions page: {exhibitions_page_url}")
                    exhibitions_response = self.session.get(exhibitions_page_url, timeout=10)
                    if exhibitions_response.status_code == 200:
                        exhibitions_soup = BeautifulSoup(exhibitions_response.content, 'html.parser')
                        # Find all exhibition links
                        lacma_exhibition_links = exhibitions_soup.find_all('a', href=lambda href: href and '/art/exhibition/' in href.lower())
                        for link in lacma_exhibition_links[:15]:  # Check first 15 exhibitions
                            try:
                                exhibition_url = urljoin(venue.website_url, link['href'])
                                logger.info(f"Scraping LACMA exhibition: {exhibition_url}")
                                exhibition_response = self.session.get(exhibition_url, timeout=10)
                                exhibition_response.raise_for_status()
                                exhibition_soup = BeautifulSoup(exhibition_response.content, 'html.parser')
                                
                                # For exhibition pages, treat the page itself as an exhibition event
                                # Check if it's an individual exhibition page (same logic as above)
                                is_listing_page = any(keyword in exhibition_url.lower() for keyword in [
                                    '/exhibitions',  # Plural (listing page)
                                    '/exhibition-experiences/',  # Spy Museum listing
                                    '/whats-on/exhibitions',  # Air and Space listing
                                    '/calendar',
                                    '/past-exhibitions',
                                    '/current',
                                    '/upcoming'
                                ])
                                
                                is_individual_page = any(pattern in exhibition_url.lower() for pattern in [
                                    '/exhibition/', '/exhibitions/', '/exhibition-experiences/', '/whats-on/exhibitions/'
                                ]) and not is_listing_page
                                
                                if is_individual_page:
                                    # Extract the path after the exhibition keyword to verify it's a specific page
                                    url_lower = exhibition_url.lower()
                                    for pattern in ['/exhibition/', '/exhibitions/', '/exhibition-experiences/', '/whats-on/exhibitions/']:
                                        if pattern in url_lower:
                                            path_after = url_lower.split(pattern)[1].split('/')[0].split('?')[0]
                                            # Skip category pages (not individual exhibitions)
                                            category_pages = ['traveling', 'past', 'upcoming', 'washington', 'newyork', 'online', 'current', 'future']
                                            if path_after.lower() in category_pages:
                                                logger.debug(f"⚠️ Skipping category page: {exhibition_url}")
                                                break
                                            if path_after and len(path_after) > 3 and any(c.isalpha() for c in path_after):
                                                exhibition_event = self._extract_exhibition_from_page(exhibition_soup, venue, exhibition_url, event_type, time_range)
                                                if exhibition_event:
                                                    events.append(exhibition_event)
                                                    # Stop if we've reached the maximum
                                                    if len(events) >= max_exhibitions_per_venue:
                                                        break
                                                break
                                else:
                                    # Listing page - extract events from it
                                    exhibition_events = self._extract_events_from_html(
                                        exhibition_soup, venue, exhibition_url, event_type=event_type, time_range=time_range
                                    )
                                    events.extend(exhibition_events)
                            except Exception as e:
                                logger.debug(f"Error scraping LACMA exhibition {link['href']}: {e}")
                                continue
                except Exception as e:
                    logger.debug(f"Error accessing LACMA exhibitions page: {e}")
            
            # For Met Museum, also try specific known tour URLs
            if 'metmuseum.org' in venue.website_url:
                known_tour_urls = [
                    'https://engage.metmuseum.org/events/public-guided-tours/collection-tour-islamic-art/',
                    'https://engage.metmuseum.org/events/public-guided-tours/collection-tour-egyptian-art/',
                    'https://engage.metmuseum.org/events/public-guided-tours/collection-tour-european-paintings/',
                    'https://engage.metmuseum.org/events/public-guided-tours/museum-highlights/',
                ]
                
                for tour_url in known_tour_urls:
                    try:
                        logger.info(f"Scraping known tour page: {tour_url}")
                        tour_response = self.session.get(tour_url, timeout=10)
                        tour_response.raise_for_status()
                        tour_soup = BeautifulSoup(tour_response.content, 'html.parser')
                        
                        # Extract events from tour page with tour URL context
                        tour_events = self._extract_events_from_html(
                            tour_soup, venue, tour_url, event_type=event_type, time_range=time_range
                        )
                        events.extend(tour_events)
                    except Exception as e:
                        logger.debug(f"Error scraping known tour page {tour_url}: {e}")
                    continue
            
            # Also check main page for events (but only if we haven't already extracted exhibitions)
            # This prevents duplicates when exhibitions are already extracted from listing pages
            if event_type and event_type.lower() == 'exhibition':
                # For exhibitions, skip main page extraction if we already have exhibitions
                # (they would have been extracted from listing pages)
                # Also check if we've reached the limit
                exhibition_count = len([e for e in events if e.get('event_type') == 'exhibition'])
                if exhibition_count == 0 and len(events) < max_exhibitions_per_venue:
                    main_events = self._extract_events_from_html(soup, venue, event_type=event_type, time_range=time_range)
                    # Filter to only exhibitions and limit
                    main_exhibitions = [e for e in main_events if e.get('event_type') == 'exhibition']
                    remaining_slots = max_exhibitions_per_venue - exhibition_count
                    events.extend(main_exhibitions[:remaining_slots])
            else:
                # For other event types, always check main page
                main_events = self._extract_events_from_html(soup, venue, event_type=event_type, time_range=time_range)
                events.extend(main_events)
            
        except Timeout:
            logger.error(f"⏱️ Timeout error scraping website {venue.website_url} - returning empty list")
            return events
        except ConnectionError as e:
            logger.error(f"🔌 Connection error scraping website {venue.website_url}: {e} - returning empty list")
            return events
        except RequestException as e:
            logger.error(f"❌ Request error scraping website {venue.website_url}: {e} - returning empty list")
            return events
        except Exception as e:
            logger.error(f"❌ Unexpected error scraping website {venue.website_url}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return events
        
        # Final limit check - ensure we don't return more than max_exhibitions_per_venue for exhibitions
        if event_type and event_type.lower() == 'exhibition':
            exhibition_events = [e for e in events if e.get('event_type') == 'exhibition']
            other_events = [e for e in events if e.get('event_type') != 'exhibition']
            # Limit exhibitions to max_exhibitions_per_venue, keep all other event types
            if len(exhibition_events) > max_exhibitions_per_venue:
                logger.warning(f"⚠️ CRITICAL: Found {len(exhibition_events)} exhibitions for {venue.name}, limiting to {max_exhibitions_per_venue}")
                logger.warning(f"   Exhibition titles: {[e.get('title') for e in exhibition_events]}")
            limited_exhibitions = exhibition_events[:max_exhibitions_per_venue]
            events = limited_exhibitions + other_events
            if len(exhibition_events) > max_exhibitions_per_venue:
                logger.error(f"❌ CRITICAL ERROR: _scrape_venue_website found {len(exhibition_events)} exhibitions for {venue.name}, but limit is {max_exhibitions_per_venue}!")
                logger.error(f"   Exhibition titles: {[e.get('title') for e in exhibition_events]}")
            logger.info(f"📦 _scrape_venue_website FINAL RETURN: {len(limited_exhibitions)} exhibitions for {venue.name} (found {len(exhibition_events)}, limit {max_exhibitions_per_venue})")
        
        # ABSOLUTE FINAL CHECK: Never return more than max_exhibitions_per_venue exhibitions
        # This is the last line of defense - slice the list one more time just to be absolutely sure
        if event_type and event_type.lower() == 'exhibition':
            final_exhibitions = [e for e in events if e.get('event_type') == 'exhibition']
            final_others = [e for e in events if e.get('event_type') != 'exhibition']
            final_limited = final_exhibitions[:max_exhibitions_per_venue]
            events = final_limited + final_others
            if len(final_exhibitions) > max_exhibitions_per_venue:
                logger.error(f"❌ ABSOLUTE FINAL CHECK FAILED: Still had {len(final_exhibitions)} exhibitions after all checks!")
        
        # If no events found and no specialized scraper was used, try generic scraper as fallback
        if len(events) == 0:
            logger.info(f"⚠️  No events found with standard methods for {venue.name}, trying generic scraper as fallback...")
            try:
                from scripts.generic_venue_scraper import GenericVenueScraper
                generic_scraper = GenericVenueScraper()
                generic_events = generic_scraper.scrape_venue_events(
                    venue_url=venue.website_url,
                    venue_name=venue.name,
                    event_type=event_type,
                    time_range=time_range
                )
                # Convert generic events to our format and validate them
                valid_generic_events = []
                for event in generic_events:
                    event['venue_id'] = venue.id
                    event['city_id'] = venue.city_id
                    event['source'] = 'website'
                    event['source_url'] = venue.website_url
                    event['organizer'] = venue.name
                    # Add meeting_point if start_location exists
                    if event.get('start_location') and not event.get('meeting_point'):
                        event['meeting_point'] = event.get('start_location')
                    
                    # Validate the event before adding it
                    if self._is_valid_event(event):
                        valid_generic_events.append(event)
                    else:
                        logger.debug(f"⚠️ Generic scraper event filtered out: '{event.get('title', 'N/A')}'")
                
                events.extend(valid_generic_events)
                if valid_generic_events:
                    logger.info(f"✅ Generic scraper found {len(valid_generic_events)} valid events for {venue.name} (filtered {len(generic_events) - len(valid_generic_events)} invalid events)")
                elif generic_events:
                    logger.info(f"⚠️ Generic scraper found {len(generic_events)} events but all were filtered out by validation")
            except Exception as generic_error:
                logger.debug(f"Generic scraper fallback failed: {generic_error}")
        
        return events
    
    def _extract_events_from_html(self, soup, venue, tour_url=None, event_type=None, time_range='today'):
        """Extract events from HTML content"""
        events = []
        
        logger.info(f"🔍 Parsing HTML for {venue.name}...")
        
        # Look for tour-specific content first
        tour_keywords = ['public guided tour', 'private guided tour', 'premium guided tour', 'accessibility tour', 'multilingual app']
        
        # Find headings that contain tour information
        tour_headings = soup.find_all(['h1', 'h2', 'h3', 'h4'], string=lambda text: text and any(keyword in text.lower() for keyword in tour_keywords))
        logger.info(f"   Found {len(tour_headings)} tour headings")
        
        for heading in tour_headings:
            # Get the parent section
            section = heading.find_parent(['div', 'section', 'article'])
            if section:
                event_data = self._parse_event_element(section, venue, tour_url=tour_url, event_type=event_type, time_range=time_range)
                if event_data:
                    events.append(event_data)
        
        # Also look for tour descriptions
        tour_descriptions = soup.find_all('p', string=lambda text: text and ('guided tour' in text.lower() or 'self-guided' in text.lower()))
        for desc in tour_descriptions:
            event_data = self._parse_event_element(desc, venue, tour_url=tour_url, event_type=event_type, time_range=time_range)
            if event_data:
                events.append(event_data)
        
        # Common selectors for events
        event_selectors = [
            '.event', '.events', '.event-item', '.event-card',
            '.calendar-event', '.upcoming-event', '.program',
            '.tour', '.tours', '.guided-tour', '.walking-tour',
            '[class*="event"]', '[class*="program"]', '[class*="tour"]'
        ]
        
        total_elements_found = 0
        for selector in event_selectors:
            event_elements = soup.select(selector)
            if event_elements:
                logger.info(f"   Selector '{selector}' found {len(event_elements)} elements")
                total_elements_found += len(event_elements)
            
            for element in event_elements:
                try:
                    event_data = self._parse_event_element(element, venue, tour_url=tour_url, event_type=event_type, time_range=time_range)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.debug(f"Error parsing event element: {e}")
                    continue
        
        logger.info(f"   Total event elements found: {total_elements_found}, Valid events extracted: {len(events)}")
        return events
    
    def _parse_event_element(self, element, venue, tour_url=None, event_type=None, time_range='today'):
        """Parse individual event element with enhanced intelligence"""
        try:
            # Extract title with improved logic
            title = self._extract_text(element, [
                'h1', 'h2', 'h3', '.title', '.event-title', '.name'
            ])
            
            if not title:
                logger.debug(f"   ❌ No title found in element")
                return None
            
            logger.info(f"   📝 Extracted title: '{title}'")
            
            # Extract description first to use in title logic
            description = self._extract_text(element, [
                '.description', '.summary', '.content', 'p'
            ])
            
            # Enhanced title improvement logic
            title = self._improve_title(title, description, venue, tour_url)
            title = self._clean_title(title)  # Clean and normalize title text
            
            # Extract date/time with enhanced parsing
            # First try specific date selectors
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when', '.exhibition-date', '.date-range'
            ])
            
            # If no date found in specific selectors, extract from element's full text
            # This is important for listing pages where dates are in the general text
            if not date_text or len(date_text) < 5:
                element_text = element.get_text() if hasattr(element, 'get_text') else str(element)
                # Look for date patterns in the element text
                date_patterns = [
                    r'([A-Z][a-z]{2,9}\s+\d{1,2}[–—\-]\s*[A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4})',  # January 17–May 3, 2026
                    r'([A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4}[–—\-]\s*[A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4})',  # January 17, 2026–May 3, 2026
                    r'(\d{1,2}/\d{1,2}/\d{4}[–—\-]\d{1,2}/\d{1,2}/\d{4})',  # 1/17/2026–5/3/2026
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, element_text)
                    if match:
                        date_text = match.group(1)
                        logger.info(f"   📅 Found date in element text: {date_text}")
                        break
            
            # Extract location/meeting point with enhanced detection
            location = self._extract_location(element, venue)
            
            # Extract URL - use tour_url/exhibition_url if available, otherwise extract from element
            url = tour_url  # Use the tour/exhibition page URL as the primary URL
            if not url:
                url = self._extract_url(element, venue)
                # Ensure URL is absolute
                if url and not url.startswith('http'):
                    url = urljoin(venue.website_url, url)
            
            # Clean up URL - remove fragments and ensure it's a proper URL
            if url:
                # Remove common fragments that don't add value
                url = url.split('#')[0].split('?')[0] if '#' in url or '?' in url else url
                # Skip if it's just the homepage
                parsed = urlparse(url)
                if parsed.path in ['', '/'] and not parsed.query:
                    # If we have a better URL from the element, use that instead
                    element_url = self._extract_url(element, venue)
                    if element_url and element_url != url:
                        url = element_url
                        if not url.startswith('http'):
                            url = urljoin(venue.website_url, url)
            
            # Extract image
            image_url = self._extract_image(element, venue)
            
            # Determine event type based on venue type (if not already determined)
            if not event_type:
                event_type = self._determine_event_type(venue.venue_type, title, description)
            
            # Parse dates - use exhibition-specific parser for exhibitions
            if event_type == 'exhibition' and date_text:
                start_date, end_date, start_time, end_time = self._parse_exhibition_dates(
                    date_text, url, venue, time_range=time_range
                )
            else:
                # Use enhanced parser for tours and other event types
                start_date, end_date, start_time, end_time = self._parse_dates_enhanced(
                    date_text, url, venue, event_type=event_type, time_range=time_range
                )
            
            # Extract meeting point information
            meeting_point = self._extract_meeting_point(element, description)
            
            event_data = {
                'title': title,
                'description': description or '',
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location,
                'meeting_point': meeting_point,
                'venue_id': venue.id,
                'city_id': venue.city_id,
                'event_type': event_type,
                'url': url,
                'image_url': image_url,
                'source': 'website',
                'source_url': venue.website_url,
                'organizer': venue.name
            }
            
            # Extract exhibition-specific fields if this is an exhibition
            if event_type == 'exhibition':
                exhibition_details = self._extract_exhibition_details(element, description, url)
                event_data.update(exhibition_details)
            
            # Validate event quality before returning
            if not self._is_valid_event(event_data):
                logger.info(f"⚠️ Filtered out: '{title}'")
                logger.info(f"   Reason: Has time={event_data.get('start_time') is not None}, Has URL={event_data.get('url') != event_data.get('source_url')}, Has desc={bool(description)}, Desc len={len(description or '')}")
                return None
            
            logger.info(f"✅ Valid event found: '{title}'")
            return event_data
            
        except Exception as e:
            logger.debug(f"Error parsing event element: {e}")
            return None
    
    def _clean_title(self, title):
        """Clean and normalize title text to fix common issues"""
        if not title:
            return title
        
        import re
        
        # Remove trailing commas and whitespace
        title = re.sub(r',\s*$', '', title)
        title = title.strip()
        
        # Remove dates from title (e.g., "December 10, 2025," or "Dec 10, 2025")
        # Pattern: Month Day, Year or Month Day Year
        date_patterns = [
            r'\s*[A-Z][a-z]+\s+\d{1,2},?\s+\d{4},?\s*$',  # "December 10, 2025," or "December 10, 2025"
            r'\s*[A-Z][a-z]{2,3}\.?\s+\d{1,2},?\s+\d{4},?\s*$',  # "Dec. 10, 2025," or "Dec 10, 2025"
            r'\s*\d{1,2}/\d{1,2}/\d{4},?\s*$',  # "12/10/2025,"
            r'\s*\d{1,2}-\d{1,2}-\d{4},?\s*$',  # "12-10-2025,"
        ]
        for pattern in date_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Fix missing spaces after apostrophes (e.g., "Bellows'sLove" -> "Bellows's Love")
        title = re.sub(r"([a-z]'s)([A-Z])", r"\1 \2", title)
        
        # Fix missing spaces after colons (e.g., "Title:Subtitle" -> "Title: Subtitle")
        title = re.sub(r"([^:]):([A-Za-z])", r"\1: \2", title)
        
        # Fix missing spaces after periods (e.g., "Mr.John" -> "Mr. John")
        title = re.sub(r"([a-z])\.([A-Z])", r"\1. \2", title)
        
        # Fix missing spaces before capital letters after lowercase (e.g., "wordWord" -> "word Word")
        # But be careful not to break acronyms or proper nouns
        title = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", title)
        
        # Normalize multiple spaces to single space
        title = re.sub(r'\s+', ' ', title)
        
        # Strip leading/trailing whitespace
        title = title.strip()
        
        return title
    
    def _extract_text(self, element, selectors):
        """Extract text from element using multiple selectors"""
        for selector in selectors:
            found = element.select_one(selector)
            if found and found.get_text(strip=True):
                return found.get_text(strip=True)
        return None
    
    def _extract_url(self, element, venue=None):
        """Extract URL from event element with improved logic for exhibitions"""
        # Priority 1: Look for links in the element itself
        link = element.find('a', href=True)
        if link:
            href = link['href']
            # Skip generic/homepage links
            if href and href not in ['#', '#main-content', '/', '']:
                # Prefer exhibition/event-specific URLs
                if any(keyword in href.lower() for keyword in ['exhibition', 'exhibit', 'event', 'program', 'tour']):
                    if venue:
                        return urljoin(venue.website_url, href)
                    return href if href.startswith('http') else href
                # Otherwise return any valid link
                if venue:
                    return urljoin(venue.website_url, href)
                return href if href.startswith('http') else href
        
        # Priority 2: Look for parent links (element might be inside a link)
        parent_link = element.find_parent('a', href=True)
        if parent_link:
            href = parent_link['href']
            if href and href not in ['#', '#main-content', '/', '']:
                # Prefer exhibition/event-specific URLs
                if any(keyword in href.lower() for keyword in ['exhibition', 'exhibit', 'event', 'program', 'tour']):
                    if venue:
                        return urljoin(venue.website_url, href)
                    return href if href.startswith('http') else href
                # Otherwise return any valid link
                if venue:
                    return urljoin(venue.website_url, href)
                return href if href.startswith('http') else href
        
        # Priority 3: Look for nearby links (sibling or nearby elements)
        # Check if element is in a card/list item that might have a link nearby
        parent = element.find_parent(['div', 'li', 'article', 'section'])
        if parent:
            nearby_link = parent.find('a', href=True)
            if nearby_link:
                href = nearby_link['href']
                if href and href not in ['#', '#main-content', '/', '']:
                    if any(keyword in href.lower() for keyword in ['exhibition', 'exhibit', 'event', 'program', 'tour']):
                        if venue:
                            return urljoin(venue.website_url, href)
                        return href if href.startswith('http') else href
        
        return None
    
    def _extract_image(self, element, venue):
        """Extract image from event element with enhanced detection"""
        import re
        
        # Look for images in the element
        img = element.find('img')
        if img:
            # Try multiple image source attributes (lazy loading, responsive images, etc.)
            img_src = (img.get('src') or 
                      img.get('data-src') or 
                      img.get('data-lazy-src') or
                      img.get('data-original'))
            
            # Also check srcset for responsive images
            if not img_src and img.get('srcset'):
                srcset = img.get('srcset')
                # Extract first URL from srcset
                srcset_match = re.search(r'([^\s,]+\.(?:jpg|jpeg|png|gif|webp))', srcset, re.IGNORECASE)
                if srcset_match:
                    img_src = srcset_match.group(1)
            
            if img_src:
                # Convert relative URLs to absolute
                if img_src.startswith('/'):
                    img_src = urljoin(venue.website_url, img_src)
                elif not img_src.startswith('http'):
                    img_src = urljoin(venue.website_url, img_src)
                
                # Skip Google Maps photo references (long base64-like strings)
                if len(img_src) > 100 and not img_src.startswith('http'):
                    return None
                
                # Skip data URIs and placeholder images
                if img_src.startswith('data:') or 'placeholder' in img_src.lower():
                    pass
                else:
                    return img_src
        
        # Look for background images in CSS
        style = element.get('style', '')
        if 'background-image' in style:
            bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
            if bg_match:
                img_src = bg_match.group(1)
                if img_src.startswith('/'):
                    img_src = urljoin(venue.website_url, img_src)
                elif not img_src.startswith('http'):
                    img_src = urljoin(venue.website_url, img_src)
                
                # Skip Google Maps photo references
                if len(img_src) > 100 and not img_src.startswith('http'):
                    return None
                    
                return img_src
        
        # Look for picture element (modern responsive images)
        picture = element.find('picture')
        if picture:
            source = picture.find('source')
            if source and source.get('srcset'):
                srcset = source.get('srcset')
                srcset_match = re.search(r'([^\s,]+\.(?:jpg|jpeg|png|gif|webp))', srcset, re.IGNORECASE)
                if srcset_match:
                    img_src = srcset_match.group(1)
                    if img_src.startswith('/'):
                        img_src = urljoin(venue.website_url, img_src)
                    elif not img_src.startswith('http'):
                        img_src = urljoin(venue.website_url, img_src)
                    return img_src
        
        # Use venue's default image only if it's a proper URL
        if venue.image_url and venue.image_url.startswith('http') and len(venue.image_url) < 200:
            return venue.image_url
        
        return None
    
    def _improve_title(self, title, description, venue, tour_url):
        """Improve event title with better context and specificity"""
        
        # If we have a tour_url, try to extract the real title from the page
        if tour_url and ('metmuseum.org' in tour_url or 'engage.metmuseum.org' in tour_url):
            try:
                response = self.session.get(tour_url, timeout=5)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try to get the real page title
                page_title = soup.find('title')
                if page_title:
                    page_title_text = page_title.get_text(strip=True)
                    if 'Collection Tour' in page_title_text:
                        # Extract the specific tour type from the title
                        if 'Islamic Art' in page_title_text:
                            title = "Collection Tour: Islamic Art"
                        elif 'Egyptian Art' in page_title_text:
                            title = "Collection Tour: Egyptian Art"
                        elif 'European Paintings' in page_title_text:
                            title = "Collection Tour: European Paintings"
                        elif 'Museum Highlights' in page_title_text:
                            title = "Museum Highlights Tour"
                        else:
                            title = page_title_text
                        logger.info(f"📝 Extracted real title from page: '{title}'")
                        # Clean title before returning
                        return self._clean_title(title)
                
                # Also try h1 tags
                h1_tag = soup.find('h1')
                if h1_tag:
                    h1_text = h1_tag.get_text(strip=True)
                    if 'Collection Tour' in h1_text:
                        title = h1_text
                        logger.info(f"📝 Extracted title from h1: '{title}'")
                        # Clean title before returning
                        return self._clean_title(title)
                        
            except Exception as e:
                logger.debug(f"Error extracting title from {tour_url}: {e}")
        
        # Fallback to original logic for generic titles
        if title in ['Guided Museum Tour', 'Self-Guided Audio Tour', 'Tour', 'Exhibition', 'Event', 'Upcoming Public Programs', 'Upcoming Events', 'Past Events']:
            # Try to extract more specific information from URL or description
            if tour_url:
                # Extract specific tour type from URL
                if 'islamic' in tour_url.lower():
                    title = "Collection Tour: Islamic Art"
                elif 'egyptian' in tour_url.lower():
                    title = "Collection Tour: Egyptian Art"
                elif 'european' in tour_url.lower():
                    title = "Collection Tour: European Paintings"
                elif 'modern' in tour_url.lower():
                    title = "Collection Tour: Modern Art"
                elif 'collection' in tour_url.lower():
                    title = "Collection Tour"
                else:
                    title = f"Museum Tour - {venue.name}"
            elif description:
                # Extract from description
                desc_lower = description.lower()
                if 'islamic' in desc_lower:
                    title = "Collection Tour: Islamic Art"
                elif 'egyptian' in desc_lower:
                    title = "Collection Tour: Egyptian Art"
                elif 'european' in desc_lower:
                    title = "Collection Tour: European Paintings"
                elif 'modern' in desc_lower:
                    title = "Collection Tour: Modern Art"
                else:
                    title = f"Museum Tour - {venue.name}"
            else:
                title = f"Museum Tour - {venue.name}"
        
        # Remove generic date-based titles and replace with descriptive ones
        date_patterns = [
            r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+.*$',
            r'^(\d{1,2}/\d{1,2}/\d{4})$',
            r'^(\d{4}-\d{1,2}-\d{1,2})$',
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, title):
                # Replace date-based title with more descriptive one
                if description:
                    desc_lower = description.lower()
                    if 'islamic' in desc_lower:
                        title = "Islamic Art Collection Tour"
                    elif 'egyptian' in desc_lower:
                        title = "Egyptian Art Collection Tour"
                    elif 'european' in desc_lower:
                        title = "European Art Collection Tour"
                    elif 'modern' in desc_lower:
                        title = "Modern Art Collection Tour"
                    elif 'highlights' in desc_lower:
                        title = "Museum Highlights Tour"
                    elif 'collection' in desc_lower:
                        title = "Collection Tour"
                    else:
                        title = f"Museum Tour - {venue.name}"
                else:
                    title = f"Museum Tour - {venue.name}"
                break
        
        # Also handle generic "Collection Tour" title
        if title == "Collection Tour" and description:
            desc_lower = description.lower()
            if 'islamic' in desc_lower:
                title = "Islamic Art Collection Tour"
            elif 'egyptian' in desc_lower:
                title = "Egyptian Art Collection Tour"
            elif 'european' in desc_lower:
                title = "European Art Collection Tour"
            elif 'modern' in desc_lower:
                title = "Modern Art Collection Tour"
            elif 'highlights' in desc_lower:
                title = "Museum Highlights Tour"
            elif 'span' in desc_lower and 'years' in desc_lower:
                title = "Museum Highlights Tour"
        
        return title

    def _extract_location(self, element, venue):
        """Extract location information with enhanced detection"""
        # First try standard location selectors
        location = self._extract_text(element, [
            '.location', '.venue', '.where', '.address'
        ])
        
        if location:
            return location
        
        # If no location found, use venue name
        return venue.name

    def _extract_meeting_point(self, element, description):
        """Extract meeting point information from element and description"""
        meeting_point = None
        
        # Look for meeting point patterns in the element text
        element_text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        # Common meeting point patterns
        meeting_patterns = [
            r'meeting\s+point[:\s]*([^.\n]+)',
            r'departs?\s+from[:\s]*([^.\n]+)',
            r'meet\s+at[:\s]*([^.\n]+)',
            r'gallery\s+(\d+)',
            r'hall\s+(\d+)',
            r'patio[:\s]*([^.\n]+)',
            r'lobby[:\s]*([^.\n]+)',
        ]
        
        for pattern in meeting_patterns:
            match = re.search(pattern, element_text, re.IGNORECASE)
            if match:
                meeting_point = match.group(1).strip()
                break
        
        # Also check description
        if not meeting_point and description:
            for pattern in meeting_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    meeting_point = match.group(1).strip()
                    break
        
        return meeting_point

    def _scrape_with_cloudscraper(self, url):
        """Scrape a page using cloudscraper to bypass bot protection (Railway-compatible)"""
        try:
            import cloudscraper
            import platform
            
            # Detect platform for Railway compatibility (Linux) vs local (macOS/Windows)
            detected_platform = platform.system().lower()
            if detected_platform == 'linux' or 'RAILWAY_ENVIRONMENT' in os.environ:
                platform_name = 'linux'
            elif detected_platform == 'darwin':
                platform_name = 'darwin'
            else:
                platform_name = 'windows'
            
            # Create a cloudscraper session with platform detection
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': platform_name,
                    'desktop': True
                }
            )
            
            # Disable SSL verification to avoid certificate errors
            scraper.verify = False
            
            # Make the request
            response = scraper.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            logger.debug(f"Error scraping with cloudscraper: {e}")
            return None
    
    def _parse_dates_enhanced(self, date_text, url, venue, event_type=None, time_range='today'):
        """Parse dates with enhanced schedule logic for recurring events"""
        from datetime import datetime, time, timedelta
        
        # Calculate date range based on time_range
        today = date.today()
        
        if time_range == 'today':
            range_start = today
            range_end = today
        elif time_range == 'this_week':
            range_start = today
            range_end = today + timedelta(days=7)
        elif time_range == 'this_month':
            range_start = today
            range_end = today + timedelta(days=30)
        else:
            # Default to this week
            range_start = today
            range_end = today + timedelta(days=7)
        
        # Default dates based on event type, but be flexible
        # Exhibitions can be single-day, date ranges, or ongoing
        # Tours are typically specific events on specific dates
        if event_type == 'exhibition':
            # For exhibitions, default to the full range (they might be ongoing)
            # But actual dates will be extracted from the page if available
            start_date = range_start
            end_date = range_end
        else:
            # Tours are specific events, default to today
            start_date = today
            end_date = today
        
        start_time = None
        end_time = None
        
        # If we have a Met Museum URL, scrape the actual page to get schedule info
        if url and 'metmuseum.org' in url:
            try:
                logger.info(f"🔍 Scraping Met Museum page for schedule: {url}")
                page_html = self._scrape_with_cloudscraper(url)
                
                if page_html:
                    soup = BeautifulSoup(page_html, 'html.parser')
                    page_text = soup.get_text()
                    
                    logger.info(f"📄 Page text sample: {page_text[:500]}")
                    
                    # Look for day-of-week patterns with times
                    # Examples: "Fridays 6:30pm - 7:30pm", "Weekdays 3:00pm", "Sundays 1:00pm"
                    day_time_patterns = [
                        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Weekday|Weekend)s?\s+(\d{1,2}):(\d{2})\s*([ap]m)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]m)',
                        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Weekday|Weekend)s?\s+(\d{1,2}):(\d{2})\s*([ap]m)',
                    ]
                    
                    for pattern in day_time_patterns:
                        match = re.search(pattern, page_text, re.IGNORECASE)
                        if match:
                            day_mentioned = match.group(1).lower()
                            weekday = today.strftime('%A').lower()
                            
                            logger.info(f"📅 Found schedule: {match.group(0)}")
                            logger.info(f"📅 Day mentioned: {day_mentioned}, Today: {weekday}")
                            
                            # Check if today matches the mentioned day
                            if day_mentioned in weekday or (day_mentioned == 'weekday' and weekday not in ['saturday', 'sunday']):
                                # Extract start time
                                hour = int(match.group(2))
                                minute = int(match.group(3))
                                ampm = match.group(4).upper()
                                
                                if ampm == 'PM' and hour != 12:
                                    hour += 12
                                elif ampm == 'AM' and hour == 12:
                                    hour = 0
                                
                                start_time = time_class(hour, minute)
                                
                                # Extract end time if available (pattern with range)
                                if len(match.groups()) >= 7:
                                    end_hour = int(match.group(5))
                                    end_minute = int(match.group(6))
                                    end_ampm = match.group(7).upper()
                                    
                                    if end_ampm == 'PM' and end_hour != 12:
                                        end_hour += 12
                                    elif end_ampm == 'AM' and end_hour == 12:
                                        end_hour = 0
                                    
                                    end_time = time_class(end_hour, end_minute)
                                    logger.info(f"⏰ Extracted times from page: {start_time} - {end_time}")
                                else:
                                    logger.info(f"⏰ Extracted start time from page: {start_time}")
                                
                                break
                            else:
                                # Day doesn't match - skip this event
                                logger.info(f"📅 Skipping event: {day_mentioned} tour but today is {weekday}")
                                return None, None, None, None
                    
            except Exception as e:
                logger.debug(f"Error scraping Met Museum page: {e}")
        
        # Fallback: Try to extract time from URL (e.g., "630pm" → 6:30 PM)
        if not start_time and url:
            url_time_match = re.search(r'(\d{1,2})(\d{2})(am|pm)', url.lower())
            if url_time_match:
                hour = int(url_time_match.group(1))
                minute = int(url_time_match.group(2))
                ampm = url_time_match.group(3).upper()
                
                if ampm == 'PM' and hour != 12:
                    hour += 12
                elif ampm == 'AM' and hour == 12:
                    hour = 0
                
                start_time = time(hour, minute)
                logger.info(f"⏰ Extracted time from URL: {start_time}")
        
        # If we have a start time but no end time, assume 1-hour duration for tours
        if start_time and not end_time:
            from datetime import timedelta
            # Calculate end time (start time + 1 hour)
            start_datetime = datetime.combine(today, start_time)
            end_datetime = start_datetime + timedelta(hours=1)
            end_time = end_datetime.time()
            logger.info(f"⏰ Assuming 1-hour tour duration: {start_time} - {end_time}")
        
        # Look for explicit time patterns in date_text
        if date_text:
            # First, try to parse date from weekday abbreviation format (e.g., "Wed, Dec 3")
            weekday_month_pattern = r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+([A-Z][a-z]{2,3})\s+(\d{1,2})'
            date_match = re.search(weekday_month_pattern, date_text, re.IGNORECASE)
            if date_match:
                month_abbr = date_match.group(2)
                day = int(date_match.group(3))
                # Map month abbreviations to numbers
                month_map = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                month_num = month_map.get(month_abbr.lower())
                if month_num:
                    current_year = today.year
                    try:
                        parsed_date = date(current_year, month_num, day)
                        # If the date is in the past, assume it's next year
                        if parsed_date < today:
                            parsed_date = date(current_year + 1, month_num, day)
                        start_date = parsed_date
                        end_date = parsed_date
                        logger.info(f"📅 Parsed date from weekday format: {start_date}")
                    except ValueError:
                        logger.debug(f"Invalid date: {month_num}/{day}")
            
            # Look for 24-hour time range format (e.g., "12:00–12:30" or "12:00-12:30")
            time_range_pattern = r'(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})'
            time_range_match = re.search(time_range_pattern, date_text)
            if time_range_match:
                start_hour = int(time_range_match.group(1))
                start_min = int(time_range_match.group(2))
                end_hour = int(time_range_match.group(3))
                end_min = int(time_range_match.group(4))
                
                # Validate 24-hour format times
                if 0 <= start_hour <= 23 and 0 <= start_min <= 59 and 0 <= end_hour <= 23 and 0 <= end_min <= 59:
                    start_time = time_class(start_hour, start_min)
                    end_time = time_class(end_hour, end_min)
                    logger.info(f"⏰ Parsed 24-hour time range: {start_time} - {end_time}")
            
            # Look for 12-hour time range format with AM/PM (e.g., "5:00 pm–7:00 pm" or "5:00 pm - 7:00 pm")
            if not start_time or not end_time:
                time_range_ampm_pattern = r'(\d{1,2}):(\d{2})\s*([ap]m)\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap]m)'
                time_range_ampm_match = re.search(time_range_ampm_pattern, date_text, re.IGNORECASE)
                if time_range_ampm_match:
                    start_hour = int(time_range_ampm_match.group(1))
                    start_min = int(time_range_ampm_match.group(2))
                    start_ampm = time_range_ampm_match.group(3).upper()
                    end_hour = int(time_range_ampm_match.group(4))
                    end_min = int(time_range_ampm_match.group(5))
                    end_ampm = time_range_ampm_match.group(6).upper()
                    
                    # Convert to 24-hour format
                    if start_ampm == 'PM' and start_hour != 12:
                        start_hour += 12
                    elif start_ampm == 'AM' and start_hour == 12:
                        start_hour = 0
                    
                    if end_ampm == 'PM' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'AM' and end_hour == 12:
                        end_hour = 0
                    
                    start_time = time_class(start_hour, start_min)
                    end_time = time_class(end_hour, end_min)
                    logger.info(f"⏰ Parsed 12-hour time range: {start_time} - {end_time}")
            
            # Also check for 12-hour format with AM/PM
            time_patterns = [
                r'(\d{1,2}):(\d{2})\s*([ap]m)',
                r'(\d{1,2})\s*([ap]m)',
            ]
            
            # Only use 12-hour format if we haven't already found a time
            if not start_time:
                for pattern in time_patterns:
                    match = re.search(pattern, date_text, re.IGNORECASE)
                    if match:
                        if len(match.groups()) == 3:  # HH:MM AM/PM
                            hour = int(match.group(1))
                            minute = int(match.group(2))
                            ampm = match.group(3).upper()
                            
                            if ampm == 'PM' and hour != 12:
                                hour += 12
                            elif ampm == 'AM' and hour == 12:
                                hour = 0
                            
                            start_time = time(hour, minute)
                            break
                        elif len(match.groups()) == 2:  # H AM/PM
                            hour = int(match.group(1))
                            ampm = match.group(2).upper()
                            
                            if ampm == 'PM' and hour != 12:
                                hour += 12
                            elif ampm == 'AM' and hour == 12:
                                hour = 0
                            
                            start_time = time(hour, 0)
                            break
        
        # Final check: If we have a start time but no end time, assume 1-hour duration for tours
        if start_time and not end_time:
            from datetime import timedelta
            # Calculate end time (start time + 1 hour)
            start_datetime = datetime.combine(today, start_time)
            end_datetime = start_datetime + timedelta(hours=1)
            end_time = end_datetime.time()
            logger.info(f"⏰ Assuming 1-hour tour duration: {start_time} - {end_time}")
        
        return start_date, end_date, start_time, end_time

    def _parse_dates(self, date_text):
        """Parse date and time from text (legacy method for compatibility)"""
        return self._parse_dates_enhanced(date_text, None, None)
    
    def _determine_event_type(self, venue_type, title, description):
        """Determine event type based on venue and content"""
        content = f"{title} {description}".lower()
        
        # Prioritize workshop/class detection (before other types)
        if 'workshop' in content or 'class' in content or 'sketching' in content or 'art making' in content:
            return 'workshop'
        # Prioritize performance/concert detection
        elif 'performance' in content or 'concert' in content or 'consort' in content or 'recital' in content:
            return 'talk'  # Use 'talk' as the event type for performances (or could be 'festival' depending on DB schema)
        # Prioritize talk detection (before tour, since "tour" might be in talk descriptions)
        elif 'talk' in content and ('spotlight talk' in content or 'talk:' in content or 'talk ' in content or 'talk,' in content):
            return 'talk'
        # Also check for lecture, discussion, conversation patterns
        elif 'lecture' in content or 'discussion' in content or 'conversation' in content:
            return 'talk'
        # Prioritize tour detection
        elif 'tour' in content or 'guided' in content:
            return 'tour'
        elif venue_type == 'museum':
            if 'exhibition' in content or 'exhibit' in content:
                return 'exhibition'
            else:
                return 'event'  # Default museums to generic event type
        elif venue_type == 'gallery':
            return 'exhibition'
        elif venue_type == 'theater':
            return 'festival'
        elif 'photowalk' in content or 'photo walk' in content:
            return 'photowalk'
        elif 'festival' in content:
            return 'festival'
        else:
            return 'event'  # Default to generic event type for most venues
    
    def _extract_exhibition_from_page(self, soup, venue, url, event_type=None, time_range='today'):
        """Extract an exhibition event from an individual exhibition page"""
        try:
            # Special handling for Hirshhorn exhibition pages
            is_hirshhorn = 'hirshhorn.si.edu' in url.lower()
            
            # Extract title from page - prioritize better sources
            title = None
            # First try meta tags (most reliable)
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content')
                # Clean title: remove venue name suffix
                from scripts.utils import clean_event_title
                title = clean_event_title(title)
            
            # If no meta title, try structured selectors
            if not title:
                title_selectors = ['.exhibition-title', '.page-title', '[itemprop="name"]']
                for selector in title_selectors:
                    element = soup.select_one(selector)
                    if element:
                        title = element.get_text(strip=True)
                        if title and len(title) > 3:
                            break
            
            # Then try h1 (but filter out generic navigation titles)
            if not title:
                h1 = soup.find('h1')
                if h1:
                    h1_text = h1.get_text(strip=True)
                    # Filter out generic navigation titles
                    generic_titles = ['global search', 'search', 'menu', 'navigation', 'skip to content', 
                                     'calendar', 'events', 'exhibitions', 'home', 'about', 'our staff',
                                     'join us for an event', 'join us', 'join us for', 'join us!']
                    if h1_text.lower() not in generic_titles and len(h1_text) > 3:
                        title = h1_text
            
            # Fallback to page title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    # Clean title: remove venue name suffix
                    from scripts.utils import clean_event_title
                    title = clean_event_title(title)
            
            # If no title found, try to extract from URL
            if not title:
                # Extract from URL slug (e.g., /art/exhibition/metropolis-ii -> Metropolis II)
                url_parts = url.split('/')
                if 'exhibition' in url_parts:
                    idx = url_parts.index('exhibition')
                    if idx + 1 < len(url_parts):
                        slug = url_parts[idx + 1]
                        # Convert slug to title (metropolis-ii -> Metropolis II)
                        title = slug.replace('-', ' ').title()
            
            if not title or len(title) < 3:
                logger.debug(f"Could not extract title from exhibition page: {url}")
                return None
            
            # Clean and normalize title
            title = self._clean_title(title)
            
            # Extract description
            description = None
            
            # Special handling for Hirshhorn: description is often in paragraphs after h2 with dates
            if is_hirshhorn:
                h2 = soup.find('h2')
                if h2:
                    # Get paragraphs after the h2
                    next_p = h2.find_next_sibling('p')
                    if next_p:
                        desc_parts = []
                        # Collect first few paragraphs after h2
                        current = next_p
                        for _ in range(3):
                            if current and current.name == 'p':
                                text = current.get_text(strip=True)
                                if text and len(text) > 20:
                                    desc_parts.append(text)
                                current = current.find_next_sibling('p')
                            else:
                                break
                        if desc_parts:
                            description = ' '.join(desc_parts)
                            logger.info(f"📝 Found Hirshhorn description: {description[:100]}...")
            
            # Fallback to standard selectors
            if not description:
                desc_selectors = ['.exhibition-description', '.description', '.content', 'article p', '.summary']
                for selector in desc_selectors:
                    element = soup.select_one(selector)
                    if element:
                        description = element.get_text(strip=True)
                        if description and len(description) > 20:
                            break
            
            # If no description, get first few paragraphs
            if not description:
                paragraphs = soup.find_all('p')
                desc_parts = []
                for p in paragraphs[:3]:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        desc_parts.append(text)
                if desc_parts:
                    description = ' '.join(desc_parts[:200])  # Limit length
            
            # Extract image with comprehensive strategy
            image_url = self._extract_exhibition_image(soup, url, venue)
            
            # Extract dates from page first
            date_text = self._extract_exhibition_dates(soup)
            
            # Parse dates - this will extract actual dates from the page if found
            start_date, end_date, start_time, end_time = self._parse_exhibition_dates(
                date_text, url, venue, time_range=time_range
            )
            
            # If we couldn't parse start date, handle permanent/ongoing exhibitions
            if not start_date:
                # Check if this might be a permanent/ongoing exhibition
                page_text_lower = soup.get_text().lower()
                is_permanent = any(indicator in page_text_lower for indicator in [
                    'permanent', 'ongoing', 'always on view', 'always on display',
                    'permanent collection', 'permanent exhibition'
                ])
                
                if is_permanent or not date_text:
                    # For permanent exhibitions or exhibitions without date info:
                    # Set start_date to today and end_date to 2 years from now
                    from datetime import timedelta
                    start_date = date.today()
                    end_date = start_date + timedelta(days=730)  # 2 years from now
                    logger.info(f"✅ Treating '{title}' as permanent/ongoing exhibition (start: {start_date.isoformat()}, end: {end_date.isoformat()})")
                else:
                    # Date text exists but couldn't parse it - skip
                    logger.info(f"⚠️ Exhibition '{title}' has unparseable date text '{date_text}' - skipping")
                    return None
            
            # For ongoing exhibitions (end_date is None), skip if start_date is in the past
            # For exhibitions with end dates, skip if they've ended
            today = date.today()
            if end_date is None:
                # Ongoing exhibition - skip if start date is in the past (shouldn't happen, but just in case)
                if start_date < today:
                    logger.info(f"⏰ Skipping past ongoing exhibition start: {title} (started {start_date.isoformat()})")
                    return None
            elif end_date < today:
                logger.info(f"⏰ Exhibition '{title}' ended on {end_date.isoformat()} - skipping")
                return None
            
            # Extract exhibition details
            exhibition_details = self._extract_exhibition_details(soup, description or '', url)
            
            # Create event data
            event_data = {
                'title': title,
                'description': description or '',
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': venue.name,
                'venue_id': venue.id,
                'city_id': venue.city_id,
                'event_type': 'exhibition',
                'url': url,
                'image_url': image_url,
                'source': 'website',
                'source_url': venue.website_url,
                'organizer': venue.name
            }
            
            # Add exhibition-specific fields
            event_data.update(exhibition_details)
            
            # Validate
            if self._is_valid_event(event_data):
                logger.info(f"✅ Extracted exhibition from page: '{title}'")
                return event_data
            else:
                logger.debug(f"⚠️ Exhibition page did not pass validation: '{title}'")
                return None
                
        except Exception as e:
            logger.debug(f"Error extracting exhibition from page {url}: {e}")
            return None
    
    def _extract_events_from_artic_listing_page(self, soup, venue, page_url, event_type=None, time_range='today'):
        """Extract events from Art Institute of Chicago events listing page
        
        The actual page format:
        - Event items have titles in <strong class="title"> elements
        - Event type labels appear as plain text (e.g., "Tour", "Class/Workshop") before the title
        - Time ranges: "12:00–12:30"
        - Dates appear in headings like "03 Dec Wed"
        - Descriptions and "Free" label in parent container
        
        Args:
            soup: BeautifulSoup object of the events listing page
            venue: Venue object
            page_url: URL of the events listing page
            event_type: Optional filter for event type (tour, talk, workshop, etc.)
            time_range: Time range for events
        
        Returns:
            List of event dictionaries
        """
        events = []
        
        try:
            logger.info(f"🔍 Starting Art Institute events extraction from {page_url}")
            
            # Find all date sections first (h3/h2 with dates like "03 Dec Wed" or "03DecWed")
            date_sections = []
            all_headings = soup.find_all(['h2', 'h3', 'h4'])
            for heading in all_headings:
                heading_text = heading.get_text(strip=True)
                # Match both formats: "03 Dec Wed" (with spaces) and "03DecWed" (without spaces)
                if re.search(r'\d{1,2}\s*[A-Z][a-z]{2,3}\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)', heading_text, re.IGNORECASE):
                    date_sections.append(heading)
            
            logger.info(f"🔍 Found {len(date_sections)} date sections")
            
            # Find all title elements (these are the event titles)
            title_elements = soup.find_all('strong', class_=re.compile('title', re.I))
            logger.info(f"🔍 Found {len(title_elements)} title elements")
            
            # Process each title element
            for title_elem in title_elements:
                try:
                    title = title_elem.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    
                    # Get parent container (contains all event info)
                    parent = title_elem.find_parent(['div', 'article', 'li', 'section'])
                    if not parent:
                        continue
                    
                    parent_text = parent.get_text()
                    
                    # Extract event type label (appears before title, like "Tour", "Class/Workshop")
                    # Look for type labels in the parent text before the title
                    # The label appears as a standalone word surrounded by whitespace/newlines
                    text_before_title = parent_text[:parent_text.find(title)] if title in parent_text else ''
                    type_label_match = re.search(r'(?:^|\s)(Tour|Talk|Class/Workshop|Workshop|Screening|Special Event)(?:\s|$)', text_before_title, re.IGNORECASE)
                    detected_type = None
                    if type_label_match:
                        type_label = type_label_match.group(1).lower()
                        if type_label == 'class/workshop' or type_label == 'workshop':
                            detected_type = 'workshop'
                        elif type_label == 'talk':
                            detected_type = 'talk'
                        elif type_label == 'tour':
                            detected_type = 'tour'
                        elif type_label == 'screening':
                            detected_type = 'festival'
                        elif type_label == 'special event':
                            detected_type = 'festival'
                    
                    # If no type label found, detect from title
                    if not detected_type:
                        description_elem = parent.find('p')
                        description_text = description_elem.get_text(strip=True) if description_elem else ''
                        detected_type = self._determine_event_type(venue.venue_type, title, description_text)
                        logger.info(f"⚠️ No type label found, detected '{detected_type}' from title: '{title}'")
                    
                    # Even if type label was found, double-check with title (label might be wrong)
                    # For example, label says "Tour" but title says "Spotlight Talk"
                    if detected_type and title:
                        description_elem = parent.find('p')
                        description_text = description_elem.get_text(strip=True) if description_elem else ''
                        title_based_type = self._determine_event_type(venue.venue_type, title, description_text)
                        # If title-based detection is more specific (talk/workshop vs tour), use it
                        if title_based_type in ['talk', 'workshop'] and detected_type == 'tour':
                            logger.info(f"⚠️ Type label says '{detected_type}' but title suggests '{title_based_type}', using '{title_based_type}': '{title}'")
                            detected_type = title_based_type
                    
                    if not detected_type:
                        continue
                    
                    # Filter by event_type if specified
                    if event_type and detected_type != event_type.lower():
                        continue
                    
                    # Clean title
                    title = self._clean_title(title)
                    
                    # Skip generic titles
                    generic_titles = ['join us for an event', 'join us', 'join us for', 'join us!', 'our staff', 
                                     'now open!', 'exhibition highlights', 'gallery tour']
                    if title.lower() in generic_titles:
                        continue
                    
                    # Extract time range (e.g., "12:00–12:30")
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})', parent_text)
                    start_time = None
                    end_time = None
                    if time_match:
                        start_hour = int(time_match.group(1))
                        start_min = int(time_match.group(2))
                        end_hour = int(time_match.group(3))
                        end_min = int(time_match.group(4))
                        
                        # Validate times
                        if 0 <= start_hour <= 23 and 0 <= start_min <= 59 and 0 <= end_hour <= 23 and 0 <= end_min <= 59:
                            start_time = time_class(start_hour, start_min)
                            end_time = time_class(end_hour, end_min)
                    
                    # If no time found, skip (talks and workshops require times)
                    if detected_type in ['talk', 'workshop'] and not start_time:
                        logger.debug(f"⚠️ Skipping {detected_type} '{title}' - no start time found")
                        continue
                    
                    # Find date - look for date section before this event
                    event_date = None
                    for date_section in date_sections:
                        # Check if this event comes after this date section
                        if date_section in title_elem.find_all_previous(['h2', 'h3', 'h4']):
                            date_text = date_section.get_text(strip=True)
                            # Match both formats: "03 Dec Wed" (with spaces) and "03DecWed" (without spaces)
                            date_match = re.search(r'(\d{1,2})\s*([A-Z][a-z]{2,3})\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)', date_text, re.IGNORECASE)
                            if date_match:
                                day = int(date_match.group(1))
                                month_abbr = date_match.group(2)
                                month_map = {
                                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                                }
                                month_num = month_map.get(month_abbr.lower())
                                if month_num:
                                    today = date.today()
                                    current_year = today.year
                                    try:
                                        event_date = date(current_year, month_num, day)
                                        if event_date < today:
                                            event_date = date(current_year + 1, month_num, day)
                                        break
                                    except ValueError:
                                        continue
                    
                    # If no date found, use today as fallback
                    if not event_date:
                        event_date = date.today()
                        logger.debug(f"⚠️ No date found for '{title}', using today: {event_date}")
                    
                    # Extract description
                    description = None
                    desc_elem = parent.find('p')
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)[:500]
                    
                    # Extract event URL
                    event_url = None
                    link = parent.find('a', href=True)
                    if link:
                        href = link.get('href')
                        if href:
                            event_url = urljoin(page_url, href)
                    
                    # Extract image
                    image_url = None
                    img = parent.find('img')
                    if img:
                        img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                        if img_src:
                            image_url = urljoin(page_url, img_src)
                    
                    # Check if event is free
                    is_free = 'free' in parent_text.lower()
                    price = 'Free' if is_free else None
                    
                    # Create event data
                    event_data = {
                        'title': title,
                        'description': description or '',
                        'url': event_url or page_url,
                        'image_url': image_url or '',
                        'start_date': event_date.isoformat(),
                        'end_date': event_date.isoformat(),
                        'start_time': start_time.strftime('%H:%M:%S') if start_time else None,
                        'end_time': end_time.strftime('%H:%M:%S') if end_time else None,
                        'event_type': detected_type,
                        'venue_id': venue.id,
                        'city_id': venue.city_id,
                        'source': 'website',
                        'source_url': page_url,
                        'price': price
                    }
                    
                    # Validate event
                    logger.info(f"🔍 Validating {detected_type} event: '{title}' on {event_date} at {start_time if start_time else 'TBD'}")
                    logger.info(f"   Event data: type={detected_type}, has_time={start_time is not None}, has_date={event_date is not None}")
                    if self._is_valid_event(event_data):
                        events.append(event_data)
                        logger.info(f"✅ Extracted {detected_type} event: '{title}' on {event_date} at {start_time if start_time else 'TBD'}")
                    else:
                        logger.warning(f"⚠️ Event '{title}' did not pass validation (type: {detected_type}, time: {start_time})")
                        # Log why it failed validation
                        logger.warning(f"   Event data keys: {list(event_data.keys())}")
                        logger.warning(f"   Title: {event_data.get('title')}")
                        logger.warning(f"   Event type: {event_data.get('event_type')}")
                        logger.warning(f"   Start time: {event_data.get('start_time')}")
                        logger.warning(f"   Start date: {event_data.get('start_date')}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing event item '{title if 'title' in locals() else 'unknown'}': {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
            
            logger.info(f"📦 Art Institute events extraction complete: found {len(events)} events")
            if event_type:
                filtered = [e for e in events if e.get('event_type') == event_type]
                logger.info(f"   Filtered to {len(filtered)} {event_type} events")
            else:
                # Log breakdown by type
                type_counts = {}
                for e in events:
                    etype = e.get('event_type', 'unknown')
                    type_counts[etype] = type_counts.get(etype, 0) + 1
                logger.info(f"   Event breakdown by type: {type_counts}")
        
        except Exception as e:
            logger.error(f"Error extracting events from Art Institute listing page: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return events
    
    def _extract_exhibitions_from_listing_page(self, soup, venue, page_url, event_type=None, time_range='today', max_exhibitions_per_venue=5):
        """Extract exhibitions directly from a listing page (e.g., Smithsonian museums, Met Museum)
        
        Args:
            soup: BeautifulSoup object of the listing page
            venue: Venue object
            page_url: URL of the listing page
            event_type: Optional filter for event type
            time_range: Time range for events
            max_exhibitions_per_venue: Maximum number of exhibitions to extract (default: 5)
        
        Returns:
            List of at most max_exhibitions_per_venue exhibition events
        """
        events = []
        # CRITICAL: Enforce limit - this function MUST NEVER return more than max_exhibitions_per_venue
        if max_exhibitions_per_venue <= 0:
            logger.warning(f"Invalid max_exhibitions_per_venue: {max_exhibitions_per_venue}, defaulting to 5")
            max_exhibitions_per_venue = 5
        
        try:
            # Special handling for Hirshhorn Museum listing page
            # Hirshhorn uses a card-based layout where each exhibition has its own page
            # We need to extract links and visit individual pages for full descriptions
            if 'hirshhorn.si.edu' in page_url.lower() and '/exhibitions-events' in page_url.lower():
                logger.info(f"🔍 Processing Hirshhorn listing page: {page_url}")
                
                # Find all exhibition links (format: /exhibitions/[slug]/)
                exhibition_links = soup.find_all('a', href=lambda href: href and '/exhibitions/' in str(href).lower() and href != '/exhibitions/' and href != '/exhibitions-events/')
                
                # Filter to get unique exhibition URLs
                seen_urls = set()
                unique_exhibition_links = []
                for link in exhibition_links:
                    href = link.get('href', '')
                    if href:
                        # Make absolute URL
                        from urllib.parse import urljoin
                        full_url = urljoin(page_url, href)
                        
                        # Skip if not a proper exhibition page URL
                        if '/exhibitions/' not in full_url.lower() or full_url.lower().endswith('/exhibitions/'):
                            continue
                        
                        # Normalize URL (remove trailing slash, lowercase for comparison)
                        normalized = full_url.rstrip('/').lower()
                        if normalized not in seen_urls and 'hirshhorn.si.edu/exhibitions/' in normalized:
                            seen_urls.add(normalized)
                            unique_exhibition_links.append((link, full_url))
                
                logger.info(f"📋 Found {len(unique_exhibition_links)} unique Hirshhorn exhibition links")
                
                # Visit each exhibition page to extract full details
                for link_elem, exhibition_url in unique_exhibition_links[:max_exhibitions_per_venue]:
                    if len(events) >= max_exhibitions_per_venue:
                        break
                    
                    try:
                        # Extract title from listing page (faster than visiting page first)
                        title = None
                        # Try to get title from the link text or nearby elements
                        title_elem = link_elem.find(['h4', 'h3', 'h2'], class_=lambda c: c and 'title' in str(c).lower()) or link_elem
                        title = title_elem.get_text(strip=True)
                        
                        # Try parent container for title
                        if not title or len(title) < 5:
                            parent = link_elem.find_parent(['li', 'div', 'article'])
                            if parent:
                                title_elem = parent.find(['h4', 'h3', 'h2'], class_=lambda c: c and 'title' in str(c).lower())
                                if title_elem:
                                    title = title_elem.get_text(strip=True)
                        
                        # Extract date from listing page
                        date_text = None
                        parent = link_elem.find_parent(['li', 'div', 'article'])
                        if parent:
                            date_elem = parent.find('p', class_=lambda c: c and 'date' in str(c).lower())
                            if date_elem:
                                date_text = date_elem.get_text(strip=True)
                        
                        # Visit individual exhibition page for full description
                        logger.info(f"🔍 Fetching Hirshhorn exhibition page: {exhibition_url}")
                        try:
                            exhibition_response = self.session.get(exhibition_url, timeout=10)
                            exhibition_response.raise_for_status()
                            exhibition_soup = BeautifulSoup(exhibition_response.content, 'html.parser')
                            
                            # Extract title from page if not found (usually in h1)
                            if not title or len(title) < 5:
                                h1 = exhibition_soup.find('h1')
                                if h1:
                                    title = h1.get_text(strip=True)
                            
                            # Extract date range from page (usually in h2 after h1)
                            if not date_text:
                                h2 = exhibition_soup.find('h2')
                                if h2:
                                    h2_text = h2.get_text(strip=True)
                                    # Check if it looks like a date range
                                    if re.search(r'[A-Z][a-z]{2,9}\s+\d{1,2},?\s*\d{4}[–—\-]', h2_text):
                                        date_text = h2_text
                            
                            # Extract full description from page
                            description = None
                            # Special handling for Hirshhorn: description is often in paragraphs after h2 with dates
                            h2 = exhibition_soup.find('h2')
                            if h2:
                                # Get paragraphs after the h2
                                desc_parts = []
                                next_elem = h2.find_next_sibling()
                                while next_elem and len(desc_parts) < 5:  # Get up to 5 paragraphs
                                    if next_elem.name == 'p':
                                        text = next_elem.get_text(strip=True)
                                        if text and len(text) > 20:
                                            desc_parts.append(text)
                                    elif next_elem.name in ['h1', 'h2', 'h3', 'section']:
                                        # Stop at next heading or section
                                        break
                                    next_elem = next_elem.find_next_sibling()
                                
                                if desc_parts:
                                    description = ' '.join(desc_parts)
                                    logger.info(f"📝 Found Hirshhorn description ({len(description)} chars): {description[:100]}...")
                            
                            # Fallback to standard selectors if no description found
                            if not description:
                                desc_selectors = ['.exhibition-description', '.description', '.content', 'article p', '.summary']
                                for selector in desc_selectors:
                                    element = exhibition_soup.select_one(selector)
                                    if element:
                                        desc_text = element.get_text(strip=True)
                                        if desc_text and len(desc_text) > 50:
                                            description = desc_text[:1000]  # Limit length
                                            break
                            
                            # If still no description, get first few paragraphs
                            if not description:
                                paragraphs = exhibition_soup.find_all('p')
                                desc_parts = []
                                for p in paragraphs[:3]:
                                    text = p.get_text(strip=True)
                                    if text and len(text) > 20 and not re.match(r'^[A-Z][a-z]{2,9}\s+\d{1,2},?\s*\d{4}', text):
                                        # Skip if it looks like a date
                                        desc_parts.append(text)
                                    if len(' '.join(desc_parts)) > 100:
                                        break
                                if desc_parts:
                                    description = ' '.join(desc_parts)[:1000]
                            
                            # Extract image - use comprehensive extraction method for individual page
                            image_url = self._extract_exhibition_image(exhibition_soup, exhibition_url, venue)
                            
                            # Fallback to listing page image if individual page didn't have one
                            if not image_url and link_elem:
                                parent = link_elem.find_parent(['li', 'div', 'article'])
                                if parent:
                                    # Look for image-frame div
                                    image_frame = parent.find(['div'], class_=lambda c: c and 'image-frame' in str(c).lower())
                                    if image_frame:
                                        img = image_frame.find('img')
                                        if img:
                                            img_src = (img.get('src') or img.get('data-src') or 
                                                     img.get('data-lazy-src') or img.get('data-original'))
                                            if img_src:
                                                # Filter out logos and icons
                                                img_src_lower = img_src.lower()
                                                if not any(skip in img_src_lower for skip in ['logo', 'icon', 'avatar', 'sponsor', 'si-white', 'theme']):
                                                    # Check if it's a reasonable image size (likely exhibition image, not thumbnail)
                                                    width = img.get('width')
                                                    height = img.get('height')
                                                    if width and height:
                                                        try:
                                                            if int(width) >= 200 and int(height) >= 200:
                                                                from urllib.parse import urljoin
                                                                image_url = urljoin(page_url, img_src)
                                                        except:
                                                            pass
                                                    else:
                                                        # No dimensions, but check if it looks like an exhibition image URL
                                                        if '/wp-content/uploads/' in img_src_lower and ('exhibition' in img_src_lower or any(ext in img_src_lower for ext in ['.jpg', '.jpeg', '.png'])):
                                                            from urllib.parse import urljoin
                                                            image_url = urljoin(page_url, img_src)
                            
                            # Parse dates
                            if date_text:
                                start_date, end_date, start_time, end_time = self._parse_exhibition_dates(
                                    date_text, exhibition_url, venue, time_range=time_range
                                )
                            else:
                                start_date, end_date = None, None
                            
                            # Handle permanent exhibitions without dates
                            if not start_date:
                                is_permanent = 'ongoing' in date_text.lower() if date_text else False
                                if is_permanent:
                                    from datetime import timedelta
                                    start_date = date.today()
                                    end_date = start_date + timedelta(days=730)
                                else:
                                    logger.debug(f"⚠️ Could not parse date for '{title}' - skipping")
                                    continue
                            
                            # Skip past exhibitions
                            today = date.today()
                            if end_date and end_date < today:
                                continue
                            if end_date is None and start_date < today:
                                continue
                            
                            # Clean title
                            if title:
                                title = self._clean_title(title)
                            
                            # Create event data
                            event_data = {
                                'title': title or 'Untitled Exhibition',
                                'description': description or '',
                                'start_date': start_date.isoformat() if start_date else None,
                                'end_date': end_date.isoformat() if end_date is not None else None,
                                'start_time': None,
                                'end_time': None,
                                'start_location': venue.name,
                                'venue_id': venue.id,
                                'city_id': venue.city_id,
                                'event_type': 'exhibition',
                                'url': exhibition_url,
                                'image_url': image_url,
                                'source': 'website',
                                'source_url': page_url,
                                'organizer': venue.name
                            }
                            
                            if self._is_valid_event(event_data):
                                end_date_str = end_date.isoformat() if end_date else "ongoing"
                                logger.info(f"✅ Extracted Hirshhorn exhibition: '{title}' ({start_date.isoformat()} to {end_date_str}) [description: {len(description or '')} chars]")
                                events.append(event_data)
                        
                        except Exception as e:
                            logger.debug(f"⚠️ Error fetching Hirshhorn exhibition page {exhibition_url}: {e}")
                            continue
                    
                    except Exception as e:
                        logger.debug(f"⚠️ Error processing Hirshhorn exhibition link: {e}")
                        continue
                
                if events:
                    logger.info(f"📦 Hirshhorn listing page extraction complete: found {len(events)} exhibitions")
                    return events[:max_exhibitions_per_venue]
            
            # Special handling for OCMA (Orange County Museum of Art)
            elif 'ocma.art' in page_url.lower() and '/exhibitions' in page_url.lower():
                logger.info(f"🔍 Processing OCMA listing page: {page_url}")
                
                # Find all exhibition links
                exhibition_links = soup.find_all('a', href=lambda href: href and '/exhibitions/' in str(href).lower() and href != '/exhibitions/')
                
                seen_titles = set()
                
                for link in exhibition_links:
                    if len(events) >= max_exhibitions_per_venue:
                        break
                    
                    href = link.get('href', '')
                    if not href or href.endswith('/exhibitions/'):
                        continue
                    
                    # Get link text and parent container
                    link_text = link.get_text(strip=True)
                    parent = link.find_parent(['li', 'div', 'article', 'section', 'p'])
                    if not parent:
                        parent = link.parent
                    
                    parent_text = parent.get_text() if parent else ''
                    
                    # Pattern: Title followed by date range
                    # Example: "Cynthia Daignault: Light Atlas September 20, 2025 – February 8, 2026"
                    date_range_pattern = re.compile(
                        r'([A-Z][^:]+(?:[:][^:]+)?)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*[–—\-]\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                        re.MULTILINE
                    )
                    
                    title = None
                    date_text = None
                    
                    # Try to match pattern in parent text
                    match = date_range_pattern.search(parent_text)
                    if match:
                        title = match.group(1).strip()
                        date_text = f"{match.group(2).strip()} – {match.group(3).strip()}"
                    else:
                        # Look for date range anywhere in parent
                        date_match = re.search(
                            r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*[–—\-]\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                            parent_text
                        )
                        if date_match:
                            date_text = date_match.group(0)
                            title = link_text if link_text and len(link_text) > 5 else None
                            if not title:
                                # Extract from text before date
                                text_before = parent_text[:date_match.start()].strip()
                                title_parts = text_before.split('\n')
                                for part in reversed(title_parts):
                                    part = part.strip()
                                    if part and len(part) > 5:
                                        title = part
                                        break
                    
                    # Fallback: use link text or URL slug
                    if not title or len(title) < 5:
                        if link_text and len(link_text) > 5:
                            title = link_text
                        else:
                            # Extract from URL slug
                            url_slug = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                            if url_slug and url_slug != 'exhibitions':
                                title = ' '.join(word.capitalize() for word in url_slug.replace('-', ' ').split())
                    
                    # Clean title to remove dates, trailing commas, etc.
                    if title:
                        title = self._clean_title(title)
                    
                    # Filter out section headings
                    # Use utility function to check for category headings
                    from scripts.utils import is_category_heading
                    if not title or is_category_heading(title):
                        continue
                    
                    if title.lower() in seen_titles:
                        continue
                    
                    seen_titles.add(title.lower())
                    
                    # Parse dates manually
                    start_date = None
                    end_date = None
                    if date_text:
                        # Parse date range: "September 20, 2025 – February 8, 2026"
                        date_parts = re.split(r'[–—\-]', date_text)
                        if len(date_parts) == 2:
                            start_date_str = date_parts[0].strip()
                            end_date_str = date_parts[1].strip()
                            
                            # Parse dates using datetime
                            from datetime import datetime
                            try:
                                # Try format: "September 20, 2025"
                                start_date = datetime.strptime(start_date_str, "%B %d, %Y").date()
                            except:
                                try:
                                    # Try format: "September 20 2025" (no comma)
                                    start_date = datetime.strptime(start_date_str, "%B %d %Y").date()
                                except:
                                    pass
                            
                            try:
                                end_date = datetime.strptime(end_date_str, "%B %d, %Y").date()
                            except:
                                try:
                                    end_date = datetime.strptime(end_date_str, "%B %d %Y").date()
                                except:
                                    pass
                    
                    # Only include current and upcoming (not past)
                    from datetime import date
                    if end_date and end_date < date.today():
                        continue
                    
                    # Build full URL
                    from urllib.parse import urljoin
                    full_url = urljoin(page_url, href)
                    
                    # Extract image
                    image_url = None
                    if parent:
                        img = parent.find('img')
                        if img:
                            img_src = img.get('src') or img.get('data-src')
                            if img_src:
                                image_url = urljoin(page_url, img_src)
                    
                    # Clean title to remove dates, trailing commas, etc.
                    if title:
                        title = self._clean_title(title)
                    
                    events.append({
                        'title': title,
                        'description': '',
                        'start_date': start_date.isoformat() if start_date else None,
                        'end_date': end_date.isoformat() if end_date else None,
                        'start_time': None,
                        'end_time': None,
                        'start_location': venue.name,
                        'url': full_url,
                        'image_url': image_url,
                        'event_type': 'exhibition',
                        'venue_id': venue.id,
                        'city_id': venue.city_id,
                        'source': 'website',
                        'source_url': page_url,
                        'organizer': venue.name
                    })
                
                if events:
                    logger.info(f"📦 OCMA listing page extraction complete: found {len(events)} exhibitions")
                    return events[:max_exhibitions_per_venue]
            
            return events
        
        except Exception as e:
            logger.error(f"Error extracting exhibitions from listing page: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return events
    
    def _extract_ocma_calendar_events(self, soup, venue, page_url, event_type=None, time_range='this_month'):
        """Extract events from OCMA calendar page"""
        events = []
        
        try:
            # OCMA calendar format:
            # Event Type Event Title Date, Time
            # Example: "Family Program Bring Your Own Baby Tour & Tea December 3, 2025, 11:00 AM"
            # Example: "Tour Public Tour December 7, 2025, 1:00 PM"
            # Example: "Public Program Art Happy Hour & Pop-Up Talk December 5, 2025, 5:00–6:00 PM"
            
            # Find all event links (they link to individual event pages)
            event_links = soup.find_all('a', href=lambda href: href and '/calendar/' in str(href).lower() and href != '/calendar/')
            
            seen_titles = set()
            
            for link in event_links:
                href = link.get('href', '')
                if not href or href == '/calendar/' or href.endswith('/calendar/'):
                    continue
                
                # Get parent container
                parent = link.find_parent(['li', 'div', 'article', 'section', 'p', 'h3', 'h4'])
                if not parent:
                    parent = link.parent
                
                parent_text = parent.get_text() if parent else ''
                link_text = link.get_text(strip=True)
                
                # Clean up parent text - split by newlines to get structured parts
                parent_lines = [line.strip() for line in parent_text.split('\n') if line.strip()]
                
                title = None
                event_type_str = None
                date_str = None
                start_time_str = None
                end_time_str = None
                
                # First, try to use link text as title (most reliable)
                # But clean it up - remove event type prefixes and dates
                if link_text and len(link_text) > 5:
                    title = link_text
                    # Remove common prefixes
                    title = re.sub(r'^(Family Program|Tour|Public Program|Artist Talk|Past Tour|Past Family Program|Past Public Program)\s*', '', title, flags=re.IGNORECASE)
                    # Remove trailing dates/times - handle both with and without space before date
                    # Pattern: "TitleDecember 3, 2025, 11:00 AM" or "Title December 3, 2025, 11:00 AM"
                    title = re.sub(r'([A-Z][a-z]+)\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}.*)$', r'\1', title)
                    # Also remove any remaining date/time patterns
                    title = re.sub(r'\s+[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}.*$', '', title)
                    # Remove time patterns like "11:00 AM" or "11:00–12:00 PM"
                    title = re.sub(r'\s+\d{1,2}:\d{2}\s*([ap])\.?m\.?(\s*[–—\-]\s*\d{1,2}:\d{2}\s*([ap])\.?m\.?)?.*$', '', title, flags=re.IGNORECASE)
                    title = title.strip()
                    # Use the comprehensive _clean_title method for final cleaning
                    title = self._clean_title(title)
                
                # Look for event type keywords at the start of any line
                event_type_pattern = re.compile(r'^(Family Program|Tour|Public Program|Artist Talk|Past Tour|Past Family Program|Past Public Program)', re.IGNORECASE)
                
                # Find the line with event type
                for line in parent_lines:
                    if event_type_pattern.match(line):
                        event_type_str = line.strip()
                        break
                
                # Look for date/time pattern in any line
                # Pattern 1: "5:00–6:00 PM" (shared am/pm at the end) - OCMA format
                date_time_pattern1 = re.compile(
                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                    re.IGNORECASE
                )
                # Pattern 2: "5:00 PM–6:00 PM" (am/pm after each time) - fallback
                date_time_pattern2 = re.compile(
                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                    re.IGNORECASE
                )
                # Pattern 3: Single time "5:00 PM"
                date_time_pattern3 = re.compile(
                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                    re.IGNORECASE
                )
                
                for line in parent_lines:
                    # Try pattern 1 first (shared am/pm): "5:00–6:00 PM"
                    date_match = date_time_pattern1.search(line)
                    if date_match:
                        date_str = date_match.group(1).strip()
                        start_time_str = f"{date_match.group(2)}:{date_match.group(3)} {date_match.group(6)}.m."
                        end_time_str = f"{date_match.group(4)}:{date_match.group(5)} {date_match.group(6)}.m."
                        break
                    # Try pattern 2 (separate am/pm): "5:00 PM–6:00 PM"
                    date_match = date_time_pattern2.search(line)
                    if date_match:
                        date_str = date_match.group(1).strip()
                        start_time_str = f"{date_match.group(2)}:{date_match.group(3)} {date_match.group(4)}.m."
                        end_time_str = f"{date_match.group(5)}:{date_match.group(6)} {date_match.group(7)}.m."
                        break
                    # Try pattern 3 (single time): "5:00 PM"
                    date_match = date_time_pattern3.search(line)
                    if date_match:
                        date_str = date_match.group(1).strip()
                        start_time_str = f"{date_match.group(2)}:{date_match.group(3)} {date_match.group(4)}.m."
                        end_time_str = None
                        break
                
                # If we don't have title from link, try to extract from parent text
                # Pattern: Event Type Title Date, Time
                # But we need to be careful - the title is between event type and date
                if not title or len(title) < 5:
                    # Try to find title between event type and date
                    if event_type_str and date_str:
                        # Find the text between event type and date
                        event_type_pos = parent_text.find(event_type_str)
                        date_pos = parent_text.find(date_str)
                        if event_type_pos >= 0 and date_pos > event_type_pos:
                            title_candidate = parent_text[event_type_pos + len(event_type_str):date_pos].strip()
                            # Clean up title - remove extra whitespace, newlines
                            title_candidate = ' '.join(title_candidate.split())
                            if len(title_candidate) > 5:
                                title = title_candidate
                    
                    # Fallback: try pattern matching on full text
                    if not title or len(title) < 5:
                        event_pattern = re.compile(
                            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(.+?)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                            re.MULTILINE
                        )
                        match = event_pattern.search(parent_text)
                        if match:
                            if not event_type_str:
                                event_type_str = match.group(1).strip()
                            # Extract title - but be careful not to include date
                            title_part = match.group(2).strip()
                            # Remove any trailing date-like patterns
                            title_part = re.sub(r'\s+[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}.*$', '', title_part)
                            if len(title_part) > 5:
                                title = title_part
                            if not date_str:
                                date_str = match.group(3).strip()
                                start_time_str = f"{match.group(4)}:{match.group(5)} {match.group(6)}.m."
                
                # If we still don't have a title, try URL slug
                if not title or len(title) < 5:
                    url_slug = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    if url_slug and url_slug != 'calendar':
                        title = ' '.join(word.capitalize() for word in url_slug.replace('-', ' ').split())
                
                # Clean title to remove dates, trailing commas, etc.
                if title:
                    title = self._clean_title(title)
                
                if not title or title.lower() in seen_titles:
                    continue
                
                # Common sense: Filter out section headers before processing
                title_lower_check = title.lower().strip()
                section_headers = [
                    'past events', 'upcoming events', 'all events', 'all past events',
                    'today\'s events', 'todays events', 'today events',
                    'current events', 'future events', 'recent events',
                    'event listings', 'event list', 'event schedule',
                ]
                if any(title_lower_check == header or title_lower_check.startswith(header + ' ') or title_lower_check.startswith(header + '→') for header in section_headers):
                    continue
                
                seen_titles.add(title.lower())
                
                # Parse date
                start_date = None
                if date_str:
                    from datetime import datetime
                    try:
                        # Try format: "December 3, 2025"
                        start_date = datetime.strptime(date_str, "%B %d, %Y").date()
                        logger.debug(f"   📅 Parsed date from calendar listing: {start_date}")
                    except ValueError as e1:
                        try:
                            # Try format: "December 3 2025" (no comma)
                            start_date = datetime.strptime(date_str, "%B %d %Y").date()
                            logger.debug(f"   📅 Parsed date from calendar listing (no comma): {start_date}")
                        except ValueError as e2:
                            logger.warning(f"   ⚠️ Failed to parse date_str '{date_str}' from calendar listing: {e1}, {e2}")
                
                # Only include if in time range
                if start_date:
                    from datetime import date, timedelta
                    today = date.today()
                    if time_range == 'today':
                        if start_date != today:
                            continue
                    elif time_range == 'this_week':
                        week_end = today + timedelta(days=7)
                        if not (today <= start_date <= week_end):
                            continue
                    elif time_range == 'this_month':
                        month_end = today + timedelta(days=30)
                        if not (today <= start_date <= month_end):
                            continue
                
                # Parse times
                start_time = None
                end_time = None
                if start_time_str:
                    try:
                        # Parse "11:00 a.m." or "11:00 am"
                        time_match = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', start_time_str.lower())
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = int(time_match.group(2))
                            am_pm = time_match.group(3)
                            if am_pm == 'p' and hour != 12:
                                hour += 12
                            elif am_pm == 'a' and hour == 12:
                                hour = 0
                            from datetime import time as dt_time
                            start_time = dt_time(hour, minute)
                            logger.debug(f"   ⏰ Parsed start_time from calendar listing: {start_time}")
                    except (ValueError, IndexError, AttributeError) as e:
                        logger.warning(f"   ⚠️ Failed to parse start_time_str '{start_time_str}' from calendar listing: {e}")
                
                if end_time_str:
                    try:
                        time_match = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', end_time_str.lower())
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = int(time_match.group(2))
                            am_pm = time_match.group(3)
                            if am_pm == 'p' and hour != 12:
                                hour += 12
                            elif am_pm == 'a' and hour == 12:
                                hour = 0
                            from datetime import time as dt_time
                            end_time = dt_time(hour, minute)
                            logger.debug(f"   ⏰ Parsed end_time from calendar listing: {end_time}")
                    except (ValueError, IndexError, AttributeError) as e:
                        logger.warning(f"   ⚠️ Failed to parse end_time_str '{end_time_str}' from calendar listing: {e}")
                
                # Determine event type from event_type_str and title
                determined_type = 'event'
                if event_type_str:
                    event_type_lower = event_type_str.lower()
                    if 'tour' in event_type_lower:
                        determined_type = 'tour'
                    elif 'talk' in event_type_lower or 'lecture' in event_type_lower:
                        determined_type = 'talk'
                    elif 'workshop' in event_type_lower or 'studio' in event_type_lower or 'make' in event_type_lower:
                        determined_type = 'workshop'
                    elif 'family' in event_type_lower or 'play' in event_type_lower:
                        determined_type = 'workshop'  # Family programs are often workshops
                
                # Also check the title for event type keywords (e.g., "Pop-Up Talk" in title)
                if title:
                    title_lower = title.lower()
                    if 'talk' in title_lower or 'lecture' in title_lower or 'discussion' in title_lower:
                        determined_type = 'talk'
                    elif 'tour' in title_lower and determined_type == 'event':
                        determined_type = 'tour'
                    elif 'workshop' in title_lower or 'studio' in title_lower or 'make' in title_lower:
                        determined_type = 'workshop'
                
                # Filter by requested event type if specified
                if event_type and determined_type != event_type.lower():
                    continue
                
                # Detect if event is baby-friendly
                is_baby_friendly = False
                combined_text = f"{title.lower()} {parent_text.lower()}"
                baby_keywords = [
                    'baby', 'babies', 'toddler', 'toddlers', 'infant', 'infants',
                    'ages 0-2', 'ages 0–2', 'ages 0 to 2', '0-2 years', '0–2 years',
                    'ages 0-3', 'ages 0–3', 'ages 0 to 3', '0-3 years', '0–3 years',
                    'bring your own baby', 'byob', 'baby-friendly', 'baby friendly',
                    'stroller', 'strollers', 'nursing', 'breastfeeding',
                    'family program', 'family-friendly', 'family friendly',
                    'art & play', 'art and play', 'play time', 'playtime',
                    'children', 'kids', 'little ones', 'young families'
                ]
                if any(keyword in combined_text for keyword in baby_keywords):
                    is_baby_friendly = True
                
                # Build full URL
                from urllib.parse import urljoin
                full_url = urljoin(page_url, href)
                
                # Extract image from the link or parent element
                image_url = None
                # Try to find image in the link or parent
                img_elem = link.find('img') or (parent.find('img') if parent else None)
                if img_elem:
                    img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
                    if img_src:
                        image_url = urljoin(page_url, img_src)
                
                # Extract description and additional details from individual event page
                # IMPORTANT: Always fetch event page for talks and tours to get accurate times
                # First, try to get description from calendar listing as fallback
                description = ''
                # Try to extract description from parent container on calendar listing
                if parent:
                    # Look for description text in siblings or nearby elements
                    # OCMA often has description text near the event link
                    parent_siblings = parent.find_next_siblings(['p', 'div'])
                    for sibling in parent_siblings[:3]:  # Check first 3 siblings
                        sibling_text = sibling.get_text(strip=True)
                        # Skip if it's just the date/time or event type
                        if sibling_text and len(sibling_text) > 20 and not re.match(r'^[A-Z][a-z]+\s+\d{1,2}', sibling_text):
                            description = sibling_text
                            logger.debug(f"   📝 Found description from calendar listing: {description[:100]}")
                            break
                
                meeting_location = None
                # Initialize registration fields before event page fetch
                registration_required = False
                registration_info = ''
                # Store original times before event page fetch
                original_start_time = start_time
                original_end_time = end_time
                if full_url:
                    try:
                        logger.info(f"   🔍 Fetching event page for details: {full_url}")
                        event_response = self.session.get(full_url, timeout=10)
                        logger.info(f"   📡 Event page response status: {event_response.status_code} for {full_url}")
                        if event_response.status_code == 200:
                            logger.info(f"   ✅ Successfully fetched event page: {full_url}")
                            event_soup = BeautifulSoup(event_response.content, 'html.parser')
                            # Look for main content area
                            main_content = event_soup.find('article') or event_soup.find('main') or event_soup
                            
                            # Extract date/time from individual event page (more accurate than calendar listing)
                            # PRIORITY: Check h2 tags first (OCMA often puts date/time in h2)
                            # Then check other headings and paragraphs
                            h2_elements = main_content.find_all('h2') if main_content else []
                            other_elements = main_content.find_all(['h1', 'h3', 'p']) if main_content else []
                            date_time_elements = h2_elements + other_elements  # h2 first, then others
                            logger.info(f"   🔍 Checking {len(h2_elements)} h2 elements and {len(other_elements)} other elements for date/time on {full_url}")
                            
                            # Compile patterns once before the loop
                            # Pattern 1: "5:00–6:00 PM" (shared am/pm at the end) - OCMA format
                            date_time_pattern1 = re.compile(
                                r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                                re.IGNORECASE
                            )
                            # Pattern 2: "5:00 PM–6:00 PM" (am/pm after each time) - fallback
                            date_time_pattern2 = re.compile(
                                r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                                re.IGNORECASE
                            )
                            
                            match = None
                            for elem in date_time_elements:
                                elem_text = elem.get_text(strip=True)
                                # Log all h2 elements (they're most likely to contain date/time)
                                if elem.name == 'h2':
                                    logger.info(f"   📝 Checking h2 element: {elem_text[:150]}")
                                elif date_time_elements.index(elem) < 3:
                                    logger.debug(f"   📝 Checking element {elem.name}: {elem_text[:80]}")
                                
                                # Try pattern 1 first (shared am/pm): "5:00–6:00 PM"
                                match = date_time_pattern1.search(elem_text)
                                if match:
                                    logger.info(f"   ✅ Found date/time pattern (shared am/pm) in {elem.name}: {elem_text}")
                                    # Pattern 1 groups: date, start_hour, start_min, end_hour, end_min, am_pm
                                    date_str = match.group(1).strip()
                                    start_time_str = f"{match.group(2)}:{match.group(3)} {match.group(6)}.m."
                                    end_time_str = f"{match.group(4)}:{match.group(5)} {match.group(6)}.m."
                                    break  # Found a match, exit loop
                                
                                # Try pattern 2 (am/pm after each time): "5:00 PM–6:00 PM"
                                match = date_time_pattern2.search(elem_text)
                                if match:
                                    logger.info(f"   ✅ Found date/time pattern (separate am/pm) in {elem.name}: {elem_text}")
                                    # Pattern 2 groups: date, start_hour, start_min, start_am_pm, end_hour, end_min, end_am_pm
                                    date_str = match.group(1).strip()
                                    start_time_str = f"{match.group(2)}:{match.group(3)} {match.group(4)}.m."
                                    end_time_str = f"{match.group(5)}:{match.group(6)} {match.group(7)}.m."
                                    break  # Found a match, exit loop
                                
                                if elem.name == 'h2':
                                    logger.debug(f"   ⚠️ No time range pattern match in h2: {elem_text[:150]}")
                            
                            if match:
                                    # Re-parse dates and times - CRITICAL: Update the actual date/time objects, not just strings
                                    # Store original values to preserve them if parsing fails
                                    original_start_date = start_date
                                    original_start_time = start_time
                                    original_end_time = end_time
                                    
                                    from datetime import datetime, time as dt_time
                                    
                                    # Parse date - preserve original if parsing fails
                                    new_start_date = None
                                    try:
                                        new_start_date = datetime.strptime(date_str, "%B %d, %Y").date()
                                        logger.debug(f"   📅 Parsed start_date from event page: {new_start_date}")
                                    except ValueError as e1:
                                        try:
                                            new_start_date = datetime.strptime(date_str, "%B %d %Y").date()
                                            logger.debug(f"   📅 Parsed start_date from event page (no comma): {new_start_date}")
                                        except ValueError as e2:
                                            logger.warning(f"   ⚠️ Failed to parse date_str '{date_str}': {e1}, {e2}")
                                            # Keep original date if parsing fails
                                            new_start_date = original_start_date
                                    
                                    # Only update if we successfully parsed a new date
                                    if new_start_date:
                                        start_date = new_start_date
                                    
                                    # Parse start time - preserve original if parsing fails
                                    if start_time_str:
                                        time_match = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', start_time_str.lower())
                                        if time_match:
                                            try:
                                                hour = int(time_match.group(1))
                                                minute = int(time_match.group(2))
                                                am_pm = time_match.group(3)
                                                if am_pm == 'p' and hour != 12:
                                                    hour += 12
                                                elif am_pm == 'a' and hour == 12:
                                                    hour = 0
                                                new_start_time = dt_time(hour, minute)
                                                start_time = new_start_time
                                                logger.info(f"   ⏰ Updated start_time from event page: {start_time}")
                                            except (ValueError, IndexError) as e:
                                                logger.warning(f"   ⚠️ Failed to parse start_time_str '{start_time_str}': {e}")
                                                # Keep original time if parsing fails
                                                if not start_time:
                                                    start_time = original_start_time
                                    
                                    # Parse end time - preserve original if parsing fails
                                    if end_time_str:
                                        time_match = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', end_time_str.lower())
                                        if time_match:
                                            try:
                                                hour = int(time_match.group(1))
                                                minute = int(time_match.group(2))
                                                am_pm = time_match.group(3)
                                                if am_pm == 'p' and hour != 12:
                                                    hour += 12
                                                elif am_pm == 'a' and hour == 12:
                                                    hour = 0
                                                new_end_time = dt_time(hour, minute)
                                                end_time = new_end_time
                                                logger.info(f"   ⏰ Updated end_time from event page: {end_time}")
                                            except (ValueError, IndexError) as e:
                                                logger.warning(f"   ⚠️ Failed to parse end_time_str '{end_time_str}': {e}")
                                                # Keep original time if parsing fails
                                                if not end_time:
                                                    end_time = original_end_time
                                    
                                    if start_time or end_time:
                                        logger.info(f"   ✅ Updated times from event page - Start: {start_time}, End: {end_time}")
                                    break
                            
                            # Also look for single time pattern (ONLY if time range wasn't found)
                            # This is important for events that only show start time on the page
                            # Only check if we didn't already find a time range pattern
                            if not match:
                                logger.debug(f"   🔍 No time range pattern found, checking for single time pattern...")
                                # Compile single time pattern once
                                single_time_pattern = re.compile(
                                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                                    re.IGNORECASE
                                )
                                
                                # Store original values to preserve them if parsing fails
                                original_start_date = start_date
                                original_start_time = start_time
                                
                                for elem in date_time_elements:
                                    elem_text = elem.get_text(strip=True)
                                    match = single_time_pattern.search(elem_text)
                                    if match:
                                        # Extract date and time
                                        date_str_check = match.group(1).strip()
                                        time_str = f"{match.group(2)}:{match.group(3)} {match.group(4)}.m."
                                        
                                        # Update date if not set or different - CRITICAL: Update the actual date object
                                        if not date_str or date_str_check != date_str:
                                            date_str = date_str_check
                                            from datetime import datetime
                                            new_start_date = None
                                            try:
                                                new_start_date = datetime.strptime(date_str, "%B %d, %Y").date()
                                                logger.debug(f"   📅 Updated start_date from event page (single time): {new_start_date}")
                                            except ValueError as e1:
                                                try:
                                                    new_start_date = datetime.strptime(date_str, "%B %d %Y").date()
                                                    logger.debug(f"   📅 Updated start_date from event page (single time, no comma): {new_start_date}")
                                                except ValueError as e2:
                                                    logger.warning(f"   ⚠️ Failed to parse date_str '{date_str}': {e1}, {e2}")
                                                    # Keep original date if parsing fails
                                                    new_start_date = original_start_date
                                            
                                            if new_start_date:
                                                start_date = new_start_date
                                        
                                        # Always update start time from event page (more accurate than calendar listing)
                                        # CRITICAL: Update the actual time object
                                        time_match = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', time_str.lower())
                                        if time_match:
                                            try:
                                                hour = int(time_match.group(1))
                                                minute = int(time_match.group(2))
                                                am_pm = time_match.group(3)
                                                if am_pm == 'p' and hour != 12:
                                                    hour += 12
                                                elif am_pm == 'a' and hour == 12:
                                                    hour = 0
                                                from datetime import time as dt_time
                                                new_start_time = dt_time(hour, minute)
                                                if not start_time or start_time != new_start_time:
                                                    start_time = new_start_time
                                                    logger.info(f"   ⏰ Updated start_time from event page (single time): {start_time}")
                                            except (ValueError, IndexError) as e:
                                                logger.warning(f"   ⚠️ Failed to parse time_str '{time_str}': {e}")
                                                # Keep original time if parsing fails
                                                if not start_time:
                                                    start_time = original_start_time
                                        break  # Found a match, exit loop
                            
                            # Extract description - get all text content from main area
                            # Always fetch from event page (more complete than calendar listing)
                            desc_elem = main_content.find('p') if main_content else None
                            if desc_elem:
                                event_page_description = desc_elem.get_text(strip=True)
                                # Get all paragraph text for full description
                                all_paragraphs = main_content.find_all('p')
                                if len(all_paragraphs) > 1:
                                    event_page_description = ' '.join([p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True)])
                                
                                # Use event page description if it's longer/more complete
                                if event_page_description and (not description or len(event_page_description) > len(description)):
                                    description = event_page_description
                                    logger.info(f"   📝 Extracted description from event page (length: {len(description)} chars)")
                                elif description and not event_page_description:
                                    logger.debug(f"   📝 Using description from calendar listing (length: {len(description)} chars)")
                                elif event_page_description:
                                    description = event_page_description
                                    logger.info(f"   📝 Extracted description from event page (length: {len(description)} chars)")
                            
                            # Also get full text content for better parsing (includes headings, etc.)
                            full_text = main_content.get_text() if main_content else ''
                            
                            # Extract meeting location and duration from description/full_text
                            # Use full_text for better coverage (includes all text on the page)
                            search_text = full_text if full_text else description
                            if search_text:
                                # Extract meeting location from description (e.g., "Meet in the Atrium at 1:00 PM")
                                location_patterns = [
                                    r'meet\s+(?:in|at)\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)(?:\s+at\s+\d+|\s*\.|,|$)',
                                    r'meeting\s+(?:location|point|place)[:\s]+([A-Z][a-zA-Z\s]+?)(?:\.|,|$)',
                                    r'location[:\s]+([A-Z][a-zA-Z\s]+?)(?:\.|,|$)',
                                    r'gather\s+(?:in|at)\s+(?:the\s+)?([A-Z][a-zA-Z\s]+?)(?:\.|,|$)',
                                ]
                                for pattern in location_patterns:
                                    match = re.search(pattern, search_text, re.IGNORECASE)
                                    if match:
                                        meeting_location = match.group(1).strip()
                                        # Clean up common trailing words and time references
                                        meeting_location = re.sub(r'\s+(?:at\s+\d+|on|in|for|to|the)\s*$', '', meeting_location, flags=re.IGNORECASE)
                                        # Remove any trailing time patterns
                                        meeting_location = re.sub(r'\s+\d{1,2}:\d{2}\s*([ap])\.?m\.?\s*$', '', meeting_location, flags=re.IGNORECASE)
                                        meeting_location = meeting_location.strip()
                                        if meeting_location and len(meeting_location) > 1:
                                            logger.debug(f"   📍 Extracted meeting location: {meeting_location}")
                                            break
                                
                                # Calculate end time if duration is mentioned (e.g., "30-minute tour", "half-hour", "1 hour talk")
                                # This is important for talks and tours which should have end times
                                if start_time and not end_time:
                                    logger.debug(f"   🔍 Searching for duration in text (length: {len(search_text)} chars)")
                                    duration_patterns = [
                                        (r'half[-\s]?hour', 30),  # "half-hour" = 30 minutes (check first)
                                        (r'half[-\s]?an[-\s]?hour', 30),  # "half an hour" = 30 minutes
                                        (r'(\d+)[\s-]?minute', None),  # e.g., "30-minute" or "30 minute"
                                        (r'(\d+)[\s-]?min\b', None),  # \b to avoid matching "minimum"
                                        (r'(\d+)[\s-]?hour', None),  # e.g., "1-hour" or "1 hour"
                                        (r'(\d+)[\s-]?hr\b', None),  # e.g., "2-hr" or "2 hr"
                                    ]
                                    for pattern, fixed_duration in duration_patterns:
                                        match = re.search(pattern, search_text, re.IGNORECASE)
                                        if match:
                                            # Handle fixed durations (like "half-hour")
                                            if fixed_duration is not None:
                                                duration_minutes = fixed_duration
                                            else:
                                                duration_minutes = int(match.group(1))
                                                # Check if it's hours or minutes
                                                if 'hour' in pattern or 'hr' in pattern:
                                                    duration_minutes = duration_minutes * 60
                                            
                                            # Calculate end time
                                            from datetime import datetime, timedelta
                                            if start_date and start_time:
                                                start_datetime = datetime.combine(start_date, start_time)
                                                end_datetime = start_datetime + timedelta(minutes=duration_minutes)
                                                end_time = end_datetime.time()
                                                logger.info(f"   ⏱️ Calculated end time from {duration_minutes}min duration (matched pattern: {pattern}): {end_time}")
                                            break
                                    else:
                                        # No duration pattern matched
                                        logger.debug(f"   ⚠️ No duration pattern matched in text. Sample: {search_text[:200]}")
                                
                                # For talks and workshops, ensure we have an end time
                                # If no duration was found, use default durations
                                if start_time and not end_time:
                                    default_duration_minutes = None
                                    if determined_type == 'talk':
                                        # Default: talks are usually 1 hour
                                        default_duration_minutes = 60
                                    elif determined_type == 'workshop':
                                        # Default: workshops are usually 2 hours
                                        default_duration_minutes = 120
                                    
                                    if default_duration_minutes and start_date and start_time:
                                        from datetime import datetime, timedelta
                                        start_datetime = datetime.combine(start_date, start_time)
                                        end_datetime = start_datetime + timedelta(minutes=default_duration_minutes)
                                        end_time = end_datetime.time()
                                        logger.info(f"   ⏱️ Set default end time for {determined_type}: {end_time} (default duration: {default_duration_minutes} minutes)")
                                
                                # Extract registration requirement from description
                                # Look for patterns like "Tickets are free, required", "Registration required", etc.
                                # Note: registration_required and registration_info are already initialized above
                                registration_patterns = [
                                    r'tickets?\s+(?:are\s+)?(?:free,?\s+)?required',
                                    r'registration\s+(?:is\s+)?required',
                                    r'reservation\s+(?:is\s+)?required',
                                    r'tickets?\s+required',
                                    r'advance\s+registration',
                                    r'pre[-\s]?registration',
                                ]
                                for pattern in registration_patterns:
                                    match = re.search(pattern, search_text, re.IGNORECASE)
                                    if match:
                                        registration_required = True
                                        # Extract surrounding context for registration info
                                        start_pos = max(0, match.start() - 50)
                                        end_pos = min(len(search_text), match.end() + 100)
                                        registration_info = search_text[start_pos:end_pos].strip()
                                        logger.debug(f"   🎫 Found registration requirement: {registration_info[:100]}")
                                        break
                            
                            # Extract image if not already found
                            if not image_url:
                                img_elem = main_content.find('img') if main_content else None
                                if img_elem:
                                    img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
                                    if img_src:
                                        image_url = urljoin(full_url, img_src)
                                        # Skip placeholder images
                                        if 'placeholder' in image_url.lower() or 'default' in image_url.lower():
                                            image_url = None
                    except Exception as e:
                        logger.error(f"❌ Error fetching details from {full_url}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # Set start_location - use meeting location if found, otherwise venue name
                start_location = venue.name
                if meeting_location:
                    start_location = f"{venue.name} - {meeting_location}"
                
                # Validate required fields before adding to events list
                # Handle missing start_date - check if it might be ongoing/permanent
                if not start_date:
                    from scripts.utils import get_ongoing_exhibition_dates, detect_ongoing_exhibition
                    # Check if event might be ongoing/permanent
                    description_text = description or ''
                    title_text = title or ''
                    is_ongoing = detect_ongoing_exhibition(description_text) or detect_ongoing_exhibition(title_text)
                    
                    if is_ongoing:
                        # Set dates for ongoing exhibition
                        start_date_obj, end_date_obj = get_ongoing_exhibition_dates()
                        start_date = start_date_obj
                        end_date = end_date_obj
                        logger.info(f"   🔄 Treating '{title}' as ongoing/permanent exhibition (start: {start_date.isoformat()}, end: {end_date.isoformat()})")
                    else:
                        logger.warning(f"   ⚠️ Skipping event '{title}' - missing start_date")
                        continue
                
                # Final title cleaning to ensure it's always clean (in case title was modified elsewhere)
                if title:
                    title = self._clean_title(title)
                
                # Log what we're about to save
                logger.info(f"   📦 Saving event: '{title}'")
                logger.info(f"      - Start date: {start_date.isoformat() if start_date else 'None'}")
                logger.info(f"      - Description: {len(description)} chars" + (f" ({description[:50]}...)" if description else " (empty)"))
                logger.info(f"      - Start time: {start_time.isoformat() if start_time else 'None'}")
                logger.info(f"      - End time: {end_time.isoformat() if end_time else 'None'}")
                logger.info(f"      - URL: {full_url}")
                
                # Final check: Ensure talks and workshops always have end times
                # This is a safety net in case duration wasn't found earlier
                if start_time and not end_time:
                    if determined_type == 'talk':
                        # Default: talks are usually 1 hour
                        from datetime import datetime, timedelta
                        if start_date:
                            start_datetime = datetime.combine(start_date, start_time)
                            end_datetime = start_datetime + timedelta(minutes=60)
                            end_time = end_datetime.time()
                            logger.info(f"   ⏱️ Final check: Set default end time for talk: {end_time}")
                    elif determined_type == 'workshop':
                        # Default: workshops are usually 2 hours
                        from datetime import datetime, timedelta
                        if start_date:
                            start_datetime = datetime.combine(start_date, start_time)
                            end_datetime = start_datetime + timedelta(minutes=120)
                            end_time = end_datetime.time()
                            logger.info(f"   ⏱️ Final check: Set default end time for workshop: {end_time}")
                
                events.append({
                    'title': title,
                    'description': description,
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': None,
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None,
                    'start_location': start_location,
                    'url': full_url,
                    'image_url': image_url,
                    'event_type': determined_type,
                    'is_baby_friendly': is_baby_friendly,
                    'is_registration_required': registration_required,
                    'registration_info': registration_info,
                    'venue_id': venue.id,
                    'city_id': venue.city_id,
                    'source': 'website',
                    'source_url': page_url,
                    'organizer': venue.name
                })
            
            logger.info(f"📅 Extracted {len(events)} events from OCMA calendar page")
            
        except Exception as e:
            logger.debug(f"Error extracting OCMA calendar events: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return events
    
    def _extract_hirshhorn_tours(self, soup, venue, page_url, event_type=None, time_range='today', max_tours_per_venue=20):
        """Extract tours from Hirshhorn tours page using JSON-LD structured data and individual event pages
        
        Args:
            soup: BeautifulSoup object of the tours page
            venue: Venue object
            page_url: URL of the tours page
            event_type: Optional filter for event type
            time_range: Time range for events
            max_tours_per_venue: Maximum number of tours to extract
        
        Returns:
            List of tour events
        """
        events = []
        scraped_urls = set()  # Track URLs we've already scraped
        
        try:
            logger.info(f"🔍 Extracting Hirshhorn tours from JSON-LD structured data")
            
            # First, find all individual tour event page URLs
            tour_event_urls = []
            
            # Look for links to individual event pages (pattern: /event/.../YYYY-MM-DD/)
            event_links = soup.find_all('a', href=re.compile(r'/event/.*/\d{4}-\d{2}-\d{2}/'))
            for link in event_links:
                href = link.get('href', '')
                if href:
                    full_url = urljoin(page_url, href)
                    if full_url not in scraped_urls:
                        tour_event_urls.append(full_url)
                        scraped_urls.add(full_url)
            
            # Also look for links in JSON-LD data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Event':
                                event_url = item.get('url', '')
                                if event_url and event_url not in scraped_urls:
                                    tour_event_urls.append(event_url)
                                    scraped_urls.add(event_url)
                                
                                tour_event = self._parse_hirshhorn_tour_from_json_ld(item, venue, page_url, time_range)
                                if tour_event and self._is_valid_event(tour_event):
                                    events.append(tour_event)
                    elif isinstance(data, dict):
                        # Check if this is a graph structure
                        if '@graph' in data:
                            for item in data['@graph']:
                                if isinstance(item, dict) and item.get('@type') == 'Event':
                                    event_url = item.get('url', '')
                                    if event_url and event_url not in scraped_urls:
                                        tour_event_urls.append(event_url)
                                        scraped_urls.add(event_url)
                                    
                                    tour_event = self._parse_hirshhorn_tour_from_json_ld(item, venue, page_url, time_range)
                                    if tour_event and self._is_valid_event(tour_event):
                                        events.append(tour_event)
                        elif data.get('@type') == 'Event':
                            event_url = data.get('url', '')
                            if event_url and event_url not in scraped_urls:
                                tour_event_urls.append(event_url)
                                scraped_urls.add(event_url)
                            
                            tour_event = self._parse_hirshhorn_tour_from_json_ld(data, venue, page_url, time_range)
                            if tour_event and self._is_valid_event(tour_event):
                                events.append(tour_event)
                
                except json.JSONDecodeError as e:
                    logger.debug(f"⚠️ Error parsing JSON-LD: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Error processing JSON-LD item: {e}")
                    continue
            
            # Now scrape individual tour event pages for more detailed information
            logger.info(f"🔍 Found {len(tour_event_urls)} individual tour event pages to scrape")
            for event_url in tour_event_urls[:max_tours_per_venue]:  # Limit to max_tours_per_venue
                try:
                    logger.info(f"📄 Scraping individual tour event page: {event_url}")
                    tour_event = self._scrape_hirshhorn_tour_event_page(event_url, venue, page_url, time_range)
                    if tour_event and self._is_valid_event(tour_event):
                        # Check if we already have this event from JSON-LD
                        existing = False
                        for existing_event in events:
                            if (existing_event.get('url') == tour_event.get('url') and 
                                existing_event.get('start_date') == tour_event.get('start_date')):
                                # Update existing event with more detailed info from page scraping
                                existing_event.update(tour_event)
                                existing = True
                                break
                        
                        if not existing:
                            events.append(tour_event)
                except Exception as e:
                    logger.debug(f"⚠️ Error scraping tour event page {event_url}: {e}")
                    continue
            
            logger.info(f"📦 Extracted {len(events)} tours from Hirshhorn tours page")
            return events[:max_tours_per_venue]
        
        except Exception as e:
            logger.error(f"Error extracting Hirshhorn tours: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return events
    
    def _scrape_hirshhorn_tour_event_page(self, event_url, venue, page_url, time_range='today'):
        """Scrape individual Hirshhorn tour event page to extract detailed information
        
        Args:
            event_url: URL of the individual tour event page
            venue: Venue object
            page_url: Source tours page URL
            time_range: Time range filter
        
        Returns:
            Dictionary with event data or None
        """
        try:
            from datetime import datetime, date, time as time_class
            import html
            import re
            
            logger.info(f"🔍 Scraping Hirshhorn tour event page: {event_url}")
            
            # Fetch the page
            try:
                response = self.session.get(event_url, timeout=10)
                response.raise_for_status()
            except Exception as e:
                logger.debug(f"⚠️ Error fetching tour event page: {e}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title from h1
            title = None
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
                title = html.unescape(title)
            
            if not title:
                logger.debug(f"⚠️ No title found on tour event page")
                return None
            
            # Extract date and time from the page
            # Look for pattern like "December 5, 2025 | 11:30 am–12:00 pm"
            date_time_text = None
            
            # Get full page text for searching
            page_text = soup.get_text()
            
            # Try to find date/time in h2 after h1
            if h1:
                # Try next sibling h2 (most common case)
                next_h2 = h1.find_next_sibling('h2')
                if not next_h2:
                    # Also try finding h2 in the same parent or nearby
                    parent = h1.parent
                    if parent:
                        next_h2 = parent.find('h2')
                if not next_h2:
                    # Try finding h2 anywhere after h1 in the document
                    next_h2 = h1.find_next('h2')
                if next_h2:
                    date_time_text = next_h2.get_text(strip=True)
                    logger.info(f"   📅 Found date/time in h2: {date_time_text}")
                else:
                    # Also check if h1 itself contains date/time
                    h1_text = h1.get_text(strip=True)
                    if '|' in h1_text and re.search(r'\d{1,2}:\d{2}\s*[ap]m', h1_text, re.IGNORECASE):
                        date_time_text = h1_text
                        logger.info(f"   📅 Found date/time in h1: {date_time_text}")
            
            # Also check for date/time in the page text near the title
            if not date_time_text:
                # Look for pattern: "Month Day, Year | time–time" near the h1
                if h1:
                    # Get text from h1 and next few siblings
                    parent = h1.parent
                    if parent:
                        siblings_text = []
                        for sibling in h1.next_siblings:
                            if hasattr(sibling, 'get_text'):
                                text = sibling.get_text(strip=True)
                                if text:
                                    siblings_text.append(text)
                                    if len(siblings_text) >= 3:  # Check first 3 siblings
                                        break
                        combined_text = ' '.join(siblings_text)
                        # Look for date/time pattern
                        date_time_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*\|\s*(\d{1,2}:\d{2}\s*[ap]m[–—\-]\d{1,2}:\d{2}\s*[ap]m)', combined_text, re.IGNORECASE)
                        if date_time_match:
                            date_time_text = date_time_match.group(0)
                            logger.info(f"   📅 Found date/time near h1: {date_time_text}")
            
            # Also search the full page text for date/time patterns
            if not date_time_text:
                # Look for "Month Day, Year | time–time" pattern anywhere in page
                # Try multiple patterns to catch different formats
                patterns = [
                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*\|\s*(\d{1,2}:\d{2}\s*[ap]m\s*[–—\-]\s*\d{1,2}:\d{2}\s*[ap]m)',  # With pipe separator
                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s+(\d{1,2}:\d{2}\s*[ap]m\s*[–—\-]\s*\d{1,2}:\d{2}\s*[ap]m)',  # Without pipe
                    r'(\d{1,2}:\d{2}\s*[ap]m\s*[–—\-]\s*\d{1,2}:\d{2}\s*[ap]m)',  # Just time range
                ]
                for pattern in patterns:
                    date_time_match = re.search(pattern, page_text, re.IGNORECASE)
                    if date_time_match:
                        date_time_text = date_time_match.group(0)
                        logger.info(f"   📅 Found date/time in page text: {date_time_text}")
                        break
            
            # Check JSON-LD on the page for structured data (but don't return early - we want to extract more details)
            json_ld_start_date = None
            json_ld_end_date = None
            json_ld_start_time = None
            json_ld_end_time = None
            
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Event':
                        start_date_str = data.get('startDate', '')
                        end_date_str = data.get('endDate', '')
                        if start_date_str:
                            try:
                                from datetime import datetime as dt
                                dt_start = dt.fromisoformat(start_date_str.replace('Z', '+00:00'))
                                json_ld_start_date = dt_start.date()
                                json_ld_start_time = dt_start.time()
                                logger.info(f"   📅 Found start date/time in JSON-LD: {json_ld_start_date} {json_ld_start_time}")
                            except:
                                pass
                        if end_date_str:
                            try:
                                from datetime import datetime as dt
                                dt_end = dt.fromisoformat(end_date_str.replace('Z', '+00:00'))
                                json_ld_end_date = dt_end.date()
                                json_ld_end_time = dt_end.time()
                                logger.info(f"   📅 Found end date/time in JSON-LD: {json_ld_end_date} {json_ld_end_time}")
                            except:
                                pass
                except:
                    continue
            
            # Parse date and time from text
            # Prefer JSON-LD if available, but also try to parse from page text
            start_date = json_ld_start_date
            end_date = json_ld_end_date
            start_time = json_ld_start_time
            end_time = json_ld_end_time
            
            # If we have JSON-LD data, use it as primary source
            if json_ld_start_date and json_ld_start_time:
                logger.info(f"   ✅ Using JSON-LD date/time: {start_date} {start_time}")
            
            # Also try to parse from date_time_text if available (this will override JSON-LD if more specific)
            if date_time_text:
                logger.info(f"   📝 Parsing date/time from text: {date_time_text}")
                # Parse date: "December 5, 2025" or "December 6, 2025"
                date_match = re.search(r'([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})', date_time_text)
                if date_match:
                    month_name = date_match.group(1)
                    day = int(date_match.group(2))
                    year = int(date_match.group(3))
                    
                    month_map = {
                        'January': 1, 'February': 2, 'March': 3, 'April': 4,
                        'May': 5, 'June': 6, 'July': 7, 'August': 8,
                        'September': 9, 'October': 10, 'November': 11, 'December': 12
                    }
                    month = month_map.get(month_name)
                    if month:
                        start_date = date(year, month, day)
                        end_date = start_date
                        logger.info(f"   📅 Parsed date from text: {start_date}")
            
                # Parse time range: "11:30 am–12:30 pm" or "11:30 am - 12:30 pm"
                # Try multiple patterns to handle different dash types and spacing
                time_patterns = [
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap]m)',  # Standard with em/en dash
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]m)',  # With hyphen
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s+to\s+(\d{1,2}):(\d{2})\s*([ap]m)',  # With "to"
                ]
                
                time_range_match = None
                for pattern in time_patterns:
                    time_range_match = re.search(pattern, date_time_text, re.IGNORECASE)
                    if time_range_match:
                        logger.info(f"   ⏰ Matched time pattern: {time_range_match.group(0)}")
                        break
                
                if time_range_match:
                    start_hour = int(time_range_match.group(1))
                    start_min = int(time_range_match.group(2))
                    start_ampm = time_range_match.group(3).upper()
                    end_hour = int(time_range_match.group(4))
                    end_min = int(time_range_match.group(5))
                    end_ampm = time_range_match.group(6).upper()
                    
                    # Convert to 24-hour format
                    if start_ampm == 'PM' and start_hour != 12:
                        start_hour += 12
                    elif start_ampm == 'AM' and start_hour == 12:
                        start_hour = 0
                    
                    if end_ampm == 'PM' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'AM' and end_hour == 12:
                        end_hour = 0
                    
                    start_time = time_class(start_hour, start_min)
                    end_time = time_class(end_hour, end_min)
                    logger.info(f"   ✅ Parsed times: {start_time} - {end_time}")
                else:
                    # Try single time: "11:30 am"
                    single_time_match = re.search(r'(\d{1,2}):(\d{2})\s*([ap]m)', date_time_text, re.IGNORECASE)
                    if single_time_match:
                        hour = int(single_time_match.group(1))
                        minute = int(single_time_match.group(2))
                        ampm = single_time_match.group(3).upper()
                        
                        if ampm == 'PM' and hour != 12:
                            hour += 12
                        elif ampm == 'AM' and hour == 12:
                            hour = 0
                        
                        start_time = time_class(hour, minute)
                        # Assume 1-hour duration if no end time
                        from datetime import timedelta
                        start_datetime = datetime.combine(start_date or date.today(), start_time)
                        end_datetime = start_datetime + timedelta(hours=1)
                        end_time = end_datetime.time()
            
            # If we still don't have date/time, try to extract from URL (e.g., /2025-12-05/)
            if not start_date:
                url_date_match = re.search(r'/(\d{4})-(\d{2})-(\d{2})/', event_url)
                if url_date_match:
                    year = int(url_date_match.group(1))
                    month = int(url_date_match.group(2))
                    day = int(url_date_match.group(3))
                    start_date = date(year, month, day)
                    end_date = start_date
                    logger.info(f"   📅 Extracted date from URL: {start_date}")
            
            # If we still don't have times, try to extract from page text more broadly
            if not start_time or not end_time:
                logger.info(f"   🔍 Searching for times in page text (start_time={start_time}, end_time={end_time})")
                # Look for time patterns anywhere in the page text
                # Try multiple patterns to handle different dash types
                time_patterns = [
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap]m)',  # Standard with em/en dash
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]m)',  # With hyphen
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s+to\s+(\d{1,2}):(\d{2})\s*([ap]m)',  # With "to"
                ]
                
                time_range_match = None
                for pattern in time_patterns:
                    time_range_match = re.search(pattern, page_text, re.IGNORECASE)
                    if time_range_match:
                        logger.info(f"   ⏰ Found time range in page text: {time_range_match.group(0)}")
                        break
                
                if time_range_match:
                    start_hour = int(time_range_match.group(1))
                    start_min = int(time_range_match.group(2))
                    start_ampm = time_range_match.group(3).upper()
                    end_hour = int(time_range_match.group(4))
                    end_min = int(time_range_match.group(5))
                    end_ampm = time_range_match.group(6).upper()
                    
                    # Convert to 24-hour format
                    if start_ampm == 'PM' and start_hour != 12:
                        start_hour += 12
                    elif start_ampm == 'AM' and start_hour == 12:
                        start_hour = 0
                    
                    if end_ampm == 'PM' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'AM' and end_hour == 12:
                        end_hour = 0
                    
                    start_time = time_class(start_hour, start_min)
                    end_time = time_class(end_hour, end_min)
                    logger.info(f"   ⏰ Extracted times from page text: {start_time} - {end_time}")
                else:
                    # Try single time pattern
                    single_time_match = re.search(r'(\d{1,2}):(\d{2})\s*([ap]m)', page_text, re.IGNORECASE)
                    if single_time_match and not start_time:
                        hour = int(single_time_match.group(1))
                        minute = int(single_time_match.group(2))
                        ampm = single_time_match.group(3).upper()
                        
                        if ampm == 'PM' and hour != 12:
                            hour += 12
                        elif ampm == 'AM' and hour == 12:
                            hour = 0
                        
                        start_time = time_class(hour, minute)
                        # Assume 1-hour duration if no end time
                        from datetime import timedelta
                        start_datetime = datetime.combine(start_date or date.today(), start_time)
                        end_datetime = start_datetime + timedelta(hours=1)
                        end_time = end_datetime.time()
                        logger.info(f"   ⏰ Extracted single time from page text: {start_time} (assuming 1-hour duration: {end_time})")
            
            # Extract description
            description = ''
            # Look for description in various places
            desc_selectors = [
                '.event-description',
                '.description',
                '.content',
                'article p',
                '.event-details p'
            ]
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(separator=' ', strip=True)
                    if description:
                        break
            
            # If no description found, try to get text from main content area
            if not description:
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|event'))
                if main_content:
                    # Get all paragraph text
                    paragraphs = main_content.find_all('p')
                    desc_parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                    description = ' '.join(desc_parts[:3])  # Take first 3 paragraphs
            
            # Extract image
            image_url = None
            
            # Try to find image in various places
            img_selectors = [
                'meta[property="og:image"]',
                'meta[name="twitter:image"]',
                '.event-image img',
                '.featured-image img',
                'article img',
                'main img'
            ]
            for selector in img_selectors:
                img_elem = soup.select_one(selector)
                if img_elem:
                    if img_elem.name == 'meta':
                        image_url = img_elem.get('content')
                    else:
                        image_url = img_elem.get('src') or img_elem.get('data-src')
                    
                    if image_url:
                        # Make absolute URL if relative
                        if not image_url.startswith('http'):
                            image_url = urljoin(event_url, image_url)
                        break
            
            # Extract meeting point/location - extract just the location name, not the full text
            location = venue.name
            meeting_point = None
            
            # Look for "MEET IN THE LOBBY" or similar text patterns
            # The location text might be: "Smithsonian Hirshhorn Museum and Sculpture Garden - THE LOBBY  30–60 Minutes..."
            # We want to extract just "THE LOBBY"
            
            # First, try to find location in structured elements (h2, h3, divs with location classes)
            location_elements = soup.find_all(['h2', 'h3', 'div', 'p'], class_=re.compile(r'location|meeting|where', re.I))
            for elem in location_elements:
                elem_text = elem.get_text(strip=True)
                # Look for pattern like "venue name - LOCATION" or just "LOCATION"
                if venue.name in elem_text and ' - ' in elem_text:
                    # Extract part after " - "
                    parts = elem_text.split(' - ', 1)
                    if len(parts) > 1:
                        location_part = parts[1].strip()
                        # Stop at common delimiters
                        location_part = re.split(r'\s+\d|FREE|Registration|Join|Duration|Minutes|30|60|–', location_part, flags=re.IGNORECASE)[0].strip()
                        if location_part and len(location_part) < 100:  # Reasonable length
                            location = location_part
                            logger.info(f"   📍 Extracted location from element: {location}")
                            break
            
            # If not found in structured elements, search page text
            if location == venue.name:
                # Pattern 1: "venue name - LOCATION" format
                venue_location_pattern = re.escape(venue.name) + r'\s*-\s*([A-Z][A-Z\s]+?)(?:\s+\d|FREE|Registration|Join|Duration|Minutes|30|60|–)'
                match = re.search(venue_location_pattern, page_text, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    # Clean up - remove extra whitespace
                    location = re.sub(r'\s+', ' ', location)
                    logger.info(f"   📍 Extracted location from venue pattern: {location}")
                else:
                    # Pattern 2: "MEET IN THE LOBBY" or "MEET AT THE LOBBY"
                    meeting_patterns = [
                        r'MEET\s+(?:IN|AT)\s+(THE\s+[A-Z]+(?:\s+[A-Z]+)*?)(?:\s+\d|FREE|Registration|Join|Duration|Minutes|30|60|–|$)',  # "MEET IN THE LOBBY"
                        r'MEET\s+(?:IN|AT)\s+([A-Z][A-Z\s]{2,30}?)(?:\s+\d|FREE|Registration|Join|Duration|Minutes|30|60|–|$)',  # More flexible
                    ]
                    
                    for pattern in meeting_patterns:
                        meeting_match = re.search(pattern, page_text, re.IGNORECASE)
                        if meeting_match:
                            meeting_point = meeting_match.group(1).strip()
                            # Clean up the meeting point
                            meeting_point = re.sub(r'\s+', ' ', meeting_point)  # Normalize whitespace
                            # Remove venue name if it got captured
                            if venue.name.upper() in meeting_point.upper():
                                meeting_point = meeting_point.replace(venue.name, '').strip(' -')
                            if meeting_point and len(meeting_point) < 100:
                                location = meeting_point
                                logger.info(f"   📍 Extracted location from meeting pattern: {location}")
                                break
            
            # If still not found, try JSON-LD
            if location == venue.name:
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'Event':
                            if 'location' in data:
                                loc = data['location']
                                if isinstance(loc, dict):
                                    loc_name = loc.get('name', '')
                                    if loc_name and loc_name != venue.name:
                                        # Extract just the location part if it contains venue name
                                        if venue.name in loc_name and ' - ' in loc_name:
                                            # Extract part after " - "
                                            parts = loc_name.split(' - ', 1)
                                            if len(parts) > 1:
                                                location = parts[1].strip()
                                                # Stop at common delimiters
                                                location = re.split(r'\s+\d|FREE|Registration|Join|Duration|Minutes|30|60|–', location, flags=re.IGNORECASE)[0].strip()
                                            else:
                                                location = loc_name
                                        else:
                                            location = loc_name
                                        if location and len(location) < 100:
                                            logger.info(f"   📍 Extracted location from JSON-LD: {location}")
                                            break
                    except:
                        continue
            
            # Extract registration information
            is_registration_required = False
            registration_url = None
            registration_info = None
            registration_opens_date = None
            registration_opens_time = None
            
            # Look for registration-related text patterns
            registration_patterns = [
                r'registration\s+is\s+not\s+required',
                r'registration\s+is\s+required',
                r'registration\s+required',
                r'advance\s+registration',
                r'pre-registration',
                r'registration\s+opens',
                r'register\s+now',
                r'registration\s+not\s+required',
                r'no\s+registration\s+required',
                r'free\s+admission',
                r'free\s+event'
            ]
            
            for pattern in registration_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    registration_text = match.group(0)
                    
                    # Determine if registration is required
                    if any(phrase in registration_text.lower() for phrase in ['not required', 'no registration', 'free admission', 'free event']):
                        is_registration_required = False
                    elif any(phrase in registration_text.lower() for phrase in ['required', 'register now', 'advance registration', 'pre-registration']):
                        is_registration_required = True
                    
                    # Store the registration info text
                    if not registration_info:
                        # Try to get the full sentence or context
                        context_match = re.search(r'[^.!?]*(?:' + re.escape(registration_text) + r')[^.!?]*[.!?]?', page_text, re.IGNORECASE)
                        if context_match:
                            registration_info = context_match.group(0).strip()
                        else:
                            registration_info = registration_text
                    
                    logger.info(f"   📝 Found registration info: {registration_info} (required: {is_registration_required})")
                    break
            
            # Look for registration URL/links
            registration_link_patterns = [
                r'href=["\']([^"\']*(?:register|registration|rsvp|ticket|book|reserve)[^"\']*)["\']',
                r'https?://[^\s]*(?:register|registration|rsvp|ticket|book|reserve)[^\s]*'
            ]
            
            for pattern in registration_link_patterns:
                matches = re.finditer(pattern, str(soup), re.IGNORECASE)
                for match in matches:
                    potential_url = match.group(1) if match.groups() else match.group(0)
                    # Clean up the URL
                    potential_url = potential_url.strip('"\'')
                    if potential_url.startswith('http'):
                        registration_url = potential_url
                        logger.info(f"   🔗 Found registration URL: {registration_url}")
                        break
                if registration_url:
                    break
            
            # Also check for registration links in anchor tags
            if not registration_url:
                reg_links = soup.find_all('a', href=re.compile(r'register|registration|rsvp|ticket|book|reserve', re.I))
                for link in reg_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True).lower()
                    if any(word in link_text for word in ['register', 'registration', 'rsvp', 'ticket', 'book', 'reserve']):
                        if href:
                            if not href.startswith('http'):
                                registration_url = urljoin(event_url, href)
                            else:
                                registration_url = href
                            logger.info(f"   🔗 Found registration URL from link: {registration_url}")
                            break
            
            # Look for registration opens date/time
            registration_opens_patterns = [
                r'registration\s+opens\s+(?:on\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
                r'registration\s+opens\s+(\d{1,2})/(\d{1,2})/(\d{4})',
                r'registration\s+opens\s+(\d{4})-(\d{2})-(\d{2})',
                r'registration\s+opens\s+(?:at\s+)?(\d{1,2}):(\d{2})\s*([ap]m)'
            ]
            
            for pattern in registration_opens_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    if len(match.groups()) >= 3 and any(month in match.group(0) for month in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']):
                        # Date pattern
                        month_name = match.group(1)
                        day = int(match.group(2))
                        year = int(match.group(3))
                        month_map = {
                            'January': 1, 'February': 2, 'March': 3, 'April': 4,
                            'May': 5, 'June': 6, 'July': 7, 'August': 8,
                            'September': 9, 'October': 10, 'November': 11, 'December': 12
                        }
                        month = month_map.get(month_name)
                        if month:
                            registration_opens_date = date(year, month, day)
                            logger.info(f"   📅 Found registration opens date: {registration_opens_date}")
                    elif ':' in match.group(0):
                        # Time pattern
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        ampm = match.group(3).upper() if len(match.groups()) >= 3 else 'AM'
                        if ampm == 'PM' and hour != 12:
                            hour += 12
                        elif ampm == 'AM' and hour == 12:
                            hour = 0
                        registration_opens_time = time_class(hour, minute)
                        logger.info(f"   ⏰ Found registration opens time: {registration_opens_time}")
                    break
            
            # Clean title
            title = self._clean_title(title)
            
            # Don't filter by date here - allow all dates through for updates
            # The higher-level code will handle date filtering if needed
            # This allows us to update existing events regardless of their date
            if start_date and time_range == 'today':
                today = date.today()
                if start_date != today:
                    logger.debug(f"⚠️ Tour '{title}' - date {start_date} not today (today is {today}), but allowing for potential update")
                    # Don't return None - allow it through for updates
            
            # For tours, we need at least a start date
            if not start_date:
                logger.warning(f"⚠️ Tour '{title}' - missing date, cannot create event")
                logger.warning(f"   URL: {event_url}")
                logger.warning(f"   Page text sample: {page_text[:500]}")
                return None
            
            # For times: if missing, log but still return event data (for updates)
            # The update logic in app.py will handle adding times to existing events
            if not start_time:
                logger.warning(f"⚠️ Tour '{title}' - missing start time, trying harder to find it")
                logger.warning(f"   URL: {event_url}")
                logger.warning(f"   Date found: {start_date}")
                
                # Try one more time to find times in the raw HTML
                html_str = str(soup)
                
                # Try multiple patterns in raw HTML
                time_patterns = [
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap]m)',  # Standard
                    r'(\d{1,2}):(\d{2})\s*([ap]m)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]m)',  # With hyphen
                ]
                
                for pattern in time_patterns:
                    time_in_html = re.search(pattern, html_str, re.IGNORECASE)
                    if time_in_html:
                        logger.warning(f"   ⚠️ Found time in HTML: {time_in_html.group(0)}")
                        try:
                            start_hour = int(time_in_html.group(1))
                            start_min = int(time_in_html.group(2))
                            start_ampm = time_in_html.group(3).upper()
                            end_hour = int(time_in_html.group(4))
                            end_min = int(time_in_html.group(5))
                            end_ampm = time_in_html.group(6).upper()
                            
                            if start_ampm == 'PM' and start_hour != 12:
                                start_hour += 12
                            elif start_ampm == 'AM' and start_hour == 12:
                                start_hour = 0
                            
                            if end_ampm == 'PM' and end_hour != 12:
                                end_hour += 12
                            elif end_ampm == 'AM' and end_hour == 12:
                                end_hour = 0
                            
                            start_time = time_class(start_hour, start_min)
                            end_time = time_class(end_hour, end_min)
                            logger.info(f"   ✅ Successfully parsed times from HTML: {start_time} - {end_time}")
                            break
                        except Exception as e:
                            logger.warning(f"   ⚠️ Error parsing time from HTML: {e}")
                            continue
                
                # If still no times, log detailed info but allow event through for updates
                if not start_time:
                    logger.warning(f"   Page text sample: {page_text[:1000]}")
                    logger.warning(f"   ⚠️ Still no times found - will return event data for potential update")
                    # Don't return None - allow event through for updates
                    # The update logic in app.py will add times if they become available
            
            # Log extracted information for debugging
            logger.info(f"   ✅ Successfully extracted tour details:")
            logger.info(f"      Title: {title}")
            logger.info(f"      Date: {start_date}")
            logger.info(f"      Start time: {start_time}")
            logger.info(f"      End time: {end_time}")
            logger.info(f"      URL: {event_url}")
            
            # Create event data
            start_time_str = start_time.isoformat() if start_time else None
            end_time_str = end_time.isoformat() if end_time else None
            
            tour_event = {
                'title': title,
                'description': description or '',
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat() if end_date else start_date.isoformat(),
                'start_time': start_time_str,
                'end_time': end_time_str,
                'start_location': location,
                'venue_id': venue.id,
                'city_id': venue.city_id,
                'event_type': 'tour',
                'url': event_url,
                'image_url': image_url,
                'source': 'website',
                'source_url': page_url,
                'organizer': venue.name,
                'is_registration_required': is_registration_required,
                'registration_url': registration_url,
                'registration_info': registration_info,
                'registration_opens_date': registration_opens_date.isoformat() if registration_opens_date else None,
                'registration_opens_time': registration_opens_time.isoformat() if registration_opens_time else None
            }
            
            # Log success with times if available - CRITICAL LOGGING
            if start_time:
                logger.info(f"✅ Scraped Hirshhorn tour event page: '{title}' ({start_date.isoformat()} {start_time.isoformat()}{' - ' + end_time.isoformat() if end_time else ''})")
                logger.info(f"   📤 RETURNING event with start_time='{start_time_str}', end_time='{end_time_str}'")
                logger.info(f"   📤 Full event data: start_time={tour_event.get('start_time')}, end_time={tour_event.get('end_time')}")
            else:
                logger.warning(f"⚠️ Scraped Hirshhorn tour event page but NO TIMES: '{title}' ({start_date.isoformat()})")
                logger.warning(f"   📤 RETURNING event with start_time=None, end_time=None")
                logger.warning(f"   📤 Full event data: start_time={tour_event.get('start_time')}, end_time={tour_event.get('end_time')}")
            
            return tour_event
        
        except Exception as e:
            logger.error(f"Error scraping Hirshhorn tour event page: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_hirshhorn_tour_from_json_ld(self, event_data, venue, page_url, time_range='today'):
        """Parse a single tour event from JSON-LD structured data
        
        Args:
            event_data: Dictionary containing JSON-LD Event data
            venue: Venue object
            page_url: Source page URL
            time_range: Time range filter
        
        Returns:
            Dictionary with event data or None
        """
        try:
            from datetime import datetime
            import html
            
            # Extract title
            title = event_data.get('name', '').strip()
            if not title:
                return None
            
            # Clean HTML entities
            title = html.unescape(title)
            
            # Extract description
            description = event_data.get('description', '')
            if description:
                # Remove HTML tags and decode entities
                from bs4 import BeautifulSoup as BS
                description = BS(description, 'html.parser').get_text(separator=' ', strip=True)
                description = html.unescape(description)
            
            # Extract dates and times
            start_date = None
            end_date = None
            start_time = None
            end_time = None
            
            start_date_str = event_data.get('startDate', '')
            end_date_str = event_data.get('endDate', '')
            
            if start_date_str:
                try:
                    # Parse ISO 8601 format: "2025-12-05T11:30:00-05:00"
                    dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    start_date = dt.date()
                    start_time = dt.time()
                except Exception as e:
                    logger.debug(f"⚠️ Error parsing startDate '{start_date_str}': {e}")
            
            if end_date_str:
                try:
                    dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    end_date = dt.date()
                    end_time = dt.time()
                except Exception as e:
                    logger.debug(f"⚠️ Error parsing endDate '{end_date_str}': {e}")
            
            # For tours, we need at least a start date and time
            if not start_date or not start_time:
                logger.debug(f"⚠️ Skipping tour '{title}' - missing date or time")
                return None
            
            # Extract image URL
            image_url = None
            if 'image' in event_data:
                img = event_data['image']
                if isinstance(img, str):
                    image_url = img
                elif isinstance(img, dict):
                    image_url = img.get('url') or img.get('contentUrl')
            
            # Extract event URL
            event_url = event_data.get('url', page_url)
            
            # Extract location
            location = venue.name
            if 'location' in event_data:
                loc = event_data['location']
                if isinstance(loc, dict):
                    location = loc.get('name', location)
            
            # Clean title
            title = self._clean_title(title)
            
            # Extract registration information from JSON-LD if available
            is_registration_required = False
            registration_url = None
            registration_info = None
            
            # Check for registration-related fields in JSON-LD
            if 'offers' in event_data:
                offers = event_data['offers']
                if isinstance(offers, dict):
                    # Check if there's a price or availability info
                    if offers.get('price') == '0' or offers.get('price') == 'Free':
                        is_registration_required = False
                    elif offers.get('url'):
                        registration_url = offers.get('url')
                        is_registration_required = True
            
            # Create event data
            tour_event = {
                'title': title,
                'description': description or '',
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location,
                'venue_id': venue.id,
                'city_id': venue.city_id,
                'event_type': 'tour',
                'url': event_url,
                'image_url': image_url,
                'source': 'website',
                'source_url': page_url,
                'organizer': venue.name,
                'is_registration_required': is_registration_required,
                'registration_url': registration_url,
                'registration_info': registration_info,
                'registration_opens_date': None,
                'registration_opens_time': None
            }
            
            logger.info(f"✅ Parsed Hirshhorn tour: '{title}' ({start_date.isoformat()} {start_time.isoformat()})")
            return tour_event
        
        except Exception as e:
            logger.error(f"Error parsing Hirshhorn tour from JSON-LD: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_exhibition_dates(self, soup):
        """Extract date text from exhibition page"""
        # Special handling for Hirshhorn: dates are often in h2 right after h1
        h1 = soup.find('h1')
        if h1:
            # Check if next sibling is h2 with dates
            next_h2 = h1.find_next_sibling('h2')
            if next_h2:
                h2_text = next_h2.get_text(strip=True)
                # Check if it looks like a date range (e.g., "Apr 04, 2025–Jan 03, 2027")
                if re.search(r'[A-Z][a-z]{2,9}\s+\d{1,2},?\s*\d{4}[–—\-]', h2_text):
                    logger.info(f"📅 Found date in h2 after h1: {h2_text}")
                    return h2_text
        
        # Special handling for SFMOMA: dates are often in specific divs or spans
        # Look for common SFMOMA date patterns first
        sfmoma_date_selectors = [
            '.exhibition-date-range',
            '.date-range',
            '.exhibition-meta .date',
            '.exhibition-header .date',
            '[data-date-range]',
            '.hero-meta .date',
            '.exhibition-info .date'
        ]
        
        for selector in sfmoma_date_selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                if date_text and len(date_text) > 5:
                    # Check if it's a date range (contains dash or date pattern)
                    if '–' in date_text or '—' in date_text or ('-' in date_text and len(date_text.split('-')) > 1):
                        logger.info(f"📅 Found SFMOMA date in {selector}: {date_text}")
                        return date_text
                    # Also check for date patterns even without dash (might be formatted differently)
                    if re.search(r'[A-Z][a-z]{2,9}\s+\d{1,2},?\s*\d{4}', date_text):
                        logger.info(f"📅 Found SFMOMA date pattern in {selector}: {date_text}")
                        return date_text
        
        # Look for date patterns in various places
        date_selectors = [
            '.exhibition-dates',
            '.dates',
            '.exhibition-date',
            '.date-range',
            'time',
            '[itemprop="startDate"]',
            '[itemprop="endDate"]',
            '.exhibition-info',
            '.exhibition-meta'
        ]
        
        # First pass: Look for date RANGES in selectors (prioritize these)
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                if date_text and len(date_text) > 5:
                    # Check if it's a date range (contains dash) - prioritize these
                    if '–' in date_text or '—' in date_text or ('-' in date_text and len(date_text.split('-')) > 1):
                        return date_text
        
        # Second pass: Look for date ranges in page text (prioritize ranges)
        page_text = soup.get_text()
        date_range_patterns = [
            # SFMOMA format: "January 17, 2026 – May 3, 2026" (with commas, spaces, and en-dash)
            r'([A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4}\s*[–—\-]\s*[A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4})',
            # Full month names with commas: "November 28, 2025–May 29, 2026"
            r'([A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4}[–—\-]\s*[A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4})',
            # Abbreviated: "Feb 14–May 9, 2021"
            r'([A-Z][a-z]{2,8}\s+\d{1,2}[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4})',
            # Same month: "Feb 14–9, 2021"
            r'([A-Z][a-z]{2,8}\s+\d{1,2}[–—\-]\s*\d{1,2},\s*\d{4})',
            # With commas: "Feb 14, 2021–May 9, 2021"
            r'([A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4}[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4})',
            # Numeric: "2/14/2021–5/9/2021"
            r'(\d{1,2}/\d{1,2}/\d{4}[–—\-]\d{1,2}/\d{1,2}/\d{4})',
            # With spaces: "Feb 14 – May 9, 2021"
            r'([A-Z][a-z]{2,8}\s+\d{1,2}\s*[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4})',
            # ISO format: "2024-03-15–2024-06-20"
            r'(\d{4}-\d{2}-\d{2}[–—\-]\d{4}-\d{2}-\d{2})',
        ]
        
        for pattern in date_range_patterns:
            match = re.search(pattern, page_text)
            if match:
                date_text = match.group(1)
                # Verify it's actually a range
                if '–' in date_text or '—' in date_text or ('-' in date_text and len(date_text.split('-')) > 1):
                    logger.info(f"📅 Found date range in page: {date_text}")
                    return date_text
        
        # Third pass: Fall back to single dates from selectors (if no range found)
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                if date_text and len(date_text) > 5:
                    return date_text
        
        return None
    
    def _parse_exhibition_dates(self, date_text, url, venue, time_range='today'):
        """Parse exhibition dates from text like 'Feb 14–May 9, 2021' or ISO format '2024-03-15–2024-06-20'"""
        from datetime import datetime, timedelta
        
        today = date.today()
        start_date = None
        end_date = None
        start_time = None
        end_time = None
        
        # If we have date text, try to parse it
        if date_text:
            # First check if it's ISO format (YYYY-MM-DD–YYYY-MM-DD)
            iso_pattern = r'(\d{4})-(\d{2})-(\d{2})[–—\-](\d{4})-(\d{2})-(\d{2})'
            match = re.search(iso_pattern, date_text)
            if match:
                try:
                    start_year = int(match.group(1))
                    start_month = int(match.group(2))
                    start_day = int(match.group(3))
                    end_year = int(match.group(4))
                    end_month = int(match.group(5))
                    end_day = int(match.group(6))
                    start_date = date(start_year, start_month, start_day)
                    end_date = date(end_year, end_month, end_day)
                    logger.info(f"📅 Parsed exhibition dates (ISO format): {start_date.isoformat()} to {end_date.isoformat()}")
                    return start_date, end_date, start_time, end_time
                except ValueError as e:
                    logger.debug(f"Invalid ISO date values: {e}")
            
            # Also check for single ISO date
            single_iso_pattern = r'(\d{4})-(\d{2})-(\d{2})'
            match = re.search(single_iso_pattern, date_text)
            if match and not start_date:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    start_date = date(year, month, day)
                    # If it's a single date, assume it's the start date and set end date to 1 year later
                    end_date = date(year + 1, month, day)
                    logger.info(f"📅 Parsed single ISO date: {start_date.isoformat()} (assuming 1 year duration)")
                    return start_date, end_date, start_time, end_time
                except ValueError as e:
                    logger.debug(f"Invalid single ISO date value: {e}")
            # Convert month names to numbers (used in multiple patterns)
            month_map = {
                'january': 1, 'jan': 1,
                'february': 2, 'feb': 2,
                'march': 3, 'mar': 3,
                'april': 4, 'apr': 4,
                'may': 5,
                'june': 6, 'jun': 6,
                'july': 7, 'jul': 7,
                'august': 8, 'aug': 8,
                'september': 9, 'sep': 9, 'sept': 9,
                'october': 10, 'oct': 10,
                'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            
            # Pattern 1: "Nov 1, 2015–Jan 22, 2017" or "November 28, 2025–May 29, 2026" (different years - each date has its own year)
            # Support both abbreviated (Nov) and full (November) month names
            range_pattern_with_years = r'([A-Z][a-z]{2,9})\s+(\d{1,2}),\s*(\d{4})[–—\-]\s*([A-Z][a-z]{2,9})\s+(\d{1,2}),\s*(\d{4})'
            match = re.search(range_pattern_with_years, date_text)
            
            if match:
                start_month_name = match.group(1)
                start_day = int(match.group(2))
                start_year = int(match.group(3))
                end_month_name = match.group(4)
                end_day = int(match.group(5))
                end_year = int(match.group(6))
                
                start_month = month_map.get(start_month_name.lower())
                end_month = month_map.get(end_month_name.lower())
                
                if start_month and end_month:
                    try:
                        start_date = date(start_year, start_month, start_day)
                        end_date = date(end_year, end_month, end_day)
                        logger.info(f"📅 Parsed exhibition dates (different years): {start_date.isoformat()} to {end_date.isoformat()}")
                    except ValueError as e:
                        logger.debug(f"Invalid date values: {e}")
            
            # Pattern 2: "Feb 14–May 9, 2021" or "January 17–May 3, 2026" or "Jan 24 – Aug 2, 2026" (same year)
            # Support both abbreviated (Jan) and full (January) month names
            # Note: Allow optional comma after first date and flexible whitespace around dash
            # Also handle SFMOMA format: "January 17, 2026 – May 3, 2026" (with commas and spaces)
            if not start_date:
                # Try pattern with commas first (SFMOMA format)
                range_pattern_with_commas = r'([A-Z][a-z]{2,9})\s+(\d{1,2}),\s*(\d{4})\s*[–—\-]\s*([A-Z][a-z]{2,9})\s+(\d{1,2}),\s*(\d{4})'
                match = re.search(range_pattern_with_commas, date_text)
                
                if match:
                    start_month_name = match.group(1)
                    start_day = int(match.group(2))
                    start_year = int(match.group(3))
                    end_month_name = match.group(4)
                    end_day = int(match.group(5))
                    end_year = int(match.group(6))
                    
                    start_month = month_map.get(start_month_name.lower())
                    end_month = month_map.get(end_month_name.lower())
                    
                    if start_month and end_month:
                        try:
                            start_date = date(start_year, start_month, start_day)
                            end_date = date(end_year, end_month, end_day)
                            logger.info(f"📅 Parsed exhibition dates (with commas, different years): {start_date.isoformat()} to {end_date.isoformat()}")
                        except ValueError as e:
                            logger.debug(f"Invalid date values: {e}")
                
                # If that didn't match, try the original pattern without commas
                if not start_date:
                    range_pattern = r'([A-Z][a-z]{2,9})\s+(\d{1,2}),?\s*[–—\-]\s*([A-Z][a-z]{2,9})\s+(\d{1,2}),\s*(\d{4})'
                    match = re.search(range_pattern, date_text)
                    
                    if match:
                        start_month_name = match.group(1)
                        start_day = int(match.group(2))
                        end_month_name = match.group(3)
                        end_day = int(match.group(4))
                        year = int(match.group(5))
                        
                        start_month = month_map.get(start_month_name.lower())
                        end_month = month_map.get(end_month_name.lower())
                        
                        if start_month and end_month:
                            try:
                                start_date = date(year, start_month, start_day)
                                end_date = date(year, end_month, end_day)
                                logger.info(f"📅 Parsed exhibition dates (same year): {start_date.isoformat()} to {end_date.isoformat()}")
                            except ValueError as e:
                                logger.debug(f"Invalid date values: {e}")
            
            # Pattern 3: "Feb 14–9, 2021" or "January 17–3, 2026" (same month, different days)
            # Support both abbreviated (Jan) and full (January) month names
            if not start_date:
                range_pattern2 = r'([A-Z][a-z]{2,9})\s+(\d{1,2})[–—\-]\s*(\d{1,2}),\s*(\d{4})'
                match = re.search(range_pattern2, date_text)
                if match:
                    month_name = match.group(1)
                    start_day = int(match.group(2))
                    end_day = int(match.group(3))
                    year = int(match.group(4))
                    
                    month = month_map.get(month_name.lower())
                    if month:
                        try:
                            start_date = date(year, month, start_day)
                            end_date = date(year, month, end_day)
                            logger.info(f"📅 Parsed exhibition dates (same month): {start_date.isoformat()} to {end_date.isoformat()}")
                        except ValueError as e:
                            logger.debug(f"Invalid date values: {e}")
            
            # Pattern: "Through [Month] [Day], [Year]" (Met Museum format)
            if not start_date:
                through_pattern = r'Through\s+([A-Z][a-z]{2,9})\s+(\d{1,2}),?\s*(\d{4})?'
                match = re.search(through_pattern, date_text)
                if match:
                    month_name = match.group(1)
                    day = int(match.group(2))
                    year_str = match.group(3)
                    
                    month = month_map.get(month_name.lower())
                    if month:
                        # If year is provided, use it; otherwise assume current year
                        if year_str:
                            year = int(year_str)
                        else:
                            year = today.year
                            # If through date has passed this year, assume next year
                            try:
                                through_date = date(year, month, day)
                                if through_date < today:
                                    year += 1
                            except ValueError:
                                pass
                        
                        try:
                            end_date = date(year, month, day)
                            # For "Through" format, start_date is unknown, so use today as a reasonable default
                            # But only if the through date is in the future
                            if end_date >= today:
                                start_date = today
                                logger.info(f"📅 Parsed through date: {end_date.isoformat()} (start: {start_date.isoformat()})")
                        except ValueError as e:
                            logger.debug(f"Invalid through date values: {e}")
            
            # Pattern: "Closing [Month] [Day], [Year]" (NGA format)
            if not start_date:
                closing_pattern = r'Closing\s+([A-Z][a-z]{2,9})\s+(\d{1,2}),?\s*(\d{4})?'
                match = re.search(closing_pattern, date_text)
                if match:
                    month_name = match.group(1)
                    day = int(match.group(2))
                    year_str = match.group(3)
                    
                    month = month_map.get(month_name.lower())
                    if month:
                        # If year is provided, use it; otherwise assume current year
                        if year_str:
                            year = int(year_str)
                        else:
                            year = today.year
                            # If closing date has passed this year, assume next year
                            try:
                                closing_date = date(year, month, day)
                                if closing_date < today:
                                    year += 1
                            except ValueError:
                                pass
                        
                        try:
                            end_date = date(year, month, day)
                            # For "Closing" format, start_date is unknown, so use today as a reasonable default
                            # But only if the closing date is in the future
                            if end_date >= today:
                                start_date = today
                                logger.info(f"📅 Parsed closing date: {end_date.isoformat()} (start: {start_date.isoformat()})")
                        except ValueError as e:
                            logger.debug(f"Invalid closing date values: {e}")
            
            # Pattern: "Ongoing" or "Permanent" - set start to today, end to 2 years from now
            if not start_date:
                date_lower = date_text.lower()
                if 'ongoing' in date_lower or 'permanent' in date_lower:
                    from datetime import timedelta
                    start_date = today
                    end_date = today + timedelta(days=730)  # 2 years from now for permanent/ongoing
                    logger.info(f"📅 Parsed permanent/ongoing exhibition: {start_date.isoformat()} to {end_date.isoformat()}")
            
            # Pattern: MM/DD/YYYY–MM/DD/YYYY
            if not start_date:
                numeric_pattern = r'(\d{1,2})/(\d{1,2})/(\d{4})[–—\-](\d{1,2})/(\d{1,2})/(\d{4})'
                match = re.search(numeric_pattern, date_text)
                if match:
                    start_month = int(match.group(1))
                    start_day = int(match.group(2))
                    start_year = int(match.group(3))
                    end_month = int(match.group(4))
                    end_day = int(match.group(5))
                    end_year = int(match.group(6))
                    
                    try:
                        start_date = date(start_year, start_month, start_day)
                        end_date = date(end_year, end_month, end_day)
                        logger.info(f"📅 Parsed exhibition dates (numeric): {start_date.isoformat()} to {end_date.isoformat()}")
                    except ValueError as e:
                        logger.debug(f"Invalid date values: {e}")
        
        # If we couldn't parse dates, check if it might be a permanent exhibition
        # For permanent exhibitions without date info, we'll handle it in the caller
        # This allows the caller to set default dates for permanent exhibitions
        if not start_date:
            if date_text:
                # Check if date text suggests permanent/ongoing
                date_lower = date_text.lower()
                if any(indicator in date_lower for indicator in ['permanent', 'ongoing', 'always on view']):
                    from datetime import timedelta
                    start_date = today
                    end_date = today + timedelta(days=730)  # 2 years from now
                    logger.info(f"📅 Detected permanent exhibition from date text: {start_date.isoformat()} to {end_date.isoformat()}")
                    return start_date, end_date, start_time, end_time
                
                # We tried to parse but failed - log and return None
                logger.debug(f"⚠️ Could not parse date text: '{date_text}' - returning None")
            else:
                # No date text found on page - might be permanent, caller will handle
                logger.debug("⚠️ No date text found on exhibition page - caller will handle as permanent")
            return None, None, None, None
        
        return start_date, end_date, start_time, end_time
    
    def _extract_exhibition_image(self, soup, url, venue):
        """Extract exhibition image with comprehensive strategy"""
        import re
        
        # Strategy 1: Open Graph image (most reliable for social sharing)
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            if img_url and not img_url.startswith('data:') and 'placeholder' not in img_url.lower():
                if not img_url.startswith('http'):
                    img_url = urljoin(url, img_url)
                logger.info(f"   📸 Found OG image: {img_url[:80]}...")
                return img_url
        
        # Strategy 2: Schema.org image
        schema_image = soup.find('meta', attrs={'itemprop': 'image'})
        if schema_image and schema_image.get('content'):
            img_url = schema_image.get('content')
            if img_url and not img_url.startswith('data:') and 'placeholder' not in img_url.lower():
                if not img_url.startswith('http'):
                    img_url = urljoin(url, img_url)
                logger.info(f"   📸 Found schema image: {img_url[:80]}...")
                return img_url
        
        # Strategy 3: Exhibition-specific selectors (prioritize larger/hero images)
        exhibition_selectors = [
            '.exhibition-hero img',
            '.hero-image img',
            '.exhibition-featured img',
            '.exhibition-image img',
            '.exhibition-banner img',
            '.exhibition-header img',
            'header img',
            '.hero img',
            '.featured-image img',
            '.main-image img',
            'article img.exhibition',
            '.exhibition img',
            'img.exhibition',
            'article img',
            '.content img',
            'main img'
        ]
        
        for selector in exhibition_selectors:
            img = soup.select_one(selector)
            if img:
                img_src = self._get_image_src(img, url)
                if img_src:
                    # Prefer larger images (check width/height or file size indicators)
                    width = img.get('width') or img.get('data-width')
                    height = img.get('height') or img.get('data-height')
                    
                    # Skip very small images (likely icons)
                    if width and height:
                        try:
                            if int(width) < 200 or int(height) < 200:
                                continue
                        except:
                            pass
                    
                    # Final check: skip logos, icons, and theme assets
                    skip_keywords = ['logo', 'icon', 'avatar', 'sponsor', 'si-white', 'theme', '/themes/', '/assets/']
                    if not any(skip in img_src.lower() for skip in skip_keywords):
                        logger.info(f"   📸 Found image via selector '{selector}': {img_src[:80]}...")
                        return img_src
        
        # Strategy 4: Look for images in hero/featured sections
        hero_sections = soup.find_all(['section', 'div'], 
            class_=lambda c: c and any(keyword in str(c).lower() for keyword in 
                ['hero', 'featured', 'banner', 'header', 'exhibition-hero', 'exhibition-featured']))
        
        for section in hero_sections:
            img = section.find('img')
            if img:
                img_src = self._get_image_src(img, url)
                if img_src:
                    # Skip logos, icons, and theme assets
                    skip_keywords = ['logo', 'icon', 'avatar', 'sponsor', 'si-white', 'theme', '/themes/', '/assets/']
                    if not any(skip in img_src.lower() for skip in skip_keywords):
                        logger.info(f"   📸 Found image in hero section: {img_src[:80]}...")
                        return img_src
        
        # Strategy 5: Look for background images in hero sections
        for section in hero_sections:
            style = section.get('style', '')
            if 'background-image' in style:
                bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
                if bg_match:
                    img_src = bg_match.group(1)
                    if img_src and not img_src.startswith('data:') and 'placeholder' not in img_src.lower():
                        if not img_src.startswith('http'):
                            img_src = urljoin(url, img_src)
                        logger.info(f"   📸 Found background image: {img_src[:80]}...")
                        return img_src
        
        # Strategy 6: Find largest image on page (likely the main exhibition image)
        all_images = soup.find_all('img')
        best_image = None
        best_size = 0
        
        for img in all_images:
            img_src = self._get_image_src(img, url)
            if not img_src or img_src.startswith('data:') or 'placeholder' in img_src.lower():
                continue
            
            # Skip icons, logos, avatars, thumbnails, and other non-exhibition images
            skip_keywords = ['icon', 'logo', 'avatar', 'thumbnail', 'sponsor', 'partner', 
                           'social', 'facebook', 'twitter', 'instagram', 'youtube',
                           'button', 'badge', 'stamp', 'seal', 'watermark', 'si-white', 
                           'theme', '/themes/', '/assets/']
            if any(skip in img_src.lower() for skip in skip_keywords):
                continue
            
            # Skip very small images based on URL patterns (e.g., thumb, small, mini)
            size_keywords = ['thumb', 'small', 'mini', 'tiny', 'xs', 'sm']
            if any(size in img_src.lower() for size in size_keywords):
                # Only skip if it's clearly a thumbnail (not a main image with size in name)
                if 'thumb' in img_src.lower() or 'thumbnail' in img_src.lower():
                    continue
            
            # Estimate size from attributes or filename
            width = img.get('width') or img.get('data-width')
            height = img.get('height') or img.get('data-height')
            
            size = 0
            if width and height:
                try:
                    size = int(width) * int(height)
                except:
                    pass
            
            # Also check filename for size indicators (e.g., image-1200x800.jpg)
            size_match = re.search(r'(\d+)x(\d+)', img_src)
            if size_match:
                try:
                    size = int(size_match.group(1)) * int(size_match.group(2))
                except:
                    pass
            
            if size > best_size:
                best_size = size
                best_image = img_src
        
        if best_image and best_size > 40000:  # At least 200x200
            # Final check: skip if it's clearly a logo, icon, or theme asset
            skip_keywords = ['logo', 'icon', 'avatar', 'si-white', 'theme', '/themes/', '/assets/']
            if not any(skip in best_image.lower() for skip in skip_keywords):
                logger.info(f"   📸 Found largest image ({best_size}px): {best_image[:80]}...")
                return best_image
        
        logger.debug(f"   ⚠️ No suitable image found for exhibition page")
        return None
    
    def _get_image_src(self, img_element, base_url):
        """Extract image source from img element, handling lazy loading and responsive images"""
        import re
        
        # Try multiple image source attributes (lazy loading, responsive images, etc.)
        img_src = (img_element.get('src') or 
                  img_element.get('data-src') or 
                  img_element.get('data-lazy-src') or
                  img_element.get('data-original') or
                  img_element.get('data-image') or
                  img_element.get('data-img'))
        
        # Check srcset for responsive images (prefer larger sizes)
        if not img_src and img_element.get('srcset'):
            srcset = img_element.get('srcset')
            # Extract URLs from srcset, prefer larger ones
            srcset_matches = re.findall(r'([^\s,]+\.(?:jpg|jpeg|png|gif|webp))(?:\s+(\d+)w)?', srcset, re.IGNORECASE)
            if srcset_matches:
                # Sort by width if available, take largest
                srcset_matches.sort(key=lambda x: int(x[1]) if x[1] else 0, reverse=True)
                img_src = srcset_matches[0][0]
        
        # Check picture element (modern responsive images)
        if not img_src:
            picture = img_element.find_parent('picture')
            if picture:
                sources = picture.find_all('source')
                for source in sources:
                    if source.get('srcset'):
                        srcset = source.get('srcset')
                        srcset_matches = re.findall(r'([^\s,]+\.(?:jpg|jpeg|png|gif|webp))(?:\s+(\d+)w)?', srcset, re.IGNORECASE)
                        if srcset_matches:
                            srcset_matches.sort(key=lambda x: int(x[1]) if x[1] else 0, reverse=True)
                            img_src = srcset_matches[0][0]
                            break
        
        if img_src:
            # Convert relative URLs to absolute
            if img_src.startswith('/'):
                img_src = urljoin(base_url, img_src)
            elif not img_src.startswith('http'):
                img_src = urljoin(base_url, img_src)
            
            # Skip data URIs and placeholder images
            if img_src.startswith('data:') or 'placeholder' in img_src.lower():
                return None
            
            return img_src
        
        return None
    
    def _extract_exhibition_details(self, element, description, url):
        """Extract exhibition-specific details from HTML element"""
        details = {}
        
        # Extract curator
        curator = self._extract_text(element, [
            '.curator', '[class*="curator"]', '[class*="curated"]'
        ])
        if not curator:
            # Look for "Curated by" or "Curator:" patterns in text
            text_content = element.get_text() if hasattr(element, 'get_text') else str(element)
            curator_match = re.search(r'curated by[:\s]+([^\.\n,]+)', text_content, re.IGNORECASE)
            if curator_match:
                curator = curator_match.group(1).strip()
        if curator:
            details['curator'] = curator
        
        # Extract artists (look for artist names, "by [artist]", etc.)
        artists = []
        # Look for artist links or artist names
        artist_links = element.find_all('a', href=lambda href: href and ('artist' in href.lower() or '/artist/' in href.lower()))
        for link in artist_links[:5]:  # Limit to first 5
            artist_name = link.get_text(strip=True)
            if artist_name and len(artist_name) > 2:
                artists.append(artist_name)
        
        # Also look for "by [Artist Name]" patterns
        text_content = element.get_text() if hasattr(element, 'get_text') else str(element)
        by_patterns = [
            r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'artist[s]?[:\s]+([^\.\n,]+)',
        ]
        for pattern in by_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                artist = match.strip()
                if artist and len(artist) > 2 and artist not in artists:
                    artists.append(artist)
        
        if artists:
            details['artists'] = ', '.join(artists[:10])  # Limit to 10 artists
        
        # Extract exhibition type (solo, group, retrospective, etc.)
        text_lower = text_content.lower()
        if 'solo' in text_lower or 'solo exhibition' in text_lower:
            details['exhibition_type'] = 'solo'
        elif 'retrospective' in text_lower:
            details['exhibition_type'] = 'retrospective'
        elif 'traveling' in text_lower or 'touring' in text_lower:
            details['exhibition_type'] = 'traveling'
        elif 'permanent' in text_lower or 'permanent collection' in text_lower:
            details['exhibition_type'] = 'permanent collection'
            details['is_permanent'] = True
        elif 'group' in text_lower or 'group show' in text_lower:
            details['exhibition_type'] = 'group'
        
        # Extract collection period (Modern, Contemporary, etc.)
        period_keywords = {
            'modern': 'Modern Art',
            'contemporary': 'Contemporary',
            'renaissance': 'Renaissance',
            'ancient': 'Ancient',
            'medieval': 'Medieval',
            'baroque': 'Baroque',
            'impressionist': 'Impressionist',
            'abstract': 'Abstract',
        }
        for keyword, period in period_keywords.items():
            if keyword in text_lower:
                details['collection_period'] = period
                break
        
        # Try to extract number of artworks (look for patterns like "50 works", "over 100 pieces")
        artwork_count_match = re.search(r'(\d+)\s+(?:works?|pieces?|artworks?|objects?)', text_content, re.IGNORECASE)
        if artwork_count_match:
            try:
                details['number_of_artworks'] = int(artwork_count_match.group(1))
            except ValueError:
                pass
        
        # Extract admission price if mentioned
        # Look for various price patterns
        price_patterns = [
            r'admission[:\s]+\$(\d+(?:\.\d{2})?)',  # "Admission: $25"
            r'ticket[:\s]+\$(\d+(?:\.\d{2})?)',  # "Ticket: $25"
            r'\$(\d+(?:\.\d{2})?)\s*(?:per\s+person|admission|ticket)',  # "$25 per person"
            r'\$(\d+(?:\.\d{2})?)\s*(?:adult|general)',  # "$25 adult"
            r'(\d+)\s*dollars?',  # "25 dollars"
            r'\$(\d+(?:\.\d{2})?)',  # General "$25" pattern (fallback)
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, text_content, re.IGNORECASE)
            if price_match:
                try:
                    price = float(price_match.group(1))
                    details['admission_price'] = price
                    logger.info(f"   💰 Found admission price: ${price}")
                    break
                except ValueError:
                    continue
        
        # Also check for "free" indicators
        if 'admission_price' not in details:
            free_indicators = ['free admission', 'admission free', 'no charge', 'complimentary', 'free entry']
            if any(indicator in text_content.lower() for indicator in free_indicators):
                details['admission_price'] = 0.0
                logger.info(f"   🆓 Found free admission indicator")
        
        return details
    
    def _is_english(self, text):
        """Check if text is primarily in English"""
        if not text or not isinstance(text, str):
            return True  # Default to English if we can't determine
        
        text_lower = text.lower()
        
        # Common non-English words/patterns (Spanish, French, German, etc.)
        non_english_indicators = [
            # Spanish
            r'\b(conversaci[oó]n|galer[ií]as|vida|trabajo|mi[eé]rcoles|diciembre|encu[eé]ntranos|boleto|admisi[oó]n|esperar|dispositivos|escucha|asistida|disponibles|reservaci[oó]n|correo|semanas|anticipaci[oó]n)\b',
            r'\b(que|de|la|el|en|y|a|es|son|para|con|por|del|las|los|una|un|este|esta|estos|estas)\b',
            # French
            r'\b(conversation|galeries|mercredi|d[eé]cembre|trouvez|billet|admission|attendre|dispositifs|écoute|assistée|disponibles|réservation|courriel|semaines|anticipation)\b',
            # German
            r'\b(gespr[aä]ch|galerien|mittwoch|dezember|finden|ticket|eintritt|erwarten|ger[aä]te|h[öo]ren|assistiert|verf[üu]gbar|reservierung|e-mail|wochen|vorlaufzeit)\b',
        ]
        
        # Check for accented characters common in non-English languages
        accented_chars = ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'ü', 'à', 'è', 'ì', 'ò', 'ù', 'â', 'ê', 'î', 'ô', 'û', 
                         'ä', 'ë', 'ï', 'ö', 'ü', 'ç', 'ã', 'õ', 'å', 'æ', 'ø']
        
        # Count non-English indicators
        non_english_count = 0
        for pattern in non_english_indicators:
            matches = len(re.findall(pattern, text_lower))
            non_english_count += matches
        
        # Count accented characters
        accented_count = sum(1 for char in text if char in accented_chars)
        
        # If there are many non-English indicators or accented characters, likely not English
        # Use a threshold: if more than 2 non-English words or more than 3 accented chars, filter out
        if non_english_count > 2 or accented_count > 3:
            return False
        
        # Also check if title starts with common non-English words
        first_words = text_lower.split()[:3]
        non_english_starters = ['conversación', 'conversacion', 'galerias', 'galerías', 'miércoles', 'miercoles']
        if any(word in first_words for word in non_english_starters):
            return False
        
        return True
    
    def _is_uncertain_title(self, title: str) -> bool:
        """Check if a title is uncertain and might need NLP validation"""
        if not title or len(title) < 3:
            return False
        
        title_lower = title.lower().strip()
        
        # Titles that are potentially problematic:
        # 1. Very short titles (less than 10 chars) that aren't clearly events
        # 2. Titles with common section header words
        # 3. Generic single or two-word titles
        
        uncertain_indicators = [
            len(title) < 10,  # Very short
            any(word in title_lower for word in ['events', 'calendar', 'schedule', 'listings', 'programs', 'program']),
            len(title.split()) <= 2,  # Very short word count
        ]
        
        # Only flag as uncertain if it passes basic heuristics but has these characteristics
        return any(uncertain_indicators)
    
    def _validate_title_with_nlp(self, title: str, description: str = '') -> bool:
        """Use NLP/LLM to validate if a title is a real event title or a section header"""
        # Check cache first
        title_key = title.lower().strip()
        if title_key in self._title_validation_cache:
            return self._title_validation_cache[title_key]
        
        try:
            from scripts.utils import query_llm
            
            prompt = f"""You are an expert at identifying event titles vs navigation/section headers on museum and cultural venue websites.

Analyze this title and determine if it's a REAL EVENT TITLE or a NAVIGATION/SECTION HEADER.

Title: "{title}"
Description: "{description[:200] if description else 'No description'}"

Examples of NAVIGATION/SECTION HEADERS (NOT events):
- "Past Events"
- "Upcoming Events" 
- "All Events"
- "Event Calendar"
- "Event Listings"
- "What's On"
- "Programs"
- "Exhibitions & Events"

Examples of REAL EVENT TITLES:
- "Art Happy Hour & Pop-Up Talk"
- "Public Tour"
- "Bring Your Own Baby Tour & Tea"
- "Family Program: Art & Play"
- "Artist Talk: Emily's Sassy Lime"

Respond with ONLY "VALID" if it's a real event title, or "INVALID" if it's a navigation/section header.
Be strict - if it's clearly a section header or navigation element, mark it as INVALID."""

            result = query_llm(prompt, max_tokens=50, temperature=0.1)
            
            if result.get('success') and result.get('response'):
                response_text = result['response'].strip().upper()
                is_valid = 'VALID' in response_text and 'INVALID' not in response_text
                # Cache the result
                self._title_validation_cache[title_key] = is_valid
                return is_valid
            else:
                # If LLM fails, default to allowing it (heuristics already passed)
                logger.debug(f"⚠️ NLP validation failed for '{title}', defaulting to valid")
                return True
                
        except Exception as e:
            logger.debug(f"⚠️ Error in NLP title validation for '{title}': {e}")
            # If NLP fails, default to allowing it (heuristics already passed)
            return True
    
    def _is_valid_event(self, event_data):
        """Validate event quality to filter out generic/incomplete events"""
        
        # Must have a title
        if not event_data.get('title'):
            return False
        
        title = event_data.get('title', '')
        if not title or not isinstance(title, str):
            return False
        
        # Check if event is in English (filter out non-English events)
        if not self._is_english(title):
            logger.debug(f"⚠️ Filtered out non-English event: '{title}'")
            return False
        
        description = event_data.get('description', '') or ''
        if isinstance(description, str) and description:
            # Also check description if it's substantial
            if len(description) > 50 and not self._is_english(description):
                logger.debug(f"⚠️ Filtered out event with non-English description: '{title}'")
                return False
        
        title = title.lower().strip()
        
        if isinstance(description, str):
            description = description.lower()
        else:
            description = ''
        
        # Filter out overly generic single-word titles and navigation/page titles
        generic_titles = [
            'tour', 'tours', 'visit', 'admission', 'hours', 
            'tickets', 'information', 'about', 'overview', 'home',
            'location', 'contact', 'directions', 'address',
            # Navigation and page titles
            'exhibitions & events', 'exhibitions and events', 'exhibitions',
            "today's events", 'todays events', 'today events',
            'results', 'calendar', 'events calendar', 'event calendar',
            'resources for groups', 'resources', 'groups',
            'search', 'filter', 'browse', 'explore',
            'upcoming events', 'past events', 'all events', 'all past events', 'all past events→',
            'event listings', 'event list', 'event schedule',
            'art sense', 'art sense 2025',  # OCMA special events listing
            'what\'s on', 'whats on', 'what is on',
            'programs', 'program', 'activities',
            'visit us', 'plan your visit', 'getting here',
            'news', 'press', 'media', 'blog',
            'support', 'donate', 'membership', 'join',
            'shop', 'store', 'gift shop', 'cafe', 'restaurant',
            'education', 'learn', 'schools', 'teachers',
            'collections', 'collection', 'artworks', 'artwork',
            'exhibitions', 'current exhibitions', 'past exhibitions',
            'virtual tour', 'virtual tours', 'online tour',
            'accessibility', 'access', 'wheelchair',
            'faq', 'frequently asked questions', 'help',
            'our staff', 'staff',
            'now open!', 'exhibition highlights', 'image slideshow', 'gallery', 'slideshow',
            'join us for an event', 'join us', 'join us for', 'join us!',
            # Booking/reservation titles
            'book a tour', 'book tour', 'book tours', 'book now', 'reserve a tour',
            'reserve tour', 'reserve tours', 'booking', 'reservations',
            'schedule a tour', 'schedule tour', 'schedule tours'
        ]
        if title in generic_titles:
            return False
        
        # Filter out titles that end with navigation symbols (arrows, etc.)
        if title.endswith('→') or title.endswith('←') or title.endswith('›') or title.endswith('»'):
            return False
        
        # Common sense: Filter out obvious section headers/navigation elements
        # These are clearly not events - they're page sections or navigation
        section_headers = [
            'past events', 'upcoming events', 'all events', 'all past events',
            'today\'s events', 'todays events', 'today events',
            'current events', 'future events', 'recent events',
            'event listings', 'event list', 'event schedule', 'event calendar',
            'what\'s on', 'whats on', 'what is on',
            'exhibitions & events', 'exhibitions and events',
        ]
        # Check exact match or if title starts with these (case-insensitive)
        title_lower_check = title.lower().strip()
        for header in section_headers:
            if title_lower_check == header or title_lower_check.startswith(header + ' ') or title_lower_check.startswith(header + '→'):
                return False
        
        # Use NLP/LLM for uncertain cases (titles that pass heuristics but might still be invalid)
        # Only check if title seems potentially problematic (short, generic, or contains common section words)
        # NOTE: Skip LLM validation for exhibitions - they're usually clearly identifiable and LLM adds latency/cost
        # Only use LLM for other event types (tours, talks, etc.) where titles might be more ambiguous
        event_type = event_data.get('event_type', '').lower()
        if event_type != 'exhibition' and self._is_uncertain_title(title):
            is_valid = self._validate_title_with_nlp(title, description)
            if not is_valid:
                logger.debug(f"⚠️ NLP filtered out invalid title: '{title}'")
                return False
        
        # Also filter titles that are clearly navigation/page titles (case-insensitive partial match)
        navigation_patterns = [
            r'^(exhibitions?\s*[&]?\s*events?)$',
            r"^(today'?s?\s*events?)$",
            r'^(results?)$',
            r'^(calendar)$',
            r'^(resources?\s*(for|about)?\s*(groups?|visitors?)?)$',
            r'^(event\s*(list|listing|schedule|calendar|search))$',
            r"^(what'?s?\s*on)$",
            r'^(upcoming|past|all)\s*(past\s*)?events?$',
            r'^(plan\s*your\s*visit)$',
            r'^(visit\s*us)$',
            r'^(getting\s*here)$',
            r'^(current|past|upcoming)\s*exhibitions?$',
            r'^(join\s*us\s*(for\s*(an\s*)?(event|program|activity))?)$',  # "Join us", "Join us for", "Join us for an event"
            # Booking/reservation patterns
            r'^(book\s*(a\s*)?(tour|tours?|now))$',
            r'^(reserve\s*(a\s*)?(tour|tours?))$',
            r'^(schedule\s*(a\s*)?(tour|tours?))$',
            r'^(booking|reservations?)$'
        ]
        for pattern in navigation_patterns:
            try:
                if re.match(pattern, title, re.IGNORECASE):
                    return False
            except (TypeError, AttributeError):
                # Title might be None or not a string, skip pattern matching
                pass
        
        # Check event type
        event_type = event_data.get('event_type', '').lower()
        
        # Filter out non-event content URLs (articles, videos, blogs, etc.)
        url = event_data.get('url', '')
        if url:
            url_lower = url.lower()
            non_event_url_patterns = [
                '/article/', '/articles/',  # Articles (like /article/video-kerry-james-marshall)
                '/video/', '/videos/',  # Videos
                '/blog/', '/blogs/',  # Blog posts
                '/news/', '/press/',  # News/press releases
                '/magazine/', '/magazines/',  # Magazine articles
                '/story/', '/stories/',  # Stories
                '/feature/', '/features/',  # Features
                '/essay/', '/essays/',  # Essays
                '/interview/', '/interviews/',  # Interviews
                '/podcast/', '/podcasts/',  # Podcasts
            ]
            
            for pattern in non_event_url_patterns:
                if pattern in url_lower:
                    logger.debug(f"⚠️ Filtered out non-event content URL: '{url}'")
                    return False
        
        # RELAXED VALIDATION: Accept events from known venues/sources
        # If we have a venue_id, we trust it's a real event from a real venue
        has_venue = event_data.get('venue_id') is not None
        
        # Must have either a specific time OR a URL OR a meaningful description
        # BUT if it's from a known venue, be more lenient
        has_specific_time = event_data.get('start_time') is not None
        has_url = event_data.get('url') and event_data['url'] != event_data.get('source_url')
        has_meaningful_description = description and len(description) >= 15  # Lowered from 30 to 15
        
        # Filter out very short or generic titles
        # BUT be more lenient if event has URL or description from known venue
        if len(title) < 5:
            # Allow short titles if they have URL or description from known venue
            if has_venue and (has_url or has_meaningful_description):
                logger.debug(f"⚠️ Allowing short title '{title}' because it has venue, URL, or description")
            else:
                return False
        
        # CRITICAL: Tours and talks must have a start time - if they don't, they're probably not actually tours/talks
        if event_type in ['tour', 'talk']:
            if not has_specific_time:
                logger.debug(f"⚠️  Rejecting {event_type} without start time: '{event_data.get('title')}'")
                return False
        
        # Allow other event types (workshops) without times to pass through - app.py will handle them
        # Previously rejected workshops without times, but now we let them through
        # so app.py can save them (it has better logic for handling missing times)
        if event_type in ['workshop']:
            # Allow through if it has time, URL, description, or is from a known venue
            if not has_specific_time:
                if has_venue:
                    # From known venue - allow through even without time
                    logger.debug(f"ℹ️  Allowing {event_type} '{event_data.get('title')}' without time (from known venue)")
                elif has_url or has_meaningful_description:
                    # Has URL or description - allow through
                    logger.debug(f"ℹ️  Allowing {event_type} '{event_data.get('title')}' without time (has URL/description)")
                else:
                    # No time, URL, or description - still allow but log
                    logger.debug(f"⚠️  Allowing {event_type} '{event_data.get('title')}' without time/URL/description (will be handled by app.py)")
        
        # If from a known venue, accept if it has ANY description or URL
        if has_venue:
            if description or has_url:
                return True
        
        # For other events, require at least one quality indicator
        if not (has_specific_time or has_url or has_meaningful_description):
            return False
        
        # Additional quality checks
        # Reject if description is just a location/address without event info
        location_indicators = ['meet your driver', 'meet at', 'pickup location', 'departure point']
        if any(indicator in description for indicator in location_indicators):
            # Only allow if it also has other meaningful content
            if not (has_specific_time or has_url or len(description) >= 50):  # Lowered from 100 to 50
                return False
        
        return True
    
    def _filter_by_time_range(self, events, time_range):
        """Filter events by time range"""
        from datetime import date, timedelta, datetime
        
        if not time_range or time_range == 'all':
            return events
        
        today = date.today()
        filtered = []
        
        for event in events:
            start_date_str = event.get('start_date')
            end_date_str = event.get('end_date')
            
            if not start_date_str:
                # If no date, include it (might be ongoing exhibition)
                filtered.append(event)
                continue
            
            try:
                event_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                # For ongoing exhibitions, end_date_str is None - treat as ongoing (no end date)
                event_end = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            except:
                # If date parsing fails, include it
                filtered.append(event)
                continue
            
            # Check if event overlaps with time range
            if time_range == 'today':
                # For ongoing exhibitions (event_end is None), include if started today or earlier
                if event_end is None:
                    if event_start <= today:
                        filtered.append(event)
                elif event_start <= today <= event_end:
                    filtered.append(event)
            elif time_range == 'this_week':
                week_end = today + timedelta(days=7)
                # For ongoing exhibitions (event_end is None), include if started before week_end
                if event_end is None:
                    if event_start <= week_end:
                        filtered.append(event)
                # Event overlaps if it starts before week_end and ends after today
                elif event_start <= week_end and event_end >= today:
                    filtered.append(event)
            elif time_range == 'this_month':
                month_end = today + timedelta(days=30)
                # For ongoing exhibitions (event_end is None), include if started before month_end
                if event_end is None:
                    if event_start <= month_end:
                        filtered.append(event)
                # Event overlaps if it starts before month_end and ends after today
                elif event_start <= month_end and event_end >= today:
                    filtered.append(event)
            else:
                # Unknown time range, include all
                filtered.append(event)
        
        return filtered
    
    def _scrape_instagram_events(self, venue):
        """Scrape events from Instagram (placeholder)"""
        # This would require Instagram API or web scraping
        # For now, return empty list
        return []

def update_progress(step, total_steps, message):
    """Update scraping progress"""
    progress = {
        'current_step': step,
        'total_steps': total_steps,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('scraping_progress.json', 'w') as f:
        json.dump(progress, f)

def main():
    """Main scraping function"""
    try:
        total_steps = 4
        
        # Step 1: Initialize
        update_progress(1, total_steps, "Initializing venue event scraper...")
        
        # Step 2: Get parameters
        update_progress(2, total_steps, "Loading scraping parameters...")
        venue_ids = os.getenv('SCRAPE_VENUE_IDS', '').split(',') if os.getenv('SCRAPE_VENUE_IDS') else []
        venue_ids = [int(vid) for vid in venue_ids if vid.strip()]
        city_id = int(os.getenv('SCRAPE_CITY_ID', 0)) if os.getenv('SCRAPE_CITY_ID') else None
        
        # Step 3: Scrape events
        update_progress(3, total_steps, "Scraping events from venues...")
        scraper = VenueEventScraper()
        events = scraper.scrape_venue_events(venue_ids, city_id)
        
        # Step 4: Save results
        update_progress(4, total_steps, "Saving scraped events...")
        
        scraped_data = {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "total_events": len(events),
                "scraper_version": "2.0",
                "venue_ids": venue_ids,
                "city_id": city_id
            },
            "events": events
        }
        
        with open('dc_scraped_data.json', 'w') as f:
            json.dump(scraped_data, f, indent=2)
        
        logger.info(f"✅ Successfully scraped {len(events)} events from venues")
        return True
        
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
