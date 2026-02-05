#!/usr/bin/env python3
"""
Comprehensive Scraper for Smithsonian American Art Museum (SAAM)
Scrapes exhibitions, tours, talks, workshops, and other events from SAAM and Renwick Gallery
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time as dt_time, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import cloudscraper

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City
from scripts.utils import detect_ongoing_exhibition, get_ongoing_exhibition_dates, process_ongoing_exhibition_dates, is_category_heading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import shared progress update function
from scripts.utils import update_scraping_progress

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
    import platform as plat
    detected = plat.system().lower()
    platform_name = 'linux' if (detected == 'linux' or os.environ.get('RAILWAY_ENVIRONMENT')) else ('darwin' if detected == 'darwin' else 'windows')
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': platform_name,
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


def _extract_exhibition_images(soup: BeautifulSoup, url: str, max_images: int = 10) -> List[str]:
    """
    Extract multiple images from an exhibition/event page, prioritizing hero/feature images.
    Returns a list of image URLs, filtered to exclude logos, icons, and small images.
    
    Args:
        soup: BeautifulSoup object
        url: Base URL for resolving relative image paths
        max_images: Maximum number of images to return
    
    Returns:
        List of image URLs (strings)
    """
    image_urls = []
    seen_urls = set()
    
    # Skip patterns for non-content images
    skip_patterns = ['logo', 'icon', 'avatar', 'placeholder', 'spacer', 'button', 
                     'badge', 'social', 'share', 'menu', 'nav', 'header', 'footer']
    
    # Priority 1: Open Graph image (usually the best featured image)
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        img_url = og_image.get('content')
        if img_url not in seen_urls:
            if not img_url.startswith('http'):
                img_url = urljoin(SAAM_BASE_URL, img_url)
            image_urls.append(img_url)
            seen_urls.add(img_url)
    
    # Priority 2: Hero/feature/main images (exhibition/event specific)
    hero_selectors = [
        ('img', {'class': re.compile(r'hero|feature|main|exhibition|event|banner', re.I)}),
        ('img', {'id': re.compile(r'hero|feature|main|exhibition|event|banner', re.I)}),
        ('img', {'data-class': re.compile(r'hero|feature|main|exhibition|event', re.I)}),
    ]
    
    for tag, attrs in hero_selectors:
        hero_imgs = soup.find_all(tag, attrs)
        for img in hero_imgs:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            if src and src not in seen_urls:
                # Check if it's a content image (not a logo/icon)
                if not any(skip in src.lower() for skip in skip_patterns):
                    if not src.startswith('http'):
                        src = urljoin(SAAM_BASE_URL, src)
                    image_urls.append(src)
                    seen_urls.add(src)
                    if len(image_urls) >= max_images:
                        return image_urls
    
    # Priority 3: Images in main content areas (article, main, content sections)
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|body|exhibition', re.I))
    if main_content:
        content_imgs = main_content.find_all('img')
        for img in content_imgs:
            # Skip if it's inside a figure/caption (might be decorative)
            if img.find_parent(['figure', 'figcaption']):
                continue
            
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            if src and src not in seen_urls:
                # Check if it's a content image
                if not any(skip in src.lower() for skip in skip_patterns):
                    # Check image size if available (prefer larger images)
                    img_width = img.get('width')
                    img_height = img.get('height')
                    is_substantial = True
                    
                    if img_width and img_height:
                        try:
                            width = int(img_width)
                            height = int(img_height)
                            # Prefer images that are at least 200x200 pixels
                            if width < 200 or height < 200:
                                is_substantial = False
                        except (ValueError, TypeError):
                            pass
                    
                    if is_substantial:
                        if not src.startswith('http'):
                            src = urljoin(SAAM_BASE_URL, src)
                        image_urls.append(src)
                        seen_urls.add(src)
                        if len(image_urls) >= max_images:
                            return image_urls
    
    # Priority 4: All other substantial images (fallback)
    all_imgs = soup.find_all('img')
    for img in all_imgs:
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
        if src and src not in seen_urls:
            # Check if it's a content image
            if not any(skip in src.lower() for skip in skip_patterns):
                # Check image size
                img_width = img.get('width')
                img_height = img.get('height')
                is_substantial = True
                
                if img_width and img_height:
                    try:
                        width = int(img_width)
                        height = int(img_height)
                        if width < 200 or height < 200:
                            is_substantial = False
                    except (ValueError, TypeError):
                        pass
                
                if is_substantial:
                    if not src.startswith('http'):
                        src = urljoin(SAAM_BASE_URL, src)
                    image_urls.append(src)
                    seen_urls.add(src)
                    if len(image_urls) >= max_images:
                        return image_urls
    
    return image_urls


# Use shared parse_date_range from utils (but keep parse_single_date for other uses)
from scripts.utils import parse_date_range as parse_date_range_shared

def parse_date_range(date_string: str) -> Optional[Dict[str, date]]:
    """
    Parse date range string - uses shared utility function.
    Falls back to parse_single_date for compatibility with existing code.
    """
    # Try shared function first
    result = parse_date_range_shared(date_string)
    if result:
        return result
    
    # Fallback: try to parse as single date using local parse_single_date
    # (for compatibility with existing code that expects this behavior)
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
    """
    Scrape a single SAAM exhibition page.
    
    This function is used by:
    - The main SAAM scraper (scrape_saam_exhibitions) for bulk scraping
    - The URL scraper (extract_event_data_from_url) for "Quick Add from URL"
    
    Both use the same extraction logic, ensuring consistency.
    """
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
        
        # Extract description using shared utility function
        from scripts.utils import extract_description_from_soup
        description = extract_description_from_soup(soup, max_length=2000)
        
        # Extract date range, meeting location, and ongoing status - prioritize "Visiting Information" section
        date_range = None
        location = VENUE_NAME  # Default
        meeting_location = None  # Specific location like "Luce Foundation Center, 3rd Floor"
        is_ongoing = False  # Whether the exhibition is ongoing
        visiting_section_text = ""  # Initialize to ensure it's always defined
        
        # First, try to extract dates from structured HTML using shared utility
        from scripts.utils import extract_date_range_from_soup
        date_text = extract_date_range_from_soup(soup)
        if date_text:
            date_range = parse_date_range(date_text)
        
        # Find "Visiting Information" heading first (dates are usually here)
        visiting_heading = None
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = heading.get_text(strip=True).lower()
            if 'visiting' in heading_text and 'information' in heading_text:
                visiting_heading = heading
                break
        
        # Extract dates, meeting location, and ongoing status from "Visiting Information" section first (most reliable)
        if visiting_heading:
            # Get all text content after the heading (within the section)
            # Find the next sibling or parent's next siblings
            visiting_section_text = ""
            visiting_elements = []
            
            # Try to get the section container - check multiple possible structures
            visiting_container = None
            
            # Method 1: Check next sibling
            visiting_container = visiting_heading.find_next_sibling(['div', 'section', 'dl', 'ul', 'ol'])
            
            # Method 2: Check parent container
            if not visiting_container:
                parent = visiting_heading.parent
                if parent and parent.name in ['div', 'section', 'article']:
                    visiting_container = parent
            
            # Method 3: Get all following siblings until next heading
            if not visiting_container:
                # Collect all siblings until we hit another heading
                siblings = []
                for sibling in visiting_heading.find_next_siblings():
                    if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        break
                    siblings.append(sibling)
                if siblings:
                    visiting_container = siblings[0] if len(siblings) == 1 else None
            
            # Get text from the container or following elements
            if visiting_container:
                # Get text from the container and its immediate children
                for elem in [visiting_container] + list(visiting_container.find_all(['div', 'p', 'span', 'li', 'dt', 'dd', 'strong', 'em'], limit=20)):
                    elem_text = elem.get_text(separator=' ', strip=True)
                    if elem_text:
                        visiting_section_text += " " + elem_text
                        visiting_elements.append((elem, elem_text))
            
            # Also check direct next siblings (even if we found a container)
            next_sibling = visiting_heading.find_next_sibling()
            if next_sibling:
                sibling_text = next_sibling.get_text(separator=' ', strip=True)
                if sibling_text:
                    visiting_section_text += " " + sibling_text
                    visiting_elements.append((next_sibling, sibling_text))
            
            # Also get text from all following siblings until next heading (more comprehensive)
            sibling_count = 0
            for sibling in visiting_heading.find_next_siblings(['div', 'p', 'span', 'ul', 'ol', 'dl']):
                # Stop if we hit another heading
                if sibling.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    break
                sibling_text = sibling.get_text(separator=' ', strip=True)
                if sibling_text:
                    # Check if this text is already in visiting_section_text (avoid duplicates)
                    if sibling_text not in visiting_section_text:
                        visiting_section_text += " " + sibling_text
                        visiting_elements.append((sibling, sibling_text))
                sibling_count += 1
                # Limit to first 15 siblings to avoid going too far
                if sibling_count > 15:
                    break
            
            # Also try getting text from the next few elements more directly
            # Sometimes the date is in a <p> or <div> right after the heading
            current = visiting_heading.next_sibling
            direct_count = 0
            while current and direct_count < 10:
                if hasattr(current, 'get_text'):
                    direct_text = current.get_text(separator=' ', strip=True)
                    if direct_text and direct_text not in visiting_section_text:
                        visiting_section_text += " " + direct_text
                        visiting_elements.append((current, direct_text))
                current = current.next_sibling
                direct_count += 1
            
            # Clean up the text
            visiting_section_text = ' '.join(visiting_section_text.split())
            
            # Additional method: Get all text from the section more directly
            # Find the parent section or container and get all its text
            # This is a fallback if the structured extraction didn't work
            if not visiting_section_text or len(visiting_section_text) < 50:
                # Try to get text from parent section
                parent_section = visiting_heading.find_parent(['section', 'div', 'article'])
                if parent_section:
                    # Get all text from the section, but only after the heading
                    section_text = parent_section.get_text(separator=' ', strip=True)
                    # Find where the heading text appears and get text after it
                    heading_text = visiting_heading.get_text(strip=True)
                    heading_pos = section_text.find(heading_text)
                    if heading_pos >= 0:
                        text_after_heading = section_text[heading_pos + len(heading_text):]
                        # Limit to first 500 characters to avoid getting too much
                        text_after_heading = text_after_heading[:500]
                        if text_after_heading:
                            visiting_section_text = text_after_heading
                            logger.debug(f"   📝 Extracted additional text from parent section: {len(visiting_section_text)} chars")
            
            # Final fallback: Get ALL text from everything after the heading until next heading
            # This is the most comprehensive method - just grab everything
            if not visiting_section_text or 'october' not in visiting_section_text.lower() and 'august' not in visiting_section_text.lower():
                # Build text from all elements after the heading
                all_text_parts = []
                for elem in visiting_heading.find_all_next(['div', 'p', 'span', 'li', 'dt', 'dd', 'strong', 'em', 'a']):
                    # Stop at next heading
                    if elem.find_parent(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                        break
                    # Stop if we hit another major heading
                    if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        break
                    elem_text = elem.get_text(separator=' ', strip=True)
                    if elem_text and len(elem_text) > 5:  # Only meaningful text
                        all_text_parts.append(elem_text)
                    # Limit to first 20 elements to avoid going too far
                    if len(all_text_parts) > 20:
                        break
                
                if all_text_parts:
                    comprehensive_text = ' '.join(all_text_parts)
                    # Check if this has the date range
                    if re.search(r'[A-Za-z]+\s+\d{1,2},?\s+\d{4}\s*[–—-]\s*[A-Za-z]+\s+\d{1,2},?\s+\d{4}', comprehensive_text, re.IGNORECASE):
                        visiting_section_text = comprehensive_text
                        logger.debug(f"   📝 Found date range using comprehensive text extraction: {len(visiting_section_text)} chars")
            
            # Debug: Log what we extracted
            if visiting_section_text:
                logger.debug(f"   📝 Visiting section text ({len(visiting_section_text)} chars): {visiting_section_text[:300]}...")
                # Check if date range is in the text
                if re.search(r'[A-Za-z]+\s+\d{1,2},?\s+\d{4}\s*[–—-]\s*[A-Za-z]+\s+\d{1,2},?\s+\d{4}', visiting_section_text, re.IGNORECASE):
                    logger.debug(f"   ✅ Date range pattern found in visiting section text!")
                else:
                    logger.warning(f"   ⚠️ Date range pattern NOT found in visiting section text")
            else:
                logger.warning(f"   ⚠️ No text extracted from Visiting Information section")
            
            # Check for "ongoing" status using utility function
            is_ongoing = detect_ongoing_exhibition(visiting_section_text)
            if is_ongoing:
                logger.debug(f"   🔄 Exhibition marked as ongoing/permanent")
            
            # Extract meeting location (e.g., "Luce Foundation Center, 3rd Floor")
            # Look for common location patterns
            location_patterns = [
                r'Luce Foundation Center[^,]*,\s*[^,]+',  # "Luce Foundation Center, 3rd Floor"
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Center|Gallery|Room|Floor|Building|Lobby|Atrium)[^,]*,\s*[^,]+)',  # Generic location patterns
            ]
            
            for pattern in location_patterns:
                location_match = re.search(pattern, visiting_section_text, re.IGNORECASE)
                if location_match:
                    meeting_location = location_match.group(0).strip()
                    # Clean up common prefixes
                    meeting_location = re.sub(r'^(Location|Meet in|Located in|At)\s*:?\s*', '', meeting_location, flags=re.IGNORECASE)
                    meeting_location = meeting_location.strip()
                    if meeting_location:
                        logger.debug(f"   📍 Found meeting location: {meeting_location}")
                        break
            
            # Also check individual elements for location (more precise)
            if not meeting_location:
                for elem, elem_text in visiting_elements:
                    # Look for location indicators
                    if any(keyword in elem_text.lower() for keyword in ['luce foundation', 'center', 'floor', 'gallery', 'room']):
                        # Try to extract location from this element
                        for pattern in location_patterns:
                            location_match = re.search(pattern, elem_text, re.IGNORECASE)
                            if location_match:
                                meeting_location = location_match.group(0).strip()
                                meeting_location = re.sub(r'^(Location|Meet in|Located in|At)\s*:?\s*', '', meeting_location, flags=re.IGNORECASE)
                                meeting_location = meeting_location.strip()
                                if meeting_location:
                                    logger.debug(f"   📍 Found meeting location in element: {meeting_location}")
                                    break
                        if meeting_location:
                            break
            
            # Look for date range OR single date pattern in the combined text
            # Pattern 1: Date range "October 1, 2021 – August 2, 2026" or "October 1, 2021 - August 2, 2026"
            # Pattern 2: Single date "October 1, 2021" (exhibitions can be single-day events)
            # BUT: Skip if we already detected "Ongoing" - ongoing exhibitions shouldn't have date ranges
            if not is_ongoing:
                # First try date range pattern
                date_range_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–—-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
                date_range_match = re.search(date_range_pattern, visiting_section_text, re.IGNORECASE)
                
                if date_range_match:
                    full_match = date_range_match.group(0)
                    logger.debug(f"   🔍 Found date range pattern: '{full_match}'")
                    parsed_range = parse_date_range(full_match)
                    if parsed_range:
                        date_range = parsed_range
                        logger.debug(f"   📅 Parsed date range: start={date_range.get('start_date')}, end={date_range.get('end_date')}")
                    else:
                        logger.warning(f"   ⚠️ Failed to parse date range from: '{full_match}'")
                else:
                    # Try single date pattern (exhibitions can be single-day events)
                    single_date_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
                    single_date_match = re.search(single_date_pattern, visiting_section_text, re.IGNORECASE)
                    if single_date_match:
                        full_match = single_date_match.group(0)
                        logger.debug(f"   🔍 Found single date pattern: '{full_match}'")
                        parsed_range = parse_date_range(full_match)  # parse_date_range handles single dates too
                        if parsed_range:
                            date_range = parsed_range
                            logger.debug(f"   📅 Parsed single date: start={date_range.get('start_date')}, end={date_range.get('end_date')}")
                    else:
                        logger.debug(f"   🔍 No date pattern found in visiting section text")
            
            # If not found in combined text, check individual elements (but skip if ongoing)
            if not date_range and not is_ongoing:
                # First try date range pattern
                date_range_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–—-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
                # Then try single date pattern
                single_date_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
                
                # First check the visiting_elements we already collected
                for elem, elem_text in visiting_elements:
                    if not elem_text:
                        continue
                    # Look for date range pattern first
                    date_range_match = re.search(date_range_pattern, elem_text, re.IGNORECASE)
                    if date_range_match:
                        full_match = date_range_match.group(0)
                        date_range = parse_date_range(full_match)
                        if date_range:
                            logger.debug(f"   📅 Found date range in Visiting Information element: {date_range} from text: '{full_match}'")
                            break
                    # If no range, try single date
                    if not date_range:
                        single_date_match = re.search(single_date_pattern, elem_text, re.IGNORECASE)
                        if single_date_match:
                            full_match = single_date_match.group(0)
                            date_range = parse_date_range(full_match)  # parse_date_range handles single dates
                            if date_range:
                                logger.debug(f"   📅 Found single date in Visiting Information element: {date_range} from text: '{full_match}'")
                                break
                
                # If still not found, check all following elements
                if not date_range:
                    elements_checked = 0
                    for elem in visiting_heading.find_all_next(['div', 'p', 'span', 'li', 'dt', 'dd', 'strong', 'em']):
                        # Stop if we hit another heading
                        if elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                            break
                        elem_text = elem.get_text(separator=' ', strip=True)
                        if not elem_text:
                            continue
                        # Look for date range pattern first
                        date_range_match = re.search(date_range_pattern, elem_text, re.IGNORECASE)
                        if date_range_match:
                            full_match = date_range_match.group(0)
                            date_range = parse_date_range(full_match)
                            if date_range:
                                logger.debug(f"   📅 Found date range in Visiting Information element: {date_range} from text: '{full_match}'")
                                break
                        # If no range, try single date
                        if not date_range:
                            single_date_match = re.search(single_date_pattern, elem_text, re.IGNORECASE)
                            if single_date_match:
                                full_match = single_date_match.group(0)
                                date_range = parse_date_range(full_match)  # parse_date_range handles single dates
                                if date_range:
                                    logger.debug(f"   📅 Found single date in Visiting Information element: {date_range} from text: '{full_match}'")
                                    break
                        
                        elements_checked += 1
                        # Limit search to first 30 elements after heading
                        if elements_checked > 30:
                            break
        
        # Fallback 1: Check schema.org JSON-LD for dates (very reliable)
        # BUT: Skip if we already detected "Ongoing" - ongoing exhibitions shouldn't have date ranges
        if not date_range and not is_ongoing:
            schema_script = soup.find('script', type='application/ld+json')
            if schema_script:
                try:
                    import json
                    schema_data = json.loads(schema_script.string)
                    if isinstance(schema_data, dict):
                        if 'startDate' in schema_data and 'endDate' in schema_data:
                            start_date_str = schema_data['startDate']
                            end_date_str = schema_data['endDate']
                            # Parse ISO format dates
                            try:
                                start_date = datetime.fromisoformat(start_date_str.split('T')[0]).date()
                                end_date = datetime.fromisoformat(end_date_str.split('T')[0]).date()
                                date_range = {'start_date': start_date, 'end_date': end_date}
                                logger.debug(f"   📅 Found date range in schema.org: {date_range}")
                            except (ValueError, AttributeError):
                                pass
                    elif isinstance(schema_data, list):
                        for item in schema_data:
                            if isinstance(item, dict) and 'startDate' in item and 'endDate' in item:
                                start_date_str = item['startDate']
                                end_date_str = item['endDate']
                                try:
                                    start_date = datetime.fromisoformat(start_date_str.split('T')[0]).date()
                                    end_date = datetime.fromisoformat(end_date_str.split('T')[0]).date()
                                    date_range = {'start_date': start_date, 'end_date': end_date}
                                    logger.debug(f"   📅 Found date range in schema.org: {date_range}")
                                    break
                                except (ValueError, AttributeError):
                                    pass
                except (json.JSONDecodeError, AttributeError):
                    pass
        
        # Fallback 2: Look for dates elsewhere if not found in Visiting Information or schema
        # BUT: Skip if we already detected "Ongoing" - ongoing exhibitions shouldn't have date ranges
        if not date_range and not is_ongoing:
            # Search entire page text for date range pattern first
            page_text = soup.get_text()
            date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–—-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', page_text, re.IGNORECASE)
            if date_range_match:
                full_match = date_range_match.group(0)
                logger.debug(f"   🔍 Found date range pattern in page text: '{full_match}'")
                parsed_range = parse_date_range(full_match)
                if parsed_range:
                    date_range = parsed_range
                    logger.debug(f"   📅 Parsed date range from page text: start={date_range.get('start_date')}, end={date_range.get('end_date')}")
                else:
                    logger.warning(f"   ⚠️ Failed to parse date range from page text: '{full_match}'")
            else:
                # Try single date pattern (exhibitions can be single-day events)
                single_date_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', page_text, re.IGNORECASE)
                if single_date_match:
                    full_match = single_date_match.group(0)
                    logger.debug(f"   🔍 Found single date pattern in page text: '{full_match}'")
                    parsed_range = parse_date_range(full_match)  # parse_date_range handles single dates
                    if parsed_range:
                        date_range = parsed_range
                        logger.debug(f"   📅 Parsed single date from page text: start={date_range.get('start_date')}, end={date_range.get('end_date')}")
        
        # Fallback 3: Look for date in specific elements (but skip if ongoing)
        if not date_range and not is_ongoing:
            date_containers = soup.find_all(['div', 'span', 'p'], 
                                           class_=re.compile(r'date|time|duration', re.I))
            for container in date_containers:
                date_text = container.get_text(strip=True)
                date_range = parse_date_range(date_text)
                if date_range:
                    logger.debug(f"   📅 Found date range in date container: {date_range}")
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
        
        # Extract images (multiple)
        image_url = None
        additional_images = []
        
        # Use enhanced image extraction
        all_images = _extract_exhibition_images(soup, url)
        if all_images:
            image_url = all_images[0]
            additional_images = all_images[1:] if len(all_images) > 1 else []
        
        # Extract times (e.g., opening reception times, special event times)
        # Look for time patterns in the page text
        start_time = None
        end_time = None
        page_text = soup.get_text()
        
        # Look for opening reception times, special event times, etc.
        # Pattern: "Opening Reception: Friday, January 23, 2026, 6-8pm" or "6:00 – 8:00 p.m."
        # Try time range with colons first: "6:00 – 8:00 p.m." or "6:00-8:00pm"
        time_range_colon = re.search(r'(\d{1,2}):(\d{2})\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', page_text, re.IGNORECASE)
        if time_range_colon:
            try:
                start_hour = int(time_range_colon.group(1))
                start_min = int(time_range_colon.group(2))
                end_hour = int(time_range_colon.group(3))
                end_min = int(time_range_colon.group(4))
                am_pm = time_range_colon.group(5).upper()
                # Convert to 24-hour format
                if am_pm == 'PM' and start_hour != 12:
                    start_hour = (start_hour % 12) + 12
                elif am_pm == 'AM' and start_hour == 12:
                    start_hour = 0
                if am_pm == 'PM' and end_hour != 12:
                    end_hour = (end_hour % 12) + 12
                elif am_pm == 'AM' and end_hour == 12:
                    end_hour = 0
                start_time = dt_time(start_hour, start_min)
                end_time = dt_time(end_hour, end_min)
            except (ValueError, IndexError):
                pass
        
        # Try simple time range without colons: "6-8pm" or "6 – 8 p.m."
        if not start_time:
            time_range_simple = re.search(r'(\d{1,2})\s*[–-]\s*(\d{1,2})\s*([ap])\.?m\.?', page_text, re.IGNORECASE)
            if time_range_simple:
                try:
                    start_hour = int(time_range_simple.group(1))
                    end_hour = int(time_range_simple.group(2))
                    am_pm = time_range_simple.group(3).upper()
                    # Convert to 24-hour format
                    if am_pm == 'PM' and start_hour != 12:
                        start_hour = (start_hour % 12) + 12
                    elif am_pm == 'AM' and start_hour == 12:
                        start_hour = 0
                    if am_pm == 'PM' and end_hour != 12:
                        end_hour = (end_hour % 12) + 12
                    elif am_pm == 'AM' and end_hour == 12:
                        end_hour = 0
                    start_time = dt_time(start_hour, 0)
                    end_time = dt_time(end_hour, 0)
                except (ValueError, IndexError):
                    pass
        
        # Try single time with colon: "6:00 p.m." or "6:00pm"
        if not start_time:
            time_single_colon = re.search(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', page_text, re.IGNORECASE)
            if time_single_colon:
                try:
                    hour = int(time_single_colon.group(1))
                    minute = int(time_single_colon.group(2))
                    am_pm = time_single_colon.group(3).upper()
                    # Convert to 24-hour format
                    if am_pm == 'PM' and hour != 12:
                        hour = (hour % 12) + 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0
                    start_time = dt_time(hour, minute)
                except (ValueError, IndexError):
                    pass
        
        # Try single time without colon: "6pm" or "6 p.m."
        if not start_time:
            time_single = re.search(r'(\d{1,2})\s*([ap])\.?m\.?', page_text, re.IGNORECASE)
            if time_single:
                try:
                    hour = int(time_single.group(1))
                    am_pm = time_single.group(2).upper()
                    # Convert to 24-hour format
                    if am_pm == 'PM' and hour != 12:
                        hour = (hour % 12) + 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0
                    start_time = dt_time(hour, 0)
                except (ValueError, IndexError):
                    pass
        
        # Also check schema.org for times
        if not start_time:
            schema_script = soup.find('script', type='application/ld+json')
            if schema_script:
                try:
                    import json
                    schema_data = json.loads(schema_script.string)
                    if isinstance(schema_data, dict):
                        if 'startDate' in schema_data and 'T' in str(schema_data['startDate']):
                            start_date_str = schema_data['startDate']
                            time_part = start_date_str.split('T')[1].split('+')[0].split('-')[0]
                            if ':' in time_part:
                                hours, minutes = time_part.split(':')[:2]
                                hour_int = int(hours)
                                am_pm = 'PM' if hour_int >= 12 else 'AM'
                                hour_12 = hour_int % 12 if hour_int % 12 != 0 else 12
                                start_time = dt_time(hour_int, int(minutes))
                        if 'endDate' in schema_data and 'T' in str(schema_data['endDate']):
                            end_date_str = schema_data['endDate']
                            time_part = end_date_str.split('T')[1].split('+')[0].split('-')[0]
                            if ':' in time_part:
                                hours, minutes = time_part.split(':')[:2]
                                hour_int = int(hours)
                                am_pm = 'PM' if hour_int >= 12 else 'AM'
                                hour_12 = hour_int % 12 if hour_int % 12 != 0 else 12
                                end_time = dt_time(hour_int, int(minutes))
                except (json.JSONDecodeError, AttributeError, ValueError):
                    pass
        
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
        
        # Add times if found
        if start_time:
            event['start_time'] = start_time
        if end_time:
            event['end_time'] = end_time
        
        # Process dates using utility function (handles ongoing exhibitions)
        # Combine visiting section text with any other text for ongoing detection
        # Use visiting_section_text if available, otherwise fall back to description
        text_for_ongoing_check = visiting_section_text if visiting_section_text else None
        if not text_for_ongoing_check and description:
            text_for_ongoing_check = description
        
        # If we already detected ongoing, ensure it's passed to the processing function
        if is_ongoing and not text_for_ongoing_check:
            # If we detected ongoing but don't have text, use a minimal indicator
            text_for_ongoing_check = "ongoing"
        
        # Debug: Log date_range before processing
        if date_range:
            logger.debug(f"   📅 Date range BEFORE processing: start={date_range.get('start_date')}, end={date_range.get('end_date')}")
        
        date_range = process_ongoing_exhibition_dates(date_range, text_for_ongoing_check)
        
        # Debug: Log the date_range after processing
        if date_range:
            logger.debug(f"   📅 Date range AFTER processing: start={date_range.get('start_date')}, end={date_range.get('end_date')}")
        else:
            logger.warning(f"   ⚠️ No date_range after processing - dates will not be set")
        
        if date_range:
            event['start_date'] = date_range.get('start_date')
            event['end_date'] = date_range.get('end_date')
            # Debug: Log what we're setting
            logger.debug(f"   📅 Setting event dates: start={event.get('start_date')}, end={event.get('end_date')}")
            
            # Verify both dates are set
            if not event.get('start_date'):
                logger.warning(f"   ⚠️ start_date is None after setting from date_range")
            if not event.get('end_date'):
                logger.warning(f"   ⚠️ end_date is None after setting from date_range")
            
            # Update is_ongoing flag if dates indicate ongoing (but don't override valid dates)
            # Only mark as ongoing if end_date is unreasonably far (10+ years)
            if date_range.get('end_date'):
                ten_years_from_now = date.today() + timedelta(days=3650)
                if date_range['end_date'] > ten_years_from_now:
                    is_ongoing = True
            if is_ongoing:
                logger.debug(f"   🔄 Set ongoing/permanent exhibition dates: {event['start_date']} to {event['end_date']} (2 years from today)")
        elif is_ongoing:
            # Fallback: if no date_range but marked as ongoing, set dates
            start_date_obj, end_date = get_ongoing_exhibition_dates()
            event['start_date'] = start_date_obj
            event['end_date'] = end_date
            logger.debug(f"   🔄 Set ongoing/permanent exhibition dates: {event['start_date']} to {event['end_date']} (2 years from today)")
        
        # Add ongoing status to description if applicable
        if is_ongoing and 'ongoing' not in (event.get('description') or '').lower():
            if event.get('description'):
                event['description'] = f"{event['description']} (Ongoing exhibition)"
            else:
                event['description'] = f"Ongoing exhibition at {location}"
        
        if meeting_location:
            event['meeting_point'] = meeting_location
            # Also update description to include location if not already present
            if meeting_location.lower() not in (description or "").lower():
                if description:
                    event['description'] = f"{description} Located at {meeting_location}."
                else:
                    event['description'] = f"Exhibition at {location}. Located at {meeting_location}."
        
        if image_url:
            event['image_url'] = image_url
        
        # Add additional images if any
        if additional_images:
            event['additional_images'] = additional_images
        
        # Final debug: Log what we're returning
        logger.debug(f"   ✅ Returning event with dates: start={event.get('start_date')}, end={event.get('end_date')}")
        if additional_images:
            logger.debug(f"   📸 Found {len(additional_images)} additional images")
        
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
            
            # Skip section headings and category pages using utility function
            if is_category_heading(title):
                logger.debug(f"   ⏭️ Skipping category heading: '{title}'")
                continue
            
            # Skip if URL indicates it's a category page, not a specific exhibition
            if href in ['/exhibitions/upcoming', '/exhibitions/traveling', '/exhibitions/past', 
                       '/exhibitions/current', '/exhibitions']:
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
            
            # Extract image from listing page (thumbnail/preview image)
            image_url = None
            img_elem = container.find('img')
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src') or img_elem.get('data-original')
                if img_src:
                    # Skip logos, icons, and small decorative images
                    skip_patterns = ['logo', 'icon', 'avatar', 'placeholder', 'spacer', 'button', 
                                   'badge', 'social', 'share', 'menu', 'nav', 'header', 'footer']
                    if not any(skip in img_src.lower() for skip in skip_patterns):
                        # Check image size if available (prefer larger images)
                        img_width = img_elem.get('width')
                        img_height = img_elem.get('height')
                        is_substantial = True
                        
                        if img_width and img_height:
                            try:
                                width = int(img_width)
                                height = int(img_height)
                                # Prefer images that are at least 150x150 pixels (thumbnails are usually larger)
                                if width < 150 or height < 150:
                                    is_substantial = False
                            except (ValueError, TypeError):
                                pass
                        
                        if is_substantial:
                            if not img_src.startswith('http'):
                                image_url = urljoin(SAAM_BASE_URL, img_src)
                            else:
                                image_url = img_src
            
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
            
            # Add image from listing page if found
            if image_url:
                event['image_url'] = image_url
            
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
        
        # Normalize whitespace in page text to make regex matching more reliable
        # BeautifulSoup can split text across elements, so we need to join it properly
        page_text = ' '.join(soup.get_text().split())
        
        # Debug: Log if we found the walk-in section
        if walkin_section:
            logger.info(f"   ✅ Found walk-in section heading: {walkin_section.get_text()[:100]}")
        else:
            logger.warning(f"   ⚠️  Could not find 'walk-in' section heading on tours page")
            # Try to find any headings that might contain tour info
            all_headings = soup.find_all(['h2', 'h3', 'h4', 'h5'])
            logger.info(f"   Found {len(all_headings)} headings on page")
            for i, h in enumerate(all_headings[:5]):  # Log first 5 headings
                logger.info(f"   Heading {i+1}: {h.get_text()[:80]}")
        
        # Debug: Check if page text contains key phrases
        if '12:30' in page_text or '2 p.m.' in page_text or '4 p.m.' in page_text:
            logger.info(f"   ✅ Page text contains tour times (12:30, 2 p.m., or 4 p.m.)")
        else:
            logger.warning(f"   ⚠️  Page text does NOT contain expected tour times")
        
        if 'main building' in page_text.lower():
            logger.info(f"   ✅ Page text contains 'main building'")
        else:
            logger.warning(f"   ⚠️  Page text does NOT contain 'main building'")
        
        # Parse walk-in tours for SAAM main building
        # Look for text containing "SAAM's main building" and times
        saam_walkin_text = None
        if walkin_section:
            # Get the parent container and normalize text
            container = walkin_section.find_next(['div', 'section', 'ul'])
            if container:
                container_text = ' '.join(container.get_text().split())  # Normalize whitespace
                # Find the line about SAAM main building - need to get the FULL sentence with all times
                # The sentence is: "Free, docent-led walk-in tours at SAAM's main building start at 12:30 p.m., 2 p.m., and 4 p.m. daily."
                # First find where "SAAM's main building" appears
                saam_pos = container_text.lower().find("saam's main building")
                if saam_pos == -1:
                    saam_pos = container_text.lower().find("saam main building")
                
                if saam_pos >= 0:
                    # Get text starting from before "SAAM" to the end of the sentence (next period)
                    # Look backwards for sentence start (previous period or start of text)
                    sentence_start = max(0, container_text.rfind('.', 0, saam_pos))
                    if sentence_start > 0:
                        sentence_start += 1  # Skip the period
                    # Look forwards for sentence end (next period after "daily" or similar)
                    # The sentence ends after "daily" or similar words
                    sentence_end = container_text.find('.', saam_pos)
                    # Also check for common sentence endings
                    for end_marker in ['. Tours', '. Check', '. All']:
                        marker_pos = container_text.find(end_marker, saam_pos)
                        if marker_pos > saam_pos and (sentence_end == -1 or marker_pos < sentence_end):
                            sentence_end = marker_pos
                    
                    if sentence_end > saam_pos:
                        saam_walkin_text = container_text[sentence_start:sentence_end+1].strip()
                        # Make sure it contains "start at" and times
                        if 'start at' in saam_walkin_text.lower():
                            logger.info(f"   ✅ Found SAAM walk-in text in container: {saam_walkin_text[:200]}")
                        else:
                            saam_walkin_text = None
                    else:
                        saam_walkin_text = None
                else:
                    saam_walkin_text = None
                
                # Fallback to regex if position search didn't work
                if not saam_walkin_text:
                    saam_match = re.search(
                        r"SAAM'?s?\s+main\s+building[^.]*start\s+at[^.]*\.?",
                        container_text,
                        re.IGNORECASE
                    )
                    if saam_match:
                        saam_walkin_text = saam_match.group(0).strip()
                        # Try to extend to get full sentence with all times
                        match_start = container_text.find(saam_walkin_text)
                        next_period = container_text.find('.', match_start + len(saam_walkin_text))
                        if next_period > match_start:
                            saam_walkin_text = container_text[match_start:next_period+1].strip()
                        logger.info(f"   ✅ Found SAAM walk-in text (regex fallback): {saam_walkin_text[:150]}")
                else:
                    # Fallback: search for the full sentence containing all times
                    # The sentence is: "Free, docent-led walk-in tours at SAAM's main building start at 12:30 p.m., 2 p.m., and 4 p.m. daily."
                    # Find position of "SAAM's main building" or "SAAM main building"
                    saam_pos = container_text.lower().find("saam")
                    if saam_pos >= 0:
                        # Find the sentence start (previous period or start)
                        sentence_start = max(0, container_text.rfind('.', 0, saam_pos))
                        if sentence_start > 0:
                            sentence_start += 1
                        # Find sentence end - look for "daily" or "Check" followed by period
                        sentence_end = -1
                        for end_phrase in ['daily.', 'Check', 'Tours last']:
                            phrase_pos = container_text.find(end_phrase, saam_pos)
                            if phrase_pos > saam_pos:
                                # Find the period after this phrase
                                period_pos = container_text.find('.', phrase_pos)
                                if period_pos > phrase_pos:
                                    sentence_end = period_pos + 1
                                    break
                        
                        if sentence_end == -1:
                            # Fallback: find next period
                            sentence_end = container_text.find('.', saam_pos) + 1
                        
                        if sentence_end > saam_pos:
                            saam_walkin_text = container_text[sentence_start:sentence_end].strip()
                            if 'start at' in saam_walkin_text.lower():
                                logger.info(f"   ✅ Found SAAM text (position-based): {saam_walkin_text[:200]}")
                            else:
                                saam_walkin_text = None
                        else:
                            saam_walkin_text = None
                    else:
                        saam_walkin_text = None
        
        # Fallback: search in full page text (normalized)
        if not saam_walkin_text:
            # Try multiple patterns to find SAAM walk-in tour text
            patterns = [
                r"SAAM'?s?\s+main\s+building[^.]*start\s+at[^.]*\.?",
                r"Free[^.]*docent-led[^.]*walk-in[^.]*SAAM[^.]*main building[^.]*start\s+at[^.]*\.?",
                r"main\s+building[^.]*start\s+at\s+12:30[^.]*\.?",
            ]
            for pattern in patterns:
                saam_match = re.search(pattern, page_text, re.IGNORECASE)
                if saam_match:
                    saam_walkin_text = saam_match.group(0).strip()
                    logger.info(f"   ✅ Found SAAM text with fallback pattern: {saam_walkin_text[:100]}")
                    break
        
        if saam_walkin_text:
            logger.info(f"   ✅ Found SAAM walk-in tour text: {saam_walkin_text[:150]}...")
            # Extract times (e.g., "12:30 p.m., 2 p.m., and 4 p.m.")
            # Handle cases where text might be truncated (e.g., "12:30 p." instead of "12:30 p.m.")
            times = re.findall(r'(\d{1,2}(?::\d{2})?\s*[ap]\.?m?\.?)', saam_walkin_text, re.IGNORECASE)
            # Clean up times - if we have "12:30 p." add ".m."
            cleaned_times = []
            for t in times:
                if t.endswith(' p.') or t.endswith(' a.'):
                    cleaned_times.append(t + 'm.')
                else:
                    cleaned_times.append(t)
            times = cleaned_times
            logger.info(f"   📅 Found {len(times)} SAAM tour time(s): {times}")
            if not times:
                logger.warning(f"   ⚠️  No times extracted from SAAM text: {saam_walkin_text[:200]}")
                # Try a more lenient pattern
                times = re.findall(r'(\d{1,2}(?::\d{2})?\s*[ap]\.?m?\.?)', page_text, re.IGNORECASE)
                if times:
                    logger.info(f"   🔄 Found times with lenient pattern: {times[:5]}")
                    # Filter to only times near "main building" or "SAAM"
                    saam_context = page_text[max(0, page_text.lower().find('main building')-100):page_text.lower().find('main building')+300]
                    times = re.findall(r'(\d{1,2}(?::\d{2})?\s*[ap]\.?m?\.?)', saam_context, re.IGNORECASE)
                    logger.info(f"   🔄 Times near 'main building': {times[:5]}")
            
            saam_tour_count = 0
            logger.info(f"   🔄 Creating walk-in tour events for {len(times)} time slot(s) over next 30 days...")
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
                        
                        start_time = dt_time(hour, minute)
                        end_time = dt_time(hour + 1, minute)  # Tours last approximately one hour
                        
                        event = {
                            'title': 'Docent-Led Walk-In Tour',
                            'description': 'Free, docent-led walk-in tour at the Smithsonian American Art Museum. Tours last approximately one hour.',
                            'event_type': 'tour',
                            'start_date': tour_date,  # This is a date object
                            'end_date': tour_date,    # This is a date object
                            'start_time': start_time.strftime('%H:%M'),  # String format 'HH:MM'
                            'end_time': end_time.strftime('%H:%M'),      # String format 'HH:MM'
                            'organizer': VENUE_NAME,
                            'source_url': SAAM_TOURS_URL,
                            'url': SAAM_TOURS_URL,  # Also set url field
                            'social_media_platform': 'website',
                            'social_media_url': SAAM_TOURS_URL,
                            'meeting_point': 'Check with the Information Desk when you arrive',
                            'is_selected': True,  # Make sure tours are visible
                            'source': 'website',  # Set source field
                        }
                        events.append(event)
                        saam_tour_count += 1
                        if saam_tour_count <= 3:  # Log first 3 for debugging
                            logger.info(f"   📝 Sample SAAM tour event: {event['title']} on {event['start_date']} at {event['start_time']}")
            
            logger.info(f"   ✅ Created {saam_tour_count} SAAM walk-in tour events in memory")
        else:
            logger.warning(f"   ⚠️  Could not find SAAM walk-in tour information on tours page")
        
        # Parse walk-in tours for Renwick Gallery
        renwick_walkin_text = None
        
        # Debug: Check if "Renwick" appears anywhere on the page
        if 'Renwick' in page_text:
            logger.debug(f"   ✅ Found 'Renwick' mentioned on tours page")
            # Find the context around Renwick mentions
            renwick_contexts = []
            for match in re.finditer(r'Renwick', page_text, re.IGNORECASE):
                start = max(0, match.start() - 100)
                end = min(len(page_text), match.end() + 100)
                context = page_text[start:end].replace('\n', ' ').strip()
                renwick_contexts.append(context)
            if renwick_contexts:
                logger.debug(f"   Renwick contexts found: {len(renwick_contexts)}")
                for i, ctx in enumerate(renwick_contexts[:3]):  # Log first 3
                    logger.debug(f"   Context {i+1}: ...{ctx}...")
        else:
            logger.warning(f"   ⚠️  'Renwick' not found anywhere on tours page - tours may not be listed")
        
        # Try multiple strategies to find Renwick tour information
        # Strategy 1: Look in walk-in section container
        if walkin_section:
            # Get parent container and normalize text
            container = walkin_section.find_next(['div', 'section', 'ul', 'p'])
            if container:
                container_text = ' '.join(container.get_text().split())  # Normalize whitespace
                # Find the line about Renwick Gallery - try multiple patterns
                # Also search in the full container text (not just line by line)
                if 'renwick' in container_text.lower() and ('start' in container_text.lower() or 'noon' in container_text.lower()):
                    # Extract the relevant portion
                    renwick_match = re.search(r'[^.]*Renwick[^.]*start\s+at[^.]*\.?', container_text, re.IGNORECASE)
                    if renwick_match:
                        renwick_walkin_text = renwick_match.group(0).strip()
                        logger.debug(f"   Found Renwick text in container: {renwick_walkin_text[:100]}")
                    else:
                        # Fallback: just use the container text if it mentions Renwick
                        for line in container_text.split('.'):
                            line_lower = line.lower()
                            if 'renwick' in line_lower and ('start' in line_lower or 'noon' in line_lower):
                                renwick_walkin_text = line.strip()
                                logger.debug(f"   Found Renwick line in container: {renwick_walkin_text[:100]}")
                                break
        
        # Strategy 2: Search in full page text with multiple patterns
        # Actual text format: "Free, docent-led walk-in tours at SAAM's Renwick Gallery start at noon Monday through Saturday"
        if not renwick_walkin_text:
            patterns = [
                r"SAAM'?s?\s+Renwick\s+Gallery[^.]*start\s+at[^.]*\.?",  # Match "SAAM's Renwick Gallery start at"
                r"Renwick\s+Gallery[^.]*start\s+at[^.]*\.?",
                r"Renwick\s+Gallery[^.]*tour[^.]*\.?",
                r"Renwick[^.]*start\s+at\s+noon[^.]*\.?",  # Match "Renwick...start at noon"
                r"Renwick[^.]*noon[^.]*Monday[^.]*\.?",  # Match "Renwick...noon...Monday"
                r"Renwick[^.]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)[^.]*\.?",
            ]
            for pattern in patterns:
                renwick_match = re.search(pattern, page_text, re.IGNORECASE)
                if renwick_match:
                    renwick_walkin_text = renwick_match.group(0).strip()
                    logger.debug(f"   Found Renwick text with pattern {pattern}: {renwick_walkin_text[:100]}")
                    break
        
        # Strategy 3: Look for any mention of Renwick near time patterns (expanded context)
        if not renwick_walkin_text:
            # Find all mentions of "Renwick" and check nearby text for times
            renwick_mentions = list(re.finditer(r'Renwick', page_text, re.IGNORECASE))
            for mention in renwick_mentions:
                # Get text around the mention (400 chars before and after for more context)
                start_pos = max(0, mention.start() - 400)
                end_pos = min(len(page_text), mention.end() + 400)
                context = page_text[start_pos:end_pos]
                
                # Check if this context has time patterns or "start at"
                if re.search(r'\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?|noon|start\s+at', context, re.IGNORECASE):
                    renwick_walkin_text = context.strip()
                    logger.debug(f"   Found Renwick with time context: {renwick_walkin_text[:150]}")
                    break
        
        if renwick_walkin_text:
            logger.info(f"   ✅ Found Renwick walk-in tour text: {renwick_walkin_text[:150]}...")
            # Check if it says "noon" or specific times
            if 'noon' in renwick_walkin_text.lower():
                times = ['12:00 p.m.']
                logger.info(f"   📅 Detected 'noon' - using time: {times[0]}")
            else:
                times = re.findall(r'(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', renwick_walkin_text, re.IGNORECASE)
                logger.info(f"   📅 Found {len(times)} Renwick tour time(s) via regex: {times}")
            
            if not times:
                logger.warning(f"   ⚠️  No times extracted from Renwick text: {renwick_walkin_text[:200]}")
            
            # Check days (Monday through Saturday, no tours on Sundays)
            days_match = re.search(r'(Monday through Saturday|Monday-Saturday|Mon-Sat)', renwick_walkin_text, re.IGNORECASE)
            is_weekdays_only = days_match is not None
            
            renwick_tour_count = 0
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
                        start_time = dt_time(12, 0)
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
                            
                            start_time = dt_time(hour, minute)
                    end_time = dt_time(start_time.hour + 1, start_time.minute)  # Tours last approximately one hour
                    
                    event = {
                        'title': 'Docent-Led Walk-In Tour',
                        'description': 'Free, docent-led walk-in tour at the Renwick Gallery. Tours last approximately one hour.',
                        'event_type': 'tour',
                        'start_date': tour_date,  # This is a date object
                        'end_date': tour_date,    # This is a date object
                        'start_time': start_time.strftime('%H:%M'),  # String format 'HH:MM'
                        'end_time': end_time.strftime('%H:%M'),      # String format 'HH:MM'
                        'organizer': RENWICK_VENUE_NAME,  # This should be "Renwick Gallery"
                        'source_url': SAAM_TOURS_URL,
                        'url': SAAM_TOURS_URL,  # Also set url field
                        'social_media_platform': 'website',
                        'social_media_url': SAAM_TOURS_URL,
                        'meeting_point': 'Check with the Information Desk when you arrive',
                        'location': RENWICK_VENUE_NAME,  # Also set location to ensure detection
                        'venue_name': RENWICK_VENUE_NAME,  # Explicitly set venue_name for detection
                        'is_selected': True,  # Make sure tours are visible
                        'source': 'website',  # Set source field
                    }
                    events.append(event)
                    renwick_tour_count += 1
                    if renwick_tour_count <= 3:  # Log first 3 for debugging
                        logger.info(f"   📝 Sample Renwick tour event: {event['title']} on {event['start_date']} at {event['start_time']}")
            
            logger.info(f"   ✅ Created {renwick_tour_count} Renwick walk-in tour events in memory")
        else:
            logger.warning(f"   ⚠️  Could not find Renwick walk-in tour information on tours page")
            # Debug: Show what we did find
            if 'Renwick' in page_text:
                logger.info(f"   🔍 'Renwick' IS in page text, but patterns didn't match")
                # Try to find the actual text
                renwick_snippet = re.search(r'[^.]*Renwick[^.]{0,100}', page_text, re.IGNORECASE)
                if renwick_snippet:
                    logger.info(f"   📝 Sample Renwick text found: {renwick_snippet.group(0)[:200]}")
            else:
                logger.warning(f"   🔍 'Renwick' NOT found in page text at all")
        
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
        if events:
            logger.info(f"   📊 Tour breakdown: {len([e for e in events if 'Walk-In Tour' in e.get('title', '')])} walk-in tours, {len([e for e in events if 'Walk-In Tour' not in e.get('title', '')])} other tours")
            # Log sample tour
            sample = events[0]
            logger.info(f"   📝 Sample tour: {sample.get('title')} on {sample.get('start_date')} at {sample.get('start_time')}")
        
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
                # Clean title: remove venue name suffix
                from scripts.utils import clean_event_title
                title = clean_event_title(title)
                if title.lower() in ['search events', 'search', 'events', 'event', 'redirecting']:
                    title = None
        
        # Try OG title
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
                # Clean title: remove venue name suffix
                from scripts.utils import clean_event_title
                title = clean_event_title(title)
        
        # Skip generic titles
        if not title or title.lower() in ['search events', 'search', 'events', 'event', 'redirecting'] or 'find events including' in title.lower():
            logger.debug(f"   ⚠️ Could not find valid title for {url}")
            return None
        
        # Re-determine event type from title and description (more accurate than URL-based detection)
        title_lower = title.lower()
        if 'gallery talk' in title_lower or ('talk' in title_lower and 'walk-in' not in title_lower):
            event_type = 'talk'
        elif 'workshop' in title_lower:
            event_type = 'workshop'
        elif 'tour' in title_lower and 'walk-in' not in title_lower:
            event_type = 'tour'
        elif 'lecture' in title_lower:
            event_type = 'talk'
        elif 'art in the a.m.' in title_lower or 'art am' in title_lower:
            event_type = 'talk'
        elif 'virtual' in title_lower and 'workshop' in title_lower:
            event_type = 'workshop'
        # Keep the passed event_type if we couldn't determine a better one
        
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
        # Pattern 1a: Full date with time range "January 23, 2026, 1 – 2pm" (single digit hours without colons)
        date_time_range_pattern_simple = r'(\w+day,?\s+)?(\w+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2})\s*[–-]\s*(\d{1,2})\s*([ap]m)'
        match = re.search(date_time_range_pattern_simple, page_text, re.I | re.DOTALL)
        if match:
            # Extract date
            date_str = match.group(2) if match.group(2) else match.group(1)
            parsed_date = parse_single_date(date_str)
            if parsed_date:
                start_date = parsed_date
            
            # Extract times - single digit hours without colons
            if match.group(3) and match.group(4) and match.group(5):
                start_hour = int(match.group(3))
                end_hour = int(match.group(4))
                am_pm = match.group(5).upper()
                start_time = f"{start_hour}:00 {am_pm}"
                end_time = f"{end_hour}:00 {am_pm}"
        
        # Pattern 1b: Full date with time range "January 23, 2026, 12:15 – 1:15pm" (with colons)
        # Only use this if we didn't already find a time
        if not start_time:
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
        
        # Pattern 2a: Date with single time "January 23, 2026, 1pm" (single digit hour without colon)
        # Only use this if we didn't already find a time range (don't overwrite end_time)
        if not start_time:
            date_time_single_pattern_simple = r'(\w+day,?\s+)?(\w+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2})\s*([ap]m)'
            match = re.search(date_time_single_pattern_simple, page_text, re.I)
            if match:
                date_str = match.group(2) if match.group(2) else match.group(1)
                parsed_date = parse_single_date(date_str)
                if parsed_date:
                    start_date = parsed_date
                start_hour = int(match.group(3))
                am_pm = match.group(4).upper()
                start_time = f"{start_hour}:00 {am_pm}"
        
        # Pattern 2b: Date with single time "January 23, 2026, 12:15pm" (with colon)
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
        
        # Fallback: Look for time range separately
        if not start_time:
            # Try pattern with colons first "12:15 – 1:15pm"
            time_range_match = re.search(r'(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*([ap]m)', page_text, re.I | re.DOTALL)
            if time_range_match:
                start_time = f"{time_range_match.group(1)} {time_range_match.group(3).upper()}"
                end_time = f"{time_range_match.group(2)} {time_range_match.group(3).upper()}"
            else:
                # Try pattern without colons "1 – 2pm"
                time_range_match_simple = re.search(r'(\d{1,2})\s*[–-]\s*(\d{1,2})\s*([ap]m)', page_text, re.I | re.DOTALL)
                if time_range_match_simple:
                    start_hour = int(time_range_match_simple.group(1))
                    end_hour = int(time_range_match_simple.group(2))
                    am_pm = time_range_match_simple.group(3).upper()
                    start_time = f"{start_hour}:00 {am_pm}"
                    end_time = f"{end_hour}:00 {am_pm}"
                else:
                    # Single time with colon
                    time_match = re.search(r'(\d{1,2}:\d{2})\s*([ap]m)', page_text, re.I)
                    if time_match:
                        start_time = f"{time_match.group(1)} {time_match.group(2).upper()}"
                    else:
                        # Single time without colon "1pm"
                        time_match_simple = re.search(r'(\d{1,2})\s*([ap]m)', page_text, re.I)
                        if time_match_simple:
                            start_hour = int(time_match_simple.group(1))
                            am_pm = time_match_simple.group(2).upper()
                            start_time = f"{start_hour}:00 {am_pm}"
        
        # If we have start_time but no end_time, try to find the time range
        if start_time and not end_time:
            # Try to find time range near the start time
            time_range_match = re.search(r'(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*([ap]m)', page_text, re.I | re.DOTALL)
            if time_range_match:
                found_start = f"{time_range_match.group(1)} {time_range_match.group(3).upper()}"
                # Check if this matches our start time (allowing for slight variations)
                if found_start == start_time or found_start.replace(' ', '') == start_time.replace(' ', ''):
                    end_time = f"{time_range_match.group(2)} {time_range_match.group(3).upper()}"
            
            # If still no end_time, try to calculate from duration or assume 1 hour
            if not end_time:
                # Look for duration mentions in description
                if description:
                    duration_match = re.search(r'(\d+)\s*(hour|hr|minute|min)', description.lower())
                    if duration_match:
                        duration = int(duration_match.group(1))
                        unit = duration_match.group(2) if len(duration_match.groups()) > 1 else ''
                        # Parse start_time to add duration
                        try:
                            time_parts = start_time.replace('AM', '').replace('PM', '').strip().split(':')
                            hour = int(time_parts[0])
                            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                            is_pm = 'PM' in start_time.upper()
                            
                            if 'hour' in unit or 'hr' in unit:
                                hour += duration
                            elif 'minute' in unit or 'min' in unit:
                                minute += duration
                                if minute >= 60:
                                    hour += minute // 60
                                    minute = minute % 60
                            
                            # Convert to 12-hour format
                            if hour >= 12:
                                is_pm = True
                                if hour > 12:
                                    hour -= 12
                            elif hour == 0:
                                hour = 12
                            
                            end_time = f"{hour}:{minute:02d} {'PM' if is_pm else 'AM'}"
                        except (ValueError, IndexError):
                            pass
                
                # Default: assume 1 hour duration if no duration found
                if not end_time:
                    try:
                        time_parts = start_time.replace('AM', '').replace('PM', '').strip().split(':')
                        hour_12 = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                        is_pm = 'PM' in start_time.upper()
                        
                        # Convert to 24-hour format first
                        hour_24 = hour_12
                        if is_pm and hour_12 != 12:
                            hour_24 = hour_12 + 12
                        elif not is_pm and hour_12 == 12:
                            hour_24 = 0
                        
                        # Add 1 hour
                        hour_24 += 1
                        
                        # Handle hour overflow
                        if hour_24 >= 24:
                            hour_24 = hour_24 % 24
                        
                        # Convert back to 12-hour format
                        if hour_24 == 0:
                            hour_12 = 12
                            is_pm = False
                        elif hour_24 == 12:
                            hour_12 = 12
                            is_pm = True
                        elif hour_24 > 12:
                            hour_12 = hour_24 - 12
                            is_pm = True
                        else:
                            hour_12 = hour_24
                            is_pm = False
                        
                        end_time = f"{hour_12}:{minute:02d} {'PM' if is_pm else 'AM'}"
                    except (ValueError, IndexError):
                        pass
        
        # Validate and fix end_time format if needed (ensure hour is 1-12)
        if end_time:
            try:
                # Check if end_time has invalid hour (e.g., "23:30 PM")
                time_match = re.match(r'(\d{1,2}):(\d{2})\s*([AP]M)', end_time, re.I)
                if time_match:
                    hour = int(time_match.group(1))
                    if hour > 12 or hour == 0:
                        # Re-parse and fix
                        minute = int(time_match.group(2))
                        am_pm = time_match.group(3).upper()
                        # Convert to 24-hour, then back to 12-hour
                        hour_24 = hour
                        if am_pm == 'PM' and hour != 12:
                            hour_24 = hour + 12
                        elif am_pm == 'AM' and hour == 12:
                            hour_24 = 0
                        # Convert back to 12-hour
                        if hour_24 == 0:
                            hour = 12
                            am_pm = 'AM'
                        elif hour_24 == 12:
                            hour = 12
                            am_pm = 'PM'
                        elif hour_24 > 12:
                            hour = hour_24 - 12
                            am_pm = 'PM'
                        else:
                            hour = hour_24
                            am_pm = 'AM'
                        end_time = f"{hour}:{minute:02d} {am_pm}"
            except (ValueError, AttributeError):
                pass
        
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
        
        # Determine venue location - check Building field first (most reliable)
        location = None
        # Find Building field by checking all dt elements
        for dt in soup.find_all('dt'):
            if dt.get_text(strip=True).lower() == 'building':
                building_dd = dt.find_next_sibling('dd')
                if building_dd:
                    building_text = building_dd.get_text(strip=True)
                    if 'renwick' in building_text.lower():
                        location = RENWICK_VENUE_NAME
                    elif 'smithsonian american art museum' in building_text.lower() or 'saam' in building_text.lower():
                        location = VENUE_NAME
                    break
        
        # Check Event Location field if Building field not found
        if not location:
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
        
        # Extract image - try multiple methods
        image_url = None
        
        # Method 1: Try Open Graph image (most reliable)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image.get('content')
            if not image_url.startswith('http'):
                image_url = urljoin(SAAM_BASE_URL, image_url)
        
        # Method 2: Try hero/feature/main image
        if not image_url:
            img_elem = soup.find('img', class_=re.compile(r'hero|feature|main|event|exhibition', re.I))
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
                if img_src:
                    if not img_src.startswith('http'):
                        image_url = urljoin(SAAM_BASE_URL, img_src)
                    else:
                        image_url = img_src
        
        # Method 3: Try first substantial image (not logo/icon)
        if not image_url:
            images = soup.find_all('img')
            for img in images:
                img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if img_src and not any(skip in img_src.lower() for skip in ['logo', 'icon', 'avatar', 'placeholder', 'spacer']):
                    # Check if image is reasonably sized (likely a content image)
                    img_width = img.get('width')
                    img_height = img.get('height')
                    if img_width and img_height:
                        try:
                            width = int(img_width)
                            height = int(img_height)
                            if width > 200 and height > 200:  # Substantial image
                                if not img_src.startswith('http'):
                                    image_url = urljoin(SAAM_BASE_URL, img_src)
                                else:
                                    image_url = img_src
                                break
                        except (ValueError, TypeError):
                            pass
                    else:
                        # No size info, but it's not a logo/icon, so use it
                        if not img_src.startswith('http'):
                            image_url = urljoin(SAAM_BASE_URL, img_src)
                        else:
                            image_url = img_src
                        break
        
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
        
        # Final validation: ensure end_time is in correct format (1-12 hour)
        # If end_time is invalid, recalculate from start_time
        if end_time and start_time:
            # Check if end_time has invalid hour
            end_time_match = re.match(r'(\d{1,2}):(\d{2})\s*([AP]M)', end_time, re.I)
            if end_time_match:
                hour = int(end_time_match.group(1))
                if hour > 12 or hour == 0:
                    # Invalid hour - recalculate from start_time
                    try:
                        start_parts = start_time.replace('AM', '').replace('PM', '').strip().split(':')
                        hour_12 = int(start_parts[0])
                        minute = int(start_parts[1]) if len(start_parts) > 1 else 0
                        is_pm = 'PM' in start_time.upper()
                        
                        # Convert to 24-hour, add 1 hour, convert back
                        hour_24 = hour_12
                        if is_pm and hour_12 != 12:
                            hour_24 = hour_12 + 12
                        elif not is_pm and hour_12 == 12:
                            hour_24 = 0
                        
                        hour_24 += 1
                        if hour_24 >= 24:
                            hour_24 = hour_24 % 24
                        
                        # Convert back to 12-hour
                        if hour_24 == 0:
                            hour_12 = 12
                            is_pm = False
                        elif hour_24 == 12:
                            hour_12 = 12
                            is_pm = True
                        elif hour_24 > 12:
                            hour_12 = hour_24 - 12
                            is_pm = True
                        else:
                            hour_12 = hour_24
                            is_pm = False
                        
                        end_time = f"{hour_12}:{minute:02d} {'PM' if is_pm else 'AM'}"
                    except (ValueError, IndexError):
                        # If recalculation fails, just fix the hour format
                        minute = int(end_time_match.group(2))
                        am_pm = end_time_match.group(3).upper()
                        if hour > 12:
                            hour = hour - 12
                            am_pm = 'PM'
                        end_time = f"{hour}:{minute:02d} {am_pm}"
        
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


def scrape_all_saam_events(target_venue_name: str = None) -> List[Dict]:
    """
    Main function to scrape all SAAM events (exhibitions, tours, talks, etc.)
    
    Args:
        target_venue_name: Optional venue name to filter events for (e.g., "Renwick Gallery")
                          If provided, only events for that venue will be returned.
    """
    scraper = create_scraper()
    all_events = []
    
    # Total steps: Exhibitions, Tours, Events = 3 steps
    total_steps = 3
    
    if target_venue_name:
        logger.info(f"🎨 Starting SAAM scraping for {target_venue_name}...")
    else:
        logger.info("🎨 Starting comprehensive SAAM scraping...")
    
    # 1. Scrape exhibitions
    update_scraping_progress(1, total_steps, "Scraping exhibitions...", events_found=len(all_events), venue_name=VENUE_NAME)
    logger.info("📋 Scraping exhibitions...")
    exhibitions = scrape_saam_exhibitions(scraper)
    all_events.extend(exhibitions)
    update_scraping_progress(1, total_steps, f"✅ Found {len(exhibitions)} exhibitions", events_found=len(all_events), venue_name=VENUE_NAME)
    logger.info(f"   ✅ Found {len(exhibitions)} exhibitions")
    
    # 2. Scrape tours
    update_scraping_progress(2, total_steps, "Scraping tours...", events_found=len(all_events), venue_name=VENUE_NAME)
    logger.info("🚶 Scraping tours...")
    tours = scrape_saam_tours(scraper)
    all_events.extend(tours)
    update_scraping_progress(2, total_steps, f"✅ Found {len(tours)} tours", events_found=len(all_events), venue_name=VENUE_NAME)
    logger.info(f"   ✅ Found {len(tours)} tours")
    if tours:
        tour_types = {}
        for tour in tours:
            tour_type = tour.get('event_type', 'unknown')
            tour_types[tour_type] = tour_types.get(tour_type, 0) + 1
        logger.info(f"   📊 Tour breakdown by type: {tour_types}")
        # Log sample tours
        for i, tour in enumerate(tours[:3]):
            logger.info(f"   📝 Sample tour {i+1}: {tour.get('title')} on {tour.get('start_date')} at {tour.get('start_time')}")
    
    # 3. Scrape events (talks, gallery talks, etc.)
    update_scraping_progress(3, total_steps, "Scraping events (talks, etc.)...", events_found=len(all_events), venue_name=VENUE_NAME)
    logger.info("🎤 Scraping events (talks, etc.)...")
    events = scrape_saam_events(scraper)
    all_events.extend(events)
    update_scraping_progress(3, total_steps, f"✅ Found {len(events)} events", events_found=len(all_events), venue_name=VENUE_NAME)
    logger.info(f"   ✅ Found {len(events)} events")
    
    # Log final breakdown
    event_types = {}
    for event in all_events:
        event_type = event.get('event_type', 'unknown')
        event_types[event_type] = event_types.get(event_type, 0) + 1
    logger.info(f"✅ Total SAAM events scraped: {len(all_events)} (breakdown: {event_types})")
    
    # If target_venue_name is specified, filter events for that venue only
    if target_venue_name:
        filtered_events = []
        target_lower = target_venue_name.lower()
        for event_data in all_events:
            organizer = event_data.get('organizer', '').lower()
            location = event_data.get('location', '').lower()
            title = event_data.get('title', '').lower()
            venue_name = event_data.get('venue_name', '').lower()
            
            # Check if this event belongs to the target venue
            is_target_venue = (
                target_lower in organizer or
                target_lower in location or
                target_lower in title or
                target_lower in venue_name
            )
            
            if is_target_venue:
                filtered_events.append(event_data)
                logger.debug(f"   ✅ Included for {target_venue_name}: {event_data.get('title', '')[:50]}")
            else:
                logger.debug(f"   ⏭️  Excluded (not for {target_venue_name}): {event_data.get('title', '')[:50]}")
        
        logger.info(f"📊 Filtered to {len(filtered_events)} events for {target_venue_name} (from {len(all_events)} total)")
        return filtered_events
    
    return all_events


def create_events_in_database(events: List[Dict]) -> tuple:
    """
    Create or update events in the database.
    Uses shared event_database_handler for common logic.
    Handles SAAM/Renwick venue determination.
    Returns (created_count, updated_count)
    """
    from scripts.event_database_handler import create_events_in_database as shared_create_events
    
    with app.app_context():
        # Group events by venue (SAAM vs Renwick)
        saam_events = []
        renwick_events = []
        
        for event_data in events:
            # Determine venue based on organizer (SAAM-specific logic)
            organizer = event_data.get('organizer', VENUE_NAME)
            title = event_data.get('title', '')
            location = event_data.get('location', '')
            event_type = event_data.get('event_type', 'unknown')
            
            # Check multiple fields for Renwick identification
            is_renwick = (
                'Renwick' in organizer or
                'Renwick' in location or
                'Renwick' in title or
                event_data.get('venue_name') == RENWICK_VENUE_NAME
            )
            
            if is_renwick:
                renwick_events.append(event_data)
                logger.debug(f"   📍 Classified as Renwick: {title[:50]}... (organizer: {organizer})")
            else:
                saam_events.append(event_data)
        
        # Log detailed breakdown
        saam_by_type = {}
        for e in saam_events:
            et = e.get('event_type', 'unknown')
            saam_by_type[et] = saam_by_type.get(et, 0) + 1
        renwick_by_type = {}
        for e in renwick_events:
            et = e.get('event_type', 'unknown')
            renwick_by_type[et] = renwick_by_type.get(et, 0) + 1
        
        logger.info(f"📊 Event grouping: {len(saam_events)} SAAM events ({saam_by_type}), {len(renwick_events)} Renwick events ({renwick_by_type})")
        
        total_created = 0
        total_updated = 0
        
        # Process SAAM events
        if saam_events:
            venue = Venue.query.filter(
                db.func.lower(Venue.name).like(f'%{VENUE_NAME.lower()}%')
            ).first()
            
            if venue:
                logger.info(f"✅ Found venue: {venue.name} (ID: {venue.id})")
                logger.info(f"📊 Processing {len(saam_events)} SAAM events...")
                
                def saam_event_processor(event_data):
                    """Add SAAM-specific fields"""
                    event_data['source'] = 'website'
                    # Handle online events
                    if event_data.get('is_online') and not event_data.get('start_location'):
                        event_data['start_location'] = 'Online'
                
                created, updated, skipped = shared_create_events(
                    events=saam_events,
                    venue_id=venue.id,
                    city_id=venue.city_id,
                    venue_name=venue.name,
                    db=db,
                    Event=Event,
                    Venue=Venue,
                    batch_size=5,
                    logger_instance=logger,
                    custom_event_processor=saam_event_processor
                )
                total_created += created
                total_updated += updated
        
        # Process Renwick events (if any)
        if renwick_events:
            logger.info(f"📊 Found {len(renwick_events)} Renwick events to process")
            renwick_venue = Venue.query.filter(
                db.func.lower(Venue.name).like('%Renwick%')
            ).first()
            
            if renwick_venue:
                logger.info(f"✅ Found venue: {renwick_venue.name} (ID: {renwick_venue.id})")
                logger.info(f"📊 Processing {len(renwick_events)} Renwick events...")
                
                def renwick_event_processor(event_data):
                    """Add Renwick-specific fields"""
                    event_data['source'] = 'website'
                    event_data['organizer'] = renwick_venue.name
                
                created, updated, skipped = shared_create_events(
                    events=renwick_events,
                    venue_id=renwick_venue.id,
                    city_id=renwick_venue.city_id,
                    venue_name=renwick_venue.name,
                    db=db,
                    Event=Event,
                    Venue=Venue,
                    batch_size=5,
                    logger_instance=logger,
                    custom_event_processor=renwick_event_processor
                )
                total_created += created
                total_updated += updated
                logger.info(f"✅ Renwick: Created {created}, Updated {updated}, Skipped {skipped}")
            else:
                logger.warning(f"⚠️  Renwick Gallery venue not found in database! {len(renwick_events)} Renwick events will not be saved.")
                logger.warning(f"   Please ensure 'Renwick Gallery' venue exists in the database.")
        else:
            logger.debug(f"ℹ️  No Renwick events found in this batch")
        
        return total_created, total_updated


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

