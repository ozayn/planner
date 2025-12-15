#!/usr/bin/env python3
"""
Test accessing /exhibitions/current URL that generic scraper tries
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from scripts.nga_comprehensive_scraper import create_scraper
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_exhibitions_current():
    """Test accessing /exhibitions/current URL"""
    print("=" * 80)
    print("Testing NGA /exhibitions/current URL")
    print("=" * 80)
    
    test_urls = [
        'https://www.nga.gov/exhibitions/current',
        'https://www.nga.gov/calendar?tab=exhibitions',  # What we actually use
    ]
    
    scraper = create_scraper()
    
    for url in test_urls:
        print(f"\n📄 Testing: {url}")
        try:
            response = scraper.get(url, timeout=20)
            print(f"   Status: {response.status_code}")
            if response.status_code == 403:
                print("   ⚠️  403 Forbidden!")
            elif response.status_code == 200:
                print("   ✅ Success")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_exhibitions_current()
