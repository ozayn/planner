#!/usr/bin/env python3
"""
Update venue closure status for government shutdown and other temporary closures
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue

def update_venue_closure_status():
    """Update venue closure status for government shutdown"""
    
    with app.app_context():
        # First, let's add a closure_status field if it doesn't exist
        # This will be handled by the auto-migration system
        
        # Get Washington DC venues
        dc_venues = Venue.query.filter_by(city_id=1).all()
        print(f"🏛️ Found {len(dc_venues)} venues in Washington DC")
        
        # Government-run venues that are typically closed during shutdown
        government_venues = [
            'Smithsonian National Museum of Natural History',
            'Smithsonian National Museum of American History', 
            'Smithsonian National Museum of African American History and Culture',
            'Smithsonian National Air and Space Museum',
            'Smithsonian National Museum of the American Indian',
            'Smithsonian Hirshhorn Museum and Sculpture Garden',
            'Smithsonian Arthur M. Sackler Gallery',
            'Smithsonian Freer Gallery of Art',
            'National Gallery of Art',
            'United States Holocaust Memorial Museum',
            'National Zoo',
            'United States Botanic Garden',
            'Capitol Building',
            'White House',
            'Supreme Court',
            'Library of Congress',
            'National Archives',
            'National Portrait Gallery'
        ]
        
        # Private/independent venues that typically remain open
        private_venues = [
            'International Spy Museum',
            'Newseum',
            'The Phillips Collection',
            'Arena Stage',
            "Ford's Theatre",
            'Kennedy Center',
            '9:30 Club',
            'Suns Cinema',
            'Politics and Prose Bookstore',
            'Kramerbooks & Afterwords Cafe',
            'The Hamilton',
            'Founding Farmers'
        ]
        
        # Memorials and outdoor sites that remain accessible
        outdoor_venues = [
            'Lincoln Memorial',
            'Jefferson Memorial',
            'Martin Luther King Jr. Memorial',
            'Vietnam Veterans Memorial',
            'Korean War Veterans Memorial',
            'World War II Memorial',
            'Washington Monument',
            'National Mall',
            'Tidal Basin',
            'Rock Creek Park',
            'Georgetown',
            'Dupont Circle'
        ]
        
        # Embassy venues (typically remain open)
        embassy_venues = [
            'Embassy of the United Kingdom',
            'Embassy of France',
            'Embassy of Germany',
            'Embassy of Italy',
            'Embassy of Japan',
            'Embassy of Canada',
            'Embassy of Spain',
            'Embassy of the Netherlands',
            'Embassy of Australia',
            'Embassy of Brazil',
            'Embassy of India',
            'Embassy of Mexico',
            'Embassy of South Korea',
            'Embassy of Sweden',
            'Embassy of Switzerland'
        ]
        
        venues_updated = 0
        
        for venue in dc_venues:
            venue_name = venue.name
            closure_info = None
            closure_status = "open"
            
            # Determine closure status based on venue type
            if venue_name in government_venues:
                closure_status = "closed"
                closure_info = "Closed due to government shutdown. Check website for reopening updates."
            elif venue_name in private_venues:
                closure_status = "open"
                closure_info = "Independent venue - typically remains open during government shutdown."
            elif venue_name in outdoor_venues:
                closure_status = "open"
                closure_info = "Outdoor site - remains accessible during government shutdown."
            elif venue_name in embassy_venues:
                closure_status = "open"
                closure_info = "Embassy - typically remains open during government shutdown."
            else:
                # Default for unknown venues
                closure_status = "unknown"
                closure_info = "Status unknown - please check venue website for current hours."
            
            # Update venue with closure information
            if hasattr(venue, 'closure_status'):
                venue.closure_status = closure_status
            else:
                # Use additional_info field to store closure information
                import json
                additional_info = {}
                if venue.additional_info:
                    try:
                        additional_info = json.loads(venue.additional_info)
                    except:
                        additional_info = {}
                
                additional_info['closure_status'] = closure_status
                additional_info['closure_reason'] = closure_info
                additional_info['last_updated'] = datetime.utcnow().isoformat()
                
                venue.additional_info = json.dumps(additional_info)
            
            # Also update holiday_hours with closure info
            if closure_status == "closed":
                venue.holiday_hours = f"TEMPORARILY CLOSED: {closure_info}"
            
            venues_updated += 1
            
            print(f"✅ Updated {venue_name}: {closure_status.upper()}")
            if closure_status == "closed":
                print(f"   ⚠️  {closure_info}")
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n🎉 Successfully updated {venues_updated} venues with closure status!")
        
        # Show summary
        print("\n📊 CLOSURE STATUS SUMMARY:")
        print("=" * 50)
        
        closed_count = 0
        open_count = 0
        unknown_count = 0
        
        for venue in dc_venues:
            if hasattr(venue, 'closure_status'):
                status = venue.closure_status
            else:
                try:
                    import json
                    additional_info = json.loads(venue.additional_info or '{}')
                    status = additional_info.get('closure_status', 'unknown')
                except:
                    status = 'unknown'
            
            if status == "closed":
                closed_count += 1
            elif status == "open":
                open_count += 1
            else:
                unknown_count += 1
        
        print(f"🔴 CLOSED: {closed_count} venues")
        print(f"🟢 OPEN: {open_count} venues") 
        print(f"🟡 UNKNOWN: {unknown_count} venues")
        
        return True

def main():
    """Main function"""
    success = update_venue_closure_status()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
