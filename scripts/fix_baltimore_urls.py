#!/usr/bin/env python3
"""
Fix Baltimore venue URLs with correct, working URLs
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

# Correct URLs for Baltimore venues
BALTIMORE_URL_FIXES = {
    "Baltimore Museum of Art": "https://artbma.org",
    "Fort McHenry National Monument": "https://www.nps.gov/fomc/index.htm",
    "Inner Harbor": "https://www.baltimore.org/neighborhoods/inner-harbor/",
    "National Aquarium": "https://aqua.org",
    "Walters Art Museum": "https://thewalters.org"
}

def fix_baltimore_urls():
    """Update Baltimore venue URLs to correct websites"""
    with app.app_context():
        for venue_name, correct_url in BALTIMORE_URL_FIXES.items():
            venue = Venue.query.filter_by(name=venue_name).first()
            if venue:
                old_url = venue.website_url
                venue.website_url = correct_url
                db.session.commit()
                print(f"✅ Updated {venue_name}: {old_url} → {correct_url}")
            else:
                print(f"⚠️  Venue not found: {venue_name}")

if __name__ == "__main__":
    fix_baltimore_urls()


