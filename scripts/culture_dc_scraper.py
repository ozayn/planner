#!/usr/bin/env python3
"""
Specialized Scraper for Culture DC (Washington, DC)
Scrapes music events, DJ sets, and upcoming performances.
"""
import os
import sys
import re
import logging
import json
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import urllib3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City
from scripts.utils import update_scraping_progress

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VENUE_NAME = "Culture DC"
CITY_NAME = "Washington"
BASE_URL = "https://www.culturedc.com"
EVENTS_URL = "https://www.culturedc.com/events"

def create_scraper():
    """Create a session for scraping"""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    })
    return session

def parse_culture_date(date_str: str) -> Optional[date]:
    """Parse date string like 'February 6, 2026' or 'February, 14th 2025'"""
    if not date_str:
        return None
    
    # Clean up common artifacts from scraping
    date_str = date_str.replace('Calendar Icon', '').replace('Clock Icon', '').strip()
    
    # Handle "February, 14th 2025" -> "February 14 2025"
    # Remove ordinal suffixes (st, nd, rd, th)
    date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
    # Remove commas and extra whitespace
    date_str = date_str.replace(',', ' ').strip()
    date_str = re.sub(r'\s+', ' ', date_str)
    
    # Common formats
    formats = [
        '%B %d %Y',  # February 14 2025
        '%b %d %Y',  # Feb 14 2025
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    return None

def parse_culture_time(time_str: str) -> Optional[time]:
    """Parse time string like '10:00 PM'"""
    if not time_str:
        return None
    
    time_str = time_str.strip().upper().replace('CLOCK ICON', '').strip()
    
    # Handle "10:00 PM" or "10 PM"
    try:
        return datetime.strptime(time_str, '%I:%M %p').time()
    except ValueError:
        try:
            return datetime.strptime(time_str, '%I %p').time()
        except ValueError:
            return None

def scrape_event_details(scraper, event_url: str) -> Dict:
    """
    Scrapes details for a specific event from its page
    """
    details = {
        'description': "",
        'image_url': None
    }
    
    if not event_url or event_url == EVENTS_URL:
        return details
        
    try:
        logger.info(f"  ∟ 🔍 Fetching details from: {event_url}")
        response = scraper.get(event_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extract Image
        # Look for the main event image
        img_elem = soup.find('img', class_='event-image')
        if not img_elem:
            # Fallback to og:image
            og_img = soup.find('meta', property='og:image')
            if og_img:
                details['image_url'] = og_img.get('content')
        else:
            details['image_url'] = img_elem.get('src')
            
        # 2. Extract Description
        # Look for description containers
        desc_elem = soup.find('div', class_='event-description') or \
                    soup.find('div', class_='rich-text-block') or \
                    soup.find('div', class_=re.compile(r'description|detail', re.I))
        
        if desc_elem:
            details['description'] = desc_elem.get_text(separator=' ', strip=True)
        else:
            # Fallback to general text if needed, but try to avoid footer/nav
            main_content = soup.find('main') or soup.find('div', class_='section')
            if main_content:
                details['description'] = main_content.get_text(separator=' ', strip=True)
                
    except Exception as e:
        logger.error(f"  ∟ ❌ Error fetching details: {e}")
        
    return details

def scrape_culture_dc() -> List[Dict]:
    """
    Main scraping function for Culture DC
    """
    scraper = create_scraper()
    events = []
    
    try:
        logger.info(f"🚀 Starting scrape for {VENUE_NAME}...")
        response = scraper.get(EVENTS_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for links to /events/
        event_links = soup.find_all('a', href=re.compile(r'/events/'))
        logger.info(f"Found {len(event_links)} potential event links")
        
        unique_events = {}
        
        # Use a higher-level container if possible to find title/date/time
        # In evaluation, many links were found inside cards
        
        for link in event_links:
            try:
                event_url = urljoin(BASE_URL, link.get('href'))
                if event_url == EVENTS_URL:
                    continue
                
                # Find the nearest container that has the event info
                # Usually it's a few levels up
                container = link
                for _ in range(5):
                    if container.parent:
                        container = container.parent
                        if 'w-dyn-item' in container.get('class', []) or \
                           'event' in str(container.get('class', [])).lower():
                            break
                
                text = container.get_text(separator=' ', strip=True)
                
                # Title - try to find a heading
                title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'div'], 
                                          class_=re.compile(r'title|name|heading', re.I))
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Try to get first non-empty text line
                    title = link.get_text(strip=True) or link.get('title') or ""
                
                # Clean title
                title = title.replace('Culture - ', '').replace('Calendar Icon', '').strip()
                
                # Date and Time
                # Formats: "February 6, 2026", "10:00 PM"
                # Updated regex to handle "February, 14th 2025" and other variations
                # Optional commas and spaces everywhere
                date_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{4}'
                time_pattern = r'\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)'
                
                date_match = re.search(date_pattern, text, re.I)
                time_match = re.search(time_pattern, text, re.I)
                
                if not date_match:
                    continue
                
                # If title is still weak, use everything before the date match
                if not title or len(title) < 3:
                    title = text[:date_match.start()].strip()
                
                # Further clean title
                title = re.sub(r'\s*Calendar Icon\s*', '', title)
                title = title.strip()
                
                event_date = parse_culture_date(date_match.group(0))
                event_time = parse_culture_time(time_match.group(0)) if time_match else None
                
                if not event_date:
                    continue
                
                # Skip past events (more than 1 day ago)
                today = date.today()
                if event_date < today - timedelta(days=1):
                    logger.debug(f"Skipping past event: {title} on {event_date}")
                    continue
                
                # Deduplicate by URL and Date
                event_key = f"{event_url}_{event_date}"
                if event_key in unique_events:
                    continue
                
                logger.info(f"Found event: {title} on {event_date}")
                
                # Get more details from event page
                details = scrape_event_details(scraper, event_url)
                
                event_data = {
                    'title': title,
                    'start_date': event_date,
                    'end_date': event_date,
                    'start_time': event_time,
                    'url': event_url,
                    'description': details['description'],
                    'image_url': details['image_url'],
                    'event_type': 'music',
                    'venue_name': VENUE_NAME,
                    'city_name': CITY_NAME
                }
                
                unique_events[event_key] = event_data
                
            except Exception as e:
                logger.error(f"Error processing link {link.get('href')}: {e}")
                continue
                
        events = list(unique_events.values())
        logger.info(f"✅ Successfully scraped {len(events)} unique events from {VENUE_NAME}")
        
    except Exception as e:
        logger.error(f"❌ Critical error scraping {VENUE_NAME}: {e}")
        
    return events

def save_events_to_db(events: List[Dict]):
    """Save scraped events to the database"""
    if not events:
        logger.info("No events to save.")
        return
        
    with app.app_context():
        city = City.query.filter_by(name=CITY_NAME).first()
        venue = Venue.query.filter_by(name=VENUE_NAME).first()
        
        if not city or not venue:
            logger.error(f"Missing city ({CITY_NAME}) or venue ({VENUE_NAME}) in database")
            return
            
        added_count = 0
        updated_count = 0
        
        for event_data in events:
            # Check if event already exists
            existing_event = Event.query.filter_by(
                title=event_data['title'],
                start_date=event_data['start_date'],
                venue_id=venue.id
            ).first()
            
            if existing_event:
                # Update existing event
                existing_event.start_time = event_data['start_time']
                existing_event.url = event_data['url']
                if event_data['description']:
                    existing_event.description = event_data['description']
                if event_data['image_url']:
                    existing_event.image_url = event_data['image_url']
                existing_event.event_type = 'music'
                updated_count += 1
            else:
                # Create new event
                new_event = Event(
                    title=event_data['title'],
                    description=event_data['description'],
                    start_date=event_data['start_date'],
                    end_date=event_data['end_date'],
                    start_time=event_data['start_time'],
                    url=event_data['url'],
                    image_url=event_data['image_url'],
                    event_type='music',
                    city_id=city.id,
                    venue_id=venue.id,
                    source='website'
                )
                db.session.add(new_event)
                added_count += 1
                
        db.session.commit()
        logger.info(f"Database update complete: {added_count} added, {updated_count} updated.")
        
        # Update scraping progress
        message = f"Found {len(events)} events, saved {added_count} new, updated {updated_count}"
        update_scraping_progress(1, 1, message, events_found=len(events), events_saved=added_count, events_updated=updated_count, venue_name=VENUE_NAME)

def scrape_all_culture_dc_events():
    """Main entry point for scraping and saving"""
    events = scrape_culture_dc()
    save_events_to_db(events)
    return events

if __name__ == "__main__":
    scrape_all_culture_dc_events()
