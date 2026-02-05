#!/usr/bin/env python3
"""
Add Mexican Cultural Institute to DC venues
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue, City

VENUE_DATA = {
    'name': 'Mexican Cultural Institute',
    'address': '2829 16th St NW, Washington, DC 20009',
    'latitude': 38.9260,
    'longitude': -77.0370,
    'description': 'Mexican Cultural Institute of Washington DC hosts cultural events including exhibitions, music, film screenings, talks, lectures, conferences, and culinary events. Occupies a beaux-arts mansion with Rivera-esque murals.',
    'venue_type': 'cultural_center',
    'phone_number': '(202) 728-1628',
    'website_url': 'https://instituteofmexicodc.org',
    'opening_hours': 'Monday-Friday: 10:00 AM - 6:00 PM, Saturday: 12:00 PM - 4:00 PM',
    'admission_fee': 'Free',
}

def add_mexican_cultural_institute():
    """Add Mexican Cultural Institute to the venues database"""
    print("🏛️ Adding Mexican Cultural Institute to DC venues...")
    
    with app.app_context():
        try:
            dc_city = City.query.filter_by(name='Washington', country='United States').first()
            if not dc_city:
                print("❌ Washington DC city not found in database")
                return False
            
            existing = Venue.query.filter_by(
                name=VENUE_DATA['name'],
                city_id=dc_city.id
            ).first()
            
            if existing:
                print(f"⚠️  '{VENUE_DATA['name']}' already exists (ID: {existing.id})")
                return True
            
            venue = Venue(
                name=VENUE_DATA['name'],
                address=VENUE_DATA['address'],
                city_id=dc_city.id,
                latitude=VENUE_DATA['latitude'],
                longitude=VENUE_DATA['longitude'],
                description=VENUE_DATA['description'],
                venue_type=VENUE_DATA['venue_type'],
                phone_number=VENUE_DATA['phone_number'],
                website_url=VENUE_DATA['website_url'],
                opening_hours=VENUE_DATA['opening_hours'],
                admission_fee=VENUE_DATA['admission_fee'],
            )
            
            db.session.add(venue)
            db.session.commit()
            
            print(f"✅ Added '{VENUE_DATA['name']}' to DC venues (ID: {venue.id})")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_mexican_cultural_institute()
    sys.exit(0 if success else 1)
