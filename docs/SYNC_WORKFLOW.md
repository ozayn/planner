# Sync Workflow

## Purpose

This document describes the safe **Local → Production** sync workflow for cities, venues, and sources in the Planner repository. Use it when local and deployed numeric IDs differ: JSON files are the transport layer, and matching is done by name rather than ID.

---

## Core Rules

- **JSON files are the transport layer** — Edit `data/cities.json`, `data/venues.json`, and `data/sources.json` locally; reload endpoints read these files into the database.
- **Match by name, not numeric ID** — Reload logic matches cities by `name` + `state` + `country`, venues and sources by `name`. IDs in JSON are not used for matching.
- **Reload each environment separately** — Run reload endpoints on local first, then on production after deploy. Each database gets its own IDs.
- **Verify by city/venue/source name, not by local IDs** — Production IDs differ from local. Always verify by selecting the city and checking names and counts.
- **Avoid renaming venues or sources casually** — Renaming creates a new record; the old one remains and events may still point to it. Fix events manually if you rename.

---

## Safest Manual Workflow

1. **Back up** `data/cities.json`, `data/venues.json`, `data/sources.json`
2. **Edit JSON locally** by name (use `city_name` for venues)
3. **Validate JSON syntax** — e.g. `python3 -c "import json; json.load(open('data/venues.json'))"`
4. **Reload locally** — Call `reload-cities`, `reload-venues-from-json`, `reload-sources` as needed
5. **Verify locally** in Admin UI and API (select city, check names and counts)
6. **Commit and push** JSON changes
7. **Deploy** (e.g. push to trigger Railway deploy)
8. **Call production reload endpoints** (see Preferred Production Endpoint Order)
9. **Verify production** by name and counts (Admin UI and API)

---

## Preferred Production Endpoint Order

Call in this order:

1. `POST /api/admin/reload-cities`
2. `POST /api/admin/reload-venues-from-json`
3. `POST /api/admin/reload-sources`

**Alternative:** `POST /api/admin/load-all-data` — loads all three in one call. Use when convenient, but granular calls give clearer per-entity feedback.

**Avoid:** `POST /api/load-data` — expects an older venues.json structure and can fail or corrupt data.

**Optional — `scripts/sync_json_to_production.py`:** Syncs JSON directly to PostgreSQL from your machine. Set **`PRODUCTION_DATABASE_URL`** in `.env` (Railway public URL; see `.env.example`). The script prefers that variable over `DATABASE_URL` so local development can keep `DATABASE_URL` on SQLite.

---

## Verification Steps

- **`GET /api/admin/stats`** — Total counts for cities, venues, sources, events
- **`GET /api/admin/cities`** — List cities; find target city by name and note its `id`
- **`GET /api/venues?city_id=<id>`** — Venues for that city; verify by name
- **`GET /api/sources?city_id=<id>`** — Sources for that city; verify by name
- **Admin UI** — Select the city, confirm venue and source names and counts

---

## Risks and Pitfalls

- **Renaming venues/sources** — Creates a new record; the old one remains. Events still reference the old record. Fix events manually or via migration.
- **Duplicate names** — Venue and source matching uses `name` only. Duplicate names can cause the wrong record to be updated.
- **Duplicate cities** — Same `name` + `state` + `country` can overwrite or confuse matching.
- **Venue matching by name only** — If two cities have venues with the same name, the first match wins. Keep venue names unique per city.
- **Scripts that hardcode `city_id`** — Some scripts (e.g. `sync_monitor.py`) use `city_id=1`. Production may use different IDs. Prefer name-based lookup or `/api/admin/stats`.

---

## Readiness Assessment

| Entity  | Status | Notes |
|---------|--------|-------|
| **Cities** | Ready | Match by `name` + `state` + `country` |
| **Venues**  | Ready if names unique per city | Match by `name` only |
| **Sources** | Ready | Match by `name`; `city_id` mapped via `cities.json` |

**Known gaps:**

- Venue matching uses `name` only — risky if the same name exists in multiple cities
- Some scripts hardcode `city_id` and are not safe across environments

---

## Maintainer Checklist

**Before sync:**

- [ ] Backed up `data/cities.json`, `data/venues.json`, `data/sources.json`
- [ ] Edited JSON by name; `city_name` correct for venues
- [ ] Validated JSON syntax

**After local reload:**

- [ ] Verified in Admin UI (selected city, checked names/counts)
- [ ] Verified via API if needed

**After production reload:**

- [ ] Verified production stats and city/venue/source counts
- [ ] Verified target city by name in Admin UI

---

## Scrapers: resolving cities / venues / sources (no hardcoded IDs)

Local SQLite and production PostgreSQL use **different numeric IDs** for the same logical city or venue. Scrapers should **not** assume `city_id`, `venue_id`, or `source_id` from JSON or from a dev machine.

Use **`scripts/scraper_db_lookup.py`**: `resolve_city_by_name`, `resolve_venue_in_city`, `resolve_source_in_city` — natural keys (name, state, website host substrings, name/handle substrings) within the **current** database session.

---

## Recommended Future Improvements

- **Stronger natural-key matching for venues** — Match by `name` + `city_name` (or `website_url`) to avoid cross-city collisions
- **Better duplicate detection** — Pre-reload checks for duplicate names; warnings or blocking
- **Optional sync helper tooling** — Script or CLI to run the workflow steps (backup, validate, reload, verify) with minimal manual steps
