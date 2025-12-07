#!/usr/bin/env python3
"""
Fix San Francisco venue URLs
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

VENUE_URL_FIXES = {
    "San Francisco Museum of Modern Art (SFMOMA)": "https://www.sfmoma.org",
    "SFMOMA": "https://www.sfmoma.org",
    "de Young Museum": "https://deyoung.famsf.org",
}

def fix_sf_venue_urls():
    """Fix San Francisco venue URLs in the database"""
    with app.app_context():
        print("🔍 Fixing San Francisco venue URLs...")
        
        fixed_count = 0
        
        for venue_name, correct_url in VENUE_URL_FIXES.items():
            # Try exact match first
            venue = Venue.query.filter_by(name=venue_name).first()
            
            # If not found, try partial match
            if not venue:
                venues = Venue.query.filter(Venue.name.contains(venue_name.split()[0])).all()
                for v in venues:
                    if venue_name.lower() in v.name.lower() or v.name.lower() in venue_name.lower():
                        venue = v
                        break
            
            if venue:
                old_url = venue.website_url
                if old_url != correct_url:
                    venue.website_url = correct_url
                    fixed_count += 1
                    print(f"✅ Updated {venue.name}")
                    print(f"   Old: {old_url}")
                    print(f"   New: {correct_url}")
                else:
                    print(f"⏭️  {venue.name} already has correct URL: {correct_url}")
            else:
                print(f"⚠️  Venue not found: {venue_name}")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ Successfully updated {fixed_count} venue URLs")
        else:
            print(f"\n✅ All venue URLs are already correct")
        
        return True

if __name__ == "__main__":
    fix_sf_venue_urls()
