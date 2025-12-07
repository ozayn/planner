#!/usr/bin/env python3
"""
Fix Golden Gate Bridge URL
Quick script to fix the incorrect URL for Golden Gate Bridge in the database.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

def fix_golden_gate_url():
    """Fix the Golden Gate Bridge URL in the database"""
    with app.app_context():
        venue = Venue.query.filter_by(name="Golden Gate Bridge").first()
        
        if not venue:
            print("❌ Golden Gate Bridge venue not found in database")
            return False
        
        old_url = venue.website_url
        correct_url = "https://www.goldengate.org"
        
        if old_url == correct_url:
            print(f"✅ Golden Gate Bridge URL is already correct: {correct_url}")
            return True
        
        print(f"🔍 Found Golden Gate Bridge venue")
        print(f"   Current URL: {old_url}")
        print(f"   Correct URL: {correct_url}")
        
        venue.website_url = correct_url
        db.session.commit()
        
        print(f"✅ Successfully updated Golden Gate Bridge URL")
        print(f"   Old: {old_url}")
        print(f"   New: {correct_url}")
        
        return True

if __name__ == "__main__":
    success = fix_golden_gate_url()
    sys.exit(0 if success else 1)
