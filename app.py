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
    from flask import Flask, render_template, request, jsonify, session, redirect, Response, stream_with_context
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

# Calendar export configuration
CALENDAR_DEBUG = os.getenv('CALENDAR_DEBUG', 'false').lower() == 'true'
VENUE_ADDRESSES = {
    'NGA': 'National Gallery of Art, Constitution Ave NW, Washington, DC 20565, USA',
    'HIRSHHORN': 'Smithsonian Hirshhorn Museum and Sculpture Garden, Independence Ave SW, Washington, DC 20560, USA',
    'WEBSTERS': "Webster's Bookstore Cafe, 133 E Beaver Ave, State College, PA 16801, USA"
}

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
def migrate_events_schema():
    """Migrate Railway PostgreSQL events table schema to match expected schema.
    Returns: (success: bool, message: str, added_columns: list)
    """
    # Check if we're on Railway (either by RAILWAY_ENVIRONMENT or by PostgreSQL DATABASE_URL)
    db_url = os.getenv('DATABASE_URL', '')
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or ('postgresql' in db_url or 'postgres' in db_url)
    
    # Try Railway PostgreSQL migration first
    if is_railway and db_url:
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            
            # Connect to Railway PostgreSQL
            railway_conn = psycopg2.connect(db_url)
            railway_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            railway_cursor = railway_conn.cursor()
            
            # Get Railway schema
            railway_cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'events'
            """)
            railway_columns = {row[0]: row[1] for row in railway_cursor.fetchall()}
            
            # Ensure visits table exists
            railway_cursor.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id SERIAL PRIMARY KEY,
                    city_id INTEGER REFERENCES cities(id) ON DELETE SET NULL,
                    ip_address VARCHAR(100),
                    user_agent VARCHAR(500),
                    referrer VARCHAR(500),
                    page_path VARCHAR(200),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """)
            
            # Define expected columns (based on current Event model)
            # This should match all columns in the Event model definition
            expected_columns = [
                # Social media fields
                ('social_media_platform', 'VARCHAR(50)'),
                ('social_media_handle', 'VARCHAR(100)'),
                ('social_media_page_name', 'VARCHAR(100)'),
                ('social_media_posted_by', 'VARCHAR(100)'),
                ('social_media_url', 'VARCHAR(500)'),
                # Location fields
                ('start_location', 'VARCHAR(200)'),
                ('end_location', 'VARCHAR(200)'),
                # Online event field
                ('is_online', 'BOOLEAN'),
                # Baby-friendly field
                ('is_baby_friendly', 'BOOLEAN'),
                # Registration fields
                ('is_registration_required', 'BOOLEAN'),
                ('registration_opens_date', 'DATE'),
                ('registration_opens_time', 'TIME'),
                ('registration_url', 'VARCHAR(1000)'),
                ('registration_info', 'TEXT'),
                # Exhibition-specific fields
                ('artists', 'TEXT'),
                ('exhibition_type', 'VARCHAR(100)'),
                ('collection_period', 'VARCHAR(200)'),
                ('number_of_artworks', 'INTEGER'),
                ('opening_reception_date', 'DATE'),
                ('opening_reception_time', 'TIME'),
                ('is_permanent', 'BOOLEAN'),
                ('related_exhibitions', 'TEXT')
            ]
            
            # Add missing columns with appropriate defaults
            added_columns = []
            errors = []
            for col_name, pg_type in expected_columns:
                if col_name not in railway_columns:
                    try:
                        # Add default values for BOOLEAN columns to match model defaults
                        if col_name == 'is_online':
                            railway_cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {pg_type} DEFAULT FALSE")
                        elif col_name == 'is_baby_friendly':
                            railway_cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {pg_type} DEFAULT FALSE")
                        elif col_name == 'is_registration_required':
                            railway_cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {pg_type} DEFAULT FALSE")
                        elif col_name == 'is_permanent':
                            railway_cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {pg_type} DEFAULT FALSE")
                        else:
                            railway_cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {pg_type}")
                        added_columns.append(col_name)
                        print(f"✅ Auto-migrated: {col_name}")
                    except Exception as e:
                        error_msg = f"Failed to add {col_name}: {str(e)}"
                        errors.append(error_msg)
                        print(f"⚠️  Auto-migration failed for {col_name}: {e}")
            
            railway_cursor.close()
            railway_conn.close()
            
            if added_columns:
                message = f"Successfully added {len(added_columns)} columns: {', '.join(added_columns)}"
                if errors:
                    message += f". Errors: {'; '.join(errors)}"
                return True, message, added_columns
            elif errors:
                return False, f"Migration failed: {'; '.join(errors)}", []
            else:
                return True, "Schema is already up to date", []
        except ImportError:
            # psycopg2 not available - fall through to SQLite migration
            pass
        except Exception as e:
            # Railway migration failed - fall through to SQLite migration
            pass
    
    # Try SQLite migration for local development
    try:
        import sqlalchemy
        inspector = sqlalchemy.inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('events')]
        
        # Define expected columns for SQLite
        expected_columns = [
            ('is_baby_friendly', 'INTEGER', 0),  # SQLite uses INTEGER for BOOLEAN
            ('is_online', 'INTEGER', 0),
            ('is_registration_required', 'INTEGER', 0),
            ('is_permanent', 'INTEGER', 0),
        ]
        
        added_columns = []
        errors = []
        
        for col_name, col_type, default_val in expected_columns:
            if col_name not in existing_columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(sqlalchemy.text(f"ALTER TABLE events ADD COLUMN {col_name} {col_type} DEFAULT {default_val}"))
                        conn.commit()
                    
                    added_columns.append(col_name)
                    print(f"✅ Auto-migrated (SQLite): {col_name}")
                except Exception as e:
                    error_msg = f"Failed to add {col_name}: {str(e)}"
                    errors.append(error_msg)
                    print(f"⚠️  Auto-migration failed for {col_name}: {e}")
        
        if added_columns:
            message = f"Successfully added {len(added_columns)} columns: {', '.join(added_columns)}"
            if errors:
                message += f". Errors: {'; '.join(errors)}"
            return True, message, added_columns
        elif errors:
            return False, f"Migration failed: {'; '.join(errors)}", []
        else:
            return True, "Schema is already up to date", []
    except Exception as e:
        return False, f"SQLite migration error: {str(e)}", []

def migrate_venues_schema():
    """Migrate venues table schema to add ticketing_url column if missing."""
    try:
        # Check if we're on Railway (PostgreSQL)
        db_url = os.getenv('DATABASE_URL', '')
        is_railway = os.getenv('RAILWAY_ENVIRONMENT') or ('postgresql' in db_url or 'postgres' in db_url)
        
        if is_railway and db_url:
            try:
                import psycopg2
                from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
                
                railway_conn = psycopg2.connect(db_url)
                railway_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                railway_cursor = railway_conn.cursor()
                
                # Check if ticketing_url column exists
                railway_cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'venues' AND column_name = 'ticketing_url'
                """)
                exists = railway_cursor.fetchone()
                
                if not exists:
                    railway_cursor.execute("ALTER TABLE venues ADD COLUMN ticketing_url VARCHAR(200)")
                    railway_cursor.close()
                    railway_conn.close()
                    return True, "Added ticketing_url column to venues table", ['ticketing_url']
                else:
                    railway_cursor.close()
                    railway_conn.close()
                    return True, "Venues schema is already up to date", []
            except ImportError:
                pass
            except Exception as e:
                pass
        
        # Try SQLite migration for local development
        try:
            import sqlalchemy
            inspector = sqlalchemy.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('venues')]
            
            if 'ticketing_url' not in existing_columns:
                with db.engine.connect() as conn:
                    conn.execute(sqlalchemy.text("ALTER TABLE venues ADD COLUMN ticketing_url VARCHAR(200)"))
                    conn.commit()
                return True, "Added ticketing_url column to venues table", ['ticketing_url']
            else:
                return True, "Venues schema is already up to date", []
        except Exception as e:
            return False, f"Venues migration error: {str(e)}", []
    except Exception as e:
        return False, f"Venues migration error: {str(e)}", []

def auto_migrate_schema():
    """Automatically migrate schema on startup (Railway PostgreSQL or local SQLite)."""
    try:
        with app.app_context():
            # Migrate events table
            success, message, _ = migrate_events_schema()
            if success:
                print(f"✅ Events schema migration: {message}")
            else:
                print(f"⚠️  Events schema migration: {message}")
            
            # Migrate venues table
            success, message, _ = migrate_venues_schema()
            if success:
                print(f"✅ Venues schema migration: {message}")
            else:
                print(f"⚠️  Venues schema migration: {message}")
    except Exception as e:
        # Migration can fail on startup if database isn't ready yet - that's okay
        print(f"⚠️  Schema migration: {str(e)}")

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
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
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
    image_url = db.Column(db.String(1000))  # Increased for long Google Maps photo references
    instagram_url = db.Column(db.String(200))
    facebook_url = db.Column(db.String(200))
    twitter_url = db.Column(db.String(200))
    youtube_url = db.Column(db.String(200))
    tiktok_url = db.Column(db.String(200))
    website_url = db.Column(db.String(200))
    ticketing_url = db.Column(db.String(200))  # Eventbrite, Ticketmaster, or other ticketing links
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
            'ticketing_url': self.ticketing_url,
            'description': self.description,
            'opening_hours': self.opening_hours,
            'holiday_hours': self.holiday_hours,
            'phone_number': self.phone_number,
            'email': self.email,
            'tour_info': self.tour_info,
            'admission_fee': self.admission_fee,
            'additional_info': self.additional_info,
            'city_id': self.city_id,
            'city_name': self.city.name if self.city else None,
            'city_timezone': self._get_city_timezone(),
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }
    
    def _get_city_timezone(self):
        """Get city timezone, with fallback lookup if relationship not loaded"""
        if self.city and self.city.timezone:
            return self.city.timezone
        if self.city_id:
            city = db.session.get(City, self.city_id)
            if city and city.timezone:
                return city.timezone
        return None

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
    image_url = db.Column(db.String(1000))  # Increased for long Google Maps photo references
    url = db.Column(db.String(1000))  # Increased for long URLs
    is_selected = db.Column(db.Boolean, default=True)
    is_online = db.Column(db.Boolean, default=False)  # True for online/virtual events
    is_baby_friendly = db.Column(db.Boolean, default=False)  # True for baby/toddler-friendly events
    event_type = db.Column(db.String(50), nullable=False)  # 'tour', 'exhibition', 'festival', 'photowalk'
    
    # Registration fields
    is_registration_required = db.Column(db.Boolean, default=False)  # True if registration is required
    registration_opens_date = db.Column(db.Date)  # Date when registration opens
    registration_opens_time = db.Column(db.Time)  # Time when registration opens
    registration_url = db.Column(db.String(1000))  # URL to register for the event
    registration_info = db.Column(db.Text)  # Additional registration details (e.g., "Registration opens 2 weeks before event")
    source = db.Column(db.String(50))  # 'instagram', 'facebook', 'website', etc.
    source_url = db.Column(db.String(1000))  # URL of the source (e.g., Instagram post URL) - increased for long URLs
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
    artists = db.Column(db.Text)  # Comma-separated or JSON list of artist names
    exhibition_type = db.Column(db.String(100))  # 'solo', 'group', 'retrospective', 'permanent collection', 'traveling', etc.
    collection_period = db.Column(db.String(200))  # e.g., 'Modern Art', 'Contemporary', 'Ancient', 'Renaissance'
    number_of_artworks = db.Column(db.Integer)  # Number of pieces in exhibition
    opening_reception_date = db.Column(db.Date)  # Opening reception/vernissage date
    opening_reception_time = db.Column(db.Time)  # Opening reception time
    is_permanent = db.Column(db.Boolean, default=False)  # True for permanent collections
    related_exhibitions = db.Column(db.Text)  # JSON array of related exhibition IDs or titles
    
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
        from urllib.parse import quote
        
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
        
        # Route external image URLs through proxy to bypass hotlinking restrictions
        if image_url and isinstance(image_url, str) and image_url.startswith('http'):
            from urllib.parse import quote
            # Check if it's from a domain that blocks hotlinking (e.g., hirshhorn.si.edu)
            blocked_domains = ['hirshhorn.si.edu', 'si.edu']
            if any(domain in image_url for domain in blocked_domains):
                # Route through our proxy endpoint
                encoded_url = quote(image_url, safe='')
                image_url = f"/api/image-proxy?url={encoded_url}"
        
        # Generate Google Maps link for navigation
        # Priority: venue coordinates/name > event coordinates > event location
        # This ensures venue-based events use the venue for maps, not the specific meeting point
        maps_link = ""
        if self.venue and self.venue.latitude and self.venue.longitude:
            # Use venue coordinates if available (most accurate)
            maps_link = f"https://www.google.com/maps/@{self.venue.latitude},{self.venue.longitude},17z"
        elif self.venue and self.venue.name and self.venue.name.strip():
            # Use venue name for search (e.g., "National Gallery of Art")
            venue_name = self.venue.name.replace(' ', '+')
            maps_link = f"https://www.google.com/maps/search/{venue_name}"
        elif self.start_latitude and self.start_longitude:
            # Fall back to event coordinates if no venue
            maps_link = f"https://www.google.com/maps/@{self.start_latitude},{self.start_longitude},17z"
        elif self.start_location and self.start_location.strip():
            # Last resort: use meeting point location if no venue
            location_name = self.start_location.replace(' ', '+')
            maps_link = f"https://www.google.com/maps/search/{location_name}"
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
            'is_online': self.is_online if hasattr(self, 'is_online') else False,  # Online/virtual event flag
            'is_baby_friendly': self.is_baby_friendly if hasattr(self, 'is_baby_friendly') else False,  # Baby/toddler-friendly event flag
            'url': self.url,
            'is_selected': self.is_selected,
            'event_type': self.event_type,
            'is_registration_required': self.is_registration_required if hasattr(self, 'is_registration_required') else False,
            'registration_opens_date': self.registration_opens_date.isoformat() if hasattr(self, 'registration_opens_date') and self.registration_opens_date else None,
            'registration_opens_time': self.registration_opens_time.strftime('%H:%M') if hasattr(self, 'registration_opens_time') and self.registration_opens_time else None,
            'registration_url': self.registration_url if hasattr(self, 'registration_url') else None,
            'registration_info': self.registration_info if hasattr(self, 'registration_info') else None,
            'start_location': self.start_location,
            'end_location': self.end_location,
            'venue_id': self.venue_id,
            'venue_name': self.venue.name if self.venue else None,
            'venue_type': self.venue.venue_type if self.venue else None,
            'venue_address': self.venue.address if self.venue else None,
            'city_id': self.city_id,
            'city_name': self.city.name if self.city else None,
            'city_timezone': self._get_city_timezone(),
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
            'artists': self.artists,
            'exhibition_type': self.exhibition_type,
            'collection_period': self.collection_period,
            'number_of_artworks': self.number_of_artworks,
            'opening_reception_date': self.opening_reception_date.isoformat() if self.opening_reception_date else None,
            'opening_reception_time': self.opening_reception_time.isoformat() if self.opening_reception_time else None,
            'is_permanent': self.is_permanent,
            'related_exhibitions': self.related_exhibitions,
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
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }
    
    def _get_city_timezone(self):
        """Get city timezone, with fallback lookup if relationship not loaded"""
        if self.city and self.city.timezone:
            return self.city.timezone
        if self.city_id:
            city = db.session.get(City, self.city_id)
            if city and city.timezone:
                return city.timezone
        return None

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
            'last_checked': self.last_checked.isoformat() + 'Z' if self.last_checked else None,
            'last_event_found': self.last_event_found.isoformat() + 'Z' if self.last_event_found else None,
            'events_found_count': self.events_found_count,
            'reliability_score': self.reliability_score,
            'posting_frequency': self.posting_frequency,
            'notes': self.notes,
            'scraping_pattern': self.scraping_pattern,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
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

class Visit(db.Model):
    """Tracking website visits"""
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='SET NULL'))
    ip_address = db.Column(db.String(100))
    user_agent = db.Column(db.String(500))
    referrer = db.Column(db.String(500))
    page_path = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    city = db.relationship('City', backref='visits')
    
    def to_dict(self):
        return {
            'id': self.id,
            'city_id': self.city_id,
            'city_name': self.city.name if self.city else 'Main Page',
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'user_agent': self.user_agent,
            'referrer': self.referrer,
            'page_path': self.page_path
        }
    
    def __repr__(self):
        return f"<Visit {self.id} (City: {self.city_id})>"

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

@app.route('/test-calendar')
def test_calendar():
    """Test page for calendar export debugging"""
    return render_template('test_calendar.html')

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
    ga_id = os.getenv('GOOGLE_ANALYTICS_ID')
    return render_template('index.html', google_analytics_id=ga_id)


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
        })

@app.after_request
def add_header(response):
    """
    Disable caching for all routes to ensure the latest UI is always loaded
    during active development and deployment updates.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/api/log-visit', methods=['POST'])
def log_visit():
    """Log a website visit"""
    try:
        data = request.get_json() or {}
        city_id = data.get('city_id')
        page_path = data.get('page_path', '/')
        
        # Get client info
        # Use X-Forwarded-For for Railway/Proxy
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0]
        else:
            ip_address = request.remote_addr
            
        user_agent = request.headers.get('User-Agent')
        referrer = request.headers.get('Referer')
        
        # Create visit record
        visit = Visit(
            city_id=city_id if city_id and str(city_id).isdigit() else None,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            page_path=page_path
        )
        
        db.session.add(visit)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        app_logger.error(f"Error logging visit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/visit-stats')
def get_visit_stats():
    """Get visit statistics for the admin panel"""
    try:
        from sqlalchemy import func
        
        # Total visits
        total_visits = Visit.query.count()
        
        # Visits in the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_visits = Visit.query.filter(Visit.timestamp >= yesterday).count()
        
        # Visits by city
        city_stats = db.session.query(
            City.name, func.count(Visit.id)
        ).join(City, Visit.city_id == City.id, isouter=True).group_by(City.name).all()
        
        city_data = [{'city': name or 'Main Page', 'count': count} for name, count in city_stats]
        
        # Recent visits list
        latest_visits = Visit.query.order_by(Visit.timestamp.desc()).limit(20).all()
        
        return jsonify({
            'total': total_visits,
            'recent_24h': recent_visits,
            'by_city': city_data,
            'latest': [v.to_dict() for v in latest_visits]
        })
    except Exception as e:
        app_logger.error(f"Error getting visit stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/clear-visits', methods=['POST'])
def clear_visits():
    """Clear all visit records from the database"""
    try:
        # Delete all records from the visits table
        num_deleted = db.session.query(Visit).delete()
        db.session.commit()
        
        app_logger.info(f"Admin cleared {num_deleted} visit records")
        return jsonify({
            'success': True, 
            'message': f'Successfully deleted {num_deleted} visit records.'
        })
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error clearing visits: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    time_range = request.args.get('time_range', 'this_week')
    event_type = request.args.get('event_type')
    include_unselected = request.args.get('include_unselected', 'false').lower() == 'true'
    
    if not city_id:
        return jsonify({'error': 'City ID is required'}), 400
    
    try:
        city_id_int = int(city_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid City ID format'}), 400
        
    city = db.session.get(City, city_id_int)
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
    elif time_range == 'all':
        # For "all", don't filter by date - return all events
        # Set a very wide date range (past and far future)
        start_date = None
        end_date = None
    else:
        return jsonify({'error': 'Invalid time range'}), 400
    
    # Query events based on type
    events = []
    
    # Get venues for this city once (used by events)
    city_venues = Venue.query.filter_by(city_id=city_id).all()
    venue_ids = [v.id for v in city_venues]
    
    # Import for OR condition
    from sqlalchemy import or_
    
    if not event_type or event_type == 'tour':
        tour_filter = Event.event_type == 'tour'
        if venue_ids:
            tour_filter = tour_filter & or_(Event.city_id == city_id, Event.venue_id.in_(venue_ids))
        else:
            tour_filter = tour_filter & (Event.city_id == city_id)
        
        tour_query = Event.query.filter(tour_filter)
        # Show all events by default (both selected and unselected)
        # Users can filter by is_selected on the frontend if needed
        
        # Only filter by date if not "all"
        if time_range != 'all':
            tour_query = tour_query.filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date
            )
        
        tour_events = tour_query.options(db.joinedload(Event.city)).all()
        events.extend([event.to_dict() for event in tour_events])
    
    if not event_type or event_type == 'exhibition':
        exhibition_filter = Event.event_type == 'exhibition'
        if venue_ids:
            exhibition_filter = exhibition_filter & or_(Event.city_id == city_id, Event.venue_id.in_(venue_ids))
        else:
            exhibition_filter = exhibition_filter & (Event.city_id == city_id)
        
        exhibition_query = Event.query.filter(exhibition_filter)
        # Show all events by default (both selected and unselected)
        
        # Only filter by date if not "all"
        if time_range == 'all':
            # For "all", show all exhibitions (no date filtering)
            pass
        elif time_range == 'today':
            # For today, only show exhibitions that are currently running
            exhibition_query = exhibition_query.filter(
                Event.start_date <= start_date,
                Event.end_date >= start_date
            )
        else:
            # For other time ranges, show exhibitions that overlap with the range
            exhibition_query = exhibition_query.filter(
                Event.start_date <= end_date,
                Event.end_date >= start_date
            )
        
        exhibition_events = exhibition_query.all()
        events.extend([event.to_dict() for event in exhibition_events])
    
    if not event_type or event_type == 'festival':
        festival_query = Event.query.filter(
            Event.event_type == 'festival',
            Event.city_id == city_id
        )
        # Show all events by default (both selected and unselected)
        
        # Only filter by date if not "all"
        if time_range != 'all':
            festival_query = festival_query.filter(
                Event.start_date <= end_date,
                Event.end_date >= start_date
            )
        
        festival_events = festival_query.all()
        events.extend([event.to_dict() for event in festival_events])
    
    if not event_type or event_type == 'photowalk':
        photowalk_query = Event.query.filter(
            Event.event_type == 'photowalk',
            Event.city_id == city_id
        )
        # Show all events by default (both selected and unselected)
        
        # Only filter by date if not "all"
        if time_range != 'all':
            photowalk_query = photowalk_query.filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date
            )
        
        photowalk_events = photowalk_query.all()
        events.extend([event.to_dict() for event in photowalk_events])
    
    if not event_type or event_type == 'music':
        music_query = Event.query.filter(
            Event.event_type == 'music',
            Event.city_id == city_id
        )
        if time_range != 'all':
            music_query = music_query.filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date
            )
        music_events = music_query.all()
        events.extend([event.to_dict() for event in music_events])

    if not event_type or event_type == 'film':
        film_query = Event.query.filter(
            Event.event_type == 'film',
            Event.city_id == city_id
        )
        if time_range != 'all':
            film_query = film_query.filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date
            )
        film_events = film_query.all()
        events.extend([event.to_dict() for event in film_events])

    if not event_type or event_type == 'workshop':
        workshop_query = Event.query.filter(
            Event.event_type == 'workshop',
            Event.city_id == city_id
        )
        if time_range != 'all':
            workshop_query = workshop_query.filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date
            )
        workshop_events = workshop_query.all()
        events.extend([event.to_dict() for event in workshop_events])

    if not event_type or event_type == 'talk':
        talk_query = Event.query.filter(
            Event.event_type == 'talk',
            Event.city_id == city_id
        )
        if time_range != 'all':
            talk_query = talk_query.filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date
            )
        talk_events = talk_query.all()
        events.extend([event.to_dict() for event in talk_events])
    
    # Handle other event types (music, food, community_event, etc.)
    # These should be included when event_type is empty or matches
    if not event_type or event_type not in ['tour', 'exhibition', 'festival', 'photowalk', 'film', 'workshop', 'talk', 'music']:
        if venue_ids:
            other_filter = or_(Event.city_id == city_id, Event.venue_id.in_(venue_ids))
        else:
            other_filter = Event.city_id == city_id
        
        other_events = Event.query.filter(other_filter)
        # Show all events by default (both selected and unselected)
        
        # Only filter by date if not "all"
        if time_range != 'all':
            other_events = other_events.filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date
            )
        
        # If a specific event_type was provided, filter by it
        if event_type:
            other_events = other_events.filter(Event.event_type == event_type)
        else:
            # Exclude the types we already handled above
            other_events = other_events.filter(
                ~Event.event_type.in_(['tour', 'exhibition', 'festival', 'photowalk', 'film', 'workshop', 'talk', 'music'])
            )
        
        other_events = other_events.all()
        events.extend([event.to_dict() for event in other_events])
    
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
    
    # Sort by most recently updated first
    venues = query.order_by(Venue.updated_at.desc()).all()
    return jsonify([venue.to_dict() for venue in venues])

@app.route('/api/image/<photo_reference>')
def get_venue_image(photo_reference):
    """Secure image proxy endpoint that adds API key server-side"""
    try:
        # Validate photo reference is not empty
        if not photo_reference or not photo_reference.strip():
            app_logger.warning("Empty photo reference provided to /api/image/ endpoint")
            return jsonify({'error': 'Invalid photo reference'}), 400
        
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

@app.route('/api/image-proxy')
def proxy_external_image():
    """Proxy external images to bypass hotlinking restrictions (e.g., Cloudflare)"""
    from flask import request
    from urllib.parse import unquote, quote
    import requests
    from flask import Response
    
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({'error': 'Missing url parameter'}), 400
        
        # Decode the URL if it was encoded
        image_url = unquote(image_url)
        
        # Validate that it's an HTTP(S) URL
        if not image_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid URL'}), 400
        
        # Disable SSL verification warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Set proper headers to avoid bot detection and hotlinking restrictions
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://hirshhorn.si.edu/',  # Add referer to make request look legitimate (bypasses hotlinking)
            'Origin': 'https://hirshhorn.si.edu',
        }
        
        # Try regular requests first (works well with proper headers)
        try:
            response = requests.get(image_url, headers=headers, timeout=15, allow_redirects=True, verify=False)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # If regular requests fails, try cloudscraper (for Cloudflare protection)
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper()
                app_logger.info(f"Regular request failed, trying cloudscraper for {image_url}")
                # Disable SSL verification for cloudscraper too (fixes SSL certificate errors)
                response = scraper.get(image_url, headers=headers, timeout=15, allow_redirects=True, verify=False)
                response.raise_for_status()
            except ImportError:
                # cloudscraper not available, re-raise original error
                raise e
            except Exception as e2:
                # cloudscraper also failed, log and raise
                app_logger.error(f"Both regular requests and cloudscraper failed for {image_url}: {e}, {e2}")
                raise e
        
        # Determine content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        if not content_type.startswith('image/'):
            content_type = 'image/jpeg'
        
        # Return the image with proper headers
        return Response(
            response.content,
            mimetype=content_type,
            headers={
                'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                'Content-Type': content_type,
                'Access-Control-Allow-Origin': '*'  # Allow cross-origin requests
            }
        )
        
    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error proxying image from {image_url}: {e}")
        return jsonify({'error': f'Failed to fetch image: {str(e)}'}), 500
    except Exception as e:
        app_logger.error(f"Unexpected error proxying image: {e}")
        return jsonify({'error': 'Failed to proxy image'}), 500

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

def save_event_to_database(event_data, city_id, venue_exhibition_counts, venue_event_counts, max_exhibitions_per_venue, max_events_per_venue):
    """
    Helper function to save a single event to the database with all validation logic.
    Returns (saved_event, was_created) tuple, or (None, False) if skipped.
    """
    from datetime import datetime as dt
    from datetime import date
    
    try:
        title = event_data.get('title', 'Untitled Event')
        
        # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
        from scripts.utils import is_category_heading
        if is_category_heading(title):
            app_logger.debug(f"⚠️ Skipping category heading: '{title}'")
            return None, False
        
        # Skip non-English language events
        language = event_data.get('language', 'English')
        if language and language.lower() != 'english':
            app_logger.debug(f"⚠️ Skipping non-English event: '{title}' (language: {language})")
            return None, False
        
        venue_id = event_data.get('venue_id')
        city_id_event = event_data.get('city_id', city_id)
        start_date_str = event_data.get('start_date')
        event_type = event_data.get('event_type', 'tour')
        
        # CRITICAL: For exhibitions, check if we've already saved max_exhibitions_per_venue for this venue
        if event_type == 'exhibition' and venue_id:
            venue = db.session.get(Venue, venue_id)
            if venue and venue.website_url:
                website = venue.website_url.lower().strip()
                current_count = 0
                for vid, count in venue_exhibition_counts.items():
                    v = db.session.get(Venue, vid)
                    if v and v.website_url and v.website_url.lower().strip() == website:
                        current_count += count
            else:
                current_count = venue_exhibition_counts.get(venue_id, 0)
            
            if current_count >= max_exhibitions_per_venue:
                app_logger.info(f"⚠️ Skipped exhibition '{title}' - already saved {current_count} exhibitions for venue {venue_id} (limit: {max_exhibitions_per_venue})")
                return None, False
        
        # Detect if event is baby-friendly
        is_baby_friendly = False
        title_lower = title.lower()
        description_lower = (event_data.get('description', '') or '').lower()
        combined_text = f"{title_lower} {description_lower}"
        
        baby_keywords = [
            'baby', 'babies', 'toddler', 'toddlers', 'infant', 'infants',
            'ages 0-2', 'ages 0–2', 'ages 0 to 2', '0-2 years', '0–2 years',
            'ages 0-3', 'ages 0–3', 'ages 0 to 3', '0-3 years', '0–3 years',
            'bring your own baby', 'byob', 'baby-friendly', 'baby friendly',
            'stroller', 'strollers', 'nursing', 'breastfeeding',
            'family program', 'family-friendly', 'family friendly',
            'art & play', 'art and play', 'play time', 'playtime',
            'children', 'kids', 'little ones', 'young families'
        ]
        
        if any(keyword in combined_text for keyword in baby_keywords):
            is_baby_friendly = True
            app_logger.info(f"   👶 Detected baby-friendly event: '{title}'")
        
        # Parse start date
        if start_date_str:
            start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = date.today()
        
        # Check for existing event
        event_url = event_data.get('url', '')
        existing_event = None
        
        if event_type == 'tour' and event_url:
            normalized_url = event_url.rstrip('/')
            existing_event = Event.query.filter(
                ((Event.url == event_url) | (Event.url == normalized_url)),
                Event.event_type == 'tour',
                Event.city_id == city_id_event,
                Event.start_date == start_date
            ).first()
        
        if not existing_event:
            if event_type == 'exhibition' and venue_id:
                venue = db.session.get(Venue, venue_id)
                if venue and venue.website_url:
                    existing_event = db.session.query(Event).join(Venue).filter(
                        Event.title == title,
                        Event.event_type == 'exhibition',
                        Venue.website_url == venue.website_url,
                        Event.city_id == city_id_event,
                        Event.start_date == start_date
                    ).first()
                else:
                    existing_event = Event.query.filter_by(
                        title=title,
                        venue_id=venue_id,
                        city_id=city_id_event,
                        start_date=start_date
                    ).first()
            else:
                if event_url:
                    normalized_url = event_url.rstrip('/')
                    existing_event = Event.query.filter(
                        (((Event.url == event_url) | (Event.url == normalized_url)) & (Event.start_date == start_date)) |
                        ((Event.title == title) & (Event.venue_id == venue_id) & (Event.city_id == city_id_event) & (Event.start_date == start_date)),
                        Event.event_type == event_type
                    ).first()
                else:
                    existing_event = Event.query.filter_by(
                        title=title,
                        venue_id=venue_id,
                        city_id=city_id_event,
                        start_date=start_date
                    ).first()
        
        start_time_str = event_data.get('start_time')
        end_time_str = event_data.get('end_time')
        
        # Default end_time for music/performance events to 11:59 PM if missing
        if event_type in ['music', 'performance'] and not end_time_str:
            end_time_str = '23:59'
        
        # Update existing event
        if existing_event:
            app_logger.info(f"🔄 Updating existing event: '{title}' (venue_id: {venue_id}, date: {start_date})")
            event = existing_event
            updated_fields = []
            
            # Update description if new one is longer
            new_description = event_data.get('description', '')
            if new_description and (not event.description or len(new_description) > len(event.description)):
                event.description = new_description
                updated_fields.append('description')
            
            # Update event_type if more specific
            new_event_type = event_data.get('event_type')
            if new_event_type and new_event_type != 'event' and event.event_type == 'event':
                event.event_type = new_event_type
                updated_fields.append('event_type')
            
            if event_data.get('url') and event_data.get('url') != event.url:
                event.url = event_data.get('url')
                updated_fields.append('url')
            
            if event_data.get('image_url') and event_data.get('image_url') != event.image_url:
                event.image_url = event_data.get('image_url')
                updated_fields.append('image_url')
            
            # Update times
            if start_time_str and start_time_str != 'None' and str(start_time_str).strip():
                try:
                    new_start_time = dt.strptime(str(start_time_str), '%H:%M:%S').time()
                except ValueError:
                    try:
                        new_start_time = dt.strptime(str(start_time_str), '%H:%M').time()
                    except ValueError:
                        new_start_time = None
                
                if new_start_time and (not event.start_time or event.start_time != new_start_time):
                    event.start_time = new_start_time
                    updated_fields.append('start_time')
            
            if end_time_str and end_time_str != 'None' and str(end_time_str).strip():
                try:
                    new_end_time = dt.strptime(str(end_time_str), '%H:%M:%S').time()
                except ValueError:
                    try:
                        new_end_time = dt.strptime(str(end_time_str), '%H:%M').time()
                    except ValueError:
                        new_end_time = None
                
                if new_end_time and (not event.end_time or event.end_time != new_end_time):
                    event.end_time = new_end_time
                    updated_fields.append('end_time')
            
            if event_data.get('start_location') and event_data.get('start_location') != event.start_location:
                event.start_location = event_data.get('start_location')
                updated_fields.append('start_location')
            
            if hasattr(Event, 'is_registration_required'):
                new_reg_required = event_data.get('is_registration_required', False)
                if event.is_registration_required != new_reg_required:
                    event.is_registration_required = new_reg_required
                    updated_fields.append('is_registration_required')
            
            if hasattr(Event, 'registration_url') and event_data.get('registration_url'):
                if event.registration_url != event_data.get('registration_url'):
                    event.registration_url = event_data.get('registration_url')
                    updated_fields.append('registration_url')
            
            if hasattr(Event, 'registration_info') and event_data.get('registration_info'):
                new_reg_info = event_data.get('registration_info')
                if not event.registration_info or event.registration_info != new_reg_info:
                    event.registration_info = new_reg_info
                    updated_fields.append('registration_info')
            
            if hasattr(Event, 'is_baby_friendly') and is_baby_friendly and not event.is_baby_friendly:
                event.is_baby_friendly = True
                updated_fields.append('is_baby_friendly')
            
            if updated_fields:
                app_logger.info(f"   ✅ Updated fields: {', '.join(updated_fields)}")
                db.session.commit()
                return event, False
            else:
                return event, False
        
        # Limit events per venue for non-exhibition event types
        if event_type and event_type != 'exhibition' and venue_id:
            current_count = venue_event_counts.get(venue_id, 0)
            if current_count >= max_events_per_venue:
                app_logger.info(f"⚠️ Skipped {event_type} event '{title}' - already saved {current_count} {event_type} events for venue {venue_id} (limit: {max_events_per_venue})")
                return None, False
            venue_event_counts[venue_id] = current_count + 1
        
        # Create new event
        event = Event()
        event.title = title
        event.description = event_data.get('description', '')
        event.event_type = event_type
        event.url = event_data.get('url', '')
        event.image_url = event_data.get('image_url', '')
        event.start_date = start_date
        
        end_date_str = event_data.get('end_date')
        if end_date_str:
            event.end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_time_str and start_time_str != 'None':
            try:
                event.start_time = dt.strptime(start_time_str, '%H:%M:%S').time()
            except ValueError:
                try:
                    event.start_time = dt.strptime(start_time_str, '%H:%M').time()
                except ValueError:
                    event.start_time = None
        
        if end_time_str and end_time_str != 'None':
            try:
                event.end_time = dt.strptime(end_time_str, '%H:%M:%S').time()
            except ValueError:
                try:
                    event.end_time = dt.strptime(end_time_str, '%H:%M').time()
                except ValueError:
                    event.end_time = None
        
        event.start_location = event_data.get('start_location', '')
        event.venue_id = venue_id
        event.city_id = city_id_event
        event.source = 'website'
        event.source_url = event_data.get('source_url', '')
        event.social_media_url = event_data.get('social_media_url', '')
        event.organizer = event_data.get('organizer', '')
        
        if hasattr(Event, 'is_registration_required'):
            event.is_registration_required = event_data.get('is_registration_required', False)
        if hasattr(Event, 'registration_url'):
            event.registration_url = event_data.get('registration_url')
        if hasattr(Event, 'registration_info'):
            event.registration_info = event_data.get('registration_info')
        if hasattr(Event, 'is_baby_friendly'):
            event.is_baby_friendly = is_baby_friendly
        
        db.session.add(event)
        db.session.commit()
        
        # Track exhibition count
        if event_type == 'exhibition' and venue_id:
            venue_exhibition_counts[venue_id] = venue_exhibition_counts.get(venue_id, 0) + 1
        
        app_logger.info(f"✅ Saved new event to database: '{title}'")
        return event, True
        
    except Exception as e:
        app_logger.error(f"Error saving event to database: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        db.session.rollback()
        return None, False

@app.route('/api/scrape-stream', methods=['POST'])
def trigger_scraping_stream():
    """Trigger scraping with Server-Sent Events (SSE) streaming for real-time event updates"""
    def generate():
        """Generator function that yields events as they are scraped"""
        # Ensure we're in app context
        with app.app_context():
            try:
                import json
                from datetime import datetime
                from scripts.venue_event_scraper import VenueEventScraper
                from scripts.source_event_scraper import SourceEventScraper
                
                # Get parameters from request
                data = request.get_json() or {}
                city_id = data.get('city_id')
                event_type = data.get('event_type', '')
                time_range = data.get('time_range', 'this_week')
                venue_ids = data.get('venue_ids', [])
                source_ids = data.get('source_ids', [])
                
                # Get city information
                if city_id:
                    city = db.session.get(City, city_id)
                    if not city:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'City not found'})}\n\n"
                        return
                    city_name = city.name
                else:
                    city_name = 'Washington DC'
                
                # Validate that at least one venue or source is selected
                if not venue_ids and not source_ids:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Please select at least one venue or source to scrape'})}\n\n"
                    return
                
                # Send initial progress
                scraping_summary = []
                if venue_ids:
                    scraping_summary.append(f'{len(venue_ids)} venues')
                if source_ids:
                    scraping_summary.append(f'{len(source_ids)} sources')
                
                yield f"data: {json.dumps({'type': 'progress', 'percentage': 10, 'message': f'Starting scraping for {city_name} ({", ".join(scraping_summary)})...'})}\n\n"
                
                events_saved = 0
                # Track exhibitions and events per venue for limits
                venue_exhibition_counts = {}
                venue_event_counts = {}
                max_events_per_venue = data.get('max_events_per_venue') or data.get('max_exhibitions_per_venue', 10)
                max_exhibitions_per_venue = data.get('max_exhibitions_per_venue', 5)
                
                # Scrape venues if any selected
                if venue_ids:
                    yield f"data: {json.dumps({'type': 'progress', 'percentage': 20, 'message': f'Scraping events from {len(venue_ids)} venues...'})}\n\n"
                
                try:
                    venue_scraper = VenueEventScraper()
                    max_events_per_venue = data.get('max_events_per_venue') or data.get('max_exhibitions_per_venue', 10)
                    max_exhibitions_per_venue = max_events_per_venue if event_type == 'exhibition' or not event_type else max_events_per_venue
                    
                    # Get venues
                    if venue_ids:
                        venues = Venue.query.filter(Venue.id.in_(venue_ids)).all()
                    else:
                        venues = Venue.query.filter_by(city_id=city_id).all()
                    
                    # Filter active venues
                    active_venues = []
                    for venue in venues:
                        if 'newseum' in venue.name.lower():
                            continue
                        if not venue.website_url or 'example.com' in venue.website_url:
                            continue
                        active_venues.append(venue)
                    
                    venues = active_venues
                    total_venues = len(venues)
                    
                    for idx, venue in enumerate(venues):
                        try:
                            # Update progress
                            progress = 20 + int((idx / total_venues) * 30)
                            yield f"data: {json.dumps({'type': 'progress', 'percentage': progress, 'message': f'Scraping {venue.name}...', 'venue_name': venue.name})}\n\n"
                            
                            # Scrape venue
                            events = venue_scraper._scrape_venue_website(
                                venue, 
                                event_type=event_type, 
                                time_range=time_range, 
                                max_exhibitions_per_venue=max_exhibitions_per_venue,
                                max_events_per_venue=max_events_per_venue
                            )
                            
                            # Filter by event_type if specified
                            if event_type:
                                events = [e for e in events if e.get('event_type', '').lower() == event_type.lower()]
                            
                            # Filter by time_range
                            events = venue_scraper._filter_by_time_range(events, time_range)
                            
                            # Limit events per venue
                            if event_type and event_type.lower() == 'exhibition':
                                exhibition_events = [e for e in events if e.get('event_type') == 'exhibition']
                                other_events = [e for e in events if e.get('event_type') != 'exhibition']
                                if len(exhibition_events) > max_exhibitions_per_venue:
                                    events = exhibition_events[:max_exhibitions_per_venue] + other_events
                            else:
                                if len(events) > max_events_per_venue:
                                    events = events[:max_events_per_venue]
                            
                            # Prepare events for batch processing with shared handler
                            venue_events = []
                            for event_data in events:
                                # Ensure city_id is set
                                event_data['city_id'] = city_id
                                event_data['venue_id'] = venue.id
                                event_data['organizer'] = venue.name
                                event_data['source_url'] = venue.website_url or ''
                                venue_events.append(event_data)
                            
                            # Process events using shared handler
                            if venue_events:
                                from scripts.event_database_handler import create_events_in_database as shared_create_events
                                
                                def generic_event_processor(event_data):
                                    """Add generic scraper-specific fields"""
                                    event_data['source'] = 'website'
                                    if not event_data.get('organizer'):
                                        event_data['organizer'] = venue.name
                                
                                created, updated, skipped = shared_create_events(
                                    events=venue_events,
                                    venue_id=venue.id,
                                    city_id=venue.city_id,
                                    venue_name=venue.name,
                                    db=db,
                                    Event=Event,
                                    Venue=Venue,
                                    batch_size=5,
                                    logger_instance=app_logger,
                                    source_url=venue.website_url,
                                    custom_event_processor=generic_event_processor
                                )
                                
                                # Query saved events to stream them
                                # Get events that were just created/updated (by title and venue)
                                event_titles = [e.get('title') for e in venue_events if e.get('title')]
                                if event_titles:
                                    saved_events = Event.query.filter(
                                        Event.venue_id == venue.id,
                                        Event.title.in_(event_titles)
                                    ).all()
                                    
                                    # Stream saved events
                                    for saved_event in saved_events:
                                        event_dict = {
                                            'id': saved_event.id,
                                            'title': saved_event.title,
                                            'description': saved_event.description or '',
                                            'start_date': saved_event.start_date.isoformat() if saved_event.start_date else None,
                                            'end_date': saved_event.end_date.isoformat() if saved_event.end_date else None,
                                            'start_time': saved_event.start_time.strftime('%H:%M:%S') if saved_event.start_time else None,
                                            'end_time': saved_event.end_time.strftime('%H:%M:%S') if saved_event.end_time else None,
                                            'url': saved_event.url or '',
                                            'event_type': saved_event.event_type,
                                            'venue_id': saved_event.venue_id,
                                            'venue_name': venue.name,
                                            'image_url': saved_event.image_url or '',
                                            'is_baby_friendly': getattr(saved_event, 'is_baby_friendly', False),
                                            'start_location': saved_event.start_location or ''
                                        }
                                        yield f"data: {json.dumps({'type': 'event', 'event': event_dict})}\n\n"
                                        events_saved += 1
                            
                        except Exception as e:
                            app_logger.error(f"Error scraping venue {venue.name}: {e}")
                            import traceback
                            app_logger.error(f"Traceback: {traceback.format_exc()}")
                            yield f"data: {json.dumps({'type': 'error', 'message': f'Error scraping {venue.name}: {str(e)}'})}\n\n"
                            continue
                    
                except Exception as e:
                    app_logger.error(f"Error in venue scraping: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Error scraping venues: {str(e)}'})}\n\n"
                
                # Scrape sources if any selected
                if source_ids:
                    yield f"data: {json.dumps({'type': 'progress', 'percentage': 60, 'message': f'Scraping events from {len(source_ids)} sources...'})}\n\n"
                    
                    try:
                        source_scraper = SourceEventScraper()
                        sources = Source.query.filter(Source.id.in_(source_ids)).all()
                        total_sources = len(sources)
                        
                        for idx, source in enumerate(sources):
                            try:
                                # Update progress
                                progress = 60 + int((idx / total_sources) * 30)
                                yield f"data: {json.dumps({'type': 'progress', 'percentage': progress, 'message': f'Scraping {source.name}...', 'source_name': source.name})}\n\n"
                                
                                # Scrape source
                                source_events = source_scraper.scrape_source_events(
                                    source_ids=[source.id],
                                    city_id=city_id,
                                    event_type=event_type,
                                    time_range=time_range
                                )
                                
                                # Filter by event_type if specified
                                if event_type:
                                    source_events = [e for e in source_events if e.get('event_type', '').lower() == event_type.lower()]
                                
                                # Filter by time_range
                                source_events = source_scraper._filter_by_time_range(source_events, time_range) if hasattr(source_scraper, '_filter_by_time_range') else source_events
                                
                                # Group source events by venue_id for batch processing
                                source_events_by_venue = {}
                                for event_data in source_events:
                                    # Ensure city_id is set
                                    event_data['city_id'] = city_id
                                    event_data['source'] = 'source'
                                    event_data['source_url'] = source.url or ''
                                    event_data['organizer'] = source.name
                                    
                                    venue_id = event_data.get('venue_id')
                                    if not venue_id:
                                        # Skip events without venue_id (shared handler requires it)
                                        app_logger.warning(f"⚠️ Skipping source event '{event_data.get('title', 'Unknown')}': missing venue_id")
                                        continue
                                    
                                    if venue_id not in source_events_by_venue:
                                        source_events_by_venue[venue_id] = []
                                    source_events_by_venue[venue_id].append(event_data)
                                
                                # Process source events by venue using shared handler
                                for venue_id, venue_source_events in source_events_by_venue.items():
                                    try:
                                        venue = db.session.get(Venue, venue_id)
                                        if not venue:
                                            app_logger.warning(f"⚠️ Skipping {len(venue_source_events)} source events: venue_id {venue_id} not found")
                                            continue
                                        
                                        from scripts.event_database_handler import create_events_in_database as shared_create_events
                                        
                                        def source_event_processor(event_data):
                                            """Add source-specific fields"""
                                            event_data['source'] = 'source'
                                            if not event_data.get('organizer'):
                                                event_data['organizer'] = source.name
                                        
                                        created, updated, skipped = shared_create_events(
                                            events=venue_source_events,
                                            venue_id=venue.id,
                                            city_id=venue.city_id,
                                            venue_name=venue.name,
                                            db=db,
                                            Event=Event,
                                            Venue=Venue,
                                            batch_size=5,
                                            logger_instance=app_logger,
                                            source_url=source.url,
                                            custom_event_processor=source_event_processor
                                        )
                                        
                                        # Query saved events to stream them
                                        event_titles = [e.get('title') for e in venue_source_events if e.get('title')]
                                        if event_titles:
                                            saved_events = Event.query.filter(
                                                Event.venue_id == venue.id,
                                                Event.title.in_(event_titles)
                                            ).all()
                                            
                                            # Stream saved events
                                            for saved_event in saved_events:
                                                event_dict = {
                                                    'id': saved_event.id,
                                                    'title': saved_event.title,
                                                    'description': saved_event.description or '',
                                                    'start_date': saved_event.start_date.isoformat() if saved_event.start_date else None,
                                                    'end_date': saved_event.end_date.isoformat() if saved_event.end_date else None,
                                                    'start_time': saved_event.start_time.strftime('%H:%M:%S') if saved_event.start_time else None,
                                                    'end_time': saved_event.end_time.strftime('%H:%M:%S') if saved_event.end_time else None,
                                                    'url': saved_event.url or '',
                                                    'event_type': saved_event.event_type,
                                                    'venue_id': saved_event.venue_id,
                                                    'venue_name': saved_event.venue.name if saved_event.venue else '',
                                                    'image_url': saved_event.image_url or '',
                                                    'is_baby_friendly': getattr(saved_event, 'is_baby_friendly', False),
                                                    'start_location': saved_event.start_location or ''
                                                }
                                                yield f"data: {json.dumps({'type': 'event', 'event': event_dict})}\n\n"
                                                events_saved += 1
                                        
                                    except Exception as e:
                                        app_logger.error(f"Error processing source events for venue_id {venue_id}: {e}")
                                        import traceback
                                        app_logger.error(traceback.format_exc())
                                        continue
                                
                            except Exception as e:
                                app_logger.error(f"Error scraping source {source.name}: {e}")
                                yield f"data: {json.dumps({'type': 'error', 'message': f'Error scraping {source.name}: {str(e)}'})}\n\n"
                                continue
                    
                    except Exception as e:
                        app_logger.error(f"Error in source scraping: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Error scraping sources: {str(e)}'})}\n\n"
                
                # Send completion message
                yield f"data: {json.dumps({'type': 'complete', 'total_events': events_saved, 'message': f'Scraping complete! Found {events_saved} events.'})}\n\n"
                
            except Exception as e:
                app_logger.error(f"Error in streaming scraper: {e}")
                import traceback
                app_logger.error(traceback.format_exc())
                yield f"data: {json.dumps({'type': 'error', 'message': f'Scraping error: {str(e)}'})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'  # Disable buffering in nginx
    })

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
                            city = db.session.get(City, city_id)
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
    import signal
    import sys
    from requests.exceptions import Timeout, ConnectionError, RequestException
    
    # Note: Signal handling doesn't prevent gunicorn timeouts, but we'll handle exceptions
    # The real fix is shorter timeouts per venue (10s) to prevent worker hangs
    
    try:
        import json
        from datetime import datetime
        from scripts.venue_event_scraper import VenueEventScraper
        from scripts.source_event_scraper import SourceEventScraper
        
        # Get parameters from request
        data = request.get_json() or {}
        city_id = data.get('city_id')
        event_type = data.get('event_type', '')
        time_range = data.get('time_range', 'this_week')
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
        
        # Validate that at least one venue or source is selected
        if not venue_ids and not source_ids:
            return jsonify({
                'error': 'Please select at least one venue or source to scrape'
            }), 400
        
        # Initialize progress tracking
        scraping_summary = []
        if venue_ids:
            scraping_summary.append(f'{len(venue_ids)} venues')
        if source_ids:
            scraping_summary.append(f'{len(source_ids)} sources')
        
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 10,
            'message': f'Starting scraping for {city_name} ({", ".join(scraping_summary)})...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'venues_processed': 0,
            'total_venues': len(venue_ids),
            'sources_processed': 0,
            'total_sources': len(source_ids),
            'current_venue': None,
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Step 1: Scrape from venues and sources
        all_events = []
        
        # Scrape venues if any selected
        if venue_ids:
            progress_data.update({
                'current_step': 2,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 20,
                'message': f'Scraping events from {len(venue_ids)} venues...'
            })
            
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            
            try:
                venue_scraper = VenueEventScraper()
                # Get max_events_per_venue from request (default: 10), fallback to max_exhibitions_per_venue for backward compatibility
                max_events_per_venue = data.get('max_events_per_venue') or data.get('max_exhibitions_per_venue', 10)
                app_logger.info(f"📊 Backend: Received max_events_per_venue={max_events_per_venue} from request (raw: {data.get('max_events_per_venue')}, fallback: {data.get('max_exhibitions_per_venue')})")
                # For exhibitions, use the same limit
                max_exhibitions_per_venue = max_events_per_venue if event_type == 'exhibition' or not event_type else max_events_per_venue
                # Update progress before scraping
                progress_data.update({
                    'current_step': 2,
                    'total_steps': 3,  # Ensure total_steps is always included
                    'percentage': 20,
                    'message': f'Scraping events from {len(venue_ids)} venues...',
                    'events_found': 0,
                    'venues_processed': 0
                })
                with open('scraping_progress.json', 'w') as f:
                    json.dump(progress_data, f)
                
                venue_events = venue_scraper.scrape_venue_events(
                    city_id=city_id,
                    event_type=event_type,
                    time_range=time_range,
                    venue_ids=venue_ids,
                    max_exhibitions_per_venue=max_exhibitions_per_venue,
                    max_events_per_venue=max_events_per_venue
                )
                all_events.extend(venue_events)
                
                # Update progress after scraping
                progress_data.update({
                    'current_step': 2,
                    'total_steps': 3,  # Ensure total_steps is always included
                    'events_found': len(venue_events),
                    'events_saved': 0,  # Reset saved count, will update during saving
                    'venues_processed': len(venue_ids),
                    'percentage': 50,
                    'message': f'Found {len(venue_events)} events from {len(venue_ids)} venues. Saving to database...'
                })
                with open('scraping_progress.json', 'w') as f:
                    json.dump(progress_data, f)
                
                app_logger.info(f"Scraped {len(venue_events)} events from venues")
            except (ConnectionError, Timeout, Exception) as e:
                app_logger.error(f"Error scraping venues: {type(e).__name__}: {e}")
                import traceback
                app_logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue with empty list rather than failing completely
                all_events.extend([])
            except SystemExit:
                # Prevent gunicorn worker from exiting on connection errors
                app_logger.error("SystemExit caught in scraping - preventing worker crash")
                all_events.extend([])
        
        # Scrape sources if any selected
        if source_ids:
            progress_data.update({
                'current_step': 2,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 50,
                'message': f'Scraping events from {len(source_ids)} sources...'
            })
            
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            
            source_scraper = SourceEventScraper()
            source_events = source_scraper.scrape_source_events(
                source_ids=source_ids,
                city_id=city_id,
                event_type=event_type,
                time_range=time_range
            )
            all_events.extend(source_events)
            app_logger.info(f"Scraped {len(source_events)} events from sources")
            
            # Update progress after source scraping
            progress_data.update({
                'current_step': 2,
                'total_steps': 3,  # Ensure total_steps is always included
                'events_found': len(all_events),
                'sources_processed': len(source_ids),
                'percentage': 50,
                'message': f'Found {len(all_events)} total events. Processing...'
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        
        # Final deduplication across all scraped events
        # For exhibitions, use URL + title to deduplicate across venues with same website
        unique_events = {}
        venue_websites = {}  # Cache venue_id -> website_url mapping
        
        for event in all_events:
            title_clean = event.get('title', '').lower().strip()
            date_key = event.get('start_time', '')[:10] if event.get('start_time') else ''
            venue_id = event.get('venue_id')
            event_type = event.get('event_type', 'tour')
            event_url = event.get('url', '').lower().strip()
            
            # For exhibitions, deduplicate by title + URL across venues with same website
            if event_type == 'exhibition' and venue_id and event_url:
                # Get venue website (with caching)
                if venue_id not in venue_websites:
                    venue = db.session.get(Venue, venue_id)
                    venue_websites[venue_id] = venue.website_url.lower().strip() if venue and venue.website_url else ''
                
                website = venue_websites[venue_id]
                # Use title + URL + website as key to prevent duplicates across duplicate venues
                event_key = f"exhibition_{title_clean}_{event_url}_{website}"
            else:
                # For other events, use venue_id as before
                location_key = venue_id or event.get('source_id', '')
                event_key = f"{title_clean}_{date_key}_{location_key}"
            
            if event_key not in unique_events:
                unique_events[event_key] = event
        
        events_scraped = list(unique_events.values())
        app_logger.info(f"After deduplication: {len(events_scraped)} unique events (removed {len(all_events) - len(events_scraped)} duplicates)")
        app_logger.info(f"Total events scraped: {len(events_scraped)}")
        
        # Update progress after deduplication
        progress_data.update({
            'current_step': 2,
            'total_steps': 3,  # Ensure total_steps is always included
            'events_found': len(events_scraped),
            'percentage': 60,
            'message': f'Found {len(events_scraped)} unique events after deduplication. Preparing to save...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Save scraped events to file for loading
        scraped_data = {
            "metadata": {
                "scraped_at": datetime.utcnow().isoformat() + 'Z',
                "total_events": len(events_scraped),
                "scraper_version": "3.0",
                "venue_ids": venue_ids,
                "source_ids": source_ids,
                "city_id": city_id,
                "event_type": event_type
            },
            "events": events_scraped
        }
        
        with open('dc_scraped_data.json', 'w') as f:
            json.dump(scraped_data, f, indent=2)
        
        # Step 2: Load events into database using shared handler (batch by venue)
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 70,
            'message': f'Loading {len(events_scraped)} events into database...',
            'events_found': len(events_scraped),
            'events_saved': 0  # Reset saved count, will update during saving
        })
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import shared handler
        from scripts.event_database_handler import create_events_in_database as shared_create_events
        
        # Group events by venue_id for batch processing
        events_by_venue = {}
        for event_data in events_scraped:
            venue_id = event_data.get('venue_id')
            if not venue_id:
                app_logger.warning(f"⚠️ Skipping event '{event_data.get('title', 'Unknown')}': missing venue_id")
                continue
            
            if venue_id not in events_by_venue:
                events_by_venue[venue_id] = []
            events_by_venue[venue_id].append(event_data)
        
        # Process events by venue using shared handler
        total_created = 0
        total_updated = 0
        total_skipped = 0
        
        for venue_id, venue_events in events_by_venue.items():
            try:
                # Get venue info
                venue = db.session.get(Venue, venue_id)
                if not venue:
                    app_logger.warning(f"⚠️ Skipping {len(venue_events)} events: venue_id {venue_id} not found")
                    continue
                
                app_logger.info(f"📊 Processing {len(venue_events)} events for venue: {venue.name} (ID: {venue_id})")
                
                # Custom processor for generic scraper events
                def generic_event_processor(event_data):
                    """Add generic scraper-specific fields"""
                    event_data['source'] = 'website'
                    if not event_data.get('organizer'):
                        event_data['organizer'] = venue.name
                    if not event_data.get('source_url'):
                        event_data['source_url'] = venue.website_url or ''
                
                # Use shared handler for all common logic
                created, updated, skipped = shared_create_events(
                    events=venue_events,
                    venue_id=venue.id,
                    city_id=venue.city_id,
                    venue_name=venue.name,
                    db=db,
                    Event=Event,
                    Venue=Venue,
                    batch_size=5,
                    logger_instance=app_logger,
                    source_url=venue.website_url,
                    custom_event_processor=generic_event_processor
                )
                
                total_created += created
                total_updated += updated
                total_skipped += skipped
                
                # Update progress
                events_loaded = total_created + total_updated
                progress_data.update({
                    'current_step': 3,
                    'total_steps': 3,
                    'events_found': len(events_scraped),
                    'events_saved': events_loaded,
                    'percentage': min(70 + int((events_loaded / max(len(events_scraped), 1)) * 20), 90),
                    'message': f'Saving events to database... ({events_loaded}/{len(events_scraped)})'
                })
                with open('scraping_progress.json', 'w') as f:
                    json.dump(progress_data, f)
                
            except Exception as e:
                app_logger.error(f"❌ Error processing events for venue_id {venue_id}: {e}")
                import traceback
                app_logger.error(traceback.format_exc())
                continue
        
        # Events are already committed by shared handler in batches
        events_loaded = total_created + total_updated
        app_logger.info(f"✅ Successfully processed events: {total_created} created, {total_updated} updated, {total_skipped} skipped")
        
        # Step 3: Complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'Scraping complete! Found {len(events_scraped)} events, saved {events_loaded} to database.',
            'events_found': len(events_scraped),
            'events_saved': events_loaded
        })
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"Scraping completed: {events_loaded} events added")
        
        return jsonify({
            'message': f'Scraping completed successfully for {city_name}',
            'events_added': events_loaded,
            'city': city_name,
            'event_type': event_type,
            'time_range': time_range,
            'venue_count': len(venue_ids),
            'source_count': len(source_ids),
            'total_scraped': len(venue_ids) + len(source_ids)
        })
        
    except SystemExit:
        # Prevent gunicorn worker from exiting on connection errors
        app_logger.error("SystemExit caught in scraping - preventing worker crash")
        return jsonify({
            'error': 'Scraping failed due to connection error',
            'details': 'Network connection error occurred. Please try again.'
        }), 500
    except (ConnectionError, Timeout, RequestException) as e:
        app_logger.error(f"Network error during scraping: {type(e).__name__}: {e}")
        return jsonify({
            'error': 'Scraping failed due to network error',
            'details': str(e)
        }), 500
    except Exception as e:
        app_logger.error(f"Scraping error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Scraping failed',
            'details': str(e)
        }), 500
    finally:
        # Cleanup if needed
        pass

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

@app.route('/admin/vipassana')
@login_required
def admin_vipassana():
    """Vipassana scraper admin page with separate database"""
    return render_template('admin/vipassana.html', session=session)


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

@app.route('/api/debug-eventbrite-token')
def debug_eventbrite_token():
    """Debug Eventbrite API token configuration (does not expose token value)"""
    import os
    try:
        eventbrite_token = os.getenv('EVENTBRITE_API_TOKEN') or os.getenv('EVENTBRITE_PRIVATE_TOKEN')
        all_env_vars = dict(os.environ)
        eventbrite_vars = {k: '***SET***' if v else 'NOT SET' for k, v in all_env_vars.items() if 'EVENTBRITE' in k.upper()}
        
        return jsonify({
            'token_set': bool(eventbrite_token),
            'token_length': len(eventbrite_token) if eventbrite_token else 0,
            'token_preview': f"{eventbrite_token[:10]}..." if eventbrite_token and len(eventbrite_token) > 10 else None,
            'eventbrite_env_vars': eventbrite_vars,
            'checking_vars': ['EVENTBRITE_API_TOKEN', 'EVENTBRITE_PRIVATE_TOKEN'],
            'EVENTBRITE_API_TOKEN_set': bool(os.getenv('EVENTBRITE_API_TOKEN')),
            'EVENTBRITE_PRIVATE_TOKEN_set': bool(os.getenv('EVENTBRITE_PRIVATE_TOKEN'))
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
    """Get admin statistics - always returns fresh counts from database"""
    try:
        # Expire all objects to ensure fresh queries (no caching)
        db.session.expire_all()
        
        # Use direct SQL queries to bypass any SQLAlchemy caching
        from sqlalchemy import text
        
        cities_count = db.session.execute(text("SELECT COUNT(*) FROM cities")).scalar()
        venues_count = db.session.execute(text("SELECT COUNT(*) FROM venues")).scalar()
        sources_count = db.session.execute(text("SELECT COUNT(*) FROM sources")).scalar()
        
        # Try to count events, but handle case where is_online column might not exist yet
        try:
            # Use direct SQL to get accurate count and avoid caching
            events_count = db.session.execute(text("SELECT COUNT(*) FROM events")).scalar()
        except Exception as event_error:
            app_logger.warning(f"Error counting events (possibly missing is_online column): {event_error}")
            # Try to add the column if it doesn't exist
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns('events')]
                if 'is_online' not in columns:
                    app_logger.info("Adding is_online column to events table...")
                    with db.engine.connect() as conn:
                        conn.execute(db.text("ALTER TABLE events ADD COLUMN is_online BOOLEAN DEFAULT 0"))
                        conn.commit()
                    app_logger.info("Successfully added is_online column")
                    events_count = Event.query.count()
                else:
                    # Column exists but query still failed, return 0
                    events_count = 0
            except Exception as migration_error:
                app_logger.error(f"Error adding is_online column: {migration_error}")
                events_count = 0
        
        app_logger.info(f"Stats (fresh SQL queries): cities={cities_count}, venues={venues_count}, events={events_count}, sources={sources_count}")
        
        return jsonify({
            'cities': cities_count,
            'venues': venues_count,
            'events': events_count,
            'sources': sources_count
        })
    except Exception as e:
        app_logger.error(f"Error getting admin stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'cities': 0,
            'venues': 0,
            'events': 0,
            'sources': 0,
            'error': str(e)
        }), 500

@app.route('/api/admin/cities')
def admin_cities():
    """Get all cities for admin, sorted by most recently updated (most recent first)"""
    try:
        cities = City.query.order_by(City.updated_at.desc()).all()
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
        # Sort by most recently updated first, then by created_at descending, then by ID descending as tiebreakers
        # Use NULLS LAST to ensure NULL updated_at values appear at the end (PostgreSQL default behavior)
        # Note: updated_at defaults to created_at on creation, so we use created_at as secondary sort
        from sqlalchemy import desc, nulls_last
        venues = Venue.query.order_by(
            nulls_last(desc(Venue.updated_at)), 
            desc(Venue.created_at),
            desc(Venue.id)
        ).all()
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

@app.route('/api/admin/migrate-venues-schema', methods=['GET', 'POST'])
def migrate_venues_schema_endpoint():
    """Public endpoint to migrate venues schema (for emergency fixes) - accepts GET or POST"""
    try:
        success, message, added_columns = migrate_venues_schema()
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'added_columns': added_columns or []
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/migrate-schema', methods=['POST'])
@login_required
def migrate_schema():
    """Manually trigger schema migration for events and venues tables"""
    try:
        # Migrate events table
        success, message, added_columns = migrate_events_schema()
        events_message = message
        
        # Migrate venues table
        venues_success, venues_message, venues_columns = migrate_venues_schema()
        
        if success and venues_success:
            return jsonify({
                'success': True,
                'message': f'Events: {events_message}. Venues: {venues_message}',
                'added_columns': (added_columns or []) + (venues_columns or [])
            })
        else:
            error_msg = f'Events: {events_message}. Venues: {venues_message}'
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events')
def admin_events():
    """Get all events for admin, sorted by most recently updated (most recent first)"""
    try:
        events = Event.query.order_by(Event.updated_at.desc()).all()
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
        error_str = str(e)
        # If error is due to missing columns, try to migrate and retry
        if 'does not exist' in error_str or 'UndefinedColumn' in error_str:
            try:
                success, message, _ = migrate_events_schema()
                if success:
                    # Retry the query after migration
                    events = Event.query.order_by(Event.updated_at.desc()).all()
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
            except Exception as migration_error:
                return jsonify({
                    'error': f'Query failed and migration failed: {error_str}. Migration error: {str(migration_error)}'
                }), 500
        
        return jsonify({'error': error_str}), 500

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
        
        # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
        from scripts.utils import is_category_heading
        if is_category_heading(title):
            return jsonify({'error': f'Invalid title: "{title}" is a category heading, not an event title'}), 400
        
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
        
        # Skip category headings (already validated above, but double-check)
        if is_category_heading(title):
            return jsonify({'error': f'Invalid title: "{title}" is a category heading, not an event title'}), 400
        
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
            artists=data.get('artists', '').strip(),
            exhibition_type=data.get('exhibition_type', '').strip(),
            collection_period=data.get('collection_period', '').strip(),
            number_of_artworks=data.get('number_of_artworks'),
            opening_reception_date=datetime.strptime(data['opening_reception_date'], '%Y-%m-%d').date() if data.get('opening_reception_date') else None,
            opening_reception_time=datetime.strptime(data['opening_reception_time'], '%H:%M').time() if data.get('opening_reception_time') else None,
            is_permanent=data.get('is_permanent', False),
            related_exhibitions=data.get('related_exhibitions', '').strip(),
            
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

@app.route('/api/admin/update-cities-json', methods=['POST'])
def update_cities_json_from_db():
    """Update cities.json file directly from database (for syncing production changes)"""
    try:
        from scripts.update_cities_json import update_cities_json
        
        success = update_cities_json()
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully updated data/cities.json from database'
            })
        else:
            return jsonify({'error': 'Failed to update cities.json'}), 500
            
    except Exception as e:
        app_logger.error(f"Error updating cities.json: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-venues-json', methods=['POST'])
def update_venues_json_from_db():
    """Update venues.json file directly from database (for syncing production changes)"""
    try:
        from scripts.update_venues_json import update_venues_json
        
        success = update_venues_json()
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully updated data/venues.json from database'
            })
        else:
            return jsonify({'error': 'Failed to update venues.json'}), 500
            
    except Exception as e:
        app_logger.error(f"Error updating venues.json: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-sources-json', methods=['POST'])
def update_sources_json_from_db():
    """Update sources.json file directly from database (for syncing production changes)"""
    try:
        from scripts.update_sources_json import update_sources_json
        
        success = update_sources_json()
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully updated data/sources.json from database'
            })
        else:
            return jsonify({'error': 'Failed to update sources.json'}), 500
            
    except Exception as e:
        app_logger.error(f"Error updating sources.json: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-all-json', methods=['POST'])
def update_all_json_from_db():
    """Update all JSON files (cities, venues, sources) from database"""
    try:
        from scripts.update_cities_json import update_cities_json
        from scripts.update_venues_json import update_venues_json
        from scripts.update_sources_json import update_sources_json
        
        results = {
            'cities': update_cities_json(),
            'venues': update_venues_json(),
            'sources': update_sources_json()
        }
        
        all_success = all(results.values())
        
        return jsonify({
            'success': all_success,
            'message': 'Updated JSON files from database',
            'results': results
        })
            
    except Exception as e:
        app_logger.error(f"Error updating JSON files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/clean-duplicates', methods=['POST'])
def clean_duplicate_events():
    """Remove duplicate events from database"""
    try:
        from sqlalchemy import func
        
        app_logger.info("🧹 Cleaning duplicate events from database...")
        
        # Find duplicates based on title, venue_id, city_id, start_date
        duplicates = db.session.query(
            Event.title,
            Event.venue_id,
            Event.city_id,
            Event.start_date,
            func.count(Event.id).label('count')
        ).group_by(
            Event.title,
            Event.venue_id,
            Event.city_id,
            Event.start_date
        ).having(func.count(Event.id) > 1).all()
        
        total_duplicates = 0
        for duplicate in duplicates:
            title, venue_id, city_id, start_date, count = duplicate
            
            # Keep the first event, delete the rest
            events_to_keep = Event.query.filter_by(
                title=title,
                venue_id=venue_id,
                city_id=city_id,
                start_date=start_date
            ).order_by(Event.id).limit(1).all()
            
            events_to_delete = Event.query.filter_by(
                title=title,
                venue_id=venue_id,
                city_id=city_id,
                start_date=start_date
            ).order_by(Event.id).offset(1).all()
            
            for event in events_to_delete:
                db.session.delete(event)
                total_duplicates += 1
        
        db.session.commit()
        app_logger.info(f"✅ Removed {total_duplicates} duplicate events")
        
        return jsonify({
            'message': f'Successfully removed {total_duplicates} duplicate events',
            'duplicates_removed': total_duplicates
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error cleaning duplicates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reload-cities', methods=['POST'])
def reload_cities_from_json():
    """Reload cities from cities.json into database - preserves existing cities to avoid breaking events/venues/sources"""
    try:
        import json
        from pathlib import Path
        
        app_logger.info("🔄 Reloading cities from cities.json...")
        
        cities_file = Path("data/cities.json")
        if not cities_file.exists():
            return jsonify({'error': 'cities.json not found'}), 404
        
        with open(cities_file, 'r') as f:
            data = json.load(f)
        
        cities_data = data.get('cities', data)
        if not cities_data:
            return jsonify({'error': 'No cities found in cities.json'}), 404
        total_cities = len(cities_data)
        
        app_logger.info(f"📊 Found {total_cities} cities in JSON")
        
        # Get existing cities by name (case-insensitive) to preserve IDs
        existing_cities = {}
        for city in City.query.all():
            # Use lowercase name as key for case-insensitive matching
            key = f"{city.name.lower()}|{city.state or ''}|{city.country or ''}"
            existing_cities[key] = city
        
        app_logger.info(f"📍 Found {len(existing_cities)} existing cities in database")
        
        # Process cities from JSON
        cities_updated = 0
        cities_added = 0
        cities_skipped = 0
        
        for city_id, city_info in cities_data.items():
            try:
                city_name = city_info.get('name', '').strip()
                city_state = city_info.get('state', '').strip()
                city_country = city_info.get('country', '').strip()
                city_timezone = city_info.get('timezone', 'UTC')
                
                if not city_name:
                    app_logger.warning(f"Skipping city with no name: {city_info}")
                    cities_skipped += 1
                    continue
                
                # Create key for matching (case-insensitive)
                key = f"{city_name.lower()}|{city_state}|{city_country}"
                
                # Check if city already exists
                existing_city = existing_cities.get(key)
                
                if existing_city:
                    # Update existing city (preserve ID to keep events/venues/sources linked)
                    existing_city.name = city_name
                    existing_city.state = city_state
                    existing_city.country = city_country
                    existing_city.timezone = city_timezone
                    cities_updated += 1
                    app_logger.debug(f"Updated city: {city_name} (ID: {existing_city.id})")
                else:
                    # Add new city
                    new_city = City(
                        name=city_name,
                        country=city_country,
                        state=city_state,
                        timezone=city_timezone
                    )
                    db.session.add(new_city)
                    cities_added += 1
                    app_logger.debug(f"Added new city: {city_name}")
                    
            except Exception as e:
                app_logger.error(f"Error processing city {city_info.get('name')}: {e}")
                cities_skipped += 1
                continue
        
        db.session.commit()
        app_logger.info(f"✅ Successfully processed cities: {cities_updated} updated, {cities_added} added, {cities_skipped} skipped")
        
        return jsonify({
            'message': f'Successfully reloaded cities',
            'cities_updated': cities_updated,
            'cities_added': cities_added,
            'cities_skipped': cities_skipped,
            'total_cities': cities_updated + cities_added
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error reloading cities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/fix-column-sizes', methods=['POST'])
def fix_column_sizes():
    """Fix column sizes for long URLs - needed for Railway PostgreSQL"""
    try:
        app_logger.info("🔧 Fixing column sizes for long URLs...")
        
        # Check if we're on PostgreSQL (Railway)
        if 'postgresql' in str(db.engine.url):
            from sqlalchemy import text
            
            # Alter column sizes
            alterations = [
                "ALTER TABLE venues ALTER COLUMN image_url TYPE VARCHAR(1000)",
                "ALTER TABLE events ALTER COLUMN image_url TYPE VARCHAR(1000)",
                "ALTER TABLE events ALTER COLUMN url TYPE VARCHAR(1000)",
                "ALTER TABLE events ALTER COLUMN source_url TYPE VARCHAR(1000)"
            ]
            
            for sql in alterations:
                try:
                    db.session.execute(text(sql))
                    app_logger.info(f"✅ Executed: {sql}")
                except Exception as e:
                    app_logger.warning(f"⚠️ Could not execute {sql}: {e}")
            
            db.session.commit()
            app_logger.info("✅ Column sizes updated successfully")
            
            return jsonify({
                'message': 'Column sizes updated successfully',
                'database_type': 'PostgreSQL'
            })
        else:
            return jsonify({
                'message': 'No changes needed - SQLite does not enforce string lengths',
                'database_type': 'SQLite'
            })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error fixing column sizes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/load-all-data', methods=['POST'])
def load_all_data_to_database():
    """Load all data (cities, venues, sources) from JSON files into database"""
    try:
        import json
        from pathlib import Path
        from datetime import datetime
        
        app_logger.info("🚀 Loading all data from JSON files...")
        
        # Step 1: Create tables if they don't exist
        try:
            db.create_all()
            # Explicitly create visits table if it doesn't exist (for SQLite)
            if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
                from sqlalchemy import inspect
                inspector = db.inspect(db.engine)
                if 'visits' not in inspector.get_table_names():
                    Visit.__table__.create(db.engine)
            app_logger.info("✅ Database tables created/verified")
        except Exception as e:
            app_logger.error(f"Error creating tables: {e}")
            return jsonify({'error': f'Table creation failed: {str(e)}'}), 500
        
        # Step 2: Load cities
        cities_file = Path("data/cities.json")
        if not cities_file.exists():
            return jsonify({'error': 'cities.json not found'}), 404
        
        with open(cities_file, 'r') as f:
            cities_data = json.load(f)
        
        cities_json = cities_data.get('cities', {})
        app_logger.info(f"📊 Found {len(cities_json)} cities in JSON")
        
        # Get existing cities by name (case-insensitive) to preserve IDs and avoid breaking events/venues/sources
        existing_cities = {}
        for city in City.query.all():
            # Use lowercase name as key for case-insensitive matching
            key = f"{city.name.lower()}|{city.state or ''}|{city.country or ''}"
            existing_cities[key] = city
        
        app_logger.info(f"📍 Found {len(existing_cities)} existing cities in database")
        
        # Process cities from JSON (update existing, add new)
        cities_updated = 0
        cities_added = 0
        cities_skipped = 0
        
        for city_id, city_info in cities_json.items():
            try:
                city_name = city_info.get('name', '').strip()
                city_state = city_info.get('state', '').strip()
                city_country = city_info.get('country', '').strip()
                city_timezone = city_info.get('timezone', 'UTC')
                
                if not city_name:
                    app_logger.warning(f"Skipping city with no name: {city_info}")
                    cities_skipped += 1
                    continue
                
                # Create key for matching (case-insensitive)
                key = f"{city_name.lower()}|{city_state}|{city_country}"
                
                # Check if city already exists
                existing_city = existing_cities.get(key)
                
                if existing_city:
                    # Update existing city (preserve ID to keep events/venues/sources linked)
                    existing_city.name = city_name
                    existing_city.state = city_state
                    existing_city.country = city_country
                    existing_city.timezone = city_timezone
                    cities_updated += 1
                else:
                    # Add new city
                    new_city = City(
                        name=city_name,
                        country=city_country,
                        state=city_state,
                        timezone=city_timezone
                    )
                    db.session.add(new_city)
                    cities_added += 1
                    
            except Exception as e:
                app_logger.error(f"Error processing city {city_info.get('name')}: {e}")
                cities_skipped += 1
                continue
        
        db.session.commit()
        cities_loaded = cities_updated + cities_added
        app_logger.info(f"✅ Processed cities: {cities_updated} updated, {cities_added} added, {cities_skipped} skipped (total: {cities_loaded})")
        
        # Step 3: Load venues
        venues_file = Path("data/venues.json")
        if not venues_file.exists():
            return jsonify({'error': 'venues.json not found'}), 404
        
        with open(venues_file, 'r') as f:
            venues_data = json.load(f)
        
        venues_json = venues_data.get('venues', {})
        app_logger.info(f"📊 Found {len(venues_json)} venues in JSON")
        
        # Get existing venues by name to preserve IDs and avoid breaking events
        existing_venues = {}
        for venue in Venue.query.all():
            key = venue.name.lower().strip()
            existing_venues[key] = venue
        
        app_logger.info(f"📍 Found {len(existing_venues)} existing venues in database")
        
        # Create city name mapping for faster lookups
        cities_by_name = {city.name: city for city in City.query.all()}
        
        venues_updated = 0
        venues_added = 0
        venues_skipped = 0
        
        for venue_id, venue_data in venues_json.items():
            # Skip metadata entries
            if venue_id == 'metadata' or not isinstance(venue_data, dict):
                continue
            
            try:
                venue_name = venue_data.get('name', '').strip()
                if not venue_name:
                    venues_skipped += 1
                    continue
                
                # Get city name from venue data
                city_name = venue_data.get('city_name', '').strip()
                if not city_name:
                    app_logger.warning(f"Venue {venue_name} has no city_name, skipping")
                    venues_skipped += 1
                    continue
                
                # Find city in database (handle "Washington" or "Washington, DC" format)
                # Try exact match first, then try without comma
                city = cities_by_name.get(city_name) or cities_by_name.get(city_name.split(',')[0].strip())
                
                # If still not found, try case-insensitive match
                if not city:
                    city_name_clean = city_name.split(',')[0].strip()
                    for db_city_name, db_city in cities_by_name.items():
                        if db_city_name.lower() == city_name_clean.lower():
                            city = db_city
                            break
                
                if not city:
                    app_logger.warning(f"City not found for venue {venue_name}: {city_name} (available cities: {list(cities_by_name.keys())[:5]})")
                    venues_skipped += 1
                    continue
                
                # Check if venue already exists
                key = venue_name.lower()
                existing_venue = existing_venues.get(key)
                
                if existing_venue:
                    # Update existing venue (preserve ID to keep events linked)
                    existing_venue.venue_type = venue_data.get('venue_type', existing_venue.venue_type or 'museum')
                    existing_venue.address = venue_data.get('address', existing_venue.address)
                    existing_venue.latitude = venue_data.get('latitude', existing_venue.latitude)
                    existing_venue.longitude = venue_data.get('longitude', existing_venue.longitude)
                    existing_venue.image_url = venue_data.get('image_url', existing_venue.image_url)
                    existing_venue.instagram_url = venue_data.get('instagram_url', existing_venue.instagram_url)
                    existing_venue.facebook_url = venue_data.get('facebook_url', existing_venue.facebook_url)
                    existing_venue.twitter_url = venue_data.get('twitter_url', existing_venue.twitter_url)
                    existing_venue.youtube_url = venue_data.get('youtube_url', existing_venue.youtube_url)
                    existing_venue.tiktok_url = venue_data.get('tiktok_url', existing_venue.tiktok_url)
                    existing_venue.website_url = venue_data.get('website_url', existing_venue.website_url)
                    existing_venue.description = venue_data.get('description', existing_venue.description)
                    existing_venue.city_id = city.id
                    existing_venue.opening_hours = venue_data.get('opening_hours', existing_venue.opening_hours)
                    existing_venue.holiday_hours = venue_data.get('holiday_hours', existing_venue.holiday_hours)
                    existing_venue.phone_number = venue_data.get('phone_number', existing_venue.phone_number)
                    existing_venue.email = venue_data.get('email', existing_venue.email)
                    existing_venue.tour_info = venue_data.get('tour_info', existing_venue.tour_info)
                    existing_venue.admission_fee = venue_data.get('admission_fee', existing_venue.admission_fee)
                    venues_updated += 1
                else:
                    # Create new venue
                    venue = Venue(
                        name=venue_name,
                        venue_type=venue_data.get('venue_type', 'museum'),
                        address=venue_data.get('address', ''),
                        latitude=venue_data.get('latitude'),
                        longitude=venue_data.get('longitude'),
                        image_url=venue_data.get('image_url', ''),
                        instagram_url=venue_data.get('instagram_url', ''),
                        facebook_url=venue_data.get('facebook_url', ''),
                        twitter_url=venue_data.get('twitter_url', ''),
                        youtube_url=venue_data.get('youtube_url', ''),
                        tiktok_url=venue_data.get('tiktok_url', ''),
                        website_url=venue_data.get('website_url', ''),
                        description=venue_data.get('description', ''),
                        city_id=city.id,
                        opening_hours=venue_data.get('opening_hours', ''),
                        holiday_hours=venue_data.get('holiday_hours', ''),
                        phone_number=venue_data.get('phone_number', ''),
                        email=venue_data.get('email', ''),
                        tour_info=venue_data.get('tour_info', ''),
                        admission_fee=venue_data.get('admission_fee', '')
                    )
                    db.session.add(venue)
                    venues_added += 1
            except Exception as e:
                app_logger.error(f"Error processing venue {venue_data.get('name', 'Unknown')}: {e}")
                venues_skipped += 1
                continue
        
        db.session.commit()
        venues_loaded = venues_updated + venues_added
        app_logger.info(f"✅ Processed venues: {venues_updated} updated, {venues_added} added, {venues_skipped} skipped (total: {venues_loaded})")
        if venues_skipped > 0:
            app_logger.warning(f"⚠️  Skipped {venues_skipped} venues (missing city or invalid data)")
        
        # Step 4: Load sources
        sources_file = Path("data/sources.json")
        if not sources_file.exists():
            return jsonify({'error': 'sources.json not found'}), 404
        
        with open(sources_file, 'r') as f:
            sources_data = json.load(f)
        
        sources_json = sources_data.get('sources', {})
        app_logger.info(f"📊 Found {len(sources_json)} sources in JSON")
        
        # Get existing sources by name to preserve IDs and avoid breaking events
        existing_sources = {}
        for source in Source.query.all():
            key = source.name.lower().strip()
            existing_sources[key] = source
        
        app_logger.info(f"📍 Found {len(existing_sources)} existing sources in database")
        
        # Create a mapping of JSON city IDs to actual database city IDs
        city_id_mapping = {}
        for json_city_id, city_info in cities_json.items():
            city = City.query.filter_by(name=city_info.get('name')).first()
            if city:
                city_id_mapping[int(json_city_id)] = city.id
        
        app_logger.info(f"📍 City ID mapping created: {len(city_id_mapping)} cities mapped")
        
        sources_updated = 0
        sources_added = 0
        sources_skipped = 0
        for source_id, source_info in sources_json.items():
            try:
                # Map JSON city_id to actual database city_id
                json_city_id = source_info.get('city_id')
                actual_city_id = city_id_mapping.get(json_city_id)
                
                if not actual_city_id:
                    app_logger.warning(f"Skipping source {source_info.get('name')} - city_id {json_city_id} not found")
                    sources_skipped += 1
                    continue
                
                source_name = source_info.get('name', '').strip()
                if not source_name:
                    sources_skipped += 1
                    continue
                
                # Check if source already exists
                key = source_name.lower()
                existing_source = existing_sources.get(key)
                
                if existing_source:
                    # Update existing source (preserve ID to keep events linked)
                    existing_source.name = source_name
                    existing_source.handle = source_info.get('handle', existing_source.handle)
                    existing_source.source_type = source_info.get('source_type', existing_source.source_type)
                    existing_source.url = source_info.get('url', existing_source.url)
                    existing_source.description = source_info.get('description', existing_source.description)
                    existing_source.city_id = actual_city_id
                    existing_source.covers_multiple_cities = source_info.get('covers_multiple_cities', False)
                    existing_source.covered_cities = source_info.get('covered_cities', '')
                    existing_source.event_types = source_info.get('event_types', '[]')
                    existing_source.is_active = source_info.get('is_active', True)
                    existing_source.reliability_score = source_info.get('reliability_score', 3.0)
                    existing_source.posting_frequency = source_info.get('posting_frequency', '')
                    existing_source.notes = source_info.get('notes', '')
                    existing_source.scraping_pattern = source_info.get('scraping_pattern', '')
                    sources_updated += 1
                else:
                    # Add new source
                    source = Source(
                        name=source_name,
                        handle=source_info.get('handle'),
                        source_type=source_info.get('source_type'),
                        url=source_info.get('url'),
                        description=source_info.get('description'),
                        city_id=actual_city_id,  # Use actual database city_id
                        covers_multiple_cities=source_info.get('covers_multiple_cities', False),
                        covered_cities=source_info.get('covered_cities', ''),
                        event_types=source_info.get('event_types', '[]'),
                        is_active=source_info.get('is_active', True),
                        reliability_score=source_info.get('reliability_score', 3.0),
                        posting_frequency=source_info.get('posting_frequency', ''),
                        notes=source_info.get('notes', ''),
                        scraping_pattern=source_info.get('scraping_pattern', '')
                    )
                    db.session.add(source)
                    sources_added += 1
            except Exception as e:
                app_logger.error(f"Error processing source {source_info.get('name')}: {e}")
                sources_skipped += 1
                continue
        
        db.session.commit()
        sources_loaded = sources_updated + sources_added
        app_logger.info(f"✅ Processed sources: {sources_updated} updated, {sources_added} added, {sources_skipped} skipped (total: {sources_loaded})")
        
        return jsonify({
            'message': f'Successfully loaded all data',
            'cities_loaded': cities_loaded,
            'venues_loaded': venues_loaded,
            'venues_skipped': venues_skipped,
            'sources_loaded': sources_loaded,
            'total_items': cities_loaded + venues_loaded + sources_loaded
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error loading all data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reload-sources', methods=['POST'])
def reload_sources_from_json():
    """Reload sources from sources.json into database (handles city_id mismatch between local and production)"""
    try:
        import json
        from pathlib import Path
        
        app_logger.info("🔄 Reloading sources from sources.json...")
        
        sources_file = Path("data/sources.json")
        if not sources_file.exists():
            return jsonify({'error': 'sources.json not found'}), 404
        
        with open(sources_file, 'r') as f:
            data = json.load(f)
        
        sources_data = data.get('sources', {})
        total_sources = len(sources_data)
        
        app_logger.info(f"📊 Found {total_sources} sources in JSON")
        
        # Create city_id mapping from cities.json (handles city_id mismatch between local and production)
        cities_file = Path("data/cities.json")
        city_id_mapping = {}
        if cities_file.exists():
            with open(cities_file, 'r') as f:
                cities_data = json.load(f)
            cities_json = cities_data.get('cities', {})
            for json_city_id, city_info in cities_json.items():
                city_name = city_info.get('name')
                if city_name:
                    # Find city in production database by name
                    city = City.query.filter_by(name=city_name).first()
                    if city:
                        city_id_mapping[int(json_city_id)] = city.id
        
        app_logger.info(f"📍 City ID mapping created: {len(city_id_mapping)} cities mapped")
        
        # Get existing sources by name to preserve IDs and avoid breaking events
        existing_sources = {}
        for source in Source.query.all():
            # Use name as key for matching
            key = source.name.lower().strip()
            existing_sources[key] = source
        
        app_logger.info(f"📍 Found {len(existing_sources)} existing sources in database")
        
        # Process sources from JSON (update existing, add new)
        sources_updated = 0
        sources_added = 0
        sources_skipped = 0
        for source_id, source_info in sources_data.items():
            try:
                # Map JSON city_id to production city_id
                json_city_id = source_info.get('city_id')
                actual_city_id = city_id_mapping.get(json_city_id)
                
                if not actual_city_id:
                    app_logger.warning(f"⚠️ Skipping source {source_info.get('name')} - city_id {json_city_id} not found in mapping")
                    sources_skipped += 1
                    continue
                
                source_name = source_info.get('name', '').strip()
                if not source_name:
                    sources_skipped += 1
                    continue
                
                # Check if source already exists
                key = source_name.lower()
                existing_source = existing_sources.get(key)
                
                if existing_source:
                    # Update existing source (preserve ID to keep events linked)
                    existing_source.name = source_name
                    existing_source.handle = source_info.get('handle', existing_source.handle)
                    existing_source.source_type = source_info.get('source_type', existing_source.source_type)
                    existing_source.url = source_info.get('url', existing_source.url)
                    existing_source.description = source_info.get('description', existing_source.description)
                    existing_source.city_id = actual_city_id
                    existing_source.covers_multiple_cities = source_info.get('covers_multiple_cities', False)
                    existing_source.covered_cities = source_info.get('covered_cities', '')
                    existing_source.event_types = source_info.get('event_types', '[]')
                    existing_source.is_active = source_info.get('is_active', True)
                    existing_source.reliability_score = source_info.get('reliability_score', 3.0)
                    existing_source.posting_frequency = source_info.get('posting_frequency', '')
                    existing_source.notes = source_info.get('notes', '')
                    existing_source.scraping_pattern = source_info.get('scraping_pattern', '')
                    sources_updated += 1
                else:
                    # Add new source
                    source = Source(
                        name=source_name,
                        handle=source_info.get('handle'),
                        source_type=source_info.get('source_type'),
                        url=source_info.get('url'),
                        description=source_info.get('description'),
                        city_id=actual_city_id,  # Use production city_id
                        covers_multiple_cities=source_info.get('covers_multiple_cities', False),
                        covered_cities=source_info.get('covered_cities', ''),
                        event_types=source_info.get('event_types', '[]'),
                        is_active=source_info.get('is_active', True),
                        reliability_score=source_info.get('reliability_score', 3.0),
                        posting_frequency=source_info.get('posting_frequency', ''),
                        notes=source_info.get('notes', ''),
                        scraping_pattern=source_info.get('scraping_pattern', '')
                    )
                    db.session.add(source)
                    sources_added += 1
            except Exception as e:
                app_logger.error(f"Error loading source {source_info.get('name')}: {e}")
                sources_skipped += 1
                continue
        
        db.session.commit()
        sources_loaded = sources_updated + sources_added
        app_logger.info(f"✅ Successfully processed sources: {sources_updated} updated, {sources_added} added, {sources_skipped} skipped (total: {sources_loaded})")
        
        return jsonify({
            'message': f'Successfully reloaded sources',
            'sources_updated': sources_updated,
            'sources_added': sources_added,
            'sources_skipped': sources_skipped,
            'total_sources': sources_loaded
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error reloading sources: {e}")
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

@app.route('/api/admin/reload-venues-from-json', methods=['POST'])
def reload_venues_from_json():
    """Reload venues from JSON file to database (for syncing production with latest data)"""
    try:
        import json
        from datetime import datetime
        
        app_logger.info("🔄 Reloading venues from venues.json...")
        
        # Load venues.json
        venues_file = os.path.join(os.path.dirname(__file__), 'data', 'venues.json')
        if not os.path.exists(venues_file):
            return jsonify({'error': 'venues.json not found'}), 404
        
        with open(venues_file, 'r') as f:
            venues_data = json.load(f)
        
        if "venues" not in venues_data:
            return jsonify({'error': 'Invalid venues.json format'}), 400
        
        venues_section = venues_data["venues"]
        updated_count = 0
        venues_found_in_json = len(venues_section)
        venues_matched_in_db = 0
        
        app_logger.info(f"JSON has {venues_found_in_json} venues (flat structure)")
        
        # Handle flat structure: each key is a venue ID, value is venue data
        for venue_id, venue_data in venues_section.items():
            # Check if this is actually venue data (has 'name' key)
            if not isinstance(venue_data, dict) or 'name' not in venue_data:
                app_logger.warning(f"⚠️ Invalid venue data at key {venue_id}")
                continue
            
            venue_name = venue_data.get('name', 'Unknown')
            city_name = venue_data.get('city_name', '')
            
            # Find existing venue by name only (city_id might differ between local and production)
            venue = Venue.query.filter_by(name=venue_name).first()
            
            if venue:
                venues_matched_in_db += 1
                old_url = venue.website_url
                new_url = venue_data.get('website_url', venue.website_url)
                
                if old_url != new_url:
                    app_logger.info(f"✓ Updating {venue.name}: {old_url} → {new_url}")
                
                # Update venue with JSON data
                venue.venue_type = venue_data.get('venue_type', venue.venue_type)
                venue.address = venue_data.get('address', venue.address)
                venue.latitude = venue_data.get('latitude', venue.latitude)
                venue.longitude = venue_data.get('longitude', venue.longitude)
                venue.image_url = venue_data.get('image_url', venue.image_url)
                venue.instagram_url = venue_data.get('instagram_url', venue.instagram_url)
                venue.facebook_url = venue_data.get('facebook_url', venue.facebook_url)
                venue.twitter_url = venue_data.get('twitter_url', venue.twitter_url)
                venue.youtube_url = venue_data.get('youtube_url', venue.youtube_url)
                venue.tiktok_url = venue_data.get('tiktok_url', venue.tiktok_url)
                venue.website_url = new_url
                venue.ticketing_url = venue_data.get('ticketing_url', venue.ticketing_url)
                venue.description = venue_data.get('description', venue.description)
                venue.opening_hours = venue_data.get('opening_hours', venue.opening_hours)
                venue.holiday_hours = venue_data.get('holiday_hours', venue.holiday_hours)
                venue.phone_number = venue_data.get('phone_number', venue.phone_number)
                venue.email = venue_data.get('email', venue.email)
                venue.tour_info = venue_data.get('tour_info', venue.tour_info)
                venue.admission_fee = venue_data.get('admission_fee', venue.admission_fee)
                venue.additional_info = venue_data.get('additional_info', venue.additional_info)
                venue.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Venue doesn't exist - create it
                # Find city by name (city_id differs between local and production)
                city = None
                if city_name:
                    # Try exact match first
                    city = City.query.filter_by(name=city_name).first()
                    # If not found, try partial match (e.g., "Irvine" matches "Irvine, California, United States")
                    if not city and ',' in city_name:
                        city_name_base = city_name.split(',')[0].strip()
                        city = City.query.filter(City.name.like(f"{city_name_base}%")).first()
                
                if not city:
                    app_logger.warning(f"⚠️ City not found for venue {venue_name}: {city_name} - skipping creation")
                    continue
                
                # Create new venue
                app_logger.info(f"➕ Creating new venue: {venue_name} in {city.name}")
                new_venue = Venue(
                    name=venue_name,
                    venue_type=venue_data.get('venue_type', 'venue'),
                    address=venue_data.get('address'),
                    city_id=city.id,
                    latitude=venue_data.get('latitude'),
                    longitude=venue_data.get('longitude'),
                    image_url=venue_data.get('image_url'),
                    instagram_url=venue_data.get('instagram_url'),
                    facebook_url=venue_data.get('facebook_url'),
                    twitter_url=venue_data.get('twitter_url'),
                    youtube_url=venue_data.get('youtube_url'),
                    tiktok_url=venue_data.get('tiktok_url'),
                    website_url=venue_data.get('website_url'),
                    ticketing_url=venue_data.get('ticketing_url'),
                    description=venue_data.get('description'),
                    opening_hours=venue_data.get('opening_hours'),
                    holiday_hours=venue_data.get('holiday_hours'),
                    phone_number=venue_data.get('phone_number'),
                    email=venue_data.get('email'),
                    tour_info=venue_data.get('tour_info'),
                    admission_fee=venue_data.get('admission_fee'),
                    additional_info=venue_data.get('additional_info'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(new_venue)
                updated_count += 1
                app_logger.info(f"✅ Created venue: {venue_name}")
        
        db.session.commit()
        app_logger.info(f"✅ Successfully reloaded {updated_count} venues from JSON")
        app_logger.info(f"📊 Stats: {venues_found_in_json} in JSON, {venues_matched_in_db} matched in DB, {updated_count} updated")
        
        return jsonify({
            'success': True,
            'message': f'Successfully reloaded {updated_count} venues from JSON',
            'updated_count': updated_count,
            'venues_in_json': venues_found_in_json,
            'venues_matched': venues_matched_in_db
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"❌ Error reloading venues: {e}")
        import traceback
        traceback.print_exc()
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

@app.route('/api/admin/clear-past-events', methods=['POST'])
def clear_past_events():
    """Delete all events that have ended in the past"""
    try:
        today = date.today()
        
        # Build query for past events
        # 1. Event has an end_date and end_date < today
        # 2. Event has no end_date and start_date < today
        # AND Event is not permanent
        query = Event.query.filter(
            db.or_(
                db.and_(Event.end_date.isnot(None), Event.end_date < today),
                db.and_(Event.end_date.is_(None), Event.start_date < today)
            ),
            Event.is_permanent == False
        )
        
        # Count and delete
        past_events_count = query.count()
        query.delete(synchronize_session=False)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {past_events_count} past events from database'
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
    """Get all sources for admin, sorted by most recently updated (most recent first)"""
    try:
        sources = Source.query.order_by(Source.updated_at.desc()).all()
        sources_data = []
        for source in sources:
            source_dict = source.to_dict()
            if source.city:
                source_dict['city_name'] = source.city.name
            sources_data.append(source_dict)
        return jsonify(sources_data)
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
        if 'ticketing_url' in data:
            venue.ticketing_url = clean_url_field(data['ticketing_url'])
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
            if 'artists' in data:
                event.artists = clean_text_field(data['artists'])
            if 'exhibition_type' in data:
                event.exhibition_type = clean_text_field(data['exhibition_type'])
            if 'collection_period' in data:
                event.collection_period = clean_text_field(data['collection_period'])
            if 'number_of_artworks' in data:
                event.number_of_artworks = clean_numeric_field(data['number_of_artworks'])
            if 'opening_reception_date' in data and data['opening_reception_date']:
                event.opening_reception_date = datetime.strptime(data['opening_reception_date'], '%Y-%m-%d').date()
            if 'opening_reception_time' in data and data['opening_reception_time']:
                event.opening_reception_time = datetime.strptime(data['opening_reception_time'], '%H:%M').time()
            if 'is_permanent' in data:
                event.is_permanent = bool(data['is_permanent'])
            if 'related_exhibitions' in data:
                event.related_exhibitions = clean_text_field(data['related_exhibitions'])
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
        
        # Save uploaded file at low quality to save space
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"event_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save at low quality using PIL to reduce file size
        try:
            from PIL import Image
            import io
            
            # Read the uploaded file
            file.seek(0)  # Reset file pointer
            image = Image.open(io.BytesIO(file.read()))
            
            # Convert to JPEG at low quality (60) for smaller file size
            # Also resize if image is very large (max width 1200px)
            max_width = 1200
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (for JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = rgb_image
            
            # Save as JPEG at quality=60 (low quality, smaller file size)
            file_path = os.path.splitext(file_path)[0] + '.jpg'
            image.save(file_path, format='JPEG', quality=60, optimize=True)
            
            app_logger.info(f"✅ Saved image at low quality: {file_path} (size: {os.path.getsize(file_path)} bytes)")
        except Exception as e:
            # Fallback to direct save if PIL processing fails
            app_logger.warning(f"⚠️ Failed to save with PIL, using direct save: {e}")
            file.seek(0)  # Reset file pointer
            file.save(file_path)
        
        # Get OCR engine preference from form
        ocr_engine = request.form.get('ocr_engine', 'auto')
        
        # Process image to extract event data
        from scripts.hybrid_event_processor import HybridEventProcessor
        processor = HybridEventProcessor(ocr_engine_preference=ocr_engine)
        extracted_data = processor.process_image_with_llm(file_path)
        
        # Keep uploaded file at low quality (don't delete - user may want to reference it)
        app_logger.info(f"📸 Saved low-quality screenshot: {file_path}")
        
        # Get city timezone from city_id
        city_timezone = None
        app_logger.info(f"🌍 Getting timezone - city_id: {extracted_data.city_id}, city: {extracted_data.city}")
        
        if extracted_data.city_id:
            city = db.session.get(City, extracted_data.city_id)
            if city and city.timezone:
                city_timezone = city.timezone
                app_logger.info(f"✅ Found timezone from city_id: {city_timezone}")
            else:
                app_logger.warning(f"⚠️ City not found or no timezone for city_id: {extracted_data.city_id}")
        
        # Fallback: if city is Washington (by name or NGA event), use America/New_York
        if not city_timezone:
            if extracted_data.city and 'washington' in extracted_data.city.lower():
                city_timezone = 'America/New_York'
                app_logger.info(f"✅ Set timezone to America/New_York for Washington (fallback)")
            # Also check if it's an NGA event (source is website and has NGA indicators)
            elif extracted_data.source == 'website' and extracted_data.raw_text:
                raw_lower = extracted_data.raw_text.lower()
                if any(indicator in raw_lower for indicator in ['nga', 'national gallery', 'finding awe']):
                    city_timezone = 'America/New_York'
                    app_logger.info(f"✅ Set timezone to America/New_York for NGA event (fallback)")
        
        if not city_timezone:
            city_timezone = 'UTC'  # Final fallback
            app_logger.warning(f"⚠️ No timezone found, defaulting to UTC")
        
        # Extract registration and online status from LLM reasoning if available
        is_registration_required = False
        registration_url = None
        is_online = False
        
        # Try to extract from LLM reasoning JSON if it contains registration/online info
        if extracted_data.llm_reasoning:
            try:
                import json
                # Try to find JSON in the reasoning
                json_start = extracted_data.llm_reasoning.find('{')
                json_end = extracted_data.llm_reasoning.rfind('}') + 1
                if json_start != -1 and json_end > 0:
                    llm_json = json.loads(extracted_data.llm_reasoning[json_start:json_end])
                    is_registration_required = llm_json.get('is_registration_required', False)
                    registration_url = llm_json.get('registration_url')
                    is_online = llm_json.get('is_online', False)
            except:
                pass
        
        # Fallback: Check raw text for indicators
        if extracted_data.raw_text:
            text_lower = extracted_data.raw_text.lower()
            # Check for "Register Now" button
            if 'register now' in text_lower:
                is_registration_required = True
            # Check for "Virtual" tag (and no "In-person" tag)
            if 'virtual' in text_lower and 'in-person' not in text_lower and 'in person' not in text_lower:
                is_online = True
            elif 'in-person' in text_lower or 'in person' in text_lower:
                is_online = False
        
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
                'venue_id': extracted_data.venue_id,
                'city_timezone': city_timezone,
                'is_online': is_online,
                'is_registration_required': is_registration_required,
                'registration_url': registration_url,
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
        
        # Use city_id from frontend (which should be auto-selected by smart detection)
        city_id = data.get('city_id')
        
        # Auto-detect NGA venue if not provided
        venue_id = data.get('venue_id')
        if not venue_id:
            # Check if this is an NGA event by title, description, or location
            title_lower = (data.get('title') or '').lower()
            desc_lower = (data.get('description') or '').lower()
            loc_lower = (start_location or '').lower()
            
            is_nga = any([
                'national gallery' in title_lower or 'national gallery' in desc_lower,
                'nga' in title_lower or 'nga' in desc_lower,
                'finding awe' in title_lower,
                'west building' in loc_lower or 'east building' in loc_lower,
                'constitution ave' in loc_lower
            ])
            
            if is_nga and city_id:
                # Find National Gallery of Art venue
                nga_venue = Venue.query.filter(
                    db.func.lower(Venue.name).like('%national gallery%'),
                    Venue.city_id == city_id
                ).first()
                
                if nga_venue:
                    venue_id = nga_venue.id
                    app_logger.info(f"🏛️ Auto-detected NGA venue: {nga_venue.name} (ID: {venue_id})")
        
        event = Event(
            title=title,
            description=data.get('description', ''),
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            event_type=data.get('event_type', 'tour'),
            start_location=start_location,
            end_location=end_location,
            url=data.get('url', ''),
            city_id=city_id,
            venue_id=venue_id,
            source=data.get('source'),
            source_url=data.get('source_url'),
            # Online/virtual status
            is_online=data.get('is_online', False),
            # Registration fields
            is_registration_required=data.get('is_registration_required', False),
            registration_url=data.get('registration_url'),
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
            event.admission_price = data.get('price') or data.get('admission_price')
            event.artists = data.get('artists', '')
            event.exhibition_type = data.get('exhibition_type', '')
            event.collection_period = data.get('collection_period', '')
            event.number_of_artworks = data.get('number_of_artworks')
            if data.get('opening_reception_date'):
                event.opening_reception_date = datetime.strptime(data['opening_reception_date'], '%Y-%m-%d').date()
            if data.get('opening_reception_time'):
                event.opening_reception_time = datetime.strptime(data['opening_reception_time'], '%H:%M').time()
            event.is_permanent = data.get('is_permanent', False)
            event.related_exhibitions = data.get('related_exhibitions', '')
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
                    venue = db.session.get(Venue, event.venue_id)
                    if venue:
                        venue_data = venue.to_dict()
                
                # Get city data if city_id provided
                city_data = None
                if event.city_id:
                    city = db.session.get(City, event.city_id)
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

@app.route('/api/admin/extract-event-from-url', methods=['POST'])
def extract_event_from_url():
    """Extract event data from a URL without creating events (for preview/editing)"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Import extraction function
        from scripts.url_event_scraper import extract_event_data_from_url
        
        # Extract data
        extracted_data = extract_event_data_from_url(url)
        
        # Try to match venue and city from extracted location or venue field
        venue_id = None
        city_id = None
        
        # Check venue field first (more reliable for SAAM events)
        venue_text = extracted_data.get('venue', '')
        location_text = extracted_data.get('location', '')
        
        # Try to match venue from venue field first
        if venue_text:
            venue = Venue.query.filter(
                db.func.lower(Venue.name).like(f'%{venue_text.lower()}%')
            ).first()
            
            if venue:
                venue_id = venue.id
                city_id = venue.city_id
                app_logger.info(f"Matched venue from venue field: {venue.name} (ID: {venue_id}, City: {city_id})")
            else:
                # Try to match common variations
                cleaned_venue = venue_text.replace('The ', '').replace('the ', '')
                venue = Venue.query.filter(
                    db.func.lower(Venue.name).like(f'%{cleaned_venue.lower()}%')
                ).first()
                
                if venue:
                    venue_id = venue.id
                    city_id = venue.city_id
                    app_logger.info(f"Matched venue (cleaned) from venue field: {venue.name} (ID: {venue_id}, City: {city_id})")
        
        # Fallback to location field if venue field didn't match
        if not venue_id and location_text:
            # Try to find matching venue (Venue model is defined in this file)
            # Try exact match first
            venue = Venue.query.filter(
                db.func.lower(Venue.name).like(f'%{location_text.lower()}%')
            ).first()
            
            if venue:
                venue_id = venue.id
                city_id = venue.city_id
                app_logger.info(f"Matched venue from location field: {venue.name} (ID: {venue_id}, City: {city_id})")
            else:
                # Try to match common variations
                # "The Metropolitan Museum of Art" -> "Metropolitan Museum of Art"
                cleaned_location = location_text.replace('The ', '').replace('the ', '')
                venue = Venue.query.filter(
                    db.func.lower(Venue.name).like(f'%{cleaned_location.lower()}%')
                ).first()
                
                if venue:
                    venue_id = venue.id
                    city_id = venue.city_id
                    app_logger.info(f"Matched venue (cleaned) from location field: {venue.name} (ID: {venue_id}, City: {city_id})")
        
        # Add IDs to response
        extracted_data['venue_id'] = venue_id
        extracted_data['city_id'] = city_id
        
        return jsonify(extracted_data)
        
    except Exception as e:
        app_logger.error(f"Error extracting event from URL: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scrape-event-from-url', methods=['POST'])
def scrape_event_from_url():
    """Scrape event data from a URL and create events based on schedule"""
    try:
        data = request.get_json()
        
        url = data.get('url')
        venue_id = data.get('venue_id')
        city_id = data.get('city_id')
        time_period = data.get('time_period', 'this_week')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Get edited extracted data if provided
        # Convert price from string to float if needed
        price_val = data.get('price')
        if isinstance(price_val, str):
            if price_val.lower() in ['free', '0', '0.0']:
                price_val = 0.0
            else:
                try:
                    price_val = float(price_val)
                except (ValueError, TypeError):
                    price_val = None
        
        override_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'start_time': data.get('start_time'),
            'end_time': data.get('end_time'),
            'location': data.get('location'),
            'image_url': data.get('image_url'),
            'schedule_info': data.get('schedule_info'),
            'days_of_week': data.get('days_of_week'),
            'is_registration_required': data.get('is_registration_required'),
            'registration_url': data.get('registration_url'),
            'registration_info': data.get('registration_info'),
            'price': price_val,
            'admission_price': data.get('admission_price')
        }
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not city_id:
            return jsonify({'error': 'City ID is required'}), 400
        
        # Get venue if provided
        venue = None
        if venue_id:
            venue = db.session.get(Venue, venue_id)
            if not venue:
                return jsonify({'error': 'Venue not found'}), 404
        
        # Get city
        city = db.session.get(City, city_id)
        if not city:
            return jsonify({'error': 'City not found'}), 404
        
        # Import scraper
        from scripts.url_event_scraper import scrape_event_from_url
        from datetime import date, timedelta
        
        # Calculate date range based on time_period
        today = date.today()
        period_start = today
        period_end = today
        
        if time_period == 'today':
            period_start = today
            period_end = today
        elif time_period == 'tomorrow':
            period_start = today + timedelta(days=1)
            period_end = today + timedelta(days=1)
        elif time_period == 'this_week':
            # This week = today to end of week (Sunday)
            period_start = today
            days_until_sunday = (6 - today.weekday()) % 7
            period_end = today + timedelta(days=days_until_sunday)
        elif time_period == 'this_month':
            # This month = today to end of month
            period_start = today
            next_month = today.replace(day=28) + timedelta(days=4)
            period_end = next_month - timedelta(days=next_month.day)
        elif time_period == 'custom':
            if start_date and end_date:
                try:
                    period_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                    period_end = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            else:
                return jsonify({'error': 'Custom period requires start_date and end_date'}), 400
        
        # Scrape and create events
        result = scrape_event_from_url(url, venue, city, period_start, period_end, override_data)
        
        return jsonify({
            'success': True,
            'events_created': result['events_created'],
            'events': result['events'],
            'schedule_info': result.get('schedule_info'),
            'message': f'Successfully created {result["events_created"]} event(s)'
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping event from URL: {e}")
        import traceback
        traceback.print_exc()
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
        
        # Get city timezone - prioritize city_timezone from request, then lookup from city_id
        timezone = data.get('city_timezone')  # Use city_timezone if provided in request
        if not timezone and city_id:
            city = db.session.get(City, city_id)
            if city and city.timezone:
                timezone = city.timezone
        if not timezone:
            timezone = 'UTC'  # Final fallback
        
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

def detect_venue_type(venue_name=None, title=None, url=None, start_location=None):
    """Detect special venue types (NGA, Hirshhorn, Webster's)"""
    venue_name_lower = (venue_name or '').lower()
    title_lower = (title or '').lower()
    url_lower = (url or '').lower()
    start_loc_lower = (start_location or '').lower()
    
    is_nga = (
        'national gallery' in venue_name_lower or 'nga' in venue_name_lower or
        'national gallery' in title_lower or 'finding awe' in title_lower or
        'nga.gov' in url_lower or
        (('west building' in start_loc_lower or 'east building' in start_loc_lower) and
         ('gallery' in start_loc_lower or 'floor' in start_loc_lower))
    )
    
    is_hirshhorn = 'hirshhorn' in venue_name_lower
    
    is_websters = (
        "webster's" in venue_name_lower or 'websters' in venue_name_lower or
        "webster's" in title_lower or 'websters' in title_lower or
        'webstersbooksandcafe.com' in url_lower
    )
    
    return {'is_nga': is_nga, 'is_hirshhorn': is_hirshhorn, 'is_websters': is_websters}

def get_calendar_location(event_data):
    """Get calendar location for event, handling special venues and fallbacks"""
    venue_name = event_data.get('venue_name')
    venue_address = event_data.get('venue_address')
    title = event_data.get('title')
    url = event_data.get('url')
    start_location = event_data.get('start_location')
    city_name = event_data.get('city_name')
    
    venue_types = detect_venue_type(venue_name, title, url, start_location)
    has_venue_name = venue_name and isinstance(venue_name, str) and venue_name.strip()
    has_venue_address = venue_address and isinstance(venue_address, str) and venue_address.strip()
    
    # Special venue handling
    if venue_types['is_nga']:
        if has_venue_name and has_venue_address:
            return f"{venue_name.strip()}, {venue_address.strip()}"
        elif has_venue_address:
            return venue_address.strip()
        elif has_venue_name:
            return f"{venue_name.strip()}, Constitution Ave NW, Washington, DC 20565, USA"
        return VENUE_ADDRESSES['NGA']
    
    if venue_types['is_hirshhorn']:
        if has_venue_name and has_venue_address:
            return f"{venue_name.strip()}, {venue_address.strip()}"
        elif has_venue_address:
            return venue_address.strip()
        elif has_venue_name:
            return f"{venue_name.strip()}, Independence Ave SW, Washington, DC 20560, USA"
        return VENUE_ADDRESSES['HIRSHHORN']
    
    if venue_types['is_websters']:
        return VENUE_ADDRESSES['WEBSTERS']
    
    # General venue handling - use XML tags for iCal format
    # If no venue address, use start/end location instead
    end_location = event_data.get('end_location')
    has_end_location = end_location and isinstance(end_location, str) and end_location.strip()
    has_start_location = start_location and isinstance(start_location, str) and start_location.strip()
    
    if has_venue_name and has_venue_address:
        return f"<location>{venue_name.strip()}</location><address>{venue_address.strip()}</address>"
    elif has_venue_address:
        return f"<address>{venue_address.strip()}</address>"
    elif has_venue_name:
        # No venue address - use start/end location if available
        location = f"<location>{venue_name.strip()}</location>"
        if has_start_location:
            if has_end_location and end_location.strip() != start_location.strip():
                location += f"<address>{start_location.strip()} to {end_location.strip()}</address>"
            else:
                location += f"<address>{start_location.strip()}</address>"
        elif city_name and isinstance(city_name, str) and city_name.strip():
            location += f"<address>{city_name.strip()}</address>"
        return location
    elif has_start_location:
        # No venue at all - use start/end location
        if has_end_location and end_location.strip() != start_location.strip():
            return f"{start_location.strip()} to {end_location.strip()}"
        return start_location.strip()
    
    return ''

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
    
    # Determine if event is all-day: no times specified (regardless of event type)
    is_all_day = False
    if not event_data.get('start_time') and not event_data.get('end_time'):
        is_all_day = True
    
    # Handle times if provided - use floating time (no timezone conversion)
    # For all-day events, use DATE format (YYYYMMDD) instead of DATETIME format
    if is_all_day:
        # For all-day events, use DATE format (end date should be exclusive, so add 1 day)
        from datetime import timedelta
        start_datetime_str = start_date.strftime('%Y%m%d')
        # For all-day events, end date is exclusive in iCal format, so add 1 day
        end_date_exclusive = end_date + timedelta(days=1)
        end_datetime_str = end_date_exclusive.strftime('%Y%m%d')
    else:
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
    
    # Extract recurrence info from description if present (and remove the marker)
    description = event_data.get('description', '')
    is_recurring_from_desc = False
    recurrence_rule_from_desc = ''
    if description:
        import re
        recurrence_match = re.search(r'\[RECURRING:\s*([^\]]+)\](.*)', description, re.DOTALL)
        if recurrence_match:
            is_recurring_from_desc = True
            recurrence_rule_from_desc = recurrence_match.group(1).strip()
            # Remove the recurrence marker from description
            description = re.sub(r'\[RECURRING:[^\]]+\]\s*', '', description).strip()
    
    # Build enhanced description with additional information
    description_parts = []
    
    # Add specific meeting location to the beginning of description if available
    # This is for cases where the location is a specific room/gallery within a venue
    start_location = event_data.get('start_location')
    venue_name = event_data.get('venue_name')
    if start_location and start_location.strip():
        start_loc_lower = start_location.lower().strip()
        venue_lower = (venue_name or '').lower().strip()
        # Add if start_location is different from venue name
        # This handles cases like "West Building Main Floor, Gallery 61" vs "National Gallery of Art"
        if not venue_lower or (start_loc_lower != venue_lower and venue_lower not in start_loc_lower and start_loc_lower not in venue_lower):
            description_parts.insert(0, f"Meeting Location: {start_location.strip()}")
    
    if description:
        description_parts.append(description)
    
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
    
    # Get calendar location (use provided location or calculate from venue info)
    calendar_location = event_data.get('location', '')
    if not calendar_location:
        calendar_location = get_calendar_location(event_data)
    
    # Generate timezone information for iCal
    timezone_info = generate_timezone_info(timezone_str)
    
    # Create iCal content with timezone information
    # For all-day events, use DATE format (no TZID), for timed events use DATETIME format with TZID
    if is_all_day:
        dtstart_line = f"DTSTART;VALUE=DATE:{start_datetime_str}"
        dtend_line = f"DTEND;VALUE=DATE:{end_datetime_str}"
    else:
        dtstart_line = f"DTSTART;TZID={timezone_str}:{start_datetime_str}"
        dtend_line = f"DTEND;TZID={timezone_str}:{end_datetime_str}"
    
    # Check if this is a recurring event
    # Use the recurrence info we extracted from description above
    is_recurring = event_data.get('is_recurring', False) or is_recurring_from_desc
    recurrence_rule = event_data.get('recurrence_rule', '') or recurrence_rule_from_desc
    
    # Build RRULE line if this is a recurring event
    rrule_line = ''
    if is_recurring and recurrence_rule:
        # Format: RRULE:FREQ=DAILY (no end date = forever)
        rrule_line = f"RRULE:{recurrence_rule}\n"
    
    ical_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Event Planner//Event Planner//EN
{timezone_info}
BEGIN:VEVENT
UID:{event_id}@eventplanner.com
{dtstart_line}
{dtend_line}
{rrule_line}SUMMARY:{event_data['title']}
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
        
        venue = db.session.get(Venue, venue_id)
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
            title=title,
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
            event.admission_price = data.get('price') or data.get('admission_price')
            event.artists = data.get('artists', '')
            event.exhibition_type = data.get('exhibition_type', '')
            event.collection_period = data.get('collection_period', '')
            event.number_of_artworks = data.get('number_of_artworks')
            if data.get('opening_reception_date'):
                event.opening_reception_date = datetime.strptime(data['opening_reception_date'], '%Y-%m-%d').date()
            if data.get('opening_reception_time'):
                event.opening_reception_time = datetime.strptime(data['opening_reception_time'], '%H:%M').time()
            event.is_permanent = data.get('is_permanent', False)
            event.related_exhibitions = data.get('related_exhibitions', '')
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

# Event Scraping API Endpoints
@app.route('/api/admin/scrape-smithsonian', methods=['POST'])
def scrape_smithsonian():
    """Scrape events from Smithsonian museums."""
    try:
        logger.info("Starting Smithsonian scraping...")
        
        # Import scraping modules
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
        
        from smithsonian_scraper import SmithsonianEventScraper
        from scraping_database_integration import EventDatabaseManager
        
        # Scrape Smithsonian events
        scraper = SmithsonianEventScraper()
        scraped_events = scraper.scrape_all_smithsonian_events()
        
        # Save to database
        event_manager = EventDatabaseManager()
        saved_count = event_manager.save_scraped_events(scraped_events, city_id=1)
        
        result = {
            'success': True,
            'events_found': len(scraped_events),
            'events_saved': saved_count,
            'message': f'Successfully scraped {len(scraped_events)} events, saved {saved_count} to database'
        }
        
        logger.info(f"Smithsonian scraping completed: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in Smithsonian scraping: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Smithsonian scraping failed'
        }), 500

@app.route('/api/admin/scrape-museums', methods=['POST'])
def scrape_museums():
    """Scrape events from museums only."""
    try:
        logger.info("Starting museum scraping...")
        
        # Import scraping modules
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
        
        from scraping_database_integration import ScrapingScheduler
        
        # Run museum scraping
        scheduler = ScrapingScheduler()
        result = scheduler.run_museum_scraping(city_id=1)
        
        return jsonify({
            'success': True,
            'museums_scraped': result['museums_scraped'],
            'events_found': result['events_found'],
            'events_saved': result['events_saved'],
            'message': f'Successfully scraped {result["museums_scraped"]} museums, saved {result["events_saved"]} events'
        })
        
    except Exception as e:
        logger.error(f"Error in museum scraping: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Museum scraping failed'
        }), 500

@app.route('/api/admin/scrape-all-venues', methods=['POST'])
def scrape_all_venues():
    """Scrape events from all venues."""
    try:
        logger.info("Starting all venues scraping...")
        
        # Import scraping modules
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
        
        from scraping_database_integration import ScrapingScheduler
        
        # Run all venues scraping
        scheduler = ScrapingScheduler()
        result = scheduler.run_daily_scraping(city_id=1)
        
        return jsonify({
            'success': True,
            'venues_scraped': result['venues_scraped'],
            'events_found': result['events_found'],
            'events_saved': result['events_saved'],
            'message': f'Successfully scraped {result["venues_scraped"]} venues, saved {result["events_saved"]} events'
        })
        
    except Exception as e:
        logger.error(f"Error in all venues scraping: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'All venues scraping failed'
        }), 500

@app.route('/api/admin/scrape-finding-awe', methods=['POST'])
def scrape_finding_awe():
    """Scrape all Finding Awe events from NGA."""
    try:
        app_logger.info("Starting Finding Awe scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting Finding Awe scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'National Gallery of Art - Finding Awe',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the Finding Awe scraper
        from scripts.nga_finding_awe_scraper import scrape_all_finding_awe_events, create_events_in_database
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 20,
            'message': 'Scraping Finding Awe events...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all Finding Awe events (with incremental saving)
        try:
            result = scrape_all_finding_awe_events(save_incrementally=True)
            if isinstance(result, tuple):
                events, created_count, updated_count = result
            else:
                # Fallback if function returns old format
                events = result
                created_count = 0
                updated_count = 0
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_all_finding_awe_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
            created_count = 0
            updated_count = 0
        
        if not events:
            progress_data.update({
                'current_step': 3,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 100,
                'message': '❌ No Finding Awe events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0
            }), 404
        
        # Events are already saved incrementally during scraping
        skipped_count = len(events) - created_count - updated_count
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ Finding Awe scraping completed! Found {len(events)} events, created {created_count} new, updated {updated_count} existing, {skipped_count} skipped',
            'events_saved': created_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"Finding Awe scraping completed: found {len(events)} events, created {created_count} new events, skipped {skipped_count} duplicates")
        
        message = f"Found {len(events)} Finding Awe events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if skipped_count > 0:
            message += f", {skipped_count} already existed"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_skipped': skipped_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping Finding Awe events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-nga', methods=['POST'])
def scrape_nga():
    """Scrape all NGA events: Finding Awe, tours, exhibitions, talks, and other events."""
    try:
        app_logger.info("Starting comprehensive NGA scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 5,
            'percentage': 5,
            'message': 'Starting NGA scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'National Gallery of Art',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the comprehensive NGA scraper
        from scripts.nga_comprehensive_scraper import scrape_all_nga_events, create_events_in_database
        
        # Update progress - scraping Finding Awe
        progress_data.update({
            'current_step': 1,
            'total_steps': 5,  # Ensure total_steps is always included
            'percentage': 10,
            'message': 'Scraping Finding Awe events...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all NGA events
        try:
            events = scrape_all_nga_events()
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_all_nga_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
        
        if not events:
            progress_data.update({
                'percentage': 100,
                'message': '❌ No NGA events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0,
                'events_updated': 0
            }), 404
        
        # Update progress - saving events
        progress_data.update({
            'current_step': 4,
            'total_steps': 5,  # Ensure total_steps is always included
            'percentage': 80,
            'message': f'Saving {len(events)} events to database...',
            'events_found': len(events)
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Create/update events in database
        created_count, updated_count = create_events_in_database(events)
        
        # Update progress - complete
        progress_data.update({
            'current_step': 5,
            'total_steps': 5,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ NGA scraping completed! Found {len(events)} events, created {created_count} new, updated {updated_count} existing',
            'events_saved': created_count,
            'events_updated': updated_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"NGA scraping completed: found {len(events)} events, created {created_count} new events, updated {updated_count} existing events")
        
        message = f"Found {len(events)} NGA events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if updated_count > 0:
            message += f", updated {updated_count} existing events"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_updated': updated_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping NGA events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-saam', methods=['POST'])
def scrape_saam():
    """Scrape all SAAM events: exhibitions, tours, talks, and other events."""
    try:
        app_logger.info("Starting comprehensive SAAM scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting SAAM scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'Smithsonian American Art Museum',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the comprehensive SAAM scraper
        from scripts.saam_scraper import scrape_all_saam_events, create_events_in_database
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 20,
            'message': 'Scraping SAAM events (exhibitions, tours, talks)...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all SAAM events
        try:
            events = scrape_all_saam_events()
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_all_saam_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
        
        if not events:
            progress_data.update({
                'current_step': 3,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 100,
                'message': '❌ No SAAM events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0,
                'events_updated': 0
            }), 404
        
        # Update progress - saving events
        progress_data.update({
            'current_step': 3,
            'percentage': 80,
            'message': f'Saving {len(events)} events to database...',
            'events_found': len(events)
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Create/update events in database
        created_count, updated_count = create_events_in_database(events)
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ SAAM scraping completed! Found {len(events)} events, created {created_count} new, updated {updated_count} existing',
            'events_saved': created_count,
            'events_updated': updated_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"SAAM scraping completed: found {len(events)} events, created {created_count} new events, updated {updated_count} existing events")
        
        message = f"Found {len(events)} SAAM events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if updated_count > 0:
            message += f", updated {updated_count} existing events"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_updated': updated_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping SAAM events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e),
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0
        }), 500

@app.route('/api/admin/search-eventbrite-organizer', methods=['POST'])
def search_eventbrite_organizer():
    """
    Search Eventbrite for organizer pages matching a venue name.
    
    Note: Eventbrite API doesn't have a public search endpoint for organizers.
    This function can:
    1. Extract and verify organizer IDs from URLs
    2. Get organizer details if we have an organizer ID
    3. Provide helpful instructions for manual search
    """
    try:
        data = request.get_json() or {}
        venue_name = data.get('venue_name', '').strip()
        city_name = data.get('city_name', '').strip()
        organizer_url = data.get('organizer_url', '').strip()  # Optional: if user provides URL
        organizer_id = data.get('organizer_id', '').strip()  # Optional: if user provides ID directly
        
        # Import Eventbrite scraper
        from scripts.eventbrite_scraper import EventbriteScraper
        scraper = EventbriteScraper()
        
        # API token is optional - we can still extract IDs from URLs and do web scraping without it
        # Only require it for API verification
        
        # If user provided an organizer URL, extract the organizer ID and verify it
        if organizer_url and 'eventbrite.com' in organizer_url:
            extracted_id = scraper.extract_organizer_id_from_url(organizer_url)
            if extracted_id:
                organizer_id = extracted_id
        
        # If we have an organizer ID, get organizer details
        if organizer_id:
            try:
                org_url = f'{scraper.api_base_url}/organizers/{organizer_id}/'
                response = scraper.session.get(org_url, params={'expand': 'description'}, timeout=10)
                
                if response.status_code == 200:
                    org_data = response.json()
                    
                    # Try to get event count
                    events_url = f'{scraper.api_base_url}/organizers/{organizer_id}/events/'
                    events_response = scraper.session.get(events_url, params={'status': 'live'}, timeout=10)
                    event_count = 0
                    if events_response.status_code == 200:
                        events_data = events_response.json()
                        event_count = len(events_data.get('events', []))
                    
                    # Construct proper organizer URL
                    org_name_slug = org_data.get('name', '').lower().replace(' ', '-').replace("'", '').replace(',', '')
                    proper_url = organizer_url if organizer_url else f"https://www.eventbrite.com/o/{org_name_slug}-{organizer_id}"
                    
                    return jsonify({
                        'success': True,
                        'organizers': [{
                            'id': organizer_id,
                            'name': org_data.get('name', 'Unknown'),
                            'description': org_data.get('description', {}).get('text', ''),
                            'url': proper_url,
                            'event_count': event_count,
                            'verified': True
                        }],
                        'total_found': 1
                    })
                else:
                    app_logger.warning(f"Could not fetch organizer {organizer_id}: {response.status_code}")
            except Exception as e:
                app_logger.warning(f"Error verifying organizer {organizer_id}: {e}")
                # Still return success with the ID we extracted
                if organizer_url:
                    return jsonify({
                        'success': True,
                        'organizers': [{
                            'id': organizer_id,
                            'name': 'Unknown (from URL)',
                            'url': organizer_url,
                            'event_count': 0,
                            'verified': False,
                            'note': 'Organizer ID extracted but could not verify via API'
                        }],
                        'total_found': 1
                    })
        
        # If we have a venue name, search for organizers using web scraping
        if venue_name:
            app_logger.info(f"Searching Eventbrite for organizers matching: {venue_name}")
            
            use_web_search = data.get('use_web_search', True)
            organizers = []
            
            # Try web scraping search if enabled
            if use_web_search:
                try:
                    organizers = scraper.search_organizers_by_venue_name(
                        venue_name, 
                        city_name,
                        state=state if state else None,
                        max_results=10
                    )
                    app_logger.info(f"Web search found {len(organizers)} organizers")
                except Exception as e:
                    app_logger.warning(f"Web search failed: {e}")
                    import traceback
                    app_logger.debug(traceback.format_exc())
            
            if organizers:
                return jsonify({
                    'success': True,
                    'query': f"{venue_name} {city_name}".strip(),
                    'organizers': organizers,
                    'total_found': len(organizers),
                    'source': 'web_search'
                })
            
            # If no results, return helpful instructions with search URL
            # Build location slug with city and state
            if city_name and state:
                city_slug = city_name.lower().replace(' ', '-')
                state_slug = state.lower().replace(' ', '-')
                if state_slug in ['dc', 'district-of-columbia', 'washington-dc']:
                    location_slug = 'dc--washington'
                else:
                    location_slug = f"{city_slug}-{state_slug}"
            elif city_name:
                city_slug = city_name.lower().replace(' ', '-')
                if city_slug == 'washington':
                    location_slug = 'dc--washington'
                else:
                    location_slug = city_slug
            else:
                location_slug = 'dc--washington'
            
            venue_slug = venue_name.replace(' ', '-').lower()
            search_url = f'https://www.eventbrite.com/d/{location_slug}/{venue_slug}/'
            
            return jsonify({
                'success': False,
                'error': 'No organizers found',
                'message': f'Could not find Eventbrite organizers for "{venue_name}". Try searching manually on Eventbrite or paste an organizer URL.',
                'search_url': search_url,
                'organizers': [],
                'instructions': [
                    '1. Go to eventbrite.com and search for events by the venue name',
                    '2. Click on any event from that venue',
                    '3. Click on the organizer name to go to their organizer page',
                    '4. Copy the organizer page URL (format: https://www.eventbrite.com/o/organizer-name-1234567890)',
                    '5. Paste the URL into the Ticketing URL field',
                    '6. Click "Search Eventbrite" again to verify and extract the organizer ID'
                ]
            })
        
        return jsonify({
            'success': False,
            'error': 'Missing parameters',
            'message': 'Please provide either venue_name, organizer_url, or organizer_id'
        }), 400
            
    except Exception as e:
        app_logger.error(f"Error in search_eventbrite_organizer: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-eventbrite', methods=['POST'])
def scrape_eventbrite():
    """Scrape events from Eventbrite for venues with Eventbrite ticketing URLs"""
    try:
        data = request.get_json() or {}
        venue_id = data.get('venue_id')
        city_id = data.get('city_id')
        time_range = data.get('time_range', 'this_month')
        
        # Import Eventbrite scraper
        from scripts.eventbrite_scraper import EventbriteScraper, scrape_all_eventbrite_venues, scrape_eventbrite_events_for_venue
        
        if venue_id:
            # Scrape events for specific venue
            app_logger.info(f"Scraping Eventbrite events for venue ID {venue_id}")
            events = scrape_eventbrite_events_for_venue(venue_id, time_range=time_range)
        elif city_id:
            # Scrape events for all Eventbrite venues in city
            app_logger.info(f"Scraping Eventbrite events for city ID {city_id}")
            events = scrape_all_eventbrite_venues(city_id=city_id, time_range=time_range)
        else:
            # Scrape all Eventbrite venues
            app_logger.info("Scraping Eventbrite events for all venues")
            events = scrape_all_eventbrite_venues(time_range=time_range)
        
        if not events:
            return jsonify({
                'success': False,
                'error': 'No events found from Eventbrite',
                'events_found': 0,
                'events_saved': 0
            }), 404
        
        # Save events to database (similar to other scrapers)
        events_saved = 0
        events_skipped = 0
        
        for event_data in events:
            try:
                title = event_data.get('title', 'Untitled Event')
                venue_id_event = event_data.get('venue_id')
                city_id_event = event_data.get('city_id')
                start_date_str = event_data.get('start_date')
                
                # Check for duplicates
                from datetime import datetime as dt
                if start_date_str:
                    try:
                        start_date = dt.strptime(start_date_str, '%Y-%m-%d').date() if isinstance(start_date_str, str) else start_date_str
                    except:
                        start_date = None
                else:
                    start_date = None
                
                # Check if event already exists
                existing = Event.query.filter_by(
                    title=title,
                    venue_id=venue_id_event,
                    city_id=city_id_event
                )
                if start_date:
                    existing = existing.filter_by(start_date=start_date)
                
                existing_event = existing.first()
                
                if existing_event:
                    events_skipped += 1
                    continue
                
                # Create new event
                event = Event(
                    title=title,
                    description=event_data.get('description', ''),
                    start_date=start_date or date.today(),
                    end_date=event_data.get('end_date'),
                    start_time=event_data.get('start_time'),
                    end_time=event_data.get('end_time'),
                    event_type=event_data.get('event_type', 'tour'),
                    venue_id=venue_id_event,
                    city_id=city_id_event,
                    url=event_data.get('url'),
                    image_url=event_data.get('image_url'),
                    source='eventbrite',
                    source_url=event_data.get('source_url', event_data.get('url')),
                    is_registration_required=event_data.get('is_registration_required', True),
                    registration_url=event_data.get('registration_url', event_data.get('url')),
                    start_location=event_data.get('start_location', '')
                )
                
                db.session.add(event)
                events_saved += 1
                
            except Exception as e:
                app_logger.error(f"Error saving event {event_data.get('title')}: {e}")
                continue
        
        db.session.commit()
        
        app_logger.info(f"✅ Saved {events_saved} Eventbrite events, skipped {events_skipped} duplicates")
        
        return jsonify({
            'success': True,
            'message': f'Successfully scraped and saved {events_saved} events from Eventbrite',
            'events_found': len(events),
            'events_saved': events_saved,
            'events_skipped': events_skipped
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error scraping Eventbrite events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-dc-embassy-eventbrite', methods=['POST'])
def scrape_dc_embassy_eventbrite():
    """Scrape events from Eventbrite for DC embassy venues"""
    try:
        # Handle empty request body gracefully
        try:
            data = request.get_json() or {}
        except Exception as e:
            app_logger.warning(f"Could not parse request JSON: {e}, using empty dict")
            data = {}
        
        time_range = data.get('time_range', 'this_month')
        search_missing = data.get('search_missing', True)  # Default to True to search for missing organizers
        
        app_logger.info(f"Starting DC embassy Eventbrite scraping (time_range: {time_range}, search_missing: {search_missing})")
        
        # Check if Eventbrite API token is available
        import os
        eventbrite_token = os.getenv('EVENTBRITE_API_TOKEN') or os.getenv('EVENTBRITE_PRIVATE_TOKEN')
        if not eventbrite_token:
            app_logger.warning("⚠️  No Eventbrite API token found in environment variables")
            return jsonify({
                'success': False,
                'error': 'Eventbrite API token not configured. Please set EVENTBRITE_API_TOKEN in Railway environment variables.',
                'events_found': 0,
                'events_saved': 0
            }), 500
        
        # Import enhanced DC embassy scraper
        from scripts.eventbrite_scraper import scrape_dc_embassy_events
        
        # Use the scraper function - it will detect we're in an app context
        try:
            all_events = scrape_dc_embassy_events(
                city_id=None,  # Will auto-detect Washington DC
                time_range=time_range,
                search_missing=search_missing
            )
            app_logger.info(f"Scraper returned {len(all_events) if all_events else 0} events")
        except Exception as scraper_error:
            app_logger.error(f"Error in scrape_dc_embassy_events: {scraper_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Scraper error: {str(scraper_error)}',
                'events_found': 0,
                'events_saved': 0,
                'traceback': traceback.format_exc()
            }), 500
        
        if not all_events:
            # Log more details about why no events were found
            dc_city = City.query.filter(
                db.or_(
                    City.name == 'Washington',
                    City.name == 'Washington, DC',
                    City.name == 'Washington DC'
                )
            ).filter_by(country='United States').first()
            
            embassy_venues = []
            venues_with_urls = []
            venue_details = []
            if dc_city:
                embassy_venues = Venue.query.filter_by(
                    city_id=dc_city.id,
                    venue_type='embassy'
                ).all()
                venues_with_urls = [v for v in embassy_venues if v.ticketing_url and 'eventbrite' in v.ticketing_url.lower()]
                app_logger.warning(f"No events found. Found {len(embassy_venues)} embassies, {len(venues_with_urls)} with Eventbrite URLs")
                
                # Test organizer ID extraction for each venue
                from scripts.eventbrite_scraper import EventbriteScraper
                test_scraper = EventbriteScraper()
                for v in venues_with_urls:
                    organizer_id = test_scraper.extract_organizer_id_from_url(v.ticketing_url)
                    app_logger.info(f"  - {v.name}: {v.ticketing_url} → Organizer ID: {organizer_id if organizer_id else 'FAILED'}")
                    venue_details.append({
                        'name': v.name,
                        'url': v.ticketing_url,
                        'organizer_id': organizer_id if organizer_id else None
                    })
            
            return jsonify({
                'success': False,
                'error': 'No events found from DC embassy Eventbrite pages',
                'events_found': 0,
                'events_saved': 0,
                'debug_info': {
                    'embassies_found': len(embassy_venues),
                    'embassies_with_urls': len(venues_with_urls),
                    'venues_attempted': venue_details,
                    'api_token_set': bool(eventbrite_token)
                }
            }), 404
        
        # Save events to database
        events_saved = 0
        events_skipped = 0
        
        for event_data in all_events:
            try:
                title = event_data.get('title', 'Untitled Event')
                venue_id_event = event_data.get('venue_id')
                city_id_event = event_data.get('city_id')
                start_date_str = event_data.get('start_date')
                
                # Check for duplicates
                from datetime import datetime as dt
                if start_date_str:
                    try:
                        start_date = dt.strptime(start_date_str, '%Y-%m-%d').date() if isinstance(start_date_str, str) else start_date_str
                    except:
                        start_date = None
                else:
                    start_date = None
                
                # Check if event already exists
                existing = Event.query.filter_by(
                    title=title,
                    venue_id=venue_id_event,
                    city_id=city_id_event
                )
                if start_date:
                    existing = existing.filter_by(start_date=start_date)
                
                existing_event = existing.first()
                
                if existing_event:
                    events_skipped += 1
                    continue
                
                # Create new event
                event = Event(
                    title=title,
                    description=event_data.get('description', ''),
                    start_date=start_date or date.today(),
                    end_date=event_data.get('end_date'),
                    start_time=event_data.get('start_time'),
                    end_time=event_data.get('end_time'),
                    event_type=event_data.get('event_type', 'tour'),
                    venue_id=venue_id_event,
                    city_id=city_id_event,
                    url=event_data.get('url'),
                    image_url=event_data.get('image_url'),
                    source='eventbrite',
                    source_url=event_data.get('source_url', event_data.get('url')),
                    is_registration_required=event_data.get('is_registration_required', True),
                    registration_url=event_data.get('registration_url', event_data.get('url')),
                    start_location=event_data.get('start_location', '')
                )
                
                db.session.add(event)
                events_saved += 1
                
            except Exception as e:
                app_logger.error(f"Error saving event {event_data.get('title')}: {e}")
                continue
        
        db.session.commit()
        
        app_logger.info(f"✅ Saved {events_saved} DC embassy Eventbrite events, skipped {events_skipped} duplicates")
        
        return jsonify({
            'success': True,
            'message': f'Successfully scraped and saved {events_saved} events from DC embassy Eventbrite pages',
            'events_found': len(all_events),
            'events_saved': events_saved,
            'events_skipped': events_skipped
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error scraping DC embassy Eventbrite events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-npg', methods=['POST'])
def scrape_npg():
    """Scrape all NPG events: exhibitions, tours, talks, and other events."""
    try:
        app_logger.info("Starting comprehensive NPG scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting NPG scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'National Portrait Gallery',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the comprehensive NPG scraper
        from scripts.npg_scraper import scrape_all_npg_events, create_events_in_database
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 20,
            'message': 'Scraping NPG events (exhibitions, tours, talks, programs)...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all NPG events
        try:
            events = scrape_all_npg_events()
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_all_npg_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
        
        if not events:
            progress_data.update({
                'percentage': 100,
                'message': '❌ No NPG events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0,
                'events_updated': 0
            }), 404
        
        # Update progress - saving events
        progress_data.update({
            'current_step': 2,
            'percentage': 60,
            'message': f'Saving {len(events)} events to database...',
            'events_found': len(events)
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Create/update events in database
        created_count, updated_count = create_events_in_database(events)
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ NPG scraping completed! Found {len(events)} events, created {created_count} new, updated {updated_count} existing',
            'events_saved': created_count,
            'events_updated': updated_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"NPG scraping completed: found {len(events)} events, created {created_count} new events, updated {updated_count} existing events")
        
        message = f"Found {len(events)} NPG events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if updated_count > 0:
            message += f", updated {updated_count} existing events"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_updated': updated_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping NPG events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e),
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0
        }), 500

@app.route('/api/admin/scrape-suns-cinema', methods=['POST'])
def scrape_suns_cinema_endpoint():
    """Scrape all Suns Cinema movie showtimes and upcoming screenings."""
    try:
        app_logger.info("Starting Suns Cinema scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting Suns Cinema scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'Suns Cinema',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the Suns Cinema scraper
        from scripts.suns_cinema_scraper import scrape_all_suns_cinema_events
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,
            'percentage': 30,
            'message': 'Scraping movie showtimes from Suns Cinema...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape events
        events = scrape_all_suns_cinema_events()
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,
            'percentage': 100,
            'message': f'✅ Suns Cinema scraping completed! Found {len(events)} screenings.',
            'events_found': len(events),
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'message': f"Found {len(events)} screenings at Suns Cinema"
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping Suns Cinema: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-culture-dc', methods=['POST'])
def scrape_culture_dc_endpoint():
    """Scrape all Culture DC events: music, DJ sets, and upcoming performances."""
    try:
        app_logger.info("Starting Culture DC scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 1,
            'percentage': 5,
            'message': 'Starting Culture DC scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'Culture DC',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the Culture DC scraper
        from scripts.culture_dc_scraper import scrape_all_culture_dc_events
        
        # Update progress - scraping events
        progress_data.update({
            'message': 'Scraping music events from Culture DC...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape events
        events = scrape_all_culture_dc_events()
        
        # Update progress - complete
        progress_data.update({
            'percentage': 100,
            'message': f'✅ Culture DC scraping completed! Found {len(events)} events.',
            'events_found': len(events),
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'message': f"Found {len(events)} events at Culture DC"
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping Culture DC: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-asian-art', methods=['POST'])
def scrape_asian_art():
    """Scrape all Asian Art Museum events: exhibitions, tours, talks, and other events."""
    try:
        app_logger.info("Starting comprehensive Asian Art Museum scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting Asian Art Museum scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'Smithsonian National Museum of Asian Art',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the comprehensive Asian Art scraper
        from scripts.asian_art_scraper import scrape_all_asian_art_events, create_events_in_database
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 10,
            'message': 'Scraping exhibitions, events, and films...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all Asian Art Museum events
        try:
            events = scrape_all_asian_art_events()
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_all_asian_art_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
        
        if not events:
            progress_data.update({
                'current_step': 3,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 100,
                'message': '❌ No Asian Art Museum events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0,
                'events_updated': 0
            }), 404
        
        # Update progress - saving events
        progress_data.update({
            'current_step': 2,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 60,
            'message': f'Saving {len(events)} events to database...',
            'events_found': len(events)
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Create/update events in database
        created_count, updated_count = create_events_in_database(events)
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ Asian Art Museum scraping completed! Found {len(events)} events, created {created_count} new, updated {updated_count} existing',
            'events_saved': created_count,
            'events_updated': updated_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')), 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"Asian Art Museum scraping completed: found {len(events)} events, created {created_count} new events, updated {updated_count} existing events")
        
        message = f"Found {len(events)} Asian Art Museum events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if updated_count > 0:
            message += f", updated {updated_count} existing events"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_updated': updated_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping Asian Art Museum events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e),
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0
        }), 500


@app.route('/api/admin/scrape-african-art', methods=['POST'])
def scrape_african_art():
    """Scrape all African Art Museum events: exhibitions, tours, talks, and other events."""
    try:
        app_logger.info("🎨 Starting comprehensive African Art Museum scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting African Art Museum scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'Smithsonian National Museum of African Art',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the comprehensive African Art scraper
        from scripts.african_art_scraper import scrape_all_african_art_events, create_events_in_database
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 20,
            'message': 'Scraping exhibitions, events, and tours...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all African Art Museum events
        try:
            events = scrape_all_african_art_events()
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_all_african_art_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
        
        if not events:
            progress_data.update({
                'current_step': 3,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 100,
                'message': '❌ No African Art Museum events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0,
                'events_updated': 0
            }), 200  # Return 200 so frontend can handle the error message
        
        # Update progress - saving events
        progress_data.update({
            'current_step': 3,
            'percentage': 80,
            'message': f'Saving {len(events)} events to database...',
            'events_found': len(events)
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Create/update events in database
        created_count, updated_count = create_events_in_database(events)
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ African Art Museum scraping completed! Found {len(events)} events, created {created_count} new, updated {updated_count} existing',
            'events_saved': created_count,
            'events_updated': updated_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"African Art Museum scraping completed: found {len(events)} events, created {created_count} new events, updated {updated_count} existing events")
        
        message = f"Found {len(events)} African Art Museum events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if updated_count > 0:
            message += f", updated {updated_count} existing events"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_updated': updated_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping African Art Museum: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e),
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0
        }), 500

@app.route('/api/admin/scrape-hirshhorn', methods=['POST'])
def scrape_hirshhorn():
    """Scrape exhibitions and tours from Hirshhorn Museum and Sculpture Garden."""
    try:
        app_logger.info("Starting Hirshhorn Museum scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 10,
            'message': 'Starting Hirshhorn Museum scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': None,
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Find Hirshhorn venue
        hirshhorn = Venue.query.filter(
            db.func.lower(Venue.name).like('%hirshhorn%')
        ).first()
        
        if not hirshhorn:
            progress_data.update({
                'percentage': 100,
                'message': '❌ Hirshhorn Museum venue not found in database',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'Hirshhorn Museum venue not found in database',
                'events_found': 0,
                'events_saved': 0
            }), 404
        
        app_logger.info(f"Found Hirshhorn venue: {hirshhorn.name} (ID: {hirshhorn.id})")
        
        progress_data.update({
            'current_step': 2,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 20,
            'message': f'Scraping exhibitions and tours from {hirshhorn.name}...',
            'current_venue': hirshhorn.name
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the venue event scraper
        from scripts.venue_event_scraper import VenueEventScraper
        
        # Scrape Hirshhorn exhibitions and tours
        scraper = VenueEventScraper()
        
        # First scrape exhibitions
        exhibitions = []
        tours = []
        
        try:
            exhibitions = scraper.scrape_venue_events(
                venue_ids=[hirshhorn.id],
                event_type='exhibition',
                time_range='all',  # Get all current and future exhibitions
                max_exhibitions_per_venue=10,
                max_events_per_venue=10
            ) or []
            
            # Then scrape tours
            tours = scraper.scrape_venue_events(
                venue_ids=[hirshhorn.id],
                event_type='tour',
                time_range='all',  # Get all current and future tours
                max_exhibitions_per_venue=5,
                max_events_per_venue=20
            ) or []
            
            # Combine both types
            scraped_events = exhibitions + tours
            
            # Handle case where scraper returns None
            if scraped_events is None:
                app_logger.warning("Hirshhorn scraper returned None - treating as empty list")
                scraped_events = []
        except Exception as scrape_error:
            app_logger.error(f"Exception during Hirshhorn scraping: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            scraped_events = []
        
        app_logger.info(f"Scraped {len(scraped_events) if scraped_events else 0} events from Hirshhorn")
        
        # Update progress - events found
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 60,
            'message': f'Found {len(scraped_events)} events. Saving to database...',
            'events_found': len(scraped_events),
            'venues_processed': 1
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        if not scraped_events:
            return jsonify({
                'success': False,
                'error': 'No exhibitions or tours found or scraping failed. Check logs for details.',
                'events_found': 0,
                'events_saved': 0,
                'exhibitions_found': len(exhibitions) if exhibitions else 0,
                'tours_found': len(tours) if tours else 0
            }), 404
        
        # Update progress - events found
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 60,
            'message': f'Found {len(scraped_events)} events. Saving to database...',
            'events_found': len(scraped_events),
            'venues_processed': 1
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Save events to database using the same logic as the main scrape endpoint
        events_saved = 0
        events_updated = 0
        venue_exhibition_counts = {}
        max_exhibitions_per_venue = 10
        recent_events_list = []
        
        for idx, event_data in enumerate(scraped_events):
            try:
                title = event_data.get('title', 'Untitled Event')
                venue_id = event_data.get('venue_id')
                city_id_event = event_data.get('city_id', hirshhorn.city_id)
                start_date_str = event_data.get('start_date')
                event_type = event_data.get('event_type', 'exhibition')
                
                # Check for duplicates (same logic as main scrape endpoint)
                from datetime import datetime as dt
                if start_date_str:
                    start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
                else:
                    from datetime import date
                    start_date = date.today()
                
                # Check if event already exists - UPDATE instead of skip
                event_url = event_data.get('url', '')
                existing_event = None
                
                # For tours, try to match by URL first (most reliable)
                if event_type == 'tour' and event_url:
                    normalized_url = event_url.rstrip('/')
                    existing_event = Event.query.filter(
                        (Event.url == event_url) | (Event.url == normalized_url),
                        Event.event_type == 'tour',
                        Event.city_id == city_id_event
                    ).first()
                
                # If not found by URL, try title + venue + date matching
                if not existing_event:
                    existing_event = Event.query.filter_by(
                        title=title,
                        venue_id=venue_id,
                        city_id=city_id_event,
                        start_date=start_date
                    ).first()
                
                # Get time strings early for both updates and new events
                start_time_str = event_data.get('start_time')
                end_time_str = event_data.get('end_time')
                
                # If event exists, UPDATE it instead of skipping
                if existing_event:
                    app_logger.info(f"🔄 Updating existing event: '{title}' (venue_id: {venue_id}, date: {start_date})")
                    app_logger.info(f"   Current times - start: {existing_event.start_time}, end: {existing_event.end_time}")
                    app_logger.info(f"   Scraped times - start: {start_time_str}, end: {end_time_str}")
                    event = existing_event
                    updated_fields = []
                    
                    # Update fields if new data is available
                    if event_data.get('description') and event_data.get('description') != event.description:
                        event.description = event_data.get('description')
                        updated_fields.append('description')
                    
                    if event_data.get('url') and event_data.get('url') != event.url:
                        event.url = event_data.get('url')
                        updated_fields.append('url')
                    
                    if event_data.get('image_url') and event_data.get('image_url') != event.image_url:
                        event.image_url = event_data.get('image_url')
                        updated_fields.append('image_url')
                    
                    # Update times if they're missing or if new times are provided
                    if start_time_str and start_time_str != 'None' and str(start_time_str).strip():
                        try:
                            new_start_time = dt.strptime(str(start_time_str), '%H:%M:%S').time()
                        except ValueError:
                            try:
                                new_start_time = dt.strptime(str(start_time_str), '%H:%M').time()
                            except ValueError:
                                new_start_time = None
                        
                        if new_start_time:
                            old_start_time = event.start_time
                            if not event.start_time or event.start_time != new_start_time:
                                event.start_time = new_start_time
                                updated_fields.append('start_time')
                                app_logger.info(f"   ⏰ Updated start_time: {new_start_time} (was: {old_start_time})")
                    
                    if end_time_str and end_time_str != 'None' and str(end_time_str).strip():
                        try:
                            new_end_time = dt.strptime(str(end_time_str), '%H:%M:%S').time()
                        except ValueError:
                            try:
                                new_end_time = dt.strptime(str(end_time_str), '%H:%M').time()
                            except ValueError:
                                new_end_time = None
                        
                        if new_end_time:
                            old_end_time = event.end_time
                            if not event.end_time or event.end_time != new_end_time:
                                event.end_time = new_end_time
                                updated_fields.append('end_time')
                                app_logger.info(f"   ⏰ Updated end_time: {new_end_time} (was: {old_end_time})")
                    
                    # FORCED UPDATE for missing times
                    if (not event.start_time and start_time_str and start_time_str != 'None' and str(start_time_str).strip()) or \
                       (not event.end_time and end_time_str and end_time_str != 'None' and str(end_time_str).strip()):
                        if not event.start_time and start_time_str and start_time_str != 'None' and str(start_time_str).strip():
                            try:
                                new_start_time = dt.strptime(str(start_time_str), '%H:%M:%S').time()
                            except ValueError:
                                try:
                                    new_start_time = dt.strptime(str(start_time_str), '%H:%M').time()
                                except ValueError:
                                    new_start_time = None
                            if new_start_time:
                                event.start_time = new_start_time
                                if 'start_time' not in updated_fields:
                                    updated_fields.append('start_time')
                                app_logger.info(f"   ⏰ FORCED UPDATE: Added missing start_time: {new_start_time}")
                        
                        if not event.end_time and end_time_str and end_time_str != 'None' and str(end_time_str).strip():
                            try:
                                new_end_time = dt.strptime(str(end_time_str), '%H:%M:%S').time()
                            except ValueError:
                                try:
                                    new_end_time = dt.strptime(str(end_time_str), '%H:%M').time()
                                except ValueError:
                                    new_end_time = None
                            if new_end_time:
                                event.end_time = new_end_time
                                if 'end_time' not in updated_fields:
                                    updated_fields.append('end_time')
                                app_logger.info(f"   ⏰ FORCED UPDATE: Added missing end_time: {new_end_time}")
                    
                    if updated_fields:
                        app_logger.info(f"   ✅ Updated fields: {', '.join(updated_fields)}")
                        events_saved += 1
                        events_updated += 1
                        # Add to recent events
                        recent_events_list.append({
                            'title': title,
                            'event_type': event_type,
                            'start_date': start_date.isoformat(),
                            'start_time': str(event.start_time) if event.start_time else None,
                            'start_location': event.start_location
                        })
                        # Update progress every 5 events
                        if events_saved % 5 == 0:
                            progress_data.update({
                                'current_step': 3,
                                'total_steps': 3,  # Ensure total_steps is always included
                                'percentage': 60 + int((events_saved / len(scraped_events)) * 30) if scraped_events else 90,
                                'events_saved': events_saved,
                                'recent_events': recent_events_list[-10:]  # Keep last 10
                            })
                            with open('scraping_progress.json', 'w') as f:
                                json.dump(progress_data, f)
                    else:
                        app_logger.info(f"   ℹ️ No changes needed")
                    
                    # Continue to next event (don't create new one)
                    continue
                
                # Check exhibition count limit (only for new events)
                if event_type == 'exhibition' and venue_id:
                    current_count = venue_exhibition_counts.get(venue_id, 0)
                    if current_count >= max_exhibitions_per_venue:
                        continue
                    venue_exhibition_counts[venue_id] = current_count + 1
                
                # Create new event
                event = Event()
                event.title = title
                event.description = event_data.get('description', '')
                event.event_type = event_type
                event.url = event_data.get('url', '')
                event.image_url = event_data.get('image_url', '')
                event.start_date = start_date
                
                end_date_str = event_data.get('end_date')
                if end_date_str:
                    event.end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()
                
                # Times - handle both HH:MM:SS and HH:MM formats
                if start_time_str and start_time_str != 'None':
                    try:
                        event.start_time = dt.strptime(start_time_str, '%H:%M:%S').time()
                    except ValueError:
                        try:
                            event.start_time = dt.strptime(start_time_str, '%H:%M').time()
                        except ValueError:
                            app_logger.warning(f"Could not parse start_time '{start_time_str}' for event '{title}'")
                            event.start_time = None
                
                if end_time_str and end_time_str != 'None':
                    try:
                        event.end_time = dt.strptime(end_time_str, '%H:%M:%S').time()
                    except ValueError:
                        try:
                            event.end_time = dt.strptime(end_time_str, '%H:%M').time()
                        except ValueError:
                            app_logger.warning(f"Could not parse end_time '{end_time_str}' for event '{title}'")
                            event.end_time = None
                
                event.start_location = event_data.get('start_location', '')
                event.venue_id = venue_id
                event.city_id = city_id_event
                event.source = 'website'
                event.source_url = event_data.get('source_url', '')
                event.organizer = event_data.get('organizer', '')
                
                # Registration information
                if hasattr(Event, 'is_registration_required'):
                    event.is_registration_required = event_data.get('is_registration_required', False)
                if hasattr(Event, 'registration_url'):
                    event.registration_url = event_data.get('registration_url')
                if hasattr(Event, 'registration_info'):
                    event.registration_info = event_data.get('registration_info')
                
                db.session.add(event)
                events_saved += 1
                
                # Add to recent events
                recent_events_list.append({
                    'title': title,
                    'event_type': event_type,
                    'start_date': start_date.isoformat(),
                    'start_time': str(event.start_time) if event.start_time else None,
                    'start_location': event.start_location
                })
                
                # Update progress every 5 events
                if events_saved % 5 == 0:
                    progress_data.update({
                        'current_step': 3,
                        'total_steps': 3,  # Ensure total_steps is always included
                        'percentage': 60 + int((events_saved / len(scraped_events)) * 30),
                        'events_saved': events_saved,
                        'recent_events': recent_events_list[-10:]  # Keep last 10
                    })
                    with open('scraping_progress.json', 'w') as f:
                        json.dump(progress_data, f)
                
            except Exception as e:
                app_logger.error(f"Error saving event {event_data.get('title', 'Unknown')}: {e}")
                continue
        
        # Commit all events
        db.session.commit()
        
        # Final progress update
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,
            'percentage': 100,
            'message': f'✅ Scraping completed! Found {len(scraped_events)} events, saved {events_saved} ({events_updated} updated)',
            'events_saved': events_saved,
            'recent_events': recent_events_list[-10:]  # Keep last 10
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"Hirshhorn scraping completed: found {len(scraped_events)} events, saved {events_saved} ({events_updated} updated)")
        
        # Provide clearer message when events are found but skipped as duplicates
        if len(scraped_events) > 0 and events_saved == 0:
            message = f'Found {len(scraped_events)} exhibitions, but all already exist in database (skipped duplicates).'
        elif events_saved > 0:
            message = f'Successfully scraped {len(scraped_events)} exhibitions, saved {events_saved} new events to database'
        else:
            message = f'Successfully scraped {len(scraped_events)} exhibitions, saved {events_saved} to database'
        
        return jsonify({
            'success': True,
            'events_found': len(scraped_events),
            'events_saved': events_saved,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        app_logger.error(f"Error scraping Hirshhorn: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-websters', methods=['POST'])
def scrape_websters():
    """Scrape all events from Webster's Bookstore Cafe."""
    try:
        app_logger.info("Starting Webster's Bookstore Cafe scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting Webster\'s Bookstore Cafe scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'Webster\'s Bookstore Cafe',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the Webster's scraper
        from scripts.websters_scraper import scrape_websters_events, create_events_in_database
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 20,
            'message': 'Scraping Webster\'s events...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all Webster's events
        try:
            events = scrape_websters_events()
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_websters_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
        
        if not events:
            progress_data.update({
                'current_step': 3,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 100,
                'message': '❌ No Webster\'s events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0
            }), 404
        
        # Update progress - saving events
        progress_data.update({
            'current_step': 3,
            'percentage': 80,
            'message': f'Saving {len(events)} events to database...',
            'events_found': len(events)
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Create events in database
        created_count = create_events_in_database(events)
        skipped_count = len(events) - created_count
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ Webster\'s scraping completed! Found {len(events)} events, created {created_count} new, {skipped_count} already existed',
            'events_saved': created_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"Webster's scraping completed: found {len(events)} events, created {created_count} new events, skipped {skipped_count} duplicates")
        
        message = f"Found {len(events)} Webster's events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if skipped_count > 0:
            message += f", {skipped_count} already existed"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_skipped': skipped_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error scraping Webster's events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/scrape-vipassana', methods=['POST'])
def scrape_vipassana():
    """Scrape all virtual Vipassana meditation events from dhamma.org."""
    try:
        app_logger.info("Starting Vipassana virtual events scraping...")
        
        # Initialize progress tracking
        progress_data = {
            'current_step': 1,
            'total_steps': 3,
            'percentage': 5,
            'message': 'Starting Vipassana virtual events scraping...',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'events_found': 0,
            'events_saved': 0,
            'events_updated': 0,
            'venues_processed': 0,
            'total_venues': 1,
            'current_venue': 'Vipassana Meditation (Virtual)',
            'recent_events': []
        }
        
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Import the Vipassana scraper
        from scripts.vipassana_scraper import scrape_vipassana_events, create_events_in_database
        
        # Update progress - scraping events
        progress_data.update({
            'current_step': 1,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 20,
            'message': 'Scraping Vipassana virtual events...'
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Scrape all Vipassana events
        try:
            events = scrape_vipassana_events()
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_vipassana_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            # Return empty list to continue with error handling
            events = []
        
        if not events:
            progress_data.update({
                'current_step': 3,
                'total_steps': 3,  # Ensure total_steps is always included
                'percentage': 100,
                'message': '❌ No Vipassana events found or scraping failed',
                'error': True
            })
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
            return jsonify({
                'success': False,
                'error': 'No events found or scraping failed',
                'events_found': 0,
                'events_saved': 0
            }), 404
        
        # Update progress - saving events
        progress_data.update({
            'current_step': 3,
            'percentage': 80,
            'message': f'Saving {len(events)} events to database...',
            'events_found': len(events)
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        # Create events in database
        created_count = create_events_in_database(events)
        skipped_count = len(events) - created_count
        
        # Update progress - complete
        progress_data.update({
            'current_step': 3,
            'total_steps': 3,  # Ensure total_steps is always included
            'percentage': 100,
            'message': f'✅ Vipassana scraping completed! Found {len(events)} events, created {created_count} new, {skipped_count} already existed',
            'events_saved': created_count,
            'recent_events': [{'title': e.get('title', 'Unknown'), 'type': e.get('event_type', 'unknown'), 'date': str(e.get('start_date')) if e.get('start_date') else None, 'time': str(e.get('start_time')) if e.get('start_time') else None, 'location': e.get('location_name')} for e in events[:10]]
        })
        with open('scraping_progress.json', 'w') as f:
            json.dump(progress_data, f)
        
        app_logger.info(f"Vipassana scraping completed: found {len(events)} events, created {created_count} new events, skipped {skipped_count} duplicates")
        
        message = f"Found {len(events)} Vipassana events"
        if created_count > 0:
            message += f", created {created_count} new events"
        if skipped_count > 0:
            message += f", {skipped_count} already existed"
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'events_skipped': skipped_count,
            'message': message
        })
        
    except Exception as e:
        app_logger.error(f"Error in Vipassana scraping: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        
        # Update progress with error
        try:
            progress_data = {
                'percentage': 100,
                'message': f'❌ Error: {str(e)}',
                'error': True,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            with open('scraping_progress.json', 'w') as f:
                json.dump(progress_data, f)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/vipassana/scrape', methods=['POST'])
@login_required
def scrape_vipassana_separate():
    """Scrape Vipassana events into separate database"""
    try:
        app_logger.info("Starting Vipassana scraping (separate database)...")
        
        # Import the separate database
        from scripts.vipassana_database import vipassana_app, vipassana_db, VipassanaEvent, init_vipassana_database
        from scripts.vipassana_scraper import scrape_vipassana_events
        
        # Initialize database if needed
        init_vipassana_database()
        
        # Scrape events
        try:
            events = scrape_vipassana_events()
            app_logger.info(f"Scraper returned {len(events) if events else 0} events")
        except Exception as scrape_error:
            app_logger.error(f"Error in scrape_vipassana_events: {scrape_error}")
            import traceback
            app_logger.error(traceback.format_exc())
            
            # Check if it's a 401 error
            error_str = str(scrape_error).lower()
            if '401' in error_str or 'authorization required' in error_str:
                return jsonify({
                    'success': False,
                    'error': 'The page returned 401 Authorization Required. This means the page requires authentication or has IP-based access control.',
                    'events_found': 0,
                    'events_saved': 0,
                    'suggestion': 'Please verify that the URL https://www.dhamma.org/en/os/locations/virtual_events is publicly accessible in your browser. If it requires login, you may need to provide credentials or use a different approach.'
                }), 401
            
            events = []
        
        if not events:
            app_logger.warning("No events found by scraper")
            # Check if page might be JavaScript-rendered
            try:
                import cloudscraper
                test_scraper = cloudscraper.create_scraper()
                test_response = test_scraper.get('https://www.dhamma.org/en/os/locations/virtual_events', timeout=10)
                page_size = len(test_response.text)
                page_preview = test_response.text[:1000].lower()
                
                is_js_rendered = (
                    page_size < 5000 or
                    'react' in page_preview or
                    'vue' in page_preview or
                    'loading' in page_preview
                )
                
                error_msg = 'No events found. The scraper couldn\'t extract schedule information from the page.'
                suggestion = 'Please click the "Debug Scraper" button to see what the scraper found on the page.'
                
                if is_js_rendered:
                    error_msg += ' The page appears to load content dynamically via JavaScript, which the scraper cannot access.'
                    suggestion += ' The page might require a browser-based scraper (like Selenium) to access JavaScript-rendered content.'
            except Exception as check_error:
                app_logger.debug(f"Could not check if page is JS-rendered: {check_error}")
                error_msg = 'No events found. The scraper couldn\'t extract schedule information from the page.'
                suggestion = 'Please click the "Debug Scraper" button to see what the scraper found on the page.'
            
            return jsonify({
                'success': False,
                'error': error_msg,
                'events_found': 0,
                'events_saved': 0,
                'suggestion': suggestion
            }), 404
        
        # Save to separate database
        created_count = 0
        with vipassana_app.app_context():
            for event_data in events:
                try:
                    # Extract day_of_week before removing it
                    day_of_week = event_data.get('day_of_week', 'Daily')
                    
                    # Remove internal fields
                    event_data.pop('is_english', None)
                    event_data.pop('day_of_week', None)
                    
                    # Check if event already exists
                    existing = VipassanaEvent.query.filter_by(
                        title=event_data.get('title'),
                        start_time=datetime.strptime(event_data['start_time'], '%H:%M').time() if event_data.get('start_time') else None,
                        day_of_week=day_of_week
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Create new event
                    event = VipassanaEvent(
                        title=event_data.get('title', ''),
                        description=event_data.get('description', ''),
                        start_date=datetime.fromisoformat(event_data['start_date']).date(),
                        end_date=datetime.fromisoformat(event_data.get('end_date', event_data['start_date'])).date(),
                        start_time=datetime.strptime(event_data['start_time'], '%H:%M').time() if event_data.get('start_time') else None,
                        end_time=datetime.strptime(event_data['end_time'], '%H:%M').time() if event_data.get('end_time') else None,
                        url=event_data.get('url'),
                        zoom_link=event_data.get('zoom_link'),
                        zoom_password=event_data.get('zoom_password'),
                        timezone=event_data.get('timezone'),
                        location_name=event_data.get('location_name'),
                        day_of_week=day_of_week,
                        recurrence_rule=event_data.get('recurrence_rule', 'FREQ=DAILY')
                    )
                    
                    vipassana_db.session.add(event)
                    vipassana_db.session.commit()
                    created_count += 1
                except Exception as e:
                    app_logger.error(f"Error saving event: {e}")
                    vipassana_db.session.rollback()
                    continue
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'events_saved': created_count,
            'message': f'Found {len(events)} events, created {created_count} new events'
        })
        
    except Exception as e:
        app_logger.error(f"Error in Vipassana scraping (separate DB): {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/vipassana/debug', methods=['GET'])
@login_required
def debug_vipassana_scraper():
    """Debug endpoint to see what the scraper finds"""
    try:
        from scripts.vipassana_scraper import _get_vipassana_credentials
        import cloudscraper
        from bs4 import BeautifulSoup
        from requests.auth import HTTPBasicAuth
        import logging
        
        logger = logging.getLogger(__name__)
        VIPASSANA_URL = 'https://www.dhamma.org/en/os/locations/virtual_events'
        
        # Get credentials for authentication
        username, password = _get_vipassana_credentials()
        auth = None
        if username and password:
            auth = HTTPBasicAuth(username, password)
        
        # Fetch the page with authentication
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',  # Let requests handle decompression
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.dhamma.org/'
        })
        
        response = scraper.get(VIPASSANA_URL, timeout=30, auth=auth)
        
        # Check if response is actually HTML
        content_type = response.headers.get('Content-Type', '')
        logger.info(f"Response Content-Type: {content_type}")
        logger.info(f"Response status: {response.status_code}")
        
        # Try to get the text - requests should handle decompression automatically
        try:
            html_content = response.text
            # Check if it looks like binary data
            if len(html_content) > 0:
                first_chars = html_content[:100]
                # If it's mostly non-printable characters, it might be binary
                printable_count = sum(1 for c in first_chars if c.isprintable() or c in '\n\r\t')
                if printable_count < len(first_chars) * 0.5:
                    logger.warning("Response appears to be binary/compressed")
                    # Try to get raw content
                    raw_content = response.content
                    logger.info(f"Raw content length: {len(raw_content)}")
                    logger.info(f"Raw content first 100 bytes: {raw_content[:100]}")
                    # Try different decompression
                    import gzip
                    try:
                        html_content = gzip.decompress(raw_content).decode('utf-8')
                        logger.info("Successfully decompressed with gzip")
                    except:
                        try:
                            import zlib
                            html_content = zlib.decompress(raw_content).decode('utf-8')
                            logger.info("Successfully decompressed with zlib")
                        except:
                            html_content = raw_content.decode('utf-8', errors='replace')
                            logger.warning("Using raw content with error replacement")
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            html_content = response.content.decode('utf-8', errors='replace')
        
        # Check content type and encoding
        content_type = response.headers.get('Content-Type', '')
        content_encoding = response.headers.get('Content-Encoding', '')
        
        # Try to decode the response properly
        try:
            # If it's compressed, requests should handle it automatically, but let's check
            if content_encoding:
                # Response should already be decompressed by requests/cloudscraper
                pass
            
            # Try to decode as text
            if hasattr(response, 'text'):
                html_content = response.text
            else:
                # Try to decode manually
                html_content = response.content.decode('utf-8', errors='ignore')
        except Exception as decode_error:
            # If decoding fails, try different encodings
            try:
                html_content = response.content.decode('latin-1', errors='ignore')
            except:
                html_content = response.content.decode('utf-8', errors='replace')
        
        # Only parse as HTML if it looks like HTML
        if html_content.strip().startswith('<') or '<html' in html_content[:200].lower():
            soup = BeautifulSoup(html_content, 'html.parser')
        else:
            # Create empty soup if not HTML
            soup = BeautifulSoup('', 'html.parser')
            logger.warning("Response doesn't appear to be HTML - skipping parsing")
        
        # Get some basic info
        page_title = soup.find('title')
        page_text = soup.get_text()
        page_text_sample = page_text[:2000]  # Show more content
        
        # Count various elements
        tables = len(soup.find_all('table'))
        divs = len(soup.find_all('div'))
        links = len(soup.find_all('a', href=True))
        zoom_links = soup.find_all('a', href=lambda x: x and ('zoom' in x.lower() or 'zoom.us' in x.lower()) if x else False)
        teams_links = soup.find_all('a', href=lambda x: x and ('teams' in x.lower() or 'microsoft' in x.lower()) if x else False)
        meet_links = soup.find_all('a', href=lambda x: x and 'meet' in x.lower() if x else False)
        
        # Extract actual zoom/teams links
        zoom_urls = [link.get('href', '') for link in zoom_links[:10]]
        teams_urls = [link.get('href', '') for link in teams_links[:10]]
        meet_urls = [link.get('href', '') for link in meet_links[:10]]
        
        # Look for timezone patterns
        import re
        timezone_matches = []
        tz_patterns = [
            r'([A-Z]{2}),\s*([^\(]+)\s*\(([^\)]+)\)',  # "SE, Central European Time (CET)"
            r'(EST|EDT|PST|PDT|CST|CDT|MST|MDT|UTC|GMT|CET|CEST|IST|ICT|JST)',
            r'(Eastern|Central|Mountain|Pacific|European|Indochina|India)\s+(Standard|Daylight)?\s*Time',
        ]
        for pattern in tz_patterns:
            matches = re.findall(pattern, page_text, re.I)
            timezone_matches.extend([str(m) for m in matches[:10]])  # First 10 matches
        
        # Look for day+time patterns
        day_time_matches = re.findall(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)s?\s+(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?|AM|PM)', page_text, re.I)
        
        # Look for "Click to Join" or similar patterns
        join_patterns = re.findall(r'(click\s+to\s+join|join\s+meeting|join\s+link|meeting\s+link)', page_text, re.I)
        
        return jsonify({
            'page_title': page_title.get_text() if page_title else 'No title',
            'page_size': len(html_content),
            'status_code': response.status_code,
            'content_type': content_type,
            'content_encoding': content_encoding,
            'has_auth': bool(auth),
            'raw_content_preview': html_content[:500] if len(html_content) > 0 else 'Empty content',
            'is_html': html_content.strip().startswith('<') or '<html' in html_content[:200].lower(),
            'elements_found': {
                'tables': tables,
                'divs': divs,
                'links': links,
                'zoom_links': len(zoom_links),
                'teams_links': len(teams_links),
                'meet_links': len(meet_links)
            },
            'zoom_urls': zoom_urls,
            'teams_urls': teams_urls,
            'meet_urls': meet_urls,
            'timezone_matches': list(set(timezone_matches))[:15],  # Remove duplicates
            'day_time_matches': [f"{m[0]} {m[1]}:{m[2] or '00'} {m[3]}" for m in day_time_matches[:15]],
            'join_patterns': list(set(join_patterns))[:10],
            'page_text_sample': page_text_sample
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/admin/vipassana/events', methods=['GET'])
@login_required
def get_vipassana_events():
    """Get all Vipassana events from separate database"""
    try:
        from scripts.vipassana_database import vipassana_app, VipassanaEvent, init_vipassana_database
        
        # Initialize database if needed
        init_vipassana_database()
        
        with vipassana_app.app_context():
            events = VipassanaEvent.query.order_by(VipassanaEvent.created_at.desc()).all()
            events_data = [event.to_dict() for event in events]
            
            return jsonify(events_data)
    except Exception as e:
        app_logger.error(f"Error getting Vipassana events: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        # Return empty array on error instead of error object
        return jsonify([])

@app.route('/api/admin/vipassana/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_vipassana_event(event_id):
    """Delete a Vipassana event from separate database"""
    try:
        from scripts.vipassana_database import vipassana_app, vipassana_db, VipassanaEvent, init_vipassana_database
        
        # Initialize database if needed
        init_vipassana_database()
        
        with vipassana_app.app_context():
            event = VipassanaEvent.query.get(event_id)
            if not event:
                return jsonify({
                    'success': False,
                    'error': 'Event not found'
                }), 404
            
            event_title = event.title
            vipassana_db.session.delete(event)
            vipassana_db.session.commit()
            
            app_logger.info(f"Deleted Vipassana event: {event_title} (ID: {event_id})")
            
            return jsonify({
                'success': True,
                'message': f'Event "{event_title}" deleted successfully'
            })
    except Exception as e:
        app_logger.error(f"Error deleting Vipassana event: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/discover-new-venues', methods=['POST'])
def discover_new_venues():
    """Discover new venues and scrape their events."""
    try:
        logger.info("Starting venue discovery...")
        
        # Import scraping modules
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
        
        from event_scraping_system import EventScrapingOrchestrator
        
        # Discover and scrape
        orchestrator = EventScrapingOrchestrator()
        events = orchestrator.discover_and_scrape("Washington DC")
        
        return jsonify({
            'success': True,
            'events_found': len(events),
            'message': f'Successfully discovered {len(events)} events from new venues'
        })
        
    except Exception as e:
        logger.error(f"Error in venue discovery: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Venue discovery failed'
        }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    # Generic CRUD endpoints are already registered at import time
    
    # Get port from environment (Railway provides PORT), default to 5001 for local
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_ENV') != 'production'
    
    app.run(debug=debug, port=port, host='0.0.0.0')