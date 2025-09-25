# Database Synchronization Guide

## 🎯 **Overview**

This guide ensures consistent database schemas and data between local development and deployed environments, preventing the "only one source" issue from happening again.

## 🔧 **Unified Data Management System**

### **Core Components**

1. **`scripts/unified_data_manager.py`** - Single source of truth for data loading
2. **`scripts/schema_validator.py`** - Validates database schema consistency  
3. **`scripts/sync_monitor.py`** - Monitors sync status between environments
4. **`railway_data_loader.py`** - Updated to use unified system

### **Key Features**

- ✅ **Environment Detection**: Automatically detects local vs deployed
- ✅ **Data Validation**: Validates foreign key relationships
- ✅ **Integrity Checks**: Ensures data consistency
- ✅ **Error Handling**: Comprehensive error reporting
- ✅ **Force Reload**: Option to completely refresh data

## 📋 **Usage Commands**

### **Data Management**

```bash
# Sync all data (recommended)
python scripts/unified_data_manager.py

# Force reload all data
python scripts/unified_data_manager.py --force

# Show database info
python scripts/unified_data_manager.py --info

# Validate data integrity only
python scripts/unified_data_manager.py --validate
```

### **Schema Validation**

```bash
# Full schema validation report
python scripts/schema_validator.py --report

# Validate specific table
python scripts/schema_validator.py --table sources

# JSON output
python scripts/schema_validator.py --json
```

### **Sync Monitoring**

```bash
# Check sync status between local and deployed
python scripts/sync_monitor.py

# Generate full sync report
python scripts/sync_monitor.py --report

# Quick sync check
python scripts/sync_monitor.py --check-only
```

## 🚀 **Deployment Process**

### **Railway Deployment**

The Railway deployment automatically uses the unified system:

1. **Start Command**: `python railway_data_loader.py && gunicorn app:app --bind 0.0.0.0:$PORT`
2. **Data Loading**: Uses `UnifiedDataManager` for consistency
3. **Environment Detection**: Automatically detects Railway environment

### **Local Development**

For local development, use the unified data manager:

```bash
# After pulling changes or updating JSON files
python scripts/unified_data_manager.py

# If you suspect data issues
python scripts/unified_data_manager.py --force
```

## 🔍 **Monitoring & Alerts**

### **Regular Checks**

Run these commands regularly to ensure sync:

```bash
# Check if databases are in sync
python scripts/sync_monitor.py --check-only

# Validate schema integrity
python scripts/schema_validator.py --report
```

### **Automated Monitoring**

Consider setting up automated checks:

```bash
# Add to your development workflow
#!/bin/bash
echo "🔍 Checking database sync..."
python scripts/sync_monitor.py --check-only
if [ $? -ne 0 ]; then
    echo "⚠️ Database sync issues detected!"
    python scripts/unified_data_manager.py --force
fi
```

## 🛠️ **Troubleshooting**

### **Common Issues**

1. **"Only one source" problem**
   ```bash
   # Solution: Use unified data manager
   python scripts/unified_data_manager.py --force
   ```

2. **Schema mismatches**
   ```bash
   # Check schema differences
   python scripts/schema_validator.py --report
   
   # Fix with force reload
   python scripts/unified_data_manager.py --force
   ```

3. **Foreign key violations**
   ```bash
   # Validate data integrity
   python scripts/unified_data_manager.py --validate
   
   # Fix with force reload
   python scripts/unified_data_manager.py --force
   ```

### **Data Recovery**

If data gets corrupted:

```bash
# Complete data reset
python scripts/unified_data_manager.py --force

# Verify recovery
python scripts/schema_validator.py --report
python scripts/sync_monitor.py --report
```

## 📊 **Expected Data Counts**

### **Minimum Expected Counts**

- **Cities**: 20-50
- **Sources**: 30-100  
- **Venues**: 100-500
- **Events**: 0-10,000

### **Validation Rules**

- All sources must have valid `city_id` references
- All venues must have valid `city_id` references  
- All events must have valid `city_id` references
- Required fields must not be null

## 🔄 **Workflow Integration**

### **Before Deployment**

```bash
# 1. Validate local data
python scripts/schema_validator.py --report

# 2. Check sync status
python scripts/sync_monitor.py --check-only

# 3. Fix any issues
python scripts/unified_data_manager.py --force

# 4. Deploy
git push origin main
```

### **After Deployment**

```bash
# 1. Verify deployment
python scripts/sync_monitor.py --report

# 2. Check API endpoints
curl https://planner.ozayn.com/api/sources?city_id=1 | jq length
```

## 📝 **Best Practices**

1. **Always use unified data manager** for data loading
2. **Run validation checks** before and after deployments
3. **Monitor sync status** regularly
4. **Use force reload** when in doubt
5. **Check logs** for detailed error information

## 🚨 **Emergency Procedures**

### **Complete Data Reset**

If everything goes wrong:

```bash
# 1. Stop the application
# 2. Clear database completely
# 3. Force reload all data
python scripts/unified_data_manager.py --force

# 4. Verify recovery
python scripts/schema_validator.py --report
python scripts/sync_monitor.py --report

# 5. Restart application
```

### **Rollback Procedure**

If deployment fails:

```bash
# 1. Revert to previous commit
git revert HEAD

# 2. Force reload data
python scripts/unified_data_manager.py --force

# 3. Redeploy
git push origin main
```

---

## 🎉 **Success Metrics**

✅ **Database Sync**: Local and deployed databases have identical schemas  
✅ **Data Integrity**: All foreign key relationships are valid  
✅ **Consistent Counts**: Expected number of records in each table  
✅ **API Consistency**: Same data available via API endpoints  
✅ **Monitoring**: Automated checks catch issues early  

This system ensures the "only one source" problem never happens again! 🚀
