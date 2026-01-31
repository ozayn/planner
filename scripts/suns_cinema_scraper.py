#!/usr/bin/env python3
"""
Specialized Scraper for Suns Cinema (Washington, DC)
Scrapes movie showtimes and upcoming screenings.
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import urllib3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City
from scripts.utils import update_scraping_progress, parse_date_range

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VENUE_NAME = "Suns Cinema"
CITY_NAME = "Washington"
BASE_URL = "https://sunscinema.com/"

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

def parse_time(time_str: str) -> Optional[time]:
    """Parse time string like '6:00 pm'"""
    if not time_str:
        return None
    time_str = time_str.strip().lower()
    # Remove 'sold out' if present
    time_str = time_str.replace('sold out', '').strip()
    
    try:
        return datetime.strptime(time_str, '%I:%M %p').time()
    except ValueError:
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return None

def scrape_suns_cinema() -> List[Dict]:
    """
    Scrape events from Suns Cinema using specialized CSS selectors
    Returns list of event dictionaries
    """
    scraper = create_scraper()
    events = []
    
    try:
        logger.info(f"🔍 Scraping Suns Cinema from: {BASE_URL}")
        response = scraper.get(BASE_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        today = date.today()
        current_year = today.year
        
        # 1. Scrape Current Showtimes
        # Based on the HTML debug, showtimes are in h2 tags
        h2_tags = soup.find_all('h2')
        
        for h2 in h2_tags:
            title = h2.get_text(strip=True)
            if not title or title.lower() in ['upcoming movies', 'coming soon', 'suns cinema', 'future dates', 'sold out']:
                continue
                
            # Get specific URL for this movie
            link_elem = h2.find_parent('a') or h2.find('a')
            movie_url = urljoin(BASE_URL, link_elem.get('href')) if link_elem and link_elem.get('href') else BASE_URL

            # Find the nearest container or parent that might have showtimes
            parent = h2.find_parent('div', class_='show') or h2.find_parent('div') or h2.parent
            
            show_text = parent.get_text()
            time_matches = list(re.finditer(r'(\d{1,2}:\d{2})\s*(am|pm)', show_text, re.I))
            
            if not time_matches:
                # Try looking in next siblings
                curr = h2.next_sibling
                while curr and not time_matches:
                    if hasattr(curr, 'get_text'):
                        text = curr.get_text()
                        time_matches = list(re.finditer(r'(\d{1,2}:\d{2})\s*(am|pm)', text, re.I))
                        if time_matches: show_text = text
                    curr = curr.next_sibling

            # Get description
            desc_elem = parent.select_one('.show__description') or parent.select_one('p')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            for tm in time_matches:
                t_str = tm.group(0)
                p_time = parse_time(t_str)
                # Check if "Sold Out" appears shortly after the time
                is_sold_out = "Sold Out" in show_text[tm.end():tm.end()+50]
                
                final_desc = description
                if is_sold_out:
                    final_desc = f"[SOLD OUT] {description}".strip()
                
                events.append({
                    'title': title,
                    'start_date': today,
                    'start_time': p_time,
                    'event_type': 'film',
                    'venue_name': VENUE_NAME,
                    'city_name': CITY_NAME,
                    'description': final_desc,
                    'url': movie_url,
                    'source': 'website'
                })

        # 2. Scrape "Upcoming Movies" section
        # These are in h3 tags within the upcoming section
        h3_tags = soup.find_all('h3')
        for h3 in h3_tags:
            title = h3.get_text(strip=True)
            if not title or title.lower() in ['upcoming movies', 'coming soon', 'suns cinema', 'future dates', 'sold out']:
                continue
            
            # Get specific URL for this movie
            link_elem = h3.find_parent('a') or h3.find('a')
            movie_url = urljoin(BASE_URL, link_elem.get('href')) if link_elem and link_elem.get('href') else BASE_URL

            # The date is usually in a parent or sibling container
            parent = h3.find_parent()
            parent_text = parent.get_text() if parent else ""
            
            # Try to find a month/day pattern in parent or siblings
            date_match = re.search(r'([A-Z][a-z]{2})\s+(\d{1,2})', parent_text)
            if not date_match:
                # Try previous sibling text
                prev = h3.find_previous(string=True)
                if prev: date_match = re.search(r'([A-Z][a-z]{2})\s+(\d{1,2})', prev)

            if date_match:
                month_str = date_match.group(1)
                day = int(date_match.group(2))
                month_map = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = month_map.get(month_str)
                if month:
                    year = current_year
                    if month < today.month: year += 1
                    event_date = date(year, month, day)
                    
                    events.append({
                        'title': title,
                        'start_date': event_date,
                        'event_type': 'film',
                        'venue_name': VENUE_NAME,
                        'city_name': CITY_NAME,
                        'description': f"Upcoming screening at Suns Cinema",
                        'url': movie_url,
                        'source': 'website'
                    })

        # Deduplicate events by title and date and time
        unique_events = []
        seen = set()
        for e in events:
            key = (e['title'].lower().strip(), e['start_date'], e.get('start_time'))
            if key not in seen:
                unique_events.append(e)
                seen.add(key)
        
        return unique_events

    except Exception as e:
        logger.error(f"❌ Error scraping Suns Cinema: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def scrape_all_suns_cinema_events():
    """Main entry point for the scraper"""
    logger.info("🎬 Starting Suns Cinema scraping...")
    events_data = scrape_suns_cinema()
    
    for e in events_data:
        logger.info(f"Scraped: {e['title']} on {e['start_date']} at {e.get('start_time')} - URL: {e['url']}")
    
    if not events_data:
        logger.warning("⚠️ No events found for Suns Cinema")
        return []
    
    logger.info(f"✅ Found {len(events_data)} events for Suns Cinema")
    
    # Save to database
    with app.app_context():
        # Get venue and city
        venue = Venue.query.filter_by(name=VENUE_NAME).first()
        city = City.query.filter(db.func.lower(City.name) == CITY_NAME.lower()).first()
        
        if not venue:
            logger.error(f"❌ Venue '{VENUE_NAME}' not found")
            return events_data
            
        processed_events = []
        for event_data in events_data:
            # Create a copy to modify
            db_data = event_data.copy()
            
            # Remove non-model fields
            db_data.pop('venue_name', None)
            db_data.pop('city_name', None)
            
            # Ensure venue_id and city_id are set
            db_data['venue_id'] = venue.id
            if city:
                db_data['city_id'] = city.id
            
            # Check for existing event
            existing = Event.query.filter_by(
                title=db_data['title'],
                start_date=db_data['start_date'],
                start_time=db_data.get('start_time'),
                venue_id=venue.id
            ).first()
            
            if existing:
                # Update existing
                for key, value in db_data.items():
                    setattr(existing, key, value)
                processed_events.append(existing)
            else:
                # Create new
                new_event = Event(**db_data)
                db.session.add(new_event)
                processed_events.append(new_event)
        
        db.session.commit()
        logger.info(f"💾 Saved {len(processed_events)} events to database")
        
    return events_data

if __name__ == "__main__":
    scrape_all_suns_cinema_events()
