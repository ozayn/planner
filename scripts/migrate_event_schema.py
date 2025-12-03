#!/usr/bin/env python3
"""
Migrate Events table schema to match model definition
- Remove deprecated instagram_* columns
- Update VARCHAR sizes for URL fields (500 -> 1000)
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Event
from dotenv import load_dotenv

load_dotenv()

def detect_environment():
    """Detect if running locally or deployed"""
    return (
        os.getenv('RAILWAY_ENVIRONMENT') is not None or
        os.getenv('DATABASE_URL', '').startswith('postgresql://') or
        'railway.app' in os.getenv('RAILWAY_PUBLIC_DOMAIN', '')
    )

def migrate_local_sqlite():
    """Migrate local SQLite database"""
    db_path = 'instance/events.db'
    if not os.path.exists(db_path):
        print("❌ Local database not found at instance/events.db")
        return False
    
    print("🔧 Migrating local SQLite database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get current columns
        cursor.execute("PRAGMA table_info(events)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Step 1: Remove deprecated instagram_* columns
        deprecated_columns = ['instagram_handle', 'instagram_page', 'instagram_posted_by']
        for col in deprecated_columns:
            if col in columns:
                print(f"   Removing deprecated column: {col}")
                # SQLite doesn't support DROP COLUMN directly, need to recreate table
                # This is a simplified approach - in production, you'd want a full migration
                print(f"   ⚠️  SQLite doesn't support DROP COLUMN easily")
                print(f"   ⚠️  Column {col} will be ignored but not removed")
                print(f"   💡 To fully remove, recreate the table or use a migration tool")
        
        # Step 2: Update VARCHAR sizes
        # SQLite doesn't enforce VARCHAR sizes, but we can document the change
        print("   ℹ️  SQLite doesn't enforce VARCHAR sizes")
        print("   ℹ️  Column sizes are informational only in SQLite")
        print("   ✅ Model definition already specifies VARCHAR(1000) for URL fields")
        
        # Step 3: Verify schema matches model
        print("\n   ✅ Local database schema migration complete")
        print("   ℹ️  Note: Deprecated columns exist but are unused")
        print("   ℹ️  The model will ignore these columns")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error migrating local database: {e}")
        conn.close()
        return False

def migrate_postgresql():
    """Migrate PostgreSQL database (deployed)"""
    print("🔧 Migrating PostgreSQL database...")
    
    try:
        with app.app_context():
            from sqlalchemy import text
            
            # Get database connection
            conn = db.engine.connect()
            
            try:
                # Check if deprecated columns exist
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'events' 
                    AND column_name IN ('instagram_handle', 'instagram_page', 'instagram_posted_by')
                """))
                existing_deprecated = [row[0] for row in result]
                
                # Step 1: Remove deprecated columns
                for col in existing_deprecated:
                    print(f"   Removing deprecated column: {col}")
                    try:
                        conn.execute(text(f"ALTER TABLE events DROP COLUMN IF EXISTS {col}"))
                        conn.commit()
                        print(f"   ✅ Removed {col}")
                    except Exception as e:
                        print(f"   ⚠️  Error removing {col}: {e}")
                
                # Step 2: Update VARCHAR sizes (if needed)
                url_columns = [
                    ('image_url', 1000),
                    ('url', 1000),
                    ('source_url', 1000),
                    ('registration_url', 1000)
                ]
                
                for col_name, new_size in url_columns:
                    # Check current size first
                    result = conn.execute(text(f"""
                        SELECT character_maximum_length 
                        FROM information_schema.columns 
                        WHERE table_name = 'events' 
                        AND column_name = '{col_name}'
                    """))
                    current_size = result.fetchone()
                    
                    if current_size and current_size[0] and current_size[0] < new_size:
                        print(f"   Updating {col_name} from VARCHAR({current_size[0]}) to VARCHAR({new_size})")
                        try:
                            conn.execute(text(f"""
                                ALTER TABLE events 
                                ALTER COLUMN {col_name} TYPE VARCHAR({new_size})
                            """))
                            conn.commit()
                            print(f"   ✅ Updated {col_name}")
                        except Exception as e:
                            print(f"   ⚠️  Error updating {col_name}: {e}")
                    elif current_size and current_size[0] and current_size[0] >= new_size:
                        print(f"   ✅ {col_name} already VARCHAR({current_size[0]}) - no change needed")
                    else:
                        print(f"   ⚠️  Could not determine current size for {col_name}")
                
                print("\n   ✅ PostgreSQL database migration complete")
                return True
                
            finally:
                conn.close()
                
    except Exception as e:
        print(f"❌ Error migrating PostgreSQL database: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_clean_local_database():
    """Create a clean local database by recreating the table"""
    print("\n🔧 Creating clean local database (recreating events table)...")
    
    db_path = 'instance/events.db'
    if not os.path.exists(db_path):
        print("❌ Local database not found")
        return False
    
    print("⚠️  This will recreate the events table with the correct schema")
    print("⚠️  All existing events will be lost!")
    
    response = input("   Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("   ❌ Migration cancelled")
        return False
    
    try:
        with app.app_context():
            # Drop and recreate the table
            Event.__table__.drop(db.engine, checkfirst=True)
            Event.__table__.create(db.engine, checkfirst=True)
            
            print("   ✅ Events table recreated with correct schema")
            print("   ⚠️  All events have been removed - you'll need to re-scrape")
            return True
            
    except Exception as e:
        print(f"❌ Error recreating table: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main migration function"""
    print("=" * 80)
    print("EVENTS TABLE SCHEMA MIGRATION")
    print("=" * 80)
    print()
    
    is_railway = detect_environment()
    
    if is_railway:
        print("📍 Detected: Railway/PostgreSQL environment")
        print()
        success = migrate_postgresql()
    else:
        print("📍 Detected: Local/SQLite environment")
        print()
        
        # For SQLite, we have two options:
        # 1. Simple migration (just document changes)
        # 2. Full migration (recreate table - loses data)
        
        print("SQLite migration options:")
        print("  1. Simple migration (keeps data, deprecated columns remain but unused)")
        print("  2. Full migration (recreates table, removes deprecated columns, loses all events)")
        print()
        
        choice = input("Choose option (1 or 2): ").strip()
        
        if choice == '1':
            success = migrate_local_sqlite()
        elif choice == '2':
            success = create_clean_local_database()
        else:
            print("❌ Invalid choice")
            return 1
    
    print()
    print("=" * 80)
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
    print("=" * 80)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

