#!/usr/bin/env python3
"""
Add The Wharf DC to DC venues
"""

import sys
sys.path.append('.')

from app import app, db, Venue, City

VENUE_DATA = {
    'name': 'The Wharf DC',
    'address': '760 Maine Ave SW, Washington, DC 20024',
    'latitude': 38.8806,
    'longitude': -77.0249,
    'description': "Washington DC's waterfront destination featuring restaurants, shops, entertainment venues, piers, and year-round activities. One mile of waterfront with kayaking, paddleboarding, ice rink, concerts, and events. Near Waterfront Metro.",
    'venue_type': 'waterfront',
    'phone_number': '',
    'website_url': 'https://www.wharfdc.com',
    'opening_hours': 'Hours vary by business',
    'admission_fee': 'Free to explore; events and activities vary',
}

def add_wharf_dc():
    """Add The Wharf DC to the venues database"""
    print("🏛️ Adding The Wharf DC to DC venues...")
    
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
    success = add_wharf_dc()
    sys.exit(0 if success else 1)
