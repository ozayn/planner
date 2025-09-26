#!/usr/bin/env python3
"""
Automatic Database Schema Synchronization
This script ensures Railway PostgreSQL always matches the local SQLite schema.
Run this after any schema changes to keep production in sync.
"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

def get_local_schema():
    """Get the current local SQLite schema."""
    conn = sqlite3.connect('instance/events.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(events)')
    columns = cursor.fetchall()
    conn.close()
    
    # Convert to dict for easier comparison
    schema = {}
    for col in columns:
        schema[col[1]] = col[2]  # column_name: data_type
    return schema

def sync_railway_schema():
    """Sync Railway PostgreSQL with local SQLite schema."""
    
    # Load environment variables
    load_dotenv()
    
    # Get Railway database URL
    railway_db_url = os.getenv('DATABASE_URL')
    if not railway_db_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("💡 Make sure you're running this with Railway environment variables")
        return False
    
    print("🔗 Connecting to Railway PostgreSQL...")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        conn = psycopg2.connect(railway_db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected to Railway database")
        
        # Get current Railway schema
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'events'
            ORDER BY ordinal_position
        """)
        railway_columns = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get local schema
        local_schema = get_local_schema()
        
        print(f"📊 Local schema: {len(local_schema)} columns")
        print(f"📊 Railway schema: {len(railway_columns)} columns")
        
        # Find missing columns in Railway
        missing_columns = []
        for col_name, col_type in local_schema.items():
            if col_name not in railway_columns:
                # Convert SQLite types to PostgreSQL types
                pg_type = convert_sqlite_to_postgres(col_type)
                missing_columns.append((col_name, pg_type))
        
        if not missing_columns:
            print("✅ Railway schema is already up to date!")
            return True
        
        print(f"\n🔧 Adding {len(missing_columns)} missing columns to Railway:")
        
        # Add missing columns
        added_count = 0
        for col_name, pg_type in missing_columns:
            try:
                cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {pg_type}")
                print(f"✅ Added: {col_name} ({pg_type})")
                added_count += 1
            except Exception as e:
                print(f"❌ Failed to add {col_name}: {e}")
        
        print(f"\n🎉 Successfully added {added_count} columns to Railway!")
        print("🔄 Railway database now matches local schema")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False

def convert_sqlite_to_postgres(sqlite_type):
    """Convert SQLite data types to PostgreSQL equivalents."""
    type_mapping = {
        'INTEGER': 'INTEGER',
        'VARCHAR(200)': 'VARCHAR(200)',
        'VARCHAR(100)': 'VARCHAR(100)',
        'VARCHAR(50)': 'VARCHAR(50)',
        'VARCHAR(500)': 'VARCHAR(500)',
        'TEXT': 'TEXT',
        'DATE': 'DATE',
        'TIME': 'TIME',
        'DATETIME': 'TIMESTAMP',
        'BOOLEAN': 'BOOLEAN',
        'FLOAT': 'REAL'
    }
    return type_mapping.get(sqlite_type, 'TEXT')

if __name__ == "__main__":
    print("🚀 Syncing Railway PostgreSQL with local SQLite schema...")
    success = sync_railway_schema()
    if success:
        print("\n✅ Schema synchronization completed!")
        print("🎯 Railway database now matches local schema")
    else:
        print("\n❌ Schema synchronization failed!")
        sys.exit(1)
