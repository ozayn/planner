#!/usr/bin/env python3
"""
Fetch real Google Maps images for embassies and other venues missing proper image URLs
"""

import os
import sys
import json
sys.path.append('.')

from app import app, db, Venue
from scripts.fetch_google_maps_image import get_google_maps_image

def fetch_real_embassy_images():
    """Fetch real Google Maps images for venues with fake/missing image URLs"""
    print("📸 Fetching real Google Maps images for venues...")
    
    with app.app_context():
        try:
            # Get venues that need real image URLs
            # These are venues with fake photo references or no images
            venues_needing_images = Venue.query.filter(
                (Venue.image_url == None) | 
                (Venue.image_url == '') |
                (Venue.venue_type == 'embassy')  # All embassies need real images
            ).all()
            
            print(f"📊 Found {len(venues_needing_images)} venues needing real images")
            
            updated_count = 0
            failed_count = 0
            
            for venue in venues_needing_images:
                print(f"\n🔍 Fetching image for: {venue.name}")
                
                # Use the existing Google Maps image fetcher
                photo_data = get_google_maps_image(
                    venue_name=venue.name,
                    address=venue.address,
                    city=venue.city.name if venue.city else None,
                    state=venue.city.state if venue.city and venue.city.state else None
                )
                
                if photo_data and isinstance(photo_data, dict) and 'photo_reference' in photo_data:
                    # Store as JSON string (this is how existing venues store it)
                    venue.image_url = json.dumps(photo_data)
                    updated_count += 1
                    print(f"✅ Got real photo reference for '{venue.name}'")
                    
                    # Add a small delay to avoid hitting API rate limits
                    time.sleep(0.5)
                else:
                    # Remove fake image URL if we couldn't get a real one
                    venue.image_url = ""
                    failed_count += 1
                    print(f"❌ Could not get image for '{venue.name}' - removed fake URL")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Real image fetching complete!")
            print(f"✅ Successfully updated: {updated_count} venues")
            print(f"❌ Failed to fetch: {failed_count} venues")
            
            # Verify results
            venues_with_images = Venue.query.filter(
                (Venue.image_url != None) & (Venue.image_url != '')
            ).count()
            
            total_venues = Venue.query.count()
            
            print(f"\n📊 Final Image Coverage:")
            print(f"   Total venues: {total_venues}")
            print(f"   With real image URLs: {venues_with_images}")
            print(f"   Coverage: {(venues_with_images/total_venues)*100:.1f}%")
            
            return True
            
        except Exception as e:
            print(f"❌ Error fetching real images: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    # Import time for delays
    import time
    
    success = fetch_real_embassy_images()
    sys.exit(0 if success else 1)
