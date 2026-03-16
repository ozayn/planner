# Production NYC Duplicate Venue Cleanup Checklist

**Context:** After reload, production has duplicate venue records for Metropolitan Museum of Art and American Museum of Natural History. This checklist guides safe identification and removal of the stale duplicates.

**Important:** Deleting a venue sets `event.venue_id` to NULL for any events linked to it (events are not deleted, but they lose their venue link). Always delete the duplicate that has **no events** or **fewer events**.

---

## 1. Safest Way to Identify the Stale Duplicate

### Primary: Event Count

**Rule:** Keep the venue that has events. Delete the one that has none (or fewer).

| Criterion | Keep | Delete |
|-----------|------|--------|
| Event count | Venue with events | Venue with no events |
| If both have events | Venue with more events | Venue with fewer events |
| If both have 0 events | Venue with newer `updated_at` (reloaded) | Venue with older `updated_at` (stale) |

### Secondary: `updated_at`

After reload, the venue that was matched and updated will have a **newer** `updated_at`. The stale duplicate will have an **older** `updated_at`. Use this when both duplicates have zero events.

### Tertiary: Metadata (optional)

The reloaded venue will have the updated metadata from your local JSON (e.g. `instagram_url`, `facebook_url`, real description). The stale duplicate may have empty or generic fields. Compare in Admin UI to confirm which was updated.

### How to Get Event Count per Venue

**Option A — Admin UI:** Open Admin → Events. Search or scroll for events at "Metropolitan Museum of Art" or "American Museum of Natural History". Note the venue ID on each event. The venue IDs that appear = have events = keep. The venue ID that never appears = safe to delete.

**Option B — API (requires auth):**

```bash
# 1. Get NYC venues and note the duplicate venue IDs
curl -s "https://planner.ozayn.com/api/venues?city_id=683" | python3 -m json.tool | grep -E '"id"|"name"'

# 2. Get event count per venue (replace with your session cookie)
curl -s "https://planner.ozayn.com/api/admin/events" -H "Cookie: session=YOUR_SESSION" | python3 -c "
import json, sys
from collections import Counter
events = json.load(sys.stdin)
counts = Counter(e.get('venue_id') for e in events if e.get('venue_id'))
# Replace 123, 456 with the two duplicate venue IDs (e.g. the two Met IDs)
for vid in [123, 456]:
    print(f'Venue {vid}: {counts.get(vid, 0)} events')
"
```

---

## 2. What to Verify Before Deleting a Duplicate

### Pre-Delete Verification

- [ ] **Event count confirmed** — The duplicate you will delete has 0 events (or fewer than the one you keep).
- [ ] **Venue ID noted** — You have the exact venue `id` you will delete (from Admin UI or API).
- [ ] **Name confirmed** — The venue is "Metropolitan Museum of Art" or "American Museum of Natural History".
- [ ] **City confirmed** — The venue is in New York (city_id 683).
- [ ] **Stale signal** — The duplicate has older `updated_at` than the one you are keeping (or has no events).

### Do Not Delete If

- The venue has events linked to it (unless you plan to transfer them first).
- You are unsure which duplicate is which.
- The venue is the only record for that name (no duplicate).

---

## 3. How to Avoid Deleting the Venue That Events Depend On

### Rule

**Never delete the venue that has events.** Delete only the duplicate with zero (or fewer) events.

### Steps

1. **Get event count per duplicate** — Use Admin Events tab or the API to see which venue IDs have events.
2. **Keep the venue with events** — If one Met has 5 events and the other has 0, keep the one with 5.
3. **Delete the venue with no events** — Safe to delete.
4. **If both have events** — Do not delete either via the simple flow. You would need to transfer events from one venue to the other first (e.g. via a script like `remove_duplicate_venues.py`), then delete the empty duplicate. For now, **do not delete** until you have a transfer plan.

### Admin UI Check

1. Open Admin → Events.
2. For each event at Met or AMNH, note the venue name and ID.
3. The venue IDs that appear = have events = keep.
4. The venue ID that never appears in any event = safe to delete.

---

## 4. Post-Reload Admin Verification Checklist for NYC

Complete this **after** calling reload endpoints and **before** deleting duplicates.

### Step 1: Confirm Reload Succeeded

- [ ] `POST /api/admin/reload-cities` returned success
- [ ] `POST /api/admin/reload-venues-from-json` returned success (note `updated_count`)
- [ ] `POST /api/admin/reload-sources` returned success

### Step 2: Verify NYC in Admin UI

- [ ] Open Admin → select "New York" (or filter venues by New York)
- [ ] NYC venue count: expect 13 before cleanup (11 unique + 2 duplicates)
- [ ] NYC source count: expect 12
- [ ] All 11 unique venue names present (including Brooklyn Museum, Lincoln Center, BAM)

### Step 3: Identify Duplicates

- [ ] Found 2 "Metropolitan Museum of Art" records — note both IDs and `updated_at`
- [ ] Found 2 "American Museum of Natural History" records — note both IDs and `updated_at`

### Step 4: Determine Which Duplicate to Delete

For each pair (Met, AMNH):

- [ ] Checked event count per venue ID
- [ ] Identified the venue with events (or with newer `updated_at` if both have 0 events)
- [ ] Marked the stale duplicate ID for deletion: Met = _____, AMNH = _____

### Step 5: Pre-Delete Double-Check

- [ ] Stale Met has 0 events (or fewer than the other)
- [ ] Stale AMNH has 0 events (or fewer than the other)
- [ ] Ready to delete

---

## 5. Final Expected NYC State After Cleanup

### Venues (11 total)

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

### Sources (12 total)

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

### Verification After Cleanup

- [ ] `GET /api/venues?city_id=683` returns exactly 11 venues
- [ ] No duplicate venue names in the list
- [ ] `GET /api/sources?city_id=2` returns 12 sources (or use admin sources filtered by New York)
- [ ] Admin UI: New York shows 11 venues, 12 sources

---

## Quick Reference: Delete Endpoint

```
DELETE /api/delete-venue/<venue_id>
```

**Note:** Requires admin authentication on production. Use the Admin UI delete button, or `curl` with your session cookie.

---

## If Both Duplicates Have Events

Do **not** delete either venue manually. Options:

1. **Use `scripts/remove_duplicate_venues.py`** — It transfers events from duplicates to the kept venue, then deletes the empty duplicate. Run locally against production DB, or adapt for production use.
2. **Manual event transfer** — In Admin, edit each event to point to the venue you are keeping, then delete the empty duplicate.
3. **Leave duplicates** — If the impact is low, you can defer cleanup until you have a safe transfer process.
