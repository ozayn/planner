#!/usr/bin/env python3
"""
Add new exhibition fields to local SQLite database
"""

import os
import sys
import sqlite3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db

def add_exhibition_fields():
    """Add new exhibition fields to events table"""
    db_path = os.path.join(project_root, 'instance', 'events.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    print(f"🔗 Connecting to database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(events)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    print(f"📋 Found {len(existing_columns)} existing columns")
    
    # New exhibition fields to add
    new_columns = [
        ('artists', 'TEXT'),
        ('exhibition_type', 'VARCHAR(100)'),
        ('collection_period', 'VARCHAR(200)'),
        ('number_of_artworks', 'INTEGER'),
        ('opening_reception_date', 'DATE'),
        ('opening_reception_time', 'TIME'),
        ('is_permanent', 'BOOLEAN DEFAULT 0'),
        ('related_exhibitions', 'TEXT')
    ]
    
    added_count = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")
                print(f"✅ Added column: {col_name}")
                added_count += 1
            except Exception as e:
                print(f"❌ Failed to add {col_name}: {e}")
        else:
            print(f"⏭️  Column already exists: {col_name}")
    
    conn.commit()
    conn.close()
    
    if added_count > 0:
        print(f"\n🎉 Successfully added {added_count} new columns!")
    else:
        print("\n✅ All columns already exist")
    
    return True

if __name__ == "__main__":
    with app.app_context():
        success = add_exhibition_fields()
        sys.exit(0 if success else 1)

