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
        
    def scrape_venue_events(self, venue_ids=None, city_id=None, event_type=None, time_range=None):
        """Scrape events from selected venues
        
        Args:
            venue_ids: List of venue IDs to scrape
            city_id: City ID to scrape venues from
            event_type: Type of events to scrape (tour, exhibition, festival, photowalk)
            time_range: Time range for events (today, tomorrow, this_week, next_week, this_month)
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
                
                logger.info(f"Scraping events from {len(venues)} venues")
                
                # Track unique events to prevent duplicates
                unique_events = set()
                
                for venue in venues:
                    try:
                        logger.info(f"Scraping events for: {venue.name}")
                        update_progress(2, 4, f"Scraping {venue.name}...")
                        events = self._scrape_venue_website(venue)
                        
                        # Add unique events only
                        for event in events:
                            event_key = f"{event['title']}_{event['venue_id']}"
                            if event_key not in unique_events:
                                unique_events.add(event_key)
                                self.scraped_events.append(event)
                        
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
            for link in tour_links[:3]:  # Check first 3 tour links
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
            
            # Also check main page for events
            main_events = self._extract_events_from_html(soup, venue)
            events.extend(main_events)
            
        except Exception as e:
            logger.error(f"Error scraping website {venue.website_url}: {e}")
        
        return events
    
    def _extract_events_from_html(self, soup, venue, tour_url=None):
        """Extract events from HTML content"""
        events = []
        
        # Look for tour-specific content first
        tour_keywords = ['public guided tour', 'private guided tour', 'premium guided tour', 'accessibility tour', 'multilingual app']
        
        # Find headings that contain tour information
        tour_headings = soup.find_all(['h1', 'h2', 'h3', 'h4'], string=lambda text: text and any(keyword in text.lower() for keyword in tour_keywords))
        
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
        
        for selector in event_selectors:
            event_elements = soup.select(selector)
            
            for element in event_elements:
                try:
                    event_data = self._parse_event_element(element, venue)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.debug(f"Error parsing event element: {e}")
                    continue
        
        return events
    
    def _parse_event_element(self, element, venue, tour_url=None):
        """Parse individual event element"""
        try:
            # Extract title
            title = self._extract_text(element, [
                'h1', 'h2', 'h3', '.title', '.event-title', '.name'
            ])
            
            if not title:
                return None
            
            # Extract description first to use in title logic
            description = self._extract_text(element, [
                '.description', '.summary', '.content', 'p'
            ])
            
            # Make title more specific by including venue name
            if title in ['Guided Museum Tour', 'Self-Guided Audio Tour', 'Tour', 'Exhibition', 'Event', 'Upcoming Public Programs', 'Upcoming Events']:
                # Try to extract more specific information
                if 'tour' in description.lower() if description else False:
                    title = f"Museum Tour - {venue.name}"
                elif 'program' in title.lower():
                    title = f"Public Program - {venue.name}"
                else:
                    title = f"{title} - {venue.name}"
            
            # Extract date/time
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when'
            ])
            
            # Extract location
            location = self._extract_text(element, [
                '.location', '.venue', '.where', '.address'
            ]) or venue.name
            
            # Extract URL - use tour_url if available, otherwise extract from element
            url = tour_url  # Use the tour page URL as the primary URL
            if not url:
                url = self._extract_url(element)
                if url and not url.startswith('http'):
                    url = urljoin(venue.website_url, url)
            
            # Extract image
            image_url = self._extract_image(element, venue)
            
            # Parse dates
            start_date, end_date, start_time, end_time = self._parse_dates(date_text)
            
            # Determine event type based on venue type
            event_type = self._determine_event_type(venue.venue_type, title, description)
            
            event_data = {
                'title': title,
                'description': description or '',
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location,
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
                logger.info(f"⚠️ Filtered out: '{title}' - Reason: Quality check failed")
                logger.debug(f"   Has time: {event_data.get('start_time') is not None}, Has URL: {event_data.get('url') != event_data.get('source_url')}, Description length: {len(description)}")
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
    
    def _parse_dates(self, date_text):
        """Parse date and time from text"""
        if not date_text:
            return None, None, None, None
        
        # Simple date parsing (can be improved)
        today = date.today()
        
        # Look for common date patterns
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\w+)\s+(\d{1,2})',            # Month Day
        ]
        
        start_date = None
        end_date = None
        start_time = None
        end_time = None
        
        # For now, use today as default
        start_date = today
        end_date = today
        
        return start_date, end_date, start_time, end_time
    
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
            'tickets', 'information', 'about', 'overview', 'home'
        ]
        if title in generic_titles:
            return False
        
        # Very lenient validation - accept almost anything with a title
        # Only filter out if it's completely empty or just generic words
        if len(title) < 3:
            return False
        
        # Accept any event that has a title longer than 3 characters
        # Even TBD events are valid if they have location/details
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
