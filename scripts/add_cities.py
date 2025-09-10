#!/usr/bin/env python3
"""
Add cities to the database using comprehensive geocoding and timezone lookup
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, get_timezone_for_city, get_city_details_with_geopy, format_city_name, format_country_name

def add_cities():
    """Add initial cities to the database with comprehensive geocoding"""
    cities_data = [
        {'name': 'Washington', 'country': 'United States'},
        {'name': 'New York', 'country': 'United States'},
        {'name': 'Los Angeles', 'country': 'United States'},
        {'name': 'San Francisco', 'country': 'United States'},
        {'name': 'Chicago', 'country': 'United States'},
        {'name': 'Boston', 'country': 'United States'},
        {'name': 'Seattle', 'country': 'United States'},
        {'name': 'Miami', 'country': 'United States'},
        {'name': 'London', 'country': 'United Kingdom'},
        {'name': 'Paris', 'country': 'France'},
        {'name': 'Tokyo', 'country': 'Japan'},
        {'name': 'Sydney', 'country': 'Australia'},
        {'name': 'Montreal', 'country': 'Canada'},
        {'name': 'Toronto', 'country': 'Canada'},
        {'name': 'Vancouver', 'country': 'Canada'},
    ]
    
    with app.app_context():
        # Check if cities already exist
        existing_cities = City.query.count()
        if existing_cities > 0:
            print(f"✅ {existing_cities} cities already exist in database")
            return
        
        # Add cities with comprehensive geocoding
        for city_data in cities_data:
            # Format names properly
            formatted_name = format_city_name(city_data['name'])
            formatted_country = format_country_name(city_data['country'])
            
            # Get comprehensive city details using geocoding
            city_details = get_city_details_with_geopy(formatted_name, formatted_country)
            
            if city_details:
                state = city_details.get('state')
                timezone = get_timezone_for_city(formatted_name, formatted_country, state)
                
                city = City(
                    name=formatted_name,
                    state=state,
                    country=formatted_country,
                    timezone=timezone
                )
                
                db.session.add(city)
                print(f"✅ Added {formatted_name}, {formatted_country} (state: {state or 'N/A'}, timezone: {timezone})")
            else:
                # Fallback if geocoding fails
                timezone = get_timezone_for_city(formatted_name, formatted_country)
                
                city = City(
                    name=formatted_name,
                    state=None,
                    country=formatted_country,
                    timezone=timezone
                )
                
                db.session.add(city)
                print(f"✅ Added {formatted_name}, {formatted_country} (state: N/A, timezone: {timezone}) [fallback]")
        
        db.session.commit()
        print(f"✅ Added {len(cities_data)} cities to database with comprehensive geocoding")

if __name__ == '__main__':
    add_cities()

