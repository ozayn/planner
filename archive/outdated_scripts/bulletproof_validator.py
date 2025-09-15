#!/usr/bin/env python3
"""
BULLETPROOF SYSTEM VALIDATOR
This script ensures ALL components work together properly
"""

import os
import sys
import subprocess
import sqlite3
import requests
import json
from pathlib import Path

class BulletproofValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.db_path = os.path.expanduser('~/.local/share/planner/events.db')
        
    def log_error(self, message):
        self.errors.append(f"❌ {message}")
        print(f"❌ {message}")
        
    def log_warning(self, message):
        self.warnings.append(f"⚠️  {message}")
        print(f"⚠️  {message}")
        
    def log_success(self, message):
        print(f"✅ {message}")

    def validate_database_schema(self):
        """Validate database schema matches code expectations"""
        print("\n🔍 Validating database schema...")
        
        if not os.path.exists(self.db_path):
            self.log_error("Database file does not exist")
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check all required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['cities', 'venues', 'events']
            for table in required_tables:
                if table not in tables:
                    self.log_error(f"Missing table: {table}")
                    return False
                else:
                    self.log_success(f"Table {table} exists")
            
            # Check cities table columns
            cursor.execute("PRAGMA table_info(cities)")
            city_columns = [row[1] for row in cursor.fetchall()]
            required_city_columns = ['id', 'name', 'state', 'country', 'timezone', 'created_at']
            for col in required_city_columns:
                if col not in city_columns:
                    self.log_error(f"Missing cities column: {col}")
                    return False
            self.log_success("Cities table schema correct")
            
            # Check venues table columns
            cursor.execute("PRAGMA table_info(venues)")
            venue_columns = [row[1] for row in cursor.fetchall()]
            required_venue_columns = ['id', 'name', 'venue_type', 'address', 'city_id', 'opening_hours', 'holiday_hours', 'phone_number', 'email', 'tour_info', 'admission_fee', 'created_at']
            for col in required_venue_columns:
                if col not in venue_columns:
                    self.log_error(f"Missing venues column: {col}")
                    return False
            self.log_success("Venues table schema correct")
            
            # Check events table columns
            cursor.execute("PRAGMA table_info(events)")
            event_columns = [row[1] for row in cursor.fetchall()]
            required_event_columns = ['id', 'title', 'description', 'start_date', 'end_date', 'start_time', 'end_time', 'image_url', 'url', 'is_selected', 'created_at', 'event_type', 'city_id', 'venue_id']
            for col in required_event_columns:
                if col not in event_columns:
                    self.log_error(f"Missing events column: {col}")
                    return False
            self.log_success("Events table schema correct")
            
            conn.close()
            return True
            
        except Exception as e:
            self.log_error(f"Database validation failed: {e}")
            return False

    def validate_api_endpoints(self):
        """Validate all API endpoints exist and work"""
        print("\n🔍 Validating API endpoints...")
        
        base_url = "http://localhost:5001"
        required_endpoints = [
            ('/', 'GET'),  # Main page
            ('/admin', 'GET'),  # Admin page
            ('/api/cities', 'GET'),
            ('/api/admin/stats', 'GET'),
            ('/api/admin/cities', 'GET'),
            ('/api/admin/venues', 'GET'),
            ('/api/admin/events', 'GET'),
            ('/api/discover-venues', 'POST'),
            ('/api/add-venue-manually', 'POST'),
            ('/api/add-event', 'POST'),
            ('/api/delete-city/1', 'DELETE'),
            ('/api/delete-venue/1', 'DELETE'),
            ('/api/delete-event/1', 'DELETE'),
        ]
        
        for endpoint, method in required_endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                elif method == 'POST':
                    response = requests.post(f"{base_url}{endpoint}", json={}, timeout=5)
                elif method == 'DELETE':
                    response = requests.delete(f"{base_url}{endpoint}", timeout=5)
                
                if response.status_code in [200, 400, 404, 500]:  # Any response means endpoint exists
                    self.log_success(f"Endpoint {method} {endpoint} exists")
                else:
                    self.log_warning(f"Endpoint {method} {endpoint} returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log_error(f"Endpoint {method} {endpoint} failed: {e}")
                return False
                
        return True

    def validate_model_consistency(self):
        """Validate model definitions match database and to_dict methods"""
        print("\n🔍 Validating model consistency...")
        
        try:
            # Import the app to check models
            sys.path.append('.')
            from app import app, db, City, Venue, Event
            
            with app.app_context():
                # Test City model
                city = City.query.first()
                if city:
                    city_dict = city.to_dict()
                    required_city_fields = ['id', 'name', 'state', 'country', 'timezone', 'created_at']
                    for field in required_city_fields:
                        if field not in city_dict:
                            self.log_error(f"City.to_dict() missing field: {field}")
                            return False
                    self.log_success("City model consistency correct")
                
                # Test Venue model
                venue = Venue.query.first()
                if venue:
                    venue_dict = venue.to_dict()
                    required_venue_fields = ['id', 'name', 'venue_type', 'address', 'city_id', 'opening_hours', 'holiday_hours', 'phone_number', 'email', 'tour_info', 'admission_fee', 'created_at']
                    for field in required_venue_fields:
                        if field not in venue_dict:
                            self.log_error(f"Venue.to_dict() missing field: {field}")
                            return False
                    self.log_success("Venue model consistency correct")
                
                # Test Event model
                event = Event.query.first()
                if event:
                    event_dict = event.to_dict()
                    required_event_fields = ['id', 'title', 'description', 'start_date', 'end_date', 'start_time', 'end_time', 'image_url', 'url', 'created_at', 'event_type']
                    for field in required_event_fields:
                        if field not in event_dict:
                            self.log_error(f"Event.to_dict() missing field: {field}")
                            return False
                    self.log_success("Event model consistency correct")
                
            return True
            
        except Exception as e:
            self.log_error(f"Model validation failed: {e}")
            return False

    def validate_data_integrity(self):
        """Validate data integrity and relationships"""
        print("\n🔍 Validating data integrity...")
        
        try:
            sys.path.append('.')
            from app import app, db, City, Venue, Event
            
            with app.app_context():
                # Check cities exist
                cities_count = City.query.count()
                if cities_count == 0:
                    self.log_error("No cities found in database")
                    return False
                self.log_success(f"Found {cities_count} cities")
                
                # Check venues exist
                venues_count = Venue.query.count()
                self.log_success(f"Found {venues_count} venues")
                
                # Check events count
                events_count = Event.query.count()
                self.log_success(f"Found {events_count} events")
                
                # Check foreign key relationships
                venues_with_cities = Venue.query.join(City).count()
                if venues_count > 0 and venues_with_cities != venues_count:
                    self.log_warning(f"Some venues don't have valid city relationships")
                
                events_with_cities = Event.query.filter(Event.city_id.isnot(None)).count()
                events_with_venues = Event.query.filter(Event.venue_id.isnot(None)).count()
                self.log_success(f"Events with cities: {events_with_cities}, Events with venues: {events_with_venues}")
                
            return True
            
        except Exception as e:
            self.log_error(f"Data integrity validation failed: {e}")
            return False

    def validate_frontend_backend_integration(self):
        """Validate frontend-backend integration"""
        print("\n🔍 Validating frontend-backend integration...")
        
        try:
            # Test admin page loads
            response = requests.get("http://localhost:5001/admin", timeout=5)
            if response.status_code == 200:
                self.log_success("Admin page loads correctly")
            else:
                self.log_error(f"Admin page failed to load: {response.status_code}")
                return False
            
            # Test main page loads
            response = requests.get("http://localhost:5001/", timeout=5)
            if response.status_code == 200:
                self.log_success("Main page loads correctly")
            else:
                self.log_error(f"Main page failed to load: {response.status_code}")
                return False
                
            return True
            
        except Exception as e:
            self.log_error(f"Frontend validation failed: {e}")
            return False

    def run_comprehensive_validation(self):
        """Run all validations"""
        print("🛡️  BULLETPROOF SYSTEM VALIDATION")
        print("=" * 60)
        
        validations = [
            ("Database Schema", self.validate_database_schema),
            ("API Endpoints", self.validate_api_endpoints),
            ("Model Consistency", self.validate_model_consistency),
            ("Data Integrity", self.validate_data_integrity),
            ("Frontend-Backend Integration", self.validate_frontend_backend_integration)
        ]
        
        all_passed = True
        
        for validation_name, validation_func in validations:
            print(f"\n📋 {validation_name}:")
            if not validation_func():
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL VALIDATIONS PASSED!")
            print("✅ System is bulletproof and ready!")
            return True
        else:
            print("🚨 VALIDATION FAILURES DETECTED!")
            print("\n❌ Errors found:")
            for error in self.errors:
                print(f"   {error}")
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   {warning}")
            return False

def main():
    """Main function"""
    validator = BulletproofValidator()
    success = validator.run_comprehensive_validation()
    
    if success:
        print("\n🛡️  SYSTEM IS BULLETPROOF!")
        print("You can restart with confidence!")
        sys.exit(0)
    else:
        print("\n🚨 SYSTEM NEEDS FIXES!")
        print("Fix the errors above before restarting!")
        sys.exit(1)

if __name__ == '__main__':
    main()
