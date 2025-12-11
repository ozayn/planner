#!/usr/bin/env python3
"""
Eventbrite Event Scraper

This module handles scraping events from Eventbrite using their API.
It can extract organizer IDs from Eventbrite URLs and fetch events via the API.
Also includes web scraping capabilities to search for organizer pages.
"""

import os
import sys
import re
import requests
import logging
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup
import time as time_module

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from app import app, db, Venue, Event, City
except ImportError:
    # Allow importing without app context for testing
    pass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventbriteScraper:
    """Scrapes events from Eventbrite using their API"""
    
    def __init__(self, api_token: Optional[str] = None, use_public_token: bool = False):
        """
        Initialize Eventbrite scraper
        
        Args:
            api_token: Eventbrite Personal OAuth Token (Private Token). If not provided, will try to get from environment.
            use_public_token: If True, use public token instead (limited functionality, no auth needed)
        """
        # Priority: provided token > private token > public token
        if api_token:
            self.api_token = api_token
        elif use_public_token:
            self.api_token = os.getenv('EVENTBRITE_PUBLIC_TOKEN') or 'ZRQRSTL4V3Y5X2X5X2X5'
        else:
            self.api_token = os.getenv('EVENTBRITE_API_TOKEN') or os.getenv('EVENTBRITE_PRIVATE_TOKEN')
        
        self.api_base_url = 'https://www.eventbriteapi.com/v3'
        self.session = requests.Session()
        
        if self.api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            })
        else:
            logger.warning("⚠️  No Eventbrite API token found. Set EVENTBRITE_API_TOKEN or EVENTBRITE_PRIVATE_TOKEN in .env file to use API.")
            logger.warning("   You can still extract organizer IDs from URLs, but API calls will fail.")
    
    def extract_organizer_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract organizer ID from Eventbrite URL
        
        Args:
            url: Eventbrite organizer page URL (e.g., https://www.eventbrite.com/o/organizer-name-1234567890)
                 Can also be eventbrite.fi (e.g., https://www.eventbrite.fi/o/organizer-name-1234567890)
        
        Returns:
            Organizer ID as string, or None if not found
        """
        if not url or 'eventbrite' not in url.lower():
            return None
        
        # Pattern 1: Organizer page URL: eventbrite.com/o/organizer-name-1234567890 or eventbrite.fi/o/...
        # Handle both .com and .fi domains (and potentially other country-specific domains)
        match = re.search(r'eventbrite\.(?:com|fi|co\.uk|de|fr|es|it|nl|se|no|dk|fi)/o/[^/]+-(\d+)', url, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 2: Event page - try to get organizer from event
        if '/e/' in url:
            event_id = re.search(r'/e/(\d+)', url)
            if event_id and self.api_token:
                # Try to get organizer ID from event details via API
                try:
                    event_data = self.get_event_details(event_id.group(1))
                    if event_data and 'organizer_id' in event_data:
                        return event_data['organizer_id']
                except Exception as e:
                    logger.warning(f"Could not extract organizer ID from event: {e}")
        
        return None
    
    def get_organizer_events(self, organizer_id: str, status: str = 'live', 
                            start_date: Optional[date] = None, 
                            end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Get events for a specific organizer using Eventbrite API
        
        Args:
            organizer_id: Eventbrite organizer ID
            status: Event status filter ('live', 'draft', 'canceled', 'completed', 'started', 'ended')
            start_date: Filter events starting from this date
            end_date: Filter events ending before this date
        
        Returns:
            List of event dictionaries
        """
        if not self.api_token:
            logger.error("Cannot fetch events: No API token provided")
            return []
        
        events = []
        url = f'{self.api_base_url}/organizers/{organizer_id}/events/'
        
        params = {
            'status': status,
            'order_by': 'start_asc',
            'expand': 'venue,organizer,category,subcategory,format'
        }
        
        if start_date:
            params['start_date.range_start'] = start_date.isoformat() + 'T00:00:00Z'
        if end_date:
            params['start_date.range_end'] = end_date.isoformat() + 'T23:59:59Z'
        
        try:
            # Handle pagination
            while url:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                events.extend(data.get('events', []))
                
                # Check for next page
                pagination = data.get('pagination', {})
                if pagination.get('has_more_items', False):
                    url = pagination.get('continuation')
                    params = {}  # Continuation URL includes all params
                else:
                    url = None
                
                logger.info(f"Fetched {len(data.get('events', []))} events (total: {len(events)})")
            
            logger.info(f"✅ Successfully fetched {len(events)} events for organizer {organizer_id}")
            return events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching events from Eventbrite API: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return []
    
    def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific event
        
        Args:
            event_id: Eventbrite event ID
        
        Returns:
            Event details dictionary or None if error
        """
        if not self.api_token:
            logger.error("Cannot fetch event details: No API token provided")
            return None
        
        url = f'{self.api_base_url}/events/{event_id}/'
        params = {
            'expand': 'venue,organizer,format,category,subcategory'
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching event details: {e}")
            return None
    
    def convert_eventbrite_event_to_our_format(self, eb_event: Dict[str, Any], 
                                               venue: Optional[Venue] = None,
                                               city: Optional[City] = None) -> Dict[str, Any]:
        """
        Convert Eventbrite event format to our event format
        
        Args:
            eb_event: Eventbrite event dictionary from API
            venue: Venue object (optional, will try to match from event data)
            city: City object (optional, will try to match from event data)
        
        Returns:
            Event dictionary in our format
        """
        # Extract basic info
        name = eb_event.get('name', {}).get('text', 'Untitled Event')
        description = eb_event.get('description', {}).get('text', '')
        
        # Filter out non-English events (unless they have English subtitles/translation)
        # Check if event title/description indicates it's in a non-English language
        combined_text = f"{name} {description}".lower()
        
        # Check for English accessibility indicators (allow these events even if in another language)
        english_accessibility_indicators = [
            'english subtitles', 'with english subtitles', 'english translation',
            'with english translation', 'subtitled in english', 'english captions',
            'english audio', 'in english', 'conducted in english', 'presented in english'
        ]
        has_english_access = any(indicator in combined_text for indicator in english_accessibility_indicators)
        
        # Common non-English language indicators (phrases that explicitly indicate language)
        non_english_indicators = [
            # Italian
            'in italiano', 'in italian', 'italiano', 'in biblioteca in italiano',
            # Spanish
            'en español', 'en espanol', 'in spanish', 'español', 'espanol',
            # French
            'en français', 'en francais', 'in french', 'français', 'francais',
            # German
            'auf deutsch', 'in german', 'deutsch',
            # Portuguese
            'em português', 'em portugues', 'in portuguese', 'português', 'portugues',
            # Other languages
            'en català', 'en catala', 'catalan',  # Catalan
            'en euskera', 'basque',  # Basque
            'en galego', 'galician',  # Galician
            '中文', '日本語',  # Chinese, Japanese (but Korean is okay)
        ]
        
        # Skip if event is explicitly in a non-English language
        # Exception 1: Events with English subtitles/translation are okay
        # Exception 2: Korean events are okay (K-Cinema, K-Art, etc.)
        if any(indicator in combined_text for indicator in non_english_indicators):
            # Check if it has English accessibility (subtitles, translation, etc.)
            if has_english_access:
                logger.debug(f"Keeping non-English event with English subtitles: {name}")
                # Don't skip - event is accessible to English speakers
            else:
                # Check if it's Korean (we want Korean events)
                korean_indicators = ['k-cinema', 'k-art', 'korean', '한국', 'k-pop', 'hallyu', 'k-artsong']
                is_korean_event = any(indicator in combined_text for indicator in korean_indicators)
                
                if not is_korean_event:
                    logger.info(f"Skipping non-English event: {name} (detected non-English language indicator without English accessibility)")
                    return None
        
        # Extract dates/times
        start = eb_event.get('start', {})
        end = eb_event.get('end', {})
        
        start_datetime = None
        end_datetime = None
        if start.get('local'):
            try:
                start_datetime = datetime.fromisoformat(start['local'].replace('Z', '+00:00'))
            except:
                pass
        
        if end.get('local'):
            try:
                end_datetime = datetime.fromisoformat(end['local'].replace('Z', '+00:00'))
            except:
                pass
        
        # Extract venue info
        venue_data = eb_event.get('venue', {})
        venue_name = venue_data.get('name', '')
        venue_address = venue_data.get('address', {}).get('localized_area_display', '')
        
        # Extract URL
        event_url = eb_event.get('url', '')
        
        # Extract image
        image_url = None
        logo = eb_event.get('logo', {})
        if logo and logo.get('url'):
            image_url = logo['url']
        
        # Determine event type based on category, subcategory, format, name, and description
        # Priority: 1) Eventbrite categories, 2) Title/description keywords, 3) Default to 'event'
        event_type = None  # Will be set based on detection
        
        # Get category and subcategory (can be IDs or expanded objects)
        category_id = eb_event.get('category_id')
        subcategory_id = eb_event.get('subcategory_id')
        category_obj = eb_event.get('category', {})
        subcategory_obj = eb_event.get('subcategory', {})
        format_obj = eb_event.get('format', {})
        
        # Extract category/subcategory names if expanded objects are available
        category_name = category_obj.get('name', '').lower() if isinstance(category_obj, dict) else ''
        subcategory_name = subcategory_obj.get('name', '').lower() if isinstance(subcategory_obj, dict) else ''
        format_name = format_obj.get('name', '').lower() if isinstance(format_obj, dict) else ''
        
        # Check event name and description for keywords
        name_lower = name.lower()
        description_lower = description.lower()
        
        # STEP 1: Check Eventbrite categories first (most reliable)
        # Workshop/Class category
        workshop_category_ids = ['103']  # Classes & Workshops category ID
        workshop_subcategory_ids = ['5003', '5004']  # Classes & Workshops subcategories
        if (str(category_id) in workshop_category_ids or
            str(subcategory_id) in workshop_subcategory_ids or
            'workshop' in category_name or 'class' in category_name or
            'workshop' in subcategory_name or 'class' in subcategory_name):
            event_type = 'workshop'
        
        # Performance/Dance category
        elif (str(category_id) == '105' or  # Performing Arts category ID
              str(subcategory_id) in ['5005', '5006', '5007'] or  # Performing Arts subcategories (Dance, Music, Theater)
              'dance' in category_name or 'dance' in subcategory_name or
              'performing' in category_name or 'performing' in subcategory_name or
              'arts' in category_name or 'arts' in subcategory_name):
            event_type = 'performance'
        
        # Film/Movie category
        elif (str(category_id) == '104' or  # Film & Media category ID
              str(subcategory_id) in ['5001', '5002'] or  # Film & Media subcategories
              'film' in category_name or 'film' in subcategory_name):
            event_type = 'film'
        
        # STEP 2: If no category match, check title and description keywords
        if not event_type:
            all_text = f"{name_lower} {description_lower}"
            
            # Workshop/Class keywords
            workshop_keywords = ['workshop', 'class', 'workshop:', 'masterclass', 'training', 'seminar', 
                                'workshop at', 'hands-on', 'hands on', 'learning session']
            if any(keyword in all_text for keyword in workshop_keywords):
                event_type = 'workshop'
            
            # Performance/Dance keywords
            elif any(keyword in all_text for keyword in ['performance', 'dance', 'concert', 'soirée', 'soiree', 'recital', 'show', 
                               'ballet', 'theater', 'theatre', 'opera', 'symphony', 'orchestra', 'choreography']):
                event_type = 'performance'
            
            # Film/Movie keywords
            elif any(keyword in all_text for keyword in ['movie', 'film', 'cinema', 'screening', 'k-cinema', 'movie night', 'film screening', 
                        '영화', '상영', '시네마']):  # Korean words for movie/film/screening
                event_type = 'film'
            
            # Exhibition keywords
            elif 'exhibition' in all_text or 'exhibit' in all_text:
                event_type = 'exhibition'
            
            # Festival keywords
            elif 'festival' in all_text:
                event_type = 'festival'
            
            # Tour keywords
            elif 'tour' in all_text:
                event_type = 'tour'
        
        # STEP 3: Default to 'event' if nothing matched
        if not event_type:
            event_type = 'event'
        
        # Build our event format
        event_data = {
            'title': name,
            'description': description,
            'url': event_url,
            'image_url': image_url,
            'event_type': event_type,
            'source': 'eventbrite',
            'source_url': event_url,
            'is_registration_required': True,  # Eventbrite events typically require registration
            'registration_url': event_url,
            'start_location': venue_address or venue_name,
        }
        
        # Add dates/times
        if start_datetime:
            event_data['start_date'] = start_datetime.date()
            event_data['start_time'] = start_datetime.time()
        
        if end_datetime:
            event_data['end_date'] = end_datetime.date()
            event_data['end_time'] = end_datetime.time()
        
        # Filter out events that are already over
        # Check if event has ended (use end_datetime if available, otherwise start_datetime)
        event_end = end_datetime if end_datetime else start_datetime
        if event_end:
            # Get current time, handling timezone-aware and naive datetimes
            from datetime import timezone
            if event_end.tzinfo:
                # Event has timezone info, use UTC for comparison
                now = datetime.now(timezone.utc)
                # Convert event_end to UTC if it has timezone info
                event_end_utc = event_end.astimezone(timezone.utc)
            else:
                # Event is naive, use naive datetime
                now = datetime.now()
                event_end_utc = event_end
            
            if event_end_utc < now:
                # Event is in the past, return None to skip it
                logger.debug(f"Skipping past event: {name} (ended: {event_end_utc})")
                return None
        
        # Add venue/city info if available
        if venue:
            event_data['venue_id'] = venue.id
            event_data['city_id'] = venue.city_id
        elif city:
            event_data['city_id'] = city.id
        
        return event_data
    
    def scrape_venue_events(self, venue: Venue, time_range: str = 'this_month') -> List[Dict[str, Any]]:
        """
        Scrape events from Eventbrite for a venue
        
        Args:
            venue: Venue object with ticketing_url containing Eventbrite URL
            time_range: Time range for events ('today', 'this_week', 'this_month', 'all')
        
        Returns:
            List of event dictionaries in our format
        """
        if not venue.ticketing_url or 'eventbrite' not in venue.ticketing_url.lower():
            logger.debug(f"Venue {venue.name} does not have Eventbrite ticketing URL")
            return []
        
        # Extract organizer ID
        organizer_id = self.extract_organizer_id_from_url(venue.ticketing_url)
        if not organizer_id:
            logger.warning(f"Could not extract organizer ID from URL: {venue.ticketing_url}")
            logger.warning(f"  URL pattern check: {'eventbrite' in venue.ticketing_url.lower() if venue.ticketing_url else 'No URL'}")
            return []
        
        logger.info(f"Scraping Eventbrite events for {venue.name} (organizer ID: {organizer_id})")
        
        # Check if API token is available
        if not self.api_token:
            logger.error(f"Cannot fetch events for {venue.name}: No API token available")
            return []
        
        # Calculate date range
        today = date.today()
        start_date = None
        end_date = None
        
        if time_range == 'today':
            start_date = today
            end_date = today
        elif time_range == 'this_week':
            start_date = today
            end_date = today + timedelta(days=7)
        elif time_range == 'this_month':
            start_date = today
            end_date = today + timedelta(days=30)
        # 'all' means no date filter
        
        # Fetch events from API
        events = self.get_organizer_events(organizer_id, status='live', 
                                          start_date=start_date, end_date=end_date)
        
        # Convert to our format and filter out past events
        converted_events = []
        for eb_event in events:
            try:
                event_data = self.convert_eventbrite_event_to_our_format(
                    eb_event, venue=venue, city=venue.city if hasattr(venue, 'city') else None
                )
                # Skip if event is None (past event was filtered out)
                if event_data is not None:
                    converted_events.append(event_data)
            except Exception as e:
                logger.error(f"Error converting event {eb_event.get('id')}: {e}")
        
        logger.info(f"✅ Converted {len(converted_events)} events for {venue.name}")
        return converted_events
    
    def search_events_by_keyword(self, keyword: str, location: str = None, 
                                 max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for events by keyword using Eventbrite API.
        Note: This requires an API token and may have limited functionality.
        
        Args:
            keyword: Search keyword (venue name, event name, etc.)
            location: Optional location string (e.g., "Washington, DC")
            max_results: Maximum number of events to return
        
        Returns:
            List of event dictionaries with organizer information
        """
        if not self.api_token:
            logger.warning("Cannot search events: No API token")
            return []
        
        try:
            # Eventbrite events search endpoint
            # Note: The /events/search/ endpoint was deprecated, but we can try /events/ with filters
            events_url = f'{self.api_base_url}/events/search/'
            
            params = {
                'q': keyword,
                'sort_by': 'date',
                'status': 'live'
            }
            
            if location:
                params['location.address'] = location
            
            response = self.session.get(events_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])[:max_results]
                
                # Extract unique organizers from events
                organizers = {}
                for event in events:
                    organizer_id = event.get('organizer_id')
                    if organizer_id and organizer_id not in organizers:
                        organizers[organizer_id] = {
                            'id': organizer_id,
                            'name': event.get('organizer', {}).get('name', 'Unknown'),
                            'url': f"https://www.eventbrite.com/o/{organizer_id}",
                            'event_count': 1,
                            'verified': False,
                            'source': 'event_search'
                        }
                    elif organizer_id:
                        organizers[organizer_id]['event_count'] += 1
                
                return list(organizers.values())
            else:
                logger.warning(f"Event search returned status {response.status_code}")
                return []
                
        except Exception as e:
            logger.debug(f"Event search failed (may be deprecated): {e}")
            return []
    
    def search_organizers_by_venue_name(self, venue_name: str, city_name: str = None, 
                                       state: str = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Eventbrite website for organizer pages matching a venue name.
        
        Since Eventbrite API doesn't have a public search endpoint, this uses web scraping
        to search Eventbrite's website and extract organizer information.
        
        Args:
            venue_name: Name of the venue to search for
            city_name: Optional city name to narrow search
            state: Optional state name (e.g., "DC", "Virginia") to narrow search
            max_results: Maximum number of organizers to return
        
        Returns:
            List of organizer dictionaries with id, name, url, event_count, etc.
        """
        logger.info(f"Searching Eventbrite website for organizers matching: {venue_name}")
        if city_name:
            logger.info(f"  City: {city_name}")
        if state:
            logger.info(f"  State: {state}")
        
        organizers = {}
        
        try:
            # Build Eventbrite search URL with city and state
            search_query = venue_name
            if city_name:
                search_query += f" {city_name}"
            if state:
                search_query += f" {state}"
            
            # Eventbrite search URL format: /d/{location}/{category}/
            # Location can be: city-state or city--state (e.g., "washington-dc" or "dc--washington")
            if city_name and state:
                # Format: city-state (e.g., "washington-dc", "new-york-ny")
                city_slug = city_name.lower().replace(' ', '-')
                state_slug = state.lower().replace(' ', '-')
                # Handle DC specially - Eventbrite uses "dc--washington" format
                if state_slug in ['dc', 'district-of-columbia', 'washington-dc']:
                    location_slug = 'dc--washington'
                else:
                    location_slug = f"{city_slug}-{state_slug}"
            elif city_name:
                # Just city
                city_slug = city_name.lower().replace(' ', '-')
                # Default to DC format if it's Washington
                if city_slug == 'washington':
                    location_slug = 'dc--washington'
                else:
                    location_slug = city_slug
            else:
                location_slug = 'dc--washington'  # Default
            
            venue_slug = venue_name.replace(' ', '-').lower()
            search_url = f'https://www.eventbrite.com/d/{location_slug}/{venue_slug}/'
            
            logger.info(f"Searching Eventbrite: {search_url}")
            
            # Use cloudscraper or requests with proper headers to bypass bot protection
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper()
            except ImportError:
                scraper = requests.Session()
                scraper.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
            
            response = scraper.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find organizer links in the page
            # Eventbrite organizer links typically look like: /o/organizer-name-1234567890
            organizer_pattern = re.compile(r'/o/[^/]+-(\d+)')
            
            # Look for links to organizer pages
            organizer_links = soup.find_all('a', href=organizer_pattern)
            
            logger.info(f"Found {len(organizer_links)} organizer links on search page")
            
            # Extract unique organizer IDs and names
            for link in organizer_links[:20]:  # Limit to first 20 links
                href = link.get('href', '')
                match = organizer_pattern.search(href)
                if match:
                    organizer_id = match.group(1)
                    organizer_name = link.get_text(strip=True) or link.get('aria-label', '')
                    
                    if organizer_id and organizer_id not in organizers:
                        # Construct full URL
                        if href.startswith('http'):
                            organizer_url = href
                        else:
                            organizer_url = f"https://www.eventbrite.com{href}"
                        
                        organizers[organizer_id] = {
                            'id': organizer_id,
                            'name': organizer_name or 'Unknown',
                            'url': organizer_url,
                            'event_count': 0,
                            'verified': False,
                            'source': 'web_scrape'
                        }
            
            # Also look for organizer information in event cards
            # Eventbrite event cards often have organizer info
            event_cards = soup.find_all(['div', 'article'], class_=re.compile(r'event|card|listing', re.I))
            
            for card in event_cards[:30]:  # Check first 30 event cards
                # Look for organizer links within event cards
                org_link = card.find('a', href=organizer_pattern)
                if org_link:
                    href = org_link.get('href', '')
                    match = organizer_pattern.search(href)
                    if match:
                        organizer_id = match.group(1)
                        organizer_name = org_link.get_text(strip=True)
                        
                        if organizer_id and organizer_id not in organizers:
                            if href.startswith('http'):
                                organizer_url = href
                            else:
                                organizer_url = f"https://www.eventbrite.com{href}"
                            
                            organizers[organizer_id] = {
                                'id': organizer_id,
                                'name': organizer_name or 'Unknown',
                                'url': organizer_url,
                                'event_count': 0,
                                'verified': False,
                                'source': 'web_scrape'
                            }
            
            # Verify organizers via API and get event counts
            if self.api_token:
                logger.info(f"Verifying {len(organizers)} organizers via API...")
                for org_id, org_data in list(organizers.items()):
                    try:
                        # Get organizer details
                        org_url = f'{self.api_base_url}/organizers/{org_id}/'
                        api_response = self.session.get(org_url, params={'expand': 'description'}, timeout=5)
                        
                        if api_response.status_code == 200:
                            org_info = api_response.json()
                            org_data['name'] = org_info.get('name', org_data['name'])
                            org_data['description'] = org_info.get('description', {}).get('text', '')
                            org_data['verified'] = True
                            
                            # Get event count
                            events_url = f'{self.api_base_url}/organizers/{org_id}/events/'
                            events_response = self.session.get(events_url, params={'status': 'live'}, timeout=5)
                            if events_response.status_code == 200:
                                events_data = events_response.json()
                                org_data['event_count'] = len(events_data.get('events', []))
                        
                        # Rate limiting
                        time_module.sleep(0.2)
                    except Exception as e:
                        logger.debug(f"Could not verify organizer {org_id}: {e}")
                        continue
            
            # Sort by relevance (name match, then event count)
            organizer_list = list(organizers.values())
            organizer_list.sort(key=lambda x: (
                venue_name.lower() not in x['name'].lower(),  # Name match first
                -x['event_count'],  # More events = more relevant
                x['name']  # Alphabetical as tiebreaker
            ))
            
            logger.info(f"✅ Found {len(organizer_list)} organizers for {venue_name}")
            return organizer_list[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching Eventbrite website: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_organizer_by_id(self, organizer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organizer details by ID using Eventbrite API
        
        Args:
            organizer_id: Eventbrite organizer ID
        
        Returns:
            Organizer dictionary or None if not found
        """
        if not self.api_token:
            logger.warning("Cannot get organizer details: No API token")
            return None
        
        try:
            org_url = f'{self.api_base_url}/organizers/{organizer_id}/'
            response = self.session.get(org_url, params={'expand': 'description'}, timeout=10)
            response.raise_for_status()
            
            org_data = response.json()
            
            # Get event count
            events_url = f'{self.api_base_url}/organizers/{organizer_id}/events/'
            events_response = self.session.get(events_url, params={'status': 'live'}, timeout=10)
            event_count = 0
            if events_response.status_code == 200:
                events_data = events_response.json()
                event_count = len(events_data.get('events', []))
            
            # Construct organizer URL
            org_name_slug = org_data.get('name', '').lower().replace(' ', '-').replace("'", '').replace(',', '')
            organizer_url = f"https://www.eventbrite.com/o/{org_name_slug}-{organizer_id}"
            
            return {
                'id': organizer_id,
                'name': org_data.get('name', 'Unknown'),
                'description': org_data.get('description', {}).get('text', ''),
                'url': organizer_url,
                'event_count': event_count,
                'verified': True
            }
            
        except Exception as e:
            logger.error(f"Error getting organizer {organizer_id}: {e}")
            return None


def scrape_eventbrite_events_for_venue(venue_id: int, time_range: str = 'this_month') -> List[Dict[str, Any]]:
    """
    Convenience function to scrape Eventbrite events for a venue
    
    Args:
        venue_id: Venue ID
        time_range: Time range for events
    
    Returns:
        List of event dictionaries
    """
    with app.app_context():
        venue = Venue.query.get(venue_id)
        if not venue:
            logger.error(f"Venue {venue_id} not found")
            return []
        
        scraper = EventbriteScraper()
        return scraper.scrape_venue_events(venue, time_range=time_range)


def scrape_all_eventbrite_venues(city_id: Optional[int] = None, time_range: str = 'this_month') -> List[Dict[str, Any]]:
    """
    Scrape events from all venues with Eventbrite ticketing URLs
    
    Args:
        city_id: Optional city ID to filter venues
        time_range: Time range for events
    
    Returns:
        List of all event dictionaries
    """
    with app.app_context():
        # Get venues with Eventbrite URLs
        query = Venue.query.filter(Venue.ticketing_url.like('%eventbrite.com%'))
        if city_id:
            query = query.filter_by(city_id=city_id)
        
        venues = query.all()
        logger.info(f"Found {len(venues)} venues with Eventbrite URLs")
        
        scraper = EventbriteScraper()
        all_events = []
        
        for venue in venues:
            try:
                events = scraper.scrape_venue_events(venue, time_range=time_range)
                all_events.extend(events)
                logger.info(f"Scraped {len(events)} events from {venue.name}")
            except Exception as e:
                logger.error(f"Error scraping {venue.name}: {e}")
        
        logger.info(f"✅ Total: {len(all_events)} events scraped from {len(venues)} venues")
        return all_events


def scrape_dc_embassy_events(city_id: Optional[int] = None, time_range: str = 'this_month', 
                              search_missing: bool = True) -> List[Dict[str, Any]]:
    """
    Enhanced scraper for DC embassy events from Eventbrite.
    
    This function:
    1. Scrapes events from embassies that already have Eventbrite URLs
    2. Optionally searches for Eventbrite organizers for embassies without URLs
    3. Scrapes events from found organizers
    
    Args:
        city_id: Optional city ID (defaults to Washington DC if not provided)
        time_range: Time range for events ('today', 'this_week', 'this_month', 'all')
        search_missing: If True, search for Eventbrite organizers for embassies without URLs
    
    Returns:
        List of all event dictionaries
    """
    # Always use app context - even if we're in one, nesting is safe
    # This ensures db is properly bound to the app
    with app.app_context():
        return _scrape_dc_embassy_events_impl(city_id, time_range, search_missing)


def _scrape_dc_embassy_events_impl(city_id: Optional[int] = None, time_range: str = 'this_month', 
                                    search_missing: bool = True) -> List[Dict[str, Any]]:
    """Internal implementation of DC embassy events scraper"""
    # Use module-level db, City, Venue - they're bound to the current app context
    # The wrapper function ensures we're always in an app context when this is called
    
    # Get Washington DC city if not provided
    if not city_id:
        dc_city = City.query.filter(
            db.or_(
                City.name == 'Washington',
                City.name == 'Washington, DC',
                City.name == 'Washington DC'
            )
        ).filter_by(country='United States').first()
        
        if not dc_city:
            logger.error("Washington DC city not found in database")
            return []
        city_id = dc_city.id
        
        # Get all DC embassy venues
        embassy_venues = Venue.query.filter_by(
            city_id=city_id,
            venue_type='embassy'
        ).all()
        
        logger.info(f"Found {len(embassy_venues)} DC embassy venues")
        
        scraper = EventbriteScraper()
        all_events = []
        
        # Calculate date range
        today = date.today()
        start_date = None
        end_date = None
        
        if time_range == 'today':
            start_date = today
            end_date = today
        elif time_range == 'this_week':
            start_date = today
            end_date = today + timedelta(days=7)
        elif time_range == 'this_month':
            start_date = today
            end_date = today + timedelta(days=30)
        
        # Process embassies with Eventbrite URLs (handle both .com and .fi domains)
        venues_with_urls = [v for v in embassy_venues if v.ticketing_url and 'eventbrite' in v.ticketing_url.lower()]
        venues_without_urls = [v for v in embassy_venues if not v.ticketing_url or 'eventbrite' not in v.ticketing_url.lower()]
        
        logger.info(f"  - {len(venues_with_urls)} embassies with Eventbrite URLs")
        logger.info(f"  - {len(venues_without_urls)} embassies without Eventbrite URLs")
        
        # Scrape from embassies with URLs
        for venue in venues_with_urls:
            try:
                logger.info(f"Scraping events from {venue.name} (has Eventbrite URL: {venue.ticketing_url})")
                events = scraper.scrape_venue_events(venue, time_range=time_range)
                logger.info(f"  ✅ Found {len(events)} events from {venue.name}")
                if len(events) == 0:
                    logger.warning(f"  ⚠️  No events found for {venue.name} - organizer ID extraction or API call may have failed")
                all_events.extend(events)
            except Exception as e:
                logger.error(f"  ❌ Error scraping {venue.name}: {e}")
                import traceback
                logger.error(f"  Traceback: {traceback.format_exc()}")
                continue
        
        # Search and scrape from embassies without URLs (if enabled)
        if search_missing and venues_without_urls:
            logger.info(f"\n🔍 Searching for Eventbrite organizers for {len(venues_without_urls)} embassies without URLs...")
            
            dc_city_obj = City.query.get(city_id)
            city_name = dc_city_obj.name if dc_city_obj else 'Washington'
            state = 'DC' if 'Washington' in city_name else None
            
            for venue in venues_without_urls:
                try:
                    logger.info(f"\n🔍 Searching for Eventbrite organizer: {venue.name}")
                    
                    # Search for organizers matching this embassy
                    organizers = scraper.search_organizers_by_venue_name(
                        venue_name=venue.name,
                        city_name=city_name,
                        state=state,
                        max_results=3  # Limit to top 3 matches
                    )
                    
                    if not organizers:
                        logger.info(f"  ⚠️  No Eventbrite organizers found for {venue.name}")
                        continue
                    
                    # Try to find the best matching organizer
                    best_organizer = None
                    for org in organizers:
                        # Check if organizer name contains embassy name or vice versa
                        org_name_lower = org.get('name', '').lower()
                        venue_name_lower = venue.name.lower()
                        
                        # Simple matching: check if key words match
                        if any(word in org_name_lower for word in venue_name_lower.split() if len(word) > 3):
                            best_organizer = org
                            break
                    
                    # If no good match, use the first one
                    if not best_organizer and organizers:
                        best_organizer = organizers[0]
                    
                    if best_organizer:
                        organizer_id = best_organizer.get('id')
                        logger.info(f"  ✅ Found organizer: {best_organizer.get('name')} (ID: {organizer_id})")
                        
                        # Fetch events from this organizer
                        try:
                            events = scraper.get_organizer_events(
                                organizer_id=organizer_id,
                                status='live',
                                start_date=start_date,
                                end_date=end_date
                            )
                            
                            # Convert events to our format and filter out past events
                            for eb_event in events:
                                try:
                                    event_data = scraper.convert_eventbrite_event_to_our_format(
                                        eb_event,
                                        venue=venue,
                                        city=dc_city_obj
                                    )
                                    # Skip if event is None (past event was filtered out)
                                    if event_data is not None:
                                        all_events.append(event_data)
                                except Exception as e:
                                    logger.error(f"  ❌ Error converting event: {e}")
                            
                            logger.info(f"  ✅ Scraped {len(events)} events from {best_organizer.get('name')}")
                            
                        except Exception as e:
                            logger.error(f"  ❌ Error fetching events from organizer {organizer_id}: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"  ❌ Error searching for {venue.name}: {e}")
                    continue
        
        logger.info(f"\n✅ Total: {len(all_events)} events scraped from DC embassies")
        
        # Log summary of what was attempted
        if len(all_events) == 0:
            logger.warning("⚠️  No events found. Summary:")
            logger.warning(f"  - Attempted to scrape {len(venues_with_urls)} embassies with Eventbrite URLs")
            for v in venues_with_urls:
                organizer_id = scraper.extract_organizer_id_from_url(v.ticketing_url)
                logger.warning(f"    - {v.name}: URL={v.ticketing_url}, Organizer ID={organizer_id if organizer_id else 'FAILED'}")
        
        return all_events


def search_organizers(venue_name: str, city_name: str = None, state: str = None, 
                     max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Convenience function to search for Eventbrite organizers by venue name
    
    Args:
        venue_name: Name of the venue
        city_name: Optional city name
        state: Optional state name
        max_results: Maximum results to return
    
    Returns:
        List of organizer dictionaries
    """
    scraper = EventbriteScraper()
    return scraper.search_organizers_by_venue_name(venue_name, city_name, state, max_results)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape events from Eventbrite')
    parser.add_argument('--venue-id', type=int, help='Scrape events for specific venue ID')
    parser.add_argument('--city-id', type=int, help='Scrape events for all Eventbrite venues in city')
    parser.add_argument('--time-range', default='this_month', 
                       choices=['today', 'this_week', 'this_month', 'all'],
                       help='Time range for events')
    parser.add_argument('--test-url', help='Test extracting organizer ID from URL')
    parser.add_argument('--search', help='Search for organizers by venue name')
    parser.add_argument('--city', help='City name for search (optional)')
    parser.add_argument('--state', help='State name for search (optional, e.g., "DC", "Virginia")')
    parser.add_argument('--organizer-id', help='Get organizer details by ID')
    
    args = parser.parse_args()
    
    scraper = EventbriteScraper()
    
    if args.test_url:
        organizer_id = scraper.extract_organizer_id_from_url(args.test_url)
        print(f"Organizer ID: {organizer_id}")
    elif args.search:
        organizers = scraper.search_organizers_by_venue_name(
            args.search, 
            city_name=args.city,
            state=args.state,
            max_results=10
        )
        print(f"Found {len(organizers)} organizers:")
        for org in organizers:
            print(f"\n  - {org['name']}")
            print(f"    ID: {org['id']}")
            print(f"    URL: {org['url']}")
            print(f"    Events: {org.get('event_count', 0)}")
            print(f"    Verified: {org.get('verified', False)}")
    elif args.organizer_id:
        org = scraper.get_organizer_by_id(args.organizer_id)
        if org:
            print(f"Organizer: {org['name']}")
            print(f"  ID: {org['id']}")
            print(f"  URL: {org['url']}")
            print(f"  Events: {org['event_count']}")
            print(f"  Description: {org.get('description', '')[:100]}...")
        else:
            print("Organizer not found")
    elif args.venue_id:
        events = scrape_eventbrite_events_for_venue(args.venue_id, args.time_range)
        print(f"Found {len(events)} events")
        for event in events:
            print(f"  - {event['title']} ({event.get('start_date')})")
    elif args.city_id:
        events = scrape_all_eventbrite_venues(city_id=args.city_id, time_range=args.time_range)
        print(f"Found {len(events)} events")
    else:
        parser.print_help()
