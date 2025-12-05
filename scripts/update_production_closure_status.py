#!/usr/bin/env python3
"""
Update closure status directly in production database via API
"""

import requests
import json
import sys

def update_production_closure_status():
    """Update closure status in production database"""
    
    base_url = "https://planner.ozayn.com"
    
    # Get all venues from production
    print("📡 Fetching venues from production...")
    response = requests.get(f"{base_url}/api/admin/venues")
    if response.status_code != 200:
        print(f"❌ Error fetching venues: {response.status_code}")
        return False
    
    venues = response.json()
    print(f"✅ Found {len(venues)} venues in production")
    
    # Get DC venues
    dc_venues = [v for v in venues if 'Washington' in v.get('city_name', '')]
    print(f"🏛️ Found {len(dc_venues)} DC venues")
    
    # Define closure status for each venue
    closure_status_map = {
        # Government venues - CLOSED
        'Smithsonian National Museum of Natural History': 'closed',
        'Smithsonian National Museum of American History': 'closed',
        'Smithsonian National Museum of African American History and Culture': 'closed',
        'Smithsonian National Air and Space Museum': 'closed',
        'Smithsonian National Museum of the American Indian': 'closed',
        'Smithsonian Hirshhorn Museum and Sculpture Garden': 'closed',
        'Smithsonian National Museum of Asian Art': 'closed',
        'National Gallery of Art': 'closed',
        'United States Holocaust Memorial Museum': 'closed',
        'National Zoo': 'closed',
        'United States Botanic Garden': 'closed',
        'Capitol Building': 'closed',
        'White House': 'closed',
        'Supreme Court': 'closed',
        'Library of Congress': 'closed',
        'National Portrait Gallery': 'closed',
        
        # Private venues - OPEN
        'International Spy Museum': 'open',
        'Newseum': 'open',
        'The Phillips Collection': 'open',
        'Arena Stage': 'open',
        "Ford's Theatre": 'open',
        'Kennedy Center': 'open',
        '9:30 Club': 'open',
        'Suns Cinema': 'open',
        'Politics and Prose Bookstore': 'open',
        'Kramerbooks & Afterwords Cafe': 'open',
        'The Hamilton': 'open',
        'Founding Farmers': 'open',
        
        # Outdoor sites - OPEN
        'Lincoln Memorial': 'open',
        'Jefferson Memorial': 'open',
        'Martin Luther King Jr. Memorial': 'open',
        'Vietnam Veterans Memorial': 'open',
        'Korean War Veterans Memorial': 'open',
        'World War II Memorial': 'open',
        'Washington Monument': 'open',
        'National Mall': 'open',
        'Rock Creek Park': 'open',
        'Tidal Basin': 'open',
        'Georgetown': 'open',
        'Dupont Circle': 'open',
        
        # Embassies - OPEN
        'Embassy of the United Kingdom': 'open',
        'Embassy of France': 'open',
        'Embassy of Germany': 'open',
        'Embassy of Italy': 'open',
        'Embassy of Japan': 'open',
        'Embassy of Canada': 'open',
        'Embassy of Spain': 'open',
        'Embassy of the Netherlands': 'open',
        'Embassy of Australia': 'open',
        'Embassy of Brazil': 'open',
        'Embassy of India': 'open',
        'Embassy of Mexico': 'open',
        'Embassy of South Korea': 'open',
        'Embassy of Sweden': 'open',
        'Embassy of Switzerland': 'open'
    }
    
    updated_count = 0
    
    for venue in dc_venues:
        venue_name = venue['name']
        venue_id = venue['id']
        
        if venue_name in closure_status_map:
            closure_status = closure_status_map[venue_name]
            
            # Create additional_info with closure status
            additional_info = {
                'closure_status': closure_status,
                'closure_reason': 'Closed due to government shutdown. Check website for reopening updates.' if closure_status == 'closed' else 'Independent venue - typically remains open during government shutdown.' if closure_status == 'open' else 'Status unknown - please check venue website for current hours.',
                'last_updated': '2025-10-21T21:00:00.000000'
            }
            
            # Update venue via API
            update_data = {
                'additional_info': json.dumps(additional_info)
            }
            
            try:
                response = requests.put(f"{base_url}/api/admin/venues/{venue_id}", json=update_data)
                if response.status_code == 200:
                    print(f"✅ Updated {venue_name}: {closure_status.upper()}")
                    updated_count += 1
                else:
                    print(f"❌ Failed to update {venue_name}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error updating {venue_name}: {e}")
    
    print(f"\n🎉 Successfully updated {updated_count} venues with closure status!")
    return True

def main():
    """Main function"""
    success = update_production_closure_status()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

