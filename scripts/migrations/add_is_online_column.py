#!/usr/bin/env python3
"""
Database migration: Add is_online column to events table
"""
import os
import sys
import sqlite3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db

def add_is_online_column():
    """Add is_online column to events table if it doesn't exist"""
    with app.app_context():
        try:
            # Check if column already exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('events')]
            
            if 'is_online' in columns:
                print("✅ Column 'is_online' already exists in events table")
                return True
            
            # Add the column (SQLite compatible)
            print("🔧 Adding 'is_online' column to events table...")
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE events ADD COLUMN is_online BOOLEAN DEFAULT 0"))
                conn.commit()
            
            print("✅ Successfully added 'is_online' column to events table")
            return True
            
        except Exception as e:
            print(f"❌ Error adding column: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_is_online_column()
    sys.exit(0 if success else 1)

