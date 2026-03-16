"""Centralized date parsing helpers for scrapers."""

import re
from datetime import date, datetime
from typing import Optional


# Common month patterns (full and abbreviated)
MONTH_PATTERN = (
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|'
    r'Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?'
)
DATE_REGEX = re.compile(
    rf'{MONTH_PATTERN}\s+\d{{1,2}},?\s+\d{{4}}',
    re.I
)
ISO_DATE_REGEX = re.compile(r'\d{4}-\d{2}-\d{2}')

# Format order: try most specific first
DATE_FORMATS = [
    '%A, %B %d, %Y',   # Sunday, March 22, 2026
    '%A, %b %d, %Y',   # Sunday, Mar 22, 2026
    '%b. %d, %Y',      # Feb. 11, 2026
    '%b %d, %Y',       # Feb 11, 2026
    '%B %d, %Y',       # February 11, 2026
    '%B. %d, %Y',      # February. 11, 2026
    '%Y-%m-%d',        # 2026-02-11
    '%m/%d/%Y',        # 02/11/2026
    '%m-%d-%Y',        # 02-11-2026
]


def parse_date(text: str) -> Optional[date]:
    """
    Parse a date from text. Handles common formats and regex fallbacks.

    Args:
        text: Raw text that may contain a date (e.g. "Feb. 11, 2026", "Sunday, March 22, 2026").

    Returns:
        date object or None if no valid date found.
    """
    if not text or not isinstance(text, str):
        return None

    # Strip common noise
    text = re.sub(r'calendar icon|clock icon|map marker icon', '', text, flags=re.I).strip()

    # Try explicit formats first if we have a clean candidate
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue

    # Regex: "Feb. 11, 2026" or "March 22, 2026"
    match = DATE_REGEX.search(text)
    if match:
        date_str = match.group(0)
        for fmt in DATE_FORMATS[:4]:  # month formats only
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

    # ISO-style: 2026-02-11
    iso_match = ISO_DATE_REGEX.search(text)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(0), '%Y-%m-%d').date()
        except ValueError:
            pass

    return None
