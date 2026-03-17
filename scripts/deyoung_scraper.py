#!/usr/bin/env python3
"""
de Young Museum (FAMSF) scraper.
Scrapes exhibitions from https://www.famsf.org/exhibitions?where=de-young
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


def scrape_all_deyoung_events() -> List[Dict]:
    """Entry point for source/cron scraper. Returns events with venue_id/city_id set by caller."""
    return scrape_deyoung_events()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = scrape_all_deyoung_events()
    print(f"Found {len(events)} events")
    for e in events[:5]:
        print(f"  - {e['title']} | {e['start_date']}–{e['end_date']} | {e['event_type']}")
