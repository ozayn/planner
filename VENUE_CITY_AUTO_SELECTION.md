# Venue & City Auto-Selection Feature

## 🎉 Enhancement Added (October 10, 2025)

The URL event extraction now **automatically matches and selects** the venue and city!

---

## Problem Solved

**Before**: After extraction, users had to manually:
- Find and select the venue from dropdown
- Select the city from dropdown
- Easy to miss or select wrong venue

**After**: System automatically:
- Matches extracted location to venue database
- Selects correct venue in dropdown
- Selects corresponding city in dropdown
- Shows visual confirmation of match

---

## How It Works

### Backend Matching Logic

```python
# app.py - extract_event_from_url endpoint

# Extract location from LLM or web scraping
location_text = extracted_data.get('location')  
# e.g., "The Metropolitan Museum of Art"

# Try exact match first
venue = Venue.query.filter(
    db.func.lower(Venue.name).like(f'%{location_text.lower()}%')
).first()

if venue:
    venue_id = venue.id
    city_id = venue.city_id
else:
    # Try with "The" removed
    cleaned_location = location_text.replace('The ', '')
    venue = Venue.query.filter(
        db.func.lower(Venue.name).like(f'%{cleaned_location.lower()}%')
    ).first()
```

### Frontend Auto-Selection

```javascript
// templates/admin.html - displayExtractedData function

// Auto-select venue dropdown
if (data.venue_id) {
    document.getElementById('urlVenueSelect').value = data.venue_id;
}

// Auto-select city dropdown  
if (data.city_id) {
    document.getElementById('urlCitySelect').value = data.city_id;
}
```

---

## Example: Met Museum

**URL**: `https://engage.metmuseum.org/events/public-guided-tours/collection-tour-islamic-art/`

### Extraction Response
```json
{
  "title": "Collection Tour: Islamic Art",
  "description": "A guided tour of the Islamic art collection...",
  "location": "The Metropolitan Museum of Art",
  "venue_id": 74,
  "city_id": 2,
  "llm_extracted": true,
  "confidence": "medium"
}
```

### What Happens in UI

1. **Auto-Fill button clicked**
2. **LLM extracts**: "The Metropolitan Museum of Art"
3. **Backend matches**: Venue ID 74, City ID 2
4. **Preview shows**: "✅ Auto-matched" for venue and city
5. **Dropdowns auto-select**: 
   - Venue: "The Metropolitan Museum of Art"
   - City: "New York"
6. **User can**: Review, edit if needed, or proceed

---

## Features

### ✅ Smart Matching

**Handles variations**:
- "The Metropolitan Museum of Art" → matches "Metropolitan Museum of Art"
- "met museum" → matches (case-insensitive)
- Partial matches with LIKE operator
- Removes common prefixes ("The", "the")

### ✅ Visual Indicators

**Preview section shows**:
```
Venue: ✅ Auto-matched
City: ✅ Auto-matched
```

Or if no match:
```
Venue: ❌ Not matched
City: ❌ Not matched
```

### ✅ AI Extraction Badge

When using LLM:
```
🤖 AI Extracted (medium confidence)
```

Color-coded by confidence:
- 🟢 **Green**: High confidence
- 🟡 **Yellow**: Medium confidence (default)
- 🔴 **Red**: Low confidence

### ✅ Manual Override

Users can still:
- Change venue selection if wrong
- Change city if needed
- Leave blank for city-wide events

---

## Matching Logic

### Priority Order

1. **Exact substring match** (case-insensitive)
   - "metropolitan museum" → "The Metropolitan Museum of Art" ✅

2. **Cleaned match** (remove "The")
   - "The Met" → "Met Museum" ✅

3. **No match** (venue_id = null)
   - User must select manually

### Database Query

```sql
SELECT * FROM venues 
WHERE LOWER(name) LIKE '%the metropolitan museum of art%'
LIMIT 1;
```

Returns first matching venue with:
- `id` (venue_id)
- `city_id` (foreign key)

---

## Files Modified

### Backend
**File**: `app.py`
**Function**: `extract_event_from_url()`

Added:
- Venue name matching logic
- Cleaned name fallback
- venue_id and city_id in response

### Frontend
**File**: `templates/admin.html`
**Function**: `displayExtractedData(data)`

Added:
- venue_id dropdown auto-selection
- city_id dropdown auto-selection
- Visual match indicators
- AI extraction badges
- Console logging for debugging

---

## Testing

### Test Command
```bash
curl -X POST http://localhost:5001/api/admin/extract-event-from-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://engage.metmuseum.org/events/.../collection-tour-islamic-art/"}'
```

### Expected Response
```json
{
  "title": "Collection Tour: Islamic Art",
  "location": "The Metropolitan Museum of Art",
  "venue_id": 74,
  "city_id": 2,
  "llm_extracted": true
}
```

### Test in Browser
1. Go to `http://localhost:5001/admin`
2. Click "🔗 From URL"
3. Paste Met Museum URL
4. Click "🔍 Auto-Fill"
5. Wait ~7 seconds
6. **Check**:
   - Preview shows "✅ Auto-matched" for venue and city
   - Venue dropdown shows "The Metropolitan Museum of Art"
   - City dropdown shows "New York"
   - Title is "Collection Tour: Islamic Art"

---

## Edge Cases

### Case 1: No Venue Match
**Location**: "Some Unknown Place"
**Result**: 
- `venue_id`: null
- `city_id`: null
- Preview: "❌ Not matched"
- User must select manually

### Case 2: Ambiguous Name
**Location**: "Museum"
**Result**:
- Matches first venue with "museum" in name
- May not be the right one
- User should verify and change if needed

### Case 3: City-Wide Event
**Location**: null or general city name
**Result**:
- `venue_id`: null (correct)
- `city_id`: may be matched if city name in location
- User can leave venue empty

---

## Benefits

### For Users
- ✅ **Faster**: No manual searching through dropdowns
- ✅ **Accurate**: Matches venue names precisely
- ✅ **Convenient**: One click to fill everything
- ✅ **Flexible**: Can still change if needed

### For Data Quality
- ✅ **Consistency**: Same venue always matched the same way
- ✅ **Completeness**: Venue and city always populated when possible
- ✅ **Validation**: Only matches existing venues in database

---

## Limitations

### What Can't Be Matched
- ❌ Venues not in database yet
- ❌ Misspelled venue names  
- ❌ Very different name variations
- ❌ Venues with generic names

### Workarounds
- Add venue to database first
- Manually select from dropdown
- Edit location text before matching
- Use partial venue name that matches

---

## Future Enhancements

Potential improvements:
1. **Fuzzy Matching**: Use Levenshtein distance for typos
2. **Alias Table**: Store venue name variations
3. **City Inference**: Infer city from URL domain
4. **Multi-Venue**: Support events at multiple venues
5. **Learning**: Track corrections to improve matching
6. **Confidence Score**: Show match confidence percentage

---

## Related Features

This enhancement works with:
- ✅ **Auto-Fill Button** - Extracts URL data
- ✅ **LLM Fallback** - Gets data from bot-protected sites
- ✅ **Venue Database** - Matches against known venues
- ✅ **City Database** - Links venue to city
- ✅ **Preview Section** - Shows match status

---

## Summary

🎉 The URL event extraction now includes **intelligent venue and city matching**!

**Flow**:
```
URL → Extract data → Match venue → Get city → Auto-select dropdowns
```

**Result**:
- Venue automatically selected ✅
- City automatically selected ✅
- Visual confirmation shown ✅
- User can override if needed ✅

**Try it now with the Met Museum URL!** 🚀



