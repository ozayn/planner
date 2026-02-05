#!/usr/bin/env python3
"""
Wharf DC Scraper - Uses generic scraper with event URLs from venue additional_info.

Gets the events path from the venue's additional_info.event_paths and scrapes
that URL directly (no discovery). Includes Wharf-specific extraction for the
page structure (h3 titles, date/time/location blocks, Learn More links).
"""

import json
import logging
import re
import sys
import time
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urljoin

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from bs4 import BeautifulSoup

from scripts.generic_venue_scraper import GenericVenueScraper
from scripts.event_database_handler import create_events_in_database

logger = logging.getLogger(__name__)


def _parse_wharf_date(date_str: str):
    """Parse date like 'Feb. 11, 2026' or 'Dec. 21, 2025'."""
    if not date_str:
        return None
    date_str = re.sub(r'calendar icon|clock icon|map marker icon', '', date_str, flags=re.I).strip()
    for fmt in ['%b. %d, %Y', '%b %d, %Y', '%B %d, %Y']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_single_time(s: str) -> str | None:
    """Parse a single time like '7pm' or '7:30pm' to HH:MM."""
    if not s:
        return None
    s = s.strip()
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', s, re.I)
    if match:
        hour, minute, ampm = int(match.group(1)), int(match.group(2) or 0), match.group(3).upper()
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        return f'{hour:02d}:{minute:02d}'
    return None


def _parse_wharf_time_range(time_str: str) -> tuple[str | None, str | None]:
    """Parse time range like '7pm–10pm' or '12pm–4pm' to (start_time, end_time)."""
    if not time_str:
        return None, None
    time_str = re.sub(r'[\u00a0\u2013\u2014–\-]', ' ', time_str).strip()
    # Match both times: "7pm 10pm" or "12pm 4pm"
    matches = list(re.finditer(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', time_str, re.I))
    if len(matches) >= 2:
        start = _parse_single_time(matches[0].group(0))
        end = _parse_single_time(matches[1].group(0))
        return start, end
    if len(matches) == 1:
        return _parse_single_time(matches[0].group(0)), None
    return None, None


def _extract_wharf_events(html: str, base_url: str, venue_name: str) -> list:
    """
    Wharf-specific extraction: page has h3 event titles, date/time/location blocks, Learn More links.
    """
    events = []
    soup = BeautifulSoup(html, 'html.parser')
    from urllib.parse import urljoin

    # Find event blocks - typically each event is in a section/card with h3 heading
    for h3 in soup.find_all(['h3', 'h4']):
        title = (h3.get_text(strip=True) or '').replace('&amp;', '&')
        if not title or len(title) < 4:
            continue
        # Skip non-event headings
        if any(skip in title.lower() for skip in ['upcoming events', 'events at', 'visit the', 'the anthem', 'browse']):
            continue

        # Get container (parent section/div)
        container = h3.find_parent(['section', 'div', 'article']) or h3.parent
        if not container:
            continue

        text = container.get_text(separator=' ', strip=True)
        # Find Learn More / More Info / Explore link
        link = None
        for a in container.find_all('a', href=True):
            href = a.get('href', '')
            if 'wharfdc.com' in href or href.startswith('/'):
                link_text = (a.get_text(strip=True) or '').lower()
                if 'learn more' in link_text or 'more info' in link_text or 'explore' in link_text:
                    link = urljoin(base_url, href)
                    break
        if not link:
            for a in container.find_all('a', href=True):
                href = a.get('href', '')
                if '/upcoming-events/' in href or '/mardigras' in href or '/ireland' in href or '/bloomaroo' in href or '/chihuahuas' in href or '/fish-market' in href:
                    link = urljoin(base_url, href)
                    break

        # Parse date: "Feb. 11, 2026" or "Dec. 21, 2025"
        date_match = re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}', text, re.I)
        event_date = _parse_wharf_date(date_match.group(0)) if date_match else None

        # Parse time: "7pm – 10pm" or "12pm–4pm" (handles en-dash, hyphen, em-dash)
        time_match = re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[–\-—]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)', text, re.I)
        start_time, end_time = _parse_wharf_time_range(time_match.group(0)) if time_match else (None, None)

        # Location/meeting point - after "map marker icon", e.g. "District Pier" or "The Wharf Ice Rink"
        loc_match = re.search(r'map\s*marker\s*icon\s*\[?([^\]\n]+?(?:Ice Rink|Pier|Square|Stage|Market))\]?', text, re.I)
        location = loc_match.group(1).strip() if loc_match else None

        # Description - text between date/time and the link, first sentence or two
        desc_parts = []
        for node in container.find_all(string=True):
            s = node.strip()
            if s and len(s) > 30 and 'Learn More' not in s and 'More Info' not in s:
                if not re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', s):
                    desc_parts.append(s[:300])
                    break
        description = ' '.join(desc_parts)[:400] if desc_parts else None

        if not event_date:
            continue  # Need at least a date

        # Extract image from listing page - Wharf uses background-image on divs (no img tags)
        image_url = None
        card = h3
        for _ in range(10):
            card = card.parent
            if not card:
                break
            for el in card.find_all(style=True):
                style = el.get('style', '')
                if 'background-image' in style:
                    m = re.search(r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)', style)
                    if m:
                        img_src = m.group(1).strip()
                        if img_src and 'logo' not in img_src.lower() and 'icon' not in img_src.lower():
                            if not img_src.startswith('http'):
                                img_src = urljoin(base_url, img_src)
                            image_url = img_src
                            break
            if image_url:
                break

        events.append({
            'title': title,
            'start_date': event_date,
            'end_date': event_date,
            'start_time': start_time,
            'end_time': end_time,
            'url': link or base_url,
            'description': description,
            'event_type': 'festival',  # Wharf events are typically festivals/community events
            'venue_name': venue_name,
            'start_location': location,
            'image_url': image_url,
        })

    return events


def _extract_image_from_page(html: str, page_url: str) -> str | None:
    """
    Extract event image URL from a Wharf DC event detail page.
    Tries og:image first (most reliable), then hero/feature/event img elements.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Strategy 1: og:image meta tag (most reliable on event pages)
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        img_url = og_image.get('content').strip()
        if img_url and not img_url.startswith('data:'):
            if not img_url.startswith('http'):
                img_url = urljoin(page_url, img_url)
            return img_url

    # Strategy 2: img with hero/feature/event classes
    for cls in ['hero', 'feature', 'event-image', 'main', 'banner']:
        img = soup.find('img', class_=re.compile(cls, re.I))
        if img:
            img_src = img.get('src') or img.get('data-src') or img.get('data-srcset', '').split(',')[0].strip().split()[0]
            if img_src and 'placeholder' not in img_src.lower():
                if not img_src.startswith('http'):
                    img_src = urljoin(page_url, img_src)
                return img_src

    # Strategy 3: First substantial image in main content (skip icons/logos)
    main = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|detail', re.I))
    if main:
        for img in main.find_all('img'):
            img_src = img.get('src') or img.get('data-src')
            if img_src and any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                skip = ['icon', 'logo', 'avatar', 'social', 'facebook', 'twitter', 'share']
                if not any(s in img_src.lower() for s in skip):
                    if not img_src.startswith('http'):
                        img_src = urljoin(page_url, img_src)
                    return img_src

    return None


def _enrich_events_with_images(events: list, session: requests.Session) -> None:
    """
    Fetch each event's detail page and add image_url to events that don't have one.
    Modifies events in place. Adds a small delay between requests to be polite.
    """
    listing_url = 'https://www.wharfdc.com/upcoming-events/'
    for ev in events:
        if ev.get('image_url'):
            continue
        url = ev.get('url')
        if not url or url == listing_url:
            continue
        # Only fetch wharfdc.com event detail pages (not external links)
        if 'wharfdc.com' not in url:
            continue
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            img = _extract_image_from_page(resp.text, url)
            if img:
                ev['image_url'] = img
                logger.debug(f"   🖼️ Image for {ev.get('title', '')[:40]}: {img[:60]}...")
            time.sleep(0.3)  # Be polite
        except Exception as e:
            logger.debug(f"   ⚠️ Could not fetch image from {url}: {e}")


def get_event_urls_from_venue(venue) -> list:
    """Extract event page URLs from venue's additional_info.event_paths."""
    urls = []
    if not venue or not venue.additional_info:
        return urls
    try:
        info = json.loads(venue.additional_info) if isinstance(venue.additional_info, str) else venue.additional_info
        paths = info.get('event_paths', {})
        if not paths:
            return urls
        for key, val in paths.items():
            if val:
                if val.startswith('http://') or val.startswith('https://'):
                    urls.append(val)
                else:
                    from urllib.parse import urlparse
                    base = venue.website_url or ''
                    if base:
                        parsed = urlparse(base)
                        base_domain = f"{parsed.scheme}://{parsed.netloc}"
                        path = val if val.startswith('/') else '/' + val
                        urls.append(base_domain.rstrip('/') + path)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return urls


def scrape_wharf_dc_events():
    """
    Scrape events from The Wharf DC using venue's event paths from additional_info.
    Tries Wharf-specific extraction first, then falls back to generic scraper.
    Returns list of event dicts.
    """
    from app import app, db, Venue, City

    with app.app_context():
        dc = City.query.filter(db.func.lower(City.name).like('%washington%')).first()
        if not dc:
            logger.warning("Wharf DC scraper: Washington DC city not found in database")
            return []

        venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%wharf dc%'),
            Venue.city_id == dc.id
        ).first()

        if not venue:
            logger.warning("Wharf DC scraper: Wharf DC venue not found in database (run load-all-data or add venue)")
            return []

        event_urls = get_event_urls_from_venue(venue)
        # Fallback: production DB may not have additional_info with event_paths - use known URL
        if not event_urls:
            event_urls = ['https://www.wharfdc.com/upcoming-events/']
            logger.debug("Wharf DC: using fallback events URL (venue additional_info missing or empty)")

        events = []
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

        for url in event_urls:
            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
                wharf_events = _extract_wharf_events(resp.text, url, venue.name)
                if wharf_events:
                    events.extend(wharf_events)
                    break  # Got events from first URL
            except Exception as e:
                logging.getLogger(__name__).warning(f"Wharf extraction failed for {url}: {e}")

        # Fallback to generic scraper if Wharf-specific extraction found nothing
        if not events:
            scraper = GenericVenueScraper()
            events = scraper.scrape_venue_events(
                venue_url=venue.website_url or event_urls[0],
                venue_name=venue.name,
                event_type=None,
                time_range='next_month',
                event_urls=event_urls
            )

        # Enrich events with images from their detail pages (for any without image_url)
        if events:
            _enrich_events_with_images(events, session)

        return events


def create_events_in_database_wrapper(events):
    """Save Wharf DC events to database."""
    from app import app, db, Venue, City, Event

    with app.app_context():
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%wharf dc%')
        ).first()
        if not venue:
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
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)

    logger.info("🏛️ Wharf DC scraper: scraping using venue additional_info event paths...")
    events = scrape_wharf_dc_events()
    logger.info(f"   Found {len(events)} events")

    if events:
        created, updated, skipped = create_events_in_database_wrapper(events)
        logger.info(f"   Created: {created}, Updated: {updated}, Skipped: {skipped}")
    else:
        logger.info("   No events to save.")

    return events


if __name__ == '__main__':
    main()
