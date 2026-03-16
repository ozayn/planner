# Production NYC Audit: Decision Guide

**Context:** Production audit found duplicate NYC venues (Met, AMNH), empty `/api/sources?city_id=683`, and local JSON ready to sync. This guide helps you decide the safest next step.

---

## 1. Safest Interpretation of Production Findings

### Duplicate Venues (Met, AMNH)

| Finding | Interpretation |
|---------|----------------|
| Two "Metropolitan Museum of Art" records | Production has duplicate venue rows. Likely from prior manual adds or a past reload/import. |
| Two "American Museum of Natural History" records | Same as above. |
| **Risk** | Events may be linked to either duplicate. Deleting the wrong one would orphan events. |

### Empty `/api/sources?city_id=683`

| Finding | Interpretation |
|---------|----------------|
| Empty list | **Not necessarily missing sources.** The public `/api/sources` endpoint reads from the deployed `sources.json` file and filters by `source.city_id == city_id`. |
| **Cause** | NYC sources in `sources.json` use `city_id: 2` (JSON convention). You passed `city_id=683` (production DB id). No sources match. |
| **Action** | Try `GET /api/sources?city_id=2` — that should return NYC sources if the deployed JSON has them. |

### Summary

- **Duplicates:** Real; need a safe cleanup plan.
- **Empty sources:** Likely a `city_id` mismatch; verify with `city_id=2` before concluding sources are missing.

---

## 2. Sync Now vs. Clean Duplicates First

### Recommendation: **Reload First, Then Clean Duplicates**

| Approach | Pros | Cons |
|----------|------|-----|
| **Clean first, then reload** | Cleaner state before reload | You may delete the venue that has events; events would be orphaned. Hard to know which duplicate to keep. |
| **Reload first, then clean** | One duplicate gets updated with correct data; you can identify the stale one by `updated_at` and delete it. | Duplicates remain briefly after reload. |

**Why reload first:**

1. Reload updates **one** of the duplicates (the first match by name). That record gets the correct metadata.
2. The other duplicate is left unchanged and becomes clearly "stale" (older `updated_at`, possibly no events).
3. After reload, you can safely delete the stale duplicate (e.g., the one with older `updated_at` and no events).
4. If you delete first, you risk removing the record that has events.

---

## 3. What Happens If You Reload With Duplicates Present

### `POST /api/admin/reload-cities`

- Matches by `name` + `state` + `country`.
- NYC exists; it will be updated in place.
- **No impact on duplicates.** Safe.

### `POST /api/admin/reload-venues-from-json`

- For each venue in JSON: `Venue.query.filter_by(name=venue_name).first()`.
- With 2 Mets: **first()** returns one row; that row is updated. The other is untouched.
- **Result:** 1 Met updated with JSON data, 1 Met unchanged (stale duplicate).
- **No new duplicates created.** Reload does not add a third Met.

### `POST /api/admin/reload-sources`

- Reads from `sources.json`; matches by name.
- Maps JSON `city_id` → production `city_id` via `cities.json` name lookup.
- NYC sources get `city_id=683` in the DB.
- **Result:** Sources added/updated in DB. No duplicate-source logic; reload matches by name and updates or creates.

### Summary

| Endpoint | With Duplicates Present |
|----------|-------------------------|
| reload-cities | Safe; no change to duplicates |
| reload-venues-from-json | Updates one of each duplicate; leaves the other. Duplicates remain until you clean them. |
| reload-sources | Safe; adds/updates sources by name |

---

## 4. Safest Production Cleanup/Sync Order

### Recommended Sequence

| Step | Action | Purpose |
|------|--------|---------|
| 1 | **Verify sources** | Call `GET /api/sources?city_id=2`. If you get NYC sources, the JSON is fine. |
| 2 | **Backup** | Back up `data/cities.json`, `data/venues.json`, `data/sources.json` (if not already done). |
| 3 | **Deploy** | Ensure production has the latest JSON (commit and push; wait for deploy). |
| 4 | **Reload cities** | `POST /api/admin/reload-cities` |
| 5 | **Reload venues** | `POST /api/admin/reload-venues-from-json` — one of each duplicate will be updated. |
| 6 | **Reload sources** | `POST /api/admin/reload-sources` |
| 7 | **Verify** | Check NYC in Admin UI; confirm venue/source counts. |
| 8 | **Clean duplicates** | In Admin UI, delete the stale Met and AMNH duplicates (the ones with older `updated_at` or no events). |

### Duplicate Cleanup (After Reload)

1. In Admin, open NYC venues.
2. Find the two Mets and two AMNHs.
3. Compare `updated_at` — the one updated by reload will be newer.
4. Check which has events (if any).
5. Delete the **stale** duplicate (older `updated_at`, ideally no events). If both have events, keep the one with more events or the newer one.

---

## 5. Source Verification: Public vs. Admin Endpoints

### Public `/api/sources`

- **Reads from:** Deployed `sources.json` file.
- **Filters by:** `source.city_id == city_id` (from the request).
- **Auth:** None.
- **For NYC:** Use `city_id=2` (JSON convention), not `683`.

### Admin `/api/admin/sources`

- **Reads from:** Database.
- **Returns:** All sources (with `city_name`).
- **Auth:** Required on production.
- **For NYC:** Filter the response by `city_name == "New York"` or `city_id == 683`.

### When to Use Which

| Goal | Endpoint |
|------|----------|
| See what the public site shows for NYC sources | `GET /api/sources?city_id=2` |
| See what the DB has for NYC sources | `GET /api/admin/sources` (then filter by city_name or city_id) |
| Confirm sources exist before reload | Use both: `city_id=2` for JSON, admin for DB. |

**You do not need admin auth for basic source verification.** Use `GET /api/sources?city_id=2` first. If that returns NYC sources, the deployed JSON is fine. Admin is for DB-level verification.

---

## 6. Before-Sync Decision Checklist (This Situation)

### Pre-Reload Verification

- [ ] Tried `GET /api/sources?city_id=2` — if empty, sources may be missing in deployed JSON; if populated, JSON is fine.
- [ ] Confirmed production NYC `city_id` is 683 (for venues and post-reload verification).
- [ ] Noted duplicate venues: Met (2), AMNH (2).
- [ ] Local JSON validated and tested locally.
- [ ] Backup of local JSON taken.

### Decision

- [ ] **Reload first, then clean duplicates** — chosen as the approach.
- [ ] **Deploy** — latest JSON is on production before reload.

### Reload Order

- [ ] 1. `POST /api/admin/reload-cities`
- [ ] 2. `POST /api/admin/reload-venues-from-json`
- [ ] 3. `POST /api/admin/reload-sources`

### Post-Reload

- [ ] Verify NYC in Admin UI (venue/source counts).
- [ ] Identify stale Met and AMNH duplicates (older `updated_at`).
- [ ] Delete stale duplicates in Admin UI.
- [ ] Re-verify NYC venue count (should be 11).

### If Sources Are Truly Missing

- [ ] If `GET /api/sources?city_id=2` is empty and deployed JSON has no NYC sources, reload will add them from your local JSON after deploy.
- [ ] Ensure deploy includes the updated `sources.json` before calling reload.

---

## Quick Reference

```bash
# Verify NYC sources (use city_id=2, not 683)
curl -s "https://planner.ozayn.com/api/sources?city_id=2" | python3 -m json.tool

# After reload, verify NYC venues (should eventually be 11 after duplicate cleanup)
curl -s "https://planner.ozayn.com/api/venues?city_id=683" | python3 -m json.tool
```
