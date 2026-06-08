#!/usr/bin/env python3
"""
Simple test to add an event and see the full error
"""
import os
import sys
from datetime import date, time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

def test_add_event():
    """Try to add a simple test event"""
    with app.app_context():
        print("=" * 80)
        print("Testing Event Creation")
        print("=" * 80)
        
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
        success = test_add_event()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


