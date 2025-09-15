#!/usr/bin/env python3
"""
COMPREHENSIVE REGRESSION PREVENTION SCRIPT
This script ensures ALL critical components are present and working
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_contains(file_path, required_content):
    """Check if file contains required content"""
    if not os.path.exists(file_path):
        return False, f"File {file_path} does not exist"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    for item in required_content:
        if item not in content:
            return False, f"Missing: {item}"
    
    return True, "All required content found"

def fix_app_py():
    """Ensure app.py has all required components"""
    print("🔧 Checking app.py for regressions...")
    
    required_components = [
        "@app.route('/admin')",
        "@app.route('/api/admin/stats')",
        "@app.route('/api/admin/cities')",
        "@app.route('/api/admin/venues')",
        "@app.route('/api/admin/events')",
        "@app.route('/api/discover-venues')",
        "@app.route('/api/add-venue-manually')",
        "db_path = os.path.expanduser('~/.local/share/planner/events.db')",
        "opening_hours = db.Column(db.Text)",
        "holiday_hours = db.Column(db.Text)",
        "phone_number = db.Column(db.String(50))",
        "email = db.Column(db.String(200))",
        "tour_info = db.Column(db.Text)",
        "admission_fee = db.Column(db.Text)"
    ]
    
    is_valid, message = check_file_contains('app.py', required_components)
    
    if not is_valid:
        print(f"❌ app.py regression detected: {message}")
        print("🔧 This needs to be fixed manually")
        return False
    else:
        print("✅ app.py is complete")
        return True

def check_database_schema():
    """Check if database schema is correct"""
    print("🔧 Checking database schema...")
    
    try:
        # Import and check database
        sys.path.append('.')
        from app import app, db, Venue
        
        with app.app_context():
            # Check if Venue table has all required columns
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('venue')]
            
            required_columns = [
                'id', 'name', 'venue_type', 'description', 'address',
                'latitude', 'longitude', 'image_url', 'instagram_url',
                'website_url', 'opening_hours', 'holiday_hours',
                'phone_number', 'email', 'tour_info', 'admission_fee',
                'city_id', 'created_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"❌ Missing database columns: {missing_columns}")
                return False
            else:
                print("✅ Database schema is complete")
                return True
                
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_cities_data():
    """Check if cities are populated"""
    print("🔧 Checking cities data...")
    
    try:
        from app import app, db, City
        
        with app.app_context():
            cities_count = City.query.count()
            
            if cities_count == 0:
                print("❌ No cities found in database")
                return False
            else:
                print(f"✅ {cities_count} cities found")
                return True
                
    except Exception as e:
        print(f"❌ Cities check failed: {e}")
        return False

def check_admin_template():
    """Check if admin template exists and has correct JavaScript"""
    print("🔧 Checking admin template...")
    
    if not os.path.exists('templates/admin.html'):
        print("❌ Admin template missing")
        return False
    
    # Check for correct JavaScript structure
    with open('templates/admin.html', 'r') as f:
        content = f.read()
    
    required_js = [
        "data.cities",
        "data.venues", 
        "data.events",
        "/api/admin/stats",
        "/api/admin/cities",
        "/api/admin/venues",
        "/api/admin/events"
    ]
    
    missing_js = [item for item in required_js if item not in content]
    
    if missing_js:
        print(f"❌ Admin template JavaScript issues: {missing_js}")
        return False
    else:
        print("✅ Admin template is complete")
        return True

def run_comprehensive_check():
    """Run all checks"""
    print("🛡️  COMPREHENSIVE REGRESSION CHECK")
    print("=" * 50)
    
    checks = [
        ("app.py components", fix_app_py),
        ("Database schema", check_database_schema),
        ("Cities data", check_cities_data),
        ("Admin template", check_admin_template)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - NO REGRESSIONS DETECTED!")
        return True
    else:
        print("🚨 REGRESSIONS DETECTED - MANUAL FIX REQUIRED!")
        return False

if __name__ == '__main__':
    success = run_comprehensive_check()
    sys.exit(0 if success else 1)
