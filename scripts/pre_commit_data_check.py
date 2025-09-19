#!/usr/bin/env python3
"""
Pre-commit data validation check
Runs before commits to ensure data integrity
"""

import os
import sys
import json
sys.path.append('.')

def check_venues_json_integrity():
    """Check venues.json for common issues"""
    print("🔍 Checking venues.json integrity...")
    
    venues_file = 'data/venues.json'
    if not os.path.exists(venues_file):
        print("❌ venues.json missing")
        return False
    
    try:
        with open(venues_file, 'r') as f:
            data = json.load(f)
        
        venues = data.get('venues', {})
        issues = []
        
        # Check for fake image URLs (my mistake pattern)
        fake_image_count = 0
        missing_social_count = 0
        
        for venue_id, venue_data in venues.items():
            venue_name = venue_data.get('name', 'Unknown')
            
            # Check for fake image URLs
            image_url = venue_data.get('image_url', '')
            if isinstance(image_url, str) and image_url.startswith('AciIO2') and len(image_url) == 200:
                fake_image_count += 1
                issues.append(f"Fake image URL in {venue_name}")
            
            # Check for missing social media in major venues
            venue_type = venue_data.get('venue_type', '')
            if venue_type in ['museum', 'embassy', 'arts_center']:
                has_social = any([
                    venue_data.get('instagram_url'),
                    venue_data.get('facebook_url'),
                    venue_data.get('twitter_url')
                ])
                if not has_social:
                    missing_social_count += 1
        
        if fake_image_count > 0:
            print(f"❌ Found {fake_image_count} venues with fake image URLs")
            return False
        
        if missing_social_count > 10:  # Allow some missing, but not too many
            print(f"⚠️  {missing_social_count} major venues missing social media")
        
        print(f"✅ venues.json integrity check passed ({len(venues)} venues)")
        return True
        
    except Exception as e:
        print(f"❌ Error checking venues.json: {e}")
        return False

def check_database_venue_types():
    """Check for venue type consistency (if database is available)"""
    try:
        from app import app, db, Venue
        
        with app.app_context():
            print("🏛️  Checking venue type consistency...")
            
            venues = Venue.query.all()
            inconsistent_types = []
            
            for venue in venues:
                if venue.venue_type and venue.venue_type != venue.venue_type.lower():
                    inconsistent_types.append(f"{venue.name}: '{venue.venue_type}' should be lowercase")
            
            if inconsistent_types:
                print(f"❌ Found {len(inconsistent_types)} venue type inconsistencies")
                for issue in inconsistent_types[:5]:  # Show first 5
                    print(f"   - {issue}")
                return False
            
            print(f"✅ Venue types consistent ({len(venues)} venues)")
            return True
            
    except Exception as e:
        print(f"⚠️  Could not check database venue types: {e}")
        return True  # Don't fail if database not available

def main():
    """Run pre-commit data validation"""
    print("🛡️  PRE-COMMIT DATA VALIDATION")
    print("=" * 50)
    
    checks = [
        ("venues.json integrity", check_venues_json_integrity),
        ("venue type consistency", check_database_venue_types),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n{check_name.upper()}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 ALL PRE-COMMIT CHECKS PASSED!")
        print("✅ Safe to commit")
        return 0
    else:
        print("🚨 PRE-COMMIT CHECKS FAILED!")
        print("❌ Please fix issues before committing")
        return 1

if __name__ == '__main__':
    sys.exit(main())
