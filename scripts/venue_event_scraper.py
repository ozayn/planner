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
                        events = self._scrape_venue_website(venue)
                        
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
                        continue
                
                logger.info(f"Total unique events scraped: {len(self.scraped_events)}")
                return self.scraped_events
                
        except Exception as e:
            logger.error(f"Error in scrape_venue_events: {e}")
            return []
    
    def _scrape_venue_website(self, venue):
        """Scrape events from venue's main website"""
        events = []
        
        if not venue.website_url:
            return events
        
        try:
            logger.info(f"Scraping website: {venue.website_url}")
            response = self.session.get(venue.website_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for tour-specific pages first
            tour_links = soup.find_all('a', href=lambda href: href and 'tour' in href.lower())
            for link in tour_links[:5]:  # Check first 5 tour links
                try:
                    tour_url = urljoin(venue.website_url, link['href'])
                    logger.info(f"Scraping tour page: {tour_url}")
                    tour_response = self.session.get(tour_url, timeout=10)
                    tour_response.raise_for_status()
                    tour_soup = BeautifulSoup(tour_response.content, 'html.parser')
                    
                    # Extract events from tour page with tour URL context
                    tour_events = self._extract_events_from_html(tour_soup, venue, tour_url)
                    events.extend(tour_events)
                except Exception as e:
                    logger.debug(f"Error scraping tour page {link['href']}: {e}")
                    continue
            
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
                        tour_events = self._extract_events_from_html(tour_soup, venue, tour_url)
                        events.extend(tour_events)
                    except Exception as e:
                        logger.debug(f"Error scraping known tour page {tour_url}: {e}")
                    continue
            
            # Also check main page for events
            main_events = self._extract_events_from_html(soup, venue)
            events.extend(main_events)
            
        except Exception as e:
            logger.error(f"Error scraping website {venue.website_url}: {e}")
        
        return events
    
    def _extract_events_from_html(self, soup, venue, tour_url=None):
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
                event_data = self._parse_event_element(section, venue, tour_url)
                if event_data:
                    events.append(event_data)
        
        # Also look for tour descriptions
        tour_descriptions = soup.find_all('p', string=lambda text: text and ('guided tour' in text.lower() or 'self-guided' in text.lower()))
        for desc in tour_descriptions:
            event_data = self._parse_event_element(desc, venue, tour_url)
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
                    event_data = self._parse_event_element(element, venue)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.debug(f"Error parsing event element: {e}")
                    continue
        
        logger.info(f"   Total event elements found: {total_elements_found}, Valid events extracted: {len(events)}")
        return events
    
    def _parse_event_element(self, element, venue, tour_url=None):
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
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when'
            ])
            
            # Extract location/meeting point with enhanced detection
            location = self._extract_location(element, venue)
            
            # Extract URL - use tour_url if available, otherwise extract from element
            url = tour_url  # Use the tour page URL as the primary URL
            if not url:
                url = self._extract_url(element)
                if url and not url.startswith('http'):
                    url = urljoin(venue.website_url, url)
            
            # Extract image
            image_url = self._extract_image(element, venue)
            
            # Parse dates with enhanced schedule logic
            start_date, end_date, start_time, end_time = self._parse_dates_enhanced(date_text, url, venue)
            
            # Determine event type based on venue type
            event_type = self._determine_event_type(venue.venue_type, title, description)
            
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
    
    def _extract_url(self, element):
        """Extract URL from event element"""
        # Look for links
        link = element.find('a', href=True)
        if link:
            href = link['href']
            # Convert relative URLs to absolute
            if href.startswith('/'):
                return href  # Will be converted to absolute later
            elif not href.startswith('http'):
                return href  # Will be converted to absolute later
            return href
        
        # Look for parent links
        parent_link = element.find_parent('a', href=True)
        if parent_link:
            href = parent_link['href']
            if href.startswith('/'):
                return href
            elif not href.startswith('http'):
                return href
            return href
        
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
    
    def _parse_dates_enhanced(self, date_text, url, venue):
        """Parse dates with enhanced schedule logic for recurring events - focus on TODAY"""
        from datetime import datetime, time
        
        # Default to today for all events
        today = date.today()
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
    
    def _is_valid_event(self, event_data):
        """Validate event quality to filter out generic/incomplete events"""
        
        # Must have a title
        if not event_data.get('title'):
            return False
        
        title = event_data.get('title', '').lower().strip()
        description = event_data.get('description', '').lower()
        
        # Filter out overly generic single-word titles
        generic_titles = [
            'tour', 'tours', 'visit', 'admission', 'hours', 
            'tickets', 'information', 'about', 'overview', 'home',
            'location', 'contact', 'directions', 'address'
        ]
        if title in generic_titles:
            return False
        
        # Filter out very short or generic titles
        if len(title) < 5:
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
