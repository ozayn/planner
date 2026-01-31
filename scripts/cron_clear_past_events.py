#!/usr/bin/env python3
"""
Cronjob script to clear past events from the database weekly.

This script deletes events that have already ended and are not permanent collections.
It is designed to be run from a cronjob (e.g., once a week).

Usage:
    source venv/bin/activate && python scripts/cron_clear_past_events.py
"""

import os
import sys
import logging
from datetime import datetime, date
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
log_dir = project_root / 'logs'
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f'cron_clear_past_events_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def clear_past_events():
    """Logic to clear past events from the database"""
    from app import app, db, Event
    
    start_time = datetime.now()
    logger.info("-" * 40)
    logger.info(f"⌛ Starting past events cleanup...")
    
    with app.app_context():
        today = date.today()
        
        # Build query for past events
        # 1. Event has an end_date and end_date < today
        # 2. Event has no end_date and start_date < today
        # AND Event is not permanent
        query = Event.query.filter(
            db.or_(
                db.and_(Event.end_date.isnot(None), Event.end_date < today),
                db.and_(Event.end_date.is_(None), Event.start_date < today)
            ),
            Event.is_permanent == False
        )
        
        # Count and delete
        past_events_count = query.count()
        
        if past_events_count > 0:
            logger.info(f"🗑️  Found {past_events_count} past events to delete.")
            query.delete(synchronize_session=False)
            db.session.commit()
            logger.info(f"✅ Successfully deleted {past_events_count} past events.")
        else:
            logger.info("✅ No past events found to delete.")
        
        return past_events_count

def main():
    """Main function to clear past events"""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"⌛ Starting weekly past events cleanup cronjob - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        past_events_count = clear_past_events()
        
        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 80)
        logger.info("📊 CLEANUP SUMMARY")
        logger.info("=" * 80)
        logger.info(f"   Events deleted: {past_events_count}")
        logger.info(f"   Duration: {duration}")
        logger.info(f"   Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Fatal error in cronjob: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
