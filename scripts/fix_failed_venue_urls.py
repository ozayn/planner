#!/usr/bin/env python3
"""
Fix the 15 failed venue URLs manually
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Venue

# Known corrections for the 15 failed URLs
CORRECTIONS = {
    'Dupont Circle': 'https://www.nps.gov/rocr/planyourvisit/dupont-circle.htm',  # Keep - 404 might be temporary, or try: https://www.nps.gov/rocr/index.htm
    'Embassy of Canada': 'https://international.gc.ca/world-monde/united_states-etats_unis/washington.aspx',
    'Embassy of Australia': 'https://usa.embassy.gov.au',  # Keep - timeout might be temporary, URL is correct
    'Embassy of Mexico': 'https://embamex.sre.gob.mx/eua/index.php/en/',
    'Embassy of South Korea': 'https://overseas.mofa.go.kr/us-washington-en/index.do',
    'The Bookstore in Glover Park': None,  # May be closed or no website - needs manual verification
    'South Beach': 'https://www.miamibeach.gov/parks-recreation/beaches/south-beach',
    'McCord Museum': 'https://www.mccord-stewart.ca/en/',  # Updated domain (merged with Stewart Museum)
    'National Museum of Iran': 'https://www.museumiran.ir/',  # Persian domain
    'Nassau Hall': 'https://www.princeton.edu/about/history/nassau-hall',  # Different page to avoid SSL issue
    'Princeton Cemetery': 'https://www.princeton.edu/visit/princeton-cemetery',  # Use Princeton main site
    'Princeton University Store': 'https://store.princeton.edu/',  # Add trailing slash
    'Laugh Factory': 'https://www.laughfactory.com/clubs/chicago',  # Keep - 404 might be temporary, URL format is correct
    'William R. Mason Regional Park': 'https://www.ocparks.com/parks/wmason',  # Shorter path (abbreviation)
    'Orange County Museum of Art (OCMA)': 'https://ocma.art',  # Keep - 406 might be bot protection, URL is correct
}

def fix_failed_urls(dry_run=True):
    """Fix the failed venue URLs"""
    
    with app.app_context():
        print("🔧 FIXING FAILED VENUE URLs")
        print("=" * 80)
        print(f"Dry run: {dry_run}\n")
        
        fixed = 0
        skipped = 0
        
        for venue_name, correct_url in CORRECTIONS.items():
            # Find venue by name
            venue = Venue.query.filter(Venue.name.ilike(f'%{venue_name}%')).first()
            
            if not venue:
                print(f"❌ {venue_name} - NOT FOUND in database")
                continue
            
            if correct_url is None:
                print(f"⏭️  {venue.name} - No correction available (may be closed)")
                skipped += 1
                continue
            
            old_url = venue.website_url
            if old_url == correct_url:
                print(f"✅ {venue.name} - Already correct: {correct_url}")
                continue
            
            print(f"🔧 {venue.name}")
            print(f"   Old: {old_url}")
            print(f"   New: {correct_url}")
            
            if not dry_run:
                venue.website_url = correct_url
                db.session.commit()
                print(f"   ✅ Updated!")
                fixed += 1
            else:
                print(f"   ⏳ Would update (dry run)")
                fixed += 1
        
        if not dry_run:
            print(f"\n✅ Fixed {fixed} URLs")
            print(f"⏭️  Skipped {skipped} URLs")
            
            # Update venues.json
            print("\n🔄 Updating venues.json...")
            from scripts.update_venues_json import update_venues_json
            update_venues_json()
            print("✅ venues.json updated")
        else:
            print(f"\n📊 Would fix {fixed} URLs (dry run)")
            print(f"⏭️  Would skip {skipped} URLs")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Actually apply the fixes')
    args = parser.parse_args()
    
    fix_failed_urls(dry_run=not args.apply)
