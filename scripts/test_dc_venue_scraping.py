#!/usr/bin/env python3
"""
Test and analyze scraping performance for Washington DC venues
This script will help identify which venues need improved scraping
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue, City

# Setup logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dc_venue_scraping():
    """Test scraping on all DC venues and generate a report"""
    
    with app.app_context():
        # Get Washington DC city
        dc = City.query.filter_by(name='Washington').first()
        if not dc:
            print("❌ Washington DC not found in database")
            return
        
        print(f"🏛️ Testing scraping for Washington DC venues (city_id: {dc.id})")
        
        # Get all DC venues
        venues = Venue.query.filter_by(city_id=dc.id).all()
        print(f"📊 Found {len(venues)} venues in Washington DC\n")
        
        # Import the scraper
        try:
            from scripts.venue_event_scraper import VenueEventScraper
            scraper = VenueEventScraper()
        except Exception as e:
            print(f"❌ Error importing scraper: {e}")
            return
        
        # Test results
        results = {
            'total_venues': len(venues),
            'venues_with_websites': 0,
            'venues_without_websites': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'venues_with_events': 0,
            'total_events_found': 0,
            'venue_details': []
        }
        
        # Test on a sample of venues first (top 10 museums)
        museums = [v for v in venues if 'museum' in v.venue_type.lower() or 'museum' in v.name.lower()][:10]
        galleries = [v for v in venues if 'gallery' in v.venue_type.lower() or 'gallery' in v.name.lower()][:5]
        
        test_venues = museums + galleries
        
        print(f"🧪 Testing scraping on {len(test_venues)} sample venues...\n")
        
        for i, venue in enumerate(test_venues, 1):
            print(f"\n[{i}/{len(test_venues)}] Testing: {venue.name}")
            print(f"   Website: {venue.website_url}")
            
            venue_result = {
                'venue_id': venue.id,
                'venue_name': venue.name,
                'website_url': venue.website_url,
                'venue_type': venue.venue_type,
                'has_website': bool(venue.website_url),
                'scrape_success': False,
                'error': None,
                'events_found': 0,
                'event_types': {},
                'needs_improvement': False
            }
            
            if not venue.website_url or 'example.com' in venue.website_url:
                print("   ⚠️  No valid website URL")
                venue_result['error'] = 'No website URL'
                results['venues_without_websites'] += 1
                results['venue_details'].append(venue_result)
                continue
            
            results['venues_with_websites'] += 1
            
            # Skip closed venues
            if 'newseum' in venue.name.lower():
                print("   ⚠️  Skipping closed venue (Newseum)")
                venue_result['error'] = 'Closed venue'
                results['venue_details'].append(venue_result)
                continue
            
            try:
                # Test scraping exhibitions (most common)
                print("   🔍 Scraping exhibitions...")
                events = scraper.scrape_venue_events(
                    venue_ids=[venue.id],
                    event_type='exhibition',
                    time_range='this_month',
                    max_exhibitions_per_venue=5,
                    max_events_per_venue=10
                )
                
                venue_result['events_found'] = len(events)
                venue_result['scrape_success'] = True
                
                # Count event types
                for event in events:
                    etype = event.get('event_type', 'unknown')
                    venue_result['event_types'][etype] = venue_result['event_types'].get(etype, 0) + 1
                
                if events:
                    print(f"   ✅ Found {len(events)} events")
                    results['venues_with_events'] += 1
                    results['total_events_found'] += len(events)
                    
                    # Show sample events
                    for event in events[:3]:
                        print(f"      - {event.get('title', 'No title')[:60]}")
                else:
                    print("   ⚠️  No events found (may need improvement)")
                    venue_result['needs_improvement'] = True
                
                results['successful_scrapes'] += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                venue_result['error'] = str(e)
                venue_result['needs_improvement'] = True
                results['failed_scrapes'] += 1
            
            results['venue_details'].append(venue_result)
        
        # Generate report
        print("\n" + "="*60)
        print("📊 SCRAPING TEST REPORT")
        print("="*60)
        print(f"Total venues tested: {len(test_venues)}")
        print(f"Venues with websites: {results['venues_with_websites']}")
        print(f"Venues without websites: {results['venues_without_websites']}")
        print(f"Successful scrapes: {results['successful_scrapes']}")
        print(f"Failed scrapes: {results['failed_scrapes']}")
        print(f"Venues with events found: {results['venues_with_events']}")
        print(f"Total events found: {results['total_events_found']}")
        
        # Identify venues that need improvement
        needs_improvement = [v for v in results['venue_details'] if v.get('needs_improvement')]
        if needs_improvement:
            print(f"\n⚠️  Venues needing improvement: {len(needs_improvement)}")
            for v in needs_improvement:
                print(f"   - {v['venue_name']}: {v.get('error', 'No events found')}")
        
        # Save detailed report
        report_file = 'dc_venue_scraping_report.json'
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        return results

if __name__ == '__main__':
    test_dc_venue_scraping()

