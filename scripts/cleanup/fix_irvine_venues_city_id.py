#!/usr/bin/env python3
"""
Fix Irvine venues that have incorrect city_id (27 instead of 26)
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, City

def fix_irvine_venues():
    """Fix Irvine venues that have wrong city_id"""
    with app.app_context():
        # Get Irvine city
        irvine = City.query.filter_by(name='Irvine').first()
        if not irvine:
            print("❌ Irvine city not found in database")
            return False
        
        print(f"✅ Found Irvine (ID: {irvine.id})")
        
        # Find all venues with Irvine in name but wrong city_id
        irvine_venue_names = [
            'Irvine Barclay Theatre',
            'Orange County Great Park',
            'Irvine Museum of Art',
            'Pretend City Children\'s Museum',
            'Irvine Spectrum Center',
            'Bren Events Center',
            'Irvine Fine Arts Center',
            'William R. Mason Regional Park',
            'Orange County Museum of Art (OCMA)'
        ]
        
        fixed_count = 0
        for venue_name in irvine_venue_names:
            venue = Venue.query.filter_by(name=venue_name).first()
            if venue:
                if venue.city_id != irvine.id:
                    old_city_id = venue.city_id
                    venue.city_id = irvine.id
                    fixed_count += 1
                    print(f"   ✅ Fixed: {venue_name} (city_id: {old_city_id} → {irvine.id})")
                else:
                    print(f"   ✓ Already correct: {venue_name}")
            else:
                print(f"   ⚠️  Not found: {venue_name}")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ Fixed {fixed_count} Irvine venues")
        else:
            print(f"\n✅ All Irvine venues already have correct city_id")
        
        return True

if __name__ == '__main__':
    try:
        fix_irvine_venues()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
