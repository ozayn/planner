#!/usr/bin/env python3
"""
Test script to scrape events from Irvine venues using the generic scraper
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, City, Event
from scripts.generic_venue_scraper import GenericVenueScraper
from datetime import datetime

def scrape_irvine_venues():
    """Scrape events from all Irvine venues using the generic scraper"""
    with app.app_context():
        # Get Irvine city
        irvine = City.query.filter_by(name='Irvine').first()
        if not irvine:
            print("❌ Irvine city not found in database")
            return
        
        print(f"✅ Found Irvine city: ID {irvine.id}\n")
        
        # Get all Irvine venues
        venues = Venue.query.filter_by(city_id=irvine.id).all()
        print(f"Found {len(venues)} Irvine venues\n")
        
        if not venues:
            print("⚠️  No venues found for Irvine")
            return
        
        # Initialize generic scraper
        generic_scraper = GenericVenueScraper()
        
        total_events = 0
        venues_with_events = 0
        
        for venue in venues:
            if not venue.website_url:
                print(f"⏭️  Skipping {venue.name} - no website URL")
                continue
            
            print(f"\n{'='*60}")
            print(f"🏛️  Scraping: {venue.name}")
            print(f"   Type: {venue.venue_type}")
            print(f"   URL: {venue.website_url}")
            print(f"{'='*60}")
            
            try:
                # Use generic scraper to scrape events
                events = generic_scraper.scrape_venue_events(
                    venue_url=venue.website_url,
                    venue_name=venue.name,
                    event_type=None,  # Let scraper determine type
                    time_range='this_month'  # Get events for this month
                )
                
                if events:
                    print(f"✅ Found {len(events)} events")
                    venues_with_events += 1
                    total_events += len(events)
                    
                    # Display event details
                    for i, event in enumerate(events, 1):
                        print(f"\n   Event {i}:")
                        print(f"      Title: {event.get('title', 'N/A')}")
                        print(f"      Type: {event.get('event_type', 'N/A')}")
                        if event.get('start_date'):
                            print(f"      Date: {event.get('start_date')}")
                        if event.get('start_time'):
                            print(f"      Time: {event.get('start_time')}")
                        if event.get('location'):
                            print(f"      Location: {event.get('location')}")
                        if event.get('url'):
                            print(f"      URL: {event.get('url')}")
                else:
                    print("❌ No events found")
                    
            except Exception as e:
                print(f"❌ Error scraping {venue.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"Total venues scraped: {len(venues)}")
        print(f"Venues with events: {venues_with_events}")
        print(f"Total events found: {total_events}")

if __name__ == '__main__':
    scrape_irvine_venues()

