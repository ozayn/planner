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
        
        # Find the events section
        # Events are typically listed in a section with headings like "Webster's Current Events!"
        events_text = soup.get_text()
        
        # Look for the events section - it usually starts with "Webster's Current Events!" or similar
        # Events are listed in format: MM-DD: Event Name Time - Time or MM-DD: Event Name Time
        
        # Pattern to match event lines:
        # Format: MM-DD: Event Name Time - Time
        # Or: MM-DD: Event Name Time
        # May have emojis or special characters
        
        # Find all text that matches the pattern
        # Events are typically in a list or paragraph format
        # Format: MM-DD: Event Name [tabs/spaces] [emoji]Time - Time
        # Example: "12-5: Jazz Quartet						5pm - 6:30pm"
        # Example: "12-3: Jason Adams First Wed. Open Mic		🎤5pm - 7pm"
        # Times can be: "7:30pm", "5pm", "4pm", "6pm", etc.
        # May have **Type** markers like **Brunch**, **Music**
        # May have emojis before the time (🎤, etc.)
        
        # Improved pattern: event name should stop before we hit a time pattern
        # Allow for optional emoji before time, and ensure we capture the first time as start
        # Pattern: MM-DD: EventName [whitespace] [emoji?] Time - Time
        event_pattern = re.compile(
            r'(\d{1,2})-(\d{1,2}):\s*([^\n]+?)(?=\s*[^\w\s]*\s*\d{1,2}:?\d{0,2}\s*(?:am|pm|a\.m\.|p\.m\.))\s*[^\w\s]*\s*(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\s*(?:[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.))?',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Also look for events with just start time
        event_pattern_simple = re.compile(
            r'(\d{1,2})-(\d{1,2}):\s*([^\n]+?)(?=\s*[^\w\s]*\s*\d{1,2}:?\d{0,2}\s*(?:am|pm|a\.m\.|p\.m\.))\s*[^\w\s]*\s*(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Find all event listings in the page
        page_text = soup.get_text()
        
        # Try to find events in the entire text first (multiline matching)
        current_year = datetime.now().year
        
        # Find all matches in the full text
        all_matches = list(event_pattern.finditer(page_text))
        all_matches_simple = list(event_pattern_simple.finditer(page_text))
        
        # Combine and deduplicate matches (prefer matches with end time)
        seen_positions = set()
        matches_to_process = []
        
        # Add matches with end time first
        for match in all_matches:
            pos = match.start()
            if pos not in seen_positions:
                seen_positions.add(pos)
                matches_to_process.append(('full', match))
        
        # Add simple matches only if not already covered
        for match in all_matches_simple:
            pos = match.start()
            # Check if this position is already covered by a full match
            is_covered = False
            for match_type, existing_match in matches_to_process:
                # Check if the matches are for the same event (same date and similar position)
                if abs(existing_match.start() - pos) < 50:  # Within 50 chars, consider it covered
                    is_covered = True
                    # Debug: Log when we skip a simple match because full match exists
                    if 'Book Release' in match.group(0):
                        logger.info(f"   🔍 Skipping simple match for Book Release (covered by full match at position {existing_match.start()})")
                    break
            if not is_covered and pos not in seen_positions:
                seen_positions.add(pos)
                matches_to_process.append(('simple', match))
                # Debug: Log when we add a simple match
                if 'Book Release' in match.group(0):
                    logger.info(f"   🔍 Adding simple match for Book Release at position {pos}")
        
        # Process matches
        for match_type, match in matches_to_process:
            # Debug: Check which match type is being processed for Book Release
            if 'Book Release' in match.group(0):
                logger.info(f"   🔍 Processing {match_type} match for Book Release")
            
            if match_type == 'full':
                # Full match with end time
                month = int(match.group(1))
                day = int(match.group(2))
                event_name = match.group(3).strip()
                start_hour = int(match.group(4))
                start_min = int(match.group(5)) if match.group(5) else 0
                start_ampm_raw = match.group(6)
                start_ampm = start_ampm_raw.lower().replace('.', '')
                end_hour = int(match.group(7)) if match.group(7) else None
                end_min = int(match.group(8)) if match.group(8) and match.group(8) else 0
                end_ampm = match.group(9).lower().replace('.', '') if match.group(9) else None
                
                # Save original 12-hour format values BEFORE conversion
                original_start_hour_12h = start_hour
                original_start_ampm = start_ampm
                original_end_hour_12h = end_hour if end_hour is not None else None
                original_end_ampm = end_ampm
                
                # Debug logging for Book Release Party
                if 'Book Release' in event_name:
                    logger.info(f"   🔍 DEBUG Book Release: hour={start_hour}, ampm_raw='{start_ampm_raw}', ampm='{start_ampm}'")
                
                # Clean event name (remove extra whitespace, emojis, etc.)
                event_name = re.sub(r'\s+', ' ', event_name).strip()
                # Remove **Type** markers but keep the type for event_type detection
                event_type_marker = None
                type_match = re.search(r'\*\*([^*]+)\*\*', event_name)
                if type_match:
                    event_type_marker = type_match.group(1).strip()
                    event_name = re.sub(r'\*\*[^*]+\*\*', '', event_name).strip()
                # Remove emojis
                event_name = re.sub(r'[🎤🎵🎭📚☕]', '', event_name).strip()
                # Remove common prefixes
                event_name = re.sub(r'^(Brunch|Music|Class|Event|Workshop|Reading|Open Mic|Book Club)\s+', '', event_name, flags=re.I).strip()
                
                # Validation: For a coffeeshop, times before 7am are likely errors
                # If we have a time between 1am-6am, it's probably PM (e.g., 5pm not 5am)
                # Check BEFORE converting to 24-hour format
                if 1 <= start_hour <= 6 and start_ampm == 'am':
                    logger.warning(f"   ⚠️  Suspicious AM time {start_hour}:00 for '{event_name}', assuming PM")
                    start_ampm = 'pm'
                
                # Debug logging for Book Release Party
                if 'Book Release' in event_name:
                    logger.info(f"   🔍 DEBUG Before conversion: hour={start_hour}, ampm='{start_ampm}'")
                
                # Convert to 24-hour format
                if start_ampm == 'pm' and start_hour != 12:
                    start_hour += 12
                elif start_ampm == 'am' and start_hour == 12:
                    start_hour = 0
                
                # Debug logging for Book Release Party
                if 'Book Release' in event_name:
                    logger.info(f"   🔍 DEBUG After conversion: hour={start_hour}, creating time({start_hour}, {start_min})")
                
                # Create time object immediately after conversion
                start_time_obj = time(start_hour, start_min)
                
                # Debug: Verify time object was created correctly
                if 'Book Release' in event_name:
                    logger.info(f"   🔍 DEBUG Created time object: {start_time_obj}, strftime: {start_time_obj.strftime('%H:%M')}")
                
                # Calculate end time
                if end_hour is not None and end_ampm:
                    # Validation: For end times, check if they're suspicious AM times
                    if 1 <= end_hour <= 6 and end_ampm == 'am':
                        logger.warning(f"   ⚠️  Suspicious AM end time {end_hour}:00 for '{event_name}', assuming PM")
                        end_ampm = 'pm'
                    
                    if end_ampm == 'pm' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'am' and end_hour == 12:
                        end_hour = 0
                    end_time_obj = time(end_hour, end_min)
                    
                    # Common sense validation: Events shouldn't last more than 8 hours
                    # If duration is unreasonable, the start time is probably wrong
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min
                    duration_hours = (end_minutes - start_minutes) / 60
                    
                    # Handle next-day events
                    if duration_hours < 0:
                        duration_hours += 24
                    
                    if duration_hours > 8:
                        # If event is longer than 8 hours, start time is probably wrong
                        # Check if converting start from AM to PM would fix it
                        # Use original 12-hour format values
                        if 1 <= original_start_hour_12h <= 6 and original_start_ampm == 'am':
                            logger.warning(f"   ⚠️  Unreasonable duration {duration_hours:.1f}h for '{event_name}' (start: {original_start_hour_12h}:{start_min:02d}am, end: {original_end_hour_12h}:{end_min:02d}{original_end_ampm}), converting start time from AM to PM")
                            start_hour = original_start_hour_12h + 12
                            start_time_obj = time(start_hour, start_min)
                            # Recalculate duration
                            start_minutes = start_hour * 60 + start_min
                            duration_hours = (end_minutes - start_minutes) / 60
                            if duration_hours < 0:
                                duration_hours += 24
                            logger.info(f"   ✅ Corrected: {duration_hours:.1f} hours ({start_hour}:{start_min:02d} - {end_hour}:{end_min:02d})")
                    
                    # Debug: Check if start_time_obj was modified
                    if 'Book Release' in event_name:
                        logger.info(f"   🔍 DEBUG After duration validation: start_time_obj = {start_time_obj}")
                else:
                    # Default to 2 hours if no end time specified
                    end_hour_24 = start_hour + 2
                    if end_hour_24 >= 24:
                        end_hour_24 -= 24
                    end_time_obj = time(end_hour_24, start_min)
                
                # Create event date
                try:
                    event_date = date(current_year, month, day)
                    today = date.today()
                    
                    # If the date is in the past, only assume it's next year if:
                    # 1. The month is close to today (within 2 months ahead, like Jan/Feb when we're in Dec)
                    # 2. Otherwise, skip it as a past event
                    if event_date < today:
                        # Calculate months difference
                        months_ahead = (month - today.month) % 12
                        # If the event month is within 2 months ahead (e.g., Jan/Feb when in Dec), assume next year
                        # Otherwise, it's clearly a past event (e.g., Nov when in Dec)
                        if months_ahead <= 2 and months_ahead > 0:
                            event_date = date(current_year + 1, month, day)
                        else:
                            # Event is clearly in the past, skip it
                            logger.info(f"   ⏭️  Skipping past event: {event_name} on {event_date}")
                            continue
                    
                    # Skip events that are still in the past (after checking next year)
                    if event_date < today:
                        logger.info(f"   ⏭️  Skipping past event: {event_name} on {event_date}")
                        continue
                    
                    # Also check if the event datetime (date + time) is in the past
                    event_datetime = datetime.combine(event_date, start_time_obj)
                    if event_datetime < datetime.now():
                        logger.info(f"   ⏭️  Skipping past event: {event_name} on {event_date} at {start_time_obj}")
                        continue
                except ValueError:
                    logger.warning(f"Invalid date: {month}-{day}, skipping")
                    continue
                
                # Determine event type based on name and type marker
                event_type = None
                event_name_lower = event_name.lower()
                
                # Check type marker first
                if event_type_marker:
                    type_marker_lower = event_type_marker.lower()
                    if 'brunch' in type_marker_lower:
                        event_type = 'food'
                    elif 'music' in type_marker_lower:
                        event_type = 'music'
                    elif 'class' in type_marker_lower or 'workshop' in type_marker_lower:
                        event_type = 'workshop'
                    elif 'talk' in type_marker_lower or 'reading' in type_marker_lower:
                        event_type = 'talk'
                
                # Fallback to name-based detection
                if not event_type:
                    if any(word in event_name_lower for word in ['brunch', 'music brunch', 'sunday music brunch']):
                        event_type = 'food'
                    elif any(word in event_name_lower for word in ['music', 'concert', 'performance', 'open mic', 'quartet', 'jazz']):
                        event_type = 'music'
                    elif any(word in event_name_lower for word in ['class', 'workshop', 'lesson', 'mushroom class', 'golden wheel']):
                        event_type = 'workshop'
                    elif any(word in event_name_lower for word in ['book', 'reading', 'author', 'book release']):
                        event_type = 'talk'
                    elif any(word in event_name_lower for word in ['write', 'writing', 'shut up and write']):
                        event_type = 'workshop'
                    elif any(word in event_name_lower for word in ['tarot', 'aura', 'reading']):
                        event_type = 'workshop'
                    else:
                        event_type = 'community_event'
                
                event_data = {
                    'title': event_name,
                    'description': f"Event at {VENUE_NAME}",
                    'start_date': event_date.isoformat(),
                    'end_date': event_date.isoformat(),
                    'start_time': start_time_obj.strftime('%H:%M'),
                    'end_time': end_time_obj.strftime('%H:%M'),
                    'event_type': event_type,
                    'url': WEBSTERS_URL,
                    'venue_name': VENUE_NAME,
                    'city_name': CITY_NAME,
                    'source': 'website'
                }
                
                events.append(event_data)
                logger.info(f"   ✅ Found event: {event_name} on {event_date} at {start_time_obj}")
            
            elif match_type == 'simple':
                # Simple match without end time
                month = int(match.group(1))
                day = int(match.group(2))
                event_name = match.group(3).strip()
                start_hour = int(match.group(4))
                start_min = int(match.group(5)) if match.group(5) else 0
                start_ampm_raw = match.group(6)
                start_ampm = start_ampm_raw.lower().replace('.', '')
                end_hour = None
                end_min = 0
                end_ampm = None
                
                # Validation: For a coffeeshop, times before 7am are likely errors
                # If we have a time between 1am-6am, it's probably PM (e.g., 5pm not 5am)
                # Check BEFORE converting to 24-hour format
                if 1 <= start_hour <= 6 and start_ampm == 'am':
                    logger.warning(f"   ⚠️  Suspicious AM time {start_hour}:00 for '{event_name}' (raw: '{start_ampm_raw}'), assuming PM")
                    start_ampm = 'pm'
                
                # Convert to 24-hour format
                if start_ampm == 'pm' and start_hour != 12:
                    start_hour += 12
                elif start_ampm == 'am' and start_hour == 12:
                    start_hour = 0
                
                start_time_obj = time(start_hour, start_min)
                # Default to 2 hours duration
                end_hour_24 = start_hour + 2
                if end_hour_24 >= 24:
                    end_hour_24 -= 24
                end_time_obj = time(end_hour_24, start_min)
                
                # Create event date
                try:
                    event_date = date(current_year, month, day)
                    today = date.today()
                    
                    # If the date is in the past, only assume it's next year if:
                    # 1. The month is close to today (within 2 months ahead, like Jan/Feb when we're in Dec)
                    # 2. Otherwise, skip it as a past event
                    if event_date < today:
                        # Calculate months difference
                        months_ahead = (month - today.month) % 12
                        # If the event month is within 2 months ahead (e.g., Jan/Feb when in Dec), assume next year
                        # Otherwise, it's clearly a past event (e.g., Nov when in Dec)
                        if months_ahead <= 2 and months_ahead > 0:
                            event_date = date(current_year + 1, month, day)
                        else:
                            # Event is clearly in the past, skip it
                            logger.info(f"   ⏭️  Skipping past event: {event_name} on {event_date}")
                            continue
                    
                    # Skip events that are still in the past (after checking next year)
                    if event_date < today:
                        logger.info(f"   ⏭️  Skipping past event: {event_name} on {event_date}")
                        continue
                    
                    # Also check if the event datetime (date + time) is in the past
                    event_datetime = datetime.combine(event_date, start_time_obj)
                    if event_datetime < datetime.now():
                        logger.info(f"   ⏭️  Skipping past event: {event_name} on {event_date} at {start_time_obj}")
                        continue
                except ValueError:
                    logger.warning(f"Invalid date: {month}-{day}, skipping")
                    continue
                
                # Determine event type based on name and type marker
                event_type = None
                event_name_lower = event_name.lower()
                
                # Check type marker first
                if event_type_marker:
                    type_marker_lower = event_type_marker.lower()
                    if 'brunch' in type_marker_lower:
                        event_type = 'food'
                    elif 'music' in type_marker_lower:
                        event_type = 'music'
                    elif 'class' in type_marker_lower or 'workshop' in type_marker_lower:
                        event_type = 'workshop'
                    elif 'talk' in type_marker_lower or 'reading' in type_marker_lower:
                        event_type = 'talk'
                
                # Fallback to name-based detection
                if not event_type:
                    if any(word in event_name_lower for word in ['brunch', 'music brunch', 'sunday music brunch']):
                        event_type = 'food'
                    elif any(word in event_name_lower for word in ['music', 'concert', 'performance', 'open mic', 'quartet', 'jazz']):
                        event_type = 'music'
                    elif any(word in event_name_lower for word in ['class', 'workshop', 'lesson', 'mushroom class', 'golden wheel']):
                        event_type = 'workshop'
                    elif any(word in event_name_lower for word in ['book', 'reading', 'author', 'book release']):
                        event_type = 'talk'
                    elif any(word in event_name_lower for word in ['write', 'writing', 'shut up and write']):
                        event_type = 'workshop'
                    elif any(word in event_name_lower for word in ['tarot', 'aura', 'reading']):
                        event_type = 'workshop'
                    else:
                        event_type = 'community_event'
                
                event_data = {
                    'title': event_name,
                    'description': f"Event at {VENUE_NAME}",
                    'start_date': event_date.isoformat(),
                    'end_date': event_date.isoformat(),
                    'start_time': start_time_obj.strftime('%H:%M'),
                    'end_time': end_time_obj.strftime('%H:%M'),
                    'event_type': event_type,
                    'url': WEBSTERS_URL,
                    'venue_name': VENUE_NAME,
                    'city_name': CITY_NAME,
                    'source': 'website'
                }
                
                events.append(event_data)
                logger.info(f"   ✅ Found event: {event_name} on {event_date} at {start_time_obj}")
        
        logger.info(f"✅ Scraped {len(events)} Webster's events")
        return events
        
    except Exception as e:
        logger.error(f"❌ Error scraping Webster's events: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def create_events_in_database(events):
    """Create events in the database from scraped data"""
    created_count = 0
    
    with app.app_context():
        # Get city and venue
        city = City.query.filter_by(name=CITY_NAME, state=STATE).first()
        if not city:
            logger.error(f"❌ City {CITY_NAME}, {STATE} not found in database")
            return 0
        
        venue = Venue.query.filter_by(name=VENUE_NAME, city_id=city.id).first()
        if not venue:
            logger.warning(f"⚠️  Venue {VENUE_NAME} not found, creating it...")
            # Create venue
            venue = Venue(
                name=VENUE_NAME,
                city_id=city.id,
                address="133 E. Beaver Ave",
                website_url="https://www.webstersbooksandcafe.com/",
                phone_number="814-272-1410",
                email="info@webstersbooksandcafe.com",
                venue_type="cafe",
                description="A vibrant community hub in downtown State College, offering a unique blend of a used bookstore with thousands of titles and a cafe serving organic, fair-trade European-style coffee beverages, tea, and other beverages that are all plant-based."
            )
            db.session.add(venue)
            db.session.commit()
            logger.info(f"✅ Created venue: {VENUE_NAME}")
        
        # Get source
        source = Source.query.filter_by(url=WEBSTERS_URL).first()
        
        for event_data in events:
            try:
                # Check if event already exists
                existing = Event.query.filter_by(
                    title=event_data['title'],
                    start_date=datetime.fromisoformat(event_data['start_date']).date(),
                    venue_id=venue.id
                ).first()
                
                if existing:
                    logger.debug(f"   ⏭️  Event already exists: {event_data['title']}")
                    continue
                
                # Create new event
                event = Event(
                    title=event_data['title'],
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
                logger.info(f"   ✅ Created event: {event_data['title']}")
                
            except Exception as e:
                logger.error(f"   ❌ Error creating event {event_data.get('title', 'Unknown')}: {e}")
                db.session.rollback()
                continue
        
        logger.info(f"✅ Created {created_count} new events in database")
        return created_count


if __name__ == '__main__':
    print("🔍 Scraping Webster's Bookstore Cafe events...")
    events = scrape_websters_events()
    
    if events:
        print(f"\n✅ Found {len(events)} events")
        print("\n📋 Events:")
        for event in events:
            print(f"  - {event['title']} on {event['start_date']} at {event['start_time']}")
        
        print("\n💾 Creating events in database...")
        created = create_events_in_database(events)
        print(f"✅ Created {created} new events")
    else:
        print("❌ No events found")

