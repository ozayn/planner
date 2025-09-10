#!/usr/bin/env python3
"""
Migrate database to add new venue fields
"""

import os
import sys
import sqlite3

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

def migrate_venue_fields():
    """Add new fields to venues table"""
    
    with app.app_context():
        # Get the database path
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        
        print(f"Database path: {db_path}")
        
        if not os.path.exists(db_path):
            print("Database doesn't exist, creating tables...")
            db.create_all()
            return
        
        # Connect to SQLite database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if new columns exist
        cursor.execute("PRAGMA table_info(venues)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_fields = [
            ('facebook_url', 'TEXT'),
            ('twitter_url', 'TEXT'),
            ('youtube_url', 'TEXT'),
            ('tiktok_url', 'TEXT'),
            ('opening_hours', 'TEXT'),
            ('holiday_hours', 'TEXT'),
            ('phone_number', 'VARCHAR(50)'),
            ('email', 'VARCHAR(200)')
        ]
        
        for field_name, field_type in new_fields:
            if field_name not in columns:
                print(f"Adding column: {field_name}")
                cursor.execute(f"ALTER TABLE venues ADD COLUMN {field_name} {field_type}")
            else:
                print(f"Column {field_name} already exists")
        
        conn.commit()
        conn.close()
        print("✅ Migration completed successfully!")

if __name__ == '__main__':
    migrate_venue_fields()
