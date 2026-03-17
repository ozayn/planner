# Add + Fully Wire Up Venue/Source — Reusable Template

**Use this template when adding a new venue and/or source to the Planner.** Fill in the placeholders and follow all steps.

---

## Input Template

```
Add this to Planner and fully wire it up:

City: CITY_NAME (JSON ID: CITY_JSON_ID)

Venue:
- name:
- type:
- website:
- address:
- description:

Source:
- name:
- type:
- url:
- handle:
- description:
- event_types: []

Do all:
- add/update venue
- add/update source
- add scraper if needed
- add admin button
- add to scheduled cron flow
- reuse existing repo patterns
- normalize to canonical event_type categories
- avoid duplicate records
```

---

## Canonical Event Types

Map scraped categories to these repo values:

| Canonical | Use for |
|-----------|---------|
| `exhibition` | Art exhibitions, shows |
| `tour` | Guided tours, walkthroughs |
| `talk` | Lectures, artist talks, conversations, readings |
| `workshop` | Hands-on workshops, classes |
| `film` | Screenings, film events |
| `music` | Concerts, performances |
| `event` | General events, special programs |
| `festival` | Festivals |
| `photowalk` | Photography walks |
| `improv` | Improv, comedy |

---

## Implementation Checklist

### 1. Venue
- **File:** `data/venues.json`
- **Convention:** Match existing structure (city_id, city_name, venue_type, etc.)
- **If exists:** Update fields; do not create duplicate
- **ID:** Use next available or match by name/website

### 2. Source
- **File:** `data/sources.json`
- **Convention:** Match existing structure (handle, source_type, url, event_types as JSON string)
- **If exists:** Update fields; do not create duplicate
- **event_types:** Store as JSON string, e.g. `"[\"art_exhibitions\", \"museum_events\", \"lectures\"]"`

### 3. Scraper
- **Inspect first:** Check `scripts/source_event_scraper.py`, `scripts/venue_event_scraper.py`, `scripts/generic_venue_scraper.py`
- **Prefer:** Source scraper if source URL is the listing page; venue scraper if venue homepage has built-in logic
- **Pattern:** Create `scripts/{name}_scraper.py` (e.g. `deyoung_scraper.py`, `hammer_scraper.py`)
- **Wire:** Add branch in `source_event_scraper._scrape_website_source()` or `venue_event_scraper` routing
- **Entry point:** `scrape_all_{name}_events()` returning list of event dicts

### 4. Admin Button
- **File:** `templates/admin/sections/events.html`
- **Location:** Add to city section (DC, NYC, LA, SF, Other) or create new section
- **Style:** Use `add-button scraper-btn` with distinct background color
- **Handler:** `start{Name}Scraping()` in `static/js/admin/init.js`

### 5. API Endpoint
- **File:** `app.py`
- **Route:** `POST /api/admin/scrape-{name}`
- **Pattern:** Reuse Hammer/OCMA pattern: find venue, call scraper, `shared_create_events`, return JSON

### 6. Cron Flow
- **File:** `scripts/cron_run_scheduled_scrapers.py`
- **Placement:** Add block after similar scrapers (e.g. Hammer, OCMA)
- **Seasonal:** Use `get_venue_schedule_rule` / `should_run` if seasonal
- **Always-run:** Add as standalone block with try/except

---

## Output Summary (Report After Editing)

After making changes, report:

1. **Files changed** — List all modified/created files
2. **Venue record** — Exact JSON added/updated (or "unchanged")
3. **Source record** — Exact JSON added/updated (or "unchanged")
4. **Scraper status** — New / reused / none
5. **Admin button location** — Section + button name
6. **Scheduled-flow location** — File + placement
7. **Reload commands** — Exact commands to sync data
8. **Manual test steps** — Admin button, cron, scraper CLI
9. **Assumptions/limitations** — What the first version does not cover

---

## Reference: Existing Patterns

| Venue/Source | Scraper | Admin Endpoint | Cron |
|--------------|---------|----------------|------|
| Hammer Museum | `hammer_scraper.py` | `/api/admin/scrape-hammer` | Always |
| OCMA | Built-in in `venue_event_scraper` | `/api/admin/scrape-ocma` | Always |
| de Young | `deyoung_scraper.py` | `/api/admin/scrape-deyoung` | Always |
| Shoot NYC | `shoot_nyc_scraper.py` | (via sources) | Always |
| Tulip Day | `tulipday_scraper.py` | `/api/admin/scrape-tulipday` | Seasonal (Mar–Apr) |
| DC Parade | `dcparade_scraper.py` | (via sources) | Seasonal (Jan–Feb) |

---

## Quick Reference: Key Paths

- Venues: `data/venues.json`
- Sources: `data/sources.json`
- Source scraper routing: `scripts/source_event_scraper.py` → `_scrape_website_source`
- Venue scraper routing: `scripts/venue_event_scraper.py` → `has_specialized_scraper`, standard methods
- Admin events template: `templates/admin/sections/events.html`
- Admin JS handlers: `static/js/admin/init.js`
- Cron: `scripts/cron_run_scheduled_scrapers.py`
- Event DB handler: `scripts/event_database_handler.py` → `create_events_in_database`
