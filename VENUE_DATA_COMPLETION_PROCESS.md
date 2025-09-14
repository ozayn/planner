# Venue Data Completion Process

## Overview
This document outlines the systematic approach we used to successfully complete missing venue data, specifically for the 5 London venues that had the least filled fields.

## Process Steps

### 1. Identify Incomplete Venues
- Create analysis script to find venues with least filled fields
- Focus on venues with missing: phone_number, email, tour_info, social media URLs
- Example: Found 5 London venues with only 55.6% completion (10/18 fields)

### 2. Clear Incorrect Data First
- Clear existing incorrect image_url fields to avoid confusion
- Create backup before making changes
- Save backups in `data/backups/` directory for organization

### 3. Fetch Google Maps Images
- Use `get_google_maps_image()` function from `scripts/utils.py`
- Function uses Google Places API to:
  - Search for venue by name + city + country
  - Get place details including photos
  - Construct proper Google Maps image URLs with photo references
- Example usage:
  ```python
  from scripts.utils import get_google_maps_image
  image_url = get_google_maps_image(
      venue_name="Victoria and Albert Museum",
      city="London",
      country="United Kingdom"
  )
  ```

### 4. Fill Missing Venue Details
- Use real, accurate information for each venue:
  - **Phone numbers**: Official venue contact numbers
  - **Email addresses**: Official venue email addresses
  - **Tour info**: Accurate admission and tour information
  - **Social media**: Official Instagram, Facebook, Twitter, YouTube, TikTok handles/URLs

### 5. Update venues.json File
- Modify the JSON file with new data
- Create backup before each update
- Verify all changes are properly saved

### 6. Reload to Database
- Use modified load script that works with current JSON format
- Clear existing venues and reload from updated JSON
- Verify data integrity and show sample results

## Tools and Scripts Used

### Key Functions
- `get_google_maps_image()` in `scripts/utils.py` - Fetches Google Maps images
- `load_venues_from_json()` - Loads venues from JSON to database

### Backup Organization
- All backups saved in `data/backups/` directory
- Descriptive backup names with timestamps
- Example: `venues.json.backup.before_image_update`

## Example Results

### Before (55.6% completion):
- Missing: phone_number, email, tour_info, instagram_url, facebook_url, twitter_url, youtube_url, tiktok_url

### After (100% completion):
- ✅ Phone: +44 20 7942 2000
- ✅ Email: info@vam.ac.uk
- ✅ Tour Info: Free admission. Guided tours available daily...
- ✅ Social Media: @vamuseum (Instagram), @V_and_A (Twitter), etc.
- ✅ Google Maps Image: Proper photo reference URL

## Success Metrics
- **Victoria and Albert Museum**: 100% completion
- **Natural History Museum**: 100% completion
- **Tate Britain**: 100% completion
- **Royal Academy of Arts**: 100% completion
- **Science Museum**: 100% completion

## Lessons Learned
1. Always create backups before making changes
2. Clear incorrect data first to avoid confusion
3. Use real venue information, not placeholder data
4. Organize backups in dedicated directories
5. Verify data integrity after database reload
6. The Google Maps API method works reliably for fetching venue images

## Future Applications
This process can be applied to any venue with incomplete data:
1. Run analysis to identify incomplete venues
2. Follow the same systematic approach
3. Use the established tools and backup organization
4. Verify results before considering complete
