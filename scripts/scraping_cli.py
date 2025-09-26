#!/usr/bin/env python3
"""
Event Scraping CLI Tool
Command-line interface for running event scraping operations.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def setup_logging(level=logging.INFO):
    """Setup logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/event_scraping.log')
        ]
    )

def scrape_smithsonian():
    """Scrape events from Smithsonian museums."""
    print("🏛️ Scraping Smithsonian Museum Events...")
    
    try:
        from smithsonian_scraper import SmithsonianEventScraper
        
        scraper = SmithsonianEventScraper()
        events = scraper.scrape_all_smithsonian_events()
        
        print(f"✅ Found {len(events)} Smithsonian events")
        
        # Show sample events
        for i, event in enumerate(events[:3]):
            print(f"\n{i+1}. {event['title']}")
            print(f"   Organizer: {event['organizer']}")
            print(f"   Confidence: {event['confidence_score']:.2f}")
            if event.get('start_date'):
                print(f"   Date: {event['start_date']}")
            if event.get('start_time'):
                print(f"   Time: {event['start_time']}")
        
        return events
        
    except Exception as e:
        print(f"❌ Error scraping Smithsonian events: {e}")
        return []

def scrape_all_venues(city_id=1):
    """Scrape events from all venues."""
    print(f"🏙️ Scraping Events from All Venues (City ID: {city_id})...")
    
    try:
        from scraping_database_integration import ScrapingScheduler
        
        scheduler = ScrapingScheduler()
        result = scheduler.run_daily_scraping(city_id)
        
        print(f"✅ Scraping completed:")
        print(f"   Venues scraped: {result['venues_scraped']}")
        print(f"   Events found: {result['events_found']}")
        print(f"   Events saved: {result['events_saved']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error scraping all venues: {e}")
        return {}

def scrape_museums_only(city_id=1):
    """Scrape events from museums only."""
    print(f"🏛️ Scraping Events from Museums Only (City ID: {city_id})...")
    
    try:
        from scraping_database_integration import ScrapingScheduler
        
        scheduler = ScrapingScheduler()
        result = scheduler.run_museum_scraping(city_id)
        
        print(f"✅ Museum scraping completed:")
        print(f"   Museums scraped: {result['museums_scraped']}")
        print(f"   Events found: {result['events_found']}")
        print(f"   Events saved: {result['events_saved']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error scraping museums: {e}")
        return {}

def discover_new_venues(city_name="Washington DC"):
    """Discover new venues and scrape their events."""
    print(f"🔍 Discovering New Venues in {city_name}...")
    
    try:
        from event_scraping_system import EventScrapingOrchestrator
        
        orchestrator = EventScrapingOrchestrator()
        events = orchestrator.discover_and_scrape(city_name)
        
        print(f"✅ Discovery completed:")
        print(f"   Events found: {len(events)}")
        
        # Show sample events
        for i, event in enumerate(events[:3]):
            print(f"\n{i+1}. {event.title}")
            print(f"   Organizer: {event.organizer}")
            print(f"   Confidence: {event.confidence_score:.2f}")
        
        return events
        
    except Exception as e:
        print(f"❌ Error discovering venues: {e}")
        return []

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description='Event Scraping CLI Tool')
    parser.add_argument('command', choices=[
        'smithsonian', 'all-venues', 'museums', 'discover', 'help'
    ], help='Scraping command to run')
    parser.add_argument('--city-id', type=int, default=1, 
                       help='City ID for scraping (default: 1 for Washington DC)')
    parser.add_argument('--city-name', type=str, default="Washington DC",
                       help='City name for venue discovery (default: Washington DC)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    print(f"🚀 Event Scraping Tool - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if args.command == 'smithsonian':
        events = scrape_smithsonian()
        if events:
            print(f"\n📊 Summary: Found {len(events)} Smithsonian events")
    
    elif args.command == 'all-venues':
        result = scrape_all_venues(args.city_id)
        if result:
            print(f"\n📊 Summary: Scraped {result['venues_scraped']} venues, saved {result['events_saved']} events")
    
    elif args.command == 'museums':
        result = scrape_museums_only(args.city_id)
        if result:
            print(f"\n📊 Summary: Scraped {result['museums_scraped']} museums, saved {result['events_saved']} events")
    
    elif args.command == 'discover':
        events = discover_new_venues(args.city_name)
        if events:
            print(f"\n📊 Summary: Discovered {len(events)} events from new venues")
    
    elif args.command == 'help':
        print("Available commands:")
        print("  smithsonian  - Scrape events from Smithsonian museums")
        print("  all-venues   - Scrape events from all venues in database")
        print("  museums     - Scrape events from museums only")
        print("  discover     - Discover new venues and scrape their events")
        print("  help         - Show this help message")
        print("\nExamples:")
        print("  python scraping_cli.py smithsonian")
        print("  python scraping_cli.py all-venues --city-id 1")
        print("  python scraping_cli.py museums --verbose")
        print("  python scraping_cli.py discover --city-name 'New York'")
    
    print("\n✅ Scraping operation completed!")

if __name__ == "__main__":
    main()
