#!/usr/bin/env python3
"""
Duplicate prevention utilities for the event planner database
"""

import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, City, Venue, Event

class DuplicatePrevention:
    """Handles duplicate prevention for all database tables"""
    
    @staticmethod
    def check_city_exists(name: str, country: str) -> Optional[City]:
        """Check if a city already exists by name and country"""
        return City.query.filter_by(name=name, country=country).first()
    
    @staticmethod
    def get_or_create_city(name: str, country: str, state: str = None, timezone: str = None) -> City:
        """Get existing city or create new one if it doesn't exist - using comprehensive geocoding"""
        # Import the comprehensive functions
        from app import format_city_name, format_country_name, get_city_details_with_geopy, get_timezone_for_city
        
        # Format names properly
        formatted_name = format_city_name(name)
        formatted_country = format_country_name(country)
        formatted_state = format_city_name(state) if state else None
        
        # Check for existing city with formatted names
        existing_city = City.query.filter_by(
            name=formatted_name, 
            country=formatted_country,
            state=formatted_state
        ).first()
        
        if existing_city:
            return existing_city
        
        # If no state provided, try to get it from geocoding
        if not formatted_state:
            try:
                city_details = get_city_details_with_geopy(formatted_name, formatted_country)
                if city_details and city_details.get('state'):
                    formatted_state = city_details['state']
            except Exception as e:
                print(f"Could not auto-detect state for {formatted_name}: {e}")
        
        # Get timezone if not provided
        if not timezone:
            timezone = get_timezone_for_city(formatted_name, formatted_country, formatted_state)
        
        # Create new city with comprehensive data
        city = City(
            name=formatted_name,
            country=formatted_country,
            state=formatted_state,
            timezone=timezone
        )
        db.session.add(city)
        db.session.commit()
        return city
    
    @staticmethod
    def check_venue_exists(name: str, city_id: int) -> Optional[Venue]:
        """Check if a venue already exists by name and city"""
        return Venue.query.filter_by(name=name, city_id=city_id).first()
    
    @staticmethod
    def get_or_create_venue(venue_data: Dict[str, Any], city_id: int) -> Venue:
        """Get existing venue or create new one if it doesn't exist"""
        existing_venue = DuplicatePrevention.check_venue_exists(venue_data['name'], city_id)
        if existing_venue:
            return existing_venue
        
        # Create new venue
        venue = Venue(
            name=venue_data['name'],
            venue_type=venue_data['venue_type'],
            address=venue_data.get('address', ''),
            latitude=venue_data.get('latitude'),
            longitude=venue_data.get('longitude'),
            image_url=venue_data.get('image_url', ''),
            instagram_url=venue_data.get('instagram_url', ''),
            facebook_url=venue_data.get('facebook_url', ''),
            twitter_url=venue_data.get('twitter_url', ''),
            youtube_url=venue_data.get('youtube_url', ''),
            tiktok_url=venue_data.get('tiktok_url', ''),
            opening_hours=venue_data.get('opening_hours', ''),
            holiday_hours=venue_data.get('holiday_hours', ''),
            phone_number=venue_data.get('phone_number', ''),
            email=venue_data.get('email', ''),
            website_url=venue_data.get('website_url', ''),
            description=venue_data.get('description', ''),
            city_id=city_id
        )
        db.session.add(venue)
        db.session.commit()
        return venue
    
    @staticmethod
    def check_event_exists(title: str, start_date: datetime.date, venue_id: int = None, city_id: int = None) -> Optional[Event]:
        """Check if an event already exists by title, start_date, and location"""
        query = Event.query.filter_by(title=title, start_date=start_date)
        
        if venue_id:
            query = query.filter_by(venue_id=venue_id)
        elif city_id:
            # For city-based events, check if any event with this city_id exists
            # This is more complex for polymorphic events
            pass
        
        return query.first()
    
    @staticmethod
    def check_event_exists(name: str, start_date: datetime.date, event_type: str, venue_id: int = None, city_id: int = None) -> Optional[Event]:
        """Check if an event already exists"""
        query = Event.query.filter_by(name=name, start_date=start_date, event_type=event_type)
        
        if venue_id:
            query = query.filter_by(venue_id=venue_id)
        elif city_id:
            query = query.filter_by(city_id=city_id)
        
        return query.first()

class DiscoveryStatusTracker:
    """Tracks venue discovery status per city"""
    
    @staticmethod
    def is_city_discovered(city_id: int) -> bool:
        """Check if venues have been discovered for this city"""
        venue_count = Venue.query.filter_by(city_id=city_id).count()
        return venue_count > 0
    
    @staticmethod
    def get_discovery_status(city_id: int) -> Dict[str, Any]:
        """Get discovery status for a city"""
        venue_count = Venue.query.filter_by(city_id=city_id).count()
        event_count = Event.query.join(Venue).filter(Venue.city_id == city_id).count()
        
        return {
            'city_id': city_id,
            'venues_discovered': venue_count > 0,
            'venue_count': venue_count,
            'event_count': event_count,
            'last_discovery': None  # Could add timestamp tracking later
        }

if __name__ == '__main__':
    # Test the duplicate prevention
    print("Testing duplicate prevention...")
    
    # Test city duplicate prevention
    city = DuplicatePrevention.get_or_create_city("Test City", "Test Country")
    print(f"Created/found city: {city.name}, {city.country}")
    
    # Test venue duplicate prevention
    venue_data = {
        'name': 'Test Venue',
        'venue_type': 'museum',
        'address': '123 Test St',
        'description': 'A test venue'
    }
    venue = DuplicatePrevention.get_or_create_venue(venue_data, city.id)
    print(f"Created/found venue: {venue.name}")
    
    print("Duplicate prevention test completed!")

