#!/usr/bin/env python3
"""
Fix NYC Venue URLs

Updates NYC venue URLs to point to real, working websites.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

# Mapping of correct URLs for NYC venues
NYC_VENUE_URL_FIXES = {
    "American Museum of Natural History": "https://www.amnh.org",
    "Metropolitan Museum of Art": "https://www.metmuseum.org",
    "Museum of Modern Art (MoMA)": "https://www.moma.org",
    "Brooklyn Bridge": "https://www.nyc.gov/html/dot/html/infrastructure/brooklyn-bridge.shtml",
    "Central Park": "https://www.centralparknyc.org",
    "Empire State Building": "https://www.esbnyc.com",
    "Statue of Liberty": "https://www.nps.gov/stli/index.htm",
    "Times Square": "https://www.timessquarenyc.org"
}

def fix_nyc_venue_urls():
    """Update NYC venue URLs to correct real websites"""
    with app.app_context():
        # Get NYC city
        from app import City
        nyc = City.query.filter_by(name='New York').first()
        if not nyc:
            print("❌ NYC not found in database")
            return False
        
        print(f"🔍 Found NYC (city_id={nyc.id})")
        
        # Get all NYC venues
        venues = Venue.query.filter_by(city_id=nyc.id).all()
        print(f"📍 Found {len(venues)} NYC venues")
        
        fixed_count = 0
        for venue in venues:
            if venue.name in NYC_VENUE_URL_FIXES:
                old_url = venue.website_url
                new_url = NYC_VENUE_URL_FIXES[venue.name]
                
                if old_url != new_url:
                    venue.website_url = new_url
                    fixed_count += 1
                    print(f"✅ Updated {venue.name}")
                    print(f"   Old: {old_url}")
                    print(f"   New: {new_url}")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ Successfully updated {fixed_count} venue URLs")
        else:
            print("\n✅ All venue URLs are already correct")
        
        return True

if __name__ == "__main__":
    success = fix_nyc_venue_urls()
    sys.exit(0 if success else 1)

