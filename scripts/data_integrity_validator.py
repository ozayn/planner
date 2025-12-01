#!/usr/bin/env python3
"""
Comprehensive Data Integrity Validator
Prevents common data issues and validates venue data consistency
"""

import os
import sys
import json
import requests
from datetime import datetime
sys.path.append('.')

from app import app, db, Venue, City, Source, Event

class DataIntegrityValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.fixes_applied = []
        
    def log_error(self, message):
        self.errors.append(message)
        print(f"❌ ERROR: {message}")
    
    def log_warning(self, message):
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")
    
    def log_fix(self, message):
        self.fixes_applied.append(message)
        print(f"🔧 FIXED: {message}")
    
    def validate_image_urls(self):
        """Validate all venue image URLs"""
        print("\n🖼️  Validating venue image URLs...")
        
        venues = Venue.query.all()
        invalid_images = []
        fake_images = []
        missing_images = []
        
        for venue in venues:
            if not venue.image_url:
                missing_images.append(venue.name)
                continue
            
            # Check if it's a fake photo reference (my mistake pattern)
            if isinstance(venue.image_url, str) and venue.image_url.startswith('AciIO2') and len(venue.image_url) == 200:
                fake_images.append(venue.name)
                continue
            
            # Check if it's valid JSON
            if isinstance(venue.image_url, str) and venue.image_url.startswith('{'):
                try:
                    photo_data = json.loads(venue.image_url)
                    if not isinstance(photo_data, dict) or 'photo_reference' not in photo_data:
                        invalid_images.append(venue.name)
                except json.JSONDecodeError:
                    invalid_images.append(venue.name)
        
        if missing_images:
            self.log_warning(f"{len(missing_images)} venues missing image URLs: {missing_images[:5]}...")
        
        if fake_images:
            self.log_error(f"{len(fake_images)} venues have fake image URLs: {fake_images}")
        
        if invalid_images:
            self.log_error(f"{len(invalid_images)} venues have invalid image JSON: {invalid_images}")
        
        return len(fake_images) == 0 and len(invalid_images) == 0
    
    def validate_social_media_data(self):
        """Validate social media data completeness"""
        print("\n📱 Validating social media data...")
        
        venues = Venue.query.all()
        missing_social_media = []
        
        for venue in venues:
            has_social = any([
                venue.instagram_url,
                venue.facebook_url, 
                venue.twitter_url,
                venue.youtube_url,
                venue.tiktok_url
            ])
            
            if not has_social and venue.venue_type in ['museum', 'arts_center', 'embassy']:
                missing_social_media.append(venue.name)
        
        if missing_social_media:
            self.log_warning(f"{len(missing_social_media)} major venues missing social media: {missing_social_media[:5]}...")
        
        return len(missing_social_media) < 10  # Allow some venues without social media
    
    def validate_venue_types(self):
        """Validate venue type consistency"""
        print("\n🏛️  Validating venue types...")
        
        venues = Venue.query.all()
        venue_types = set()
        inconsistent_types = []
        
        for venue in venues:
            if venue.venue_type:
                venue_types.add(venue.venue_type)
                
                # Check for common inconsistencies
                if venue.venue_type != venue.venue_type.lower():
                    inconsistent_types.append(f"{venue.name}: '{venue.venue_type}' should be lowercase")
        
        print(f"📊 Found {len(venue_types)} unique venue types: {sorted(venue_types)}")
        
        if inconsistent_types:
            self.log_error(f"Venue type case inconsistencies: {inconsistent_types}")
        
        return len(inconsistent_types) == 0
    
    def validate_json_sync(self):
        """Validate that JSON files are in sync with database"""
        print("\n🔄 Validating JSON synchronization...")
        
        # Check venues.json
        venues_json_path = 'data/venues.json'
        if not os.path.exists(venues_json_path):
            self.log_error("venues.json file missing")
            return False
        
        try:
            with open(venues_json_path, 'r') as f:
                venues_json = json.load(f)
            
            db_venue_count = Venue.query.count()
            json_venue_count = len(venues_json.get('venues', {}))
            
            if db_venue_count != json_venue_count:
                self.log_error(f"Venue count mismatch: DB={db_venue_count}, JSON={json_venue_count}")
                return False
            
            # Check if social media fields are included
            sample_venue = list(venues_json.get('venues', {}).values())[0]
            required_fields = ['instagram_url', 'facebook_url', 'twitter_url']
            missing_fields = [field for field in required_fields if field not in sample_venue]
            
            if missing_fields:
                self.log_error(f"venues.json missing social media fields: {missing_fields}")
                return False
            
            print(f"✅ venues.json is properly synchronized ({json_venue_count} venues)")
            return True
            
        except Exception as e:
            self.log_error(f"Error validating venues.json: {e}")
            return False
    
    def validate_api_endpoints(self):
        """Validate that critical API endpoints are working"""
        print("\n🔗 Validating API endpoints...")
        
        endpoints_to_test = [
            ('/api/stats', 'Public stats endpoint'),
            ('/api/cities', 'Cities endpoint'),
            ('/api/venues?city_id=1', 'Venues endpoint'),
        ]
        
        failed_endpoints = []
        
        for endpoint, description in endpoints_to_test:
            try:
                response = requests.get(f'http://localhost:5001{endpoint}', timeout=5)
                if response.status_code == 200:
                    print(f"✅ {description}: OK")
                else:
                    failed_endpoints.append(f"{description} returned {response.status_code}")
            except Exception as e:
                failed_endpoints.append(f"{description} failed: {e}")
        
        if failed_endpoints:
            for failure in failed_endpoints:
                self.log_error(f"API endpoint failure: {failure}")
        
        return len(failed_endpoints) == 0
    
    def check_backup_system(self):
        """Validate backup system is working"""
        print("\n💾 Validating backup system...")
        
        backup_dir = 'data/backups'
        if not os.path.exists(backup_dir):
            self.log_error("Backup directory missing")
            return False
        
        # Check for recent backups
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.backup.20250919')]
        
        if len(backup_files) < 1:
            self.log_warning("No recent backups found for today")
        else:
            print(f"✅ Found {len(backup_files)} backup files for today")
        
        return True
    
    def check_duplicates(self):
        """Check for duplicate cities, venues, and events"""
        print("\n🔍 Checking for duplicates...")
        
        from collections import defaultdict
        
        duplicates_found = False
        
        # Check cities
        cities = City.query.all()
        city_keys = defaultdict(list)
        for city in cities:
            key = (
                city.name.lower().strip(),
                (city.state or '').lower().strip(),
                city.country.lower().strip()
            )
            city_keys[key].append(city)
        
        city_duplicates = {k: v for k, v in city_keys.items() if len(v) > 1}
        if city_duplicates:
            duplicates_found = True
            for key, cities_list in city_duplicates.items():
                name, state, country = key
                self.log_error(f"Duplicate city: {name.title()}, {state.title() if state else 'N/A'}, {country.title()} (IDs: {[c.id for c in cities_list]})")
        
        # Check venues
        venues = Venue.query.all()
        venue_keys = defaultdict(list)
        for venue in venues:
            key = (venue.name.lower().strip(), venue.city_id)
            venue_keys[key].append(venue)
        
        venue_duplicates = {k: v for k, v in venue_keys.items() if len(v) > 1}
        if venue_duplicates:
            duplicates_found = True
            for key, venues_list in venue_duplicates.items():
                name, city_id = key
                self.log_error(f"Duplicate venue: {name.title()} in city_id {city_id} (IDs: {[v.id for v in venues_list]})")
        
        if not duplicates_found:
            print("✅ No duplicates found")
        
        return not duplicates_found
    
    def run_full_validation(self):
        """Run all validation checks"""
        print("🛡️  RUNNING COMPREHENSIVE DATA INTEGRITY VALIDATION")
        print("=" * 60)
        
        with app.app_context():
            validations = [
                ("Duplicates", self.check_duplicates),
                ("Image URLs", self.validate_image_urls),
                ("Social Media Data", self.validate_social_media_data),
                ("Venue Types", self.validate_venue_types),
                ("JSON Synchronization", self.validate_json_sync),
                ("API Endpoints", self.validate_api_endpoints),
                ("Backup System", self.check_backup_system),
            ]
            
            passed = 0
            total = len(validations)
            
            for name, validation_func in validations:
                print(f"\n{'='*20} {name} {'='*20}")
                try:
                    if validation_func():
                        passed += 1
                        print(f"✅ {name}: PASSED")
                    else:
                        print(f"❌ {name}: FAILED")
                except Exception as e:
                    self.log_error(f"{name} validation crashed: {e}")
                    print(f"💥 {name}: CRASHED")
        
        # Final report
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60)
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Errors: {len(self.errors)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"🔧 Fixes Applied: {len(self.fixes_applied)}")
        
        if self.errors:
            print(f"\n❌ ERRORS TO FIX:")
            for error in self.errors:
                print(f"   - {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if self.fixes_applied:
            print(f"\n🔧 FIXES APPLIED:")
            for fix in self.fixes_applied:
                print(f"   - {fix}")
        
        print("\n" + "="*60)
        
        if len(self.errors) == 0:
            print("🎉 ALL VALIDATIONS PASSED! Data integrity is excellent.")
            return True
        else:
            print("🚨 VALIDATION FAILED! Please fix the errors above.")
            return False

def main():
    """Run the data integrity validator"""
    validator = DataIntegrityValidator()
    success = validator.run_full_validation()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
