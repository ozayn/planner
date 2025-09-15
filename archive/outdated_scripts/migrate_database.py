#!/usr/bin/env python3
"""
Database Migration Script
Updates existing database to include all new features:
- Timestamp columns (created_at, updated_at)
- New venue fields (social media, contact info, etc.)
- Proper indexes for performance
"""

import os
import sqlite3
from datetime import datetime

def migrate_database():
    """Migrate existing database to new schema"""
    
    # Database path
    db_path = os.path.expanduser('~/.local/share/planner/events.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("   Use create_database_schema.py for fresh installation")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting database migration...")
        
        # Get current timestamp
        current_time = datetime.utcnow().isoformat()
        
        # Tables to migrate
        tables = {
            'cities': ['created_at', 'updated_at'],
            'venues': ['created_at', 'updated_at', 'facebook_url', 'twitter_url', 'youtube_url', 'tiktok_url', 'opening_hours', 'holiday_hours', 'phone_number', 'email', 'tour_info', 'admission_fee'],
            'events': ['created_at', 'updated_at'],
            'tours': ['created_at', 'updated_at'],
            'exhibitions': ['created_at', 'updated_at'],
            'festivals': ['created_at', 'updated_at'],
            'photowalks': ['created_at', 'updated_at']
        }
        
        for table, columns in tables.items():
            print(f"\n🔍 Migrating table: {table}")
            
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                print(f"   ⚠️ Table {table} does not exist, skipping")
                continue
            
            # Get current columns
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns
            for column in columns:
                if column not in existing_columns:
                    try:
                        if column in ['created_at', 'updated_at']:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} DATETIME DEFAULT '{current_time}'")
                        elif column in ['facebook_url', 'twitter_url', 'youtube_url', 'tiktok_url']:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(200)")
                        elif column in ['opening_hours', 'holiday_hours', 'tour_info', 'admission_fee']:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
                        elif column in ['phone_number']:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(50)")
                        elif column in ['email']:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(100)")
                        
                        print(f"   ✅ Added column {column} to {table}")
                    except sqlite3.Error as e:
                        print(f"   ❌ Error adding {column} to {table}: {e}")
                else:
                    print(f"   ℹ️ Column {column} already exists in {table}")
        
        # Create indexes for better performance
        print("\n📊 Creating performance indexes...")
        
        indexes = [
            ('idx_cities_name_country', 'cities', 'name, country'),
            ('idx_venues_city_id', 'venues', 'city_id'),
            ('idx_venues_name', 'venues', 'name'),
            ('idx_events_start_date', 'events', 'start_date'),
            ('idx_events_event_type', 'events', 'event_type'),
            ('idx_tours_venue_id', 'tours', 'venue_id'),
            ('idx_exhibitions_venue_id', 'exhibitions', 'venue_id'),
            ('idx_festivals_city_id', 'festivals', 'city_id'),
            ('idx_photowalks_city_id', 'photowalks', 'city_id')
        ]
        
        for index_name, table, columns in indexes:
            try:
                # Check if index already exists
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
                if not cursor.fetchone():
                    cursor.execute(f'CREATE INDEX {index_name} ON {table} ({columns})')
                    print(f"   ✅ Created index {index_name}")
                else:
                    print(f"   ℹ️ Index {index_name} already exists")
            except sqlite3.Error as e:
                print(f"   ❌ Error creating index {index_name}: {e}")
        
        # Update existing records with proper timestamps
        print("\n🕒 Updating existing records with timestamps...")
        
        for table in tables.keys():
            try:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    # Update records that have NULL timestamps
                    cursor.execute(f"UPDATE {table} SET created_at = '{current_time}' WHERE created_at IS NULL")
                    cursor.execute(f"UPDATE {table} SET updated_at = '{current_time}' WHERE updated_at IS NULL")
                    
                    # Get count of updated records
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   ✅ Updated {count} records in {table}")
            except sqlite3.Error as e:
                print(f"   ❌ Error updating {table}: {e}")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Database migration completed successfully!")
        
        # Verify the migration
        print("\n🔍 Verifying migration results:")
        for table in tables.keys():
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"\n{table} table ({len(columns)} columns):")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def backup_database():
    """Create a backup of the database before migration"""
    
    db_path = os.path.expanduser('~/.local/share/planner/events.db')
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return None

if __name__ == '__main__':
    print("🔄 Database Migration Script")
    print("This will update your existing database with new features:")
    print("- Timestamp columns (created_at, updated_at)")
    print("- New venue fields (social media, contact info)")
    print("- Performance indexes")
    print("- NLP-powered text normalization")
    
    # Create backup
    backup_path = backup_database()
    if not backup_path:
        print("❌ Cannot proceed without backup. Exiting.")
        exit(1)
    
    # Ask user if they want to proceed
    response = input(f"\nBackup created at: {backup_path}\nProceed with migration? (y/N): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled.")
        exit(1)
    
    success = migrate_database()
    if success:
        print("\n🎉 Migration completed successfully!")
        print("\n📋 What's new:")
        print("✅ All tables now have created_at and updated_at timestamps")
        print("✅ Venues have new social media and contact fields")
        print("✅ Performance indexes added for faster queries")
        print("✅ Ready for NLP-powered text normalization")
        print("\n🚀 You can now:")
        print("1. Use the NLP utilities for smart text normalization")
        print("2. Track when records were created and last updated")
        print("3. Add social media links and contact info to venues")
        print("4. Enjoy faster database queries")
    else:
        print("💥 Migration failed!")
        print(f"Your original database is safe at: {backup_path}")

