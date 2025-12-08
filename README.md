# Event Planner App

A minimal, artistic web and mobile app for discovering events in cities worldwide.

## 🚨 **IMPORTANT REMINDERS**

### **🔑 Critical Setup Steps**
- **⚠️ ALWAYS activate virtual environment first**: `source venv/bin/activate && python`
- **❌ NEVER use `python3` directly**: Causes "no module named bs4" and other dependency errors
- **✅ CORRECT**: `source venv/bin/activate && python scripts/venue_event_scraper.py`
- **❌ WRONG**: `python3 scripts/venue_event_scraper.py` (uses system Python without dependencies)
- **Use port 5001, never 5000**: App runs on `http://localhost:5001`
- **Environment variables**: Add API keys to `.env` file (never commit this file)

### **🤖 Hybrid OCR + LLM System**
- **Default OCR**: Tesseract (local), Google Vision API (deployment)
- **LLM Processing**: Google Gemini for intelligent event extraction
- **Smart Detection**: Automatically chooses optimal OCR engine
- **Instagram Context**: Extracts page names, handles, and poster info
- **Intelligent Processing**: 90% confidence with Vision API, 80% with Tesseract

### **🔗 Create Events from URL (✅ FIXED)**
**STATUS**: Feature fully functional - Auto-Fill button now works correctly!

#### **What Works**:
- **📋 Paste Any Event URL**: Automatically scrape and create events from web pages
- **🔍 Auto-Fill Button**: Click to extract event details before creating
- **📅 Smart Time Periods**: Choose today, tomorrow, this week, this month, or custom dates
- **🔄 Recurring Event Handling**: Detects schedules like "Fridays 6:30pm - 7:30pm" or "Weekdays 3pm"
- **📊 Multi-Event Creation**: Automatically creates events for all matching days in period
- **🎯 Intelligent Extraction**: Pulls title, description, times, and images from page
- **🛡️ Bot Protection Bypass**: Uses cloudscraper with retry logic (Railway-compatible)
- **🤖 LLM Fallback**: Automatically uses AI (Gemini/Groq) when web scraping is blocked
- **✅ Duplicate Prevention**: Skips events that already exist in database

#### **✅ Recently Fixed Issues**:
1. **Auto-Fill Button Fixed** (October 10, 2025):
   - **Problem**: Button click with `onclick="autoFillFromUrl(event)"` wasn't triggering
   - **Root Cause**: Event parameter not properly passed in inline onclick handler
   - **Solution**: 
     - Removed inline onclick handler
     - Added button ID (`autoFillBtn`)
     - Simplified `autoFillFromUrl()` to not require parameters
     - Added proper event listener in `openUrlScraperModal()`
   - **Status**: ✅ Fully functional

2. **Venue Dropdown Loading**:
   - Fixed: Changed from `/api/venues` to `/api/admin/venues`
   - Status: ✅ Working

3. **LLM Fallback Added** (October 10, 2025):
   - **Enhancement**: Added automatic LLM extraction when bot protection blocks scraping
   - **How it Works**: Tries web scraping first (3 attempts), then automatically uses LLM
   - **LLM Providers**: Google Gemini, Groq, OpenAI, Anthropic (automatic fallback chain)
   - **Result**: Bot-protected sites (like Met Museum) now work!
   - **Indicator**: Extracted data includes `llm_extracted: true` and confidence level
   - **Status**: ✅ Fully functional

#### **How to Use**:
1. Click "🔗 From URL" button in Events section
2. Paste event page URL
3. Click "🔍 Auto-Fill" button (now works!)
4. Review and edit extracted data
5. Select venue (optional) and city (required)
6. Choose time period for recurring events
7. Click "🔗 Create Events"

#### **Backend Status**:
- ✅ `/api/admin/extract-event-from-url` endpoint functional
- ✅ `extract_event_data_from_url()` function works
- ✅ Cloudscraper bypasses bot protection
- ✅ Schedule detection works ("Fridays 6:30pm - 7:30pm")
- ✅ `/api/admin/scrape-event-from-url` creates events correctly

#### **Frontend Status**:
- ✅ Auto-Fill button click handler (FIXED)
- ✅ Event parameter passing (FIXED)
- ✅ Preview section display
- ✅ Form submission with extracted data

#### **Testing**:
```bash
# Test extraction API
curl -X POST http://localhost:5001/api/admin/extract-event-from-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

📖 **For detailed usage guide, see [docs/URL_EVENT_CREATION_GUIDE.md](docs/URL_EVENT_CREATION_GUIDE.md)**

### **🎯 Event Scraping Intelligence**
- **Today-Focused**: Scrapes events for TODAY only (more relevant and useful)
- **Smart Schedule Detection**: 
  - **Reads actual webpage content** to find schedule (e.g., "Fridays 6:30pm - 7:30pm")
  - **Day-aware filtering**: Only shows events if today matches the specified day
  - **Uses cloudscraper** to bypass bot protection (Railway-compatible, no browser needed)
  - Extracts both start AND end times from page text
  - Falls back to URL-based time extraction (e.g., "630pm" in URL → 6:30 PM)
- **Tour Duration Assumption**: If no end time is specified, assumes 1-hour duration
  - Example: 3:00 PM start → 4:00 PM end (automatically calculated)
  - **Essential for Google Calendar integration** - calendar events require both start and end times
  - Makes events more complete and useful for planning
- **Enhanced Title Extraction**: Converts generic dates to descriptive titles
  - "Friday, October 10" → "Museum Highlights Tour"
  - "Collection Tour: Islamic Art" (from actual page titles)
- **Meeting Point Detection**: Extracts specific locations like "Gallery 534, Vélez Blanco Patio"

### **🌐 Generic Venue Scraper (Universal Fallback)**
- **Universal Compatibility**: A generic scraper (`scripts/generic_venue_scraper.py`) that works for any venue/location by using common patterns learned from specialized scrapers
- **Two-Tier Architecture**: 
  - **Specialized Scrapers** (Priority): Custom scrapers for specific venues (Hirshhorn, NGA, etc.) with venue-specific logic
  - **Generic Scraper** (Fallback): Universal scraper that uses common HTML patterns, CSS selectors, and extraction methods
- **Automatic Fallback**: When standard scraping methods find no events, the system automatically tries the generic scraper
- **Pattern-Based Extraction**: Uses patterns learned from specialized scrapers:
  - Common CSS selectors (`.event`, `.event-item`, `.program`, `.tour`, etc.)
  - JSON-LD structured data extraction
  - Multiple date/time format parsing
  - Automatic event type detection
- **Continuous Improvement**: The generic scraper is designed to evolve - as we create new specialized scrapers or discover new patterns, we extract reusable patterns and add them to the generic scraper, making it work better for more venues over time
- **Error Handling**: Includes bot protection bypass (cloudscraper), SSL error handling, and retry logic
- **Documentation**: See `docs/GENERIC_SCRAPER_GUIDE.md` for detailed usage and integration examples

### **🌐 Deployment Configuration**
- **Platform**: Railway with custom domain `planner.ozayn.com`
- **Database**: PostgreSQL (Railway managed)
- **Environment Detection**: Automatically switches OCR engines based on environment
- **Security**: All API keys properly protected, no exposed credentials
- **🚨 DEPLOYMENT PREFERENCE**: 
  - ✅ **ALWAYS use GitHub integration**: Push to GitHub and let Railway auto-deploy
  - ❌ **NEVER use `railway up`**: Bypasses GitHub, creates inconsistency
  - **Deployment process**: `git push` → Railway auto-detects → Builds → Runs `reset_railway_database.py` → Deploys
  - **Wait time**: ~2-3 minutes for automatic deployment to complete

### **🔄 Syncing Data Between Local & Production**
- **⚠️ CRITICAL**: Local SQLite and Railway PostgreSQL have **different city IDs**
  - Local: New York = city_id 2, Washington = city_id 1
  - Production: New York = city_id 452, Washington = city_id 451
- **Syncing Workflow** (follow these exact steps):
  1. Make data changes locally (e.g., update venue URLs in local database)
  2. Export to JSON: `source venv/bin/activate && python scripts/update_venues_json.py` (or cities, sources)
  3. Commit and push JSON files: `git add data/*.json && git commit -m "Update venue data" && git push`
  4. Wait 2-3 minutes for Railway auto-deploy
  5. Call reload endpoint: `curl -X POST https://planner.ozayn.com/api/admin/reload-venues-from-json`
  6. Verify changes: Check production at `https://planner.ozayn.com/api/admin/venues`
- **Available Reload Endpoints**:
  - `/api/admin/reload-cities` - Reload all cities from `cities.json` (clears and reloads)
  - `/api/admin/reload-venues-from-json` - Sync venues from JSON to production DB
    - Matches venues by **name only** (handles city_id mismatch between environments)
    - Updates all venue fields (website_url, social media, contact info, etc.)
    - Returns stats: `{updated_count, venues_in_json, venues_matched}`
  - `/api/admin/load-all-data` - **Load all data** (cities, venues, sources) from JSON files
    - **Use this after deployment** if venues/sources are empty
    - Clears existing data and reloads from JSON files
    - Handles city matching automatically (case-insensitive)
    - Returns: `{cities_loaded, venues_loaded, venues_skipped, sources_loaded}`
- **Why Not `railway run`?**:
  - ❌ Can't run local scripts on Railway (connection to postgres.railway.internal fails)
  - ✅ Use API endpoints instead - they run in production environment with access to production DB
- **Data Flow**: Local DB → JSON files → Git → Railway → Reload API → Production DB
- **Common Issue**: If URLs don't update, check that JSON was committed/pushed and Railway finished deploying
- **Fix Script Available**: Use `scripts/fix_all_venue_urls.py` to fix known fake URLs in batch
- **🚨 After Railway Deployment**: If venues/sources are empty, call `/api/admin/load-all-data` to reload everything
- **Venue Loading Structure**:
  - `venues.json` has venues at top level (not nested under cities)
  - Each venue has a `city_name` field used for matching
  - City matching is case-insensitive and handles different formats
  - If venues don't load, check `venues_skipped` count in response
- **Venue Loading Notes**:
  - `venues.json` structure: Venues are at top level, each has `city_name` field
  - City matching is case-insensitive and handles different formats
  - If `venues_skipped > 0`, check Railway logs for city matching errors
  - The endpoint loads cities first, then venues (matching by city_name), then sources
- **🚨 After Railway Deployment**: If venues/sources are empty, call `/api/admin/load-all-data` to reload everything

### **🐛 Troubleshooting Common Issues**
- **"no module named bs4" Error**:
  - **Cause**: Using system Python instead of virtual environment
  - **Solution**: `source venv/bin/activate && python` instead of `python3`
  - **Check**: `which python` should show `/Users/oz/Dropbox/2025/planner/venv/bin/python`
- **"no module named requests" Error**:
  - **Cause**: Same issue - virtual environment not activated
  - **Solution**: Always use `source venv/bin/activate && python`
- **Port 5000 already in use**:
  - **Cause**: Another app using port 5000
  - **Solution**: Use port 5001 (already configured in app.py)
- **Railway deployment fails**:
  - **Cause**: Missing dependencies or environment variables
  - **Solution**: Check requirements.txt and .env file are committed
- **Venues/Sources Empty After Deployment**:
  - **Cause**: Railway deployment clears database but may fail to reload data
  - **Solution**: Call reload endpoint after deployment: `curl -X POST https://planner.ozayn.com/api/admin/load-all-data`
  - **Note**: The `/api/admin/load-all-data` endpoint loads cities, venues, and sources from JSON files
  - **Structure**: `venues.json` has venues at top level with `city_name` field (not nested under cities)
  - **City Matching**: Uses case-insensitive matching to find cities by name
  - **Response**: Check `venues_loaded` and `venues_skipped` in response to debug issues
  - **Known Issue (Fixed)**: The `load-all-data` endpoint had a bug where it returned early after loading venues, preventing sources from loading. This has been fixed.
  - **If venues still don't load**: Check Railway logs for city matching errors - venues are skipped if their `city_name` doesn't match any city in the database
- **Venues/Sources Empty After Deployment**:
  - **Cause**: Railway deployment clears database but may fail to reload data
  - **Solution**: Call reload endpoint after deployment: `curl -X POST https://planner.ozayn.com/api/admin/load-all-data`
  - **Note**: The `/api/admin/load-all-data` endpoint loads cities, venues, and sources from JSON files
  - **Structure**: `venues.json` has venues at top level with `city_name` field (not nested under cities)
  - **City Matching**: Uses case-insensitive matching to find cities by name
  - **Response**: Check `venues_loaded` and `venues_skipped` in response to debug issues
  - **Known Issue (Fixed)**: The `load-all-data` endpoint had a bug where it returned early after loading venues, preventing sources from loading. This has been fixed.
  - **If venues still don't load**: Check Railway logs for city matching errors - venues are skipped if their `city_name` doesn't match any city in the database

### **⚠️ JavaScript Variable Scope - Admin Table Sorting**
**CRITICAL LESSON LEARNED**: Never declare local variables that shadow window-scoped data arrays!

#### **The Bug Pattern (DO NOT DO THIS)**:
```javascript
// ❌ WRONG - Creates local variable that shadows window scope
let allSources = [];

async function loadSources() {
    allSources = await fetch('/api/admin/sources').then(r => r.json());
    // Problem: sortTable() looks for window.allSources but finds local allSources
}

function sortTable(tableId, field) {
    dataArray = window.allSources;  // ❌ Undefined! Local variable shadows it
}
```

#### **The Correct Pattern (DO THIS)**:
```javascript
// ✅ CORRECT - No local declaration, uses window scope directly

async function loadSources() {
    window.allSources = await fetch('/api/admin/sources').then(r => r.json());
    // Now sortTable() can find window.allSources correctly
}

function sortTable(tableId, field) {
    dataArray = window.allSources;  // ✅ Works! Finds window-scoped variable
}
```

#### **Why This Matters**:
- **Admin table sorting** relies on `window.allEvents`, `window.allVenues`, `window.allCities`, `window.allSources`
- **Local variable declarations** (`let`, `const`, `var`) create **shadowing** in that scope
- **Symptom**: Sorting appears broken, console shows "Data arrays not available"
- **Fix**: Remove local declarations, always use `window.variableName` explicitly

#### **Checklist for New Admin Tables**:
- [ ] ❌ NO `let allTableName = []` declarations
- [ ] ✅ USE `window.allTableName` in load function
- [ ] ✅ USE `window.allTableName` in all references
- [ ] ✅ USE `window.filteredTableName` for filtered data
- [ ] ✅ TEST sorting immediately after adding new table

#### **Real Example - Sources Table Bug**:
```javascript
// Before (BROKEN):
let allSources = [];  // ❌ This line broke sorting!
async function loadSources() {
    allSources = await response.json();  // Sets local, not window
}

// After (FIXED):
// No declaration here!
async function loadSources() {
    window.allSources = await response.json();  // ✅ Sets window scope
}
```

**Remember**: Events, Venues, and Cities tables work because they DON'T have local declarations!

### **🔒 Security & API Keys**
- **NEVER commit `.env` file**: Contains sensitive API keys and secrets
- **NEVER hardcode API keys**: Always use environment variables
- **Check `.gitignore`**: Ensure `.env`, `*.key`, `*.pem` files are ignored
- **Rotate keys regularly**: Change API keys periodically for security
- **Use different keys**: Separate keys for development, staging, and production
- **Monitor key usage**: Check API dashboards for unusual activity
- **Secure credentials file**: `config/google-vision-credentials.json` contains Google service account
- **Environment-specific configs**: Use `FLASK_ENV=development` locally, `production` on Railway
- **Security tools available**: 
  - Run `./scripts/security_check.sh` to scan for exposed secrets
  - Use `./clean_api_key.sh` if API keys were accidentally committed

### **💻 Development Rules**
- **Always use modal forms for edit functions**: Never use `prompt()` dialogs for editing data
- **Prevent event bubbling**: Add `event.stopPropagation()` to action buttons to prevent row click events
- **Use proper form validation**: All modals should have client-side and server-side validation
- **Maintain consistent UX**: All tables should follow the same interaction patterns
- **🚨 Database schema changes**: When adding/modifying table columns, update ALL related components:
  - **Model definition**: Add new fields to SQLAlchemy model class
  - **Database migration**: ✅ **AUTOMATIC** - Schema auto-migrates on Railway startup
  - **Modal forms**: Add/edit forms must include new fields with proper validation
  - **Table headers**: Update display logic to show new fields
  - **API endpoints**: Update all CRUD endpoints to handle new fields
  - **Data processing**: Update hybrid event processor and extraction logic
  - **Form validation**: Add client-side and server-side validation for new fields
  - **JavaScript functions**: Update all functions that reference field names
  - **Calendar integration**: Update calendar event creation to include new fields
  - **Deployment database**: ✅ **AUTOMATIC** - Railway PostgreSQL auto-syncs with local SQLite
  - **Backward compatibility**: Maintain legacy field support during transition
  - **Testing**: Test all forms, APIs, and integrations with new schema
  - **🚨 CRITICAL**: Monitor ALL processes that populate form fields:
    - **LLM prompts**: Update extraction prompts to request new fields
    - **Response parsing**: Update JSON parsing logic to handle new fields
    - **Fallback extraction**: Update regex patterns and fallback logic
    - **Data flow tracing**: Follow data from extraction → processing → storage → display
    - **Field mapping**: Ensure all field references are updated consistently
    - **Logging**: Update log messages to reflect new field names

### **🔄 Schema Synchronization (SOLVED)**
- **✅ Automatic Migration**: The app now automatically migrates Railway PostgreSQL to match local SQLite schema on startup
- **✅ No Manual Steps**: Schema changes are automatically deployed when you push code to GitHub
- **✅ Type Conversion**: SQLite types are automatically converted to PostgreSQL equivalents
- **✅ Error Handling**: Migration failures are logged but don't crash the app
- **Manual Sync**: If needed, run `python scripts/sync_schema.py` with Railway environment

### **📚 Lessons Learned from Schema Issues**
- **Problem**: Railway PostgreSQL doesn't automatically create new columns when SQLAlchemy models are updated
- **Root Cause**: SQLAlchemy only creates tables, not column additions, on existing databases
- **Solution**: Auto-migration function runs on Railway startup to add missing columns
- **Key Insight**: Always define expected columns in code rather than reading from local SQLite (which doesn't exist on Railway)
- **Dashboard Impact**: Missing columns cause API errors, resulting in "undefined" counts on admin dashboard
- **Prevention**: The auto-migration function prevents this recurring problem permanently

### **🔧 Troubleshooting Schema Issues**
- **Symptom**: Dashboard shows "undefined" counts for Cities, Venues, Events, Sources
- **Cause**: Missing columns in Railway PostgreSQL database
- **Check**: Look for errors like "column events.social_media_platform does not exist" in Railway logs
- **Solution**: The auto-migration should fix this automatically on next deployment
- **Manual Fix**: If auto-migration fails, run `python scripts/sync_schema.py` with Railway environment
- **Verification**: Check API endpoints return correct counts: `/api/admin/cities`, `/api/admin/venues`, etc.
- **🚨 Timezone handling**: Always use CITY timezone for event date/time processing:
  - Image upload event extraction MUST use city timezone, not server timezone
  - Date/time parsing should consider the event's location timezone
  - Never use `datetime.now()` or `date.today()` without timezone context

### **🔧 Testing & Debugging**
- **Test in both environments**: Always test locally AND on Railway deployment
- **Check browser console**: Look for JavaScript errors before reporting issues
- **Verify data persistence**: After adding/editing, refresh page to confirm data saved
- **Test all CRUD operations**: Create, Read, Update, Delete for each entity type
- **Mobile responsiveness**: Test on mobile devices - app uses pastel design for mobile-first
- **🚨 Always check `.env` file first**: When troubleshooting, check `.env` for API keys, configuration, and environment settings

### **📁 File Organization**
- **Never modify files in `/archive/`**: These are outdated - use current files in root directories
- **Keep scripts in `/scripts/`**: All utility scripts belong there, not in root
- **Update documentation**: When changing functionality, update relevant docs in `/docs/`
- **Use proper imports**: Import from correct modules (e.g., `scripts/utils.py`, not `utils.py`)

### **🚀 Performance & Optimization**
- **Monitor API calls**: Check browser Network tab for failed requests
- **Image optimization**: Large images in `/uploads/` can slow down the app
- **Database queries**: Use browser dev tools to monitor slow database operations
- **Memory leaks**: Check for JavaScript memory leaks in long-running sessions

### **📊 Current System Status**
- **Cities**: 25 loaded
- **Venues**: 178 loaded  
- **Sources**: 37 loaded
- **Hybrid Processing**: ✅ Production ready
- **Instagram Recognition**: ✅ Working perfectly

## ✨ Features

- **🌍 Global Cities**: Support for 22 major cities worldwide with 147+ venues
- **🏛️ Venue Management**: Comprehensive venue database with images, hours, and details
- **📰 Event Sources**: 36+ event sources for Washington DC with smart scraping
- **🎨 Minimal Design**: Pastel colors, artistic fonts, icon-based UI
- **🔧 Admin Interface**: Full CRUD operations for cities, venues, and sources
- **🛡️ Bulletproof Setup**: Automated restart script with dependency management
- **🤖 LLM Integration**: Multiple AI providers (Groq, OpenAI, Anthropic, etc.)
- **📊 Data Management**: JSON-based data with database synchronization

## 🚀 Quick Start

⚠️ **IMPORTANT: Always activate virtual environment first!**

### Option 1: Automated Setup
```bash
# Clone and setup
git clone https://github.com/ozayn/planner.git
cd planner

# 🔥 ALWAYS RUN THIS FIRST!
source venv/bin/activate

# Create virtual environment (if not exists)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with setup.py (recommended)
python setup.py install

# Or install dependencies manually
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python scripts/data_manager.py load

# Start the app
python app.py
```

### Option 2: Manual Setup Only
```bash
# Clone and setup
git clone https://github.com/ozayn/planner.git
cd planner

# 🔥 ALWAYS RUN THIS FIRST!
source venv/bin/activate

# Create virtual environment (if not exists)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python scripts/data_manager.py load

# Start the app
python app.py
```

Visit: `http://localhost:5001`

📖 **For detailed setup instructions, see [docs/setup/SETUP_GUIDE.md](docs/setup/SETUP_GUIDE.md)**

## 🎭 Event Types

### 🚶 Tours
- Museum tours with start/end times
- Meeting locations (entrance, rotunda, specific floors)
- Images (tour-specific or museum default)
- Opening hours tracking
- Google Calendar integration

### 🏛️ Venues
- Museums, buildings, locations
- Opening hours for specific dates
- Location and images
- Instagram links for additional events

### 🎨 Exhibitions
- Date ranges
- Specific locations within venues
- Multi-day calendar events

### 🎪 Festivals
- Single or multi-day events
- Multiple locations for different days

### 📸 Photowalks
- Start/end times and locations
- Descriptions and details

## 🛠️ Technical Stack

- **Backend**: Python Flask with SQLAlchemy
- **Database**: SQLite (local development), PostgreSQL (Railway production)
- **Frontend**: HTML/CSS/JavaScript with minimal design
- **AI Integration**: Multiple LLM providers (Groq, OpenAI, Anthropic, Cohere, Google, Mistral)
- **Data Management**: JSON files with database synchronization
- **Admin Interface**: Dynamic CRUD operations
- **Deployment**: Railway-ready with Procfile
- **Design**: Pastel colors, minimal UI, icon-based interactions


## 📁 Project Structure

```
planner/
├── app.py                 # Main Flask application
├── data/                  # JSON data files
│   ├── cities.json        # Predefined cities
│   ├── venues.json        # Predefined venues
│   └── sources.json       # Event sources
├── scripts/               # Utility scripts
│   ├── data_manager.py    # Database management
│   ├── utils.py           # Core utilities
│   ├── env_config.py      # Environment configuration
│   └── enhanced_llm_fallback.py # LLM integration
├── templates/             # HTML templates
│   ├── index.html         # Main web interface
│   ├── admin.html         # Admin interface
│   └── debug.html         # Debug interface
├── docs/                  # 📚 Comprehensive Documentation
│   ├── setup/             # Setup & installation guides
│   ├── deployment/        # Deployment guides
│   ├── admin/             # Admin interface docs
│   ├── data/              # Data management guides
│   ├── session-notes/     # Development session notes
│   └── README.md          # Documentation index
├── archive/               # Archived files
│   ├── outdated_scripts/  # Old scripts
│   └── outdated_docs/     # Old documentation
├── requirements.txt       # Production dependencies
├── restart.sh            # Bulletproof restart script
├── setup_github.sh       # GitHub setup script
└── README.md             # This file
```

## 📚 Documentation

All documentation is organized in the `docs/` directory:

- **[📖 Documentation Index](docs/README.md)** - Complete documentation overview
- **[🚀 Setup Guide](docs/setup/SETUP_GUIDE.md)** - Detailed installation instructions
- **[☁️ Deployment Guide](docs/deployment/RAILWAY_DEPLOYMENT.md)** - Railway deployment
- **[🔍 Google Vision Setup](docs/setup/GOOGLE_VISION_SETUP.md)** - OCR configuration
- **[🏗️ Architecture](docs/ARCHITECTURE.md)** - System design
- **[📊 API Documentation](docs/API_DOCUMENTATION.md)** - API endpoints

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# LLM API Keys (optional - app works without them)
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
COHERE_API_KEY=your_cohere_api_key
GOOGLE_API_KEY=your_google_api_key
MISTRAL_API_KEY=your_mistral_api_key

# Google Maps (optional)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# Eventbrite API (optional - for scraping Eventbrite events)
# Use Personal OAuth Token (Private Token) - this is what you need for reading public events
EVENTBRITE_API_TOKEN=your_eventbrite_personal_oauth_token
# Alternative name (both work):
# EVENTBRITE_PRIVATE_TOKEN=your_eventbrite_personal_oauth_token
# Optional: Public token for anonymous access (limited functionality)
# EVENTBRITE_PUBLIC_TOKEN=ZRQRSTL4V3Y5X2X5X2X5

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key

# Database
DATABASE_URL=sqlite:///instance/events.db
```

## 🎨 Design System

### Colors
- Primary Pastel: `#E8F4FD`
- Secondary Pastel: `#F0F8E8`
- Accent Pastel: `#FFF0F5`
- Neutral Pastel: `#F8F9FA`

### Fonts
- Display: Playfair Display (artistic serif)
- Body: Inter (clean sans-serif)

### Principles
- Minimal text, maximum icons
- Soft shadows and rounded corners
- No dark buttons or harsh edges
- Pastel color palette throughout

## 📊 Database Schema

The app uses a comprehensive database schema supporting:
- Cities with timezone information
- Venues with opening hours
- Multiple event types (tours, exhibitions, festivals, photowalks)
- Polymorphic event inheritance
- Calendar integration tracking

## 🔧 API Endpoints

- `GET /api/cities` - Get available cities
- `GET /api/events` - Get events with filters
- `GET /api/venues` - Get venues for a city
- `POST /api/calendar/add` - Add event to Google Calendar

## 🌐 Supported Cities

Currently seeded with 22 cities including:
- Washington, DC (38 venues, 36 sources)
- New York, NY (10 venues)
- Los Angeles, CA (5 venues)
- San Francisco, CA (5 venues)
- Chicago, IL (5 venues)
- Boston, MA (5 venues)
- Seattle, WA (5 venues)
- Miami, FL (5 venues)
- London, UK (10 venues)
- Paris, France (10 venues)
- Tokyo, Japan (5 venues)
- Sydney, Australia (5 venues)
- Montreal, Canada (5 venues)
- Toronto, Canada (5 venues)
- Vancouver, Canada (5 venues)
- Tehran, Iran (5 venues)
- Baltimore, MD (5 venues)
- Philadelphia, PA (5 venues)
- Madrid, Spain (5 venues)
- Berlin, Germany (5 venues)
- Munich, Germany (5 venues)
- Princeton, NJ (9 venues)

## 🏗️ Professional Structure

This project follows professional Python development practices:

- **Clean Architecture**: Separated concerns with config/, scripts/, tests/ directories
- **Modular Design**: Each component has its own module with proper imports
- **Testing Suite**: Comprehensive unit tests in tests/ directory
- **Configuration Management**: Environment-based configuration with settings.py
- **Development Tools**: Separate requirements-dev.txt for development dependencies
- **Documentation**: Comprehensive README and inline documentation
- **Code Organization**: No messy files in root directory - everything properly organized

## 🔧 Troubleshooting

### Quick Fixes
- **🚨 Image processing broken?** → [QUICK_FIX_GUIDE.md](docs/QUICK_FIX_GUIDE.md)
- **Port 5000 in use**: App runs on port 5001 by default
- **Database errors**: Run `python scripts/data_manager.py load` to reload data
- **Python not found**: Use `python3` instead of `python`
- **Dependencies not found**: Make sure virtual environment is activated with `source venv/bin/activate`
- **API key errors**: Add your API keys to `.env` file (GROQ_API_KEY, OPENAI_API_KEY, etc.)

### Getting Help
- **Quick fixes**: [QUICK_FIX_GUIDE.md](docs/QUICK_FIX_GUIDE.md) - Common issues solved in 2 minutes
- **Detailed setup**: [docs/setup/SETUP_GUIDE.md](docs/setup/SETUP_GUIDE.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 🤝 Contributing

1. Follow the minimal design principles
2. Use pastel colors and artistic fonts
3. Prefer icons over text labels
4. Maintain timezone accuracy
5. Test on both web and mobile
6. Follow the established project structure
7. Add tests for new features
8. Update documentation as needed

## 📄 License

MIT License - feel free to use and modify!
