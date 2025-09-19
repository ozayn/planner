#!/usr/bin/env python3
"""
Automated tests for venue data to prevent regressions
"""

import os
import sys
import json
import requests
import unittest
sys.path.append('.')

from app import app, db, Venue

class VenueDataTests(unittest.TestCase):
    
    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        self.app_context.pop()
    
    def test_no_fake_image_urls(self):
        """Test that no venues have fake image URLs"""
        venues_with_fake_images = []
        
        for venue in Venue.query.all():
            if venue.image_url:
                # Check for my fake image pattern
                if (isinstance(venue.image_url, str) and 
                    venue.image_url.startswith('AciIO2') and 
                    len(venue.image_url) == 200 and
                    'MCxHBCtV4IU74SVbi1yjLBPb' in venue.image_url):
                    venues_with_fake_images.append(venue.name)
        
        self.assertEqual(len(venues_with_fake_images), 0, 
                        f"Found venues with fake image URLs: {venues_with_fake_images}")
    
    def test_image_url_formats(self):
        """Test that image URLs are in correct format"""
        invalid_formats = []
        
        for venue in Venue.query.all():
            if venue.image_url:
                # Should be either raw photo reference or valid JSON
                if venue.image_url.startswith('{'):
                    try:
                        photo_data = json.loads(venue.image_url)
                        if not isinstance(photo_data, dict) or 'photo_reference' not in photo_data:
                            invalid_formats.append(f"{venue.name}: Invalid JSON format")
                    except json.JSONDecodeError:
                        invalid_formats.append(f"{venue.name}: Invalid JSON")
        
        self.assertEqual(len(invalid_formats), 0,
                        f"Found venues with invalid image formats: {invalid_formats}")
    
    def test_venue_type_consistency(self):
        """Test that venue types are consistent (lowercase, standardized)"""
        inconsistent_types = []
        
        for venue in Venue.query.all():
            if venue.venue_type:
                if venue.venue_type != venue.venue_type.lower():
                    inconsistent_types.append(f"{venue.name}: '{venue.venue_type}' not lowercase")
        
        self.assertEqual(len(inconsistent_types), 0,
                        f"Found inconsistent venue types: {inconsistent_types}")
    
    def test_major_venues_have_social_media(self):
        """Test that major venues have social media presence"""
        missing_social = []
        
        major_venue_types = ['museum', 'embassy', 'arts_center']
        
        for venue in Venue.query.filter(Venue.venue_type.in_(major_venue_types)).all():
            has_social = any([
                venue.instagram_url,
                venue.facebook_url,
                venue.twitter_url
            ])
            
            if not has_social:
                missing_social.append(f"{venue.name} ({venue.venue_type})")
        
        # Allow some venues to not have social media, but not too many
        self.assertLess(len(missing_social), 10,
                       f"Too many major venues missing social media: {missing_social}")
    
    def test_json_database_sync(self):
        """Test that venues.json is in sync with database"""
        venues_json_path = 'data/venues.json'
        
        if not os.path.exists(venues_json_path):
            self.fail("venues.json file missing")
        
        with open(venues_json_path, 'r') as f:
            json_data = json.load(f)
        
        db_count = Venue.query.count()
        json_count = len(json_data.get('venues', {}))
        
        self.assertEqual(db_count, json_count,
                        f"Database has {db_count} venues but JSON has {json_count}")
    
    def test_api_endpoints_working(self):
        """Test that critical API endpoints return valid responses"""
        endpoints = [
            '/api/stats',
            '/api/cities',
            '/api/venues?city_id=1'
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f'http://localhost:5001{endpoint}', timeout=5)
                self.assertEqual(response.status_code, 200,
                               f"Endpoint {endpoint} returned {response.status_code}")
                
                # Test that response is valid JSON
                data = response.json()
                self.assertIsInstance(data, (dict, list),
                                    f"Endpoint {endpoint} didn't return valid JSON")
                
            except requests.exceptions.RequestException:
                self.fail(f"Could not connect to endpoint {endpoint} - is server running?")

def run_tests():
    """Run all venue data tests"""
    print("🧪 RUNNING AUTOMATED VENUE DATA TESTS")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(VenueDataTests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Tests passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Tests failed: {len(result.failures)}")
    print(f"💥 Test errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, failure in result.failures:
            print(f"   - {test}: {failure.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n💥 ERRORS:")
        for test, error in result.errors:
            print(f"   - {test}: {error.split('Exception:')[-1].strip()}")
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
