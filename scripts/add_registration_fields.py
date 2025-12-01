#!/usr/bin/env python3
"""
Database migration: Add registration fields to events table
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db

def add_registration_fields():
    """Add registration fields to events table if they don't exist"""
    with app.app_context():
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('events')]
            
            fields_to_add = [
                ('is_registration_required', 'BOOLEAN DEFAULT 0'),
                ('registration_opens_date', 'DATE'),
                ('registration_opens_time', 'TIME'),
                ('registration_url', 'VARCHAR(1000)'),
                ('registration_info', 'TEXT'),
            ]
            
            added_count = 0
            for field_name, field_type in fields_to_add:
                if field_name not in columns:
                    print(f"🔧 Adding '{field_name}' column to events table...")
                    with db.engine.connect() as conn:
                        conn.execute(db.text(f"ALTER TABLE events ADD COLUMN {field_name} {field_type}"))
                        conn.commit()
                    print(f"✅ Successfully added '{field_name}' column")
                    added_count += 1
                else:
                    print(f"✅ Column '{field_name}' already exists")
            
            if added_count == 0:
                print("✅ All registration fields already exist in events table")
            else:
                print(f"✅ Added {added_count} registration field(s) to events table")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding registration fields: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_registration_fields()
    sys.exit(0 if success else 1)


