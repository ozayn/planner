#!/usr/bin/env python3
"""
Generic Venue Event Scraper
A universal scraper that works for any venue/location by using common patterns
learned from specialized scrapers. This serves as a fallback when no specialized
scraper exists for a venue.

Key Features:
- Extracts events from common HTML patterns
- Handles various date/time formats
- Extracts titles, descriptions, images, locations
- Works with different event listing page structures
- Handles registration information
- Supports multiple event types (tours, exhibitions, talks, workshops, etc.)
"""

import os
import sys
import re
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class GenericVenueScraper:
    """
    Generic scraper that works for any venue by using common patterns.
    This is designed to work alongside specialized scrapers as a fallback.
    """
    
    def __init__(self):
        """Initialize the generic scraper with common patterns"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Disable SSL verification for sites with certificate issues
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configure retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            connect=3,
            read=3,
            redirect=3
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Common event selectors (learned from specialized scrapers)
        self.event_selectors = [
            '.event', '.events', '.event-item', '.event-card', '.event-list-item',
            '.calendar-event', '.upcoming-event', '.program', '.program-item',
            '.tour', '.tours', '.guided-tour', '.walking-tour',
            '.exhibition', '.exhibitions', '.exhibition-item',
            '.workshop', '.workshops', '.class', '.classes',
            '.talk', '.talks', '.lecture', '.lectures',
            '[class*="event"]', '[class*="program"]', '[class*="tour"]',
            '[class*="exhibition"]', '[data-event]', '[data-event-id]',
            'article.event', 'article.program', 'li.event', 'li.program'
        ]
        
        # Common date/time patterns
        self.date_patterns = [
            # Full dates with time
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?',  # "December 5, 2025 | 11:30 am–12:00 pm"
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # Date ranges
            r'(\w+)\s+(\d{1,2})\s*[–-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23 - August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*[–-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 - August 23, 2026"
            # Standard formats
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "December 5, 2025"
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # "5 December 2025"
        ]
        
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am–12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*-\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am - 12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s+to\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am to 12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([AP]M)\s*[–-]\s*(\d{1,2}):(\d{2})\s*([AP]M)',  # "11:30 AM–12:00 PM"
            r'(\d{1,2}):(\d{2})\s*([AP]M)',  # "11:30 AM"
            r'(\d{1,2}):(\d{2})',  # "11:30"
        ]
    
    def scrape_venue_events(self, venue_url: str, venue_name: str = None, 
                           event_type: str = None, time_range: str = 'this_month') -> List[Dict]:
        """
        Main method to scrape events from any venue URL.
        
        Args:
            venue_url: The venue's website URL
            venue_name: Optional venue name for context
            event_type: Optional filter for event type
            time_range: Time range filter ('today', 'this_week', 'this_month')
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        try:
            logger.info(f"🔍 Generic scraper: Starting scrape for {venue_url}")
            
            # Try to find event listing pages
            event_pages = self._discover_event_pages(venue_url)
            
            # Scrape each event page
            for page_url in event_pages:
                page_events = self._scrape_event_page(page_url, venue_name, event_type, time_range)
                events.extend(page_events)
            
            # Also scrape the main page
            main_events = self._scrape_event_page(venue_url, venue_name, event_type, time_range)
            events.extend(main_events)
            
            # Deduplicate
            events = self._deduplicate_events(events)
            
            logger.info(f"✅ Generic scraper: Found {len(events)} unique events")
            return events
            
        except Exception as e:
            logger.error(f"❌ Error in generic scraper for {venue_url}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _discover_event_pages(self, base_url: str) -> List[str]:
        """Discover event listing pages from the main page"""
        event_pages = []
        
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for links to event pages
            event_keywords = ['events', 'calendar', 'programs', 'exhibitions', 'tours', 'schedule']
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Check if link text or URL contains event keywords
                if any(keyword in href.lower() or keyword in text for keyword in event_keywords):
                    full_url = urljoin(base_url, href)
                    if full_url not in event_pages:
                        event_pages.append(full_url)
            
            logger.info(f"📄 Discovered {len(event_pages)} potential event pages")
            
        except Exception as e:
            logger.debug(f"Error discovering event pages: {e}")
        
        return event_pages[:5]  # Limit to 5 pages
    
    def _scrape_event_page(self, url: str, venue_name: str = None, 
                          event_type: str = None, time_range: str = 'this_month') -> List[Dict]:
        """Scrape events from a single page"""
        events = []
        
        try:
            # Try regular requests first
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                html_content = response.text
            except RequestException as e:
                # If 403 or other error, try cloudscraper
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
                    if CLOUDSCRAPER_AVAILABLE:
                        logger.info(f"⚠️  403 error, trying cloudscraper for {url}")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url, timeout=10, verify=False)
                        html_content = response.text
                    else:
                        return events
                else:
                    return events
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Try JSON-LD first (structured data)
            json_ld_events = self._extract_json_ld_events(soup, url)
            events.extend(json_ld_events)
            
            # Extract events from HTML
            html_events = self._extract_events_from_html(soup, url, venue_name, event_type, time_range)
            events.extend(html_events)
            
        except Exception as e:
            logger.debug(f"Error scraping page {url}: {e}")
        
        return events
    
    def _extract_json_ld_events(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract events from JSON-LD structured data"""
        events = []
        
        try:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    script_content = script.string if script.string else script.get_text()
                    data = json.loads(script_content)
                    
                    # Handle both single objects and arrays
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        if item.get('@type') in ['Event', 'ExhibitionEvent', 'TheaterEvent']:
                            event = self._parse_json_ld_event(item, base_url)
                            if event:
                                events.append(event)
                                
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Error parsing JSON-LD: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extracting JSON-LD: {e}")
        
        return events
    
    def _parse_json_ld_event(self, data: Dict, base_url: str) -> Optional[Dict]:
        """Parse a single JSON-LD event"""
        try:
            title = data.get('name', '')
            description = data.get('description', '')
            
            # Extract dates
            start_date = None
            end_date = None
            start_time = None
            end_time = None
            
            if 'startDate' in data:
                start_datetime = self._parse_iso_datetime(data['startDate'])
                if start_datetime:
                    start_date = start_datetime.date()
                    start_time = start_datetime.time()
            
            if 'endDate' in data:
                end_datetime = self._parse_iso_datetime(data['endDate'])
                if end_datetime:
                    end_date = end_datetime.date()
                    end_time = end_datetime.time()
            
            # Extract location
            location = None
            if 'location' in data:
                loc = data['location']
                if isinstance(loc, dict):
                    location = loc.get('name', '')
                    if not location and 'address' in loc:
                        addr = loc['address']
                        if isinstance(addr, dict):
                            location = addr.get('streetAddress', '')
                elif isinstance(loc, str):
                    location = loc
            
            # Extract image
            image_url = None
            if 'image' in data:
                img = data['image']
                if isinstance(img, str):
                    image_url = img
                elif isinstance(img, list) and len(img) > 0:
                    image_url = img[0] if isinstance(img[0], str) else img[0].get('url', '')
                elif isinstance(img, dict):
                    image_url = img.get('url', '')
            
            # Extract URL
            url = data.get('url', base_url)
            if url and not url.startswith('http'):
                url = urljoin(base_url, url)
            
            # Determine event type
            event_type = self._determine_event_type(title, description, data.get('@type', ''))
            
            return {
                'title': title,
                'description': description,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location,
                'url': url,
                'image_url': image_url,
                'event_type': event_type
            }
            
        except Exception as e:
            logger.debug(f"Error parsing JSON-LD event: {e}")
            return None
    
    def _extract_events_from_html(self, soup: BeautifulSoup, base_url: str, 
                                  venue_name: str = None, event_type: str = None, 
                                  time_range: str = 'this_month') -> List[Dict]:
        """Extract events from HTML using common selectors"""
        events = []
        
        # Try each selector
        for selector in self.event_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        event = self._parse_event_element(element, base_url, venue_name, event_type, time_range)
                        if event:
                            events.append(event)
                            
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        return events
    
    def _parse_event_element(self, element, base_url: str, venue_name: str = None,
                            event_type: str = None, time_range: str = 'this_month') -> Optional[Dict]:
        """Parse a single event element from HTML"""
        try:
            # Extract title
            title = self._extract_text(element, [
                'h1', 'h2', 'h3', 'h4', '.title', '.event-title', '.name',
                '[itemprop="name"]', 'meta[property="og:title"]'
            ])
            
            if not title or len(title) < 3:
                return None
            
            # Extract description
            description = self._extract_text(element, [
                '.description', '.summary', '.content', 'p', '.event-description',
                '[itemprop="description"]', 'meta[property="og:description"]'
            ])
            
            # Extract date/time
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when', '.schedule',
                '[itemprop="startDate"]', '[itemprop="endDate"]', 'time[datetime]'
            ])
            
            start_date, end_date, start_time, end_time = self._parse_dates_and_times(
                date_text, element, base_url
            )
            
            # Extract location
            location = self._extract_text(element, [
                '.location', '.venue', '.where', '.address', '.meeting-point',
                '[itemprop="location"]', '[itemprop="address"]'
            ])
            
            # Extract URL
            url = self._extract_url(element, base_url)
            
            # Extract image
            image_url = self._extract_image(element, base_url)
            
            # Determine event type
            if not event_type:
                event_type = self._determine_event_type(title, description)
            
            # Filter by time range
            if start_date and not self._is_in_time_range(start_date, time_range):
                return None
            
            return {
                'title': title.strip(),
                'description': description.strip() if description else '',
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location.strip() if location else None,
                'url': url,
                'image_url': image_url,
                'event_type': event_type
            }
            
        except Exception as e:
            logger.debug(f"Error parsing event element: {e}")
            return None
    
    def _extract_text(self, element, selectors: List[str]) -> Optional[str]:
        """Extract text using multiple selector strategies"""
        # Try CSS selectors first
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    text = found.get_text(strip=True)
                    if text:
                        return text
            except:
                continue
        
        # Try meta tags
        if 'meta[' in str(selectors):
            for selector in selectors:
                if 'meta[' in selector:
                    try:
                        meta = element.select_one(selector)
                        if meta:
                            content = meta.get('content', '')
                            if content:
                                return content
                    except:
                        continue
        
        # Fallback: get text from element itself
        text = element.get_text(strip=True)
        if text and len(text) > 3:
            return text
        
        return None
    
    def _extract_url(self, element, base_url: str) -> Optional[str]:
        """Extract event URL"""
        # Try link
        link = element.find('a', href=True)
        if link:
            return urljoin(base_url, link['href'])
        
        # Try data attributes
        for attr in ['data-url', 'data-href', 'data-link']:
            if element.get(attr):
                return urljoin(base_url, element[attr])
        
        return base_url
    
    def _extract_image(self, element, base_url: str) -> Optional[str]:
        """Extract event image URL"""
        # Try img tag
        img = element.find('img')
        if img:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                return urljoin(base_url, src)
        
        # Try meta tags
        og_image = element.select_one('meta[property="og:image"]')
        if og_image:
            return og_image.get('content', '')
        
        return None
    
    def _parse_dates_and_times(self, date_text: str, element, base_url: str) -> Tuple:
        """Parse dates and times from text and HTML attributes"""
        start_date = None
        end_date = None
        start_time = None
        end_time = None
        today = date.today()
        
        # Try time[datetime] attribute first
        time_elem = element.find('time', datetime=True)
        if time_elem:
            datetime_str = time_elem.get('datetime', '')
            parsed = self._parse_iso_datetime(datetime_str)
            if parsed:
                start_date = parsed.date()
                start_time = parsed.time()
                # Try to get end time from text content
                time_text = time_elem.get_text(strip=True)
                if time_text:
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', time_text, re.IGNORECASE)
                    if time_match:
                        _, _, end_time = self._parse_time_match(time_match)
        
        # Parse from text if we don't have dates yet
        if date_text and not start_date:
            # Try date patterns
            for pattern in self.date_patterns:
                match = re.search(pattern, date_text, re.IGNORECASE)
                if match:
                    parsed_start, parsed_end = self._parse_date_match(match, date_text)
                    if parsed_start:
                        start_date = parsed_start
                        end_date = parsed_end
                        break
        
        # Parse times from text if we don't have them yet
        if date_text and not start_time:
            # Try time patterns
            for pattern in self.time_patterns:
                match = re.search(pattern, date_text, re.IGNORECASE)
                if match:
                    parsed_start, parsed_end = self._parse_time_match(match)
                    if parsed_start:
                        start_time = parsed_start
                        end_time = parsed_end
                        break
        
        # If we have a start time but no end time, assume 1-hour duration
        if start_time and not end_time:
            start_datetime = datetime.combine(today, start_time)
            end_datetime = start_datetime + timedelta(hours=1)
            end_time = end_datetime.time()
        
        return start_date, end_date, start_time, end_time
    
    def _parse_iso_datetime(self, iso_string: str) -> Optional[datetime]:
        """Parse ISO 8601 datetime string"""
        try:
            # Remove timezone info for simplicity
            iso_string = re.sub(r'[+-]\d{2}:\d{2}$', '', iso_string)
            iso_string = re.sub(r'Z$', '', iso_string)
            
            # Try different formats
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(iso_string[:len(fmt) + 5], fmt)
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error parsing ISO datetime {iso_string}: {e}")
        
        return None
    
    def _parse_date_match(self, match: re.Match, text: str) -> Tuple[Optional[date], Optional[date]]:
        """Parse date from regex match"""
        try:
            groups = match.groups()
            today = date.today()
            
            # Pattern: "May 23 - August 23, 2026" (year only at end)
            if len(groups) >= 5 and groups[4]:  # Has year at end
                try:
                    month1 = self._month_name_to_num(groups[0])
                    day1 = int(groups[1])
                    month2 = self._month_name_to_num(groups[2])
                    day2 = int(groups[3])
                    year = int(groups[4])
                    
                    start_date = date(year, month1, day1)
                    end_date = date(year, month2, day2)
                    return start_date, end_date
                except:
                    pass
            
            # Pattern: "May 23, 2026 - August 23, 2026" (year after each date)
            if len(groups) >= 6:
                try:
                    month1 = self._month_name_to_num(groups[0])
                    day1 = int(groups[1])
                    year1 = int(groups[2])
                    month2 = self._month_name_to_num(groups[3])
                    day2 = int(groups[4])
                    year2 = int(groups[5])
                    
                    start_date = date(year1, month1, day1)
                    end_date = date(year2, month2, day2)
                    return start_date, end_date
                except:
                    pass
            
            # Pattern: "December 5, 2025" (single date)
            if len(groups) >= 3:
                try:
                    month = self._month_name_to_num(groups[1] if len(groups) > 1 else groups[0])
                    day = int(groups[2] if len(groups) > 2 else groups[1])
                    year = int(groups[3] if len(groups) > 3 else groups[2])
                    
                    start_date = date(year, month, day)
                    return start_date, None
                except:
                    pass
            
            # Pattern: MM/DD/YYYY
            if len(groups) >= 3:
                try:
                    month = int(groups[0])
                    day = int(groups[1])
                    year = int(groups[2])
                    start_date = date(year, month, day)
                    return start_date, None
                except:
                    pass
            
            # Pattern: YYYY-MM-DD
            if len(groups) >= 3:
                try:
                    year = int(groups[0])
                    month = int(groups[1])
                    day = int(groups[2])
                    start_date = date(year, month, day)
                    return start_date, None
                except:
                    pass
            
        except Exception as e:
            logger.debug(f"Error parsing date match: {e}")
        
        return None, None
    
    def _month_name_to_num(self, month_name: str) -> int:
        """Convert month name to number"""
        months = {
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
        return months.get(month_name.lower(), 1)
    
    def _parse_time_match(self, match: re.Match) -> Tuple[Optional[time], Optional[time]]:
        """Parse time from regex match"""
        try:
            groups = match.groups()
            
            # Pattern: "11:30 am–12:00 pm"
            if len(groups) >= 6:
                start_hour = int(groups[0])
                start_min = int(groups[1])
                start_ampm = groups[2].lower()
                
                if start_ampm == 'p' and start_hour != 12:
                    start_hour += 12
                elif start_ampm == 'a' and start_hour == 12:
                    start_hour = 0
                
                start_time = time(start_hour, start_min)
                
                # End time
                if len(groups) >= 6:
                    end_hour = int(groups[3])
                    end_min = int(groups[4])
                    end_ampm = groups[5].lower()
                    
                    if end_ampm == 'p' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'a' and end_hour == 12:
                        end_hour = 0
                    
                    end_time = time(end_hour, end_min)
                    return start_time, end_time
                
                return start_time, None
            
        except Exception as e:
            logger.debug(f"Error parsing time match: {e}")
        
        return None, None
    
    def _determine_event_type(self, title: str, description: str = '', json_type: str = '') -> str:
        """Determine event type from title, description, and JSON-LD type"""
        content = f"{title} {description}".lower()
        
        if 'exhibition' in content or 'exhibit' in content or 'ExhibitionEvent' in json_type:
            return 'exhibition'
        elif 'tour' in content or 'guided' in content:
            return 'tour'
        elif 'workshop' in content or 'class' in content:
            return 'workshop'
        elif 'talk' in content or 'lecture' in content or 'discussion' in content:
            return 'talk'
        elif 'performance' in content or 'concert' in content or 'show' in content:
            return 'festival'
        elif 'festival' in content:
            return 'festival'
        else:
            return 'event'  # Generic fallback
    
    def _is_in_time_range(self, event_date: date, time_range: str) -> bool:
        """Check if event date is within the specified time range"""
        today = date.today()
        
        if time_range == 'today':
            return event_date == today
        elif time_range == 'this_week':
            week_end = today + timedelta(days=7)
            return today <= event_date <= week_end
        elif time_range == 'this_month':
            month_end = today + timedelta(days=30)
            return today <= event_date <= month_end
        else:
            return True  # No filter
    
    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        """Remove duplicate events based on title and date"""
        seen = set()
        unique_events = []
        
        for event in events:
            key = (event.get('title', '').lower().strip(), event.get('start_date'))
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events



