# Scraper Date/Time Extraction and Saving Issues

## Overview
Analysis of why dates and times are not being saved correctly by the scraper.

## Issues Found

### 1. **Variable Scope and Assignment Issues in OCMA Extraction**

**Location:** `scripts/venue_event_scraper.py` lines 2949-2990

**Problem:**
- `start_date`, `start_time`, and `end_time` are updated inside the `if match:` block when parsing from event pages
- However, these variables are initialized earlier (lines 2741, 2771-2772) from calendar listing parsing
- If the event page parsing fails or doesn't find a match, the variables might remain as `None` even if they were extracted from the calendar listing
- The `break` statement on line 2990 exits the loop, but if parsing fails silently, the variables won't be updated

**Example:**
```python
# Line 2741: Initialized from calendar listing
start_date = None
if date_str:
    start_date = datetime.strptime(date_str, "%B %d, %Y").date()

# Lines 2949-2990: Updated from event page
if match:
    try:
        start_date = datetime.strptime(date_str, "%B %d, %Y").date()  # This might fail silently
    except:
        pass  # If this fails, start_date might remain None even if it was set earlier
```

**Fix Needed:**
- Ensure that if event page parsing fails, we still use the values from calendar listing
- Add better error handling and logging
- Don't overwrite valid values with `None`

### 2. **Single Time Pattern Loop Issue**

**Location:** `scripts/venue_event_scraper.py` lines 3002-3005

**Problem:**
- The `match` variable is set inside a loop (line 3004) but the `if match:` check is outside the loop (line 3005)
- This means it only checks the last element's match, not breaking early when a match is found
- Should break immediately when a match is found

**Current Code:**
```python
for elem in date_time_elements:
    elem_text = elem.get_text(strip=True)
    match = single_time_pattern.search(elem_text)
if match:  # This is OUTSIDE the loop - only checks last match
    # Process match
```

**Fix Needed:**
- Move the `if match:` check inside the loop and break when found

### 3. **Missing End Date Extraction for OCMA Events**

**Location:** `scripts/venue_event_scraper.py` line 3217

**Problem:**
- OCMA events always set `'end_date': None` in the event dictionary (line 3217)
- The event page parsing doesn't extract `end_date` for single-day events
- For multi-day events, there's no logic to extract end dates from OCMA pages

**Current Code:**
```python
events.append({
    'start_date': start_date.isoformat() if start_date else None,
    'end_date': None,  # Always None for OCMA events
    ...
})
```

**Fix Needed:**
- Add logic to extract end dates from event pages if available
- For exhibitions, check for date ranges in the page content

### 4. **Silent Failure in Date/Time Parsing**

**Location:** Multiple locations with `except: pass`

**Problem:**
- Many date/time parsing blocks have `except: pass` which silently swallows errors
- This makes debugging difficult and can cause dates/times to be `None` without clear indication why

**Examples:**
- Line 2751: `except: pass` - date parsing failure
- Line 2787: `except: pass` - time parsing failure
- Line 2960: `except: pass` - date parsing failure in event page

**Fix Needed:**
- Add specific exception handling
- Log warnings when parsing fails
- Don't silently fail - at least log what went wrong

### 5. **Time String Format Mismatch**

**Location:** `scripts/venue_event_scraper.py` lines 2932-2933, 2942-2943

**Problem:**
- When creating time strings from parsed groups, the format is `f"{match.group(2)}:{match.group(3)} {match.group(6)}.m."`
- This creates strings like `"5:00 p.m."` or `"5:00 a.m."`
- But the regex pattern on line 2964 expects `r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?'` which should match, but the format might be inconsistent

**Current Code:**
```python
start_time_str = f"{match.group(2)}:{match.group(3)} {match.group(6)}.m."  # "5:00 p.m."
# Later...
time_match = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', start_time_str.lower())  # Should match "5:00 p.m."
```

**Fix Needed:**
- Ensure consistent time string formatting
- Test that the regex patterns match the formatted strings

### 6. **Missing Validation Before Adding to Event Dictionary**

**Location:** `scripts/venue_event_scraper.py` lines 3213-3232

**Problem:**
- Events are added to the list even if `start_date` is `None`
- No validation that required fields are present before creating the event dictionary
- This can lead to events being saved with missing dates/times

**Current Code:**
```python
events.append({
    'start_date': start_date.isoformat() if start_date else None,  # Could be None
    'start_time': start_time.isoformat() if start_time else None,  # Could be None
    ...
})
```

**Fix Needed:**
- Add validation before appending to events list
- Skip events that don't have required fields (at minimum, `start_date`)
- Log warnings for events with missing times

### 7. **Database Save Code Expects String Format**

**Location:** `app.py` lines 2265-2284

**Problem:**
- The database save code expects time strings in `'%H:%M:%S'` or `'%H:%M'` format
- But the scraper returns `.isoformat()` which returns `"17:00:00"` format
- This should work, but there might be edge cases where the format doesn't match

**Current Code:**
```python
# Scraper returns:
'start_time': start_time.isoformat() if start_time else None  # Returns "17:00:00"

# Database save expects:
event.start_time = dt.strptime(start_time_str, '%H:%M:%S').time()  # Should parse "17:00:00"
```

**Fix Needed:**
- Ensure consistent format between scraper output and database input
- Add format validation

## Recommended Fixes Priority

1. **HIGH**: Fix variable scope issues in OCMA extraction (Issue #1)
2. **HIGH**: Fix single time pattern loop (Issue #2)
3. **MEDIUM**: Add end date extraction for OCMA events (Issue #3)
4. **MEDIUM**: Replace silent failures with proper error handling (Issue #4)
5. **LOW**: Validate events before adding to list (Issue #6)
6. **LOW**: Ensure consistent time string formatting (Issue #5, #7)

## Testing Recommendations

1. Test OCMA event scraping with the specific URL: `https://ocma.art/calendar/art-happy-hour-pop-up-talk-december-25/`
2. Add logging to track:
   - When dates/times are extracted from calendar listing
   - When dates/times are updated from event page
   - When dates/times are added to event dictionary
   - When dates/times are saved to database
3. Verify that events have dates/times after scraping
4. Check database to ensure saved events have correct dates/times

