#!/usr/bin/env python3
"""
Scraper for Webster's Bookstore Cafe events
Scrapes events from the community page: https://www.webstersbooksandcafe.com/community
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time
from bs4 import BeautifulSoup
import cloudscraper

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City, Source

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBSTERS_URL = 'https://www.webstersbooksandcafe.com/community'
VENUE_NAME = "Webster's Bookstore Cafe"
CITY_NAME = "State College"
STATE = "Pennsylvania"

def scrape_websters_events():
    """Scrape all events from Webster's community page"""
    events = []
    
    try:
        # Create a cloudscraper session to bypass bot detection
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
        
        logger.info(f"🔍 Scraping Webster's events from: {WEBSTERS_URL}")
        response = scraper.get(WEBSTERS_URL, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # New pattern to match date markers: "Jan 29th:", "Feb 1st:", etc.
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_map = {m: i+1 for i, m in enumerate(months)}
        month_pattern = '|'.join(months)
        date_marker_pattern = rf'({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*:'
        
        # Regular expression for time: e.g. "10am - 2pm" or "7:30 - 11:30" or "6:30pm - 8pm"
        time_pattern = re.compile(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', re.I)
        
        # Find all positions of date markers
        matches = list(re.finditer(date_marker_pattern, page_text))
        
        if not matches:
            logger.warning("⚠️ No date markers found on the page.")
            return []
        
        current_year = datetime.now().year
        today = date.today()
        
        for i in range(len(matches)):
            start_pos = matches[i].start()
            end_pos = matches[i+1].start() if i+1 < len(matches) else len(page_text)
            
            chunk = page_text[start_pos:end_pos].strip()
            month_str = matches[i].group(1)
            day_val = int(matches[i].group(2))
            month_val = month_map[month_str]
            
            date_line_match = re.match(date_marker_pattern, chunk)
            content = chunk[date_line_match.end():].strip()
            
            lines = content.split('\n')
            name_buffer = []
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                t_match = time_pattern.search(line)
                if t_match:
                    # Time found!
                    time_str = t_match.group(0)
                    
                    line_parts = line.split(time_str)
                    pre_text = line_parts[0].strip(':').strip()
                    post_text = line_parts[1].strip() if len(line_parts) > 1 else ""
                    
                    if pre_text:
                        name_buffer.append(pre_text)
                    
                    event_name = " ".join(name_buffer).strip()
                    event_name = re.sub(r'\s+', ' ', event_name).strip(':').strip()
                    
                    if not event_name or event_name == "Event":
                        event_name = "Webster's Event"
                    
                    # Filter garbage
                    if any(garbage in event_name for garbage in ['Contact8', '133 E. Beaver', 'info@websters']):
                        name_buffer = []
                        continue
                    
                    # Times
                    start_h = int(t_match.group(1))
                    start_m = int(t_match.group(2)) if t_match.group(2) else 0
                    start_ampm = t_match.group(3).lower() if t_match.group(3) else None
                    
                    end_h = int(t_match.group(4))
                    end_m = int(t_match.group(5)) if t_match.group(5) else 0
                    end_ampm = t_match.group(6).lower() if t_match.group(6) else None
                    
                    if not start_ampm and end_ampm:
                        start_ampm = end_ampm
                    elif not start_ampm:
                        if start_h >= 8 and start_h < 12: start_ampm = 'am'
                        else: start_ampm = 'pm'
                    if not end_ampm:
                        end_ampm = start_ampm
                        
                    def to_24h(h, ampm):
                        if ampm == 'pm' and h != 12: return h + 12
                        if ampm == 'am' and h == 12: return 0
                        return h
                        
                    start_24h = to_24h(start_h, start_ampm)
                    end_24h = to_24h(end_h, end_ampm)
                    
                    try:
                        start_time_obj = time(start_24h, start_m)
                        end_time_obj = time(end_24h, end_m)
                    except ValueError:
                        continue
                        
                    try:
                        event_date = date(current_year, month_val, day_val)
                        if event_date < today:
                            if month_val <= 2 and today.month >= 11:
                                event_date = date(current_year + 1, month_val, day_val)
                            else:
                                name_buffer = []
                                continue
                    except ValueError:
                        continue
                        
                    if event_date == today:
                        if start_time_obj < datetime.now().time():
                            name_buffer = []
                            continue

                    # Type detection
                    event_type = 'community_event'
                    name_low = event_name.lower()
                    if any(w in name_low for w in ['brunch', 'food']): event_type = 'food'
                    elif any(w in name_low for w in ['music', 'concert', 'jazz', 'quartet', 'open mic', 'show']): event_type = 'music'
                    elif any(w in name_low for w in ['workshop', 'class', 'writing', 'write', 'golden wheel']): event_type = 'workshop'
                    elif any(w in name_low for w in ['talk', 'reading', 'author', 'book', 'lecture']): event_type = 'talk'
                    
                    events.append({
                        'title': event_name,
                        'description': f"{event_name} at Webster's Bookstore Cafe. {post_text}",
                        'start_date': event_date.isoformat(),
                        'end_date': event_date.isoformat(),
                        'start_time': start_time_obj.strftime('%H:%M'),
                        'end_time': end_time_obj.strftime('%H:%M'),
                        'event_type': event_type,
                        'url': WEBSTERS_URL,
                        'venue_name': VENUE_NAME,
                        'city_name': CITY_NAME,
                        'source': 'website'
                    })
                    logger.info(f"   ✅ Found event: {event_name} on {event_date} at {start_time_obj}")
                    name_buffer = []
                else:
                    name_buffer.append(line)
        
        logger.info(f"✅ Scraped {len(events)} Webster's events")
        return events
        
    except Exception as e:
        logger.error(f"❌ Error scraping Webster's events: {e}")
        return []

def create_events_in_database(events):
    """Create events in the database from scraped data"""
    created_count = 0
    
    with app.app_context():
        city = City.query.filter_by(name=CITY_NAME, state=STATE).first()
        if not city:
            logger.error(f"❌ City {CITY_NAME}, {STATE} not found")
            return 0
        
        venue = Venue.query.filter_by(name=VENUE_NAME, city_id=city.id).first()
        if not venue:
            venue = Venue(
                name=VENUE_NAME,
                city_id=city.id,
                address="133 E. Beaver Ave",
                website_url="https://www.webstersbooksandcafe.com/",
                phone_number="814-272-1410",
                email="info@webstersbooksandcafe.com",
                venue_type="cafe",
                description="A vibrant community hub in downtown State College."
            )
            db.session.add(venue)
            db.session.commit()
        
        for event_data in events:
            try:
                title = event_data.get('title', '').strip()
                if not title: continue
                
                # Check for duplicates
                existing = Event.query.filter_by(
                    title=title,
                    start_date=datetime.fromisoformat(event_data['start_date']).date(),
                    venue_id=venue.id
                ).first()
                
                if existing: continue
                
                event = Event(
                    title=title,
                    description=event_data.get('description', ''),
                    start_date=datetime.fromisoformat(event_data['start_date']).date(),
                    end_date=datetime.fromisoformat(event_data.get('end_date', event_data['start_date'])).date(),
                    start_time=time.fromisoformat(event_data['start_time']),
                    end_time=time.fromisoformat(event_data.get('end_time', '23:59')),
                    event_type=event_data.get('event_type'),
                    url=event_data.get('url', WEBSTERS_URL),
                    venue_id=venue.id,
                    city_id=city.id,
                    source='website',
                    source_url=WEBSTERS_URL
                )
                
                db.session.add(event)
                db.session.commit()
                created_count += 1
                logger.info(f"   ✅ Created event: {title}")
                
            except Exception as e:
                logger.error(f"   ❌ Error creating event {title}: {e}")
                db.session.rollback()
        
        return created_count

if __name__ == '__main__':
    events = scrape_websters_events()
    if events:
        created = create_events_in_database(events)
        print(f"✅ Found {len(events)} events, created {created} new ones.")
    else:
        print("❌ No events found.")
