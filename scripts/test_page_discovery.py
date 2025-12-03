#!/usr/bin/env python3
"""
Test script for automatic page discovery
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.page_discovery import PageDiscovery
import requests

def test_discovery(venue_url, event_type=None):
    """Test page discovery for a venue"""
    print(f"\n{'='*60}")
    print(f"Testing Page Discovery")
    print(f"{'='*60}")
    print(f"Venue URL: {venue_url}")
    print(f"Event Type: {event_type or 'All'}")
    print(f"{'='*60}\n")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    discoverer = PageDiscovery(session)
    
    print("🔍 Starting discovery...\n")
    discovered_urls = discoverer.discover_pages(venue_url, event_type=event_type, max_pages=20)
    
    print(f"\n✅ Discovery complete!")
    print(f"📊 Found {len(discovered_urls)} relevant pages\n")
    
    if discovered_urls:
        print("Discovered pages:")
        for i, url in enumerate(discovered_urls[:10], 1):  # Show first 10
            print(f"  {i}. {url}")
        if len(discovered_urls) > 10:
            print(f"  ... and {len(discovered_urls) - 10} more")
    else:
        print("⚠️  No pages discovered")
        print("\nThis could mean:")
        print("  - The venue doesn't have a sitemap")
        print("  - Navigation structure is non-standard")
        print("  - URL patterns don't match common conventions")
        print("  - The scraper will use fallback methods")
    
    return discovered_urls

if __name__ == "__main__":
    # Test with some example venues
    test_venues = [
        ("https://www.lacma.org", "exhibition"),
        ("https://www.lacma.org", "tour"),
        # Add more test venues here
    ]
    
    if len(sys.argv) > 1:
        # Custom URL provided
        url = sys.argv[1]
        event_type = sys.argv[2] if len(sys.argv) > 2 else None
        test_discovery(url, event_type)
    else:
        # Run default tests
        print("Running default tests...")
        print("Usage: python scripts/test_page_discovery.py <url> [event_type]")
        print("\nExample:")
        print("  python scripts/test_page_discovery.py https://www.lacma.org exhibition")
        print("  python scripts/test_page_discovery.py https://www.metmuseum.org tour")
        print("\nRunning LACMA test...\n")
        test_discovery("https://www.lacma.org", "exhibition")

