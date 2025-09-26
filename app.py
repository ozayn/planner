import os
import sys
import json
import re
import logging
from datetime import datetime, timedelta, date
from functools import wraps

# Google OAuth imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    
    # Configure OAuth for Railway's proxy environment
    import os
    if 'RAILWAY_ENVIRONMENT' in os.environ:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: Google OAuth libraries not found. Admin authentication will be disabled.")
    GOOGLE_OAUTH_AVAILABLE = False

# Try to import dotenv with fallback
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  Warning: python-dotenv not found. Environment variables may not be loaded.")
    print("   Run: source venv/bin/activate")
    # Try to add venv to path as fallback
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_site_packages = os.path.join(project_root, 'venv', 'lib', 'python3.13', 'site-packages')
    if os.path.exists(venv_site_packages):
        sys.path.insert(0, venv_site_packages)
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ Successfully loaded dotenv from virtual environment")
        except ImportError:
            pass

# Import Flask components
try:
    from flask import Flask, render_template, request, jsonify, session, redirect
    from flask_cors import CORS
    from flask_sqlalchemy import SQLAlchemy
    from flask_wtf.csrf import CSRFProtect
    import pytz
except ImportError as e:
    print(f"❌ Error importing Flask components: {e}")
    print("   Please run: source venv/bin/activate")
    sys.exit(1)

# Import field cleaning utilities
from scripts.utils import (
    clean_text_field,
    clean_url_field,
    clean_email_field,
    clean_phone_field,
    clean_numeric_field,
    clean_integer_field
)
from scripts.env_config import ensure_env_loaded, get_app_config

# Ensure environment is loaded
ensure_env_loaded()

# Configure logging
def setup_logging():
    """Setup comprehensive logging for debugging"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Setup file handler for all logs
    file_handler = logging.FileHandler(os.path.join(logs_dir, 'app.log'))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Setup console handler for important logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[file_handler, console_handler]
    )
    
    # Create specific loggers
    app_logger = logging.getLogger('app')
    api_logger = logging.getLogger('api')
    venue_logger = logging.getLogger('venue')
    llm_logger = logging.getLogger('llm')
    
    return app_logger, api_logger, venue_logger, llm_logger

# Setup logging
app_logger, api_logger, venue_logger, llm_logger = setup_logging()

# Get app configuration
app_config = get_app_config()
DEFAULT_MAX_VENUES = app_config['max_venues_per_city']

app = Flask(__name__)
CORS(app)

# Configure CSRF protection
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['WTF_CSRF_ENABLED'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
csrf = CSRFProtect(app)

# Google OAuth Configuration
if GOOGLE_OAUTH_AVAILABLE:
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
    
    # OAuth scopes (include openid which Google adds automatically)
    SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
    
    # OAuth flow configuration
    CLIENT_CONFIG = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": []
        }
    }
else:
    GOOGLE_CLIENT_ID = None
    GOOGLE_CLIENT_SECRET = None
    ADMIN_EMAILS = []

# Exempt admin API endpoints from CSRF protection
@csrf.exempt
@app.route('/api/admin/add-city', methods=['POST'])
def add_city():
    """Add a new city with proper formatting and duplicate checking"""
    try:
        data = request.get_json()
        
        # Get and format the input data
        name = data.get('name', '').strip()
        country = data.get('country', '').strip()
        state = data.get('state', '').strip() if data.get('state') else None
        
        if not name or not country:
            return jsonify({'error': 'City name and country are required'}), 400
        
        # Format the names properly
        formatted_name = format_city_name(name)
        formatted_country = format_country_name(country, name)  # Pass city name as context
        formatted_state = state.strip().title() if state else None  # Simple title case for states
        
        # Check for duplicates directly (more reliable than external function)
        print(f"🔍 Checking for duplicates: {formatted_name}, {formatted_state}, {formatted_country}")
        
        # Direct duplicate check in the same database session
        duplicate_city = City.query.filter_by(
            name=formatted_name,
            state=formatted_state,
            country=formatted_country
        ).first()
        
        if duplicate_city:
            return jsonify({'error': f'City "{formatted_name}, {formatted_state}" already exists (ID: {duplicate_city.id})'}), 400
        
        # Get timezone - use provided timezone or auto-detect
        provided_timezone = data.get('timezone', '').strip()
        if provided_timezone:
            timezone = provided_timezone
        else:
            timezone = get_timezone_for_city(formatted_name, formatted_country, formatted_state)
        
        # If no state provided, try to get it from geocoding
        if not formatted_state:
            try:
                city_details = get_city_details_with_geopy(formatted_name, formatted_country)
                if city_details and city_details.get('state'):
                    formatted_state = city_details['state']
                    print(f"Auto-detected state/province: {formatted_state}")
            except Exception as e:
                print(f"Could not auto-detect state for {formatted_name}: {e}")
        
        # Create the city
        city = City(
            name=formatted_name,
            state=formatted_state,
            country=formatted_country,
            timezone=timezone
        )
        
        db.session.add(city)
        db.session.commit()
        
        # Update cities.json
        try:
            from scripts.update_cities_json import update_cities_json
            update_cities_json()
        except Exception as cities_json_error:
            print(f"⚠️ Warning: Could not update cities.json: {cities_json_error}")
        
        return jsonify({
            'success': True, 
            'message': f'City "{formatted_name}, {formatted_country}" added successfully',
            'city_id': city.id,
            'city': city.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error adding city: {e}")
        return jsonify({'error': str(e)}), 500

# Database configuration
# Use Railway's DATABASE_URL if available, otherwise use local SQLite
if os.getenv('DATABASE_URL'):
    # Production database (Railway PostgreSQL)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
else:
    # Development database (local SQLite) - use project directory
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'events.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Auto-migrate schema on startup (Railway only)
def auto_migrate_schema():
    """Automatically migrate Railway PostgreSQL schema to match expected schema."""
    if os.getenv('RAILWAY_ENVIRONMENT') and os.getenv('DATABASE_URL'):
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            
            # Connect to Railway PostgreSQL
            railway_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            railway_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            railway_cursor = railway_conn.cursor()
            
            # Get Railway schema
            railway_cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'events'
            """)
            railway_columns = {row[0]: row[1] for row in railway_cursor.fetchall()}
            
            # Define expected columns (based on current Event model)
            expected_columns = [
                ('social_media_platform', 'VARCHAR(50)'),
                ('social_media_handle', 'VARCHAR(100)'),
                ('social_media_page_name', 'VARCHAR(100)'),
                ('social_media_posted_by', 'VARCHAR(100)'),
                ('social_media_url', 'VARCHAR(500)'),
                ('start_location', 'VARCHAR(200)'),
                ('end_location', 'VARCHAR(200)')
            ]
            
            # Add missing columns
            added_count = 0
            for col_name, pg_type in expected_columns:
                if col_name not in railway_columns:
                    try:
                        railway_cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {pg_type}")
                        added_count += 1
                        print(f"✅ Auto-migrated: {col_name}")
                    except Exception as e:
                        print(f"⚠️  Auto-migration failed for {col_name}: {e}")
            
            if added_count > 0:
                print(f"🎉 Auto-migrated {added_count} columns to Railway PostgreSQL")
            else:
                print("✅ Railway schema is already up to date")
            
            railway_cursor.close()
            railway_conn.close()
            
        except Exception as e:
            print(f"⚠️  Auto-migration failed: {e}")

# Run auto-migration on startup
auto_migrate_schema()

# Define models directly in app.py for simplicity
class City(db.Model):
    """Cities where events take place"""
    __tablename__ = 'cities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=True)  # For US states, null for international
    country = db.Column(db.String(100), nullable=False)
    timezone = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    venues = db.relationship('Venue', backref='city', lazy=True)
    events = db.relationship('Event', backref='city', lazy=True)
    
    def to_dict(self):
        # Format display name based on whether it's a US city with state
        if self.state and self.country == 'United States':
            display_name = f"{self.name}, {self.state}"
        else:
            display_name = f"{self.name}, {self.country}"
        
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'country': self.country,
            'display_name': display_name,
            'timezone': self.timezone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Venue(db.Model):
    """Venues like museums, buildings, locations"""
    __tablename__ = 'venues'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    venue_type = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    image_url = db.Column(db.String(500))
    instagram_url = db.Column(db.String(200))
    facebook_url = db.Column(db.String(200))
    twitter_url = db.Column(db.String(200))
    youtube_url = db.Column(db.String(200))
    tiktok_url = db.Column(db.String(200))
    website_url = db.Column(db.String(200))
    description = db.Column(db.Text)
    opening_hours = db.Column(db.Text)
    holiday_hours = db.Column(db.Text)
    phone_number = db.Column(db.String(50))
    email = db.Column(db.String(100))
    tour_info = db.Column(db.Text)
    admission_fee = db.Column(db.Text)
    additional_info = db.Column(db.Text)  # JSON blob for extra venue details
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    events = db.relationship('Event', backref='venue', lazy=True)
    
    def to_dict(self):
        # Handle image_url - use secure image proxy endpoint
        image_url = self.image_url
        if image_url:
            # First check if it's a dict with photo_reference
            if isinstance(image_url, dict) and 'photo_reference' in image_url:
                photo_ref = image_url['photo_reference']
                image_url = f"/api/image/{photo_ref}"
            elif isinstance(image_url, str) and image_url.startswith('{'):
                # Try to parse as JSON if it's a string starting with {
                try:
                    import json
                    photo_data = json.loads(image_url)
                    if isinstance(photo_data, dict) and 'photo_reference' in photo_data:
                        photo_ref = photo_data['photo_reference']
                        image_url = f"/api/image/{photo_ref}"
                except (json.JSONDecodeError, TypeError):
                    # If it's not valid JSON, treat as raw photo reference
                    if len(image_url) > 50 and not image_url.startswith('http'):
                        image_url = f"/api/image/{image_url}"
            elif isinstance(image_url, str) and 'maps.googleapis.com' in image_url:
                # Extract photo reference from existing Google Maps URL
                import re
                pattern = r'photoreference=([^&]+)'
                match = re.search(pattern, image_url)
                if match:
                    photo_ref = match.group(1)
                    image_url = f"/api/image/{photo_ref}"
            elif isinstance(image_url, str) and len(image_url) > 50 and not image_url.startswith('http'):
                # Raw photo reference string
                image_url = f"/api/image/{image_url}"
        
        # Generate Google Maps link for navigation
        maps_link = ""
        if self.latitude and self.longitude:
            maps_link = f"https://www.google.com/maps/@{self.latitude},{self.longitude},17z"
        elif self.name and self.name.strip():
            venue_name = self.name.replace(' ', '+')
            maps_link = f"https://www.google.com/maps/search/{venue_name}"
        else:
            maps_link = "https://www.google.com/maps"
        
        return {
            'id': self.id,
            'name': self.name,
            'venue_type': self.venue_type,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'image_url': image_url,
            'maps_link': maps_link,  # Add clickable Google Maps link
            'instagram_url': self.instagram_url,
            'facebook_url': self.facebook_url,
            'twitter_url': self.twitter_url,
            'youtube_url': self.youtube_url,
            'tiktok_url': self.tiktok_url,
            'website_url': self.website_url,
            'description': self.description,
            'opening_hours': self.opening_hours,
            'holiday_hours': self.holiday_hours,
            'phone_number': self.phone_number,
            'email': self.email,
            'tour_info': self.tour_info,
            'admission_fee': self.admission_fee,
            'city_id': self.city_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Event(db.Model):
    """Unified event class for all event types"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    image_url = db.Column(db.String(500))
    url = db.Column(db.String(500))
    is_selected = db.Column(db.Boolean, default=True)
    event_type = db.Column(db.String(50), nullable=False)  # 'tour', 'exhibition', 'festival', 'photowalk'
    source = db.Column(db.String(50))  # 'instagram', 'facebook', 'website', etc.
    source_url = db.Column(db.String(500))  # URL of the source (e.g., Instagram post URL)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Location fields (multi-purpose)
    start_location = db.Column(db.String(200))  # Meeting point, exhibition location, start point
    end_location = db.Column(db.String(200))    # End point, secondary location
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id', ondelete='SET NULL'))  # For venue-based events
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'))   # For city-wide events
    
    # Geographic coordinates
    start_latitude = db.Column(db.Float)
    start_longitude = db.Column(db.Float)
    end_latitude = db.Column(db.Float)
    end_longitude = db.Column(db.Float)
    
    # Tour-specific fields
    tour_type = db.Column(db.String(50))        # 'Guided', 'Self-guided', 'Audio tour'
    max_participants = db.Column(db.Integer)
    price = db.Column(db.Float)
    language = db.Column(db.String(50), default='English')
    
    # Exhibition-specific fields
    exhibition_location = db.Column(db.String(200))  # Specific gallery/room
    curator = db.Column(db.String(200))
    admission_price = db.Column(db.Float)
    
    # Festival-specific fields
    festival_type = db.Column(db.String(100))    # 'Music', 'Art', 'Food', 'Cultural'
    multiple_locations = db.Column(db.Boolean, default=False)
    
    # Photowalk-specific fields
    difficulty_level = db.Column(db.String(50))  # 'Easy', 'Medium', 'Hard'
    equipment_needed = db.Column(db.Text)
    organizer = db.Column(db.String(200))
    
    # Social media and source fields (generic for multiple platforms)
    social_media_platform = db.Column(db.String(50))  # 'instagram', 'meetup', 'eventbrite', 'facebook', etc.
    social_media_handle = db.Column(db.String(100))   # Handle without @ (e.g., 'dupontphotowalk')
    social_media_page_name = db.Column(db.String(100))  # Page/group name (e.g., 'DC Street Meet')
    social_media_posted_by = db.Column(db.String(100))  # Who posted the content
    social_media_url = db.Column(db.String(500))       # Direct URL to the post/event
    
    def to_dict(self):
        """Convert event to dictionary with all relevant fields"""
        # Handle image_url - convert photo data to public Google Maps URL (no API key required)
        image_url = self.image_url
        if image_url and isinstance(image_url, dict) and 'photo_reference' in image_url:
            # Generate public Google Maps URL using event location
            if self.start_location and self.start_location.strip():
                location_name = self.start_location.replace(' ', '+')
                if self.start_latitude and self.start_longitude:
                    image_url = f"https://via.placeholder.com/400x300/667eea/ffffff?text={location_name.replace('+', '+')}"
                else:
                    image_url = f"https://via.placeholder.com/400x300/667eea/ffffff?text={location_name.replace('+', '+')}"
            elif self.venue and self.venue.name and self.venue.name.strip():
                venue_name = self.venue.name.replace(' ', '+')
                if self.venue.latitude and self.venue.longitude:
                    image_url = f"https://via.placeholder.com/400x300/667eea/ffffff?text={venue_name.replace('+', '+')}"
                else:
                    image_url = f"https://via.placeholder.com/400x300/667eea/ffffff?text={venue_name.replace('+', '+')}"
            elif self.title and self.title.strip():
                # Fallback to a generic search
                title_name = self.title.replace(' ', '+')
                image_url = f"https://via.placeholder.com/400x300/667eea/ffffff?text={title_name.replace('+', '+')}"
            else:
                # Ultimate fallback
                image_url = "https://via.placeholder.com/400x300/667eea/ffffff?text=Event"
        
        # Generate Google Maps link for navigation
        maps_link = ""
        if self.start_latitude and self.start_longitude:
            maps_link = f"https://www.google.com/maps/@{self.start_latitude},{self.start_longitude},17z"
        elif self.start_location and self.start_location.strip():
            location_name = self.start_location.replace(' ', '+')
            maps_link = f"https://www.google.com/maps/search/{location_name}"
        elif self.venue and self.venue.latitude and self.venue.longitude:
            maps_link = f"https://www.google.com/maps/@{self.venue.latitude},{self.venue.longitude},17z"
        elif self.venue and self.venue.name and self.venue.name.strip():
            venue_name = self.venue.name.replace(' ', '+')
            maps_link = f"https://www.google.com/maps/search/{venue_name}"
        else:
            maps_link = "https://www.google.com/maps"
        
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'image_url': image_url,
            'maps_link': maps_link,  # Add clickable Google Maps link
            'url': self.url,
            'is_selected': self.is_selected,
            'event_type': self.event_type,
            'start_location': self.start_location,
            'end_location': self.end_location,
            'venue_id': self.venue_id,
            'venue_name': self.venue.name if self.venue else None,
            'city_id': self.city_id,
            'start_latitude': self.start_latitude,
            'start_longitude': self.start_longitude,
            'end_latitude': self.end_latitude,
            'end_longitude': self.end_longitude,
            'tour_type': self.tour_type,
            'max_participants': self.max_participants,
            'price': self.price,
            'language': self.language,
            'exhibition_location': self.exhibition_location,
            'curator': self.curator,
            'admission_price': self.admission_price,
            'festival_type': self.festival_type,
            'multiple_locations': self.multiple_locations,
            'difficulty_level': self.difficulty_level,
            'equipment_needed': self.equipment_needed,
            'organizer': self.organizer,
            'source': self.source,
            'source_url': self.source_url,
            'social_media_platform': self.social_media_platform,
            'social_media_handle': self.social_media_handle,
            'social_media_page_name': self.social_media_page_name,
            'social_media_posted_by': self.social_media_posted_by,
            'social_media_url': self.social_media_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Source(db.Model):
    """Sources for events (Instagram accounts, websites, etc.)"""
    __tablename__ = 'sources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # "Princeton Photography Club"
    handle = db.Column(db.String(100), nullable=False)  # "@princetonphotoclub" or "princetonphotoclub.com"
    source_type = db.Column(db.String(50), nullable=False)  # 'instagram', 'website', 'eventbrite', 'facebook'
    url = db.Column(db.String(500))  # Full URL to the source
    description = db.Column(db.Text)  # Description of what this source posts
    
    # Coverage
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'))  # Primary city
    covers_multiple_cities = db.Column(db.Boolean, default=False)  # Does it cover multiple cities?
    covered_cities = db.Column(db.Text)  # JSON string of city IDs if covers multiple
    
    # Event types this source typically posts
    event_types = db.Column(db.Text)  # JSON string: ["photowalk", "tour", "exhibition"]
    
    # Status and tracking
    is_active = db.Column(db.Boolean, default=True)  # Is this source still active?
    last_checked = db.Column(db.DateTime)  # When did we last check this source?
    last_event_found = db.Column(db.DateTime)  # When did we last find an event from this source?
    events_found_count = db.Column(db.Integer, default=0)  # How many events have we found from this source?
    
    # Reliability metrics
    reliability_score = db.Column(db.Float, default=5.0)  # 1-10 scale
    posting_frequency = db.Column(db.String(50))  # 'daily', 'weekly', 'monthly', 'irregular'
    
    # Notes and patterns
    notes = db.Column(db.Text)  # Special instructions, patterns, etc.
    scraping_pattern = db.Column(db.Text)  # Any specific scraping patterns or rules
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    city = db.relationship('City', backref='sources')
    
    def to_dict(self):
        """Convert source to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'handle': self.handle,
            'source_type': self.source_type,
            'url': self.url,
            'description': self.description,
            'city_id': self.city_id,
            'city_name': self.city.name if self.city else None,
            'covers_multiple_cities': self.covers_multiple_cities,
            'covered_cities': self.covered_cities,
            'event_types': self._parse_event_types(),
            'is_active': self.is_active,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'last_event_found': self.last_event_found.isoformat() if self.last_event_found else None,
            'events_found_count': self.events_found_count,
            'reliability_score': self.reliability_score,
            'posting_frequency': self.posting_frequency,
            'notes': self.notes,
            'scraping_pattern': self.scraping_pattern,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def _parse_event_types(self):
        """Parse event_types field, handling both JSON and string formats"""
        if not self.event_types:
            return []
        
        try:
            # Try to parse as JSON first
            return json.loads(self.event_types)
        except (json.JSONDecodeError, TypeError):
            try:
                # If JSON fails, try to parse as Python literal (single quotes)
                import ast
                return ast.literal_eval(self.event_types)
            except (ValueError, SyntaxError):
                # If all else fails, treat as comma-separated string
                return [item.strip() for item in self.event_types.split(',') if item.strip()]
    
    def __repr__(self):
        return f"<Source {self.name} ({self.source_type})>"

# OAuth Helper Functions
def is_admin_email(email):
    """Check if email is in admin whitelist"""
    if not GOOGLE_OAUTH_AVAILABLE or not ADMIN_EMAILS:
        return True  # Allow access if OAuth not configured
    return email.strip().lower() in [admin.strip().lower() for admin in ADMIN_EMAILS if admin.strip()]

def login_required(f):
    """Decorator to require Google OAuth login for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For local development only, bypass OAuth if running on localhost
        is_local = (request.host.startswith('localhost') or 
                   request.host.startswith('127.0.0.1') or
                   request.host.startswith('10.'))
        
        if is_local:
            print("DEBUG: Local development detected, bypassing OAuth")
            return f(*args, **kwargs)
        
        if not GOOGLE_OAUTH_AVAILABLE:
            return f(*args, **kwargs)  # Allow access if OAuth not configured
        
        # Check if user is logged in (more strict validation)
        if ('user_email' not in session or 
            not session.get('user_email') or 
            'credentials' not in session):
            print("DEBUG: No valid session found, redirecting to login")
            return redirect('/auth/login')
        
        # Check if user is admin
        if not is_admin_email(session['user_email']):
            return render_template('unauthorized.html', 
                                 user_email=session['user_email'],
                                 admin_emails=ADMIN_EMAILS), 403
        
        print(f"DEBUG: Authenticated user: {session['user_email']}")
        return f(*args, **kwargs)
    return decorated_function

# Import and register generic CRUD endpoints after all models are defined
try:
    from scripts.generic_crud_generator import register_generic_crud_endpoints
    register_generic_crud_endpoints(app, db, City, Venue, Event)
except ImportError as e:
    print(f"Warning: Could not import generic CRUD generator: {e}")

# Import consolidated utilities
from scripts.utils import (
    DatabaseFields,
    DatabaseConfig,
    format_city_name,
    format_country_name,
    format_venue_name,
    check_city_duplicate,
    check_venue_duplicate,
    get_timezone_for_city,
    get_city_details_with_geopy,
    get_event_type_fields,
    validate_event_data,
    normalize_country,
    normalize_city,
    normalize_venue,
    normalize_country_with_nlp,
    _countries_are_same,
    cleanup_duplicate_cities
)

# Utility functions are now imported from scripts.utils

@app.route('/api/csrf-token')
def get_csrf_token():
    """Get CSRF token for frontend forms"""
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})

def create_error_response(message, status_code=500):
    """Create standardized error response"""
    return jsonify({'error': message}), status_code

@app.route('/test-events')
def test_events():
    """Test page for debugging events"""
    return render_template('test_events.html')

def update_json_with_new_venue(venue, city):
    """Update venues.json with a newly added venue"""
    import json
    import os
    from datetime import datetime
    
    # Check environment - skip JSON updates in production
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    if environment == 'production':
        print(f"🏭 Production mode: Skipping JSON update for venue '{venue.name}'")
        print(f"📝 Venue addition logged for later processing")
        # Log the addition for potential batch processing
        logger.info(f"Venue added in production: {venue.name} (ID: {venue.id}) in {city.name}")
        return
    
    # Development mode - proceed with JSON update
    print(f"🔧 Development mode: Updating venues.json for venue '{venue.name}'")
    
    # Define path to venues.json
    venues_json_path = os.path.join(os.path.dirname(__file__), 'data', 'venues.json')
    
    # Check if venues.json exists
    if not os.path.exists(venues_json_path):
        print(f"Warning: venues.json file not found at {venues_json_path}")
        return
    
    # Work with venues.json
    json_file_path = venues_json_path
    
    try:
        # Load existing JSON
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find the city in the JSON
        city_found = False
        for city_id, city_data in data['cities'].items():
            if city_data['name'] == city.name:
                city_found = True
                
                # Check if venue already exists
                existing_venue_names = [v['name'] for v in city_data['venues']]
                if venue.name in existing_venue_names:
                    print(f"Venue '{venue.name}' already exists in JSON for {city.name}")
                    return
                
                # Create venue entry for JSON
                venue_entry = {
                    "name": venue.name,
                    "venue_type": venue.venue_type or "Museum",
                    "address": venue.address or "",
                    "opening_hours": venue.opening_hours or "",
                    "phone_number": venue.phone_number or "",
                    "email": venue.email or "",
                    "description": venue.description or "",
                    "tour_info": venue.tour_info or "",
                    "admission_fee": venue.admission_fee or "",
                    "website_url": venue.website_url or "",
                    "latitude": venue.latitude,
                    "longitude": venue.longitude,
                    "additional_info": venue.additional_info or "{}",
                    "image_url": venue.image_url or "",
                    "facebook_url": venue.facebook_url or "",
                    "instagram_url": venue.instagram_url or "",
                    "twitter_url": venue.twitter_url or "",
                    "youtube_url": venue.youtube_url or "",
                    "tiktok_url": venue.tiktok_url or "",
                    "holiday_hours": venue.holiday_hours or ""
                }
                
                # Add venue to city
                city_data['venues'].append(venue_entry)
                
                # Update metadata
                data['metadata']['total_venues'] = data['metadata']['total_venues'] + 1
                data['metadata']['last_update'] = f"Added {venue.name} via admin interface"
                data['metadata']['last_venue_addition'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                break
        
        if not city_found:
            print(f"Warning: City '{city.name}' not found in JSON file")
            return
        
        # Save updated JSON
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully updated venues.json with venue '{venue.name}'")
        print(f"📁 Updated file: {venues_json_path}")
        
    except Exception as e:
        print(f"Error updating JSON file: {e}")
        raise

@app.route('/')
def index():
    """Main page with city selection and time filtering"""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    return '', 204  # No content response

@app.route('/api/cities')
def get_cities():
    """Get list of available cities"""
    cities = City.query.all()
    return jsonify([city.to_dict() for city in cities])

@app.route('/api/venue-types')
def get_venue_types():
    """Get all allowed venue types for form dropdowns"""
    from scripts.venue_types import get_allowed_venue_types
    venue_types = get_allowed_venue_types()
    return jsonify({
        'venue_types': [{'value': vtype.lower().replace(' ', '_'), 'text': vtype} for vtype in venue_types]
    })

@app.route('/api/stats')
def get_public_stats():
    """Get public statistics for the main page"""
    try:
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        sources_count = Source.query.count()
        events_count = Event.query.count()
        
        return jsonify({
            'cities': cities_count,
            'venues': venues_count,
            'sources': sources_count,
            'events': events_count
        })
    except Exception as e:
        print(f"Error getting public stats: {e}")
        return jsonify({
            'cities': 0,
            'venues': 0,
            'sources': 0,
            'events': 0
        }), 500

@app.route('/api/sources')
def get_sources():
    """Get sources for a specific city"""
    city_id = request.args.get('city_id')
    
    if not city_id:
        return jsonify({'error': 'City ID is required'}), 400
    
    try:
        # Load sources from JSON file
        import json
        with open('data/sources.json', 'r') as f:
            sources_data = json.load(f)
        
        sources = sources_data.get('sources', {})
        
        # Filter by city_id if provided
        filtered_sources = []
        for source_id, source in sources.items():
            if source.get('city_id') == int(city_id) or source.get('covers_multiple_cities', False):
                filtered_sources.append({
                    'id': source_id,
                    'name': source.get('name', ''),
                    'handle': source.get('handle', ''),
                    'source_type': source.get('source_type', ''),
                    'url': source.get('url', ''),
                    'description': source.get('description', ''),
                    'city_id': source.get('city_id'),
                    'event_types': source.get('event_types', '[]'),
                    'is_active': source.get('is_active', True)
                })
        
        return jsonify(filtered_sources)
        
    except Exception as e:
        app_logger.error(f"Error loading sources: {e}")
        return jsonify({'error': 'Failed to load sources'}), 500

@app.route('/api/events')
def get_events():
    """Get events for a specific city and time range"""
    city_id = request.args.get('city_id')
    time_range = request.args.get('time_range', 'today')
    event_type = request.args.get('event_type')
    
    if not city_id:
        return jsonify({'error': 'City ID is required'}), 400
    
    city = db.session.get(City, city_id)
    if not city:
        return jsonify({'error': 'City not found'}), 404
    
    # Calculate date range based on time_range
    now = datetime.now(pytz.timezone(city.timezone))
    
    if time_range == 'today':
        start_date = now.date()
        end_date = now.date()
    elif time_range == 'tomorrow':
        start_date = (now + timedelta(days=1)).date()
        end_date = (now + timedelta(days=1)).date()
    elif time_range == 'this_week':
        start_date = now.date()
        end_date = (now + timedelta(days=6)).date()  # 7 days total including today
    elif time_range == 'next_week':
        start_date = (now + timedelta(days=7)).date()
        end_date = (now + timedelta(days=13)).date()  # 7 days starting next week
    elif time_range == 'this_month':
        start_date = now.date()
        end_date = (now + timedelta(days=29)).date()  # 30 days total including today
    elif time_range == 'next_month':
        start_date = (now + timedelta(days=30)).date()
        end_date = (now + timedelta(days=59)).date()  # 30 days starting next month
    elif time_range == 'custom':
        # Handle custom date range from request parameters
        custom_start = request.args.get('custom_start_date')
        custom_end = request.args.get('custom_end_date')
        
        if not custom_start or not custom_end:
            return jsonify({'error': 'Custom start and end dates required for custom range'}), 400
        
        try:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid custom date format. Use YYYY-MM-DD'}), 400
    else:
        return jsonify({'error': 'Invalid time range'}), 400
    
    # Query events based on type
    events = []
    
    # Get venues for this city once (used by events)
    city_venues = Venue.query.filter_by(city_id=city_id).all()
    venue_ids = [v.id for v in city_venues]
    
    if not event_type or event_type == 'tour':
        tour_events = Event.query.filter(
            Event.event_type == 'tour',
            Event.venue_id.in_(venue_ids),
            Event.start_date >= start_date,
            Event.start_date <= end_date
        ).all()
        events.extend([event.to_dict() for event in tour_events])
    
    if not event_type or event_type == 'exhibition':
        if time_range == 'today':
            # For today, only show exhibitions that are currently running
            exhibition_events = Event.query.filter(
                Event.event_type == 'exhibition',
                Event.venue_id.in_(venue_ids),
                Event.start_date <= start_date,
                Event.end_date >= start_date
            ).all()
        else:
            # For other time ranges, show exhibitions that overlap with the range
            exhibition_events = Event.query.filter(
                Event.event_type == 'exhibition',
                Event.venue_id.in_(venue_ids),
                Event.start_date <= end_date,
                Event.end_date >= start_date
            ).all()
        events.extend([event.to_dict() for event in exhibition_events])
    
    if not event_type or event_type == 'festival':
        festival_events = Event.query.filter(
            Event.event_type == 'festival',
            Event.city_id == city_id,
            Event.start_date <= end_date,
            Event.end_date >= start_date
        ).all()
        events.extend([event.to_dict() for event in festival_events])
    
    if not event_type or event_type == 'photowalk':
        photowalk_events = Event.query.filter(
            Event.event_type == 'photowalk',
            Event.city_id == city_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date
        ).all()
        events.extend([event.to_dict() for event in photowalk_events])
    
    return jsonify(events)

@app.route('/api/venues')
def get_venues():
    """Get venues for a specific city and venue types"""
    city_id = request.args.get('city_id')
    venue_type = request.args.get('venue_type')
    venue_types = request.args.get('venue_types')
    
    if not city_id:
        return jsonify({'error': 'City ID is required'}), 400
    
    query = Venue.query.filter(Venue.city_id == city_id)
    
    # Filter out permanently closed venues
    closed_keywords = ['permanently closed', 'currently closed', 'no longer open', 'permanently shut down']
    for keyword in closed_keywords:
        query = query.filter(
            db.and_(
                ~Venue.opening_hours.ilike(f'%{keyword}%'),
                ~Venue.description.ilike(f'%{keyword}%')
            )
        )
    
    # Handle single venue type (backward compatibility, case-insensitive)
    if venue_type:
        query = query.filter(
            db.or_(
                Venue.venue_type == venue_type,
                Venue.venue_type == venue_type.lower(),
                Venue.venue_type == venue_type.capitalize(),
                Venue.venue_type == venue_type.title()
            )
        )
    
    # Handle multiple venue types (case-insensitive)
    if venue_types:
        venue_type_list = [vt.strip() for vt in venue_types.split(',') if vt.strip()]
        if venue_type_list:
            # Create case-insensitive filters for each venue type
            filters = []
            for venue_type in venue_type_list:
                # Check both exact match and case-insensitive match
                filters.append(
                    db.or_(
                        Venue.venue_type == venue_type,
                        Venue.venue_type == venue_type.lower(),
                        Venue.venue_type == venue_type.capitalize(),
                        Venue.venue_type == venue_type.title()
                    )
                )
            query = query.filter(db.or_(*filters))
    
    venues = query.all()
    return jsonify([venue.to_dict() for venue in venues])

@app.route('/api/image/<photo_reference>')
def get_venue_image(photo_reference):
    """Secure image proxy endpoint that adds API key server-side"""
    try:
        google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        if not google_maps_api_key:
            return jsonify({'error': 'Google Maps API key not configured'}), 500
        
        # Construct the Google Maps photo URL with API key
        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_reference}&key={google_maps_api_key}"
        
        # Fetch the image from Google Maps
        import requests
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Return the image with proper headers
        from flask import Response
        return Response(
            response.content,
            mimetype='image/jpeg',
            headers={
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'Content-Type': 'image/jpeg'
            }
        )
        
    except Exception as e:
        app_logger.error(f"Error fetching image for photo reference {photo_reference}: {e}")
        return jsonify({'error': 'Failed to fetch image'}), 500

@app.route('/api/scrape-progress')
def get_scraping_progress():
    """Get real-time scraping progress"""
    try:
        # Read the current scraping progress from a temporary file
        progress_file = 'scraping_progress.json'
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            return jsonify(progress_data)
        else:
            return jsonify({
                'status': 'not_started',
                'current_step': '',
                'progress': 0,
                'events_found': 0,
                'log_entries': []
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-database', methods=['POST'])
def clear_database():
    """Clear all data from database"""
    try:
        app_logger.info("Starting database clear...")
        
        # Clear in order to respect foreign key constraints
        Event.query.delete()
        Venue.query.delete()
        Source.query.delete()
        City.query.delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database cleared successfully!'
        })
        
    except Exception as e:
        app_logger.error(f"Database clear error: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/load-data', methods=['POST'])
def load_data():
    """Load data from JSON files into database"""
    try:
        import json
        import os
        
        app_logger.info("Starting data loading...")
        
        # Clear existing data first
        app_logger.info("Clearing existing data...")
        Event.query.delete()
        Venue.query.delete()
        Source.query.delete()
        City.query.delete()
        db.session.commit()
        app_logger.info("Existing data cleared")
        
        # Load cities
        cities_loaded = 0
        try:
            with open('data/cities.json', 'r') as f:
                cities_data = json.load(f)
            
            if "cities" in cities_data:
                cities_section = cities_data["cities"]
                for city_id, city_data in cities_section.items():
                    city = City(
                        name=city_data['name'],
                        state=city_data.get('state'),
                        country=city_data['country'],
                        timezone=city_data.get('timezone', 'America/New_York')
                    )
                    db.session.add(city)
                    cities_loaded += 1
            
            db.session.commit()
            app_logger.info(f"Loaded {cities_loaded} cities")
        except Exception as e:
            app_logger.error(f"Error loading cities: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to load cities: {str(e)}'
            }), 500
        
        # Load venues
        venues_loaded = 0
        try:
            app_logger.info("Starting venues loading...")
            with open('data/venues.json', 'r') as f:
                venues_data = json.load(f)
            
            app_logger.info(f"Venues JSON loaded, keys: {list(venues_data.keys())}")
            
            if "venues" in venues_data:
                venues_section = venues_data["venues"]
                app_logger.info(f"Found venues section with {len(venues_section)} cities")
                
                for city_id, city_data in venues_section.items():
                    if city_id == "metadata":
                        continue
                        
                    city_name = city_data.get('name', 'Unknown')
                    city_venues = city_data.get('venues', [])
                    
                    app_logger.info(f"Processing city: {city_name} with {len(city_venues)} venues")
                    
                    # Find the city
                    city = City.query.filter_by(name=city_name.split(',')[0].strip()).first()
                    if not city:
                        app_logger.warning(f"City not found: {city_name}")
                        continue
                    
                    for venue_data in city_venues:
                        try:
                            # Truncate fields to fit database limits
                            def truncate_field(value, max_length):
                                if value and len(str(value)) > max_length:
                                    return str(value)[:max_length]
                                return value
                            
                            venue = Venue(
                                name=truncate_field(venue_data['name'], 200),
                                venue_type=truncate_field(venue_data['venue_type'], 50),
                                address=venue_data.get('address'),  # TEXT field, no limit
                                latitude=venue_data.get('latitude'),
                                longitude=venue_data.get('longitude'),
                                image_url=truncate_field(venue_data.get('image_url'), 500),
                                instagram_url=truncate_field(venue_data.get('instagram_url'), 200),
                                facebook_url=truncate_field(venue_data.get('facebook_url'), 200),
                                twitter_url=truncate_field(venue_data.get('twitter_url'), 200),
                                youtube_url=truncate_field(venue_data.get('youtube_url'), 200),
                                tiktok_url=truncate_field(venue_data.get('tiktok_url'), 200),
                                website_url=truncate_field(venue_data.get('website_url'), 200),
                                description=venue_data.get('description'),  # TEXT field, no limit
                                opening_hours=venue_data.get('opening_hours'),  # TEXT field, no limit
                                holiday_hours=venue_data.get('holiday_hours'),  # TEXT field, no limit
                                phone_number=truncate_field(venue_data.get('phone_number'), 50),
                                email=truncate_field(venue_data.get('email'), 200),
                                tour_info=venue_data.get('tour_info'),  # TEXT field, no limit
                                admission_fee=venue_data.get('admission_fee'),  # TEXT field, no limit
                                additional_info=venue_data.get('additional_info'),  # TEXT field, no limit
                                city_id=city.id
                            )
                            db.session.add(venue)
                            venues_loaded += 1
                        except Exception as venue_error:
                            app_logger.error(f"Error creating venue {venue_data.get('name', 'Unknown')}: {venue_error}")
                            continue
            
            db.session.commit()
            app_logger.info(f"Loaded {venues_loaded} venues")
        except Exception as e:
            app_logger.error(f"Error loading venues: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to load venues: {str(e)}'
            }), 500
        
        # Load sources
        sources_loaded = 0
        try:
            app_logger.info("Starting sources loading...")
            with open('data/sources.json', 'r') as f:
                sources_data = json.load(f)
            
            app_logger.info(f"Sources JSON loaded, keys: {list(sources_data.keys())}")
            
            if "sources" in sources_data:
                sources_section = sources_data["sources"]
                app_logger.info(f"Found sources section with {len(sources_section)} sources")
                
                for source_id, source_data in sources_section.items():
                    try:
                        # Find the city by city_id
                        city_id = source_data.get('city_id')
                        if city_id:
                            # Try multiple lookup methods
                            city = City.query.get(city_id)
                            if not city:
                                # Try by name as fallback
                                city_name = source_data.get('city_name', 'Washington')
                                city = City.query.filter_by(name=city_name).first()
                                if not city:
                                    app_logger.warning(f"City not found for city_id: {city_id}, city_name: {city_name}")
                                    continue
                                else:
                                    app_logger.info(f"Found city by name: {city_name} (ID: {city.id})")
                            else:
                                app_logger.info(f"Found city by ID: {city_id} ({city.name})")
                        else:
                            app_logger.warning(f"No city_id for source: {source_data.get('name', 'Unknown')}")
                            continue
                        
                        # Handle list fields (convert to JSON string for database)
                        event_types = source_data.get('event_types', '')
                        if isinstance(event_types, list):
                            event_types = json.dumps(event_types)
                        
                        covered_cities = source_data.get('covered_cities', '')
                        if isinstance(covered_cities, list):
                            covered_cities = json.dumps(covered_cities)
                        
                        source = Source(
                            name=source_data['name'],
                            handle=source_data.get('handle', ''),
                            source_type=source_data['source_type'],
                            url=source_data.get('url'),
                            description=source_data.get('description'),
                            city_id=city.id,
                            covers_multiple_cities=source_data.get('covers_multiple_cities', False),
                            covered_cities=covered_cities,
                            event_types=event_types,
                            is_active=source_data.get('is_active', True),
                            last_checked=source_data.get('last_checked'),
                            last_event_found=source_data.get('last_event_found'),
                            events_found_count=source_data.get('events_found_count', 0),
                            reliability_score=source_data.get('reliability_score', 5.0),
                            posting_frequency=source_data.get('posting_frequency'),
                            notes=source_data.get('notes'),
                            scraping_pattern=source_data.get('scraping_pattern')
                        )
                        db.session.add(source)
                        sources_loaded += 1
                    except Exception as source_error:
                        app_logger.error(f"Error creating source {source_data.get('name', 'Unknown')}: {source_error}")
                        continue
            
            db.session.commit()
            app_logger.info(f"Loaded {sources_loaded} sources")
        except Exception as e:
            app_logger.error(f"Error loading sources: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to load sources: {str(e)}'
            }), 500
        
        # Get final counts
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        sources_count = Source.query.count()
        events_count = Event.query.count()
        
        return jsonify({
            'success': True,
            'message': f'Data loaded successfully! Cities: {cities_loaded}, Venues: {venues_loaded}, Sources: {sources_loaded}',
            'counts': {
                'cities': cities_count,
                'venues': venues_count,
                'sources': sources_count,
                'events': events_count
            }
        })
        
    except Exception as e:
        app_logger.error(f"Data loading error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scrape', methods=['POST'])
def trigger_scraping():
    """Trigger the scraping process to refresh event data"""
    try:
        import json
        from datetime import datetime
        from scripts.venue_event_scraper import VenueEventScraper
        from scripts.seed_dc_data import load_scraped_events
        
        # Get parameters from request
        data = request.get_json() or {}
        city_id = data.get('city_id')
        event_type = data.get('event_type', '')
        time_range = data.get('time_range', 'today')
        venue_ids = data.get('venue_ids', [])
        source_ids = data.get('source_ids', [])
        custom_start_date = data.get('custom_start_date')
        custom_end_date = data.get('custom_end_date')
        
        # Get city information
        if city_id:
            city = db.session.get(City, city_id)
            if not city:
                return jsonify({'error': 'City not found'}), 404
            city_name = city.name
        else:
            city_name = 'Washington DC'  # Default for now
        
        app_logger.info(f"Starting scraping for {city_name}, event_type: {event_type}, venues: {len(venue_ids)}, sources: {len(source_ids)}")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 10,
            'message': f'Starting scraping for {city_name}...',
            'timestamp': datetime.now().isoformat()
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Step 1: Run venue event scraper directly
        progress_data.update({
            'current_step': 2,
            'percentage': 30,
            'message': f'Scraping events from {len(venue_ids)} venues...'
        })
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        scraper = VenueEventScraper()
        events_scraped = scraper.scrape_venue_events(
            city_id=city_id,
            event_type=event_type,
            time_range=time_range,
            venue_ids=venue_ids
        )
        
        # Step 2: Load events into database
        progress_data.update({
            'current_step': 3,
            'percentage': 70,
            'message': 'Loading events into database...'
        })
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Load scraped events into database
        success = load_scraped_events()
        
        if not success:
            app_logger.error("Failed to load events into database")
            return jsonify({
                'error': 'Database loading failed'
            }), 500
        
        # Step 3: Complete
        progress_data.update({
            'current_step': 3,
            'percentage': 100,
            'message': f'Scraping complete! Found {events_scraped} events.'
        })
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        events_added = events_scraped
        
        app_logger.info(f"Scraping completed: {events_added} events added")
        
        return jsonify({
            'message': f'Scraping completed successfully for {city_name}',
            'events_added': events_added,
            'city': city_name,
            'event_type': event_type,
            'time_range': time_range,
            'venue_count': len(venue_ids),
            'scraper_output': scraper_result.stdout,
            'seed_output': seed_result.stdout
        })
        
    except Exception as e:
        app_logger.error(f"Scraping error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Scraping failed',
            'details': str(e)
        }), 500

# OAuth Routes
@app.route('/auth/login')
def auth_login():
    """Initiate Google OAuth login"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return redirect('/admin')  # Skip auth if not configured
    
    # For local development, redirect directly to admin
    is_local = (request.host.startswith('localhost') or 
               request.host.startswith('127.0.0.1') or
               request.host.startswith('10.'))
    
    if is_local:
        return redirect('/admin')
    
    try:
        # Create flow with proper configuration
        flow = Flow.from_client_config(CLIENT_CONFIG, SCOPES)
        
        # Use custom domain for OAuth callback to maintain consistent branding
        if 'railway.app' in request.host or 'ozayn.com' in request.host:
            flow.redirect_uri = 'https://planner.ozayn.com/auth/callback'
        else:
            flow.redirect_uri = request.url_root + 'auth/callback'
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        print(f"OAuth login error: {e}")
        return f"OAuth error: {e}", 500

@app.route('/auth/callback')
def auth_callback():
    """Handle Google OAuth callback"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return redirect('/admin')
    
    try:
        # Create flow without state validation to avoid CSRF issues on Railway
        flow = Flow.from_client_config(CLIENT_CONFIG, SCOPES)
        
        # Use custom domain for OAuth callback to maintain consistent branding
        if 'railway.app' in request.host or 'ozayn.com' in request.host:
            flow.redirect_uri = 'https://planner.ozayn.com/auth/callback'
        else:
            flow.redirect_uri = request.url_root + 'auth/callback'
        
        # Handle Railway proxy HTTPS issue
        authorization_response = request.url
        if 'railway.app' in request.host or 'ozayn.com' in request.host:
            authorization_response = authorization_response.replace('http://', 'https://')
        
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        email = user_info.get('email')
        name = user_info.get('name')
        
        if not is_admin_email(email):
            return f"Access denied for {email}. Contact administrator.", 403
        
        # Store user info in session
        session['user_email'] = email
        session['user_name'] = name
        session['credentials'] = credentials.to_json()
        
        return redirect('/admin')
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return f"OAuth callback error: {e}", 500

@app.route('/auth/logout')
def auth_logout():
    """Logout user"""
    # Clear all session data
    session.clear()
    
    # For production environments, also clear any OAuth-specific session data
    if 'credentials' in session:
        del session['credentials']
    if 'user_email' in session:
        del session['user_email']
    if 'user_name' in session:
        del session['user_name']
    if 'state' in session:
        del session['state']
    
    # Force session to be saved
    session.permanent = False
    
    # Redirect to custom domain instead of Railway domain
    if 'railway.app' in request.host:
        redirect_url = 'https://planner.ozayn.com/'
    else:
        redirect_url = '/'
    
    # Create response with cache control headers to prevent caching
    response = redirect(redirect_url)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/admin')
@login_required
def admin():
    """Admin interface"""
    return render_template('admin.html', session=session)


@app.route('/test-admin')
def test_admin():
    """Test admin page"""
    return render_template('test_admin.html')

@app.route('/admin-simple')
def admin_simple():
    """Simple admin page"""
    return render_template('admin_simple.html')

@app.route('/admin-status')
def admin_status():
    """Simple admin status page"""
    try:
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        sources_count = Source.query.count()
        events_count = Event.query.count()
        
        return f"""
        <h1>Database Status</h1>
        <p>Cities: {cities_count}</p>
        <p>Venues: {venues_count}</p>
        <p>Sources: {sources_count}</p>
        <p>Events: {events_count}</p>
        <br>
        <button onclick="clearDatabase()">Clear Database</button>
        <button onclick="loadData()">Load Data</button>
        <script>
        function clearDatabase() {{
            fetch('/api/clear-database', {{method: 'POST'}})
                .then(r => r.json())
                .then(data => {{
                    alert(data.message);
                    location.reload();
                }});
        }}
        function loadData() {{
            fetch('/api/load-data', {{method: 'POST'}})
                .then(r => r.json())
                .then(data => {{
                    alert(data.message);
                    location.reload();
                }});
        }}
        </script>
        """
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/admin-test')
def admin_test():
    """Test admin page"""
    return render_template('admin_test.html')

@app.route('/api/test-files')
def test_files():
    """Test if JSON files are accessible on Railway"""
    try:
        import os
        import json
        
        result = {
            'data_dir_exists': os.path.exists('data'),
            'data_dir_contents': [],
            'cities_file_exists': False,
            'venues_file_exists': False,
            'sources_file_exists': False,
            'cities_file_size': 0,
            'venues_file_size': 0,
            'sources_file_size': 0,
            'cities_json_valid': False,
            'venues_json_valid': False,
            'sources_json_valid': False
        }
        
        if os.path.exists('data'):
            result['data_dir_contents'] = os.listdir('data')
            
            # Check cities.json
            cities_path = 'data/cities.json'
            if os.path.exists(cities_path):
                result['cities_file_exists'] = True
                result['cities_file_size'] = os.path.getsize(cities_path)
                try:
                    with open(cities_path, 'r') as f:
                        json.load(f)
                    result['cities_json_valid'] = True
                except:
                    pass
            
            # Check venues.json
            venues_path = 'data/venues.json'
            if os.path.exists(venues_path):
                result['venues_file_exists'] = True
                result['venues_file_size'] = os.path.getsize(venues_path)
                try:
                    with open(venues_path, 'r') as f:
                        json.load(f)
                    result['venues_json_valid'] = True
                except:
                    pass
            
            # Check sources.json
            sources_path = 'data/sources.json'
            if os.path.exists(sources_path):
                result['sources_file_exists'] = True
                result['sources_file_size'] = os.path.getsize(sources_path)
                try:
                    with open(sources_path, 'r') as f:
                        json.load(f)
                    result['sources_json_valid'] = True
                except:
                    pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug-cities')
def debug_cities():
    """Debug city data on Railway"""
    try:
        cities = City.query.all()
        city_data = []
        for city in cities:
            city_data.append({
                'id': city.id,
                'name': city.name,
                'state': city.state,
                'country': city.country
            })
        
        return jsonify({
            'cities_count': len(city_data),
            'cities': city_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug-oauth')
def debug_oauth():
    """Debug OAuth configuration"""
    try:
        return jsonify({
            'oauth_available': GOOGLE_OAUTH_AVAILABLE,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret_set': bool(GOOGLE_CLIENT_SECRET),
            'admin_emails': ADMIN_EMAILS,
            'current_host': request.host,
            'current_url': request.url,
            'callback_url': 'https://planner.ozayn.com/auth/callback' if 'railway.app' in request.host or 'ozayn.com' in request.host else request.url_root + 'auth/callback'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-oauth')
def test_oauth():
    """Test OAuth flow manually"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return "OAuth not available"
    
    try:
        # Create flow
        flow = Flow.from_client_config(CLIENT_CONFIG, SCOPES)
        flow.redirect_uri = 'https://planner.ozayn.com/auth/callback'
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return f"""
        <h1>OAuth Test</h1>
        <p><strong>Authorization URL:</strong></p>
        <p><a href="{authorization_url}" target="_blank">{authorization_url}</a></p>
        <p><strong>State:</strong> {state}</p>
        <p><strong>Callback URL:</strong> https://planner.ozayn.com/auth/callback</p>
        <p><strong>Client ID:</strong> {GOOGLE_CLIENT_ID}</p>
        """
        
    except Exception as e:
        return f"OAuth Test Error: {e}"

@app.route('/api/admin/stats')
def admin_stats():
    """Get admin statistics"""
    try:
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        events_count = Event.query.count()
        sources_count = Source.query.count()
        
        return jsonify({
            'cities': cities_count,
            'venues': venues_count,
            'events': events_count,
            'sources': sources_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cities')
def admin_cities():
    """Get all cities for admin"""
    try:
        cities = City.query.all()
        cities_data = []
        
        for city in cities:
            # Count venues and events for this city
            venue_count = Venue.query.filter_by(city_id=city.id).count()
            event_count = Event.query.filter_by(city_id=city.id).count()
            
            city_dict = city.to_dict()
            city_dict.update({
                'venue_count': venue_count,
                'event_count': event_count
            })
            cities_data.append(city_dict)
        
        return jsonify(cities_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/venues')
def admin_venues():
    """Get all venues for admin"""
    try:
        venues = Venue.query.all()
        venues_data = []
        
        for venue in venues:
            venue_dict = venue.to_dict()
            if venue.city:
                # Use full display name with state if available
                if venue.city.state:
                    venue_dict['city_name'] = f"{venue.city.name}, {venue.city.state}, {venue.city.country}"
                else:
                    venue_dict['city_name'] = f"{venue.city.name}, {venue.city.country}"
            else:
                venue_dict['city_name'] = 'Unknown'
            venues_data.append(venue_dict)
        
        return jsonify(venues_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events')
def admin_events():
    """Get all events for admin"""
    try:
        events = Event.query.all()
        events_data = []
        
        for event in events:
            event_dict = event.to_dict()
            event_dict.update({
                'venue_name': event.venue.name if event.venue else None,
                'city_name': event.city.name if event.city else 'Unknown',
                'city_timezone': event.city.timezone if event.city else 'UTC'
            })
            events_data.append(event_dict)
        
        return jsonify(events_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/lookup-city', methods=['POST'])
def lookup_city():
    """Lookup city information with geocoding"""
    try:
        data = request.get_json()
        city_name = data.get('city_name', '').strip()
        country = data.get('country', '').strip()
        
        if not city_name or not country:
            return jsonify({'error': 'City name and country are required'}), 400
        
        # Format the names
        formatted_name = format_city_name(city_name)
        formatted_country = format_country_name(country, city_name)  # Pass city name as context
        
        # Check if city already exists in database
        existing_city = City.query.filter_by(
            name=formatted_name,
            country=formatted_country
        ).first()
        
        if existing_city:
            return jsonify({'success': True, 'city': existing_city.to_dict()})
        
        # Use the exact same comprehensive geocoding function as add-city
        try:
            city_details = get_city_details_with_geopy(formatted_name, formatted_country)
            
            if city_details:
                # Get timezone using the same function
                timezone = get_timezone_for_city(
                    formatted_name, 
                    formatted_country, 
                    city_details.get('state')
                )
                
                return jsonify({
                    'success': True,
                    'city': {
                        'name': formatted_name,
                        'country': formatted_country,
                        'state': city_details.get('state'),
                        'timezone': timezone,
                        'latitude': city_details.get('latitude'),
                        'longitude': city_details.get('longitude'),
                        'full_address': city_details.get('full_address')
                    }
                })
            else:
                # Fallback - use the same logic as add-city
                timezone = get_timezone_for_city(formatted_name, formatted_country)
                
                return jsonify({
                    'success': True,
                    'city': {
                        'name': formatted_name,
                        'country': formatted_country,
                        'state': None,
                        'timezone': timezone
                    }
                })
                
        except Exception as geocoding_error:
            # Fallback to basic timezone lookup - same as add-city
            timezone = get_timezone_for_city(formatted_name, formatted_country)
            
            return jsonify({
                'success': True,
                'city': {
                    'name': formatted_name,
                    'country': formatted_country,
                    'state': None,
                    'timezone': timezone
                }
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cities/<int:city_id>', methods=['PUT'])
def update_city(city_id):
    """Update an existing city"""
    try:
        city = City.query.get_or_404(city_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        if 'name' not in data or not data['name'].strip():
            return jsonify({'error': 'City name is required'}), 400
        
        if 'country' not in data or not data['country'].strip():
            return jsonify({'error': 'Country is required'}), 400
        
        # Validate field lengths
        if len(data['name'].strip()) > 100:
            return jsonify({'error': 'City name must be 100 characters or less'}), 400
        
        if len(data['country'].strip()) > 100:
            return jsonify({'error': 'Country name must be 100 characters or less'}), 400
        
        if data.get('state') and len(data['state'].strip()) > 50:
            return jsonify({'error': 'State name must be 50 characters or less'}), 400
        
        # Clean and format the data
        new_name = format_city_name(data['name'])
        new_country = format_country_name(data['country'], data['name'])
        new_state = format_city_name(data.get('state', '')) if data.get('state') else None
        
        # Check for duplicates (excluding current city)
        existing_city = City.query.filter(
            City.name == new_name,
            City.country == new_country,
            City.state == new_state,
            City.id != city_id
        ).first()
        
        if existing_city:
            return jsonify({'error': f'City "{new_name}, {new_country}" already exists'}), 400
        
        # Update city fields
        city.name = new_name
        city.country = new_country
        city.state = new_state
        
        # Update timezone if provided
        if 'timezone' in data:
            timezone = data['timezone'].strip()
            if timezone:
                # Validate timezone format
                try:
                    import pytz
                    pytz.timezone(timezone)  # This will raise an exception if invalid
                    city.timezone = timezone
                except pytz.exceptions.UnknownTimeZoneError:
                    return jsonify({'error': f'Invalid timezone: {timezone}'}), 400
        
        city.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update cities.json
        try:
            from scripts.update_cities_json import update_cities_json
            update_cities_json()
        except Exception as cities_json_error:
            print(f"⚠️ Warning: Could not update cities.json: {cities_json_error}")
        
        return jsonify({
            'success': True,
            'message': f'City "{city.name}" updated successfully',
            'city': city.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating city: {e}")
        return jsonify({'error': str(e)}), 500

@csrf.exempt
@app.route('/api/admin/sync-cities', methods=['POST'])
def manual_sync_cities():
    """Manually sync cities from database to predefined_cities.json"""
    try:
        success = sync_cities_to_predefined_json()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Cities synced to predefined_cities.json successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to sync cities'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@csrf.exempt
@app.route('/api/admin/cities/<int:city_id>', methods=['DELETE'])
def delete_city(city_id):
    """Delete a city and handle related data"""
    try:
        city = City.query.get_or_404(city_id)
        city_name = city.name
        
        # Check if city has venues or events
        venues_count = Venue.query.filter_by(city_id=city_id).count()
        events_count = Event.query.filter_by(city_id=city_id).count()
        
        if venues_count > 0 or events_count > 0:
            return jsonify({
                'error': f'Cannot delete city "{city_name}" because it has {venues_count} venues and {events_count} events. Please delete or reassign them first.'
            }), 400
        
        # Delete the city
        db.session.delete(city)
        db.session.commit()
        
        # Update cities.json
        try:
            from scripts.update_cities_json import update_cities_json
            update_cities_json()
        except Exception as cities_json_error:
            print(f"⚠️ Warning: Could not update cities.json: {cities_json_error}")
        
        return jsonify({
            'success': True,
            'message': f'City "{city_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting city: {e}")
        return jsonify({'error': f'Failed to delete city: {str(e)}'}), 500

@app.route('/api/admin/discover-venues', methods=['POST'])
def discover_venues():
    """Discover venues for a city using predefined database (no AI quota used)"""
    try:
        api_logger.info("Starting venue discovery process")
        data = request.get_json()
        city_id = data.get('city_id')
        
        api_logger.debug(f"Discovery request data: {data}")
        
        if not city_id:
            api_logger.warning("City ID missing from discovery request")
            return jsonify({'error': 'City ID is required'}), 400
        
        # Get the city
        city = db.session.get(City, city_id)
        if not city:
            api_logger.error(f"City not found for city_id: {city_id}")
            return jsonify({'error': 'City not found'}), 404
        
        api_logger.info(f"Discovering venues for city: {city.name}, {city.country}")
        
        # Use predefined venue discovery instead of AI
        from scripts.discover_venues_predefined import discover_venues_for_city
        
        # Run the predefined venue discovery
        api_logger.info(f"Running predefined venue discovery with max_venues: {DEFAULT_MAX_VENUES}")
        result = discover_venues_for_city(city_id, DEFAULT_MAX_VENUES)
        
        api_logger.debug(f"Discovery result: {result}")
        
        if not result.get('success'):
            api_logger.error(f"Predefined venue discovery failed: {result.get('error')}")
            return jsonify({
                'error': 'Venue discovery failed',
                'details': result.get('error')
            }), 500
        
        # Get all venues for this city
        venues = Venue.query.filter_by(city_id=city_id).all()
        venues_data = [venue.to_dict() for venue in venues]
        
        api_logger.info(f"Found {len(venues_data)} venues for {city.name}")
        api_logger.info(f"Venues added: {result.get('venues_added', 0)}")
        
        return jsonify({
            'success': True,
            'message': f'Venue discovery completed for {city.name}',
            'venues': venues_data,
            'venues_found': len(venues_data),
            'venues_added': result.get('venues_added', 0),
            'method': 'predefined_database'
        })
        
    except Exception as e:
        api_logger.error(f"Error in venue discovery: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-event', methods=['POST'])
def add_event():
    """Add a new event"""
    try:
        data = request.get_json()
        
        # Get required fields
        title = data.get('title', '').strip()
        event_type = data.get('event_type', '').strip()
        start_date = data.get('start_date')
        
        if not title or not event_type or not start_date:
            return jsonify({'error': 'Title, event type, and start date are required'}), 400
        
        # Parse dates
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = None
            if data.get('end_date'):
                end_date_obj = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        
        # Parse times
        start_time_obj = None
        end_time_obj = None
        if data.get('start_time'):
            try:
                start_time_obj = datetime.strptime(data['start_time'], '%H:%M').time()
            except ValueError:
                pass
        if data.get('end_time'):
            try:
                end_time_obj = datetime.strptime(data['end_time'], '%H:%M').time()
            except ValueError:
                pass
        
        # Check for duplicate events
        from scripts.utils import check_event_duplicate
        duplicate_event, duplicate_type = check_event_duplicate(
            title, start_date_obj, 
            venue_id=data.get('venue_id'), 
            city_id=data.get('city_id')
        )
        if duplicate_event:
            if duplicate_type in ["exact_venue", "exact_city", "exact_no_location"]:
                return jsonify({'error': f'Event "{title}" already exists on {start_date} (ID: {duplicate_event.id})'}), 400
            else:
                return jsonify({'error': f'Similar event already exists on {start_date}: "{duplicate_event.title}" (ID: {duplicate_event.id})'}), 400
        
        # Create event with all unified fields
        event = Event(
            title=title,
            event_type=event_type,
            description=data.get('description', '').strip(),
            start_date=start_date_obj,
            end_date=end_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj,
            image_url=data.get('image_url', '').strip(),
            url=data.get('url', '').strip(),
            
            # Location fields
            start_location=data.get('start_location', '').strip(),
            end_location=data.get('end_location', '').strip(),
            venue_id=data.get('venue_id'),
            city_id=data.get('city_id'),
            
            # Geographic coordinates
            start_latitude=data.get('start_latitude'),
            start_longitude=data.get('start_longitude'),
            end_latitude=data.get('end_latitude'),
            end_longitude=data.get('end_longitude'),
            
            # Tour-specific fields
            tour_type=data.get('tour_type', '').strip(),
            max_participants=data.get('max_participants'),
            price=data.get('price'),
            language=data.get('language', 'English'),
            
            # Exhibition-specific fields
            exhibition_location=data.get('exhibition_location', '').strip(),
            curator=data.get('curator', '').strip(),
            admission_price=data.get('admission_price'),
            
            # Festival-specific fields
            festival_type=data.get('festival_type', '').strip(),
            multiple_locations=data.get('multiple_locations', False),
            
            # Photowalk-specific fields
            difficulty_level=data.get('difficulty_level', '').strip(),
            equipment_needed=data.get('equipment_needed', '').strip(),
            organizer=data.get('organizer', '').strip()
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Update events.json
        try:
            from scripts.update_events_json import update_events_json
            update_events_json()
        except Exception as events_json_error:
            print(f"⚠️ Warning: Could not update events.json: {events_json_error}")
        
        return jsonify({
            'success': True,
            'message': f'Event "{title}" added successfully',
            'event_id': event.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/smart-search-venue', methods=['POST'])
def smart_search_venue():
    """Use AI to search for venue details and populate form"""
    try:
        data = request.get_json()
        venue_name = data.get('venue_name', '').strip()
        city_name = data.get('city_name', '').strip()
        city_id = data.get('city_id')
        
        if not venue_name or not city_name or not city_id:
            return jsonify({'error': 'Venue name, city name, and city ID are required'}), 400
        
        # Check if city exists
        city = db.session.get(City, city_id)
        if not city:
            return jsonify({'error': 'City not found'}), 404
        
        # Use the existing LLM venue detail searcher
        from scripts.fetch_venue_details import LLMVenueDetailSearcher
        
        # Construct full location string with country
        location = city_name
        if city.state:
            location += f", {city.state}"
        if city.country:
            location += f", {city.country}"
        
        searcher = LLMVenueDetailSearcher(silent=True)
        venue_details = searcher.search_venue_details(
            venue_name=venue_name,
            city=location,
            silent=True
        )
        
        if not venue_details or not venue_details.get('name'):
            return jsonify({'error': 'Could not find venue details'}), 404
        
        # Get Google Maps image for the venue
        from scripts.utils import get_google_maps_image
        google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        image_url = None
        if google_maps_api_key:
            try:
                image_url = get_google_maps_image(
                    venue_name=venue_details['name'],
                    city=city_name,
                    api_key=google_maps_api_key
                )
            except Exception as e:
                print(f"Warning: Could not fetch Google Maps image: {e}")
        
        # Validate and normalize venue_type to match our dropdown options
        llm_venue_type = venue_details.get('venue_type', 'Museum')
        from scripts.venue_types import get_allowed_venue_types
        allowed_venue_types = get_allowed_venue_types()
        
        # Normalize venue type - check for exact match first
        if llm_venue_type in allowed_venue_types:
            validated_venue_type = llm_venue_type
        else:
            # Try case-insensitive match
            llm_lower = llm_venue_type.lower()
            for allowed_type in allowed_venue_types:
                if llm_lower == allowed_type.lower():
                    validated_venue_type = allowed_type
                    break
            else:
                # If no match found, use 'other' as fallback
                validated_venue_type = 'other'
                print(f"Warning: LLM returned unknown venue_type '{llm_venue_type}', using 'other'")

        # Prepare the response with venue details
        response_data = {
            'success': True,
            'venue_details': {
                'name': venue_details.get('name', venue_name),
                'venue_type': validated_venue_type,
                'address': venue_details.get('address', ''),
                'opening_hours': venue_details.get('opening_hours', ''),
                'admission_fee': venue_details.get('admission_fee', ''),
                'website_url': venue_details.get('website_url', ''),
                'phone_number': venue_details.get('phone_number', ''),
                'email': venue_details.get('email', ''),
                'description': venue_details.get('description', ''),
                'image_url': image_url,
                'latitude': venue_details.get('latitude'),
                'longitude': venue_details.get('longitude'),
                'facebook_url': venue_details.get('facebook_url', ''),
                'instagram_url': venue_details.get('instagram_url', ''),
                'twitter_url': venue_details.get('twitter_url', '')
            },
            'city_id': city_id,
            'city_name': city_name
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        api_logger.error(f"Error in smart venue search: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/create-json-copy', methods=['POST'])
def create_json_copy():
    """Create a fresh copy of predefined_venues.json for safe editing"""
    try:
        import shutil
        from datetime import datetime
        
        # Define paths
        original_path = os.path.join(os.path.dirname(__file__), 'data', 'predefined_venues.json')
        venues_path = os.path.join(os.path.dirname(__file__), 'data', 'venues.json')
        
        if not os.path.exists(original_path):
            return jsonify({'error': 'Original predefined_venues.json not found'}), 404
        
        # Create venues.json
        shutil.copy2(original_path, venues_path)
        
        return jsonify({
            'success': True,
            'message': f'✅ Created fresh venues.json from predefined_venues.json\n📁 Working file: {venues_path}\n📁 Original: {original_path}\n\nYou can now safely add venues without affecting the original file.',
            'original_path': original_path,
            'venues_path': venues_path
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/apply-json-copy', methods=['POST'])
def apply_json_copy():
    """Apply changes from copy back to original predefined_venues.json"""
    try:
        import shutil
        from datetime import datetime
        
        # Define paths
        original_path = os.path.join(os.path.dirname(__file__), 'data', 'predefined_venues.json')
        venues_path = os.path.join(os.path.dirname(__file__), 'data', 'venues.json')
        
        if not os.path.exists(venues_path):
            return jsonify({'error': 'venues.json not found. Create a copy first.'}), 404
        
        # Create backup of original
        backup_path = f"{original_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(original_path, backup_path)
        
        # Apply venues.json to original
        shutil.copy2(venues_path, original_path)
        
        return jsonify({
            'success': True,
            'message': f'✅ Applied venues.json changes to original file\n📁 Original: {original_path}\n📁 Backup: {backup_path}\n📁 Working file: {venues_path}\n\nThe original file has been updated with your changes.',
            'original_path': original_path,
            'backup_path': backup_path,
            'venues_path': venues_path
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export-cities', methods=['POST'])
def export_cities_to_json():
    """Export all cities from database to JSON file (matches cities.json format)"""
    try:
        import json
        import os
        from datetime import datetime
        
        print("🔄 Starting cities export from database...")
        
        # Get all cities
        cities = City.query.order_by(City.id).all()
        
        # Create the JSON structure (matches cities.json format)
        export_data = {
            "metadata": {
                "version": "1.0",
                "created": datetime.now().strftime("%Y-%m-%d"),
                "description": "Cities exported from database - always most updated version",
                "total_cities": len(cities),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "export_source": "database",
                "environment": os.getenv('ENVIRONMENT', 'development')
            },
            "cities": {}
        }
        
        # Add cities to export data
        for city in cities:
            export_data["cities"][str(city.id)] = {
                "name": city.name,
                "state": city.state or "",
                "country": city.country,
                "timezone": city.timezone or "UTC"
            }
        
        # Save to file
        export_path = os.path.join(os.path.dirname(__file__), 'data', 'exports', 'cities_exported.json')
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully exported {len(cities)} cities to {export_path}")
        
        # Return the file as a download
        from flask import send_file
        return send_file(
            export_path,
            as_attachment=True,
            download_name=f'cities_exported_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            mimetype='application/json'
        )
        
    except Exception as e:
        print(f"❌ Error exporting cities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export-sources', methods=['POST'])
def export_sources_to_json():
    """Export all sources from database to JSON file (matches sources.json format)"""
    try:
        import json
        import os
        from datetime import datetime
        
        print("🔄 Starting sources export from database...")
        
        # Get all sources with their cities
        sources = Source.query.all()
        cities = City.query.all()
        
        # Create the JSON structure (matches sources.json format)
        export_data = {}
        
        # Group sources by city
        for city in cities:
            city_sources = [s for s in sources if s.city_id == city.id]
            
            if city_sources:  # Only add cities that have sources
                export_data[str(city.id)] = {
                    "name": city.name,
                    "sources": []
                }
                
                # Add sources for this city
                for source in city_sources:
                    # Parse JSON fields back to lists
                    event_types = []
                    if source.event_types:
                        try:
                            event_types = json.loads(source.event_types)
                        except:
                            event_types = []
                    
                    covered_cities = []
                    if source.covered_cities:
                        try:
                            covered_cities = json.loads(source.covered_cities)
                        except:
                            covered_cities = []
                    
                    source_entry = {
                        "name": source.name,
                        "handle": source.handle or "",
                        "source_type": source.source_type or "website",
                        "url": source.url or "",
                        "description": source.description or "",
                        "city_id": source.city_id,
                        "covers_multiple_cities": source.covers_multiple_cities or False,
                        "covered_cities": covered_cities,
                        "event_types": event_types,
                        "is_active": source.is_active,
                        "last_checked": source.last_checked.isoformat() if source.last_checked else None,
                        "last_event_found": source.last_event_found.isoformat() if source.last_event_found else None,
                        "events_found_count": source.events_found_count or 0,
                        "reliability_score": float(source.reliability_score) if source.reliability_score else 0.0,
                        "posting_frequency": source.posting_frequency or "",
                        "notes": source.notes or "",
                        "scraping_pattern": source.scraping_pattern or ""
                    }
                    export_data[str(city.id)]["sources"].append(source_entry)
        
        # Save to file
        export_path = os.path.join(os.path.dirname(__file__), 'data', 'exports', 'sources_exported.json')
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully exported {len(sources)} sources to {export_path}")
        
        # Return the file as a download
        from flask import send_file
        return send_file(
            export_path,
            as_attachment=True,
            download_name=f'sources_exported_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            mimetype='application/json'
        )
        
    except Exception as e:
        print(f"❌ Error exporting sources: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export-venues', methods=['POST'])
def export_venues_to_json():
    """Export all venues from database to JSON file (matches venues.json format)"""
    try:
        import json
        import os
        from datetime import datetime
        
        print("🔄 Starting venues export from database...")
        
        # Get all venues with their cities
        venues = Venue.query.all()
        cities = City.query.all()
        
        # Create the JSON structure (matches venues.json format)
        export_data = {}
        
        # Group venues by city
        for city in cities:
            city_venues = [v for v in venues if v.city_id == city.id]
            
            if city_venues:  # Only add cities that have venues
                export_data[str(city.id)] = {
                    "name": city.name,
                    "venues": []
                }
                
                # Add venues for this city
                for venue in city_venues:
                    venue_entry = {
                        "name": venue.name,
                        "venue_type": venue.venue_type or "museum",
                        "address": venue.address or "",
                        "opening_hours": venue.opening_hours or "",
                        "holiday_hours": venue.holiday_hours or "",
                        "phone_number": venue.phone_number or "",
                        "email": venue.email or "",
                        "description": venue.description or "",
                        "tour_info": venue.tour_info or "",
                        "admission_fee": venue.admission_fee or "",
                        "website_url": venue.website_url or "",
                        "latitude": venue.latitude,
                        "longitude": venue.longitude,
                        "image_url": venue.image_url or "",
                        "instagram_url": venue.instagram_url or "",
                        "facebook_url": venue.facebook_url or "",
                        "twitter_url": venue.twitter_url or "",
                        "youtube_url": venue.youtube_url or "",
                        "tiktok_url": venue.tiktok_url or "",
                        "additional_info": venue.additional_info or ""
                    }
                    export_data[str(city.id)]["venues"].append(venue_entry)
        
        # Save to file
        export_path = os.path.join(os.path.dirname(__file__), 'data', 'exports', 'venues_exported.json')
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully exported {len(venues)} venues to {export_path}")
        
        # Return the file as a download
        from flask import send_file
        return send_file(
            export_path,
            as_attachment=True,
            download_name=f'venues_exported_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
            mimetype='application/json'
        )
        
    except Exception as e:
        print(f"❌ Error exporting venues: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/add-venue', methods=['POST'])
def add_venue():
    """Add a new venue"""
    try:
        data = request.get_json()
        
        # Get required fields
        name = data.get('name', '').strip()
        venue_type = data.get('venue_type', '').strip()
        city_id = data.get('city_id')
        
        if not name or not venue_type or not city_id:
            return jsonify({'error': 'Name, venue type, and city are required'}), 400
        
        # Check if city exists
        city = db.session.get(City, city_id)
        if not city:
            return jsonify({'error': 'City not found'}), 404
        
        # Check for duplicate venues in the same city
        from scripts.utils import check_venue_duplicate
        duplicate_venue, duplicate_type = check_venue_duplicate(name, city_id)
        if duplicate_venue:
            if duplicate_type == "exact":
                return jsonify({'error': f'Venue "{name}" already exists in {city.name} (ID: {duplicate_venue.id})'}), 400
            else:
                return jsonify({'error': f'Similar venue already exists in {city.name}: "{duplicate_venue.name}" (ID: {duplicate_venue.id})'}), 400
        
        # Create venue
        venue = Venue(
            name=name,
            venue_type=venue_type,
            address=data.get('address', '').strip(),
            website_url=data.get('website_url', '').strip(),
            description=data.get('description', '').strip(),
            city_id=city_id
        )
        
        db.session.add(venue)
        db.session.commit()
        
        # Automatically enhance venue with LLM and Google Maps data
        enhancement_results = {
            'llm_enhanced': False,
            'google_maps_image': False,
            'enhancement_errors': []
        }
        
        try:
            print(f"🤖 Automatically enhancing venue: {venue.name}")
            
            # Step 1: LLM Enhancement
            try:
                from scripts.utils import query_llm_for_venue_details
                from scripts.fetch_venue_details import LLMVenueDetailSearcher
                
                print(f"🔍 Running LLM enhancement for {venue.name}...")
                searcher = LLMVenueDetailSearcher(silent=True)
                llm_details = searcher.search_venue_details(venue.name, f"{city.name}, {city.country}")
                
                if llm_details:
                    # Update venue with LLM data
                    venue.description = llm_details.get('description', venue.description)
                    venue.address = llm_details.get('address', venue.address)
                    venue.website_url = llm_details.get('website_url', venue.website_url)
                    venue.phone_number = llm_details.get('phone_number', venue.phone_number)
                    venue.email = llm_details.get('email', venue.email)
                    venue.opening_hours = llm_details.get('opening_hours', venue.opening_hours)
                    venue.holiday_hours = llm_details.get('holiday_hours', venue.holiday_hours)
                    venue.admission_fee = llm_details.get('admission_fee', venue.admission_fee)
                    venue.tour_info = llm_details.get('tour_info', venue.tour_info)
                    venue.instagram_url = llm_details.get('instagram_url', venue.instagram_url)
                    venue.facebook_url = llm_details.get('facebook_url', venue.facebook_url)
                    venue.twitter_url = llm_details.get('twitter_url', venue.twitter_url)
                    venue.youtube_url = llm_details.get('youtube_url', venue.youtube_url)
                    venue.tiktok_url = llm_details.get('tiktok_url', venue.tiktok_url)
                    
                    # Handle coordinates
                    if llm_details.get('latitude'):
                        try:
                            venue.latitude = float(llm_details['latitude'])
                        except (ValueError, TypeError):
                            pass
                    if llm_details.get('longitude'):
                        try:
                            venue.longitude = float(llm_details['longitude'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Handle additional_info as JSON
                    if llm_details.get('additional_info'):
                        try:
                            if isinstance(llm_details['additional_info'], str):
                                import json
                                venue.additional_info = json.loads(llm_details['additional_info'])
                            else:
                                venue.additional_info = llm_details['additional_info']
                        except (json.JSONDecodeError, TypeError):
                            venue.additional_info = llm_details['additional_info']
                    
                    enhancement_results['llm_enhanced'] = True
                    print(f"✅ LLM enhancement completed for {venue.name}")
                else:
                    enhancement_results['enhancement_errors'].append("LLM enhancement failed")
                    print(f"⚠️ LLM enhancement failed for {venue.name}")
                    
            except Exception as llm_error:
                enhancement_results['enhancement_errors'].append(f"LLM error: {str(llm_error)}")
                print(f"❌ LLM enhancement error: {llm_error}")
            
            # Step 2: Google Maps Image
            try:
                from scripts.utils import get_google_maps_image
                
                print(f"📸 Fetching Google Maps image for {venue.name}...")
                image_url = get_google_maps_image(
                    venue_name=venue.name,
                    city=city.name,
                    state=city.state,
                    country=city.country
                )
                
                if image_url:
                    venue.image_url = image_url
                    enhancement_results['google_maps_image'] = True
                    print(f"✅ Google Maps image fetched for {venue.name}")
                else:
                    enhancement_results['enhancement_errors'].append("Google Maps image not found")
                    print(f"⚠️ No Google Maps image found for {venue.name}")
                    
            except Exception as image_error:
                enhancement_results['enhancement_errors'].append(f"Google Maps error: {str(image_error)}")
                print(f"❌ Google Maps image error: {image_error}")
            
            # Commit enhanced venue data
            db.session.commit()
            print(f"💾 Enhanced venue data saved for {venue.name}")
            
        except Exception as enhancement_error:
            enhancement_results['enhancement_errors'].append(f"Enhancement error: {str(enhancement_error)}")
            print(f"❌ Venue enhancement failed: {enhancement_error}")
            # Don't fail the entire operation if enhancement fails
        
        # Update the predefined_venues.json file with the enhanced venue
        try:
            update_json_with_new_venue(venue, city)
        except Exception as json_error:
            print(f"Warning: Could not update JSON file: {json_error}")
            # Don't fail the entire operation if JSON update fails
        
        # Prepare response message
        message = f'Venue "{name}" added successfully'
        if enhancement_results['llm_enhanced']:
            message += " with LLM enhancement"
        if enhancement_results['google_maps_image']:
            message += " and Google Maps image"
        if enhancement_results['enhancement_errors']:
            message += f" (warnings: {', '.join(enhancement_results['enhancement_errors'])})"
        
        return jsonify({
            'success': True,
            'message': message,
            'venue_id': venue.id,
            'enhancement_results': enhancement_results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/clear-events', methods=['POST'])
def clear_events():
    """Clear all events from database"""
    try:
        # Count events before deletion
        events_count = Event.query.count()
        
        # Delete all events
        Event.query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {events_count} events from database'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/clear-venues', methods=['POST'])
def clear_venues():
    """Clear all venues from database"""
    try:
        # Count venues before deletion
        venues_count = Venue.query.count()
        
        # Delete all venues (this will also delete associated events due to foreign key constraints)
        Venue.query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {venues_count} venues from database'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Source Management Endpoints
@app.route('/api/admin/sources')
def admin_sources():
    """Get all sources for admin"""
    try:
        sources = Source.query.join(City).order_by(City.name, Source.name).all()
        return jsonify([source.to_dict() for source in sources])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/add-source', methods=['POST'])
def add_source():
    """Add a new event source"""
    try:
        data = request.get_json()
        
        # Get required fields
        name = clean_text_field(data.get('name', ''))
        handle = clean_text_field(data.get('handle', ''))
        source_type = clean_text_field(data.get('source_type', ''))
        city_id = data.get('city_id')
        
        # Auto-generate name from handle if not provided
        if not name and handle:
            name = handle.replace('@', '').replace('_', ' ').replace('-', ' ').title()
        
        if not handle or not source_type or not city_id:
            return jsonify({'error': 'Handle, source type, and city are required'}), 400
        
        if not name:
            name = 'Source'  # Default fallback
        
        # Check if city exists
        city = db.session.get(City, city_id)
        if not city:
            return jsonify({'error': 'City not found'}), 404
        
        # Check for duplicates
        existing_source = Source.query.filter(
            Source.handle == handle,
            Source.city_id == city_id
        ).first()
        
        if existing_source:
            return jsonify({'error': f'Source with handle "{handle}" already exists in this city'}), 400
        
        # Create new source
        source = Source(
            name=name,
            handle=handle,
            source_type=source_type,
            url=clean_url_field(data.get('url', '')),
            description=clean_text_field(data.get('description', '')),
            city_id=city_id,
            covers_multiple_cities=data.get('covers_multiple_cities', False),
            covered_cities=data.get('covered_cities', ''),
            event_types=data.get('event_types', ''),
            is_active=data.get('is_active', True),
            reliability_score=data.get('reliability_score', 5.0),
            posting_frequency=clean_text_field(data.get('posting_frequency', '')),
            notes=clean_text_field(data.get('notes', '')),
            scraping_pattern=clean_text_field(data.get('scraping_pattern', ''))
        )
        
        db.session.add(source)
        db.session.commit()
        
        # Update sources.json
        try:
            from scripts.update_sources_json import update_sources_json
            update_sources_json()
        except Exception as sources_json_error:
            print(f"⚠️ Warning: Could not update sources.json: {sources_json_error}")
        
        return jsonify({
            'success': True,
            'message': f'Source "{name}" added successfully',
            'source_id': source.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/sources/<int:source_id>', methods=['PUT'])
def update_source(source_id):
    """Update a source with refreshed information"""
    try:
        source = Source.query.get_or_404(source_id)
        data = request.get_json()
        
        # Update source fields
        if 'name' in data:
            source.name = data['name']
        if 'description' in data:
            source.description = data['description']
        if 'url' in data:
            source.url = data['url']
        if 'last_checked' in data:
            from datetime import datetime
            source.last_checked = datetime.fromisoformat(data['last_checked'].replace('Z', '+00:00'))
        
        # Update other fields if provided
        for field in ['reliability_score', 'posting_frequency', 'event_types', 'notes', 'scraping_pattern', 'is_active']:
            if field in data:
                setattr(source, field, data[field])
        
        source.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Source "{source.name}" updated successfully',
            'source': {
                'id': source.id,
                'name': source.name,
                'description': source.description,
                'url': source.url,
                'last_checked': source.last_checked.isoformat() if source.last_checked else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/edit-source', methods=['POST'])
def edit_source():
    """Edit an existing source"""
    try:
        data = request.get_json()
        source_id = data.get('id')
        
        if not source_id:
            return jsonify({'error': 'Source ID is required'}), 400
        
        # Get the source
        source = db.session.get(Source, source_id)
        if not source:
            return jsonify({'error': 'Source not found'}), 404
        
        # Update fields
        if 'name' in data:
            source.name = clean_text_field(data['name'])
        if 'handle' in data:
            source.handle = clean_text_field(data['handle'])
        if 'source_type' in data:
            source.source_type = clean_text_field(data['source_type'])
        if 'url' in data:
            source.url = clean_url_field(data['url'])
        if 'description' in data:
            source.description = clean_text_field(data['description'])
        if 'city_id' in data:
            source.city_id = data['city_id']
        if 'covers_multiple_cities' in data:
            source.covers_multiple_cities = data['covers_multiple_cities']
        if 'covered_cities' in data:
            source.covered_cities = data['covered_cities']
        if 'event_types' in data:
            source.event_types = data['event_types']
        if 'is_active' in data:
            source.is_active = data['is_active']
        if 'reliability_score' in data:
            source.reliability_score = data['reliability_score']
        if 'posting_frequency' in data:
            source.posting_frequency = clean_text_field(data['posting_frequency'])
        if 'notes' in data:
            source.notes = clean_text_field(data['notes'])
        if 'scraping_pattern' in data:
            source.scraping_pattern = clean_text_field(data['scraping_pattern'])
        
        source.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update sources.json
        try:
            from scripts.update_sources_json import update_sources_json
            update_sources_json()
        except Exception as sources_json_error:
            print(f"⚠️ Warning: Could not update sources.json: {sources_json_error}")
        
        return jsonify({
            'success': True,
            'message': f'Source "{source.name}" updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-source/<int:source_id>', methods=['DELETE'])
def delete_source(source_id):
    """Delete a source"""
    try:
        source = db.session.get(Source, source_id)
        if not source:
            return jsonify({'error': 'Source not found'}), 404
        
        source_name = source.name
        db.session.delete(source)
        db.session.commit()
        
        # Update sources.json
        try:
            from scripts.update_sources_json import update_sources_json
            update_sources_json()
        except Exception as sources_json_error:
            print(f"⚠️ Warning: Could not update sources.json: {sources_json_error}")
        
        return jsonify({
            'success': True,
            'message': f'Source "{source_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/edit-city', methods=['POST'])
def edit_city():
    """Edit city details"""
    try:
        data = request.get_json()
        city_id = data.get('id')
        
        if not city_id:
            return jsonify({'error': 'City ID is required'}), 400
        
        # Get the city
        city = db.session.get(City, city_id)
        if not city:
            return jsonify({'error': 'City not found'}), 404
        
        # Prepare updated values for duplicate checking
        updated_name = clean_text_field(data.get('name', city.name))
        updated_country = clean_text_field(data.get('country', city.country))
        updated_state = clean_text_field(data.get('state', city.state))
        
        # Check for duplicates before updating
        from scripts.utils import check_city_duplicate_active
        duplicate_city, duplicate_type = check_city_duplicate_active(updated_name, updated_state, updated_country, exclude_id=city_id)
        if duplicate_city:
            if duplicate_type == "exact":
                return jsonify({'error': f'City "{updated_name}" already exists (ID: {duplicate_city.id})'}), 400
            elif duplicate_type == "variation":
                return jsonify({'error': f'Similar city already exists: "{duplicate_city.name}" (ID: {duplicate_city.id}). Please use the existing city or choose a different name.'}), 400
            else:
                return jsonify({'error': f'City with similar name already exists: "{duplicate_city.name}" (ID: {duplicate_city.id})'}), 400
        
        # Update fields with cleaning
        if 'name' in data:
            city.name = updated_name
        if 'country' in data:
            city.country = updated_country
        if 'state' in data:
            city.state = updated_state
        if 'timezone' in data:
            city.timezone = clean_text_field(data['timezone'])
        
        db.session.commit()
        
        # Update cities.json
        try:
            from scripts.update_cities_json import update_cities_json
            update_cities_json()
        except Exception as cities_json_error:
            print(f"⚠️ Warning: Could not update cities.json: {cities_json_error}")
        
        return jsonify({
            'success': True,
            'message': f'City "{city.name}" updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/edit-venue', methods=['POST'])
def edit_venue():
    """Edit venue details"""
    try:
        data = request.get_json()
        venue_id = data.get('id')
        
        if not venue_id:
            return jsonify({'error': 'Venue ID is required'}), 400
        
        # Get the venue
        venue = db.session.get(Venue, venue_id)
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        # Prepare updated values for duplicate checking
        updated_name = clean_text_field(data.get('name', venue.name))
        updated_city_id = data.get('city_id', venue.city_id)
        
        # Check for duplicates before updating
        from scripts.utils import check_venue_duplicate
        duplicate_venue, duplicate_type = check_venue_duplicate(updated_name, updated_city_id, exclude_id=venue_id)
        if duplicate_venue:
            if duplicate_type == "exact":
                return jsonify({'error': f'Venue "{updated_name}" already exists in this city (ID: {duplicate_venue.id})'}), 400
            else:
                return jsonify({'error': f'Similar venue already exists in this city: "{duplicate_venue.name}" (ID: {duplicate_venue.id})'}), 400
        
        # Update fields with cleaning
        if 'name' in data:
            venue.name = clean_text_field(data['name'])
        if 'venue_type' in data:
            venue.venue_type = clean_text_field(data['venue_type'])
        if 'description' in data:
            venue.description = clean_text_field(data['description'])
        if 'address' in data:
            venue.address = clean_text_field(data['address'])
        if 'latitude' in data:
            venue.latitude = clean_numeric_field(data['latitude'])
        if 'longitude' in data:
            venue.longitude = clean_numeric_field(data['longitude'])
        if 'phone_number' in data:
            venue.phone_number = clean_phone_field(data['phone_number'])
        if 'email' in data:
            venue.email = clean_email_field(data['email'])
        if 'opening_hours' in data:
            venue.opening_hours = clean_text_field(data['opening_hours'])
        if 'holiday_hours' in data:
            venue.holiday_hours = clean_text_field(data['holiday_hours'])
        if 'website_url' in data:
            venue.website_url = clean_url_field(data['website_url'])
        if 'instagram_url' in data:
            venue.instagram_url = clean_url_field(data['instagram_url'])
        if 'facebook_url' in data:
            venue.facebook_url = clean_url_field(data['facebook_url'])
        if 'twitter_url' in data:
            venue.twitter_url = clean_url_field(data['twitter_url'])
        if 'youtube_url' in data:
            venue.youtube_url = clean_url_field(data['youtube_url'])
        if 'tiktok_url' in data:
            venue.tiktok_url = clean_url_field(data['tiktok_url'])
        if 'image_url' in data:
            venue.image_url = clean_url_field(data['image_url'])
        if 'tour_info' in data:
            venue.tour_info = clean_text_field(data['tour_info'])
        if 'admission_fee' in data:
            venue.admission_fee = clean_text_field(data['admission_fee'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Venue "{venue.name}" updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/edit-event', methods=['POST'])
def edit_event():
    """Edit event details"""
    try:
        data = request.get_json()
        event_id = data.get('id')
        
        if not event_id:
            return jsonify({'error': 'Event ID is required'}), 400
        
        # Get the event
        event = db.session.get(Event, event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        # Prepare updated values for duplicate checking
        updated_title = clean_text_field(data.get('title', event.title))
        updated_start_date = data.get('start_date', event.start_date)
        updated_venue_id = data.get('venue_id', event.venue_id)
        updated_city_id = data.get('city_id', event.city_id)
        
        # Parse date if it's a string
        if isinstance(updated_start_date, str):
            try:
                updated_start_date = datetime.strptime(updated_start_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400
        
        # Check for duplicates before updating
        from scripts.utils import check_event_duplicate
        duplicate_event, duplicate_type = check_event_duplicate(
            updated_title, updated_start_date, 
            venue_id=updated_venue_id, 
            city_id=updated_city_id, 
            exclude_id=event_id
        )
        if duplicate_event:
            if duplicate_type in ["exact_venue", "exact_city", "exact_no_location"]:
                return jsonify({'error': f'Event "{updated_title}" already exists on {updated_start_date} (ID: {duplicate_event.id})'}), 400
            else:
                return jsonify({'error': f'Similar event already exists on {updated_start_date}: "{duplicate_event.title}" (ID: {duplicate_event.id})'}), 400
        
        # Update basic fields with cleaning
        if 'title' in data:
            event.title = clean_text_field(data['title'])
        if 'event_type' in data:
            event.event_type = clean_text_field(data['event_type'])
        if 'description' in data:
            event.description = clean_text_field(data['description'])
        if 'start_date' in data:
            event.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'end_date' in data and data['end_date']:
            event.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        if 'start_time' in data and data['start_time']:
            event.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        if 'end_time' in data and data['end_time']:
            event.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        if 'city_id' in data:
            event.city_id = data['city_id']
        if 'venue_id' in data:
            event.venue_id = data['venue_id']
        if 'start_location' in data:
            event.start_location = clean_text_field(data['start_location'])
        if 'end_location' in data:
            event.end_location = clean_text_field(data['end_location'])
        if 'start_latitude' in data:
            event.start_latitude = clean_numeric_field(data['start_latitude'])
        if 'start_longitude' in data:
            event.start_longitude = clean_numeric_field(data['start_longitude'])
        if 'end_latitude' in data:
            event.end_latitude = clean_numeric_field(data['end_latitude'])
        if 'end_longitude' in data:
            event.end_longitude = clean_numeric_field(data['end_longitude'])
        if 'image_url' in data:
            event.image_url = clean_url_field(data['image_url'])
        if 'url' in data:
            event.url = clean_url_field(data['url'])
        
        # Update event type specific fields with cleaning
        if event.event_type == 'tour':
            if 'tour_type' in data:
                event.tour_type = clean_text_field(data['tour_type'])
            if 'max_participants' in data:
                event.max_participants = clean_integer_field(data['max_participants'])
            if 'price' in data:
                event.price = clean_numeric_field(data['price'])
            if 'language' in data:
                event.language = clean_text_field(data['language'])
        elif event.event_type == 'exhibition':
            if 'exhibition_location' in data:
                event.exhibition_location = clean_text_field(data['exhibition_location'])
            if 'curator' in data:
                event.curator = clean_text_field(data['curator'])
            if 'admission_price' in data:
                event.admission_price = clean_numeric_field(data['admission_price'])
        elif event.event_type == 'festival':
            if 'festival_type' in data:
                event.festival_type = clean_text_field(data['festival_type'])
            if 'multiple_locations' in data:
                event.multiple_locations = data['multiple_locations']
        elif event.event_type == 'photowalk':
            if 'difficulty_level' in data:
                event.difficulty_level = clean_text_field(data['difficulty_level'])
            if 'equipment_needed' in data:
                event.equipment_needed = clean_text_field(data['equipment_needed'])
            if 'organizer' in data:
                event.organizer = clean_text_field(data['organizer'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Event "{event.title}" updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/fetch-venue-details', methods=['POST'])
def fetch_venue_details():
    """Fetch comprehensive venue details using LLM"""
    try:
        data = request.get_json()
        venue_id = data.get('venue_id')
        
        if not venue_id:
            return jsonify({'error': 'Venue ID is required'}), 400
        
        # Get the venue
        venue = db.session.get(Venue, venue_id)
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        # Import the fetch venue details script
        import subprocess
        import sys
        
        # Run the fetch venue details script
        result = subprocess.run([
            sys.executable, 'scripts/fetch_venue_details.py',
            '--venue-id', str(venue_id)
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Venue details fetching failed',
                'details': result.stderr
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'Venue details fetched for {venue.name}',
            'output': result.stdout
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fetch-venue-images', methods=['POST'])
def fetch_venue_images():
    """Fetch images for all venues"""
    try:
        data = request.get_json() or {}
        use_placeholders = data.get('use_placeholders', False)
        
        # Import the fetch venue images script
        import subprocess
        import sys
        
        # Run the fetch venue images script
        cmd = [sys.executable, 'scripts/fetch_venue_images.py']
        if use_placeholders:
            cmd.append('--use-placeholders')
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Venue images fetching failed',
                'details': result.stderr
            }), 500
        
        # Count venues with images
        venues_with_images = Venue.query.filter(Venue.image_url.isnot(None)).count()
        total_venues = Venue.query.count()
        
        return jsonify({
            'success': True,
            'message': f'Images fetched for venues',
            'total_venues': total_venues,
            'venues_with_images': venues_with_images,
            'output': result.stdout
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-venue-details', methods=['POST'])
def update_venue_details():
    """Update venue details for all venues"""
    try:
        # Import the update venue details script
        import subprocess
        import sys
        
        # Run the update venue details script
        result = subprocess.run([
            sys.executable, 'scripts/update_venue_details.py'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Venue details update failed',
                'details': result.stderr
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Venue details updated successfully',
            'output': result.stdout
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-venue/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    """Delete a venue"""
    try:
        venue = db.session.get(Venue, venue_id)
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        venue_name = venue.name
        
        # Delete the venue (this will cascade to events)
        db.session.delete(venue)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Venue "{venue_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Delete an event"""
    try:
        event = db.session.get(Event, event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        event_title = event.title
        
        # Delete the event
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Event "{event_title}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/cleanup-duplicates', methods=['POST'])
def cleanup_duplicates():
    """Clean up duplicate cities with different country formats"""
    try:
        result = cleanup_duplicate_cities()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/auto-fill-event', methods=['POST'])
def auto_fill_event():
    """Auto-fill event form fields using AI"""
    try:
        data = request.get_json()
        event_name = data.get('name', '').strip()
        event_type = data.get('event_type', '').strip()
        
        if not event_name or not event_type:
            return jsonify({'error': 'Event name and type are required'}), 400
        
        # For now, return mock data. In the future, this could use LLM to generate realistic data
        mock_data = {
            'description': f"An engaging {event_type} event featuring {event_name}",
            'start_time': '10:00',
            'end_time': '16:00',
            'url': f"https://example.com/{event_name.lower().replace(' ', '-')}",
            'image_url': f"https://via.placeholder.com/400x300?text={event_name.replace(' ', '+')}",
            'start_location': 'Main Entrance',
            'end_location': 'Main Entrance',
            'tour_type': 'Guided' if event_type == 'tour' else None,
            'max_participants': 25 if event_type == 'tour' else None,
            'price': 15.00 if event_type == 'tour' else None,
            'language': 'English',
            'exhibition_location': 'Gallery A' if event_type == 'exhibition' else None,
            'curator': 'Dr. Jane Smith' if event_type == 'exhibition' else None,
            'admission_price': 12.00 if event_type == 'exhibition' else None,
            'festival_type': 'Cultural' if event_type == 'festival' else None,
            'multiple_locations': True if event_type == 'festival' else False,
            'difficulty_level': None,  # Leave empty - not required
            'equipment_needed': 'Camera, comfortable shoes' if event_type == 'photowalk' else None,
            'organizer': 'Local Photography Club' if event_type == 'photowalk' else None
        }
        
        return jsonify({
            'success': True,
            'data': mock_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/auto-fill-venue', methods=['POST'])
def auto_fill_venue():
    """Auto-fill venue form fields using AI"""
    try:
        data = request.get_json()
        venue_name = data.get('name', '').strip()
        venue_type = data.get('venue_type', '').strip()
        
        if not venue_name or not venue_type:
            return jsonify({'error': 'Venue name and type are required'}), 400
        
        # For now, return mock data. In the future, this could use LLM to generate realistic data
        mock_data = {
            'address': f"123 Main Street, {venue_name} District",
            'website_url': f"https://{venue_name.lower().replace(' ', '')}.org",
            'description': f"A {venue_type} featuring {venue_name}",
            'opening_hours': 'Monday-Friday: 9:00 AM - 5:00 PM, Saturday-Sunday: 10:00 AM - 6:00 PM',
            'holiday_hours': 'Closed on major holidays',
            'phone_number': '+1 (555) 123-4567',
            'email': f"info@{venue_name.lower().replace(' ', '')}.org",
            'tour_info': f"Guided tours available daily at {venue_name}",
            'admission_fee': 'Adults: $15, Seniors: $12, Students: $8, Children under 12: Free'
        }
        
        return jsonify({
            'success': True,
            'data': mock_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/discover-venues', methods=['POST'])
def discover_venues_frontend():
    """Discover venues for frontend (redirects to admin endpoint)"""
    try:
        api_logger.info(f"Frontend venue discovery request received")
        data = request.get_json()
        city_id = data.get('city_id')
        
        api_logger.debug(f"Request data: {data}")
        
        if not city_id:
            api_logger.warning("City ID missing from request")
            return jsonify({'error': 'City ID is required'}), 400
        
        api_logger.info(f"Starting venue discovery for city_id: {city_id}")
        
        # Redirect to admin endpoint
        result = discover_venues()
        api_logger.info(f"Venue discovery completed for city_id: {city_id}")
        return result
        
    except Exception as e:
        api_logger.error(f"Error in frontend venue discovery: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-venue-manually', methods=['POST'])
def add_venue_manually():
    """Add venue manually from frontend"""
    try:
        data = request.get_json()
        
        # Extract venue data
        venue_data = {
            'name': data.get('name', ''),
            'venue_type': data.get('venue_type', 'museum'),
            'description': data.get('description', ''),
            'address': data.get('address', ''),
            'website_url': data.get('website_url', ''),
            'phone': data.get('phone', ''),
            'email': data.get('email', ''),
            'hours': data.get('hours', ''),
            'price_range': data.get('price_range', ''),
            'rating': data.get('rating', ''),
            'amenities': data.get('amenities', ''),
            'accessibility': data.get('accessibility', ''),
            'parking': data.get('parking', ''),
            'public_transport': data.get('public_transport', ''),
            'special_features': data.get('special_features', ''),
            'city_id': data.get('city_id')
        }
        
        # Validate required fields
        if not venue_data['name'] or not venue_data['city_id']:
            return jsonify({'error': 'Name and city are required'}), 400
        
        # Check if venue already exists
        existing_venue = Venue.query.filter_by(
            name=venue_data['name'],
            city_id=venue_data['city_id']
        ).first()
        
        if existing_venue:
            return jsonify({'error': 'Venue already exists in this city'}), 400
        
        # Create new venue
        venue = Venue(**venue_data)
        db.session.add(venue)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Venue "{venue_data["name"]}" added successfully',
            'venue': venue.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def sync_cities_to_predefined_json():
    """Sync cities from database to predefined_cities.json"""
    try:
        import json
        from pathlib import Path
        from datetime import datetime
        
        # Load existing predefined cities
        json_file = Path("data/predefined_cities.json")
        if not json_file.exists():
            print("❌ predefined_cities.json not found")
            return False
        
        with open(json_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        existing_cities = existing_data.get('cities', {})
        existing_names = {city_data['name'].lower(): city_data for city_data in existing_cities.values()}
        
        # Get all cities from database
        db_cities = City.query.all()
        
        new_cities = []
        updated_cities = []
        
        for city in db_cities:
            city_key = city.name.lower()
            
            if city_key not in existing_names:
                # New city
                new_cities.append(city)
            else:
                # Check if city data has changed
                existing_city = existing_names[city_key]
                if (existing_city.get('state') != city.state or 
                    existing_city.get('country') != city.country or 
                    existing_city.get('timezone') != city.timezone):
                    updated_cities.append(city)
        
        if not new_cities and not updated_cities:
            return True  # No changes needed
        
        # Add new cities to existing data
        next_id = max([int(k) for k in existing_cities.keys()], default=0) + 1
        
        for city in new_cities:
            existing_cities[str(next_id)] = {
                "name": city.name,
                "state": city.state,
                "country": city.country,
                "timezone": city.timezone
            }
            next_id += 1
        
        # Update existing cities
        for city in updated_cities:
            # Find the city in existing data
            for city_id, city_data in existing_cities.items():
                if city_data['name'].lower() == city.name.lower():
                    existing_cities[city_id] = {
                        "name": city.name,
                        "state": city.state,
                        "country": city.country,
                        "timezone": city.timezone
                    }
                    break
        
        # Update metadata
        existing_data['metadata']['version'] = "1.2"
        existing_data['metadata']['total_cities'] = len(existing_cities)
        existing_data['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing_data['metadata']['new_cities_added'] = len(new_cities)
        existing_data['metadata']['cities_updated'] = len(updated_cities)
        
        # Write updated data
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Synced cities to predefined_cities.json")
        print(f"   New cities: {len(new_cities)}, Updated: {len(updated_cities)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error syncing cities: {e}")
        return False

# Image Upload and Event Creation Endpoints
@app.route('/api/admin/upload-event-image', methods=['POST'])
def upload_event_image():
    """Upload an image and extract event information"""
    try:
        from scripts.image_event_processor import ImageEventProcessor
        from scripts.google_calendar_integration import GoogleCalendarManager, create_calendar_event_from_extracted_data
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, TIFF'}), 400
        
        # Save uploaded file
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"event_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Get OCR engine preference from form
        ocr_engine = request.form.get('ocr_engine', 'auto')
        
        # Process image to extract event data
        from scripts.hybrid_event_processor import HybridEventProcessor
        processor = HybridEventProcessor(ocr_engine_preference=ocr_engine)
        extracted_data = processor.process_image_with_llm(file_path)
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception as e:
            app_logger.warning(f"Could not remove uploaded file {file_path}: {e}")
        
        return jsonify({
            'success': True,
            'extracted_data': {
                'title': extracted_data.title,
                'description': extracted_data.description,
                'start_date': extracted_data.start_date.isoformat() if extracted_data.start_date else None,
                'end_date': extracted_data.end_date.isoformat() if extracted_data.end_date else None,
                'start_time': extracted_data.start_time.isoformat() if extracted_data.start_time else None,
                'end_time': extracted_data.end_time.isoformat() if extracted_data.end_time else None,
                'start_location': extracted_data.start_location,
                'end_location': extracted_data.end_location,
                'event_type': extracted_data.event_type,
                'city': extracted_data.city,
                'city_id': extracted_data.city_id,
                'confidence': extracted_data.confidence,
                'source': extracted_data.source,
                'raw_text': extracted_data.raw_text,
                'llm_reasoning': extracted_data.llm_reasoning,
                'social_media_platform': extracted_data.social_media_platform,
                'social_media_handle': extracted_data.social_media_handle,
                'social_media_page_name': extracted_data.social_media_page_name,
                'social_media_posted_by': extracted_data.social_media_posted_by,
                'social_media_url': extracted_data.social_media_url
            }
        })
        
    except Exception as e:
        app_logger.error(f"Error processing uploaded image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/create-event-from-data', methods=['POST'])
def create_event_from_data():
    """Create an event from extracted data and optional venue/source information"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Event title is required'}), 400
        
        if not data.get('start_date'):
            return jsonify({'error': 'Start date is required'}), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = None
            if data.get('end_date'):
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Parse times
        start_time = None
        end_time = None
        if data.get('start_time'):
            try:
                start_time = datetime.strptime(data['start_time'], '%H:%M:%S').time()
            except ValueError:
                try:
                    start_time = datetime.strptime(data['start_time'], '%H:%M').time()
                except ValueError:
                    return jsonify({'error': 'Invalid time format. Use HH:MM or HH:MM:SS'}), 400
        
        if data.get('end_time'):
            try:
                end_time = datetime.strptime(data['end_time'], '%H:%M:%S').time()
            except ValueError:
                try:
                    end_time = datetime.strptime(data['end_time'], '%H:%M').time()
                except ValueError:
                    return jsonify({'error': 'Invalid time format. Use HH:MM or HH:MM:SS'}), 400
        
        # Create event
        start_location = data.get('start_location', '')
        end_location = data.get('end_location', '')
        location = data.get('location', '')
        
        # If location is not defined, set it to start_location
        if not location and start_location:
            location = start_location
        
        event = Event(
            title=data['title'],
            description=data.get('description', ''),
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            event_type=data.get('event_type', 'tour'),
            start_location=start_location,
            end_location=end_location,
            url=data.get('url', ''),
            city_id=data.get('city_id'),
            venue_id=data.get('venue_id'),
            source=data.get('source'),
            source_url=data.get('source_url'),
            # Social media fields
            social_media_platform=data.get('social_media_platform'),
            social_media_handle=data.get('social_media_handle'),
            social_media_page_name=data.get('social_media_page_name'),
            social_media_posted_by=data.get('social_media_posted_by'),
            social_media_url=data.get('social_media_url')
        )
        
        # Add event type specific fields
        if event.event_type == 'tour':
            event.tour_type = data.get('tour_type', 'Guided')
            event.max_participants = data.get('max_participants')
            event.price = data.get('price')
            event.language = data.get('language', 'English')
        elif event.event_type == 'exhibition':
            event.exhibition_location = data.get('exhibition_location', '')
            event.curator = data.get('curator', '')
            event.admission_price = data.get('price')
        elif event.event_type == 'festival':
            event.festival_type = data.get('festival_type', 'Cultural')
            event.multiple_locations = data.get('multiple_locations', False)
        elif event.event_type == 'photowalk':
            event.difficulty_level = data.get('difficulty_level', '') or None
            event.equipment_needed = data.get('equipment_needed', '')
            event.organizer = data.get('organizer', '')
        
        # Add to database
        db.session.add(event)
        db.session.commit()
        
        # Create Google Calendar event if requested
        calendar_event_id = None
        if data.get('create_calendar_event', False):
            try:
                from scripts.google_calendar_integration import GoogleCalendarManager, create_calendar_event_from_extracted_data
                
                # Get venue data if venue_id provided
                venue_data = None
                if event.venue_id:
                    venue = Venue.query.get(event.venue_id)
                    if venue:
                        venue_data = venue.to_dict()
                
                # Get city data if city_id provided
                city_data = None
                if event.city_id:
                    city = City.query.get(event.city_id)
                    if city:
                        city_data = city.to_dict()
                
                # Create calendar event
                calendar_manager = GoogleCalendarManager()
                if calendar_manager.authenticate():
                    calendar_event = create_calendar_event_from_extracted_data(
                        data, venue_data, city_data
                    )
                    if calendar_event:
                        calendar_event_id = calendar_manager.create_event(calendar_event)
                
            except Exception as e:
                app_logger.warning(f"Could not create Google Calendar event: {e}")
        
        return jsonify({
            'success': True,
            'event_id': event.id,
            'calendar_event_id': calendar_event_id,
            'message': 'Event created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error creating event: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/add', methods=['POST'])
def add_event_to_calendar():
    """Add an event to the user's calendar"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'start_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Extract event data
        title = data.get('title')
        description = data.get('description', '')
        start_date = data.get('start_date')
        end_date = data.get('end_date', start_date)  # Default to start_date if not provided
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        location = data.get('location', '')
        event_type = data.get('event_type', 'event')
        city_id = data.get('city_id')
        
        # Get city timezone if city_id is provided
        timezone = 'UTC'  # Default timezone
        if city_id:
            city = City.query.get(city_id)
            if city and city.timezone:
                timezone = city.timezone
        
        # Create calendar event data with enhanced information
        calendar_event = {
            'title': title,
            'description': description,
            'start_date': start_date,
            'end_date': end_date,
            'start_time': start_time,
            'end_time': end_time,
            'location': location,
            'event_type': event_type,
            'timezone': timezone,
            # Additional fields for enhanced calendar integration
            'start_location': data.get('start_location'),
            'end_location': data.get('end_location'),
            'social_media_platform': data.get('social_media_platform'),
            'social_media_handle': data.get('social_media_handle'),
            'social_media_page_name': data.get('social_media_page_name'),
            'social_media_posted_by': data.get('social_media_posted_by'),
            'social_media_url': data.get('social_media_url'),
            'url': data.get('url'),
            'source': data.get('source'),
            'source_url': data.get('source_url'),
            'organizer': data.get('organizer'),
            'price': data.get('price'),
            # Legacy Instagram fields for backward compatibility
            'instagram_handle': data.get('instagram_handle')
        }
        
        # Generate iCal format for calendar integration
        ical_content = generate_ical_event(calendar_event)
        
        app_logger.info(f"Calendar event created: {title} on {start_date} in {timezone}")
        
        return jsonify({
            'success': True,
            'message': 'Event added to calendar successfully',
            'event': calendar_event,
            'ical_content': ical_content
        })
        
    except Exception as e:
        app_logger.error(f"Error adding event to calendar: {e}")
        return jsonify({'error': str(e)}), 500

def generate_timezone_info(timezone_str):
    """Generate VTIMEZONE information for iCal format"""
    import pytz
    from datetime import datetime
    
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        
        # Get timezone abbreviation and offset
        tz_abbr = now.strftime('%Z')
        tz_offset = now.strftime('%z')
        
        # Format offset for iCal (e.g., -0500 -> -0500)
        if len(tz_offset) == 5:
            offset_formatted = tz_offset
        else:
            offset_formatted = tz_offset[:3] + '00'
        
        # For simplicity, we'll use a basic timezone definition
        # In a production system, you'd want to handle DST rules properly
        return f"""BEGIN:VTIMEZONE
TZID:{timezone_str}
BEGIN:STANDARD
DTSTART:20071104T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
TZOFFSETFROM:{offset_formatted}
TZOFFSETTO:{offset_formatted}
TZNAME:{tz_abbr}
END:STANDARD
END:VTIMEZONE"""
        
    except Exception as e:
        # Fallback to UTC if timezone is invalid
        return f"""BEGIN:VTIMEZONE
TZID:UTC
BEGIN:STANDARD
DTSTART:20071104T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
TZOFFSETFROM:+0000
TZOFFSETTO:+0000
TZNAME:UTC
END:STANDARD
END:VTIMEZONE"""

def generate_ical_event(event_data):
    """Generate iCal format for calendar event"""
    from datetime import datetime
    import pytz
    
    # Parse dates and times
    start_date = datetime.strptime(event_data['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(event_data['end_date'], '%Y-%m-%d').date()
    
    # Get timezone
    timezone_str = event_data.get('timezone', 'UTC')
    try:
        tz = pytz.timezone(timezone_str)
    except:
        tz = pytz.UTC  # Fallback to UTC if timezone is invalid
    
    # Handle times if provided - use floating time (no timezone conversion)
    start_datetime_str = start_date.strftime('%Y%m%d')
    end_datetime_str = end_date.strftime('%Y%m%d')
    
    if event_data.get('start_time'):
        start_time_str = event_data['start_time']
        # Handle both HH:MM and HH:MM:SS formats
        if len(start_time_str.split(':')) == 2:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        else:
            start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        
        # Use floating time format (no timezone conversion)
        start_datetime_str = f"{start_date.strftime('%Y%m%d')}T{start_time.strftime('%H%M%S')}"
    
    if event_data.get('end_time'):
        end_time_str = event_data['end_time']
        # Handle both HH:MM and HH:MM:SS formats
        if len(end_time_str.split(':')) == 2:
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        else:
            end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
        
        # Use floating time format (no timezone conversion)
        end_datetime_str = f"{end_date.strftime('%Y%m%d')}T{end_time.strftime('%H%M%S')}"
    
    # Generate unique ID
    import uuid
    event_id = str(uuid.uuid4())
    
    # Build enhanced description with additional information
    description_parts = []
    if event_data.get('description'):
        description_parts.append(event_data['description'])
    
    # Add event type
    if event_data.get('event_type'):
        description_parts.append(f"Event Type: {event_data['event_type'].title()}")
    
    # Add end location if different from start location
    if event_data.get('end_location') and event_data.get('end_location') != event_data.get('start_location'):
        description_parts.append(f"End Location: {event_data['end_location']}")
    
    # Add social media and web links
    if event_data.get('social_media_platform') and event_data.get('social_media_handle'):
        platform_name = event_data['social_media_platform'].title()
        description_parts.append(f"{platform_name}: @{event_data['social_media_handle']}")
    elif event_data.get('instagram_handle'):
        # Legacy Instagram support
        description_parts.append(f"Instagram: @{event_data['instagram_handle']}")
    
    if event_data.get('social_media_url'):
        description_parts.append(f"Social Media URL: {event_data['social_media_url']}")
    elif event_data.get('url'):
        description_parts.append(f"Website: {event_data['url']}")
    
    # Add source information
    if event_data.get('source'):
        description_parts.append(f"Source: {event_data['source']}")
    
    if event_data.get('source_url'):
        description_parts.append(f"Source URL: {event_data['source_url']}")
    
    # Add organizer and pricing
    if event_data.get('organizer'):
        description_parts.append(f"Organizer: {event_data['organizer']}")
    
    if event_data.get('price'):
        description_parts.append(f"Price: ${event_data['price']}")
    
    enhanced_description = '\\n\\n'.join(description_parts) if description_parts else event_data.get('description', '')
    
    # Use start_location as the calendar location if available
    calendar_location = event_data.get('start_location') or event_data.get('location', '')
    
    # Generate timezone information for iCal
    timezone_info = generate_timezone_info(timezone_str)
    
    # Create iCal content with timezone information
    ical_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Event Planner//Event Planner//EN
{timezone_info}
BEGIN:VEVENT
UID:{event_id}@eventplanner.com
DTSTART;TZID={timezone_str}:{start_datetime_str}
DTEND;TZID={timezone_str}:{end_datetime_str}
SUMMARY:{event_data['title']}
DESCRIPTION:{enhanced_description}
LOCATION:{calendar_location}
END:VEVENT
END:VCALENDAR"""
    
    return ical_content

@app.route('/api/admin/create-event-from-venue', methods=['POST'])
def create_event_from_venue():
    """Create an event based on venue information and additional data"""
    try:
        data = request.get_json()
        
        venue_id = data.get('venue_id')
        if not venue_id:
            return jsonify({'error': 'Venue ID is required'}), 400
        
        venue = Venue.query.get(venue_id)
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Event title is required'}), 400
        
        if not data.get('start_date'):
            return jsonify({'error': 'Start date is required'}), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = None
            if data.get('end_date'):
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Parse times
        start_time = None
        end_time = None
        if data.get('start_time'):
            try:
                start_time = datetime.strptime(data['start_time'], '%H:%M:%S').time()
            except ValueError:
                try:
                    start_time = datetime.strptime(data['start_time'], '%H:%M').time()
                except ValueError:
                    return jsonify({'error': 'Invalid time format. Use HH:MM or HH:MM:SS'}), 400
        
        if data.get('end_time'):
            try:
                end_time = datetime.strptime(data['end_time'], '%H:%M:%S').time()
            except ValueError:
                try:
                    end_time = datetime.strptime(data['end_time'], '%H:%M').time()
                except ValueError:
                    return jsonify({'error': 'Invalid time format. Use HH:MM or HH:MM:SS'}), 400
        
        # Create event
        event = Event(
            title=data['title'],
            description=data.get('description', ''),
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            event_type=data.get('event_type', 'tour'),
            start_location=venue.name,
            venue_id=venue.id,
            city_id=venue.city_id,
            url=data.get('url', ''),
            source=data.get('source'),
            source_url=data.get('source_url')
        )
        
        # Add event type specific fields
        if event.event_type == 'tour':
            event.tour_type = data.get('tour_type', 'Guided')
            event.max_participants = data.get('max_participants')
            event.price = data.get('price')
            event.language = data.get('language', 'English')
        elif event.event_type == 'exhibition':
            event.exhibition_location = data.get('exhibition_location', '')
            event.curator = data.get('curator', '')
            event.admission_price = data.get('price')
        elif event.event_type == 'festival':
            event.festival_type = data.get('festival_type', 'Cultural')
            event.multiple_locations = data.get('multiple_locations', False)
        elif event.event_type == 'photowalk':
            event.difficulty_level = data.get('difficulty_level', '') or None
            event.equipment_needed = data.get('equipment_needed', '')
            event.organizer = data.get('organizer', '')
        
        # Add to database
        db.session.add(event)
        db.session.commit()
        
        # Create Google Calendar event if requested
        calendar_event_id = None
        if data.get('create_calendar_event', False):
            try:
                from scripts.google_calendar_integration import GoogleCalendarManager, create_calendar_event_from_extracted_data
                
                calendar_manager = GoogleCalendarManager()
                if calendar_manager.authenticate():
                    calendar_event = create_calendar_event_from_extracted_data(
                        data, venue.to_dict(), venue.city.to_dict() if venue.city else None
                    )
                    if calendar_event:
                        calendar_event_id = calendar_manager.create_event(calendar_event)
                
            except Exception as e:
                app_logger.warning(f"Could not create Google Calendar event: {e}")
        
        return jsonify({
            'success': True,
            'event_id': event.id,
            'calendar_event_id': calendar_event_id,
            'message': f'Event created successfully for venue: {venue.name}'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating event from venue: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    # Generic CRUD endpoints are already registered at import time
    
    # Get port from environment (Railway provides PORT), default to 5001 for local
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_ENV') != 'production'
    
    app.run(debug=debug, port=port, host='0.0.0.0')