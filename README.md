# Event Planner App

A minimal, artistic web and mobile app for discovering events in cities worldwide.

## 🚨 **IMPORTANT REMINDERS**

### **🔑 Critical Setup Steps**
- **ALWAYS activate virtual environment first**: `source venv/bin/activate`
- **Use port 5001, never 5000**: App runs on `http://localhost:5001`
- **Use `python3` not `python`**: System Python vs venv Python
- **Environment variables**: Add API keys to `.env` file (never commit this file)

### **🤖 Hybrid OCR + LLM System**
- **Default OCR**: Tesseract (local), Google Vision API (deployment)
- **LLM Processing**: Google Gemini for intelligent event extraction
- **Smart Detection**: Automatically chooses optimal OCR engine
- **Instagram Context**: Extracts page names, handles, and poster info
- **Intelligent Processing**: 90% confidence with Vision API, 80% with Tesseract

### **🌐 Deployment Configuration**
- **Platform**: Railway with custom domain `planner.ozayn.com`
- **Database**: PostgreSQL (Railway managed)
- **Environment Detection**: Automatically switches OCR engines based on environment
- **Security**: All API keys properly protected, no exposed credentials

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
  - **Database migration**: Create and run migration script to add columns
  - **Modal forms**: Add/edit forms must include new fields with proper validation
  - **Table headers**: Update display logic to show new fields
  - **API endpoints**: Update all CRUD endpoints to handle new fields
  - **Data processing**: Update hybrid event processor and extraction logic
  - **Form validation**: Add client-side and server-side validation for new fields
  - **JavaScript functions**: Update all functions that reference field names
  - **Calendar integration**: Update calendar event creation to include new fields
  - **Deployment database**: Run migration on production database (Railway PostgreSQL)
  - **Backward compatibility**: Maintain legacy field support during transition
  - **Testing**: Test all forms, APIs, and integrations with new schema
  - **🚨 CRITICAL**: Monitor ALL processes that populate form fields:
    - **LLM prompts**: Update extraction prompts to request new fields
    - **Response parsing**: Update JSON parsing logic to handle new fields
    - **Fallback extraction**: Update regex patterns and fallback logic
    - **Data flow tracing**: Follow data from extraction → processing → storage → display
    - **Field mapping**: Ensure all field references are updated consistently
    - **Logging**: Update log messages to reflect new field names
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
