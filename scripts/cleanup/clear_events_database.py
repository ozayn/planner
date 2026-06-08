#!/usr/bin/env python3
"""
Clear all events from the database
WARNING: This will delete ALL events!
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def clear_events():
    """Clear all events from the database"""
    with app.app_context():
        # Count events first
        total_events = Event.query.count()
        print(f"📊 Found {total_events} events in database")
        
        if total_events == 0:
            print("✅ Database is already empty")
            return True
        
        # Confirm deletion (allow command line argument to skip confirmation)
        if len(sys.argv) > 1 and sys.argv[1] == '--yes':
            confirmation = 'DELETE ALL EVENTS'
            print(f"\n⚠️  WARNING: Deleting ALL {total_events} events (--yes flag provided)")
        else:
            print(f"\n⚠️  WARNING: This will delete ALL {total_events} events!")
            print("   Type 'DELETE ALL EVENTS' to confirm (or run with --yes flag):")
            confirmation = input().strip()
        
        if confirmation != 'DELETE ALL EVENTS':
            print("❌ Deletion cancelled")
            return False
        
        try:
            # Delete all events
            deleted_count = Event.query.delete()
            db.session.commit()
            
            print(f"\n✅ Successfully deleted {deleted_count} events")
            
            # Verify
            remaining = Event.query.count()
            if remaining == 0:
                print("✅ Verified: Database is now empty")
            else:
                print(f"⚠️  Warning: {remaining} events still remain")
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting events: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        success = clear_events()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

