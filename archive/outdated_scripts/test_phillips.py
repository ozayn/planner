#!/usr/bin/env python3
"""Quick test of Phillips Collection LLM search"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.fetch_venue_details import LLMVenueDetailSearcher

def test_phillips():
    print("🔍 Testing Phillips Collection search...")
    
    searcher = LLMVenueDetailSearcher(silent=False)
    result = searcher.search_venue_details('Phillips Collection', 'Washington, DC, United States', silent=False)
    
    print("\n=== RESULT ===")
    if result and result.get('name'):
        print(f"✅ Success! Found: {result['name']}")
        print(f"Address: {result.get('address', 'N/A')}")
        print(f"Type: {result.get('venue_type', 'N/A')}")
        print(f"Website: {result.get('website_url', 'N/A')}")
        print(f"Phone: {result.get('phone_number', 'N/A')}")
        return True
    else:
        print("❌ Failed to get venue details")
        print("Result:", result)
        return False

if __name__ == '__main__':
    test_phillips()


