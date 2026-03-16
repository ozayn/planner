# Planner Roadmap

This roadmap is a practical maintainer guide for the Event Planner project. It reflects the current codebase state and analysis done in 2025. Use it to prioritize work, avoid regressions, and keep the system maintainable.

---

## 1. Immediate priorities

- **Verify the admin API protection change** in a non-local or temporary test setup
  - The `before_request` guard for `/api/admin/*` returns 401 when unauthenticated on production
  - Localhost bypasses auth; temporarily comment out the `is_local` block in `_is_admin_authenticated()` (app.py ~1008–1009) to test 401 locally
  - Use `curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/admin/stats` to verify 401 without browser redirects

- **Document which production scripts now require authenticated access**
  - Scripts that call production admin APIs will get 401 without session cookies:
    - `load_production_data.sh` — `POST /api/admin/load-all-data`, `GET /api/admin/stats`
    - `commit_and_reload_venues.sh` — `POST /api/admin/load-all-data`
    - `update_production_cities.sh`, `update_production_db_now.sh` — cities CRUD
    - `verify_production_cities.sh` — `GET /api/admin/cities`
    - `scripts/update_production_closure_status.py` — venues GET/PUT
    - `scripts/update_newseum_production.py` — venues GET/PUT
    - `scripts/check_remote_baby_friendly.py`, `scripts/compare_venue_urls.py`, `scripts/compare_event_schema.py` — read-only
    - `fix_and_reload_venues.py`, `test_venue_loading.py` — load-all-data, stats
  - Add a short note in README or `docs/ADMIN_API_NOTES.md` about cookie-based auth for these scripts

- **Confirm whether any admin flows broke** after the auth guard change
  - Test: load `/admin`, switch sections (Overview, Cities, Venues, Events, Sources), add/edit city, add/edit venue, create event from URL, run a scrape
  - The fetch wrapper in `static/js/admin/core.js` redirects to `/auth/login` on 401; verify this works when session expires

- **Investigate missing `PUT /api/admin/venues/<id>`** references used by some scripts
  - `scripts/update_production_closure_status.py` and `scripts/update_newseum_production.py` call `PUT /api/admin/venues/{venue_id}`
  - app.py defines `POST /api/admin/edit-venue` but no `PUT /api/admin/venues/<id>`
  - Either add the PUT route or update the scripts to use `POST /api/admin/edit-venue`

---

## 2. Security and admin hardening

- **Protect all `/api/admin/*` routes consistently**
  - Done: `before_request` in app.py returns 401 for unauthenticated `/api/admin/*` requests
  - Only `/admin` and `POST /api/admin/migrate-schema` had `@login_required` before; now all admin API routes are guarded

- **Review localhost and “OAuth unavailable” bypasses** and decide what should remain long-term
  - `_is_admin_authenticated()` bypasses when: (1) host is localhost/127.0.0.1/10.*, or (2) `GOOGLE_OAUTH_AVAILABLE` is False
  - Localhost bypass is useful for dev; OAuth-unavailable bypass effectively disables auth when Google libs are missing
  - Consider: require explicit env flag (e.g. `DISABLE_ADMIN_AUTH=true`) for local dev instead of implicit localhost detection

- **Remove unsafe production defaults** like fallback `SECRET_KEY`
  - app.py line 142: `SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')`
  - In production, fail startup if SECRET_KEY is missing or equals the dev default

- **Review CSRF assumptions** for admin actions
  - `WTF_CSRF_ENABLED = False`; admin routes use `@csrf.exempt`
  - Document why CSRF is disabled and whether session cookies are sufficient for same-origin admin

- **Document the intended auth model** for local vs production
  - Local: localhost bypass, optional OAuth
  - Production: Google OAuth, `ADMIN_EMAILS` whitelist, session cookies
  - Add to `docs/` or `MAINTAINER_NOTES.md`

---

## 3. Data model and sync cleanup

- **Clarify source of truth for each entity**
  - **Cities**: `data/cities.json` → DB via reload; JSON is source of truth
  - **Venues**: `data/venues.json` → DB via reload; JSON is source of truth
  - **Sources**: `data/sources.json` → DB via reload; JSON is source of truth
  - **Events**: DB only; no JSON source of truth; events come from scraping and manual creation

- **Resolve DB vs JSON inconsistencies**, especially around `/api/sources`
  - Public `GET /api/sources` vs admin `GET /api/admin/sources` — document which is used where
  - Ensure sources JSON format matches what reload scripts expect

- **Review production reset/load workflow** for possible drift
  - `POST /api/admin/load-all-data` loads cities, venues, sources from JSON
  - Used after deploy when DB is empty; preserves IDs when updating existing rows
  - Document: when to use load-all-data vs reload-* individually

- **Verify JSON formats** are consistent with load scripts
  - `data/cities.json`, `data/venues.json`, `data/sources.json` — structure documented in README and `docs/data/`
  - Venues use `city_name` for matching; cities use name/state/country

- **Create maintainer notes** for how to safely edit and sync data
  - Add city: edit JSON → reload-cities → commit
  - Edit in production: update-all-json → export → commit
  - See README “Adding a New City” and “Syncing Production Changes Back to JSON”

---

## 4. Scraping and ingestion stability

- **Document the main ingestion path**
  - **Admin-triggered scrapes**: `POST /api/admin/scrape-*` (Hirshhorn, NGA, SAAM, NPG, etc.) → app.py handlers → `scripts/venue_event_scraper.py` or specialized scrapers
  - **Streaming scrape**: `POST /api/scrape-stream` — used for long-running scrapes with progress
  - **Legacy**: `POST /api/scrape` — older bulk scrape
  - **URL import**: `POST /api/admin/extract-event-from-url` + `scrape-event-from-url` → `scripts/url_event_scraper.py`
  - **Shared DB write**: `scripts/event_database_handler.py` — `create_events_in_database()` used by dcparade_scraper, saam_scraper, etc.

- **Review scraper exceptions and special-case ingestion paths**
  - `scripts/venue_event_scraper.py` — main orchestrator; selects scraper by venue/URL
  - Specialized: `scripts/saam_scraper.py`, `scripts/npg_scraper.py`, `scripts/nga_comprehensive_scraper.py`, `scripts/nga_finding_awe_scraper.py`, `scripts/wharf_dc_scraper.py`, `scripts/websters_scraper.py`, etc.
  - `scripts/url_event_scraper.py` — URL-based extraction with domain-specific branches (SAAM, NPG, OCMA, NGA, Finding Awe, Hirshhorn, etc.)

- **Identify venues with fragile or custom logic**
  - OCMA, Hirshhorn, NGA, SAAM, NPG, Webster’s, Wharf DC, DC Parade, Tulip Day, WIT, Suns Cinema, Culture DC, African Art, Asian Art — each has custom extraction
  - Generic scraper is fallback when no specialized scraper matches

- **Compare shared ingestion logic** with special-case scrapers like Webster’s
  - Webster’s uses `scripts/websters_scraper.py` with direct DB writes
  - Others use `event_database_handler` or venue_event_scraper
  - Standardize where possible to reduce drift

- **Add a debugging checklist** for missing, duplicate, or misassigned events
  - Missing: check scraper logs, venue URL, bot detection, date parsing
  - Duplicate: check URL normalization, deduplication in `scrape_event_from_url` and `event_database_handler`
  - Misassigned: check venue_id, city_id, `is_category_heading` filter

---

## 5. URL import feature improvement

- **Document the full “event from URL” flow**
  - Entry: `POST /api/admin/extract-event-from-url` (preview) and `POST /api/admin/scrape-event-from-url` (create)
  - Core: `scripts/url_event_scraper.py` — `extract_event_data_from_url()`, `scrape_event_from_url()`
  - Domain routing: Instagram, Tulip Day, SAAM, NPG, OCMA, Finding Awe, Hirshhorn, NGA, generic
  - Generic path: cloudscraper → BeautifulSoup → `_extract_*` helpers; LLM fallback on bot detection or exception
  - See prior analysis in this conversation for full flow

- **Review generic extraction quality**
  - Helpers: `_extract_title`, `_extract_description`, `_extract_schedule`, `_extract_date`, `_extract_images`, `_extract_meeting_point`, `_extract_time_from_event_date_field`, `_extract_time_from_json_ld`, `_extract_registration_url`
  - Drupal-style pages get extra handling for date fields and JSON-LD

- **Review LLM fallback triggers** and cost/quality tradeoffs
  - Triggered when: bot detection (“Pardon Our Interruption”, “Access Denied”) after 3 attempts, or any exception in generic scraper
  - `scripts/llm_url_extractor.py` → `extract_event_with_llm()` → `EnhancedLLMFallback`
  - Instagram uses LLM first (scraping is fallback)

- **Identify the most common URL types** used in practice and where extraction fails
  - Add logging or admin feedback for extraction failures
  - Track which domains return empty or low-quality data

- **Make URL import easier to debug** from the admin UI
  - Show extraction source (scraper vs LLM) in preview
  - Optionally log failed extractions for review

---

## 6. Frontend maintainability

- **Document `templates/index.html`** as the main user-facing page
  - Large file (~8700+ lines); contains city selection, event list, filters, wizard, calendar export
  - Primary entry for public event browsing

- **Identify the highest-risk UI logic**
  - **City selection**: localStorage, dropdown, affects all downstream data
  - **Wizard completion**: onboarding flow, city/venue selection
  - **Event rendering**: event cards, dates, times, types
  - **Filtering**: event type, venue, date range

- **Gradually separate critical UX logic** from giant embedded blocks
  - Move inline scripts to `static/js/` modules where feasible
  - Keep changes incremental to avoid regressions

- **Add notes for how event data flows** from backend to UI
  - `GET /api/events?city_id=&time_range=` → event list
  - `GET /api/venues?city_id=` → venue dropdown
  - `GET /api/cities` → city list
  - Document in `docs/` or `MAINTAINER_NOTES.md`

---

## 7. Admin maintainability

- **Document the main admin workflows**
  - **Add/edit city**: Add City modal → `POST /api/admin/add-city`, Edit → `POST /api/admin/edit-city`
  - **Add/edit venue**: Add Venue modal → `POST /api/admin/add-venue`, Edit → `POST /api/admin/edit-venue`
  - **Create event from URL**: URL Scraper modal → extract-event-from-url → scrape-event-from-url
  - **Create event from venue**: Create from Venue modal → `POST /api/admin/create-event-from-venue`
  - **Scrape source**: Per-source buttons in Events section → `POST /api/admin/scrape-*`
  - **Sync JSON**: Manage venues.json, Export from DB, update-all-json, reload-*

- **Mark destructive routes and actions clearly**
  - `POST /api/admin/clear-events`, `clear-past-events`, `clear-venues`
  - `DELETE /api/admin/cities/<id>`
  - `POST /api/admin/load-all-data`, `reload-*` (overwrite DB from JSON)
  - Add warnings in admin UI or docs

- **Add a small shared fetch/error handling layer** for admin JS
  - `static/js/admin/core.js` has a fetch wrapper for 401 → redirect
  - Consider: shared `adminFetch()` that handles 401, 500, network errors consistently
  - Keep minimal; avoid large refactor

- **Create a maintainer checklist** before running destructive actions
  - Backup DB or export JSON before clear/reload
  - Verify you have the right environment (local vs production)
  - Document in `MAINTAINER_NOTES.md`

---

## 8. Testing and regression checks

- **Add lightweight manual regression checks** for:
  - Public event browsing: load `/`, select city, see events
  - Admin loading: load `/admin`, see Overview stats, switch sections
  - URL import: paste URL, Auto-Fill, create event
  - Venue scrape: run one scrape (e.g. Hirshhorn), verify events created
  - JSON sync: reload-cities, verify counts

- **Add a small professional testing mechanism** for critical routes and flows
  - Consider pytest + requests for API smoke tests
  - Or a simple shell script that curls key endpoints and checks status codes

- **Start with smoke tests** rather than broad full coverage
  - `GET /`, `GET /admin`, `GET /api/admin/stats`, `GET /api/events`
  - One scrape, one URL import

- **Track known fragile behaviors** and test those first
  - Date parsing in scrapers (see `SCRAPER_DATE_TIME_ISSUES.md`)
  - OCMA, Hirshhorn extraction
  - Bot detection and LLM fallback

---

## 9. Documentation

- **Create or maintain**
  - `MAINTAINER_NOTES.md` — operational notes, common tasks, debugging
  - `ROADMAP.md` — this file
  - `ADMIN_API_NOTES.md` — admin routes, auth, scripts that need auth
  - `DATA_SYNC_NOTES.md` — JSON ↔ DB workflow, when to reload, when to update

- **Document local startup, production startup, and deploy/reset behavior**
  - Local: `source venv/bin/activate && python app.py` or `./restart_local.sh` (port 5001)
  - Production: Railway, Procfile uses gunicorn; `load-all-data` after deploy if DB empty
  - Reset: clear-* endpoints, then load-all-data or reload-*

- **Document common debugging commands** and operational scripts
  - `curl http://localhost:5001/api/admin/stats`
  - `curl -X POST http://localhost:5001/api/admin/reload-cities`
  - Scripts in `scripts/` for data fixes, schema migrations

- **Keep security notes** close to auth/config documentation
  - `docs/SECURITY_CHECKLIST.md` exists
  - Add admin auth model, env vars (SECRET_KEY, GOOGLE_CLIENT_*, ADMIN_EMAILS)

---

## 10. Possible future refactors

- **Reduce `app.py` responsibility** over time
  - app.py is very large (~10k lines); routes, models, business logic mixed
  - Extract route groups into blueprints or separate modules
  - Move scraper orchestration into dedicated modules

- **Reduce `templates/index.html` size** over time
  - Extract sections into partials
  - Move inline JS to external files
  - Do incrementally to avoid breaking changes

- **Move shared auth checks** into a clearer structure
  - `_is_admin_authenticated()` is a start
  - Consider a small `auth.py` or `admin_auth.py` module

- **Standardize ingestion paths** across scrapers
  - All scrapers → `event_database_handler.create_events_in_database()` or equivalent
  - Consistent deduplication, validation, error handling

- **Make admin API patterns more consistent**
  - Response format (success, error, data)
  - Naming (edit-venue vs PUT /venues/id)
  - Error codes and messages

---

## Suggested order of work

1. **Immediate (this week)**
   - Verify admin API 401 behavior (temporary local test)
   - Document production scripts that need auth
   - Investigate `PUT /api/admin/venues/<id>` and fix scripts or add route

2. **Short term (next 2–4 weeks)**
   - Create `ADMIN_API_NOTES.md` and `DATA_SYNC_NOTES.md`
   - Add maintainer checklist for destructive actions
   - Review and document auth bypass behavior for local vs production

3. **Medium term (1–2 months)**
   - Add smoke test script or minimal pytest suite
   - Document URL import flow and extraction failure points
   - Create debugging checklist for scraping issues

4. **Longer term (as capacity allows)**
   - Extract app.py routes into blueprints
   - Reduce index.html size
   - Standardize scraper → DB ingestion path
