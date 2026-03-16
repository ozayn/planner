# No Past Events: Implementation Recommendation

**Status:** Implemented (March 2025)  
**Date:** March 2025

---

## 1. Best Shared Place to Enforce the Rule

**Primary location: `scripts/event_database_handler.py`**

The shared handler `create_events_in_database()` is the single choke point for almost all scrapers:

- Museum scrapers (NGA, SAAM, NPG, Asian Art, African Art)
- Source scrapers (Shoot NYC, Wharf DC, DC Parade, Webster’s)
- Venue event scraper (via app.py scrape-stream)
- Source event scraper (via app.py scrape-stream)
- Generic venue scraper (via app.py scrape-from-venue)
- Tulip Day, WIT Eventbrite, Webster’s, etc.
- Cron scrape (`cron_run_scheduled_scrapers.py`)

Adding the rule here ensures it applies to all these flows without touching each scraper.

---

## 2. Where to Implement: Scraper vs Shared Ingestion vs Both

**Implement in the shared ingestion path only.**

| Approach | Pros | Cons |
|----------|------|------|
| **Per-scraper** | Scrapers can skip past events earlier | Duplicated logic, easy to miss scrapers, inconsistent behavior |
| **Shared ingestion only** | Single place, consistent, easy to maintain | Past events still extracted and sent to handler |
| **Both** | Defense in depth | Redundant, more maintenance, risk of divergence |

**Recommendation:** Implement only in `create_events_in_database()`. Scraper-level filtering (e.g. `generic_venue_scraper._is_in_time_range`) can stay for performance, but the shared handler is the authoritative enforcement point.

---

## 3. Exceptions to Allow

| Exception | Rationale | How to Handle |
|-----------|-----------|---------------|
| **Ongoing exhibitions** | No `start_date`; `handle_ongoing_exhibition_dates()` sets `start_date=today`, `end_date=2 years` | Already handled; they pass the “no past” check |
| **Multi-day events** | Event may have started in the past but still runs today | Keep if `end_date >= today` |
| **Archival / backfill** | Intentional import of historical events | Add `skip_past_events=False` parameter for these flows |
| **URL import** | User chooses date range; custom range may include past dates | Do not filter; user intent overrides |
| **Existing event updates** | Updating a past event (e.g. description) | Allow updates; only skip *creating* new past events |

---

## 4. Safest Minimal Implementation Plan

### Phase 1: Add helper and parameter (event_database_handler.py)

1. Add `is_event_past(event_data: Dict) -> bool`:

   ```python
   def is_event_past(event_data: Dict) -> bool:
       """
       Return True if event is entirely in the past (should not be saved).
       Multi-day events: keep if end_date >= today.
       Single-day: keep if start_date >= today.
       """
       today = date.today()
       start_date = event_data.get('start_date')
       end_date = event_data.get('end_date')
       
       if not start_date:
           return False  # No date = not past (ongoing will get dates)
       
       # Normalize string dates to date objects
       if isinstance(start_date, str):
           start_date = parse_date(start_date)
       if isinstance(end_date, str):
           end_date = parse_date(end_date)
       
       # Multi-day: event still current if it ends today or later
       if end_date and end_date >= today:
           return False
       
       # Single-day or past multi-day: check start_date
       return start_date < today
   ```

2. Add `skip_past_events: bool = True` to `create_events_in_database()`.

3. Insert the check **after** `handle_ongoing_exhibition_dates()` and **before** baby-friendly detection:

   ```python
   if skip_past_events and is_event_past(event_data):
       skipped_count += 1
       logger_instance.debug(f"   ⏭️ Skipping past event: '{title}' (start: {start_date}, end: {end_date})")
       continue
   ```

### Phase 2: Existing event updates

- **Do not** skip when `existing` is found. The handler already updates existing events; past events can be updated (e.g. description, URL).
- Only skip when creating **new** events. The current flow already separates create vs update, so no change needed.

### Phase 3: Flows that bypass the shared handler

| Flow | Action |
|------|--------|
| **URL import** (`scripts/url_event_scraper.py`) | No change. User-driven; date range is explicit. |
| **save_event_to_database** (app.py) | Unused; no change. |
| **Direct Event creation** elsewhere | Audit for any other bypasses; if found, either route through the handler or add the same check. |

### Phase 4: Optional backfill override

- For archival/backfill scripts, call `create_events_in_database(..., skip_past_events=False)`.
- Document this in the handler docstring and in any backfill scripts.

---

## 5. Avoiding Breakage: Ongoing Exhibitions and Multi-Day Events

### Ongoing exhibitions

- Flow: no `start_date` → `handle_ongoing_exhibition_dates()` runs first → sets `start_date=today`, `end_date=2 years`.
- The past-event check runs **after** this, so these events have `start_date >= today` and are not skipped.

### Multi-day events

- Rule: keep if `end_date >= today` (event still running).
- Single-day: keep if `start_date >= today`.
- Edge case: `end_date` missing → treat as single-day and use `start_date >= today`.

### Date normalization

- `start_date` / `end_date` may be `date` objects or `"YYYY-MM-DD"` strings.
- `is_event_past()` must normalize both before comparing to `today`.

---

## 6. Practical Maintainer Recommendation

1. **Single source of truth:** All “no past events” logic lives in `event_database_handler.py`. Scrapers do not implement their own past-event filtering for correctness; they may still filter for performance (e.g. time_range).

2. **Document the rule:** Add a short section to the handler module docstring and to any scraper/ingestion docs describing the rule and exceptions.

3. **Default on:** `skip_past_events=True` by default so new callers get the rule automatically.

4. **Explicit override:** Use `skip_past_events=False` only in named backfill/archival scripts, with a comment explaining why.

5. **Logging:** Log skipped past events at debug level so they can be inspected without cluttering logs.

6. **Tests:** Add unit tests for `is_event_past()` covering:
   - Single-day past
   - Single-day today/future
   - Multi-day past (end_date < today)
   - Multi-day current (end_date >= today, start_date < today)
   - No start_date (return False)
   - Ongoing exhibition (after date handling: start_date=today)

---

## Summary

| Question | Answer |
|----------|--------|
| **Best shared place** | `scripts/event_database_handler.py` – `create_events_in_database()` |
| **Where to implement** | Shared ingestion only |
| **Exceptions** | Ongoing exhibitions (handled by date logic), multi-day events (end_date >= today), archival (skip_past_events=False), URL import (no filter) |
| **Implementation** | Add `is_event_past()` helper and `skip_past_events=True` check after `handle_ongoing_exhibition_dates()` |
| **Avoid breakage** | Check runs after ongoing-exhibition date handling; multi-day rule uses `end_date >= today` |
| **Maintainer rule** | One place, default on, explicit override for backfill, document and test |
