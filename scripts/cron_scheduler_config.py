#!/usr/bin/env python3
"""
Scheduler config for cron_run_scheduled_scrapers.py.

Defines per-scraper run rules:
- always: run every cron execution
- seasonal: run only in specified months (1-12)
- manual_only: never run from cron (admin button only)
"""

from datetime import date

# Run rule constants
RULE_ALWAYS = "always"
RULE_SEASONAL = "seasonal"
RULE_MANUAL = "manual_only"


def should_run(rule: str, seasonal_months: list[int] | None = None, today: date | None = None) -> bool:
    """
    Return True if the scraper should run given its rule and optional seasonal months.

    Args:
        rule: RULE_ALWAYS, RULE_SEASONAL, or RULE_MANUAL
        seasonal_months: For RULE_SEASONAL, list of months (1-12) when to run
        today: Date to check (default: today)
    """
    if today is None:
        today = date.today()

    if rule == RULE_ALWAYS:
        return True
    if rule == RULE_MANUAL:
        return False
    if rule == RULE_SEASONAL and seasonal_months:
        return today.month in seasonal_months
    return False


# Venue-based scrapers (matched by URL in cron loop)
# Key: substring to match in venue.website_url
# Value: (rule, seasonal_months or None)
VENUE_SCHEDULE_RULES = {
    "tulipday.eu": (RULE_SEASONAL, [3, 4]),  # March, April - tulip season
}

# Standalone scrapers (run outside the museum loop)
# Key: scraper id (for logging)
# Value: (rule, seasonal_months or None)
STANDALONE_SCHEDULE_RULES = {
    "websters": (RULE_ALWAYS, None),
    "wharf_dc": (RULE_ALWAYS, None),
    "shoot_nyc": (RULE_ALWAYS, None),
    "hammer": (RULE_ALWAYS, None),
    "dcparade": (RULE_SEASONAL, [1, 2]),  # January, February - Chinese New Year
}


def get_venue_schedule_rule(venue_url: str) -> tuple[str, list[int] | None]:
    """Get (rule, seasonal_months) for a venue by its website URL."""
    url_lower = (venue_url or "").lower()
    for key, (rule, months) in VENUE_SCHEDULE_RULES.items():
        if key in url_lower:
            return rule, months
    return RULE_ALWAYS, None


def get_standalone_schedule_rule(scraper_id: str) -> tuple[str, list[int] | None]:
    """Get (rule, seasonal_months) for a standalone scraper."""
    return STANDALONE_SCHEDULE_RULES.get(scraper_id, (RULE_ALWAYS, None))
