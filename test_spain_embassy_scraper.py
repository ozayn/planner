#!/usr/bin/env python3
"""Test script to scrape Spain Embassy events from Eventbrite"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, City, Venue
from scripts.eventbrite_scraper import EventbriteScraper, scrape_eventbrite_events_for_venue
from datetime import datetime

def test_spain_embassy_scraping():
    """Test scraping Spain Embassy events from Eventbrite"""
    with app.app_context():
        # Find Washington DC city
        dc_city = City.query.filter(
            db.or_(
                City.name == 'Washington',
                City.name == 'Washington, DC',
                City.name == 'Washington DC'
            )
        ).filter_by(country='United States').first()
        
        if not dc_city:
            print("❌ Washington DC city not found in database")
            return
        
        print(f"✅ Found Washington DC (city_id: {dc_city.id})")
        
        # Find Spain Embassy
        spain_embassy = Venue.query.filter_by(
            name='Embassy of Spain',
            city_id=dc_city.id
        ).first()
        
        if not spain_embassy:
            print("❌ Embassy of Spain not found in database")
            return
        
        print(f"\n🏛️  Found Embassy of Spain (venue_id: {spain_embassy.id})")
        print(f"   Name: {spain_embassy.name}")
        print(f"   Ticketing URL: {spain_embassy.ticketing_url or '(none)'}")
        print(f"   Website URL: {spain_embassy.website_url or '(none)'}")
        
        # Check if it has Eventbrite URL
        if spain_embassy.ticketing_url and 'eventbrite.com' in spain_embassy.ticketing_url:
            print(f"\n✅ Embassy has Eventbrite URL - will scrape directly")
            print(f"   URL: {spain_embassy.ticketing_url}")
            
            # Test extracting organizer ID
            scraper = EventbriteScraper()
            organizer_id = scraper.extract_organizer_id_from_url(spain_embassy.ticketing_url)
            if organizer_id:
                print(f"   Organizer ID: {organizer_id}")
            else:
                print(f"   ⚠️  Could not extract organizer ID from URL")
            
            # Scrape events
            print(f"\n🚀 Scraping events from Eventbrite...")
            print(f"   Time range: this_month")
            
            try:
                events = scrape_eventbrite_events_for_venue(
                    venue_id=spain_embassy.id,
                    time_range='this_month'
                )
                
                print(f"\n✅ Scraping completed!")
                print(f"   Total events found: {len(events)}")
                
                if events:
                    print(f"\n📅 Events found:")
                    for i, event in enumerate(events, 1):
                        print(f"\n   {i}. {event.get('title', 'Untitled')}")
                        print(f"      Date: {event.get('start_date')}")
                        print(f"      Time: {event.get('start_time')}")
                        print(f"      URL: {event.get('url', 'N/A')}")
                        if event.get('description'):
                            desc = event.get('description', '')[:100]
                            print(f"      Description: {desc}...")
                else:
                    print(f"   ⚠️  No events found for this month")
                    
            except Exception as e:
                print(f"\n❌ Error scraping events: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\n⚠️  Embassy does not have Eventbrite URL - will search for organizers")
            
            # Search for Eventbrite organizers
            scraper = EventbriteScraper()
            print(f"\n🔍 Searching for Eventbrite organizers matching 'Embassy of Spain'...")
            
            try:
                organizers = scraper.search_organizers_by_venue_name(
                    venue_name='Embassy of Spain',
                    city_name='Washington',
                    state='DC',
                    max_results=5
                )
                
                print(f"\n✅ Found {len(organizers)} organizers:")
                for i, org in enumerate(organizers, 1):
                    print(f"\n   {i}. {org.get('name')}")
                    print(f"      ID: {org.get('id')}")
                    print(f"      URL: {org.get('url')}")
                    print(f"      Events: {org.get('event_count', 0)}")
                    print(f"      Verified: {org.get('verified', False)}")
                
                if organizers:
                    # Try to get events from the first organizer
                    best_org = organizers[0]
                    organizer_id = best_org.get('id')
                    
                    print(f"\n🚀 Fetching events from organizer: {best_org.get('name')} (ID: {organizer_id})")
                    
                    from datetime import date, timedelta
                    today = date.today()
                    events = scraper.get_organizer_events(
                        organizer_id=organizer_id,
                        status='live',
                        start_date=today,
                        end_date=today + timedelta(days=30)
                    )
                    
                    print(f"\n✅ Found {len(events)} events:")
                    for i, eb_event in enumerate(events[:10], 1):  # Show first 10
                        name = eb_event.get('name', {}).get('text', 'Untitled')
                        start = eb_event.get('start', {}).get('local', 'N/A')
                        url = eb_event.get('url', 'N/A')
                        print(f"\n   {i}. {name}")
                        print(f"      Start: {start}")
                        print(f"      URL: {url}")
                    
            except Exception as e:
                print(f"\n❌ Error searching for organizers: {e}")
                import traceback
                traceback.print_exc()

if __name__ == '__main__':
    test_spain_embassy_scraping()
