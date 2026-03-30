#!/usr/bin/env python3
"""
Big Onion Walking Tours — dedicated parser for the our-tours listing and tour detail pages.

Fetches https://bigonion.com/our-tours/, extracts tour links, then each tour detail page for
schedule (smallest DOM occurrence block + JSON-LD fallback), description, image, location, price.
Uses cloudscraper
with optional Webshare proxy (scraper_proxy_opt_in('big_onion')).

Data: sources.json (handle bigonion.com) and venue with bigonion.org website_url.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bs4 import BeautifulSoup

from scripts.event_database_handler import create_events_in_database
from scripts.scraper_db_lookup import resolve_city_by_name, resolve_venue_in_city
from scripts.scraper_utils import create_cloudscraper_session, scraper_proxy_opt_in
from scripts.wharf_dc_scraper import get_event_urls_from_venue

logger = logging.getLogger(__name__)

BIG_ONION_WEBSITE = "https://bigonion.com"
BIG_ONION_DEFAULT = "https://bigonion.com/our-tours/"
BIG_ONION_NETLOC = "bigonion.com"
BIG_ONION_VENUE_NAME = "Big Onion Walking Tours"

# First path segment must not be one of these (WordPress / site pages, not individual tours)
_STATIC_PAGE_SLUGS = frozenset(
    {
        "our-tours",
        "the-schedule",
        "about-us",
        "how-it-works",
        "contact",
        "cart",
        "checkout",
        "search",
        "blog",
        "feed",
        "comments",
        "privacy-policy",
        "terms-of-use",
        "terms",
        "gift-certificates",
        "private-tours",
        "group-tours",
        "shop",
        "store",
        "home",
        "wp-admin",
        "wp-login",
        "wp-content",
        "wp-json",
        "category",
        "tag",
        "author",
        "page",
    }
)

# Canonical types required for this scraper output
_SIMPLE_TYPES = frozenset({"tour", "talk", "event"})

# Link / button labels that must never become event titles
_GENERIC_CTA_TITLES = frozenset(
    {
        "more info",
        "learn more",
        "read more",
        "book now",
        "buy tickets",
        "click here",
        "details",
        "view details",
        "more details",
        "get tickets",
        "shop now",
        "add to cart",
        "see more",
        "show more",
        "sign up",
        "register",
        "subscribe",
        "continue",
        "explore",
    }
)


def _is_generic_cta_title(text: Optional[str]) -> bool:
    if not text:
        return True
    t = " ".join(text.strip().split()).lower()
    if len(t) < 3:
        return True
    return t in _GENERIC_CTA_TITLES


def _title_from_url_slug(url: str) -> str:
    """Readable title from last path segment (e.g. satans-seat-... -> title case words)."""
    path = urlparse(url).path.strip("/")
    if not path:
        return ""
    seg = path.split("/")[-1]
    if not seg:
        return ""
    words = seg.replace("-", " ").replace("_", " ").split()
    if not words:
        return ""
    return " ".join(w[:1].upper() + w[1:].lower() if w else "" for w in words)


def _normalize_big_onion_event_type(event_data: dict) -> None:
    """Map to canonical tour / talk / event only."""
    raw = (event_data.get("event_type") or "tour").strip().lower()
    blob = f"{event_data.get('title', '')} {event_data.get('description', '')}".lower()
    if any(
        x in blob
        for x in (
            "lecture",
            "symposium",
            "author talk",
            "book talk",
        )
    ):
        event_data["event_type"] = "talk"
        return
    if raw in _SIMPLE_TYPES:
        event_data["event_type"] = raw
        return
    if "tour" in blob or "walking" in blob or "big onion" in blob:
        event_data["event_type"] = "tour"
        return
    event_data["event_type"] = "event"


def _get_http_session():
    """Cloudscraper session with optional Webshare proxy."""
    use_proxy = scraper_proxy_opt_in("big_onion")
    session = create_cloudscraper_session(
        base_url=BIG_ONION_DEFAULT.rstrip("/"),
        use_proxy=use_proxy,
    )
    if session:
        return session
    import requests

    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    s.verify = False
    return s


def _fetch_html(session, url: str) -> Optional[str]:
    try:
        r = session.get(url, timeout=30, verify=False)
        if r.status_code != 200:
            logger.debug("Big Onion: HTTP %s for %s", r.status_code, url)
            return None
        return r.text
    except Exception as e:
        logger.debug("Big Onion: fetch failed %s: %s", url, e)
        return None


def _slug_first_segment(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return ""
    return path.split("/")[0].lower()


def _is_candidate_tour_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host != BIG_ONION_NETLOC:
        return False
    seg = _slug_first_segment(url)
    if not seg or seg in _STATIC_PAGE_SLUGS:
        return False
    if seg.startswith("wp-"):
        return False
    # Single-segment public tour pages (WordPress pages)
    parts = [x for x in p.path.strip("/").split("/") if x]
    if len(parts) != 1:
        return False
    return True


def _parse_tour_links_from_listing(html: str, listing_url: str) -> List[Tuple[str, str]]:
    """Return list of (absolute_url, link_text) for tour detail pages."""
    soup = BeautifulSoup(html, "html.parser")
    seen: Dict[str, str] = {}
    for a in soup.select('a[href*="bigonion.com"]'):
        href = (a.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        abs_url = urljoin(listing_url, href)
        # Normalize: no query/fragment for dedup
        p = urlparse(abs_url)
        clean = f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}/"
        if not _is_candidate_tour_url(clean):
            continue
        title = a.get_text(" ", strip=True)
        if not title or len(title) < 3:
            continue
        if clean not in seen:
            seen[clean] = title
        else:
            prev = seen[clean]
            if _is_generic_cta_title(prev) and not _is_generic_cta_title(title):
                seen[clean] = title
    out = [(u, t) for u, t in seen.items()]
    out.sort(key=lambda x: x[0])
    return out


def _meta_content(soup: BeautifulSoup, prop: str) -> Optional[str]:
    m = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
    if m and m.get("content"):
        return m.get("content", "").strip()
    return None


def _parse_json_ld_events(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            types = t if isinstance(t, list) else [t] if t else []
            if any(str(x) in ("Event", "TheaterEvent", "ExhibitionEvent") for x in types):
                out.append(item)
    return out


_MONTH_ABBREV = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _resolve_event_date(month: int, day: int) -> Optional[date]:
    """Pick year so the occurrence is plausibly upcoming (rolling window)."""
    today = date.today()
    for y in (today.year, today.year + 1):
        try:
            d = date(y, month, day)
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


# Month-first: do not treat the hour in "Mar 1:00" / "Apr 11:00" as the calendar day.
_RE_MONTH_DAY = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?!\s*:)\b",
    re.I,
)
# Day-first: "28 Mar", "11 Apr" (common on Big Onion tour rows)
_RE_DAY_MONTH = re.compile(
    r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",
    re.I,
)
# e.g. 11:00 am – 1:00 pm or 11:00 am - 1:00 pm or 11:00 am to 1:00 pm
_RE_TIME_RANGE = re.compile(
    r"\b(\d{1,2}):(\d{2})\s*(am|pm)\s*(?:[\u2013\u2014\-]|\s+to\s+)\s*(\d{1,2}):(\d{2})\s*(am|pm)\b",
    re.I,
)


def _main_content_plain_text(soup: BeautifulSoup) -> str:
    """Prefer article/main body text where the schedule row usually lives."""
    for tag in ("article", "main"):
        el = soup.find(tag)
        if el:
            return el.get_text("\n", strip=True)
    el = soup.select_one(".entry-content, .post-content, .entry, #primary, .content-area")
    if el:
        return el.get_text("\n", strip=True)
    body = soup.find("body")
    return body.get_text("\n", strip=True) if body else ""


def _normalize_schedule_text(raw: str) -> str:
    return (
        raw.replace("\u2013", " - ")
        .replace("\u2014", " - ")
        .replace("–", " - ")
        .replace("—", " - ")
    )


# Max distance from the time range to the paired month/day within the same occurrence text
_PAIR_LOOKBACK = 420
_PAIR_LOOKAHEAD = 320


def _calendar_date_matches_in_segment(seg: str) -> List[re.Match]:
    """Month-first and day-first date tokens in document order."""
    ms: List[re.Match] = []
    for m in _RE_MONTH_DAY.finditer(seg):
        ms.append(m)
    for m in _RE_DAY_MONTH.finditer(seg):
        ms.append(m)
    ms.sort(key=lambda m: m.start())
    return ms


def _month_day_from_date_match(m: re.Match) -> Optional[Tuple[int, int]]:
    """(month, day) from a _RE_MONTH_DAY or _RE_DAY_MONTH match."""
    if m.re is _RE_MONTH_DAY:
        key = m.group(1).lower()[:3]
        month = _MONTH_ABBREV.get(key)
        if not month:
            return None
        return month, int(m.group(2))
    if m.re is _RE_DAY_MONTH:
        key = m.group(2).lower()[:3]
        month = _MONTH_ABBREV.get(key)
        if not month:
            return None
        return month, int(m.group(1))
    return None


def _pair_month_day_with_time_range(text: str, tr: re.Match) -> Optional[re.Match]:
    """
    Month/day that belongs with this time range: closest to the range, not the first
    month mention elsewhere on the page (e.g. 'Apr 1' in a blurb vs 'Apr 25' on the row).
    Supports month-first (Apr 17) and day-first (28 Mar, 11 Apr).
    """
    before = text[max(0, tr.start() - _PAIR_LOOKBACK) : tr.start()]
    after = text[tr.end() : min(len(text), tr.end() + _PAIR_LOOKAHEAD)]
    before_ms = _calendar_date_matches_in_segment(before)
    after_ms = _calendar_date_matches_in_segment(after)
    last_b = before_ms[-1] if before_ms else None
    first_a = after_ms[0] if after_ms else None
    if last_b and not first_a:
        return last_b
    if first_a and not last_b:
        return first_a
    if last_b and first_a:
        gap_b = tr.start() - last_b.end()
        gap_a = first_a.start() - tr.end()
        return last_b if gap_b <= gap_a else first_a
    return None


# Ignore tiny snippets (related tours, promos); prefer the main schedule row copy.
_MIN_SCHEDULE_BLOCK_LEN = 40


def _best_dom_schedule_block_text(soup: BeautifulSoup) -> Optional[str]:
    """
    Longest plausible schedule block under main content that contains both a month/day
    and a time range. Preferring longest reduces picking an unrelated short widget with
    a stray date/time (JSON-LD on Big Onion is not used for schedule — visible is truth).
    """
    root = soup.find("article") or soup.find("main") or soup.select_one(
        ".entry-content, .post-content, .entry, #primary, .content-area"
    )
    if not root:
        return None
    best_len = -1
    best: Optional[str] = None
    for el in [root, *root.find_all(True)]:
        if el.name in ("script", "style", "noscript"):
            continue
        if el.find_parent("footer") or el.find_parent("nav") or el.find_parent("aside") or el.find_parent("header"):
            continue
        t = el.get_text(" ", strip=True)
        if len(t) < _MIN_SCHEDULE_BLOCK_LEN or len(t) > 2500:
            continue
        nt = _normalize_schedule_text(t)
        if not _RE_TIME_RANGE.search(nt) or (
            not _RE_MONTH_DAY.search(nt) and not _RE_DAY_MONTH.search(nt)
        ):
            continue
        if len(t) > best_len:
            best_len = len(t)
            best = nt
    return best


def _parse_visible_occurrence(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Parse visible schedule from one occurrence block only (date + time not stitched
    from unrelated page regions). Uses the best DOM subtree (see _best_dom_schedule_block_text).
    """
    block = _best_dom_schedule_block_text(soup)
    if not block:
        return {}
    source = block

    for tr in _RE_TIME_RANGE.finditer(source):
        md = _pair_month_day_with_time_range(source, tr)
        if not md:
            continue
        sh, sm, sap, eh, em, eap = (
            int(tr.group(1)),
            int(tr.group(2)),
            tr.group(3),
            int(tr.group(4)),
            int(tr.group(5)),
            tr.group(6),
        )
        cal = _month_day_from_date_match(md)
        if not cal:
            continue
        month, day = cal
        sd = _resolve_event_date(month, day)
        if not sd:
            continue
        return {
            "start_date": sd.isoformat(),
            "end_date": sd.isoformat(),
            "start_time": _hhmm_from_12h(sh, sm, sap),
            "end_time": _hhmm_from_12h(eh, em, eap),
        }
    return {}


def _apply_visible_schedule_authoritative(out: Dict[str, Any], visible: Dict[str, Any]) -> None:
    """
    Big Onion schedule: only the visible occurrence row. Strip any schedule keys, then
    fill from visible when paired date+time exist; otherwise leave schedule unset (skip later).
    """
    for k in ("start_date", "end_date", "start_time", "end_time"):
        out.pop(k, None)
    has_vis_date = bool(visible.get("start_date"))
    has_vis_time = bool(visible.get("start_time") or visible.get("end_time"))
    if has_vis_date and has_vis_time:
        out["start_date"] = visible["start_date"]
        out["end_date"] = visible.get("end_date") or visible["start_date"]
        if visible.get("start_time"):
            out["start_time"] = visible["start_time"]
        if visible.get("end_time"):
            out["end_time"] = visible["end_time"]


def _format_json_ld_location(loc: Any) -> Optional[str]:
    """Turn schema.org Event location into a single line for start_location."""
    if isinstance(loc, str) and loc.strip():
        return loc.strip()[:500]
    if not isinstance(loc, dict):
        return None
    parts: List[str] = []
    name = loc.get("name")
    if isinstance(name, str) and name.strip():
        parts.append(name.strip())
    addr = loc.get("address")
    if isinstance(addr, str) and addr.strip():
        parts.append(addr.strip())
    elif isinstance(addr, dict):
        line = addr.get("streetAddress") or addr.get("name")
        city = addr.get("addressLocality")
        if isinstance(line, str) and line.strip():
            parts.append(line.strip())
        if isinstance(city, str) and city.strip():
            parts.append(city.strip())
    return ", ".join(parts)[:500] if parts else None


def _price_from_json_ld_item(item: dict) -> Optional[float]:
    offers = item.get("offers")
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if not isinstance(offers, dict):
        return None
    p = offers.get("price")
    if p is None and isinstance(offers.get("priceSpecification"), dict):
        p = offers["priceSpecification"].get("price")
    if p is None:
        return None
    try:
        return float(str(p).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _meeting_location_from_html(soup: BeautifulSoup) -> Optional[str]:
    """Visible meeting / departure line when JSON-LD omits location."""
    for tag in soup.find_all(["strong", "b", "span", "h3", "h4", "dt", "p"]):
        txt = tag.get_text(" ", strip=True)
        if not txt or len(txt) > 120:
            continue
        if re.match(r"^(Meeting|Meet at|Meet-up|Departure|Tour starts|Location)\b", txt, re.I):
            nxt = tag.find_next_sibling()
            if nxt and nxt.name not in ("script", "style"):
                loc = nxt.get_text(" ", strip=True)
                if loc and 4 < len(loc) < 600:
                    return loc[:500]
            m = re.search(r":\s*(.+)", txt)
            if m and len(m.group(1).strip()) > 4:
                return m.group(1).strip()[:500]
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        m = re.match(r"^(Meeting|Meet at)\s*:?\s*(.+)$", t, re.I)
        if m and len(m.group(2).strip()) > 4:
            return m.group(2).strip()[:500]
    return None


def _resolve_tour_title(soup: BeautifulSoup, page_url: str, json_ld_name: Optional[str]) -> str:
    """Prefer real tour names; never return generic CTA labels."""
    candidates: List[str] = []
    if json_ld_name and json_ld_name.strip():
        candidates.append(json_ld_name.strip())
    og = _meta_content(soup, "og:title")
    if og:
        candidates.append(og.split("|")[0].strip())
    h1 = soup.find("h1")
    if h1:
        ht = h1.get_text(" ", strip=True)
        if ht:
            candidates.append(ht)
    tt = soup.find("title")
    if tt:
        tt_text = tt.get_text(" ", strip=True)
        if tt_text:
            candidates.append(tt_text.split("|")[0].strip())
    for c in candidates:
        if c and not _is_generic_cta_title(c):
            return c
    slug = _title_from_url_slug(page_url)
    if slug and not _is_generic_cta_title(slug):
        return slug
    return ""


def _enrich_from_detail(html: str, page_url: str) -> Dict[str, Any]:
    """Pull description, image, location, price, and schedule from a tour detail page."""
    soup = BeautifulSoup(html, "html.parser")
    out: Dict[str, Any] = {}
    desc = _meta_content(soup, "og:description") or _meta_content(soup, "description")
    if desc:
        out["description"] = desc
    img = _meta_content(soup, "og:image")
    if img:
        out["image_url"] = img

    json_name: Optional[str] = None
    for item in _parse_json_ld_events(html):
        n = item.get("name")
        if isinstance(n, str) and n.strip():
            json_name = n.strip()
        loc = _format_json_ld_location(item.get("location"))
        if loc:
            out["start_location"] = loc
        pr = _price_from_json_ld_item(item)
        if pr is not None:
            out["price"] = pr
        # Do not use JSON-LD Event start/end — often UTC or misaligned vs the visible row.
        break

    if not (out.get("start_location") or "").strip():
        ml = _meeting_location_from_html(soup)
        if ml:
            out["start_location"] = ml

    visible = _parse_visible_occurrence(soup)
    _apply_visible_schedule_authoritative(out, visible)

    resolved = _resolve_tour_title(soup, page_url, json_name)
    if resolved:
        out["title"] = resolved
    return out


def _finalize_event_title(ev: Dict[str, Any], tour_url: str) -> None:
    """If listing or meta still left a CTA as title, replace with slug-based title."""
    t = (ev.get("title") or "").strip()
    if t and not _is_generic_cta_title(t):
        return
    slug = _title_from_url_slug(tour_url)
    if slug:
        ev["title"] = slug


def _title_acceptable(ev: Dict[str, Any]) -> bool:
    t = (ev.get("title") or "").strip()
    if len(t) < 4:
        return False
    return not _is_generic_cta_title(t)


def _has_real_scheduled_occurrence(ev: Dict[str, Any]) -> bool:
    """
    True only when detail enrichment produced a concrete date and clock time from the
    visible occurrence row, so generic tour product pages without a real run time are skipped.
    """
    if not ev.get("start_date"):
        return False
    return bool(ev.get("start_time") or ev.get("end_time"))


def _parse_date_field(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
        except (ValueError, AttributeError):
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
    return None


def _drop_if_past_dated_occurrence(ev: Dict[str, Any]) -> bool:
    """Return True if this event should be skipped (fully in the past)."""
    today = date.today()
    start_d = _parse_date_field(ev.get("start_date"))
    if not start_d:
        return False
    end_d = _parse_date_field(ev.get("end_date"))
    if end_d is not None:
        return end_d < today
    return start_d < today


def parse_big_onion_tours_listing(
    listing_url: str,
    session=None,
    enrich_details: bool = True,
) -> List[Dict[str, Any]]:
    """
    Fetch listing page, extract tour links, optionally enrich from detail pages.
    """
    if session is None:
        session = _get_http_session()
    html = _fetch_html(session, listing_url)
    if not html:
        logger.warning("Big Onion: empty or failed listing fetch: %s", listing_url)
        return []

    pairs = _parse_tour_links_from_listing(html, listing_url)
    logger.info("Big Onion: found %s tour links on listing", len(pairs))

    events: List[Dict[str, Any]] = []
    for i, (tour_url, link_title) in enumerate(pairs):
        ev: Dict[str, Any] = {
            "title": link_title,
            "url": tour_url,
            "description": "",
            "event_type": "tour",
            "venue_name": BIG_ONION_VENUE_NAME,
        }
        if enrich_details:
            dh = _fetch_html(session, tour_url)
            if dh:
                extra = _enrich_from_detail(dh, tour_url)
                if extra.get("title"):
                    ev["title"] = extra["title"]
                if extra.get("description"):
                    ev["description"] = extra["description"]
                if extra.get("image_url"):
                    ev["image_url"] = extra["image_url"]
                if extra.get("start_location"):
                    ev["start_location"] = extra["start_location"]
                if extra.get("price") is not None:
                    ev["price"] = extra["price"]
                if extra.get("start_date"):
                    ev["start_date"] = extra["start_date"]
                if extra.get("end_date"):
                    ev["end_date"] = extra["end_date"]
                if extra.get("start_time"):
                    ev["start_time"] = extra["start_time"]
                if extra.get("end_time"):
                    ev["end_time"] = extra["end_time"]
        _finalize_event_title(ev, tour_url)
        if not _has_real_scheduled_occurrence(ev):
            logger.debug("Big Onion: skipping (no scheduled date+time): %s", ev.get("url"))
            continue
        if not _title_acceptable(ev):
            logger.debug("Big Onion: skipping (no acceptable title): %s", ev.get("url"))
            continue
        _normalize_big_onion_event_type(ev)
        if _drop_if_past_dated_occurrence(ev):
            logger.debug("Big Onion: skipping past-dated: %s", ev.get("title"))
            continue
        events.append(ev)
    return events


def _resolve_big_onion_venue(db, City, Venue):
    """Big Onion venue in NYC via shared natural-key lookup (see scripts/scraper_db_lookup.py)."""
    city = resolve_city_by_name(db, City, "New York", "New York")
    if not city:
        logger.warning(
            "Big Onion scraper: city not found — expected a city named 'New York' "
            "(with state 'New York' if present in the database)"
        )
        return None
    venue = resolve_venue_in_city(
        db,
        Venue,
        city.id,
        website_contains=["bigonion.com"],
        name_contains=["big onion"],
    )
    if not venue:
        logger.warning(
            "Big Onion scraper: venue not found for city %r (id=%s) — "
            "expect website containing bigonion.com or name containing 'Big Onion'",
            city.name,
            city.id,
        )
        return None
    return venue


def scrape_big_onion_events():
    """
    Scrape Big Onion Walking Tours using the dedicated listing/detail parser.
    Listing URL comes from venue additional_info.event_paths or BIG_ONION_DEFAULT.
    """
    from app import app, db, City, Venue

    with app.app_context():
        venue = _resolve_big_onion_venue(db, City, Venue)
        if not venue:
            return []

        event_urls = get_event_urls_from_venue(venue)
        if not event_urls:
            event_urls = [BIG_ONION_DEFAULT]
            logger.debug("Big Onion: using default tours listing URL")

        listing_url = event_urls[0].rstrip("/") + "/"
        session = _get_http_session()
        events = parse_big_onion_tours_listing(listing_url, session=session, enrich_details=True)
        return events


def create_events_in_database_wrapper(events):
    """Persist Big Onion events; tag source as website."""

    from app import app, db, City, Venue, Event

    with app.app_context():
        venue = _resolve_big_onion_venue(db, City, Venue)
        if not venue:
            return 0, 0, 0

        def processor(e):
            e["source"] = "website"
            e["organizer"] = venue.name
            e["venue_name"] = venue.name
            _normalize_big_onion_event_type(e)

        created, updated, skipped = create_events_in_database(
            events=events,
            venue_id=venue.id,
            city_id=venue.city_id,
            venue_name=venue.name,
            db=db,
            Event=Event,
            Venue=Venue,
            source_url=BIG_ONION_DEFAULT,
            custom_event_processor=processor,
        )
        return created, updated, skipped


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("🧅 Big Onion Walking Tours: scraping…")
    events = scrape_big_onion_events()
    logger.info("   Found %s events", len(events))
    if events:
        c, u, s = create_events_in_database_wrapper(events)
        logger.info("   Created: %s, Updated: %s, Skipped: %s", c, u, s)
    return events


if __name__ == "__main__":
    main()
