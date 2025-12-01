#!/usr/bin/env python3
"""
Test what event data is actually returned for calendar export
"""
import os
import sys
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

def test_event_data():
    """Test what event data is returned"""
    with app.app_context():
        # Find the Landseer event
        event = Event.query.filter(
            Event.title.like('%Landseer%')
        ).first()
        
        if not event:
            print("❌ Landseer event not found")
            # Try any Finding Awe event
            event = Event.query.filter(
                Event.title.like('%Finding Awe%')
            ).first()
            
            if not event:
                print("❌ No Finding Awe events found")
                return
        
        print(f"✅ Found event: {event.title}")
        print(f"   ID: {event.id}")
        print(f"   Venue ID: {event.venue_id}")
        print(f"   Start Location: {event.start_location}")
        
        # Get the event as dict (what the API returns)
        event_dict = event.to_dict()
        
        print(f"\n📋 Event data (to_dict() output):")
        print(f"   venue_address: {repr(event_dict.get('venue_address'))}")
        print(f"   venue_name: {repr(event_dict.get('venue_name'))}")
        print(f"   city_name: {repr(event_dict.get('city_name'))}")
        print(f"   start_location: {repr(event_dict.get('start_location'))}")
        print(f"   title: {repr(event_dict.get('title'))}")
        print(f"   url: {repr(event_dict.get('url'))}")
        
        # Simulate JavaScript NGA detection
        print(f"\n🔍 Simulating JavaScript NGA Detection:")
        venue_name = event_dict.get('venue_name') or ''
        title = event_dict.get('title') or ''
        url = event_dict.get('url') or ''
        start_location = event_dict.get('start_location') or ''
        
        venueNameLower = venue_name.lower()
        titleLower = title.lower()
        urlLower = url.lower()
        startLocLower = start_location.lower()
        
        hasNGAVenueName = 'national gallery' in venueNameLower or 'nga' in venueNameLower
        hasNGATitle = 'national gallery' in titleLower or 'finding awe' in titleLower
        hasNGAUrl = 'nga.gov' in urlLower
        hasNGALocation = (('west building' in startLocLower or 'east building' in startLocLower) and 
                         ('gallery' in startLocLower or 'floor' in startLocLower or 'main floor' in startLocLower))
        
        isNGAEvent = hasNGAVenueName or hasNGATitle or hasNGAUrl or hasNGALocation
        
        print(f"   hasNGAVenueName: {hasNGAVenueName} (venue_name: {repr(venue_name)})")
        print(f"   hasNGATitle: {hasNGATitle} (title: {repr(title)})")
        print(f"   hasNGAUrl: {hasNGAUrl} (url: {repr(url)})")
        print(f"   hasNGALocation: {hasNGALocation} (start_location: {repr(start_location)})")
        print(f"   isNGAEvent: {isNGAEvent}")
        
        if isNGAEvent:
            print(f"\n✅ Should use: 'Constitution Ave NW, Washington, DC 20565'")
        else:
            print(f"\n❌ Would NOT detect as NGA event!")
            if event_dict.get('venue_address'):
                print(f"   Would use venue_address: {event_dict.get('venue_address')}")
            elif venue_name:
                print(f"   Would use venue_name: {venue_name}")
            else:
                print(f"   Would use start_location: {start_location}")
        
        # Check venue directly
        if event.venue:
            print(f"\n🏛️  Venue details:")
            print(f"   Name: {event.venue.name}")
            print(f"   Address: {event.venue.address or 'NO ADDRESS'}")

if __name__ == '__main__':
    test_event_data()


