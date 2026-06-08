#!/usr/bin/env python3
"""
DC Urban Walkers — Meetup group scraper for https://www.meetup.com/dc-urban-walkers/

Parses embedded Apollo state from the public group page (no browser automation).
Each upcoming event includes title, schedule, location, description, URL, and image when present.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dateutil import parser as date_parser

from scripts.event_database_handler import create_events_in_database
from scripts.scraper_db_lookup import resolve_city_by_name, resolve_venue_in_city
from scripts.scraper_utils import create_cloudscraper_session

logger = logging.getLogger(__name__)

GROUP_URL = "https://www.meetup.com/dc-urban-walkers/"
GROUP_URLNAME = "dc-urban-walkers"
VENUE_NAME = "DC Urban Walkers"
CITY_NAME = "Washington"
SCRAPER_KEY = "dc_urban_walkers"


def _get_http_session():
    session = create_cloudscraper_session(
        verify_ssl=True,
        use_proxy=False,
        scraper_key=SCRAPER_KEY,
    )
    if not session:
        raise RuntimeError("cloudscraper session unavailable")
    session.headers.update({
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.meetup.com/",
    })
    return session


def _fetch_apollo_state(session, url: str) -> Dict[str, Any]:
    response = session.get(url, timeout=20)
    response.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"No __NEXT_DATA__ on {url}")
    payload = json.loads(match.group(1))
    apollo = payload.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__")
    if not apollo:
        raise ValueError(f"No __APOLLO_STATE__ on {url}")
    return apollo


def _resolve_ref(apollo: Dict[str, Any], ref: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(ref, dict):
        return None
    key = ref.get("__ref")
    if not key:
        return None
    node = apollo.get(key)
    return node if isinstance(node, dict) else None


def _photo_url(apollo: Dict[str, Any], event: Dict[str, Any]) -> Optional[str]:
    for field in ("displayPhoto", "featuredEventPhoto", "featuredPhoto"):
        photo_ref = event.get(field)
        photo = _resolve_ref(apollo, photo_ref)
        if not photo:
            continue
        for key in ("highResUrl", "baseUrl", "photoUrl"):
            url = photo.get(key)
            if url and isinstance(url, str):
                return url
    return None


def _format_venue_location(apollo: Dict[str, Any], event: Dict[str, Any]) -> str:
    """Meetup Apollo venue ref — typically the walk start / meeting point."""
    venue = _resolve_ref(apollo, event.get("venue"))
    if not venue:
        return ""
    parts = [
        venue.get("name") or "",
        venue.get("address") or "",
        venue.get("city") or "",
        venue.get("state") or "",
    ]
    return ", ".join(p.strip() for p in parts if p and str(p).strip())


def _clean_location_label(value: str) -> str:
    """Strip markdown emphasis and collapse whitespace from a location line."""
    if not value:
        return ""
    text = re.sub(r"\*+", "", value)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip(" .")


_START_LOCATION_RE = re.compile(
    r"^\s*\*{0,2}Start\s+Location\*{0,2}\s*:\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_END_LOCATION_RE = re.compile(
    r"^\s*\*{0,2}(?:Exit|End)\s+Location\*{0,2}\s*:\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_walk_locations(description: str) -> Tuple[str, str]:
    """
    Extract labeled start/end locations from Meetup event description.

    Apollo Event has a single ``venue`` (start); end/exit is usually only in prose, e.g.
    ``**Start Location:**`` and ``**Exit Location:**`` / ``**End Location:**``.
    """
    if not description:
        return "", ""

    start_match = _START_LOCATION_RE.search(description)
    end_match = _END_LOCATION_RE.search(description)
    start_loc = _clean_location_label(start_match.group(1)) if start_match else ""
    end_loc = _clean_location_label(end_match.group(1)) if end_match else ""
    return start_loc, end_loc


def _parse_iso_datetime(value: Optional[str]) -> Tuple[Optional[date], Optional[time]]:
    if not value:
        return None, None
    try:
        dt = date_parser.isoparse(value)
        return dt.date(), dt.time().replace(tzinfo=None)
    except (ValueError, TypeError):
        return None, None


def _infer_event_type(title: str, description: str = "") -> str:
    """Default ``walk`` for this group; only a few clear keyword overrides."""
    blob = f"{title} {description}".lower()

    if any(
        phrase in blob
        for phrase in (
            "photowalk",
            "photo walk",
            "photography walk",
            "street photography",
            "camera walk",
        )
    ) or re.search(r"\b(photography|photographers?|camera)\b", blob):
        return "photowalk"

    if re.search(r"\b(hike|hiking|hikes)\b", blob) or any(
        phrase in blob
        for phrase in (
            "nature trail",
            "forest trail",
            "mountain trail",
            "national park",
            "state park",
        )
    ):
        return "hike"

    if any(
        phrase in blob
        for phrase in (
            "guided tour",
            "walking tour",
            "museum tour",
            "historical tour",
            "history tour",
        )
    ):
        return "tour"

    return "walk"


def _sync_inferred_event_types(db, Event, venue_id: int, events: List[Dict[str, Any]]) -> None:
    """Persist inferred types on re-scrape (walk/hike are outside handler canonical_types)."""
    changed = False
    for ev in events:
        target = ev.get("event_type") or "walk"
        url = (ev.get("url") or "").strip()
        if not url:
            continue
        row = db.session.query(Event).filter(Event.url == url, Event.venue_id == venue_id).first()
        if row and row.event_type != target:
            row.event_type = target
            changed = True
    if changed:
        db.session.commit()


def _belongs_to_group(event: Dict[str, Any]) -> bool:
    event_url = (event.get("eventUrl") or "").lower()
    if f"/{GROUP_URLNAME}/events/" in event_url:
        return True
    group = event.get("group")
    group_node = None
    if isinstance(group, dict) and "__ref" in group:
        return GROUP_URLNAME in str(group.get("__ref", "")).lower()
    if isinstance(group, dict):
        group_node = group
    urlname = (group_node or {}).get("urlname") or (group_node or {}).get("name", "")
    return GROUP_URLNAME in str(urlname).lower()


def _events_from_apollo(apollo: Dict[str, Any]) -> List[Dict[str, Any]]:
    today = date.today()
    events: List[Dict[str, Any]] = []
    seen_urls = set()

    for node in apollo.values():
        if not isinstance(node, dict) or node.get("__typename") != "Event":
            continue
        if node.get("status") == "PAST":
            continue
        if not _belongs_to_group(node):
            event_url = (node.get("eventUrl") or "").lower()
            if f"/{GROUP_URLNAME}/events/" not in event_url:
                continue

        title = (node.get("title") or "").strip()
        event_url = (node.get("eventUrl") or "").strip()
        if not title or not event_url:
            continue

        normalized_url = event_url.split("?")[0].rstrip("/") + "/"
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)

        start_date, start_time = _parse_iso_datetime(node.get("dateTime"))
        end_date, end_time = _parse_iso_datetime(node.get("endTime"))
        if not start_date:
            logger.debug("DC Urban Walkers: skip (no start date): %s", title)
            continue
        if start_date < today:
            logger.debug("DC Urban Walkers: skip past: %s", title)
            continue

        description = (node.get("description") or "").strip()
        venue_location = _format_venue_location(apollo, node)
        desc_start, desc_end = _parse_walk_locations(description)
        start_location = desc_start or venue_location
        end_location = desc_end

        events.append({
            "title": title,
            "description": description,
            "start_date": start_date,
            "end_date": end_date or start_date,
            "start_time": start_time,
            "end_time": end_time,
            "start_location": start_location,
            "end_location": end_location,
            "url": normalized_url,
            "source_url": normalized_url,
            "registration_url": normalized_url,
            "image_url": _photo_url(apollo, node),
            "event_type": _infer_event_type(title, description),
            "is_registration_required": True,
            "source": "meetup",
            "organizer": VENUE_NAME,
        })

    events.sort(key=lambda e: (e.get("start_date"), e.get("start_time") or time.min))
    return events


def _resolve_venue(db, City, Venue):
    city = resolve_city_by_name(db, City, CITY_NAME, "District of Columbia")
    if not city:
        city = resolve_city_by_name(db, City, CITY_NAME)
    if not city:
        logger.warning("DC Urban Walkers: Washington city not found in database")
        return None
    venue = resolve_venue_in_city(
        db,
        Venue,
        city.id,
        website_contains=["meetup.com/dc-urban-walkers"],
        name_contains=["dc urban walkers"],
    )
    if not venue:
        logger.warning("DC Urban Walkers: venue not found — sync data/venues.json first")
    return venue


def scrape_dc_urban_walkers_events() -> List[Dict[str, Any]]:
    """Scrape upcoming events from the DC Urban Walkers Meetup group page."""
    from app import app, db, City, Venue

    with app.app_context():
        venue = _resolve_venue(db, City, Venue)
        if not venue:
            return []

        session = _get_http_session()
        apollo = _fetch_apollo_state(session, GROUP_URL)
        events = _events_from_apollo(apollo)

        for ev in events:
            ev["venue_id"] = venue.id
            ev["city_id"] = venue.city_id
            ev["venue_name"] = venue.name

        logger.info("DC Urban Walkers: found %s upcoming event(s)", len(events))
        return events


def create_events_in_database_wrapper(events: List[Dict[str, Any]]):
    from app import app, db, City, Venue, Event

    with app.app_context():
        venue = _resolve_venue(db, City, Venue)
        if not venue:
            return 0, 0, 0

        def processor(e):
            e["source"] = "meetup"
            e["organizer"] = venue.name
            e["venue_name"] = venue.name

        result = create_events_in_database(
            events=events,
            venue_id=venue.id,
            city_id=venue.city_id,
            venue_name=venue.name,
            db=db,
            Event=Event,
            Venue=Venue,
            source_url=GROUP_URL,
            custom_event_processor=processor,
        )
        _sync_inferred_event_types(db, Event, venue.id, events)
        return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("🚶 DC Urban Walkers: scraping Meetup group…")
    events = scrape_dc_urban_walkers_events()
    logger.info("   Found %s events", len(events))
    if events:
        created, updated, skipped = create_events_in_database_wrapper(events)
        logger.info("   Created: %s, Updated: %s, Skipped: %s", created, updated, skipped)
    return events


if __name__ == "__main__":
    main()
