# 🛡️ Mistake Prevention Checklist

## 🚨 BEFORE Making Any Venue Changes

### ✅ Pre-Change Checklist:
- [ ] **Check for duplicates**: `python scripts/check_duplicates.py` - **ALWAYS RUN THIS FIRST**
- [ ] **Backup current data**: `python scripts/update_venues_json.py` 
- [ ] **Run validation**: `python scripts/data_integrity_validator.py`
- [ ] **Check API key**: Verify `GOOGLE_MAPS_API_KEY` in `.env`
- [ ] **Test current functionality**: Load venues in browser to ensure it works

## 🔧 WHEN Adding New Venues

### ✅ New Venue Checklist:
- [ ] **Use real addresses** with proper coordinates
- [ ] **Fetch real images**: Use `scripts/fetch_google_maps_image.py`
- [ ] **Add social media**: Research and add real handles for major venues
- [ ] **Use standard venue types**: Check existing types in database
- [ ] **Test venue appears**: Verify it shows up in filtering
- [ ] **Validate data**: Run `scripts/data_integrity_validator.py`

### ❌ NEVER DO:
- [ ] Create fake photo references (like `AciIO2...` patterns)
- [ ] Add venues without testing image URLs
- [ ] Use inconsistent venue type capitalization
- [ ] Skip social media for museums/embassies/arts centers

## 🔄 WHEN Modifying Existing Data

### ✅ Modification Checklist:
- [ ] **Check for duplicates FIRST**: `python scripts/check_duplicates.py` - **REQUIRED**
- [ ] **Create backup first**: Automatic backup before changes
- [ ] **Check backup structure**: Verify `data/backups/` has recent files
- [ ] **Make incremental changes**: Don't bulk update without testing
- [ ] **Test each change**: Verify functionality after each modification
- [ ] **Sync JSON files**: Run `scripts/update_venues_json.py`
- [ ] **Validate integrity**: Run full validation suite
- [ ] **Re-check duplicates**: `python scripts/check_duplicates.py` after changes

## 📱 SOCIAL MEDIA DATA RULES

### ✅ Social Media Checklist:
- [ ] **Check backups first**: Look in `data/backups/` for recent data
- [ ] **Use full URLs**: Not just handles (e.g., `https://instagram.com/handle`)
- [ ] **Include in JSON export**: Ensure `update_venues_json.py` exports all fields
- [ ] **Test restoration**: Verify backup restoration process works
- [ ] **Validate coverage**: Major venues should have 3+ social platforms

## 🖼️ IMAGE URL MANAGEMENT

### ✅ Image URL Checklist:
- [ ] **Use Google Places API**: Never create fake photo references
- [ ] **Store correct format**: JSON string or raw photo reference
- [ ] **Test image endpoints**: `curl -I http://localhost:5001/api/image/{ref}`
- [ ] **Check to_dict() logic**: Ensure JSON parsing happens before raw string
- [ ] **Validate all images**: No broken or fake image URLs

## 🎯 BEFORE EVERY COMMIT

### ✅ Pre-Commit Checklist:
- [ ] **Run pre-commit hook**: `python scripts/pre_commit_data_check.py`
- [ ] **Run full validation**: `python scripts/data_integrity_validator.py`
- [ ] **Test in browser**: Load venues and verify functionality
- [ ] **Check for errors**: No console errors or broken features
- [ ] **Update JSON files**: Ensure all JSON files are synchronized

## 🔍 AUTOMATED PREVENTION SYSTEMS

### 1. 🤖 Pre-Commit Hook
**Location**: `.git/hooks/pre-commit`
**Purpose**: Automatically validates data before every commit
**Blocks commits** if data quality issues are detected

### 2. 📋 Data Integrity Validator
**Command**: `python scripts/data_integrity_validator.py`
**Purpose**: Comprehensive validation of all venue data
**Checks**: Images, social media, venue types, JSON sync, API endpoints

### 3. 🧪 Automated Tests
**Command**: `python scripts/automated_venue_tests.py`
**Purpose**: Unit tests for venue data integrity
**Catches**: Fake images, format issues, missing social media

### 4. 📚 Documentation
**File**: `VENUE_DATA_MANAGEMENT_GUIDE.md`
**Purpose**: Comprehensive guide for venue data management
**Includes**: Best practices, emergency procedures, troubleshooting

## 🚨 EMERGENCY RECOVERY PROCEDURES

### If Social Media Data is Lost:
```bash
python scripts/restore_venue_social_media.py
python scripts/update_venues_json.py
python scripts/data_integrity_validator.py
```

### If Images Break:
```bash
python scripts/fetch_real_embassy_images.py
python scripts/update_venues_json.py
curl -I http://localhost:5001/api/image/{test_reference}
```

### If Venue Types are Inconsistent:
```bash
python scripts/standardize_venue_types.py
# Update frontend filters manually
python scripts/data_integrity_validator.py
```

## 📈 REGULAR MAINTENANCE

### Daily:
- [ ] Check backup files exist
- [ ] Run duplicate check: `python scripts/check_duplicates.py`
- [ ] Run quick validation

### Weekly:
- [ ] Full data integrity validation (includes duplicate check)
- [ ] Test all API endpoints
- [ ] Verify JSON synchronization
- [ ] Check for duplicates: `python scripts/check_duplicates.py`

### Monthly:
- [ ] Audit social media coverage
- [ ] Update venue information
- [ ] Review and update documentation
- [ ] Comprehensive duplicate check and cleanup

## 🎯 SUCCESS METRICS

### Data Quality Targets:
- **No duplicates**: 0 duplicates in cities, venues, or events
- **Image coverage**: 100% (no broken or fake images)
- **Social media coverage**: >90% for major venues (museums, embassies, arts centers)
- **Venue type consistency**: 100% (all lowercase, standardized)
- **JSON synchronization**: 100% (database matches JSON files)
- **API uptime**: 100% (all endpoints working)

---

**Remember**: Prevention is better than recovery! 🛡️
**Always validate before committing!** ✅
