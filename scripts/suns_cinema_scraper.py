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
    Scrape events from Suns Cinema
    Returns list of event dictionaries
    """
    scraper = create_scraper()
    events = []
    
    try:
        logger.info(f"🔍 Scraping Suns Cinema from: {BASE_URL}")
        response = scraper.get(BASE_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Scrape Current Showtimes (Home Page)
        # Suns Cinema uses Filmbot. The showtimes are usually organized by day.
        # Looking at the provided content, it has tabs like "Saturday, Jan 31", "Sunday, Feb 1"
        
        # Let's look for movie containers
        # Common Filmbot patterns: .movie-row, .movie-container, etc.
        # Based on the text content provided:
        # "Saturday, Jan 31 Sunday, Feb 1 Monday, Feb 2 Future Dates"
        # "A NEW LOVE IN TOKYO Life, love, sex, work, play… there are so many ways to tie them up."
        # "6:00 pmSold Out"
        
        # We'll try to find the movie entries
        # Since I don't have the exact HTML structure, I'll use text-based heuristic or common Filmbot patterns
        
        # Filmbot usually has sections for each day
        # Let's look for anything that looks like a movie entry
        movie_entries = soup.find_all(class_=re.compile(r'movie|film|showtime', re.I))
        
        # If no specific classes found, look for headings followed by times
        if not movie_entries:
            movie_entries = soup.find_all(['h2', 'h3', 'h4'])
            
        # Extract today's date for reference
        today = date.today()
        current_year = today.year
        
        # 2. Scrape "Upcoming Movies" section
        upcoming_section = soup.find(string=re.compile(r'Upcoming Movies', re.I))
        if upcoming_section:
            parent = upcoming_section.find_parent()
            if parent:
                # Look for list items or divs following this section
                upcoming_list = parent.find_next_sibling(['ul', 'div'])
                if upcoming_list:
                    items = upcoming_list.find_all(['li', 'div'])
                    for item in items:
                        text = item.get_text(strip=True)
                        # Pattern: "Feb 1 THE STRANGER AND THE FOG"
                        match = re.match(r'^([A-Z][a-z]{2})\s+(\d{1,2})\s+(.+)$', text)
                        if match:
                            month_str = match.group(1)
                            day = int(match.group(2))
                            title = match.group(3).strip()
                            
                            # Convert month to number
                            month_map = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            month = month_map.get(month_str)
                            if month:
                                # Determine year (handle year wrap-around)
                                year = current_year
                                if month < today.month:
                                    year += 1
                                
                                event_date = date(year, month, day)
                                
                                events.append({
                                    'title': title,
                                    'start_date': event_date,
                                    'event_type': 'film',
                                    'venue_name': VENUE_NAME,
                                    'city_name': CITY_NAME,
                                    'description': f"Upcoming screening at Suns Cinema",
                                    'url': BASE_URL,
                                    'source': 'website'
                                })

        # 3. Process current day showtimes if we can find them
        # Looking at the provided content:
        # "A NEW LOVE IN TOKYO" ... "6:00 pmSold Out"
        # "THE MOTHER & THE BEAR" ... "8:45 pmSold Out"
        
        # Heuristic: Find titles (all caps usually) and check for nearby time patterns
        all_text = soup.get_text()
        
        # Look for dates like "Saturday, Jan 31"
        date_matches = re.finditer(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Z][a-z]{2})\s+(\d{1,2})', all_text)
        
        date_positions = []
        for m in date_matches:
            month_str = m.group(2)
            day = int(m.group(3))
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month = month_map.get(month_str)
            if month:
                year = current_year
                if month < today.month:
                    year += 1
                event_date = date(year, month, day)
                date_positions.append((m.start(), m.end(), event_date))
        
        # Sort date positions to iterate between them
        date_positions.sort()
        
        for i in range(len(date_positions)):
            start_pos = date_positions[i][1]
            end_pos = date_positions[i+1][0] if i+1 < len(date_positions) else len(all_text)
            
            section_text = all_text[start_pos:end_pos]
            event_date = date_positions[i][2]
            
            # Look for movie entries in this section
            # Heuristic: Titles are usually followed by descriptions and then times
            # Let's try to find time patterns like "6:00 pm"
            time_matches = re.finditer(r'(\d{1,2}:\d{2})\s*(am|pm)(Sold Out)?', section_text, re.I)
            
            last_pos = 0
            for tm in time_matches:
                t_str = f"{tm.group(1)} {tm.group(2)}"
                p_time = parse_time(t_str)
                is_sold_out = bool(tm.group(3))
                
                # The title should be before this time
                pre_time_text = section_text[last_pos:tm.start()].strip()
                
                # Split by lines and look for something that looks like a title
                lines = [l.strip() for l in pre_time_text.split('\n') if l.strip()]
                if lines:
                    # Often the title is the first line or the longest line among the first few
                    title = lines[0]
                    # Clean up title - if it's too long, it might be a description
                    if len(title) > 100:
                        title = title[:100] + "..."
                    
                    description = ""
                    if len(lines) > 1:
                        description = " ".join(lines[1:])
                    
                    if is_sold_out:
                        description = f"[SOLD OUT] {description}".strip()
                    
                    events.append({
                        'title': title,
                        'start_date': event_date,
                        'start_time': p_time,
                        'event_type': 'film',
                        'venue_name': VENUE_NAME,
                        'city_name': CITY_NAME,
                        'description': description,
                        'url': BASE_URL,
                        'source': 'website'
                    })
                
                last_pos = tm.end()

        # Deduplicate events by title and date
        unique_events = []
        seen = set()
        for e in events:
            key = (e['title'], e['start_date'], e.get('start_time'))
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
