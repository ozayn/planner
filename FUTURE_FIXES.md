# Future Fixes

## Date/Time Extraction for OCMA Events

### Issue
Date and time extraction is not working correctly for OCMA (Orange County Museum of Art) events. Events are being scraped but times are not being extracted properly.

### Expected Format
OCMA uses the format: "December 5, 2025, 5:00–6:00 PM" where the am/pm is shared at the end (not "5:00 PM–6:00 PM").

### What We've Tried
1. Fixed regex patterns to handle shared am/pm format ("5:00–6:00 PM")
2. Fixed logic bug where event page parsing only ran when status code was NOT 200 (now runs when status IS 200)
3. Prioritized h2 tags for date/time extraction (OCMA often puts date/time in h2)
4. Ensured actual date/time objects are updated (not just strings)
5. Moved pattern compilation outside loops for efficiency
6. Added extensive logging to trace extraction

### Files Modified
- `scripts/venue_event_scraper.py` - `_extract_ocma_calendar_events` function (lines ~2580-3230)

### Next Steps to Debug
1. Test with actual OCMA event page HTML to see exact format
2. Check if event pages are being fetched successfully (check logs)
3. Verify regex patterns match the actual HTML text
4. Check if variables are being overwritten after extraction
5. Test with a specific event URL: `https://ocma.art/calendar/art-happy-hour-pop-up-talk-december-25/`

### Related Code Sections
- Calendar listing pattern matching: lines ~2642-2675
- Event page date/time extraction: lines ~2886-3040
- Date/time parsing: lines ~2740-2803
- Event dictionary creation: lines ~3212-3229

## Date/Time Extraction for SAAM Events

### Issue
Date and time extraction is not working correctly for SAAM (Smithsonian American Art Museum) events. Events are being scraped but times are not being extracted properly.

### Expected Format
SAAM uses various formats for dates and times:
- "Friday, January 23, 2026, 12:15 – 1:15pm EST"
- "January 23, 2026, 1 – 2pm" (single digit hours without colons)
- "Wednesday, December 17, 2025, 10:30am EST"

### What We've Tried
1. Multiple regex patterns for different time formats (with/without colons, single digit hours)
2. Pattern matching for date/time ranges in page text
3. Fallback to schema.org structured data extraction
4. Time range extraction with shared am/pm format
5. Duration calculation when end_time is missing (assumes 1 hour)
6. Extensive pattern matching in `scrape_event_detail` function

### Files Modified
- `scripts/saam_scraper.py` - `scrape_event_detail` function (lines ~1155-1354)
- `scripts/url_event_scraper.py` - SAAM event page detection and extraction (lines ~41-82)

### Next Steps to Debug
1. Test with actual SAAM event page HTML to see exact format used on current pages
2. Check if event pages are being fetched successfully (check logs)
3. Verify regex patterns match the actual HTML text on SAAM pages
4. Check if time variables are being overwritten or reset after extraction
5. Test with specific SAAM event URLs to identify the exact format
6. Check if time extraction logic is being bypassed or returning None
7. Verify that extracted times are properly saved to the event dictionary
8. Check database to see if times are None or missing for SAAM events

### Related Code Sections
- Date/time extraction in `scrape_event_detail`: lines ~1155-1354
- Pattern matching for time ranges: lines ~1163-1254
- Schema.org fallback extraction: lines ~1383-1449
- Time validation and formatting: lines ~1353-1409
- Event dictionary creation with times: lines ~1829-1833
- URL event scraper SAAM detection: `scripts/url_event_scraper.py` lines ~41-82

## African Art Museum Scraper - Date Range and Image Extraction

### Issue
The African Art Museum scraper is not correctly extracting date ranges and images from the listing page. The scraper needs to:
1. Extract date ranges like "June 3, 2024 – December 31, 2026" from the main listing page
2. Extract images from the listing page exhibition cards
3. Handle "ongoing", "permanent", and "indefinitely" exhibitions by setting end date to 3 years from now
4. Only create valid exhibitions (filter out navigation items like Calendar, Marketplace, etc.)

### Current Status
- Scraper exists but is not working correctly
- Button is disabled in admin interface
- Should not be called automatically

### Files Modified
- `scripts/african_art_scraper.py` - Main scraper implementation
- `app.py` - API endpoint `/api/admin/scrape-african-art` (lines ~6827-6877)
- `templates/admin.html` - Button and JavaScript function (lines ~1990, ~8936-8957)

### Next Steps to Fix
1. Debug why date ranges aren't being extracted from listing page HTML
2. Verify container detection logic for finding exhibition cards
3. Test date range parsing with actual HTML from listing page
4. Ensure image extraction is finding images in the correct containers
5. Verify filtering logic is working to exclude non-exhibition items
6. Test with actual page HTML to understand the structure better

### Related Code Sections
- Exhibition scraping: `scripts/african_art_scraper.py` - `scrape_african_art_exhibitions` function
- Date extraction: lines ~406-480
- Image extraction: lines ~448-481
- URL validation: lines ~294-316
- API endpoint: `app.py` lines ~6827-6877

## Scraper Timeout Handling Pattern (WORKING SOLUTION)

### Issue
Scrapers were causing gunicorn worker timeouts in production, especially when scraping multiple detail pages. The default 10-15 second timeouts were too long, and exceptions weren't being caught properly, causing entire workers to hang and crash.

### Solution Applied (Asian Art Scraper - December 2025)

#### 1. **Reduced Timeout Values**
- **Detail page requests**: Use `timeout=(3, 5)` - 3 seconds connect, 5 seconds read
- **Listing page requests**: Use `timeout=(3, 8)` - 3 seconds connect, 8 seconds read
- This prevents any single request from taking too long

#### 2. **Comprehensive Exception Handling**
Import all timeout-related exceptions:
```python
from requests.exceptions import Timeout, RequestException, ConnectionError, ReadTimeout, ConnectTimeout
from socket import timeout as SocketTimeout
```

Catch all timeout exceptions explicitly:
```python
except (Timeout, ReadTimeout, ConnectTimeout, SocketTimeout) as e:
    logger.warning(f"   ⚠️ Timeout scraping event detail {url}: {type(e).__name__}")
    return None
except (ConnectionError, RequestException) as e:
    logger.warning(f"   ⚠️ Connection error scraping event detail {url}: {type(e).__name__}")
    return None
except Exception as e:
    logger.warning(f"   ⚠️ Error scraping event detail {url}: {type(e).__name__} - {str(e)[:100]}")
    return None
```

#### 3. **Fallback to Listing Data**
When detail page scraping fails (timeout or error), fall back to listing page data instead of failing completely:
```python
event_data = scrape_event_detail(scraper, full_url)

if event_data:
    # Merge detail page data with listing data
    ...
elif listing_data.get('title'):
    # If detail page failed, use listing data as fallback
    listing_data['source_url'] = full_url
    listing_data['event_type'] = 'event'
    listing_data['organizer'] = VENUE_NAME
    # ... populate required fields
    events.append(listing_data)
```

#### 4. **Key Principles**
- **Fail fast**: Shorter timeouts prevent workers from hanging
- **Graceful degradation**: Use listing data when detail pages fail
- **Comprehensive exception catching**: Catch socket-level, connection-level, and request-level timeouts
- **Continue processing**: Don't let one failed request stop the entire scraping process
- **Better logging**: Log exception type names, not full error messages to avoid log spam

### Files Modified
- `scripts/asian_art_scraper.py` - Applied timeout handling pattern to:
  - `scrape_event_detail()` function
  - `scrape_exhibition_detail()` function
  - All HTTP requests (listing pages and detail pages)

### Results
- ✅ No more gunicorn worker timeouts
- ✅ Scraping completes successfully even when some detail pages fail
- ✅ More events captured using listing data fallback
- ✅ Faster overall scraping due to shorter timeouts

### Apply to Other Scrapers
This pattern should be applied to:
- `scripts/saam_scraper.py` - Similar detail page scraping
- `scripts/african_art_scraper.py` - When reactivated
- `scripts/venue_event_scraper.py` - Already has some timeout handling, but could be improved
- Any other scraper that makes multiple HTTP requests for detail pages

### Related Commits
- `aad081e` - "Improve timeout handling: reduce timeouts and add socket-level exception catching"
- `3e15a51` - "Fix timeout issues in Asian Art scraper - add exception handling and fallback to listing data"







