# NYC Implementation Plan

A practical maintainer plan for adding New York City support to Planner within the current architecture. No code changes yet—this is a planning document.

---

## 1. Files, models, and data that need to change

### City setup

- **`data/cities.json`** — NYC already exists (city_id `2`, name `"New York"`, state `"New York"`, timezone `"America/New_York"`). No change required.
- **Database** — City model supports multiple cities. Reload preserves IDs.

### Venues

- **`data/venues.json`** — Add NYC venues with:
  - `city_id`: 2
  - `city_name`: `"New York"` (used for matching; must match cities.json)
  - Same schema as DC venues: name, venue_type, address, website_url, social URLs, etc.
- **Venue model** — No schema change. `city_id` and `city_name` already exist.

### Sources

- **`data/sources.json`** — Add NYC sources with:
  - `city_id`: 2
  - Same schema: name, handle, source_type, url, description, etc.
- **Source model** — No schema change.

### Load/reload flow

- **`POST /api/admin/load-all-data`** or individual reloads:
  - `reload-cities` — No change (NYC already in JSON)
  - `reload-venues-from-json` — Matches venues by `city_name`; will load NYC venues when added
  - `reload-sources` — Will load NYC sources when added

### Admin UI

- **`templates/admin/sections/events.html`** — Add a "New York, NY" section for NYC-specific scrape buttons (when scrapers exist). Optional initially; can rely on Discover flow.
- **`templates/admin/modals/create_from_venue.html`** — Already city-aware; no change.
- **`templates/admin/modals/url_scraper.html`** — Already has city/venue dropdowns; no change.

### Scraper registration (when adding NYC-specific scrapers)

- **`app.py`** — Add new routes like `POST /api/admin/scrape-moma`, etc., and wire to new scraper modules.
- **`scripts/venue_event_scraper.py`** — Add URL/name checks for NYC venues (e.g. `metmuseum.org`, `moma.org`) to route to specialized scrapers, same pattern as NGA/SAAM.

---

## 2. How NYC venues should be added in the current system

### Option A: Edit JSON directly (recommended for bulk)

1. Add entries to `data/venues.json` with `city_id: 2`, `city_name: "New York"`.
2. Use next available venue ID (check current max in metadata or `venues` keys).
3. Run `curl -X POST http://localhost:5001/api/admin/reload-venues-from-json` (local) or production equivalent.
4. Commit and push JSON; after deploy, call reload on production.

### Option B: Add via admin UI

1. Admin → Venues → Add Venue.
2. Select city "New York" from dropdown.
3. Fill in name, type, website, etc.
4. Run `update-all-json` to sync back to JSON, then commit.

### Venue requirements for scraping

- **`website_url`** — Required for venue-based scraping. Generic scraper and specialized scrapers use it.
- **`venue_type`** — Used for filtering in Discover (museum, theater, etc.).
- Avoid `example.com` or placeholder URLs; they are skipped.

### Sources

- Same workflow: add to `data/sources.json` with `city_id: 2`, or add via admin.
- `source_event_scraper` is city-agnostic; it filters by `source_ids` passed from the UI.

---

## 3. Which existing scraping paths can likely be reused

### Fully reusable (no code changes)

| Path | How it works | NYC usage |
|------|--------------|-----------|
| **Venue scrape (Discover)** | `scrape_venue_events(city_id=2)` filters venues by `city_id` | Select NYC, load venues, scrape—works for any city |
| **Generic venue scraper** | Fallback when no specialized scraper matches; URL-agnostic | NYC venues with standard event pages will use it |
| **URL import (From URL)** | `extract_event_data_from_url` + `scrape_event_from_url` | Paste NYC event URLs; generic extraction or LLM fallback |
| **Create from Venue** | Picks venue, then scrapes its website | Works for any venue in DB |
| **Quick Add from URL** | Same as URL import, streamlined UI | Same as above |
| **Source scrape** | `scrape_source_events(source_ids=[...])` | Add NYC Instagram/website sources, scrape by source |
| **Eventbrite** | `scrape_eventbrite_events_for_venue(venue_id)` or `scrape_all_eventbrite_venues(city_id=2)` | Add NYC venues with Eventbrite ticketing URLs |

### DC-only (not reusable for NYC)

| Scraper | Reason |
|---------|--------|
| NGA, SAAM, NPG, Hirshhorn, Asian Art, African Art | Smithsonian museums in DC |
| Wharf DC, DC Parade, Tulip Day | DC-specific venues/events |
| WIT, Suns Cinema, Culture DC | DC venues |
| DC Embassy Eventbrite | DC embassy events |
| Webster's | State College, PA |

### Partially reusable

- **`url_event_scraper`** — Domain-specific branches (SAAM, NPG, NGA, Hirshhorn, OCMA, etc.) are DC/CA-focused. NYC URLs (e.g. metmuseum.org, moma.org) go through generic extraction + LLM fallback. Quality depends on page structure.

---

## 4. Where custom scraper work would plug in if needed

### Venue_event_scraper routing

In `scripts/venue_event_scraper.py`, `_scrape_venue_website()` checks `venue.website_url` and `venue.name`:

- Add `elif` blocks before the generic scraper, e.g.:
  - `'metmuseum.org' in venue_url_lower` → `from scripts.met_scraper import scrape_met_events`
  - `'moma.org' in venue_url_lower` → `from scripts.moma_scraper import scrape_moma_events`
- Follow the NGA/SAAM pattern: call scraper, assign `venue_id` and `city_id` to events, filter by `event_type`/`time_range`, apply limits, return.

### Admin scrape buttons

In `app.py`:

- Add routes like `@app.route('/api/admin/scrape-met', methods=['POST'])`.
- Resolve venue by name or ID (e.g. "Metropolitan Museum of Art"), call scraper, use `event_database_handler.create_events_in_database()`.

In `templates/admin/sections/events.html`:

- Add a "New York, NY" section with buttons that call these new endpoints.

### URL import

In `scripts/url_event_scraper.py`, `extract_event_data_from_url()`:

- Add domain checks for NYC sites (e.g. metmuseum.org, moma.org) if they need custom extraction.
- Otherwise, generic + LLM fallback will handle most URLs.

### Shared ingestion

- All scrapers should use `scripts/event_database_handler.create_events_in_database()`.
- Pass `venue_id` and `city_id` from the venue object.
- Deduplication and validation are centralized there.

---

## 5. Safest phased rollout plan for adding NYC venues

### Phase 1: Data only (no new scrapers)

1. **Add 5–10 NYC venues** to `data/venues.json` (e.g. Met, MoMA, Brooklyn Museum, Lincoln Center, etc.).
2. **Add 2–3 NYC sources** to `data/sources.json` (e.g. NYC-focused Instagram accounts or event sites).
3. **Reload locally**: `reload-venues-from-json`, `reload-sources`.
4. **Verify**:
   - NYC appears in city dropdown.
   - NYC venues load in Discover when NYC is selected.
   - Event list is empty until scraping runs.
5. **Commit and push** JSON; reload on production after deploy.

### Phase 2: Test generic scraping

1. **Use Discover flow**: Select NYC, load venues, run scrape.
2. **Check** which venues return events via generic scraper.
3. **Use Create from Venue** for a few NYC venues.
4. **Use URL import** for a few NYC event URLs.
5. **Document** which venues work, which fail, and why (bot detection, structure, etc.).

### Phase 3: Add 1–2 specialized scrapers (optional)

1. Pick high-value NYC venues with consistent, scrapeable sites (e.g. Met or MoMA).
2. Create `scripts/met_scraper.py` (or similar) following `nga_comprehensive_scraper` or `saam_scraper` pattern.
3. Add routing in `venue_event_scraper._scrape_venue_website()`.
4. Add admin button and route in `app.py` and `events.html`.
5. Test end-to-end: scrape → DB → public UI.

### Phase 4: Expand and stabilize

1. Add more NYC venues based on Phase 2 results.
2. Add more specialized scrapers as needed.
3. Add NYC sources and test source scraping.
4. Update `RECURRING_TOURS_NOTES.md` or similar if NYC has distinct recurring patterns.

---

## 6. Risks for NYC compared with DC

### Scale

- **DC**: ~212 venues, ~56 sources.
- **NYC**: Likely hundreds to thousands of venues.
- **Risk**: Full-city scrape can be slow; timeouts and memory use may increase.
- **Mitigation**: Start with a small set (10–20 venues); use `max_events_per_venue`; consider city-scoped batching or background jobs later.

### Duplicate and overlapping events

- **Risk**: Multiple NYC venues may share platforms (Eventbrite, etc.); same event can appear under different venues.
- **Mitigation**: Rely on `event_database_handler` URL-based deduplication; monitor for duplicates and refine rules if needed.

### Bot detection and blocking

- **Risk**: Major NYC institutions (Met, MoMA, Lincoln Center) may have stricter anti-scraping.
- **Mitigation**: Use `cloudscraper` where applicable; add retries and backoff; use LLM fallback in URL import when scraping fails.

### Generic scraper quality

- **Risk**: NYC museum/venue sites vary; generic scraper may miss events or misparse dates.
- **Mitigation**: Phase 2 testing will show which venues need specialized scrapers; prioritize those for custom logic.

### Recurring tour grouping

- **Risk**: NYC may have different recurring patterns (e.g. daily tours, weekly performances).
- **Mitigation**: Recurring logic is largely title/URL/date-based; test with NYC data and adjust grouping rules if needed.

### Admin UI clutter

- **Risk**: Adding many NYC scrape buttons could overload the Events admin section.
- **Mitigation**: Prefer Discover flow for generic scraping; use admin buttons only for high-value, specialized scrapers. Consider city-filtered or collapsible sections.

### Data consistency

- **Risk**: `city_id` can differ between local and production (e.g. README notes local vs production ID mismatch).
- **Mitigation**: Use `city_name` for matching in reload; avoid hardcoding `city_id` in scripts; use venue/city resolution from DB.

---

## Summary checklist

- [ ] NYC exists in `cities.json` (already done)
- [ ] Add NYC venues to `venues.json` with `city_id: 2`, `city_name: "New York"`
- [ ] Add NYC sources to `sources.json` with `city_id: 2`
- [ ] Reload venues and sources (local, then production)
- [ ] Test Discover flow: select NYC, load venues, scrape
- [ ] Test URL import and Create from Venue for NYC
- [ ] Document which venues work with generic scraper
- [ ] Add specialized scrapers only where needed
- [ ] Add admin scrape buttons only for new specialized scrapers
- [ ] Monitor scale, performance, and duplicates as NYC data grows
