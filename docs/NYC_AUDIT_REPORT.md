# NYC Data Audit Report

**Date:** 2026-03-16  
**Scope:** `data/cities.json`, `data/venues.json`, `data/sources.json`, and admin/reload logic affecting NYC.

---

## Summary

- **City:** New York (city_id `2`) exists and is correctly configured.
- **Venues:** 8 NYC venues exist (IDs 69, 71, 72, 73, 74, 76, 77, 78). Mix of museums, landmarks, parks. Several have generic descriptions and some URLs are not ideal for event scraping.
- **Sources:** 11 NYC sources exist (IDs 38–49). All look complete and well-configured.
- **Verdict:** NYC data is present and structurally valid. Some venue cleanup is recommended before rollout: fix weak event URLs, add missing social links, and consider adding Brooklyn Museum and Lincoln Center as venues (they exist as sources only).

---

## 1. City Entry

| Field | Value |
|-------|-------|
| **ID** | 2 |
| **Name** | New York |
| **State** | New York |
| **Country** | United States |
| **Timezone** | America/New_York |

**Status:** Correct and consistent with `city_name: "New York"` used in venues and sources.

---

## 2. NYC Venues Table

| ID | Name | Venue Type | Website URL | Complete? | Domain Correct? | Scraping Viable? |
|----|------|------------|-------------|-----------|-----------------|------------------|
| 69 | American Museum of Natural History | museum | https://www.amnh.org | Partial | Yes | Likely generic or custom |
| 71 | Brooklyn Bridge | landmark | https://www.nyc.gov/html/dot/html/infrastructure/brooklyn-bridge.shtml | Partial | Wrong | No |
| 72 | Central Park | park | https://www.centralparknyc.org | Partial | Yes | Possibly generic |
| 73 | Empire State Building | landmark | https://www.esbnyc.com | Partial | Yes | Possibly generic |
| 74 | Metropolitan Museum of Art | museum | https://www.metmuseum.org | Partial | Yes | Likely custom |
| 76 | Museum of Modern Art (MoMA) | museum | https://www.moma.org | Complete | Yes | Likely custom |
| 77 | Statue of Liberty | monument | https://www.nps.gov/stli/index.htm | Partial | Yes | Possibly generic |
| 78 | Times Square | landmark | https://www.timessquarenyc.org | Partial | Yes | Possibly generic |

**Notes per venue:**

- **69 (AMNH):** `amnh.org` is correct. Generic description. No Instagram. Good candidate for generic or custom scraper.
- **71 (Brooklyn Bridge):** URL is NYC DOT infrastructure page, not an events site. Landmark with no event calendar. **Not suitable for venue-based scraping.**
- **72 (Central Park):** `centralparknyc.org` is correct. Park events calendar. Generic description. Could work with generic scraper.
- **73 (Empire State Building):** `esbnyc.com` is correct. Observation deck; events are secondary. May have limited event content.
- **74 (Met):** `metmuseum.org` is correct. Generic description. No social URLs (Met uses @metmuseum). Major museum; likely needs custom scraper.
- **76 (MoMA):** Complete entry. `moma.org` correct. Has social links. Major museum; likely needs custom scraper.
- **77 (Statue of Liberty):** `nps.gov/stli` is correct. NPS site; may have tours/events. Generic description.
- **78 (Times Square):** `timessquarenyc.org` is correct. May have events. Generic description.

**Gap:** Venue ID 70 and 75 are missing in the sequence (not NYC-specific; just noting).

---

## 3. NYC Sources Table

| ID | Name | Type | URL | Complete? | Notes |
|----|------|------|-----|-----------|-------|
| 38 | NYC Arts | instagram | https://www.instagram.com/nycarts/ | Yes | Official NYC arts |
| 39 | Time Out New York | instagram | https://www.instagram.com/timeoutnewyork/ | Yes | Events publication |
| 40 | The Metropolitan Museum of Art | instagram | https://www.instagram.com/metmuseum/ | Yes | Met official |
| 41 | MoMA | instagram | https://www.instagram.com/themuseumofmodernart/ | Yes | MoMA official |
| 42 | Brooklyn Museum | instagram | https://www.instagram.com/brooklynmuseum/ | Yes | Brooklyn Museum official |
| 43 | NYC Parks | instagram | https://www.instagram.com/nycparks/ | Yes | NYC Parks official |
| 44 | Lincoln Center | instagram | https://www.instagram.com/lincolncenter/ | Yes | Lincoln Center official |
| 45 | Brooklyn Academy of Music | instagram | https://www.instagram.com/bam_brooklyn/ | Yes | BAM official |
| 46 | NYC.com | website | https://www.nyc.com | Yes | Events calendar |
| 47 | Gothamist | instagram | https://www.instagram.com/gothamist/ | Yes | NYC news/culture |
| 48 | Big Onion Walking Tours | website | https://bigonion.com/our-tours/ | Yes | Walking tours |
| 49 | Ellis Island Hard Hat Tours | website | https://shop.saveellisisland.org/products/novelty-hard-hat-tour | Partial | Product/shop page, not events calendar |

**Notes:**

- Sources 38–47 look complete and usable.
- **48 (Big Onion):** Tours page; may be scrapeable for tour schedules.
- **49 (Ellis Island):** Points to a product/shop URL, not an events listing. **Weak for scraping.**

---

## 4. Duplicate, Suspicious, Outdated, or Malformed Entries

### Venues

- **No duplicates** among NYC venues.
- **Brooklyn Bridge (71):** Website is infrastructure info, not events. Consider changing to a more event-oriented URL (e.g. NYC Parks or NYC tourism) or marking as non-scrapeable.
- **Generic descriptions:** Several venues use "A [type] in New York offering cultural experiences and entertainment." Consider replacing with real descriptions.
- **Missing social links:** AMNH, Met have empty Instagram; Met uses @metmuseum.

### Sources

- **No duplicates.**
- **Ellis Island Hard Hat Tours (49):** URL is a product page; not ideal for event scraping.
- **Source–venue mismatch:** Brooklyn Museum, Lincoln Center, BAM are sources but not venues. Events from these sources would not attach to venue records.

---

## 5. Rollout Readiness

| Aspect | Status | Notes |
|--------|--------|-------|
| City configured | Ready | NYC (id 2) present and correct |
| Venue count | 8 | Enough for initial testing |
| Source count | 11 | Good coverage |
| Venue URLs | Needs cleanup | Brooklyn Bridge URL not event-oriented |
| Venue completeness | Partial | Generic descriptions, some missing social |
| Source completeness | Good | 10 of 11 look complete |
| Admin/reload logic | NYC-compatible | Uses `city_name`; "New York" matches |

**Verdict:** NYC data is usable for rollout but would benefit from cleanup first.

---

## 6. Cleanup Recommendations

### High priority

1. **Brooklyn Bridge (71):**  
   - Option A: Change `website_url` to an events-oriented page (e.g. NYC Parks events, NYC tourism) if one exists.  
   - Option B: Leave as-is and treat as non-scrapeable landmark (no venue-based scraping).

2. **Add Met Instagram:** Set `instagram_url` to `https://www.instagram.com/metmuseum/` for venue 74.

3. **Add AMNH Instagram:** Set `instagram_url` to `https://www.instagram.com/amnh/` (or correct handle) for venue 69.

### Medium priority

4. **Add Brooklyn Museum venue:** Create venue for Brooklyn Museum (e.g. `brooklynmuseum.org`) so source 42 can attach events to a venue.

5. **Add Lincoln Center venue:** Create venue for Lincoln Center (e.g. `lincolncenter.org`) so source 44 can attach events to a venue.

6. **Add BAM venue:** Create venue for Brooklyn Academy of Music (e.g. `bam.org`) so source 45 can attach events to a venue.

### Low priority

7. **Improve descriptions:** Replace generic "A [type] in New York offering cultural experiences and entertainment." with real descriptions for AMNH, Brooklyn Bridge, Central Park, Empire State Building, Met, Statue of Liberty, Times Square.

8. **Ellis Island source (49):** Consider changing URL to an events/schedule page if available, or document as low-priority for scraping.

### Optional

9. **Venue ID gaps:** IDs 70 and 75 are unused. No action required; IDs need not be sequential.

---

## 7. Admin/Reload Logic Notes

- **load-all-data** and **reload-venues-from-json** match venues to cities by `city_name` (case-insensitive). "New York" in venues matches city "New York".
- **reload-sources** matches sources by name; `city_id` is stored from JSON.
- No NYC-specific logic in reload flows; NYC is handled like other cities.
