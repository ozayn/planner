#!/usr/bin/env python3
"""
Source Event Scraper
Scrapes events from event sources (websites, Instagram pages, etc.)
"""

import os
import sys
import requests
import logging
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Source, Event, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceEventScraper:
    """Scrapes events from various event sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.scraped_events = []
    
    def scrape_source_events(self, source_ids=None, city_id=None, event_type=None, time_range=None):
        """Scrape events from selected sources
        
        Args:
            source_ids: List of source IDs to scrape
            city_id: City ID to scrape sources from
            event_type: Type of events to scrape
            time_range: Time range for events
        """
        try:
            with app.app_context():
                # Get sources to scrape
                if source_ids:
                    sources = Source.query.filter(Source.id.in_(source_ids)).all()
                elif city_id:
                    sources = Source.query.filter_by(city_id=city_id).all()
                else:
                    sources = Source.query.limit(10).all()
                
                logger.info(f"Scraping events from {len(sources)} sources")
                
                # Track unique events to prevent duplicates
                unique_events = set()
                
                for source in sources:
                    try:
                        logger.info(f"Scraping events from: {source.name}")
                        
                        # Only scrape website sources for now
                        if source.source_type == 'website':
                            events = self._scrape_website_source(source)
                        elif source.source_type == 'instagram':
                            # Instagram scraping would require API or more complex methods
                            logger.info(f"Instagram scraping not yet implemented for {source.name}")
                            events = []
                        else:
                            logger.info(f"Source type '{source.source_type}' not yet supported for {source.name}")
                            events = []
                        
                        # Add unique events only with better deduplication
                        for event in events:
                            # Create a more comprehensive unique key
                            title_clean = event['title'].lower().strip()
                            date_key = event.get('start_time', '')[:10] if event.get('start_time') else ''
                            source_key = f"{source.name}_{source.id}"
                            event_key = f"{title_clean}_{date_key}_{source_key}"
                            
                            if event_key not in unique_events:
                                unique_events.add(event_key)
                                self.scraped_events.append(event)
                                logger.debug(f"✅ Added unique event: {event['title']}")
                            else:
                                logger.debug(f"⚠️ Skipped duplicate event: {event['title']}")
                        
                        # Rate limiting
                        import time
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error scraping {source.name}: {e}")
                        continue
                
                logger.info(f"Total unique events scraped from sources: {len(self.scraped_events)}")
                return self.scraped_events
                
        except Exception as e:
            logger.error(f"Error in scrape_source_events: {e}")
            return []
    
    def _scrape_website_source(self, source):
        """Scrape events from a website source"""
        events = []
        
        if not source.url:
            return events
        
        try:
            logger.info(f"Scraping website: {source.url}")
            response = self.session.get(source.url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract events based on common patterns
            events = self._extract_events_from_html(soup, source)
            
        except Exception as e:
            logger.error(f"Error scraping website {source.url}: {e}")
        
        return events
    
    def _extract_events_from_html(self, soup, source):
        """Extract events from HTML content"""
        events = []
        
        # Common selectors for events on tour/event websites
        event_selectors = [
            '.tour', '.tours', '.tour-item', '.tour-card',
            '.event', '.events', '.event-item', '.event-card',
            '.calendar-event', '.upcoming-event', '.scheduled-tour',
            '[class*="tour"]', '[class*="event"]', '[class*="schedule"]'
        ]
        
        for selector in event_selectors:
            event_elements = soup.select(selector)
            
            for element in event_elements:
                try:
                    event_data = self._parse_event_element(element, source)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.debug(f"Error parsing event element: {e}")
                    continue
        
        return events
    
    def _parse_event_element(self, element, source):
        """Parse individual event element"""
        try:
            # Extract title
            title = self._extract_text(element, [
                'h1', 'h2', 'h3', 'h4', '.title', '.tour-title', '.event-title', '.name'
            ])
            
            if not title:
                return None
            
            # Extract description
            description = self._extract_text(element, [
                '.description', '.summary', '.content', 'p', '.tour-description'
            ])
            
            # Extract date/time information
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when', '.schedule'
            ])
            
            # Extract location
            location = self._extract_text(element, [
                '.location', '.venue', '.where', '.address', '.meeting-point'
            ])
            
            # Extract URL
            url = self._extract_url(element, source.url)
            
            # Extract image
            image_url = self._extract_image(element, source)
            
            # Parse dates (use simple parsing for now)
            start_date, end_date, start_time, end_time = self._parse_dates(date_text)
            
            # Determine event type from source's event types or content
            event_type = self._determine_event_type(source, title, description)
            
            event_data = {
                'title': title,
                'description': description or '',
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location or '',
                'city_id': source.city_id,
                'event_type': event_type,
                'url': url,
                'image_url': image_url,
                'source': source.source_type,
                'source_url': source.url,
                'organizer': source.name,
                'social_media_platform': source.source_type if source.source_type != 'website' else None,
                'social_media_handle': source.handle if source.source_type != 'website' else None,
                'social_media_url': source.url if source.source_type != 'website' else None
            }
            
            # Validate event quality
            if not self._is_valid_event(event_data):
                logger.info(f"⚠️ Filtered out: '{title}' - Reason: Quality check failed")
                logger.debug(f"   Has time: {event_data.get('start_time') is not None}, Has URL: {event_data.get('url') != event_data.get('source_url')}, Description length: {len(description or '')}")
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
    
    def _extract_url(self, element, base_url):
        """Extract URL from event element"""
        link = element.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('/'):
                return urljoin(base_url, href)
            elif not href.startswith('http'):
                return urljoin(base_url, href)
            return href
        
        parent_link = element.find_parent('a', href=True)
        if parent_link:
            href = parent_link['href']
            if href.startswith('/'):
                return urljoin(base_url, href)
            elif not href.startswith('http'):
                return urljoin(base_url, href)
            return href
        
        return base_url
    
    def _extract_image(self, element, source):
        """Extract image from event element"""
        import re
        
        img = element.find('img')
        if img:
            img_src = (img.get('src') or 
                      img.get('data-src') or 
                      img.get('data-lazy-src') or
                      img.get('data-original'))
            
            if not img_src and img.get('srcset'):
                srcset = img.get('srcset')
                srcset_match = re.search(r'([^\s,]+\.(?:jpg|jpeg|png|gif|webp))', srcset, re.IGNORECASE)
                if srcset_match:
                    img_src = srcset_match.group(1)
            
            if img_src:
                if img_src.startswith('/'):
                    img_src = urljoin(source.url, img_src)
                elif not img_src.startswith('http'):
                    img_src = urljoin(source.url, img_src)
                
                if not (img_src.startswith('data:') or 'placeholder' in img_src.lower()):
                    return img_src
        
        return None
    
    def _parse_dates(self, date_text):
        """Parse date and time from text"""
        if not date_text:
            return None, None, None, None
        
        # For now, use today as default (can be enhanced with better date parsing)
        today = date.today()
        start_date = today
        end_date = today
        start_time = None
        end_time = None
        
        # Try to extract time from text
        import re
        time_pattern = r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?'
        time_matches = re.findall(time_pattern, date_text)
        
        if time_matches:
            hour, minute, period = time_matches[0]
            hour = int(hour)
            minute = int(minute)
            
            if period and period.upper() == 'PM' and hour != 12:
                hour += 12
            elif period and period.upper() == 'AM' and hour == 12:
                hour = 0
            
            from datetime import time
            start_time = time(hour, minute)
        
        return start_date, end_date, start_time, end_time
    
    def _determine_event_type(self, source, title, description):
        """Determine event type based on source and content"""
        content = f"{title} {description}".lower()
        
        # Check source's event types
        import json
        if source.event_types:
            try:
                event_types = json.loads(source.event_types) if isinstance(source.event_types, str) else source.event_types
                if event_types:
                    # Map source event types to our event types
                    if any(t in ['tours', 'walking_tours', 'historical_tours', 'tour'] for t in event_types):
                        return 'tour'
                    elif any(t in ['exhibitions', 'art_exhibitions', 'exhibition'] for t in event_types):
                        return 'exhibition'
                    elif any(t in ['festivals', 'festival'] for t in event_types):
                        return 'festival'
                    elif any(t in ['photowalks', 'photography'] for t in event_types):
                        return 'photowalk'
            except:
                pass
        
        # Fallback to content-based detection
        if 'tour' in content or 'walk' in content or 'guided' in content:
            return 'tour'
        elif 'exhibition' in content or 'exhibit' in content or 'gallery' in content:
            return 'exhibition'
        elif 'festival' in content:
            return 'festival'
        elif 'photowalk' in content or 'photo walk' in content:
            return 'photowalk'
        else:
            return 'tour'
    
    def _is_valid_event(self, event_data):
        """Validate event quality to filter out generic/incomplete events"""
        
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
