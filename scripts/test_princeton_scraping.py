#!/usr/bin/env python3
"""
Test script to scrape events from Princeton venues using the generic scraper
This will help us develop and improve the generic scraper for Princeton venues.
"""
import sys
import os
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, City, Event
from scripts.generic_venue_scraper import GenericVenueScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def scrape_princeton_venues():
    """Scrape events from all Princeton venues using the generic scraper"""
    with app.app_context():
        # Get Princeton city
        princeton = City.query.filter_by(name='Princeton').first()
        if not princeton:
            print("❌ Princeton city not found in database")
            return
        
        print(f"✅ Found Princeton city: ID {princeton.id}\n")
        
        # Get all Princeton venues
        venues = Venue.query.filter_by(city_id=princeton.id).all()
        print(f"Found {len(venues)} Princeton venues\n")
        
        if not venues:
            print("⚠️  No venues found for Princeton")
            return
        
        # Initialize generic scraper
        generic_scraper = GenericVenueScraper()
        
        total_events = 0
        venues_with_events = 0
        results = []
        
        for venue in venues:
            if not venue.website_url:
                print(f"⏭️  Skipping {venue.name} - no website URL")
                continue
            
            print(f"\n{'='*60}")
            print(f"🏛️  Scraping: {venue.name}")
            print(f"   Type: {venue.venue_type}")
            print(f"   URL: {venue.website_url}")
            print(f"{'='*60}")
            
            venue_result = {
                'venue_name': venue.name,
                'venue_type': venue.venue_type,
                'venue_url': venue.website_url,
                'events_found': 0,
                'events': [],
                'error': None
            }
            
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
                    venue_result['events_found'] = len(events)
                    
                    # Display event details
                    for i, event in enumerate(events, 1):
                        print(f"\n   Event {i}:")
                        print(f"      Title: {event.get('title', 'N/A')}")
                        print(f"      Type: {event.get('event_type', 'N/A')}")
                        if event.get('start_date'):
                            print(f"      Date: {event.get('start_date')}")
                        if event.get('start_time'):
                            print(f"      Time: {event.get('start_time')}")
                        if event.get('end_time'):
                            print(f"      End Time: {event.get('end_time')}")
                        if event.get('location'):
                            print(f"      Location: {event.get('location')}")
                        if event.get('description'):
                            desc = event.get('description', '')[:100]
                            print(f"      Description: {desc}...")
                        if event.get('url'):
                            print(f"      URL: {event.get('url')}")
                        if event.get('image_url'):
                            print(f"      Image: {event.get('image_url')[:50]}...")
                        
                        # Store event for results
                        venue_result['events'].append({
                            'title': event.get('title'),
                            'event_type': event.get('event_type'),
                            'start_date': str(event.get('start_date')) if event.get('start_date') else None,
                            'start_time': str(event.get('start_time')) if event.get('start_time') else None,
                            'end_time': str(event.get('end_time')) if event.get('end_time') else None,
                            'location': event.get('location'),
                            'url': event.get('url'),
                            'description': event.get('description', '')[:200] if event.get('description') else None
                        })
                else:
                    print("❌ No events found")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Error scraping {venue.name}: {error_msg}")
                venue_result['error'] = error_msg
                import traceback
                traceback.print_exc()
            
            results.append(venue_result)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"Total venues scraped: {len(venues)}")
        print(f"Venues with events: {venues_with_events}")
        print(f"Total events found: {total_events}")
        
        # Save results to JSON file
        output_file = 'princeton_scraping_results.json'
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'city': 'Princeton',
            'summary': {
                'total_venues': len(venues),
                'venues_with_events': venues_with_events,
                'total_events': total_events
            },
            'results': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✅ Results saved to {output_file}")
        
        return results

if __name__ == '__main__':
    scrape_princeton_venues()








