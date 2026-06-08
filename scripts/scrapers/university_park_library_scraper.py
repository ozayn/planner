#!/usr/bin/env python3
"""
University Park Library (Irvine) scraper.
Scrapes events from City of Irvine library program guide PDF.
URL format: https://legacy.cityofirvine.org/civica/filebank/blobdload.asp?BlobID=...
"""

import io
import logging
import re
from datetime import date, datetime
from typing import Dict, List, Optional

import requests
from pypdf import PdfReader

logger = logging.getLogger(__name__)

VENUE_NAME = "University Park Library"
SOURCE_URL = "https://legacy.cityofirvine.org/civica/filebank/blobdload.asp?BlobID=36797"
REQUEST_TIMEOUT = 30

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_time_range(text: str) -> Optional[tuple]:
    """Parse '10:30 a.m./11:30 a.m.' or '4:30 p.m.' -> (start_time, end_time) as HH:MM."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip().lower()
    # "10:30 a.m./11:30 a.m." or "4:30 p.m." or "10 a.m."
    parts = re.split(r"\s*/\s*", text)
    times = []
    for part in parts:
        m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", part, re.I)
        if m:
            h, min_val, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3).replace(".", "")
            if "p" in ampm and h != 12:
                h += 12
            elif "a" in ampm and h == 12:
                h = 0
            times.append(f"{h:02d}:{min_val:02d}")
    if not times:
        return None
    return (times[0], times[1] if len(times) > 1 else None)


def _infer_event_type(title: str) -> str:
    """Map title to canonical event_type."""
    t = title.lower()
    if "lecture" in t:
        return "talk"
    if "book club" in t or "conversation" in t:
        return "talk"
    if "workshop" in t or "craft" in t or "ciy:" in t or "brick builder" in t or "board game" in t:
        return "workshop"
    if "film" in t or "movie" in t or "screening" in t:
        return "film"
    if "concert" in t or "music" in t:
        return "music"
    return "event"


def scrape_university_park_library_events(pdf_url: str = SOURCE_URL) -> List[Dict]:
    """
    Scrape events from University Park Library program guide PDF.
    Returns normalized event dicts (current/future only).
    """
    events = []
    today = date.today()

    try:
        resp = requests.get(
            pdf_url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
        resp.raise_for_status()
        if not resp.content or len(resp.content) < 100:
            logger.warning("PDF response empty or too small")
            return events

        reader = PdfReader(io.BytesIO(resp.content))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

    except Exception as e:
        logger.error(f"Failed to fetch/parse PDF: {e}")
        return events

    # Extract month/year: "MAR2026" or "MAR 2026"
    month_year = re.search(r"([A-Za-z]{3})\s*(\d{4})", text)
    if not month_year:
        logger.warning("Could not find month/year in PDF")
        return events
    month_str, year_str = month_year.group(1), month_year.group(2)
    month = MONTH_MAP.get(month_str[:3].lower())
    year = int(year_str)
    if not month:
        return events

    # Find all "time + title" blocks; associate with preceding day number
    time_pat = re.compile(
        r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)(?:\s*/\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?))?",
        re.I,
    )
    day_pat = re.compile(r"\b([1-9]|[12]\d|3[01])\b")
    seen = set()

    for time_m in time_pat.finditer(text):
        full_time = time_m.group(0)
        parsed = _parse_time_range(full_time)
        if not parsed:
            continue
        start_time, end_time = parsed
        after_time = text[time_m.end() : time_m.end() + 120].strip()
        # Title: take until next time, day number, or separator
        title = re.split(r"\s*—\s*|\s+\d{1,2}\s+|\s*\n\s*\d{1,2}\s+", after_time)[0]
        title = re.sub(r"\s+", " ", title).strip()
        title = re.sub(r"\s*\(Ages[^)]*\)\s*$", "", title).strip()
        title = re.sub(r"\s*\(Grades[^)]*\)\s*$", "", title).strip()
        title = re.sub(r"\s*\(All Ages\)\s*$", "", title).strip()
        if not title or len(title) < 3:
            continue
        # Find preceding day number (before this time match)
        before = text[: time_m.start()]
        day_matches = list(day_pat.finditer(before))
        if not day_matches:
            continue
        day_num = int(day_matches[-1].group(1))
        try:
            start_date = date(year, month, day_num)
        except ValueError:
            continue
        if start_date < today:
            continue
        key = (start_date.isoformat(), start_time or "", title[:50])
        if key in seen:
            continue
        seen.add(key)
        event_type = _infer_event_type(title)
        events.append({
            "title": title,
            "description": "",
            "start_date": start_date.isoformat(),
            "end_date": start_date.isoformat(),
            "start_time": start_time,
            "end_time": end_time,
            "url": "https://cityofirvine.org/libraries",
            "image_url": None,
            "event_type": event_type,
            "venue_name": VENUE_NAME,
            "start_location": VENUE_NAME,
            "end_location": None,
            "source": "website",
            "source_url": pdf_url,
            "organizer": VENUE_NAME,
        })

    logger.info(f"University Park Library: scraped {len(events)} events from PDF")
    return events


def scrape_all_university_park_library_events() -> List[Dict]:
    """Entry point for source/cron scraper."""
    return scrape_university_park_library_events()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    evs = scrape_all_university_park_library_events()
    print(f"Found {len(evs)} events")
    for e in evs[:8]:
        print(f"  - {e['start_date']} {e.get('start_time')} | {e['event_type']} | {e['title'][:50]}")
