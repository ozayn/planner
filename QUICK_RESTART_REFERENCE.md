# 🚀 Quick Restart Reference Card

## **Essential Commands**

### **Start Application**
```bash
source venv/bin/activate && python app.py
```

### **Test Core Functionality**
```bash
# Test API endpoints
curl -s "http://localhost:5001/api/cities" | jq length
curl -s "http://localhost:5001/api/admin/venues" | jq '.[0] | keys'

# Test venue discovery
curl -s -X POST "http://localhost:5001/api/admin/discover-venues" \
  -H "Content-Type: application/json" \
  -d '{"city_id": 1}' | jq .success
```

### **Verify Environment**
```bash
# Test environment loading
python scripts/env_config.py

# Test dynamic prompts
python scripts/dynamic_prompts.py
```

## **Key Files Modified Today**

### **New Files**
- `scripts/dynamic_prompts.py` - Dynamic prompt generation
- `scripts/env_config.py` - Centralized environment management
- `COMPREHENSIVE_CODE_REVIEW_SUMMARY.md` - Complete documentation

### **Updated Files**
- `app.py` - Fixed SQLAlchemy warnings, added missing endpoints, updated Venue model
- `scripts/utils.py` - Added dynamic prompt integration
- `scripts/discover_venues.py` - Removed unused hardcoded prompts
- `scripts/fetch_venue_details.py` - Removed unused hardcoded prompts
- `CONTINUATION_GUIDE.md` - Updated with new status

## **What's Fixed**

✅ **SQLAlchemy Warnings** - No more deprecation warnings  
✅ **Dynamic Prompts** - Automatically adapt to schema changes  
✅ **Missing API Endpoints** - All frontend calls now work  
✅ **Database Schema** - Venue model matches database  
✅ **Environment Loading** - No more "env forgetting" issues  
✅ **Code Cleanup** - Removed unused hardcoded code  

## **Quick Health Check**

```bash
# 1. Start app
source venv/bin/activate && python app.py &

# 2. Wait for startup
sleep 3

# 3. Test endpoints
curl -s "http://localhost:5001/api/cities" | jq length
curl -s "http://localhost:5001/api/admin/venues" | jq '.[0] | keys | length'

# 4. Test venue discovery
curl -s -X POST "http://localhost:5001/api/admin/discover-venues" \
  -H "Content-Type: application/json" \
  -d '{"city_id": 1}' | jq .success

# Expected results:
# - Cities: 2
# - Venue fields: 24
# - Venue discovery: true
```

## **Troubleshooting**

### **If Flask won't start:**
```bash
pkill -f "python app.py"
source venv/bin/activate
python app.py
```

### **If API calls fail:**
```bash
# Check if app is running
curl -s "http://localhost:5001/api/cities"

# Check environment
python scripts/env_config.py
```

### **If venue discovery fails:**
```bash
# Test LLM utilities
python -c "
from scripts.utils import get_llm_status
print('LLM Status:', get_llm_status())
"
```

---

*For detailed documentation, see `COMPREHENSIVE_CODE_REVIEW_SUMMARY.md`*

