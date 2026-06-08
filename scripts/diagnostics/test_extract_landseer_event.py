#!/usr/bin/env python3
"""
Test extracting event data from the Landseer Finding Awe event page
"""
import os
import sys
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.nga_finding_awe_scraper import scrape_individual_event
import cloudscraper

def test_extraction():
    """Test extracting event data from the URL"""
    url = 'https://www.nga.gov/calendar/finding-awe/finding-awe-sir-edwin-landseers-alpine-mastiffs-reanimating-distressed-traveler?evd=202601241915'
    
    print("🔍 Testing event extraction from URL...")
    print(f"URL: {url}")
    print("=" * 80)
    
    # Create scraper session
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'darwin',
            'desktop': True
        }
    )
    
    # Extract event data
    event_data = scrape_individual_event(url, scraper)
    
    if event_data:
        print("\n✅ Extraction successful!")
        print("\n" + "=" * 80)
        print("📋 Extracted Event Data:")
        print("=" * 80)
        print(json.dumps(event_data, indent=2, default=str))
        
        print("\n" + "=" * 80)
        print("📋 Key Information:")
        print("=" * 80)
        print(f"   Title: {event_data.get('title', 'N/A')}")
        print(f"   Date: {event_data.get('start_date', 'N/A')}")
        print(f"   Time: {event_data.get('start_time', 'N/A')} - {event_data.get('end_time', 'N/A')}")
        print(f"   Location: {event_data.get('location', 'N/A')}")
        print(f"   Online: {event_data.get('is_online', False)}")
        print(f"   Registration Required: {event_data.get('is_registration_required', False)}")
        print(f"   Registration Opens Date: {event_data.get('registration_opens_date', 'N/A')}")
        print(f"   Registration Opens Time: {event_data.get('registration_opens_time', 'N/A')}")
        print(f"   Registration URL: {event_data.get('registration_url', 'N/A')}")
        print(f"   Registration Info: {event_data.get('registration_info', 'N/A')}")
        desc = event_data.get('description', '') or ''
        print(f"   Description: {desc[:200]}..." if len(desc) > 200 else f"   Description: {desc}")
        print(f"   Description length: {len(desc)} characters")
        
        return 0
    else:
        print("\n❌ Extraction failed - no data returned")
        return 1

if __name__ == '__main__':
    sys.exit(test_extraction())


