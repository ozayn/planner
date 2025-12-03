#!/usr/bin/env python3
"""
Comprehensive improvements for Washington DC venue scraping
This script enhances the venue scraper with DC-specific improvements
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue, City

def analyze_dc_venues():
    """Analyze DC venues and identify improvement opportunities"""
    
    with app.app_context():
        dc = City.query.filter_by(name='Washington').first()
        if not dc:
            print("❌ Washington DC not found")
            return
        
        venues = Venue.query.filter_by(city_id=dc.id).all()
        
        # Categorize venues
        museums = []
        galleries = []
        theaters = []
        memorials = []
        other = []
        
        for venue in venues:
            venue_type = (venue.venue_type or '').lower()
            name = venue.name.lower()
            
            if 'museum' in venue_type or 'museum' in name:
                museums.append(venue)
            elif 'gallery' in venue_type or 'gallery' in name:
                galleries.append(venue)
            elif 'theater' in venue_type or 'theater' in venue_type or 'theatre' in venue_type:
                theaters.append(venue)
            elif 'memorial' in name or 'monument' in name:
                memorials.append(venue)
            else:
                other.append(venue)
        
        print("📊 DC Venue Analysis")
        print("="*60)
        print(f"Total venues: {len(venues)}")
        print(f"Museums: {len(museums)}")
        print(f"Galleries: {len(galleries)}")
        print(f"Theaters: {len(theaters)}")
        print(f"Memorials/Monuments: {len(memorials)}")
        print(f"Other: {len(other)}")
        
        print("\n🏛️ Major Museums (for focused improvements):")
        major_museums = [
            'National Gallery of Art',
            'National Portrait Gallery',
            'Hirshhorn',
            'Phillips Collection',
            'International Spy Museum',
            'National Air and Space Museum',
            'National Museum of Natural History',
            'National Museum of American History',
            'National Museum of African American History and Culture'
        ]
        
        for museum_name in major_museums:
            matching = [v for v in museums if museum_name.lower() in v.name.lower()]
            if matching:
                venue = matching[0]
                print(f"  ✅ {venue.name}")
                print(f"     URL: {venue.website_url}")
                print(f"     Type: {venue.venue_type}")
                print()
        
        return {
            'museums': museums,
            'galleries': galleries,
            'theaters': theaters,
            'memorials': memorials,
            'other': other
        }

def create_improvement_plan():
    """Create a comprehensive improvement plan for DC venue scraping"""
    
    improvements = {
        'venue_specific_patterns': {
            'National Gallery of Art': {
                'exhibition_url_patterns': [
                    '/exhibitions/',
                    '/calendar/',
                    '/calendar/finding-awe'
                ],
                'listing_page_selectors': [
                    '.exhibition-card',
                    '.calendar-event',
                    '[data-event-type="exhibition"]'
                ],
                'special_handling': 'nga_calendar_page'
            },
            'Hirshhorn Museum': {
                'exhibition_url_patterns': [
                    '/exhibitions-events/',
                    '/exhibitions/'
                ],
                'listing_page_selectors': [
                    '.exhibition-item',
                    '.event-card'
                ],
                'special_handling': 'hirshhorn_date_format'
            },
            'International Spy Museum': {
                'exhibition_url_patterns': [
                    '/exhibition-experiences/'
                ],
                'listing_page_selectors': [
                    '.exhibition-card',
                    '.experience-card'
                ],
                'special_handling': 'spy_museum_galleries'
            },
            'Phillips Collection': {
                'exhibition_url_patterns': [
                    '/exhibitions/',
                    '/calendar/'
                ],
                'listing_page_selectors': [
                    '.exhibition-item',
                    '.event-listing'
                ],
                'special_handling': 'phillips_format'
            }
        },
        
        'smithsonian_improvements': {
            'date_extraction': 'Improve date parsing for permanent exhibitions',
            'listing_page_detection': 'Better detection of listing vs individual pages',
            'exhibition_status': 'Handle "ongoing" and "permanent" exhibitions'
        },
        
        'general_improvements': {
            'error_handling': 'Better retry logic for failed requests',
            'timeout_handling': 'Increase timeout for slow-loading pages',
            'rate_limiting': 'Implement smarter rate limiting',
            'duplicate_detection': 'Improve duplicate event detection',
            'date_parsing': 'Better handling of date ranges and ongoing exhibitions'
        }
    }
    
    print("\n🎯 IMPROVEMENT PLAN")
    print("="*60)
    
    print("\n1. Venue-Specific Patterns:")
    for venue, config in improvements['venue_specific_patterns'].items():
        print(f"   ✅ {venue}")
        print(f"      Patterns: {len(config['exhibition_url_patterns'])}")
        print(f"      Special handling: {config['special_handling']}")
    
    print("\n2. Smithsonian Improvements:")
    for key, desc in improvements['smithsonian_improvements'].items():
        print(f"   ✅ {key}: {desc}")
    
    print("\n3. General Improvements:")
    for key, desc in improvements['general_improvements'].items():
        print(f"   ✅ {key}: {desc}")
    
    return improvements

if __name__ == '__main__':
    print("🚀 DC Venue Scraping Improvement Analysis\n")
    
    venues_by_category = analyze_dc_venues()
    improvements = create_improvement_plan()
    
    print("\n✅ Analysis complete! Ready to implement improvements.")
    print("\nNext steps:")
    print("1. Add venue-specific scraping patterns")
    print("2. Improve Smithsonian date extraction")
    print("3. Enhance listing page detection")
    print("4. Add special handling for major DC museums")

