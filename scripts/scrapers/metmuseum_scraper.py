#!/usr/bin/env python3
"""
The Metropolitan Museum of Art — free guided tours from the public schedule page.

Source: https://www.metmuseum.org/es/tours (SSR HTML; avoids Vercel/429 issues common on
other Met program URLs). Fetched with gzip/deflate only (no brotli) so responses decode
reliably without optional brotli dependency.

English-only: titles with explicit non-English language labels or non-Latin lead
characters are skipped.
"""

from __future__ import annotations

import logging
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urljoin, urlparse

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import requests
from bs4 import BeautifulSoup

from scripts.event_database_handler import create_events_in_database
from scripts.scraper_db_lookup import resolve_city_by_name, resolve_venue_in_city

logger = logging.getLogger(__name__)

MET_WEBSITE = "https://www.metmuseum.org"
# Public free-tours schedule (Spanish locale page; lists all languages; we filter to English)
MET_FREE_TOURS_URL = "https://www.metmuseum.org/es/tours"
MET_TOURS_DEFAULT = MET_FREE_TOURS_URL

_MONTH_MAP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

# Substrings in title (lowercase) → skip (non-English tour labels)
_NON_ENGLISH_TITLE_MARKERS = (
    " in russian",
    " in arabic",
    " in japanese",
    " in french",
    " in portuguese",
    " in spanish",
    " in korean",
    " in chinese",
    " in german",
    " in italian",
    " in hindi",
    " in hebrew",
    " in turkish",
    " in polish",
    " in dutch",
    "mandarin",
    "cantonese",
    " in vietnamese",
    " in ukrainian",
)

_CANONICAL_TYPES = frozenset(
    {"tour", "exhibition", "festival", "photowalk", "film", "workshop", "talk", "music", "improv", "event"}
)

_TYPE_ALIASES = {
    "screening": "film",
    "lecture": "talk",
    "lectures": "talk",
    "gallery talk": "talk",
    "artist talk": "talk",
    "performance": "event",
    "museum_event": "event",
    "class": "workshop",
    "classes": "workshop",
    "demo": "workshop",
}


def _normalize_met_event_type(event_data: dict) -> None:
    """Map scraper output to canonical event_type; infer from title/description when needed."""
    raw = (event_data.get("event_type") or "event").strip().lower()
    if raw in _TYPE_ALIASES:
        raw = _TYPE_ALIASES[raw]
    if raw in _CANONICAL_TYPES:
        event_data["event_type"] = raw
        return
    blob = f"{event_data.get('title', '')} {event_data.get('description', '')}".lower()
    if "tour" in blob and raw not in _CANONICAL_TYPES:
        event_data["event_type"] = "tour"
    elif any(x in blob for x in ("film", "screening", "cinema")):
        event_data["event_type"] = "film"
    elif any(x in blob for x in ("workshop", "class", "studio")):
        event_data["event_type"] = "workshop"
    elif any(x in blob for x in ("talk", "lecture", "conversation", "symposium")):
        event_data["event_type"] = "talk"
    elif "exhibition" in blob or "gallery" in blob:
        event_data["event_type"] = "exhibition"
    else:
        event_data["event_type"] = "event" if raw not in _CANONICAL_TYPES else raw


def _is_english_met_tour_title(title: str) -> bool:
    """True if this tour row should be kept as English-language."""
    if not title or not title.strip():
        return False
    t = title.strip()
    low = t.lower()

    for marker in _NON_ENGLISH_TITLE_MARKERS:
        if marker in low:
            return False

    m = re.search(r"\(museum highlights in ([^)]+)\)", low)
    if m:
        inner = m.group(1).lower()
        if "english" not in inner:
            return False

    # Leading character: skip Cyrillic, Arabic, CJK blocks
    first = t[0]
    o = ord(first)
    if 0x0400 <= o <= 0x04FF:
        return False
    if 0x0600 <= o <= 0x06FF:
        return False
    if 0x3040 <= o <= 0x9FFF:
        return False
    if 0xAC00 <= o <= 0xD7AF:
        return False

    return True


def _parse_date_heading(heading: str) -> Optional[date]:
    """Parse 'Monday, March 30' into a date (year from rolling window)."""
    m = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})",
        heading,
        re.I,
    )
    if not m:
        return None
    mon = _MONTH_MAP.get(m.group(1).lower())
    if not mon:
        return None
    day = int(m.group(2))
    today = date.today()
    for year in (today.year, today.year + 1):
        try:
            d = date(year, mon, day)
        except ValueError:
            return None
        if d >= today - timedelta(days=1):
            return d
    return None


def _hhmm_from_12h(hour: int, minute: int, ampm: str) -> str:
    ap = ampm.strip().lower()
    h = hour
    if ap == "am":
        if h == 12:
            h = 0
    else:
        if h != 12:
            h += 12
    return f"{h:02d}:{minute:02d}"


def _first_time_hhmm_in_text(text: str) -> Optional[str]:
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(AM|PM)\b", text, re.I)
    if not m:
        return None
    return _hhmm_from_12h(int(m.group(1)), int(m.group(2)), m.group(3))


def _location_after_time(card) -> Optional[str]:
    """Line after the first 'H:MM AM/PM' in card text (usually 'The Met Fifth Avenue')."""
    lines = [ln.strip() for ln in card.get_text("\n", strip=True).split("\n") if ln.strip()]
    for i, ln in enumerate(lines):
        if re.search(r"\b\d{1,2}:\d{2}\s*(AM|PM)\b", ln, re.I):
            if i + 1 < len(lines):
                loc = lines[i + 1]
                if len(loc) < 200 and ("Met" in loc or "Cloisters" in loc):
                    return loc
            return None
    return None


def _description_from_card(card) -> str:
    desc = card.find("div", class_=re.compile(r"description"))
    if not desc:
        return ""
    parts = []
    for p in desc.find_all("p"):
        txt = p.get_text(" ", strip=True)
        if txt:
            parts.append(txt)
    return "\n\n".join(parts)


def _image_url_from_card(card, base: str) -> Optional[str]:
    img = card.find("img")
    if not img:
        return None
    src = (img.get("src") or "").strip()
    if not src:
        return None
    if src.startswith("/_next/image"):
        q = parse_qs(urlparse(src).query)
        u = q.get("url", [None])[0]
        if u:
            return unquote(u)
    if src.startswith("http"):
        return src
    return urljoin(base, src)


def _event_url_from_card(card) -> Optional[str]:
    h4 = card.find("h4")
    if not h4:
        return None
    a = h4.find("a", href=True)
    if a:
        return a["href"].strip()
    a2 = card.find("a", href=re.compile(r"engage\.metmuseum\.org"))
    if a2:
        return a2["href"].strip()
    return None


def _fetch_met_free_tours_html() -> Optional[str]:
    """GET schedule page; avoid brotli so body decodes without optional brotli package."""
    try:
        r = requests.get(
            MET_FREE_TOURS_URL,
            timeout=45,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        if r.status_code != 200:
            logger.warning("Met scraper: HTTP %s for %s", r.status_code, MET_FREE_TOURS_URL)
            return None
        return r.text
    except Exception as e:
        logger.warning("Met scraper: fetch failed %s: %s", MET_FREE_TOURS_URL, e)
        return None


def parse_met_free_tours_html(html: str) -> List[Dict[str, Any]]:
    """Parse Met /es/tours HTML into event dicts (caller filters English if needed)."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    if not main:
        return []

    events: List[Dict[str, Any]] = []
    for h3 in main.find_all("h3", class_=re.compile(r"date")):
        start_d = _parse_date_heading(h3.get_text(strip=True))
        if not start_d:
            continue
        block = h3.parent
        cw = block.find("div", class_=re.compile(r"cardWrapper"))
        if not cw:
            continue
        for card in cw.find_all("div", class_=re.compile(r"eventCard")):
            h4 = card.find("h4")
            title = h4.get_text(strip=True) if h4 else ""
            if not title:
                continue
            if not _is_english_met_tour_title(title):
                continue

            card_text = card.get_text(" ", strip=True)
            start_time = _first_time_hhmm_in_text(card_text)
            loc = _location_after_time(card)
            url = _event_url_from_card(card)
            desc = _description_from_card(card)
            img = _image_url_from_card(card, MET_WEBSITE)

            ev: Dict[str, Any] = {
                "title": title,
                "description": desc,
                "event_type": "tour",
                "start_date": start_d.isoformat(),
                "end_date": start_d.isoformat(),
                "venue_name": "The Metropolitan Museum of Art",
            }
            if start_time:
                ev["start_time"] = start_time
            if loc:
                ev["start_location"] = loc
            if url:
                ev["url"] = url
            if img:
                ev["image_url"] = img

            _normalize_met_event_type(ev)
            events.append(ev)

    return events


def scrape_metmuseum_events():
    """
    Scrape Met free guided tours from the public schedule page (English rows only).
    """
    from app import app, db, City, Venue

    with app.app_context():
        city = resolve_city_by_name(db, City, "New York", "New York")
        if not city:
            logger.warning(
                "Metropolitan Museum scraper: city not found — expected 'New York' (state 'New York' if stored)"
            )
            return []
        venue = resolve_venue_in_city(
            db,
            Venue,
            city.id,
            website_contains=["metmuseum.org"],
            name_contains=["metropolitan museum"],
        )
        if not venue:
            logger.warning(
                "Metropolitan Museum scraper: venue not found for city %r (id=%s) — metmuseum.org / Metropolitan Museum",
                city.name,
                city.id,
            )
            return []

        html = _fetch_met_free_tours_html()
        if not html:
            return []

        events = parse_met_free_tours_html(html)
        logger.info("Met scraper: %s English tour rows from %s", len(events), MET_FREE_TOURS_URL)
        return events


def create_events_in_database_wrapper(events):
    """Persist Met events; tag source as website."""

    from app import app, db, City, Venue, Event

    with app.app_context():
        city = resolve_city_by_name(db, City, "New York", "New York")
        if not city:
            return 0, 0, 0
        venue = resolve_venue_in_city(
            db,
            Venue,
            city.id,
            website_contains=["metmuseum.org"],
            name_contains=["metropolitan museum"],
        )
        if not venue:
            return 0, 0, 0

        def processor(e):
            e["source"] = "website"
            _normalize_met_event_type(e)

        created, updated, skipped = create_events_in_database(
            events=events,
            venue_id=venue.id,
            city_id=venue.city_id,
            venue_name=venue.name,
            db=db,
            Event=Event,
            Venue=Venue,
            source_url=MET_FREE_TOURS_URL,
            custom_event_processor=processor,
        )
        return created, updated, skipped


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("🏛️ The Met: scraping free tours (English)…")
    events = scrape_metmuseum_events()
    logger.info("   Found %s events", len(events))
    if events:
        c, u, s = create_events_in_database_wrapper(events)
        logger.info("   Created: %s, Updated: %s, Skipped: %s", c, u, s)
    return events


if __name__ == "__main__":
    main()
