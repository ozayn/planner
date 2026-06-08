#!/usr/bin/env python3
"""Startup environment checks for scheduled cron scrapers."""

import logging
import os

from scripts.env_config import ensure_env_loaded
from scripts.cron_bucket_config import BUCKET_PROTECTED, BUCKET_STABLE

logger = logging.getLogger(__name__)


def _has_eventbrite_token() -> bool:
    return bool(
        (os.getenv("EVENTBRITE_API_TOKEN") or "").strip()
        or (os.getenv("EVENTBRITE_PRIVATE_TOKEN") or "").strip()
    )


def _has_webshare_proxy() -> bool:
    """True when any Webshare proxy env var is configured (see scraper_utils.session)."""
    if (os.getenv("WEBSHARE_PROXY_URL") or "").strip():
        return True
    if (os.getenv("WEBSHARE_PROXY_HTTP") or "").strip():
        return True
    if (os.getenv("WEBSHARE_PROXY_HTTPS") or "").strip():
        return True
    return False


def validate_cron_env(bucket: str) -> bool:
    """
    Validate cron environment for the given bucket.

    Returns False when required vars are missing (caller should exit before scraping).
    """
    ensure_env_loaded()

    ok = True

    db_url = (os.getenv("DATABASE_URL") or "").strip()
    if not db_url:
        logger.error("❌ Missing required env var: DATABASE_URL")
        logger.error(
            "   Cron will fall back to local SQLite and fail (e.g. no such table: cities). "
            "Set DATABASE_URL to your PostgreSQL connection string."
        )
        ok = False

    if bucket == BUCKET_STABLE:
        if not _has_eventbrite_token():
            logger.warning(
                "⚠️ Stable cron: no Eventbrite token configured; Eventbrite sections may fail"
            )
            logger.warning(
                "   Set EVENTBRITE_API_TOKEN or EVENTBRITE_PRIVATE_TOKEN"
            )
    elif bucket == BUCKET_PROTECTED:
        if not _has_webshare_proxy():
            logger.warning(
                "⚠️ Protected cron: WEBSHARE_PROXY_URL not set; proxy-sensitive scrapers may fail"
            )
            logger.warning(
                "   Set WEBSHARE_PROXY_URL (or WEBSHARE_PROXY_HTTP / WEBSHARE_PROXY_HTTPS)"
            )
    else:
        raise ValueError(f"Unknown cron bucket: {bucket}")

    return ok
