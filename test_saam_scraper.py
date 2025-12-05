#!/usr/bin/env python3
"""
Test script for SAAM scraper - tests different event types
"""
import os
import sys
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from scripts.saam_scraper import (
    scrape_saam_exhibitions,
    scrape_saam_tours,
    scrape_saam_events,
    scrape_event_detail,
    create_scraper
)

def print_event_details(event, index=None):
    """Print formatted event details"""
    prefix = f"{index}. " if index else ""
    print(f"\n{prefix}{'='*80}")
    print(f"Title: {event.get('title', 'N/A')}")
    print(f"Event Type: {event.get('event_type', 'N/A')}")
    print(f"Description: {event.get('description', 'N/A')[:200]}..." if event.get('description') and len(event.get('description', '')) > 200 else f"Description: {event.get('description', 'N/A')}")
    print(f"Start Date: {event.get('start_date', 'N/A')}")
    print(f"End Date: {event.get('end_date', 'N/A')}")
    print(f"Start Time: {event.get('start_time', 'N/A')}")
    print(f"End Time: {event.get('end_time', 'N/A')}")
    print(f"Location/Organizer: {event.get('organizer', 'N/A')}")
    print(f"Meeting Point: {event.get('meeting_point', 'N/A')}")
    print(f"Online: {event.get('is_online', False)}")
    print(f"Registration Required: {event.get('is_registration_required', False)}")
    print(f"Registration URL: {event.get('registration_url', 'N/A')}")
    print(f"Price: {event.get('price', 'N/A')}")
    print(f"Admission Price: {event.get('admission_price', 'N/A')}")
    print(f"Image URL: {event.get('image_url', 'N/A')}")
    print(f"Source URL: {event.get('source_url', 'N/A')}")
    print(f"{'='*80}")

def test_exhibitions():
    """Test exhibition scraping"""
    print("\n" + "="*80)
    print("TESTING EXHIBITIONS")
    print("="*80)
    
    scraper = create_scraper()
    exhibitions = scrape_saam_exhibitions(scraper)
    
    print(f"\n✅ Found {len(exhibitions)} exhibitions")
    
    # Show first 3 exhibitions
    for i, exhibition in enumerate(exhibitions[:3], 1):
        print_event_details(exhibition, i)
    
    # Check what fields are missing
    print("\n📊 FIELD COMPLETENESS CHECK:")
    required_fields = ['title', 'start_date', 'end_date', 'description', 'event_type']
    optional_fields = ['image_url', 'organizer', 'source_url']
    
    for field in required_fields + optional_fields:
        count = sum(1 for e in exhibitions if e.get(field))
        percentage = (count / len(exhibitions) * 100) if exhibitions else 0
        status = "✅" if field in required_fields and percentage == 100 else "⚠️" if percentage < 50 else "✅"
        print(f"  {status} {field}: {count}/{len(exhibitions)} ({percentage:.1f}%)")

def test_tours():
    """Test tour scraping"""
    print("\n" + "="*80)
    print("TESTING TOURS")
    print("="*80)
    
    scraper = create_scraper()
    tours = scrape_saam_tours(scraper)
    
    print(f"\n✅ Found {len(tours)} tours")
    
    # Show first 3 tours
    for i, tour in enumerate(tours[:3], 1):
        print_event_details(tour, i)
    
    # Check what fields are missing
    print("\n📊 FIELD COMPLETENESS CHECK:")
    required_fields = ['title', 'start_date', 'start_time', 'event_type']
    optional_fields = ['end_time', 'description', 'meeting_point', 'organizer', 'source_url']
    
    for field in required_fields + optional_fields:
        count = sum(1 for t in tours if t.get(field))
        percentage = (count / len(tours) * 100) if tours else 0
        status = "✅" if field in required_fields and percentage == 100 else "⚠️" if percentage < 50 else "✅"
        print(f"  {status} {field}: {count}/{len(tours)} ({percentage:.1f}%)")

def test_events():
    """Test event scraping (talks, gallery talks, etc.)"""
    print("\n" + "="*80)
    print("TESTING EVENTS (TALKS, GALLERY TALKS, ETC.)")
    print("="*80)
    
    scraper = create_scraper()
    events = scrape_saam_events(scraper)
    
    print(f"\n✅ Found {len(events)} events")
    
    # Show first 5 events
    for i, event in enumerate(events[:5], 1):
        print_event_details(event, i)
    
    # Check what fields are missing
    print("\n📊 FIELD COMPLETENESS CHECK:")
    required_fields = ['title', 'start_date', 'event_type']
    optional_fields = ['start_time', 'end_time', 'description', 'meeting_point', 'organizer', 
                      'is_online', 'is_registration_required', 'registration_url', 'price', 
                      'image_url', 'source_url']
    
    for field in required_fields + optional_fields:
        count = sum(1 for e in events if e.get(field) is not None and e.get(field) != '')
        percentage = (count / len(events) * 100) if events else 0
        status = "✅" if field in required_fields and percentage == 100 else "⚠️" if percentage < 50 else "✅"
        print(f"  {status} {field}: {count}/{len(events)} ({percentage:.1f}%)")
    
    # Check event types
    print("\n📊 EVENT TYPES:")
    event_types = {}
    for event in events:
        event_type = event.get('event_type', 'unknown')
        event_types[event_type] = event_types.get(event_type, 0) + 1
    for event_type, count in sorted(event_types.items()):
        print(f"  {event_type}: {count}")

def test_specific_event_url(url, event_type='event'):
    """Test scraping a specific event URL"""
    print("\n" + "="*80)
    print(f"TESTING SPECIFIC EVENT: {url}")
    print("="*80)
    
    scraper = create_scraper()
    event = scrape_event_detail(scraper, url, event_type=event_type)
    
    if event:
        print_event_details(event)
        
        # Check completeness
        print("\n📊 FIELD COMPLETENESS:")
        fields = {
            'Required': ['title', 'start_date', 'event_type'],
            'Important': ['description', 'start_time', 'organizer', 'source_url'],
            'Optional': ['end_time', 'meeting_point', 'is_online', 'is_registration_required', 
                        'registration_url', 'price', 'image_url']
        }
        
        for category, field_list in fields.items():
            print(f"\n{category}:")
            for field in field_list:
                value = event.get(field)
                status = "✅" if value else "❌"
                print(f"  {status} {field}: {value if value else 'MISSING'}")
    else:
        print("❌ Failed to scrape event")

if __name__ == '__main__':
    print("🧪 SAAM SCRAPER TEST SUITE")
    print("="*80)
    
    # Test exhibitions
    try:
        test_exhibitions()
    except Exception as e:
        print(f"❌ Error testing exhibitions: {e}")
        import traceback
        traceback.print_exc()
    
    # Test tours
    try:
        test_tours()
    except Exception as e:
        print(f"❌ Error testing tours: {e}")
        import traceback
        traceback.print_exc()
    
    # Test events
    try:
        test_events()
    except Exception as e:
        print(f"❌ Error testing events: {e}")
        import traceback
        traceback.print_exc()
    
    # Test specific URLs if provided
    # Uncomment and add URLs to test specific events
    # test_specific_event_url('https://americanart.si.edu/events/example-event', 'talk')
    
    print("\n" + "="*80)
    print("✅ TEST SUITE COMPLETE")
    print("="*80)



