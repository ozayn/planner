#!/usr/bin/env python3
"""
List open museums in Washington DC during government shutdown
"""

import sys
import os
import json

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue

def list_open_museums():
    """List museums that are open during government shutdown"""
    
    with app.app_context():
        # Get Washington DC venues
        dc_venues = Venue.query.filter_by(city_id=1).all()
        
        print("🏛️ MUSEUMS OPEN DURING GOVERNMENT SHUTDOWN")
        print("=" * 60)
        
        # Categorize venues
        open_museums = []
        closed_museums = []
        outdoor_sites = []
        entertainment_venues = []
        embassies = []
        
        for venue in dc_venues:
            # Get closure status from additional_info
            closure_status = "unknown"
            closure_reason = ""
            
            if venue.additional_info:
                try:
                    additional_info = json.loads(venue.additional_info)
                    closure_status = additional_info.get('closure_status', 'unknown')
                    closure_reason = additional_info.get('closure_reason', '')
                except:
                    pass
            
            venue_info = {
                'name': venue.name,
                'type': venue.venue_type,
                'status': closure_status,
                'reason': closure_reason,
                'website': venue.website_url,
                'address': venue.address
            }
            
            if closure_status == "open":
                if venue.venue_type == "museum":
                    open_museums.append(venue_info)
                elif venue.venue_type in ["memorial", "landmark", "park"]:
                    outdoor_sites.append(venue_info)
                elif venue.venue_type in ["theater", "cinema", "restaurant", "bookstore"]:
                    entertainment_venues.append(venue_info)
                elif venue.venue_type == "embassy":
                    embassies.append(venue_info)
            elif closure_status == "closed":
                closed_museums.append(venue_info)
        
        # Display open museums
        if open_museums:
            print("\n🟢 OPEN MUSEUMS:")
            print("-" * 30)
            for museum in open_museums:
                print(f"🏛️  {museum['name']}")
                print(f"   📍 {museum['address']}")
                print(f"   🌐 {museum['website']}")
                print()
        
        # Display outdoor sites
        if outdoor_sites:
            print("\n🟢 OPEN OUTDOOR SITES & MEMORIALS:")
            print("-" * 40)
            for site in outdoor_sites:
                print(f"🏛️  {site['name']}")
                print(f"   📍 {site['address']}")
                print(f"   🌐 {site['website']}")
                print()
        
        # Display entertainment venues
        if entertainment_venues:
            print("\n🟢 OPEN ENTERTAINMENT & CULTURAL VENUES:")
            print("-" * 45)
            for venue in entertainment_venues:
                print(f"🎭  {venue['name']}")
                print(f"   📍 {venue['address']}")
                print(f"   🌐 {venue['website']}")
                print()
        
        # Display closed museums
        if closed_museums:
            print("\n🔴 CLOSED DURING GOVERNMENT SHUTDOWN:")
            print("-" * 40)
            for museum in closed_museums:
                print(f"🚫 {museum['name']}")
                print(f"   ⚠️  {museum['reason']}")
                print()
        
        # Summary
        print("\n📊 SUMMARY:")
        print("=" * 20)
        print(f"🟢 Open Museums: {len(open_museums)}")
        print(f"🟢 Open Outdoor Sites: {len(outdoor_sites)}")
        print(f"🟢 Open Entertainment Venues: {len(entertainment_venues)}")
        print(f"🔴 Closed Museums: {len(closed_museums)}")
        
        return True

def main():
    """Main function"""
    success = list_open_museums()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
