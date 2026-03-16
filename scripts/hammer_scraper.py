#!/usr/bin/env python3
"""
Hammer Museum (UCLA) source scraper.
Scrapes programs and events from https://hammer.ucla.edu/programs-events
"""

import logging
import re
from datetime import date, datetime, time
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HAMMER_BASE_URL = "https://hammer.ucla.edu"
HAMMER_PROGRAMS_URL = "https://hammer.ucla.edu/programs-events"
VENUE_NAME = "Hammer Museum"

# Map Hammer category labels to repo canonical event_type
# Canonical: tour, exhibition, festival, photowalk, film, workshop, talk, music, improv, event
CATEGORY_TO_EVENT_TYPE = {
    "screenings": "film",
    "tours & talks": "talk",
    "tours and talks": "talk",
    "conversations": "talk",
    "lectures": "talk",
    "readings": "talk",
    "music & performance": "music",
    "music and performance": "music",
    "hammer forum": "talk",
    "special programs": "event",
    "kids": "event",
    "members": "event",
    "public engagement": "event",
    "ucla film & tv archive": "film",
}


def _get_session():
    """Create a session for fetching (cloudscraper preferred)."""
    try:
        from scripts.scraper_utils import create_cloudscraper_session
        session = create_cloudscraper_session(base_url=HAMMER_BASE_URL)
        if session:
            return session
    except Exception as e:
        logger.debug(f"Cloudscraper not available: {e}")
    import requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    session.verify = False
    return session


def _parse_occurrence_date(date_text: str, url: str) -> Optional[tuple]:
    """
    Parse date/time from occurrence text like 'Wed Mar 1812:30 PM' or 'Wed Mar 18 12:30 PM'.
    Extracts year from URL path if present (/programs-events/2026/...).

    Returns (date_obj, time_obj) or (date_obj, None) if no time, or None if unparseable.
    """
    if not date_text or not isinstance(date_text, str):
        return None

    # Normalize: add space between day and hour if missing (e.g. "Mar 1812" -> "Mar 18 12")
    date_text = re.sub(r"(\d{1,2})(\d{1,2}:\d{2})", r"\1 \2", date_text.strip())

    # Extract year from URL: /programs-events/2026/... or /programs-events/2014/05/...
    year = None
    url_year = None
    if url:
        match = re.search(r"/programs-events/(\d{4})/", url)
        if match:
            url_year = int(match.group(1))
            year = url_year

    if year is None:
        year = date.today().year

    # Pattern: "Wed Mar 18 12:30 PM" or "Fri Mar 20 7:30 PM"
    match = re.search(
        r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+"
        r"(\d{1,2})\s+"
        r"(\d{1,2}):(\d{2})\s*(AM|PM)?",
        date_text,
        re.I,
    )
    if not match:
        # Try date only (no time)
        match = re.search(
            r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+"
            r"(\d{1,2})",
            date_text,
            re.I,
        )
        if match:
            month_str, day = match.group(1), int(match.group(2))
            month_map = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            }
            month = month_map.get(month_str[:3].lower())
            if month:
                try:
                    # Override stale URL year for recurring events: if URL year is past
                    # but (month, day) this year would be today or future, use current year
                    today = date.today()
                    if url_year is not None and url_year < today.year:
                        try:
                            d_curr = date(today.year, month, day)
                            if d_curr >= today:
                                year = today.year
                                logger.debug("URL year %s overridden to %s for recurring event (date-only)", url_year, year)
                        except ValueError:
                            pass
                    d = date(year, month, day)
                    return (d, None)
                except ValueError:
                    pass
        return None

    month_str, day = match.group(1), int(match.group(2))
    hour, minute = int(match.group(3)), int(match.group(4))
    am_pm = (match.group(5) or "").upper()

    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    month = month_map.get(month_str[:3].lower())
    if not month:
        return None

    # Override stale URL year for recurring events: if URL year is past but
    # (month, day) this year would be today or future, use current year
    today = date.today()
    if url_year is not None and url_year < today.year:
        try:
            d_curr = date(today.year, month, day)
            if d_curr >= today:
                year = today.year
                logger.debug("URL year %s overridden to %s for recurring event", url_year, year)
        except ValueError:
            pass

    try:
        d = date(year, month, day)
    except ValueError:
        return None

    if am_pm == "PM" and hour != 12:
        hour += 12
    elif am_pm == "AM" and hour == 12:
        hour = 0
    try:
        t = time(hour, minute)
    except ValueError:
        t = None

    return (d, t)


def _classify_event_type(category: str, title: str) -> str:
    """Map category and title to repo event_type."""
    if category:
        cat_lower = category.strip().lower()
        if cat_lower in CATEGORY_TO_EVENT_TYPE:
            return CATEGORY_TO_EVENT_TYPE[cat_lower]
    title_lower = (title or "").lower()
    if "screening" in title_lower or "film" in title_lower or "family flicks" in title_lower:
        return "film"
    if "talk" in title_lower or "lecture" in title_lower:
        return "talk"
    if "workshop" in title_lower or "art lab" in title_lower:
        return "workshop"
    if "performance" in title_lower or "concert" in title_lower:
        return "music"
    return "event"


def _fetch_html(url: str) -> Optional[str]:
    """Fetch page HTML."""
    try:
        session = _get_session()
        resp = session.get(url, timeout=25, verify=False)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def scrape_hammer_events() -> List[Dict]:
    """
    Scrape events from Hammer Museum programs-events page.
    Returns normalized event dicts (current/future only).
    """
    events = []
    html = _fetch_html(HAMMER_PROGRAMS_URL)
    if not html:
        return events

    soup = BeautifulSoup(html, "html.parser")
    today = date.today()

    # Find all occurrence blocks (each has date, parent link, title, etc.)
    occurrences = soup.find_all(class_="result-item__occurrence")
    seen_urls = set()

    for occ in occurrences:
        link = occ.find_parent("a")
        if not link:
            continue

        href = link.get("href", "")
        if not href or "/programs-events/" not in href:
            continue

        event_url = urljoin(HAMMER_BASE_URL, href)
        if event_url in seen_urls:
            continue
        seen_urls.add(event_url)

        # Title
        title_el = link.find(class_="result-item__title")
        title = title_el.get_text(strip=True) if title_el else None
        if not title or len(title) < 3:
            continue

        # Description
        excerpt_el = link.find(class_="result-item__excerpt")
        description = excerpt_el.get_text(strip=True) if excerpt_el else ""

        # Category
        category_el = link.find(class_="category--last") or link.find(class_="program__category")
        category = category_el.get_text(strip=True) if category_el else ""

        # Date/time
        parsed = _parse_occurrence_date(occ.get_text(strip=True), href)
        if not parsed:
            continue
        start_date, start_time = parsed

        # Skip past events
        if start_date < today:
            continue

        # Image
        image_url = None
        img = link.find("img", src=True)
        if img:
            img_src = img.get("src", "")
            if img_src and not img_src.startswith("data:"):
                image_url = urljoin(HAMMER_BASE_URL, img_src)

        event_type = _classify_event_type(category, title)

        event = {
            "title": title,
            "description": description,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": start_date.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": None,
            "url": event_url,
            "image_url": image_url,
            "event_type": event_type,
            "venue_name": VENUE_NAME,
            "start_location": VENUE_NAME,
            "end_location": None,
            "source": "website",
            "source_url": HAMMER_PROGRAMS_URL,
            "organizer": VENUE_NAME,
        }
        events.append(event)

    logger.info(f"Hammer Museum: scraped {len(events)} current/future events")
    return events


def scrape_all_hammer_events() -> List[Dict]:
    """Entry point for source scraper. Returns events with venue_id/city_id set by caller."""
    return scrape_hammer_events()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = scrape_all_hammer_events()
    print(f"Found {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title']} | {e['start_date']} {e.get('start_time', '')} | {e['event_type']}")
