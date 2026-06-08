#!/usr/bin/env python3
"""
Remove stale government-shutdown closure notes from data/venues.json.

- Clears holiday_hours with TEMPORARILY CLOSED / government shutdown text
- Sets closure_status to open when it was closed only for the shutdown
- Removes closure_reason text that references government shutdown
- Preserves other additional_info keys (event_paths, scraping_paths, etc.)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).parent.parent
venues_path = project_root / "data" / "venues.json"

SHUTDOWN_HOLIDAY_PREFIX = "TEMPORARILY CLOSED: Closed due to government shutdown."


def _has_shutdown_text(text: str) -> bool:
    return "government shutdown" in (text or "").lower()


def _clean_additional_info(ai: dict, now: str) -> bool:
    changed = False
    reason = ai.get("closure_reason") or ""

    if _has_shutdown_text(reason):
        if ai.get("closure_status") == "closed":
            ai["closure_status"] = "open"
        del ai["closure_reason"]
        ai["last_updated"] = now
        changed = True

    return changed


def main():
    with open(venues_path, "r") as f:
        data = json.load(f)

    venues = data.get("venues", {})
    updated = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")

    for vid, venue in venues.items():
        changed = False
        changes = []

        hh = venue.get("holiday_hours") or ""
        if _has_shutdown_text(hh):
            venue["holiday_hours"] = ""
            changed = True
            changes.append("holiday_hours cleared")

        ai_str = venue.get("additional_info") or ""
        if ai_str.strip():
            try:
                ai = json.loads(ai_str)
            except json.JSONDecodeError:
                ai = None
            if isinstance(ai, dict) and _clean_additional_info(ai, now):
                venue["additional_info"] = json.dumps(ai)
                changed = True
                changes.append("additional_info updated")

        if changed:
            updated.append((vid, venue.get("name", vid), changes))
            print(f"  ✅ [{vid}] {venue.get('name', vid)} — {', '.join(changes)}")

    with open(venues_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"\n🎉 Updated {len(updated)} venues — removed government-shutdown closure notes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
