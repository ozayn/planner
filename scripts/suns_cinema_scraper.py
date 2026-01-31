#!/usr/bin/env python3
"""
Specialized Scraper for Suns Cinema (Washington, DC)
Scrapes movie showtimes and upcoming screenings with full details.
"""
import os
import sys
import re
import logging
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
from scripts.utils import update_scraping_progress, parse_date_range

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VENUE_NAME = "Suns Cinema"
CITY_NAME = "Washington"
BASE_URL = "https://sunscinema.com/"

# Cache for movie details to avoid redundant requests
movie_details_cache = {}

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

def scrape_movie_details(scraper, movie_url: str) -> Dict:
    """
    Scrapes details for a specific movie from its page
    """
    if movie_url in movie_details_cache:
        return movie_details_cache[movie_url]
    
    details = {
        'description': "",
        'image_url': None,
        'run_time': None,
        'director': None,
        'language': None,
        'starring': None,
        'found_times': []
    }
    
    if not movie_url or movie_url == BASE_URL:
        return details
        
    try:
        logger.info(f"  ∟ 🔍 Fetching details from: {movie_url}")
        response = scraper.get(movie_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extract Image
        img_elem = soup.find('img', alt=re.compile(r'Poster for', re.I))
        if not img_elem:
            img_elem = soup.select_one('.movie-poster img, .poster img')
            
        if img_elem and img_elem.get('src'):
            details['image_url'] = img_elem.get('src')
        
        # 2. Extract Metadata
        page_text = soup.get_text()
        
        # Extract Director - Use non-greedy match until "Run Time" or newline
        dir_match = re.search(r'Director:\s*(.*?)(?=\s*(?:Run Time|Release Year|Language|Starring|$|\n))', page_text, re.I | re.DOTALL)
        if dir_match:
            details['director'] = dir_match.group(1).strip().rstrip('.').rstrip(',')
        
        # Extract Run Time
        rt_match = re.search(r'Run Time:\s*(\d+)\s*min', page_text, re.I)
        if rt_match:
            details['run_time'] = int(rt_match.group(1))
        
        # Extract Language
        lang_match = re.search(r'Language:\s*([^\n|.]+)', page_text, re.I)
        if lang_match:
            details['language'] = lang_match.group(1).strip()

        # Extract Starring
        star_match = re.search(r'Starring:\s*(.*?)(?=\s*(?:Legendary|Restored|Trailer|Copyright|$|\n))', page_text, re.I | re.DOTALL)
        if star_match:
            details['starring'] = star_match.group(1).strip()

        # 3. Extract Description
        description_parts = []
        for p in soup.find_all('p'):
            p_text = p.get_text(strip=True)
            if len(p_text) > 50 and not any(x in p_text for x in ['Director:', 'Starring:', 'Run Time:', 'Language:']):
                if not any(x in p_text.lower() for x in ['copyright', 'powered by', 'skip to content']):
                    description_parts.append(p_text)
                    if len(description_parts) >= 2: break

        details['description'] = "\n\n".join(description_parts)
        
        # 4. Extract Showtimes
        time_matches = re.findall(r'(\d{1,2}:\d{2})\s*(am|pm)', page_text, re.I)
        if time_matches:
            details['found_times'] = [f"{t[0]} {t[1]}" for t in time_matches]

        # Construct enhanced description
        meta_info = []
        if details['director']:
            # Shorten "Director" to "Dir." for a more professional, cinematic feel
            meta_info.append(f"Dir. {details['director']}")
        if details['language']:
            meta_info.append(details['language'])
        if details['run_time']:
            meta_info.append(f"{details['run_time']} min")
            
        header = " • ".join(meta_info)
        
        enhanced_parts = []
        if header:
            enhanced_parts.append(header)
        if details['starring']:
            enhanced_parts.append(f"Cast: {details['starring']}")
            
        if details['description']:
            # Use double newlines for clear separation
            enhanced_parts.append(details['description'])
            
        details['full_description'] = "\n\n".join(enhanced_parts)
        
        movie_details_cache[movie_url] = details
        return details
        
    except Exception as e:
        logger.error(f"    ❌ Error fetching movie details: {e}")
        return details

def scrape_suns_cinema() -> List[Dict]:
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
        h2_tags = soup.find_all('h2')
        for h2 in h2_tags:
            title = h2.get_text(strip=True)
            if not title or title.lower() in ['upcoming movies', 'coming soon', 'suns cinema', 'future dates', 'sold out']:
                continue
            link_elem = h2.find_parent('a') or h2.find('a')
            movie_url = urljoin(BASE_URL, link_elem.get('href')) if link_elem and link_elem.get('href') else BASE_URL
            details = scrape_movie_details(scraper, movie_url)
            parent = h2.find_parent('div', class_='show') or h2.find_parent('div') or h2.parent
            show_text = parent.get_text()
            time_matches = list(re.finditer(r'(\d{1,2}:\d{2})\s*(am|pm)', show_text, re.I))
            if not time_matches and details['found_times']:
                p_time = parse_time(details['found_times'][0])
                time_matches = [p_time]
            for tm in time_matches:
                if isinstance(tm, time):
                    p_time = tm
                    is_sold_out = False
                else:
                    t_str = tm.group(0)
                    p_time = parse_time(t_str)
                    is_sold_out = "Sold Out" in show_text[tm.end():tm.end()+50]
                e_time = None
                if p_time and details['run_time']:
                    dummy_dt = datetime.combine(today, p_time)
                    e_time = (dummy_dt + timedelta(minutes=details['run_time'])).time()
                events.append({
                    'title': title, 'start_date': today, 'start_time': p_time, 'end_time': e_time,
                    'event_type': 'film', 'venue_name': VENUE_NAME, 'city_name': CITY_NAME,
                    'description': f"[SOLD OUT] {details.get('full_description', '')}" if is_sold_out else details.get('full_description', ""),
                    'image_url': details['image_url'], 'url': movie_url, 'source': 'website'
                })

        # 2. Scrape Upcoming
        h3_tags = soup.find_all('h3')
        for h3 in h3_tags:
            title = h3.get_text(strip=True)
            if not title or title.lower() in ['upcoming movies', 'coming soon', 'suns cinema', 'future dates', 'sold out']:
                continue
            link_elem = h3.find_parent('a') or h3.find('a')
            movie_url = urljoin(BASE_URL, link_elem.get('href')) if link_elem and link_elem.get('href') else BASE_URL
            details = scrape_movie_details(scraper, movie_url)
            parent = h3.find_parent()
            parent_text = parent.get_text() if parent else ""
            date_match = re.search(r'([A-Z][a-z]{2})\s+(\d{1,2})', parent_text)
            if not date_match:
                prev = h3.find_previous(string=True)
                if prev: date_match = re.search(r'([A-Z][a-z]{2})\s+(\d{1,2})', prev)
            if date_match:
                month_str = date_match.group(1)
                day = int(date_match.group(2))
                month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
                month = month_map.get(month_str)
                if month:
                    year = current_year
                    if month < today.month: year += 1
                    event_date = date(year, month, day)
                    time_match = re.search(r'(\d{1,2}:\d{2})\s*(am|pm)', parent_text, re.I)
                    p_time = parse_time(time_match.group(0)) if time_match else (parse_time(details['found_times'][0]) if details['found_times'] else None)
                    e_time = None
                    if p_time and details['run_time']:
                        dummy_dt = datetime.combine(event_date, p_time)
                        e_time = (dummy_dt + timedelta(minutes=details['run_time'])).time()
                    events.append({
                        'title': title, 'start_date': event_date, 'start_time': p_time, 'end_time': e_time,
                        'event_type': 'film', 'venue_name': VENUE_NAME, 'city_name': CITY_NAME,
                        'description': details.get('full_description', f"Upcoming screening at Suns Cinema"),
                        'image_url': details['image_url'], 'url': movie_url, 'source': 'website'
                    })

        # Deduplicate - Prefer events with times
        deduped = {}
        for e in events:
            key = (e['title'].lower().strip(), e['start_date'])
            existing = deduped.get(key)
            if not existing or (not existing.get('start_time') and e.get('start_time')):
                deduped[key] = e
            elif existing and existing.get('start_time') == e.get('start_time'):
                # Already have this time, keep the one with more description
                if len(e.get('description', '')) > len(existing.get('description', '')):
                    deduped[key] = e
        
        return list(deduped.values())

    except Exception as e:
        logger.error(f"❌ Error scraping Suns Cinema: {e}")
        return []

def scrape_all_suns_cinema_events():
    logger.info("🎬 Starting Suns Cinema scraping...")
    events_data = scrape_suns_cinema()
    if not events_data:
        return []
    with app.app_context():
        venue = Venue.query.filter_by(name=VENUE_NAME).first()
        city = City.query.filter(db.func.lower(City.name) == CITY_NAME.lower()).first()
        if not venue: return events_data
        for event_data in events_data:
            db_data = event_data.copy()
            db_data.pop('venue_name', None); db_data.pop('city_name', None)
            db_data['venue_id'] = venue.id
            if city: db_data['city_id'] = city.id
            existing = Event.query.filter_by(title=db_data['title'], start_date=db_data['start_date'], start_time=db_data.get('start_time'), venue_id=venue.id).first()
            if existing:
                for key, value in db_data.items(): setattr(existing, key, value)
            else:
                db.session.add(Event(**db_data))
        db.session.commit()
    return events_data

if __name__ == "__main__":
    scrape_all_suns_cinema_events()
