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
import logging
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re

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
        self.scraped_events = []
        
    def scrape_venue_events(self, venue_ids=None, city_id=None, event_type=None, time_range='today'):
        """Scrape events from selected venues - focused on TODAY
        
        Args:
            venue_ids: List of venue IDs to scrape
            city_id: City ID to scrape venues from
            event_type: Type of events to scrape (tour, exhibition, festival, photowalk)
            time_range: Time range for events (defaults to 'today')
        """
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
                        events = self._scrape_venue_website(venue, event_type=event_type, time_range=time_range)
                        
                        # Filter by event_type if specified
                        if event_type:
                            events = [e for e in events if e.get('event_type', '').lower() == event_type.lower()]
                            logger.info(f"   Filtered to {len(events)} {event_type} events")
                        
                        # Filter by time_range
                        events = self._filter_by_time_range(events, time_range)
                        logger.info(f"   After time_range filter: {len(events)} events")
                        
                        # Add unique events only with better deduplication
                        for event in events:
                            # Create a more comprehensive unique key
                            title_clean = event['title'].lower().strip()
                            url_key = event.get('url', '')[:50] if event.get('url') else ''  # Use URL for better deduplication
                            event_key = f"{title_clean}_{url_key}_{venue.id}"
                            
                            if event_key not in unique_events:
                                unique_events.add(event_key)
                                self.scraped_events.append(event)
                                logger.debug(f"✅ Added unique event: {event['title']}")
                            else:
                                logger.debug(f"⚠️ Skipped duplicate event: {event['title']}")
                        
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
                        
                    except Exception as e:
                        logger.error(f"Error scraping {venue.name}: {e}")
                        import traceback
                        logger.debug(f"Traceback: {traceback.format_exc()}")
                        continue
                
                logger.info(f"Total unique events scraped: {len(self.scraped_events)}")
                return self.scraped_events
                
        except Exception as e:
            logger.error(f"Error in scrape_venue_events: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _scrape_venue_website(self, venue, event_type=None, time_range='today'):
        """Scrape events from venue's main website
        
        Args:
            venue: Venue object to scrape
            event_type: Optional filter for event type (tour, exhibition, etc.)
            time_range: Time range for events (today, this_week, this_month, etc.)
        """
        events = []
        
        if not venue.website_url:
            return events
        
        try:
            logger.info(f"Scraping website: {venue.website_url}")
            response = self.session.get(venue.website_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
                for link in unique_exhibition_links[:10]:  # Check first 10 exhibition links
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
                            '/exhibitions-events' in url_path  # Hirshhorn exhibitions page
                        ])
                        
                        # Check if it's an individual exhibition page (has a specific name/slug after the exhibition path)
                        is_individual_page = False
                        if not is_listing_page and url_lower != venue.website_url.lower():
                            # Check for individual page patterns with slugs
                            individual_patterns = [
                                ('/art/exhibition/', 3),  # LACMA: /art/exhibition/name (3 parts: art, exhibition, name)
                                ('/exhibitions/', 2),  # NGA/Phillips: /exhibitions/name (2 parts: exhibitions, name)
                                ('/exhibition-experiences/', 2),  # Spy Museum: /exhibition-experiences/name
                                ('/whats-on/exhibitions/', 3),  # Air and Space: /whats-on/exhibitions/name
                                ('/explore/exhibitions/', 3),  # Smithsonian: /explore/exhibitions/name (but not washington/newyork/online)
                            ]
                            
                            for pattern, min_parts in individual_patterns:
                                if pattern in url_lower:
                                    # Extract the path after the pattern
                                    path_after = url_lower.split(pattern)[1].split('/')[0].split('?')[0]
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
                            # This is an individual exhibition page - extract it as an event
                            logger.info(f"Extracting individual exhibition from: {exhibition_url}")
                            exhibition_event = self._extract_exhibition_from_page(exhibition_soup, venue, exhibition_url, event_type, time_range)
                            if exhibition_event:
                                # Only add if it's current or future (check is done in _extract_exhibition_from_page)
                                logger.info(f"✅ Successfully extracted exhibition: {exhibition_event.get('title')}")
                                events.append(exhibition_event)
                            else:
                                logger.debug(f"⚠️ Failed to extract exhibition from: {exhibition_url}")
                        else:
                            # This is a listing page - find links to individual exhibitions and follow them
                            logger.info(f"Found listing page, searching for individual exhibition links...")
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
                                        # Check if it has a slug after the exhibition path
                                        individual_patterns = [
                                            ('/art/exhibition/', 3),
                                            ('/exhibitions/', 2),
                                            ('/exhibition-experiences/', 2),
                                            ('/whats-on/exhibitions/', 3),
                                        ]
                                        
                                        is_individual = False
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
                                            except Exception as e:
                                                logger.debug(f"Error following exhibition link {individual_url}: {e}")
                                                continue
                            
                            # Also try to extract events directly from listing page (for museums that list exhibitions inline)
                            listing_events = self._extract_events_from_html(
                                exhibition_soup, venue, exhibition_url, event_type=event_type, time_range=time_range
                            )
                            events.extend(listing_events)
                    except Exception as e:
                        logger.debug(f"Error scraping exhibition page {link['href']}: {e}")
                        continue
            
            # Only scrape tour pages if event_type is 'tour' or None (all types)
            if not event_type or event_type.lower() == 'tour':
                # Look for tour-specific pages
                tour_links = soup.find_all('a', href=lambda href: href and 'tour' in href.lower())
                for link in tour_links[:5]:  # Check first 5 tour links
                    try:
                        tour_url = urljoin(venue.website_url, link['href'])
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
                                            if path_after and len(path_after) > 3 and any(c.isalpha() for c in path_after):
                                                exhibition_event = self._extract_exhibition_from_page(exhibition_soup, venue, exhibition_url, event_type, time_range)
                                                if exhibition_event:
                                                    events.append(exhibition_event)
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
            
            # Also check main page for events
            main_events = self._extract_events_from_html(soup, venue, event_type=event_type, time_range=time_range)
            events.extend(main_events)
            
        except Exception as e:
            logger.error(f"Error scraping website {venue.website_url}: {e}")
        
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
                event_type = self._determine_event_type(venue.venue_type, title, description, url)
            
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
                        return title
                
                # Also try h1 tags
                h1_tag = soup.find('h1')
                if h1_tag:
                    h1_text = h1_tag.get_text(strip=True)
                    if 'Collection Tour' in h1_text:
                        title = h1_text
                        logger.info(f"📝 Extracted title from h1: '{title}'")
                        return title
                        
            except Exception as e:
                logger.debug(f"Error extracting title from {tour_url}: {e}")
        
        # Fallback to original logic for generic titles
        if title in ['Guided Museum Tour', 'Self-Guided Audio Tour', 'Tour', 'Exhibition', 'Event', 'Upcoming Public Programs', 'Upcoming Events']:
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
            
            # Create a cloudscraper session
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
            
            # Make the request
            response = scraper.get(url, timeout=10)
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
        
        # For exhibitions, default to the full time range (they're ongoing)
        # For tours, default to today (they're specific events)
        if event_type == 'exhibition':
            # Exhibitions are ongoing, so use the full range
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
                                
                                start_time = time(hour, minute)
                                
                                # Extract end time if available (pattern with range)
                                if len(match.groups()) >= 7:
                                    end_hour = int(match.group(5))
                                    end_minute = int(match.group(6))
                                    end_ampm = match.group(7).upper()
                                    
                                    if end_ampm == 'PM' and end_hour != 12:
                                        end_hour += 12
                                    elif end_ampm == 'AM' and end_hour == 12:
                                        end_hour = 0
                                    
                                    end_time = time(end_hour, end_minute)
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
            time_patterns = [
                r'(\d{1,2}):(\d{2})\s*([ap]m)',
                r'(\d{1,2})\s*([ap]m)',
            ]
            
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
        
        # Prioritize tour detection
        if 'tour' in content or 'guided' in content:
            return 'tour'
        elif venue_type == 'museum':
            if 'exhibition' in content or 'exhibit' in content:
                return 'exhibition'
            else:
                return 'tour'  # Default museums to tours
        elif venue_type == 'gallery':
            return 'exhibition'
        elif venue_type == 'theater':
            return 'festival'
        elif 'photowalk' in content or 'photo walk' in content:
            return 'photowalk'
        elif 'festival' in content:
            return 'festival'
        else:
            return 'tour'  # Default to tour for most venues
    
    def _extract_exhibition_from_page(self, soup, venue, url, event_type=None, time_range='today'):
        """Extract an exhibition event from an individual exhibition page"""
        try:
            # Extract title from page - prioritize better sources
            title = None
            # First try meta tags (most reliable)
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content')
                # Remove site name suffix (e.g., " | National Gallery of Art")
                if '|' in title:
                    title = title.split('|')[0].strip()
            
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
                                     'calendar', 'events', 'exhibitions', 'home', 'about']
                    if h1_text.lower() not in generic_titles and len(h1_text) > 3:
                        title = h1_text
            
            # Fallback to page title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    # Remove site name suffix
                    if '|' in title:
                        title = title.split('|')[0].strip()
            
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
            
            # Extract description
            description = None
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
            
            # If we couldn't parse dates, skip the exhibition (we need valid dates)
            if not start_date or not end_date:
                logger.info(f"⚠️ Exhibition '{title}' has no valid dates - skipping")
                return None
            
            # Check if exhibition has ended - skip if end date is in the past
            today = date.today()
            if end_date < today:
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
    
    def _extract_exhibitions_from_listing_page(self, soup, venue, page_url, event_type=None, time_range='today'):
        """Extract exhibitions directly from a listing page (e.g., Smithsonian museums)"""
        events = []
        
        try:
            # Look for exhibition entries on the page
            # Pattern: Title followed by date range
            # Smithsonian format: "Title Title" followed by "Month Day, Year–Month Day, Year" or "Ongoing"
            
            # Find all headings that might be exhibition titles
            headings = soup.find_all(['h2', 'h3', 'h4', 'h5'])
            
            for heading in headings:
                title = heading.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                
                # Skip generic headings
                generic_titles = ['exhibitions', 'exhibition', 'current exhibitions', 'upcoming exhibitions', 
                                 'past exhibitions', 'washington, dc', 'new york, ny', 'online', 'traveling']
                if title.lower() in generic_titles:
                    continue
                
                # Look for date information in the heading's parent or siblings
                parent = heading.parent
                if not parent:
                    continue
                
                parent_text = parent.get_text()
                
                # Extract date range from parent text (if not already extracted from link)
                if 'date_text' not in locals() or not date_text:
                    date_text = None
                    date_patterns = [
                        r'([A-Z][a-z]{2,8}\s+\d{1,2},?\s*\d{4}[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},?\s*\d{4})',  # Nov 25, 2025–Jan 1, 2027
                        r'([A-Z][a-z]{2,8}\s+\d{1,2}[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},?\s*\d{4})',  # Nov 25–Jan 1, 2027
                        r'([A-Z][a-z]{2,8}\s+\d{1,2},?\s*\d{4}[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},?\s*\d{4})',  # Sep 29, 2024–Jan 19, 2026 (Hirshhorn)
                        r'Closing\s+([A-Z][a-z]{2,8}\s+\d{1,2},?\s*\d{4})',  # NGA format: "Closing August 2, 2026"
                        r'Closing\s+([A-Z][a-z]{2,8}\s+\d{1,2})',  # NGA format: "Closing August 2"
                        r'(Ongoing)',
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, parent_text)
                        if match:
                            date_text = match.group(1)
                            break
                
                if not date_text:
                    continue
                
                # Parse dates
                start_date, end_date, start_time, end_time = self._parse_exhibition_dates(
                    date_text, page_url, venue, time_range=time_range
                )
                
                # Skip if no valid dates or if exhibition has ended
                if not start_date or not end_date:
                    continue
                
                today = date.today()
                if end_date < today:
                    logger.debug(f"⏰ Skipping past exhibition: {title} (ended {end_date.isoformat()})")
                    continue
                
                # Try to find a link to the exhibition page
                exhibition_url = page_url
                link = heading.find('a', href=True) or parent.find('a', href=True)
                if link:
                    href = link.get('href', '')
                    if href:
                        from urllib.parse import urljoin
                        exhibition_url = urljoin(page_url, href)
                
                # Extract description from parent or next siblings
                description = None
                desc_elements = parent.find_all(['p', 'div'], class_=lambda c: c and ('description' in str(c).lower() or 'summary' in str(c).lower()))
                if desc_elements:
                    description = desc_elements[0].get_text(strip=True)
                else:
                    # Get first paragraph after heading
                    next_p = heading.find_next('p')
                    if next_p:
                        description = next_p.get_text(strip=True)
                
                # Extract image
                image_url = None
                img = parent.find('img') or heading.find_next('img')
                if img and img.get('src'):
                    from urllib.parse import urljoin
                    image_url = urljoin(page_url, img['src'])
                
                # Create event data
                event_data = {
                    'title': title,
                    'description': description or '',
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'start_time': None,
                    'end_time': None,
                    'start_location': venue.name,
                    'venue_id': venue.id,
                    'city_id': venue.city_id,
                    'event_type': 'exhibition',
                    'url': exhibition_url,
                    'image_url': image_url,
                    'source': 'website',
                    'source_url': venue.website_url,
                    'organizer': venue.name
                }
                
                # Validate
                if self._is_valid_event(event_data):
                    logger.info(f"✅ Extracted exhibition from listing page: '{title}' ({start_date.isoformat()} to {end_date.isoformat()})")
                    events.append(event_data)
                else:
                    logger.debug(f"⚠️ Exhibition from listing page did not pass validation: '{title}'")
        
        except Exception as e:
            logger.debug(f"Error extracting exhibitions from listing page {page_url}: {e}")
        
        return events
    
    def _extract_exhibition_dates(self, soup):
        """Extract date text from exhibition page"""
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
            r'([A-Z][a-z]{2,8}\s+\d{1,2}[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4})',  # Feb 14–May 9, 2021
            r'([A-Z][a-z]{2,8}\s+\d{1,2}[–—\-]\s*\d{1,2},\s*\d{4})',  # Feb 14–9, 2021
            r'([A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4}[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4})',  # Feb 14, 2021–May 9, 2021
            r'(\d{1,2}/\d{1,2}/\d{4}[–—\-]\d{1,2}/\d{1,2}/\d{4})',  # 2/14/2021–5/9/2021
            r'([A-Z][a-z]{2,8}\s+\d{1,2}\s*[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},\s*\d{4})',  # Feb 14 – May 9, 2021 (with spaces)
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
        """Parse exhibition dates from text like 'Feb 14–May 9, 2021'"""
        from datetime import datetime, timedelta
        
        today = date.today()
        start_date = None
        end_date = None
        start_time = None
        end_time = None
        
        # If we have date text, try to parse it
        if date_text:
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
            
            # Pattern 1: "Nov 1, 2015–Jan 22, 2017" (different years - each date has its own year)
            range_pattern_with_years = r'([A-Z][a-z]{2,8})\s+(\d{1,2}),\s*(\d{4})[–—\-]\s*([A-Z][a-z]{2,8})\s+(\d{1,2}),\s*(\d{4})'
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
            
            # Pattern 2: "Feb 14–May 9, 2021" or "January 17–May 3, 2026" (same year)
            # Support both abbreviated (Jan) and full (January) month names
            if not start_date:
                range_pattern = r'([A-Z][a-z]{2,9})\s+(\d{1,2})[–—\-]\s*([A-Z][a-z]{2,9})\s+(\d{1,2}),\s*(\d{4})'
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
            
            # Pattern: "Ongoing" - set start to today, end to far future
            if not start_date and 'ongoing' in date_text.lower():
                start_date = today
                end_date = date(today.year + 10, 12, 31)  # 10 years in the future
                logger.info(f"📅 Parsed ongoing exhibition: {start_date.isoformat()} to {end_date.isoformat()}")
            
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
        
        # If we couldn't parse dates, return None (don't use time_range defaults)
        # This allows the caller to decide what to do (e.g., skip the exhibition)
        if not start_date or not end_date:
            if date_text:
                # We tried to parse but failed - log and return None
                logger.debug(f"⚠️ Could not parse date text: '{date_text}' - returning None")
            else:
                # No date text found on page
                logger.debug("⚠️ No date text found on exhibition page - returning None")
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
                    
                    # Final check: skip logos and icons
                    if not any(skip in img_src.lower() for skip in ['logo', 'icon', 'avatar', 'sponsor']):
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
                    # Skip logos and icons
                    if not any(skip in img_src.lower() for skip in ['logo', 'icon', 'avatar', 'sponsor']):
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
                           'button', 'badge', 'stamp', 'seal', 'watermark']
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
            # Final check: skip if it's clearly a logo or icon
            if not any(skip in best_image.lower() for skip in ['logo', 'icon', 'avatar']):
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
    
    def _is_valid_event(self, event_data):
        """Validate event quality to filter out generic/incomplete events"""
        
        # Must have a title
        if not event_data.get('title'):
            return False
        
        title = event_data.get('title', '')
        if not title or not isinstance(title, str):
            return False
        title = title.lower().strip()
        
        description = event_data.get('description', '') or ''
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
            'upcoming events', 'past events', 'all events',
            'event listings', 'event list', 'event schedule',
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
            # Booking/reservation titles
            'book a tour', 'book tour', 'book tours', 'book now', 'reserve a tour',
            'reserve tour', 'reserve tours', 'booking', 'reservations',
            'schedule a tour', 'schedule tour', 'schedule tours'
        ]
        if title in generic_titles:
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
            r'^(upcoming|past|all)\s*events?$',
            r'^(plan\s*your\s*visit)$',
            r'^(visit\s*us)$',
            r'^(getting\s*here)$',
            r'^(current|past|upcoming)\s*exhibitions?$',
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
        
        # Filter out very short or generic titles
        if len(title) < 5:
            return False
        
        # Check event type
        event_type = event_data.get('event_type', '').lower()
        
        # TOURS REQUIRE A TIME - reject tours without a specific start time
        if event_type == 'tour':
            has_specific_time = event_data.get('start_time') is not None
            if not has_specific_time:
                logger.debug(f"⚠️ Rejecting tour '{event_data.get('title')}' - no start time")
                return False
        
        # RELAXED VALIDATION: Accept events from known venues/sources
        # If we have a venue_id, we trust it's a real event from a real venue
        has_venue = event_data.get('venue_id') is not None
        
        # Must have either a specific time OR a URL OR a meaningful description
        # BUT if it's from a known venue, be more lenient
        has_specific_time = event_data.get('start_time') is not None
        has_url = event_data.get('url') and event_data['url'] != event_data.get('source_url')
        has_meaningful_description = description and len(description) >= 15  # Lowered from 30 to 15
        
        # If from a known venue, accept if it has ANY description or URL
        # (But tours already checked above - they must have time)
        if has_venue and event_type != 'tour':
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
                event_end = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else event_start
            except:
                # If date parsing fails, include it
                filtered.append(event)
                continue
            
            # Check if event overlaps with time range
            if time_range == 'today':
                if event_start <= today <= event_end:
                    filtered.append(event)
            elif time_range == 'this_week':
                week_end = today + timedelta(days=7)
                # Event overlaps if it starts before week_end and ends after today
                if event_start <= week_end and event_end >= today:
                    filtered.append(event)
            elif time_range == 'this_month':
                month_end = today + timedelta(days=30)
                if event_start <= month_end and event_end >= today:
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
