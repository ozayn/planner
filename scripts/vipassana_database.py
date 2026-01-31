#!/usr/bin/env python3
"""
Separate database for Vipassana events
This uses a separate SQLite database to keep Vipassana events isolated
"""
import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create a separate Flask app instance for Vipassana database
vipassana_app = Flask(__name__)

# Use a separate database file
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'vipassana_events.db')
vipassana_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
vipassana_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create separate database instance
vipassana_db = SQLAlchemy(vipassana_app)

# Define simplified Event model for Vipassana
class VipassanaEvent(vipassana_db.Model):
    """Vipassana event model - simplified version"""
    __tablename__ = 'vipassana_events'
    
    id = vipassana_db.Column(vipassana_db.Integer, primary_key=True)
    title = vipassana_db.Column(vipassana_db.String(200), nullable=False)
    description = vipassana_db.Column(vipassana_db.Text)
    start_date = vipassana_db.Column(vipassana_db.Date, nullable=False)
    end_date = vipassana_db.Column(vipassana_db.Date)
    start_time = vipassana_db.Column(vipassana_db.Time)
    end_time = vipassana_db.Column(vipassana_db.Time)
    url = vipassana_db.Column(vipassana_db.String(1000))
    zoom_link = vipassana_db.Column(vipassana_db.String(1000))
    zoom_password = vipassana_db.Column(vipassana_db.String(100))
    timezone = vipassana_db.Column(vipassana_db.String(100))
    location_name = vipassana_db.Column(vipassana_db.String(200))
    day_of_week = vipassana_db.Column(vipassana_db.String(20))  # Monday, Tuesday, etc. or 'Daily'
    recurrence_rule = vipassana_db.Column(vipassana_db.String(100))  # e.g., 'FREQ=WEEKLY;BYDAY=WE'
    created_at = vipassana_db.Column(vipassana_db.DateTime, default=datetime.utcnow)
    updated_at = vipassana_db.Column(vipassana_db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'url': self.url,
            'zoom_link': self.zoom_link,
            'zoom_password': self.zoom_password,
            'timezone': self.timezone,
            'location_name': self.location_name,
            'day_of_week': self.day_of_week,
            'recurrence_rule': self.recurrence_rule,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Initialize database
def init_vipassana_database():
    """Initialize the Vipassana database"""
    with vipassana_app.app_context():
        vipassana_db.create_all()
        print(f"✅ Vipassana database initialized: {db_path}")

if __name__ == '__main__':
    init_vipassana_database()
