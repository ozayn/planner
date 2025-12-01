#!/usr/bin/env python3
"""
Diagnose database errors when adding events
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event
from sqlalchemy import inspect

def diagnose_database():
    """Check database schema and constraints"""
    with app.app_context():
        print("=" * 80)
        print("Database Schema Diagnosis")
        print("=" * 80)
        
        # Check if events table exists
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'events' not in tables:
            print("❌ ERROR: 'events' table does not exist!")
            return
        
        print("✅ 'events' table exists")
        
        # Get columns
        columns = inspector.get_columns('events')
        print(f"\n📋 Table has {len(columns)} columns:")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col['default'] is not None else ""
            print(f"   - {col['name']}: {col['type']} {nullable}{default}")
        
        # Check for required columns
        required_columns = ['id', 'title', 'start_date', 'city_id']
        missing_columns = []
        column_names = [col['name'] for col in columns]
        
        for req_col in required_columns:
            if req_col not in column_names:
                missing_columns.append(req_col)
        
        if missing_columns:
            print(f"\n❌ Missing required columns: {missing_columns}")
        else:
            print(f"\n✅ All required columns present")
        
        # Check for optional columns
        optional_columns = ['is_online', 'is_registration_required', 'registration_opens_date', 
                          'registration_opens_time', 'registration_url', 'registration_info']
        print(f"\n📋 Optional columns status:")
        for opt_col in optional_columns:
            if opt_col in column_names:
                print(f"   ✅ {opt_col} exists")
            else:
                print(f"   ⚠️  {opt_col} missing (may need migration)")
        
        # Check foreign key constraints
        print(f"\n🔗 Foreign key constraints:")
        try:
            fks = inspector.get_foreign_keys('events')
            if fks:
                for fk in fks:
                    print(f"   - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            else:
                print("   (No foreign key constraints found)")
        except Exception as e:
            print(f"   ⚠️  Could not check foreign keys: {e}")
        
        # Try to create a test event to see what error we get
        print(f"\n🧪 Testing event creation...")
        try:
            from datetime import date
            test_event = Event(
                title="TEST EVENT - DELETE ME",
                start_date=date.today(),
                city_id=1,
                is_selected=False
            )
            db.session.add(test_event)
            db.session.commit()
            print("   ✅ Test event created successfully")
            
            # Delete the test event
            db.session.delete(test_event)
            db.session.commit()
            print("   ✅ Test event deleted")
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Error creating test event: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    diagnose_database()


