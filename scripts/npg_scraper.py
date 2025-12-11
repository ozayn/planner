#!/usr/bin/env python3
"""
Comprehensive Scraper for National Portrait Gallery (NPG)
Scrapes exhibitions, tours, talks, programs, and other events from NPG
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
import requests
import urllib3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VENUE_NAME = "National Portrait Gallery"
CITY_NAME = "Washington"

# NPG URLs
NPG_BASE_URL = 'https://npg.si.edu'
NPG_EXHIBITIONS_URL = 'https://npg.si.edu/whats-on/current-exhibitions'
NPG_EVENTS_URL = 'https://npg.si.edu/events'
NPG_TOURS_URL = 'https://npg.si.edu/docent-tours'
NPG_ADULT_PROGRAMS_URL = 'https://npg.si.edu/adult-programs'
NPG_FAMILY_PROGRAMS_URL = 'https://npg.si.edu/families'


def create_scraper():
    """Create a cloudscraper session to bypass bot detection"""
    # Suppress SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Use requests with SSL verification disabled as a workaround for local SSL issues
    # In production/Railway, SSL should work fine
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


def parse_date_range(date_string: str) -> Optional[Dict[str, date]]:
    """
    Parse date range string like "September 26, 2025 - March 1, 2026"
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
        '%B %d, %Y',      # September 26, 2025
        '%b %d, %Y',      # Sep 26, 2025
        '%d %B %Y',       # 26 September 2025
        '%d %b %Y',       # 26 Sep 2025
        '%Y-%m-%d',       # 2025-09-26
        '%m/%d/%Y',       # 09/26/2025
        '%d/%m/%Y',       # 26/09/2025
        '%B %Y',          # September 2025
        '%b %Y',          # Sep 2025
        '%Y',             # 2025
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_string, fmt).date()
            return parsed
        except ValueError:
            continue
    
    # Try regex patterns for more flexible parsing
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


def parse_time(time_string: str) -> Optional[time]:
    """Parse time string like '12:00 p.m.' or '2:30 PM'"""
    if not time_string:
        return None
    
    time_string = time_string.strip().lower()
    
    # Remove periods and extra spaces
    time_string = re.sub(r'\.', '', time_string)
    time_string = re.sub(r'\s+', ' ', time_string)
    
    # Pattern for "HH:MM AM/PM" or "H:MM AM/PM"
    time_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)'
    match = re.search(time_pattern, time_string)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        am_pm = match.group(3)
        
        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0
        
        return time(hour, minute)
    
    # Pattern for "HH AM/PM" (no minutes)
    time_pattern2 = r'(\d{1,2})\s*(am|pm)'
    match = re.search(time_pattern2, time_string)
    if match:
        hour = int(match.group(1))
        am_pm = match.group(2)
        
        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0
        
        return time(hour, 0)
    
    return None


def scrape_npg_exhibitions(scraper=None) -> List[Dict]:
    """
    Scrape all exhibitions from NPG whats-on page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🔍 Scraping NPG exhibitions from: {NPG_EXHIBITIONS_URL}")
        response = scraper.get(NPG_EXHIBITIONS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all exhibition items - they're in h3 headings with dates below
        # Based on the page structure, exhibitions appear as h3 headings
        exhibitions = soup.find_all('h3')
        
        processed_titles = set()
        
        for h3 in exhibitions:
            # Get the title
            title_elem = h3.find('a') or h3
            title = title_elem.get_text(strip=True) if title_elem else h3.get_text(strip=True)
            
            if not title or len(title) < 5:
                continue
            
            # Skip section headings
            skip_titles = ['current exhibitions', 'permanent exhibitions', 'exhibitions', 'what\'s on']
            if title.lower() in skip_titles:
                continue
            
            # Skip if we've already processed this title
            if title in processed_titles:
                continue
            processed_titles.add(title)
            
            # Find the container that holds this exhibition
            # Look higher up in the DOM tree to find the exhibition card/block
            container = h3.parent
            # Traverse up to find a container with date information AND images
            # We need to go higher to find containers that include both the h3 and associated images
            for level in range(8):  # Increased range to find broader containers
                if container:
                    container_text = container.get_text()
                    # Check if this container has a date range pattern
                    date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text)
                    if date_range_match:
                        # Found a container with the date - check if it also has images
                        imgs_in_container = container.find_all('img')
                        if imgs_in_container:
                            # This container has both date and images, use it
                            break
                        # Otherwise continue searching for a container that has both
                container = container.parent if container else None
            
            # Look for date information in the container
            date_text = None
            description = None
            image_url = None
            exhibition_url = None
            
            # Get the link URL if it exists
            link = h3.find('a', href=True)
            if link:
                href = link.get('href', '')
                if href:
                    exhibition_url = urljoin(NPG_BASE_URL, href)
            
            # Extract date from container text
            if container:
                container_text = container.get_text()
                
                # Look for date range pattern: "September 26, 2025 – March 1, 2026"
                date_range_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text)
                if date_range_match:
                    date_text = date_range_match.group(0)
                else:
                    # Try simpler pattern
                    date_simple_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', container_text)
                    if date_simple_match:
                        date_text = date_simple_match.group(0)
                
                # Extract date range from container text
                if date_text:
                    date_range = parse_date_range(date_text)
                
                # Get description - look for paragraphs after the h3
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
                    desc_para = container.find('p')
                    if desc_para:
                        desc_text = desc_para.get_text(strip=True)
                        if len(desc_text) > 50:
                            description = desc_text
                
                # Get image from container - find the image closest/associated with this h3
                # Look in progressively broader containers to find the most relevant image
                img = None
                
                # Strategy 1: Look for images near the h3 (in same immediate container or siblings)
                current = h3
                for level in range(3):
                    parent = current.parent if current else None
                    if parent:
                        # Check for images in this immediate parent or its siblings
                        imgs_near = parent.find_all('img', recursive=False)  # Direct children only
                        for candidate_img in imgs_near:
                            img_src = candidate_img.get('src') or candidate_img.get('data-src') or candidate_img.get('data-lazy-src')
                            if img_src and 'grid_default' in img_src.lower():
                                img = candidate_img
                                break
                        if img:
                            break
                    current = parent
                
                # Strategy 2: If no image found nearby, look in the broader container
                # but try to find the one closest to the h3 in DOM order
                if not img and container:
                    all_imgs_in_container = container.find_all('img')
                    # Find images that come after this h3 in the DOM (more likely to be associated)
                    h3_position = None
                    for i, elem in enumerate(container.descendants):
                        if elem == h3:
                            h3_position = i
                            break
                    
                    grid_default_imgs = []
                    for candidate_img in all_imgs_in_container:
                        img_src = candidate_img.get('src') or candidate_img.get('data-src') or candidate_img.get('data-lazy-src')
                        if img_src and 'grid_default' in img_src.lower():
                            grid_default_imgs.append(candidate_img)
                    
                    if grid_default_imgs and h3_position is not None:
                        # Find the image closest to the h3 position
                        closest_img = None
                        closest_distance = float('inf')
                        for candidate_img in grid_default_imgs:
                            img_position = None
                            for i, elem in enumerate(container.descendants):
                                if elem == candidate_img:
                                    img_position = i
                                    break
                            if img_position is not None:
                                distance = abs(img_position - h3_position)
                                if distance < closest_distance:
                                    closest_distance = distance
                                    closest_img = candidate_img
                        if closest_img:
                            img = closest_img
                    elif grid_default_imgs:
                        # Fallback: just use first grid_default image
                        img = grid_default_imgs[0]
                
                if img:
                    img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if img_src:
                        image_url = urljoin(NPG_BASE_URL, img_src)
            
            # If we found an exhibition URL, try to scrape more details
            if exhibition_url and exhibition_url not in [NPG_EXHIBITIONS_URL, NPG_EXHIBITIONS_URL + '/']:
                try:
                    detail_data = scrape_exhibition_detail(scraper, exhibition_url)
                    if detail_data:
                        # Merge detail data with what we found
                        if detail_data.get('description') and not description:
                            description = detail_data['description']
                        
                        # For images: prefer listing page (grid_default) unless detail page has larger/better image
                        # Check if detail page image is generic/default (like npg-00106.jpg which appears on many pages)
                        detail_image = detail_data.get('image_url')
                        if detail_image:
                            # Generic/default image patterns that appear on multiple exhibitions
                            generic_patterns = ['npg-00106.jpg', 'dayofdead.jpg']  # Add more generic patterns as needed
                            is_generic_detail_image = any(pattern in detail_image.lower() for pattern in generic_patterns)
                            
                            if not image_url:
                                # No listing page image, use detail page image (even if generic)
                                image_url = detail_image
                            elif not is_generic_detail_image and 'slides_wide' in detail_image.lower() and 'grid_default' in (image_url or '').lower():
                                # Detail page has slides_wide (larger) AND it's not generic, listing page only has grid_default, prefer larger
                                image_url = detail_image
                            elif is_generic_detail_image and image_url:
                                # Detail page image is generic, keep listing page image even if it's grid_default
                                pass  # Keep existing image_url
                            # Otherwise keep the listing page image
                        
                        if detail_data.get('start_date') and not date_text:
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
                'source_url': exhibition_url or NPG_EXHIBITIONS_URL,
                'organizer': VENUE_NAME,
                'social_media_platform': 'website',
                'social_media_url': exhibition_url or NPG_EXHIBITIONS_URL,
            }
            
            if date_range:
                event['start_date'] = date_range['start_date']
                event['end_date'] = date_range['end_date']
            else:
                # Default to today if no date found (ongoing exhibition)
                event['start_date'] = date.today()
            
            if image_url:
                event['image_url'] = image_url
            
            events.append(event)
        
        logger.info(f"   ✅ Found {len(events)} exhibitions")
        
    except Exception as e:
        logger.error(f"❌ Error scraping NPG exhibitions: {e}")
        import traceback
        traceback.print_exc()
    
    return events


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
        
        # Extract image - try multiple strategies
        image_url = None
        
        # Strategy 1: Look for hero/feature/main images by class
        img_elem = soup.find('img', class_=re.compile(r'hero|feature|main|exhibition|header', re.I))
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
            if img_src:
                image_url = urljoin(NPG_BASE_URL, img_src)
        
        # Strategy 2: Look for images with keywords in URL (page-header, hero, etc.)
        # Prefer larger image sizes (slides_wide, large) over smaller ones (medium, thumbnail)
        if not image_url:
            all_imgs = soup.find_all('img')
            candidate_images = []
            
            for img in all_imgs:
                img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if img_src:
                    src_lower = img_src.lower()
                    # Skip small icons/logos/decoration
                    skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'twitter', 'facebook', 'instagram', 'svg']
                    if any(pattern in src_lower for pattern in skip_patterns):
                        continue
                    
                    # Collect images with certain keywords in path
                    if any(keyword in src_lower for keyword in ['page-header', 'hero', 'feature', 'exhibition', 'header']):
                        # Assign priority: slides_wide > large > medium > thumbnail
                        priority = 0
                        if 'slides_wide' in src_lower or 'wide' in src_lower:
                            priority = 4
                        elif 'large' in src_lower:
                            priority = 3
                        elif 'medium' in src_lower:
                            priority = 2
                        elif 'thumbnail' in src_lower:
                            priority = 1
                        else:
                            priority = 2  # Default priority for page-header images
                        
                        candidate_images.append((priority, img_src))
            
            # Sort by priority (highest first) and use the best one
            if candidate_images:
                candidate_images.sort(key=lambda x: x[0], reverse=True)
                image_url = urljoin(NPG_BASE_URL, candidate_images[0][1])
        
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
                            image_url = urljoin(NPG_BASE_URL, img_src)
                            break
        
        # Build event dictionary
        event = {
            'title': title,
            'description': description or f"Exhibition at {VENUE_NAME}",
            'event_type': 'exhibition',
            'source_url': url,
            'organizer': VENUE_NAME,
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


def scrape_npg_tours(scraper=None) -> List[Dict]:
    """
    Scrape docent tours from NPG
    Daily tours at 12:00 p.m. and 2:30 p.m., meeting in F Street Lobby
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🔍 Scraping NPG tours from: {NPG_TOURS_URL}")
        response = scraper.get(NPG_TOURS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract tour information from the page
        page_text = soup.get_text()
        
        # Default tour times (confirmed from website)
        tour_times = ['12:00 p.m.', '2:30 p.m.']
        meeting_point = "F Street Lobby"
        
        # Try to extract tour times from page if they're mentioned
        time_pattern = r'(\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.)'
        found_times = re.findall(time_pattern, page_text, re.I)
        if found_times:
            # Update tour times if found
            extracted_times = []
            for match in found_times:
                time_str = f"{match[0]}:{match[1]} {match[2]}"
                # Only add if it's a common tour time (around noon or afternoon)
                hour = int(match[0])
                if 11 <= hour <= 15:  # Tours typically between 11am and 3pm
                    extracted_times.append(time_str)
            if extracted_times:
                tour_times = list(set(extracted_times))  # Remove duplicates
        
        # Look for meeting point information
        if 'f street' in page_text.lower():
            meeting_point = "F Street Lobby"
        elif 'g street' in page_text.lower():
            meeting_point = "G Street Lobby"
        
        # Create daily docent tour events for next 60 days
        today = date.today()
        for i in range(60):
            tour_date = today + timedelta(days=i)
            
            for tour_time_str in tour_times:
                start_time_obj = parse_time(tour_time_str)
                if not start_time_obj:
                    continue
                
                # Tours typically last 1 hour
                end_time_obj = time(start_time_obj.hour + 1, start_time_obj.minute)
                
                # Format end time in 12-hour format
                end_hour = end_time_obj.hour
                end_am_pm = 'p.m.' if end_hour >= 12 else 'a.m.'
                if end_hour > 12:
                    end_hour = end_hour - 12
                elif end_hour == 0:
                    end_hour = 12
                end_time_str = f"{end_hour}:{end_time_obj.minute:02d} {end_am_pm}"
                
                event = {
                    'title': 'Docent Tour',
                    'description': 'Daily walk-in docent-led tour providing insights into the museum\'s collection of portraits. No reservations necessary. Last-minute cancellations may occur due to volunteer availability.',
                    'event_type': 'tour',
                    'start_date': tour_date,
                    'end_date': tour_date,
                    'start_time': tour_time_str,
                    'end_time': end_time_str,
                    'meeting_point': meeting_point,
                    'source_url': NPG_TOURS_URL,
                    'organizer': VENUE_NAME,
                    'social_media_platform': 'website',
                    'social_media_url': NPG_TOURS_URL,
                }
                
                events.append(event)
        
        # Look for Spanish-language tours (usually on select Sundays)
        # Check for links to Spanish tour events
        spanish_tour_links = soup.find_all('a', href=re.compile(r'spanish|espanol|español', re.I))
        for link in spanish_tour_links:
            href = link.get('href', '')
            if not href:
                continue
            
            full_url = urljoin(NPG_BASE_URL, href)
            
            # Try to scrape the Spanish tour page for specific dates
            try:
                spanish_tour_data = scrape_event_detail(scraper, full_url)
                if spanish_tour_data:
                    # Update title to indicate it's Spanish-language
                    spanish_tour_data['title'] = 'Spanish-Language Docent Tour'
                    spanish_tour_data['description'] = 'Spanish-language walk-in docent-led tour. Free but may require registration. Meeting point: F Street Lobby.'
                    spanish_tour_data['event_type'] = 'tour'
                    events.append(spanish_tour_data)
            except Exception as e:
                logger.debug(f"   ⚠️ Error scraping Spanish tour {full_url}: {e}")
        
        # Also check page text for mentions of Spanish tours on Sundays
        if 'spanish' in page_text.lower() and 'sunday' in page_text.lower():
            # Look for Sunday dates mentioned
            today = date.today()
            for i in range(180):  # Check next 6 months
                tour_date = today + timedelta(days=i)
                if tour_date.weekday() == 6:  # Sunday
                    # Check if there's mention of this specific Sunday
                    # For now, add Spanish tours for all Sundays in next 3 months
                    if i < 90:  # Only next 3 months
                        event = {
                            'title': 'Spanish-Language Docent Tour',
                            'description': 'Spanish-language walk-in docent-led tour on select Sundays. Free but may require registration. Please check the website for specific dates.',
                            'event_type': 'tour',
                            'start_date': tour_date,
                            'end_date': tour_date,
                            'start_time': '3:00 p.m.',
                            'end_time': '4:00 p.m.',
                            'meeting_point': meeting_point,
                            'source_url': NPG_TOURS_URL,
                            'organizer': VENUE_NAME,
                            'social_media_platform': 'website',
                            'social_media_url': NPG_TOURS_URL,
                        }
                        events.append(event)
        
        logger.info(f"   ✅ Found {len(events)} tour events")
        
    except Exception as e:
        logger.error(f"❌ Error scraping NPG tours: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_npg_events(scraper=None) -> List[Dict]:
    """
    Scrape events (talks, programs, etc.) from NPG events page
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    try:
        logger.info(f"🔍 Scraping NPG events from: {NPG_EVENTS_URL}")
        response = scraper.get(NPG_EVENTS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all event links
        event_links = soup.find_all('a', href=re.compile(r'/event/'))
        
        processed_urls = set()
        
        for link in event_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Build full URL
            full_url = urljoin(NPG_BASE_URL, href)
            
            # Skip if we've already processed this URL
            if full_url in processed_urls:
                continue
            processed_urls.add(full_url)
            
            # Scrape individual event page
            try:
                event_data = scrape_event_detail(scraper, full_url)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                logger.warning(f"   ⚠️ Error scraping event {full_url}: {e}")
        
        logger.info(f"   ✅ Found {len(events)} events")
        
    except Exception as e:
        logger.error(f"❌ Error scraping NPG events: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_event_detail(scraper, url: str) -> Optional[Dict]:
    """Scrape details from an individual event page"""
    try:
        logger.debug(f"   📄 Scraping event page: {url}")
        response = scraper.get(url, timeout=15)
        response.raise_for_status()
        
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
        
        # Extract description - look for paragraphs after the title
        description = None
        desc_parts = []
        
        # Look for description in paragraphs
        for p in soup.find_all('p'):
            p_text = p.get_text(strip=True)
            # Skip very short paragraphs or navigation text
            if len(p_text) > 50 and p_text.lower() not in ['home', 'events', 'exhibitions', 'learn']:
                desc_parts.append(p_text)
        
        if desc_parts:
            description = ' '.join(desc_parts[:3])  # Take first 3 paragraphs
        
        if not description:
            # Try to find description in divs
            desc_elem = soup.find('div', class_=re.compile(r'description|summary|intro|content', re.I))
            if desc_elem:
                description = desc_elem.get_text(strip=True)
        
        # Extract date and time - look for structured event information
        page_text = soup.get_text()
        
        event_date = None
        start_time = None
        end_time = None
        meeting_point = None
        registration_required = False
        registration_url = None
        registration_info = None
        price = None
        
        # Extract date pattern: "Thu Dec 4, 2025 5:30pm - 6:30pm" or "Event Date: Thu Dec 4, 2025 5:30pm - 6:30pm"
        date_time_pattern = r'(?:Event Date:\s*)?(?:([A-Za-z]{3})\s+)?([A-Za-z]{3})\s+(\d{1,2}),?\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*(am|pm)\s*-?\s*(\d{1,2}):(\d{2})\s*(am|pm)'
        date_time_match = re.search(date_time_pattern, page_text, re.I)
        
        if date_time_match:
            # Parse date
            month_str = date_time_match.group(2)
            day = int(date_time_match.group(3))
            year = int(date_time_match.group(4))
            
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'june': 6, 'july': 7, 'august': 8, 'september': 9,
                'october': 10, 'november': 11, 'december': 12
            }
            month = month_map.get(month_str.lower()[:3])
            if month:
                event_date = date(year, month, day)
            
            # Parse start time
            start_hour = int(date_time_match.group(5))
            start_minute = int(date_time_match.group(6))
            start_am_pm = date_time_match.group(7).lower()
            if start_am_pm == 'pm' and start_hour != 12:
                start_hour += 12
            elif start_am_pm == 'am' and start_hour == 12:
                start_hour = 0
            start_time = time(start_hour, start_minute)
            
            # Parse end time
            end_hour = int(date_time_match.group(8))
            end_minute = int(date_time_match.group(9))
            end_am_pm = date_time_match.group(10).lower()
            if end_am_pm == 'pm' and end_hour != 12:
                end_hour += 12
            elif end_am_pm == 'am' and end_hour == 12:
                end_hour = 0
            end_time = time(end_hour, end_minute)
        else:
            # Fallback: Look for date/time information with simpler patterns
            date_elem = soup.find(text=re.compile(r'\d{1,2}:\d{2}'))
            if date_elem:
                date_text = date_elem.parent.get_text() if hasattr(date_elem, 'parent') else str(date_elem)
                # Try to parse date from text
                event_date = parse_single_date(date_text)
                # Try to parse time
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)', date_text, re.I)
                if time_match:
                    start_time_str = f"{time_match.group(1)}:{time_match.group(2)} {time_match.group(3)}"
                    start_time = parse_time(start_time_str)
                    if start_time:
                        # Assume 1 hour duration
                        end_hour = start_time.hour + 1
                        if end_hour >= 24:
                            end_hour = 23
                        end_time = time(end_hour, start_time.minute)
        
        # Extract location/meeting point
        location_match = re.search(r'Event Location:\s*([^\n]+)', page_text, re.I)
        if location_match:
            meeting_point = location_match.group(1).strip()
        else:
            # Look for common location patterns
            for loc_text in ['G Street Lobby', 'F Street Lobby', 'Great Hall']:
                if loc_text.lower() in page_text.lower():
                    meeting_point = loc_text
                    break
        
        # Extract cost/price
        cost_match = re.search(r'Event Cost:\s*([^\n]+)', page_text, re.I)
        cost_text = None
        if cost_match:
            cost_text = cost_match.group(1).strip()
            if 'free' in cost_text.lower():
                price = 0.0
            else:
                # Try to extract dollar amount
                price_match = re.search(r'\$(\d+(?:\.\d{2})?)', cost_text)
                if price_match:
                    price = float(price_match.group(1))
        
        # Extract registration requirements - check cost_text first, then page_text
        if cost_text and ('registration required' in cost_text.lower() or 'registration' in cost_text.lower()):
            registration_required = True
            # Store the full cost text as registration info if it contains registration info
            # e.g., "Free. Registration Required."
            registration_info = cost_text
        elif 'registration required' in page_text.lower():
            registration_required = True
        
        # Extract registration/ticket URL
        ticket_link = soup.find('a', href=re.compile(r'eventbrite|ticket|register|rsvp', re.I))
        if ticket_link:
            registration_url = ticket_link.get('href', '')
            if not registration_url.startswith('http'):
                registration_url = urljoin(NPG_BASE_URL, registration_url)
        
        # Also look for "Get Tickets:" link in text
        tickets_match = re.search(r'Get Tickets:\s*(https?://[^\s\n]+)', page_text, re.I)
        if tickets_match:
            registration_url = tickets_match.group(1).strip()
        
        # Determine event type
        event_type = 'event'
        title_lower = title.lower()
        
        # Check event category first
        category_match = re.search(r'Event Category:\s*([^\n]+)', page_text, re.I)
        if category_match:
            category = category_match.group(1).strip().lower()
            if 'talk' in category or 'gallery talk' in category:
                event_type = 'talk'
            elif 'tour' in category:
                event_type = 'tour'
        
        if 'talk' in title_lower or 'lecture' in title_lower:
            event_type = 'talk'
        elif 'workshop' in title_lower:
            event_type = 'workshop'
        elif 'tour' in title_lower or 'walk' in title_lower:
            event_type = 'tour'
        elif 'conversation' in title_lower:
            event_type = 'talk'
        elif 'first thursdays' in title_lower:
            event_type = 'talk'
        
        # Extract image
        image_url = None
        img_elem = soup.find('img', class_=re.compile(r'hero|feature|main|event', re.I))
        if not img_elem:
            # Look for first image in content area
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content', re.I))
            if main_content:
                img_elem = main_content.find('img')
        
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src')
            if img_src:
                image_url = urljoin(NPG_BASE_URL, img_src)
        
        # Build event dictionary
        event = {
            'title': title,
            'description': description or f"Event at {VENUE_NAME}",
            'event_type': event_type,
            'source_url': url,
            'organizer': VENUE_NAME,
            'social_media_platform': 'website',
            'social_media_url': url,
        }
        
        if event_date:
            event['start_date'] = event_date
            event['end_date'] = event_date
        else:
            # Default to today if no date found
            event['start_date'] = date.today()
        
        if start_time:
            # Format start time in 12-hour format
            start_hour_12 = start_time.hour
            start_am_pm = 'a.m.'
            if start_hour_12 >= 12:
                start_am_pm = 'p.m.'
                if start_hour_12 > 12:
                    start_hour_12 = start_hour_12 - 12
            elif start_hour_12 == 0:
                start_hour_12 = 12
            event['start_time'] = f"{start_hour_12}:{start_time.minute:02d} {start_am_pm}"
        
        if end_time:
            # Format end time in 12-hour format
            end_hour_12 = end_time.hour
            end_am_pm = 'a.m.'
            if end_hour_12 >= 12:
                end_am_pm = 'p.m.'
                if end_hour_12 > 12:
                    end_hour_12 = end_hour_12 - 12
            elif end_hour_12 == 0:
                end_hour_12 = 12
            event['end_time'] = f"{end_hour_12}:{end_time.minute:02d} {end_am_pm}"
        
        if meeting_point:
            event['meeting_point'] = meeting_point
        
        if price is not None:
            event['price'] = price
            event['admission_price'] = price
        
        if registration_required:
            event['is_registration_required'] = True
        
        if registration_url:
            event['registration_url'] = registration_url
        
        # Set registration_info - use extracted text if available (e.g., "Free. Registration Required."), otherwise create default
        if registration_info:
            event['registration_info'] = registration_info
        elif registration_required:
            event['registration_info'] = 'Registration required'
        elif registration_url:
            event['registration_info'] = 'Registration available'
        
        if image_url:
            event['image_url'] = image_url
        
        return event
        
    except Exception as e:
        logger.warning(f"   ⚠️ Error scraping event detail {url}: {e}")
        return None


def scrape_npg_programs(scraper=None) -> List[Dict]:
    """
    Scrape adult and family programs from NPG
    Returns list of event dictionaries
    """
    if scraper is None:
        scraper = create_scraper()
    
    events = []
    
    # Scrape adult programs
    try:
        logger.info(f"🔍 Scraping NPG adult programs from: {NPG_ADULT_PROGRAMS_URL}")
        response = scraper.get(NPG_ADULT_PROGRAMS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all program sections/links
        # Look for headings that might contain program information
        program_headings = soup.find_all(['h2', 'h3', 'h4'])
        
        processed_titles = set()
        
        for heading in program_headings:
            heading_text = heading.get_text(strip=True)
            heading_lower = heading_text.lower()
            
            # Look for Conversation Circle (every other Friday)
            if 'conversation circle' in heading_lower:
                # Check if we've already processed this
                if 'Conversation Circle' in processed_titles:
                    continue
                processed_titles.add('Conversation Circle')
                
                # Extract details from the page content
                container = heading.parent or heading.find_next_sibling()
                if container:
                    container_text = container.get_text()
                    
                    # Look for time information
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.)', container_text, re.I)
                    start_time_str = '10:00 a.m.'
                    end_time_str = '12:00 p.m.'
                    if time_match:
                        start_time_str = f"{time_match.group(1)}:{time_match.group(2)} {time_match.group(3)}"
                    
                    # Look for location
                    location = 'G Street Lobby'
                    if 'g street' in container_text.lower():
                        location = 'G Street Lobby'
                    
                    # Create events for next 2 months (every other Friday)
                    today = date.today()
                    week_count = 0
                    for i in range(60):
                        program_date = today + timedelta(days=i)
                        if program_date.weekday() == 4:  # Friday
                            week_count += 1
                            # Every other Friday means even week numbers
                            if week_count % 2 == 1:
                                event = {
                                    'title': 'Conversation Circle',
                                    'description': 'Every other Friday from 10:00 a.m. to 12:00 p.m. in the G Street Lobby. This program encourages English-language learners to practice conversational skills, learn new vocabulary, and meet friends.',
                                    'event_type': 'program',
                                    'start_date': program_date,
                                    'end_date': program_date,
                                    'start_time': start_time_str,
                                    'end_time': end_time_str,
                                    'meeting_point': location,
                                    'source_url': NPG_ADULT_PROGRAMS_URL,
                                    'organizer': VENUE_NAME,
                                    'social_media_platform': 'website',
                                    'social_media_url': NPG_ADULT_PROGRAMS_URL,
                                }
                                events.append(event)
            
            # Look for Drawn to Figures (monthly on select Tuesdays)
            elif 'drawn to figures' in heading_lower or 'drawn to figure' in heading_lower:
                if 'Drawn to Figures' in processed_titles:
                    continue
                processed_titles.add('Drawn to Figures')
                
                container = heading.parent or heading.find_next_sibling()
                if container:
                    container_text = container.get_text()
                    
                    # Extract time: 11:30 a.m. to 1:30 p.m.
                    start_time_str = '11:30 a.m.'
                    end_time_str = '1:30 p.m.'
                    
                    # Create events for next 3 months (once per month on Tuesdays)
                    today = date.today()
                    tuesday_count = 0
                    last_month = -1
                    for i in range(90):
                        program_date = today + timedelta(days=i)
                        if program_date.weekday() == 1:  # Tuesday
                            # Only add if it's a different month
                            if program_date.month != last_month:
                                event = {
                                    'title': 'Drawn to Figures',
                                    'description': 'Monthly on select Tuesdays from 11:30 a.m. to 1:30 p.m. Join drop-in sketching sessions in the galleries with artist Jill Galloway. Open to artists of all levels, ages 18 and up.',
                                    'event_type': 'workshop',
                                    'start_date': program_date,
                                    'end_date': program_date,
                                    'start_time': start_time_str,
                                    'end_time': end_time_str,
                                    'meeting_point': 'Galleries',
                                    'source_url': NPG_ADULT_PROGRAMS_URL,
                                    'organizer': VENUE_NAME,
                                    'social_media_platform': 'website',
                                    'social_media_url': NPG_ADULT_PROGRAMS_URL,
                                }
                                events.append(event)
                                last_month = program_date.month
        
        # Also look for individual program/event links
        program_links = soup.find_all('a', href=re.compile(r'/event/|/program'))
        
        processed_urls = set()
        
        for link in program_links:
            href = link.get('href', '')
            if not href:
                continue
            
            full_url = urljoin(NPG_BASE_URL, href)
            
            if full_url in processed_urls:
                continue
            processed_urls.add(full_url)
            
            # Try to scrape program detail if it's an event page
            if '/event/' in full_url:
                try:
                    program_data = scrape_event_detail(scraper, full_url)
                    if program_data and program_data.get('title') not in processed_titles:
                        events.append(program_data)
                        processed_titles.add(program_data.get('title'))
                except Exception as e:
                    logger.debug(f"   ⚠️ Error scraping program {full_url}: {e}")
        
        logger.info(f"   ✅ Found {len(events)} adult programs")
        
    except Exception as e:
        logger.error(f"❌ Error scraping NPG adult programs: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_all_npg_events() -> List[Dict]:
    """Main function to scrape all NPG events (exhibitions, tours, talks, programs)"""
    scraper = create_scraper()
    all_events = []
    
    logger.info("🖼️ Starting comprehensive NPG scraping...")
    
    # 1. Scrape exhibitions
    logger.info("📋 Scraping exhibitions...")
    exhibitions = scrape_npg_exhibitions(scraper)
    all_events.extend(exhibitions)
    logger.info(f"   ✅ Found {len(exhibitions)} exhibitions")
    
    # 2. Scrape tours (DISABLED - taking too much space)
    # logger.info("🚶 Scraping tours...")
    # tours = scrape_npg_tours(scraper)
    # all_events.extend(tours)
    # logger.info(f"   ✅ Found {len(tours)} tours")
    
    # 3. Scrape events (talks, etc.)
    logger.info("🎤 Scraping events (talks, etc.)...")
    events = scrape_npg_events(scraper)
    all_events.extend(events)
    logger.info(f"   ✅ Found {len(events)} events")
    
    # 4. Scrape programs
    logger.info("📚 Scraping programs...")
    programs = scrape_npg_programs(scraper)
    all_events.extend(programs)
    logger.info(f"   ✅ Found {len(programs)} programs")
    
    logger.info(f"✅ Total NPG events scraped: {len(all_events)}")
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
                # Find venue
                venue = Venue.query.filter(
                    db.func.lower(Venue.name).like(f'%{VENUE_NAME.lower()}%')
                ).first()
                
                if not venue:
                    logger.warning(f"   ⚠️  Venue '{VENUE_NAME}' not found, skipping event: {event_data.get('title')}")
                    continue
                
                # Find city
                city = City.query.filter(
                    db.func.lower(City.name).like(f'%{CITY_NAME.lower().split(",")[0]}%')
                ).first()
                
                if not city:
                    logger.warning(f"   ⚠️  City '{CITY_NAME}' not found, skipping event: {event_data.get('title')}")
                    continue
                
                # Validate required fields
                title = event_data.get('title', '').strip()
                if not title:
                    logger.warning(f"   ⚠️  Skipping event: missing title")
                    continue
                
                # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                from scripts.utils import is_category_heading, get_ongoing_exhibition_dates, detect_ongoing_exhibition
                if is_category_heading(title):
                    logger.debug(f"   ⏭️ Skipping category heading: '{title}'")
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
                
                # Handle missing start_date - check if it might be ongoing/permanent
                if not event_data.get('start_date'):
                    # Check if event might be ongoing/permanent
                    description_text = event_data.get('description', '') or ''
                    event_type = event_data.get('event_type', '').lower()
                    is_ongoing = detect_ongoing_exhibition(description_text) or detect_ongoing_exhibition(title)
                    
                    # If it's an exhibition without dates, treat as ongoing
                    if event_type == 'exhibition' or 'exhibition' in title.lower():
                        is_ongoing = True
                    
                    if is_ongoing:
                        # Set dates for ongoing exhibition
                        start_date_obj, end_date_obj = get_ongoing_exhibition_dates()
                        event_data['start_date'] = start_date_obj
                        event_data['end_date'] = end_date_obj
                        logger.info(f"   🔄 Treating '{title}' as ongoing/permanent exhibition (start: {start_date_obj.isoformat()}, end: {end_date_obj.isoformat()})")
                    else:
                        logger.warning(f"   ⚠️  Skipping event '{title}': missing start_date")
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
                            time_str = str(event_data['start_time'])
                            start_time_obj = parse_time(time_str)
                    except (ValueError, TypeError):
                        pass
                
                if event_data.get('end_time'):
                    try:
                        if isinstance(event_data['end_time'], time):
                            end_time_obj = event_data['end_time']
                        else:
                            time_str = str(event_data['end_time'])
                            end_time_obj = parse_time(time_str)
                    except (ValueError, TypeError):
                        pass
                
                # Check if event already exists
                existing = None
                source_url = event_data.get('source_url') or event_data.get('url')
                
                # First, try to match by title + venue + date (for recurring events)
                existing = Event.query.filter_by(
                    title=event_data.get('title'),
                    venue_id=venue.id,
                    start_date=event_date,
                    city_id=city.id
                ).first()
                
                # If not found and we have a unique URL, try URL-based matching
                if not existing and source_url:
                    generic_urls = ['/docent-tours', '/tours', '/events', '/whats-on']
                    is_generic_url = any(generic in source_url.lower() for generic in generic_urls)
                    
                    if not is_generic_url:
                        existing = Event.query.filter_by(
                            url=source_url,
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
                    
                    if event_data.get('description') and (not existing.description or len(event_data['description']) > len(existing.description or '')):
                        existing.description = event_data.get('description')
                        updated = True
                    
                    if source_url and existing.url != source_url:
                        existing.url = source_url
                        updated = True
                    
                    if event_data.get('image_url') and not existing.image_url:
                        existing.image_url = event_data.get('image_url')
                        updated = True
                    
                    if event_data.get('meeting_point') and existing.start_location != event_data.get('meeting_point'):
                        existing.start_location = event_data.get('meeting_point')
                        updated = True
                    
                    if start_time_obj and (not existing.start_time or existing.start_time != start_time_obj):
                        existing.start_time = start_time_obj
                        updated = True
                    
                    if end_time_obj and (not existing.end_time or existing.end_time != end_time_obj):
                        existing.end_time = end_time_obj
                        updated = True
                    
                    # Update baby-friendly flag if detected
                    if hasattr(Event, 'is_baby_friendly') and is_baby_friendly:
                        if not existing.is_baby_friendly:
                            existing.is_baby_friendly = True
                            updated = True
                    
                    if updated:
                        db.session.commit()
                        updated_count += 1
                        logger.info(f"   ✅ Updated: {event_data['title']}")
                else:
                    # Create new event
                    location_text = event_data.get('meeting_point') or event_data.get('location') or venue.name
                    
                    event = Event(
                        title=event_data['title'],
                        description=event_data.get('description'),
                        start_date=event_date,
                        end_date=end_date,
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        start_location=location_text,
                        venue_id=venue.id,
                        city_id=city.id,
                        event_type=event_data.get('event_type', 'event'),
                        url=source_url,
                        image_url=event_data.get('image_url'),
                        social_media_platform=event_data.get('social_media_platform', 'website'),
                        social_media_url=source_url,
                        organizer=VENUE_NAME,
                    )
                    
                    # Set baby-friendly flag if detected
                    if hasattr(Event, 'is_baby_friendly'):
                        event.is_baby_friendly = is_baby_friendly
                    
                    db.session.add(event)
                    db.session.commit()
                    created_count += 1
                    logger.info(f"   ✅ Created: {event_data['title']}")
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing event '{event_data.get('title', 'Unknown')}': {e}")
                db.session.rollback()
                continue
        
        logger.info(f"✅ Created {created_count} events, updated {updated_count} events")
        return (created_count, updated_count)


if __name__ == '__main__':
    # Test the scraper
    events = scrape_all_npg_events()
    print(f"\n✅ Scraped {len(events)} events")
    
    # Create events in database
    created, updated = create_events_in_database(events)
    print(f"✅ Created {created} events, updated {updated} events")
