# Event Planner App

A minimal, artistic web and mobile app for discovering events in cities worldwide.

## ✨ Features

- **🌍 Global Cities**: Support for major cities worldwide (DC, NYC, London, LA, etc.)
- **⏰ Smart Filtering**: Today, tomorrow, this week, this month
- **🎯 Event Types**: Tours, venues, exhibitions, festivals, photowalks
- **📅 Calendar Integration**: Add events to Google Calendar with timezone support
- **🎨 Minimal Design**: Pastel colors, artistic fonts, icon-based UI
- **📱 Mobile App**: React Native app with consistent design
- **🕷️ Smart Scraping**: Generic scraping system for museums and events

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd planner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp env_example.txt .env

# Initialize database
python scripts/seed_data.py

# Start the app
python app.py
```

Visit: `http://localhost:5001`

📖 **For detailed setup instructions, see [SETUP.md](SETUP.md)**

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

- **Backend**: Python Flask
- **Database**: SQLAlchemy (SQLite)
- **Scraping**: BeautifulSoup, Selenium
- **Calendar**: Google Calendar API
- **Web Frontend**: HTML/CSS/JavaScript with artistic fonts
- **Mobile**: React Native
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
python scripts/seed_data.py
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
├── config/                # Configuration and models
│   ├── __init__.py
│   ├── models.py          # Database models (legacy)
│   ├── settings.py        # App configuration
│   ├── calendar_service.py # Google Calendar integration
│   └── scraper.py         # Web scraping utilities
├── scripts/               # Utility scripts
│   ├── __init__.py
│   └── seed_data.py       # Database seeding
├── tests/                 # Test suite
│   ├── __init__.py
│   └── test_app.py        # Unit tests
├── templates/             # HTML templates
│   └── index.html         # Main web interface
├── static/                # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── mobile/                # React Native mobile app
│   ├── App.js
│   ├── package.json
│   └── README.md
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── setup.py              # Automated setup script
└── README.md             # This file
```

## 📱 Mobile App Setup

```bash
cd mobile
npm install
npm start
# Then run on device/emulator
npm run android  # or npm run ios
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Database
DATABASE_URL=sqlite:///events.db

# Flask
FLASK_ENV=development
FLASK_DEBUG=True

# Google Calendar API
GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=token.json

# App
APP_PORT=5001
APP_HOST=0.0.0.0
```

### Google Calendar Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create credentials (OAuth 2.0)
5. Download credentials.json
6. Place in project root

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

Currently seeded with:
- Washington, DC
- New York, NY
- Baltimore, MD
- Philadelphia, PA
- London, UK
- Los Angeles, CA
- Paris, France
- Tokyo, Japan
- Sydney, Australia

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
- **Port 5000 in use**: Change `APP_PORT` in `.env` to 5001
- **Database errors**: Delete `instance/events.db` and run `python scripts/seed_data.py`
- **Python not found**: Use `python3` instead of `python`
- **Dependencies not found**: Make sure virtual environment is activated

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
