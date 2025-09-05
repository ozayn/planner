from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import pytz

# This will be initialized in app.py
db = SQLAlchemy()

class City(db.Model):
    """Cities where events take place"""
    __tablename__ = 'cities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    timezone = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    venues = db.relationship('Venue', backref='city', lazy=True)
    festivals = db.relationship('Festival', backref='city', lazy=True)
    photowalks = db.relationship('Photowalk', backref='city', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'country': self.country,
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

def setup_relationships():
    """Setup model relationships"""
    # Relationships are defined in the model classes themselves
    pass