#!/usr/bin/env python3
"""
Operational buckets for scheduled cron scrapers.

- stable: Eventbrite (embassies, cultural centers, extras), Meetup, reliable direct scrapers (NGA, SAAM, …)
- protected: troublesome direct website scrapers only (403 / Cloudflare / proxy-sensitive)

Eventbrite-backed venues always use the shared Eventbrite flow on stable cron, even when they are
embassies or cultural centers. Protected is not used for venue type alone.

Classify new *direct* scrapers here when adding them to cron_run_scheduled_scrapers.py.
"""

BUCKET_STABLE = "stable"
BUCKET_PROTECTED = "protected"

# Direct website scrapers with recurring operational trouble (not Eventbrite flow).
PROTECTED_DIRECT_URL_FRAGMENT: dict[str, str] = {
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
PROTECTED_DIRECT_NAME_FRAGMENT: dict[str, str] = {
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

# Backward-compatible aliases
VENUE_URL_BUCKET = PROTECTED_DIRECT_URL_FRAGMENT
VENUE_NAME_BUCKET = PROTECTED_DIRECT_NAME_FRAGMENT

# Non-embassy DC venues scraped via shared Eventbrite on stable cron (see cron_run_scheduled_scrapers).
EVENTBRITE_EXTRA_VENUE_NAME_FRAGMENTS = (
    "washington improv theater",
    "smithsonian national museum of american history",
)

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


def is_protected_direct_scraper_venue(website_url: str, venue_name: str = "") -> bool:
    """True when cron runs a troublesome direct website scraper for this venue (not Eventbrite)."""
    url_lower = (website_url or "").lower()
    for fragment in PROTECTED_DIRECT_URL_FRAGMENT:
        if fragment in url_lower:
            return True
    name_lower = (venue_name or "").lower()
    for fragment in PROTECTED_DIRECT_NAME_FRAGMENT:
        if fragment in name_lower:
            return True
    return False


def get_venue_scraper_bucket_heuristic(website_url: str, venue_name: str = "") -> str:
    """Return stable or protected from direct-scraper rules only (no admin override)."""
    if is_protected_direct_scraper_venue(website_url, venue_name):
        return BUCKET_PROTECTED
    return BUCKET_STABLE


def venue_uses_shared_eventbrite_cron(venue) -> bool:
    """
    True when stable cron scrapes this venue via the shared Eventbrite flow.

    Includes diplomatic/cultural Eventbrite venues and named Eventbrite extras.
    Does not include museums that only have an Eventbrite ticketing_url but are
    scraped via a protected direct website scraper (e.g. NPG, Asian Art).
    """
    from scripts.eventbrite_scraper import is_diplomatic_eventbrite_venue

    if is_diplomatic_eventbrite_venue(venue):
        return True

    name_lower = (venue.name or "").lower()
    if not any(frag in name_lower for frag in EVENTBRITE_EXTRA_VENUE_NAME_FRAGMENTS):
        return False
    return "eventbrite" in (venue.ticketing_url or "").lower()


def resolve_venue_scraper_bucket(
    website_url: str,
    venue_name: str = "",
    cron_bucket=None,
    venue=None,
) -> str:
    """Cron bucket for a venue: explicit admin setting wins, else direct-scraper / Eventbrite rules."""
    explicit = parse_venue_cron_bucket_setting(cron_bucket)
    if explicit:
        return explicit
    if is_protected_direct_scraper_venue(website_url, venue_name):
        return BUCKET_PROTECTED
    if venue is not None and venue_uses_shared_eventbrite_cron(venue):
        return BUCKET_STABLE
    return BUCKET_STABLE


def get_venue_scraper_bucket(website_url: str, venue_name: str = "") -> str:
    """Backward-compatible alias for heuristic-only classification."""
    return get_venue_scraper_bucket_heuristic(website_url, venue_name)


def bucket_display_name(bucket: str) -> str:
    if bucket == BUCKET_PROTECTED:
        return "Protected cron"
    return "Stable cron"


def bucket_runs_stable_sections(bucket: str) -> bool:
    """Eventbrite embassies/extras and other stable-only sections (standalones use standalone_runs_in_bucket)."""
    return bucket == BUCKET_STABLE
