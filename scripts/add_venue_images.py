#!/usr/bin/env python3
"""
Add Image URLs to Venues Script
Adds image_url field to all venues in predefined_venues.json
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def get_venue_image_url(venue_name, venue_type, city_name):
    """Get image URL for a specific venue"""
    
    # Venue-specific image URLs
    image_urls = {
        # Los Angeles venues
        "Getty Center": "https://www.getty.edu/content/dam/getty/images/visit/getty-center-aerial-view.jpg",
        "Los Angeles County Museum of Art (LACMA)": "https://www.lacma.org/sites/default/files/styles/large/public/2021-03/LACMA_Exterior_Chris_Burden_Urban_Light_2019.jpg",
        "Griffith Observatory": "https://griffithobservatory.org/wp-content/uploads/2021/03/Griffith-Observatory-Exterior-Day.jpg",
        "Hollywood Walk of Fame": "https://www.walkoffame.com/wp-content/uploads/2021/03/hollywood-walk-of-fame-stars.jpg",
        "Santa Monica Pier": "https://www.santamonicapier.org/wp-content/uploads/2021/03/santa-monica-pier-ferris-wheel.jpg",
        
        # San Francisco venues
        "San Francisco Museum of Modern Art (SFMOMA)": "https://www.sfmoma.org/wp-content/uploads/2021/03/sfmoma-exterior-building.jpg",
        "de Young Museum": "https://www.famsf.org/sites/default/files/styles/large/public/2021-03/de-young-museum-exterior.jpg",
        "Palace of Fine Arts": "https://www.palaceoffinearts.org/wp-content/uploads/2021/03/palace-of-fine-arts-exterior.jpg",
        "Golden Gate Bridge": "https://www.goldengate.org/wp-content/uploads/2021/03/golden-gate-bridge-aerial-view.jpg",
        "Alcatraz Island": "https://www.nps.gov/alca/learn/photosmultimedia/images/alcatraz-island-aerial.jpg",
        
        # Chicago venues
        "Art Institute of Chicago": "https://www.artic.edu/sites/default/files/styles/large/public/2021-03/art-institute-chicago-exterior.jpg",
        "Field Museum": "https://www.fieldmuseum.org/sites/default/files/styles/large/public/2021-03/field-museum-exterior.jpg",
        "Shedd Aquarium": "https://www.sheddaquarium.org/sites/default/files/styles/large/public/2021-03/shedd-aquarium-exterior.jpg",
        "Millennium Park": "https://www.millenniumpark.org/wp-content/uploads/2021/03/millennium-park-cloud-gate.jpg",
        "Willis Tower Skydeck": "https://theskydeck.com/wp-content/uploads/2021/03/willis-tower-skydeck-exterior.jpg",
        
        # New York venues
        "Metropolitan Museum of Art": "https://www.metmuseum.org/sites/default/files/styles/large/public/2021-03/met-museum-exterior.jpg",
        "American Museum of Natural History": "https://www.amnh.org/sites/default/files/styles/large/public/2021-03/amnh-exterior.jpg",
        "Museum of Modern Art (MoMA)": "https://www.moma.org/sites/default/files/styles/large/public/2021-03/moma-exterior.jpg",
        "Statue of Liberty": "https://www.nps.gov/stli/learn/photosmultimedia/images/statue-of-liberty-aerial.jpg",
        "Empire State Building": "https://www.esbnyc.com/sites/default/files/styles/large/public/2021-03/empire-state-building-exterior.jpg",
        "Central Park": "https://www.centralparknyc.org/sites/default/files/styles/large/public/2021-03/central-park-aerial-view.jpg",
        "Times Square": "https://www.timessquarenyc.org/sites/default/files/styles/large/public/2021-03/times-square-night-lights.jpg",
        "Brooklyn Bridge": "https://www.nyc.gov/sites/default/files/styles/large/public/2021-03/brooklyn-bridge-aerial-view.jpg",
        
        # Paris venues
        "Louvre Museum": "https://www.louvre.fr/sites/default/files/styles/large/public/2021-03/louvre-museum-exterior-pyramid.jpg",
        "Musée d'Orsay": "https://www.musee-orsay.fr/sites/default/files/styles/large/public/2021-03/musee-orsay-exterior.jpg",
        "Eiffel Tower": "https://www.toureiffel.paris/sites/default/files/styles/large/public/2021-03/eiffel-tower-aerial-view.jpg",
        "Notre-Dame Cathedral": "https://www.notredamedeparis.fr/sites/default/files/styles/large/public/2021-03/notre-dame-cathedral-exterior.jpg",
        "Arc de Triomphe": "https://www.arcdetriompheparis.com/sites/default/files/styles/large/public/2021-03/arc-de-triomphe-exterior.jpg",
        
        # London venues
        "British Museum": "https://www.britishmuseum.org/sites/default/files/styles/large/public/2021-03/british-museum-exterior.jpg",
        "National Gallery": "https://www.nationalgallery.org.uk/sites/default/files/styles/large/public/2021-03/national-gallery-exterior.jpg",
        "Tower of London": "https://www.hrp.org.uk/sites/default/files/styles/large/public/2021-03/tower-of-london-exterior.jpg",
        "Tate Modern": "https://www.tate.org.uk/sites/default/files/styles/large/public/2021-03/tate-modern-exterior.jpg",
        "Westminster Abbey": "https://www.westminster-abbey.org/sites/default/files/styles/large/public/2021-03/westminster-abbey-exterior.jpg",
        
        # Washington DC venues
        "Smithsonian National Air and Space Museum": "https://airandspace.si.edu/sites/default/files/styles/large/public/2021-03/air-space-museum-exterior.jpg",
        "Smithsonian National Museum of Natural History": "https://naturalhistory.si.edu/sites/default/files/styles/large/public/2021-03/natural-history-museum-exterior.jpg",
        "National Gallery of Art": "https://www.nga.gov/sites/default/files/styles/large/public/2021-03/national-gallery-art-exterior.jpg",
        "Lincoln Memorial": "https://www.nps.gov/linc/learn/photosmultimedia/images/lincoln-memorial-exterior.jpg",
        "Washington Monument": "https://www.nps.gov/wamo/learn/photosmultimedia/images/washington-monument-exterior.jpg",
        "White House": "https://www.whitehouse.gov/sites/default/files/styles/large/public/2021-03/white-house-exterior.jpg",
        "Capitol Building": "https://www.capitol.gov/sites/default/files/styles/large/public/2021-03/capitol-building-exterior.jpg"
    }
    
    # Return specific image URL or default based on venue type
    if venue_name in image_urls:
        return image_urls[venue_name]
    
    # Default image URLs based on venue type
    default_images = {
        "Museum": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop",
        "Observatory": "https://images.unsplash.com/photo-1446776877081-d282a0f896e2?w=800&h=600&fit=crop",
        "Landmark": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop",
        "Park": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=600&fit=crop",
        "Monument": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop",
        "Cathedral": "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=800&h=600&fit=crop",
        "Bridge": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop",
        "Aquarium": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&h=600&fit=crop",
        "Theater": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=600&fit=crop",
        "Zoo": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&h=600&fit=crop"
    }
    
    return default_images.get(venue_type, "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop")

def add_image_urls_to_venues():
    """Add image_url field to all venues in predefined_venues.json"""
    
    print("🖼️ Adding image URLs to venues...")
    print("=" * 60)
    
    # Load predefined venues
    venues_file = Path("data/predefined_venues.json")
    if not venues_file.exists():
        print("❌ predefined_venues.json not found")
        return False
        
    with open(venues_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Found {data['metadata']['total_venues']} venues across {data['metadata']['total_cities']} cities")
    print("=" * 60)
    
    enhanced_count = 0
    total_venues = 0
    
    # Process each city
    for city_id, city_data in data['cities'].items():
        city_name = city_data['name']
        venues = city_data['venues']
        
        print(f"\n🏙️ Processing {city_name} ({len(venues)} venues)...")
        print("-" * 50)
        
        for i, venue in enumerate(venues):
            total_venues += 1
            venue_name = venue['name']
            venue_type = venue['venue_type']
            
            print(f"  [{i+1}/{len(venues)}] Venue: {venue_name}")
            
            # Check if venue already has image_url
            if venue.get('image_url'):
                print(f"      ⏭️  Already has image URL, skipping")
                continue
            
            print(f"      🖼️ Adding image URL...")
            # Get image URL
            image_url = get_venue_image_url(venue_name, venue_type, city_name)
            
            # Add image URL to venue
            venue['image_url'] = image_url
            enhanced_count += 1
            print(f"      ✅ Image URL added!")
    
    # Update metadata
    data['metadata']['venues_with_images'] = enhanced_count
    data['metadata']['last_image_update'] = "2025-09-10 16:45:00"
    
    # Save enhanced data
    with open(venues_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Image URL addition complete!")
    print(f"   Added images to: {enhanced_count}/{total_venues} venues")
    print(f"   Updated: {venues_file}")
    
    return True

if __name__ == "__main__":
    success = add_image_urls_to_venues()
    if not success:
        sys.exit(1)
