#!/usr/bin/env python3
"""
Add British Museum event paths to database
"""

import os
import sys
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

def add_british_museum_paths():
    """Add event paths for British Museum to database"""
    
    with app.app_context():
        # Find British Museum
        venue = Venue.query.filter_by(name='British Museum').first()
        
        if not venue:
            print("❌ British Museum not found in database")
            return False
        
        print(f"✅ Found British Museum (ID: {venue.id})")
        print(f"   Website: {venue.website_url}")
        
        # Prepare event paths based on user-provided knowledge
        event_paths = {
            'exhibitions': '/exhibitions-events',
            'tours': '/visit/tours-and-talks',
            'talks': '/visit/tours-and-talks'  # Same page for tours and talks
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
            print(f"✅ Successfully saved event paths for British Museum:")
            print(f"   Exhibitions: {event_paths['exhibitions']}")
            print(f"   Tours: {event_paths['tours']}")
            print(f"   Talks: {event_paths['talks']}")
            print(f"\n   Full additional_info: {venue.additional_info}")
            return True
        except Exception as e:
            print(f"❌ Error saving paths: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_british_museum_paths()
    sys.exit(0 if success else 1)
