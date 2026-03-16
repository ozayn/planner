# Sources vs Venues/Cities: city_id Mismatch Explanation

**Observed behavior:** `/api/cities` and `/api/venues` use production DB ids (e.g. 683 for New York), but `/api/sources` only returns data when given JSON convention ids (e.g. 2 for New York).

---

## 1. Exact Code Path for `/api/sources`

**File:** `app.py`  
**Lines:** 1344–1380

```python
@app.route('/api/sources')
def get_sources():
    """Get sources for a specific city"""
    city_id = request.args.get('city_id')
    # ...
    with open('data/sources.json', 'r') as f:
        sources_data = json.load(f)
    sources = sources_data.get('sources', {})
    for source_id, source in sources.items():
        if source.get('city_id') == int(city_id) or source.get('covers_multiple_cities', False):
            filtered_sources.append({...})
    return jsonify(filtered_sources)
```

**Flow:**

1. Read `city_id` from query string.
2. Load `data/sources.json` from disk.
3. Filter sources where `source['city_id'] == int(city_id)`.
4. Return filtered list.

No database access. No mapping from DB city id to JSON city id.

---

## 2. Does `/api/sources` Read from JSON Instead of the Database?

**Yes.** `/api/sources` reads only from the `data/sources.json` file.

| Endpoint       | Data source        | Filter field |
|----------------|--------------------|---------------|
| `/api/cities`  | Database (`City`)  | N/A           |
| `/api/venues`  | Database (`Venue`) | `Venue.city_id` |
| `/api/events`  | Database (`Event`) | `Event.city_id`, `Event.venue_id` |
| `/api/sources` | **File** (`data/sources.json`) | `source.city_id` |

The admin sources endpoint (`/api/admin/sources`) uses the database; the public `/api/sources` does not.

---

## 3. Why `city_id` Values Differ

### JSON convention (used by `/api/sources`)

- `cities.json` keys: `"1"`, `"2"`, `"3"`, …
- `sources.json` uses those keys as `city_id`:
  - `"1"` → Washington
  - `"2"` → New York
- These ids are tied to the JSON structure, not the database.

### Database convention (used by `/api/cities`, `/api/venues`, `/api/events`)

- Cities get ids from the DB (auto-increment).
- On production (e.g. PostgreSQL), ids can be 451, 452, 683, etc.
- Venues and events store `city_id` from the DB.

### Mismatch

| Environment | New York `city_id` | Used by |
|-------------|--------------------|---------|
| Local (SQLite) | Often 2 | DB and JSON both use 2 |
| Production (PostgreSQL) | e.g. 683 | DB uses 683; JSON still uses 2 |

`/api/sources` filters by `source.city_id` in the JSON, so it only matches when you pass the JSON convention id (2 for New York), not the DB id (683).

---

## 4. Intentional Design, Legacy, or Bug?

**Assessment: legacy behavior that behaves like a bug in production.**

### Evidence

1. **ROADMAP.md (lines 354–355):**
   > "Resolve DB vs JSON inconsistencies, especially around `/api/sources`"

2. **Other endpoints use the DB:** `/api/venues` and `/api/events` use DB ids consistently.

3. **Frontend uses DB ids:** `templates/index.html` gets `cityId` from the city dropdown, which is filled from `/api/cities` (DB ids). It then calls:
   - `/api/sources?city_id=${cityId}` → passes DB id (e.g. 683)
   - `/api/sources` expects JSON id (2) → no match → empty list

4. **Local vs production:** Locally, DB and JSON ids often align (1, 2, 3…), so sources work. On production, DB ids diverge, so sources fail for cities whose DB id ≠ JSON id.

### Conclusion

- Not intentional: the app expects a single `city_id` system.
- Legacy: sources were originally JSON-only; DB-backed endpoints were added later.
- Bug in production: sources do not load for cities when DB and JSON ids differ.

---

## 5. Maintainer Precautions

### When auditing production

- Use **JSON convention** for sources: `city_id=2` for NYC, `city_id=1` for DC.
- Do not assume `/api/sources?city_id=<db_id>` will work for all cities.

### When documenting

- Note that `/api/sources` uses JSON `city_id`, not DB `city_id`.
- See `docs/PRODUCTION_AUDIT_BEFORE_SYNC.md` and `docs/PRODUCTION_NYC_AUDIT_DECISION_GUIDE.md`.

### When testing

- Test sources with both JSON and DB ids if environments can differ.
- On production, verify sources for cities whose DB id ≠ JSON id (e.g. NYC).

### When fixing (future work)

- Either:
  - Switch `/api/sources` to read from the DB (like venues), or
  - Add a mapping from DB `city_id` → JSON `city_id` when reading from JSON.
- Ensure the frontend receives sources for the selected city regardless of DB vs JSON id.

### Sync and reload

- `reload-sources` writes from JSON into the DB and maps JSON `city_id` → DB `city_id` via `cities.json` name lookup.
- The DB ends up with correct DB `city_id`s.
- `/api/sources` still reads from JSON, so it continues to use JSON `city_id`s until the endpoint is changed.

---

## Summary

| Question | Answer |
|----------|--------|
| Code path | `app.py` 1344–1380: reads `data/sources.json`, filters by `source.city_id == city_id` |
| JSON vs DB | Reads from JSON only; no DB access |
| Why ids differ | JSON uses file keys (1, 2, 3…); DB uses auto-increment (e.g. 683) |
| Design / bug | Legacy; behaves as a bug when DB and JSON ids diverge |
| Precaution | Use JSON `city_id` (2 for NYC) when calling `/api/sources` on production |
