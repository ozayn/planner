#!/usr/bin/env python3
"""
Custom scraper for National Gallery of Art Finding Awe series
Scrapes all events from the Finding Awe series page
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time
from bs4 import BeautifulSoup
import cloudscraper

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City, Source

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FINDING_AWE_URL = 'https://www.nga.gov/calendar/finding-awe'
VENUE_NAME = "National Gallery of Art"
CITY_NAME = "Washington, DC"

def scrape_all_finding_awe_events():
    """Scrape all Finding Awe events from the series page"""
    events = []
    
    try:
        # Create a cloudscraper session to bypass bot detection
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info(f"🔍 Scraping Finding Awe series from: {FINDING_AWE_URL}")
        response = scraper.get(FINDING_AWE_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all event links on the page
        # NGA typically uses specific patterns for event listings
        event_links = []
        
        # Look for links that contain "finding-awe" in the URL (but not the main series page)
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Match finding-awe URLs but exclude the main series page
            if 'finding-awe' in href.lower() and href != FINDING_AWE_URL and '/finding-awe/' in href.lower():
                # Exclude the main series page URL
                if not href.lower().endswith('/finding-awe') and not href.lower().endswith('/finding-awe/'):
                    full_url = href if href.startswith('http') else f"https://www.nga.gov{href}"
                    # Only add if it's a specific event page (has a title/name in the URL)
                    if full_url != FINDING_AWE_URL and full_url not in event_links:
                        event_links.append(full_url)
        
        # Also look for event cards/listings that might have links
        event_cards = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'event|calendar|program|listing', re.I))
        for card in event_cards:
            card_links = card.find_all('a', href=True)
            for link in card_links:
                href = link.get('href', '')
                if 'finding-awe' in href.lower() and '/finding-awe/' in href.lower():
                    if not href.lower().endswith('/finding-awe') and not href.lower().endswith('/finding-awe/'):
                        full_url = href if href.startswith('http') else f"https://www.nga.gov{href}"
                        if full_url != FINDING_AWE_URL and full_url not in event_links:
                            event_links.append(full_url)
        
        logger.info(f"   Found {len(event_links)} unique Finding Awe event links")
        
        # Extract events from links
        for event_url in event_links:
            try:
                logger.info(f"   📄 Scraping: {event_url}")
                event_data = scrape_individual_event(event_url, scraper)
                if event_data:
                    events.append(event_data)
                    logger.info(f"   ✅ Successfully scraped: {event_data.get('title', 'Unknown')}")
            except Exception as e:
                logger.warning(f"   ⚠️  Error scraping event from {event_url}: {e}")
                continue
        
        logger.info(f"✅ Scraped {len(events)} Finding Awe events")
        return events
        
    except Exception as e:
        logger.error(f"Error scraping Finding Awe series: {e}")
        import traceback
        traceback.print_exc()
        return []


def scrape_individual_event(event_url, scraper=None):
    """Scrape a single Finding Awe event from its detail page"""
    if not scraper:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
    
    try:
        logger.info(f"   📄 Scraping event: {event_url}")
        response = scraper.get(event_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title
        title = None
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        if not title or 'finding awe' not in title.lower():
            # Try to find title in meta tags
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
        
        if not title:
            logger.warning(f"   ⚠️  No title found for {event_url}")
            return None
        
        # Clean title: remove venue name suffix
        from scripts.utils import clean_event_title
        title = clean_event_title(title)
        
        # Extract description - improved extraction
        description = None
        
        # First try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
            if len(description) > 50:
                logger.debug(f"   Found meta description: {description[:100]}...")
        
        # Try Open Graph description
        if not description or len(description) < 100:
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                og_desc_text = og_desc.get('content').strip()
                if len(og_desc_text) > len(description or ''):
                    description = og_desc_text
                    logger.debug(f"   Found OG description: {description[:100]}...")
        
        # Look for main content area with event description
        if not description or len(description) < 100:
            # Look for main content paragraphs
            main_content = soup.find(['article', 'main']) or soup.find('div', class_=re.compile(r'main|content|event', re.I))
            if main_content:
                # Find all paragraphs that form the description
                paragraphs = main_content.find_all('p')
                description_parts = []
                for p in paragraphs:
                    text = p.get_text(separator=' ', strip=True)
                    # Skip very short paragraphs, navigation, or metadata
                    if len(text) > 50 and not any(skip in text.lower() for skip in ['register', 'ticket', 'buy now', 'click here', 'learn more', 'follow us', 'social media']):
                        description_parts.append(text)
                
                if description_parts:
                    # Combine paragraphs that form a coherent description
                    combined = ' '.join(description_parts)
                    combined = ' '.join(combined.split())  # Clean up whitespace
                    if len(combined) > len(description or ''):
                        description = combined[:2000]  # Increased limit for better descriptions
                        logger.debug(f"   Found content description: {description[:100]}...")
        
        # Fallback to description elements
        if not description or len(description) < 50:
            desc_elem = soup.find(['div', 'p'], class_=re.compile(r'description|content|summary', re.I))
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
                description = ' '.join(description.split())[:1000]
                logger.debug(f"   Found description element: {description[:100]}...")
        
        # Extract date and time
        # PRIORITY: Page text > URL parameter (page text is more accurate)
        event_date = None
        start_time = None
        end_time = None
        
        # First, try to extract date/time from page text (most accurate)
        # Look for date patterns - handle both full and abbreviated month names
        date_patterns = [
            # Full month names: "Saturday, February 7, 2026"
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            # Abbreviated month names: "Saturday, Feb 7, 2026" or "Feb 7, 2026"
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
            # Date without day name: "February 7, 2026" or "Feb 7, 2026"
            r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
            # MM/DD/YYYY format
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            # YYYY-MM-DD format
            r'(\d{4})-(\d{2})-(\d{2})',
        ]
        
        month_map_full = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        month_map_abbrev = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 4:  # Day name, month name, day, year
                        month_name = match.group(2).lower().rstrip('.')
                        day = int(match.group(3))
                        year = int(match.group(4))
                        month = month_map_full.get(month_name) or month_map_abbrev.get(month_name[:3])
                        if month:
                            event_date = date(year, month, day)
                            logger.info(f"   📅 Parsed date: {event_date}")
                            break
                    elif len(groups) == 3:
                        # Check if first group is a month name
                        first_group = groups[0].lower().rstrip('.')
                        if first_group in month_map_full or first_group[:3] in month_map_abbrev:
                            # Month name format: "Feb 7, 2026" or "February 7, 2026"
                            month_name = first_group
                            day = int(groups[1])
                            year = int(groups[2])
                            month = month_map_full.get(month_name) or month_map_abbrev.get(month_name[:3])
                            if month:
                                event_date = date(year, month, day)
                                logger.info(f"   📅 Parsed date: {event_date}")
                                break
                        else:
                            # Numeric format: MM/DD/YYYY or YYYY-MM-DD
                            if '/' in match.group(0):
                                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                                event_date = date(year, month, day)
                                logger.info(f"   📅 Parsed date: {event_date}")
                                break
                            else:
                                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                                event_date = date(year, month, day)
                                logger.info(f"   📅 Parsed date: {event_date}")
                                break
                except (ValueError, IndexError, AttributeError) as e:
                    logger.debug(f"   ⚠️  Error parsing date: {e}")
                    continue
        
        # Extract time from page text (always try this first - it's more accurate)
        # Extract time - handle various formats
        time_patterns = [
            # "2:15 p.m. – 4:00 p.m." or "2:15 p.m. - 4:00 p.m."
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # "2:15pm – 4:00pm"
            r'(\d{1,2}):(\d{2})([ap])m\s*[–-]\s*(\d{1,2}):(\d{2})([ap])m',
            # "2:15 PM – 4:00 PM"
            r'(\d{1,2}):(\d{2})\s*([AP])M\s*[–-]\s*(\d{1,2}):(\d{2})\s*([AP])M',
        ]
        
        for time_pattern in time_patterns:
            time_match = re.search(time_pattern, page_text, re.IGNORECASE)
            if time_match:
                try:
                    start_hour = int(time_match.group(1))
                    start_min = int(time_match.group(2))
                    start_ampm = time_match.group(3).upper()
                    end_hour = int(time_match.group(4))
                    end_min = int(time_match.group(5))
                    end_ampm = time_match.group(6).upper()
                    
                    if start_ampm == 'P' and start_hour != 12:
                        start_hour += 12
                    elif start_ampm == 'A' and start_hour == 12:
                        start_hour = 0
                    
                    if end_ampm == 'P' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'A' and end_hour == 12:
                        end_hour = 0
                    
                    start_time = time(start_hour, start_min)
                    end_time = time(end_hour, end_min)
                    logger.info(f"   ⏰ Parsed time from page: {start_time} - {end_time}")
                    break
                except (ValueError, IndexError) as e:
                    logger.debug(f"   ⚠️  Error parsing time: {e}")
                    continue
        
        # If we still don't have times but have a date, try to extract from URL evd parameter as fallback
        # (in case the page parsing failed but URL has the info)
        if event_date and (not start_time or not end_time):
            import urllib.parse
            parsed_url = urllib.parse.urlparse(event_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'evd' in query_params and query_params['evd']:
                evd_value = query_params['evd'][0]
                if len(evd_value) >= 12:  # YYYYMMDDHHMM format
                    try:
                        hour = int(evd_value[8:10])
                        minute = int(evd_value[10:12])
                        if not start_time:
                            start_time = time(hour, minute)
                        if not end_time:
                            # Default end time: 90 minutes later (standard Finding Awe duration)
                            end_hour = hour
                            end_minute = minute + 90
                            if end_minute >= 60:
                                end_hour += end_minute // 60
                                end_minute = end_minute % 60
                            if end_hour >= 24:
                                end_hour = end_hour % 24
                            end_time = time(end_hour, end_minute)
                            logger.info(f"   ⏰ Extracted time from URL evd parameter: {start_time} - {end_time}")
                    except (ValueError, IndexError) as e:
                        logger.debug(f"   ⚠️  Could not parse time from evd parameter: {e}")
        
        # Detect if event is online/virtual
        is_online = False
        online_indicators = [
            r'\bonline\b',
            r'\bvirtual\b',
            r'\bzoom\b',
            r'\bwebinar\b',
            r'\bstreaming\b',
            r'\blive stream\b',
            r'\bwebcast\b',
            r'\bdigital\b',
        ]
        
        page_text_lower = page_text.lower()
        for indicator in online_indicators:
            if re.search(indicator, page_text_lower):
                is_online = True
                logger.info(f"   🌐 Detected online event")
                break
        
        # Extract location - get more detailed location information
        location = None
        if is_online:
            location = "Online"
        else:
            # Look for detailed location information
            # Try to find location in structured format first (e.g., "East Building Upper Level, Gallery 415-A")
            location_patterns = [
                # Full location: "East Building Upper Level, Gallery 415-A"
                r'(East Building|West Building)[^.\n]*(?:Upper Level|Lower Level|Main Floor|Level \d+)[^.\n]*(?:Gallery\s+\d+[-\w]*)',
                # NGA special locations: "East Building Mezzanine Terrace"
                r'(East Building|West Building)[^.\n]*(?:Mezzanine Terrace|Terrace|Mezzanine|Atrium|Lobby|Auditorium|Theater|Theatre)[^.\n]*',
                # Building with gallery: "East Building, Gallery 415-A"
                r'(East Building|West Building)[^.\n]*(?:Gallery\s+\d+[-\w]*)',
                # Just building and level: "East Building Upper Level"
                r'(East Building|West Building)[^.\n]*(?:Upper Level|Lower Level|Main Floor|Level \d+)',
                # Gallery with building context
                r'Gallery\s+\d+[-\w]*(?:\s*[^.\n]{0,50})?',
                # Fallback to just building
                r'(West Building|East Building|Main Floor)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    location = match.group(0).strip()
                    # Clean up the location text
                    location = ' '.join(location.split())  # Normalize whitespace
                    # Remove extra punctuation
                    location = location.rstrip('.,;:')
                    logger.info(f"   📍 Found location: {location}")
                    break
            
            # If still no location, try to find it in HTML structure
            if not location:
                # Look for location in list items or specific elements
                location_elements = soup.find_all(['div', 'span', 'p', 'li'], string=re.compile(r'East Building|West Building|Gallery \d+|Mezzanine|Terrace', re.I))
                for elem in location_elements:
                    text = elem.get_text(strip=True)
                    # Check if it contains building or location keywords
                    if any(keyword in text for keyword in ['Building', 'Gallery', 'Mezzanine', 'Terrace', 'Atrium', 'Lobby']):
                        # Clean up the text - remove date/time patterns
                        text = re.sub(r'\s+\d{1,2}:\d{2}\s*[ap]\.?m\.?.*$', '', text, flags=re.IGNORECASE)
                        text = re.sub(r'\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*$', '', text, flags=re.IGNORECASE)
                        text = text.split('|')[0].strip()  # Stop at pipe if present
                        if len(text) > 5 and len(text) < 100:  # Reasonable length
                            location = text
                            logger.info(f"   📍 Found location in HTML: {location}")
                            break
        
        # Extract image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '').strip()
        
        # Extract registration information
        is_registration_required = False
        registration_opens_date = None
        registration_opens_time = None
        registration_url = None
        registration_info = None
        
        # Look for registration indicators - check both page text and HTML elements
        registration_keywords = [
            r'\bregistration\s+required\b',
            r'\bregister\s+to\s+attend\b',
            r'\bregistration\s+opens\b',
            r'\bregister\s+now\b',
            r'\badvance\s+registration\b',
            r'\bpre-registration\b',
            r'\bwe encourage you to register\b',
            r'\bplease register\b',
        ]
        
        page_text_lower = page_text.lower()
        for keyword in registration_keywords:
            if re.search(keyword, page_text_lower):
                is_registration_required = True
                logger.info(f"   📝 Detected registration required: {keyword}")
                break
        
        # Also check for "Registration Required" text in visible elements
        if not is_registration_required:
            reg_required_elements = soup.find_all(string=re.compile(r'registration\s+required', re.I))
            if reg_required_elements:
                is_registration_required = True
                logger.info(f"   📝 Detected 'Registration Required' text in page")
        
        # Look for registration URL - be very strict and avoid false positives
        excluded_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 
            'pinterest.com', 'linkedin.com', 'tiktok.com', 'snapchat.com',
            'reddit.com', 'tumblr.com', 'flickr.com', 'vimeo.com'
        ]
        
        excluded_patterns = ['social', 'share', 'follow', 'like', 'subscribe', 'newsletter', 'email']
        
        # Look for links where BOTH the href AND text indicate registration
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()
            href_lower = href.lower()
            
            # Skip if it's a social media or excluded domain
            if any(domain in href_lower for domain in excluded_domains):
                continue
            
            # Skip if it contains excluded patterns
            if any(pattern in href_lower for pattern in excluded_patterns):
                continue
            
            # The href MUST contain registration-related keywords
            href_has_registration = any(word in href_lower for word in [
                'register', 'registration', 'rsvp', 'ticket', 'book', 'reserve', 
                'signup', 'sign-up', 'eventbrite', 'ticketmaster', 'event'
            ])
            
            if href_has_registration:
                registration_url = href
                if not registration_url.startswith('http'):
                    from urllib.parse import urljoin
                    registration_url = urljoin(event_url, registration_url)
                logger.info(f"   🔗 Found registration URL: {registration_url}")
                break
        
        # Look for registration opens date/time
        registration_opens_patterns = [
            r'registration\s+opens\s+(?:on\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            r'registration\s+opens\s+(\d{1,2})/(\d{1,2})/(\d{4})',
            r'registration\s+opens\s+(\d{4})-(\d{2})-(\d{2})',
        ]
        
        for pattern in registration_opens_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 3:  # Month name, day, year
                        month_name = match.group(1)
                        day = int(match.group(2))
                        year = int(match.group(3))
                        month_map = {
                            'january': 1, 'february': 2, 'march': 3, 'april': 4,
                            'may': 5, 'june': 6, 'july': 7, 'august': 8,
                            'september': 9, 'october': 10, 'november': 11, 'december': 12
                        }
                        month = month_map.get(month_name.lower())
                        if month:
                            registration_opens_date = date(year, month, day)
                            break
                    elif len(match.groups()) == 3:  # MM/DD/YYYY or YYYY-MM-DD
                        if '/' in match.group(0):
                            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                            registration_opens_date = date(year, month, day)
                        else:
                            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                            registration_opens_date = date(year, month, day)
                        break
                except (ValueError, IndexError):
                    continue
        
        # Extract registration info text
        registration_info_patterns = [
            r'registration\s+(?:opens|begins|starts)\s+[^.\n]+',
            r'registration\s+required[^.\n]*',
            r'advance\s+registration[^.\n]*',
        ]
        for pattern in registration_info_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                registration_info = match.group(0).strip()
                break
        
        event_data = {
            'title': title,
            'description': description,
            'start_date': event_date.isoformat() if event_date else None,
            'end_date': event_date.isoformat() if event_date else None,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'location': location,
            'url': event_url,
            'image_url': image_url,
            'event_type': 'talk',
            'is_online': is_online,
            'is_registration_required': is_registration_required,
            'registration_opens_date': registration_opens_date.isoformat() if registration_opens_date else None,
            'registration_opens_time': registration_opens_time.isoformat() if registration_opens_time else None,
            'registration_url': registration_url,
            'registration_info': registration_info,
        }
        
        logger.info(f"   ✅ Extracted: {title}")
        return event_data
        
    except Exception as e:
        logger.error(f"   ❌ Error scraping event {event_url}: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_event_from_element(element):
    """Extract event data from an element on the main page"""
    # This would parse event cards/listings on the main Finding Awe page
    # Implementation depends on the actual HTML structure
    return None


def create_events_in_database(events):
    """Create scraped events in the database"""
    with app.app_context():
        # Find venue and city
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like(f'%{VENUE_NAME.lower()}%')
        ).first()
        
        if not venue:
            logger.error(f"❌ Venue '{VENUE_NAME}' not found")
            return 0
        
        city = City.query.filter(
            db.func.lower(City.name).like(f'%{CITY_NAME.lower().split(",")[0]}%')
        ).first()
        
        if not city:
            logger.error(f"❌ City '{CITY_NAME}' not found")
            return 0
        
        created_count = 0
        for event_data in events:
            try:
                # Validate required fields
                title = event_data.get('title', '').strip()
                if not title:
                    logger.warning(f"   ⚠️  Skipping event: missing title")
                    continue
                
                # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                from scripts.utils import is_category_heading
                if is_category_heading(title):
                    logger.debug(f"   ⏭️ Skipping category heading: '{title}'")
                    continue
                
                if not event_data.get('start_date'):
                    logger.warning(f"   ⚠️  Skipping event '{title}': missing start_date")
                    continue
                
                # Parse date
                try:
                    event_date = datetime.fromisoformat(event_data['start_date']).date()
                except (ValueError, TypeError) as e:
                    logger.warning(f"   ⚠️  Skipping event '{event_data.get('title')}': invalid date format: {e}")
                    continue
                
                # Check if event already exists
                existing = Event.query.filter_by(
                    url=event_data.get('url'),
                    start_date=event_date,
                    city_id=city.id
                ).first()
                
                if existing:
                    logger.info(f"   ⚠️  Event already exists: {event_data['title']}")
                    continue
                
                # Parse times
                start_time_obj = None
                end_time_obj = None
                if event_data.get('start_time'):
                    try:
                        # time.isoformat() returns "HH:MM:SS", so use time.fromisoformat() directly
                        start_time_obj = time.fromisoformat(event_data['start_time'])
                        logger.debug(f"   ✅ Parsed start_time: {start_time_obj}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"   ⚠️  Could not parse start_time '{event_data.get('start_time')}': {e}")
                
                if event_data.get('end_time'):
                    try:
                        # time.isoformat() returns "HH:MM:SS", so use time.fromisoformat() directly
                        end_time_obj = time.fromisoformat(event_data['end_time'])
                        logger.debug(f"   ✅ Parsed end_time: {end_time_obj}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"   ⚠️  Could not parse end_time '{event_data.get('end_time')}': {e}")
                
                # Parse registration opens date/time
                registration_opens_date_obj = None
                registration_opens_time_obj = None
                if event_data.get('registration_opens_date'):
                    try:
                        registration_opens_date_obj = datetime.fromisoformat(event_data['registration_opens_date']).date()
                    except (ValueError, TypeError):
                        logger.debug(f"   Could not parse registration_opens_date: {event_data.get('registration_opens_date')}")
                
                if event_data.get('registration_opens_time'):
                    try:
                        registration_opens_time_obj = datetime.fromisoformat(event_data['registration_opens_time']).time()
                    except (ValueError, TypeError):
                        logger.debug(f"   Could not parse registration_opens_time: {event_data.get('registration_opens_time')}")
                
                # Determine venue_id - online events don't need a venue
                is_online = event_data.get('is_online', False)
                venue_id_for_event = None if is_online else venue.id
                
                # Ensure location is set for online events
                location = event_data.get('location')
                if is_online and not location:
                    location = "Online"
                elif not location:
                    location = None
                
                # Create event
                event = Event(
                    title=event_data['title'],
                    description=event_data.get('description'),
                    start_date=event_date,
                    end_date=event_date,
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    start_location=location,
                    venue_id=venue_id_for_event,
                    city_id=city.id,
                    event_type=event_data.get('event_type', 'talk'),
                    url=event_data.get('url'),
                    image_url=event_data.get('image_url'),
                    source='website',
                    source_url=FINDING_AWE_URL,
                    is_selected=False,
                    is_online=is_online,
                    is_registration_required=event_data.get('is_registration_required', False),
                    registration_opens_date=registration_opens_date_obj,
                    registration_opens_time=registration_opens_time_obj,
                    registration_url=event_data.get('registration_url'),
                    registration_info=event_data.get('registration_info'),
                )
                
                db.session.add(event)
                
                # Commit each event individually to avoid partial failures
                try:
                    db.session.commit()
                    created_count += 1
                    logger.info(f"   ✅ Created: {event_data['title']}")
                except Exception as commit_error:
                    db.session.rollback()
                    logger.error(f"   ❌ Database error creating event '{event_data.get('title')}': {commit_error}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue
                
            except Exception as e:
                logger.error(f"   ❌ Error creating event {event_data.get('title')}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                db.session.rollback()
                continue
        
        logger.info(f"✅ Created {created_count} new events in database")
        return created_count


if __name__ == '__main__':
    print("🔍 Scraping all Finding Awe events...")
    events = scrape_all_finding_awe_events()
    
    if events:
        print(f"\n📋 Found {len(events)} events:")
        for event in events:
            print(f"   - {event['title']}")
            if event.get('start_date'):
                print(f"     Date: {event['start_date']}")
            if event.get('start_time'):
                print(f"     Time: {event['start_time']}")
        
        print(f"\n💾 Creating events in database...")
        created = create_events_in_database(events)
        print(f"✅ Created {created} new events")
    else:
        print("❌ No events found")
