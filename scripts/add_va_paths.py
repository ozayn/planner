#!/usr/bin/env python3
"""
Add Victoria and Albert Museum event paths to database
"""

import os
import sys
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

def add_va_paths():
    """Add event paths for Victoria and Albert Museum to database"""
    
    with app.app_context():
        # Find V&A - try different name variations
        venue = None
        for name_variant in ['Victoria and Albert Museum', 'V&A', 'V & A Museum']:
            venue = Venue.query.filter_by(name=name_variant).first()
            if venue:
                break
        
        # Also try by URL
        if not venue:
            venue = Venue.query.filter(Venue.website_url.like('%vam.ac.uk%')).first()
        
        if not venue:
            print("❌ Victoria and Albert Museum not found in database")
            print("   Searching for similar venues...")
            venues = Venue.query.filter(
                (Venue.name.like('%Victoria%')) | 
                (Venue.name.like('%Albert%'))
            ).all()
            for v in venues:
                print(f"   Found: {v.name} (ID: {v.id})")
            return False
        
        print(f"✅ Found {venue.name} (ID: {venue.id})")
        print(f"   Website: {venue.website_url}")
        
        # Prepare event paths - exhibitions are at /whatson
        event_paths = {
            'exhibitions': '/whatson',
            'events': '/whatson'  # Same page has exhibitions, talks, workshops, etc.
        }
        
        # Get existing additional_info
        if venue.additional_info:
            try:
                info = json.loads(venue.additional_info) if isinstance(venue.additional_info, str) else venue.additional_info
            except (json.JSONDecodeError, TypeError):
                info = {}
        else:
            info = {}
        
        # Update with event paths
        info['event_paths'] = event_paths
        
        # Save back to venue
        venue.additional_info = json.dumps(info)
        
        try:
            db.session.commit()
            print(f"✅ Successfully saved event paths for {venue.name}:")
            print(f"   Exhibitions: {event_paths['exhibitions']}")
            print(f"   Events: {event_paths['events']}")
            print(f"\n   Full additional_info: {venue.additional_info}")
            return True
        except Exception as e:
            print(f"❌ Error saving paths: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_va_paths()
    sys.exit(0 if success else 1)
