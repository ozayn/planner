# Event Planner - Complete Setup Guide

## Overview
A web and mobile application for discovering and managing events across major cities worldwide. Features include city selection, time range filtering, event types (tours, exhibitions, festivals, photowalks), and Google Calendar integration with timezone support.

## Prerequisites
- Python 3.8 or higher
- Node.js 16+ (for mobile app)
- Git

## Quick Start

### 1. Clone and Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd planner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
# Create database and seed with sample data
python scripts/seed_data.py
```

### 3. Start Web Application
```bash
# Start the Flask server
python app.py
```

The web application will be available at: `http://localhost:5001`

### 4. Mobile App Setup (Optional)
```bash
# Navigate to mobile directory
cd mobile

# Install dependencies
npm install

# Start React Native development server
npx react-native start

# Run on iOS simulator
npx react-native run-ios

# Run on Android emulator
npx react-native run-android
```

## Environment Configuration

### Required Environment Variables
Create a `.env` file in the root directory:

```env
# Application Settings
APP_PORT=5001
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///instance/events.db

# Google Calendar Integration (Optional)
GOOGLE_CALENDAR_CLIENT_ID=your-client-id
GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:5001/auth/callback
```

### Google Calendar Setup (Optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Add credentials to `.env` file

## Project Structure
```
planner/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── config/               # Configuration modules
│   ├── models.py         # Database models
│   ├── calendar_service.py # Google Calendar integration
│   ├── scraper.py        # Generic web scraping
│   └── museum_scrapers.py # Museum-specific scrapers
├── scripts/              # Utility scripts
│   ├── seed_data.py      # Database seeding
│   └── populate_real_data.py # Real data scraping
├── templates/            # Web frontend
│   └── index.html        # Main web interface
├── mobile/               # React Native mobile app
│   ├── App.js           # Main mobile component
│   └── package.json     # Mobile dependencies
├── instance/            # Database files
└── tests/              # Test files
```

## Features

### Web Application
- **City Selection**: Choose from major cities worldwide
- **Time Filtering**: Today, tomorrow, this week, this month
- **Event Types**: Tours, exhibitions, festivals, photowalks
- **Calendar Integration**: Add events to Google Calendar with timezone support
- **Responsive Design**: Works on desktop and mobile browsers

### Mobile Application
- **React Native**: Cross-platform iOS and Android support
- **Same Features**: All web features available on mobile
- **Native Performance**: Optimized for mobile devices

### Event Types
1. **Tours**: Museum tours with start/end times, meeting locations, descriptions
2. **Exhibitions**: Art and cultural exhibitions with date ranges
3. **Festivals**: Single or multi-day events, single or multiple locations
4. **Photowalks**: Photography sessions with start/end locations

### Supported Cities
- **United States**: Washington DC, New York, Baltimore, Philadelphia, Los Angeles
- **International**: London, Paris, Tokyo, Sydney

## Database Schema

### Core Models
- **City**: City information with timezone support
- **Venue**: Museums, buildings, locations
- **Tour**: Guided tours with times and locations
- **Exhibition**: Art exhibitions with date ranges
- **Festival**: Multi-day events
- **Photowalk**: Photography sessions

## API Endpoints

### Web API
- `GET /api/cities` - List all cities
- `GET /api/events` - Get events with filters
- `POST /api/calendar/add` - Add event to Google Calendar

### Parameters
- `city_id`: Filter by city
- `time_range`: today, tomorrow, this_week, this_month
- `event_type`: tours, exhibitions, festivals, photowalks

## Development

### Adding New Cities
1. Add city to `scripts/seed_data.py`
2. Update timezone mapping in `templates/index.html`
3. Add venues and events for the city

### Adding New Event Types
1. Create model in `config/models.py`
2. Add to API endpoints in `app.py`
3. Update frontend filters in `templates/index.html`

### Web Scraping
- Generic scraper framework in `config/scraper.py`
- Museum-specific scrapers in `config/museum_scrapers.py`
- Run `python scripts/populate_real_data.py` to scrape real data

## Troubleshooting

### Common Issues
1. **Port 5000 in use**: Change `APP_PORT` in `.env` to 5001
2. **Database errors**: Delete `instance/events.db` and run `python scripts/seed_data.py`
3. **Mobile app issues**: Ensure Node.js and React Native CLI are installed
4. **Calendar integration**: Check Google Calendar API credentials

### Debug Mode
```bash
# Enable Flask debug mode
export FLASK_ENV=development
python app.py
```

## Production Deployment

### Environment Variables
```env
FLASK_ENV=production
SECRET_KEY=production-secret-key
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@host/db
```

### Database Migration
```bash
# For production, consider using Alembic for migrations
pip install alembic
alembic init alembic
```

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test thoroughly
5. Submit a pull request

## License
[Add your license information here]
