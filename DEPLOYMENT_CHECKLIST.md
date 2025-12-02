# Deployment Checklist - Exhibition Fields & Tour Validation

## ✅ Pre-Deployment Verification

### Database Schema Changes
- [x] New exhibition fields added to Event model:
  - `artists` (TEXT)
  - `exhibition_type` (VARCHAR(100))
  - `collection_period` (VARCHAR(200))
  - `number_of_artworks` (INTEGER)
  - `opening_reception_date` (DATE)
  - `opening_reception_time` (TIME)
  - `is_permanent` (BOOLEAN, default=False)
  - `related_exhibitions` (TEXT)

- [x] Migration function (`migrate_events_schema()`) includes all new fields
- [x] Auto-migration runs on Railway startup (`auto_migrate_schema()`)
- [x] Boolean fields have proper defaults in migration

### Validation Changes
- [x] Tours require start_time (validation in scraper)
- [x] Tours without start_time rejected at database save (safety check)
- [x] Generic booking titles filtered out ("Book a Tour", "Reserve a Tour", etc.)
- [x] Navigation/page titles filtered out ("Exhibitions & Events", "Calendar", etc.)

### Code Changes
- [x] `scripts/venue_event_scraper.py` - Enhanced validation
- [x] `app.py` - Database save validation + migration function
- [x] `scripts/cleanup_tours_without_time.py` - Cleanup script created
- [x] `scripts/cleanup_invalid_events.py` - Invalid events cleanup script

## 🚀 Deployment Steps

1. **Commit all changes:**
   ```bash
   git add .
   git commit -m "Add exhibition fields, enforce tour time validation, filter invalid titles"
   ```

2. **Push to GitHub:**
   ```bash
   git push origin master
   ```

3. **Railway will automatically:**
   - Deploy the new code
   - Run `auto_migrate_schema()` on startup
   - Add missing columns to PostgreSQL events table
   - Log migration results

## 🔍 Post-Deployment Verification

After deployment, check Railway logs for:
- ✅ "Schema migration: Successfully added X columns"
- ✅ No migration errors
- ✅ App starts successfully

## 📝 Notes

- **Local SQLite**: Already migrated using `scripts/add_exhibition_fields.py`
- **Railway PostgreSQL**: Will auto-migrate on next deployment
- **Existing Data**: Cleanup scripts available if needed:
  - `scripts/cleanup_tours_without_time.py` - Remove tours without times
  - `scripts/cleanup_invalid_events.py` - Remove invalid event titles

## ⚠️ Rollback Plan

If issues occur:
1. Check Railway logs for migration errors
2. Manually verify columns exist: `SELECT column_name FROM information_schema.columns WHERE table_name = 'events'`
3. If needed, manually add missing columns using Railway PostgreSQL console

