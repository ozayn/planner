#!/usr/bin/env python3
"""Test script to scrape Princeton museums only"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, City, Venue
from scripts.venue_event_scraper import VenueEventScraper
from datetime import datetime

def test_princeton_museums():
    """Test scraping Princeton museums only"""
    with app.app_context():
        # Find Princeton city
        princeton = City.query.filter_by(name='Princeton').first()
        if not princeton:
            print("❌ Princeton city not found in database")
            return
        
        print(f"✅ Found Princeton (city_id: {princeton.id})")
        
        # Get only museum venues from Princeton
        venues = Venue.query.filter_by(city_id=princeton.id, venue_type='museum').all()
        if not venues:
            print("⚠️  No museums found for Princeton, trying all venues...")
            venues = Venue.query.filter_by(city_id=princeton.id).all()
            # Filter for museums by name/type
            museums = [v for v in venues if 'museum' in v.name.lower() or v.venue_type == 'museum']
            venues = museums if museums else venues
        
        if not venues:
            print("❌ No venues found for Princeton")
            return
        
        print(f"\n📋 Found {len(venues)} Princeton museum(s):")
        venue_ids = []
        for v in venues:
            print(f"   - {v.id}: {v.name} ({v.venue_type})")
            print(f"     URL: {v.website_url}")
            venue_ids.append(v.id)
        
        print(f"\n🚀 Starting scraping for Princeton museums...")
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
            max_exhibitions_per_venue=10,
            max_events_per_venue=30
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
            print(f"\n   {venue_name}: {len(venue_events)} events")
            
            # Show all events with details
            for i, event in enumerate(venue_events, 1):
                title = event.get('title', 'N/A')
                start_date = event.get('start_date', 'N/A')
                event_type = event.get('event_type', 'N/A')
                url = event.get('url', '')
                image_url = event.get('image_url', '')
                print(f"      {i}. {title}")
                print(f"         Date: {start_date} | Type: {event_type}")
                if url:
                    print(f"         URL: {url[:80]}")
                if image_url:
                    print(f"         Image: {image_url[:60]}...")
        
        # Show date distribution
        dates = {}
        for event in events:
            date_str = event.get('start_date', 'Unknown')
            if date_str is None:
                date_str = 'No date'
            dates[date_str] = dates.get(date_str, 0) + 1
        
        print(f"\n📅 Events by date:")
        # Sort dates, handling None/string mix
        sorted_dates = sorted([d for d in dates.keys() if d != 'No date' and d != 'Unknown']) + [d for d in ['No date', 'Unknown'] if d in dates]
        for date_str in sorted_dates:
            print(f"   {date_str}: {dates[date_str]} events")
        
        return events

if __name__ == '__main__':
    test_princeton_museums()










