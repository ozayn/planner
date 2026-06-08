#!/usr/bin/env python3
"""
Add the Wassily Kandinsky Finding Awe event to the database
"""
import os
import sys
from datetime import datetime, date, time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City
from scripts.nga_finding_awe_scraper import scrape_individual_event
import cloudscraper

EVENT_URL = 'https://www.nga.gov/calendar/finding-awe/finding-awe-wassily-kandinskys-improvisation-31-sea-battle?evd=202602071915'
VENUE_NAME = "National Gallery of Art"
CITY_NAME = "Washington, DC"

def add_event():
    """Extract and add the event to the database"""
    with app.app_context():
        # Find the venue
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like(f'%{VENUE_NAME.lower()}%')
        ).first()
        
        if not venue:
            print(f"❌ Venue '{VENUE_NAME}' not found in database")
            return False
        
        print(f"✅ Found venue: {venue.name} (ID: {venue.id})")
        print(f"   Venue address: {venue.address or 'NO ADDRESS'}")
        if not venue.address:
            print(f"   ⚠️  WARNING: Venue has no address! Calendar export will use venue name instead.")
        
        # Find the city
        city = City.query.filter(
            db.func.lower(City.name).like(f'%{CITY_NAME.lower().split(",")[0]}%')
        ).first()
        
        if not city:
            print(f"❌ City '{CITY_NAME}' not found in database")
            return False
        
        print(f"🔍 Extracting event data from URL...")
        print(f"URL: {EVENT_URL}")
        
        # Create scraper session
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        
        # Extract event data
        event_data = scrape_individual_event(EVENT_URL, scraper)
        
        if not event_data:
            print("❌ Failed to extract event data")
            return False
        
        print(f"\n✅ Extracted event data:")
        print(f"   Title: {event_data.get('title')}")
        print(f"   Date: {event_data.get('start_date')}")
        start_time_str = event_data.get('start_time')
        end_time_str = event_data.get('end_time')
        print(f"   Time: {start_time_str} - {end_time_str}")
        if not start_time_str or not end_time_str:
            print(f"   ⚠️  WARNING: Times are missing!")
        print(f"   Location: {event_data.get('location')}")
        print(f"   Registration Required: {event_data.get('is_registration_required')}")
        print(f"   Registration URL: {event_data.get('registration_url')}")
        desc = event_data.get('description', '') or ''
        print(f"   Description length: {len(desc)} characters")
        
        # Parse date
        if not event_data.get('start_date'):
            print("❌ No start date found in extracted data")
            return False
        
        try:
            event_date = datetime.fromisoformat(event_data['start_date']).date()
        except (ValueError, TypeError) as e:
            print(f"❌ Error parsing date: {e}")
            return False
        
        # Check if event already exists - use filter() instead of filter_by() for more control
        try:
            existing = Event.query.filter(
                Event.url == EVENT_URL,
                Event.start_date == event_date,
                Event.city_id == city.id
            ).first()
        except Exception as query_error:
            # If query fails (e.g., missing columns), try simpler query
            print(f"   ⚠️  Query error (possibly missing columns): {query_error}")
            existing = Event.query.filter(
                Event.url == EVENT_URL,
                Event.start_date == event_date
            ).first()
        
        if existing:
            print(f"\n⚠️  Event already exists (ID: {existing.id})")
            print(f"   Title: {existing.title}")
            print(f"   Date: {existing.start_date}")
            
            # Update with new data
            print(f"\n🔄 Updating existing event with new data...")
            try:
                existing.title = event_data['title']
                existing.description = event_data.get('description')
                if event_data.get('start_time'):
                    try:
                        time_str = event_data['start_time']
                        if isinstance(time_str, str) and ':' in time_str:
                            time_parts = time_str.split(':')
                            if len(time_parts) >= 2:
                                hour = int(time_parts[0])
                                minute = int(time_parts[1])
                                second = int(time_parts[2]) if len(time_parts) > 2 else 0
                                existing.start_time = time(hour, minute, second)
                    except Exception as e:
                        print(f"   ⚠️  Could not update start_time: {e}")
                if event_data.get('end_time'):
                    try:
                        time_str = event_data['end_time']
                        if isinstance(time_str, str) and ':' in time_str:
                            time_parts = time_str.split(':')
                            if len(time_parts) >= 2:
                                hour = int(time_parts[0])
                                minute = int(time_parts[1])
                                second = int(time_parts[2]) if len(time_parts) > 2 else 0
                                existing.end_time = time(hour, minute, second)
                    except Exception as e:
                        print(f"   ⚠️  Could not update end_time: {e}")
                existing.start_location = event_data.get('location')
                if hasattr(existing, 'is_online'):
                    existing.is_online = event_data.get('is_online', False)
                if hasattr(existing, 'is_registration_required'):
                    existing.is_registration_required = event_data.get('is_registration_required', False)
                if hasattr(existing, 'registration_opens_date') and event_data.get('registration_opens_date'):
                    try:
                        existing.registration_opens_date = datetime.fromisoformat(event_data['registration_opens_date']).date()
                    except Exception as e:
                        print(f"   ⚠️  Could not update registration_opens_date: {e}")
                if hasattr(existing, 'registration_opens_time') and event_data.get('registration_opens_time'):
                    try:
                        time_str = event_data['registration_opens_time']
                        if isinstance(time_str, str) and ':' in time_str:
                            time_parts = time_str.split(':')
                            if len(time_parts) >= 2:
                                hour = int(time_parts[0])
                                minute = int(time_parts[1])
                                second = int(time_parts[2]) if len(time_parts) > 2 else 0
                                existing.registration_opens_time = time(hour, minute, second)
                    except Exception as e:
                        print(f"   ⚠️  Could not update registration_opens_time: {e}")
                if hasattr(existing, 'registration_url'):
                    existing.registration_url = event_data.get('registration_url')
                if hasattr(existing, 'registration_info'):
                    existing.registration_info = event_data.get('registration_info')
                existing.image_url = event_data.get('image_url')
                
                print(f"💾 Attempting to save updated event to database...")
                db.session.commit()
                
                # Verify it was saved
                updated_event = Event.query.get(existing.id)
                if updated_event:
                    print(f"\n✅ Event updated successfully!")
                    print(f"   ID: {updated_event.id}")
                    print(f"   Title: {updated_event.title}")
                    print(f"   Date: {updated_event.start_date}")
                    print(f"   Location: {updated_event.start_location}")
                    print(f"   Venue ID: {updated_event.venue_id}")
                    return True
                else:
                    print(f"\n⚠️  Warning: Event update committed but not found in database")
                    return False
            except Exception as update_error:
                db.session.rollback()
                print(f"\n❌ Database error updating event: {update_error}")
                print(f"   Error type: {type(update_error).__name__}")
                import traceback
                traceback.print_exc()
                return False
        
        # Parse times - handle both time.isoformat() strings (HH:MM:SS) and datetime strings
        start_time_obj = None
        end_time_obj = None
        print(f"\n🕐 Parsing times...")
        if event_data.get('start_time'):
            try:
                time_str = event_data['start_time']
                # Try time.fromisoformat() first (for "HH:MM:SS" format)
                if isinstance(time_str, str) and ':' in time_str:
                    time_parts = time_str.split(':')
                    if len(time_parts) >= 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        second = int(time_parts[2]) if len(time_parts) > 2 else 0
                        start_time_obj = time(hour, minute, second)
                        print(f"   ✅ Parsed start_time: {start_time_obj}")
                    else:
                        # Try datetime.fromisoformat() as fallback
                        start_time_obj = datetime.fromisoformat(time_str).time()
                        print(f"   ✅ Parsed start_time (datetime): {start_time_obj}")
                else:
                    start_time_obj = datetime.fromisoformat(time_str).time()
                    print(f"   ✅ Parsed start_time (datetime): {start_time_obj}")
            except (ValueError, TypeError, IndexError) as e:
                print(f"   ⚠️  Could not parse start_time '{event_data.get('start_time')}': {e}")
        else:
            print(f"   ⚠️  No start_time in event_data")
        
        if event_data.get('end_time'):
            try:
                time_str = event_data['end_time']
                # Try time.fromisoformat() first (for "HH:MM:SS" format)
                if isinstance(time_str, str) and ':' in time_str:
                    time_parts = time_str.split(':')
                    if len(time_parts) >= 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        second = int(time_parts[2]) if len(time_parts) > 2 else 0
                        end_time_obj = time(hour, minute, second)
                        print(f"   ✅ Parsed end_time: {end_time_obj}")
                    else:
                        # Try datetime.fromisoformat() as fallback
                        end_time_obj = datetime.fromisoformat(time_str).time()
                        print(f"   ✅ Parsed end_time (datetime): {end_time_obj}")
                else:
                    end_time_obj = datetime.fromisoformat(time_str).time()
                    print(f"   ✅ Parsed end_time (datetime): {end_time_obj}")
            except (ValueError, TypeError, IndexError) as e:
                print(f"   ⚠️  Could not parse end_time '{event_data.get('end_time')}': {e}")
        else:
            print(f"   ⚠️  No end_time in event_data")
        
        # Parse registration opens date/time
        registration_opens_date_obj = None
        registration_opens_time_obj = None
        if event_data.get('registration_opens_date'):
            try:
                registration_opens_date_obj = datetime.fromisoformat(event_data['registration_opens_date']).date()
            except (ValueError, TypeError):
                print(f"   ⚠️  Could not parse registration_opens_date: {event_data.get('registration_opens_date')}")
        
        if event_data.get('registration_opens_time'):
            try:
                time_str = event_data['registration_opens_time']
                # Try parsing as time string first
                if isinstance(time_str, str) and ':' in time_str:
                    time_parts = time_str.split(':')
                    if len(time_parts) >= 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        second = int(time_parts[2]) if len(time_parts) > 2 else 0
                        registration_opens_time_obj = time(hour, minute, second)
                    else:
                        registration_opens_time_obj = datetime.fromisoformat(time_str).time()
                else:
                    registration_opens_time_obj = datetime.fromisoformat(time_str).time()
            except (ValueError, TypeError, IndexError) as e:
                print(f"   ⚠️  Could not parse registration_opens_time '{event_data.get('registration_opens_time')}': {e}")
        
        # Determine venue_id - online events don't need a venue
        is_online = event_data.get('is_online', False)
        venue_id_for_event = None if is_online else venue.id
        
        # Ensure location is set for online events
        location = event_data.get('location')
        if is_online and not location:
            location = "Online"
        elif not location:
            location = None
        
        # Ensure event_type is set (required field)
        event_type = event_data.get('event_type', 'talk')
        if not event_type:
            event_type = 'talk'
        
        # Create event - only set fields that exist in the database
        event = Event(
            title=event_data['title'],
            description=event_data.get('description'),
            start_date=event_date,
            end_date=event_date,
            start_time=start_time_obj,
            end_time=end_time_obj,
            start_location=location,
            venue_id=venue_id_for_event,  # This is important - links event to venue
            city_id=city.id,
            event_type=event_type,  # Required field
            url=EVENT_URL,
            image_url=event_data.get('image_url'),
            source='website',
            source_url='https://www.nga.gov/calendar/finding-awe',
            is_selected=False,
        )
        
        # Set optional fields only if they exist in the model
        if hasattr(Event, 'is_online'):
            event.is_online = is_online
        if hasattr(Event, 'is_registration_required'):
            event.is_registration_required = event_data.get('is_registration_required', False)
        if hasattr(Event, 'registration_opens_date'):
            event.registration_opens_date = registration_opens_date_obj
        if hasattr(Event, 'registration_opens_time'):
            event.registration_opens_time = registration_opens_time_obj
        if hasattr(Event, 'registration_url'):
            event.registration_url = event_data.get('registration_url')
        if hasattr(Event, 'registration_info'):
            event.registration_info = event_data.get('registration_info')
        
        db.session.add(event)
        
        # Validate required fields before committing
        if not event.title:
            print("❌ Error: Event title is required")
            return False
        
        if not event.start_date:
            print("❌ Error: Event start_date is required")
            return False
        
        if not event.city_id:
            print("❌ Error: Event city_id is required")
            return False
        
        # Commit the event
        try:
            print(f"\n💾 Attempting to save event to database...")
            print(f"   Event details:")
            print(f"     Title: {event.title}")
            print(f"     Date: {event.start_date}")
            print(f"     City ID: {event.city_id}")
            print(f"     Venue ID: {event.venue_id}")
            print(f"     Event Type: {event.event_type}")
            
            db.session.commit()
            print(f"\n✅ Event created successfully!")
            print(f"   ID: {event.id}")
            print(f"   Title: {event.title}")
            print(f"   Date: {event.start_date}")
            print(f"   Time: {event.start_time} - {event.end_time}")
            print(f"   Venue: {venue.name}")
            print(f"   Venue ID: {event.venue_id}")
            print(f"   City: {city.name}")
            print(f"   Location: {event.start_location}")
            print(f"   Registration Required: {getattr(event, 'is_registration_required', False)}")
            if hasattr(event, 'registration_url') and event.registration_url:
                print(f"   Registration URL: {event.registration_url}")
            if hasattr(event, 'registration_info') and event.registration_info:
                print(f"   Registration Info: {event.registration_info}")
            
            # Verify it was actually saved
            saved_event = Event.query.get(event.id)
            if saved_event:
                print(f"\n✅ Verified: Event is in database (ID: {saved_event.id})")
                # Check what to_dict() returns
                event_dict = saved_event.to_dict()
                print(f"\n📋 Event.to_dict() output:")
                print(f"   venue_address: {repr(event_dict.get('venue_address'))}")
                print(f"   venue_name: {repr(event_dict.get('venue_name'))}")
                print(f"   city_name: {repr(event_dict.get('city_name'))}")
                print(f"   start_location: {repr(event_dict.get('start_location'))}")
            else:
                print(f"\n⚠️  Warning: Event was committed but not found in database")
            
            return True
        except Exception as commit_error:
            db.session.rollback()
            print(f"\n❌ Database error creating event: {commit_error}")
            print(f"   Error type: {type(commit_error).__name__}")
            print("\n" + "=" * 80)
            print("Full Traceback:")
            print("=" * 80)
            import traceback
            traceback.print_exc()
            
            # Try to get more details about the error
            if hasattr(commit_error, 'orig'):
                print(f"\n   Original error: {commit_error.orig}")
            if hasattr(commit_error, 'statement'):
                print(f"\n   SQL statement: {commit_error.statement}")
            if hasattr(commit_error, 'params'):
                print(f"\n   Parameters: {commit_error.params}")
            
            return False

if __name__ == '__main__':
    try:
        print("=" * 80)
        print("Adding Kandinsky Finding Awe Event to Database")
        print("=" * 80)
        success = add_event()
        if success:
            print("\n" + "=" * 80)
            print("✅ SUCCESS: Event added to database")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ FAILED: Event was not added to database")
            print("=" * 80)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
