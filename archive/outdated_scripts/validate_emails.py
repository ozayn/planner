#!/usr/bin/env python3
"""
Email validation script for venue data
Validates email addresses using regex and reports issues
"""

import sys
import os
import re
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_email(email):
    """
    Validate email address using regex
    Returns (is_valid, error_message)
    """
    if not email or email.strip() == '':
        return True, None  # Empty emails are allowed
    
    email = email.strip()
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, f"Invalid email format: {email}"
    
    # Additional checks
    if len(email) > 254:  # RFC 5321 limit
        return False, f"Email too long: {email}"
    
    if email.count('@') != 1:
        return False, f"Multiple @ symbols: {email}"
    
    local_part, domain = email.split('@')
    if len(local_part) > 64:  # RFC 5321 limit
        return False, f"Local part too long: {email}"
    
    if domain.startswith('.') or domain.endswith('.'):
        return False, f"Domain starts/ends with dot: {email}"
    
    return True, None

def validate_venue_emails():
    """Validate all email addresses in predefined venues"""
    print("🔍 Validating email addresses in predefined venues...")
    
    # Load predefined venues
    try:
        with open('data/predefined_venues.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading predefined venues: {e}")
        return
    
    venues = []
    for city_data in data['cities'].values():
        venues.extend(city_data['venues'])
    
    print(f"📊 Found {len(venues)} venues to validate")
    
    invalid_emails = []
    valid_count = 0
    empty_count = 0
    
    for venue in venues:
        venue_name = venue.get('name', 'Unknown')
        email = venue.get('email', '')
        
        if not email or email.strip() == '':
            empty_count += 1
            continue
        
        is_valid, error = validate_email(email)
        if is_valid:
            valid_count += 1
        else:
            invalid_emails.append({
                'venue': venue_name,
                'email': email,
                'error': error
            })
    
    print(f"\n📈 Validation Results:")
    print(f"✅ Valid emails: {valid_count}")
    print(f"📭 Empty emails: {empty_count}")
    print(f"❌ Invalid emails: {len(invalid_emails)}")
    
    if invalid_emails:
        print(f"\n❌ Invalid Email Addresses:")
        for item in invalid_emails:
            print(f"  • {item['venue']}: {item['email']} - {item['error']}")
    
    return invalid_emails

def validate_database_emails():
    """Validate email addresses in the database"""
    print("\n🔍 Validating email addresses in database...")
    
    try:
        from app import app, db, Venue
        
        with app.app_context():
            venues = Venue.query.all()
            print(f"📊 Found {len(venues)} venues in database")
            
            invalid_emails = []
            valid_count = 0
            empty_count = 0
            
            for venue in venues:
                email = venue.email or ''
                
                if not email or email.strip() == '':
                    empty_count += 1
                    continue
                
                is_valid, error = validate_email(email)
                if is_valid:
                    valid_count += 1
                else:
                    invalid_emails.append({
                        'venue_id': venue.id,
                        'venue_name': venue.name,
                        'email': email,
                        'error': error
                    })
            
            print(f"\n📈 Database Validation Results:")
            print(f"✅ Valid emails: {valid_count}")
            print(f"📭 Empty emails: {empty_count}")
            print(f"❌ Invalid emails: {len(invalid_emails)}")
            
            if invalid_emails:
                print(f"\n❌ Invalid Email Addresses in Database:")
                for item in invalid_emails:
                    print(f"  • ID {item['venue_id']} - {item['venue_name']}: {item['email']} - {item['error']}")
            
            return invalid_emails
            
    except Exception as e:
        print(f"❌ Error validating database emails: {e}")
        return []

if __name__ == "__main__":
    print("📧 Email Validation Tool")
    print("=" * 50)
    
    # Validate predefined venues
    json_invalid = validate_venue_emails()
    
    # Validate database
    db_invalid = validate_database_emails()
    
    total_invalid = len(json_invalid) + len(db_invalid)
    
    if total_invalid == 0:
        print(f"\n🎉 All email addresses are valid!")
    else:
        print(f"\n⚠️  Found {total_invalid} invalid email addresses that need fixing")
