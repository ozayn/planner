#!/usr/bin/env python3
"""Test script to verify exhibition limit is working correctly"""
import sys
import os
sys.path.insert(0, '.')

from app import app, db, Venue, City
from scripts.venue_event_scraper import VenueEventScraper
import logging

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

with app.app_context():
    # Find New York and Met Museum
    ny = City.query.filter(City.name.ilike('%new york%')).first()
    if not ny:
        print("❌ New York not found")
        sys.exit(1)
    
    met = Venue.query.filter(
        Venue.city_id == ny.id,
        Venue.name.ilike('%metropolitan%')
    ).first()
    
    if not met:
        print("❌ Met Museum not found")
        sys.exit(1)
    
    print(f"Testing with: {met.name}")
    print(f"Max exhibitions per venue: 2")
    print("-" * 60)
    
    scraper = VenueEventScraper()
    events = scraper.scrape_venue_events(
        venue_ids=[met.id],
        event_type='exhibition',
        time_range='this_month',
        max_exhibitions_per_venue=2
    )
    
    print("-" * 60)
    print(f"RESULT: Scraper returned {len(events)} events")
    
    met_exhibitions = [e for e in events if e.get('venue_id') == met.id and e.get('event_type') == 'exhibition']
    print(f"Met Museum exhibitions: {len(met_exhibitions)}")
    
    if len(met_exhibitions) > 2:
        print(f"❌ ERROR: Expected max 2, got {len(met_exhibitions)}")
        print("\nExhibitions found:")
        for i, e in enumerate(met_exhibitions, 1):
            print(f"  {i}. {e.get('title')} (URL: {e.get('url', 'N/A')[:60]})")
    else:
        print(f"✅ SUCCESS: Got {len(met_exhibitions)} exhibitions (limit: 2)")

