#!/usr/bin/env python3
"""
DC Chinese New Year Parade Scraper
Scrapes the annual parade event from dcparade.com
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

import requests
from bs4 import BeautifulSoup

from scripts.event_database_handler import create_events_in_database

logger = logging.getLogger(__name__)

DCPARADE_URL = "https://dcparade.com/"
DCPARADE_FAQ_URL = "https://dcparade.com/faq/"


def _parse_parade_date(text: str) -> tuple:
    """Parse date/time from text like 'SUNDAY, FEBRUARY 22, 2026 - 2:00 PM'."""
    start_date, start_time = None, None
    if not text:
        return start_date, start_time

    # Date: February 22, 2026 or FEBRUARY 22, 2026
    date_match = re.search(
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2},?\s+\d{4}',
        text, re.I
    )
    if date_match:
        date_str = date_match.group(0)
        for fmt in ['%B %d, %Y', '%b %d, %Y', '%B. %d, %Y', '%b. %d, %Y']:
            try:
                start_date = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue

    # Time: 2:00 PM or 2pm
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text, re.I)
    if time_match:
        hour, minute, ampm = int(time_match.group(1)), int(time_match.group(2) or 0), time_match.group(3).upper()
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        start_time = f'{hour:02d}:{minute:02d}'

    return start_date, start_time


def _parse_time_to_end_time(start_time: str, duration_minutes: int) -> str | None:
    """Given start_time (HH:MM) and duration in minutes, return end_time as HH:MM."""
    if not start_time or ':' not in start_time:
        return None
    try:
        parts = start_time.split(':')
        hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        total_minutes = hour * 60 + minute + duration_minutes
        end_hour = (total_minutes // 60) % 24
        end_min = total_minutes % 60
        return f'{end_hour:02d}:{end_min:02d}'
    except (ValueError, IndexError):
        return None


def _scrape_faq_route_and_timing(session: requests.Session) -> dict:
    """
    Scrape FAQ page for parade route (start/end locations) and timing (duration, firecracker time).
    Returns dict with start_location, end_location, end_time (or duration_minutes), firecracker_time.
    """
    result = {'start_location': None, 'end_location': None, 'duration_minutes': 50, 'firecracker_time': '16:00'}
    try:
        resp = session.get(DCPARADE_FAQ_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        page_text = soup.get_text()

        # Route: "starts on 6th and Eye St NW and ends on 6th and H"
        route_match = re.search(
            r'starts?\s+on\s+([^.]+?)\s+and\s+ends?\s+on\s+([^.]+?)(?:\.|$)',
            page_text, re.I
        )
        if route_match:
            start = route_match.group(1).strip().replace('Eye St', 'I St').replace('Eye ', 'I ')
            end = route_match.group(2).strip()
            if 'Street' not in end and 'St' not in end:
                end = f"{end} Street NW"
            if 'NW' not in end:
                end = f"{end} NW"
            result['start_location'] = start if start else '6th and I Street NW, Chinatown'
            result['end_location'] = end if end else '6th and H Street NW, Chinatown'

        # Duration: "takes about 50 minutes"
        dur_match = re.search(r'takes?\s+about\s+(\d+)\s+minutes?', page_text, re.I)
        if dur_match:
            result['duration_minutes'] = int(dur_match.group(1))

        # Firecracker: "between 3:45pm and 4pm" - use end time as event end
        fc_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)\s+and\s+(\d{1,2}):?(\d{2})?\s*(am|pm)', page_text, re.I)
        if fc_match:
            h2, m2 = int(fc_match.group(4)), int(fc_match.group(5) or 0)
            ampm = fc_match.group(6).upper()
            if ampm == 'PM' and h2 != 12:
                h2 += 12
            elif ampm == 'AM' and h2 == 12:
                h2 = 0
            result['firecracker_time'] = f'{h2:02d}:{m2:02d}'
    except Exception as e:
        logger.debug(f"Could not scrape FAQ for route/timing: {e}")
    return result


def scrape_dcparade_events() -> list:
    """
    Scrape the DC Chinese New Year Parade event from dcparade.com.
    Returns list of event dicts (typically one event per year).
    """
    events = []
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })

    try:
        resp = session.get(DCPARADE_URL, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Title from h2 or h1
        title = None
        for tag in soup.find_all(['h1', 'h2']):
            t = (tag.get_text(strip=True) or '').replace('&#8217;', "'")
            if 'parade' in t.lower() and 'chinese' in t.lower() and len(t) > 10:
                title = t
                break
        if not title:
            title = "DC Chinese Lunar New Year Parade"

        # Date/time from h3 - often "SUNDAY, FEBRUARY 22, 2026 - 2:00 PM"
        date_time_text = ''
        for h3 in soup.find_all('h3'):
            txt = h3.get_text(strip=True)
            if re.search(r'\d{4}', txt) and ('am' in txt.lower() or 'pm' in txt.lower()):
                date_time_text = txt
                break

        start_date, start_time = _parse_parade_date(date_time_text)

        # Fallback: try meta or any date on page
        if not start_date:
            page_text = soup.get_text()
            start_date, start_time = _parse_parade_date(page_text[:2000])

        if not start_date:
            logger.warning("Could not parse parade date from page")
            return events

        # Scrape FAQ for route and timing
        faq_data = _scrape_faq_route_and_timing(session)
        start_location = faq_data.get('start_location') or '6th and I Street NW, Chinatown'
        end_location = faq_data.get('end_location') or '6th and H Street NW, Chinatown'
        # End time: firecracker finale ~4pm, or parade start + 50 min
        end_time = faq_data.get('firecracker_time')
        if not end_time and start_time:
            end_time = _parse_time_to_end_time(start_time, faq_data.get('duration_minutes', 50))

        # Description - first substantial paragraph
        description = None
        for p in soup.find_all('p'):
            text = (p.get_text(strip=True) or '').replace('&#8217;', "'").replace('&#8211;', '-')
            if len(text) > 80 and 'parade' in text.lower():
                description = text[:600]
                break
        if not description:
            description = "Annual Chinese Lunar New Year Parade in DC Chinatown. Cultural performances, lion dances, firecracker show on H Street. Metro: Gallery Place/Chinatown."

        # Image - og:image or first parade-related image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image.get('content')
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(DCPARADE_URL, image_url)
        if not image_url:
            for img in soup.find_all('img', src=True):
                src = img.get('src', '')
                if 'parade' in src.lower() or 'chinatown' in src.lower() or 'gallery' in src.lower():
                    image_url = urljoin(DCPARADE_URL, src)
                    break

        # Add Metro context to locations if not already present
        metro_note = ' (Gallery Place/Chinatown Metro)'
        if metro_note not in (start_location or ''):
            start_location = f"{start_location}{metro_note}" if start_location else f"H Street, Chinatown{metro_note}"
        if metro_note not in (end_location or ''):
            end_location = f"{end_location}{metro_note}" if end_location else f"6th and H Street NW, Chinatown{metro_note}"

        events.append({
            'title': title,
            'description': description,
            'start_date': start_date,
            'end_date': start_date,
            'start_time': start_time,
            'end_time': end_time,
            'url': DCPARADE_URL,
            'event_type': 'festival',
            'venue_name': 'DC Chinatown',
            'start_location': start_location,
            'end_location': end_location,
            'image_url': image_url,
        })
        logger.info(f"   Found: {title} on {start_date} at {start_time}-{end_time or '?'} | {start_location} → {end_location}")

    except Exception as e:
        logger.error(f"Error scraping dcparade.com: {e}")
        import traceback
        logger.debug(traceback.format_exc())

    return events


def create_events_in_database_wrapper(events: list) -> tuple:
    """Save DC Parade events to database."""
    from app import app, db, Venue, City, Event

    with app.app_context():
        dc = City.query.filter(db.func.lower(City.name).like('%washington%')).first()
        if not dc:
            logger.warning("DC Parade scraper: Washington DC city not found")
            return 0, 0, 0

        # Prefer DC Chinese New Year Parade venue, fall back to DC Chinatown
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%chinese new year parade%'),
            Venue.city_id == dc.id
        ).first()
        if not venue:
            venue = Venue.query.filter(
                db.func.lower(Venue.name).like('%chinatown%'),
                Venue.city_id == dc.id
            ).first()
        if not venue:
            logger.warning("DC Parade scraper: DC Chinese New Year Parade or DC Chinatown venue not found (run reload-venues-from-json)")
            return 0, 0, 0

        def processor(e):
            e['source'] = 'website'

        created, updated, skipped = create_events_in_database(
            events=events,
            venue_id=venue.id,
            city_id=venue.city_id,
            venue_name=venue.name,
            db=db,
            Event=Event,
            Venue=Venue,
            custom_event_processor=processor
        )
        return created, updated, skipped


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger.info("🏮 DC Chinese New Year Parade scraper: scraping dcparade.com...")
    events = scrape_dcparade_events()
    logger.info(f"   Found {len(events)} events")

    if events:
        created, updated, skipped = create_events_in_database_wrapper(events)
        logger.info(f"   Created: {created}, Updated: {updated}, Skipped: {skipped}")
    else:
        logger.info("   No events to save.")

    return events


if __name__ == '__main__':
    main()
