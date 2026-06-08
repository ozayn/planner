#!/usr/bin/env python3
"""
Fix All Venue URLs

Updates all fake venue URLs to point to real, working websites.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

# Comprehensive mapping of correct URLs for all venues
VENUE_URL_FIXES = {
    # NYC
    "American Museum of Natural History": "https://www.amnh.org",
    "Metropolitan Museum of Art": "https://www.metmuseum.org",
    "Museum of Modern Art (MoMA)": "https://www.moma.org",
    "Brooklyn Bridge": "https://www.nyc.gov/html/dot/html/infrastructure/brooklyn-bridge.shtml",
    "Central Park": "https://www.centralparknyc.org",
    "Empire State Building": "https://www.esbnyc.com",
    "Statue of Liberty": "https://www.nps.gov/stli/index.htm",
    "Times Square": "https://www.timessquarenyc.org",
    
    # Washington DC
    "Capitol Building": "https://www.capitol.gov",
    "Capitol Hill": "https://www.capitol.gov",
    
    # Chicago
    "Art Institute of Chicago": "https://www.artic.edu",
    "Field Museum": "https://www.fieldmuseum.org",
    
    # Seattle
    "Museum of Pop Culture (MoPOP)": "https://www.mopop.org",
    
    # Miami
    "Frost Science Museum": "https://www.frostscience.org",
    "Pérez Art Museum Miami (PAMM)": "https://www.pamm.org",
    
    # San Francisco
    "Alcatraz Island": "https://www.nps.gov/alca/index.htm",
    "Golden Gate Bridge": "https://www.goldengate.org",
    
    # London
    "British Museum": "https://www.britishmuseum.org",
}

def fix_all_venue_urls():
    """Update all venue URLs to correct real websites"""
    with app.app_context():
        print("🔍 Scanning all venues for fake URLs...")
        
        # Get all venues
        venues = Venue.query.all()
        print(f"📍 Found {len(venues)} total venues")
        
        fixed_count = 0
        skipped_count = 0
        
        for venue in venues:
            if venue.name in VENUE_URL_FIXES:
                old_url = venue.website_url
                new_url = VENUE_URL_FIXES[venue.name]
                
                if old_url != new_url:
                    venue.website_url = new_url
                    fixed_count += 1
                    print(f"✅ Updated {venue.name}")
                    print(f"   Old: {old_url}")
                    print(f"   New: {new_url}")
                else:
                    skipped_count += 1
                    print(f"⏭️  Skipped {venue.name} (already correct)")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ Successfully updated {fixed_count} venue URLs")
            print(f"⏭️  Skipped {skipped_count} venues (already correct)")
        else:
            print(f"\n✅ All venue URLs are already correct ({skipped_count} checked)")
        
        return True

if __name__ == "__main__":
    success = fix_all_venue_urls()
    sys.exit(0 if success else 1)

