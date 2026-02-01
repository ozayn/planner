#!/usr/bin/env python3
"""
Custom scraper for National Gallery of Art Finding Awe series
Scrapes all events from the Finding Awe series page
"""
import os
import sys
import re
import logging
import time as time_module
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import cloudscraper
import urllib.parse

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

def create_scraper():
    """Create a cloudscraper session"""
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

def parse_time(time_str: str) -> Optional[time]:
    """Parse time string like '10:30 a.m.'"""
    if not time_str: return None
    # Normalize: "a.m." -> "AM", "p.m." -> "PM"
    time_str = time_str.lower().replace('.', '').replace(' ', '')
    try:
        if 'am' in time_str:
            return datetime.strptime(time_str.replace('am', ''), '%I:%M').time()
        elif 'pm' in time_str:
            t = datetime.strptime(time_str.replace('pm', ''), '%I:%M').time()
            if t.hour != 12: return time(t.hour + 12, t.minute)
            return t
    except: pass
    return None

def scrape_individual_event(event_url, scraper=None):
    """Scrape a single Finding Awe event from its detail page"""
    if not scraper: scraper = create_scraper()
    
    try:
        logger.info(f"   📄 Scraping event: {event_url}")
        
        response = None
        for attempt in range(3):
            try:
                if attempt > 0: time_module.sleep(2 * attempt)
                response = scraper.get(event_url, timeout=20)
                if response.status_code == 200: break
            except: continue
            
        if not response or response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # 1. Extract Title
        title = None
        # Look for h1 tags, but skip utility ones
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            text = h1.get_text(strip=True)
            if text.lower() not in ['global search', 'menu', 'navigation', 'search']:
                title = text
                break
        
        if not title:
            # Fallback to title tag which is very reliable
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True).split('|')[0].strip()
        
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title: title = og_title.get('content', '').strip()
        
        if not title: return None
        
        from scripts.utils import clean_event_title
        title = clean_event_title(title)
        
        # Ensure "Finding Awe:" is part of the title if it's from that series
        if 'finding awe' not in title.lower():
            title = f"Finding Awe: {title}"
        
        # 2. Extract Description
        from scripts.utils import extract_description_from_soup
        description = extract_description_from_soup(soup, max_length=2000)
        
        # 3. Extract Date and Time
        event_date = None
        start_time = None
        end_time = None
        
        # PRIORITY 1: URL evd parameter
        parsed_url = urllib.parse.urlparse(event_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'evd' in query_params and query_params['evd']:
            evd = query_params['evd'][0]
            try:
                event_date = date(int(evd[0:4]), int(evd[4:6]), int(evd[6:8]))
                if len(evd) >= 12:
                    start_time = time(int(evd[8:10]), int(evd[10:12]))
                    # Default duration 105 mins
                    end_dt = datetime.combine(event_date, start_time) + timedelta(minutes=105)
                    end_time = end_dt.time()
                logger.info(f"   📅 Date from URL: {event_date}")
            except: pass

        # PRIORITY 2: Specific Date Container (more accurate for times)
        date_container = soup.find('div', class_='c-event-header__event-date')
        if date_container:
            dt_text = date_container.get_text(strip=True)
            # Example: "Saturday, Jan 31, 2026 | 10:30 a.m.–12:15 p.m."
            
            # Extract date if not found
            if not event_date:
                date_match = re.search(r'([A-Z][a-z]+),\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})', dt_text)
                if date_match:
                    try:
                        month_map = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
                        m_str = date_match.group(2)[:3]
                        event_date = date(int(date_match.group(4)), month_map[m_str], int(date_match.group(3)))
                    except: pass
            
            # Extract precise times
            time_match = re.search(r'(\d{1,2}:\d{2})\s*([ap]\.?m\.?)\s*[–-]\s*(\d{1,2}:\d{2})\s*([ap]\.?m\.?)', dt_text, re.I)
            if time_match:
                start_time = parse_time(f"{time_match.group(1)} {time_match.group(2)}")
                end_time = parse_time(f"{time_match.group(3)} {time_match.group(4)}")
                logger.info(f"   ⏰ Time from page: {start_time} - {end_time}")

        # 4. Extract Location
        location = None
        loc_match = re.search(r'(East Building|West Building)[^.\n]*(?:Upper Level|Lower Level|Main Floor|Level \d+)[^.\n]*(?:Gallery\s+\d+[-\w]*)', page_text, re.I)
        if loc_match: location = loc_match.group(0).strip()
        else:
            loc_elem = soup.find('div', string=re.compile(r'Building|Gallery', re.I))
            if loc_elem: location = loc_elem.get_text(strip=True)

        # 5. Extract Image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image: image_url = og_image.get('content', '').strip()
        
        # 6. Registration
        is_registration_required = "registration required" in page_text.lower()
        registration_url = None
        reg_link = soup.find('a', href=re.compile(r'tickets\.nga\.gov|register|eventbrite', re.I))
        if reg_link: registration_url = urllib.parse.urljoin(event_url, reg_link['href'])

        return {
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
            'is_registration_required': is_registration_required,
            'registration_url': registration_url
        }
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return None

def scrape_all_finding_awe_events(save_incrementally=False, max_days_ahead=30):
    scraper = create_scraper()
    events = []
    
    logger.info(f"🔍 Scraping Finding Awe series from: {FINDING_AWE_URL}")
    try:
        response = scraper.get(FINDING_AWE_URL, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find specific event links
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/calendar/finding-awe/' in href and href != '/calendar/finding-awe':
                links.add(urllib.parse.urljoin(FINDING_AWE_URL, href))
        
        logger.info(f"   Found {len(links)} candidate links")
        
        today = date.today()
        cutoff = today + timedelta(days=max_days_ahead) if max_days_ahead else None
        
        processed_count = 0
        for link in links:
            # Quick check for date in URL to skip old events
            query = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
            if 'evd' in query:
                evd = query['evd'][0]
                try:
                    d = date(int(evd[0:4]), int(evd[4:6]), int(evd[6:8]))
                    if d < today or (cutoff and d > cutoff):
                        continue
                except: pass

            event = scrape_individual_event(link, scraper)
            if event:
                events.append(event)
                processed_count += 1
                
        if save_incrementally and events:
            create_events_in_database(events)
            
        return events
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return []

def create_events_in_database(events):
    from scripts.event_database_handler import create_events_in_database as shared_create_events
    with app.app_context():
        venue = Venue.query.filter(db.func.lower(Venue.name).like('%national gallery of art%')).first()
        if not venue: return 0, 0
        created, updated, skipped = shared_create_events(
            events=events, venue_id=venue.id, city_id=venue.city_id,
            venue_name=venue.name, db=db, Event=Event, Venue=Venue,
            batch_size=5, logger_instance=logger, source_url=FINDING_AWE_URL
        )
        return created, updated

if __name__ == '__main__':
    res = scrape_all_finding_awe_events(save_incrementally=True)
    print(f"Done. Found {len(res)} events.")
