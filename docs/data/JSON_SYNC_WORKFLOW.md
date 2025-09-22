# JSON Sync Workflow Documentation

## Overview
This document describes the workflow for keeping JSON files synchronized with the database. When database records are updated, the corresponding JSON files should be updated to maintain consistency.

## Available Sync Scripts

### 1. Sources Sync
**Script**: `scripts/update_sources_json.py`
**JSON File**: `data/sources.json`
**Command**: `python scripts/update_sources_json.py`

**What it syncs**:
- All source records from the database
- Enhanced fields: reliability_score, posting_frequency, event_types, notes, scraping_pattern
- Metadata: version, timestamps, total count

### 2. Cities Sync
**Script**: `scripts/update_cities_json.py` (already existed)
**JSON File**: `data/cities.json`
**Command**: `python scripts/update_cities_json.py`

**What it syncs**:
- All city records from the database
- Basic fields: name, state, country, timezone
- Metadata: version, timestamps, total count

### 3. Venues Sync
**Script**: `scripts/update_venues_json.py` (newly created)
**JSON File**: `data/venues.json`
**Command**: `python scripts/update_venues_json.py`

**What it syncs**:
- All venue records from the database
- Enhanced fields: venue_type, address, city_id, city_name, description, opening_hours, phone, email, website, admission_fee, image_url, coordinates
- Metadata: version, timestamps, total count
- Statistics: venue types, cities, top venues

### 4. Events Sync
**Script**: `scripts/update_events_json.py` (newly created)
**JSON File**: `data/events.json`
**Command**: `python scripts/update_events_json.py`

**What it syncs**:
- All event records from the database
- Enhanced fields: title, description, dates/times, event_type, venue_id, venue_name, city_name
- Metadata: version, timestamps, total count
- Statistics: event types, cities, venues

## Workflow Rules

### When to Run Sync Scripts

#### **Always Run After:**
1. **Database Updates**: Any manual database updates via admin interface
2. **Bulk Data Changes**: Importing new data or making bulk modifications
3. **Field Enhancements**: Adding new fields or updating existing ones with AI knowledge
4. **Data Corrections**: Fixing data inconsistencies or errors

#### **Specific Scenarios:**
- ✅ **Source Enhancement**: After using AI knowledge to improve source descriptions, reliability scores, event types, etc.
- ✅ **New Records**: After adding new cities, venues, sources, or events
- ✅ **Field Updates**: After modifying any field in the database
- ✅ **Data Migration**: After moving data between systems
- ✅ **Backup Creation**: Before major changes or deployments

### Backup Strategy

Each sync script automatically:
1. **Creates Backup**: Timestamped backup of existing JSON file
2. **Backup Location**: `data/backups/[filename].backup.YYYYMMDD_HHMMSS`
3. **Preserves History**: Never overwrites backups, always creates new ones
4. **Error Handling**: Graceful rollback if sync fails

### Example Workflow

```bash
# 1. Update database records (via admin interface or script)
# 2. Run appropriate sync scripts

# Update sources after enhancing with AI knowledge
python scripts/update_sources_json.py

# Update venues after adding new venues
python scripts/update_venues_json.py

# Update cities after adding new cities
python scripts/update_cities_json.py

# Update events after adding new events
python scripts/update_events_json.py

# 3. Verify JSON files are updated
# 4. Commit changes to version control
```

## Script Features

### Common Features (All Scripts)
- **Automatic Backup**: Creates timestamped backups
- **Error Handling**: Graceful error handling with rollback
- **Progress Reporting**: Shows progress and statistics
- **Metadata**: Includes version info and timestamps
- **Database Authority**: Always exports from database (single source of truth)

### Enhanced Features
- **Statistics**: Shows counts and top categories
- **Field Validation**: Ensures all fields are properly exported
- **Relationship Data**: Includes related data (city names, venue names)
- **Null Handling**: Properly handles null/empty values

## File Structure

```
data/
├── sources.json          # Synced from database
├── cities.json           # Synced from database  
├── venues.json           # Synced from database
├── events.json           # Synced from database
└── backups/
    ├── sources.json.backup.20250918_184658
    ├── venues.json.backup.20250918_184808
    └── [timestamped backups...]
```

## Best Practices

### 1. **Always Sync After Database Changes**
- Don't let JSON files get out of sync with database
- Run sync scripts immediately after any database modifications

### 2. **Use Database as Single Source of Truth**
- Database is always authoritative
- JSON files are exports/backups, not the primary source

### 3. **Test Sync Scripts**
- Verify scripts work before relying on them
- Check that all fields are properly exported
- Validate JSON file structure

### 4. **Version Control**
- Commit JSON files to version control after sync
- Include sync scripts in version control
- Document any changes to sync workflow

### 5. **Monitoring**
- Check backup directory periodically
- Monitor JSON file sizes and structure
- Verify sync scripts complete successfully

## Current Status

### ✅ **Completed Sync Scripts**
- **Sources**: `scripts/update_sources_json.py` - 37 sources synced
- **Cities**: `scripts/update_cities_json.py` - Existing script
- **Venues**: `scripts/update_venues_json.py` - 147 venues synced
- **Events**: `scripts/update_events_json.py` - 0 events synced

### 📊 **Database Statistics**
- **Sources**: 37 (including enhanced Baltimore Scenes)
- **Cities**: Multiple cities across different countries
- **Venues**: 147 venues across 19 cities
- **Events**: 0 events (ready for future event discovery)

### 🔄 **Workflow Established**
- All JSON sync scripts are functional
- Backup strategy is implemented
- Error handling is in place
- Statistics reporting is working

## Future Enhancements

### Potential Improvements
1. **Automated Sync**: Run sync scripts automatically on database changes
2. **Incremental Sync**: Only sync changed records instead of full export
3. **Validation**: Add JSON schema validation
4. **Notifications**: Send alerts when sync completes or fails
5. **Scheduling**: Regular scheduled syncs for backup purposes

### Integration Opportunities
1. **Admin Interface**: Add sync buttons to admin interface
2. **API Endpoints**: Create API endpoints for triggering syncs
3. **Monitoring**: Add sync status monitoring
4. **Logging**: Enhanced logging for sync operations

This workflow ensures data consistency between the database and JSON files, providing reliable backups and exports for the event planner system.





