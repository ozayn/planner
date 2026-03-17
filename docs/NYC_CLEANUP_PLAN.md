# NYC Cleanup Plan (Pre–Phase 1 Rollout)

**Purpose:** Prepare existing NYC venues and sources for Phase 1 rollout. No code or scraper changes—data edits only.

**Reference:** `docs/NYC_AUDIT_REPORT.md`

---

## 1. Cleanup Summary by Entry

| Entry | Action | Reason |
|-------|--------|--------|
| **Venues** | | |
| 69 AMNH | Edit | Add Instagram; improve description |
| 71 Brooklyn Bridge | Treat as non-scrapeable | No event calendar; keep for display only |
| 72 Central Park | Keep as-is | Good for Phase 1 testing |
| 73 Empire State Building | Keep as-is | Good for Phase 1 testing |
| 74 Met | Edit | Add Instagram; improve description |
| 76 MoMA | Keep as-is | Already complete |
| 77 Statue of Liberty | Keep as-is | Good for Phase 1 testing |
| 78 Times Square | Keep as-is | Good for Phase 1 testing |
| **Sources** | | |
| 38–47 | Keep as-is | Complete and usable |
| 48 Big Onion | Keep as-is | Tours page; usable |
| 49 Ellis Island Hard Hat Tours | Edit | Change URL to events/schedule page if available; else deprioritize |
| **New venues** | | |
| Brooklyn Museum | Add | Source 42 exists; no venue |
| Lincoln Center | Add | Source 44 exists; no venue |
| BAM | Add | Source 45 exists; no venue |

---

## 2. Exact Field Updates

### AMNH (venue 69)

| Field | Current | Recommended |
|-------|---------|-------------|
| `instagram_url` | `""` | `"https://www.instagram.com/amnh/"` |
| `facebook_url` | `""` | `"https://www.facebook.com/naturalhistory"` |
| `description` | `"A museum in New York offering cultural experiences and entertainment."` | `"One of the world's largest natural history museums, with 45 permanent exhibition halls, a planetarium, and a library. Features dinosaurs, mammals, ocean life, and cultural collections."` |

**Optional:** Add `twitter_url`: `"https://twitter.com/AMNH"`

---

### Met (venue 74)

| Field | Current | Recommended |
|-------|---------|-------------|
| `instagram_url` | `""` | `"https://www.instagram.com/metmuseum/"` |
| `facebook_url` | `""` | `"https://www.facebook.com/metmuseum"` |
| `twitter_url` | `""` | `"https://twitter.com/metmuseum"` |
| `description` | `"A museum in New York offering cultural experiences and entertainment."` | `"One of the world's largest art museums, with over 5,000 years of art from around the globe. Collections span ancient to contemporary, with exhibitions, concerts, lectures, and programs."` |

---

### Brooklyn Bridge (venue 71)

| Field | Current | Recommended |
|-------|---------|-------------|
| `website_url` | `"https://www.nyc.gov/html/dot/html/infrastructure/brooklyn-bridge.shtml"` | **Keep as-is** (or see note below) |
| `additional_info` | `""` | `"{\"non_scrapeable\": true, \"reason\": \"Landmark with no event calendar; website is infrastructure info only.\"}"` |

**Note:** The scraper skips venues with empty `website_url` or `example.com`. Keeping the current URL means the scraper will try and return nothing. To avoid scrape attempts entirely, you could set `website_url` to `""`, but then the venue has no link in the UI. **Recommendation:** Keep URL, add `additional_info` note, and document as non-scrapeable. No functional change.

---

### Ellis Island Hard Hat Tours (source 49)

| Field | Current | Recommended |
|-------|---------|-------------|
| `url` | `"https://shop.saveellisisland.org/products/novelty-hard-hat-tour"` | `"https://www.saveellisisland.org/visit/tours/"` (or equivalent schedule page—verify before editing) |
| `handle` | `"saveellisisland.org"` | Keep or change to `"@saveellisisland"` if they have Instagram |

**Verification:** Check https://www.saveellisisland.org/ for a tours/events/schedule page. If none exists, keep current URL and add to `notes`: `"URL is product page; scraping may require custom logic. Deprioritize for Phase 1."`

---

## 3. Brooklyn Museum, Lincoln Center, BAM: Add as Venues?

**Recommendation:** Yes. Add all three before Phase 1.

- Sources 42, 44, 45 already exist and post events.
- Source scraping can attach events to venues when a venue exists.
- These are major NYC cultural venues and good Phase 1 candidates.

### Canonical Venue Records (suggested)

**Next available venue keys:** 223, 224, 225 (current max in `venues.json` is 222).

---

#### Brooklyn Museum (key `"223"`)

```json
{
  "name": "Brooklyn Museum",
  "venue_type": "museum",
  "address": "200 Eastern Pkwy, Brooklyn, NY 11238",
  "city_id": 2,
  "city_name": "New York",
  "description": "One of the largest art museums in the United States, with collections spanning ancient Egyptian masterworks to contemporary art. Features exhibitions, programs, and community events.",
  "opening_hours": "Wed–Sun: 11:00 AM - 6:00 PM (Thu until 10:00 PM)",
  "holiday_hours": "",
  "phone_number": "(718) 638-5000",
  "email": "information@brooklynmuseum.org",
  "website_url": "https://www.brooklynmuseum.org",
  "ticketing_url": "",
  "instagram_url": "https://www.instagram.com/brooklynmuseum",
  "facebook_url": "https://www.facebook.com/brooklynmuseum",
  "twitter_url": "https://twitter.com/brooklynmuseum",
  "youtube_url": "",
  "tiktok_url": "",
  "admission_fee": "Suggested admission; pay what you wish",
  "image_url": "",
  "latitude": 40.6712,
  "longitude": -73.9638,
  "additional_info": "",
  "created_at": "",
  "updated_at": ""
}
```

**Note:** Omit `created_at` and `updated_at` when adding; reload will set them. Or use current timestamp in ISO format.

---

#### Lincoln Center (key `"224"`)

```json
{
  "name": "Lincoln Center for the Performing Arts",
  "venue_type": "arts_center",
  "address": "10 Lincoln Center Plaza, New York, NY 10023",
  "city_id": 2,
  "city_name": "New York",
  "description": "World's leading performing arts center, home to the Metropolitan Opera, New York Philharmonic, New York City Ballet, and more. Hosts opera, symphony, dance, theater, and film.",
  "opening_hours": "Varies by performance and venue",
  "holiday_hours": "",
  "phone_number": "(212) 875-5456",
  "email": "info@lincolncenter.org",
  "website_url": "https://www.lincolncenter.org",
  "ticketing_url": "",
  "instagram_url": "https://www.instagram.com/lincolncenter",
  "facebook_url": "https://www.facebook.com/LincolnCenterNYC",
  "twitter_url": "https://twitter.com/LincolnCenter",
  "youtube_url": "https://www.youtube.com/lincolncenter",
  "tiktok_url": "",
  "admission_fee": "Varies by event",
  "image_url": "",
  "latitude": 40.7723,
  "longitude": -73.9847,
  "additional_info": "",
  "created_at": "",
  "updated_at": ""
}
```

---

#### Brooklyn Academy of Music (key `"225"`)

```json
{
  "name": "Brooklyn Academy of Music",
  "venue_type": "arts_center",
  "address": "30 Lafayette Ave, Brooklyn, NY 11217",
  "city_id": 2,
  "city_name": "New York",
  "description": "BAM is a multi-venue performing arts center presenting theater, dance, music, opera, and film. Known for cutting-edge and international programming.",
  "opening_hours": "Varies by performance",
  "holiday_hours": "",
  "phone_number": "(718) 636-4100",
  "email": "info@bam.org",
  "website_url": "https://www.bam.org",
  "ticketing_url": "",
  "instagram_url": "https://www.instagram.com/bam_brooklyn",
  "facebook_url": "https://www.facebook.com/BrooklynAcademyOfMusic",
  "twitter_url": "https://twitter.com/BAM_Brooklyn",
  "youtube_url": "",
  "tiktok_url": "",
  "admission_fee": "Varies by event",
  "image_url": "",
  "latitude": 40.6865,
  "longitude": -73.9776,
  "additional_info": "",
  "created_at": "",
  "updated_at": ""
}
```

---

## 4. Safest Order to Apply Cleanups

Apply in this order to reduce risk and make rollback easier:

| Step | Action | Risk | Rollback |
|------|--------|------|----------|
| 1 | Backup `data/venues.json` and `data/sources.json` | None | Restore from backup |
| 2 | Edit AMNH (69): add Instagram, Facebook, description | Low | Revert fields |
| 3 | Edit Met (74): add Instagram, Facebook, Twitter, description | Low | Revert fields |
| 4 | Edit Brooklyn Bridge (71): add `additional_info` note | Low | Remove `additional_info` |
| 5 | Verify Ellis Island URL; edit source 49 if better URL exists | Low | Revert URL |
| 6 | Add Brooklyn Museum (223), Lincoln Center (224), BAM (225) to `venues.json` | Medium | Remove the three entries |
| 7 | Update `metadata.total_venues` in `venues.json` (212 → 215) | Low | Revert metadata |
| 8 | Reload locally: `curl -X POST http://localhost:5001/api/admin/reload-venues-from-json` | Low | Reload from backup JSON |
| 9 | Reload sources if source 49 was edited: `curl -X POST http://localhost:5001/api/admin/reload-sources` | Low | Reload from backup |
| 10 | Verify in admin: NYC city, 11 venues (8 existing + 3 new), 11 sources | — | — |
| 11 | Commit and push; after deploy, reload on production | — | Revert commit and redeploy |

---

## 5. JSON / ID / Field Constraints

### Venues (`data/venues.json`)

| Constraint | Rule |
|------------|------|
| **Structure** | Top-level `metadata` and `venues`. Venues are keyed by string IDs (e.g. `"69"`). |
| **Required fields** | `name`, `city_name` (used for city matching). |
| **City matching** | `city_name` must match a city in `cities.json` (case-insensitive). Use `"New York"` for NYC. |
| **New venue keys** | Use next available numeric string. Current max: 222. Use 223, 224, 225 for the three new venues. |
| **ID assignment** | JSON key is for file structure. DB assigns IDs on load; they may differ from JSON keys. |
| **Scraper skip rules** | Venues with empty `website_url` or `example.com` in `website_url` are skipped. |
| **Venue types** | Use lowercase with underscores: `museum`, `arts_center`, `landmark`, `park`, `monument`, etc. |
| **Optional fields** | `created_at`, `updated_at` can be omitted; reload may set them. |

### Sources (`data/sources.json`)

| Constraint | Rule |
|------------|------|
| **Structure** | Top-level `metadata` and `sources`. Sources keyed by string IDs. |
| **Required fields** | `name`, `source_type`, `url`, `city_id`. |
| **Source types** | `instagram`, `website`, etc. |
| **Matching** | Reload matches by `name`; preserves IDs. |

### Reload Logic

| Endpoint | Matching | Behavior |
|----------|----------|----------|
| `reload-venues-from-json` | Venue by `name` (exact) | Updates existing; creates new if not found. City resolved by `city_name`. |
| `reload-sources` | Source by `name` | Updates existing; creates new if not found. |
| `load-all-data` | Cities by name+state+country; venues by name; sources by name | Full load; preserves IDs where possible. |

### Before Editing

1. Create a backup: `cp data/venues.json data/backups/venues.json.backup.pre-nyc-cleanup` (and same for sources).
2. Ensure `city_name` is exactly `"New York"` for all NYC venues.
3. Do not change venue IDs (keys) for existing venues; that can break event links.
4. After edits, run `reload-venues-from-json` (and `reload-sources` if needed), then `update-all-json` to sync DB → JSON if IDs changed.

---

## 6. Maintainer Checklist

- [ ] Backup `data/venues.json` and `data/sources.json`
- [ ] Edit AMNH (69): `instagram_url`, `facebook_url`, `description`
- [ ] Edit Met (74): `instagram_url`, `facebook_url`, `twitter_url`, `description`
- [ ] Edit Brooklyn Bridge (71): `additional_info` with non-scrapeable note
- [ ] Verify Save Ellis Island for events/schedule URL; edit source 49 if better URL found
- [ ] Add Brooklyn Museum (223) to `venues.json`
- [ ] Add Lincoln Center (224) to `venues.json`
- [ ] Add BAM (225) to `venues.json`
- [ ] Update `metadata.total_venues` (212 → 215)
- [ ] Reload venues locally: `curl -X POST http://localhost:5001/api/admin/reload-venues-from-json`
- [ ] Reload sources locally if edited: `curl -X POST http://localhost:5001/api/admin/reload-sources`
- [ ] Verify in admin: NYC, 11 venues, 11 sources
- [ ] Commit and push; after deploy, reload on production
- [ ] Document completion in `docs/NYC_AUDIT_REPORT.md` or session notes
