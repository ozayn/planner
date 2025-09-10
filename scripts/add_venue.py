#!/usr/bin/env python3
"""
Manual venue addition with automatic detail fetching using LLM
Takes a venue name and city, then uses LLM to find comprehensive details
"""

import sys
import os
import json
import argparse
from typing import Optional, Dict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue
from scripts.fetch_venue_details import LLMVenueDetailSearcher
from scripts.duplicate_prevention import DuplicatePrevention

def add_venue_manually(venue_name: str, city_name: str, venue_type: str = 'museum', output_json: bool = True):
    """
    Add a venue manually with automatic detail fetching using LLM
    
    Args:
        venue_name: Name of the venue to add
        city_name: Name of the city
        venue_type: Type of venue (museum, gallery, etc.)
        output_json: If True, return JSON data instead of printing
    """
    import sys
    from io import StringIO
    
    # Suppress print statements when output_json=True
    if output_json:
        old_stdout = sys.stdout
        sys.stdout = StringIO()
    
    with app.app_context():
        # Find the city
        city = City.query.filter_by(name=city_name).first()
        if not city:
            if output_json:
                sys.stdout = old_stdout
                return {'error': f"City '{city_name}' not found in database"}
            else:
                print(f"❌ City '{city_name}' not found in database")
                return
        
        if not output_json:
            print(f"\n🔍 Adding venue '{venue_name}' to {city_name}...")
        
        # Check if venue already exists using duplicate prevention
        existing_venue = DuplicatePrevention.check_venue_exists(venue_name, city.id)
        if existing_venue:
            if output_json:
                sys.stdout = old_stdout
                return {'error': f"Venue '{venue_name}' already exists in {city_name}"}
            else:
                print(f"⚠️  Venue '{venue_name}' already exists in {city_name}")
                return
        
        # Initialize LLM detail searcher
        detail_searcher = LLMVenueDetailSearcher(silent=output_json)
        
        # Search for comprehensive venue details using LLM
        if not output_json:
            print(f"🔍 Searching LLM for comprehensive details about {venue_name}...")
        details = detail_searcher.search_venue_details(
            venue_name,
            city_name,
            '',  # No specific address provided
            silent=output_json  # Silent when outputting JSON
        )
        
        # Create the venue with all details
        venue = Venue(
            name=venue_name,
            venue_type=venue_type,
            address=details.get('address', ''),
            latitude=details.get('latitude'),
            longitude=details.get('longitude'),
            image_url=details.get('image_url', ''),
            instagram_url=details.get('instagram_url', ''),
            facebook_url=details.get('facebook_url', ''),
            twitter_url=details.get('twitter_url', ''),
            youtube_url=details.get('youtube_url', ''),
            tiktok_url=details.get('tiktok_url', ''),
            opening_hours=details.get('opening_hours', ''),
            holiday_hours=details.get('holiday_hours', ''),
            phone_number=details.get('phone_number', ''),
            email=details.get('email', ''),
            website_url=details.get('website_url', ''),
            description=details.get('description', f'{venue_type} in {city_name}'),
            city_id=city.id
        )
        
        # Add to database
        db.session.add(venue)
        db.session.commit()
        
        if output_json:
            # Restore stdout
            sys.stdout = old_stdout
            # Return JSON data for API consumption
            return {
                'success': True,
                'venue': venue.to_dict(),
                'message': f'Successfully added {venue_name} to {city_name}'
            }
        else:
            print(f"✅ Successfully added {venue_name} to {city_name}")
            print(f"   Description: {venue.description}")
            if venue.website_url:
                print(f"   Website: {venue.website_url}")
            if venue.opening_hours:
                print(f"   Hours: {venue.opening_hours}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add a venue manually with automatic detail fetching')
    parser.add_argument('--name', required=True, help='Venue name to add')
    parser.add_argument('--city', required=True, help='City name')
    parser.add_argument('--type', default='museum', help='Venue type (museum, gallery, etc.)')
    parser.add_argument('--output-json', action='store_true', help='Output JSON data instead of printing')
    
    args = parser.parse_args()
    
    result = add_venue_manually(args.name, args.city, args.type, args.output_json)
    
    if args.output_json and result:
        print(json.dumps(result, indent=2))
