#!/usr/bin/env python3
"""
Add address to National Gallery of Art if missing
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

def add_nga_address():
    """Add address to National Gallery of Art"""
    with app.app_context():
        # Find National Gallery of Art
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%national gallery%')
        ).first()
        
        if not venue:
            print("❌ National Gallery of Art not found")
            return False
        
        print(f"✅ Found venue: {venue.name}")
        print(f"   Current address: {venue.address or 'NO ADDRESS'}")
        
        # National Gallery of Art address (from venues.json)
        nga_address = "Constitution Ave NW, Washington, DC 20565"
        
        if venue.address and venue.address.strip():
            print(f"   Venue already has an address: {venue.address}")
            # Check if it's similar (might have slight variations)
            if "Constitution" in venue.address and "20565" in venue.address:
                print("   ✅ Address looks correct")
                # Make sure it's the full address format
                if venue.address != nga_address:
                    print(f"   Updating to standard format: {nga_address}")
                    venue.address = nga_address
                    db.session.commit()
                return True
            else:
                print(f"   ⚠️  Address is different. Updating to: {nga_address}")
                venue.address = nga_address
        else:
            print(f"   Adding address: {nga_address}")
            venue.address = nga_address
        
        db.session.commit()
        print(f"✅ Successfully updated venue address")
        print(f"   New address: {venue.address}")
        return True

if __name__ == '__main__':
    try:
        success = add_nga_address()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

