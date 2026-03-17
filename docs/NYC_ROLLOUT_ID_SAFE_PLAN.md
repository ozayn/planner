# NYC Rollout Plan: ID-Safe Approach

**Assumption:** Local (SQLite) and production (PostgreSQL) numeric IDs do not match.  
**Example:** Local New York = city_id 2, Washington = 1; Production New York = 452, Washington = 451.

**Goal:** Roll out NYC data and workflows without relying on stable IDs across environments.

---

## 1. Safe NYC Rollout Approach (No ID Assumptions)

### Core principle

**JSON is the source of truth.** Reload endpoints match entities by **name** (and sometimes URL), not by ID. IDs in JSON are overwritten or ignored during reload.

| Entity | Match key in reload | ID in JSON | Safe? |
|--------|---------------------|------------|-------|
| **Cities** | `name` + `state` + `country` | Key in `cities` object | Ignored for matching; DB assigns new ID for new cities |
| **Venues** | `name` (exact) | Key in `venues` object | Ignored for matching; `city_name` resolves city |
| **Sources** | `name` (exact) | Key in `sources` object | Ignored for matching; `city_id` in JSON mapped via `cities.json` name lookup |

### Rollout flow

1. **Edit JSON files** — Use `city_name: "New York"` for all NYC venues/sources. `city_id` in JSON can stay as `2` (local convention); it is not used for venue matching.
2. **Reload on each environment** — Run `reload-venues-from-json`, `reload-sources`, or `load-all-data` on that environment. Matching is by name; each DB gets its own IDs.
3. **No cross-environment ID use** — Never pass local IDs to production APIs or scripts. Always resolve by name or use IDs from the target environment.

---

## 2. Entities: Match by Name, URL, or Other Natural Keys

| Entity | Prefer | Fallback | Avoid |
|--------|--------|----------|-------|
| **City** | `name` (+ `state`, `country`) | — | `city_id` |
| **Venue** | `name` | `website_url` (for scraper routing) | `venue_id` |
| **Source** | `name` | `url` (for dedup) | `source_id` |
| **Event** | `url` + `venue_id` + `start_date` (+ `start_time`) | `title` + `venue_id` + `start_date` | `event_id` for cross-env |

**For NYC rollout:**

- **Cities:** Match by `name: "New York"`, `state: "New York"`, `country: "United States"`.
- **Venues:** Match by `name` (e.g. `"Metropolitan Museum of Art"`). Ensure names are unique within a city.
- **Sources:** Match by `name` (e.g. `"NYC Arts"`). Reload maps `city_id` via `cities.json` → DB lookup by name.

---

## 3. Risky Scripts, JSON, and Admin Flows When IDs Differ

### Scripts that hardcode IDs (risky for cross-env)

| Script | Hardcoded | Risk |
|--------|-----------|------|
| `update_venue_closure_status.py` | `city_id=1` (implied via DC filter) | Uses `city_name` for DC; **safe** |
| `fix_venue_urls.py` | `city_id=1` | **Risky** — DC-only; fails if run on env where DC ≠ 1 |
| `list_open_museums.py` | `city_id=1` | **Risky** — same as above |
| `cron_scrape_dc.py` | Assumes DC city_id | **Risky** — uses `City.query` by name; verify |
| `scraping_cli.py` | `city_id=1` default | **Risky** — default only; caller can override |
| `test_sf_scraping.py` | `city_id=4` | **Risky** — SF may differ on production |
| `unify_asian_art_museum.py` | `venue_id` 23, 24 | **Risky** — venue IDs differ across envs |
| `sync_monitor.py` | `city_id=1` in API URLs | **Risky** — production may use different ID |
| `check_remote_baby_friendly.py` | `city_id=1` in API URL | **Risky** — same |

### Scripts that use name-based lookup (safe)

- `dcparade_scraper.py` — `City.query.filter(..., City.name.like('%washington%'))`
- `wharf_dc_scraper.py` — `City.query.filter(..., City.name.like('%washington%'))`
- `nyc_real_scraper.py` — `City.query.filter_by(name='New York')`
- `load_nyc_events.py` — `City.query.filter_by(name='New York')`
- `update_production_closure_status.py` — Filters by `city_name` in response
- Reload endpoints — All match by name

### JSON structure risks

| Risk | Mitigation |
|------|------------|
| `city_id` in venues.json | Reload uses `city_name` to resolve city; `city_id` in JSON is overwritten. Keep `city_name` correct. |
| `city_id` in sources.json | Reload maps via `cities.json`: JSON `city_id` → city name → DB city. Ensure `cities.json` has NYC with key `"2"` (or whatever sources reference). |
| Venue/source keys in JSON | Keys are file structure only. Reload matches by `name`. New venues can use any unused key (e.g. 223, 224, 225). |

### Admin flows

- **City dropdown:** Loaded from `GET /api/cities`; IDs come from the current DB. Safe.
- **Venue selection:** Loaded from `GET /api/venues?city_id=X`; `X` is from the same DB. Safe.
- **Scrape buttons:** Call admin APIs that resolve venues/cities by name or by ID from the same request context. Safe as long as no local IDs are passed to production.

---

## 4. Cleanup-and-Addition Plan Using Names/Canonical Records

### Canonical records (name-based)

Treat these as the canonical identifiers. IDs are environment-specific.

**NYC city**

- `name`: `"New York"`
- `state`: `"New York"`
- `country`: `"United States"`
- `timezone`: `"America/New_York"`

**NYC venues (existing)**

| Canonical name | website_url | Notes |
|----------------|-------------|-------|
| American Museum of Natural History | https://www.amnh.org | Add Instagram, description |
| Brooklyn Bridge | (keep) | Non-scrapeable; add `additional_info` |
| Central Park | https://www.centralparknyc.org | Keep as-is |
| Empire State Building | https://www.esbnyc.com | Keep as-is |
| Metropolitan Museum of Art | https://www.metmuseum.org | Add Instagram, description |
| Museum of Modern Art (MoMA) | https://www.moma.org | Keep as-is |
| Statue of Liberty | https://www.nps.gov/stli/index.htm | Keep as-is |
| Times Square | https://www.timessquarenyc.org | Keep as-is |

**NYC venues (to add)**

| Canonical name | website_url |
|----------------|-------------|
| Brooklyn Museum | https://www.brooklynmuseum.org |
| Lincoln Center for the Performing Arts | https://www.lincolncenter.org |
| Brooklyn Academy of Music | https://www.bam.org |

**NYC sources**

- Match by `name`. Ensure `city_id` in JSON points to NYC in `cities.json` (key `"2"`). Reload will map to the correct production `city_id`.

### Cleanup order (name-based, no ID reliance)

1. Backup `venues.json`, `sources.json`, `cities.json`.
2. Edit existing NYC venues by **name** (AMNH, Met, Brooklyn Bridge).
3. Edit Ellis Island source by **name** if a better URL exists.
4. Add new venues by **name** (Brooklyn Museum, Lincoln Center, BAM) with `city_name: "New York"`.
5. Reload on local: `reload-venues-from-json`, `reload-sources` (if sources edited).
6. Verify locally by **city name** (select "New York" in UI).
7. Commit and push JSON.
8. After deploy, reload on production: same endpoints.
9. Verify on production by **city name**.

---

## 5. Recommended First Batch of NYC Actions

### Venue edits (by name)

| Venue name | Fields to update |
|------------|------------------|
| American Museum of Natural History | `instagram_url`, `facebook_url`, `description` |
| Metropolitan Museum of Art | `instagram_url`, `facebook_url`, `twitter_url`, `description` |
| Brooklyn Bridge | `additional_info`: `{"non_scrapeable": true, "reason": "Landmark with no event calendar"}` |

### Source edit (by name)

| Source name | Fields to update |
|-------------|------------------|
| Ellis Island Hard Hat Tours | `url` → schedule/events page if available; else add deprioritization note |

### New venues (by name, `city_name: "New York"`)

| Venue name | venue_type | website_url |
|------------|------------|--------------|
| Brooklyn Museum | museum | https://www.brooklynmuseum.org |
| Lincoln Center for the Performing Arts | arts_center | https://www.lincolncenter.org |
| Brooklyn Academy of Music | arts_center | https://www.bam.org |

---

## 6. Maintainer Rules to Avoid ID Mistakes

### Do

1. **Match by name** — Use `City.query.filter_by(name='New York').first()` (or equivalent) in scripts.
2. **Use `city_name` in JSON** — Always set `city_name: "New York"` for NYC venues. This drives reload matching.
3. **Keep `cities.json` consistent** — NYC must exist with `name: "New York"`. The key (e.g. `"2"`) is used for source `city_id` mapping.
4. **Reload per environment** — Run reload on the environment where you need the data. Each DB gets its own IDs.
5. **Verify by name** — After reload, check that "New York" appears and has the expected venues/sources.
6. **Use API responses for IDs** — When scripting against production, call `GET /api/cities` (or venues) and use returned IDs.

### Don't

1. **Hardcode `city_id` or `venue_id`** in scripts that run across environments.
2. **Assume local IDs = production IDs** — They differ.
3. **Pass local IDs to production APIs** — e.g. `?city_id=2` for NYC on production will be wrong.
4. **Rely on JSON keys as DB IDs** — JSON keys are for file structure; DB assigns IDs on insert.
5. **Skip `city_name`** — Venue reload requires it for city resolution.

### For production scripts

- **Option A:** Resolve city by name: `GET /api/cities` → find `"New York"` → use its `id`.
- **Option B:** Use `load-all-data` or `reload-*` so production DB is populated; then use production IDs from API responses.

---

## 7. Maintainer Checklist (ID-Safe NYC Rollout)

- [ ] Backup `data/venues.json`, `data/sources.json`, `data/cities.json`
- [ ] Confirm NYC exists in `cities.json` with `name: "New York"`, `state: "New York"`, `country: "United States"`
- [ ] Edit venues by **name** (AMNH, Met, Brooklyn Bridge) — do not rely on venue IDs
- [ ] Edit source by **name** (Ellis Island) if better URL exists
- [ ] Add new venues with `city_name: "New York"` — use next available JSON keys (223, 224, 225)
- [ ] Ensure no `city_id` or `venue_id` hardcoding in scripts you will run for NYC
- [ ] Reload locally: `reload-venues-from-json`, `reload-sources` (if needed)
- [ ] Verify locally: select "New York" in UI, confirm 11 venues and 11 sources
- [ ] Commit and push JSON only (no code changes)
- [ ] After deploy, reload on production: `POST /api/admin/reload-venues-from-json`, `reload-sources` if needed
- [ ] Verify on production: select "New York", confirm data
- [ ] Document: local NYC city_id = X, production NYC city_id = Y (for reference only; do not use in scripts)
