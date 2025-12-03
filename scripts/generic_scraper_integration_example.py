#!/usr/bin/env python3
"""
Example: How to integrate GenericVenueScraper with specialized scrapers

This shows how to use the generic scraper as a fallback when no specialized
scraper exists for a venue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generic_venue_scraper import GenericVenueScraper
from app import app, db, Venue


def scrape_venue_with_fallback(venue_id):
    """
    Scrape events for a venue, using specialized scrapers if available,
    otherwise falling back to the generic scraper.
    """
    with app.app_context():
        venue = Venue.query.get(venue_id)
        if not venue:
            print(f"Venue {venue_id} not found")
            return []
        
        events = []
        
        # Check if we have a specialized scraper for this venue
        if 'hirshhorn' in venue.name.lower() or 'hirshhorn.si.edu' in (venue.website_url or '').lower():
            # Use specialized Hirshhorn scraper
            from scripts.venue_event_scraper import VenueEventScraper
            scraper = VenueEventScraper()
            events = scraper.scrape_venue_events(venue_ids=[venue_id])
            print(f"✅ Used specialized Hirshhorn scraper: {len(events)} events")
            
        elif 'nga.gov' in (venue.website_url or '').lower() or 'national gallery' in venue.name.lower():
            # Use specialized NGA scraper
            from scripts.nga_comprehensive_scraper import scrape_all_nga_events
            events = scrape_all_nga_events()
            print(f"✅ Used specialized NGA scraper: {len(events)} events")
            
        else:
            # Use generic scraper as fallback
            generic_scraper = GenericVenueScraper()
            if venue.website_url:
                events = generic_scraper.scrape_venue_events(
                    venue_url=venue.website_url,
                    venue_name=venue.name,
                    time_range='this_month'
                )
                print(f"✅ Used generic scraper: {len(events)} events")
            else:
                print(f"⚠️  No website URL for {venue.name}")
        
        return events


if __name__ == '__main__':
    # Example usage
    if len(sys.argv) > 1:
        venue_id = int(sys.argv[1])
        events = scrape_venue_with_fallback(venue_id)
        print(f"\n📊 Found {len(events)} events")
        for event in events[:5]:  # Show first 5
            print(f"  - {event.get('title')} ({event.get('event_type')})")

