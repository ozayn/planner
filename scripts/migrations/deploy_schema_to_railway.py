#!/usr/bin/env python3
"""
Deploy schema changes to Railway PostgreSQL database.
This script adds the new generic social media fields and location fields to the events table.
"""

import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def deploy_schema_changes():
    """Deploy the new schema changes to Railway PostgreSQL."""
    
    # Load environment variables
    load_dotenv()
    
    # Get Railway database URL
    railway_db_url = os.getenv('DATABASE_URL')
    if not railway_db_url:
        print("❌ DATABASE_URL not found in environment variables")
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
        
        # Check if new columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'events' 
            AND column_name IN ('social_media_platform', 'social_media_handle', 'social_media_page_name', 'social_media_posted_by', 'social_media_url', 'start_location', 'end_location')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Existing new columns: {existing_columns}")
        
        # Add missing columns
        new_columns = [
            ('social_media_platform', 'VARCHAR(50)'),
            ('social_media_handle', 'VARCHAR(100)'),
            ('social_media_page_name', 'VARCHAR(100)'),
            ('social_media_posted_by', 'VARCHAR(100)'),
            ('social_media_url', 'VARCHAR(500)'),
            ('start_location', 'VARCHAR(200)'),
            ('end_location', 'VARCHAR(200)')
        ]
        
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
            print(f"🎉 Successfully added {len(added_columns)} new columns to Railway database")
        else:
            print("✅ All new columns already exist in Railway database")
        
        # Verify the schema
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'events' 
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("\n📊 Current Railway Events table schema:")
        for col_name, col_type in columns:
            print(f"  {col_name} ({col_type})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Error deploying schema: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Deploying schema changes to Railway PostgreSQL...")
    success = deploy_schema_changes()
    if success:
        print("✅ Schema deployment completed successfully!")
    else:
        print("❌ Schema deployment failed!")
        sys.exit(1)
