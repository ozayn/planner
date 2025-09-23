#!/usr/bin/env python3
"""
Clean Duplicate Events

This script removes duplicate events and keeps only unique ones.
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

def clean_duplicate_events():
    """Remove duplicate events and keep only unique ones"""
    try:
        with app.app_context():
            # Count events before cleanup
            total_events = Event.query.count()
            logger.info(f"Total events before cleanup: {total_events}")
            
            # Find duplicate titles
            duplicates = db.session.query(Event.title, db.func.count(Event.id)).group_by(Event.title).having(db.func.count(Event.id) > 1).all()
            
            deleted_count = 0
            
            for title, count in duplicates:
                logger.info(f"Found {count} duplicates of: {title}")
                
                # Keep the first event, delete the rest
                events_with_title = Event.query.filter_by(title=title).order_by(Event.created_at.asc()).all()
                
                for i, event in enumerate(events_with_title):
                    if i == 0:
                        logger.info(f"  Keeping: {event.title} (ID: {event.id})")
                    else:
                        logger.info(f"  Deleting: {event.title} (ID: {event.id})")
                        db.session.delete(event)
                        deleted_count += 1
            
            # Commit changes
            db.session.commit()
            
            # Count events after cleanup
            remaining_events = Event.query.count()
            
            logger.info(f"✅ Deleted {deleted_count} duplicate events")
            logger.info(f"📊 Remaining events: {remaining_events}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error cleaning duplicate events: {e}")
        db.session.rollback()
        return False

def main():
    """Main function"""
    success = clean_duplicate_events()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
