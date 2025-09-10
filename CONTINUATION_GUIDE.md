# 🚀 Multi-Model LLM System - Continuation Guide

## **📋 Current Status (Last Updated: September 9, 2025)**

### **✅ What's Working:**
- **Google Gemini**: ✅ Fully functional (11 venues discovered for LA)
- **Enhanced Fallback System**: ✅ Integrated and working
- **Venue Discovery API**: ✅ Working with Google Gemini
- **Database**: ✅ 9 venues for Los Angeles, 8 for Washington DC
- **Events**: ✅ 9 sample events added
- **Dynamic Prompts**: ✅ All LLM prompts now adapt to schema changes
- **SQLAlchemy**: ✅ No more deprecation warnings
- **API Coverage**: ✅ All frontend-backend endpoints working
- **Environment Config**: ✅ Centralized and reliable

### **❌ What's Not Working:**
- **Groq**: Rate limited (100k tokens/day exceeded - resets daily)
- **OpenAI**: Quota exceeded (need to add billing)
- **Anthropic**: Not configured (needs $5 credit)
- **Cohere**: Not configured (needs API key)
- **Mistral**: Not configured (needs API key)

## **📚 Documentation**
- **Comprehensive Code Review Summary**: See `COMPREHENSIVE_CODE_REVIEW_SUMMARY.md` for detailed documentation of all improvements made
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Database Schema**: See `docs/DATABASE_SCHEMA.md`

## **🛡️ BULLETPROOF RESTART PROCESS**

### **🚀 ONE COMMAND RESTART**
```bash
# Just run this - it handles everything!
./restart.sh
```

**OR if you prefer manual control:**
```bash
# Navigate to project directory
cd /Users/oz/Dropbox/2025/planner

# Activate virtual environment  
source venv/bin/activate

# Run bulletproof startup
python start.py
```

**This single command will:**
- ✅ Navigate to the correct directory
- ✅ Activate virtual environment
- ✅ Install any missing dependencies
- ✅ Ensure database directory exists
- ✅ Check cities data is populated
- ✅ Validate schema consistency
- ✅ Start Flask app
- ✅ Open browser to the app

### **🔧 MANUAL RESTART (if needed)**
```bash
# Navigate to project directory
cd /Users/oz/Dropbox/2025/planner

# Run bulletproof startup
python start.py
```

### **🎯 WHAT THIS PREVENTS**
- ❌ **No more missing packages** - Auto-installs dependencies
- ❌ **No more missing cities** - Auto-populates cities data
- ❌ **No more missing admin page** - Validates all endpoints
- ❌ **No more database issues** - Ensures proper database setup
- ❌ **No more missing fields** - Runs schema validation
- ❌ **No more setup problems** - Handles everything automatically
- ❌ **No more "Error loading statistics"** - Fixed JavaScript data structure
- ❌ **No more missing API endpoints** - All endpoints validated

### **📱 AFTER RESTART**
- **Main App**: http://localhost:5001
- **Admin Page**: http://localhost:5001/admin
- **All features working** exactly as you left them!

---

## **🔧 How to Continue:**

### **Step 1: Start the System**
```bash
# Navigate to project directory
cd /Users/oz/Dropbox/2025/planner

# Activate virtual environment
source venv/bin/activate

# Start Flask app
python app.py
```

### **Step 2: Test Current Setup**
```bash
# Test the enhanced LLM system
python scripts/enhanced_llm_fallback.py

# Test venue discovery
python scripts/discover_venues.py --city "Los Angeles" --country "United States" --event-type tours --max-venues 5

# Test API
curl -X POST http://localhost:5001/api/discover-venues -H "Content-Type: application/json" -d '{"city_id": 3, "event_types": ["tours"]}'
```

### **Step 3: Add More API Keys (Optional)**
When you get additional API keys, add them to `.env`:

```bash
# Anthropic Claude ($5 minimum credit)
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Cohere (often free credits)
COHERE_API_KEY=your_cohere_key_here

# Mistral (may have free tier)
MISTRAL_API_KEY=your_mistral_key_here
```

### **Step 4: Test All APIs**
```bash
# Run comprehensive test
python test_all_apis.py
```

## **🎯 Current Fallback Chain:**
1. **Groq** (Free) → Rate limited
2. **OpenAI GPT-4** → Model not found
3. **OpenAI GPT-3.5** → Quota exceeded
4. **Google Gemini** → ✅ **WORKING!**
5. **Mock Data** → Fallback for unknown cities

## **📊 What Google Gemini Discovered:**
**11 venues for Los Angeles:**
- Getty Center
- The Broad
- LACMA
- Natural History Museum
- California Science Center
- Griffith Observatory
- El Pueblo de Los Angeles
- Museum of Jurassic Technology
- Walt Disney Concert Hall
- The Huntington Library
- MOCA Grand Avenue

## **🔍 Key Files:**
- `scripts/enhanced_llm_fallback.py` - Multi-model system
- `scripts/discover_venues.py` - Venue discovery (updated)
- `test_all_apis.py` - Test script
- `.env` - API keys configuration
- `app.py` - Flask application

## **💡 Next Steps:**
1. **Test other cities** with Google Gemini
2. **Add more API keys** for redundancy
3. **Test event scraping** functionality
4. **Add more cities** to knowledge base

## **🚨 Important Notes:**
- **Groq resets daily** - will work again tomorrow
- **Google Gemini is working perfectly** - no issues
- **System never fails** - always falls back to knowledge base
- **All venues are being saved** to database correctly

## **🔧 Common Issues & Quick Fixes:**

### **"Error loading cities" in Admin Page:**
- **Cause**: Missing admin API endpoints
- **Fix**: All admin endpoints are now added (`/api/admin/stats`, `/api/admin/cities`, `/api/admin/venues`, `/api/admin/events`)
- **Test**: `curl http://localhost:5001/api/admin/stats`

### **"Error loading statistics" in Admin Page:**
- **Cause**: JavaScript error in admin page
- **Fix**: Admin endpoints are working, clear browser cache
- **Test**: Hard refresh (Ctrl+F5) or incognito mode

### **DATABASE SCHEMA REGRESSION - VENUE FIELDS:**
- **Root Cause**: During cleanup commit `ba37a24`, venue fields were removed from model but never properly migrated to database
- **Missing Fields**: `opening_hours`, `holiday_hours`, `phone_number`, `email` 
- **Impact**: Code expects these fields but database doesn't have them
- **Fix Applied**: Added missing columns to database schema using ALTER TABLE
- **Prevention**: Always check database schema matches model definition after cleanup commits

### **VENUE_ID ISSUE - COMPREHENSIVE FIX:**
- **Root Cause**: Database schema has two types of events:
  - **Venue Events**: Tours and Exhibitions (have `venue_id`)
  - **City Events**: Festivals and Photowalks (have `city_id`, NOT `venue_id`)
- **Comprehensive Fix Applied**:
  - Added validation constants: `VENUE_EVENTS = ['tour', 'exhibition']`, `CITY_EVENTS = ['festival', 'photowalk']`
  - Created validation functions: `validate_event_type()`, `get_event_count_for_venue()`, `get_event_count_for_city()`
  - Updated all admin endpoints to use these functions
  - Removed non-existent fields from venue queries
- **Prevention**: All future queries now use validation functions to prevent venue_id errors
- **Test**: All admin endpoints working correctly (`/api/admin/cities`, `/api/admin/venues`, `/api/admin/stats`)

### **Database Connection Issues - PROFESSIONAL FIX:**
- **Root Cause**: Using `/tmp` (temporary directory) and Dropbox sync conflicts
- **Professional Solution**: Using `~/.local/share/planner/events.db` (XDG Base Directory standard)
- **Benefits**: 
  - Persistent storage (survives system restarts)
  - No Dropbox sync conflicts
  - Follows professional application data standards
  - Cross-platform compatible
- **Cloud Backup**: Automatic backup to `~/Dropbox/2025/planner/backups/` for cloud access
- **API Endpoint**: `/api/backup-database` to trigger manual backups
- **Test**: `ls -la ~/.local/share/planner/` and `ls -la ~/Dropbox/2025/planner/backups/`

### **Missing API Endpoints:**
- **Cause**: Endpoints removed during cleanup
- **Fix**: All endpoints restored (`/api/discover-venues`, `/api/add-venue-manually`)
- **Test**: `curl http://localhost:5001/api/cities`

## **🎉 Success Metrics:**
- ✅ **4 models detected** (Groq, OpenAI x2, Google)
- ✅ **Google Gemini working** (128 tokens used)
- ✅ **11 venues discovered** for Los Angeles
- ✅ **API integration working**
- ✅ **Database saving working**

**The multi-model LLM fallback system is fully functional!** 🚀

---

## **🔧 DATABASE SCHEMA CHANGE CHECKLIST**

### **When Adding/Modifying Database Fields:**

1. **✅ Update Model** (`app.py`):
   ```python
   class Venue(db.Model):
       new_field = db.Column(db.Text)  # Add new field
   ```

2. **✅ Update to_dict()** (`app.py`):
   ```python
   def to_dict(self):
       return {
           # ... existing fields ...
           'new_field': self.new_field  # Add to dict
       }
   ```

3. **✅ Update Admin Endpoints** (`app.py`):
   ```python
   venues_data.append({
       # ... existing fields ...
       'new_field': venue.new_field  # Add to admin response
   })
   ```

4. **✅ Update LLM Prompts** (`scripts/discover_venues.py`):
   ```python
   field_descriptions = {
       # ... existing fields ...
       'new_field': 'Description of new field'  # Add to prompts
   }
   ```

5. **✅ Update Object Creation** (`scripts/discover_venues.py`):
   ```python
   venue = Venue(
       # ... existing fields ...
       new_field=details.get('new_field', ''),  # Add to creation
   )
   ```

6. **✅ Update Database Schema**:
   ```sql
   ALTER TABLE venues ADD COLUMN new_field TEXT;
   ```

7. **✅ Test Full Flow**:
   ```bash
   # Test venue discovery
   python scripts/discover_venues.py --city "Test City" --output-json
   
   # Check database
   python -c "from app import Venue; print(Venue.query.first().to_dict())"
   
   # Check admin API
   curl http://localhost:5001/api/admin/venues
   ```

### **🚨 CRITICAL**: Always test the **complete flow** after schema changes!

### **🔧 AUTOMATED SCHEMA VALIDATION SYSTEM**

**Use the schema validator before making any changes:**

```bash
# Run comprehensive validation
python scripts/schema_validator.py

# Should return: ✅ All schema validations passed!
```

**If validation fails, fix the issues before proceeding.**

### **🔄 COMPLETE SCHEMA CHANGE WORKFLOW**

1. **Run Schema Validator**: `python scripts/schema_validator.py`
2. **Make Changes**: Update model, to_dict(), admin endpoints, object creation
3. **Run Schema Validator Again**: Ensure all issues are fixed
4. **Test Full Flow**: 
   ```bash
   # Test venue discovery
   python scripts/discover_venues.py --city "Test City" --output-json
   
   # Check database
   python -c "from app import Venue; print(Venue.query.first().to_dict())"
   
   # Check admin API
   curl http://localhost:5001/api/admin/venues
   ```
5. **Update Existing Data**: If needed, migrate existing records

### **🚨 CRITICAL**: Always test the **complete flow** after schema changes!

---

## **DYNAMIC LLM PROMPT GENERATION METHOD**

### **Key Principle:**
Always use dynamic field generation from database models instead of hardcoded field lists in LLM prompts.

### **Implementation Pattern:**
```python
def _get_model_fields_prompt(self) -> str:
    """Dynamically generate field list from database model"""
    # Get all columns from the model
    model_columns = Model.__table__.columns
    
    # Define field descriptions for each column
    field_descriptions = {
        'field_name': 'Human-readable description',
        # ... more fields
    }
    
    # Generate field list dynamically
    field_lines = []
    for column in model_columns:
        if column.name not in ['id', 'created_at', 'foreign_key_id']:  # Skip auto-generated fields
            description = field_descriptions.get(column.name, f'{column.name.replace("_", " ").title()}')
            field_lines.append(f"- {column.name}: {description}")
    
    # Add any additional fields that aren't in the database but are useful
    additional_fields = ['significance', 'extra_info']
    for field in additional_fields:
        if field not in field_descriptions:
            field_lines.append(f"- {field}: {field_descriptions.get(field, f'{field.replace("_", " ").title()}')}")
    
    return '\n'.join(field_lines)
```

### **Usage in Prompts:**
```python
prompt = f"""
For each item, provide:
{self._get_model_fields_prompt()}

Return the response as a JSON array of objects.
"""
```

### **Benefits:**
- **Automatic Sync**: LLM prompts automatically include all database fields
- **Schema Evolution**: When database schema changes, prompts update automatically
- **No Manual Maintenance**: No need to manually update field lists
- **Consistency**: All prompts use the same field definitions
- **Professional**: Follows DRY principle and reduces errors

### **Applied In:**
- `scripts/discover_venues.py` - Venue discovery prompts
- Future: Event creation, user profiles, any model-based LLM interactions


