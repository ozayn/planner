#!/usr/bin/env python3
"""
Run all database migrations and then test adding an event
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def run_migrations():
    """Run all database migrations"""
    print("=" * 80)
    print("Running Database Migrations")
    print("=" * 80)
    
    # Import migration functions
    from scripts.add_is_online_column import add_is_online_column
    from scripts.add_registration_fields import add_registration_fields
    
    success = True
    
    print("\n1. Adding is_online column...")
    if not add_is_online_column():
        success = False
    
    print("\n2. Adding registration fields...")
    if not add_registration_fields():
        success = False
    
    return success

def test_add_event():
    """Test adding a simple event"""
    print("\n" + "=" * 80)
    print("Testing Event Creation")
    print("=" * 80)
    
    from app import app, db, Event, Venue, City
    from datetime import date
    
    with app.app_context():
        # Find Washington, DC
        city = City.query.filter(
            db.func.lower(City.name).like('%washington%')
        ).first()
        
        if not city:
            print("❌ Washington, DC not found")
            return False
        
        print(f"✅ Found city: {city.name} (ID: {city.id})")
        
        # Find National Gallery of Art
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like('%national gallery%')
        ).first()
        
        if not venue:
            print("❌ National Gallery of Art not found")
            return False
        
        print(f"✅ Found venue: {venue.name} (ID: {venue.id})")
        
        # Try to create a minimal event
        print("\n🧪 Creating minimal test event...")
        try:
            event = Event(
                title="TEST EVENT - DELETE ME",
                start_date=date(2026, 1, 24),
                end_date=date(2026, 1, 24),
                city_id=city.id,
                venue_id=venue.id,
                event_type='talk',
                is_selected=False,
                source='website'
            )
            
            print("   Event object created, adding to session...")
            db.session.add(event)
            
            print("   Committing to database...")
            db.session.commit()
            
            print(f"   ✅ Success! Event ID: {event.id}")
            
            # Delete it
            print("   Cleaning up...")
            db.session.delete(event)
            db.session.commit()
            print("   ✅ Test event deleted")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: {type(e).__name__}: {e}")
            print("\n" + "=" * 80)
            print("Full Traceback:")
            print("=" * 80)
            import traceback
            traceback.print_exc()
            
            # Try to get more details
            if hasattr(e, 'orig'):
                print(f"\nOriginal error: {e.orig}")
            if hasattr(e, 'statement'):
                print(f"\nSQL Statement: {e.statement}")
            if hasattr(e, 'params'):
                print(f"\nParameters: {e.params}")
            
            return False

if __name__ == '__main__':
    try:
        # Run migrations
        migrations_ok = run_migrations()
        
        if not migrations_ok:
            print("\n⚠️  Some migrations failed, but continuing with test...")
        
        # Test adding event
        test_ok = test_add_event()
        
        if test_ok:
            print("\n" + "=" * 80)
            print("✅ SUCCESS: Migrations and event creation test passed!")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n" + "=" * 80)
            print("❌ FAILED: Event creation test failed")
            print("=" * 80)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


