#!/usr/bin/env python3
"""
Add ticketing_url column to venues table
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db

def add_ticketing_url_column():
    """Add ticketing_url column to venues table if it doesn't exist"""
    
    print("🔄 Adding ticketing_url column to venues table...")
    
    try:
        with app.app_context():
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('venues')]
            
            if 'ticketing_url' in columns:
                print("✅ ticketing_url column already exists")
                return True
            
            # Add the new column
            db.session.execute(db.text('ALTER TABLE venues ADD COLUMN ticketing_url VARCHAR(200)'))
            db.session.commit()
            print("✅ Successfully added ticketing_url column to venues table")
            
            return True
            
    except Exception as e:
        print(f"❌ Error adding ticketing_url column: {e}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    success = add_ticketing_url_column()
    sys.exit(0 if success else 1)
