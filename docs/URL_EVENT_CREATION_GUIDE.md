# URL Event Creation Feature Guide

## Overview
The "Create Events from URL" feature allows you to automatically extract event information from any web page and create events in your database. This is particularly useful for scraping events from venue websites, museum tour pages, and event listing sites.

## Features

### ✅ Auto-Fill Button (FIXED)
The Auto-Fill button now works correctly! Previous issue with event parameter passing has been resolved.

**What Changed:**
- Removed problematic inline `onclick` handler with event parameter
- Added button ID (`autoFillBtn`) for direct reference
- Simplified `autoFillFromUrl()` function to not require parameters
- Added proper event listener in `openUrlScraperModal()` function

### 🔍 Smart Extraction
The system automatically extracts:
- **Title**: From page title, h1 tags, or URL structure
- **Description**: From meta tags or content sections
- **Start/End Times**: From schedule text (e.g., "6:30pm - 7:30pm")
- **Location**: Meeting points (e.g., "Gallery 534")
- **Image**: From Open Graph tags or first meaningful image
- **Schedule**: Recurring patterns (e.g., "Fridays", "Weekdays")

### 📅 Recurring Event Support
Detects and handles recurring schedules:
- **Day-specific**: "Fridays 6:30pm" → creates events for all Fridays in period
- **Weekdays**: "Weekdays 3pm" → creates events Monday-Friday
- **Weekends**: "Saturdays and Sundays" → creates events for weekends
- **Date ranges**: Choose today, tomorrow, this week, this month, or custom period

### 🛡️ Bot Protection Bypass + LLM Fallback
**Two-tier extraction system**:

**Tier 1: Web Scraping** (Primary)
- Uses `cloudscraper` library for bot detection bypass
- Mimics real Chrome browser on macOS
- Includes realistic headers
- Retry logic with exponential backoff (3 attempts)
- Works on Railway deployment (no browser automation needed)

**Tier 2: LLM Extraction** (Automatic Fallback)
- Activates when web scraping fails or bot detection triggers
- Uses Google Gemini, Groq, or other LLM providers
- Infers event details from URL structure and knowledge
- Returns data marked as `llm_extracted: true`
- Includes confidence level (low/medium/high)
- Works for major venues with well-known events

## How to Use

### Step 1: Open the Modal
1. Navigate to the Admin Dashboard at `http://localhost:5001/admin`
2. Scroll to the Events section
3. Click the **🔗 From URL** button (purple button)

### Step 2: Enter URL
1. Paste the event page URL in the "Event Page URL" field
2. Examples of good URLs:
   - Museum tour pages
   - Event detail pages
   - Venue calendar entries

### Step 3: Click Auto-Fill
1. Click the **🔍 Auto-Fill** button
2. Wait for extraction (button shows "⏳ Extracting...")
3. Review the extracted data in the preview section

### Step 4: Review and Edit
The preview section shows:
- All extracted data fields
- Editable form fields for corrections
- Read-only detected schedule

**Editable Fields:**
- Event Title
- Description
- Start Time
- End Time
- Location/Meeting Point

### Step 5: Configure Options
1. **Venue**: Select if event is venue-specific (optional)
2. **City**: Choose the city (required)
3. **Time Period**: Select when to create events
   - Today Only
   - Tomorrow Only
   - This Week (default)
   - This Month
   - Custom Period (specify dates)

### Step 6: Create Events
1. Click **🔗 Create Events** button
2. System will:
   - Scrape the URL (if not already extracted)
   - Use your edited data
   - Create events for matching days in the period
   - Skip duplicates (same URL + date + city)
   - Refresh the events table

## API Endpoints

### Extract for Preview
```bash
POST /api/admin/extract-event-from-url
Content-Type: application/json

{
  "url": "https://example.com/events/tour"
}
```

**Response:**
```json
{
  "title": "Museum Highlights Tour",
  "description": "Join us for a guided tour...",
  "start_time": "18:30:00",
  "end_time": "19:30:00",
  "location": "Gallery 534",
  "image_url": "https://example.com/image.jpg",
  "schedule_info": "Fridays 6:30pm - 7:30pm",
  "days_of_week": ["friday"]
}
```

### Create Events from URL
```bash
POST /api/admin/scrape-event-from-url
Content-Type: application/json

{
  "url": "https://example.com/events/tour",
  "venue_id": 123,
  "city_id": 1,
  "time_period": "this_week",
  "title": "Custom Title",
  "description": "Custom description",
  "start_time": "18:30",
  "end_time": "19:30",
  "location": "Custom location"
}
```

**Response:**
```json
{
  "events_created": 4,
  "events": [
    {
      "title": "Museum Highlights Tour",
      "start_date": "2025-10-10",
      "start_time": "18:30:00",
      "end_time": "19:30:00",
      "description": "Join us for a..."
    }
  ],
  "schedule_info": "Fridays 6:30pm - 7:30pm"
}
```

## Testing

### Test with cURL
```bash
# Test extraction
curl -X POST http://localhost:5001/api/admin/extract-event-from-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Test event creation (requires valid venue_id and city_id)
curl -X POST http://localhost:5001/api/admin/scrape-event-from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/events/tour",
    "city_id": 1,
    "time_period": "today"
  }'
```

### Test URLs
Good test URLs (publicly accessible):
- Simple pages: https://example.com
- Event pages: https://www.metmuseum.org (check their events section)
- Tour pages: Museum and venue tour pages

**Note**: Some sites have strong bot protection that even cloudscraper can't bypass. These will show "Pardon Our Interruption" or similar messages.

## Troubleshooting

### Auto-Fill Button Not Working
✅ **FIXED** - The button now has proper event listeners and should work correctly.

**If you still experience issues:**
1. Open browser console (F12)
2. Check for JavaScript errors
3. Verify the button has ID `autoFillBtn`
4. Check network tab for API call to `/api/admin/extract-event-from-url`

### Bot Detection / Extraction Fails
**Symptoms**: Returns "Pardon Our Interruption" or generic titles

**Solutions**:
- Try the URL multiple times (retry logic should work)
- Some sites are harder to scrape (e.g., Cloudflare protection)
- Consider manual entry for heavily protected sites
- Check if site requires authentication

### No Data Extracted
**Symptoms**: All fields show "Not found" or null

**Causes**:
- Page structure doesn't match extraction patterns
- JavaScript-rendered content (not in HTML source)
- Paywalled or restricted content

**Solutions**:
- Manually fill in the fields after Auto-Fill
- Use the editable form fields to correct data
- Some fields may need manual entry

### Events Not Created
**Symptoms**: "0 events created" message

**Causes**:
- No matching days in the period (e.g., "Fridays" but period has no Fridays)
- Duplicate events already exist
- Missing required fields (city_id)

**Solutions**:
- Check schedule matches your period
- Try a longer period (e.g., this month)
- Query existing events to check for duplicates
- Ensure city is selected

## Technical Details

### Extraction Function
Located in: `scripts/url_event_scraper.py`

**Key Functions:**
- `extract_event_data_from_url(url)`: Extracts data for preview
- `scrape_event_from_url(...)`: Creates events in database
- `_extract_title()`: Title extraction logic
- `_extract_description()`: Description extraction
- `_extract_image()`: Image URL extraction
- `_extract_meeting_point()`: Location extraction
- `_extract_schedule()`: Schedule and time parsing

### Schedule Detection
Uses regex patterns to detect:
```python
# Examples:
"Fridays 6:30pm - 7:30pm"  → friday, 18:30, 19:30
"Weekdays 3:00pm"          → mon-fri, 15:00, 16:00 (assumed)
"Saturday 10am-12pm"       → saturday, 10:00, 12:00
```

### Time Parsing
- Handles 12-hour format (am/pm)
- Assumes 1-hour duration if end time not specified
- Converts to 24-hour time objects

### Duplicate Prevention
Checks for existing events with:
- Same URL
- Same start_date
- Same city_id
- Same venue_id (if specified)

## Best Practices

1. **Always Use Auto-Fill**: Let the system extract first, then edit
2. **Review Extracted Data**: Verify accuracy before creating
3. **Choose Appropriate Period**: Match schedule to period
4. **Select Correct Venue**: Helps with location and organization
5. **Edit as Needed**: All fields are editable after extraction
6. **Check for Duplicates**: System skips duplicates automatically

## Known Limitations

1. **JavaScript Content**: Can't extract dynamically loaded content
2. **Bot Protection**: Some sites block automated access
3. **Complex Schedules**: May not detect all schedule patterns
4. **Image Quality**: First image may not always be the best
5. **Time Zones**: Uses local time parsing (no timezone detection)

## Future Enhancements

Potential improvements:
- LLM-based extraction for complex pages
- Screenshot capture for JavaScript sites
- Better schedule pattern recognition
- Multi-venue event support
- Timezone detection
- Event category detection
- More robust image selection
- Support for multi-day events

