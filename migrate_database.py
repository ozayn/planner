#!/usr/bin/env python3
"""
Database migration script to add missing columns to Railway PostgreSQL.
This ensures the deployed schema matches the local schema.
"""

import os
import sys

def migrate_database():
    """Add missing columns to match local schema."""
    
    # Get database URL from environment (Railway provides this)
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found")
        return False
    
    print("🔗 Connecting to database...")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Check existing columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'events'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Found {len(existing_columns)} existing columns")
        
        # Define missing columns (based on local schema)
        missing_columns = [
            ('social_media_platform', 'VARCHAR(50)'),
            ('social_media_handle', 'VARCHAR(100)'),
            ('social_media_page_name', 'VARCHAR(100)'),
            ('social_media_posted_by', 'VARCHAR(100)'),
            ('social_media_url', 'VARCHAR(500)'),
            ('start_location', 'VARCHAR(200)'),
            ('end_location', 'VARCHAR(200)')
        ]
        
        # Add missing columns
        added_count = 0
        for column_name, column_type in missing_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE events ADD COLUMN {column_name} {column_type}")
                    print(f"✅ Added: {column_name}")
                    added_count += 1
                except Exception as e:
                    print(f"❌ Failed to add {column_name}: {e}")
            else:
                print(f"⏭️  Already exists: {column_name}")
        
        print(f"\n🎉 Migration complete! Added {added_count} new columns")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Running database migration...")
    success = migrate_database()
    if success:
        print("✅ Schema now matches local database!")
    else:
        print("❌ Migration failed!")
        sys.exit(1)
