import os
import sys
import json
import re
import logging
from datetime import datetime, timedelta, date

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
    from flask import Flask, render_template, request, jsonify
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
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
csrf = CSRFProtect(app)

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
        formatted_state = format_city_name(state) if state else None
        
        # Check for duplicates using the new duplicate checking function
        from scripts.utils import check_city_duplicate_active
        print(f"🔍 Checking for duplicates: {formatted_name}, {formatted_state}, {formatted_country}")
        duplicate_city, duplicate_type = check_city_duplicate_active(formatted_name, formatted_state, formatted_country)
        print(f"🔍 Duplicate check result: {duplicate_city}, {duplicate_type}")
        if duplicate_city:
            if duplicate_type == "exact":
                return jsonify({'error': f'City "{formatted_name}" already exists (ID: {duplicate_city.id})'}), 400
            elif duplicate_type == "variation":
                return jsonify({'error': f'Similar city already exists: "{duplicate_city.name}" (ID: {duplicate_city.id}). Please use the existing city or choose a different name.'}), 400
            else:
                return jsonify({'error': f'City with similar name already exists: "{duplicate_city.name}" (ID: {duplicate_city.id})'}), 400
        
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
        
        # Sync the new city to predefined JSON
        try:
            sync_cities_to_predefined_json()
        except Exception as sync_error:
            print(f"⚠️ Warning: Could not sync city to predefined JSON: {sync_error}")
        
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
db_dir = os.path.expanduser('~/.local/share/planner')
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'events.db')

# Set the database URI explicitly
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    events = db.relationship('Event', backref='venue', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'venue_type': self.venue_type,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'image_url': self.image_url,
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
    
    def to_dict(self):
        """Convert event to dictionary with all relevant fields"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'image_url': self.image_url,
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

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
        end_date = (now + timedelta(days=7)).date()
    elif time_range == 'this_month':
        start_date = now.date()
        end_date = (now + timedelta(days=30)).date()
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
    """Get venues for a specific city"""
    city_id = request.args.get('city_id')
    venue_type = request.args.get('venue_type')
    
    if not city_id:
        return jsonify({'error': 'City ID is required'}), 400
    
    query = Venue.query.filter(Venue.city_id == city_id)
    
    if venue_type:
        query = query.filter(Venue.venue_type == venue_type)
    
    venues = query.all()
    return jsonify([venue.to_dict() for venue in venues])

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

@app.route('/api/scrape', methods=['POST'])
def trigger_scraping():
    """Trigger the scraping process to refresh event data"""
    try:
        import subprocess
        import json
        
        # Get parameters from request
        data = request.get_json() or {}
        city_id = data.get('city_id')
        event_type = data.get('event_type', '')
        time_range = data.get('time_range', 'today')
        
        # Get city information
        if city_id:
            city = db.session.get(City, city_id)
            if not city:
                return jsonify({'error': 'City not found'}), 404
            city_name = city.name
        else:
            city_name = 'Washington DC'  # Default for now
        
        # For now, we'll use the existing DC scraper but could be extended
        # to support different cities and event types
        
        # Run the DC scraper
        scraper_result = subprocess.run([
            sys.executable, 'scripts/dc_scraper_progress.py'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if scraper_result.returncode != 0:
            return jsonify({
                'error': 'Scraping failed',
                'stderr': scraper_result.stderr
            }), 500
        
        # Run the seed script to update the database
        seed_result = subprocess.run([
            sys.executable, 'scripts/seed_dc_data.py'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if seed_result.returncode != 0:
            return jsonify({
                'error': 'Database seeding failed',
                'stderr': seed_result.stderr
            }), 500
        
        # Try to parse the scraper output to get event count
        try:
            with open('dc_scraped_data.json', 'r') as f:
                scraped_data = json.load(f)
                events_added = len(scraped_data.get('events', []))
        except:
            events_added = 'unknown'
        
        return jsonify({
            'message': f'Scraping completed successfully for {city_name}',
            'events_added': events_added,
            'city': city_name,
            'event_type': event_type,
            'time_range': time_range,
            'scraper_output': scraper_result.stdout,
            'seed_output': seed_result.stdout
        })
        
    except Exception as e:
        print(f"Scraping error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Scraping failed',
            'details': str(e)
        }), 500

@app.route('/admin')
def admin():
    """Admin interface"""
    return render_template('admin.html')

@app.route('/test-admin')
def test_admin():
    """Test admin page"""
    return render_template('test_admin.html')

@app.route('/admin-simple')
def admin_simple():
    """Simple admin page"""
    return render_template('admin_simple.html')

@app.route('/admin-test')
def admin_test():
    """Test admin page"""
    return render_template('admin_test.html')

@app.route('/api/admin/stats')
def admin_stats():
    """Get admin statistics"""
    try:
        cities_count = City.query.count()
        venues_count = Venue.query.count()
        events_count = Event.query.count()
        
        return jsonify({
            'cities': cities_count,
            'venues': venues_count,
            'events': events_count
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
            
            cities_data.append({
                'id': city.id,
                'name': city.name,
                'state': city.state,
                'country': city.country,
                'timezone': city.timezone,
                'display_name': city.to_dict()['display_name'],
                'venue_count': venue_count,
                'event_count': event_count,
                'created_at': city.created_at.isoformat() if city.created_at else None
            })
        
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
            venue_dict['city_name'] = venue.city.name if venue.city else 'Unknown'
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
            events_data.append({
                'id': event.id,
                'title': event.title,
                'event_type': event.event_type,
                'start_date': event.start_date.isoformat() if event.start_date else None,
                'end_date': event.end_date.isoformat() if event.end_date else None,
                'venue_id': event.venue_id,
                'city_id': event.city_id,
                'venue_name': event.venue.name if event.venue else None,
                'city_name': event.city.name if event.city else 'Unknown',
                'created_at': event.created_at.isoformat() if event.created_at else None
            })
        
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
        
        return jsonify({
            'success': True,
            'message': f'City "{city.name}" updated successfully',
            'city': city.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating city: {e}")
        return jsonify({'error': str(e)}), 500

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
        
        return jsonify({
            'success': True,
            'message': f'Event "{title}" added successfully',
            'event_id': event.id
        })
        
    except Exception as e:
        db.session.rollback()
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
        
        return jsonify({
            'success': True,
            'message': f'Venue "{name}" added successfully',
            'venue_id': venue.id
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
            'difficulty_level': 'Beginner' if event_type == 'photowalk' else None,
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Generic CRUD endpoints are already registered at import time
    
    # Run on port 5001 to avoid port 5000
    app.run(debug=True, port=5001)