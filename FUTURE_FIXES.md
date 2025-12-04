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




