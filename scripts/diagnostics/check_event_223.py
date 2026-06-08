#!/usr/bin/env python3
"""
Check event ID 223 to see where it came from
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City, Source

def check_event_223():
    """Check event ID 223"""
    with app.app_context():
        event = Event.query.get(223)
        
        if not event:
            print("❌ Event ID 223 not found")
            return
        
        print(f"✅ Found event ID 223:")
        print(f"\n📋 Basic Info:")
        print(f"   Title: {event.title}")
        print(f"   Description: {event.description[:200] if event.description else 'None'}...")
        print(f"   Event Type: {event.event_type}")
        print(f"   Start Date: {event.start_date}")
        print(f"   End Date: {event.end_date}")
        print(f"   Start Time: {event.start_time}")
        print(f"   End Time: {event.end_time}")
        print(f"   URL: {event.url}")
        
        print(f"\n🏛️  Location Info:")
        print(f"   Venue ID: {event.venue_id}")
        if event.venue_id:
            venue = Venue.query.get(event.venue_id)
            if venue:
                print(f"   Venue: {venue.name}")
                print(f"   Venue Type: {venue.venue_type}")
        
        print(f"   City ID: {event.city_id}")
        if event.city_id:
            city = City.query.get(event.city_id)
            if city:
                print(f"   City: {city.name}, {city.country}")
        
        print(f"\n📰 Source Info:")
        print(f"   Source: {event.source}")
        print(f"   Source URL: {event.source_url}")
        
        # Check if there's a source record
        if event.source_url:
            source = Source.query.filter_by(url=event.source_url).first()
            if source:
                print(f"   Source Record: {source.name}")
                print(f"   Source Type: {source.source_type}")
        
        print(f"\n🔗 Links:")
        print(f"   Zoom Link: {getattr(event, 'zoom_link', 'N/A (field may not exist)')}")
        
        print(f"\n📅 Recurrence:")
        # Check description for recurrence info
        if event.description and '[RECURRING:' in event.description:
            import re
            match = re.search(r'\[RECURRING:\s*([^\]]+)\]', event.description)
            if match:
                print(f"   Recurrence Rule: {match.group(1)}")
        
        print(f"\n⏰ Created/Updated:")
        print(f"   Created At: {event.created_at}")
        print(f"   Updated At: {event.updated_at}")
        
        # Check if this looks like a placeholder/default event
        print(f"\n🔍 Analysis:")
        if "Vipassana Group Sitting" in event.title and not any(keyword in event.title.lower() for keyword in ['wednesday', 'sunday', 'monday', 'tuesday', 'thursday', 'friday', 'saturday', 'se,', 'cet', 'timezone']):
            print(f"   ⚠️  This looks like a placeholder/default event")
            print(f"   - Generic title without specific day/timezone")
        if event.url == 'https://www.dhamma.org/en/os/locations/virtual_events':
            print(f"   ⚠️  URL points to main page, not a specific meeting link")
        if not event.start_time or event.start_time.strftime('%H:%M') == '19:00':
            print(f"   ⚠️  Default time (7 PM) - likely a placeholder")

if __name__ == '__main__':
    check_event_223()
