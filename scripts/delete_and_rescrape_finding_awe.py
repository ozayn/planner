#!/usr/bin/env python3
"""
Delete all Finding Awe events and re-scrape them fresh from the website
"""
import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event
from scripts.nga_finding_awe_scraper import scrape_all_finding_awe_events, create_events_in_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_and_rescrape():
    """Delete all Finding Awe events and re-scrape them"""
    with app.app_context():
        # Find all Finding Awe events
        nga_events = Event.query.filter(
            Event.url.like('%finding-awe%')
        ).all()
        
        deleted_count = len(nga_events)
        print(f"🗑️  Found {deleted_count} Finding Awe events to delete")
        
        # Delete them
        for event in nga_events:
            print(f"   Deleting: {event.title[:60]}...")
            db.session.delete(event)
        
        db.session.commit()
        print(f"✅ Deleted {deleted_count} events\n")
        
        # Now re-scrape
        print("🔍 Scraping all Finding Awe events from website...")
        events = scrape_all_finding_awe_events()
        
        if not events:
            print("❌ No events found during scraping")
            return 0
        
        print(f"📋 Found {len(events)} events to create:")
        for event in events:
            print(f"   - {event.get('title', 'N/A')[:60]}")
            if event.get('start_date'):
                print(f"     Date: {event['start_date']}")
            if event.get('start_time'):
                print(f"     Time: {event['start_time']} - {event.get('end_time', 'N/A')}")
        
        print(f"\n💾 Creating events in database...")
        created_count = create_events_in_database(events)
        print(f"\n✅ Done! Created {created_count} new events")
        return created_count

if __name__ == '__main__':
    print("🔄 Deleting and re-scraping Finding Awe events...\n")
    created = delete_and_rescrape()
    print(f"\n✅ Complete! {created} events created")

