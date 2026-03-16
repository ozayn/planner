# Backlog: `/api/sources` city_id Mismatch Fix

**Status:** Documented, not yet implemented  
**Related:** `docs/SOURCES_CITY_ID_MISMATCH_EXPLANATION.md`, ROADMAP.md line 354

---

## 1. Bug Summary

**Title:** `/api/sources` uses JSON city_id while frontend passes DB city_id

**Summary:** The public `/api/sources` endpoint reads from `data/sources.json` and filters by `source.city_id`. Those values follow the JSON convention (1, 2, 3… matching `cities.json` keys). `/api/cities` and `/api/venues` return and expect database city IDs, which differ on production (e.g. 683 for New York). The frontend passes the DB city_id from the city dropdown into `/api/sources`, so sources return empty for any city where DB id ≠ JSON id.

**Root cause:** `/api/sources` was built to read from JSON; other public endpoints use the database. No mapping exists between DB and JSON city_ids.

---

## 2. User-Facing Impact

| Impact | Description |
|--------|-------------|
| **Sources not loading** | When a user selects a city (e.g. New York) whose DB id differs from its JSON id, the Discover drawer shows no sources. |
| **Inconsistent behavior** | Venues and events load correctly; sources do not. Users may assume sources are missing or broken. |
| **Environment-dependent** | Works locally when DB and JSON ids align (e.g. 1, 2, 3). Fails on production where DB ids diverge. |
| **No error feedback** | Endpoint returns an empty list; no indication that the city_id convention is wrong. |

---

## 3. Safest Future Fix Options

### Option A: Switch `/api/sources` to read from database

- Query `Source.query.filter(Source.city_id == city_id)` (same pattern as venues).
- **Pros:** Aligns with `/api/venues` and `/api/events`; single source of truth; frontend works without changes.
- **Cons:** Requires sources to be in DB (already true after reload). JSON becomes export/backup only.

### Option B: Map DB city_id → JSON city_id when reading from JSON

- Resolve city by DB id → get city name → find JSON city_id from `cities.json` by name → filter sources by that JSON city_id.
- **Pros:** Keeps JSON as source for `/api/sources`; no DB schema dependency.
- **Cons:** Extra lookup; two sources of truth; more complex; JSON must stay in sync with cities.

### Option C: Frontend passes city name instead of city_id

- Change `/api/sources` to accept `city_name` (or both `city_id` and `city_name`).
- **Pros:** Name-based matching avoids id mismatch.
- **Cons:** Requires frontend changes; API contract change; possible ambiguity for duplicate city names.

### Option D: Dual support — accept both DB and JSON city_id

- If `city_id` matches a DB city, use it to filter DB sources (or map to JSON id). If it matches a JSON city_id, filter JSON directly.
- **Pros:** Backward compatible for callers using JSON ids.
- **Cons:** More logic; two code paths; harder to reason about.

---

## 4. Recommended Option for This Repository

**Option A: Switch `/api/sources` to read from database.**

**Reasons:**

1. **Consistency:** Venues and events already use the DB; sources should too.
2. **Single source of truth:** DB is the runtime source after reload; JSON is transport/backup.
3. **No frontend changes:** Frontend already passes DB city_id; it will work as-is.
4. **Low risk:** `Source` model exists; `reload-sources` populates it; `/api/admin/sources` already reads from DB.
5. **Simpler:** One code path, no mapping layer.

**Preconditions:**

- Production must have run `reload-sources` (or `load-all-data`) so the DB has sources.
- JSON remains the source of truth for edits; reload syncs JSON → DB.

---

## 5. Regression Checks After Fix

### Functional

- [ ] **Local:** Select each city; sources load in Discover drawer.
- [ ] **Production:** Select New York (and any city with DB id ≠ JSON id); sources load.
- [ ] **Edge cases:** City with 0 sources returns empty list (not error). `covers_multiple_cities` sources still appear when relevant.
- [ ] **Admin:** `/api/admin/sources` unchanged; admin Sources section works.

### API contract

- [ ] Response shape unchanged (array of source objects with same fields).
- [ ] `city_id` query param still required; 400 when missing.
- [ ] No new required params; existing callers keep working.

### Data

- [ ] Source count per city matches expectations (e.g. NYC has 12).
- [ ] No duplicate or missing sources after switching to DB.

### Cross-environment

- [ ] Local SQLite: sources load for all cities.
- [ ] Production PostgreSQL: sources load for all cities, including NYC.

---

## 6. Suggested Roadmap / Maintainer Notes Section

Add to ROADMAP.md (e.g. under "Data consistency" or "Backlog"):

```markdown
### Backlog: `/api/sources` city_id mismatch

**Issue:** `/api/sources` reads from `data/sources.json` and filters by JSON city_id (1, 2, 3…). The frontend passes DB city_id from `/api/cities` (e.g. 683 for NYC on production). When DB id ≠ JSON id, sources return empty.

**Impact:** Sources do not load for cities like New York on production. Venues and events work; sources do not.

**Fix:** Switch `/api/sources` to read from the database (like `/api/venues`). See `docs/backlog/SOURCES_CITY_ID_FIX_PLAN.md`.

**Precondition:** Production must have run `reload-sources` so the DB has sources.
```

---

## References

- `app.py` lines 1344–1380: `/api/sources` implementation
- `templates/index.html`: `loadSources()`, `loadSourcesForCity()` — pass `cityId` from city dropdown
- `docs/SOURCES_CITY_ID_MISMATCH_EXPLANATION.md`: Full technical explanation
