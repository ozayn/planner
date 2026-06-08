# Planner scripts

Utility and operational scripts for the Planner app. Shared libraries used by `app.py` stay at **`scripts/`** root; runnable tools are grouped in subdirectories below.

## Directory layout

| Directory | Purpose |
|-----------|---------|
| [`cron/`](cron/) | Scheduled Railway/local cron entrypoints, bucket + schedule config |
| [`scrapers/`](scrapers/) | Venue/source scrapers and scraping orchestration |
| [`migrations/`](migrations/) | Schema migrations, Railway deploy helpers, DB reset |
| [`diagnostics/`](diagnostics/) | Checks, compares, tests, audits, schema validation |
| [`cleanup/`](cleanup/) | Fix/clean/remove stale data, URL fixes, closure cleanup |
| [`admin_tools/`](admin_tools/) | Data enhancement, seeding, monitoring, production tweaks |
| [`one_off/`](one_off/) | Single-use data adds and experiments |
| [`scraper_utils/`](scraper_utils/) | Shared scraper helpers (dates, sessions, proxy) |

## Core modules (stay at `scripts/` root)

Imported by the Flask app and many tools — **do not move without updating `app.py`**:

- `utils.py`, `env_config.py`, `nlp_utils.py`, `venue_types.py`
- `event_database_handler.py`, `generic_crud_generator.py`
- `update_cities_json.py`, `update_venues_json.py`, `update_sources_json.py`, `update_events_json.py`
- `sync_json_to_production.py`, `data_manager.py`, `pre_commit_data_check.py`
- `url_event_scraper.py`, `fetch_venue_details.py`, `hybrid_event_processor.py`, etc.

## Cron entrypoints

**Canonical paths (use these on Railway):**

```bash
python scripts/cron/cron_run_scheduled_scrapers.py      # stable bucket
python scripts/cron/cron_run_protected_scrapers.py        # protected bucket
python scripts/cron/cron_clear_past_events.py
python scripts/cron/cron_scrape_dc.py
```

Shell wrappers: `scripts/cron/run_cron_scrape_museums.sh`, `run_cron_scrape_protected.sh`, `run_cron_scrape.sh`

Config: `scripts/cron/cron_bucket_config.py`, `scripts/cron/cron_scheduler_config.py`

More detail: [`cron/README_CRON.md`](cron/README_CRON.md)

## Production scrapers

All `*_scraper.py` files live under **`scripts/scrapers/`**, including:

- `venue_event_scraper.py`, `generic_venue_scraper.py`, `eventbrite_scraper.py`
- Museum-specific scrapers (NGA, SAAM, NPG, Asian Art, Hirshhorn, etc.)

`app.py` still imports via `scripts.<name>` — thin **compatibility shims** at the old paths re-export from the new locations.

## Migrations

```bash
python scripts/migrations/sync_schema.py
python scripts/migrations/reset_railway_database.py
python scripts/migrations/run_migrations_and_test.py
```

## Diagnostics

```bash
python scripts/diagnostics/schema_validator.py
python scripts/diagnostics/audit_nyc_venues_production.py
python scripts/diagnostics/compare_venue_urls.py
python scripts/diagnostics/database_health.py
```

Pre-commit uses **`scripts/check_duplicates.py`** at the scripts root (not moved).

## Cleanup

```bash
python scripts/cleanup/update_closure_status_open.py
python scripts/cleanup/fix_all_venue_urls.py
python scripts/cleanup/remove_duplicate_venues.py
```

## Backward compatibility

Moved scripts have a **shim file** at the original `scripts/<name>` path that re-exports the module. Old commands and imports keep working; prefer the subdirectory paths for new work.

## Local app

```bash
./scripts/start_local_app.sh
```
