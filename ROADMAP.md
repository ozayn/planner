# Planner Roadmap

This roadmap is a practical maintainer guide for the Planner project. It reflects the current codebase state and analysis done in 2025. Use it to prioritize work, avoid regressions, and keep the system maintainable.

---

## Product understanding from the current UI

The current screenshots and UI suggest that Planner is not just an events app. It is a **two-sided system** with three core product layers:

### 1. Public event planning UI

- Clean, minimal, schedule-first browsing
- Time/type filtering
- Recurring tours grouped into a compressed top section
- Checkbox-based event selection and quick actions

### 2. Discovery and scraping control UI

- Left-side Discover drawer acts as a control center
- City, venue type, platform, content, price, event type, and time controls
- Venue/source selection tied directly to scraping and loading
- Result count and scrape workflow integrated into browsing

### 3. Admin operations console

- Event CRUD
- URL import
- Venue-based event creation
- Source-specific scraping buttons
- Bulk deletion/export actions
- Oversight of cities, venues, sources, and events

The roadmap should preserve and strengthen these three workflows. Changes to one layer should not inadvertently break another.

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

- **Confirm that the admin Events page still works correctly** after auth changes
  - Test: load `/admin`, switch sections (Overview, Cities, Venues, Events, Sources), add/edit city, add/edit venue, create event from URL, run a scrape
  - The fetch wrapper in `static/js/admin/core.js` redirects to `/auth/login` on 401; verify this works when session expires

- **Investigate missing `PUT /api/admin/venues/<id>`** references used by some scripts
  - `scripts/update_production_closure_status.py` and `scripts/update_newseum_production.py` call `PUT /api/admin/venues/{venue_id}`
  - app.py defines `POST /api/admin/edit-venue` but no `PUT /api/admin/venues/<id>`
  - Either add the PUT route or update the scripts to use `POST /api/admin/edit-venue`

- **Create a short maintainer note** for the current public UI and admin UI workflows

---

## 2. Public UI recommendations

The public interface is the primary user-facing surface. Preserve the clean schedule-first browsing experience.

**Document the main user flow:**

1. Choose city
2. Load venues
3. Optionally scrape/select sources
4. Browse events
5. Select events
6. Export/use quick actions

**Recommended follow-up work:**

- Create a dedicated note for right-pane event list behavior
- Document how recurring tours are built, displayed, collapsed, and expanded
- Review event-card information hierarchy:
  - time
  - title
  - venue
  - type
  - image
  - action buttons
- Review action clarity on event cards, especially subtle right-side controls
- Review selection behavior so users always understand what is selected
- Make recurring-tour grouping a documented first-class feature
- Add a regression checklist specifically for the public browse experience

---

## 3. Discover drawer and control-panel recommendations

The Discover drawer is a major product surface, not just a filter sidebar. Treat it as the control center for discovery and scraping.

**Document each section and its purpose:**

- city
- discovery options
- venue types
- platforms
- content
- price
- events
- event type
- when
- max events per venue
- selection
- venues/sources tab area

**Clarify the difference between:**

- Filtering already-loaded events
- Selecting venues/sources
- Triggering scraping/loading

**Make state transitions easier to maintain.**

**Recommended follow-up work:**

- Create a state-flow map for the left drawer
- Document how the drawer controls the right pane
- Review the venue/source selection panel as its own subsystem
- Add notes on which controls affect data load versus display-only filtering
- Add UX guardrails so scrape/load actions are not confused with passive filtering

---

## 4. Recurring tours as a signature feature

Recurring tours appear to be one of Planner's distinctive strengths.

- Document why recurring tours are grouped separately
- Review grouping logic for accuracy and maintainability
- Ensure grouped tours remain understandable to users

**Recommended follow-up work:**

- Create `RECURRING_TOURS_NOTES.md`
- Document:
  - how recurring tours are identified
  - how sessions are counted
  - how venue tabs inside recurring tours work
  - how grouped tours relate to underlying event rows
- Add regression checks for recurring-tour rendering and grouping

---

## 5. Admin UI recommendations

The Events admin screen is the operational hub, not just CRUD.

**Daily admin tasks:**

- Search and filter events
- Create event manually
- Create from URL
- Create from venue
- Upload event image
- Run source scrapers
- Quick add from URL
- Delete past events
- Bulk delete/export

**Also include:**

- Clearly separate safe actions from destructive actions in documentation
- Review the Events screen for operational overload and error risk

**Recommended follow-up work:**

- Create `ADMIN_EVENTS_WORKFLOW.md`
- Mark which buttons:
  - create data
  - update data
  - delete data
  - trigger scraping
  - sync or export data
- Add a maintainer checklist before running destructive or bulk operations
- Add better status/feedback handling for scrape buttons and quick-create flows

---

## 6. URL import recommendations

Make URL import a first-class roadmap area.

**Document the difference between:**

- From URL
- Quick Add from URL
- From Venue

**Review validation and feedback for URL import.** Make failures easier to diagnose from the UI.

**Recommended follow-up work:**

- Create `URL_IMPORT_NOTES.md`
- Document:
  - extract phase
  - preview/edit phase
  - scrape/create phase
  - LLM fallback
  - dedup/update rules
- Add a list of common URL types and their expected paths
- Add error/debug output guidance for failed URL imports

---

## 7. Scraping and ingestion stability

Scraping is exposed directly in both admin and discovery workflows.

- Document all user-visible scraping entry points
- Separate the most important paths:
  - public scrape flow from discovery
  - admin source-specific scrapers
  - URL import
  - venue-based creation
- Identify fragile source-specific buttons and special-case scrapers

**Recommended follow-up work:**

- Create `SCRAPING_OPERATIONS.md`
- For each source button, note:
  - scraper used
  - output path
  - dedup path
  - common failure modes
- Add a maintainer debugging checklist for:
  - no events found
  - duplicates
  - wrong venue assignment
  - partial scrape results
  - recurring-tour over-grouping

---

## 8. Visual and interaction consistency

Preserve the current visual identity:

- Minimal, quiet, whitespace-heavy, rounded, soft-border design
- Preserve the restrained visual language across future changes
- Make sure new controls fit the same design system
- Avoid cluttering already dense admin workflows
- Avoid breaking the calm scanning experience in the public event list

**Recommended follow-up work:**

- Create a short UI principles note covering:
  - minimal
  - schedule-first
  - soft emphasis
  - operational clarity without clutter
- Review button prominence where risky actions are visually similar to safe ones
- Ensure destructive actions are clearer in admin without making the interface noisy

---

## 9. Testing and regression checks

Expand testing to reflect the actual UI flows.

**Public UI smoke tests:**

- Page loads correctly
- City selection works
- Left drawer opens/closes correctly
- Venues load correctly
- Scrape/load actions update results
- Recurring tours render correctly
- Date-grouped event list renders correctly
- Event selection works
- Quick event actions work

**Admin UI smoke tests:**

- Admin loads correctly
- Overview counts load
- Events tab loads
- Filters work
- From URL opens and completes expected flow
- Quick Add works
- Scrape buttons return usable feedback
- Delete past events behaves correctly
- Bulk action buttons behave correctly
- Auth failure returns proper redirect or error state

---

## 10. Documentation updates

Expand the documentation roadmap to include these recommended documents:

- `ROADMAP.md` — this file
- `MAINTAINER_NOTES.md`
- `ADMIN_EVENTS_WORKFLOW.md`
- `PUBLIC_UI_WORKFLOW.md`
- `URL_IMPORT_NOTES.md`
- `SCRAPING_OPERATIONS.md`
- `RECURRING_TOURS_NOTES.md`
- `DATA_SYNC_NOTES.md`

**Also include:**

- Document local startup, production startup, and deploy/reset behavior
- Document common debugging commands and operational scripts
- Keep security notes close to auth/config documentation

---

## 11. Suggested order of work

1. Verify admin API protection outside localhost
2. Document the Events admin workflow
3. Document the Discover drawer and public browse flow
4. Document recurring tours as a dedicated feature
5. Stabilize URL import notes and debugging guidance
6. Add smoke tests for public and admin flows
7. Review DB/JSON/source-of-truth inconsistencies
8. Gradually reduce complexity in `app.py` and `templates/index.html`

---

## Additional reference areas

These sections remain relevant for maintainers but are not part of the core suggested order above.

### Security and admin hardening

- **Protect all `/api/admin/*` routes consistently** — Done: `before_request` in app.py returns 401 for unauthenticated `/api/admin/*` requests
- **Review localhost and "OAuth unavailable" bypasses** — `_is_admin_authenticated()` bypasses when: (1) host is localhost/127.0.0.1/10.*, or (2) `GOOGLE_OAUTH_AVAILABLE` is False
- **Remove unsafe production defaults** — e.g. fallback `SECRET_KEY` in app.py
- **Review CSRF assumptions** — `WTF_CSRF_ENABLED = False`; admin routes use `@csrf.exempt`
- **Document the intended auth model** for local vs production

### Data model and sync cleanup

- **Clarify source of truth for each entity**
  - Cities: `data/cities.json` → DB via reload; JSON is source of truth
  - Venues: `data/venues.json` → DB via reload; JSON is source of truth
  - Sources: `data/sources.json` → DB via reload; JSON is source of truth
  - Events: DB only; no JSON source of truth
- **Resolve DB vs JSON inconsistencies**, especially around `/api/sources`
- **Review production reset/load workflow** — `POST /api/admin/load-all-data`, when to use load-all-data vs reload-* individually

### Possible future refactors

- **Reduce `app.py` responsibility** — Extract route groups into blueprints or separate modules
- **Reduce `templates/index.html` size** — Extract sections into partials; move inline JS to external files
- **Move shared auth checks** into a clearer structure — e.g. `auth.py` or `admin_auth.py`
- **Standardize ingestion paths** across scrapers
- **Make admin API patterns more consistent** — Response format, naming, error codes
