#!/usr/bin/env python3
"""
Update sources.json with current database sources
This function will be imported and used in other scripts
"""

import json
import os
from pathlib import Path
from datetime import datetime

def update_sources_json():
    """Update sources.json with current database sources"""
    try:
        import sys
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, project_root)
        
        from app import app, Source, City
        
        with app.app_context():
            # Get all sources from database with their cities
            sources = Source.query.join(City).order_by(City.name, Source.name).all()
            
            # Create the JSON structure (similar format to venues.json and cities.json)
            sources_data = {}
            
            # Group sources by city
            for source in sources:
                city_id = str(source.city_id)
                
                if city_id not in sources_data:
                    sources_data[city_id] = {
                        "name": source.city.name,
                        "sources": []
                    }
                
                # Parse event types from JSON string
                try:
                    event_types = json.loads(source.event_types) if source.event_types else []
                except:
                    event_types = []
                
                # Parse covered cities from JSON string
                try:
                    covered_cities = json.loads(source.covered_cities) if source.covered_cities else None
                except:
                    covered_cities = None
                
                # Create source entry
                source_entry = {
                    "id": source.id,
                    "name": source.name,
                    "handle": source.handle,
                    "source_type": source.source_type,
                    "url": source.url or "",
                    "description": source.description or "",
                    "city_id": source.city_id,
                    "city_name": source.city.name,
                    "covers_multiple_cities": source.covers_multiple_cities,
                    "covered_cities": covered_cities,
                    "event_types": event_types,
                    "is_active": source.is_active,
                    "last_checked": source.last_checked.isoformat() if source.last_checked else "",
                    "last_event_found": source.last_event_found.isoformat() if source.last_event_found else "",
                    "events_found_count": source.events_found_count,
                    "reliability_score": source.reliability_score,
                    "posting_frequency": source.posting_frequency or "",
                    "notes": source.notes or "",
                    "scraping_pattern": source.scraping_pattern or "",
                    "created_at": source.created_at.isoformat() if source.created_at else "",
                    "updated_at": source.updated_at.isoformat() if source.updated_at else ""
                }
                
                sources_data[city_id]["sources"].append(source_entry)
            
            # Create backup of existing sources.json if it exists
            sources_file = Path("data/sources.json")
            if sources_file.exists():
                backup_file = f"data/backups/sources.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                
                import shutil
                shutil.copy2(sources_file, backup_file)
                print(f"📋 Backup created: {backup_file}")
            
            # Save to sources.json
            with open(sources_file, 'w') as f:
                json.dump(sources_data, f, indent=2, ensure_ascii=False)
            
            total_sources = sum(len(city_data["sources"]) for city_data in sources_data.values())
            print(f"✅ sources.json updated successfully!")
            print(f"   Total sources: {total_sources}")
            print(f"   Cities: {len(sources_data)}")
            
            # Show breakdown by source type
            source_types = {}
            for city_data in sources_data.values():
                for source in city_data["sources"]:
                    source_type = source["source_type"]
                    source_types[source_type] = source_types.get(source_type, 0) + 1
            
            print(f"   Source types: {source_types}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating sources.json: {e}")
        return False

if __name__ == "__main__":
    success = update_sources_json()
    if not success:
        exit(1)
