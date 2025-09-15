#!/usr/bin/env python3
"""
CREATE FRESH DATABASE
Creates a fresh database with the unified events schema
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from app import app, db

def create_fresh_database():
    """Create a fresh database with unified events schema"""
    print("🗄️  Creating fresh database with unified events schema...")
    
    # Remove any existing database files
    db_files = [
        'events.db',
        'instance/events.db',
        'backups/events.db',
        'backups/events_20250909_134510.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"   🗑️  Removed {db_file}")
    
    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)
    
    # Set the database path explicitly to match app.py
    # Use project directory instead of system directory
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance', 'events.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
    # Create fresh database
    with app.app_context():
        db.create_all()
        print("✅ Fresh database created with unified events schema")
        
        # Verify the schema
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 Tables created: {tables}")
        
        # Check events table structure
        if 'events' in tables:
            columns = inspector.get_columns('events')
            print(f"📋 Events table has {len(columns)} columns:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        
        # Verify no separate event tables exist
        separate_tables = ['tours', 'exhibitions', 'festivals', 'photowalks']
        found_separate = [table for table in separate_tables if table in tables]
        
        if found_separate:
            print(f"❌ ERROR: Found separate event tables: {found_separate}")
            return False
        else:
            print("✅ Confirmed: No separate event tables exist")
            print("✅ Unified events architecture is clean!")
            return True

def main():
    """Main function"""
    print("🆕 FRESH DATABASE CREATION")
    print("=" * 40)
    
    success = create_fresh_database()
    
    if success:
        print("\n🎉 FRESH DATABASE CREATED SUCCESSFULLY!")
        print("The database now uses the unified events architecture.")
        print("No separate event tables exist.")
    else:
        print("\n🚨 DATABASE CREATION FAILED!")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
