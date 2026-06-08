#!/usr/bin/env python3
"""
Test the generic scraper on The Wharf DC events page
"""
import sys
import json
sys.path.insert(0, '.')

from scripts.generic_venue_scraper import GenericVenueScraper

EVENTS_URL = 'https://www.wharfdc.com/upcoming-events/'

def main():
    print("🔍 Testing generic scraper on The Wharf DC...")
    print(f"   URL: {EVENTS_URL}\n")
    
    scraper = GenericVenueScraper()
    events = scraper.scrape_venue_events(
        venue_url=EVENTS_URL,
        venue_name='The Wharf DC',
        event_type=None,
        time_range='next_month'  # Get events for next few months
    )
    
    print(f"\n📊 Results: {len(events)} events found\n")
    
    for i, e in enumerate(events, 1):
        print(f"--- Event {i} ---")
        print(f"  Title: {e.get('title', 'N/A')}")
        print(f"  Date: {e.get('start_date', 'N/A')}")
        print(f"  Time: {e.get('start_time', 'N/A')}")
        print(f"  Type: {e.get('event_type', 'N/A')}")
        print(f"  URL: {e.get('url', 'N/A')[:80]}..." if e.get('url') and len(e.get('url', '')) > 80 else f"  URL: {e.get('url', 'N/A')}")
        desc = (e.get('description') or '')[:100]
        print(f"  Description: {desc}..." if len(desc) >= 100 else f"  Description: {desc}")
        print()

if __name__ == '__main__':
    main()
