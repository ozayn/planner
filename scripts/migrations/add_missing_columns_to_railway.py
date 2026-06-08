#!/usr/bin/env python3
"""
Add missing columns to Railway PostgreSQL database.
This script adds the new generic social media fields and location fields to the events table.
"""

import os
import sys
from dotenv import load_dotenv

def add_missing_columns():
    """Add the missing columns to Railway PostgreSQL database."""
    
    # Load environment variables
    load_dotenv()
    
    # Get Railway database URL from environment
    railway_db_url = os.getenv('DATABASE_URL')
    if not railway_db_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("💡 Make sure you're running this with Railway environment variables")
        return False
    
    print(f"🔗 Connecting to Railway database...")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to Railway PostgreSQL
        conn = psycopg2.connect(railway_db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected to Railway database")
        
        # Check current schema
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'events' 
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("\n📊 Current Railway Events table schema:")
        existing_columns = [col[0] for col in columns]
        for col_name, col_type in columns:
            print(f"  {col_name} ({col_type})")
        
        # Define the new columns we need to add
        new_columns = [
            ('social_media_platform', 'VARCHAR(50)'),
            ('social_media_handle', 'VARCHAR(100)'),
            ('social_media_page_name', 'VARCHAR(100)'),
            ('social_media_posted_by', 'VARCHAR(100)'),
            ('social_media_url', 'VARCHAR(500)'),
            ('start_location', 'VARCHAR(200)'),
            ('end_location', 'VARCHAR(200)')
        ]
        
        # Add missing columns
        added_columns = []
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE events ADD COLUMN {column_name} {column_type}")
                    added_columns.append(column_name)
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"❌ Failed to add column {column_name}: {e}")
            else:
                print(f"⏭️  Column {column_name} already exists")
        
        if added_columns:
            print(f"\n🎉 Successfully added {len(added_columns)} new columns to Railway database:")
            for col in added_columns:
                print(f"  - {col}")
        else:
            print("\n✅ All new columns already exist in Railway database")
        
        # Verify the final schema
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'events' 
            ORDER BY ordinal_position
        """)
        final_columns = cursor.fetchall()
        
        print(f"\n📊 Final Railway Events table schema ({len(final_columns)} columns):")
        for col_name, col_type in final_columns:
            print(f"  {col_name} ({col_type})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Adding missing columns to Railway PostgreSQL database...")
    success = add_missing_columns()
    if success:
        print("\n✅ Schema update completed successfully!")
        print("🔄 Railway app should now work with the new schema")
    else:
        print("\n❌ Schema update failed!")
        sys.exit(1)
