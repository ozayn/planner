#!/usr/bin/env python3
"""
Check all venues for city_id and city_name consistency with cities table
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, City

def check_venue_city_consistency():
    """Check all venues for city_id and city_name consistency"""
    import json
    
    with app.app_context():
        # Get all cities and create a mapping
        all_cities = City.query.all()
        city_id_to_name = {city.id: city.name for city in all_cities}
        city_id_to_full_info = {
            city.id: {
                'name': city.name,
                'state': city.state or '',
                'country': city.country or ''
            } for city in all_cities
        }
        
        print(f"📊 Found {len(all_cities)} cities in database\n")
        
        # Check database venues
        all_venues = Venue.query.all()
        print(f"📊 Checking {len(all_venues)} venues in database...\n")
        
        db_issues = []
        
        for venue in all_venues:
            venue_city_id = venue.city_id
            
            # Check if city_id exists
            if venue_city_id not in city_id_to_name:
                db_issues.append({
                    'venue_id': venue.id,
                    'venue_name': venue.name,
                    'issue': f'city_id {venue_city_id} does not exist in cities table',
                    'venue_city_id': venue_city_id
                })
                continue
            
            # Get the actual city name for this city_id
            actual_city_name = city_id_to_name[venue_city_id]
            
            # Get city from relationship (if available)
            venue_city = venue.city if hasattr(venue, 'city') else None
            if venue_city:
                # Verify the relationship is correct
                if venue_city.id != venue_city_id:
                    db_issues.append({
                        'venue_id': venue.id,
                        'venue_name': venue.name,
                        'issue': f'city relationship mismatch: city_id={venue_city_id} but relationship points to city_id={venue_city.id}',
                        'venue_city_id': venue_city_id,
                        'actual_city_name': actual_city_name
                    })
        
        # Check JSON file
        print(f"📊 Checking venues.json file...\n")
        json_issues = []
        json_fixes = []
        
        venues_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'venues.json')
        if os.path.exists(venues_file):
            with open(venues_file, 'r') as f:
                venues_data = json.load(f)
            
            venues_section = venues_data.get('venues', {})
            
            for venue_id_str, venue_data in venues_section.items():
                if not isinstance(venue_data, dict) or 'name' not in venue_data:
                    continue
                
                venue_name = venue_data.get('name', '')
                json_city_id = venue_data.get('city_id')
                json_city_name = venue_data.get('city_name', '')
                
                # Check if city_id exists
                if json_city_id not in city_id_to_name:
                    json_issues.append({
                        'venue_id': venue_id_str,
                        'venue_name': venue_name,
                        'issue': f'city_id {json_city_id} does not exist in cities table',
                        'json_city_id': json_city_id,
                        'json_city_name': json_city_name
                    })
                    continue
                
                # Get the actual city name for this city_id
                actual_city_info = city_id_to_full_info[json_city_id]
                actual_city_name = actual_city_info['name']
                
                # Check if city_name matches (case-insensitive, handle variations)
                json_city_name_lower = json_city_name.lower().strip()
                actual_city_name_lower = actual_city_name.lower().strip()
                
                # Handle common variations (e.g., "Washington" vs "Washington, DC")
                json_city_base = json_city_name_lower.split(',')[0].strip()
                actual_city_base = actual_city_name_lower.split(',')[0].strip()
                
                if json_city_base != actual_city_base:
                    json_issues.append({
                        'venue_id': venue_id_str,
                        'venue_name': venue_name,
                        'issue': f'city_name mismatch: "{json_city_name}" (in JSON) vs "{actual_city_name}" (actual)',
                        'json_city_id': json_city_id,
                        'json_city_name': json_city_name,
                        'actual_city_name': actual_city_name
                    })
                    
                    # Fix it
                    venue_data['city_name'] = actual_city_name
                    json_fixes.append({
                        'venue_id': venue_id_str,
                        'venue_name': venue_name,
                        'old_city_name': json_city_name,
                        'new_city_name': actual_city_name
                    })
        
        # Save JSON fixes
        if json_fixes:
            with open(venues_file, 'w') as f:
                json.dump(venues_data, f, indent=2)
            print(f"✅ Fixed {len(json_fixes)} venues in JSON file:\n")
            for fix in json_fixes:
                print(f"  Venue ID {fix['venue_id']}: {fix['venue_name']}")
                print(f"    Updated city_name: '{fix['old_city_name']}' → '{fix['new_city_name']}'")
            print()
        
        # Report database issues
        if db_issues:
            print(f"⚠️  Found {len(db_issues)} issues in database:\n")
            for issue in db_issues:
                print(f"  Venue ID {issue['venue_id']}: {issue['venue_name']}")
                print(f"    Issue: {issue['issue']}")
                print()
        else:
            print("✅ All database venues have valid city_id!")
        
        # Report JSON issues
        if json_issues:
            print(f"⚠️  Found {len(json_issues)} issues in JSON file:\n")
            for issue in json_issues:
                print(f"  Venue ID {issue['venue_id']}: {issue['venue_name']}")
                print(f"    Issue: {issue['issue']}")
                if 'actual_city_name' in issue:
                    print(f"    Should be: {issue['actual_city_name']}")
                print()
        else:
            print("✅ All JSON venues have consistent city_id and city_name!")
        
        return len(db_issues) == 0 and len(json_issues) == 0

if __name__ == '__main__':
    try:
        check_venue_city_consistency()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
