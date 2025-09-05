#!/usr/bin/env python3
"""
Minimal script to seed only cities - no sample events
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import app, db, City
import pytz

def seed_cities_only():
    """Seed only cities with their timezones - no events"""
    cities_data = [
        {'name': 'Washington', 'state': 'DC', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'New York', 'state': 'NY', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'Baltimore', 'state': 'MD', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'Philadelphia', 'state': 'PA', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'London', 'state': None, 'country': 'United Kingdom', 'timezone': 'Europe/London'},
        {'name': 'Los Angeles', 'state': 'CA', 'country': 'United States', 'timezone': 'America/Los_Angeles'},
        {'name': 'Paris', 'state': None, 'country': 'France', 'timezone': 'Europe/Paris'},
        {'name': 'Tokyo', 'state': None, 'country': 'Japan', 'timezone': 'Asia/Tokyo'},
        {'name': 'Sydney', 'state': None, 'country': 'Australia', 'timezone': 'Australia/Sydney'},
    ]
    
    with app.app_context():
        # Create all tables first
        db.create_all()
        
        for city_data in cities_data:
            city = City.query.filter_by(name=city_data['name']).first()
            if not city:
                city = City(**city_data)
                db.session.add(city)
        
        db.session.commit()
        print("Cities seeded successfully - no sample events")

if __name__ == '__main__':
    seed_cities_only()
