#!/usr/bin/env python3
"""
Update sources.json from database
Syncs the sources.json file with the current database state
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Source

def sanitize_json_file_for_backup(source_file, backup_file):
    """Create a sanitized backup of the JSON file"""
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Sanitize any sensitive data if needed
        sanitized_data = data  # No specific sanitization needed for sources.json
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error creating sanitized backup: {e}")
        import shutil
        shutil.copy2(source_file, backup_file)

def update_sources_json():
    """Update sources.json from database"""
    print("🔄 Updating sources.json from database...")
    
    with app.app_context():
        try:
            sources = Source.query.order_by(Source.id).all()
            print(f"📊 Found {len(sources)} sources in database")

            sources_data = {}
            for source in sources:
                source_data = {
                    "name": source.name,
                    "handle": source.handle or "",
                    "source_type": source.source_type or "instagram",
                    "url": source.url or "",
                    "description": source.description or "",
                    "city_id": source.city_id,
                    "covers_multiple_cities": source.covers_multiple_cities or False,
                    "covered_cities": source.covered_cities or "",
                    "event_types": source.event_types or "[]",
                    "is_active": source.is_active,
                    "reliability_score": source.reliability_score,
                    "posting_frequency": source.posting_frequency or "",
                    "notes": source.notes or "",
                    "scraping_pattern": source.scraping_pattern or "",
                    "last_checked": source.last_checked.isoformat() if source.last_checked else None,
                    "created_at": source.created_at.isoformat() if source.created_at else None,
                    "updated_at": source.updated_at.isoformat() if source.updated_at else None
                }
                sources_data[str(source.id)] = source_data
                print(f"  Added: {source.name} (ID: {source.id})")

            final_data = {
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "description": "Sources exported from database - always most updated version",
                    "total_sources": len(sources),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "sources": sources_data
            }

            sources_file = Path("data/sources.json")
            if sources_file.exists():
                backup_dir = Path("data/backups")
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / f"sources.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                sanitize_json_file_for_backup(sources_file, backup_file)
                print(f"📦 Created backup: {backup_file}")

            with open(sources_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Successfully updated sources.json with {len(sources)} sources")
            return True

        except Exception as e:
            print(f"❌ Error updating sources.json: {e}")
            return False

if __name__ == '__main__':
    with app.app_context():
        sys.exit(0 if update_sources_json() else 1)



