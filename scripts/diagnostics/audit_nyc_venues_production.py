#!/usr/bin/env python3
"""
Audit NYC venue data in the deployed Railway PostgreSQL database.

Read-only. No writes. Helps identify duplicate NYC venues and determine
which duplicate is stale (older updated_at, generic metadata, fewer events).

Usage:
  DATABASE_URL=postgresql://... python scripts/audit_nyc_venues_production.py
  # Or with Railway CLI:
  railway run python scripts/audit_nyc_venues_production.py
"""

import os
import sys
from collections import defaultdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _check_postgres():
    """Ensure DATABASE_URL points to PostgreSQL."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set.")
        print("   Set it to your Railway PostgreSQL connection string.")
        print("   Example: railway run python scripts/audit_nyc_venues_production.py")
        return False
    if 'sqlite' in db_url.lower():
        print("❌ DATABASE_URL points to SQLite. This script requires PostgreSQL.")
        print("   Set DATABASE_URL to your Railway PostgreSQL connection string.")
        return False
    if 'postgresql' not in db_url.lower():
        print("❌ DATABASE_URL does not appear to be PostgreSQL.")
        return False
    return True


def _truncate(text: str, max_len: int = 80) -> str:
    """Truncate text for display."""
    if not text or not isinstance(text, str):
        return "(empty)"
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _is_generic_description(desc: str) -> bool:
    """Check if description looks generic."""
    if not desc or not desc.strip():
        return True
    generic_phrases = [
        "offering cultural experiences and entertainment",
        "a museum in ",
        "a landmark in ",
        "a park in ",
    ]
    lower = desc.lower()
    return any(p in lower for p in generic_phrases)


def run_audit():
    """Run audit of NYC venues in production database."""
    if not _check_postgres():
        sys.exit(1)

    from app import app, db, City, Venue, Event

    print("=" * 70)
    print("NYC VENUE AUDIT (Production PostgreSQL)")
    print("=" * 70)
    print("Read-only. No data will be modified.")
    print()

    with app.app_context():
        # 1. Resolve New York city
        nyc = (
            City.query.filter_by(
                name="New York",
                state="New York",
                country="United States",
            )
            .first()
        )

        if not nyc:
            print("❌ New York city not found in database.")
            print("   Expected: name='New York', state='New York', country='United States'")
            sys.exit(1)

        print(f"📍 New York city_id: {nyc.id}")
        print()

        # 2. Query all venues for NYC
        venues = Venue.query.filter_by(city_id=nyc.id).order_by(Venue.name).all()
        print(f"📊 Total NYC venues: {len(venues)}")
        print()

        # 3. Group by normalized name
        def normalize(name: str) -> str:
            return (name or "").lower().strip()

        by_name = defaultdict(list)
        for v in venues:
            by_name[normalize(v.name)].append(v)

        duplicates = {k: vs for k, vs in by_name.items() if len(vs) > 1}

        # 4. Print all NYC venues
        print("-" * 70)
        print("ALL NYC VENUES")
        print("-" * 70)
        for v in venues:
            dup_marker = " ⚠️  DUPLICATE" if len(by_name[normalize(v.name)]) > 1 else ""
            print(f"  {v.id:5} | {v.name}{dup_marker}")
        print()

        if not duplicates:
            print("✅ No duplicate venue names found.")
            return

        # 5. Print duplicate analysis
        print("-" * 70)
        print("DUPLICATE VENUE ANALYSIS")
        print("-" * 70)

        for norm_name, dup_venues in sorted(duplicates.items()):
            display_name = dup_venues[0].name  # Use first for display
            print()
            print(f"🔍 Duplicate: \"{display_name}\" ({len(dup_venues)} records)")
            print()

            # Get event counts
            event_counts = {}
            for v in dup_venues:
                event_counts[v.id] = Event.query.filter_by(venue_id=v.id).count()

            # Sort by: most events first, then newest updated_at, then more complete metadata
            def _stale_score(v):
                ec = event_counts[v.id]
                # Higher = better (keep): more events, newer updated_at, non-generic description
                updated = v.updated_at or datetime.min
                generic = 1 if _is_generic_description(v.description or "") else 0
                return (ec, updated, 1 - generic)

            dup_venues_sorted = sorted(dup_venues, key=_stale_score, reverse=True)
            keep_candidate = dup_venues_sorted[0]
            stale_candidates = dup_venues_sorted[1:]

            for i, v in enumerate(dup_venues):
                event_count = event_counts[v.id]
                is_likely_stale = v in stale_candidates

                print(f"  Venue ID: {v.id}")
                print(f"  Name: {v.name}")
                print(f"  updated_at: {v.updated_at}")
                print(f"  website_url: {v.website_url or '(empty)'}")
                print(f"  instagram_url: {v.instagram_url or '(empty)'}")
                print(f"  description: {_truncate(v.description or '')}")
                if v.description and _is_generic_description(v.description):
                    print(f"             ^ generic description")
                print(f"  event_count: {event_count}")

                if is_likely_stale:
                    print(f"  >>> LIKELY STALE (older updated_at, fewer events, or generic metadata)")
                else:
                    print(f"  >>> LIKELY KEEP (has events or newer updated_at)")

                print()

        print("-" * 70)
        print("SUMMARY")
        print("-" * 70)
        print(f"  Duplicate venue names: {len(duplicates)}")
        for norm_name, dup_venues in sorted(duplicates.items()):
            print(f"    - {dup_venues[0].name}: {len(dup_venues)} records")
        print()
        print("  To delete stale duplicates: use Admin UI or DELETE /api/delete-venue/<id>")
        print("  Always delete the record with 0 events (or fewer) to avoid orphaning events.")
        print()


if __name__ == "__main__":
    try:
        run_audit()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
