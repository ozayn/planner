#!/usr/bin/env python3
"""
Tulip Day scraper for tulipday.eu
Extracts the main event details for Tulip Day Washington.
"""
import logging
import re
from datetime import datetime, date, time
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import urljoin


logger = logging.getLogger(__name__)

TULIPDAY_URL = "https://tulipday.eu/"
ORGANIZER = "Royal Anthos"


def _parse_date(text: str) -> Optional[date]:
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),\s*(\d{4})",
        text,
        re.I,
    )
    if not match:
        return None
    month_name = match.group(1).lower()
    day = int(match.group(2))
    year = int(match.group(3))
    month_map = {
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
    month = month_map.get(month_name)
    if not month:
        return None
    return date(year, month, day)


def _parse_time(time_str: str) -> Optional[time]:
    time_str = time_str.strip().lower().replace(".", "")
    match = re.match(r"(\d{1,2}):(\d{2})\s*(am|pm)", time_str)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    am_pm = match.group(3)
    if am_pm == "pm" and hour != 12:
        hour += 12
    if am_pm == "am" and hour == 12:
        hour = 0
    return time(hour, minute)


def _parse_time_range(text: str) -> tuple[Optional[time], Optional[time]]:
    match = re.search(
        r"from\s+(\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.|am|pm))\s*(?:–|-|—|to)\s*"
        r"(\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.|am|pm))",
        text,
        re.I,
    )
    if not match:
        return None, None
    start = _parse_time(match.group(1))
    end = _parse_time(match.group(2))
    return start, end


def _extract_description(text: str) -> str:
    # Keep a concise summary: look for the descriptive sentence near the event title
    match = re.search(
        r"(This spring[^.]+?National Mall[^.]+?\.)",
        text,
        re.I,
    )
    if match:
        return match.group(1).strip()

    # Fallback: first reasonable sentence mentioning Tulip Day Washington or National Mall
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if len(sentence_clean) < 40 or len(sentence_clean) > 400:
            continue
        if "tulip day washington" in sentence_clean.lower() or "national mall" in sentence_clean.lower():
            return sentence_clean
    return "Tulip Day Washington returns with a one-day tulip-picking celebration on the National Mall."


def _fetch_html(url: str) -> Optional[str]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://tulipday.eu/",
        "Connection": "keep-alive",
    }
    try:
        import requests  # Optional dependency in some local setups
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.warning(f"Tulip Day fetch via requests failed for {url}: {e}")
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url, timeout=20, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception as e2:
            logger.warning(f"Tulip Day fetch via cloudscraper failed for {url}: {e2}")
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as f:
                return f.read().decode("utf-8", errors="ignore")
        except Exception as e2:
            logger.warning(f"Tulip Day fetch failed for {url}: {e2}")
            try:
                import subprocess
                cmd = [
                    "curl",
                    "-L",
                    "-s",
                    "-A",
                    headers.get("User-Agent", "Mozilla/5.0"),
                    url,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                if result.returncode == 0 and result.stdout:
                    return result.stdout
            except Exception as e3:
                logger.error(f"Tulip Day fetch via curl failed for {url}: {e3}")
            return None


def scrape_tulipday_event() -> Optional[Dict]:
    """Scrape Tulip Day event from tulipday.eu homepage."""
    try:
        html = _fetch_html(TULIPDAY_URL)
        if not html:
            return None
        soup = None
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            page_text = unescape(soup.get_text(" ", strip=True))
        except Exception:
            # Fallback: strip tags with regex if BeautifulSoup isn't available
            page_text = unescape(re.sub(r"<[^<]+?>", " ", html))
            page_text = re.sub(r"\s+", " ", page_text)
        # Fallback: information page sometimes has the date/details
        if "tulip day washington" not in page_text.lower():
            info_html = _fetch_html(urljoin(TULIPDAY_URL, "information/"))
            if info_html:
                try:
                    from bs4 import BeautifulSoup
                    info_soup = BeautifulSoup(info_html, "html.parser")
                    page_text = unescape(info_soup.get_text(" ", strip=True))
                except Exception:
                    page_text = unescape(re.sub(r"<[^<]+?>", " ", info_html))
                    page_text = re.sub(r"\s+", " ", page_text)

        event_date = _parse_date(page_text)
        start_time, end_time = _parse_time_range(page_text)

        if not event_date:
            logger.warning("Tulip Day scraper: no date found on page")
            return None

        title = "Tulip Day Washington"
        title_text = None
        if soup is not None:
            title_tag = soup.find("title")
            if title_tag and title_tag.get_text(strip=True):
                title_text = title_tag.get_text(strip=True)
        else:
            title_match = re.search(r"<title>([^<]+)</title>", html, re.I)
            if title_match:
                title_text = title_match.group(1).strip()
        if title_text and "tulipday" in title_text.lower():
            title = title_text.split(" - ")[0].strip()

        description = _extract_description(page_text)

        image_url = None
        if soup is not None:
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                image_url = og_image.get("content", "").strip()
        if not image_url:
            og_match = re.search(r'property=["\\\']og:image["\\\']\\s+content=["\\\']([^"\\\']+)["\\\']', html, re.I)
            if og_match:
                image_url = og_match.group(1).strip()
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(TULIPDAY_URL, image_url)

        location = None
        if "national mall" in page_text.lower():
            location = "National Mall, Washington, DC"
        elif "union square" in page_text.lower():
            location = "Union Square, New York, NY"

        return {
            "title": title,
            "description": description,
            "start_date": event_date,
            "end_date": event_date,
            "start_time": start_time,
            "end_time": end_time,
            "start_location": location,
            "url": TULIPDAY_URL,
            "source_url": TULIPDAY_URL,
            "organizer": ORGANIZER,
            "event_type": "festival",
            "is_registration_required": False,
            "image_url": image_url,
        }
    except Exception as e:
        logger.error(f"Error scraping Tulip Day: {e}")
        return None


def scrape_all_tulipday_events() -> List[Dict]:
    event = scrape_tulipday_event()
    return [event] if event else []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = scrape_all_tulipday_events()
    print(f"Found {len(events)} Tulip Day events")
    if events:
        print(events[0])
