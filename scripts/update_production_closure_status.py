#!/usr/bin/env python3
"""
Update closure status directly in production database via API
"""

import requests
import json
import sys
from datetime import datetime

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
    
    # Define closure status for each venue (update during government shutdowns)
    closure_status_map = {
        # Government venues - OPEN (update to 'closed' during government shutdowns)
        'Smithsonian National Museum of Natural History': 'open',
        'Smithsonian National Museum of American History': 'open',
        'Smithsonian National Museum of African American History and Culture': 'open',
        'Smithsonian National Air and Space Museum': 'open',
        'Smithsonian National Museum of the American Indian': 'open',
        'Smithsonian Hirshhorn Museum and Sculpture Garden': 'open',
        'Smithsonian National Museum of Asian Art': 'open',
        'National Gallery of Art': 'open',
        'United States Holocaust Memorial Museum': 'open',
        'National Zoo': 'open',
        'United States Botanic Garden': 'open',
        'Capitol Building': 'open',
        'White House': 'open',
        'Supreme Court': 'open',
        'Library of Congress': 'open',
        'National Portrait Gallery': 'open',
        
        # Private venues - OPEN
        'International Spy Museum': 'open',
        'Newseum': 'closed',  # Permanently closed in December 2019
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
            if closure_status == 'closed':
                closure_reason = 'Closed due to government shutdown. Check website for reopening updates.'
            elif closure_status == 'open':
                closure_reason = 'Open - check venue website for current hours.'
            else:
                closure_reason = 'Status unknown - please check venue website for current hours.'
            additional_info = {
                'closure_status': closure_status,
                'closure_reason': closure_reason,
                'last_updated': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
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

