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

# Setup environment (create .env file)
# Add your API keys to .env file

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
- **Database**: SQLite with comprehensive schema
- **Frontend**: HTML/CSS/JavaScript with minimal design
- **AI Integration**: Multiple LLM providers (Groq, OpenAI, Anthropic, Cohere, Google, Mistral)
- **Data Management**: JSON files with database synchronization
- **Admin Interface**: Dynamic CRUD operations
- **Deployment**: Railway-ready with Procfile
- **Design**: Pastel colors, minimal UI, icon-based interactions

## 🚀 Quick Start

### Option 1: Automated Setup
```bash
python setup.py
```

### Option 2: Manual Setup

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Setup Environment**
```bash
cp env_example.txt .env
# Edit .env with your configuration
```

3. **Initialize Database**
```bash
python scripts/data_manager.py load
```

4. **Run the App**
```bash
python app.py
```

5. **Open Browser**
```
http://localhost:5001
```

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

### Common Issues
- **Port 5000 in use**: App runs on port 5001 by default
- **Database errors**: Run `python scripts/data_manager.py load` to reload data
- **Python not found**: Use `python3` instead of `python`
- **Dependencies not found**: Make sure virtual environment is activated with `source venv/bin/activate`
- **API key errors**: Add your API keys to `.env` file (GROQ_API_KEY, OPENAI_API_KEY, etc.)

### Getting Help
- Check [SETUP.md](SETUP.md) for detailed instructions
- Check [REQUIREMENTS.md](REQUIREMENTS.md) for project understanding

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
