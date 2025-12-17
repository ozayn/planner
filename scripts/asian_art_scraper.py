#!/usr/bin/env python3
"""
Comprehensive Scraper for Smithsonian National Museum of Asian Art
Scrapes exhibitions, events, tours, and programs from asia.si.edu
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
from requests.exceptions import Timeout, RequestException, ConnectionError, ReadTimeout, ConnectTimeout
from socket import timeout as SocketTimeout
import urllib3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Import shared progress update function
from scripts.utils import update_scraping_progress

VENUE_NAME = "Smithsonian National Museum of Asian Art"
CITY_NAME = "Washington"

# Asian Art Museum URLs
ASIAN_ART_BASE_URL = 'https://asia.si.edu'
ASIAN_ART_EXHIBITIONS_URL = 'https://asia.si.edu/whats-on/exhibitions/'
ASIAN_ART_EVENTS_URL = 'https://asia.si.edu/whats-on/events/'
ASIAN_ART_TOURS_URL = 'https://asia.si.edu/whats-on/tours/'
ASIAN_ART_FILMS_URL = 'https://asia.si.edu/whats-on/events/search/?edan_fq[]=p.event.topics:Films'
ASIAN_ART_PERFORMANCES_URL = 'https://asia.si.edu/whats-on/events/search/?edan_fq[]=p.event.topics:Performances'


def create_scraper():
    """Create a scraper session"""
    # Suppress SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    scraper = requests.Session()
    scraper.verify = False
    
    scraper.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    return scraper


# Use shared parse_date_range from utils
from scripts.utils import parse_date_range


def scrape_exhibition_detail(scraper, url: str, max_retries: int = 2) -> Optional[Dict]:
    """Scrape details from an individual exhibition page with retry logic"""
    import time
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"   📄 Scraping exhibition page: {url} (attempt {attempt + 1}/{max_retries})")
            # Use longer timeout: (connect timeout, read timeout) - increased for slow connections
            response = scraper.get(url, timeout=(15, 45))
            response.raise_for_status()
            break  # Success, exit retry loop
        except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as e:
            if attempt < max_retries - 1:
                wait_time = 2 * (attempt + 1)  # Exponential backoff: 2s, 4s
                logger.debug(f"   ⏳ Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                logger.warning(f"   ⚠️ Timeout scraping exhibition detail {url} after {max_retries} attempts: {type(e).__name__}")
                return None
        except (ConnectionError, RequestException) as e:
            if attempt < max_retries - 1:
                wait_time = 2 * (attempt + 1)
                logger.debug(f"   ⏳ Connection error on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                logger.warning(f"   ⚠️ Connection error scraping exhibition detail {url} after {max_retries} attempts: {type(e).__name__}")
                return None
    
    try:
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = None
        title_elem = soup.find('h1') or soup.find('h2', class_=re.compile(r'title', re.I))
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        if not title:
            meta_title = soup.find('title')
            if meta_title:
                title = meta_title.get_text(strip=True)
        
        # Clean title: remove venue name suffix
        if title:
            from scripts.utils import clean_event_title
            title = clean_event_title(title)
        
        if not title:
            logger.debug(f"   ⚠️ Could not find title for {url}")
            return None
        
        # Extract description using shared utility function
        from scripts.utils import extract_description_from_soup
        description = extract_description_from_soup(soup, max_length=2000)
        
        # Extract date range - prioritize structured HTML extraction
        date_range = None
        date_text = None
        
        # Use shared utility function to extract date text from structured HTML
        from scripts.utils import extract_date_range_from_soup
        date_text = extract_date_range_from_soup(soup)
        
        # Parse date range if found
        if date_text:
            date_range = parse_date_range(date_text)
        
        # Fallback: look for date in specific elements with date classes
        if not date_range:
            date_containers = soup.find_all(['div', 'span', 'p'], 
                                           class_=re.compile(r'date|time|duration', re.I))
            for container in date_containers:
                container_text = container.get_text(strip=True)
                date_range = parse_date_range(container_text)
                if date_range:
                    break
        
        # Last resort: look for any text with a 4-digit year
        if not date_range:
            date_elem = soup.find(string=re.compile(r'\d{4}'))
            if date_elem:
                date_text = date_elem.parent.get_text() if hasattr(date_elem, 'parent') else str(date_elem)
                date_range = parse_date_range(date_text)
        
        # Extract image - try multiple strategies
        image_url = None
        
        # Strategy 1: Look for hero/feature/main images by class
        img_elem = soup.find('img', class_=re.compile(r'hero|feature|main|exhibition|header', re.I))
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
            if img_src:
                image_url = urljoin(ASIAN_ART_BASE_URL, img_src)
        
        # Strategy 2: Look for images with keywords in URL
        if not image_url:
            all_imgs = soup.find_all('img')
            for img in all_imgs:
                img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if img_src:
                    src_lower = img_src.lower()
                    # Skip small icons/logos/decoration
                    skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'twitter', 'facebook', 'instagram', 'svg']
                    if any(pattern in src_lower for pattern in skip_patterns):
                        continue
                    
                    # Prefer images with certain keywords in path
                    if any(keyword in src_lower for keyword in ['exhibition', 'hero', 'feature', 'header', 'banner']):
                        image_url = urljoin(ASIAN_ART_BASE_URL, img_src)
                        break
        
        # Strategy 3: Find first substantial image (jpg/png/webp) not in nav/footer
        if not image_url:
            all_imgs = soup.find_all('img')
            for img in all_imgs:
                img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if img_src:
                    src_lower = img_src.lower()
                    # Skip icons/logos
                    skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg']
                    if any(pattern in src_lower for pattern in skip_patterns):
                        continue
                    
                    # Check if it's a real image file
                    if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        # Check if it's not in navigation/footer
                        parent = img.parent
                        skip_containers = ['nav', 'header', 'footer', 'menu']
                        parent_tag = parent.name if parent else ''
                        parent_classes = ' '.join(parent.get('class', [])) if parent and hasattr(parent, 'get') else ''
                        
                        if parent_tag not in skip_containers and not any(skip in parent_classes.lower() for skip in skip_containers):
                            image_url = urljoin(ASIAN_ART_BASE_URL, img_src)
                            break
        
        # Detect language from title and description
        language = 'English'  # Default
        combined_text = f"{title} {description or ''}".lower()
        
        # Only detect language when explicitly stated that event is CONDUCTED in that language
        # Don't flag just because it mentions a culture (e.g., "Korean Treasures" = about Korean art, not in Korean)
        if re.search(r'(?:in|tour|conducted|presented|given|led)\s+mandarin|mandarin\s+(?:tour|language|導覽)|普通話|館藏精華導覽', combined_text, re.I):
            language = 'Mandarin'
        # Note: Don't detect language from culture names like "Korean", "Japanese", "Chinese" in titles
        
        # Build event dictionary
        event = {
            'title': title,
            'description': description or f"Exhibition at {VENUE_NAME}",
            'event_type': 'exhibition',
            'source_url': url,
            'organizer': VENUE_NAME,
            'social_media_platform': 'website',
            'social_media_url': url,
            'language': language,
        }
        
        # Hide non-English events by default
        if language != 'English':
            event['is_selected'] = False
        
        if date_range:
            event['start_date'] = date_range['start_date']
            event['end_date'] = date_range['end_date']
        
        if image_url:
            event['image_url'] = image_url
        
        return event
        
    except Exception as e:
        logger.warning(f"   ⚠️ Error scraping exhibition detail {url}: {type(e).__name__} - {str(e)[:100]}")
        return None


def scrape_asian_art_exhibitions(scraper=None) -> List[Dict]:
    """
    Scrape all exhibitions from Asian Art Museum exhibitions page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🔍 Scraping Asian Art Museum exhibitions from: {ASIAN_ART_EXHIBITIONS_URL}")
        try:
            response = scraper.get(ASIAN_ART_EXHIBITIONS_URL, timeout=(15, 45))
            response.raise_for_status()
        except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as timeout_error:
            logger.error(f"❌ Timeout error scraping Asian Art Museum exhibitions: {timeout_error}")
            logger.error(f"   URL: {ASIAN_ART_EXHIBITIONS_URL}")
            logger.error(f"   This may indicate the server is slow or unresponsive. Try again later.")
            return events
        except (ConnectionError, RequestException) as conn_error:
            logger.error(f"❌ Connection error scraping Asian Art Museum exhibitions: {conn_error}")
            logger.error(f"   URL: {ASIAN_ART_EXHIBITIONS_URL}")
            return events
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all exhibition items - they're in h3 headings
        exhibitions = soup.find_all('h3')
        
        processed_titles = set()
        skip_titles = ['the collections and archives', 'collection area', 'browse exhibitions']
        
        for h3 in exhibitions:
            # Get the title
            title_elem = h3.find('a') or h3
            title = title_elem.get_text(strip=True) if title_elem else h3.get_text(strip=True)
            
            if not title or len(title) < 5:
                continue
            
            # Skip section headings
            if title.lower() in skip_titles:
                continue
            
            # Skip if we've already processed this title
            if title in processed_titles:
                continue
            processed_titles.add(title)
            
            # Find the container that holds this exhibition
            container = h3.parent
            date_found = False
            image_found = False
            
            # Traverse up to find a container with date information and images
            for level in range(8):
                if not container:
                    break
                
                container_text = container.get_text()
                
                # Extract date information (only once)
                if not date_found:
                    # Check if this container has a date pattern
                    date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text)
                    if date_range_match or re.search(r'[A-Za-z]+\s+\d{1,2},?\s+20\d{2}', container_text):
                        # Found a container with the date
                        date_found = True
                
                # Extract image from listing page (only once)
                if not image_found:
                    imgs = container.find_all('img')
                    for img in imgs:
                        img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                        if img_src:
                            # Skip small icons/logos/generic images
                            skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg', 'site-header', 'nav-background', 'hero-background']
                            if any(pattern in img_src.lower() for pattern in skip_patterns):
                                continue
                            
                            # Check if it's a real image file
                            if any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                # Build full URL - we'll store this in listing_data
                                listing_image_url = urljoin(ASIAN_ART_BASE_URL, img_src)
                                image_found = True
                                break
                
                container = container.parent
            
            # Now extract date and other info
            date_text = None
            description = None
            image_url = listing_image_url  # Use listing image as starting point
            exhibition_url = None
            
            # Get the link URL if it exists
            link = h3.find('a', href=True)
            if link:
                href = link.get('href', '')
                if href:
                    exhibition_url = urljoin(ASIAN_ART_BASE_URL, href)
            
            # Extract date from container text - try structured HTML first
            date_text = None
            if container:
                # First, try to find structured date format (h3 with "Dates" or similar)
                dates_heading = container.find(['h3', 'h4', 'dt'], string=re.compile('Dates?', re.I))
                if dates_heading:
                    # Check next sibling
                    next_sibling = dates_heading.find_next_sibling()
                    if next_sibling:
                        date_text = next_sibling.get_text(strip=True)
                    # Check parent's siblings
                    if not date_text and dates_heading.parent:
                        siblings = dates_heading.parent.find_all(['div', 'p', 'span', 'li'], recursive=False)
                        for sibling in siblings:
                            sibling_text = sibling.get_text(strip=True)
                            if re.search(r'[A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}[–-]', sibling_text):
                                date_text = sibling_text
                                break
                
                # Fallback: look for date range pattern in container text
                if not date_text:
                    container_text = container.get_text()
                    # Look for date range pattern: "June 21, 2025 – November 30, 2025"
                    date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text)
                    if date_range_match:
                        date_text = date_range_match.group(0)
                    else:
                        # Try simpler pattern
                        date_simple_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text)
                        if date_simple_match:
                            date_text = date_simple_match.group(0)
                
                # Get description - look for paragraphs after the h3
                # Collect multiple paragraphs for better descriptions
                desc_paragraphs = []
                next_elem = h3.find_next_sibling()
                while next_elem and len(desc_paragraphs) < 3:  # Limit to 3 paragraphs
                    if next_elem.name == 'p':
                        text = next_elem.get_text(strip=True)
                        # Skip very short text or captions
                        if len(text) > 50 and not any(keyword in text.lower() for keyword in ['credit:', 'photo:', 'image:', 'courtesy of', '©']):
                            desc_paragraphs.append(text)
                    next_elem = next_elem.find_next_sibling()
                
                if desc_paragraphs:
                    description = ' '.join(desc_paragraphs)
                
                # If no description from siblings, look in container
                if not description:
                    # Look for all paragraphs in container
                    desc_paras = container.find_all('p')
                    desc_paragraphs = []
                    for desc_para in desc_paras[:3]:  # Limit to first 3 paragraphs
                        desc_text = desc_para.get_text(strip=True)
                        if len(desc_text) > 50 and not any(keyword in desc_text.lower() for keyword in ['credit:', 'photo:', 'image:', 'courtesy of', '©']):
                            desc_paragraphs.append(desc_text)
                    if desc_paragraphs:
                        description = ' '.join(desc_paragraphs)
            
            # If we found an exhibition URL, try to scrape more details
            if exhibition_url and exhibition_url not in [ASIAN_ART_EXHIBITIONS_URL, ASIAN_ART_EXHIBITIONS_URL + '/']:
                try:
                    detail_data = scrape_exhibition_detail(scraper, exhibition_url)
                    if detail_data:
                        # Merge detail data with what we found from listing page
                        # Detail page data takes precedence for dates (more accurate)
                        if detail_data.get('description') and not description:
                            description = detail_data['description']
                        # Use listing image if available, otherwise use detail page image
                        if not image_url and detail_data.get('image_url'):
                            image_url = detail_data['image_url']
                        # Detail page dates are more reliable - use them if available
                        if detail_data.get('start_date'):
                            # Format date range for parsing
                            start_date = detail_data.get('start_date')
                            end_date = detail_data.get('end_date', start_date)
                            if isinstance(start_date, date):
                                # Convert date objects to formatted strings for parse_date_range
                                from datetime import datetime
                                start_str = start_date.strftime('%B %d, %Y')
                                end_str = end_date.strftime('%B %d, %Y') if end_date else start_str
                                date_text = f"{start_str} – {end_str}"
                            else:
                                date_text = f"{start_date} – {end_date}"
                        elif not date_text and detail_data.get('start_date'):
                            # Fallback: use detail dates even if not formatted
                            date_text = f"{detail_data.get('start_date')} - {detail_data.get('end_date', '')}"
                except Exception as e:
                    logger.debug(f"   ⚠️ Error fetching exhibition detail {exhibition_url}: {e}")
            
            # Parse date range
            date_range = None
            if date_text:
                date_range = parse_date_range(date_text)
            
            # Build event dictionary
            event = {
                'title': title,
                'description': description or f"Exhibition at {VENUE_NAME}",
                'event_type': 'exhibition',
                'source_url': exhibition_url or ASIAN_ART_EXHIBITIONS_URL,
                'organizer': VENUE_NAME,
                'social_media_platform': 'website',
                'social_media_url': exhibition_url or ASIAN_ART_EXHIBITIONS_URL,
            }
            
            if date_range:
                event['start_date'] = date_range['start_date']
                event['end_date'] = date_range['end_date']
            else:
                # Default to today if no date found (ongoing exhibition)
                event['start_date'] = date.today()
            
            if image_url:
                event['image_url'] = image_url
            
            # Ensure language is set (defaults to English)
            event['language'] = event.get('language', 'English')
            
            events.append(event)
        
        logger.info(f"   ✅ Found {len(events)} exhibitions")
        
    except Exception as e:
        logger.error(f"❌ Error scraping Asian Art Museum exhibitions: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def parse_time(time_string: str) -> Optional[time]:
    """Parse 12-hour time string like '12:00 p.m.' or '2:30 pm' into time object"""
    if not time_string:
        return None
    
    time_string = time_string.strip().lower()
    
    # Pattern: "12:00 p.m." or "2:30 pm" or "12:00pm"
    time_pattern = r'(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)'
    match = re.search(time_pattern, time_string)
    
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        am_pm = match.group(3)
        
        # Convert to 24-hour format
        if 'pm' in am_pm and hour != 12:
            hour += 12
        elif 'am' in am_pm and hour == 12:
            hour = 0
        
        return time(hour, minute)
    
    return None


def parse_single_date(date_string: str) -> Optional[date]:
    """Parse single date string like 'December 5, 2025' or 'Friday, December 5, 2025'"""
    if not date_string:
        return None
    
    date_string = date_string.strip()
    
    # Pattern: "Friday, December 5, 2025" or "December 5, 2025"
    patterns = [
        r'([A-Za-z]+day,?\s+)?([A-Za-z]+)\s+(\d{1,2}),?\s+(20\d{2})',  # Friday, December 5, 2025
        r'([A-Za-z]+)\s+(\d{1,2}),?\s+(20\d{2})',  # December 5, 2025
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_string)
        if match:
            if len(match.groups()) == 4:
                month_str = match.group(2)
                day = int(match.group(3))
                year = int(match.group(4))
            else:
                month_str = match.group(1)
                day = int(match.group(2))
                year = int(match.group(3))
            
            try:
                return datetime.strptime(f"{month_str} {day} {year}", '%B %d %Y').date()
            except ValueError:
                try:
                    return datetime.strptime(f"{month_str} {day}, {year}", '%B %d, %Y').date()
                except ValueError:
                    pass
    
    return None


def scrape_event_detail(scraper, url: str, max_retries: int = 2) -> Optional[Dict]:
    """Scrape details from an individual event page with retry logic"""
    import time as time_module
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"   📄 Scraping event page: {url} (attempt {attempt + 1}/{max_retries})")
            # Use longer timeout: (connect timeout, read timeout) - increased for slow connections
            response = scraper.get(url, timeout=(15, 45))
            response.raise_for_status()
            break  # Success, exit retry loop
        except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as e:
            if attempt < max_retries - 1:
                wait_time = 2 * (attempt + 1)  # Exponential backoff: 2s, 4s
                logger.debug(f"   ⏳ Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                time_module.sleep(wait_time)
                continue
            else:
                logger.warning(f"   ⚠️ Timeout scraping event detail {url} after {max_retries} attempts: {type(e).__name__}")
                return None
        except (ConnectionError, RequestException) as e:
            if attempt < max_retries - 1:
                wait_time = 2 * (attempt + 1)
                logger.debug(f"   ⏳ Connection error on attempt {attempt + 1}, retrying in {wait_time}s...")
                time_module.sleep(wait_time)
                continue
            else:
                logger.warning(f"   ⚠️ Connection error scraping event detail {url} after {max_retries} attempts: {type(e).__name__}")
                return None
    
    try:
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = None
        title_elem = soup.find('h1') or soup.find('h2', class_=re.compile(r'title', re.I))
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        if not title:
            meta_title = soup.find('title')
            if meta_title:
                title = meta_title.get_text(strip=True)
        
        # Clean title: remove venue name suffix
        if title:
            from scripts.utils import clean_event_title
            title = clean_event_title(title)
        
        if not title:
            logger.debug(f"   ⚠️ Could not find title for {url}")
            return None
        
        # Extract description
        description = None
        desc_parts = []
        
        # Look for description in paragraphs
        for p in soup.find_all('p'):
            p_text = p.get_text(strip=True)
            if len(p_text) > 50 and p_text.lower() not in ['home', 'events', 'exhibitions', 'learn', 'visit']:
                desc_parts.append(p_text)
        
        if desc_parts:
            description = ' '.join(desc_parts[:3])
        
        if not description:
            desc_elem = soup.find('div', class_=re.compile(r'description|summary|intro|content', re.I))
            if desc_elem:
                description = desc_elem.get_text(strip=True)
        
        # Extract date and time
        # First, try to extract dates from structured HTML (h3/dt elements)
        date_text = None
        start_date = None
        end_date = None
        
        # Look for structured date format: h3 with "Dates" followed by date range
        dates_h3 = soup.find('h3', string=re.compile('^Dates?$', re.I))
        if dates_h3:
            # Check next sibling for date text
            next_sibling = dates_h3.find_next_sibling()
            if next_sibling:
                date_text = next_sibling.get_text(strip=True)
            # If not found, check parent's siblings
            if not date_text and dates_h3.parent:
                siblings = dates_h3.parent.find_all(['div', 'p', 'span'], recursive=False)
                for sibling in siblings:
                    sibling_text = sibling.get_text(strip=True)
                    # Check if it looks like a date range
                    if re.search(r'[A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}[–-]', sibling_text):
                        date_text = sibling_text
                        break
        
        # Also try dt/dd structure
        if not date_text:
            dates_dt = soup.find('dt', string=re.compile('Dates?', re.I))
            if dates_dt:
                dates_dd = dates_dt.find_next_sibling('dd')
                if dates_dd:
                    date_text = dates_dd.get_text(strip=True)
        
        # Parse date range if found
        if date_text:
            date_range = parse_date_range(date_text)
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
        
        page_text = soup.get_text()
        
        # Normalize text: add space between year and time (e.g., "20252:00" -> "2025 2:00")
        # This handles cases where date and time are concatenated
        page_text = re.sub(r'(20\d{2})([1-9]|1[0-2]:)', r'\1 \2', page_text)
        
        event_date = None
        start_time = None
        end_time = None
        location = None
        registration_required = False
        registration_url = None
        registration_info = None
        price = None
        
        # Look for date patterns: "Friday, December 5, 2025" or "December 5, 2025"
        date_patterns = [
            r'([A-Za-z]+day,?\s+[A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # Friday, December 5, 2025
            r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # December 5, 2025
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                event_date = parse_single_date(match.group(1))
                if event_date:
                    break
        
        # First, try to find a structured time range: "2:00 pm - 3:00 pm" or "2:00 pm–3:00 pm"
        time_range_pattern = r'\b([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\s*[–\-]\s*([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\b'
        time_range_match = re.search(time_range_pattern, page_text, re.I)
        
        if time_range_match:
            # Found a time range - extract both times
            start_hour = int(time_range_match.group(1))
            start_minute = int(time_range_match.group(2))
            start_am_pm = time_range_match.group(3)
            end_hour = int(time_range_match.group(4))
            end_minute = int(time_range_match.group(5))
            end_am_pm = time_range_match.group(6)
            
            # Convert start time to 24-hour format
            start_hour_24 = start_hour
            if 'pm' in start_am_pm.lower() and start_hour != 12:
                start_hour_24 = start_hour + 12
            elif 'am' in start_am_pm.lower() and start_hour == 12:
                start_hour_24 = 0
            
            # Convert end time to 24-hour format
            end_hour_24 = end_hour
            if 'pm' in end_am_pm.lower() and end_hour != 12:
                end_hour_24 = end_hour + 12
            elif 'am' in end_am_pm.lower() and end_hour == 12:
                end_hour_24 = 0
            
            if 0 <= start_hour_24 < 24 and 0 <= start_minute < 60:
                start_time = time(start_hour_24, start_minute)
            if 0 <= end_hour_24 < 24 and 0 <= end_minute < 60:
                end_time = time(end_hour_24, end_minute)
        else:
            # Fallback: Look for individual time patterns: "12:00 pm" or "2:30 p.m."
            # Only match valid hours (1-12) and minutes (00-59)
            time_pattern = r'\b([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\b'
            time_matches = re.findall(time_pattern, page_text, re.I)
            
            if time_matches:
                # Get first time as start time
                start_time_str = f"{time_matches[0][0]}:{time_matches[0][1]} {time_matches[0][2]}"
                start_time = parse_time(start_time_str)
                
                # If there's a second time, use it as end time
                if len(time_matches) > 1:
                    end_time_str = f"{time_matches[1][0]}:{time_matches[1][1]} {time_matches[1][2]}"
                    end_time = parse_time(end_time_str)
                elif start_time:
                    # Default to 1 hour duration, but ensure valid time
                    end_hour = start_time.hour + 1
                    if end_hour >= 24:
                        end_hour = 23
                        end_minute = 59
                    elif end_hour == 24:
                        end_hour = 23
                        end_minute = 59
                    else:
                        end_minute = start_time.minute
                    
                    # Ensure valid time object
                    if 0 <= end_hour < 24 and 0 <= end_minute < 60:
                        end_time = time(end_hour, end_minute)
        
        # Extract location - look for specific venues and general location patterns
        location = None
        
        # First, look for specific Asian Art Museum venues
        specific_venues = [
            r'Meyer\s+Auditorium',
            r'Freer\s+Gallery',
            r'Sackler\s+Gallery',
            r'West\s+Building',
            r'East\s+Building',
            r'Arthur\s+M\.\s+Sackler\s+Gallery',
            r'Charles\s+Lang\s+Freer\s+Gallery'
        ]
        
        for venue_pattern in specific_venues:
            venue_match = re.search(venue_pattern, page_text, re.I)
            if venue_match:
                location = venue_match.group(0).strip()
                break
        
        # If no specific venue found, look for location patterns
        if not location:
            location_keywords = ['location', 'meeting point', 'venue', 'where', 'held at', 'taking place']
            for keyword in location_keywords:
                # Pattern 1: "Location: Meyer Auditorium"
                location_match = re.search(rf'{keyword}:\s*([^\n\.]+)', page_text, re.I)
                if location_match:
                    location = location_match.group(1).strip()
                    # Clean up location (remove extra words)
                    location = re.sub(r'^(at|in|the)\s+', '', location, flags=re.I).strip()
                    if location and len(location) > 3:
                        break
        
        # Also check for location in structured data or specific HTML elements
        if not location:
            # Look for location in meta tags or structured data
            location_elem = soup.find('meta', property=re.compile(r'location|venue', re.I))
            if location_elem:
                location = location_elem.get('content', '').strip()
            
            # Look for location in headings or specific divs
            if not location:
                for tag in soup.find_all(['h2', 'h3', 'div'], class_=re.compile(r'location|venue|place', re.I)):
                    tag_text = tag.get_text(strip=True)
                    if tag_text and len(tag_text) < 100:
                        location = tag_text
                        break
        
        # Extract registration info and ticket links
        registration_required = False
        registration_info = None
        
        # First check for explicit "no registration" or "walk-up only" - these should NOT require registration
        no_registration_patterns = [
            r'no\s+registration',
            r'walk-up\s+only',
            r'no\s+tickets?\s+(?:required|needed)',
            r'drop-in',
            r'no\s+rsvp'
        ]
        
        has_no_registration = any(re.search(pattern, page_text, re.I) for pattern in no_registration_patterns)
        
        # Only set registration_required if registration is mentioned AND it's not explicitly "no registration"
        if not has_no_registration:
            # Check if registration is mentioned
            if re.search(r'registration\s+(?:required|recommended|suggested)|register\s+(?:in\s+)?advance|rsvp|register\s+(?:for|to)', page_text, re.I):
                registration_required = True
                registration_info = 'Registration may be required. Please check the event page for details.'
                
                # Look for specific registration text to extract more detail
                reg_info_match = re.search(r'(register\s+(?:in\s+)?advance\s*(?:\(recommended\))?)|(registration\s+(?:is\s+)?(?:required|recommended|suggested))', page_text, re.I)
                if reg_info_match:
                    registration_info = reg_info_match.group(0).strip()
        
        # Look for registration/ticket URLs - check multiple patterns
        # BUT: Only set registration_required if we haven't already determined it's "no registration"
        # Pattern 1: Links with register/rsvp/ticket in href or text
        if not has_no_registration:
            reg_link = soup.find('a', href=re.compile(r'register|rsvp|ticket|eventbrite|eventive|tix|ticketmaster', re.I))
            if reg_link:
                registration_url = urljoin(ASIAN_ART_BASE_URL, reg_link.get('href', ''))
                registration_required = True
            
            # Pattern 2: Check link text for ticket/register keywords
            if not registration_url:
                for link in soup.find_all('a', href=True):
                    link_text = link.get_text(strip=True).lower()
                    href = link.get('href', '').lower()
                    if any(keyword in link_text for keyword in ['ticket', 'register', 'rsvp', 'reserve', 'book']) or \
                       any(keyword in href for keyword in ['ticket', 'register', 'rsvp', 'eventive', 'eventbrite', 'tix']):
                        registration_url = link.get('href', '')
                        # Make absolute URL if relative
                        if registration_url and not registration_url.startswith('http'):
                            registration_url = urljoin(ASIAN_ART_BASE_URL, registration_url)
                        registration_required = True
                        break
            
            # Pattern 3: Look for eventive.org or other ticket platform links specifically
            if not registration_url:
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if 'eventive.org' in href or 'eventbrite.com' in href or 'ticketmaster.com' in href or 'tix' in href.lower():
                        registration_url = href
                        if not registration_url.startswith('http'):
                            registration_url = urljoin(ASIAN_ART_BASE_URL, registration_url)
                        registration_required = True
                        break
        
        # Extract price/cost - look for "Free" or pricing information
        price = None
        
        # Pattern 1: "Free. Register in advance" or "Free, Register" etc.
        free_match = re.search(r'\b(free)\b[.,;]?\s*(?:register|admission)?', page_text, re.I)
        if free_match:
            price = 0.0
        
        # Pattern 2: Standard price patterns
        if price is None:
            cost_match = re.search(r'(?:cost|price|admission|ticket)[:\s]+([^\n]+)', page_text, re.I)
            if cost_match:
                cost_text = cost_match.group(1).strip()
                if 'free' in cost_text.lower():
                    price = 0.0
                else:
                    # Try to extract numeric price
                    price_match = re.search(r'\$?(\d+(?:\.\d{2})?)', cost_text)
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                        except ValueError:
                            pass
        
        # Detect language from title and description
        language = 'English'  # Default
        combined_text = f"{title} {description or ''}".lower()
        
        # Only detect language when explicitly stated that event is CONDUCTED in that language
        # Don't flag just because it mentions a culture (e.g., "Korean Treasures" = about Korean art, not in Korean)
        if re.search(r'(?:in|tour|conducted|presented|given|led)\s+mandarin|mandarin\s+(?:tour|language|導覽)|普通話|館藏精華導覽', combined_text, re.I):
            language = 'Mandarin'
        # Note: Don't detect language from culture names like "Korean", "Japanese", "Chinese" in titles
        
        # Determine event type - check for film, tour, and other keywords in title, description, and page content
        determined_event_type = 'event'  # default
        title_lower = title.lower() if title else ''
        desc_lower = (description or '').lower()
        page_text_lower = page_text.lower()
        combined_text = f"{title_lower} {desc_lower} {page_text_lower}"
        
        # Check for tour indicators FIRST (tours are more common and should be detected early)
        tour_keywords = ['tour', 'tours', 'guided tour', 'walking tour', 'collection tour', 'docent-led', 'docent led']
        if any(keyword in combined_text for keyword in tour_keywords):
            determined_event_type = 'tour'
        
        # Check for performance indicators (only if not already identified as tour)
        if determined_event_type == 'event':
            # Check if "Performances" appears in Topics section (most reliable)
            has_performances_topic = re.search(r'topics[:\s]+.*\bperformances?\b', page_text_lower, re.I)
            if has_performances_topic:
                determined_event_type = 'performance'
            # Check for performance keywords
            elif any(keyword in combined_text for keyword in ['performance', 'performances', 'concert', 'recital', 'ensemble', 'trio', 'quartet', 'musician', 'musicians']):
                determined_event_type = 'performance'
        
        # Check for film indicators - must be very specific to avoid false positives
        # Primary indicator: "Films" in Topics section (most reliable)
        has_films_topic = re.search(r'topics[:\s]+.*\bfilms?\b', page_text_lower, re.I)
        has_film_series = re.search(r'event\s+series[:\s]+.*\b(?:film|animated\s+adventures)\b', page_text_lower, re.I)
        
        # Strong film-specific patterns (very specific to films)
        has_dcp_format = re.search(r'format:\s*dcp\b', combined_text, re.I)  # DCP is film-specific
        has_film_length = re.search(r'length:\s*\d+\s*min\b', combined_text, re.I)  # "Length: 77 min" is film-specific
        has_directors_field = re.search(r'\bdirector[s]?:\s*[A-Z]', combined_text, re.I)  # "Directors: Name" is film-specific
        has_countries_field = re.search(r'\bcountries?:\s*[A-Z]', combined_text, re.I)  # "Countries: France, Belgium" is film-specific
        has_released_field = re.search(r'\breleased:\s*\d{4}\b', combined_text, re.I)  # "Released: 2025" is film-specific
        has_film_screening = re.search(r'\b(?:film|movie)\s+screening\b', combined_text, re.I)  # "film screening" is specific
        
        # Count strong film indicators
        strong_film_indicators = sum([
            bool(has_films_topic),
            bool(has_film_series),
            bool(has_dcp_format),
            bool(has_film_length),
            bool(has_directors_field),
            bool(has_countries_field),
            bool(has_released_field),
            bool(has_film_screening)
        ])
        
        # Only categorize as film if we have strong evidence (Topics/Series OR multiple strong indicators)
        # But only if not already identified as tour or performance
        if determined_event_type == 'event':
            if has_films_topic or has_film_series:
                # Most reliable: "Films" in Topics or film-related Event Series
                determined_event_type = 'film'
            elif strong_film_indicators >= 2:
                # Need at least 2 strong indicators (e.g., "Format: DCP" + "Length: 77 min" + "Directors:")
                determined_event_type = 'film'
            elif has_dcp_format and (has_film_length or has_directors_field):
                # DCP format is very specific to films, combined with length or directors
                determined_event_type = 'film'
        
        # Build event dictionary
        event = {
            'title': title,
            'description': description or f"Event at {VENUE_NAME}",
            'event_type': determined_event_type,
            'source_url': url,
            'organizer': VENUE_NAME,
            'social_media_platform': 'website',
            'social_media_url': url,
        }
        
        # Use structured date extraction if available, otherwise fall back to event_date
        if start_date and end_date:
            event['start_date'] = start_date
            event['end_date'] = end_date
        elif start_date:
            event['start_date'] = start_date
            event['end_date'] = start_date
        elif event_date:
            event['start_date'] = event_date
            event['end_date'] = event_date
        
        if start_time:
            # Store as time object for database
            event['start_time'] = start_time
        
        if end_time:
            # Store as time object for database
            event['end_time'] = end_time
        
        # Detect if event is online/virtual
        is_online = False
        
        # Check location for online indicators
        if location:
            location_lower = location.lower()
            online_location_indicators = ['zoom', 'virtual', 'online', 'webinar', 'livestream', 'live stream', 'webcast']
            if any(indicator in location_lower for indicator in online_location_indicators):
                is_online = True
            event['location'] = location
            event['meeting_point'] = location
        
        # Check title for online indicators
        if title and not is_online:
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ['virtual', 'online', 'webinar', 'livestream', 'live stream']):
                is_online = True
        
        # Check description for online indicators
        if description and not is_online:
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
                'webcast',
            ]
            if any(indicator in desc_lower for indicator in online_indicators):
                is_online = True
        
        # Check page text for online indicators (as fallback)
        if not is_online:
            page_text_lower = page_text.lower()
            online_indicators = [
                'online event',
                'virtual event',
                'zoom',
                'webinar',
                'livestream',
                'live stream',
                'webcast',
            ]
            if any(indicator in page_text_lower for indicator in online_indicators):
                is_online = True
        
        # Set is_online flag
        event['is_online'] = is_online
        
        # For online events, always set location to "Online" (override any physical location)
        if is_online:
            event['location'] = 'Online'
            event['meeting_point'] = 'Online'
        elif location:
            event['location'] = location
            event['meeting_point'] = location
        
        if registration_required:
            event['is_registration_required'] = True
            if registration_url:
                event['registration_url'] = registration_url
            if registration_info:
                event['registration_info'] = registration_info
        
        if price is not None:
            event['price'] = float(price)
            event['admission_price'] = float(price)
        
        # Add language field (ensure it's not None)
        event['language'] = language or 'English'
        
        # Hide non-English events by default
        if event['language'] != 'English':
            event['is_selected'] = False
        
        return event
        
    except Exception as e:
        logger.warning(f"   ⚠️ Error scraping event detail {url}: {type(e).__name__} - {str(e)[:100]}")
        return None


def scrape_asian_art_events(scraper=None) -> List[Dict]:
    """
    Scrape events from Asian Art Museum events search page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        events_search_url = 'https://asia.si.edu/whats-on/events/search/'
        logger.info(f"🔍 Scraping Asian Art Museum events from: {events_search_url}")
        try:
            response = scraper.get(events_search_url, timeout=(15, 45))
            response.raise_for_status()
        except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as timeout_error:
            logger.error(f"❌ Timeout error scraping Asian Art Museum events: {timeout_error}")
            logger.error(f"   URL: {events_search_url}")
            logger.error(f"   This may indicate the server is slow or unresponsive. Try again later.")
            return events
        except (ConnectionError, RequestException) as conn_error:
            logger.error(f"❌ Connection error scraping Asian Art Museum events: {conn_error}")
            logger.error(f"   URL: {events_search_url}")
            return events
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find event links - they're in h3 headings with links to /whats-on/events/search/event:ID
        event_links = soup.find_all('a', href=re.compile(r'/whats-on/events/search/event:', re.I))
        
        processed_urls = set()
        
        for link in event_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Build full URL
            full_url = urljoin(ASIAN_ART_BASE_URL, href)
            
            # Skip if we've already processed this URL
            if full_url in processed_urls:
                continue
            processed_urls.add(full_url)
            
            # Extract basic info from listing page first
            listing_data = {}
            h3 = link.find_parent('h3') or (link.parent if link.parent and link.parent.name == 'h3' else None)
            
            if h3:
                title = link.get_text(strip=True) or h3.get_text(strip=True)
                listing_data['title'] = title
                
                # Get container around this event to find date/time
                container = h3.parent
                date_found = False
                time_found = False
                image_found = False
                
                for level in range(8):
                    if not container:
                        break
                    
                    container_text = container.get_text()
                    
                    # Normalize text: add space between year and time
                    container_text = re.sub(r'(20\d{2})([1-9]|1[0-2]:)', r'\1 \2', container_text)
                    
                    # Extract date from listing (only once)
                    if not date_found:
                        date_patterns = [
                            r'([A-Za-z]+day,?\s+[A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # Friday, December 5, 2025
                            r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # December 5, 2025
                        ]
                        for pattern in date_patterns:
                            date_match = re.search(pattern, container_text, re.I)
                            if date_match:
                                event_date = parse_single_date(date_match.group(1))
                                if event_date:
                                    listing_data['start_date'] = event_date
                                    listing_data['end_date'] = event_date
                                    date_found = True
                                    break
                    
                    # Extract time range from listing (only once)
                    if not time_found:
                        time_range_pattern = r'\b([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\s*[–\-]\s*([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\b'
                        time_range_match = re.search(time_range_pattern, container_text, re.I)
                        
                        if time_range_match:
                            # Found time range - extract both times
                            start_hour = int(time_range_match.group(1))
                            start_minute = int(time_range_match.group(2))
                            start_am_pm = time_range_match.group(3)
                            end_hour = int(time_range_match.group(4))
                            end_minute = int(time_range_match.group(5))
                            end_am_pm = time_range_match.group(6)
                            
                            # Convert start time to 24-hour format
                            start_hour_24 = start_hour
                            if 'pm' in start_am_pm.lower() and start_hour != 12:
                                start_hour_24 = start_hour + 12
                            elif 'am' in start_am_pm.lower() and start_hour == 12:
                                start_hour_24 = 0
                            
                            # Convert end time to 24-hour format
                            end_hour_24 = end_hour
                            if 'pm' in end_am_pm.lower() and end_hour != 12:
                                end_hour_24 = end_hour + 12
                            elif 'am' in end_am_pm.lower() and end_hour == 12:
                                end_hour_24 = 0
                            
                            if 0 <= start_hour_24 < 24 and 0 <= start_minute < 60:
                                listing_data['start_time'] = time(start_hour_24, start_minute)
                            if 0 <= end_hour_24 < 24 and 0 <= end_minute < 60:
                                listing_data['end_time'] = time(end_hour_24, end_minute)
                            time_found = True
                    
                    # Extract image from listing page (only once)
                    if not image_found:
                        imgs = container.find_all('img')
                        for img in imgs:
                            img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                            if img_src:
                                # Skip small icons/logos
                                skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg', 'site-header', 'nav-background']
                                if any(pattern in img_src.lower() for pattern in skip_patterns):
                                    continue
                                
                                # Check if it's a real image file
                                if any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'trumba.com' in img_src.lower():
                                    # Build full URL
                                    image_url = urljoin(ASIAN_ART_BASE_URL, img_src)
                                    listing_data['image_url'] = image_url
                                    image_found = True
                                    break
                    
                    # Continue searching even if we found date/time, but break if we found everything
                    if date_found and time_found and image_found:
                        break
                    
                    container = container.parent if container else None
            
                # Scrape individual event page for full details
                # Use listing data as fallback if detail page scraping fails
                event_data = scrape_event_detail(scraper, full_url)
                
                if event_data:
                    # Always ensure URL is set to the canonical full_url (ensures consistency)
                    event_data['source_url'] = full_url
                    event_data['social_media_url'] = full_url
                    
                    # Merge listing data with detail page data (listing takes precedence for dates/times/images if available)
                    if listing_data.get('start_date'):
                        event_data['start_date'] = listing_data['start_date']
                        event_data['end_date'] = listing_data['end_date']
                    if listing_data.get('start_time'):
                        event_data['start_time'] = listing_data['start_time']
                    if listing_data.get('end_time'):
                        event_data['end_time'] = listing_data['end_time']
                    if listing_data.get('title'):
                        event_data['title'] = listing_data['title']  # Use listing title if available
                    
                    # Use listing page image if available, otherwise use detail page image
                    if listing_data.get('image_url'):
                        event_data['image_url'] = listing_data['image_url']
                    
                    events.append(event_data)
                elif listing_data.get('title'):
                    # If detail page scraping failed but we have listing data, use that
                    # Determine event type from title
                    title_lower = listing_data.get('title', '').lower()
                    determined_event_type = 'event'  # default
                    tour_keywords = ['tour', 'tours', 'guided tour', 'walking tour', 'collection tour', 'docent-led', 'docent led']
                    if any(keyword in title_lower for keyword in tour_keywords):
                        determined_event_type = 'tour'
                    
                    listing_data['source_url'] = full_url
                    listing_data['event_type'] = determined_event_type
                    listing_data['organizer'] = VENUE_NAME
                    listing_data['social_media_platform'] = 'website'
                    listing_data['social_media_url'] = full_url
                    listing_data['description'] = f"Event at {VENUE_NAME}"
                    listing_data['language'] = 'English'
                    events.append(listing_data)
        
        logger.info(f"   ✅ Found {len(events)} events")
        
    except Exception as e:
        logger.error(f"❌ Error scraping Asian Art Museum events: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_asian_art_films(scraper=None) -> List[Dict]:
    """
    Scrape film events from Asian Art Museum films page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🎬 Scraping Asian Art Museum films from: {ASIAN_ART_FILMS_URL}")
        try:
            response = scraper.get(ASIAN_ART_FILMS_URL, timeout=(15, 45))
            response.raise_for_status()
        except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as timeout_error:
            logger.error(f"❌ Timeout error scraping Asian Art Museum films: {timeout_error}")
            logger.error(f"   URL: {ASIAN_ART_FILMS_URL}")
            logger.error(f"   This may indicate the server is slow or unresponsive. Try again later.")
            return events
        except (ConnectionError, RequestException) as conn_error:
            logger.error(f"❌ Connection error scraping Asian Art Museum films: {conn_error}")
            logger.error(f"   URL: {ASIAN_ART_FILMS_URL}")
            return events
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find event links - they're in h3 headings with links to /whats-on/events/search/event:ID
        event_links = soup.find_all('a', href=re.compile(r'/whats-on/events/search/event:', re.I))
        
        processed_urls = set()
        
        for link in event_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Build full URL
            full_url = urljoin(ASIAN_ART_BASE_URL, href)
            
            # Skip if we've already processed this URL
            if full_url in processed_urls:
                continue
            processed_urls.add(full_url)
            
            # Extract basic info from listing page first
            listing_data = {}
            h3 = link.find_parent('h3') or (link.parent if link.parent and link.parent.name == 'h3' else None)
            
            if h3:
                title = link.get_text(strip=True) or h3.get_text(strip=True)
                listing_data['title'] = title
                
                # Get container around this event to find date/time
                container = h3.parent
                date_found = False
                time_found = False
                image_found = False
                
                for level in range(8):
                    if not container:
                        break
                    
                    container_text = container.get_text()
                    
                    # Normalize text: add space between year and time
                    container_text = re.sub(r'(20\d{2})([1-9]|1[0-2]:)', r'\1 \2', container_text)
                    
                    # Extract date from listing (only once)
                    if not date_found:
                        date_patterns = [
                            r'([A-Za-z]+day,?\s+[A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # Friday, December 5, 2025
                            r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # December 5, 2025
                        ]
                        for pattern in date_patterns:
                            date_match = re.search(pattern, container_text, re.I)
                            if date_match:
                                event_date = parse_single_date(date_match.group(1))
                                if event_date:
                                    listing_data['start_date'] = event_date
                                    listing_data['end_date'] = event_date
                                    date_found = True
                                    break
                    
                    # Extract time range from listing (only once)
                    if not time_found:
                        time_range_pattern = r'\b([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\s*[–\-]\s*([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\b'
                        time_range_match = re.search(time_range_pattern, container_text, re.I)
                        
                        if time_range_match:
                            # Found time range - extract both times
                            start_hour = int(time_range_match.group(1))
                            start_minute = int(time_range_match.group(2))
                            start_am_pm = time_range_match.group(3)
                            end_hour = int(time_range_match.group(4))
                            end_minute = int(time_range_match.group(5))
                            end_am_pm = time_range_match.group(6)
                            
                            # Convert start time to 24-hour format
                            start_hour_24 = start_hour
                            if 'pm' in start_am_pm.lower() and start_hour != 12:
                                start_hour_24 = start_hour + 12
                            elif 'am' in start_am_pm.lower() and start_hour == 12:
                                start_hour_24 = 0
                            
                            # Convert end time to 24-hour format
                            end_hour_24 = end_hour
                            if 'pm' in end_am_pm.lower() and end_hour != 12:
                                end_hour_24 = end_hour + 12
                            elif 'am' in end_am_pm.lower() and end_hour == 12:
                                end_hour_24 = 0
                            
                            if 0 <= start_hour_24 < 24 and 0 <= start_minute < 60:
                                listing_data['start_time'] = time(start_hour_24, start_minute)
                            if 0 <= end_hour_24 < 24 and 0 <= end_minute < 60:
                                listing_data['end_time'] = time(end_hour_24, end_minute)
                            time_found = True
                    
                    # Extract image from listing page (only once)
                    if not image_found:
                        imgs = container.find_all('img')
                        for img in imgs:
                            img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                            if img_src:
                                # Skip small icons/logos
                                skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg', 'site-header', 'nav-background']
                                if any(pattern in img_src.lower() for pattern in skip_patterns):
                                    continue
                                
                                # Check if it's a real image file
                                if any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'trumba.com' in img_src.lower():
                                    # Build full URL
                                    image_url = urljoin(ASIAN_ART_BASE_URL, img_src)
                                    listing_data['image_url'] = image_url
                                    image_found = True
                                    break
                    
                    # Continue searching even if we found date/time, but break if we found everything
                    if date_found and time_found and image_found:
                        break
                    
                    container = container.parent if container else None
            
            # Scrape individual event page for full details
            # Use listing data as fallback if detail page scraping fails
            event_data = scrape_event_detail(scraper, full_url)
            
            if event_data:
                # Set event type to 'film'
                event_data['event_type'] = 'film'
                
                # Always ensure URL is set to the canonical full_url (ensures consistency)
                event_data['source_url'] = full_url
                event_data['social_media_url'] = full_url
                
                # Merge listing data with detail page data (listing takes precedence for dates/times/images if available)
                if listing_data.get('start_date'):
                    event_data['start_date'] = listing_data['start_date']
                    event_data['end_date'] = listing_data['end_date']
                if listing_data.get('start_time'):
                    event_data['start_time'] = listing_data['start_time']
                if listing_data.get('end_time'):
                    event_data['end_time'] = listing_data['end_time']
                if listing_data.get('title'):
                    event_data['title'] = listing_data['title']  # Use listing title if available
                
                # Use listing page image if available, otherwise use detail page image
                if listing_data.get('image_url'):
                    event_data['image_url'] = listing_data['image_url']
                
                events.append(event_data)
            elif listing_data.get('title'):
                # If detail page scraping failed but we have listing data, use that
                listing_data['source_url'] = full_url
                listing_data['event_type'] = 'film'
                listing_data['organizer'] = VENUE_NAME
                listing_data['social_media_platform'] = 'website'
                listing_data['social_media_url'] = full_url
                listing_data['description'] = f"Film event at {VENUE_NAME}"
                listing_data['language'] = 'English'
                events.append(listing_data)
        
        logger.info(f"   ✅ Found {len(events)} film events")
        
    except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as timeout_error:
        logger.error(f"❌ Timeout error scraping Asian Art Museum films: {timeout_error}")
        logger.error(f"   URL: {ASIAN_ART_FILMS_URL}")
        logger.error(f"   This may indicate the server is slow or unresponsive. Try again later.")
    except (ConnectionError, RequestException) as conn_error:
        logger.error(f"❌ Connection error scraping Asian Art Museum films: {conn_error}")
        logger.error(f"   URL: {ASIAN_ART_FILMS_URL}")
    except Exception as e:
        logger.error(f"❌ Error scraping Asian Art Museum films: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_asian_art_performances(scraper=None) -> List[Dict]:
    """
    Scrape performance events from Asian Art Museum performances page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🎭 Scraping Asian Art Museum performances from: {ASIAN_ART_PERFORMANCES_URL}")
        try:
            response = scraper.get(ASIAN_ART_PERFORMANCES_URL, timeout=(15, 45))
            response.raise_for_status()
        except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as timeout_error:
            logger.error(f"❌ Timeout error scraping Asian Art Museum performances: {timeout_error}")
            logger.error(f"   URL: {ASIAN_ART_PERFORMANCES_URL}")
            logger.error(f"   This may indicate the server is slow or unresponsive. Try again later.")
            return events
        except (ConnectionError, RequestException) as conn_error:
            logger.error(f"❌ Connection error scraping Asian Art Museum performances: {conn_error}")
            logger.error(f"   URL: {ASIAN_ART_PERFORMANCES_URL}")
            return events
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find event links - they're in h3 headings with links to /whats-on/events/search/event:ID
        event_links = soup.find_all('a', href=re.compile(r'/whats-on/events/search/event:', re.I))
        
        processed_urls = set()
        
        for link in event_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Build full URL
            full_url = urljoin(ASIAN_ART_BASE_URL, href)
            
            # Skip if we've already processed this URL
            if full_url in processed_urls:
                continue
            processed_urls.add(full_url)
            
            # Extract basic info from listing page first
            listing_data = {}
            h3 = link.find_parent('h3') or (link.parent if link.parent and link.parent.name == 'h3' else None)
            
            if h3:
                title = link.get_text(strip=True) or h3.get_text(strip=True)
                listing_data['title'] = title
                
                # Get container around this event to find date/time
                container = h3.parent
                date_found = False
                time_found = False
                image_found = False
                
                for level in range(8):
                    if not container:
                        break
                    
                    container_text = container.get_text()
                    
                    # Normalize text: add space between year and time
                    container_text = re.sub(r'(20\d{2})([1-9]|1[0-2]:)', r'\1 \2', container_text)
                    
                    # Extract date from listing (only once)
                    if not date_found:
                        date_patterns = [
                            r'([A-Za-z]+day,?\s+[A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # Friday, December 5, 2025
                            r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # December 5, 2025
                        ]
                        for pattern in date_patterns:
                            date_match = re.search(pattern, container_text, re.I)
                            if date_match:
                                event_date = parse_single_date(date_match.group(1))
                                if event_date:
                                    listing_data['start_date'] = event_date
                                    listing_data['end_date'] = event_date
                                    date_found = True
                                    break
                    
                    # Extract time range from listing (only once)
                    if not time_found:
                        time_range_pattern = r'\b([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\s*[–\-]\s*([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\b'
                        time_range_match = re.search(time_range_pattern, container_text, re.I)
                        
                        if time_range_match:
                            # Found time range - extract both times
                            start_hour = int(time_range_match.group(1))
                            start_minute = int(time_range_match.group(2))
                            start_am_pm = time_range_match.group(3)
                            end_hour = int(time_range_match.group(4))
                            end_minute = int(time_range_match.group(5))
                            end_am_pm = time_range_match.group(6)
                            
                            # Convert start time to 24-hour format
                            start_hour_24 = start_hour
                            if 'pm' in start_am_pm.lower() and start_hour != 12:
                                start_hour_24 = start_hour + 12
                            elif 'am' in start_am_pm.lower() and start_hour == 12:
                                start_hour_24 = 0
                            
                            # Convert end time to 24-hour format
                            end_hour_24 = end_hour
                            if 'pm' in end_am_pm.lower() and end_hour != 12:
                                end_hour_24 = end_hour + 12
                            elif 'am' in end_am_pm.lower() and end_hour == 12:
                                end_hour_24 = 0
                            
                            if 0 <= start_hour_24 < 24 and 0 <= start_minute < 60:
                                listing_data['start_time'] = time(start_hour_24, start_minute)
                            if 0 <= end_hour_24 < 24 and 0 <= end_minute < 60:
                                listing_data['end_time'] = time(end_hour_24, end_minute)
                            time_found = True
                    
                    # Extract image from listing page (only once)
                    if not image_found:
                        imgs = container.find_all('img')
                        for img in imgs:
                            img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                            if img_src:
                                # Skip small icons/logos
                                skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg', 'site-header', 'nav-background']
                                if any(pattern in img_src.lower() for pattern in skip_patterns):
                                    continue
                                
                                # Check if it's a real image file
                                if any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'trumba.com' in img_src.lower():
                                    # Build full URL
                                    image_url = urljoin(ASIAN_ART_BASE_URL, img_src)
                                    listing_data['image_url'] = image_url
                                    image_found = True
                                    break
                    
                    # Continue searching even if we found date/time, but break if we found everything
                    if date_found and time_found and image_found:
                        break
                    
                    container = container.parent if container else None
            
            # Scrape individual event page for full details
            # Use listing data as fallback if detail page scraping fails
            event_data = scrape_event_detail(scraper, full_url)
            
            if event_data:
                # Set event type to 'performance'
                event_data['event_type'] = 'performance'
                
                # Always ensure URL is set to the canonical full_url (ensures consistency)
                event_data['source_url'] = full_url
                event_data['social_media_url'] = full_url
                
                # Merge listing data with detail page data (listing takes precedence for dates/times/images if available)
                if listing_data.get('start_date'):
                    event_data['start_date'] = listing_data['start_date']
                    event_data['end_date'] = listing_data['end_date']
                if listing_data.get('start_time'):
                    event_data['start_time'] = listing_data['start_time']
                if listing_data.get('end_time'):
                    event_data['end_time'] = listing_data['end_time']
                if listing_data.get('title'):
                    event_data['title'] = listing_data['title']  # Use listing title if available
                
                # Use listing page image if available, otherwise use detail page image
                if listing_data.get('image_url'):
                    event_data['image_url'] = listing_data['image_url']
                
                events.append(event_data)
            elif listing_data.get('title'):
                # If detail page scraping failed but we have listing data, use that
                listing_data['source_url'] = full_url
                listing_data['event_type'] = 'performance'
                listing_data['organizer'] = VENUE_NAME
                listing_data['social_media_platform'] = 'website'
                listing_data['social_media_url'] = full_url
                listing_data['description'] = f"Performance event at {VENUE_NAME}"
                listing_data['language'] = 'English'
                events.append(listing_data)
        
        logger.info(f"   ✅ Found {len(events)} performance events")
        
    except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as timeout_error:
        logger.error(f"❌ Timeout error scraping Asian Art Museum performances: {timeout_error}")
        logger.error(f"   URL: {ASIAN_ART_PERFORMANCES_URL}")
        logger.error(f"   This may indicate the server is slow or unresponsive. Try again later.")
    except (ConnectionError, RequestException) as conn_error:
        logger.error(f"❌ Connection error scraping Asian Art Museum performances: {conn_error}")
        logger.error(f"   URL: {ASIAN_ART_PERFORMANCES_URL}")
    except Exception as e:
        logger.error(f"❌ Error scraping Asian Art Museum performances: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_all_asian_art_events() -> List[Dict]:
    """
    Scrape all events from Asian Art Museum
    Returns combined list of all event dictionaries
    """
    all_events = []
    
    # Total steps: Exhibitions, Events, Films, Performances = 4 steps
    total_steps = 4
    
    try:
        scraper = create_scraper()
        
        # Scrape exhibitions
        try:
            update_scraping_progress(1, total_steps, "Scraping exhibitions...", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info("🔍 Scraping exhibitions...")
            exhibitions = scrape_asian_art_exhibitions(scraper)
            all_events.extend(exhibitions)
            update_scraping_progress(1, total_steps, f"✅ Found {len(exhibitions)} exhibitions", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info(f"   ✅ Found {len(exhibitions)} exhibitions")
        except Exception as e:
            logger.error(f"   ❌ Error scraping exhibitions: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue with other event types even if exhibitions fail
        
        # Scrape events (talks, tours, programs)
        try:
            update_scraping_progress(2, total_steps, "Scraping events (talks, tours, programs)...", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info("🔍 Scraping events...")
            events = scrape_asian_art_events(scraper)
            all_events.extend(events)
            update_scraping_progress(2, total_steps, f"✅ Found {len(events)} events", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info(f"   ✅ Found {len(events)} events")
        except Exception as e:
            logger.error(f"   ❌ Error scraping events: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if events fail
        
        # Scrape films
        try:
            update_scraping_progress(3, total_steps, "Scraping films...", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info("🔍 Scraping films...")
            films = scrape_asian_art_films(scraper)
            all_events.extend(films)
            update_scraping_progress(3, total_steps, f"✅ Found {len(films)} films", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info(f"   ✅ Found {len(films)} films")
        except Exception as e:
            logger.error(f"   ❌ Error scraping films: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if films fail
        
        # Scrape performances
        try:
            update_scraping_progress(4, total_steps, "Scraping performances...", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info("🔍 Scraping performances...")
            performances = scrape_asian_art_performances(scraper)
            all_events.extend(performances)
            update_scraping_progress(4, total_steps, f"✅ Found {len(performances)} performances", events_found=len(all_events), venue_name=VENUE_NAME)
            logger.info(f"   ✅ Found {len(performances)} performances")
        except Exception as e:
            logger.error(f"   ❌ Error scraping performances: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if performances fail
        
        logger.info(f"✅ Total Asian Art Museum events scraped: {len(all_events)}")
        
    except Exception as e:
        logger.error(f"Error scraping Asian Art Museum events: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return all_events


def create_events_in_database(events: List[Dict]) -> tuple:
    """
    Create or update events in the database
    Uses shared event_database_handler for common logic.
    Returns tuple of (created_count, updated_count)
    """
    from scripts.event_database_handler import create_events_in_database as shared_create_events
    
    with app.app_context():
        # Get or create venue
        venue = Venue.query.filter(
            db.func.lower(Venue.name) == VENUE_NAME.lower()
        ).first()

        if not venue:
            # Get city
            city = City.query.filter(db.func.lower(City.name) == CITY_NAME.lower()).first()
            if not city:
                logger.error(f"❌ City '{CITY_NAME}' not found in database")
                return (0, 0)

            # Build additional_info with scraping paths
            import json
            additional_info = {
                'scraping_paths': {
                    'exhibitions': '/whats-on/exhibitions/',
                    'events': '/whats-on/events/',
                    'tours': '/whats-on/tours/',
                    'films': '/whats-on/events/search/?edan_fq[]=p.event.topics:Films',
                    'performances': '/whats-on/events/search/?edan_fq[]=p.event.topics:Performances'
                }
            }
            
            venue = Venue(
                name=VENUE_NAME,
                venue_type='museum',
                city_id=city.id,
                additional_info=json.dumps(additional_info)
            )
            db.session.add(venue)
            db.session.commit()
            logger.info(f"✅ Created venue: {VENUE_NAME}")
        else:
            # Update existing venue's additional_info with scraping paths
            import json
            try:
                existing_info = json.loads(venue.additional_info) if venue.additional_info else {}
            except (json.JSONDecodeError, TypeError):
                existing_info = {}
            
            if 'scraping_paths' not in existing_info:
                existing_info['scraping_paths'] = {}
            
            # Update scraping paths
            existing_info['scraping_paths'].update({
                'exhibitions': '/whats-on/exhibitions/',
                'events': '/whats-on/events/',
                'tours': '/whats-on/tours/',
                'films': '/whats-on/events/search/?edan_fq[]=p.event.topics:Films',
                'performances': '/whats-on/events/search/?edan_fq[]=p.event.topics:Performances'
            })
            
            venue.additional_info = json.dumps(existing_info)
            db.session.commit()
            logger.debug(f"✅ Updated venue additional_info with scraping paths")
        
        logger.info(f"✅ Found venue: {venue.name} (ID: {venue.id})")
        logger.info(f"📊 Processing {len(events)} events...")
        
        # Custom processor for Asian Art-specific fields
        def asian_art_event_processor(event_data):
            """Add Asian Art-specific fields"""
            event_data['source'] = 'website'
            event_data['organizer'] = VENUE_NAME
            # Handle online events
            if event_data.get('is_online') and not event_data.get('start_location'):
                event_data['start_location'] = 'Online'
            # Handle price conversion
            price_val = event_data.get('price')
            if isinstance(price_val, str) and price_val.lower() == 'free':
                event_data['price'] = 0.0
            admission_val = event_data.get('admission_price')
            if isinstance(admission_val, str) and admission_val.lower() == 'free':
                event_data['admission_price'] = 0.0
        
        # Use shared handler for all common logic
        created_count, updated_count, skipped_count = shared_create_events(
            events=events,
            venue_id=venue.id,
            city_id=venue.city_id,
            venue_name=venue.name,
            db=db,
            Event=Event,
            Venue=Venue,
            batch_size=5,
            logger_instance=logger,
            custom_event_processor=asian_art_event_processor
        )
        
        return (created_count, updated_count)


if __name__ == '__main__':
    # Test the scraper
    events = scrape_all_asian_art_events()
    print(f"\n✅ Scraped {len(events)} events")
    for event in events[:5]:
        print(f"\n- {event.get('title')}")
        print(f"  Dates: {event.get('start_date')} to {event.get('end_date')}")
        print(f"  URL: {event.get('source_url')}")
