#!/usr/bin/env python3
"""
Sync local cities, venues, and sources JSON into the deployed Railway PostgreSQL database.

Uses natural-key matching (name, state, country for cities; name + city for venues/sources).
No destructive deletes. Duplicate production matches are logged as conflicts for manual review.

Usage:
  Dry run (default):  python scripts/sync_json_to_production.py
  Apply changes:     python scripts/sync_json_to_production.py --apply

Requires: PRODUCTION_DATABASE_URL (preferred) or DATABASE_URL set to PostgreSQL — e.g. in .env
  (Railway public URL when running from your laptop). This script sets DATABASE_URL for its
  process only so the Flask app connects to production; your normal local DATABASE_URL is unchanged
  outside this run.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _production_database_url() -> Optional[str]:
    """
    Prefer PRODUCTION_DATABASE_URL so local .env can keep DATABASE_URL=sqlite for the app.
    Fall back to DATABASE_URL only when it looks like PostgreSQL.
    """
    prod = (os.getenv("PRODUCTION_DATABASE_URL") or "").strip()
    if prod:
        return prod
    fb = os.getenv("DATABASE_URL")
    if not fb:
        return None
    low = fb.lower()
    if "sqlite" in low:
        return None
    if "postgresql" in low:
        return fb
    return None


def _check_postgres() -> bool:
    """Resolve production PostgreSQL URL and set DATABASE_URL for this process (before app import)."""
    db_url = _production_database_url()
    if not db_url:
        print("❌ No production PostgreSQL connection string.")
        print(
            "   Set PRODUCTION_DATABASE_URL in .env (recommended), or DATABASE_URL to a PostgreSQL URL."
        )
        print("   Use your Railway public Postgres URL when running this script locally.")
        return False
    if "sqlite" in db_url.lower():
        print("❌ Production URL points to SQLite. This script requires PostgreSQL.")
        return False
    if "postgresql" not in db_url.lower():
        print("❌ Production URL does not appear to be PostgreSQL.")
        return False
    os.environ["DATABASE_URL"] = db_url
    return True


def _norm(val):
    """Normalize empty string and None for state/country comparisons."""
    if val is None:
        return ""
    return str(val).strip() if val else ""


def _city_key(c):
    """Natural key for city: (name, state, country) lowercase, normalized."""
    return (
        (c.get("name") or "").strip().lower(),
        _norm(c.get("state")).lower(),
        _norm(c.get("country")).lower(),
    )


def _resolve_city_by_natural_key(db, City, city_info: dict):
    """
    Resolve DB city by natural key (name, state, country) from city_info.
    Returns (city, None) if unique match, (None, error_msg) if ambiguous or not found.
    Normalizes empty string and None for state/country.
    """
    name = (city_info.get("name") or "").strip()
    state = _norm(city_info.get("state"))
    country = _norm(city_info.get("country"))

    if not name:
        return None, "city name empty"

    # Query with normalized values; coalesce None to "" for comparison
    matches = City.query.filter(
        City.name.ilike(name),
        db.func.lower(db.func.coalesce(City.state, "")) == state.lower(),
        db.func.lower(db.func.coalesce(City.country, "")) == country.lower(),
    ).all()

    if len(matches) > 1:
        return None, f"ambiguous: {len(matches)} DB cities match ({name}, {state or '—'}, {country or '—'})"
    if len(matches) == 1:
        return matches[0], None
    return None, f"not found: ({name}, {state or '—'}, {country or '—'})"


def _safe_float(val, default=None):
    """Safely parse float. Returns default on failure."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _diff_str(old_val, new_val, max_len=60):
    """Format old -> new for dry-run diff output."""
    def _trunc(v):
        s = str(v) if v is not None else "(none)"
        return s[:max_len] + "..." if len(s) > max_len else s
    return f"{_trunc(old_val)} → {_trunc(new_val)}"


def _venue_field_diff(existing, info: dict) -> dict:
    """Return dict of field -> (old_val, new_val) for fields that would change."""
    diff = {}
    fields = [
        ("venue_type", "venue_type", "venue"),
        ("address", "address", None),
        ("latitude", "latitude", None),
        ("longitude", "longitude", None),
        ("image_url", "image_url", None),
        ("website_url", "website_url", None),
        ("description", "description", None),
    ]
    for attr, key, default in fields:
        new_raw = info.get(key, default)
        old_val = getattr(existing, attr, None)
        if key == "latitude" or key == "longitude":
            new_val = _safe_float(new_raw, old_val)
        else:
            new_val = new_raw if new_raw is not None else (default or "")
        if new_val != old_val and (new_val is not None or old_val is not None):
            diff[attr] = (old_val, new_val)
    return diff


def _source_field_diff(existing, info: dict) -> dict:
    """Return dict of field -> (old_val, new_val) for fields that would change."""
    diff = {}
    rel_new = _safe_float(info.get("reliability_score"), existing.reliability_score)
    if rel_new is not None and rel_new != (existing.reliability_score or 0):
        diff["reliability_score"] = (existing.reliability_score, rel_new)
    for attr, key in [
        ("handle", "handle"),
        ("url", "url"),
        ("description", "description"),
        ("is_active", "is_active"),
    ]:
        new_val = info.get(key)
        old_val = getattr(existing, attr, None)
        if new_val != old_val:
            diff[attr] = (old_val, new_val)
    return diff


def _load_json(path: str) -> dict:
    """Load JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(p, "r") as f:
        return json.load(f)


def run_sync(apply: bool):
    """Run sync. If apply=False, dry run only."""
    if not _check_postgres():
        sys.exit(1)

    from app import app, db, City, Venue, Source

    data_dir = Path(__file__).parent.parent / "data"
    cities_path = data_dir / "cities.json"
    venues_path = data_dir / "venues.json"
    sources_path = data_dir / "sources.json"

    for p in [cities_path, venues_path, sources_path]:
        if not p.exists():
            print(f"❌ Missing: {p}")
            sys.exit(1)

    mode = "APPLY" if apply else "DRY RUN"
    print("=" * 70)
    print(f"SYNC JSON → PRODUCTION ({mode})")
    print("=" * 70)
    print("Entities: cities, venues, sources (no events)")
    print("Matching: by natural key (name, state, country / name + city)")
    if not apply:
        print()
        print("⚠️  DRY RUN: No changes will be written. Use --apply to sync.")
    print()

    try:
        cities_data = _load_json(str(cities_path))
        venues_data = _load_json(str(venues_path))
        sources_data = _load_json(str(sources_path))
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        sys.exit(1)

    cities_json = cities_data.get("cities", cities_data)
    venues_json = venues_data.get("venues", {})
    sources_json = sources_data.get("sources", {})

    # Build JSON city_id -> city info for sources
    json_city_by_id = {}
    for kid, info in cities_json.items():
        if isinstance(info, dict) and info.get("name"):
            try:
                json_city_by_id[int(kid)] = info
            except (ValueError, TypeError):
                pass

    stats = {"cities": {"create": 0, "update": 0, "skip": 0, "conflict": 0},
             "venues": {"create": 0, "update": 0, "skip": 0, "conflict": 0},
             "sources": {"create": 0, "update": 0, "skip": 0, "conflict": 0}}
    conflicts = []

    with app.app_context():
        # --- CITIES ---
        print("-" * 70)
        print("CITIES")
        print("-" * 70)

        db_cities_by_key = defaultdict(list)
        for c in City.query.all():
            key = (c.name.lower(), _norm(c.state).lower(), _norm(c.country).lower())
            db_cities_by_key[key].append(c)

        for json_id, info in cities_json.items():
            if not isinstance(info, dict) or not info.get("name"):
                continue
            key = _city_key(info)
            name = info.get("name", "").strip()
            state = _norm(info.get("state"))
            country = _norm(info.get("country"))
            timezone = info.get("timezone") or "UTC"

            matches = db_cities_by_key[key]

            if len(matches) > 1:
                stats["cities"]["conflict"] += 1
                conflicts.append(f"City '{name}' ({state}, {country}): {len(matches)} DB matches - manual review")
                print(f"  ⚠️  CONFLICT: {name} - {len(matches)} duplicate DB records")
            elif len(matches) == 1:
                existing = matches[0]
                # Check if update needed (normalize for comparison)
                if _norm(existing.state) != state or _norm(existing.country) != country or (existing.timezone or "UTC") != timezone:
                    stats["cities"]["update"] += 1
                    print(f"  📝 UPDATE: {name} (id={existing.id})")
                    if not apply:
                        if _norm(existing.state) != state:
                            print(f"       state: {_diff_str(existing.state, state)}")
                        if _norm(existing.country) != country:
                            print(f"       country: {_diff_str(existing.country, country)}")
                        if (existing.timezone or "UTC") != timezone:
                            print(f"       timezone: {_diff_str(existing.timezone or 'UTC', timezone)}")
                    if apply:
                        existing.state = state
                        existing.country = country
                        existing.timezone = timezone
                        existing.updated_at = datetime.utcnow()
                else:
                    stats["cities"]["skip"] += 1
                    print(f"  ⏭️  SKIP: {name} (id={existing.id}) - no changes")
            else:
                stats["cities"]["create"] += 1
                print(f"  ➕ CREATE: {name}")
                if apply:
                    new_city = City(name=name, state=state, country=country, timezone=timezone)
                    db.session.add(new_city)

        if apply:
            db.session.flush()  # Get new city IDs for venues/sources

        # --- VENUES ---
        print()
        print("-" * 70)
        print("VENUES")
        print("-" * 70)

        # Build DB venues by (name_lower, city_id)
        db_venues_by_key = defaultdict(list)
        for v in Venue.query.all():
            if v.city_id:
                key = (v.name.lower().strip(), v.city_id)
                db_venues_by_key[key].append(v)

        for json_id, info in venues_json.items():
            if not isinstance(info, dict) or not info.get("name"):
                continue
            venue_name = info.get("name", "").strip()

            # Resolve city via city_id -> cities.json -> DB (natural key)
            json_city_id = info.get("city_id")
            if json_city_id is None:
                print(f"  ⚠️  SKIP: {venue_name} - no city_id in JSON")
                stats["venues"]["skip"] += 1
                continue
            try:
                json_city_id = int(json_city_id)
            except (ValueError, TypeError):
                print(f"  ⚠️  SKIP: {venue_name} - invalid city_id")
                stats["venues"]["skip"] += 1
                continue

            city_info = json_city_by_id.get(json_city_id)
            if not city_info:
                print(f"  ⚠️  SKIP: {venue_name} - city_id {json_city_id} not in cities.json")
                stats["venues"]["skip"] += 1
                continue

            city, err = _resolve_city_by_natural_key(db, City, city_info)
            if err:
                stats["venues"]["skip"] += 1
                if "ambiguous" in err:
                    conflicts.append(f"Venue '{venue_name}': {err}")
                print(f"  ⚠️  SKIP: {venue_name} - {err}")
                continue

            key = (venue_name.lower(), city.id)
            matches = db_venues_by_key[key]

            if len(matches) > 1:
                stats["venues"]["conflict"] += 1
                conflicts.append(f"Venue '{venue_name}' in {city.name}: {len(matches)} DB matches - manual review")
                print(f"  ⚠️  CONFLICT: {venue_name} in {city.name} - {len(matches)} duplicate DB records")
            elif len(matches) == 1:
                existing = matches[0]
                venue_diff = _venue_field_diff(existing, info)
                if not venue_diff:
                    stats["venues"]["skip"] += 1
                    print(f"  ⏭️  SKIP: {venue_name} (id={existing.id}) in {city.name} - no changes")
                else:
                    stats["venues"]["update"] += 1
                    print(f"  📝 UPDATE: {venue_name} (id={existing.id}) in {city.name}")
                    if not apply:
                        for field, (old_val, new_val) in venue_diff.items():
                            print(f"       {field}: {_diff_str(old_val, new_val)}")
                if apply and venue_diff:
                    existing.venue_type = info.get("venue_type") or existing.venue_type
                    existing.address = info.get("address", existing.address)
                    raw_lat, raw_lon = info.get("latitude"), info.get("longitude")
                    if raw_lat is not None:
                        lat = _safe_float(raw_lat, None)
                        if lat is None:
                            print(f"       ⚠️  latitude parse failed for {venue_name}, keeping existing")
                        else:
                            existing.latitude = lat
                    if raw_lon is not None:
                        lon = _safe_float(raw_lon, None)
                        if lon is None:
                            print(f"       ⚠️  longitude parse failed for {venue_name}, keeping existing")
                        else:
                            existing.longitude = lon
                    existing.image_url = info.get("image_url", existing.image_url)
                    existing.instagram_url = info.get("instagram_url", existing.instagram_url)
                    existing.facebook_url = info.get("facebook_url", existing.facebook_url)
                    existing.twitter_url = info.get("twitter_url", existing.twitter_url)
                    existing.youtube_url = info.get("youtube_url", existing.youtube_url)
                    existing.tiktok_url = info.get("tiktok_url", existing.tiktok_url)
                    existing.website_url = info.get("website_url", existing.website_url)
                    existing.ticketing_url = info.get("ticketing_url", existing.ticketing_url)
                    existing.description = info.get("description", existing.description)
                    existing.opening_hours = info.get("opening_hours", existing.opening_hours)
                    existing.holiday_hours = info.get("holiday_hours", existing.holiday_hours)
                    existing.phone_number = info.get("phone_number", existing.phone_number)
                    existing.email = info.get("email", existing.email)
                    existing.tour_info = info.get("tour_info", existing.tour_info)
                    existing.admission_fee = info.get("admission_fee", existing.admission_fee)
                    existing.additional_info = info.get("additional_info", existing.additional_info)
                    if "visibility" in info:
                        existing.visibility = info.get("visibility") or "public"
                    existing.updated_at = datetime.utcnow()
            else:
                stats["venues"]["create"] += 1
                print(f"  ➕ CREATE: {venue_name} in {city.name}")
                if apply:
                    raw_lat, raw_lon = info.get("latitude"), info.get("longitude")
                    lat = _safe_float(raw_lat, None)
                    lon = _safe_float(raw_lon, None)
                    if raw_lat is not None and lat is None:
                        print(f"       ⚠️  latitude parse failed for {venue_name}, using None")
                    if raw_lon is not None and lon is None:
                        print(f"       ⚠️  longitude parse failed for {venue_name}, using None")
                    new_venue = Venue(
                        name=venue_name,
                        venue_type=info.get("venue_type", "venue"),
                        address=info.get("address"),
                        city_id=city.id,
                        latitude=lat,
                        longitude=lon,
                        image_url=info.get("image_url"),
                        instagram_url=info.get("instagram_url"),
                        facebook_url=info.get("facebook_url"),
                        twitter_url=info.get("twitter_url"),
                        youtube_url=info.get("youtube_url"),
                        tiktok_url=info.get("tiktok_url"),
                        website_url=info.get("website_url"),
                        ticketing_url=info.get("ticketing_url"),
                        description=info.get("description"),
                        opening_hours=info.get("opening_hours"),
                        holiday_hours=info.get("holiday_hours"),
                        phone_number=info.get("phone_number"),
                        email=info.get("email"),
                        tour_info=info.get("tour_info"),
                        admission_fee=info.get("admission_fee"),
                        additional_info=info.get("additional_info"),
                        visibility=info.get("visibility") or "public",
                    )
                    db.session.add(new_venue)

        # --- SOURCES ---
        print()
        print("-" * 70)
        print("SOURCES")
        print("-" * 70)

        db_sources_by_key = defaultdict(list)
        for s in Source.query.all():
            if s.city_id:
                key = (s.name.lower().strip(), s.city_id)
                db_sources_by_key[key].append(s)

        for json_id, info in sources_json.items():
            if not isinstance(info, dict) or not info.get("name"):
                continue
            source_name = info.get("name", "").strip()
            json_city_id = info.get("city_id")

            if json_city_id is None:
                print(f"  ⚠️  SKIP: {source_name} - no city_id")
                stats["sources"]["skip"] += 1
                continue

            try:
                json_city_id = int(json_city_id)
            except (ValueError, TypeError):
                print(f"  ⚠️  SKIP: {source_name} - invalid city_id")
                stats["sources"]["skip"] += 1
                continue

            city_info = json_city_by_id.get(json_city_id)
            if not city_info:
                print(f"  ⚠️  SKIP: {source_name} - city_id {json_city_id} not in cities.json")
                stats["sources"]["skip"] += 1
                continue

            city, err = _resolve_city_by_natural_key(db, City, city_info)
            if err:
                stats["sources"]["skip"] += 1
                if "ambiguous" in err:
                    conflicts.append(f"Source '{source_name}': {err}")
                print(f"  ⚠️  SKIP: {source_name} - {err}")
                continue

            key = (source_name.lower(), city.id)
            matches = db_sources_by_key[key]

            if len(matches) > 1:
                stats["sources"]["conflict"] += 1
                conflicts.append(f"Source '{source_name}' in {city.name}: {len(matches)} DB matches - manual review")
                print(f"  ⚠️  CONFLICT: {source_name} in {city.name} - {len(matches)} duplicate DB records")
            elif len(matches) == 1:
                existing = matches[0]
                source_diff = _source_field_diff(existing, info)
                if not source_diff:
                    stats["sources"]["skip"] += 1
                    print(f"  ⏭️  SKIP: {source_name} (id={existing.id}) in {city.name} - no changes")
                else:
                    stats["sources"]["update"] += 1
                    print(f"  📝 UPDATE: {source_name} (id={existing.id}) in {city.name}")
                    if not apply:
                        for field, (old_val, new_val) in source_diff.items():
                            print(f"       {field}: {_diff_str(old_val, new_val)}")
                if apply and source_diff:
                    existing.handle = info.get("handle") or existing.handle
                    existing.source_type = info.get("source_type") or existing.source_type
                    existing.url = info.get("url", existing.url)
                    existing.description = info.get("description", existing.description)
                    existing.city_id = city.id
                    existing.covers_multiple_cities = info.get("covers_multiple_cities", False)
                    existing.covered_cities = info.get("covered_cities", "") or ""
                    existing.event_types = info.get("event_types", "[]") or "[]"
                    existing.is_active = info.get("is_active", True)
                    rel = _safe_float(info.get("reliability_score"), existing.reliability_score or 3.0)
                    if rel is not None:
                        existing.reliability_score = rel
                    else:
                        print(f"       ⚠️  reliability_score parse failed for {source_name}, keeping {existing.reliability_score}")
                    existing.posting_frequency = info.get("posting_frequency", "") or ""
                    existing.notes = info.get("notes", "") or ""
                    existing.scraping_pattern = info.get("scraping_pattern", "") or ""
                    existing.updated_at = datetime.utcnow()
            else:
                stats["sources"]["create"] += 1
                print(f"  ➕ CREATE: {source_name} in {city.name}")
                if apply:
                    handle = info.get("handle") or info.get("url", "") or source_name or "unknown"
                    if isinstance(handle, str) and len(handle) > 100:
                        handle = handle[:100]
                    rel = _safe_float(info.get("reliability_score"), 3.0)
                    if rel is None:
                        rel = 3.0
                        print(f"       ⚠️  reliability_score parse failed for {source_name}, using 3.0")
                    new_source = Source(
                        name=source_name,
                        handle=handle,
                        source_type=info.get("source_type") or "website",
                        url=info.get("url"),
                        description=info.get("description"),
                        city_id=city.id,
                        covers_multiple_cities=info.get("covers_multiple_cities", False),
                        covered_cities=info.get("covered_cities", "") or "",
                        event_types=info.get("event_types", "[]") or "[]",
                        is_active=info.get("is_active", True),
                        reliability_score=rel,
                        posting_frequency=info.get("posting_frequency", "") or "",
                        notes=info.get("notes", "") or "",
                        scraping_pattern=info.get("scraping_pattern", "") or "",
                    )
                    db.session.add(new_source)

        # --- COMMIT / SUMMARY ---
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)

        for entity, s in stats.items():
            print(f"  {entity}: create={s['create']} update={s['update']} skip={s['skip']} conflict={s['conflict']}")

        if conflicts:
            print()
            print("CONFLICTS (manual review required):")
            for c in conflicts:
                print(f"  - {c}")

        if apply:
            try:
                db.session.commit()
                print()
                print("✅ Changes committed to database.")
            except Exception as e:
                db.session.rollback()
                print()
                print(f"❌ Commit failed: {e}")
                sys.exit(1)
        else:
            print()
            print("✅ Dry run complete. No changes written.")
            print("   Run with --apply to sync.")


def main():
    parser = argparse.ArgumentParser(
        description="Sync local JSON (cities, venues, sources) to production PostgreSQL by natural key."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database. Default is dry run.",
    )
    args = parser.parse_args()
    run_sync(apply=args.apply)


if __name__ == "__main__":
    main()
