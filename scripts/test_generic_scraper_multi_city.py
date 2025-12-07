#!/usr/bin/env python3
"""
Test and improve the generic scraper on museums from multiple cities
This script tests the generic scraper on museums from various cities,
collects results, and identifies areas for improvement.
"""
import sys
import os
import json
import logging
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, City
from scripts.generic_venue_scraper import GenericVenueScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Test museums from different cities (prioritize major museums with good websites)
TEST_MUSEUMS = [
    # New York
    {'name': 'Metropolitan Museum of Art', 'city': 'New York', 'url': 'https://www.metmuseum.org'},
    {'name': 'Museum of Modern Art (MoMA)', 'city': 'New York', 'url': 'https://www.moma.org'},
    
    # Los Angeles
    {'name': 'Getty Center', 'city': 'Los Angeles', 'url': 'https://www.getty.edu'},
    {'name': 'Los Angeles County Museum of Art (LACMA)', 'city': 'Los Angeles', 'url': 'https://www.lacma.org'},
    
    # San Francisco
    {'name': 'de Young Museum', 'city': 'San Francisco', 'url': 'https://deyoung.famsf.org'},
    
    # Chicago
    {'name': 'Art Institute of Chicago', 'city': 'Chicago', 'url': 'https://www.artic.edu'},
    {'name': 'Field Museum', 'city': 'Chicago', 'url': 'https://www.fieldmuseum.org'},
    
    # Boston
    {'name': 'Museum of Fine Arts Boston', 'city': 'Boston', 'url': 'https://www.mfa.org'},
    
    # London
    {'name': 'British Museum', 'city': 'London', 'url': 'https://www.britishmuseum.org'},
    {'name': 'Tate Modern', 'city': 'London', 'url': 'https://www.tate.org.uk/visit/tate-modern'},
    
    # Paris
    {'name': 'Louvre Museum', 'city': 'Paris', 'url': 'https://www.louvre.fr'},
    
    # Toronto
    {'name': 'Art Gallery of Ontario', 'city': 'Toronto', 'url': 'https://ago.ca'},
    {'name': 'Royal Ontario Museum', 'city': 'Toronto', 'url': 'https://www.rom.on.ca'},
]

def test_museum_scraping(museum_info, scraper):
    """Test scraping a single museum and return results"""
    results = {
        'museum': museum_info['name'],
        'city': museum_info['city'],
        'url': museum_info['url'],
        'success': False,
        'events_found': 0,
        'events': [],
        'errors': [],
        'warnings': [],
        'issues': []
    }
    
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {museum_info['name']} ({museum_info['city']})")
        logger.info(f"URL: {museum_info['url']}")
        logger.info(f"{'='*80}")
        
        # Test exhibitions
        logger.info("\n📅 Testing EXHIBITIONS...")
        exhibitions = scraper.scrape_venue_events(
            venue_url=museum_info['url'],
            venue_name=museum_info['name'],
            event_type='exhibition',
            time_range='this_month'
        )
        logger.info(f"   Found {len(exhibitions)} exhibitions")
        
        # Test all events
        logger.info("\n📅 Testing ALL EVENTS...")
        all_events = scraper.scrape_venue_events(
            venue_url=museum_info['url'],
            venue_name=museum_info['name'],
            event_type=None,
            time_range='this_month'
        )
        logger.info(f"   Found {len(all_events)} total events")
        
        # Analyze results
        results['events'] = all_events
        results['events_found'] = len(all_events)
        results['exhibitions_found'] = len(exhibitions)
        results['success'] = len(all_events) > 0
        
        # Check for common issues
        if len(all_events) == 0:
            results['issues'].append('No events found')
        else:
            # Check event quality
            events_with_dates = [e for e in all_events if e.get('start_date')]
            events_with_times = [e for e in all_events if e.get('start_time')]
            events_with_descriptions = [e for e in all_events if e.get('description') and len(e.get('description', '')) > 20]
            events_with_urls = [e for e in all_events if e.get('url')]
            
            results['quality_metrics'] = {
                'with_dates': len(events_with_dates),
                'with_times': len(events_with_times),
                'with_descriptions': len(events_with_descriptions),
                'with_urls': len(events_with_urls)
            }
            
            if len(events_with_dates) < len(all_events) * 0.5:
                results['issues'].append('Many events missing dates')
            if len(events_with_descriptions) < len(all_events) * 0.3:
                results['issues'].append('Many events missing descriptions')
            if len(events_with_urls) < len(all_events) * 0.5:
                results['issues'].append('Many events missing URLs')
        
        # Show sample events
        if all_events:
            logger.info(f"\n📋 Sample events found:")
            for i, event in enumerate(all_events[:3], 1):
                logger.info(f"   {i}. {event.get('title', 'N/A')[:60]}")
                logger.info(f"      Type: {event.get('event_type', 'N/A')}")
                logger.info(f"      Date: {event.get('start_date', 'N/A')}")
                if event.get('url'):
                    logger.info(f"      URL: {event.get('url')[:60]}")
        
    except Exception as e:
        results['success'] = False
        results['errors'].append(str(e))
        logger.error(f"❌ Error testing {museum_info['name']}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return results

def main():
    """Main test function"""
    print("🧪 Generic Scraper Multi-City Test")
    print("=" * 80)
    print(f"Testing {len(TEST_MUSEUMS)} museums from {len(set(m['city'] for m in TEST_MUSEUMS))} cities")
    print("=" * 80)
    
    scraper = GenericVenueScraper()
    all_results = []
    
    for museum_info in TEST_MUSEUMS:
        results = test_museum_scraping(museum_info, scraper)
        all_results.append(results)
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    successful = [r for r in all_results if r['success']]
    failed = [r for r in all_results if not r['success']]
    
    print(f"\n✅ Successful: {len(successful)}/{len(all_results)}")
    print(f"❌ Failed: {len(failed)}/{len(all_results)}")
    
    if successful:
        total_events = sum(r['events_found'] for r in successful)
        avg_events = total_events / len(successful) if successful else 0
        print(f"\n📈 Events Found:")
        print(f"   Total: {total_events}")
        print(f"   Average per museum: {avg_events:.1f}")
        
        # Quality metrics
        print(f"\n📊 Quality Metrics (for successful scrapes):")
        for result in successful:
            if 'quality_metrics' in result:
                metrics = result['quality_metrics']
                print(f"\n   {result['museum']}:")
                print(f"      Events with dates: {metrics['with_dates']}/{result['events_found']}")
                print(f"      Events with times: {metrics['with_times']}/{result['events_found']}")
                print(f"      Events with descriptions: {metrics['with_descriptions']}/{result['events_found']}")
                print(f"      Events with URLs: {metrics['with_urls']}/{result['events_found']}")
    
    # Issues summary
    print(f"\n⚠️  Issues Found:")
    issues_by_type = defaultdict(int)
    for result in all_results:
        for issue in result.get('issues', []):
            issues_by_type[issue] += 1
    
    if issues_by_type:
        for issue, count in sorted(issues_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"   {issue}: {count} museums")
    else:
        print("   No issues found!")
    
    # Failed museums
    if failed:
        print(f"\n❌ Failed Museums:")
        for result in failed:
            print(f"   {result['museum']} ({result['city']})")
            if result['errors']:
                print(f"      Error: {result['errors'][0]}")
    
    # Save detailed results to JSON
    output_file = 'generic_scraper_test_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'total_museums': len(all_results),
            'successful': len(successful),
            'failed': len(failed),
            'results': all_results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
