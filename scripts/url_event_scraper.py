#!/usr/bin/env python3
"""
URL Event Scraper

Scrapes event data from a given URL and creates multiple events based on recurring schedules.
"""

import os
import sys
import re
import logging
from datetime import datetime, date, time, timedelta
from bs4 import BeautifulSoup

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_event_data_from_url(url):
    """
    Extract event data from a URL for preview/editing (doesn't create events).
    Uses web scraping first, falls back to LLM if bot detection occurs.
    
    For Finding Awe events, uses the dedicated scraper for better extraction.
    
    Args:
        url: The URL to scrape
    
    Returns:
        dict with extracted event data
    """
    # Check if this is a Finding Awe event - use dedicated scraper
    if 'finding-awe' in url.lower():
        try:
            from scripts.nga_finding_awe_scraper import scrape_individual_event
            event_data = scrape_individual_event(url)
            if event_data:
                # Convert to the format expected by the URL scraper
                return {
                    'title': event_data.get('title'),
                    'description': event_data.get('description'),
                    'start_date': event_data.get('start_date'),
                    'start_time': event_data.get('start_time'),
                    'end_time': event_data.get('end_time'),
                    'location': event_data.get('location'),
                    'image_url': event_data.get('image_url'),
                    'event_type': event_data.get('event_type', 'talk'),
                    'is_online': event_data.get('is_online', False),
                    'is_registration_required': event_data.get('is_registration_required', False),
                    'registration_opens_date': event_data.get('registration_opens_date'),
                    'registration_opens_time': event_data.get('registration_opens_time'),
                    'registration_url': event_data.get('registration_url'),
                    'registration_info': event_data.get('registration_info'),
                    'schedule_info': None,
                    'days_of_week': []
                }
        except Exception as e:
            logger.warning(f"Finding Awe scraper failed, falling back to general scraper: {e}")
            # Fall through to general scraper
    
    bot_detected = False
    
    try:
        import cloudscraper
        
        # Create a cloudscraper session
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        
        # Add headers
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Make the request with retry logic
        import time
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(2 * attempt)
                response = scraper.get(url, timeout=15)
                response.raise_for_status()
                
                if 'Pardon Our Interruption' in response.text or 'Access Denied' in response.text:
                    logger.warning(f"Bot detection triggered on attempt {attempt + 1}")
                    bot_detected = True
                    if attempt < 2:
                        continue
                    else:
                        # All 3 attempts failed - use LLM fallback
                        logger.info("Bot detection on all attempts - switching to LLM fallback")
                        break
                else:
                    bot_detected = False
                    break
            except Exception as e:
                if attempt == 2:
                    logger.warning(f"All scraping attempts failed: {e}")
                    bot_detected = True
                    break
                logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
        
        # If bot detected after all attempts, use LLM fallback
        if bot_detected:
            logger.info(f"🤖 Using LLM to extract event data from: {url}")
            from scripts.llm_url_extractor import extract_event_with_llm
            return extract_event_with_llm(url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract event information
        title = _extract_title(soup, url)
        description = _extract_description(soup)
        image_url = _extract_image(soup, url)
        meeting_point = _extract_meeting_point(page_text)
        schedule_info, days_of_week, start_time, end_time = _extract_schedule(page_text)
        start_date = _extract_date(page_text, url)
        event_type = _determine_event_type(title, description, page_text, url)
        
        return {
            'title': title,
            'description': description,
            'start_date': start_date.isoformat() if start_date else None,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'location': meeting_point,
            'image_url': image_url,
            'schedule_info': schedule_info,
            'days_of_week': days_of_week,
            'event_type': event_type
        }
        
    except Exception as e:
        logger.error(f"Error extracting from URL {url}: {e}")
        # Try LLM as last resort
        try:
            logger.info(f"🤖 Using LLM as fallback after error: {e}")
            from scripts.llm_url_extractor import extract_event_with_llm
            return extract_event_with_llm(url)
        except Exception as llm_error:
            logger.error(f"LLM fallback also failed: {llm_error}")
            raise e  # Raise original error


def scrape_event_from_url(url, venue, city, period_start, period_end, override_data=None):
    """
    Scrape event data from a URL and create events for the specified period.
    
    Args:
        url: The URL to scrape
        venue: Venue object (optional, can be None for city-wide events)
        city: City object (required)
        period_start: Start date of the period
        period_end: End date of the period
        override_data: dict with user-edited data to override scraped data
    
    Returns:
        dict with events_created count, events list, and schedule_info
    """
    try:
        # Check if this is a Finding Awe event - use dedicated scraper
        if 'finding-awe' in url.lower():
            try:
                from scripts.nga_finding_awe_scraper import scrape_individual_event
                event_data = scrape_individual_event(url)
                if event_data:
                    # Use scraped data, but allow override_data to override specific fields
                    title = override_data.get('title') if override_data and override_data.get('title') else event_data.get('title')
                    description = override_data.get('description') if override_data and override_data.get('description') else event_data.get('description')
                    image_url = override_data.get('image_url') if override_data and override_data.get('image_url') else event_data.get('image_url')
                    meeting_point = override_data.get('location') if override_data and override_data.get('location') else event_data.get('location')
                    
                    # Parse times
                    from datetime import time as dt_time
                    start_time = None
                    end_time = None
                    if override_data and override_data.get('start_time'):
                        try:
                            parts = override_data['start_time'].split(':')
                            start_time = dt_time(int(parts[0]), int(parts[1]))
                        except:
                            pass
                    if not start_time and event_data.get('start_time'):
                        try:
                            if isinstance(event_data['start_time'], str):
                                parts = event_data['start_time'].split(':')
                                start_time = dt_time(int(parts[0]), int(parts[1]))
                            else:
                                start_time = event_data['start_time']
                        except:
                            pass
                    
                    if override_data and override_data.get('end_time'):
                        try:
                            parts = override_data['end_time'].split(':')
                            end_time = dt_time(int(parts[0]), int(parts[1]))
                        except:
                            pass
                    if not end_time and event_data.get('end_time'):
                        try:
                            if isinstance(event_data['end_time'], str):
                                parts = event_data['end_time'].split(':')
                                end_time = dt_time(int(parts[0]), int(parts[1]))
                            else:
                                end_time = event_data['end_time']
                        except:
                            pass
                    
                    schedule_info = None
                    days_of_week = []
                    # Store event_type for later use
                    event_type = event_data.get('event_type', 'talk')
            except Exception as e:
                logger.warning(f"Finding Awe scraper failed, falling back to general scraper: {e}")
                # Fall through to general scraper
                event_data = None
        else:
            event_data = None
        
        # Use override data if provided, otherwise scrape
        if override_data and any(override_data.values()) and not event_data:
            title = override_data.get('title')
            description = override_data.get('description')
            image_url = override_data.get('image_url')
            meeting_point = override_data.get('location')
            schedule_info = override_data.get('schedule_info')
            days_of_week = override_data.get('days_of_week') or []
            
            # Parse times from override data
            from datetime import time as dt_time
            start_time = None
            end_time = None
            if override_data.get('start_time'):
                try:
                    parts = override_data['start_time'].split(':')
                    start_time = dt_time(int(parts[0]), int(parts[1]))
                except:
                    pass
            if override_data.get('end_time'):
                try:
                    parts = override_data['end_time'].split(':')
                    end_time = dt_time(int(parts[0]), int(parts[1]))
                except:
                    pass
        elif not event_data:
            # Scrape the data
            import cloudscraper
            
            # Create a cloudscraper session
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
            
            # Add some headers to look more like a real browser
            scraper.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Make the request with retry logic
            import time
            for attempt in range(3):
                try:
                    if attempt > 0:
                        time.sleep(2 * attempt)  # Exponential backoff
                    response = scraper.get(url, timeout=15)
                    response.raise_for_status()
                    
                    # Check if we got a bot detection page
                    if 'Pardon Our Interruption' in response.text:
                        logger.warning(f"Bot detection triggered on attempt {attempt + 1}")
                        if attempt < 2:
                            continue
                        else:
                            logger.error("Failed to bypass bot detection after 3 attempts")
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Extract basic event information
            title = _extract_title(soup, url)
            description = _extract_description(soup)
            image_url = _extract_image(soup, url)
            meeting_point = _extract_meeting_point(page_text)
            
            # Extract schedule information
            schedule_info, days_of_week, start_time, end_time = _extract_schedule(page_text)
            
            # Determine event type
            event_type = _determine_event_type(title, description, page_text, url)
        
        # Determine dates to create events for
        event_dates = []
        
        if days_of_week:
            # Recurring event - create events for matching days in the period
            current_date = period_start
            while current_date <= period_end:
                weekday = current_date.strftime('%A').lower()
                
                # Check if this day matches the schedule
                if _day_matches_schedule(weekday, days_of_week):
                    event_dates.append(current_date)
                
                current_date += timedelta(days=1)
        else:
            # Single event - use period start date
            event_dates = [period_start]
        
        # Create events in database
        events_created = 0
        created_events = []
        
        with app.app_context():
            for event_date in event_dates:
                # Check if event already exists
                filter_dict = {
                    'url': url,
                    'start_date': event_date,
                    'city_id': city.id
                }
                if venue:
                    filter_dict['venue_id'] = venue.id
                
                existing = Event.query.filter_by(**filter_dict).first()
                
                if existing:
                    logger.info(f"Event already exists for {event_date}, skipping")
                    continue
                
                # Determine location and organizer
                location = meeting_point
                if not location and venue:
                    location = venue.address
                
                organizer = venue.name if venue else None
                
                # Determine event type based on content (only if not already set from Finding Awe scraper)
                if 'event_type' not in locals() or event_type is None:
                    # Get page_text if not available (for override_data case)
                    if 'page_text' not in locals():
                        try:
                            import cloudscraper
                            scraper = cloudscraper.create_scraper()
                            response = scraper.get(url, timeout=15)
                            soup = BeautifulSoup(response.text, 'html.parser')
                            page_text = soup.get_text()
                        except:
                            page_text = f"{title} {description}"
                    event_type = _determine_event_type(title, description, page_text, url)
                
                # Create new event
                event = Event(
                    title=title,
                    description=description,
                    start_date=event_date,
                    end_date=event_date,
                    start_time=start_time,
                    end_time=end_time,
                    start_location=location,
                    venue_id=venue.id if venue else None,
                    city_id=city.id,
                    event_type=event_type,
                    url=url,
                    image_url=image_url,
                    source='website',
                    source_url=url,
                    is_selected=False
                )
                
                db.session.add(event)
                events_created += 1
                
                created_events.append({
                    'title': title,
                    'start_date': event_date.isoformat(),
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None,
                    'description': description[:100] if description else None
                })
            
            # Commit all events
            if events_created > 0:
                db.session.commit()
                logger.info(f"✅ Created {events_created} events from URL")
        
        return {
            'events_created': events_created,
            'events': created_events,
            'schedule_info': schedule_info
        }
        
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {e}")
        import traceback
        traceback.print_exc()
        raise


def _extract_title(soup, url):
    """Extract event title from page"""
    # Try page title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Clean up title
        if '|' in title:
            title = title.split('|')[0].strip()
        if title and title != 'Untitled':
            return title
    
    # Try h1
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    
    # Try URL
    url_parts = url.split('/')
    if url_parts:
        # Get last non-empty part
        for part in reversed(url_parts):
            if part and part not in ['', 'events', 'tours']:
                # Convert URL slug to title
                title = part.replace('-', ' ').replace('_', ' ').title()
                return title
    
    return 'Untitled Event'


def _extract_description(soup):
    """Extract event description from page"""
    # Look for meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        desc = meta_desc.get('content')
        if len(desc) > 50:
            return desc
    
    # Look for Open Graph description
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content'):
        desc = og_desc.get('content')
        if len(desc) > 50:
            return desc
    
    # Look for common description elements with more specific patterns
    desc_selectors = [
        {'class': re.compile(r'description', re.I)},
        {'class': re.compile(r'details', re.I)},
        {'class': re.compile(r'summary', re.I)},
        {'class': re.compile(r'content', re.I)},
        {'class': re.compile(r'event.*description', re.I)},
        {'class': re.compile(r'event.*details', re.I)},
        {'id': re.compile(r'description', re.I)},
        {'id': re.compile(r'details', re.I)},
    ]
    
    for selector in desc_selectors:
        elem = soup.find(['div', 'p', 'section', 'article'], selector)
        if elem:
            text = elem.get_text(separator=' ', strip=True)
            if len(text) > 50:  # Must be substantial
                # Clean up whitespace
                text = ' '.join(text.split())
                return text[:1000]  # Increased limit for better descriptions
    
    # Look for main content area (article, main, or content sections)
    main_content = soup.find(['article', 'main']) or soup.find('div', class_=re.compile(r'main|content', re.I))
    if main_content:
        # Find paragraphs that look like descriptions (not too short, not navigation)
        paragraphs = main_content.find_all('p')
        description_paragraphs = []
        for p in paragraphs:
            text = p.get_text(separator=' ', strip=True)
            # Skip very short paragraphs, navigation, or metadata
            if len(text) > 50 and not any(skip in text.lower() for skip in ['register', 'ticket', 'buy now', 'click here', 'learn more']):
                description_paragraphs.append(text)
        
        if description_paragraphs:
            # Combine paragraphs that form a coherent description
            combined = ' '.join(description_paragraphs)
            # Clean up whitespace
            combined = ' '.join(combined.split())
            if len(combined) > 50:
                return combined[:1000]
    
    return None


def _extract_image(soup, url):
    """Extract event image from page"""
    # Try Open Graph image
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        return og_image.get('content')
    
    # Try first substantial image
    images = soup.find_all('img')
    for img in images:
        src = img.get('src') or img.get('data-src')
        if src and not any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', 'placeholder']):
            if not src.startswith('http'):
                from urllib.parse import urljoin
                src = urljoin(url, src)
            return src
    
    return None


def _extract_meeting_point(page_text):
    """Extract meeting point information"""
    meeting_patterns = [
        # NGA format: "West Building Main Floor, Gallery 40" - capture full string up to pipe or newline
        r'(West Building|East Building)[^|\n]*?(?:Main Floor|Ground Floor|Floor \d+)?[^|\n]*?Gallery\s+\d+[^|\n]*',
        # Full building and location: "West Building, Main Floor, Gallery 40"
        r'(West Building|East Building)[^|\n]*?Gallery\s+\d+[^|\n]*',
        # Standard meeting point patterns
        r'(?:Meeting Point|Meet at|Gather at):\s*([^.\n|]+)',
        r'(?:Depart from|Tours depart from|Starting point):\s*([^.\n|]+)',
        # Building name with location details (before pipe or newline)
        r'(West Building|East Building)[^|\n]+(?:Main Floor|Ground Floor|Floor \d+)[^|\n]*',
        # Gallery with context (fallback - less specific)
        r'Gallery\s+\d+[^.\n|]*',
    ]
    
    for pattern in meeting_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            result = match.group(0).strip() if not match.groups() or 'Building' in pattern else match.group(1).strip()
            # Clean up: remove extra whitespace and stop at pipe if present
            result = result.split('|')[0].strip()
            # Remove any trailing date/time patterns
            result = re.sub(r'\s+\d{1,2}:\d{2}\s*[ap]\.?m\.?.*$', '', result, flags=re.IGNORECASE)
            result = re.sub(r'\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*$', '', result, flags=re.IGNORECASE)
            return result
    
    return None


def _determine_event_type(title, description, page_text, url):
    """Determine event type based on title, description, and page content"""
    # Combine all text for analysis
    content = f"{title} {description} {page_text}".lower()
    
    # Check for talk/conversation events
    talk_keywords = [
        'talks & conversations',
        'talk and conversation',
        'talk',
        'conversation',
        'discussion',
        'lecture',
        'speaker',
        'presentation',
        'finding awe',  # NGA specific talk series
        'workshop',  # Often includes talks
    ]
    
    if any(keyword in content for keyword in talk_keywords):
        return 'talk'
    
    # Check for tour events
    tour_keywords = [
        'tour',
        'guided tour',
        'walking tour',
        'museum tour',
        'collection tour',
    ]
    
    if any(keyword in content for keyword in tour_keywords):
        return 'tour'
    
    # Check for exhibition events
    exhibition_keywords = [
        'exhibition',
        'exhibit',
        'on view',
        'now on view',
    ]
    
    if any(keyword in content for keyword in exhibition_keywords):
        return 'exhibition'
    
    # Check for festival events
    festival_keywords = [
        'festival',
        'celebration',
    ]
    
    if any(keyword in content for keyword in festival_keywords):
        return 'festival'
    
    # Check for photowalk events
    photowalk_keywords = [
        'photowalk',
        'photo walk',
        'photography walk',
    ]
    
    if any(keyword in content for keyword in photowalk_keywords):
        return 'photowalk'
    
    # Default to tour for museum/venue events
    return 'tour'


def _extract_date(page_text, url):
    """Extract date from page text or URL parameter"""
    from datetime import date
    import calendar
    
    # First, try to extract from URL parameter (e.g., evd=202601311530)
    url_date_match = re.search(r'evd=(\d{8})', url)
    if url_date_match:
        date_str = url_date_match.group(1)  # YYYYMMDD
        try:
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            return date(year, month, day)
        except (ValueError, IndexError):
            pass
    
    # Try to extract from page text (e.g., "Saturday, Jan 31, 2026")
    date_patterns = [
        # NGA format: "Saturday, Jan 31, 2026"
        r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})',
        # Standard format: "January 31, 2026"
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})',
        # ISO format: "2026-01-31"
        r'(\d{4})-(\d{2})-(\d{2})',
    ]
    
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for pattern in date_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            try:
                if len(match.groups()) == 3:
                    # Month name format
                    month_name = match.group(1).lower()[:3]
                    day = int(match.group(2))
                    year = int(match.group(3))
                    month = month_names.get(month_name)
                    if month:
                        return date(year, month, day)
                elif len(match.groups()) == 3 and match.group(1).isdigit():
                    # ISO format
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    return date(year, month, day)
            except (ValueError, IndexError):
                continue
    
    return None


def _extract_schedule(page_text):
    """
    Extract schedule information from page text.
    
    Returns:
        tuple: (schedule_info_string, days_of_week_list, start_time, end_time)
    """
    schedule_info = None
    days_of_week = []
    start_time = None
    end_time = None
    
    # Pattern to match day(s) + time range
    # Examples: "Fridays 6:30pm - 7:30pm", "Weekdays 3:00pm", "Monday-Friday 10am-5pm"
    # Also: "Saturday, Jan 31, 2026 | 10:30 a.m. – 12:15 p.m." (NGA format)
    day_time_patterns = [
        # NGA format: "Saturday, Jan 31, 2026 | 10:30 a.m. – 12:15 p.m."
        # This pattern captures the date in the middle: (Jan|Feb|...) (\d{1,2}), (\d{4})
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.',
        # Full pattern with time range (standard format)
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Weekday|Weekend)s?\s+(\d{1,2}):(\d{2})\s*([ap]m)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]m)',
        # Single time
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Weekday|Weekend)s?\s+(\d{1,2}):(\d{2})\s*([ap]m)',
        # Range of days with time
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*-\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2}):(\d{2})\s*([ap]m)',
    ]
    
    for pattern in day_time_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            schedule_info = match.group(0)
            day_mentioned = match.group(1).lower()
            
            # Parse day(s)
            if 'weekday' in day_mentioned:
                days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            elif 'weekend' in day_mentioned:
                days_of_week = ['saturday', 'sunday']
            else:
                days_of_week = [day_mentioned]
            
            # Parse start time
            try:
                # Check if this is the NGA format with date (has more groups)
                if len(match.groups()) >= 10:
                    # NGA format: groups are: day, month, day_num, year, start_hour, start_min, start_ampm, end_hour, end_min, end_ampm
                    hour = int(match.group(5))
                    minute = int(match.group(6))
                    ampm_raw = match.group(7).upper()
                else:
                    # Standard format: groups are: day, start_hour, start_min, start_ampm, ...
                    hour = int(match.group(2))
                    minute = int(match.group(3))
                    ampm_raw = match.group(4).upper()
                
                # Handle both "am"/"pm" and "a"/"p" formats (NGA uses "a.m." which becomes "a" in regex)
                if len(ampm_raw) == 1:
                    ampm = 'AM' if ampm_raw == 'A' else 'PM'
                else:
                    ampm = ampm_raw.replace('M', '').replace('.', '')  # Normalize "am"/"pm"/"a.m."/"p.m."
                    ampm = 'AM' if 'A' in ampm.upper() else 'PM'
                
                if ampm == 'PM' and hour != 12:
                    hour += 12
                elif ampm == 'AM' and hour == 12:
                    hour = 0
                
                start_time = time(hour, minute)
                
                # Parse end time if available
                if len(match.groups()) >= 10:
                    # NGA format
                    end_hour = int(match.group(8))
                    end_minute = int(match.group(9))
                    end_ampm_raw = match.group(10).upper()
                elif len(match.groups()) >= 7:
                    # Standard format
                    end_hour = int(match.group(5))
                    end_minute = int(match.group(6))
                    end_ampm_raw = match.group(7).upper()
                else:
                    end_hour = None
                    end_minute = None
                    end_ampm_raw = None
                
                if end_hour is not None:
                    
                    # Handle both "am"/"pm" and "a"/"p" formats
                    if len(end_ampm_raw) == 1:
                        end_ampm = 'AM' if end_ampm_raw == 'A' else 'PM'
                    else:
                        end_ampm = end_ampm_raw.replace('M', '').replace('.', '')
                        end_ampm = 'AM' if 'A' in end_ampm.upper() else 'PM'
                    
                    if end_ampm == 'PM' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'AM' and end_hour == 12:
                        end_hour = 0
                    
                    end_time = time(end_hour, end_minute)
                
                if not end_time:
                    # Assume 1-hour duration
                    start_datetime = datetime.combine(date.today(), start_time)
                    end_datetime = start_datetime + timedelta(hours=1)
                    end_time = end_datetime.time()
                    
            except (ValueError, IndexError) as e:
                logger.debug(f"Error parsing time from schedule: {e}")
            
            break
    
    return schedule_info, days_of_week, start_time, end_time


def _day_matches_schedule(weekday, days_of_week):
    """Check if a weekday matches the schedule"""
    return weekday in [d.lower() for d in days_of_week]

