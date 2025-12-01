# Event Model Schema Comparison - Local vs Production

**Date**: 2025-01-18  
**Status**: ✅ Fixed - Auto-migration updated

## Summary

The production database (Railway PostgreSQL) was missing several columns that exist in the local Event model. The auto-migration function in `app.py` has been updated to include all missing fields.

## Issue Found

When querying the production API (`/api/admin/events`), the following error occurred:

```
column events.is_online does not exist
```

This indicated that the production database schema was out of sync with the local model.

## Local Event Model Fields (49 columns total)

### Core Fields
- `id`, `title`, `description`
- `start_date`, `end_date`
- `start_time`, `end_time`
- `image_url` (VARCHAR(1000))
- `url` (VARCHAR(1000))
- `is_selected`, `is_online` ⚠️ **MISSING IN PRODUCTION**
- `event_type`
- `source`, `source_url` (VARCHAR(1000))
- `created_at`, `updated_at`

### Registration Fields ⚠️ **MISSING IN PRODUCTION**
- `is_registration_required` (BOOLEAN, default=False)
- `registration_opens_date` (DATE)
- `registration_opens_time` (TIME)
- `registration_url` (VARCHAR(1000))
- `registration_info` (TEXT)

### Location Fields
- `start_location` (VARCHAR(200))
- `end_location` (VARCHAR(200))
- `venue_id`, `city_id`
- `start_latitude`, `start_longitude`
- `end_latitude`, `end_longitude`

### Social Media Fields
- `social_media_platform` (VARCHAR(50))
- `social_media_handle` (VARCHAR(100))
- `social_media_page_name` (VARCHAR(100))
- `social_media_posted_by` (VARCHAR(100))
- `social_media_url` (VARCHAR(500))

### Tour-Specific Fields
- `tour_type`, `max_participants`, `price`, `language`

### Exhibition-Specific Fields
- `exhibition_location`, `curator`, `admission_price`

### Festival-Specific Fields
- `festival_type`, `multiple_locations`

### Photowalk-Specific Fields
- `difficulty_level`, `equipment_needed`, `organizer`

## Missing Columns in Production

The following columns were missing from the production database:

1. ✅ `is_online` (BOOLEAN, default=False)
2. ✅ `is_registration_required` (BOOLEAN, default=False)
3. ✅ `registration_opens_date` (DATE)
4. ✅ `registration_opens_time` (TIME)
5. ✅ `registration_url` (VARCHAR(1000))
6. ✅ `registration_info` (TEXT)

## Fix Applied

Updated the `auto_migrate_schema()` function in `app.py` to:

1. **Include all missing fields** in the `expected_columns` list:
   - `is_online`
   - `is_registration_required`
   - `registration_opens_date`
   - `registration_opens_time`
   - `registration_url`
   - `registration_info`

2. **Add default values** for BOOLEAN columns to match the model:
   - `is_online DEFAULT FALSE`
   - `is_registration_required DEFAULT FALSE`

3. **Improve Railway detection** to work even if `RAILWAY_ENVIRONMENT` isn't set:
   - Now checks for PostgreSQL in `DATABASE_URL` as well

## Next Steps

1. **Deploy the fix**: The updated `app.py` will automatically migrate the schema on the next Railway deployment
2. **Verify**: After deployment, check Railway logs for migration messages
3. **Test**: Query `/api/admin/events` to confirm the error is resolved

## Auto-Migration Behavior

The `auto_migrate_schema()` function:
- Runs automatically on app startup
- Only runs on Railway (detected by PostgreSQL DATABASE_URL)
- Adds missing columns without affecting existing data
- Logs all migration actions
- Continues even if some columns fail (non-blocking)

## Verification Command

After deployment, verify the schema is correct:

```bash
curl -s "https://planner.ozayn.com/api/admin/events?limit=1" | python3 -m json.tool
```

Should return event data without errors.

