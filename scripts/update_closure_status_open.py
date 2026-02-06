#!/usr/bin/env python3
"""
Update venues.json: museums are no longer closed due to government shutdown.
Sets closure_status to 'open' and clears government-shutdown holiday_hours.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
venues_path = project_root / "data" / "venues.json"


def main():
    with open(venues_path, "r") as f:
        data = json.load(f)

    venues = data.get("venues", {})
    updated_count = 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")

    for vid, venue in venues.items():
        changed = False

        # Parse additional_info
        ai_str = venue.get("additional_info") or "{}"
        try:
            ai = json.loads(ai_str)
        except json.JSONDecodeError:
            continue

        # If closed due to government shutdown → open
        if ai.get("closure_status") == "closed" and "government shutdown" in (ai.get("closure_reason") or "").lower():
            ai["closure_status"] = "open"
            ai["closure_reason"] = "Open - check venue website for current hours."
            ai["last_updated"] = now
            venue["additional_info"] = json.dumps(ai)
            changed = True

        # Clear holiday_hours with government shutdown message
        hh = venue.get("holiday_hours") or ""
        if "government shutdown" in hh.lower() and "TEMPORARILY CLOSED" in hh:
            venue["holiday_hours"] = ""
            changed = True

        if changed:
            updated_count += 1
            print(f"  ✅ {venue.get('name', vid)}")

    # Write back
    with open(venues_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n🎉 Updated {updated_count} venues - museums no longer marked as closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
