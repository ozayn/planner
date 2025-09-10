#!/usr/bin/env python3
"""
Database Migration Script
Adds additional_info field to venues table
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db

def add_additional_info_field():
    """Add additional_info field to venues table"""
    
    print("🔄 Adding additional_info field to venues table...")
    
    try:
        with app.app_context():
            # Check if the field already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('venues')]
            
            if 'additional_info' in columns:
                print("✅ additional_info field already exists")
                return True
            
            # Add the new column
            db.session.execute(db.text('ALTER TABLE venues ADD COLUMN additional_info TEXT'))
            db.session.commit()
            print("✅ Successfully added additional_info field to venues table")
            
            return True
            
    except Exception as e:
        print(f"❌ Error adding additional_info field: {e}")
        return False

if __name__ == "__main__":
    success = add_additional_info_field()
    if not success:
        sys.exit(1)
    print("🎉 Migration complete!")
