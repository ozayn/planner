#!/usr/bin/env python3
"""
PREDEFINED VENUE DISCOVERY
Uses predefined venue database instead of AI to save quota
"""

import sys
import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue
from scripts.env_config import ensure_env_loaded

# Ensure environment is loaded
ensure_env_loaded()

def setup_venue_logging():
    """Setup logging for venue discovery script"""
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, 'venue_discovery.log')),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('venue_discovery')

venue_logger = setup_venue_logging()

class PredefinedVenueDiscoverer:
    """Discovers venues using predefined database instead of AI"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.venues_file = self.project_root / "data" / "predefined_venues.json"
        self.venues_data = None
        
    def load_venues_data(self):
        """Load predefined venues data from JSON file"""
        if not self.venues_file.exists():
            venue_logger.error(f"Predefined venues file not found: {self.venues_file}")
            return False
            
        try:
            with open(self.venues_file, 'r') as f:
                self.venues_data = json.load(f)
            venue_logger.info(f"Loaded predefined venues for {len(self.venues_data['cities'])} cities")
            return True
        except Exception as e:
            venue_logger.error(f"Failed to load venues data: {e}")
            return False
    
    def discover_venues_for_city(self, city_id: int, max_venues: int = 5) -> Dict:
        """Discover venues for a specific city using predefined data"""
        
        if not self.venues_data:
            if not self.load_venues_data():
                return {"success": False, "error": "Failed to load venues data"}
        
        with app.app_context():
            # Get city information
            city = City.query.get(city_id)
            if not city:
                return {"success": False, "error": f"City with ID {city_id} not found"}
            
            venue_logger.info(f"Discovering venues for {city.name}, {city.state}, {city.country}")
            
            # Find city in predefined data
            city_venues = None
            for cid, city_data in self.venues_data['cities'].items():
                if city_data['name'] == city.name:
                    city_venues = city_data['venues']
                    break
            
            if not city_venues:
                venue_logger.warning(f"No predefined venues found for {city.name}")
                return {"success": False, "error": f"No predefined venues found for {city.name}"}
            
            # Limit venues to max_venues
            venues_to_add = city_venues[:max_venues]
            
            # Clear existing venues for this city
            existing_venues = Venue.query.filter_by(city_id=city_id).all()
            for venue in existing_venues:
                db.session.delete(venue)
            
            # Add new venues
            added_venues = []
            for venue_data in venues_to_add:
                venue = Venue(
                    name=venue_data['name'],
                    venue_type=venue_data['venue_type'],
                    address=venue_data['address'],
                    city_id=city_id,
                    opening_hours=venue_data['opening_hours'],
                    holiday_hours="",  # Not provided in predefined data
                    phone_number=venue_data['phone_number'],
                    email=venue_data['email'],
                    description=venue_data.get('description', ''),  # Use description field
                    tour_info=venue_data.get('tour_info', ''),  # Use tour_info field
                    admission_fee=venue_data['admission_fee']
                )
                db.session.add(venue)
                added_venues.append(venue_data['name'])
            
            # Commit changes
            db.session.commit()
            
            venue_logger.info(f"Successfully added {len(added_venues)} venues for {city.name}")
            venue_logger.info(f"Added venues: {', '.join(added_venues)}")
            
            return {
                "success": True,
                "city_name": city.name,
                "venues_added": len(added_venues),
                "venue_names": added_venues,
                "method": "predefined_database"
            }

def discover_venues_for_city(city_id: int, max_venues: int = 5) -> Dict:
    """Main function to discover venues for a city using predefined data"""
    
    discoverer = PredefinedVenueDiscoverer()
    return discoverer.discover_venues_for_city(city_id, max_venues)

def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python discover_venues.py <city_id> [max_venues]")
        print("Example: python discover_venues.py 1 5")
        sys.exit(1)
    
    try:
        city_id = int(sys.argv[1])
        max_venues = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        
        print(f"🔍 Discovering venues for city ID {city_id} (max: {max_venues})")
        print("💡 Using predefined database - no AI quota consumed!")
        
        result = discover_venues_for_city(city_id, max_venues)
        
        if result["success"]:
            print(f"✅ Successfully discovered {result['venues_added']} venues for {result['city_name']}")
            print(f"🏛️  Venues: {', '.join(result['venue_names'])}")
        else:
            print(f"❌ Failed to discover venues: {result['error']}")
            sys.exit(1)
            
    except ValueError:
        print("❌ Invalid city_id. Please provide a valid integer.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
