#!/usr/bin/env python3
"""
Test NGA exhibitions scraper locally
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from scripts.nga_comprehensive_scraper import scrape_nga_exhibitions, create_scraper
import logging

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_exhibitions():
    """Test scraping NGA exhibitions"""
    print("=" * 80)
    print("Testing NGA Exhibitions Scraper")
    print("=" * 80)
    
    try:
        # Create scraper
        print("\n1. Creating scraper...")
        scraper = create_scraper()
        print("   ✅ Scraper created")
        
        # Scrape exhibitions
        print("\n2. Scraping exhibitions...")
        events = scrape_nga_exhibitions(scraper)
        
        print(f"\n✅ Successfully scraped {len(events)} exhibitions")
        
        if events:
            print("\n📋 Sample exhibitions:")
            for i, event in enumerate(events[:5], 1):
                print(f"   {i}. {event.get('title', 'N/A')}")
                print(f"      URL: {event.get('url', 'N/A')}")
                print(f"      Start: {event.get('start_date', 'N/A')}")
                print()
        else:
            print("   ⚠️  No exhibitions found")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_exhibitions()
    sys.exit(0 if success else 1)
