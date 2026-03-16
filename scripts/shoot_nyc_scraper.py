#!/usr/bin/env python3
"""
Shoot New York City scraper.
Scrapes street photography workshops from https://www.shootnewyorkcity.com/workshops
"""

import logging
import re
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.generic_source_scraper import scrape_source_listing
from scripts.scraper_utils import parse_date, parse_time_range

logger = logging.getLogger(__name__)

SHOOT_NYC_WORKSHOPS_URL = "https://www.shootnewyorkcity.com/workshops"


def _extract_shoot_nyc_events(html: str, base_url: str) -> List[dict]:
    """
    Extract workshop events from Shoot NYC workshops page HTML.
    Page structure: event blocks with datetime link, h1/h2 title, list items (location, time, date), description, View Event link.
    """
    events = []
    soup = BeautifulSoup(html, 'html.parser')

    # Find event blocks: look for links to /workshops/ that contain date-like text
    workshop_link_pattern = re.compile(r'/workshops/[a-zA-Z0-9\-]+', re.I)
    seen_keys = set()  # (title, start_date, url) for deduplication

    # Strategy: find all links to workshop detail pages, then for each find its associated block
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if not workshop_link_pattern.search(href):
            continue

        full_url = urljoin(base_url, href)

        # Get the block containing this link (section, article, div, or parent chain)
        block = a.find_parent(['section', 'article', 'div']) or a.parent
        if not block:
            continue

        # Walk up to get a reasonable container (avoid huge blocks)
        for _ in range(5):
            if block and block.name in ('section', 'article', 'div'):
                break
            block = block.parent if block else None
        if not block:
            block = a.parent

        text = block.get_text(separator='\n', strip=True)

        # Title: from h1/h2 in block, or from link text "View Event" sibling
        title = None
        for h in block.find_all(['h1', 'h2', 'h3']):
            t = (h.get_text(strip=True) or '').replace('&amp;', '&')
            if t and len(t) > 3 and ('workshop' in t.lower() or 'street' in t.lower() or 'photography' in t.lower() or 'photo' in t.lower()):
                title = t
                break
        if not title:
            # Fallback: "View Event" link's preceding heading
            view_link = block.find('a', string=re.compile(r'View Event', re.I))
            if view_link:
                prev = view_link.find_previous(['h1', 'h2', 'h3'])
                if prev:
                    title = (prev.get_text(strip=True) or '').replace('&amp;', '&')
        if not title:
            continue

        # Date: "Sunday, March 22, 2026" or "Saturday, March 14, 2026"
        date_match = re.search(
            r'(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),?\s+'
            r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|'
            r'Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2},?\s+\d{4}',
            text, re.I
        )
        event_date = parse_date(date_match.group(0)) if date_match else None

        # Time: "12:00 PM 4:00 PM" or "12:00 PM – 4:00 PM"
        time_match = re.search(
            r'\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[\s–\-—]?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)',
            text, re.I
        )
        start_time, end_time = parse_time_range(time_match.group(0)) if time_match else (None, None)

        # Location: "Chinatown, New York City" or "Soho, New York City" (before [(map)])
        loc_match = re.search(
            r'([^,\n]+),\s*New York City\s*\[?\s*\(map\)',
            text, re.I
        )
        location = loc_match.group(1).strip() if loc_match else None
        if not location:
            loc_match = re.search(r'([^,\n]+),\s*New York City', text, re.I)
            location = loc_match.group(1).strip() if loc_match else None

        # Description: first paragraph after the list, before "View Event"
        desc_parts = []
        for p in block.find_all(['p']):
            s = (p.get_text(strip=True) or '')
            if s and len(s) > 40 and 'View Event' not in s and 'Google Calendar' not in s:
                desc_parts.append(s[:400])
                break
        if not desc_parts:
            # Fallback: any text block 40+ chars that looks like description
            for node in block.find_all(string=True):
                s = (node.strip() if isinstance(node, str) else '')
                if s and len(s) > 40 and not re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', s):
                    if 'workshop' in s.lower() or 'street' in s.lower() or 'photo' in s.lower():
                        desc_parts.append(s[:400])
                        break
        description = desc_parts[0] if desc_parts else None

        # Prefer "View Event" URL for canonical event link
        view_a = block.find('a', string=re.compile(r'View Event', re.I))
        event_url = urljoin(base_url, view_a.get('href')) if view_a and view_a.get('href') else full_url

        if not event_date:
            continue

        dedup_key = (title, str(event_date), event_url)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        events.append({
            'title': title,
            'start_date': event_date,
            'end_date': event_date,
            'start_time': start_time,
            'end_time': end_time,
            'url': event_url,
            'description': description,
            'event_type': 'photowalk',
            'venue_name': 'Shoot New York City',
            'start_location': location,
            'end_location': location,
        })

    return events


def scrape_shoot_nyc_events() -> List[dict]:
    """Scrape Shoot NYC workshops and return normalized event dicts."""
    return scrape_source_listing(
        url=SHOOT_NYC_WORKSHOPS_URL,
        extractor=_extract_shoot_nyc_events,
        use_cloudscraper=True,
    )


def create_events_in_database_wrapper(events: list) -> tuple:
    """Save Shoot NYC events to database. Resolves or creates venue."""
    from app import app, db, Venue, City, Event
    from scripts.event_database_handler import create_events_in_database

    with app.app_context():
        nyc = City.query.filter(db.func.lower(City.name).like('%new york%')).first()
        if not nyc:
            logger.warning("Shoot NYC scraper: New York city not found")
            return 0, 0, 0

        venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%shoot new york%'),
            Venue.city_id == nyc.id,
        ).first()

        if not venue:
            venue = Venue(
                name='Shoot New York City',
                city_id=nyc.id,
                website_url='https://www.shootnewyorkcity.com',
                venue_type='workshop',
                description='Street photography workshops and walking photo tours in NYC.',
            )
            db.session.add(venue)
            db.session.commit()
            logger.info("Created venue: Shoot New York City")

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
            source_url=SHOOT_NYC_WORKSHOPS_URL,
            custom_event_processor=processor,
        )
        return created, updated, skipped


def main():
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger.info("📷 Shoot NYC scraper: scraping workshops...")
    events = scrape_shoot_nyc_events()
    logger.info(f"   Found {len(events)} events")

    if events:
        created, updated, skipped = create_events_in_database_wrapper(events)
        logger.info(f"   Created: {created}, Updated: {updated}, Skipped: {skipped}")
    else:
        logger.info("   No events to save.")

    return events


if __name__ == '__main__':
    main()
