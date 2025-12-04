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



## Google Calendar Export - Exhibition End Date Not Working

**Date:** 2025-01-24  
**Status:** Open  
**Priority:** Medium

### Problem
When exporting exhibitions to Google Calendar from the main page (index.html), the end date is not being used correctly. The calendar export shows the same date for both start and end (e.g., "Aug 2, 2025 - Aug 2, 2025" instead of "Aug 2, 2025 - Feb 1, 2026").

### Details
- **Event ID tested:** 23
- **Database has correct data:** Start Date: 2025-08-02, End Date: 2026-02-01
- **API returns correct data:** `to_dict()` includes `end_date: "2026-02-01"`
- **Frontend issue:** When clicking the calendar button, `event.end_date` appears to be missing or null in the JavaScript event object
- **Location:** `templates/index.html` - `addToCalendar()` function and `generateGoogleCalendarUrl()` function

### Symptoms
- Console logs show `endDate_obj: Sat Aug 02 2025 02:00:00` (wrong time, should be 00:00:00)
- Console logs show `endDate_iso: '2025-08-02'` (same as start date)
- Google Calendar URL shows `dates=20250802/20250802` (both dates are the same)
- Debug logs added to check `event.end_date` are not appearing (suggests browser cache or code path issue)

### Investigation Needed
1. Verify that `event.end_date` is present in the event object when `addToCalendar()` is called
2. Check if events are being modified/filtered after loading from API
3. Verify the `/api/events` response includes `end_date` for exhibitions
4. Check if there's any code that removes or modifies `end_date` after events are loaded
5. Ensure browser cache is cleared when testing fixes

### Code Locations
- `templates/index.html` line ~5421: `addToCalendar()` function
- `templates/index.html` line ~5520: `generateGoogleCalendarUrl()` function
- `app.py` line ~1100: `/api/events` endpoint
- `app.py` line ~620: `Event.to_dict()` method (confirmed working correctly)

### Fix Strategy
1. Add comprehensive logging to verify `event.end_date` exists in the event object
2. If `end_date` is missing, trace back to where events are loaded/stored
3. Fix the date parsing/formatting logic to correctly use `end_date` when available
4. Ensure all-day events use the correct date format for Google Calendar







