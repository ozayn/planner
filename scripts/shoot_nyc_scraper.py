#!/usr/bin/env python3
"""
Shoot New York City scraper.
Scrapes street photography workshops from https://www.shootnewyorkcity.com/workshops

Prices are embedded via Eventbrite checkout widgets. When EVENTBRITE_API_TOKEN is set,
we fetch prices from the Eventbrite API using event IDs extracted from the Squarespace JSON.
"""

import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from typing import List, Optional

from bs4 import BeautifulSoup

from scripts.generic_source_scraper import scrape_source_listing
from scripts.scraper_utils import parse_date, parse_time_range

logger = logging.getLogger(__name__)

SHOOT_NYC_WORKSHOPS_URL = "https://www.shootnewyorkcity.com/workshops"

# Eventbrite event ID in Squarespace body: eventId: '1234567890' or eventId: "1234567890"
_EVENTBRITE_EVENT_ID_RE = re.compile(r"eventId\s*:\s*['\"](\d+)['\"]", re.I)


def _fetch_eventbrite_price(event_id: str) -> Optional[float]:
    """
    Fetch minimum ticket price from Eventbrite API for a given event ID.
    Returns None if API token is missing or request fails.
    Uses same logic as eventbrite_scraper.convert_eventbrite_event_to_our_format.
    """
    api_token = os.getenv('EVENTBRITE_API_TOKEN') or os.getenv('EVENTBRITE_PRIVATE_TOKEN')
    if not api_token:
        return None
    try:
        from scripts.eventbrite_scraper import EventbriteScraper
        scraper = EventbriteScraper()
        details = scraper.get_event_details(event_id)
        if not details:
            return None
        is_free = details.get('is_free') is True
        if is_free:
            return 0.0
        # ticket_classes can be a list or a paginated object {ticket_classes: [...]}
        raw_tc = details.get('ticket_classes') or []
        ticket_classes = raw_tc.get('ticket_classes', raw_tc) if isinstance(raw_tc, dict) else raw_tc
        class_prices = []
        general_admission_prices = []
        workshop_prices = []  # Prefer tickets with "workshop" (main event, not add-ons)
        for tc in ticket_classes:
            if not isinstance(tc, dict):
                continue
            if tc.get('hidden') is True or tc.get('donation') is True:
                continue
            if tc.get('on_sale_status') not in (None, 'AVAILABLE'):
                continue
            if tc.get('free') is True:
                class_prices.append(0.0)
                continue
            cost = tc.get('cost') or {}
            fee = tc.get('fee') or {}
            tax = tc.get('tax') or {}
            major_value = cost.get('major_value')
            if major_value is not None:
                try:
                    total = float(major_value)
                    if fee.get('major_value') is not None:
                        total += float(fee.get('major_value', 0))
                    if tax.get('major_value') is not None:
                        total += float(tax.get('major_value', 0))
                    class_prices.append(total)
                    name_lower = (tc.get('name') or '').lower()
                    if 'general' in name_lower or 'admission' in name_lower:
                        general_admission_prices.append(total)
                    # Shoot NYC: prefer "workshop" tickets over add-ons (e.g. $10 prints)
                    if 'workshop' in name_lower:
                        workshop_prices.append(total)
                except (TypeError, ValueError):
                    pass
        if workshop_prices:
            return min(workshop_prices)
        if general_admission_prices:
            return min(general_admission_prices)
        if class_prices:
            return min(class_prices)
        # Fallback to ticket_availability.minimum_ticket_price
        tav = details.get('ticket_availability') or {}
        min_price = tav.get('minimum_ticket_price') or {}
        mv = min_price.get('major_value')
        if mv is not None:
            try:
                return float(mv)
            except (TypeError, ValueError):
                pass
        return None
    except Exception as e:
        logger.debug(f"Eventbrite price fetch failed for {event_id}: {e}")
        return None


def _build_urlid_to_eventid_map() -> dict:
    """
    Fetch Squarespace workshops JSON and build a map of urlId -> Eventbrite event ID.
    The body of each event contains eventId: '1234567890' from the Eventbrite widget.
    """
    url_to_event_id = {}
    try:
        req = Request(
            f"{SHOOT_NYC_WORKSHOPS_URL}?format=json",
            headers={'User-Agent': 'Mozilla/5.0 (compatible; Planner/1.0)'},
        )
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger.debug(f"Could not fetch Shoot NYC JSON for Eventbrite IDs: {e}")
        return url_to_event_id
    for item in data.get('upcoming', []) + data.get('past', []):
        url_id = item.get('urlId') or ''
        body = item.get('body') or ''
        match = _EVENTBRITE_EVENT_ID_RE.search(body)
        if match and url_id:
            url_to_event_id[url_id] = match.group(1)
    if url_to_event_id:
        logger.debug(f"   Mapped {len(url_to_event_id)} Shoot NYC workshop URL(s) to Eventbrite IDs")
    return url_to_event_id


def _extract_price(text: str, html: Optional[str] = None) -> Optional[float]:
    """
    Extract price from block text (and optionally HTML) when clearly available.
    Returns float (0 for free, amount for paid) or None if unclear/missing.
    """
    # Search in combined text (text + html if provided, for data attributes etc.)
    search_in = (text or "") + "\n" + (html or "")
    if not search_in.strip():
        return None
    t = search_in.strip()
    # Free: "free photo walk", "free street photo", "holding a free", title "Free Photo Walk"
    if re.search(r'\bfree\s+(photo|street|meet|event|walk)', t, re.I):
        return 0.0
    if re.search(r'holding a free\b', t, re.I):
        return 0.0
    if re.search(r'\bFree\b', t) and re.search(r'(photo|walk|meet)', t, re.I):
        return 0.0
    # Dollar amounts: $125, $150, $125.00
    m = re.search(r'\$(\d+(?:\.\d{2})?)', t)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    # USD amounts: 125 USD, 150 USD
    m = re.search(r'(\d+(?:\.\d{2})?)\s*USD\b', t, re.I)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _extract_shoot_nyc_events(html: str, base_url: str) -> List[dict]:
    """
    Extract workshop events from Shoot NYC workshops page HTML.
    Page structure: event blocks with datetime link, h1/h2 title, list items (location, time, date), description, View Event link.

    Prices: Shoot NYC embeds Eventbrite checkout. We fetch Squarespace JSON to get event IDs from the body,
    then use Eventbrite API (when EVENTBRITE_API_TOKEN is set) to get prices.
    """
    events = []
    skipped_past = 0
    soup = BeautifulSoup(html, 'html.parser')
    today = date.today()

    try:
        from scripts.env_config import ensure_env_loaded
        ensure_env_loaded()
    except ImportError:
        pass

    # Build urlId -> Eventbrite event ID map for price lookup (from Squarespace JSON)
    urlid_to_eventid = _build_urlid_to_eventid_map()
    if not urlid_to_eventid and (os.getenv('EVENTBRITE_API_TOKEN') or os.getenv('EVENTBRITE_PRIVATE_TOKEN')):
        logger.warning("   Squarespace JSON returned no Eventbrite IDs - prices will use text/URL fallback only")

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

        # Skip past events (only keep today or future)
        if event_date < today:
            skipped_past += 1
            continue

        dedup_key = (title, str(event_date), event_url)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        # Extract price: prefer Eventbrite API (Shoot NYC uses Eventbrite for ticketing)
        price = None
        url_id = (event_url or "").rstrip("/").split("/")[-1] if event_url else ""
        eventbrite_id = urlid_to_eventid.get(url_id) if url_id else None
        if eventbrite_id:
            price = _fetch_eventbrite_price(eventbrite_id)
        if price is None:
            # Fallback: parse from block text ($125, $150, 125 USD, or Free)
            price_text = "\n".join(filter(None, [title, description, text]))
            block_html = str(block) if block else ""
            price = _extract_price(price_text, block_html)
        # URL-based fallback: free-photo-walk in path indicates free event
        if price is None and "/free-photo-walk" in (event_url or "").lower():
            price = 0.0

        event_data = {
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
        }
        if price is not None:
            event_data['price'] = price
            if eventbrite_id:
                price_str = "Free" if price == 0 else f"${price:.2f}"
                logger.info(f"   💰 Price from Eventbrite: {price_str} for '{title}'")
        elif eventbrite_id:
            logger.debug(f"   ⚠️ Eventbrite ID {eventbrite_id} found but no price returned for '{title}'")
        events.append(event_data)

    if skipped_past > 0:
        logger.info(f"Skipped {skipped_past} past event(s)")
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
