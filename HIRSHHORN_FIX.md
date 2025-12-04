# Hirshhorn Museum Scraping Fix

## Problem
When scraping Hirshhorn Museum, 0 events were being saved to the database, even though the scraper found 5 exhibitions.

## Root Causes Found

1. **Date Extraction Bug**: The `date_text` variable was being reused across loop iterations, causing all exhibitions to get the same date range (2024-09-29 to 2026-01-19).

2. **Duplicate Detection Too Strict**: The duplicate check was using URL, which caused issues since all exhibitions from listing pages share the same URL.

## Fixes Applied

### 1. Fixed Date Extraction (`scripts/venue_event_scraper.py`)
- **Before**: `date_text` was checked with `if 'date_text' not in locals() or not date_text:` which reused the variable from previous iterations
- **After**: Each heading now extracts its own fresh `date_text = None` at the start of each loop iteration

### 2. Fixed Duplicate Detection (`app.py`)
- **Before**: Checked by `title + URL + venue + city`
- **After**: For exhibitions, now checks by `title + venue + start_date` (URL excluded since listing pages share URLs)

## Testing

To test the fix:
1. Select Hirshhorn Museum only
2. Select "Exhibition" event type
3. Select a time range (try "this_month" or "next_month" to catch exhibitions that span long periods)
4. Click "Scrape Selected Venues"
5. Events should now be saved and displayed

## Known Limitations

The Hirshhorn listing page (`/exhibitions-events/`) may display all exhibitions with the same date range shown. If each exhibition doesn't have its own unique date in the listing, they may still get similar dates. To get accurate dates, the scraper would need to visit each individual exhibition page, which would require additional logic.

## Next Steps

If exhibitions still share the same date range, we may need to:
1. Extract dates from individual exhibition pages (slower but more accurate)
2. Use a Hirshhorn-specific scraper that understands their page structure better









