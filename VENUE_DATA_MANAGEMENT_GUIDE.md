# 🏛️ Venue Data Management Guide

## 🚨 CRITICAL RULES TO PREVENT DATA ISSUES

### 📸 Image URL Management

#### ✅ CORRECT Ways to Add Image URLs:
1. **Use Google Places API**: Always fetch real photo references using `scripts/fetch_google_maps_image.py`
2. **Store as JSON**: For new venues, store as JSON string: `{"photo_reference": "real_ref", "maxwidth": 800, "base_url": "..."}`
3. **Store as raw string**: For simple cases, store just the photo reference string
4. **Never create fake references**: Don't make up photo reference strings

#### ❌ NEVER DO:
- Create fake photo references that look real but aren't
- Store image URLs without testing them first
- Mix up JSON format vs raw string format

#### 🔧 Image URL Processing Order (in Venue.to_dict()):
1. **Dict with photo_reference** → Extract photo_ref → `/api/image/{photo_ref}`
2. **JSON string starting with '{'** → Parse JSON → Extract photo_ref → `/api/image/{photo_ref}`
3. **Google Maps URL** → Extract photo reference → `/api/image/{photo_ref}`
4. **Raw photo reference** → `/api/image/{raw_string}`

### 📱 Social Media Data Management

#### ✅ CORRECT Process:
1. **Check backups first**: Look in `data/backups/` for recent backup files
2. **Restore from backup**: Use venue name matching to restore social media data
3. **Add to JSON export**: Ensure `update_venues_json.py` includes all social media fields
4. **Verify coverage**: Run validation to ensure major venues have social media

#### 🗃️ Backup File Structure:
```json
{
  "1": {
    "name": "Washington",
    "venues": [
      {
        "name": "Arena Stage",
        "instagram_url": "@arenastage",
        "facebook_url": "https://www.facebook.com/ArenaStage",
        ...
      }
    ]
  }
}
```

#### ⚠️ Social Media Field Requirements:
- **Museums**: Must have Instagram, Facebook, Twitter
- **Embassies**: Must have official diplomatic social media
- **Arts Centers**: Should have social media presence
- **Historic Sites**: May or may not have social media

### 🏛️ Venue Type Standardization

#### ✅ Standard Venue Types:
- `museum` (lowercase only)
- `historic_site` 
- `embassy`
- `arts_center`
- `theater`
- `park`
- `landmark`
- `government`
- `religious_site`
- `observation`
- `market`
- `shopping`
- `waterfront`
- `stadium`

#### 🔄 When Adding New Venue Types:
1. **Update database**: Use lowercase, underscore format
2. **Update frontend filters**: Add to venue type checkboxes
3. **Update JavaScript**: Include in `getSelectedVenueTypes()` function
4. **Test filtering**: Ensure venues show up when filtered

### 🔄 JSON Synchronization Rules

#### ✅ Required Fields in JSON Export:
```json
{
  "name": "Venue Name",
  "venue_type": "museum",
  "address": "Full Address",
  "instagram_url": "https://instagram.com/handle",
  "facebook_url": "https://facebook.com/page",
  "twitter_url": "https://twitter.com/handle",
  "youtube_url": "https://youtube.com/channel",
  "tiktok_url": "https://tiktok.com/@handle",
  "website_url": "https://website.com",
  "image_url": "photo_reference_or_json",
  "latitude": 38.9167,
  "longitude": -77.0711
}
```

#### 🔧 Sync Process:
1. **Database changes** → Run `scripts/update_venues_json.py`
2. **JSON changes** → Import using venue management scripts
3. **Always backup** before major changes
4. **Validate after sync** using integrity validator

## 🛡️ Prevention Systems

### 1. 📋 Pre-Commit Validation
```bash
python scripts/pre_commit_data_check.py
```
Run before every commit to catch issues early.

### 2. 🔍 Data Integrity Validator
```bash
python scripts/data_integrity_validator.py
```
Comprehensive validation of all venue data.

### 3. 🔄 Regular Sync Checks
```bash
python scripts/update_venues_json.py
python scripts/data_integrity_validator.py
```
Keep database and JSON in perfect sync.

### 4. 💾 Backup Verification
- Check `data/backups/` before major operations
- Verify backup files have expected structure
- Test restoration process periodically

## 🚨 Emergency Recovery Procedures

### If Social Media Data is Lost:
1. Check `data/backups/venues.json.backup.YYYYMMDD_HHMMSS`
2. Run `scripts/restore_venue_social_media.py`
3. Update JSON: `scripts/update_venues_json.py`
4. Validate: `scripts/data_integrity_validator.py`

### If Image URLs Break:
1. Check if they're fake references (pattern: `AciIO2...` with exactly 200 chars)
2. Use `scripts/fetch_real_embassy_images.py` to get real ones
3. Ensure Google Maps API key is in `.env`
4. Test URLs: `curl -I http://localhost:5001/api/image/{photo_ref}`

### If Venue Types are Inconsistent:
1. Run `scripts/standardize_venue_types.py`
2. Update frontend filters to match
3. Test filtering functionality
4. Validate with integrity checker

## 📝 Best Practices

### When Adding New Venues:
1. ✅ Use real addresses and coordinates
2. ✅ Fetch real Google Maps images
3. ✅ Add social media handles for major venues
4. ✅ Use standardized venue types
5. ✅ Test the venue appears in filtering
6. ✅ Run validation before committing

### When Modifying Existing Data:
1. ✅ Create backup first
2. ✅ Make changes incrementally
3. ✅ Test each change
4. ✅ Validate data integrity
5. ✅ Update JSON files
6. ✅ Commit with descriptive messages

### Regular Maintenance:
1. 🔄 Weekly: Run data integrity validator
2. 💾 Daily: Check backup creation
3. 🔗 Monthly: Validate all API endpoints
4. 📱 Quarterly: Audit social media coverage

## 🎯 Quick Reference Commands

```bash
# Validate everything
python scripts/data_integrity_validator.py

# Sync database to JSON
python scripts/update_venues_json.py

# Restore social media from backup
python scripts/restore_venue_social_media.py

# Fetch real images for venues
python scripts/fetch_real_embassy_images.py

# Standardize venue types
python scripts/standardize_venue_types.py

# Pre-commit check
python scripts/pre_commit_data_check.py
```

Remember: **Data integrity is critical for user experience!** 🎯
