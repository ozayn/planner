#!/usr/bin/env python3
"""
Comprehensive Scraper for Smithsonian American Art Museum (SAAM)
Scrapes exhibitions, tours, talks, workshops, and other events from SAAM and Renwick Gallery
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import cloudscraper

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VENUE_NAME = "Smithsonian American Art Museum"
RENWICK_VENUE_NAME = "Renwick Gallery"
CITY_NAME = "Washington"

# SAAM URLs
SAAM_BASE_URL = 'https://americanart.si.edu'
SAAM_EXHIBITIONS_URL = 'https://americanart.si.edu/exhibitions'
SAAM_EVENTS_URL = 'https://americanart.si.edu/search/events?content_type=event'
SAAM_TOURS_URL = 'https://americanart.si.edu/visit/tours'


def create_scraper():
    """Create a cloudscraper session to bypass bot detection"""
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
    
    return scraper


def parse_date_range(date_string: str) -> Optional[Dict[str, date]]:
    """
    Parse date range string like "November 25, 2025–July 12, 2026"
    Returns dict with 'start_date' and 'end_date' or None if parsing fails
    """
    if not date_string:
        return None
    
    # Clean up the date string
    date_string = date_string.strip()
    
    # Handle different separators
    separators = ['–', '-', '—', 'to', 'through']
    for sep in separators:
        if sep in date_string:
            parts = date_string.split(sep, 1)
            if len(parts) == 2:
                start_str = parts[0].strip()
                end_str = parts[1].strip()
                
                try:
                    start_date = parse_single_date(start_str)
                    end_date = parse_single_date(end_str)
                    
                    if start_date and end_date:
                        return {
                            'start_date': start_date,
                            'end_date': end_date
                        }
                except Exception as e:
                    logger.debug(f"Error parsing date range '{date_string}': {e}")
                    continue
    
    # Try to parse as single date
    single_date = parse_single_date(date_string)
    if single_date:
        return {
            'start_date': single_date,
            'end_date': single_date
        }
    
    return None


def parse_single_date(date_string: str) -> Optional[date]:
    """Parse a single date string in various formats"""
    if not date_string:
        return None
    
    date_string = date_string.strip()
    
    # Try common date formats
    date_formats = [
        '%B %d, %Y',      # November 25, 2025
        '%b %d, %Y',      # Nov 25, 2025
        '%d %B %Y',       # 25 November 2025
        '%d %b %Y',       # 25 Nov 2025
        '%Y-%m-%d',       # 2025-11-25
        '%m/%d/%Y',       # 11/25/2025
        '%d/%m/%Y',       # 25/11/2025
        '%B %Y',          # November 2025
        '%b %Y',          # Nov 2025
        '%Y',             # 2025
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_string, fmt).date()
            return parsed
        except ValueError:
            continue
    
    # Try regex patterns for more flexible parsing
    # Match "Month Day, Year" or "Day Month Year"
    month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    day_pattern = r'(\d{1,2})'
    year_pattern = r'(\d{4})'
    
    # Pattern: "Month Day, Year"
    pattern1 = rf'{month_pattern}\s+{day_pattern},?\s+{year_pattern}'
    match = re.search(pattern1, date_string, re.IGNORECASE)
    if match:
        try:
            month_str = match.group(1)
            day = int(match.group(2))
            year = int(match.group(3))
            
            # Convert month name to number
            month_map = {
                'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
                'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
                'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
                'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            month = month_map.get(month_str.lower())
            if month:
                return date(year, month, day)
        except (ValueError, IndexError):
            pass
    
    logger.debug(f"Could not parse date: {date_string}")
    return None


def scrape_saam_exhibitions(scraper=None) -> List[Dict]:
    """
    Scrape all exhibitions from SAAM exhibitions page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🔍 Scraping SAAM exhibitions from: {SAAM_EXHIBITIONS_URL}")
        response = scraper.get(SAAM_EXHIBITIONS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all exhibition items
        # Based on the page structure, exhibitions are likely in sections or divs
        # Let's look for common patterns
        
        # Try to find exhibition cards/items
        exhibition_items = []
        
        # Look for links to individual exhibition pages
        exhibition_links = soup.find_all('a', href=re.compile(r'/exhibitions/'))
        
        # Also look for exhibition titles and info in the page
        # The page might have sections for Current, Upcoming, Past exhibitions
        
        # Find all potential exhibition containers
        # Look for divs/articles with exhibition-related classes
        exhibition_containers = soup.find_all(['div', 'article', 'section'], 
                                             class_=re.compile(r'exhibition|event|program', re.I))
        
        # Also check for any divs with exhibition data
        all_divs = soup.find_all('div', class_=True)
        for div in all_divs:
            classes = ' '.join(div.get('class', []))
            if any(keyword in classes.lower() for keyword in ['exhibition', 'event', 'program', 'card', 'item']):
                if div not in exhibition_containers:
                    exhibition_containers.append(div)
        
        logger.info(f"   Found {len(exhibition_links)} exhibition links and {len(exhibition_containers)} exhibition containers")
        
        # Process exhibition links
        processed_urls = set()
        for link in exhibition_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Build full URL
            if href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(SAAM_BASE_URL, href)
            
            # Skip if we've already processed this URL
            if full_url in processed_urls:
                continue
            
            # Skip main exhibitions page
            if full_url == SAAM_EXHIBITIONS_URL or full_url == SAAM_EXHIBITIONS_URL + '/':
                continue
            
            # Only process if it's a specific exhibition page
            if '/exhibitions/' in full_url and full_url.count('/') >= 4:
                processed_urls.add(full_url)
                try:
                    exhibition_data = scrape_exhibition_detail(scraper, full_url)
                    if exhibition_data:
                        events.append(exhibition_data)
                except Exception as e:
                    logger.warning(f"   ⚠️ Error scraping exhibition {full_url}: {e}")
        
        # If we didn't find many exhibitions via links, try parsing the main page directly
        if len(events) < 3:
            logger.info("   📄 Parsing exhibitions directly from main page...")
            page_events = parse_exhibitions_from_page(soup)
            # Merge with existing events, avoiding duplicates
            for page_event in page_events:
                # Check if we already have this exhibition
                if not any(e.get('title') == page_event.get('title') for e in events):
                    events.append(page_event)
        
        logger.info(f"   ✅ Found {len(events)} exhibitions")
        
    except Exception as e:
        logger.error(f"❌ Error scraping SAAM exhibitions: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def determine_venue_from_soup(soup: BeautifulSoup, default_venue: str = VENUE_NAME) -> str:
    """
    Determine which venue (SAAM or Renwick Gallery) an exhibition belongs to
    by looking for venue links in the HTML. This function looks for links
    to /visit/renwick or /visit/saam in the provided soup context.
    
    The key is to find the venue link that's closest to the exhibition content,
    not just any venue link on the page (which might be in navigation).
    """
    location = default_venue
    
    # Look for explicit venue links - these are the most reliable indicator
    # We want to find links that are in the exhibition content area, not navigation
    # Look for links with specific patterns that indicate they're part of exhibition info
    
    # Find all venue links
    all_renwick_links = soup.find_all('a', href=re.compile(r'/visit/renwick'))
    all_saam_links = soup.find_all('a', href=re.compile(r'/visit/saam'))
    
    # Filter to find links that are likely part of exhibition info (not navigation)
    # Exhibition venue links are usually near date information or in specific containers
    renwick_links = []
    saam_links = []
    
    for link in all_renwick_links:
        # Check if this link is near date information (indicates it's exhibition-specific)
        parent = link.parent
        if parent:
            parent_text = parent.get_text()
            # If there's a date pattern nearby, it's likely exhibition-specific
            if re.search(r'\d{4}', parent_text):
                renwick_links.append(link)
            # Also check if it's in a heading or specific container
            elif parent.find_parent(['div', 'section'], class_=re.compile(r'exhibition|event|card', re.I)):
                renwick_links.append(link)
    
    for link in all_saam_links:
        parent = link.parent
        if parent:
            parent_text = parent.get_text()
            if re.search(r'\d{4}', parent_text):
                saam_links.append(link)
            elif parent.find_parent(['div', 'section'], class_=re.compile(r'exhibition|event|card', re.I)):
                saam_links.append(link)
    
    # If we found exhibition-specific links, use those
    if renwick_links or saam_links:
        if len(renwick_links) > len(saam_links):
            location = RENWICK_VENUE_NAME
            logger.debug(f"   📍 Found {len(renwick_links)} Renwick Gallery link(s) in exhibition context")
        elif len(saam_links) > 0:
            location = VENUE_NAME
            logger.debug(f"   📍 Found {len(saam_links)} SAAM link(s) in exhibition context")
    # Fallback: if no exhibition-specific links, check all links (but prefer the one with more)
    elif all_renwick_links or all_saam_links:
        if len(all_renwick_links) > len(all_saam_links):
            location = RENWICK_VENUE_NAME
            logger.debug(f"   📍 Found {len(all_renwick_links)} Renwick Gallery link(s) (fallback)")
        elif len(all_saam_links) > 0:
            location = VENUE_NAME
            logger.debug(f"   📍 Found {len(all_saam_links)} SAAM link(s) (fallback)")
    
    # Final fallback: check page text for venue mentions
    if location == default_venue:
        page_text = soup.get_text().lower()
        # Look for "Renwick Gallery" specifically near venue indicators
        if re.search(r'renwick\s+gallery', page_text, re.I):
            venue_patterns = [
                r'at\s+renwick\s+gallery',
                r'renwick\s+gallery[^,]*,\s*\d{4}',
                r'renwick\s+gallery[^.]*\.',
            ]
            for pattern in venue_patterns:
                if re.search(pattern, page_text, re.I):
                    location = RENWICK_VENUE_NAME
                    logger.debug("   📍 Found Renwick Gallery in text context")
                    break
    
    return location


def scrape_exhibition_detail(scraper, url: str) -> Optional[Dict]:
    """Scrape details from an individual exhibition page"""
    try:
        logger.debug(f"   📄 Scraping exhibition page: {url}")
        response = scraper.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = None
        title_elem = soup.find('h1') or soup.find('h2', class_=re.compile(r'title', re.I))
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        if not title:
            # Try meta title
            meta_title = soup.find('title')
            if meta_title:
                title = meta_title.get_text(strip=True)
        
        if not title:
            logger.debug(f"   ⚠️ Could not find title for {url}")
            return None
        
        # Extract description
        description = None
        desc_elem = soup.find('div', class_=re.compile(r'description|summary|intro', re.I))
        if desc_elem:
            description = desc_elem.get_text(strip=True)
        
        if not description:
            # Try first paragraph
            first_p = soup.find('p')
            if first_p:
                description = first_p.get_text(strip=True)
        
        # Extract date range
        date_range = None
        date_elem = soup.find(text=re.compile(r'\d{4}'))
        if date_elem:
            # Look for date patterns in the text
            date_text = date_elem.parent.get_text() if hasattr(date_elem, 'parent') else str(date_elem)
            date_range = parse_date_range(date_text)
        
        # Also look for date in specific elements
        if not date_range:
            date_containers = soup.find_all(['div', 'span', 'p'], 
                                           class_=re.compile(r'date|time|duration', re.I))
            for container in date_containers:
                date_text = container.get_text(strip=True)
                date_range = parse_date_range(date_text)
                if date_range:
                    break
        
        # Determine location - look for venue link in "Visiting Information" section
        location = VENUE_NAME  # Default
        
        # Find "Visiting Information" heading and look for venue link after it
        visiting_heading = None
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
            heading_text = heading.get_text(strip=True).lower()
            if 'visiting' in heading_text and 'information' in heading_text:
                visiting_heading = heading
                break
        
        if visiting_heading:
            # Find all elements after this heading
            for elem in visiting_heading.find_all_next(['div', 'section', 'a']):
                # Look for venue links
                if elem.name == 'a' and elem.get('href'):
                    href = elem.get('href', '')
                    if '/visit/renwick' in href:
                        location = RENWICK_VENUE_NAME
                        logger.debug(f"   📍 Found Renwick link after Visiting Information")
                        break
                    elif '/visit/saam' in href:
                        location = VENUE_NAME
                        logger.debug(f"   📍 Found SAAM link after Visiting Information")
                        break
                # Also check for venue links in divs/sections
                elif elem.name in ['div', 'section']:
                    venue_link = elem.find('a', href=re.compile(r'/visit/(renwick|saam)'))
                    if venue_link:
                        href = venue_link.get('href', '')
                        if 'renwick' in href:
                            location = RENWICK_VENUE_NAME
                        else:
                            location = VENUE_NAME
                        logger.debug(f"   📍 Found venue link in container after Visiting Information: {location}")
                        break
                # Stop after checking a reasonable number of elements
                if location != VENUE_NAME:
                    break
        
        # Final fallback: use the general function (but exclude navigation)
        if location == VENUE_NAME:
            # Try to exclude navigation by looking for links not in nav/menu areas
            main_content = soup.find('main') or soup.find('article') or soup
            location = determine_venue_from_soup(main_content)
        
        # Extract image
        image_url = None
        img_elem = soup.find('img', class_=re.compile(r'hero|feature|main|exhibition', re.I))
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src')
            if img_src:
                image_url = urljoin(SAAM_BASE_URL, img_src)
        
        # Build event dictionary
        event = {
            'title': title,
            'description': description or f"Exhibition at {location}",
            'event_type': 'exhibition',
            'source_url': url,
            'organizer': location,
            'social_media_platform': 'website',
            'social_media_url': url,
        }
        
        if date_range:
            event['start_date'] = date_range['start_date']
            event['end_date'] = date_range['end_date']
        
        if image_url:
            event['image_url'] = image_url
        
        return event
        
    except Exception as e:
        logger.warning(f"   ⚠️ Error scraping exhibition detail {url}: {e}")
        return None


def parse_exhibitions_from_page(soup: BeautifulSoup) -> List[Dict]:
    """Parse exhibitions directly from the main exhibitions page"""
    events = []
    
    try:
        # Look for exhibition cards/containers
        # Each exhibition is likely in a card or container div
        # Look for links to individual exhibitions first
        exhibition_links = soup.find_all('a', href=re.compile(r'/exhibitions/[^/]+$'))
        
        processed_titles = set()
        
        for link in exhibition_links:
            href = link.get('href', '')
            if not href or href in ['/exhibitions', '/exhibitions/']:
                continue
            
            # Get the exhibition container (parent element that contains the full exhibition info)
            container = link
            # Go up the DOM tree to find the exhibition container
            for _ in range(5):  # Check up to 5 levels up
                container = container.parent
                if not container:
                    break
                
                # Check if this container has venue information
                container_text = container.get_text()
                if len(container_text) > 100:  # Likely a full exhibition container
                    break
            
            if not container:
                continue
            
            # Extract title from link or nearby heading
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                # Try to find a heading in the container
                heading = container.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                if heading:
                    title = heading.get_text(strip=True)
            
            if not title or len(title) < 5:
                continue
            
            # Skip if we've already processed this title
            if title in processed_titles:
                continue
            processed_titles.add(title)
            
            # Skip section headings
            if title.lower() in ['current', 'upcoming', 'past', 'traveling', 'exhibitions', 'exhibition']:
                continue
            
            # Extract date range from container
            date_range = None
            container_text = container.get_text()
            
            # Look for date patterns in the container text
            date_range = parse_date_range(container_text)
            
            # Also look for date in specific elements within container
            if not date_range:
                date_containers = container.find_all(['div', 'span', 'p'], 
                                                    class_=re.compile(r'date|time|duration', re.I))
                for date_container in date_containers:
                    date_text = date_container.get_text(strip=True)
                    date_range = parse_date_range(date_text)
                    if date_range:
                        break
            
            # Determine location from this specific container
            # First, try to find venue link that's near the date information
            location = VENUE_NAME  # Default
            
            # Look for venue links in the same area as dates
            if date_range:
                # Find the element that contains the date
                date_elem = None
                for elem in container.find_all(['div', 'span', 'p']):
                    if date_range['start_date'].strftime('%Y') in elem.get_text():
                        date_elem = elem
                        break
                
                if date_elem:
                    # Look for venue link near the date element (within 3 levels)
                    for _ in range(3):
                        venue_link = date_elem.find('a', href=re.compile(r'/visit/(renwick|saam)'))
                        if venue_link:
                            if 'renwick' in venue_link.get('href', ''):
                                location = RENWICK_VENUE_NAME
                            else:
                                location = VENUE_NAME
                            break
                        date_elem = date_elem.parent
                        if not date_elem:
                            break
            
            # If we didn't find it near dates, use the general function
            if location == VENUE_NAME:
                location = determine_venue_from_soup(container)
            
            # Build full URL
            if href.startswith('http'):
                url = href
            else:
                url = urljoin(SAAM_BASE_URL, href)
            
            # Extract description
            description = None
            desc_elem = container.find(['p', 'div'], class_=re.compile(r'description|summary|intro', re.I))
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            # Build event
            event = {
                'title': title,
                'description': description or f"Exhibition at {location}",
                'event_type': 'exhibition',
                'organizer': location,
                'social_media_platform': 'website',
                'source_url': url,
                'social_media_url': url,
            }
            
            if date_range:
                event['start_date'] = date_range['start_date']
                event['end_date'] = date_range['end_date']
            
            events.append(event)
        
    except Exception as e:
        logger.warning(f"   ⚠️ Error parsing exhibitions from page: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_saam_tours(scraper=None) -> List[Dict]:
    """Scrape tours from SAAM tours page, including walk-in tours"""
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🔍 Scraping SAAM tours from: {SAAM_TOURS_URL}")
        response = scraper.get(SAAM_TOURS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # First, parse walk-in tours from the page content
        # Look for list items that contain walk-in tour information
        walkin_section = soup.find('h4', string=re.compile(r'walk-in', re.I))
        if not walkin_section:
            # Try finding by text
            for heading in soup.find_all(['h3', 'h4', 'h5']):
                if 'walk-in' in heading.get_text().lower():
                    walkin_section = heading
                    break
        
        page_text = soup.get_text()
        
        # Parse walk-in tours for SAAM main building
        # Look for text containing "SAAM's main building" and times
        saam_walkin_text = None
        if walkin_section:
            # Get the parent container
            container = walkin_section.find_next(['div', 'section', 'ul'])
            if container:
                container_text = container.get_text()
                # Find the line about SAAM main building
                for line in container_text.split('\n'):
                    if 'SAAM' in line and 'main building' in line.lower() and 'start at' in line.lower():
                        saam_walkin_text = line
                        break
        
        # Fallback: search in full page text
        if not saam_walkin_text:
            saam_match = re.search(
                r"SAAM'?s?\s+main\s+building[^.]*start\s+at[^.]*\.?",
                page_text,
                re.IGNORECASE
            )
            if saam_match:
                saam_walkin_text = saam_match.group(0)
        
        if saam_walkin_text:
            # Extract times (e.g., "12:30 p.m., 2 p.m., and 4 p.m.")
            times = re.findall(r'(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', saam_walkin_text, re.IGNORECASE)
            
            for time_str in times:
                # Create recurring tour events for each time slot
                # These happen daily, so we'll create events for the next 30 days
                from datetime import timedelta
                today = date.today()
                
                for day_offset in range(30):  # Next 30 days
                    tour_date = today + timedelta(days=day_offset)
                    
                    # Parse time
                    time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*([ap])\.?m\.?', time_str, re.IGNORECASE)
                    if time_match:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2)) if time_match.group(2) else 0
                        am_pm = time_match.group(3).upper()
                        
                        # Convert to 24-hour format
                        if am_pm == 'P' and hour != 12:
                            hour += 12
                        elif am_pm == 'A' and hour == 12:
                            hour = 0
                        
                        start_time = time(hour, minute)
                        end_time = time(hour + 1, minute)  # Tours last approximately one hour
                        
                        event = {
                            'title': 'Docent-Led Walk-In Tour',
                            'description': 'Free, docent-led walk-in tour at the Smithsonian American Art Museum. Tours last approximately one hour.',
                            'event_type': 'tour',
                            'start_date': tour_date,
                            'end_date': tour_date,
                            'start_time': start_time.strftime('%H:%M'),
                            'end_time': end_time.strftime('%H:%M'),
                            'organizer': VENUE_NAME,
                            'source_url': SAAM_TOURS_URL,
                            'social_media_platform': 'website',
                            'social_media_url': SAAM_TOURS_URL,
                            'meeting_point': 'Check with the Information Desk when you arrive',
                        }
                        events.append(event)
        
        # Parse walk-in tours for Renwick Gallery
        renwick_walkin_text = None
        if walkin_section:
            container = walkin_section.find_next(['div', 'section', 'ul'])
            if container:
                container_text = container.get_text()
                # Find the line about Renwick Gallery
                for line in container_text.split('\n'):
                    if 'Renwick' in line and 'start at' in line.lower():
                        renwick_walkin_text = line
                        break
        
        # Fallback: search in full page text
        if not renwick_walkin_text:
            renwick_match = re.search(
                r"Renwick\s+Gallery[^.]*start\s+at[^.]*\.?",
                page_text,
                re.IGNORECASE
            )
            if renwick_match:
                renwick_walkin_text = renwick_match.group(0)
        
        if renwick_walkin_text:
            # Check if it says "noon" or specific times
            if 'noon' in renwick_walkin_text.lower():
                times = ['12:00 p.m.']
            else:
                times = re.findall(r'(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', renwick_walkin_text, re.IGNORECASE)
            
            # Check days (Monday through Saturday, no tours on Sundays)
            days_match = re.search(r'(Monday through Saturday|Monday-Saturday|Mon-Sat)', renwick_walkin_text, re.IGNORECASE)
            is_weekdays_only = days_match is not None
            
            for time_str in times:
                from datetime import timedelta
                today = date.today()
                
                for day_offset in range(30):  # Next 30 days
                    tour_date = today + timedelta(days=day_offset)
                    
                    # Skip Sundays if it's weekdays only
                    if is_weekdays_only and tour_date.weekday() == 6:  # Sunday is 6
                        continue
                    
                    # Parse time
                    if 'noon' in time_str.lower():
                        start_time = time(12, 0)
                    else:
                        time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*([ap])\.?m\.?', time_str, re.IGNORECASE)
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = int(time_match.group(2)) if time_match.group(2) else 0
                            am_pm = time_match.group(3).upper()
                            
                            if am_pm == 'P' and hour != 12:
                                hour += 12
                            elif am_pm == 'A' and hour == 12:
                                hour = 0
                            
                            start_time = time(hour, minute)
                    end_time = time(start_time.hour + 1, start_time.minute)  # Tours last approximately one hour
                    
                    event = {
                        'title': 'Docent-Led Walk-In Tour',
                        'description': 'Free, docent-led walk-in tour at the Renwick Gallery. Tours last approximately one hour.',
                        'event_type': 'tour',
                        'start_date': tour_date,
                        'end_date': tour_date,
                        'start_time': start_time.strftime('%H:%M'),
                        'end_time': end_time.strftime('%H:%M'),
                        'organizer': RENWICK_VENUE_NAME,
                        'source_url': SAAM_TOURS_URL,
                        'social_media_platform': 'website',
                        'social_media_url': SAAM_TOURS_URL,
                        'meeting_point': 'Check with the Information Desk when you arrive',
                    }
                    events.append(event)
        
        # Also look for individual tour event links
        tour_links = soup.find_all('a', href=re.compile(r'/events/|/visit/tours'))
        
        processed_urls = set()
        for link in tour_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Build full URL
            if href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(SAAM_BASE_URL, href)
            
            if full_url in processed_urls or full_url == SAAM_TOURS_URL:
                continue
            
            # Only process specific tour/event pages (not the main tours page)
            if '/events/' in full_url and full_url.count('/') >= 4:
                processed_urls.add(full_url)
                try:
                    tour_data = scrape_event_detail(scraper, full_url, event_type='tour')
                    if tour_data:
                        events.append(tour_data)
                except Exception as e:
                    logger.warning(f"   ⚠️ Error scraping tour {full_url}: {e}")
        
        logger.info(f"   ✅ Found {len(events)} tours (including walk-in tours)")
        
    except Exception as e:
        logger.error(f"❌ Error scraping SAAM tours: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_saam_events(scraper=None) -> List[Dict]:
    """Scrape events (talks, gallery talks, etc.) from SAAM events search page and visit page"""
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    processed_urls = set()
    
    # First, check the visit page for featured events
    try:
        visit_url = 'https://americanart.si.edu/visit'
        logger.info(f"🔍 Checking visit page for featured events: {visit_url}")
        response = scraper.get(visit_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find event links on visit page
        visit_event_links = soup.find_all('a', href=re.compile(r'/events/[^/]+'))
        for link in visit_event_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Build full URL
            if href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(SAAM_BASE_URL, href)
            
            # Remove query parameters for deduplication
            base_url = full_url.split('?')[0].split('#')[0]
            
            # Skip access program series
            if any(skip in base_url.lower() for skip in ['asl-tours', 'dementia-programs', 'verbal-description']):
                continue
            
            if base_url in processed_urls:
                continue
            
            processed_urls.add(base_url)
            
            try:
                # Determine event type from URL or title
                event_type = 'event'
                title_text = link.get_text(strip=True).lower()
                
                if 'gallery talk' in title_text or ('talk' in title_text and 'walk-in' not in title_text):
                    event_type = 'talk'
                elif 'workshop' in title_text:
                    event_type = 'workshop'
                elif 'lecture' in title_text:
                    event_type = 'talk'
                elif 'art in the a.m.' in title_text or 'art am' in title_text:
                    event_type = 'talk'  # Art in the A.M. is a talk series
                
                event_data = scrape_event_detail(scraper, base_url, event_type=event_type)
                if event_data and event_data.get('title') and event_data['title'].lower() not in ['search events', 'search', 'redirecting']:
                    events.append(event_data)
            except Exception as e:
                logger.debug(f"   ⚠️ Error scraping visit page event {base_url}: {e}")
        
        logger.info(f"   ✅ Found {len(events)} events from visit page")
    except Exception as e:
        logger.warning(f"   ⚠️ Error checking visit page: {e}")
    
    # Then check the events search page
    try:
        logger.info(f"🔍 Scraping SAAM events from: {SAAM_EVENTS_URL}")
        response = scraper.get(SAAM_EVENTS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find event links - look for links to /events/ pages
        # Filter out navigation and search-related links
        all_links = soup.find_all('a', href=True)
        event_links = []
        
        for link in all_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Skip navigation/search links
            link_text = link.get_text(strip=True).lower()
            if link_text in ['search events', 'search', 'events', 'filter', 'filters']:
                continue
            
            # Look for /events/ links with actual event slugs
            if '/events/' in href:
                # Skip if it's a search/filter parameter
                if 'content_type' in href or 'filter' in href or 'search' in href.lower():
                    continue
                
                # Should have an event slug (not just /events/)
                parts = href.split('/events/')
                if len(parts) > 1 and parts[1]:
                    event_slug = parts[1].split('?')[0].split('#')[0].strip()
                    # Skip if slug is empty or just "events"
                    if event_slug and event_slug not in ['', 'events', 'event']:
                        event_links.append(link)
        
        processed_urls = set()
        for link in event_links:
            href = link.get('href', '')
            
            # Build full URL
            if href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(SAAM_BASE_URL, href)
            
            # Remove query parameters for deduplication
            base_url = full_url.split('?')[0].split('#')[0]
            
            if base_url in processed_urls:
                continue
            
            processed_urls.add(base_url)
            
            try:
                # Determine event type from URL or title
                event_type = 'event'  # Default
                title_text = link.get_text(strip=True).lower()
                
                # Skip if title is generic
                if title_text in ['search events', 'search', 'events', 'event', 'more', 'view all']:
                    continue
                
                if 'gallery talk' in title_text or 'talk' in title_text:
                    event_type = 'talk'
                elif 'tour' in title_text and 'walk-in' not in title_text:
                    event_type = 'tour'
                elif 'workshop' in title_text:
                    event_type = 'workshop'
                elif 'lecture' in title_text:
                    event_type = 'talk'
                elif 'family' in title_text or 'activity' in title_text:
                    event_type = 'workshop'
                elif 'asl' in title_text or 'accessibility' in title_text:
                    event_type = 'tour'  # Access programs
                
                # Skip access program series pages (they redirect to search)
                if any(skip in base_url.lower() for skip in ['asl-tours', 'dementia-programs', 'verbal-description']):
                    continue
                
                event_data = scrape_event_detail(scraper, base_url, event_type=event_type)
                if event_data and event_data.get('title') and event_data['title'].lower() not in ['search events', 'search', 'redirecting']:
                    events.append(event_data)
            except Exception as e:
                logger.warning(f"   ⚠️ Error scraping event {base_url}: {e}")
        
        # Also try to parse events directly from the search results page
        # Look for event cards/items in the results
        event_items = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'event|result|item', re.I))
        for item in event_items:
            # Look for event links within these items
            item_link = item.find('a', href=re.compile(r'/events/'))
            if item_link:
                href = item_link.get('href', '')
                if href and href not in processed_urls:
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(SAAM_BASE_URL, href)
                    
                    if '/events/' in full_url and full_url.count('/') >= 4:
                        processed_urls.add(full_url)
                        try:
                            # Try to extract basic info from the item itself
                            title = item_link.get_text(strip=True)
                            if title and len(title) > 5:
                                # Determine event type
                                event_type = 'event'
                                title_lower = title.lower()
                                if 'gallery talk' in title_lower or 'talk' in title_lower:
                                    event_type = 'talk'
                                elif 'tour' in title_lower:
                                    event_type = 'tour'
                                elif 'workshop' in title_lower:
                                    event_type = 'workshop'
                                
                                # Try to scrape full details
                                event_data = scrape_event_detail(scraper, full_url, event_type=event_type)
                                if event_data:
                                    events.append(event_data)
                        except Exception as e:
                            logger.debug(f"   ⚠️ Error processing event item: {e}")
        
        logger.info(f"   ✅ Found {len(events)} events")
        
    except Exception as e:
        logger.error(f"❌ Error scraping SAAM events: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_event_detail(scraper, url: str, event_type: str = 'event') -> Optional[Dict]:
    """Scrape details from an individual event/tour page"""
    try:
        logger.debug(f"   📄 Scraping event page: {url}")
        response = scraper.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if page redirects (common for access program series)
        if soup.find('title') and 'redirecting' in soup.find('title').get_text().lower():
            logger.debug(f"   ⚠️ Page redirects, skipping: {url}")
            return None
        
        # Extract title
        title = None
        
        # Try H1 first (most reliable)
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            # Skip generic titles
            if title.lower() in ['search events', 'search', 'events', 'event']:
                title = None
        
        # Try H2 with title class
        if not title:
            title_elem = soup.find('h2', class_=re.compile(r'title|heading', re.I))
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title.lower() in ['search events', 'search', 'events', 'event']:
                    title = None
        
        # Try meta title tag
        if not title:
            meta_title = soup.find('title')
            if meta_title:
                title = meta_title.get_text(strip=True)
                # Clean up meta title (remove site name)
                if '|' in title:
                    title = title.split('|')[0].strip()
                if title.lower() in ['search events', 'search', 'events', 'event', 'redirecting']:
                    title = None
        
        # Try OG title
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
                if '|' in title:
                    title = title.split('|')[0].strip()
        
        # Skip generic titles
        if not title or title.lower() in ['search events', 'search', 'events', 'event', 'redirecting'] or 'find events including' in title.lower():
            logger.debug(f"   ⚠️ Could not find valid title for {url}")
            return None
        
        # Extract description - first try schema.org JSON
        description = None
        schema_script = None  # Will be reused for time extraction
        
        schema_script = soup.find('script', type='application/ld+json')
        if schema_script:
            try:
                import json
                schema_data = json.loads(schema_script.string)
                if isinstance(schema_data, dict):
                    if 'description' in schema_data:
                        description = schema_data['description']
                elif isinstance(schema_data, list):
                    for item in schema_data:
                        if isinstance(item, dict) and 'description' in item:
                            description = item['description']
                            break
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Fallback: look for description in main content area
        if not description:
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|body', re.I))
            if main_content:
                # Look for paragraphs that contain event description (not navigation/metadata)
                paragraphs = main_content.find_all('p')
                desc_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # Skip short paragraphs that are likely navigation/metadata
                    if len(text) > 50 and not any(skip in text.lower() for skip in ['subscribe', 'newsletter', 'follow us', 'legal', 'privacy', 'join now']):
                        desc_parts.append(text)
                
                if desc_parts:
                    description = ' '.join(desc_parts)
        
        # Fallback: look for description div
        if not description:
            desc_elem = soup.find('div', class_=re.compile(r'description|summary|intro', re.I))
            if desc_elem:
                description = desc_elem.get_text(strip=True)
        
        # Fallback: first substantial paragraph
        if not description:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 100:  # Substantial paragraph
                    description = text
                    break
        
        # Extract date and time
        start_date = None
        start_time = None
        end_time = None
        
        # Look for date/time information in the page
        page_text = soup.get_text()
        
        # Try to find date/time patterns like "Friday, January 23, 2026, 12:15 – 1:15pm EST"
        # Pattern 1: Full date with time range "January 23, 2026, 12:15 – 1:15pm"
        # Use DOTALL to allow newlines between date and time
        date_time_range_pattern = r'(\w+day,?\s+)?(\w+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*([ap]m)'
        match = re.search(date_time_range_pattern, page_text, re.I | re.DOTALL)
        if match:
            # Extract date
            date_str = match.group(2) if match.group(2) else match.group(1)
            parsed_date = parse_single_date(date_str)
            if parsed_date:
                start_date = parsed_date
            
            # Extract times - ensure we have all required groups
            if match.group(3) and match.group(4) and match.group(5):
                start_time_str = match.group(3)
                end_time_str = match.group(4)
                am_pm = match.group(5).upper()
                start_time = f"{start_time_str} {am_pm}"
                end_time = f"{end_time_str} {am_pm}"
        
        # Pattern 2: Date with single time "January 23, 2026, 12:15pm"
        # Only use this if we didn't already find a time range (don't overwrite end_time)
        if not start_time:
            date_time_single_pattern = r'(\w+day,?\s+)?(\w+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}:\d{2})\s*([ap]m)'
            match = re.search(date_time_single_pattern, page_text, re.I)
            if match:
                date_str = match.group(2) if match.group(2) else match.group(1)
                parsed_date = parse_single_date(date_str)
                if parsed_date:
                    start_date = parsed_date
                start_time_str = match.group(3)
                am_pm = match.group(4).upper()
                start_time = f"{start_time_str} {am_pm}"
        
        # Fallback: Look for date separately
        if not start_date:
            date_elem = soup.find(text=re.compile(r'\d{1,2}/\d{1,2}/\d{4}|\w+ \d{1,2}, \d{4}'))
            if date_elem:
                date_text = date_elem.parent.get_text() if hasattr(date_elem, 'parent') else str(date_elem)
                parsed_date = parse_single_date(date_text)
                if parsed_date:
                    start_date = parsed_date
        
        # Fallback: Look for time range separately (handle "12:15 – 1:15pm" format)
        if not start_time:
            # Try pattern with en-dash or hyphen
            time_range_match = re.search(r'(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*([ap]m)', page_text, re.I | re.DOTALL)
            if time_range_match:
                start_time = f"{time_range_match.group(1)} {time_range_match.group(3).upper()}"
                end_time = f"{time_range_match.group(2)} {time_range_match.group(3).upper()}"
            else:
                # Single time
                time_match = re.search(r'(\d{1,2}:\d{2})\s*([ap]m)', page_text, re.I)
                if time_match:
                    start_time = f"{time_match.group(1)} {time_match.group(2).upper()}"
        
        # If we have start_time but no end_time, try to find the time range
        if start_time and not end_time:
            time_range_match = re.search(r'(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*([ap]m)', page_text, re.I | re.DOTALL)
            if time_range_match:
                found_start = f"{time_range_match.group(1)} {time_range_match.group(3).upper()}"
                # Check if this matches our start time (allowing for slight variations)
                if found_start == start_time or found_start.replace(' ', '') == start_time.replace(' ', ''):
                    end_time = f"{time_range_match.group(2)} {time_range_match.group(3).upper()}"
        
        # Also check schema.org for time (always check for end time even if start time was found)
        if schema_script:
            try:
                import json
                schema_data = json.loads(schema_script.string)
                if isinstance(schema_data, dict):
                    if 'startDate' in schema_data and not start_time:
                        start_date_str = schema_data['startDate']
                        # Parse ISO format like "2026-01-23T13:15:00"
                        if 'T' in start_date_str:
                            time_part = start_date_str.split('T')[1].split('+')[0].split('-')[0]
                            if ':' in time_part:
                                hours, minutes = time_part.split(':')[:2]
                                hour_int = int(hours)
                                am_pm = 'AM' if hour_int < 12 else 'PM'
                                if hour_int == 0:
                                    hour_int = 12
                                elif hour_int > 12:
                                    hour_int -= 12
                                start_time = f"{hour_int}:{minutes} {am_pm}"
                    # Always check for endDate
                    if 'endDate' in schema_data and not end_time:
                        end_date_str = schema_data['endDate']
                        if 'T' in end_date_str:
                            time_part = end_date_str.split('T')[1].split('+')[0].split('-')[0]
                            if ':' in time_part:
                                hours, minutes = time_part.split(':')[:2]
                                hour_int = int(hours)
                                am_pm = 'AM' if hour_int < 12 else 'PM'
                                if hour_int == 0:
                                    hour_int = 12
                                elif hour_int > 12:
                                    hour_int -= 12
                                end_time = f"{hour_int}:{minutes} {am_pm}"
                elif isinstance(schema_data, list):
                    for item in schema_data:
                        if isinstance(item, dict):
                            if 'startDate' in item and not start_time:
                                start_date_str = item['startDate']
                                if 'T' in start_date_str:
                                    time_part = start_date_str.split('T')[1].split('+')[0].split('-')[0]
                                    if ':' in time_part:
                                        hours, minutes = time_part.split(':')[:2]
                                        hour_int = int(hours)
                                        am_pm = 'AM' if hour_int < 12 else 'PM'
                                        if hour_int == 0:
                                            hour_int = 12
                                        elif hour_int > 12:
                                            hour_int -= 12
                                        start_time = f"{hour_int}:{minutes} {am_pm}"
                            if 'endDate' in item and not end_time:
                                end_date_str = item['endDate']
                                if 'T' in end_date_str:
                                    time_part = end_date_str.split('T')[1].split('+')[0].split('-')[0]
                                    if ':' in time_part:
                                        hours, minutes = time_part.split(':')[:2]
                                        hour_int = int(hours)
                                        am_pm = 'AM' if hour_int < 12 else 'PM'
                                        if hour_int == 0:
                                            hour_int = 12
                                        elif hour_int > 12:
                                            hour_int -= 12
                                        end_time = f"{hour_int}:{minutes} {am_pm}"
                            break
            except (json.JSONDecodeError, AttributeError, ValueError):
                pass
        
        # Determine if event is online/virtual
        is_online = False
        
        # Check schema.org eventAttendanceMode (reuse schema_script if already found)
        if not schema_script:
            schema_script = soup.find('script', type='application/ld+json')
        
        if schema_script:
            try:
                import json
                schema_data = json.loads(schema_script.string)
                if isinstance(schema_data, dict):
                    attendance_mode = schema_data.get('eventAttendanceMode', '')
                    if 'Online' in str(attendance_mode) or 'online' in str(attendance_mode).lower():
                        is_online = True
                elif isinstance(schema_data, list):
                    for item in schema_data:
                        if isinstance(item, dict):
                            attendance_mode = item.get('eventAttendanceMode', '')
                            if 'Online' in str(attendance_mode) or 'online' in str(attendance_mode).lower():
                                is_online = True
                                break
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Check title for "Virtual" keyword
        if title and 'virtual' in title.lower():
            is_online = True
        
        # Check description for online indicators
        if description:
            desc_lower = description.lower()
            online_indicators = [
                'online',
                'virtual',
                'zoom',
                'webinar',
                'livestream',
                'live stream',
                'streaming',
                'remote',
                'digital event',
            ]
            if any(indicator in desc_lower for indicator in online_indicators):
                is_online = True
        
        # Check URL for virtual/online
        if 'virtual' in url.lower() or 'online' in url.lower():
            is_online = True
        
        # Extract meeting point/location
        meeting_point = None
        
        # Look for "Event Location" or "Meet in" fields in tombstone/dl elements
        location_elem = soup.find('dt', string=re.compile(r'Event Location|Location|Meet', re.I))
        if location_elem:
            location_dd = location_elem.find_next_sibling('dd')
            if location_dd:
                location_text = location_dd.get_text(strip=True)
                # Extract meeting point if it says "Meet in" or similar
                meet_match = re.search(r'Meet\s+in\s+(.+?)(?:\s*\||$)', location_text, re.I)
                if meet_match:
                    meeting_point = meet_match.group(1).strip()
                elif 'G Street' in location_text or 'Lobby' in location_text:
                    # Extract location details
                    meeting_point = location_text.split('|')[0].strip() if '|' in location_text else location_text
        
        # Also check Cost field which sometimes includes location like "Free | Meet in G Street Lobby"
        # Find dt element containing "Cost" (may have whitespace)
        cost_elem = None
        for dt in soup.find_all('dt'):
            if dt.get_text(strip=True).lower() == 'cost':
                cost_elem = dt
                break
        
        if cost_elem and not meeting_point:
            cost_dd = cost_elem.find_next_sibling('dd')
            if cost_dd:
                cost_text = cost_dd.get_text(strip=True)
                if '|' in cost_text:
                    parts = cost_text.split('|')
                    for part in parts:
                        part_clean = part.strip()
                        if 'meet' in part_clean.lower() or 'lobby' in part_clean.lower() or 'g street' in part_clean.lower():
                            # Extract just the location part (remove "Meet in" prefix)
                            meeting_match = re.search(r'Meet\s+in\s+(.+?)$', part_clean, re.I)
                            if meeting_match:
                                meeting_point = meeting_match.group(1).strip()
                            else:
                                meeting_point = part_clean
                            break
        
        # Determine venue location - check Event Location field first
        location = None
        event_location_elem = soup.find('dt', string=re.compile(r'Event Location|Location', re.I))
        if event_location_elem:
            event_location_dd = event_location_elem.find_next_sibling('dd')
            if event_location_dd:
                location_text = event_location_dd.get_text(strip=True)
                # Extract venue name (e.g., "In-person | Smithsonian American Art Museum")
                if '|' in location_text:
                    venue_part = location_text.split('|')[1].strip()
                    location = venue_part
                elif 'smithsonian american art museum' in location_text.lower():
                    location = VENUE_NAME
                elif 'renwick' in location_text.lower():
                    location = RENWICK_VENUE_NAME
        
        # Fallback to determine_venue_from_soup if not found
        if not location:
            location = determine_venue_from_soup(soup)
        
        # If online, set location to "Online" instead of venue
        if is_online:
            location = "Online"
            meeting_point = None
        
        # Extract image
        image_url = None
        img_elem = soup.find('img', class_=re.compile(r'hero|feature|main|event', re.I))
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src')
            if img_src:
                image_url = urljoin(SAAM_BASE_URL, img_src)
        
        # Extract pricing information
        price = None
        admission_price = None
        is_free = None
        
        # Look for "Cost" field in tombstone/dl elements (reuse cost_elem if already found)
        if cost_elem is None:
            for dt in soup.find_all('dt'):
                if dt.get_text(strip=True).lower() == 'cost':
                    cost_elem = dt
                    break
        
        if cost_elem:
            cost_dd = cost_elem.find_next_sibling('dd')
            if cost_dd:
                cost_text = cost_dd.get_text(strip=True)
                cost_lower = cost_text.lower()
                
                # Check if it's free (handle "Free | Meet in..." format)
                cost_part = cost_text.split('|')[0].strip() if '|' in cost_text else cost_text
                cost_part_lower = cost_part.lower()
                
                # Also check the full cost_text for "free" in case it's in a different part
                if any(word in cost_part_lower for word in ['free', 'no cost', 'complimentary', 'no charge']) or 'free' in cost_lower:
                    is_free = True
                    price = 0.0
                    admission_price = 0.0
                # Check if it says "sold out" or similar
                elif any(word in cost_part_lower for word in ['sold out', 'sold-out']):
                    # Still extract price if mentioned elsewhere
                    pass
                else:
                    # Try to extract price amount
                    price_match = re.search(r'\$?(\d+(?:\.\d{2})?)', cost_part)
                    if price_match:
                        try:
                            price_value = float(price_match.group(1))
                            price = price_value
                            admission_price = price_value
                            is_free = False
                        except ValueError:
                            pass
        
        # Also check description for pricing info
        if description and price is None:
            desc_lower = description.lower()
            if any(word in desc_lower for word in ['free', 'no cost', 'complimentary', 'no charge', 'free admission']):
                is_free = True
                price = 0.0
                admission_price = 0.0
            else:
                # Look for price mentions in description
                price_patterns = [
                    r'\$(\d+(?:\.\d{2})?)',
                    r'(\d+(?:\.\d{2})?)\s*dollars?',
                    r'costs?\s*\$?(\d+(?:\.\d{2})?)',
                    r'price[:\s]+\$?(\d+(?:\.\d{2})?)',
                ]
                for pattern in price_patterns:
                    match = re.search(pattern, desc_lower, re.I)
                    if match:
                        try:
                            price_value = float(match.group(1))
                            price = price_value
                            admission_price = price_value
                            is_free = False
                            break
                        except ValueError:
                            pass
        
        # Extract registration information
        is_registration_required = False
        registration_url = None
        registration_info = None
        
        # Look for registration/ticket links
        page_text = soup.get_text().lower()
        
        # Check for registration/ticket buttons/links
        reg_links = soup.find_all('a', href=True, string=re.compile(r'register|ticket|rsvp|reserve', re.I))
        if not reg_links:
            # Also check for links with registration-related text in their text content
            reg_links = soup.find_all('a', href=True)
            for link in reg_links:
                link_text = link.get_text(strip=True).lower()
                if any(word in link_text for word in ['register', 'ticket', 'rsvp', 'reserve', 'get tickets', 'buy tickets']):
                    reg_links = [link]
                    break
        
        if reg_links:
            is_registration_required = True
            href = reg_links[0].get('href', '')
            if href:
                if href.startswith('http'):
                    registration_url = href
                else:
                    registration_url = urljoin(SAAM_BASE_URL, href)
        
        # Look for registration-related text in description
        if description:
            desc_lower = description.lower()
            registration_patterns = [
                r'registration\s+(?:is\s+)?required',
                r'advance\s+registration',
                r'pre[-\s]?registration',
                r'register\s+(?:online|now|here)',
                r'tickets?\s+(?:are\s+)?required',
                r'rsvp\s+(?:required|needed)',
            ]
            for pattern in registration_patterns:
                if re.search(pattern, desc_lower, re.I):
                    is_registration_required = True
                    # Extract registration info from context
                    match = re.search(pattern, desc_lower, re.I)
                    if match:
                        start = max(0, match.start() - 50)
                        end = min(len(description), match.end() + 100)
                        registration_info = description[start:end].strip()
                    break
        
        # Look for "no registration required" or "free, no tickets needed"
        if description:
            desc_lower = description.lower()
            if re.search(r'no\s+registration|free\s+and\s+open|no\s+tickets?\s+needed|walk[-\s]?in', desc_lower, re.I):
                is_registration_required = False
        
        # Build event dictionary
        event = {
            'title': title,
            'description': description or f"{event_type.title()} at {location}",
            'event_type': event_type,
            'source_url': url,
            'organizer': location,
            'social_media_platform': 'website',
            'social_media_url': url,
            'is_online': is_online,
            'is_registration_required': is_registration_required,
            'registration_url': registration_url,
            'registration_info': registration_info,
            'meeting_point': meeting_point,
        }
        
        if start_date:
            event['start_date'] = start_date
        if start_time:
            event['start_time'] = start_time
        
        if end_time:
            event['end_time'] = end_time
        
        if image_url:
            event['image_url'] = image_url
        
        # Add pricing information
        if price is not None:
            event['price'] = price
        if admission_price is not None:
            event['admission_price'] = admission_price
        
        return event
        
    except Exception as e:
        logger.warning(f"   ⚠️ Error scraping event detail {url}: {e}")
        return None


def scrape_all_saam_exhibitions() -> List[Dict]:
    """Main function to scrape all SAAM exhibitions"""
    scraper = create_scraper()
    return scrape_saam_exhibitions(scraper)


def scrape_all_saam_events() -> List[Dict]:
    """Main function to scrape all SAAM events (exhibitions, tours, talks, etc.)"""
    scraper = create_scraper()
    all_events = []
    
    logger.info("🎨 Starting comprehensive SAAM scraping...")
    
    # 1. Scrape exhibitions
    logger.info("📋 Scraping exhibitions...")
    exhibitions = scrape_saam_exhibitions(scraper)
    all_events.extend(exhibitions)
    logger.info(f"   ✅ Found {len(exhibitions)} exhibitions")
    
    # 2. Scrape tours
    logger.info("🚶 Scraping tours...")
    tours = scrape_saam_tours(scraper)
    all_events.extend(tours)
    logger.info(f"   ✅ Found {len(tours)} tours")
    
    # 3. Scrape events (talks, gallery talks, etc.)
    logger.info("🎤 Scraping events (talks, etc.)...")
    events = scrape_saam_events(scraper)
    all_events.extend(events)
    logger.info(f"   ✅ Found {len(events)} events")
    
    logger.info(f"✅ Total SAAM events scraped: {len(all_events)}")
    return all_events


def create_events_in_database(events: List[Dict]) -> tuple:
    """
    Create scraped events in the database with update-or-create logic
    Returns (created_count, updated_count)
    """
    with app.app_context():
        created_count = 0
        updated_count = 0
        
        for event_data in events:
            try:
                # Determine which venue this event belongs to (skip if online)
                is_online_event = event_data.get('is_online', False)
                venue = None
                venue_name = None
                
                if not is_online_event:
                    organizer = event_data.get('organizer', VENUE_NAME)
                    if 'Renwick' in organizer:
                        venue_name = RENWICK_VENUE_NAME
                    elif 'Online' not in organizer:
                        venue_name = VENUE_NAME
                    
                    if venue_name:
                        # Find venue
                        venue = Venue.query.filter(
                            db.func.lower(Venue.name).like(f'%{venue_name.lower()}%')
                        ).first()
                        
                        if not venue:
                            logger.warning(f"   ⚠️  Venue '{venue_name}' not found, skipping event: {event_data.get('title')}")
                            continue
                
                # Find city
                city = City.query.filter(
                    db.func.lower(City.name).like(f'%{CITY_NAME.lower().split(",")[0]}%')
                ).first()
                
                if not city:
                    logger.warning(f"   ⚠️  City '{CITY_NAME}' not found, skipping event: {event_data.get('title')}")
                    continue
                
                # Validate required fields
                if not event_data.get('title'):
                    logger.warning(f"   ⚠️  Skipping event: missing title")
                    continue
                
                if not event_data.get('start_date'):
                    logger.warning(f"   ⚠️  Skipping event '{event_data.get('title')}': missing start_date")
                    continue
                
                # Parse date
                if isinstance(event_data['start_date'], date):
                    event_date = event_data['start_date']
                else:
                    try:
                        event_date = datetime.fromisoformat(str(event_data['start_date'])).date()
                    except (ValueError, TypeError) as e:
                        logger.warning(f"   ⚠️  Skipping event '{event_data.get('title')}': invalid date format: {e}")
                        continue
                
                # Parse times
                start_time_obj = None
                end_time_obj = None
                if event_data.get('start_time'):
                    try:
                        if isinstance(event_data['start_time'], time):
                            start_time_obj = event_data['start_time']
                        else:
                            # Try parsing as HH:MM string
                            time_str = str(event_data['start_time'])
                            if ':' in time_str:
                                parts = time_str.split(':')
                                start_time_obj = time(int(parts[0]), int(parts[1]))
                    except (ValueError, TypeError):
                        pass
                
                if event_data.get('end_time'):
                    try:
                        if isinstance(event_data['end_time'], time):
                            end_time_obj = event_data['end_time']
                        else:
                            time_str = str(event_data['end_time'])
                            if ':' in time_str:
                                parts = time_str.split(':')
                                end_time_obj = time(int(parts[0]), int(parts[1]))
                    except (ValueError, TypeError):
                        pass
                
                # Check if event already exists
                existing = None
                source_url = event_data.get('source_url') or event_data.get('url')
                
                if source_url:
                    existing = Event.query.filter_by(
                        url=source_url,
                        city_id=city.id
                    ).first()
                
                if not existing:
                    existing = Event.query.filter_by(
                        title=event_data.get('title'),
                        venue_id=venue.id if venue else None,
                        start_date=event_date,
                        city_id=city.id
                    ).first()
                
                # Parse end_date
                end_date = event_date
                if event_data.get('end_date'):
                    if isinstance(event_data['end_date'], date):
                        end_date = event_data['end_date']
                    else:
                        try:
                            end_date = datetime.fromisoformat(str(event_data['end_date'])).date()
                        except (ValueError, TypeError):
                            end_date = event_date
                
                if existing:
                    # Update existing event
                    updated = False
                    
                    if event_data.get('title') and existing.title != event_data.get('title'):
                        existing.title = event_data.get('title')
                        updated = True
                    
                    if event_data.get('event_type') and existing.event_type != event_data.get('event_type'):
                        existing.event_type = event_data.get('event_type')
                        updated = True
                    
                    if event_data.get('description') and (not existing.description or len(event_data['description']) > len(existing.description or '')):
                        existing.description = event_data.get('description')
                        updated = True
                    
                    if source_url and existing.url != source_url:
                        existing.url = source_url
                        updated = True
                    
                    if event_data.get('image_url') and not existing.image_url:
                        existing.image_url = event_data.get('image_url')
                        updated = True
                    
                    if event_data.get('meeting_point') and existing.meeting_point != event_data.get('meeting_point'):
                        existing.meeting_point = event_data.get('meeting_point')
                        updated = True
                    
                    if start_time_obj and (not existing.start_time or existing.start_time != start_time_obj):
                        existing.start_time = start_time_obj
                        updated = True
                    
                    if end_time_obj and (not existing.end_time or existing.end_time != end_time_obj):
                        existing.end_time = end_time_obj
                        updated = True
                    
                    # Update registration fields
                    if hasattr(Event, 'is_registration_required'):
                        if event_data.get('is_registration_required') is not None:
                            if existing.is_registration_required != event_data.get('is_registration_required'):
                                existing.is_registration_required = event_data.get('is_registration_required')
                                updated = True
                    
                    if hasattr(Event, 'registration_url') and event_data.get('registration_url'):
                        if existing.registration_url != event_data.get('registration_url'):
                            existing.registration_url = event_data.get('registration_url')
                            updated = True
                    
                    if hasattr(Event, 'registration_info') and event_data.get('registration_info'):
                        if not existing.registration_info or existing.registration_info != event_data.get('registration_info'):
                            existing.registration_info = event_data.get('registration_info')
                            updated = True
                    
                    # Update pricing fields
                    if hasattr(Event, 'price') and event_data.get('price') is not None:
                        if existing.price != event_data.get('price'):
                            existing.price = event_data.get('price')
                            updated = True
                    
                    if hasattr(Event, 'admission_price') and event_data.get('admission_price') is not None:
                        if existing.admission_price != event_data.get('admission_price'):
                            existing.admission_price = event_data.get('admission_price')
                            updated = True
                    
                    # Update online status
                    if hasattr(Event, 'is_online') and event_data.get('is_online') is not None:
                        if existing.is_online != event_data.get('is_online'):
                            existing.is_online = event_data.get('is_online')
                            updated = True
                    
                    if updated:
                        db.session.commit()
                        updated_count += 1
                        logger.info(f"   ✅ Updated: {event_data['title']}")
                else:
                    # Create new event
                    # Set location for online events
                    location_text = "Online" if is_online_event else (event_data.get('meeting_point') or event_data.get('location') or (venue.name if venue else None))
                    organizer_text = event_data.get('organizer', 'Online' if is_online_event else (venue.name if venue else None))
                    
                    event = Event(
                        title=event_data['title'],
                        description=event_data.get('description'),
                        start_date=event_date,
                        end_date=end_date,
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        start_location=location_text,
                        venue_id=venue.id if venue else None,
                        city_id=city.id if not is_online_event else None,  # Online events might not have a city
                        event_type=event_data.get('event_type', 'event'),
                        url=source_url,
                        image_url=event_data.get('image_url'),
                        social_media_platform=event_data.get('social_media_platform', 'website'),
                        social_media_url=source_url,
                        organizer=organizer_text,
                    )
                    
                    # Add registration fields if they exist
                    if hasattr(Event, 'is_registration_required'):
                        event.is_registration_required = event_data.get('is_registration_required', False)
                    if hasattr(Event, 'registration_url'):
                        event.registration_url = event_data.get('registration_url')
                    if hasattr(Event, 'registration_info'):
                        event.registration_info = event_data.get('registration_info')
                    
                    # Add pricing fields if they exist
                    if hasattr(Event, 'price') and event_data.get('price') is not None:
                        event.price = event_data.get('price')
                    if hasattr(Event, 'admission_price') and event_data.get('admission_price') is not None:
                        event.admission_price = event_data.get('admission_price')
                    
                    # Add online status
                    if hasattr(Event, 'is_online') and event_data.get('is_online') is not None:
                        event.is_online = event_data.get('is_online')
                    
                    db.session.add(event)
                    db.session.commit()
                    created_count += 1
                    logger.info(f"   ✅ Created: {event_data['title']}")
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing event '{event_data.get('title', 'Unknown')}': {e}")
                db.session.rollback()
                continue
        
        return created_count, updated_count


if __name__ == '__main__':
    # Test the scraper
    logger.info("🧪 Testing comprehensive SAAM scraper...")
    events = scrape_all_saam_events()
    
    logger.info(f"\n✅ Scraped {len(events)} total events:")
    for i, event in enumerate(events, 1):
        logger.info(f"\n{i}. {event.get('title', 'N/A')} ({event.get('event_type', 'event')})")
        if event.get('start_date'):
            logger.info(f"   Date: {event.get('start_date')}")
        if event.get('start_time'):
            logger.info(f"   Time: {event.get('start_time')}")
        logger.info(f"   Location: {event.get('organizer', 'N/A')}")
        logger.info(f"   URL: {event.get('source_url', 'N/A')}")

