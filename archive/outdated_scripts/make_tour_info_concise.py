#!/usr/bin/env python3
"""
Make Tour Info Concise Script
Updates tour_info field with concise, essential tour information
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def get_concise_tour_info(venue_name, venue_type, city_name):
    """Get concise tour information for specific venues"""
    
    # Concise venue-specific tour information
    tour_info = {
        # Los Angeles venues
        "Getty Center": "Free. Guided tours 11am, 1pm, 3pm. Audio tours included.",
        "Los Angeles County Museum of Art (LACMA)": "$20. Guided tours 1pm daily. Audio tours available.",
        "Griffith Observatory": "Free. Planetarium $7. Guided telescope viewing.",
        "Hollywood Walk of Fame": "Free. Self-guided. Audio tour apps available.",
        "Santa Monica Pier": "Free. Guided pier tours available. Sunset tours offered.",
        
        # San Francisco venues
        "San Francisco Museum of Modern Art (SFMOMA)": "$25. Guided tours 1pm daily. Audio tours included.",
        "de Young Museum": "$15. Guided tours daily. Audio tours included.",
        "Palace of Fine Arts": "Free. Self-guided. Historical walking tours available.",
        "Golden Gate Bridge": "Free. Guided bridge walks. Audio tours available.",
        "Alcatraz Island": "Ferry $45. Guided audio tours included. Night tours available.",
        
        # Chicago venues
        "Art Institute of Chicago": "$25. Guided tours 1pm daily. Audio tours available.",
        "Field Museum": "$26. Guided tours daily. Audio tours included.",
        "Shedd Aquarium": "$40. Guided tours available. Behind-the-scenes tours.",
        "Millennium Park": "Free. Guided park tours. Architecture tours available.",
        "Willis Tower Skydeck": "$30. Guided tours available. Audio tours included.",
        
        # Boston venues
        "Museum of Fine Arts Boston": "$25. Guided tours 1pm daily. Audio tours available.",
        "Isabella Stewart Gardner Museum": "$20. Guided tours daily. Audio tours included.",
        "Freedom Trail": "Free. Guided walking tours. Audio tours available.",
        "Fenway Park": "$25. Guided ballpark tours. Behind-the-scenes tours.",
        "Boston Common": "Free. Guided walking tours. Historical tours available.",
        
        # Seattle venues
        "Space Needle": "$35. Guided tours available. Audio tours included.",
        "Museum of Pop Culture (MoPOP)": "$30. Guided tours available. Behind-the-scenes tours.",
        "Chihuly Garden and Glass": "$32. Guided tours available. Audio tours included.",
        "Pike Place Market": "Free. Guided market tours. Food tours available.",
        "Seattle Art Museum": "$20. Guided tours daily. Audio tours included.",
        
        # Miami venues
        "Vizcaya Museum and Gardens": "$22. Guided tours daily. Audio tours included.",
        "Pérez Art Museum Miami (PAMM)": "$16. Guided tours daily. Audio tours included.",
        "Frost Science Museum": "$30. Guided tours available. Behind-the-scenes tours.",
        "Wynwood Walls": "Free. Guided walking tours. Art tours available.",
        "South Beach": "Free. Guided walking tours. Historical tours available.",
        
        # London venues
        "British Museum": "Free. Guided tours daily. Audio tours available.",
        "National Gallery": "Free. Guided tours daily. Audio tours available.",
        "Tower of London": "£29. Guided tours by Beefeaters. Audio tours available.",
        "Tate Modern": "Free. Guided tours daily. Audio tours available.",
        "Westminster Abbey": "£27. Guided tours available. Audio tours included.",
        
        # Tokyo venues
        "Tokyo National Museum": "¥1000. Guided tours daily. Audio tours available.",
        "Meiji Shrine": "Free. Guided tours available. Audio tours available.",
        "Senso-ji Temple": "Free. Guided tours available. Audio tours available.",
        "Tokyo Tower": "¥1200. Guided tours available. Audio tours included.",
        "Ginza District": "Free. Guided walking tours. Shopping tours available.",
        
        # Sydney venues
        "Sydney Opera House": "$43. Guided tours daily. Audio tours included.",
        "Art Gallery of New South Wales": "Free. Guided tours daily. Audio tours available.",
        "Australian Museum": "$15. Guided tours daily. Audio tours included.",
        "Sydney Harbour Bridge": "Free. Guided bridge walks. Audio tours available.",
        "The Rocks": "Free. Guided walking tours. Historical tours available.",
        
        # Montreal venues
        "Montreal Museum of Fine Arts": "$24. Guided tours daily. Audio tours included.",
        "McCord Museum": "$18. Guided tours daily. Audio tours included.",
        "Notre-Dame Basilica": "$6. Guided tours available. Audio tours included.",
        "Old Montreal": "Free. Guided walking tours. Historical tours available.",
        "Mount Royal Park": "Free. Guided walking tours. Nature tours available.",
        
        # Toronto venues
        "Royal Ontario Museum": "$23. Guided tours daily. Audio tours included.",
        "Art Gallery of Ontario": "$25. Guided tours daily. Audio tours included.",
        "CN Tower": "$43. Guided tours available. Audio tours included.",
        "Casa Loma": "$40. Guided tours daily. Audio tours included.",
        "Distillery District": "Free. Guided walking tours. Historical tours available.",
        
        # Vancouver venues
        "Vancouver Art Gallery": "$24. Guided tours daily. Audio tours included.",
        "Museum of Anthropology": "$18. Guided tours daily. Audio tours included.",
        "Capilano Suspension Bridge": "$55. Guided tours available. Audio tours included.",
        "Stanley Park": "Free. Guided walking tours. Nature tours available.",
        "Granville Island": "Free. Guided walking tours. Food tours available.",
        
        # Tehran venues
        "National Museum of Iran": "$5. Guided tours daily. Audio tours available.",
        "Golestan Palace": "$8. Guided tours daily. Audio tours included.",
        "Tehran Museum of Contemporary Art": "$3. Guided tours daily. Audio tours available.",
        "Azadi Tower": "$2. Guided tours available. Audio tours included.",
        "Grand Bazaar": "Free. Guided walking tours. Shopping tours available.",
        
        # New York venues
        "Metropolitan Museum of Art": "$30. Guided tours daily. Audio tours included.",
        "American Museum of Natural History": "$28. Guided tours daily. Audio tours included.",
        "Museum of Modern Art (MoMA)": "$25. Guided tours daily. Audio tours included.",
        "Statue of Liberty": "Ferry $24. Guided tours included. Audio tours available.",
        "Empire State Building": "$44. Guided tours available. Audio tours included.",
        "Central Park": "Free. Guided walking tours. Nature tours available.",
        "Times Square": "Free. Guided walking tours. Historical tours available.",
        "Brooklyn Bridge": "Free. Guided bridge walks. Audio tours available.",
        
        # Paris venues
        "Louvre Museum": "€17. Guided tours daily. Audio tours included.",
        "Musée d'Orsay": "€16. Guided tours daily. Audio tours included.",
        "Musée du Louvre": "€17. Guided tours daily. Audio tours included.",
        "Eiffel Tower": "€29. Guided tours available. Audio tours included.",
        "Notre-Dame Cathedral": "Free. Guided tours available. Audio tours included.",
        "Arc de Triomphe": "€13. Guided tours available. Audio tours included.",
        "Champs-Élysées": "Free. Guided walking tours. Historical tours available.",
        "Montmartre": "Free. Guided walking tours. Historical tours available.",
        "Seine River": "Free. Guided river walks. Historical tours available.",
        
        # Washington DC venues
        "Smithsonian National Air and Space Museum": "Free. Guided tours daily. Audio tours available.",
        "Smithsonian National Museum of Natural History": "Free. Guided tours daily. Audio tours available.",
        "Smithsonian National Museum of American History": "Free. Guided tours daily. Audio tours available.",
        "Smithsonian National Museum of African American History and Culture": "Free. Guided tours daily. Audio tours available.",
        "Smithsonian National Museum of the American Indian": "Free. Guided tours daily. Audio tours available.",
        "Smithsonian Hirshhorn Museum and Sculpture Garden": "Free. Guided tours daily. Audio tours available.",
        "Smithsonian Freer Gallery of Art": "Free. Guided tours daily. Audio tours available.",
        "Smithsonian Arthur M. Sackler Gallery": "Free. Guided tours daily. Audio tours available.",
        "National Gallery of Art": "Free. Guided tours daily. Audio tours available.",
        "United States Holocaust Memorial Museum": "Free. Guided tours daily. Audio tours available.",
        "International Spy Museum": "$26. Guided tours daily. Audio tours included.",
        "Newseum": "$25. Guided tours daily. Audio tours included.",
        "Lincoln Memorial": "Free. Guided tours available. Audio tours available.",
        "Washington Monument": "Free. Guided tours available. Audio tours included.",
        "Jefferson Memorial": "Free. Guided tours available. Audio tours available.",
        "Vietnam Veterans Memorial": "Free. Guided tours available. Audio tours available.",
        "Korean War Veterans Memorial": "Free. Guided tours available. Audio tours available.",
        "World War II Memorial": "Free. Guided tours available. Audio tours available.",
        "Martin Luther King Jr. Memorial": "Free. Guided tours available. Audio tours available.",
        "Franklin Delano Roosevelt Memorial": "Free. Guided tours available. Audio tours available.",
        "Capitol Building": "Free. Guided tours daily. Audio tours included.",
        "White House": "Free. Guided tours by reservation. Audio tours available.",
        "Supreme Court": "Free. Guided tours daily. Audio tours included.",
        "Library of Congress": "Free. Guided tours daily. Audio tours included.",
        "Georgetown": "Free. Guided walking tours. Historical tours available.",
        "Capitol Hill": "Free. Guided walking tours. Historical tours available.",
        "Dupont Circle": "Free. Guided walking tours. Historical tours available.",
        "National Mall": "Free. Guided walking tours. Historical tours available.",
        "Tidal Basin": "Free. Guided walking tours. Nature tours available.",
        "Rock Creek Park": "Free. Guided walking tours. Nature tours available.",
        "National Zoo": "Free. Guided tours daily. Audio tours available.",
        "Kennedy Center": "Free. Guided tours daily. Audio tours included.",
        "Ford's Theatre": "$3. Guided tours daily. Audio tours included.",
        "Arena Stage": "Admission varies. Guided tours by reservation.",
        
        # Baltimore venues
        "Baltimore Museum of Art": "$20. Guided tours daily. Audio tours included.",
        "Walters Art Museum": "$20. Guided tours daily. Audio tours included.",
        "Fort McHenry National Monument": "$15. Guided tours daily. Audio tours included.",
        "Inner Harbor": "Free. Guided walking tours. Historical tours available.",
        "National Aquarium": "$40. Guided tours daily. Audio tours included.",
        
        # Philadelphia venues
        "Philadelphia Museum of Art": "$25. Guided tours daily. Audio tours included.",
        "Independence Hall": "Free. Guided tours daily. Audio tours included.",
        "Liberty Bell Center": "Free. Guided tours daily. Audio tours included.",
        "Franklin Institute": "$23. Guided tours daily. Audio tours included.",
        "Reading Terminal Market": "Free. Guided walking tours. Food tours available."
    }
    
    return tour_info.get(venue_name, f"Admission varies. Guided tours available. Audio tours available.")

def make_tour_info_concise():
    """Make tour_info field concise for all venues"""
    
    print("✂️ Making tour_info concise...")
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
    
    updated_count = 0
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
            
            # Get concise tour info
            concise_tour_info = get_concise_tour_info(venue_name, venue_type, city_name)
            
            # Update tour_info
            venue['tour_info'] = concise_tour_info
            updated_count += 1
            print(f"      ✅ Made concise")
    
    # Update metadata
    data['metadata']['last_tour_info_update'] = "2025-09-10 17:45:00"
    data['metadata']['tour_info_status'] = "Concise tour details"
    
    # Save updated data
    with open(venues_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Tour info made concise!")
    print(f"   Updated: {updated_count}/{total_venues} venues")
    print(f"   Updated: {venues_file}")
    
    return True

if __name__ == "__main__":
    success = make_tour_info_concise()
    if not success:
        sys.exit(1)
