#!/usr/bin/env python3
"""
Add events path to The Wharf DC venue's additional_info (for venue scraping)
"""

import json
import sys
sys.path.append('.')

from app import app, db, Venue, City

EVENTS_URL = 'https://www.wharfdc.com/upcoming-events/'

def add_venue_events_path():
    """Add events path to The Wharf DC venue"""
    print("🏛️ Adding events path to The Wharf DC venue...")
    
    with app.app_context():
        try:
            dc_city = City.query.filter_by(name='Washington', country='United States').first()
            if not dc_city:
                print("❌ Washington DC city not found")
                return False
            
            venue = Venue.query.filter_by(
                name='The Wharf DC',
                city_id=dc_city.id
            ).first()
            
            if not venue:
                print("❌ The Wharf DC venue not found")
                return False
            
            # Get existing additional_info
            info = {}
            if venue.additional_info:
                try:
                    info = json.loads(venue.additional_info) if isinstance(venue.additional_info, str) else venue.additional_info
                except (json.JSONDecodeError, TypeError):
                    info = {}
            
            # Add/update event_paths
            event_paths = info.get('event_paths', {})
            event_paths['events'] = EVENTS_URL
            info['event_paths'] = event_paths
            
            venue.additional_info = json.dumps(info)
            db.session.commit()
            
            print(f"✅ Added events path to The Wharf DC venue")
            print(f"   URL: {EVENTS_URL}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_venue_events_path()
    sys.exit(0 if success else 1)
