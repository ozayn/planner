#!/usr/bin/env python3
"""
Script to clear all venues and re-populate with enhanced data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue, Event

def clear_all_venues():
    """Clear all venues and related events"""
    with app.app_context():
        print("🗑️ Clearing all venues and events...")
        
        # Clear all events first (they depend on venues)
        print("Clearing events...")
        db.session.query(Event).delete()
        
        # Clear all venues
        print("Clearing venues...")
        db.session.query(Venue).delete()
        
        db.session.commit()
        print("✅ Successfully cleared all venues and events")

if __name__ == '__main__':
    clear_all_venues()

