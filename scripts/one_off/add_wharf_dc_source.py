#!/usr/bin/env python3
"""
Add The Wharf DC as an event source
"""

import sys
sys.path.append('.')

from app import app, db, Source, City

SOURCE_DATA = {
    'name': 'The Wharf DC',
    'handle': 'wharfdc.com',
    'source_type': 'website',
    'url': 'https://www.wharfdc.com/upcoming-events/',
    'description': "The Wharf DC's upcoming events - live music, festivals, outdoor movies, boat parades, fireworks, curling, Mardi Gras, Bloomaroo, and more waterfront activities.",
    'city_id': 1,
    'event_types': '["cultural_events", "festivals", "music", "family", "outdoor"]',
}

def add_wharf_dc_source():
    """Add The Wharf DC as an event source"""
    print("🏛️ Adding The Wharf DC as event source...")
    
    with app.app_context():
        try:
            dc_city = City.query.filter_by(name='Washington', country='United States').first()
            if not dc_city:
                print("❌ Washington DC city not found in database")
                return False
            
            existing = Source.query.filter_by(
                name=SOURCE_DATA['name'],
                city_id=dc_city.id
            ).first()
            
            if existing:
                # Update URL if different
                if existing.url != SOURCE_DATA['url']:
                    existing.url = SOURCE_DATA['url']
                    db.session.commit()
                    print(f"✅ Updated source URL: {SOURCE_DATA['url']}")
                else:
                    print(f"⚠️  '{SOURCE_DATA['name']}' source already exists (ID: {existing.id})")
                return True
            
            source = Source(
                name=SOURCE_DATA['name'],
                handle=SOURCE_DATA['handle'],
                source_type=SOURCE_DATA['source_type'],
                url=SOURCE_DATA['url'],
                description=SOURCE_DATA['description'],
                city_id=dc_city.id,
                event_types=SOURCE_DATA['event_types'],
                is_active=True,
            )
            
            db.session.add(source)
            db.session.commit()
            
            print(f"✅ Added '{SOURCE_DATA['name']}' as event source (ID: {source.id})")
            
            try:
                from scripts.update_sources_json import update_sources_json
                update_sources_json()
            except Exception as e:
                print(f"⚠️  Could not update sources.json: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_wharf_dc_source()
    sys.exit(0 if success else 1)
