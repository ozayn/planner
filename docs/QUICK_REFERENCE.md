# QUICK REFERENCE CARD

## 🚨 **CRITICAL REMINDERS**
- **ALWAYS activate venv**: `source venv/bin/activate`
- **Use port 5001**: Never 5000, app runs on `http://localhost:5001`
- **Use `python3`**: Not `python` (system vs venv)
- **Environment variables**: Add API keys to `.env` (never commit)

## 🚀 RESTART COMMANDS
```bash
cd /Users/oz/Dropbox/2025/planner
source venv/bin/activate
python app.py
```

## 📊 CURRENT STATUS
- **Cities**: 25 ✅
- **Venues**: 178 ✅  
- **Sources**: 37 ✅
- **Events**: 0 (ready)
- **Port**: 5001
- **Database**: `instance/events.db` (local), PostgreSQL (deployment)
- **Hybrid System**: ✅ Production ready

## 🤖 HYBRID OCR + LLM SYSTEM
- **OCR Engines**: Tesseract (local), Google Vision API (deployment)
- **LLM**: Google Gemini for intelligent processing
- **Smart Detection**: Auto-chooses optimal OCR engine
- **Instagram Context**: Extracts page names, handles, poster info
- **Confidence**: 90% (Vision API), 80% (Tesseract)

## 🌐 DEPLOYMENT
- **Platform**: Railway
- **Domain**: `planner.ozayn.com`
- **Status**: ✅ Live and operational
- **Environment**: Auto-detects local vs deployment

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
