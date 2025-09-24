#!/usr/bin/env python3
"""
Get Database Schema
Reads the actual schema from the local database to understand the correct structure
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Venue, City, Source, Event
from sqlalchemy import inspect

def get_venue_schema():
    """Get the actual Venue table schema from the database"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = inspector.get_columns('venues')
        
        print("🏛️ Venue Table Schema:")
        print("=" * 50)
        for column in columns:
            print(f"  {column['name']}: {column['type']} {'(nullable)' if column['nullable'] else '(not null)'}")
        print("=" * 50)
        
        return columns

def get_city_schema():
    """Get the actual City table schema from the database"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = inspector.get_columns('cities')
        
        print("🏙️ City Table Schema:")
        print("=" * 50)
        for column in columns:
            print(f"  {column['name']}: {column['type']} {'(nullable)' if column['nullable'] else '(not null)'}")
        print("=" * 50)
        
        return columns

def get_source_schema():
    """Get the actual Source table schema from the database"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = inspector.get_columns('sources')
        
        print("📱 Source Table Schema:")
        print("=" * 50)
        for column in columns:
            print(f"  {column['name']}: {column['type']} {'(nullable)' if column['nullable'] else '(not null)'}")
        print("=" * 50)
        
        return columns

def get_event_schema():
    """Get the actual Event table schema from the database"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = inspector.get_columns('events')
        
        print("📅 Event Table Schema:")
        print("=" * 50)
        for column in columns:
            print(f"  {column['name']}: {column['type']} {'(nullable)' if column['nullable'] else '(not null)'}")
        print("=" * 50)
        
        return columns

def main():
    """Main function to get all schemas"""
    print("🔍 DATABASE SCHEMA ANALYSIS")
    print("=" * 60)
    
    try:
        venue_columns = get_venue_schema()
        city_columns = get_city_schema()
        source_columns = get_source_schema()
        event_columns = get_event_schema()
        
        print("\n📊 Summary:")
        print(f"  Venue columns: {len(venue_columns)}")
        print(f"  City columns: {len(city_columns)}")
        print(f"  Source columns: {len(source_columns)}")
        print(f"  Event columns: {len(event_columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting schema: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
