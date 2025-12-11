#!/usr/bin/env python3
"""
Check all sources for city_id and city_name consistency with cities table
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Source, City
import json

def check_source_city_consistency():
    """Check all sources for city_id and city_name consistency"""
    with app.app_context():
        # Get all cities and create a mapping
        all_cities = City.query.all()
        city_id_to_info = {
            city.id: {
                'name': city.name,
                'state': city.state or '',
                'country': city.country or ''
            } for city in all_cities
        }
        
        print(f"📊 Found {len(all_cities)} cities in database\n")
        
        # Check database sources
        all_sources = Source.query.all()
        print(f"📊 Checking {len(all_sources)} sources in database...\n")
        
        db_issues = []
        
        for source in all_sources:
            source_city_id = source.city_id
            
            # Check if city_id exists
            if source_city_id not in city_id_to_info:
                db_issues.append({
                    'source_id': source.id,
                    'source_name': source.name,
                    'issue': f'city_id {source_city_id} does not exist in cities table',
                    'source_city_id': source_city_id
                })
                continue
            
            # Get the actual city name for this city_id
            actual_city_info = city_id_to_info[source_city_id]
            actual_city_name = actual_city_info['name']
            
            # Get city from relationship (if available)
            source_city = source.city if hasattr(source, 'city') else None
            if source_city:
                # Verify the relationship is correct
                if source_city.id != source_city_id:
                    db_issues.append({
                        'source_id': source.id,
                        'source_name': source.name,
                        'issue': f'city relationship mismatch: city_id={source_city_id} but relationship points to city_id={source_city.id}',
                        'source_city_id': source_city_id,
                        'actual_city_name': actual_city_name
                    })
        
        # Check JSON file
        print(f"📊 Checking sources.json file...\n")
        json_issues = []
        json_fixes = []
        
        sources_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sources.json')
        if os.path.exists(sources_file):
            with open(sources_file, 'r') as f:
                sources_data = json.load(f)
            
            sources_section = sources_data.get('sources', {})
            
            for source_id_str, source_data in sources_section.items():
                if not isinstance(source_data, dict) or 'name' not in source_data:
                    continue
                
                source_name = source_data.get('name', '')
                json_city_id = source_data.get('city_id')
                json_city_name = source_data.get('city_name', '')
                
                # Check if city_id exists
                if json_city_id not in city_id_to_info:
                    json_issues.append({
                        'source_id': source_id_str,
                        'source_name': source_name,
                        'issue': f'city_id {json_city_id} does not exist in cities table',
                        'json_city_id': json_city_id,
                        'json_city_name': json_city_name
                    })
                    continue
                
                # Get the actual city name for this city_id
                actual_city_info = city_id_to_info[json_city_id]
                actual_city_name = actual_city_info['name']
                
                # Check if city_name matches (case-insensitive, handle variations)
                json_city_name_lower = json_city_name.lower().strip()
                actual_city_name_lower = actual_city_name.lower().strip()
                
                # Handle common variations (e.g., "Washington" vs "Washington, DC")
                json_city_base = json_city_name_lower.split(',')[0].strip()
                actual_city_base = actual_city_name_lower.split(',')[0].strip()
                
                if json_city_base != actual_city_base:
                    json_issues.append({
                        'source_id': source_id_str,
                        'source_name': source_name,
                        'issue': f'city_name mismatch: "{json_city_name}" (in JSON) vs "{actual_city_name}" (actual)',
                        'json_city_id': json_city_id,
                        'json_city_name': json_city_name,
                        'actual_city_name': actual_city_name
                    })
                    
                    # Fix it
                    source_data['city_name'] = actual_city_name
                    json_fixes.append({
                        'source_id': source_id_str,
                        'source_name': source_name,
                        'old_city_name': json_city_name,
                        'new_city_name': actual_city_name
                    })
        
        # Save JSON fixes
        if json_fixes:
            with open(sources_file, 'w') as f:
                json.dump(sources_data, f, indent=2)
            print(f"✅ Fixed {len(json_fixes)} sources in JSON file:\n")
            for fix in json_fixes:
                print(f"  Source ID {fix['source_id']}: {fix['source_name']}")
                print(f"    Updated city_name: '{fix['old_city_name']}' → '{fix['new_city_name']}'")
            print()
        
        # Report database issues
        if db_issues:
            print(f"⚠️  Found {len(db_issues)} issues in database:\n")
            for issue in db_issues:
                print(f"  Source ID {issue['source_id']}: {issue['source_name']}")
                print(f"    Issue: {issue['issue']}")
                print()
        else:
            print("✅ All database sources have valid city_id!")
        
        # Report JSON issues
        if json_issues:
            print(f"⚠️  Found {len(json_issues)} issues in JSON file:\n")
            for issue in json_issues:
                print(f"  Source ID {issue['source_id']}: {issue['source_name']}")
                print(f"    Issue: {issue['issue']}")
                if 'actual_city_name' in issue:
                    print(f"    Should be: {issue['actual_city_name']}")
                print()
        else:
            print("✅ All JSON sources have consistent city_id and city_name!")
        
        return len(db_issues) == 0 and len(json_issues) == 0

if __name__ == '__main__':
    try:
        check_source_city_consistency()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
