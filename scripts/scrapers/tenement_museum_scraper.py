#!/usr/bin/env python3
"""
Tenement Museum — tours & programs listing (NYC).

Uses GenericVenueScraper against the tours URL from venue additional_info.event_paths,
with canonical event_type normalization. Optional Webshare proxy via scraper_proxy_opt_in.
"""

import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.event_database_handler import create_events_in_database
from scripts.generic_venue_scraper import GenericVenueScraper
from scripts.scraper_db_lookup import resolve_city_by_name, resolve_venue_in_city
from scripts.scraper_utils import scraper_proxy_opt_in
from scripts.wharf_dc_scraper import get_event_urls_from_venue

logger = logging.getLogger(__name__)

TENEMENT_WEBSITE = "https://www.tenement.org"
TENEMENT_TOURS_DEFAULT = "https://www.tenement.org/tours/"

# Canonical categories used across Planner
_CANONICAL_TYPES = frozenset(
    {"tour", "exhibition", "festival", "photowalk", "film", "workshop", "talk", "music", "improv", "event"}
)

_TYPE_ALIASES = {
    "screening": "film",
    "lecture": "talk",
    "lectures": "talk",
    "walking tour": "tour",
    "walking tours": "tour",
    "gallery talk": "talk",
    "performance": "event",
    "museum_event": "event",
    "class": "workshop",
    "classes": "workshop",
    "demo": "workshop",
}


def _normalize_tenement_event_type(event_data: dict) -> None:
    """Map scraper output to canonical event_type; infer from title/description when needed."""
    raw = (event_data.get("event_type") or "event").strip().lower()
    if raw in _TYPE_ALIASES:
        raw = _TYPE_ALIASES[raw]
    if raw in _CANONICAL_TYPES:
        event_data["event_type"] = raw
        return
    blob = f"{event_data.get('title', '')} {event_data.get('description', '')}".lower()
    if any(x in blob for x in ("walking tour", "neighborhood tour", "guided tour", "apartment tour")):
        event_data["event_type"] = "tour"
    elif "tour" in blob and raw not in _CANONICAL_TYPES:
        event_data["event_type"] = "tour"
    elif any(x in blob for x in ("film", "screening", "cinema")):
        event_data["event_type"] = "film"
    elif any(x in blob for x in ("workshop", "class", "studio")):
        event_data["event_type"] = "workshop"
    elif any(x in blob for x in ("talk", "lecture", "conversation", "symposium", "program")):
        event_data["event_type"] = "talk"
    elif "exhibition" in blob or "gallery" in blob:
        event_data["event_type"] = "exhibition"
    else:
        event_data["event_type"] = "event" if raw not in _CANONICAL_TYPES else raw


def scrape_tenement_museum_events():
    """
    Scrape Tenement Museum tours/programs from listing URL(s) in venue additional_info,
    or default /tours/ page.
    """
    from app import app, db, City, Venue

    with app.app_context():
        city = resolve_city_by_name(db, City, "New York", "New York")
        if not city:
            logger.warning(
                "Tenement Museum scraper: city not found — expected 'New York' (state 'New York' if stored)"
            )
            return []
        venue = resolve_venue_in_city(
            db,
            Venue,
            city.id,
            website_contains=["tenement.org"],
            name_contains=["tenement museum"],
        )
        if not venue:
            logger.warning(
                "Tenement Museum scraper: venue not found for city %r (id=%s) — tenement.org / Tenement Museum",
                city.name,
                city.id,
            )
            return []

        event_urls = get_event_urls_from_venue(venue)
        if not event_urls:
            event_urls = [TENEMENT_TOURS_DEFAULT]
            logger.debug("Tenement Museum: using default /tours/ URL")

        scraper = GenericVenueScraper(use_proxy=scraper_proxy_opt_in("tenement_museum"))
        base = (venue.website_url or TENEMENT_WEBSITE).rstrip("/")
        events = scraper.scrape_venue_events(
            venue_url=base,
            venue_name=venue.name,
            event_type=None,
            time_range="next_month",
            event_urls=event_urls,
        ) or []

        for e in events:
            _normalize_tenement_event_type(e)

        return events


def create_events_in_database_wrapper(events):
    """Persist Tenement Museum events; tag source as website."""

    from app import app, db, City, Venue, Event

    with app.app_context():
        city = resolve_city_by_name(db, City, "New York", "New York")
        if not city:
            return 0, 0, 0
        venue = resolve_venue_in_city(
            db,
            Venue,
            city.id,
            website_contains=["tenement.org"],
            name_contains=["tenement museum"],
        )
        if not venue:
            return 0, 0, 0

        def processor(e):
            e["source"] = "website"
            _normalize_tenement_event_type(e)

        created, updated, skipped = create_events_in_database(
            events=events,
            venue_id=venue.id,
            city_id=venue.city_id,
            venue_name=venue.name,
            db=db,
            Event=Event,
            Venue=Venue,
            source_url=TENEMENT_TOURS_DEFAULT,
            custom_event_processor=processor,
        )
        return created, updated, skipped


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("🏠 Tenement Museum: scraping tours & programs…")
    events = scrape_tenement_museum_events()
    logger.info("   Found %s events", len(events))
    if events:
        c, u, s = create_events_in_database_wrapper(events)
        logger.info("   Created: %s, Updated: %s, Skipped: %s", c, u, s)
    return events


if __name__ == "__main__":
    main()
