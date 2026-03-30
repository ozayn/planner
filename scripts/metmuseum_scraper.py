#!/usr/bin/env python3
"""
The Metropolitan Museum of Art — tours & programs listing.

Uses GenericVenueScraper against the Met tours URL from venue additional_info.event_paths,
with canonical event_type normalization. The Met front end may be behind Vercel protection;
cloudscraper + retries in the generic scraper improve success vs plain requests.
"""

import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.event_database_handler import create_events_in_database
from scripts.generic_venue_scraper import GenericVenueScraper
from scripts.scraper_utils import scraper_proxy_opt_in
from scripts.wharf_dc_scraper import get_event_urls_from_venue

logger = logging.getLogger(__name__)

MET_WEBSITE = "https://www.metmuseum.org"
MET_TOURS_DEFAULT = "https://www.metmuseum.org/events/programs/met-tours"

# Canonical categories used across Planner
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


def scrape_metmuseum_events():
    """
    Scrape Met tours/programs from listing URL(s) in venue additional_info, or default met-tours page.
    """
    from app import app, db, Venue

    with app.app_context():
        venue = (
            Venue.query.filter(Venue.city_id == 2)
            .filter(
                db.or_(
                    Venue.website_url.ilike("%metmuseum.org%"),
                    Venue.name.ilike("%metropolitan museum%"),
                )
            )
            .first()
        )

        if not venue:
            logger.warning("Metropolitan Museum scraper: venue not found (city_id=2, metmuseum.org)")
            return []

        event_urls = get_event_urls_from_venue(venue)
        if not event_urls:
            event_urls = [MET_TOURS_DEFAULT]
            logger.debug("Met: using default met-tours URL")

        scraper = GenericVenueScraper(use_proxy=scraper_proxy_opt_in('metmuseum'))
        base = (venue.website_url or MET_WEBSITE).rstrip("/")
        events = scraper.scrape_venue_events(
            venue_url=base,
            venue_name=venue.name,
            event_type=None,
            time_range="next_month",
            event_urls=event_urls,
        ) or []

        for e in events:
            _normalize_met_event_type(e)

        return events


def create_events_in_database_wrapper(events):
    """Persist Met events; tag source as website."""

    from app import app, db, Venue, Event

    with app.app_context():
        venue = (
            Venue.query.filter(Venue.city_id == 2)
            .filter(
                db.or_(
                    Venue.website_url.ilike("%metmuseum.org%"),
                    Venue.name.ilike("%metropolitan museum%"),
                )
            )
            .first()
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
            source_url=MET_TOURS_DEFAULT,
            custom_event_processor=processor,
        )
        return created, updated, skipped


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("🏛️ The Met: scraping tours & programs…")
    events = scrape_metmuseum_events()
    logger.info("   Found %s events", len(events))
    if events:
        c, u, s = create_events_in_database_wrapper(events)
        logger.info("   Created: %s, Updated: %s, Skipped: %s", c, u, s)
    return events


if __name__ == "__main__":
    main()
