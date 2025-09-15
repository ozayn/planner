#!/usr/bin/env python3
"""
Add missing timestamp columns to existing database tables
This script adds created_at and updated_at columns to all tables that don't have them
"""

import os
import sqlite3
from datetime import datetime

def add_timestamp_columns():
    """Add created_at and updated_at columns to all tables"""
    
    # Database path
    db_path = os.path.expanduser('~/.local/share/planner/events.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current timestamp
        current_time = datetime.utcnow().isoformat()
        
        # Tables to update
        tables = [
            'cities',
            'venues', 
            'events',
            'tours',
            'exhibitions',
            'festivals',
            'photowalks'
        ]
        
        for table in tables:
            print(f"🔍 Checking table: {table}")
            
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                print(f"   ⚠️ Table {table} does not exist, skipping")
                continue
            
            # Get current columns
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add created_at if missing
            if 'created_at' not in columns:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN created_at DATETIME DEFAULT '{current_time}'")
                    print(f"   ✅ Added created_at column to {table}")
                except sqlite3.Error as e:
                    print(f"   ❌ Error adding created_at to {table}: {e}")
            else:
                print(f"   ℹ️ created_at column already exists in {table}")
            
            # Add updated_at if missing
            if 'updated_at' not in columns:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN updated_at DATETIME DEFAULT '{current_time}'")
                    print(f"   ✅ Added updated_at column to {table}")
                except sqlite3.Error as e:
                    print(f"   ❌ Error adding updated_at to {table}: {e}")
            else:
                print(f"   ℹ️ updated_at column already exists in {table}")
        
        # Commit changes
        conn.commit()
        print("✅ All timestamp columns added successfully!")
        
        # Verify the changes
        print("\n🔍 Verifying table structures:")
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"\n{table} columns:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    print("🕒 Adding timestamp columns to database...")
    success = add_timestamp_columns()
    if success:
        print("🎉 Database update completed successfully!")
    else:
        print("💥 Database update failed!")

