#!/usr/bin/env python3
"""
Compare venue URLs between local venues.json and deployed API
"""

import json
import sys
import subprocess

def load_local_venues():
    """Load venues from local venues.json"""
    with open('data/venues.json', 'r') as f:
        data = json.load(f)
    venues = data.get('venues', {})
    
    local_venues = {}
    for venue_id, venue in venues.items():
        if isinstance(venue, dict) and 'name' in venue:
            name = venue.get('name')
            url = venue.get('website_url', '')
            city = venue.get('city_name', 'Unknown')
            local_venues[name] = {
                'url': url,
                'city': city
            }
    return local_venues

def load_deployed_venues():
    """Load venues from deployed API"""
    try:
        result = subprocess.run(
            ['curl', '-s', 'https://planner.ozayn.com/api/admin/venues'],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode != 0:
            print(f"Error: curl failed with return code {result.returncode}")
            return {}
        
        data = json.loads(result.stdout)
        venues = data if isinstance(data, list) else data.get('venues', [])
        
        deployed_venues = {}
        for venue in venues:
            name = venue.get('name')
            url = venue.get('website_url', '')
            # Extract city name from full city string (format: "City, State, Country")
            city_full = venue.get('city_name', 'Unknown')
            city = city_full.split(',')[0] if ',' in city_full else city_full
            deployed_venues[name] = {
                'url': url,
                'city': city
            }
        return deployed_venues
    except Exception as e:
        print(f"Error loading deployed venues: {e}")
        import traceback
        traceback.print_exc()
        return {}

def compare_urls():
    """Compare URLs between local and deployed"""
    print("Loading local venues...")
    local = load_local_venues()
    print(f"Found {len(local)} venues locally")
    
    print("\nLoading deployed venues...")
    deployed = load_deployed_venues()
    print(f"Found {len(deployed)} venues on deployed API")
    
    print("\n" + "=" * 100)
    print("COMPARING VENUE URLs")
    print("=" * 100)
    
    mismatches = []
    missing_local = []
    missing_deployed = []
    
    # Check all deployed venues
    for name, deployed_info in deployed.items():
        local_info = local.get(name)
        if not local_info:
            missing_local.append((name, deployed_info['city'], deployed_info['url']))
        elif local_info['url'] != deployed_info['url']:
            mismatches.append({
                'name': name,
                'city': deployed_info['city'],
                'local_url': local_info['url'],
                'deployed_url': deployed_info['url']
            })
    
    # Check for venues in local but not in deployed
    for name, local_info in local.items():
        if name not in deployed:
            missing_deployed.append((name, local_info['city'], local_info['url']))
    
    # Print results
    if mismatches:
        print(f"\n❌ FOUND {len(mismatches)} URL MISMATCHES:")
        print("-" * 100)
        for m in mismatches:
            print(f"\n📍 {m['city']:20} | {m['name']}")
            print(f"   Local:    {m['local_url']}")
            print(f"   Deployed: {m['deployed_url']}")
    else:
        print("\n✅ No URL mismatches found!")
    
    if missing_local:
        print(f"\n⚠️  {len(missing_local)} venues in deployed but not in local:")
        for name, city, url in missing_local[:10]:
            print(f"   {city:20} | {name:40} | {url}")
        if len(missing_local) > 10:
            print(f"   ... and {len(missing_local) - 10} more")
    
    if missing_deployed:
        print(f"\n⚠️  {len(missing_deployed)} venues in local but not in deployed:")
        for name, city, url in missing_deployed[:10]:
            print(f"   {city:20} | {name:40} | {url}")
        if len(missing_deployed) > 10:
            print(f"   ... and {len(missing_deployed) - 10} more")
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total local venues:     {len(local)}")
    print(f"Total deployed venues:  {len(deployed)}")
    print(f"URL mismatches:         {len(mismatches)}")
    print(f"Missing in local:       {len(missing_local)}")
    print(f"Missing in deployed:    {len(missing_deployed)}")
    
    return mismatches

if __name__ == "__main__":
    mismatches = compare_urls()
    sys.exit(0 if not mismatches else 1)

