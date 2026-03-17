#!/usr/bin/env python3
"""
de Young Museum (FAMSF) scraper.
Scrapes exhibitions from https://www.famsf.org/exhibitions?where=de-young
and calendar/program events (tours, talks, workshops, etc.) from
https://www.famsf.org/calendar?where=de-young
"""

import logging
import re
import time
from datetime import date, datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEYOUNG_EXHIBITIONS_URL = "https://www.famsf.org/exhibitions?where=de-young"
DEYOUNG_CALENDAR_URL = "https://www.famsf.org/calendar?where=de-young"
DEYOUNG_BASE_URL = "https://www.famsf.org"
VENUE_NAME = "de Young Museum"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2


def _get_session():
    """Create a session for fetching (uses normal SSL verification for famsf.org)."""
    try:
        from scripts.scraper_utils import create_cloudscraper_session
        session = create_cloudscraper_session(base_url=DEYOUNG_BASE_URL, verify_ssl=True)
        if session:
            return session
    except Exception as e:
        logger.debug(f"Cloudscraper not available: {e}")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def _extract_image_url(container, base_url: str) -> Optional[str]:
    """
    Extract first valid image URL from a container (listing-page card).
    Checks: img src, data-src, srcset; picture/source srcset.
    Skips placeholders (data: URLs, 1x1 gifs).
    """
    if not container:
        return None

    def is_valid(url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if url.startswith("data:"):
            return False
        return url.startswith(("http://", "https://"))

    # img: src, data-src, srcset
    for img in container.find_all("img"):
        for attr in ("src", "data-src"):
            val = img.get(attr)
            if is_valid(val):
                return urljoin(base_url, val)
        srcset = img.get("srcset")
        if srcset:
            part = srcset.split(",")[0].strip().split()[0]
            if is_valid(part):
                return urljoin(base_url, part)

    # picture/source
    picture = container.find("picture")
    if picture:
        for src in picture.find_all("source", srcset=True):
            srcset = src.get("srcset", "")
            if srcset:
                part = srcset.split(",")[0].strip().split()[0]
                if is_valid(part):
                    return urljoin(base_url, part)
    return None


def _parse_calendar_time(text: str) -> Optional[tuple]:
    """
    Parse time string like "6–7:30 pm", "1 pm", "9:30 am–4 pm", "6 pm – midnight".
    Returns (start_time, end_time) as "HH:MM" or (start_time, None) if single time.
    """
    if not text or not isinstance(text, str):
        return None
    text = text.strip().lower()
    suffix = "pm" if "pm" in text else "am"

    def to_minutes(match) -> int:
        h = int(match.group(1))
        m_val = int(match.group(2) or 0)
        ampm = (match.group(3) or suffix).lower()
        if ampm == "pm" and h != 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        return h * 60 + m_val

    if "midnight" in text:
        text = text.replace("midnight", "12:00 am")

    time_pat = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)
    matches = list(time_pat.finditer(text))
    if not matches:
        return None
    start_m = to_minutes(matches[0])
    start_time = f"{start_m // 60:02d}:{start_m % 60:02d}"
    end_time = None
    if len(matches) >= 2:
        end_m = to_minutes(matches[1])
        if end_m == 0:
            end_time = "23:59"
        else:
            end_time = f"{end_m // 60:02d}:{end_m % 60:02d}"
    return (start_time, end_time)


def _infer_event_type(card_text: str, title: str) -> str:
    """Map calendar card text to canonical event_type."""
    combined = (card_text + " " + title).lower()
    if "gallery conversation" in combined or "tour" in combined:
        return "tour"
    if "reception" in combined or "gala" in combined or "party" in combined:
        return "event"
    if "lecture" in combined or "talk" in combined:
        return "talk"
    if "workshop" in combined:
        return "workshop"
    if "concert" in combined or "music" in combined:
        return "music"
    if "film" in combined or "screening" in combined:
        return "film"
    return "event"


def _parse_date_range(text: str, today: date) -> Optional[tuple]:
    """
    Parse date range from text like:
    - "Through May 3, 2026" -> (today, 2026-05-03)
    - "Mar 21 – Jul 26, 2026" -> (2026-03-21, 2026-07-26)
    Returns (start_date, end_date) or None if unparseable.
    """
    if not text or not isinstance(text, str):
        return None
    text = text.strip()

    # "Through May 3, 2026"
    through = re.search(r"Through\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", text, re.I)
    if through:
        month_str, day, year = through.group(1), int(through.group(2)), int(through.group(3))
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month = month_map.get(month_str[:3].lower())
        if month:
            try:
                end_d = date(year, month, day)
                # Use today as start if exhibition is current
                start_d = today if today <= end_d else end_d
                return (start_d, end_d)
            except ValueError:
                pass

    # "Mar 21 – Jul 26, 2026" or "Mar 21 - Jul 26, 2026"
    range_match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2})\s*[–\-]\s*([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})",
        text,
        re.I,
    )
    if range_match:
        m1, d1, m2, d2, year = (
            range_match.group(1), int(range_match.group(2)),
            range_match.group(3), int(range_match.group(4)),
            int(range_match.group(5)),
        )
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        mo1 = month_map.get(m1[:3].lower())
        mo2 = month_map.get(m2[:3].lower())
        if mo1 and mo2:
            try:
                start_d = date(year, mo1, d1)
                end_d = date(year, mo2, d2)
                return (start_d, end_d)
            except ValueError:
                pass

    return None


def scrape_deyoung_events() -> List[Dict]:
    """
    Scrape exhibitions from de Young Museum (FAMSF) exhibitions page.
    Returns normalized event dicts (current/future only, de Young venue only).
    """
    events = []
    session = _get_session()
    html = None
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                wait = RETRY_DELAY * (2 ** (attempt - 1))
                logger.info(f"de Young: retry {attempt + 1}/{MAX_RETRIES} in {wait}s (last: {last_error})")
                time.sleep(wait)
            resp = session.get(DEYOUNG_EXHIBITIONS_URL, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            html = resp.text
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Failed to fetch de Young exhibitions after {MAX_RETRIES} attempts: {e}")
                return events
        except Exception as e:
            logger.error(f"Failed to fetch de Young exhibitions: {e}")
            return events

    if not html:
        return events

    soup = BeautifulSoup(html, "html.parser")
    today = date.today()

    links = soup.find_all(
        "a",
        href=lambda h: h and "/exhibitions/" in h and "where=" not in h and "past" not in h,
    )
    seen_urls = set()

    for a in links:
        href = a.get("href", "")
        if not href:
            continue
        event_url = urljoin(DEYOUNG_BASE_URL, href)
        if event_url in seen_urls:
            continue
        seen_urls.add(event_url)

        title = a.get_text(strip=True)
        if not title or len(title) < 3:
            continue

        parent = a.find_parent(["li", "article", "div"])
        if not parent:
            continue
        parent_text = parent.get_text()

        # Page is filtered by where=de-young so results are de Young exhibitions
        parsed = _parse_date_range(parent_text, today)
        if not parsed:
            continue
        start_date, end_date = parsed

        # Skip past exhibitions
        if end_date < today:
            continue

        # Image from listing-page card (img in same li/article as link; parent div may not contain img)
        card = a.find_parent(["li", "article"]) or parent
        image_url = _extract_image_url(card, DEYOUNG_BASE_URL)

        event = {
            "title": title,
            "description": "",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "start_time": None,
            "end_time": None,
            "url": event_url,
            "image_url": image_url,
            "event_type": "exhibition",
            "venue_name": VENUE_NAME,
            "start_location": VENUE_NAME,
            "end_location": None,
            "source": "website",
            "source_url": DEYOUNG_EXHIBITIONS_URL,
            "organizer": VENUE_NAME,
        }
        events.append(event)

    logger.info(f"de Young Museum: scraped {len(events)} current/future exhibitions")
    return events


def _scrape_calendar_events(session, today: date) -> List[Dict]:
    """
    Scrape tours, talks, lectures, workshops, and other programs from the de Young calendar.
    Returns only de Young venue events with parseable dates (skips recurring like "Select Saturdays").
    """
    events = []
    try:
        resp = session.get(DEYOUNG_CALENDAR_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch de Young calendar: {e}")
        return events

    soup = BeautifulSoup(html, "html.parser")
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "ticketing.famsf" in href:
            continue
        if "/events/" not in href:
            continue
        event_url = urljoin(DEYOUNG_BASE_URL, href)
        if event_url in seen_urls:
            continue
        seen_urls.add(event_url)

        title = a.get_text(strip=True)
        if not title or len(title) < 5 or "Donate" in title:
            continue

        card = a.find_parent("li")
        if not card:
            continue

        card_text = card.get_text()
        if "Legion" in card_text and "de Young" not in card_text:
            continue
        if "de Young" not in card_text:
            continue

        time_el = card.find("time")
        if not time_el or not time_el.get("datetime"):
            continue
        try:
            start_date = datetime.strptime(time_el["datetime"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        if start_date < today:
            continue

        start_time, end_time = None, None
        if time_el.parent:
            parts = list(time_el.parent.stripped_strings)
            if len(parts) >= 3:
                parsed = _parse_calendar_time(parts[2])
                if parsed:
                    start_time, end_time = parsed

        event_type = _infer_event_type(card_text, title)
        image_url = _extract_image_url(card, DEYOUNG_BASE_URL)

        event = {
            "title": title,
            "description": "",
            "start_date": start_date.isoformat(),
            "end_date": start_date.isoformat(),
            "start_time": start_time,
            "end_time": end_time,
            "url": event_url,
            "image_url": image_url,
            "event_type": event_type,
            "venue_name": VENUE_NAME,
            "start_location": VENUE_NAME,
            "end_location": None,
            "source": "website",
            "source_url": DEYOUNG_CALENDAR_URL,
            "organizer": VENUE_NAME,
        }
        events.append(event)

    logger.info(f"de Young Museum: scraped {len(events)} calendar/program events")
    return events


def scrape_all_deyoung_events() -> List[Dict]:
    """Entry point for source/cron scraper. Returns exhibitions + calendar/program events."""
    session = _get_session()
    today = date.today()

    exhibitions = scrape_deyoung_events()
    calendar_events = _scrape_calendar_events(session, today)

    seen_urls = {e["url"] for e in exhibitions}
    for e in calendar_events:
        if e["url"] not in seen_urls:
            seen_urls.add(e["url"])
            exhibitions.append(e)

    return exhibitions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = scrape_all_deyoung_events()
    ex = [e for e in events if e["event_type"] == "exhibition"]
    cal = [e for e in events if e["event_type"] != "exhibition"]
    print(f"Found {len(events)} events ({len(ex)} exhibitions, {len(cal)} calendar/programs)")
    for e in events[:8]:
        time_str = f" {e.get('start_time') or ''}" if e.get("start_time") else ""
        print(f"  - {e['title'][:50]} | {e['start_date']}{time_str} | {e['event_type']}")
