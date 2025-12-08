#!/usr/bin/env python3
"""
Update DC venues with correct Eventbrite URLs where available.
Based on research, most major venues don't have Eventbrite organizer pages,
but some embassies and cultural centers do.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue

# Eventbrite URLs for DC venues (organizer pages where they exist)
EVENTBRITE_URLS = {
    # Embassies with confirmed Eventbrite organizer pages
    'Embassy of South Korea': 'https://www.eventbrite.com/o/korean-cultural-center-washington-dc-30268623512',
    
    # Note: Canadian Embassy URL in database is a discovery page, not an organizer page
    # Most embassies don't have official Eventbrite organizer pages - they use third-party organizers
    # or their own ticketing systems
    
    # The following venues typically use their own ticketing systems, not Eventbrite:
    # - Smithsonian museums (use si.edu ticketing)
    # - National Gallery of Art (use nga.gov)
    # - Kennedy Center (use kennedy-center.org)
    # - Major theaters (Arena Stage, Woolly Mammoth, Studio Theatre, Shakespeare Theatre)
    # - Most museums and cultural institutions
}

def update_eventbrite_urls():
    """Update DC venues with Eventbrite URLs where available"""
    with app.app_context():
        # Get all DC venues
        from app import City
        dc_city = City.query.filter_by(name='Washington').first()
        
        if not dc_city:
            print("❌ Washington, DC not found in database")
            return
        
        dc_venues = Venue.query.filter_by(city_id=dc_city.id).all()
        print(f"Found {len(dc_venues)} DC venues")
        
        updated_count = 0
        for venue in dc_venues:
            if venue.name in EVENTBRITE_URLS:
                new_url = EVENTBRITE_URLS[venue.name]
                if venue.ticketing_url != new_url:
                    old_url = venue.ticketing_url or '(none)'
                    venue.ticketing_url = new_url
                    print(f"✓ Updated {venue.name}: {old_url} → {new_url}")
                    updated_count += 1
                else:
                    print(f"✓ {venue.name} already has correct URL: {new_url}")
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✅ Updated {updated_count} venues with Eventbrite URLs")
        else:
            print("\n✅ No updates needed - all URLs are already correct")
        
        # Show summary
        print("\n📊 Summary:")
        print(f"  - Venues with Eventbrite URLs: {sum(1 for v in dc_venues if v.ticketing_url and 'eventbrite.com' in v.ticketing_url)}")
        print(f"  - Venues without Eventbrite URLs: {sum(1 for v in dc_venues if not v.ticketing_url or 'eventbrite.com' not in v.ticketing_url)}")
        print("\n💡 Note: Most major DC venues (museums, theaters) use their own ticketing systems,")
        print("   not Eventbrite. Only some embassies and cultural centers have Eventbrite organizer pages.")

if __name__ == '__main__':
    update_eventbrite_urls()
