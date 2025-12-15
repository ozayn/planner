#!/usr/bin/env python3
"""
Shared Event Database Handler
Centralized logic for saving events to the database with deduplication,
venue validation, and immediate commits. All scrapers should use this
instead of duplicating the same logic.
"""

import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)

# Specialized museum URL domains - used for venue validation
SPECIALIZED_MUSEUM_DOMAINS = {
    'npg.si.edu': 'National Portrait Gallery',
    'nga.gov': 'National Gallery of Art',
    'americanart.si.edu': 'Smithsonian American Art Museum',
    'asia.si.edu': 'Smithsonian National Museum of Asian Art',
    'africa.si.edu': 'Smithsonian National Museum of African Art'
}


def validate_event_url_domain(event_url: str, expected_venue_name: str = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that an event URL belongs to the correct venue.
    
    Args:
        event_url: The event URL to validate
        expected_venue_name: Optional venue name to check against
        
    Returns:
        Tuple of (is_valid, reason_if_invalid)
        - is_valid: True if URL is valid for the venue, False if it belongs to another specialized museum
        - reason_if_invalid: String explaining why it's invalid, or None if valid
    """
    if not event_url:
        return True, None
    
    event_url_lower = event_url.lower()
    
    # Check if URL belongs to a specialized museum
    for domain, museum_name in SPECIALIZED_MUSEUM_DOMAINS.items():
        if domain in event_url_lower:
            # If we have an expected venue, check if it matches
            if expected_venue_name:
                expected_lower = expected_venue_name.lower()
                if museum_name.lower() in expected_lower or expected_lower in museum_name.lower():
                    return True, None
                else:
                    return False, f"URL belongs to {museum_name}, not {expected_venue_name}"
            # If no expected venue, it's valid (just belongs to a specialized museum)
            return True, None
    
    # URL doesn't belong to a specialized museum, so it's valid
    return True, None


def should_skip_event_for_venue(event_url: str, current_venue_name: str) -> bool:
    """
    Check if an event should be skipped because it belongs to a different specialized museum.
    
    Args:
        event_url: The event URL
        current_venue_name: The name of the venue currently processing this event
        
    Returns:
        True if event should be skipped (belongs to another specialized museum)
    """
    if not event_url:
        return False
    
    event_url_lower = event_url.lower()
    current_venue_lower = current_venue_name.lower()
    
    # SPECIAL CASE: Renwick Gallery is part of SAAM and shares the same website
    # So Renwick should accept events from americanart.si.edu domain
    if 'renwick' in current_venue_lower and 'americanart.si.edu' in event_url_lower:
        return False  # Don't skip - Renwick is part of SAAM
    
    # Check each specialized museum domain
    for domain, museum_name in SPECIALIZED_MUSEUM_DOMAINS.items():
        if domain in event_url_lower:
            # If this URL belongs to a specialized museum
            museum_name_lower = museum_name.lower()
            # Check if current venue matches this museum
            if museum_name_lower not in current_venue_lower and current_venue_lower not in museum_name_lower:
                # URL belongs to a different specialized museum - skip it
                return True
    
    return False


def find_existing_event(event_data: Dict, venue_id: int, city_id: int, db, Event, Venue) -> Optional:
    """
    Find an existing event in the database using multiple strategies.
    
    Priority order:
    1. URL-based matching (across all venues) - most reliable
    2. Title + date for exhibitions (across all venues with same website)
    3. Title + venue_id + date (venue-specific)
    
    Args:
        event_data: Event data dictionary
        venue_id: Venue ID
        city_id: City ID
        db: SQLAlchemy database session
        Event: Event model class
        Venue: Venue model class
        
    Returns:
        Existing Event object or None
    """
    title = event_data.get('title', '').strip()
    event_url = event_data.get('url') or event_data.get('source_url') or ''
    event_type = event_data.get('event_type', 'event')
    start_date = event_data.get('start_date')
    
    if not title or not start_date:
        return None
    
    # Convert start_date to date object if it's a string
    if isinstance(start_date, str):
        try:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return None
    
    # Strategy 1: URL-based matching (most reliable, across all venues)
    # BUT: For recurring events (same URL, different dates/times), we need to include start_time
    if event_url:
        normalized_url = event_url.rstrip('/')
        start_time = event_data.get('start_time')
        
        # Convert start_time to time object if it's a string
        if isinstance(start_time, str):
            try:
                if ':' in start_time:
                    parts = start_time.split(':')
                    from datetime import time as dt_time
                    start_time = dt_time(int(parts[0]), int(parts[1]))
                else:
                    start_time = None
            except (ValueError, IndexError):
                start_time = None
        
        # For recurring events with same URL (like walk-in tours), we MUST include date AND time
        # CRITICAL: Also include venue_id to prevent cross-venue matches (e.g., Renwick vs SAAM)
        # Otherwise all recurring tours will match the first one saved
        query = Event.query.filter(
            ((Event.url == event_url) | (Event.url == normalized_url) | 
             (Event.source_url == event_url) | (Event.source_url == normalized_url)),
            Event.venue_id == venue_id,  # CRITICAL: Match by venue to prevent cross-venue duplicates
            Event.city_id == city_id,
            Event.start_date == start_date
        )
        
        # CRITICAL: For recurring events (like walk-in tours), include start_time in matching
        # This prevents all recurring tours from matching the first one
        if start_time:
            query = query.filter(Event.start_time == start_time)
        else:
            # If no start_time in new event, only match events that also have no start_time
            # This prevents matching a recurring tour with time to one without time
            query = query.filter(Event.start_time.is_(None))
        
        existing = query.first()
        
        if existing:
            logger.debug(f"   🔍 Strategy 1 (URL-based) found existing event: {existing.id} (venue_id: {existing.venue_id})")
            return existing
    
    # Strategy 2: For exhibitions, match by title + date across venues with same website
    if event_type == 'exhibition':
        venue = db.session.get(Venue, venue_id)
        if venue and venue.website_url:
            website = venue.website_url.lower().strip()
            existing = db.session.query(Event).join(Venue).filter(
                Event.title == title,
                Event.event_type == 'exhibition',
                Venue.website_url == venue.website_url,
                Event.city_id == city_id,
                Event.start_date == start_date
            ).first()
            
            if existing:
                logger.debug(f"   🔍 Strategy 2 (exhibition title+date) found existing event: {existing.id} (venue_id: {existing.venue_id})")
                return existing
    
    # Strategy 3: Venue-specific matching (title + venue_id + date + time for recurring events)
    start_time = event_data.get('start_time')
    
    # Convert start_time to time object if it's a string
    if isinstance(start_time, str):
        try:
            if ':' in start_time:
                parts = start_time.split(':')
                from datetime import time as dt_time
                start_time = dt_time(int(parts[0]), int(parts[1]))
            else:
                start_time = None
        except (ValueError, IndexError):
            start_time = None
    
    # Strategy 3: Venue-specific matching (title + venue_id + date + time for recurring events)
    # This is the fallback if URL-based matching didn't find anything
    query = Event.query.filter_by(
        title=title,
        venue_id=venue_id,  # CRITICAL: Must match venue_id
        city_id=city_id,
        start_date=start_date
    )
    
    # Include start_time in matching for recurring events (prevents duplicates)
    if start_time:
        query = query.filter_by(start_time=start_time)
    
    existing = query.first()
    
    if existing:
        logger.debug(f"   🔍 Strategy 3 (venue-specific title+date+time) found existing event: {existing.id} (venue_id: {existing.venue_id})")
    
    return existing


def update_existing_event(existing, event_data: Dict, venue_id: int, logger) -> bool:
    """
    Update an existing event with new data.
    
    Args:
        existing: Existing Event object
        event_data: New event data
        venue_id: Correct venue ID (may differ from existing.venue_id)
        logger: Logger instance
        
    Returns:
        True if event was updated, False otherwise
    """
    updated = False
    updated_fields = []
    
    # CRITICAL: Fix venue_id if it's wrong
    if existing.venue_id != venue_id:
        existing.venue_id = venue_id
        updated = True
        updated_fields.append('venue_id')
        logger.info(f"   🔄 Corrected venue_id: {existing.venue_id} -> {venue_id}")
    
    # Update description if new one is longer
    new_description = event_data.get('description', '')
    if new_description and (not existing.description or len(new_description) > len(existing.description)):
        existing.description = new_description
        updated = True
        updated_fields.append('description')
    
    # Update event_type if more specific
    new_event_type = event_data.get('event_type')
    if new_event_type and new_event_type != 'event' and existing.event_type == 'event':
        existing.event_type = new_event_type
        updated = True
        updated_fields.append('event_type')
    
    # Update URL if different
    if event_data.get('url') and event_data.get('url') != existing.url:
        existing.url = event_data.get('url')
        updated = True
        updated_fields.append('url')
    
    # Update image_url if different
    if event_data.get('image_url') and event_data.get('image_url') != existing.image_url:
        existing.image_url = event_data.get('image_url')
        updated = True
        updated_fields.append('image_url')
    
    # Update is_online flag
    if 'is_online' in event_data and event_data['is_online'] != existing.is_online:
        existing.is_online = event_data['is_online']
        updated = True
        updated_fields.append('is_online')
        
        # If online, ensure location is set
        if event_data['is_online'] and not existing.start_location:
            existing.start_location = 'Online'
            updated_fields.append('start_location')
    
    # Update other fields as needed
    for field in ['start_time', 'end_time', 'end_date', 'start_location', 'end_location',
                  'meeting_point', 'price', 'is_registration_required', 'registration_url',
                  'is_baby_friendly']:
        if field in event_data and hasattr(existing, field):
            new_value = event_data[field]
            
            # Convert time strings to time objects
            if field in ['start_time', 'end_time'] and isinstance(new_value, str):
                try:
                    from datetime import time as dt_time
                    if ':' in new_value:
                        parts = new_value.split(':')
                        if len(parts) >= 2:
                            hour = int(parts[0])
                            minute = int(parts[1])
                            second = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                            new_value = dt_time(hour, minute, second)
                        else:
                            continue  # Skip if can't parse
                    else:
                        continue  # Skip if no colon
                except (ValueError, IndexError, TypeError):
                    continue  # Skip if can't parse
            
            if new_value is not None and getattr(existing, field) != new_value:
                setattr(existing, field, new_value)
                updated = True
                updated_fields.append(field)
    
    if updated:
        logger.debug(f"   🔄 Updated fields: {', '.join(updated_fields)}")
    
    return updated


def detect_baby_friendly(event_data: Dict) -> bool:
    """
    Detect if an event is baby-friendly based on title and description.
    
    Args:
        event_data: Event data dictionary
        
    Returns:
        True if event is baby-friendly
    """
    title = event_data.get('title', '').lower()
    description = (event_data.get('description', '') or '').lower()
    combined_text = f"{title} {description}"
    
    baby_keywords = [
        'baby', 'babies', 'toddler', 'toddlers', 'infant', 'infants',
        'ages 0-2', 'ages 0–2', 'ages 0 to 2', '0-2 years', '0–2 years',
        'ages 0-3', 'ages 0–3', 'ages 0 to 3', '0-3 years', '0–3 years',
        'bring your own baby', 'byob', 'baby-friendly', 'baby friendly',
        'stroller', 'strollers', 'nursing', 'breastfeeding',
        'family program', 'family-friendly', 'family friendly',
        'art & play', 'art and play', 'play time', 'playtime',
        'children', 'kids', 'little ones', 'young families'
    ]
    
    return any(keyword in combined_text for keyword in baby_keywords)


def handle_ongoing_exhibition_dates(event_data: Dict, logger_instance: Optional[logging.Logger] = None) -> bool:
    """
    Handle missing dates for ongoing/permanent exhibitions.
    Sets start_date to today and end_date to 2 years from today.
    
    Args:
        event_data: Event data dictionary (modified in place)
        logger_instance: Optional logger
        
    Returns:
        True if dates were set, False if event should be skipped
    """
    if logger_instance is None:
        logger_instance = logger
    
    if event_data.get('start_date'):
        return True  # Already has dates
    
    from scripts.utils import detect_ongoing_exhibition, get_ongoing_exhibition_dates
    
    title = event_data.get('title', '')
    description = event_data.get('description', '') or ''
    event_type = event_data.get('event_type', '').lower()
    
    # Check if it's an ongoing exhibition
    is_ongoing = (
        detect_ongoing_exhibition(description) or 
        detect_ongoing_exhibition(title) or
        event_type == 'exhibition' or
        'exhibition' in title.lower()
    )
    
    if is_ongoing:
        start_date_obj, end_date_obj = get_ongoing_exhibition_dates()
        event_data['start_date'] = start_date_obj
        event_data['end_date'] = end_date_obj
        logger_instance.info(f"   🔄 Treating '{title}' as ongoing/permanent exhibition (start: {start_date_obj.isoformat()}, end: {end_date_obj.isoformat()})")
        return True
    else:
        logger_instance.warning(f"   ⚠️  Skipping event '{title}': missing start_date")
        return False


def create_events_in_database(
    events: List[Dict],
    venue_id: int,
    city_id: int,
    venue_name: str,
    db,
    Event,
    Venue,
    batch_size: int = 5,
    logger_instance: Optional[logging.Logger] = None,
    source_url: Optional[str] = None,
    custom_event_processor: Optional[callable] = None
) -> Tuple[int, int, int]:
    """
    Save events to database with deduplication, venue validation, and immediate commits.
    
    This is the shared handler that all scrapers should use instead of duplicating logic.
    
    Args:
        events: List of event dictionaries
        venue_id: Venue ID for these events
        city_id: City ID for these events
        venue_name: Name of the venue (for validation)
        db: SQLAlchemy database session
        Event: Event model class
        Venue: Venue model class
        batch_size: Number of events to commit in a batch (default: 5 for immediate saving)
        logger_instance: Optional logger instance (uses module logger if not provided)
        
    Returns:
        Tuple of (created_count, updated_count, skipped_count)
    """
    if logger_instance is None:
        logger_instance = logger
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # Import utilities
    from scripts.utils import is_category_heading
    
    for event_data in events:
        try:
            title = event_data.get('title', '').strip()
            event_type = event_data.get('event_type', 'unknown')
            
            # CRITICAL: Check URL domain to ensure event belongs to this venue
            event_url = event_data.get('url') or event_data.get('source_url') or ''
            if should_skip_event_for_venue(event_url, venue_name):
                skipped_count += 1
                logger_instance.debug(f"   ⏭️ Skipping event from different specialized museum: {title} (URL: {event_url})")
                continue
            
            # Validate required fields
            if not title:
                logger_instance.warning(f"   ⚠️  Skipping event: missing title")
                skipped_count += 1
                continue
            
            # Skip category headings
            if is_category_heading(title):
                logger_instance.debug(f"   ⏭️ Skipping category heading: '{title}'")
                skipped_count += 1
                continue
            
            # Skip non-English events
            language = event_data.get('language', 'English')
            if language and language.lower() != 'english':
                logger_instance.debug(f"   ⚠️  Skipping non-English event: '{title}' (language: {language})")
                skipped_count += 1
                continue
            
            # Handle ongoing exhibitions (set dates if missing)
            if not event_data.get('start_date'):
                if event_type == 'tour':
                    logger_instance.warning(f"   ⚠️  Skipping tour '{title}': missing start_date")
                if not handle_ongoing_exhibition_dates(event_data, logger_instance):
                    skipped_count += 1
                    continue
            
            # Detect baby-friendly events
            if detect_baby_friendly(event_data):
                event_data['is_baby_friendly'] = True
                logger_instance.info(f"   👶 Detected baby-friendly event: '{title}'")
            
            # Allow custom event processing (e.g., for venue-specific fields)
            if custom_event_processor:
                custom_event_processor(event_data)
            
            # Ensure venue_id and city_id are set
            event_data['venue_id'] = venue_id
            event_data['city_id'] = city_id
            
            # Set source_url if provided
            if source_url and not event_data.get('source_url'):
                event_data['source_url'] = source_url
            
            # Find existing event
            existing = find_existing_event(event_data, venue_id, city_id, db, Event, Venue)
            
            # Debug logging for recurring tours
            if title == 'Docent-Led Walk-In Tour' and event_data.get('start_date') and event_data.get('start_time'):
                if existing:
                    logger_instance.info(f"   🔍 Found existing tour: {title} on {event_data.get('start_date')} at {event_data.get('start_time')} (existing venue_id: {existing.venue_id}, new venue_id: {venue_id})")
                else:
                    logger_instance.info(f"   ✅ No existing tour found - will create new: {title} on {event_data.get('start_date')} at {event_data.get('start_time')} (venue_id: {venue_id})")
            
            if existing:
                # Update existing event
                was_updated = update_existing_event(existing, event_data, venue_id, logger_instance)
                if was_updated:
                    # Commit immediately for updates
                    db.session.commit()
                    updated_count += 1
                    logger_instance.info(f"   ✅ Updated: {title}")
                else:
                    skipped_count += 1
                    logger_instance.info(f"   ⏭️  Event already exists (no updates needed): {title} on {event_data.get('start_date')} at {event_data.get('start_time')}")
            else:
                # Create new event
                event = Event()
                
                # Set all valid Event model fields
                valid_fields = [
                    'title', 'description', 'event_type', 'url', 'image_url',
                    'start_date', 'end_date', 'start_time', 'end_time',
                    'start_location', 'end_location', 'meeting_point',
                    'venue_id', 'city_id', 'source', 'source_url', 'organizer',
                    'price', 'is_online', 'is_registration_required', 'registration_url',
                    'registration_info', 'social_media_platform', 'social_media_handle', 
                    'social_media_url', 'is_baby_friendly', 'is_selected'
                ]
                
                for field in valid_fields:
                    if field in event_data and event_data[field] is not None:
                        # Handle date conversion if needed
                        if field in ['start_date', 'end_date'] and isinstance(event_data[field], str):
                            try:
                                from datetime import datetime
                                event_data[field] = datetime.fromisoformat(event_data[field].replace('Z', '+00:00')).date()
                            except (ValueError, AttributeError):
                                try:
                                    event_data[field] = datetime.strptime(event_data[field], '%Y-%m-%d').date()
                                except ValueError:
                                    continue  # Skip if can't parse
                        # Handle time conversion if needed
                        elif field in ['start_time', 'end_time'] and isinstance(event_data[field], str):
                            try:
                                from datetime import time as dt_time
                                time_str = event_data[field].strip()
                                if ':' in time_str:
                                    parts = time_str.split(':')
                                    if len(parts) >= 2:
                                        hour = int(parts[0])
                                        minute = int(parts[1])
                                        second = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                                        event_data[field] = dt_time(hour, minute, second)
                                    else:
                                        continue  # Skip if can't parse
                                else:
                                    continue  # Skip if no colon
                            except (ValueError, IndexError, TypeError):
                                continue  # Skip if can't parse
                        
                        setattr(event, field, event_data[field])
                
                db.session.add(event)
                created_count += 1
                
                # Commit in small batches for immediate saving
                if created_count % batch_size == 0:
                    db.session.commit()
                    logger_instance.info(f"   ✅ Created batch: {created_count} events saved so far...")
                else:
                    # Commit immediately for events not in a batch (ensures immediate saving)
                    db.session.commit()
                
                logger_instance.info(f"   ✅ Created: {title}")
        
        except Exception as e:
            error_count += 1
            logger_instance.error(f"   ❌ Error processing event '{event_data.get('title', 'Unknown')}': {e}")
            db.session.rollback()
            import traceback
            logger_instance.debug(traceback.format_exc())
            continue
    
    # Final commit for any remaining events (safety net)
    try:
        db.session.commit()
    except Exception as e:
        logger_instance.error(f"❌ Error in final commit: {e}")
        db.session.rollback()
    
    logger_instance.info(f"✅ Created {created_count} new events, updated {updated_count} existing events, skipped {skipped_count} duplicates")
    
    return (created_count, updated_count, skipped_count)
