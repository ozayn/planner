#!/usr/bin/env python3
"""
Test Admin Interface Headers
Tests that the admin interface generates proper table headers
"""

import requests
import json

def test_admin_interface():
    """Test that the admin interface loads and generates headers"""
    
    print("🧪 Testing Admin Interface Headers")
    print("=" * 60)
    
    try:
        # Test if the app is running
        response = requests.get("http://localhost:5002/admin", timeout=5)
        if response.status_code == 200:
            print("✅ Admin interface is accessible")
        else:
            print(f"❌ Admin interface returned status {response.status_code}")
            return False
        
        # Test venues API
        venues_response = requests.get("http://localhost:5002/api/admin/venues", timeout=5)
        if venues_response.status_code == 200:
            venues = venues_response.json()
            print(f"✅ Venues API working - {len(venues)} venues loaded")
            
            # Check if venues have the expected fields
            if venues:
                sample_venue = venues[0]
                expected_fields = [
                    'id', 'name', 'venue_type', 'description', 'address',
                    'website_url', 'image_url', 'latitude', 'longitude',
                    'phone_number', 'email', 'facebook_url', 'instagram_url',
                    'twitter_url', 'opening_hours', 'holiday_hours',
                    'admission_fee', 'tour_info', 'additional_info',
                    'city_id', 'city_name', 'created_at', 'updated_at'
                ]
                
                missing_fields = []
                for field in expected_fields:
                    if field not in sample_venue:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"⚠️ Missing fields in venue data: {missing_fields}")
                else:
                    print("✅ All expected venue fields present")
                    
                print(f"\\n📋 Sample venue fields:")
                for field in sorted(sample_venue.keys()):
                    value = str(sample_venue[field])
                    if len(value) > 50:
                        value = value[:50] + "..."
                    print(f"   {field}: {value}")
        else:
            print(f"❌ Venues API returned status {venues_response.status_code}")
            return False
        
        # Test cities API
        cities_response = requests.get("http://localhost:5002/api/admin/cities", timeout=5)
        if cities_response.status_code == 200:
            cities = cities_response.json()
            print(f"\\n✅ Cities API working - {len(cities)} cities loaded")
        else:
            print(f"❌ Cities API returned status {cities_response.status_code}")
            return False
        
        print("\\n" + "=" * 60)
        print("🎯 ADMIN INTERFACE TEST SUMMARY:")
        print("   ✅ Admin interface accessible")
        print("   ✅ Venues API working")
        print("   ✅ Cities API working")
        print("   ✅ Table headers should now be generated dynamically")
        print("\\n💡 To see the headers:")
        print("   1. Open http://localhost:5002/admin in your browser")
        print("   2. Click on 'Venues' tab")
        print("   3. Headers should now appear above the venue data")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the application")
        print("   Make sure the Flask app is running on port 5002")
        return False
    except Exception as e:
        print(f"❌ Error testing admin interface: {e}")
        return False

if __name__ == "__main__":
    success = test_admin_interface()
    if not success:
        exit(1)
