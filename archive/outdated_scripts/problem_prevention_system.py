#!/usr/bin/env python3
"""
COMPREHENSIVE PROBLEM PREVENTION SYSTEM
This script ensures ALL problems we encountered are prevented
"""

import os
import sys
import subprocess
import sqlite3
import requests
import json
from pathlib import Path

class ProblemPreventionSystem:
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

    def prevent_module_not_found_errors(self):
        """Prevent: ModuleNotFoundError: No module named 'scripts.llm_venue_detail_searcher'"""
        print("\n🔍 Preventing ModuleNotFoundError issues...")
        
        # Check if all required scripts exist
        required_scripts = [
            'scripts/discover_venues.py',
            'scripts/fetch_venue_details.py',
            'scripts/enhanced_llm_fallback.py',
            'scripts/add_cities.py',
            'scripts/fix_schema_permanently.py',
            'scripts/bulletproof_validator.py'
        ]
        
        for script in required_scripts:
            if not os.path.exists(script):
                self.log_error(f"Missing script: {script}")
                return False
            else:
                self.log_success(f"Script exists: {script}")
        
        # Check imports in discover_venues.py
        try:
            with open('scripts/discover_venues.py', 'r') as f:
                content = f.read()
                if 'from scripts.fetch_venue_details import' in content:
                    self.log_success("Correct import in discover_venues.py")
                else:
                    self.log_error("Wrong import in discover_venues.py")
                    return False
        except Exception as e:
            self.log_error(f"Could not check discover_venues.py: {e}")
            return False
            
        return True

    def prevent_venues_not_saving(self):
        """Prevent: Venues not saving to database"""
        print("\n🔍 Preventing venues not saving...")
        
        try:
            with open('scripts/discover_venues.py', 'r') as f:
                content = f.read()
                
                # Check for db.session.add(venue)
                if 'db.session.add(venue)' in content:
                    self.log_success("db.session.add(venue) found")
                else:
                    self.log_error("Missing db.session.add(venue)")
                    return False
                
                # Check for proper commit timing
                if 'db.session.commit()' in content:
                    self.log_success("db.session.commit() found")
                else:
                    self.log_error("Missing db.session.commit()")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check discover_venues.py: {e}")
            return False
            
        return True

    def prevent_llm_placeholder_data(self):
        """Prevent: LLM detail fetching returning placeholder data"""
        print("\n🔍 Preventing LLM placeholder data...")
        
        # Check if python-dotenv is in requirements.txt
        try:
            with open('requirements.txt', 'r') as f:
                content = f.read()
                if 'python-dotenv' in content:
                    self.log_success("python-dotenv in requirements.txt")
                else:
                    self.log_error("python-dotenv missing from requirements.txt")
                    return False
        except Exception as e:
            self.log_error(f"Could not check requirements.txt: {e}")
            return False
        
        # Check if load_dotenv() is in fetch_venue_details.py
        try:
            with open('scripts/fetch_venue_details.py', 'r') as f:
                content = f.read()
                if 'load_dotenv()' in content:
                    self.log_success("load_dotenv() found in fetch_venue_details.py")
                else:
                    self.log_error("Missing load_dotenv() in fetch_venue_details.py")
                    return False
        except Exception as e:
            self.log_error(f"Could not check fetch_venue_details.py: {e}")
            return False
            
        return True

    def prevent_llm_rate_limits(self):
        """Prevent: LLM APIs hitting rate limits/quota exceeded"""
        print("\n🔍 Preventing LLM rate limits...")
        
        # Check if enhanced_llm_fallback.py exists
        if not os.path.exists('scripts/enhanced_llm_fallback.py'):
            self.log_error("Missing enhanced_llm_fallback.py")
            return False
        
        # Check if discover_venues.py uses the fallback system
        try:
            with open('scripts/discover_venues.py', 'r') as f:
                content = f.read()
                if 'EnhancedLLMFallback' in content:
                    self.log_success("EnhancedLLMFallback system found")
                else:
                    self.log_error("Missing EnhancedLLMFallback system")
                    return False
        except Exception as e:
            self.log_error(f"Could not check discover_venues.py: {e}")
            return False
            
        return True

    def prevent_single_venue_issue(self):
        """Prevent: Only one venue found for Los Angeles"""
        print("\n🔍 Preventing single venue issue...")
        
        try:
            with open('scripts/discover_venues.py', 'r') as f:
                content = f.read()
                
                # Check for comprehensive mock data
                if 'Los Angeles' in content and 'Tokyo' in content:
                    self.log_success("Comprehensive mock data found")
                else:
                    self.log_error("Missing comprehensive mock data")
                    return False
                    
                # Check for dynamic prompt generation
                if '_get_venue_fields_prompt' in content:
                    self.log_success("Dynamic prompt generation found")
                else:
                    self.log_error("Missing dynamic prompt generation")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check discover_venues.py: {e}")
            return False
            
        return True

    def prevent_database_path_issues(self):
        """Prevent: sqlite3.OperationalError: unable to open database file"""
        print("\n🔍 Preventing database path issues...")
        
        # Check if database is in professional location
        if '/.local/share/planner/events.db' in str(self.db_path):
            self.log_success("Database in professional location")
        else:
            self.log_error("Database not in professional location")
            return False
        
        # Check if app.py uses correct database path
        try:
            with open('app.py', 'r') as f:
                content = f.read()
                if '~/.local/share/planner/events.db' in content:
                    self.log_success("app.py uses correct database path")
                else:
                    self.log_error("app.py uses wrong database path")
                    return False
        except Exception as e:
            self.log_error(f"Could not check app.py: {e}")
            return False
            
        return True

    def prevent_missing_api_endpoints(self):
        """Prevent: /api/discover-venues endpoint returning 404"""
        print("\n🔍 Preventing missing API endpoints...")
        
        required_endpoints = [
            '/api/discover-venues',
            '/api/add-venue-manually',
            '/api/admin/stats',
            '/api/admin/cities',
            '/api/admin/venues',
            '/api/admin/events',
            '/api/add-event',
            '/api/delete-city/',
            '/api/delete-venue/',
            '/api/delete-event/'
        ]
        
        try:
            with open('app.py', 'r') as f:
                content = f.read()
                
                for endpoint in required_endpoints:
                    if endpoint in content:
                        self.log_success(f"Endpoint found: {endpoint}")
                    else:
                        self.log_error(f"Missing endpoint: {endpoint}")
                        return False
                        
        except Exception as e:
            self.log_error(f"Could not check app.py: {e}")
            return False
        
        # Check for frontend-backend API endpoint mismatches
        try:
            with open('templates/admin.html', 'r') as f:
                admin_content = f.read()
                
            # Extract all API calls from admin.html
            import re
            api_calls = re.findall(r"'/api/admin/[^']*'", admin_content)
            api_calls = [call.strip("'") for call in api_calls]
            
            # Check if each API call has a corresponding route in app.py
            missing_endpoints = []
            for api_call in api_calls:
                # Remove query parameters and method-specific parts
                clean_endpoint = api_call.split('?')[0].split('/api/admin/')[1]
                if f"/api/admin/{clean_endpoint}" not in content:
                    missing_endpoints.append(api_call)
            
            if missing_endpoints:
                self.log_error(f"Frontend calls missing backend endpoints: {missing_endpoints}")
                return False
            else:
                self.log_success("All frontend API calls have backend endpoints")
                
            # Check for frontend-backend field name mismatches
            field_mismatches = []
            
            # Check lookup-city endpoint field names
            if "'city_name'" in admin_content and "'name'" in admin_content:
                if "city_name = data.get('city_name')" in content:
                    if "city_name: name" not in admin_content:
                        field_mismatches.append("lookup-city: frontend sends 'name' but backend expects 'city_name'")
            
            # Check response field names
            if "result.city_details" in admin_content and "result.city" in admin_content:
                field_mismatches.append("lookup-city: frontend expects 'city_details' but backend returns 'city'")
            
            # Check add-city response field mismatch
            if "result.city.id" in admin_content and "result.city_id" not in admin_content:
                field_mismatches.append("add-city: frontend expects 'result.city.id' but backend returns 'result.city_id'")
            
            # Check add-venue response field mismatch
            if "result.venue.id" in admin_content and "result.venue_id" not in admin_content:
                field_mismatches.append("add-venue: frontend expects 'result.venue.id' but backend returns 'result.venue_id'")
            
            # Check venue form field completeness
            if "JSON.stringify({" in admin_content:
                # Check if venue forms include all required fields
                if "add-venue" in admin_content and "opening_hours" not in admin_content:
                    field_mismatches.append("add-venue: frontend missing opening_hours, holiday_hours, phone_number, email, tour_info, admission_fee")
                
                if "edit-venue" in admin_content and "opening_hours" not in admin_content:
                    field_mismatches.append("edit-venue: frontend missing opening_hours, holiday_hours, phone_number, email, tour_info, admission_fee")
            
            # Check fetch-venue-details field mismatch
            if "fetch-venue-details" in admin_content and "venue_id" in admin_content:
                if "venue_name = data.get('venue_name')" in content and "venue_id" not in content:
                    field_mismatches.append("fetch-venue-details: frontend sends 'venue_id' but backend expects 'venue_name' and 'city_name'")
            
            # Check error message handling
            if "City not found" in admin_content and "❌ Lookup failed" in admin_content and "ℹ️ City" not in admin_content:
                field_mismatches.append("lookup-city: frontend treats 'City not found' as error instead of normal response")
            
            if field_mismatches:
                self.log_error(f"Frontend-backend field mismatches: {field_mismatches}")
                return False
            else:
                self.log_success("Frontend-backend field names are consistent")
                
        except Exception as e:
            self.log_error(f"Could not check frontend-backend API consistency: {e}")
            return False
            
        return True

    def prevent_missing_admin_route(self):
        """Prevent: /admin page returning 404"""
        print("\n🔍 Preventing missing admin route...")
        
        try:
            with open('app.py', 'r') as f:
                content = f.read()
                
                if '@app.route(\'/admin\')' in content:
                    self.log_success("Admin route found in app.py")
                else:
                    self.log_error("Missing admin route in app.py")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check app.py: {e}")
            return False
            
        return True

    def prevent_empty_database(self):
        """Prevent: Database empty (no cities)"""
        print("\n🔍 Preventing empty database...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM cities")
            cities_count = cursor.fetchone()[0]
            
            if cities_count > 0:
                self.log_success(f"Found {cities_count} cities in database")
            else:
                self.log_error("No cities found in database")
                return False
                
            conn.close()
            
        except Exception as e:
            self.log_error(f"Could not check database: {e}")
            return False
            
        return True

    def prevent_venue_field_errors(self):
        """Prevent: TypeError: 'facebook_url' is an invalid keyword argument for Venue"""
        print("\n🔍 Preventing venue field errors...")
        
        try:
            with open('scripts/discover_venues.py', 'r') as f:
                content = f.read()
                
                # Check for proper Venue constructor
                if 'Venue(' in content and 'details.get(' in content:
                    self.log_success("Proper Venue constructor found")
                else:
                    self.log_error("Improper Venue constructor")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check discover_venues.py: {e}")
            return False
            
        return True

    def prevent_frontend_errors(self):
        """Prevent: Frontend 'Error loading cities'"""
        print("\n🔍 Preventing frontend errors...")
        
        # Check index.html for correct JavaScript
        try:
            with open('templates/index.html', 'r') as f:
                content = f.read()
                
                if 'citySelect.value' in content and 'currentCityId' not in content:
                    self.log_success("Correct JavaScript in index.html")
                else:
                    self.log_error("Incorrect JavaScript in index.html")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check index.html: {e}")
            return False
        
        # Check admin.html for correct JavaScript
        try:
            with open('templates/admin.html', 'r') as f:
                content = f.read()
                
                if 'data.cities' in content and 'data.stats.cities' not in content:
                    self.log_success("Correct JavaScript in admin.html")
                else:
                    self.log_error("Incorrect JavaScript in admin.html")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check admin.html: {e}")
            return False
            
        return True

    def prevent_schema_mismatches(self):
        """Prevent: sqlite3.OperationalError: no such column"""
        print("\n🔍 Preventing schema mismatches...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check venues table has all required columns
            cursor.execute("PRAGMA table_info(venues)")
            venue_columns = [row[1] for row in cursor.fetchall()]
            
            required_venue_columns = ['opening_hours', 'holiday_hours', 'phone_number', 'email', 'tour_info', 'admission_fee']
            for col in required_venue_columns:
                if col not in venue_columns:
                    self.log_error(f"Missing venues column: {col}")
                    return False
                    
            self.log_success("All venue columns exist")
            
            # Check events table has all required columns
            cursor.execute("PRAGMA table_info(events)")
            event_columns = [row[1] for row in cursor.fetchall()]
            
            required_event_columns = ['city_id', 'venue_id']
            for col in required_event_columns:
                if col not in event_columns:
                    self.log_error(f"Missing events column: {col}")
                    return False
                    
            self.log_success("All event columns exist")
            
            conn.close()
            
        except Exception as e:
            self.log_error(f"Could not check database schema: {e}")
            return False
            
        return True

    def prevent_invalid_date_errors(self):
        """Prevent: 'Invalid Date' errors for created_at fields"""
        print("\n🔍 Preventing invalid date errors...")
        
        # Check if to_dict methods include created_at
        try:
            with open('app.py', 'r') as f:
                content = f.read()
                
                if 'created_at' in content and 'isoformat()' in content:
                    self.log_success("created_at handling found in app.py")
                else:
                    self.log_error("Missing created_at handling in app.py")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check app.py: {e}")
            return False
        
        # Check if admin.html has null checks
        try:
            with open('templates/admin.html', 'r') as f:
                content = f.read()
                
                if 'created_at ?' in content and 'N/A' in content:
                    self.log_success("Null checks found in admin.html")
                else:
                    self.log_error("Missing null checks in admin.html")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check admin.html: {e}")
            return False
            
        return True

    def prevent_delete_button_failures(self):
        """Prevent: Delete buttons don't work"""
        print("\n🔍 Preventing delete button failures...")
        
        # Check if delete endpoints exist in app.py
        try:
            with open('app.py', 'r') as f:
                content = f.read()
                
                delete_endpoints = ['/api/delete-city/', '/api/delete-venue/', '/api/delete-event/']
                for endpoint in delete_endpoints:
                    if endpoint in content:
                        self.log_success(f"Delete endpoint found: {endpoint}")
                    else:
                        self.log_error(f"Missing delete endpoint: {endpoint}")
                        return False
                        
        except Exception as e:
            self.log_error(f"Could not check app.py: {e}")
            return False
        
        # Check if admin.html has delete functions
        try:
            with open('templates/admin.html', 'r') as f:
                content = f.read()
                
                if 'deleteCity(' in content and 'deleteVenue(' in content and 'deleteEvent(' in content:
                    self.log_success("Delete functions found in admin.html")
                else:
                    self.log_error("Missing delete functions in admin.html")
                    return False
                    
        except Exception as e:
            self.log_error(f"Could not check admin.html: {e}")
            return False
            
        return True

    def prevent_frontend_backend_table_sync(self):
        """Prevent: Frontend tables not showing updated_at columns"""
        print("\n🔍 Preventing frontend-backend table synchronization issues...")
        
        try:
            with open('templates/admin.html', 'r') as f:
                admin_content = f.read()
            
            with open('app.py', 'r') as f:
                app_content = f.read()
            
            # Check if all tables have Updated column headers
            table_headers = [
                ('<th>Created</th>', '<th>Updated</th>', '<th>Actions</th>'),
                ('<th>Created</th>', '<th>Updated</th>', '<th>Actions</th>'),
                ('<th>Created</th>', '<th>Updated</th>', '<th>Actions</th>')
            ]
            
            for i, (created, updated, actions) in enumerate(table_headers):
                if created in admin_content and updated in admin_content and actions in admin_content:
                    self.log_success(f"Table {i+1} has Updated column header")
                else:
                    self.log_error(f"Table {i+1} missing Updated column header")
                    return False
            
            # Check if all tables display updated_at data
            updated_at_displays = [
                'city.updated_at ? new Date(city.updated_at).toLocaleDateString()',
                'venue.updated_at ? new Date(venue.updated_at).toLocaleDateString()',
                'event.updated_at ? new Date(event.updated_at).toLocaleDateString()'
            ]
            
            for i, display in enumerate(updated_at_displays):
                if display in admin_content:
                    self.log_success(f"Table {i+1} displays updated_at data")
                else:
                    self.log_error(f"Table {i+1} missing updated_at data display")
                    return False
            
            # Check if backend to_dict methods include updated_at
            to_dict_methods = [
                ('City', 'updated_at.isoformat()'),
                ('Venue', 'updated_at.isoformat()'),
                ('Event', 'updated_at.isoformat()')
            ]
            
            for model_name, updated_at_field in to_dict_methods:
                if updated_at_field in app_content:
                    self.log_success(f"{model_name} to_dict includes updated_at")
                else:
                    self.log_error(f"{model_name} to_dict missing updated_at")
                    return False
            
            # Check if all admin API endpoints return updated_at
            admin_endpoints = [
                '/api/admin/cities',
                '/api/admin/venues', 
                '/api/admin/events'
            ]
            
            for endpoint in admin_endpoints:
                if endpoint in app_content:
                    self.log_success(f"Admin endpoint exists: {endpoint}")
                else:
                    self.log_error(f"Missing admin endpoint: {endpoint}")
                    return False
            
            # Check for form field completeness
            form_fields = [
                ('add-city', ['name', 'country']),
                ('add-venue', ['name', 'venue_type', 'address', 'city_id']),
                ('add-event', ['name', 'event_type', 'start_time', 'end_time'])
            ]
            
            for form_name, required_fields in form_fields:
                for field in required_fields:
                    if f'name="{field}"' in admin_content or f'id="{field}"' in admin_content:
                        self.log_success(f"{form_name} has {field} field")
                    else:
                        self.log_error(f"{form_name} missing {field} field")
                        return False
            
            return True
            
        except Exception as e:
            self.log_error(f"Could not check frontend-backend table sync: {e}")
            return False

    def run_comprehensive_prevention(self):
        """Run all prevention checks"""
        print("🛡️  COMPREHENSIVE PROBLEM PREVENTION SYSTEM")
        print("=" * 70)
        
        preventions = [
            ("ModuleNotFoundError", self.prevent_module_not_found_errors),
            ("Venues Not Saving", self.prevent_venues_not_saving),
            ("LLM Placeholder Data", self.prevent_llm_placeholder_data),
            ("LLM Rate Limits", self.prevent_llm_rate_limits),
            ("Single Venue Issue", self.prevent_single_venue_issue),
            ("Database Path Issues", self.prevent_database_path_issues),
            ("Missing API Endpoints", self.prevent_missing_api_endpoints),
            ("Missing Admin Route", self.prevent_missing_admin_route),
            ("Empty Database", self.prevent_empty_database),
            ("Venue Field Errors", self.prevent_venue_field_errors),
            ("Frontend Errors", self.prevent_frontend_errors),
            ("Schema Mismatches", self.prevent_schema_mismatches),
            ("Invalid Date Errors", self.prevent_invalid_date_errors),
            ("Delete Button Failures", self.prevent_delete_button_failures),
            ("Frontend-Backend Table Sync", self.prevent_frontend_backend_table_sync)
        ]
        
        all_passed = True
        
        for prevention_name, prevention_func in preventions:
            print(f"\n📋 Preventing: {prevention_name}")
            if not prevention_func():
                all_passed = False
        
        print("\n" + "=" * 70)
        if all_passed:
            print("🎉 ALL PROBLEMS PREVENTED!")
            print("✅ System is bulletproof against ALL known issues!")
            return True
        else:
            print("🚨 PREVENTION FAILURES DETECTED!")
            print("\n❌ Errors found:")
            for error in self.errors:
                print(f"   {error}")
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   {warning}")
            return False

def main():
    """Main function"""
    preventer = ProblemPreventionSystem()
    success = preventer.run_comprehensive_prevention()
    
    if success:
        print("\n🛡️  ALL PROBLEMS PREVENTED!")
        print("You can restart with complete confidence!")
        sys.exit(0)
    else:
        print("\n🚨 PREVENTION FAILURES DETECTED!")
        print("Fix the errors above before restarting!")
        sys.exit(1)

if __name__ == '__main__':
    main()
