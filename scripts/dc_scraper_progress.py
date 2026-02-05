#!/usr/bin/env python3
"""
DC Event Scraper with Progress Tracking
Scrapes events from Washington DC venues and sources
"""

import json
import os
import sys
from datetime import datetime, timedelta
import random

# Add the parent directory to the path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def update_progress(step, total_steps, message):
    """Update progress file for real-time tracking"""
    progress = {
        'current_step': step,
        'total_steps': total_steps,
        'percentage': int((step / total_steps) * 100),
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('scraping_progress.json', 'w') as f:
        json.dump(progress, f)
    
    print(f"Progress {progress['percentage']}%: {message}")

def generate_sample_events():
    """Generate sample events for testing - replace with real scraping later"""
    
    # Get parameters from environment variables
    city_id = os.getenv('SCRAPE_CITY_ID', '')
    event_type = os.getenv('SCRAPE_EVENT_TYPE', '')
    time_range = os.getenv('SCRAPE_TIME_RANGE', 'today')
    venue_ids = os.getenv('SCRAPE_VENUE_IDS', '').split(',') if os.getenv('SCRAPE_VENUE_IDS') else []
    custom_start_date = os.getenv('SCRAPE_CUSTOM_START_DATE', '')
    custom_end_date = os.getenv('SCRAPE_CUSTOM_END_DATE', '')
    
    print(f"📊 Scraping parameters: city_id={city_id}, event_type={event_type}, time_range={time_range}, venues={len(venue_ids)}")
    if custom_start_date and custom_end_date:
        print(f"📅 Custom date range: {custom_start_date} to {custom_end_date}")
    
    # Sample event templates
    tour_templates = [
        {
            "title": "Guided Museum Tour",
            "description": "Join our expert guide for an in-depth exploration of the museum's highlights",
            "event_type": "tour",
            "tour_type": "Guided",
            "max_participants": 25,
            "price": 15.0,
            "language": "English",
            "start_location": "Main Entrance",
            "difficulty_level": "Easy"
        },
        {
            "title": "Self-Guided Audio Tour",
            "description": "Explore at your own pace with our comprehensive audio guide",
            "event_type": "tour", 
            "tour_type": "Self-guided",
            "max_participants": 50,
            "price": 8.0,
            "language": "English",
            "start_location": "Information Desk",
            "difficulty_level": "Easy"
        }
    ]
    
    exhibition_templates = [
        {
            "title": "Contemporary Art Exhibition",
            "description": "Featuring works by emerging and established contemporary artists",
            "event_type": "exhibition",
            "exhibition_location": "Gallery 1",
            "curator": "Dr. Sarah Johnson",
            "admission_price": 12.0
        },
        {
            "title": "Historical Artifacts Display",
            "description": "Rare historical artifacts from the museum's permanent collection",
            "event_type": "exhibition",
            "exhibition_location": "Main Gallery",
            "curator": "Prof. Michael Chen",
            "admission_price": 0.0
        }
    ]
    
    festival_templates = [
        {
            "title": "Cultural Festival",
            "description": "Celebrate diverse cultures with music, food, and performances",
            "event_type": "festival",
            "festival_type": "Cultural",
            "multiple_locations": True,
            "start_location": "Central Plaza",
            "end_location": "Cultural Center"
        },
        {
            "title": "Art & Music Festival",
            "description": "Local artists and musicians showcase their talents",
            "event_type": "festival",
            "festival_type": "Art",
            "multiple_locations": False,
            "start_location": "Outdoor Amphitheater"
        }
    ]
    
    photowalk_templates = [
        {
            "title": "Architecture Photowalk",
            "description": "Capture the beauty of historic and modern architecture",
            "event_type": "photowalk",
            "difficulty_level": "Medium",
            "equipment_needed": "Camera or smartphone, comfortable walking shoes",
            "organizer": "DC Photography Club",
            "start_location": "Union Station",
            "end_location": "National Mall"
        },
        {
            "title": "Nature Photowalk",
            "description": "Explore local parks and capture natural beauty",
            "event_type": "photowalk",
            "difficulty_level": "Easy",
            "equipment_needed": "Camera, extra batteries, water bottle",
            "organizer": "Nature Photography Society",
            "start_location": "Rock Creek Park",
            "end_location": "Meridian Hill Park"
        }
    ]
    
    # Combine all templates
    all_templates = tour_templates + exhibition_templates + festival_templates + photowalk_templates
    
    # Filter by event type if specified
    if event_type:
        all_templates = [template for template in all_templates if template['event_type'] == event_type]
        print(f"🎯 Filtering to {event_type} events only: {len(all_templates)} templates")
    
    # Generate events based on time range
    events = []
    
    # Handle custom date range
    if time_range == 'custom' and custom_start_date and custom_end_date:
        try:
            start_date = datetime.strptime(custom_start_date, '%Y-%m-%d')
            end_date = datetime.strptime(custom_end_date, '%Y-%m-%d')
            days_to_generate = (end_date - start_date).days + 1
            base_date = start_date
            print(f"📅 Generating events for custom range: {custom_start_date} to {custom_end_date} ({days_to_generate} days)")
        except ValueError as e:
            print(f"❌ Invalid custom date format: {e}")
            return []
    else:
        # Handle predefined time ranges
        base_date = datetime.now()
        
        if time_range == 'today':
            days_to_generate = 1
        elif time_range == 'tomorrow':
            days_to_generate = 1
            base_date = base_date + timedelta(days=1)
        elif time_range == 'this_week':
            days_to_generate = 7
        elif time_range == 'next_week':
            days_to_generate = 7
            base_date = base_date + timedelta(days=7)
        elif time_range == 'this_month':
            days_to_generate = 30
        elif time_range == 'next_month':
            days_to_generate = 30
            base_date = base_date + timedelta(days=30)
        else:
            days_to_generate = 7  # Default
        
        print(f"📅 Generating events for {days_to_generate} days starting from {base_date.strftime('%Y-%m-%d')}")
    
    for i in range(days_to_generate):
        current_date = base_date + timedelta(days=i)
        
        # Generate 2-4 events per day
        num_events = random.randint(2, 4)
        day_templates = random.sample(all_templates, min(num_events, len(all_templates)))
        
        for j, template in enumerate(day_templates):
            event = template.copy()
            
            # Add date and time
            event["start_date"] = current_date.strftime("%Y-%m-%d")
            event["end_date"] = current_date.strftime("%Y-%m-%d")
            
            # Add random times
            if event["event_type"] in ["tour", "photowalk"]:
                start_hour = random.randint(9, 15)
                event["start_time"] = f"{start_hour:02d}:00"
                event["end_time"] = f"{start_hour + random.randint(1, 3):02d}:00"
            elif event["event_type"] == "exhibition":
                event["start_time"] = "10:00"
                event["end_time"] = "17:00"
            else:  # festival
                event["start_time"] = "12:00"
                event["end_time"] = "20:00"
            
            # Add unique ID
            event["id"] = len(events) + 1
            
            # Add URL and image
            event["url"] = f"https://example.com/event/{event['id']}"
            event["image_url"] = f"https://placehold.co/400x300/667eea/ffffff?text={event['title'].replace(' ', '+')}"
            
            # Add venue association
            if venue_ids:
                # Use one of the provided venue IDs
                event["venue_id"] = int(random.choice(venue_ids))
            else:
                # Random venue ID for now (will be handled by seed script)
                event["venue_id"] = random.randint(1, 10)
            
            events.append(event)
    
    return events

def main():
    """Main scraping function"""
    try:
        total_steps = 4
        
        # Step 1: Initialize
        update_progress(1, total_steps, "Initializing DC event scraper...")
        
        # Step 2: Get parameters
        update_progress(2, total_steps, "Loading scraping parameters...")
        venue_ids = os.getenv('SCRAPE_VENUE_IDS', '').split(',') if os.getenv('SCRAPE_VENUE_IDS') else []
        venue_ids = [int(vid) for vid in venue_ids if vid.strip()]
        city_id = int(os.getenv('SCRAPE_CITY_ID', 0)) if os.getenv('SCRAPE_CITY_ID') else None
        
        # Step 3: Scrape real events from venues
        update_progress(3, total_steps, "Scraping events from venues...")
        
        # Import and use the real venue scraper
        from venue_event_scraper import VenueEventScraper
        scraper = VenueEventScraper()
        events = scraper.scrape_venue_events(venue_ids, city_id)
        
        # NO FALLBACK TO SAMPLE EVENTS - Only real scraped events
        if not events:
            print("⚠️ No events found from venues - this is normal if venues don't have events listed")
            events = []  # Empty list, no fake data
        
        # Step 4: Save to file
        update_progress(4, total_steps, "Saving scraped data...")
        
        scraped_data = {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "total_events": len(events),
                "scraper_version": "2.0",
                "venue_ids": venue_ids,
                "city_id": city_id,
                "city": "Washington DC"
            },
            "events": events
        }
        
        with open('dc_scraped_data.json', 'w') as f:
            json.dump(scraped_data, f, indent=2)
        
        print(f"✅ Successfully scraped {len(events)} events")
        return True
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
