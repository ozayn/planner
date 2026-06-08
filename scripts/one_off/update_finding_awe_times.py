#!/usr/bin/env python3
"""
Update Finding Awe events that have incorrect or missing start/end times
Re-scrapes each event page to get accurate times from page content
"""
import os
import sys
from datetime import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event
from scripts.nga_finding_awe_scraper import scrape_individual_event

def update_all_times():
    """Update all Finding Awe events with correct times from page content"""
    with app.app_context():
        # Find all Finding Awe events
        nga_events = Event.query.filter(
            Event.url.like('%finding-awe%')
        ).all()
        
        print(f"Found {len(nga_events)} Finding Awe events to check/update")
        
        # Create a single scraper session to reuse (much faster)
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        
        updated_count = 0
        for i, event in enumerate(nga_events, 1):
            print(f"\n[{i}/{len(nga_events)}] 📅 Processing: {event.title[:50]}...")
            print(f"   Current: {event.start_date} at {event.start_time} - {event.end_time}")
            
            # Use the existing scraper function (reuses session internally)
            event_data = scrape_individual_event(event.url, scraper)
            
            if event_data and event_data.get('start_time') and event_data.get('end_time'):
                # Parse times from ISO format strings
                from datetime import datetime
                try:
                    start_time = datetime.fromisoformat(event_data['start_time']).time()
                    end_time = datetime.fromisoformat(event_data['end_time']).time()
                    
                    # Check if times are different
                    if event.start_time != start_time or event.end_time != end_time:
                        old_start = event.start_time
                        old_end = event.end_time
                        event.start_time = start_time
                        event.end_time = end_time
                        db.session.commit()
                        updated_count += 1
                        print(f"   ✅ Updated: {old_start} - {old_end} → {start_time} - {end_time}")
                    else:
                        print(f"   ✓ Times already correct: {start_time} - {end_time}")
                except (ValueError, TypeError) as e:
                    print(f"   ⚠️  Error parsing times: {e}")
            else:
                print(f"   ❌ Could not extract time from page")
        
        print(f"\n✅ Updated {updated_count} events with correct times")
        return updated_count

if __name__ == '__main__':
    print("🔄 Updating Finding Awe events with correct times from page content...")
    updated = update_all_times()
    print(f"✅ Done! Updated {updated} events")

