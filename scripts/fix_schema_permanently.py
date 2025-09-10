#!/usr/bin/env python3
"""
PERMANENT SCHEMA FIX
This script ensures the database schema matches our code expectations
"""

import os
import sys
import sqlite3
from pathlib import Path

def get_db_path():
    """Get the database path"""
    return os.path.expanduser('~/.local/share/planner/events.db')

def fix_database_schema():
    """Fix the database schema to match our code expectations"""
    print("🔧 Fixing database schema...")
    
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print("❌ Database doesn't exist")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if venues table has all required columns
        cursor.execute("PRAGMA table_info(venues)")
        venue_columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Current venues table columns: {venue_columns}")
        
        # Add missing venue columns if they don't exist
        venue_required_columns = {
            'opening_hours': 'TEXT',
            'holiday_hours': 'TEXT', 
            'phone_number': 'VARCHAR(50)',
            'email': 'VARCHAR(200)',
            'tour_info': 'TEXT',
            'admission_fee': 'TEXT'
        }
        
        for column, column_type in venue_required_columns.items():
            if column not in venue_columns:
                print(f"➕ Adding {column} column to venues table")
                cursor.execute(f"ALTER TABLE venues ADD COLUMN {column} {column_type}")
        
        # Check if events table has all required columns
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Current events table columns: {columns}")
        
        # Add missing columns if they don't exist
        event_required_columns = {
            'city_id': 'INTEGER',
            'venue_id': 'INTEGER'
        }
        
        for column, column_type in event_required_columns.items():
            if column not in columns:
                print(f"➕ Adding {column} column to events table")
                cursor.execute(f"ALTER TABLE events ADD COLUMN {column} {column_type}")
        
        # Add foreign key constraints if they don't exist
        try:
            cursor.execute("ALTER TABLE events ADD CONSTRAINT fk_events_city FOREIGN KEY (city_id) REFERENCES cities(id)")
            print("➕ Added city foreign key constraint")
        except:
            print("⚠️  City foreign key constraint already exists or failed")
        
        try:
            cursor.execute("ALTER TABLE events ADD CONSTRAINT fk_events_venue FOREIGN KEY (venue_id) REFERENCES venues(id)")
            print("➕ Added venue foreign key constraint")
        except:
            print("⚠️  Venue foreign key constraint already exists or failed")
        
        conn.commit()
        print("✅ Database schema fixed")
        return True
        
    except Exception as e:
        print(f"❌ Schema fix failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_schema():
    """Verify the schema is correct"""
    print("🔍 Verifying schema...")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check events table structure
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = ['id', 'title', 'description', 'start_date', 'end_date', 'start_time', 'end_time', 'image_url', 'url', 'is_selected', 'created_at', 'event_type', 'city_id', 'venue_id']
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        else:
            print("✅ All required columns present")
            return True
            
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main function"""
    print("🛡️  PERMANENT SCHEMA FIX")
    print("=" * 40)
    
    if fix_database_schema():
        if verify_schema():
            print("\n🎉 SCHEMA PERMANENTLY FIXED!")
            print("No more database errors!")
            return True
    
    print("\n🚨 SCHEMA FIX FAILED!")
    return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
