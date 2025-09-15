# QUICK REFERENCE CARD

## 🚀 RESTART COMMANDS
```bash
cd /Users/oz/Dropbox/2025/planner
source venv/bin/activate
python app.py
```

## 📊 CURRENT STATUS
- **Cities**: 22 ✅
- **Venues**: 147 ✅  
- **Sources**: 36 ✅
- **Events**: 0 (ready)
- **Port**: 5001
- **Database**: `instance/events.db`
- **Scripts**: 8 (cleaned up from 65)

## 🔧 KEY COMMANDS
```bash
# Load all data
python scripts/data_manager.py load

# Load specific data
python scripts/data_manager.py load-cities
python scripts/data_manager.py load-venues
python scripts/data_manager.py load-sources

# Sync data
python scripts/data_manager.py sync
```

## 🌐 QUICK TESTS
```bash
# Check stats
curl http://localhost:5001/api/admin/stats

# Check cities
curl http://localhost:5001/api/cities

# Check venues
curl "http://localhost:5001/api/venues?city_id=1"

# Check sources
curl http://localhost:5001/api/admin/sources
```

## 📋 NEXT STEPS
1. Test event loading
2. Add export-sources command
3. Test GitHub deployment
4. Monitor performance

---
**Full Documentation**: See `PROJECT_STATUS_NOTES.md`
