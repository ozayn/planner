#!/usr/bin/env python3
"""Test script to scrape Princeton venues"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, City, Venue
from scripts.venue_event_scraper import VenueEventScraper
from datetime import datetime

def test_princeton_scraping():
    """Test scraping Princeton venues"""
    with app.app_context():
        # Find Princeton city
        princeton = City.query.filter_by(name='Princeton').first()
        if not princeton:
            print("❌ Princeton city not found in database")
            return
        
        print(f"✅ Found Princeton (city_id: {princeton.id})")
        
        # Get all Princeton venues
        venues = Venue.query.filter_by(city_id=princeton.id).all()
        if not venues:
            print("❌ No venues found for Princeton")
            return
        
        print(f"\n📋 Found {len(venues)} Princeton venues:")
        venue_ids = []
        for v in venues:
            print(f"   - {v.id}: {v.name}")
            print(f"     URL: {v.website_url}")
            venue_ids.append(v.id)
        
        print(f"\n🚀 Starting scraping for Princeton venues...")
        print(f"   Time range: this_month")
        print(f"   Venue IDs: {venue_ids}")
        
        # Initialize scraper
        scraper = VenueEventScraper()
        
        # Scrape events
        events = scraper.scrape_venue_events(
            city_id=princeton.id,
            event_type=None,  # All event types
            time_range='this_month',
            venue_ids=venue_ids,
            max_exhibitions_per_venue=5,
            max_events_per_venue=20
        )
        
        print(f"\n✅ Scraping completed!")
        print(f"   Total events found: {len(events)}")
        
        # Group by venue
        events_by_venue = {}
        for event in events:
            venue_id = event.get('venue_id')
            if venue_id not in events_by_venue:
                events_by_venue[venue_id] = []
            events_by_venue[venue_id].append(event)
        
        print(f"\n📊 Events by venue:")
        for venue_id, venue_events in events_by_venue.items():
            venue = Venue.query.get(venue_id)
            venue_name = venue.name if venue else f"Venue {venue_id}"
            print(f"   {venue_name}: {len(venue_events)} events")
            
            # Show first few events
            for event in venue_events[:5]:
                title = event.get('title', 'N/A')
                start_date = event.get('start_date', 'N/A')
                event_type = event.get('event_type', 'N/A')
                print(f"      - {title} ({start_date}, {event_type})")
            if len(venue_events) > 5:
                print(f"      ... and {len(venue_events) - 5} more")
        
        # Show date distribution
        dates = {}
        for event in events:
            date_str = event.get('start_date', 'Unknown')
            dates[date_str] = dates.get(date_str, 0) + 1
        
        print(f"\n📅 Events by date:")
        for date_str in sorted(dates.keys()):
            print(f"   {date_str}: {dates[date_str]} events")
        
        return events

if __name__ == '__main__':
    test_princeton_scraping()










