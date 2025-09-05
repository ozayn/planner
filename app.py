import os
import sys
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/events.db')
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    venues = db.relationship('Venue', backref='city', lazy=True)
    festivals = db.relationship('Festival', backref='city', lazy=True)
    photowalks = db.relationship('Photowalk', backref='city', lazy=True)
    
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
            'timezone': self.timezone
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
    website_url = db.Column(db.String(200))
    description = db.Column(db.Text)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tours = db.relationship('Tour', backref='venue', lazy=True)
    exhibitions = db.relationship('Exhibition', backref='venue', lazy=True)
    
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
            'website_url': self.website_url,
            'description': self.description,
            'city_id': self.city_id
        }

class Event(db.Model):
    """Base event class"""
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50))
    
    __mapper_args__ = {
        'polymorphic_identity': 'event',
        'polymorphic_on': event_type
    }
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'image_url': self.image_url,
            'url': self.url,
            'is_selected': self.is_selected,
            'event_type': self.event_type
        }

class Tour(Event):
    """Museum tours and guided tours"""
    __tablename__ = 'tours'
    
    id = db.Column(db.Integer, db.ForeignKey('events.id'), primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    meeting_location = db.Column(db.String(200))
    tour_type = db.Column(db.String(50))
    max_participants = db.Column(db.Integer)
    price = db.Column(db.Float)
    language = db.Column(db.String(50), default='English')
    
    __mapper_args__ = {
        'polymorphic_identity': 'tour'
    }
    
    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({
            'venue_id': self.venue_id,
            'venue_name': self.venue.name if self.venue else None,
            'meeting_location': self.meeting_location,
            'tour_type': self.tour_type,
            'max_participants': self.max_participants,
            'price': self.price,
            'language': self.language
        })
        return base_dict

class Exhibition(Event):
    """Museum exhibitions"""
    __tablename__ = 'exhibitions'
    
    id = db.Column(db.Integer, db.ForeignKey('events.id'), primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    exhibition_location = db.Column(db.String(200))
    curator = db.Column(db.String(200))
    admission_price = db.Column(db.Float)
    
    __mapper_args__ = {
        'polymorphic_identity': 'exhibition'
    }
    
    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({
            'venue_id': self.venue_id,
            'venue_name': self.venue.name if self.venue else None,
            'exhibition_location': self.exhibition_location,
            'curator': self.curator,
            'admission_price': self.admission_price
        })
        return base_dict

class Festival(Event):
    """Festivals and multi-day events"""
    __tablename__ = 'festivals'
    
    id = db.Column(db.Integer, db.ForeignKey('events.id'), primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    festival_type = db.Column(db.String(100))
    multiple_locations = db.Column(db.Boolean, default=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'festival'
    }
    
    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({
            'city_id': self.city_id,
            'city_name': self.city.name if self.city else None,
            'festival_type': self.festival_type,
            'multiple_locations': self.multiple_locations
        })
        return base_dict

class Photowalk(Event):
    """Photography walks and photo events"""
    __tablename__ = 'photowalks'
    
    id = db.Column(db.Integer, db.ForeignKey('events.id'), primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    start_location = db.Column(db.String(200))
    end_location = db.Column(db.String(200))
    start_latitude = db.Column(db.Float)
    start_longitude = db.Column(db.Float)
    end_latitude = db.Column(db.Float)
    end_longitude = db.Column(db.Float)
    difficulty_level = db.Column(db.String(50))
    equipment_needed = db.Column(db.Text)
    organizer = db.Column(db.String(200))
    
    __mapper_args__ = {
        'polymorphic_identity': 'photowalk'
    }
    
    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({
            'city_id': self.city_id,
            'city_name': self.city.name if self.city else None,
            'start_location': self.start_location,
            'end_location': self.end_location,
            'start_latitude': self.start_latitude,
            'start_longitude': self.start_longitude,
            'end_latitude': self.end_latitude,
            'end_longitude': self.end_longitude,
            'difficulty_level': self.difficulty_level,
            'equipment_needed': self.equipment_needed,
            'organizer': self.organizer
        })
        return base_dict

@app.route('/')
def index():
    """Main page with city selection and time filtering"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Test page"""
    return render_template('test.html')

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
    
    city = City.query.get(city_id)
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
    
    if not event_type or event_type == 'tours':
        tours = Tour.query.filter(
            Tour.venue.has(Venue.city_id == city_id),
            Tour.start_date >= start_date,
            Tour.start_date <= end_date
        ).all()
        events.extend([tour.to_dict() for tour in tours])
    
    if not event_type or event_type == 'exhibitions':
        exhibitions = Exhibition.query.filter(
            Exhibition.venue.has(Venue.city_id == city_id),
            Exhibition.start_date <= end_date,
            Exhibition.end_date >= start_date
        ).all()
        events.extend([exhibition.to_dict() for exhibition in exhibitions])
    
    if not event_type or event_type == 'festivals':
        festivals = Festival.query.filter(
            Festival.city_id == city_id,
            Festival.start_date <= end_date,
            Festival.end_date >= start_date
        ).all()
        events.extend([festival.to_dict() for festival in festivals])
    
    if not event_type or event_type == 'photowalks':
        photowalks = Photowalk.query.filter(
            Photowalk.city_id == city_id,
            Photowalk.start_date >= start_date,
            Photowalk.start_date <= end_date
        ).all()
        events.extend([photowalk.to_dict() for photowalk in photowalks])
    
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

@app.route('/api/calendar/add', methods=['POST'])
def add_to_calendar():
    """Add event to Google Calendar"""
    try:
        data = request.get_json()
        event_id = data.get('event_id')
        event_type = data.get('event_type')
        
        if not event_id or not event_type:
            return jsonify({'error': 'Event ID and type are required'}), 400
        
        # Get city timezone
        city_id = data.get('city_id')
        if not city_id:
            return jsonify({'error': 'City ID is required'}), 400
        
        city = City.query.get(city_id)
        if not city:
            return jsonify({'error': 'City not found'}), 404
        
        # Get event data based on type
        event_data = None
        if event_type == 'tour':
            tour = Tour.query.get(event_id)
            if tour:
                event_data = {
                    'title': tour.title,
                    'description': tour.description,
                    'start_time': tour.start_time.strftime('%H:%M') if tour.start_time else None,
                    'end_time': tour.end_time.strftime('%H:%M') if tour.end_time else None,
                    'start_date': data.get('start_date', date.today().isoformat()),
                    'meeting_location': tour.meeting_location,
                    'venue_name': tour.venue.name if tour.venue else None,
                    'url': tour.url
                }
        elif event_type == 'exhibition':
            exhibition = Exhibition.query.get(event_id)
            if exhibition:
                event_data = {
                    'title': exhibition.title,
                    'description': exhibition.description,
                    'start_date': exhibition.start_date.isoformat(),
                    'end_date': exhibition.end_date.isoformat(),
                    'exhibition_location': exhibition.exhibition_location,
                    'venue_name': exhibition.venue.name if exhibition.venue else None,
                    'url': exhibition.url
                }
        
        if not event_data:
            return jsonify({'error': 'Event not found'}), 404
        
        # Try to create calendar event
        try:
            from config.calendar_service import get_calendar_service, CalendarEventBuilder
            
            calendar_service = get_calendar_service()
            if calendar_service:
                # Build calendar event based on type
                if event_type == 'tour':
                    calendar_event = CalendarEventBuilder.build_tour_event(event_data, city.timezone)
                elif event_type == 'exhibition':
                    calendar_event = CalendarEventBuilder.build_exhibition_event(event_data, city.timezone)
                else:
                    return jsonify({'error': 'Unsupported event type'}), 400
                
                # Create the event
                calendar_event_id = calendar_service.create_event(calendar_event)
                
                if calendar_event_id:
                    return jsonify({
                        'message': 'Event added to Google Calendar successfully',
                        'calendar_event_id': calendar_event_id
                    })
                else:
                    return jsonify({'error': 'Failed to create calendar event'}), 500
            else:
                # Fallback to demo mode if calendar service not available
                return jsonify({
                    'message': 'Event added to calendar successfully (demo mode - Google Calendar not configured)',
                    'calendar_event_id': f'demo_{event_id}'
                })
                
        except ImportError:
            # Calendar service not available
            return jsonify({
                'message': 'Event added to calendar successfully (demo mode - Google Calendar not configured)',
                'calendar_event_id': f'demo_{event_id}'
            })
        except Exception as calendar_error:
            print(f"Calendar service error: {calendar_error}")
            return jsonify({
                'message': 'Event added to calendar successfully (demo mode - Calendar service error)',
                'calendar_event_id': f'demo_{event_id}'
            })
            
    except Exception as e:
        print(f"Error adding event to calendar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

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
            city = City.query.get(city_id)
            if not city:
                return jsonify({'error': 'City not found'}), 404
            city_name = city.name
        else:
            city_name = 'Washington DC'  # Default for now
        
        # For now, we'll use the existing DC scraper but could be extended
        # to support different cities and event types
        
        # Run the DC scraper
        scraper_result = subprocess.run([
            sys.executable, 'scripts/dc_scraper.py'
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Run on port 5001 to avoid port 5000
    app.run(debug=True, port=5001)