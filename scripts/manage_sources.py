#!/usr/bin/env python3
"""
Manage Event Sources Script
Add, update, and manage Instagram/website sources for event tracking
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, City

def create_sources_table():
    """Create the sources table in the database"""
    print("🏗️ Creating sources table...")
    
    with app.app_context():
        try:
            # Check if sources table already exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'sources' in inspector.get_table_names():
                print("✅ Sources table already exists")
                return True
            
            # Create the table
            db.create_all()
            print("✅ Sources table created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating sources table: {e}")
            return False

def add_sample_sources():
    """Add some sample sources for Princeton"""
    print("📱 Adding sample sources for Princeton...")
    
    with app.app_context():
        try:
            # Find Princeton city
            princeton_city = City.query.filter_by(name="Princeton").first()
            if not princeton_city:
                print("❌ Princeton city not found")
                return False
            
            # Sample sources
            sample_sources = [
                {
                    "name": "Princeton Photography Club",
                    "handle": "@princetonphotoclub",
                    "source_type": "instagram",
                    "url": "https://www.instagram.com/princetonphotoclub/",
                    "description": "Local photography club that posts photowalks and photography events in Princeton",
                    "city_id": princeton_city.id,
                    "covers_multiple_cities": False,
                    "event_types": json.dumps(["photowalk", "tour"]),
                    "is_active": True,
                    "reliability_score": 7.5,
                    "posting_frequency": "weekly",
                    "notes": "Posts mostly on weekends, check stories for last-minute events",
                    "scraping_pattern": "Check posts and stories weekly, look for event announcements"
                },
                {
                    "name": "Princeton University Events",
                    "handle": "princeton.edu/events",
                    "source_type": "website",
                    "url": "https://www.princeton.edu/events",
                    "description": "Official Princeton University events calendar",
                    "city_id": princeton_city.id,
                    "covers_multiple_cities": False,
                    "event_types": json.dumps(["tour", "exhibition", "festival"]),
                    "is_active": True,
                    "reliability_score": 9.0,
                    "posting_frequency": "daily",
                    "notes": "Official university source, very reliable",
                    "scraping_pattern": "Check daily, events are well-structured"
                },
                {
                    "name": "Morven Museum Events",
                    "handle": "@morvenmuseum",
                    "source_type": "instagram",
                    "url": "https://www.instagram.com/morvenmuseum/",
                    "description": "Morven Museum & Garden Instagram account for events and exhibitions",
                    "city_id": princeton_city.id,
                    "covers_multiple_cities": False,
                    "event_types": json.dumps(["exhibition", "tour"]),
                    "is_active": True,
                    "reliability_score": 8.0,
                    "posting_frequency": "weekly",
                    "notes": "Museum events, garden tours, special exhibitions",
                    "scraping_pattern": "Check weekly for new exhibitions and special events"
                }
            ]
            
            # Import the Source model (we'll need to add this to app.py)
            # For now, let's just show what we would do
            print("📋 Sample sources to add:")
            for i, source in enumerate(sample_sources, 1):
                print(f"  {i}. {source['name']} ({source['source_type']})")
                print(f"     Handle: {source['handle']}")
                print(f"     URL: {source['url']}")
                print(f"     Event types: {source['event_types']}")
                print(f"     Reliability: {source['reliability_score']}/10")
                print()
            
            print("⚠️ Note: Source model needs to be added to app.py first")
            return True
            
        except Exception as e:
            print(f"❌ Error adding sample sources: {e}")
            return False

def create_sources_json():
    """Create sources.json file with sample data"""
    print("📄 Creating sources.json...")
    
    try:
        # Sample sources data
        sources_data = {
            "metadata": {
                "version": "1.0",
                "created": datetime.now().strftime("%Y-%m-%d"),
                "description": "Event sources for tracking Instagram accounts, websites, and other event sources",
                "total_sources": 3,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "sources": {
                "1": {
                    "name": "Princeton Photography Club",
                    "handle": "@princetonphotoclub",
                    "source_type": "instagram",
                    "url": "https://www.instagram.com/princetonphotoclub/",
                    "description": "Local photography club that posts photowalks and photography events in Princeton",
                    "city_id": 1,
                    "city_name": "Princeton",
                    "covers_multiple_cities": False,
                    "covered_cities": None,
                    "event_types": ["photowalk", "tour"],
                    "is_active": True,
                    "last_checked": None,
                    "last_event_found": None,
                    "events_found_count": 0,
                    "reliability_score": 7.5,
                    "posting_frequency": "weekly",
                    "notes": "Posts mostly on weekends, check stories for last-minute events",
                    "scraping_pattern": "Check posts and stories weekly, look for event announcements"
                },
                "2": {
                    "name": "Princeton University Events",
                    "handle": "princeton.edu/events",
                    "source_type": "website",
                    "url": "https://www.princeton.edu/events",
                    "description": "Official Princeton University events calendar",
                    "city_id": 1,
                    "city_name": "Princeton",
                    "covers_multiple_cities": False,
                    "covered_cities": None,
                    "event_types": ["tour", "exhibition", "festival"],
                    "is_active": True,
                    "last_checked": None,
                    "last_event_found": None,
                    "events_found_count": 0,
                    "reliability_score": 9.0,
                    "posting_frequency": "daily",
                    "notes": "Official university source, very reliable",
                    "scraping_pattern": "Check daily, events are well-structured"
                },
                "3": {
                    "name": "Morven Museum Events",
                    "handle": "@morvenmuseum",
                    "source_type": "instagram",
                    "url": "https://www.instagram.com/morvenmuseum/",
                    "description": "Morven Museum & Garden Instagram account for events and exhibitions",
                    "city_id": 1,
                    "city_name": "Princeton",
                    "covers_multiple_cities": False,
                    "covered_cities": None,
                    "event_types": ["exhibition", "tour"],
                    "is_active": True,
                    "last_checked": None,
                    "last_event_found": None,
                    "events_found_count": 0,
                    "reliability_score": 8.0,
                    "posting_frequency": "weekly",
                    "notes": "Museum events, garden tours, special exhibitions",
                    "scraping_pattern": "Check weekly for new exhibitions and special events"
                }
            }
        }
        
        # Create sources.json
        sources_file = Path("data/sources.json")
        
        # Create backup if exists
        if sources_file.exists():
            backup_file = f"data/backups/sources.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(os.path.dirname(backup_file), exist_ok=True)
            
            import shutil
            shutil.copy2(sources_file, backup_file)
            print(f"📋 Backup created: {backup_file}")
        
        # Save sources.json
        with open(sources_file, 'w') as f:
            json.dump(sources_data, f, indent=2, ensure_ascii=False)
        
        print("✅ sources.json created successfully!")
        print(f"   File: {sources_file.absolute()}")
        print(f"   Total sources: {sources_data['metadata']['total_sources']}")
        
        # Show summary
        print(f"\n📋 Sample sources created:")
        print("-" * 50)
        for source_id, source_info in sources_data['sources'].items():
            print(f"  {source_id}. {source_info['name']} ({source_info['source_type']})")
            print(f"     Handle: {source_info['handle']}")
            print(f"     Event types: {', '.join(source_info['event_types'])}")
            print(f"     Reliability: {source_info['reliability_score']}/10")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sources.json: {e}")
        return False

def show_source_management_plan():
    """Show the plan for managing sources"""
    print("🎯 Source Management Plan")
    print("=" * 60)
    
    print("📋 What we need to track:")
    print("  ✅ Source name and handle")
    print("  ✅ Source type (instagram, website, eventbrite, etc.)")
    print("  ✅ URL and description")
    print("  ✅ City coverage")
    print("  ✅ Event types this source posts")
    print("  ✅ Active/inactive status")
    print("  ✅ Last checked and last event found")
    print("  ✅ Reliability score and posting frequency")
    print("  ✅ Notes and scraping patterns")
    
    print("\n🏗️ Implementation steps:")
    print("  1. Add Source model to app.py")
    print("  2. Create sources table in database")
    print("  3. Create sources.json for JSON sync")
    print("  4. Add source management endpoints")
    print("  5. Create source scraping/monitoring system")
    print("  6. Integrate with event creation")
    
    print("\n📱 Source types to support:")
    print("  • Instagram accounts (@handle)")
    print("  • Websites (domain.com)")
    print("  • Eventbrite organizers")
    print("  • Facebook pages")
    print("  • Meetup groups")
    print("  • University event calendars")
    print("  • Museum/venue websites")
    
    print("\n🔄 JSON synchronization:")
    print("  • sources.json (like venues.json and cities.json)")
    print("  • Auto-update when sources are added/modified")
    print("  • Backup system for sources.json")
    print("  • Import/export functionality")

if __name__ == "__main__":
    print("🎯 Event Source Management")
    print("=" * 60)
    
    print("Choose an option:")
    print("1. Show source management plan")
    print("2. Create sources.json with sample data")
    print("3. Create sources table (requires Source model in app.py)")
    print("4. Add sample sources (requires Source model in app.py)")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        show_source_management_plan()
    elif choice == "2":
        success = create_sources_json()
    elif choice == "3":
        success = create_sources_table()
    elif choice == "4":
        success = add_sample_sources()
    else:
        print("Invalid choice")
        success = False
    
    if choice != "1" and not success:
        sys.exit(1)
