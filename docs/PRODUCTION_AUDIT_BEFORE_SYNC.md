# Production Audit Before Sync

**Purpose:** Safely audit the deployed Planner instance before syncing local JSON changes. No code changes. No sync. Read-only checks only.

---

## 1. Safest Way to Audit Deployed Data

Use **read-only GET endpoints** and the **Admin UI**. Do not call any POST endpoints (reload, update, etc.).

| Method | What to Use |
|--------|-------------|
| **API** | `GET` requests only; resolve city by name, then use production `city_id` |
| **Admin UI** | Browse cities, select "New York", inspect venues and sources by name |
| **Comparison** | Compare production responses to local JSON by **name** — ignore numeric IDs |

---

## 2. Endpoints and Pages to Check First

### Recommended Order

| Step | Endpoint / Page | Purpose |
|------|-----------------|---------|
| 1 | `GET /api/admin/stats` | Total counts; confirm API is reachable |
| 2 | `GET /api/cities` or `GET /api/admin/cities` | List cities; find "New York" and note its production `id` |
| 3 | `GET /api/venues?city_id=<NYC_PROD_ID>` | NYC venues (from DB) |
| 4 | `GET /api/sources?city_id=<NYC_PROD_ID>` | NYC sources (from deployed `sources.json`) |
| 5 | Admin UI: https://planner.ozayn.com/admin | Select "New York"; visually verify names and counts |

### Base URL

- **Production:** `https://planner.ozayn.com`
- **Local:** `http://localhost:5001`

### Authentication

- `GET /api/admin/*` requires auth on production (OAuth). Use a logged-in session or ensure OAuth is configured.
- `GET /api/cities`, `GET /api/venues`, `GET /api/sources` are public and do not require admin auth.

---

## 3. Comparing Deployed vs Local When IDs Differ

### Rule: Compare by Name Only

Production `city_id`, `venue_id`, and `source_id` will not match local. Compare by **name**.

### Step-by-Step Comparison

1. **Resolve production NYC `city_id`:**
   ```bash
   curl -s https://planner.ozayn.com/api/cities | python3 -m json.tool | grep -B 2 -A 4 '"name": "New York"'
   ```
   Note the `id` field for New York.

2. **Fetch production NYC venues:**
   ```bash
   curl -s "https://planner.ozayn.com/api/venues?city_id=<NYC_PROD_ID>" | python3 -m json.tool > prod_nyc_venues.json
   ```

3. **Fetch production NYC sources:**
   ```bash
   curl -s "https://planner.ozayn.com/api/sources?city_id=<NYC_PROD_ID>" | python3 -m json.tool > prod_nyc_sources.json
   ```

4. **Extract local NYC names from JSON:**
   ```bash
   python3 -c "
   import json
   with open('data/venues.json') as f: v = json.load(f)
   local_venues = sorted([x['name'] for x in v['venues'].values() if isinstance(x, dict) and x.get('city_name') == 'New York'])
   with open('data/sources.json') as f: s = json.load(f)
   local_sources = sorted([x['name'] for x in s['sources'].values() if isinstance(x, dict) and x.get('city_id') == 2])
   print('LOCAL NYC VENUES:', local_venues)
   print('LOCAL NYC SOURCES:', local_sources)
   "
   ```

5. **Compare:** Production venue/source names vs local names. Missing names = missing records. Extra names = possible duplicates or renamed records.

### Data Source Note

- **Venues:** `GET /api/venues` returns data from the **database**. Use the production NYC `city_id` from `GET /api/cities`.
- **Sources:** `GET /api/sources` reads from the deployed **sources.json** file and filters by `city_id`. NYC sources in the JSON use `city_id: 2`. Use `city_id=2` for NYC sources (JSON convention). If that returns no results, try the production city `id` from `GET /api/cities`.

---

## 4. Practical Checklist: Auditing Deployed NYC Data Before Reload

### Pre-Audit

- [ ] Production URL confirmed: `https://planner.ozayn.com`
- [ ] You can reach production (no network/VPN issues)
- [ ] Local JSON files available for comparison

### NYC-Specific Audit

- [ ] **Resolve NYC production `city_id`** — Call `GET /api/cities`, find "New York", note `id`
- [ ] **Fetch production NYC venues** — `GET /api/venues?city_id=<id>`
- [ ] **Fetch production NYC sources** — `GET /api/sources?city_id=<id>`
- [ ] **Compare venue names** — Local expects 11 NYC venues (see list below). Production should have the same or fewer before sync.
- [ ] **Compare source names** — Local expects 12 NYC sources. Production should have the same or fewer before sync.
- [ ] **Check for duplicates** — Same venue/source name appearing twice
- [ ] **Check key records** — AMNH, Met, Brooklyn Bridge, Ellis Island source exist and have expected metadata (if you can inspect)

### Expected Local NYC Venues (Post–Phase 1 Cleanup)

| Venue Name |
|------------|
| American Museum of Natural History |
| Brooklyn Academy of Music (BAM) |
| Brooklyn Bridge |
| Brooklyn Museum |
| Central Park |
| Empire State Building |
| Lincoln Center |
| Metropolitan Museum of Art |
| Museum of Modern Art (MoMA) |
| Statue of Liberty |
| Times Square |

### Expected Local NYC Sources

| Source Name |
|-------------|
| Big Onion Walking Tours |
| Brooklyn Academy of Music |
| Brooklyn Museum |
| Ellis Island Hard Hat Tours |
| Gothamist |
| Lincoln Center |
| MoMA |
| NYC Arts |
| NYC Parks |
| NYC.com |
| The Metropolitan Museum of Art |
| Time Out New York |

---

## 5. Which Mismatches Matter Most

| Mismatch | Severity | Why |
|----------|----------|-----|
| **Missing venues** | High | Reload will add them. Audit confirms production is missing them so you know what to expect after sync. |
| **Outdated venue metadata** | Medium | Reload updates by name. If the venue exists, metadata will be refreshed. Audit helps you confirm what will change. |
| **Missing sources** | High | Reload will add them. Same as venues. |
| **Renamed records** | High | Reload matches by name. A rename in production creates a new record; the old one stays. Audit for renames before sync to avoid duplicates. |
| **Duplicates** | Medium | Reload does not remove duplicates. If production has duplicate venues/sources, they will remain. Consider cleanup before or after sync. |

### Priority Order for Audit

1. **Missing venues** — Will be added by reload; confirm list.
2. **Missing sources** — Will be added by reload; confirm list.
3. **Duplicates** — Reload won't fix; note for manual cleanup.
4. **Renamed records** — Could cause duplicates; check before sync.
5. **Outdated metadata** — Will be updated by reload; lower priority for audit.

---

## 6. Exact Before-Sync Checklist

Complete this **before** calling any production reload endpoints.

### Backup and Local Verification

- [ ] Backed up `data/cities.json`, `data/venues.json`, `data/sources.json`
- [ ] Local JSON syntax valid: `python3 -c "import json; json.load(open('data/venues.json')); json.load(open('data/sources.json')); json.load(open('data/cities.json'))"`
- [ ] Local reload and verification done (Admin UI shows expected NYC data)

### Production Audit (Read-Only)

- [ ] `GET /api/admin/stats` returns 200; note current counts
- [ ] Resolved production NYC `city_id` from `GET /api/cities`
- [ ] Fetched production NYC venues; saved or noted names
- [ ] Fetched production NYC sources; saved or noted names
- [ ] Compared production vs local venue names; documented gaps
- [ ] Compared production vs local source names; documented gaps
- [ ] Checked for duplicate venue/source names in production
- [ ] Checked for renamed records that could create duplicates on reload
- [ ] Admin UI: selected "New York", confirmed current state

### Pre-Reload Decisions

- [ ] Decided whether to fix duplicates before or after reload
- [ ] Decided whether any renames need manual event cleanup
- [ ] Confirmed deploy has latest JSON (if you've already pushed)

### Ready to Reload

- [ ] All audit steps complete
- [ ] No blocking issues (or issues documented and accepted)
- [ ] Ready to call: `reload-cities`, `reload-venues-from-json`, `reload-sources` (in that order)

---

## Quick Reference: Audit Commands

```bash
# 1. Production stats
curl -s https://planner.ozayn.com/api/admin/stats | python3 -m json.tool

# 2. Find NYC production city_id
curl -s https://planner.ozayn.com/api/cities | python3 -m json.tool | grep -B 2 -A 5 "New York"

# 3. Fetch NYC venues (replace PROD_NYC_ID)
curl -s "https://planner.ozayn.com/api/venues?city_id=PROD_NYC_ID" | python3 -m json.tool

# 4. Fetch NYC sources (replace PROD_NYC_ID)
curl -s "https://planner.ozayn.com/api/sources?city_id=PROD_NYC_ID" | python3 -m json.tool

# 5. Extract local NYC names for comparison
python3 -c "
import json
with open('data/venues.json') as f: v = json.load(f)
print('Local NYC venues:', sorted([x['name'] for x in v['venues'].values() if isinstance(x, dict) and x.get('city_name') == 'New York']))
with open('data/sources.json') as f: s = json.load(f)
print('Local NYC sources:', sorted([x['name'] for x in s['sources'].values() if isinstance(x, dict) and x.get('city_id') == 2]))
"
```
