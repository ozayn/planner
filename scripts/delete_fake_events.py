#!/usr/bin/env python3
"""
Delete Fake Events

This script removes fake/sample events and keeps only real scraped events.
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_fake_events():
    """Delete fake/sample events and keep only real scraped events"""
    try:
        with app.app_context():
            # Count events before deletion
            total_events = Event.query.count()
            logger.info(f"Total events before cleanup: {total_events}")
            
            # Delete events that are likely fake/sample events
            fake_event_patterns = [
                'Sample Event',
                'Sample Tour',
                'Sample Exhibition',
                'Sample Festival',
                'Sample Photowalk',
                'Untitled Event',
                'Test Event',
                'Demo Event',
                'Example Event',
                'Upcoming Events',  # Generic placeholder
                'Upcoming Public Programs',  # Generic placeholder
            ]
            
            deleted_count = 0
            
            for pattern in fake_event_patterns:
                events_to_delete = Event.query.filter(Event.title.like(f'%{pattern}%')).all()
                for event in events_to_delete:
                    logger.info(f"Deleting fake event: {event.title}")
                    db.session.delete(event)
                    deleted_count += 1
            
            # Also delete events with no real content (empty descriptions, no URLs, etc.)
            empty_events = Event.query.filter(
                (Event.description == '') | (Event.description.is_(None)),
                Event.url.is_(None),
                Event.start_location.like('%Sample%')
            ).all()
            
            for event in empty_events:
                logger.info(f"Deleting empty event: {event.title}")
                db.session.delete(event)
                deleted_count += 1
            
            # Commit changes
            db.session.commit()
            
            # Count events after deletion
            remaining_events = Event.query.count()
            
            logger.info(f"✅ Deleted {deleted_count} fake events")
            logger.info(f"📊 Remaining events: {remaining_events}")
            
            # Show remaining events
            remaining = Event.query.all()
            logger.info("📅 Remaining events:")
            for event in remaining:
                logger.info(f"  • {event.title} - {event.source} - {event.venue.name if event.venue else 'No venue'}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error deleting fake events: {e}")
        db.session.rollback()
        return False

def main():
    """Main function"""
    success = delete_fake_events()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
