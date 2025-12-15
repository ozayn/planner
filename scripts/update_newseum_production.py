#!/usr/bin/env python3
"""
Update Newseum closure status in production database
"""

import requests
import json
from datetime import datetime

def update_newseum_in_production():
    """Update Newseum to closed status in production"""
    
    base_url = "https://planner.ozayn.com"
    
    print("📡 Fetching venues from production...")
    response = requests.get(f"{base_url}/api/admin/venues")
    if response.status_code != 200:
        print(f"❌ Error fetching venues: {response.status_code}")
        return False
    
    venues = response.json()
    print(f"✅ Found {len(venues)} venues in production")
    
    # Find Newseum
    newseum = None
    for venue in venues:
        if venue.get('name', '').lower() == 'newseum':
            newseum = venue
            break
    
    if not newseum:
        print("⚠️  Newseum not found in production database")
        return False
    
    print(f"✅ Found Newseum (ID: {newseum['id']})")
    
    # Prepare update data
    additional_info = {
        'closure_status': 'closed',
        'closure_reason': 'Newseum permanently closed in December 2019.',
        'last_updated': datetime.now().isoformat()
    }
    
    update_data = {
        'opening_hours': 'Permanently closed',
        'additional_info': json.dumps(additional_info)
    }
    
    # Update venue via API
    try:
        print(f"📝 Updating Newseum in production...")
        response = requests.put(
            f"{base_url}/api/admin/venues/{newseum['id']}", 
            json=update_data
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully updated Newseum in production:")
            print(f"   - opening_hours: Permanently closed")
            print(f"   - closure_status: closed")
            return True
        else:
            print(f"❌ Failed to update Newseum: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating Newseum: {e}")
        return False

if __name__ == "__main__":
    success = update_newseum_in_production()
    exit(0 if success else 1)
