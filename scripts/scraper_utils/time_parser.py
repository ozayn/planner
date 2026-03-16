"""Centralized time and time-range parsing helpers for scrapers."""

import re
from typing import Optional, Tuple


def parse_time(text: str) -> Optional[str]:
    """
    Parse a single time like '7pm', '7:30pm', '12:00 PM' to HH:MM (24h).

    Args:
        text: Raw text containing a time.

    Returns:
        Time string in HH:MM format (24h) or None.
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text, re.I)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = match.group(3).upper()

    if ampm == 'PM' and hour != 12:
        hour += 12
    elif ampm == 'AM' and hour == 12:
        hour = 0

    return f'{hour:02d}:{minute:02d}'


def parse_time_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a time range like '7pm–10pm', '12:00 PM – 4:00 PM' to (start_time, end_time).

    Args:
        text: Raw text containing a time range.

    Returns:
        Tuple of (start_time, end_time) in HH:MM format, or (None, None).
    """
    if not text or not isinstance(text, str):
        return None, None

    # Normalize dashes and whitespace
    text = re.sub(r'[\u00a0\u2013\u2014–\-]', ' ', text).strip()

    matches = list(re.finditer(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', text, re.I))
    if len(matches) >= 2:
        start = parse_time(matches[0].group(0))
        end = parse_time(matches[1].group(0))
        return start, end
    if len(matches) == 1:
        return parse_time(matches[0].group(0)), None

    return None, None
