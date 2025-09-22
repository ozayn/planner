#!/usr/bin/env python3
"""
Assign Google Maps images to venues missing image URLs
Uses the Google Places API to fetch real venue images
"""

import os
import sys
import time
from typing import Optional

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, City
from scripts.utils import get_google_maps_image

def extract_state_from_address(address: str) -> Optional[str]:
    """Extract state abbreviation from address"""
    if not address:
        return None
        
    # Common US state abbreviations
    state_patterns = ['DC', 'CA', 'NY', 'FL', 'TX', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI', 
                     'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI',
                     'CO', 'MN', 'SC', 'AL', 'LA', 'KY', 'OR', 'OK', 'CT', 'UT',
                     'IA', 'NV', 'AR', 'MS', 'KS', 'NM', 'NE', 'WV', 'ID', 'HI',
                     'NH', 'ME', 'RI', 'MT', 'DE', 'SD', 'ND', 'AK', 'VT', 'WY']
    
    for state in state_patterns:
        if f', {state}' in address or f' {state} ' in address:
            return state
    
    return None

def assign_google_maps_images():
    """Assign Google Maps images to venues missing them"""
    print("🖼️  Assigning Google Maps images to venues...")
    
    with app.app_context():
        try:
            # Get venues without image URLs or with placeholder images
            venues_needing_images = Venue.query.filter(
                (Venue.image_url == None) | 
                (Venue.image_url == '') |
                (Venue.image_url.like('https://via.placeholder.com%'))
            ).all()
            
            print(f"📊 Found {len(venues_needing_images)} venues needing image URLs")
            
            if len(venues_needing_images) == 0:
                print("✅ All venues already have image URLs!")
                return True
            
            # Get cities for context
            cities = {city.id: city for city in City.query.all()}
            
            updated_count = 0
            failed_count = 0
            
            for i, venue in enumerate(venues_needing_images, 1):
                city = cities.get(venue.city_id)
                city_name = city.name if city else 'Unknown'
                state = extract_state_from_address(venue.address) if venue.address else None
                country = city.country if city else 'United States'
                
                print(f"\\n[{i}/{len(venues_needing_images)}] 🔍 Fetching image for {venue.name}")
                print(f"   📍 Location: {city_name}, {state or 'Unknown State'}, {country}")
                
                try:
                    # Fetch Google Maps image
                    image_url = get_google_maps_image(
                        venue_name=venue.name,
                        city=city_name,
                        state=state,
                        country=country
                    )
                    
                    if image_url:
                        venue.image_url = image_url
                        updated_count += 1
                        print(f"   ✅ Assigned image URL")
                    else:
                        print(f"   ❌ No image found")
                        failed_count += 1
                    
                    # Be respectful to the API - add delay
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"   ❌ Error fetching image: {e}")
                    failed_count += 1
                    continue
            
            # Commit all changes
            if updated_count > 0:
                db.session.commit()
                print(f"\\n💾 Committed {updated_count} image URL updates to database")
            
            print(f"\\n🎉 Google Maps image assignment complete!")
            print(f"📊 Results:")
            print(f"   ✅ Successfully updated: {updated_count}")
            print(f"   ❌ Failed to find images: {failed_count}")
            print(f"   📝 Total processed: {len(venues_needing_images)}")
            
            # Show final coverage
            total_venues = Venue.query.count()
            venues_with_images = Venue.query.filter(
                (Venue.image_url != None) & 
                (Venue.image_url != '') &
                (~Venue.image_url.like('https://via.placeholder.com%'))
            ).count()
            
            coverage_percent = (venues_with_images / total_venues * 100) if total_venues > 0 else 0
            
            print(f"\\n📊 Final Image Coverage:")
            print(f"   Total venues: {total_venues}")
            print(f"   With real images: {venues_with_images}")
            print(f"   Coverage: {coverage_percent:.1f}%")
            
            # List venues that still need images
            still_missing = Venue.query.filter(
                (Venue.image_url == None) | 
                (Venue.image_url == '') |
                (Venue.image_url.like('https://via.placeholder.com%'))
            ).all()
            
            if still_missing:
                print(f"\\n📝 Venues still needing images ({len(still_missing)}):")
                for venue in still_missing[:10]:  # Show first 10
                    city = cities.get(venue.city_id)
                    city_name = city.name if city else 'Unknown'
                    print(f"   - {venue.name} ({venue.venue_type}) in {city_name}")
                if len(still_missing) > 10:
                    print(f"   ... and {len(still_missing) - 10} more")
            
            return True
            
        except Exception as e:
            print(f"❌ Error assigning Google Maps images: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🖼️  Google Maps Image Assignment for Venues")
    print("=" * 60)
    
    # Check if Google Maps API key is available
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("❌ GOOGLE_MAPS_API_KEY not found in environment variables")
        print("   Please add your Google Maps API key to .env file")
        sys.exit(1)
    
    print("✅ Google Maps API key found")
    
    success = assign_google_maps_images()
    
    if success:
        print("\\n🎉 Image assignment completed successfully!")
        print("💡 Tip: The updated images will be automatically included when you export venues.json")
    else:
        print("\\n❌ Image assignment failed")
        sys.exit(1)
