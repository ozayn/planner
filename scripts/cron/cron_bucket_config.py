#!/usr/bin/env python3
"""
Operational buckets for scheduled cron scrapers.

- stable: reliable sources (Eventbrite, Meetup, most venue HTML scrapers)
- protected: recurring 403 / Cloudflare / proxy-sensitive or heavy sources (NGA, Asian Art, NPG, Hirshhorn, OCMA, etc.)

Classify new scrapers here when adding them to cron_run_scheduled_scrapers.py.
"""

BUCKET_STABLE = "stable"
BUCKET_PROTECTED = "protected"

# Specialized museum scrapers matched by venue.website_url fragment
VENUE_URL_BUCKET: dict[str, str] = {
    "nga.gov": BUCKET_PROTECTED,           # National Gallery of Art
    "asia.si.edu": BUCKET_PROTECTED,       # Smithsonian National Museum of Asian Art
    "npg.si.edu": BUCKET_PROTECTED,        # National Portrait Gallery
    "hirshhorn.si.edu": BUCKET_PROTECTED,  # Hirshhorn Museum
    "africa.si.edu": BUCKET_PROTECTED,     # African Art (legacy URL)
    "african-art-museum": BUCKET_PROTECTED,  # si.edu/museums/african-art-museum
    "ocma.art": BUCKET_PROTECTED,          # Orange County Museum of Art (OCMA)
    "tenement.org": BUCKET_PROTECTED,      # Tenement Museum
    "deyoung.famsf.org": BUCKET_PROTECTED,  # de Young Museum
}

# Fallback when URL does not match (Freer/Sackler share asia.si.edu; name guard)
VENUE_NAME_BUCKET: dict[str, str] = {
    "national gallery of art": BUCKET_PROTECTED,
    "hirshhorn": BUCKET_PROTECTED,
    "national portrait gallery": BUCKET_PROTECTED,
    "smithsonian national museum of asian art": BUCKET_PROTECTED,
    "national museum of african art": BUCKET_PROTECTED,
    "freer gallery": BUCKET_PROTECTED,
    "sackler gallery": BUCKET_PROTECTED,
    "orange county museum of art": BUCKET_PROTECTED,
    "tenement museum": BUCKET_PROTECTED,
    "de young": BUCKET_PROTECTED,
}

# Standalone scraper blocks in cron_run_scheduled_scrapers (default: stable)
STANDALONE_SCRAPER_BUCKET: dict[str, str] = {
    "tenement_museum": BUCKET_PROTECTED,
    "deyoung": BUCKET_PROTECTED,
    "ocma": BUCKET_PROTECTED,
}


def standalone_runs_in_bucket(scraper_id: str, bucket: str) -> bool:
    """Whether a standalone cron scraper block should run in this bucket."""
    return STANDALONE_SCRAPER_BUCKET.get(scraper_id, BUCKET_STABLE) == bucket


def parse_venue_cron_bucket_setting(value) -> str | None:
    """Normalize admin DB value. None/empty/inherit = no explicit override."""
    if value is None:
        return None
    if str(value).strip().lower() in ("", "inherit"):
        return None
    bucket = str(value).strip().lower()
    if bucket in (BUCKET_STABLE, BUCKET_PROTECTED):
        return bucket
    return None


def get_venue_scraper_bucket_heuristic(website_url: str, venue_name: str = "") -> str:
    """Return stable or protected bucket from URL/name rules (no admin override)."""
    url_lower = (website_url or "").lower()
    for fragment, bucket in VENUE_URL_BUCKET.items():
        if fragment in url_lower:
            return bucket
    name_lower = (venue_name or "").lower()
    for fragment, bucket in VENUE_NAME_BUCKET.items():
        if fragment in name_lower:
            return bucket
    return BUCKET_STABLE


def resolve_venue_scraper_bucket(
    website_url: str,
    venue_name: str = "",
    cron_bucket=None,
) -> str:
    """Cron bucket for a venue: explicit admin setting wins, else code heuristics."""
    explicit = parse_venue_cron_bucket_setting(cron_bucket)
    if explicit:
        return explicit
    return get_venue_scraper_bucket_heuristic(website_url, venue_name)


def get_venue_scraper_bucket(website_url: str, venue_name: str = "") -> str:
    """Backward-compatible alias for heuristic-only classification."""
    return get_venue_scraper_bucket_heuristic(website_url, venue_name)


def bucket_display_name(bucket: str) -> str:
    if bucket == BUCKET_PROTECTED:
        return "Protected cron"
    return "Stable cron"


def bucket_runs_stable_sections(bucket: str) -> bool:
    """Embassies and Eventbrite extras run on stable cron only (standalones use standalone_runs_in_bucket)."""
    return bucket == BUCKET_STABLE
