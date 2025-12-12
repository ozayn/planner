#!/usr/bin/env python3
"""
Comprehensive Scraper for Smithsonian National Museum of African Art
Scrapes exhibitions, events, tours, and programs from africa.si.edu and si.edu
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
import urllib3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VENUE_NAME = "Smithsonian National Museum of African Art"
CITY_NAME = "Washington"

# African Art Museum URLs
AFRICAN_ART_BASE_URL = 'https://africa.si.edu'
AFRICAN_ART_EXHIBITIONS_URL = 'https://africa.si.edu/exhibitions/current-exhibitions/'


def create_scraper():
    """Create a scraper session"""
    # Suppress SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    scraper = requests.Session()
    scraper.verify = False
    
    scraper.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    return scraper


# Use shared parse_date_range from utils
from scripts.utils import parse_date_range


def parse_time(time_string: str) -> Optional[time]:
    """Parse time string like '2:00 pm' or '14:00' into time object"""
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


def scrape_exhibition_detail(scraper, url: str) -> Optional[Dict]:
    """
    Scrape detailed information from an exhibition detail page
    """
    try:
        logger.debug(f"   Scraping exhibition detail: {url}")
        response = scraper.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Exhibition"
        # Clean title: remove venue name suffix
        from scripts.utils import clean_event_title
        title = clean_event_title(title)
        
        # Extract description using shared utility function
        from scripts.utils import extract_description_from_soup, extract_date_range_from_soup
        description = extract_description_from_soup(soup, max_length=2000)
        
        # Extract date range using shared utility function
        date_range = None
        date_text = extract_date_range_from_soup(soup)
        
        # Parse date range if found
        if date_text:
            date_range = parse_date_range(date_text)
        
        # Fallback: look for date patterns in the page text
        if not date_range:
            page_text = soup.get_text()
            date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', page_text)
            if date_range_match:
                date_text = date_range_match.group(0)
                date_range = parse_date_range(date_text)
        
        # Extract image
        image_url = None
        img = soup.find('img', src=re.compile(r'\.(jpg|jpeg|png|webp)', re.I))
        if img:
            img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if img_src:
                image_url = urljoin(url, img_src)
        
        # Detect language from title and description
        language = 'English'  # Default
        combined_text = f"{title} {description or ''}".lower()
        
        # Only detect language when explicitly stated that event is CONDUCTED in that language
        # Don't flag just because it mentions a culture (e.g., "African Art" = about African art, not in African language)
        if re.search(r'(?:in|tour|conducted|presented|given|led)\s+mandarin|mandarin\s+(?:tour|language|導覽)|普通話|館藏精華導覽', combined_text, re.I):
            language = 'Mandarin'
        # Note: Don't detect language from culture names like "African", "African American" in titles
        
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
        logger.warning(f"   ⚠️ Error scraping exhibition detail {url}: {e}")
        return None


def scrape_african_art_exhibitions(scraper=None) -> List[Dict]:
    """
    Scrape all exhibitions from African Art Museum exhibitions page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🔍 Scraping African Art Museum exhibitions from: {AFRICAN_ART_EXHIBITIONS_URL}")
        response = scraper.get(AFRICAN_ART_EXHIBITIONS_URL, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_title = soup.title.string if soup.title else 'No title'
        logger.info(f"   📄 Page title: {page_title}")
        logger.info(f"   📏 Page length: {len(response.text)} characters")
        logger.info(f"   ✅ Response status: {response.status_code}")
        
        # Check if page loaded correctly
        if len(response.text) < 1000:
            logger.warning(f"   ⚠️ Response seems too short ({len(response.text)} chars). May be an error page.")
            if 'error' in response.text.lower() or '404' in response.text.lower():
                logger.error(f"   ❌ Page appears to be an error page")
                return events
        
        # PRIMARY APPROACH: Use h3 headings pattern (similar to Asian Art Museum)
        # The africa.si.edu page likely uses h3 headings for exhibitions
        exhibitions = soup.find_all('h3')
        
        logger.info(f"   📰 Found {len(exhibitions)} h3 headings on page")
        
        # Debug: Show first few h3 titles and URLs
        for i, h3 in enumerate(exhibitions[:5], 1):
            title = h3.get_text(strip=True)
            link = h3.find('a', href=True)
            href = link.get('href') if link else None
            logger.debug(f"   Sample h3 #{i}: '{title}' -> {href}")
        
        processed_titles = set()
        
        # Comprehensive list of titles to skip (navigation, footer, metadata, etc.)
        skip_titles = [
            'current exhibitions', 'upcoming exhibitions', 'past exhibitions', 'browse exhibitions',
            'calendar of events', 'artwork credits', 'connect with us', 'location, hours, and admission',
            'search this site', 'skip to', 'radio africa', 'footer', 'navigation', 'menu',
            'what\'s on', 'explore', 'collections', 'about', 'support', 'visit', 'learn',
            'smithsonian', 'donate', 'my visit'
        ]
        
        # Patterns that indicate non-exhibition titles
        skip_patterns = [
            r'^\d+\s+event',  # "1 event,31" 
            r'^\d+\s+events',  # "2 events"
            r'^\d+,\d+$',  # "1,31" or similar numbers
            r'^skip to',  # Skip links
            r'^search',  # Search elements
            r'^connect',  # Social media sections
            r'^location.*hours',  # Location info
            r'^calendar',  # Calendar sections
            r'^footer',  # Footer text
            r'^navigation',  # Navigation
            r'^menu',  # Menu items
        ]
        
        for h3 in exhibitions:
            # Get the link URL FIRST - validate before doing any work
            link = h3.find('a', href=True)
            exhibition_url = None
            if link:
                href = link.get('href', '')
                if href:
                    exhibition_url = urljoin(AFRICAN_ART_BASE_URL, href)
            
            # VALIDATE URL FIRST - skip immediately if invalid
            if not exhibition_url:
                logger.debug(f"   ⏭️  Skipping '{h3.get_text(strip=True)[:50]}' - no URL")
                continue
            
            url_lower = exhibition_url.lower()
            
            # Must be an exhibition detail page, not event/calendar/etc.
            if '/event/' in url_lower or '/events/' in url_lower:
                logger.debug(f"   ⏭️  Skipping '{title[:50] if title else h3.get_text(strip=True)[:50]}' - event URL: {exhibition_url[:60]}")
                continue
            
            # Must have /exhibitions/ with a real slug
            if '/exhibitions/' in url_lower:
                parts = url_lower.split('/exhibitions/')
                if len(parts) > 1 and parts[1]:
                    path_after_exhibitions = parts[1].strip('/')
                    path_parts = [p for p in path_after_exhibitions.split('/') if p]
                    # Skip if URL ends with just listing page names (no actual exhibition slug)
                    if not path_parts or path_parts == ['current-exhibitions'] or path_parts == ['upcoming-exhibitions'] or path_parts == ['past-exhibitions']:
                        continue
                    # Must have at least one more part after the listing page name
                    if len(path_parts) > 1 or (len(path_parts) == 1 and path_parts[0] not in ['current-exhibitions', 'upcoming-exhibitions', 'past-exhibitions']):
                        # Valid exhibition URL - continue processing
                        pass
                    else:
                        logger.debug(f"   ⏭️  Skipping '{title[:50] if title else h3.get_text(strip=True)[:50]}' - listing page: {exhibition_url[:60]}")
                        continue
                else:
                    logger.debug(f"   ⏭️  Skipping '{title[:50] if title else h3.get_text(strip=True)[:50]}' - no path after /exhibitions/")
                    continue
            else:
                # No /exhibitions/ in URL - not an exhibition
                logger.debug(f"   ⏭️  Skipping '{title[:50] if title else h3.get_text(strip=True)[:50]}' - no /exhibitions/ in URL: {exhibition_url[:60]}")
                continue
            
            # Now extract title AFTER URL validation passes
            # Try to get title from link text first (more reliable)
            title = None
            if link:
                title = link.get_text(strip=True)
                # If link text is generic, try the h3
                if not title or title.lower() in ['current exhibitions', 'view', 'read more', 'learn more']:
                    title = h3.get_text(strip=True)
            else:
                title = h3.get_text(strip=True)
            
            if not title:
                continue
            
            title_lower = title.lower().strip()
            
            # STRICT TITLE VALIDATION - now that URL is validated
            # Skip exact matches (comprehensive list)
            if title_lower in skip_titles:
                continue
            
            # Skip patterns (metadata, navigation, etc.)
            if any(re.search(pattern, title_lower) for pattern in skip_patterns):
                continue
            
            # Skip if it looks like metadata or navigation
            if re.match(r'^\d+\s*(event|events)', title_lower) or re.match(r'^\d+\s*event,\d+', title_lower) or re.match(r'^\d+,\d+$', title):
                continue
            
            # Skip if too short or too long (likely not an exhibition title)
            if len(title) < 10 or len(title) > 200:
                continue
            
            # Skip if it's clearly navigation/footer text
            nav_indicators = ['skip', 'search', 'connect', 'location', 'hours', 'admission', 'credits', 'calendar', 'menu', 'marketplace', 'kwanzaa']
            if any(indicator in title_lower for indicator in nav_indicators):
                # But allow if it's clearly part of an exhibition title (longer, more descriptive)
                if len(title) < 50 or title_lower in ['current exhibitions', 'calendar', 'calendar of events']:
                    continue
            
            # Skip if we've already processed this title
            if title in processed_titles:
                continue
            processed_titles.add(title)
            
            # Find the container that holds this exhibition (article, div, section, etc.)
            # Start from h3 and traverse up to find the exhibition card/container
            container = h3.parent
            exhibition_container = None
            
            # Look for a container that likely holds the full exhibition listing
            for level in range(5):
                if not container:
                    break
                # Check if this container has both date and image, indicating it's the exhibition card
                container_text = container.get_text()
                has_date = bool(re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text))
                has_image = bool(container.find('img', src=re.compile(r'\.(jpg|jpeg|png|webp)', re.I)))
                
                if has_date or has_image:
                    exhibition_container = container
                    break
                
                container = container.parent
            
            # If we didn't find a good container, use the h3's parent
            if not exhibition_container:
                exhibition_container = h3.parent
            
            # Extract date range from listing page - look more broadly
            date_range = None
            date_text = None
            date_context_text = None  # Store full text context for "ongoing" check
            
            # First try the exhibition container
            if exhibition_container:
                container_text = exhibition_container.get_text()
                date_context_text = container_text
                
                # Look for date range pattern: "June 3, 2024 – December 31, 2026"
                date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text)
                if date_range_match:
                    date_text = date_range_match.group(0)
                    date_range = parse_date_range(date_text)
                    logger.info(f"   📅 Found date range from container: {date_text}")
            
            # If not found, look around the h3 (siblings, parent's text)
            if not date_range:
                # Check siblings after h3
                next_elem = h3.find_next_sibling()
                for _ in range(5):  # Check next 5 siblings
                    if not next_elem:
                        break
                    text = next_elem.get_text()
                    if not date_context_text:
                        date_context_text = text
                    date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', text)
                    if date_range_match:
                        date_text = date_range_match.group(0)
                        date_range = parse_date_range(date_text)
                        logger.info(f"   📅 Found date range from sibling: {date_text}")
                        break
                    next_elem = next_elem.find_next_sibling()
            
            # If still not found, look in the parent article/div section
            if not date_range:
                parent = h3.find_parent(['article', 'div', 'section', 'li'])
                if parent:
                    parent_text = parent.get_text()
                    if not date_context_text:
                        date_context_text = parent_text
                    date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', parent_text)
                    if date_range_match:
                        date_text = date_range_match.group(0)
                        date_range = parse_date_range(date_text)
                        logger.info(f"   📅 Found date range from parent: {date_text}")
            
            # Check for "ongoing", "permanent", or "indefinitely" - if found and no end date, set end date to 3 years from now
            if date_range and not date_range.get('end_date'):
                if date_context_text and re.search(r'\b(ongoing|permanent|indefinitely)\b', date_context_text, re.IGNORECASE):
                    from datetime import timedelta
                    end_date = date.today() + timedelta(days=365 * 3)
                    date_range['end_date'] = end_date
                    matched_term = re.search(r'\b(ongoing|permanent|indefinitely)\b', date_context_text, re.IGNORECASE)
                    term = matched_term.group(1) if matched_term else 'ongoing'
                    logger.info(f"   📅 Exhibition marked as '{term}' - setting end date to 3 years from now: {end_date}")
            
            # Also check if no date_range was found but text contains ongoing/permanent/indefinitely
            if not date_range and date_context_text:
                if re.search(r'\b(ongoing|permanent|indefinitely)\b', date_context_text, re.IGNORECASE):
                    from datetime import timedelta
                    # Try to find a start date in the text
                    start_date_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', date_context_text)
                    start_date = None
                    if start_date_match:
                        try:
                            start_date_str = start_date_match.group(1).strip()
                            start_date = datetime.strptime(start_date_str, '%B %d, %Y').date()
                        except ValueError:
                            try:
                                start_date = datetime.strptime(start_date_str, '%B %d %Y').date()
                            except:
                                pass
                    
                    if not start_date:
                        start_date = date.today()
                    
                    end_date = date.today() + timedelta(days=365 * 3)
                    date_range = {
                        'start_date': start_date,
                        'end_date': end_date
                    }
                    matched_term = re.search(r'\b(ongoing|permanent|indefinitely)\b', date_context_text, re.IGNORECASE)
                    term = matched_term.group(1) if matched_term else 'ongoing'
                    logger.info(f"   📅 Exhibition marked as '{term}' - setting date range: {start_date} to {end_date}")
            
            # Extract image from listing page
            listing_image_url = None
            if exhibition_container:
                imgs = exhibition_container.find_all('img')
                for img in imgs:
                    img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original') or img.get('data-lazy')
                    if not img_src:
                        continue
                    
                    # Skip small icons/logos/generic images
                    skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg', 'site-header', 'nav-background', 'hero-background', 'arrow', 'bullet', 'decoration']
                    img_src_lower = img_src.lower()
                    if any(pattern in img_src_lower for pattern in skip_patterns):
                        continue
                    
                    # Check if it's a real image file
                    if any(ext in img_src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        listing_image_url = urljoin(AFRICAN_ART_BASE_URL, img_src)
                        logger.debug(f"   🖼️  Found listing image: {listing_image_url[:80]}")
                        break
            
            description = None
            image_url = listing_image_url  # Prioritize listing image
                
            # Get description from listing page
            if exhibition_container:
                # Look for paragraphs after the h3
                next_elem = h3.find_next_sibling()
                while next_elem and not description:
                    if next_elem.name == 'p':
                        text = next_elem.get_text(strip=True)
                        if len(text) > 50:  # Only use substantial paragraphs
                            description = text
                            break
                    next_elem = next_elem.find_next_sibling()
                
                # If no description from siblings, look in container
                if not description:
                    desc_para = exhibition_container.find('p')
                    if desc_para:
                        desc_text = desc_para.get_text(strip=True)
                        if len(desc_text) > 50:
                            description = desc_text
            
            # If we found an exhibition URL, try to scrape more details
            if exhibition_url and exhibition_url != AFRICAN_ART_EXHIBITIONS_URL:
                try:
                    detail_data = scrape_exhibition_detail(scraper, exhibition_url)
                    if detail_data:
                        # Merge detail data with what we found from listing page
                        if detail_data.get('description') and not description:
                            description = detail_data['description']
                        # Use listing image if available, otherwise use detail page image
                        if not image_url and detail_data.get('image_url'):
                            image_url = detail_data['image_url']
                        if detail_data.get('start_date') and not date_range:
                            date_range = {
                                'start_date': detail_data['start_date'],
                                'end_date': detail_data.get('end_date')
                            }
                except Exception as e:
                    logger.debug(f"   ⚠️ Error fetching exhibition detail {exhibition_url}: {e}")
            
            # Parse date range if we have date_text
            if not date_range and date_text:
                date_range = parse_date_range(date_text)
            
            # Try to get better title from detail page if current title is generic
            if title_lower in ['current exhibitions']:
                try:
                    detail_data = scrape_exhibition_detail(scraper, exhibition_url)
                    if detail_data and detail_data.get('title'):
                        title = detail_data['title']
                        title_lower = title.lower().strip()
                        logger.info(f"   ✅ Got better title from detail page: {title}")
                except:
                    pass  # Use listing title if detail scrape fails
            
            # Build event dictionary
            event = {
                'title': title,
                'description': description or f"Exhibition at {VENUE_NAME}",
                'event_type': 'exhibition',
                'source_url': exhibition_url or AFRICAN_ART_EXHIBITIONS_URL,
                'organizer': VENUE_NAME,
                'social_media_platform': 'website',
                'social_media_url': exhibition_url or AFRICAN_ART_EXHIBITIONS_URL,
                'language': 'English',
            }
            
            if date_range:
                event['start_date'] = date_range['start_date']
                event['end_date'] = date_range.get('end_date')
            else:
                # Default to today if no date found (ongoing exhibition)
                event['start_date'] = date.today()
            
            if image_url:
                event['image_url'] = image_url
            
            # Ensure language is set
            event['language'] = event.get('language', 'English')
            
            events.append(event)
            logger.info(f"   ✅ Added exhibition: {title}")
        
        logger.info(f"   ✅ Scraped {len(events)} current exhibitions")
        
    except Exception as e:
        logger.error(f"❌ Error scraping African Art Museum exhibitions: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return events


def scrape_all_african_art_events(scraper=None) -> List[Dict]:
    """
    Scrape all events (exhibitions, events, tours) from African Art Museum
    """
    if scraper is None:
        scraper = create_scraper()
    
    all_events = []
    
    # Scrape exhibitions
    exhibitions = scrape_african_art_exhibitions(scraper)
    all_events.extend(exhibitions)
    
    # TODO: Add events and tours scraping when URLs are provided
    
    logger.info(f"✅ Total African Art Museum events scraped: {len(all_events)}")
    
    return all_events


def create_events_in_database(events: List[Dict]) -> tuple:
    """
    Create or update events in the database
    Returns (created_count, updated_count)
    """
    created_count = 0
    updated_count = 0
    
    with app.app_context():
        # Get venue
        venue = Venue.query.filter_by(name=VENUE_NAME).first()
        if not venue:
            logger.error(f"❌ Venue '{VENUE_NAME}' not found in database")
            return (0, 0)
        
        for event_data in events:
            try:
                # Validate title
                title = event_data.get('title', '').strip()
                if not title:
                    logger.warning(f"   ⚠️  Skipping event: missing title")
                    continue
                
                # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                from scripts.utils import is_category_heading
                if is_category_heading(title):
                    logger.debug(f"   ⏭️ Skipping category heading: '{title}'")
                    continue
                
                # Skip non-English language events
                language = event_data.get('language', 'English')
                if language and language.lower() != 'english':
                    logger.debug(f"   ⚠️  Skipping non-English event: '{title}' (language: {language})")
                    continue
                
                # Detect if event is baby-friendly
                is_baby_friendly = False
                title_lower = title.lower()
                description_lower = (event_data.get('description', '') or '').lower()
                combined_text = f"{title_lower} {description_lower}"
                
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
                    logger.info(f"   👶 Detected baby-friendly event: '{title}'")
                
                # Find existing event by title and venue
                existing = Event.query.filter_by(
                    title=title,
                    venue_id=venue.id
                ).first()
                
                if existing:
                    # Update existing event
                    existing.description = event_data.get('description', existing.description)
                    existing.event_type = event_data.get('event_type', existing.event_type)
                    existing.source_url = event_data.get('source_url', existing.source_url)
                    existing.social_media_url = event_data.get('social_media_url', existing.social_media_url)
                    existing.image_url = event_data.get('image_url', existing.image_url)
                    
                    # Update dates
                    if event_data.get('start_date'):
                        existing.start_date = event_data['start_date']
                    if event_data.get('end_date'):
                        existing.end_date = event_data['end_date']
                    
                    # Update times
                    if event_data.get('start_time'):
                        existing.start_time = event_data['start_time']
                    if event_data.get('end_time'):
                        existing.end_time = event_data['end_time']
                    
                    # Update language and visibility
                    if event_data.get('language'):
                        existing.language = event_data['language']
                    # Ensure non-English events stay hidden
                    if existing.language and existing.language != 'English':
                        existing.is_selected = False
                    elif 'is_selected' in event_data:
                        existing.is_selected = event_data['is_selected']
                    
                    # Update baby-friendly flag if detected
                    if hasattr(Event, 'is_baby_friendly') and is_baby_friendly:
                        if not existing.is_baby_friendly:
                            existing.is_baby_friendly = True
                    
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                    logger.info(f"   ✅ Updated: {event_data.get('title')}")
                else:
                    # Create new event
                    new_event = Event(
                        title=event_data.get('title', 'Untitled Event'),
                        description=event_data.get('description', ''),
                        event_type=event_data.get('event_type', 'exhibition'),
                        venue_id=venue.id,
                        city_id=venue.city_id,
                        start_date=event_data.get('start_date'),
                        end_date=event_data.get('end_date'),
                        start_time=event_data.get('start_time'),
                        end_time=event_data.get('end_time'),
                        source_url=event_data.get('source_url', ''),
                        social_media_url=event_data.get('social_media_url', ''),
                        social_media_platform=event_data.get('social_media_platform', 'website'),
                        organizer=event_data.get('organizer', VENUE_NAME),
                        image_url=event_data.get('image_url', ''),
                        language=event_data.get('language', 'English'),
                        is_selected=event_data.get('is_selected', True)
                    )
                    
                    # Set baby-friendly flag if detected
                    if hasattr(Event, 'is_baby_friendly'):
                        new_event.is_baby_friendly = is_baby_friendly
                    
                    db.session.add(new_event)
                    created_count += 1
                    logger.info(f"   ✅ Created: {event_data.get('title')}")
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Error processing event {event_data.get('title', 'Unknown')}: {e}")
                continue
        
        db.session.commit()
        logger.info(f"✅ Created {created_count} new events, updated {updated_count} existing events")
        
    return (created_count, updated_count)


if __name__ == '__main__':
    # Test scraper
    scraper = create_scraper()
    events = scrape_all_african_art_events(scraper)
    print(f"\n📊 Scraped {len(events)} events")
    for event in events[:5]:
        print(f"  - {event.get('title', 'Untitled')}")
