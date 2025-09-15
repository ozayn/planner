#!/usr/bin/env python3
"""
Script to remove duplicate cities and clean up city data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue, Event

def remove_duplicate_cities():
    """Remove duplicate city entries"""
    with app.app_context():
        print("🏙️ Cleaning up duplicate cities...")
        
        # Get all cities
        cities = City.query.all()
        print(f"Found {len(cities)} cities:")
        for city in cities:
            print(f"  ID {city.id}: {city.name}, {city.state}, {city.country}")
        
        # Remove all duplicate "New York" entries except the first one
        new_york_cities = City.query.filter(
            City.name.like('%New York%')
        ).all()
        
        if len(new_york_cities) > 1:
            print(f"\n🗑️ Found {len(new_york_cities)} New York cities, keeping only the first one")
            # Keep the first one, delete the rest
            for city in new_york_cities[1:]:
                print(f"  Removing: {city.name}, {city.state} (ID: {city.id})")
                db.session.delete(city)
            db.session.commit()
            print("✅ Duplicate cities removed")
        else:
            print("ℹ️ No duplicate cities found")
        
        # Verify final state
        cities = City.query.all()
        print(f"\n📊 Final city count: {len(cities)}")
        for city in cities:
            print(f"  ID {city.id}: {city.name}, {city.state}, {city.country}")

if __name__ == '__main__':
    remove_duplicate_cities()
