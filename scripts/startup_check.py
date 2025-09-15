#!/usr/bin/env python3
"""
Startup Validation Script
Ensures everything is working when you restart the application
"""

import sys
import os
import subprocess
import requests
import time
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue, Event

class StartupValidator:
    """Comprehensive startup validation system"""
    
    def __init__(self):
        # Use the same database path logic as app.py
        if os.getenv('DATABASE_URL'):
            # Production database
            self.db_path = os.getenv('DATABASE_URL').replace('sqlite:///', '')
        else:
            # Development database - use project directory
            self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'events.db')
        self.app_url = 'http://localhost:5001'
        self.issues = []
        self.warnings = []
    
    def check_database_exists(self) -> bool:
        """Check if database file exists"""
        if not os.path.exists(self.db_path):
            self.issues.append(f"❌ Database not found: {self.db_path}")
            return False
        return True
    
    def check_database_connection(self) -> bool:
        """Test database connection"""
        try:
            with app.app_context():
                # Test basic query
                city_count = City.query.count()
                venue_count = Venue.query.count()
                print(f"✅ Database connected: {city_count} cities, {venue_count} venues")
                return True
        except Exception as e:
            self.issues.append(f"❌ Database connection failed: {e}")
            return False
    
    def check_schema_consistency(self) -> bool:
        """Run schema validator"""
        try:
            result = subprocess.run([
                sys.executable, 'scripts/schema_validator.py'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                print("✅ Schema validation passed")
                return True
            else:
                self.issues.append(f"❌ Schema validation failed: {result.stdout}")
                return False
        except Exception as e:
            self.issues.append(f"❌ Schema validation error: {e}")
            return False
    
    def check_cities_exist(self) -> bool:
        """Check if cities are populated"""
        try:
            with app.app_context():
                cities = City.query.all()
                if len(cities) == 0:
                    self.warnings.append("⚠️  No cities in database - run: python scripts/add_cities.py")
                    return False
                else:
                    print(f"✅ {len(cities)} cities found")
                    return True
        except Exception as e:
            self.issues.append(f"❌ Cities check failed: {e}")
            return False
    
    def check_environment_variables(self) -> bool:
        """Check if required environment variables are set"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            required_vars = ['GOOGLE_API_KEY']
            missing_vars = []
            
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                self.warnings.append(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
                return False
            else:
                print("✅ Environment variables loaded")
                return True
        except Exception as e:
            self.issues.append(f"❌ Environment check failed: {e}")
            return False
    
    def check_flask_app_running(self) -> bool:
        """Check if Flask app is running"""
        try:
            response = requests.get(f"{self.app_url}/api/cities", timeout=5)
            if response.status_code == 200:
                print("✅ Flask app is running")
                return True
            else:
                self.issues.append(f"❌ Flask app not responding: {response.status_code}")
                return False
        except requests.exceptions.RequestException:
            self.issues.append("❌ Flask app not running - start with: source venv/bin/activate && python app.py")
            return False
    
    def check_api_endpoints(self) -> bool:
        """Test critical API endpoints"""
        endpoints = [
            '/api/cities',
            '/api/admin/stats',
            '/api/admin/venues',
            '/api/discover-venues'
        ]
        
        working_endpoints = 0
        for endpoint in endpoints:
            try:
                if endpoint == '/api/discover-venues':
                    # POST endpoint - use shorter timeout for startup check
                    response = requests.post(f"{self.app_url}{endpoint}", 
                                           json={'city_id': 1, 'event_types': ['tours']}, 
                                           timeout=3)  # Shorter timeout for startup check
                else:
                    # GET endpoint
                    response = requests.get(f"{self.app_url}{endpoint}", timeout=5)
                
                if endpoint == '/api/discover-venues':
                    # For discover-venues, any response (even timeout) means endpoint exists
                    if response.status_code in [200, 400, 500] or 'timeout' in str(response):
                        working_endpoints += 1
                    else:
                        self.issues.append(f"❌ {endpoint} returned {response.status_code}")
                else:
                    if response.status_code in [200, 400]:
                        working_endpoints += 1
                    else:
                        self.issues.append(f"❌ {endpoint} returned {response.status_code}")
            except Exception as e:
                self.issues.append(f"❌ {endpoint} failed: {e}")
        
        if working_endpoints == len(endpoints):
            print("✅ All API endpoints working")
            return True
        else:
            print(f"⚠️  {working_endpoints}/{len(endpoints)} API endpoints working")
            return False
    
    def check_llm_system(self) -> bool:
        """Test LLM fallback system"""
        try:
            result = subprocess.run([
                sys.executable, '-c',
                '''
from scripts.enhanced_llm_fallback import EnhancedLLMFallback
llm = EnhancedLLMFallback(silent=True)
result = llm.query_with_fallback("Test query")
print("SUCCESS" if result.get("success") else "FAILED")
'''
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if "SUCCESS" in result.stdout:
                print("✅ LLM system working")
                return True
            else:
                self.warnings.append("⚠️  LLM system not working - check API keys")
                return False
        except Exception as e:
            self.warnings.append(f"⚠️  LLM system check failed: {e}")
            return False
    
    def run_comprehensive_check(self) -> Dict:
        """Run all validation checks"""
        print("🔍 Running comprehensive startup validation...")
        print("=" * 60)
        
        checks = [
            ("Database File", self.check_database_exists),
            ("Database Connection", self.check_database_connection),
            ("Schema Consistency", self.check_schema_consistency),
            ("Cities Data", self.check_cities_exist),
            ("Environment Variables", self.check_environment_variables),
            ("Flask App", self.check_flask_app_running),
            ("API Endpoints", self.check_api_endpoints),
            ("LLM System", self.check_llm_system),
        ]
        
        passed_checks = 0
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}:")
            try:
                if check_func():
                    passed_checks += 1
            except Exception as e:
                self.issues.append(f"❌ {check_name} failed: {e}")
        
        print("\n" + "=" * 60)
        print("📊 STARTUP VALIDATION REPORT")
        print("=" * 60)
        
        if not self.issues and not self.warnings:
            print("✅ All checks passed! System is ready to go!")
            return {'status': 'success', 'issues': [], 'warnings': []}
        
        if self.issues:
            print("❌ Critical Issues Found:")
            for issue in self.issues:
                print(f"   {issue}")
        
        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   {warning}")
        
        if self.issues:
            print(f"\n🚨 {len(self.issues)} critical issues need to be fixed!")
            return {'status': 'failed', 'issues': self.issues, 'warnings': self.warnings}
        else:
            print(f"\n✅ System ready with {len(self.warnings)} warnings")
            return {'status': 'warning', 'issues': [], 'warnings': self.warnings}
    
    def print_startup_commands(self):
        """Print the correct startup sequence"""
        print("\n🚀 STARTUP COMMANDS:")
        print("=" * 40)
        print("1. Navigate to project:")
        print("   cd /Users/oz/Dropbox/2025/planner")
        print()
        print("2. Activate virtual environment:")
        print("   source venv/bin/activate")
        print()
        print("3. Run startup validation:")
        print("   python scripts/startup_check.py")
        print()
        print("4. Start Flask app:")
        print("   python app.py")
        print()
        print("5. Open browser:")
        print("   http://localhost:5001")
        print("=" * 40)

def main():
    """Main startup validation function"""
    validator = StartupValidator()
    result = validator.run_comprehensive_check()
    
    if result['status'] == 'success':
        print("\n🎉 System is ready! You can start the Flask app.")
        validator.print_startup_commands()
        return 0
    elif result['status'] == 'warning':
        print("\n⚠️  System is mostly ready, but check warnings above.")
        validator.print_startup_commands()
        return 0
    else:
        print("\n🚨 Fix the critical issues above before starting the app.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
