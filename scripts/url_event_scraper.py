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


def _parse_time_string_npg(time_string):
    """Parse time string like '5:30 p.m.' or '5:30pm' to time object"""
    if not time_string:
        return None
    
    from datetime import time as dt_time
    import re
    
    time_string = time_string.strip().lower()
    # Remove periods
    time_string = re.sub(r'\.', '', time_string)
    
    # Pattern for "HH:MM AM/PM" or "H:MM AM/PM"
    time_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)'
    match = re.search(time_pattern, time_string)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        am_pm = match.group(3)
        
        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0
        
        return dt_time(hour, minute)
    
    # Pattern for "HH AM/PM" (no minutes)
    time_pattern2 = r'(\d{1,2})\s*(am|pm)'
    match = re.search(time_pattern2, time_string)
    if match:
        hour = int(match.group(1))
        am_pm = match.group(2)
        
        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0
        
        return dt_time(hour, 0)
    
    return None


def extract_event_data_from_url(url):
    """
    Extract event data from a URL for preview/editing (doesn't create events).
    Uses web scraping first, falls back to LLM if bot detection occurs.
    
    For Finding Awe events, uses the dedicated scraper for better extraction.
    For SAAM events, uses the SAAM scraper for better extraction.
    For Instagram posts, uses Instagram scraper.
    
    Args:
        url: The URL to scrape
    
    Returns:
        dict with extracted event data
    """
    # Check if this is an Instagram post or profile
    if 'instagram.com' in url.lower() or 'instagr.am' in url.lower():
        try:
            logger.info(f"📱 Detected Instagram URL: {url}")
            is_individual_post = '/p/' in url or '/reel/' in url
            
            # For Instagram, use LLM as primary method since Instagram is very difficult to scrape
            # Instagram heavily relies on JavaScript and bot detection
            if is_individual_post:
                logger.info(f"🤖 Using LLM to extract Instagram post data (primary method): {url}")
                try:
                    from scripts.llm_url_extractor import extract_event_with_llm
                    llm_result = extract_event_with_llm(url)
                    if llm_result and (llm_result.get('title') or llm_result.get('description')):
                        logger.info(f"✅ LLM successfully extracted Instagram post data")
                        # Ensure social media fields are set
                        if 'social_media_platform' not in llm_result:
                            llm_result['social_media_platform'] = 'instagram'
                        if 'social_media_url' not in llm_result:
                            llm_result['social_media_url'] = url
                        return llm_result
                    else:
                        logger.warning(f"LLM returned empty result, trying web scraping fallback")
                except Exception as e:
                    logger.warning(f"LLM extraction failed: {e}, trying web scraping fallback")
            
            # Fallback: Try web scraping (may not work well due to Instagram's structure)
            from scripts.source_event_scraper import SourceEventScraper
            from app import Source
            
            # Extract username from URL
            username = None
            if is_individual_post:
                # Individual post - extract username from post if possible, or use URL directly
                logger.info(f"   Trying web scraping fallback for Instagram post")
                # Extract shortcode for reference
                shortcode_match = re.search(r'instagram\.com/(?:p|reel)/([^/]+)', url)
                shortcode = shortcode_match.group(1) if shortcode_match else None
            else:
                # Profile URL
                match = re.search(r'instagram\.com/([^/?]+)', url)
                if match:
                    username = match.group(1)
            
            if not username and not is_individual_post:
                # Try to extract from any Instagram URL
                match = re.search(r'instagram\.com/([^/?]+)', url)
                if match:
                    username = match.group(1)
            
            # Create a temporary source object
            class MockSource:
                def __init__(self, url, username=None):
                    if username:
                        self.name = f"Instagram @{username}"
                        self.url = f"https://www.instagram.com/{username}/"
                        self.handle = f"@{username}"
                    else:
                        self.name = "Instagram Post"
                        self.url = url
                        self.handle = None
                    self.source_type = 'instagram'
                    self.city_id = None
                    self.event_types = None
            
            mock_source = MockSource(url, username)
            
            # Use SourceEventScraper to scrape Instagram
            scraper = SourceEventScraper()
            events = scraper._scrape_instagram_source(mock_source)
            
            if events:
                # Return the first event found (or most recent)
                event = events[0]
                
                # Convert to format expected by extract_event_data_from_url
                result = {
                    'title': event.get('title', 'Instagram Event'),
                    'description': event.get('description', ''),
                    'start_date': event.get('start_date').isoformat() if event.get('start_date') else None,
                    'end_date': event.get('end_date').isoformat() if event.get('end_date') else None,
                    'start_time': event.get('start_time').isoformat() if event.get('start_time') and hasattr(event.get('start_time'), 'isoformat') else (str(event.get('start_time')) if event.get('start_time') else None),
                    'end_time': event.get('end_time').isoformat() if event.get('end_time') and hasattr(event.get('end_time'), 'isoformat') else (str(event.get('end_time')) if event.get('end_time') else None),
                    'location': event.get('location') or event.get('meeting_point'),
                    'image_url': event.get('image_url'),
                    'event_type': event.get('event_type', 'event'),
                    'language': event.get('language', 'English'),
                    'social_media_platform': 'instagram',
                    'social_media_url': event.get('social_media_url', url),
                    'social_media_handle': event.get('social_media_handle', f"@{username}" if username else None),
                }
                
                logger.info(f"✅ Successfully extracted Instagram event via web scraping: {result.get('title')}")
                return result
            else:
                logger.warning(f"⚠️ No events found from Instagram URL: {url}")
                # If LLM also failed, return a basic result
                return {
                    'title': 'Instagram Post' if is_individual_post else f"Instagram @{username}" if username else 'Instagram',
                    'description': f"Could not extract content from Instagram URL. Instagram content may require authentication or use JavaScript to load. URL: {url}",
                    'social_media_platform': 'instagram',
                    'social_media_url': url,
                    'error': 'No content extracted'
                }
        except Exception as e:
            logger.error(f"Error extracting from Instagram URL {url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Try LLM as last resort
            try:
                logger.info(f"🤖 Trying LLM as last resort after error: {e}")
                from scripts.llm_url_extractor import extract_event_with_llm
                llm_result = extract_event_with_llm(url)
                if llm_result and (llm_result.get('title') or llm_result.get('description')):
                    return llm_result
            except:
                pass
            # Fall through to regular URL scraping as fallback
    
    # Check if this is a SAAM event or exhibition page - use SAAM scraper
    if 'americanart.si.edu' in url.lower():
        # Handle SAAM exhibitions
        # Uses the same scrape_exhibition_detail function as the main SAAM scraper
        # This ensures consistency between bulk scraping and "Quick Add from URL"
        if '/exhibitions/' in url.lower():
            try:
                logger.info(f"🎯 Detected SAAM exhibition page - using SAAM scraper")
                from scripts.saam_scraper import scrape_exhibition_detail, create_scraper
                
                scraper = create_scraper()
                event_data = scrape_exhibition_detail(scraper, url)
                
                if event_data:
                    # Convert SAAM scraper format to URL scraper format
                    # Extract times if available (exhibitions can have opening receptions, special events, etc.)
                    start_time_str = None
                    end_time_str = None
                    if event_data.get('start_time'):
                        start_time_obj = event_data.get('start_time')
                        # Check if it's a time object using duck typing (avoid isinstance with time to prevent conflicts)
                        if hasattr(start_time_obj, 'strftime') and hasattr(start_time_obj, 'hour') and hasattr(start_time_obj, 'minute'):
                            start_time_str = start_time_obj.strftime('%H:%M')
                        elif isinstance(start_time_obj, str):
                            start_time_str = start_time_obj
                    if event_data.get('end_time'):
                        end_time_obj = event_data.get('end_time')
                        # Check if it's a time object using duck typing (avoid isinstance with time to prevent conflicts)
                        if hasattr(end_time_obj, 'strftime') and hasattr(end_time_obj, 'hour') and hasattr(end_time_obj, 'minute'):
                            end_time_str = end_time_obj.strftime('%H:%M')
                        elif isinstance(end_time_obj, str):
                            end_time_str = end_time_obj
                    
                    result = {
                        'title': event_data.get('title'),
                        'description': event_data.get('description'),
                        'start_date': event_data.get('start_date').isoformat() if event_data.get('start_date') else None,
                        'end_date': event_data.get('end_date').isoformat() if event_data.get('end_date') else None,
                        'start_time': start_time_str,  # Exhibitions can have times (opening receptions, etc.)
                        'end_time': end_time_str,
                        'location': event_data.get('meeting_point') or event_data.get('organizer'),
                        'venue': event_data.get('organizer'),
                        'event_type': 'exhibition',
                        'url': url,
                        'image_url': event_data.get('image_url'),  # Primary image for event tab
                        'is_online': False,
                        'price': None,
                        'is_registration_required': False,
                        'registration_info': None,
                        'language': 'English',
                    }
                    # Add additional images if available (extracted but not used in event tab)
                    if event_data.get('additional_images'):
                        result['additional_images'] = event_data.get('additional_images')
                    logger.info(f"✅ Successfully extracted SAAM exhibition data: {result.get('title')} - Dates: {result.get('start_date')} to {result.get('end_date')}")
                    return result
            except Exception as e:
                logger.error(f"❌ Error scraping SAAM exhibition: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Don't fall through - SAAM scraper should work, so this is a real error
                # Re-raise to prevent fallback to LLM
                raise
        
        # Handle SAAM events
        elif '/events/' in url.lower():
            try:
                logger.info(f"🎯 Detected SAAM event page - using direct scraping")
                import cloudscraper
                from bs4 import BeautifulSoup
                from datetime import datetime
                
                scraper = cloudscraper.create_scraper()
                response = scraper.get(url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract title from h1
                title = None
                h1 = soup.find('h1')
                if h1:
                    title = h1.get_text(strip=True)
                
                # Extract date/time from page text (format: "Wednesday, December 17, 2025, 10:30am EST")
                # Also check schema.org structured data for more reliable extraction
                page_text = soup.get_text()
                start_date = None
                start_time = None
                end_time = None
                
                # For SAAM events, prioritize page text over schema.org (schema.org can be incorrect)
                # First try page text patterns, then fall back to schema.org if needed
                schema_script = soup.find('script', type='application/ld+json')
                schema_extracted = False
                
                # Try page text first for SAAM events
                page_text_extracted = False
                
                # Pattern 1: Full date with time range "Wednesday, December 17, 2025, 1 – 2pm EST"
                date_time_range_simple = re.compile(
                    r'(\w+day,?\s+)?(\w+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2})\s*[–-]\s*(\d{1,2})\s*([ap]m)',
                    re.IGNORECASE
                )
                match = date_time_range_simple.search(page_text)
                if match:
                    date_str = match.group(2).strip()
                    try:
                        parsed_date = datetime.strptime(date_str, "%B %d, %Y").date()
                        if not start_date:
                            start_date = parsed_date
                    
                        if not start_time:
                            start_hour = int(match.group(3))
                            end_hour = int(match.group(4))
                            am_pm = match.group(5).upper()
                            start_time = f"{start_hour}:00 {am_pm}"
                            end_time = f"{end_hour}:00 {am_pm}"
                            page_text_extracted = True
                    except ValueError:
                        try:
                            parsed_date = datetime.strptime(date_str, "%B %d %Y").date()
                            if not start_date:
                                start_date = parsed_date
                        
                            if not start_time:
                                start_hour = int(match.group(3))
                                end_hour = int(match.group(4))
                                am_pm = match.group(5).upper()
                                start_time = f"{start_hour}:00 {am_pm}"
                                end_time = f"{end_hour}:00 {am_pm}"
                                page_text_extracted = True
                        except ValueError:
                            pass
            
                # Pattern 2: Full date with time range with colons "Wednesday, December 17, 2025, 10:30 – 11:30am EST"
                if not page_text_extracted:
                    date_time_range = re.compile(
                        r'(\w+day,?\s+)?(\w+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*([ap]m)',
                        re.IGNORECASE
                    )
                    match = date_time_range.search(page_text)
                    if match:
                        date_str = match.group(2).strip()
                        try:
                            parsed_date = datetime.strptime(date_str, "%B %d, %Y").date()
                            if not start_date:
                                start_date = parsed_date
                        
                            if not start_time:
                                start_time_str = match.group(3)
                                end_time_str = match.group(4)
                                am_pm = match.group(5).upper()
                                start_time = f"{start_time_str} {am_pm}"
                                end_time = f"{end_time_str} {am_pm}"
                                page_text_extracted = True
                        except ValueError:
                            try:
                                parsed_date = datetime.strptime(date_str, "%B %d %Y").date()
                                if not start_date:
                                    start_date = parsed_date
                            
                                if not start_time:
                                    start_time_str = match.group(3)
                                    end_time_str = match.group(4)
                                    am_pm = match.group(5).upper()
                                    start_time = f"{start_time_str} {am_pm}"
                                    end_time = f"{end_time_str} {am_pm}"
                                    page_text_extracted = True
                            except ValueError:
                                pass
            
                # Pattern 3: Single time "Wednesday, December 17, 2025, 10:30am EST"
                if not page_text_extracted:
                    date_time_single = re.compile(
                        r'(\w+day,?\s+)?(\w+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}:\d{2})([ap]m)',
                        re.IGNORECASE
                    )
                    match = date_time_single.search(page_text)
                    if match:
                        date_str = match.group(2).strip()
                        try:
                            parsed_date = datetime.strptime(date_str, "%B %d, %Y").date()
                            if not start_date:
                                start_date = parsed_date
                        
                            if not start_time:
                                start_time_str = match.group(3)
                                am_pm = match.group(4).upper()
                                start_time = f"{start_time_str} {am_pm}"
                                # Calculate end time as 1 hour later
                                hour, minute = map(int, start_time_str.split(':'))
                                if am_pm == 'PM' and hour != 12:
                                    hour += 12
                                elif am_pm == 'AM' and hour == 12:
                                    hour = 0
                                end_hour = (hour + 1) % 24
                                if end_hour == 0:
                                    end_time = "12:00 AM"
                                elif end_hour == 12:
                                    end_time = "12:00 PM"
                                elif end_hour > 12:
                                    end_time = f"{end_hour - 12}:{minute:02d} PM"
                                else:
                                    end_time = f"{end_hour}:{minute:02d} AM"
                                page_text_extracted = True
                        except ValueError:
                            try:
                                parsed_date = datetime.strptime(date_str, "%B %d %Y").date()
                                if not start_date:
                                    start_date = parsed_date
                            
                                if not start_time:
                                    start_time_str = match.group(3)
                                    am_pm = match.group(4).upper()
                                    start_time = f"{start_time_str} {am_pm}"
                                    # Calculate end time as 1 hour later
                                    hour, minute = map(int, start_time_str.split(':'))
                                    if am_pm == 'PM' and hour != 12:
                                        hour += 12
                                    elif am_pm == 'AM' and hour == 12:
                                        hour = 0
                                    end_hour = (hour + 1) % 24
                                    if end_hour == 0:
                                        end_time = "12:00 AM"
                                    elif end_hour == 12:
                                        end_time = "12:00 PM"
                                    elif end_hour > 12:
                                        end_time = f"{end_hour - 12}:{minute:02d} PM"
                                    else:
                                        end_time = f"{end_hour}:{minute:02d} AM"
                                    page_text_extracted = True
                            except ValueError:
                                pass
            
                # Fallback to schema.org if page text extraction didn't work
                if not page_text_extracted and schema_script:
                    try:
                        import json
                        schema_data = json.loads(schema_script.string)
                        if isinstance(schema_data, dict):
                            schema_data = [schema_data]
                    
                        for item in schema_data:
                            if isinstance(item, dict) and item.get('@type') in ['Event', 'EventSeries']:
                                # Extract startDate
                                if 'startDate' in item:
                                    start_date_str = item['startDate']
                                    if 'T' in start_date_str:
                                        # ISO format: "2025-12-17T10:30:00-05:00"
                                        date_part, time_part = start_date_str.split('T')
                                        try:
                                            parsed_start_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                                            if not start_date:
                                                start_date = parsed_start_date
                                        
                                            if not start_time:
                                                time_clean = time_part.split('+')[0].split('-')[0].split('Z')[0]
                                                if ':' in time_clean:
                                                    hours, minutes = time_clean.split(':')[:2]
                                                    hour_int = int(hours)
                                                    minute_int = int(minutes)
                                                    am_pm = 'AM' if hour_int < 12 else 'PM'
                                                    if hour_int == 0:
                                                        hour_int = 12
                                                    elif hour_int > 12:
                                                        hour_int -= 12
                                                    start_time = f"{hour_int}:{minute_int:02d} {am_pm}"
                                                    schema_extracted = True
                                        except (ValueError, IndexError):
                                            pass
                            
                                # Extract endDate
                                if 'endDate' in item:
                                    end_date_str = item['endDate']
                                    if 'T' in end_date_str:
                                        time_part = end_date_str.split('T')[1]
                                        try:
                                            time_clean = time_part.split('+')[0].split('-')[0].split('Z')[0]
                                            if ':' in time_clean:
                                                hours, minutes = time_clean.split(':')[:2]
                                                hour_int = int(hours)
                                                minute_int = int(minutes)
                                                am_pm = 'AM' if hour_int < 12 else 'PM'
                                                if hour_int == 0:
                                                    hour_int = 12
                                                elif hour_int > 12:
                                                    hour_int -= 12
                                                end_time = f"{hour_int}:{minute_int:02d} {am_pm}"
                                        except (ValueError, IndexError):
                                            pass
                    except (json.JSONDecodeError, AttributeError, KeyError):
                        pass
            
                # If we got start time from schema.org but no end time, calculate it
                if schema_extracted and start_time and not end_time:
                    # Calculate end time as 1 hour later
                    time_match = re.match(r'(\d{1,2}):(\d{2})\s+(AM|PM)', start_time)
                    if time_match:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                        am_pm = time_match.group(3)
                    
                        # Convert to 24-hour for calculation
                        hour_24 = hour
                        if am_pm == 'PM' and hour != 12:
                            hour_24 = hour + 12
                        elif am_pm == 'AM' and hour == 12:
                            hour_24 = 0
                    
                        # Add 1 hour
                        end_hour_24 = (hour_24 + 1) % 24
                    
                        # Convert back to 12-hour
                        if end_hour_24 == 0:
                            end_time = "12:00 AM"
                        elif end_hour_24 == 12:
                            end_time = "12:00 PM"
                        elif end_hour_24 > 12:
                            end_time = f"{end_hour_24 - 12}:{minute:02d} PM"
                        else:
                            end_time = f"{end_hour_24}:{minute:02d} AM"
            
            
                # Extract description
                description = None
                desc_parts = []
                for p in soup.find_all('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 50 and not any(skip in text.lower() for skip in ['subscribe', 'newsletter', 'follow us', 'legal', 'privacy']):
                        desc_parts.append(text)
                if desc_parts:
                    description = ' '.join(desc_parts)
            
                # Extract location/meeting point
                location = None
                venue = None
                meeting_point = None
            
                # Check Building field
                for dt in soup.find_all('dt'):
                    if dt.get_text(strip=True).lower() == 'building':
                        building_dd = dt.find_next_sibling('dd')
                        if building_dd:
                            venue = building_dd.get_text(strip=True)
                            break
            
                # Check Event Location field
                for dt in soup.find_all('dt'):
                    if dt.get_text(strip=True).lower() in ['event location', 'location']:
                        location_dd = dt.find_next_sibling('dd')
                        if location_dd:
                            location_text = location_dd.get_text(strip=True)
                            # Extract meeting point if it says "Meet in"
                            meet_match = re.search(r'Meet\s+in\s+(.+?)(?:\s*\||$)', location_text, re.I)
                            if meet_match:
                                meeting_point = meet_match.group(1).strip()
                            else:
                                meeting_point = location_text.split('|')[0].strip() if '|' in location_text else location_text
                            break
            
                # Extract image URL
                image_url = None
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    image_url = og_image.get('content')
            
                # Determine if online
                is_online = False
                if 'virtual' in title.lower() if title else False:
                    is_online = True
                if location_text and 'online' in location_text.lower():
                    is_online = True
            
                # Extract price and registration requirement
                price = None
                is_registration_required = False
                registration_info = None
                for dt in soup.find_all('dt'):
                    if dt.get_text(strip=True).lower() == 'cost':
                        cost_dd = dt.find_next_sibling('dd')
                        if cost_dd:
                            cost_text = cost_dd.get_text(strip=True)
                            # Extract price
                            if 'free' in cost_text.lower():
                                price = 'Free'
                            else:
                                price_match = re.search(r'\$(\d+)', cost_text)
                                if price_match:
                                    price = f"${price_match.group(1)}"
                        
                            # Extract registration requirement
                            if 'registration required' in cost_text.lower() or 'registration' in cost_text.lower():
                                is_registration_required = True
                                # Extract the full registration info (e.g., "Free | Registration required")
                                if '|' in cost_text:
                                    parts = cost_text.split('|')
                                    registration_info = parts[1].strip() if len(parts) > 1 else None
                                else:
                                    registration_info = cost_text.strip()
                            break
            
                # Determine event type
                event_type = 'event'
                if title:
                    title_lower = title.lower()
                    if 'tour' in title_lower:
                        event_type = 'tour'
                    elif 'workshop' in title_lower:
                        event_type = 'workshop'
                    elif 'talk' in title_lower or 'gallery talk' in title_lower:
                        event_type = 'talk'
                    elif 'exhibition' in title_lower:
                        event_type = 'exhibition'
            
                if title and start_date:
                    result = {
                        'title': title,
                        'description': description,
                        'start_date': start_date.isoformat() if start_date else None,
                        'start_time': start_time,
                        'end_time': end_time,
                        'location': meeting_point or location or venue,
                        'venue': venue,
                        'event_type': event_type,
                        'url': url,
                        'image_url': image_url,
                        'is_online': is_online,
                        'price': price,
                        'is_registration_required': is_registration_required,
                        'registration_info': registration_info,
                        'language': 'English',
                    }
                    logger.info(f"✅ Successfully extracted SAAM event data: {result.get('title')}")
                    return result
                else:
                    logger.warning(f"⚠️ Missing required fields (title: {bool(title)}, date: {bool(start_date)})")
            except Exception as e:
                logger.warning(f"⚠️ Error scraping SAAM event: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                # Fall through to generic scraping
    
    # Check if this is an NPG event page - use NPG scraper function
    if 'npg.si.edu' in url.lower() and '/event/' in url.lower():
        try:
            logger.info(f"🎯 Detected NPG event page - using NPG scraper")
            from scripts.npg_scraper import scrape_event_detail, create_scraper
            
            scraper = create_scraper()
            event_data = scrape_event_detail(scraper, url)
            
            if event_data:
                # Convert NPG scraper format to URL scraper format
                start_date_obj = event_data.get('start_date')
                if isinstance(start_date_obj, date):
                    start_date_str = start_date_obj.isoformat()
                elif isinstance(start_date_obj, str):
                    start_date_str = start_date_obj
                else:
                    start_date_str = None
                
                # Convert price to float if it's 0.0 (Free), otherwise keep as is
                price_value = event_data.get('price')
                if price_value == 0.0 or price_value == 0:
                    price_value = 0.0
                elif price_value is None:
                    price_value = None
                elif isinstance(price_value, str):
                    # If it's a string like "Free", convert to 0.0
                    if price_value.lower() in ['free', '0', '0.0']:
                        price_value = 0.0
                    else:
                        # Try to parse as float
                        try:
                            price_value = float(price_value)
                        except (ValueError, TypeError):
                            price_value = None
                
                result = {
                    'title': event_data.get('title'),
                    'description': event_data.get('description'),
                    'start_date': start_date_str,
                    'start_time': event_data.get('start_time'),
                    'end_time': event_data.get('end_time'),
                    'location': event_data.get('meeting_point') or event_data.get('start_location'),
                    'venue': 'National Portrait Gallery',
                    'price': price_value,
                    'is_registration_required': event_data.get('is_registration_required', False),
                    'registration_url': event_data.get('registration_url'),
                    'registration_info': event_data.get('registration_info'),
                    'event_type': event_data.get('event_type', 'event'),
                    'image_url': event_data.get('image_url'),
                    'url': url
                }
                
                logger.info(f"✅ Successfully extracted NPG event data: {result.get('title')}")
                return result
                
        except Exception as e:
            logger.warning(f"⚠️ Error scraping NPG event: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Fall through to generic scraping
    
    # Check if this is an OCMA event page - use venue scraper's OCMA extraction logic
    if 'ocma.art' in url.lower() and '/calendar/' in url.lower():
        try:
            logger.info(f"🎯 Detected OCMA event page - using venue scraper extraction")
            from scripts.venue_event_scraper import VenueEventScraper
            from app import Venue, City, app
            
            # Find OCMA venue
            with app.app_context():
                from sqlalchemy import or_
                ocma = Venue.query.filter(
                    or_(
                        db.func.lower(Venue.name).like('%orange county museum%'),
                        db.func.lower(Venue.name).like('%ocma%')
                    )
                ).first()
                
                if not ocma:
                    logger.warning(f"⚠️ OCMA venue not found in database")
                else:
                    logger.info(f"✅ Found OCMA venue: {ocma.name} (ID: {ocma.id})")
                    scraper = VenueEventScraper()
                    
                    # Fetch the page using venue scraper's session
                    logger.info(f"📡 Fetching OCMA event page: {url}")
                    try:
                        response = scraper.session.get(url, timeout=10)
                        logger.info(f"📡 Response status: {response.status_code}")
                        
                        if response.status_code == 200:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Extract using the same logic as _extract_ocma_calendar_events
                            # but for a single event page
                            # OCMA uses a specific div structure: #newclandarsinglecontent
                            main_content = soup.find('div', id='newclandarsinglecontent')
                            if not main_content:
                                main_content = soup.find('article') or soup.find('main') or soup
                            
                            logger.info(f"🔍 Looking for title and date/time in page content")
                            
                            # Extract title - look for h1 in the main content area
                            title_elem = main_content.find('h1') if main_content else None
                            if not title_elem:
                                # Fallback: search entire soup
                                title_elem = soup.find('h1')
                            title = title_elem.get_text(strip=True) if title_elem else None
                            if title:
                                title = _clean_title(title)
                            logger.info(f"📝 Found title: {title}")
                            
                            # Extract date/time from h2 (OCMA format: "December 5, 2025, 5:00–6:00 PM")
                            # Look for h2 elements that contain date/time patterns
                            # First check in main_content, then check all h2s if needed
                            h2_elements = main_content.find_all('h2') if main_content else []
                            if not h2_elements:
                                h2_elements = soup.find_all('h2')
                            logger.info(f"🔍 Found {len(h2_elements)} h2 elements")
                            
                            start_date = None
                            start_time = None
                            end_time = None
                            
                            for h2 in h2_elements:
                                h2_text = h2.get_text(strip=True)
                                logger.info(f"📝 Checking h2: {h2_text[:100]}")
                                
                                from datetime import datetime, time as dt_time
                                
                                # Pattern 1: "December 5, 2025, 5:00–6:00 PM" (same AM/PM for both times)
                                date_time_pattern1 = re.compile(
                                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                                    re.IGNORECASE
                                )
                                
                                # Pattern 2: "December 10, 2025, 11:00 AM–1:00 PM" (different AM/PM for each time)
                                date_time_pattern2 = re.compile(
                                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
                                    re.IGNORECASE
                                )
                                
                                match = date_time_pattern2.search(h2_text) or date_time_pattern1.search(h2_text)
                                if match:
                                    logger.info(f"✅ Found date/time pattern match!")
                                    date_str = match.group(1).strip()
                                    logger.info(f"📅 Date string: {date_str}")
                                    
                                    try:
                                        start_date = datetime.strptime(date_str, "%B %d, %Y").date()
                                        logger.info(f"✅ Parsed date: {start_date}")
                                    except ValueError as e1:
                                        try:
                                            start_date = datetime.strptime(date_str, "%B %d %Y").date()
                                            logger.info(f"✅ Parsed date (no comma): {start_date}")
                                        except ValueError as e2:
                                            logger.warning(f"⚠️ Failed to parse date '{date_str}': {e1}, {e2}")
                                            continue
                                    
                                    # Parse times - check which pattern matched
                                    try:
                                        if date_time_pattern2.search(h2_text):
                                            # Pattern 2: different AM/PM for each time
                                            start_hour = int(match.group(2))
                                            start_min = int(match.group(3))
                                            start_am_pm = match.group(4).lower()
                                            end_hour = int(match.group(5))
                                            end_min = int(match.group(6))
                                            end_am_pm = match.group(7).lower()
                                            
                                            logger.info(f"⏰ Raw times: {start_hour}:{start_min} {start_am_pm} - {end_hour}:{end_min} {end_am_pm}")
                                            
                                            # Convert start time to 24-hour
                                            if start_am_pm == 'p' and start_hour != 12:
                                                start_hour += 12
                                            elif start_am_pm == 'a' and start_hour == 12:
                                                start_hour = 0
                                            
                                            # Convert end time to 24-hour
                                            if end_am_pm == 'p' and end_hour != 12:
                                                end_hour += 12
                                            elif end_am_pm == 'a' and end_hour == 12:
                                                end_hour = 0
                                        else:
                                            # Pattern 1: same AM/PM for both times
                                            start_hour = int(match.group(2))
                                            start_min = int(match.group(3))
                                            end_hour = int(match.group(4))
                                            end_min = int(match.group(5))
                                            am_pm = match.group(6).lower()
                                            
                                            logger.info(f"⏰ Raw times: {start_hour}:{start_min} - {end_hour}:{end_min} {am_pm}")
                                            
                                            # Convert to 24-hour
                                            if am_pm == 'p' and start_hour != 12:
                                                start_hour += 12
                                            elif am_pm == 'a' and start_hour == 12:
                                                start_hour = 0
                                            
                                            if am_pm == 'p' and end_hour != 12:
                                                end_hour += 12
                                            elif am_pm == 'a' and end_hour == 12:
                                                end_hour = 0
                                        
                                        start_time = dt_time(start_hour, start_min)
                                        end_time = dt_time(end_hour, end_min)
                                        logger.info(f"✅ Parsed times: {start_time} - {end_time}")
                                    except (ValueError, IndexError) as e:
                                        logger.warning(f"⚠️ Failed to parse times: {e}")
                                    
                                    break
                                else:
                                    logger.debug(f"⚠️ No date/time pattern match in h2: {h2_text[:100]}")
                            
                            # Extract description
                            desc_elem = main_content.find('p') if main_content else None
                            description = ''
                            if desc_elem:
                                all_paragraphs = main_content.find_all('p')
                                if len(all_paragraphs) > 1:
                                    description = ' '.join([p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True)])
                                else:
                                    description = desc_elem.get_text(strip=True)
                            
                            logger.info(f"📝 Description length: {len(description)} chars")
                            
                            # Extract image
                            img_elem = main_content.find('img') if main_content else None
                            image_url = None
                            if img_elem:
                                img_src = img_elem.get('src') or img_elem.get('data-src')
                                if img_src:
                                    from urllib.parse import urljoin
                                    image_url = urljoin(url, img_src)
                            
                            if title:
                                if not start_date:
                                    logger.warning(f"⚠️ OCMA event '{title}' - date extraction failed, cannot create event without date")
                                    return None
                                
                                # For single-day events, end_date should be the same as start_date
                                end_date = start_date
                                
                                logger.info(f"✅ Successfully extracted OCMA event: '{title}' on {start_date} at {start_time}-{end_time}")
                                # Detect language for OCMA events
                                language = _detect_language(soup, title, description, page_text if 'page_text' in locals() else '')
                                
                                return {
                                    'title': title,
                                    'description': description,
                                    'start_date': start_date.isoformat() if start_date else None,
                                    'end_date': end_date.isoformat() if end_date else None,
                                    'start_time': start_time.isoformat() if start_time else None,
                                    'end_time': end_time.isoformat() if end_time else None,
                                    'location': ocma.name,
                                    'image_url': image_url,
                                    'event_type': 'talk' if 'talk' in title.lower() else 'event',
                                    'schedule_info': None,
                                    'days_of_week': [],
                                    'language': language
                                }
                            else:
                                logger.warning(f"⚠️ OCMA event - title extraction failed")
                                return None
                        else:
                            logger.warning(f"⚠️ Failed to fetch page: HTTP {response.status_code}")
                    except Exception as fetch_error:
                        logger.error(f"❌ Error fetching OCMA page: {fetch_error}")
                        import traceback
                        logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"❌ OCMA specialized extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fall through to general scraper
    
    # Check if this is a Finding Awe event - use dedicated scraper
    if 'finding-awe' in url.lower():
        try:
            from scripts.nga_finding_awe_scraper import scrape_individual_event
            event_data = scrape_individual_event(url)
            if event_data:
                # Convert to the format expected by the URL scraper
                # Detect language for Finding Awe events
                language = event_data.get('language', 'English')
                if not language or language == 'English':
                    try:
                        import cloudscraper
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url, timeout=15)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        page_text = soup.get_text()
                        language = _detect_language(soup, event_data.get('title'), event_data.get('description'), page_text)
                    except:
                        language = 'English'
                
                # Skip non-English language events
                if language and language.lower() != 'english':
                    logger.info(f"⚠️ Skipping non-English event: '{event_data.get('title')}' (language: {language})")
                    return None
                
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
                    'days_of_week': [],
                    'language': language
                }
        except Exception as e:
            logger.warning(f"Finding Awe scraper failed, falling back to general scraper: {e}")
            # Fall through to general scraper
    
    # Check if this is a Hirshhorn tour page - use venue scraper's extraction logic
    if 'hirshhorn.si.edu' in url.lower() and '/event/' in url.lower():
        try:
            logger.info(f"🎯 Detected Hirshhorn tour page - using specialized extraction")
            from scripts.venue_event_scraper import VenueEventScraper
            from app import Venue, City
            
            # Find Hirshhorn venue
            with app.app_context():
                hirshhorn = Venue.query.filter(Venue.name.ilike('%hirshhorn%')).first()
                if hirshhorn:
                    scraper = VenueEventScraper()
                    tour_event = scraper._scrape_hirshhorn_tour_event_page(
                        url, 
                        hirshhorn, 
                        hirshhorn.website_url, 
                        time_range='this_month'
                    )
                    if tour_event:
                        logger.info(f"✅ Successfully extracted using Hirshhorn scraper")
                        # Detect language for Hirshhorn events
                        language = tour_event.get('language', 'English')
                        if not language or language == 'English':
                            try:
                                response = scraper.session.get(url, timeout=15)
                                soup = BeautifulSoup(response.text, 'html.parser')
                                page_text = soup.get_text()
                                language = _detect_language(soup, tour_event.get('title'), tour_event.get('description'), page_text)
                            except:
                                language = 'English'
                        
                        return {
                            'title': tour_event.get('title'),
                            'description': tour_event.get('description'),
                            'start_date': tour_event.get('start_date'),
                            'start_time': tour_event.get('start_time'),
                            'end_time': tour_event.get('end_time'),
                            'location': tour_event.get('start_location'),
                            'image_url': tour_event.get('image_url'),
                            'event_type': tour_event.get('event_type', 'tour'),
                            'is_registration_required': tour_event.get('is_registration_required', False),
                            'registration_url': tour_event.get('registration_url'),
                            'registration_info': tour_event.get('registration_info'),
                            'schedule_info': None,
                            'days_of_week': [],
                            'language': language
                        }
        except Exception as e:
            logger.warning(f"Hirshhorn specialized extraction failed: {e}, falling back to general scraper")
            # Fall through to general scraper
    
    # Check if this is an NGA event page (tours, exhibitions, talks, etc.) - use NGA comprehensive scraper
    if 'nga.gov' in url.lower():
        try:
            # Check if it's an exhibition URL
            if '/exhibitions/' in url.lower():
                logger.info(f"🎯 Detected NGA exhibition page - using specialized extraction")
                from scripts.nga_comprehensive_scraper import scrape_nga_exhibition_page, create_scraper
                
                scraper = create_scraper()
                event_data = scrape_nga_exhibition_page(url, scraper)
                if event_data:
                    logger.info(f"✅ Successfully extracted using NGA exhibition scraper")
                    # Convert date objects to strings if needed
                    start_date_str = None
                    end_date_str = None
                    if event_data.get('start_date'):
                        start_date_obj = event_data.get('start_date')
                        if hasattr(start_date_obj, 'isoformat'):
                            start_date_str = start_date_obj.isoformat()
                        else:
                            start_date_str = str(start_date_obj)
                    if event_data.get('end_date'):
                        end_date_obj = event_data.get('end_date')
                        if hasattr(end_date_obj, 'isoformat'):
                            end_date_str = end_date_obj.isoformat()
                        else:
                            end_date_str = str(end_date_obj)
                    
                    # Detect language for NGA exhibitions
                    language = event_data.get('language', 'English')
                    if not language or language == 'English':
                        try:
                            response = scraper.get(url, timeout=15)
                            soup = BeautifulSoup(response.text, 'html.parser')
                            page_text = soup.get_text()
                            language = _detect_language(soup, event_data.get('title'), event_data.get('description'), page_text)
                        except:
                            language = 'English'
                    
                    # Extract times if available (exhibitions can have opening receptions, special events, etc.)
                    start_time_str = None
                    end_time_str = None
                    if event_data.get('start_time'):
                        start_time_obj = event_data.get('start_time')
                        if isinstance(start_time_obj, time):
                            start_time_str = start_time_obj.strftime('%H:%M')
                        elif isinstance(start_time_obj, str):
                            start_time_str = start_time_obj
                    if event_data.get('end_time'):
                        end_time_obj = event_data.get('end_time')
                        if isinstance(end_time_obj, time):
                            end_time_str = end_time_obj.strftime('%H:%M')
                        elif isinstance(end_time_obj, str):
                            end_time_str = end_time_obj
                    
                    return {
                        'title': event_data.get('title'),
                        'description': event_data.get('description'),
                        'start_date': start_date_str,
                        'end_date': end_date_str,
                        'start_time': start_time_str,  # Exhibitions can have times
                        'end_time': end_time_str,
                        'location': event_data.get('location'),
                        'image_url': event_data.get('image_url'),
                        'event_type': event_data.get('event_type', 'exhibition'),
                        'is_online': event_data.get('is_online', False),
                        'is_registration_required': event_data.get('is_registration_required', False),
                        'registration_url': event_data.get('registration_url'),
                        'registration_info': event_data.get('registration_info'),
                        'schedule_info': None,
                        'days_of_week': [],
                        'language': language
                    }
            # Check if it's a calendar/tour URL
            elif '/calendar/' in url.lower():
                logger.info(f"🎯 Detected NGA calendar/tour page - using specialized extraction")
                from scripts.nga_comprehensive_scraper import scrape_nga_tour_page, create_scraper
                
                scraper = create_scraper()
                event_data = scrape_nga_tour_page(url, scraper)
                if event_data:
                    logger.info(f"✅ Successfully extracted using NGA tour scraper")
                    # Convert time objects to strings if needed
                    from datetime import time as dt_time
                    start_time_str = None
                    end_time_str = None
                    if event_data.get('start_time'):
                        start_time_obj = event_data.get('start_time')
                        if isinstance(start_time_obj, dt_time):
                            start_time_str = start_time_obj.isoformat()
                        else:
                            start_time_str = str(start_time_obj)
                    if event_data.get('end_time'):
                        end_time_obj = event_data.get('end_time')
                        if isinstance(end_time_obj, dt_time):
                            end_time_str = end_time_obj.isoformat()
                        else:
                            end_time_str = str(end_time_obj)
                    
                    # Convert date object to string if needed
                    start_date_str = None
                    if event_data.get('start_date'):
                        start_date_obj = event_data.get('start_date')
                        if hasattr(start_date_obj, 'isoformat'):
                            start_date_str = start_date_obj.isoformat()
                        else:
                            start_date_str = str(start_date_obj)
                    
                    # Detect language for NGA tour pages
                    language = event_data.get('language', 'English')
                    if not language or language == 'English':
                        # Re-detect from the page if not already set
                        try:
                            response = scraper.get(url, timeout=15)
                            soup = BeautifulSoup(response.text, 'html.parser')
                            page_text = soup.get_text()
                            language = _detect_language(soup, event_data.get('title'), event_data.get('description'), page_text)
                        except:
                            language = 'English'  # Fallback to default
                    
                    return {
                        'title': event_data.get('title'),
                        'description': event_data.get('description'),
                        'start_date': start_date_str,
                        'start_time': start_time_str,
                        'end_time': end_time_str,
                        'location': event_data.get('location'),
                        'image_url': event_data.get('image_url'),
                        'event_type': event_data.get('event_type', 'tour'),
                        'is_online': event_data.get('is_online', False),
                        'is_registration_required': event_data.get('is_registration_required', False),
                        'registration_url': event_data.get('registration_url'),
                        'registration_info': event_data.get('registration_info'),
                        'schedule_info': None,
                        'days_of_week': [],
                        'language': language
                    }
        except Exception as e:
            logger.warning(f"NGA specialized extraction failed: {e}, falling back to general scraper")
            # Fall through to general scraper
    
    bot_detected = False
    
    try:
        import cloudscraper
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Create a cloudscraper session
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        
        # Disable SSL verification (like venue scraper does)
        scraper.verify = False
        
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
        # Extract multiple images
        all_images = _extract_images(soup, url, max_images=10)
        image_url = all_images[0] if all_images else None
        additional_images = all_images[1:] if len(all_images) > 1 else []
        meeting_point = _extract_meeting_point(page_text)
        schedule_info, days_of_week, start_time, end_time = _extract_schedule(page_text)
        start_date = _extract_date(page_text, url)
        event_type = _determine_event_type(title, description, page_text, url)
        language = _detect_language(soup, title, description, page_text)
        
        # Skip non-English language events
        if language and language.lower() != 'english':
            logger.info(f"⚠️ Skipping non-English event: '{title}' (language: {language})")
            return None
        
        result = {
            'title': title,
            'description': description,
            'start_date': start_date.isoformat() if start_date else None,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'location': meeting_point,
            'image_url': image_url,
            'schedule_info': schedule_info,
            'days_of_week': days_of_week,
            'event_type': event_type,
            'language': language
        }
        
        # Add additional images if any
        if additional_images:
            result['additional_images'] = additional_images
        
        return result
        
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
        # Clean URL: remove evd parameter (it's just for linking to specific date/time)
        # Save the canonical base URL instead
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query)
        if 'evd' in query_params:
            # Remove evd parameter
            del query_params['evd']
            # Reconstruct URL without evd
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            clean_url = urllib.parse.urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))
            # Remove trailing ? if no query params remain
            if clean_url.endswith('?'):
                clean_url = clean_url[:-1]
            logger.info(f"   🧹 Cleaned URL: removed evd parameter -> {clean_url}")
            url = clean_url
        # Check if this is an NGA exhibition - use specialized scraper
        event_data = None
        if 'nga.gov' in url.lower() and '/exhibitions/' in url.lower():
            try:
                from scripts.nga_comprehensive_scraper import scrape_nga_exhibition_page, create_scraper
                scraper = create_scraper()
                event_data = scrape_nga_exhibition_page(url, scraper)
                if event_data:
                    logger.info(f"✅ Successfully extracted NGA exhibition using specialized scraper")
            except Exception as e:
                logger.warning(f"NGA exhibition scraper failed: {e}")
                event_data = None
        
        # Check if this is a Finding Awe event - use dedicated scraper
        if not event_data and 'finding-awe' in url.lower():
            try:
                from scripts.nga_finding_awe_scraper import scrape_individual_event
                event_data = scrape_individual_event(url)
                if event_data:
                    # Use scraped data, but allow override_data to override specific fields
                    title = override_data.get('title') if override_data and override_data.get('title') else event_data.get('title')
                    if title:
                        title = title.strip()
                        # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                        from scripts.utils import is_category_heading
                        if is_category_heading(title):
                            logger.warning(f"   ⏭️ Skipping category heading: '{title}'")
                            event_data = None  # Skip this event
                    if event_data:  # Only proceed if not skipped
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
        
        # Handle NGA exhibition data if extracted
        if event_data and '/exhibitions/' in url.lower():
            # Use scraped data, but allow override_data to override specific fields
            title = override_data.get('title') if override_data and override_data.get('title') else event_data.get('title')
            if title:
                title = title.strip()
                # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                from scripts.utils import is_category_heading
                if is_category_heading(title):
                    logger.warning(f"   ⏭️ Skipping category heading: '{title}'")
                    event_data = None  # Skip this event
            if event_data:  # Only proceed if not skipped
                description = override_data.get('description') if override_data and override_data.get('description') else event_data.get('description')
                image_url = override_data.get('image_url') if override_data and override_data.get('image_url') else event_data.get('image_url')
                meeting_point = override_data.get('location') if override_data and override_data.get('location') else event_data.get('location')
                
                # Parse dates
                start_date = None
                end_date = None
                if override_data and override_data.get('start_date'):
                    try:
                        start_date = datetime.strptime(override_data['start_date'], '%Y-%m-%d').date()
                    except:
                        pass
                if not start_date and event_data.get('start_date'):
                    try:
                        if isinstance(event_data['start_date'], str):
                            start_date = datetime.strptime(event_data['start_date'], '%Y-%m-%d').date()
                        else:
                            start_date = event_data['start_date']
                    except:
                        pass
                
                if override_data and override_data.get('end_date'):
                    try:
                        end_date = datetime.strptime(override_data['end_date'], '%Y-%m-%d').date()
                    except:
                        pass
                if not end_date and event_data.get('end_date'):
                    try:
                        if isinstance(event_data['end_date'], str):
                            end_date = datetime.strptime(event_data['end_date'], '%Y-%m-%d').date()
                        else:
                            end_date = event_data['end_date']
                    except:
                        pass
                
                # Extract times if available (exhibitions can have opening receptions, special events, etc.)
                start_time = None
                end_time = None
                if event_data.get('start_time'):
                    start_time_str = event_data.get('start_time')
                    if isinstance(start_time_str, str):
                        # Try to parse time string
                        try:
                            if ':' in start_time_str:
                                parts = start_time_str.split(':')
                                start_time = time(int(parts[0]), int(parts[1]))
                            else:
                                start_time = time(int(start_time_str), 0)
                        except (ValueError, IndexError):
                            pass
                if event_data.get('end_time'):
                    end_time_str = event_data.get('end_time')
                    if isinstance(end_time_str, str):
                        # Try to parse time string
                        try:
                            if ':' in end_time_str:
                                parts = end_time_str.split(':')
                                end_time = time(int(parts[0]), int(parts[1]))
                            else:
                                end_time = time(int(end_time_str), 0)
                        except (ValueError, IndexError):
                            pass
                
                schedule_info = None
                days_of_week = []
                event_type = event_data.get('event_type', 'exhibition')
        
        # Check if this is an NPG event - use extract_event_data_from_url which has NPG-specific logic
        if not event_data and 'npg.si.edu' in url.lower() and '/event/' in url.lower():
            try:
                logger.info(f"🎯 Detected NPG event in scrape_event_from_url - using extract_event_data_from_url")
                event_data = extract_event_data_from_url(url)
                if event_data and event_data.get('title'):
                    logger.info(f"✅ Successfully extracted NPG event data")
                    # Process NPG event_data to extract dates and times
                    title = override_data.get('title') if override_data and override_data.get('title') else event_data.get('title')
                    if title:
                        title = title.strip()
                        # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                        from scripts.utils import is_category_heading
                        if is_category_heading(title):
                            logger.warning(f"   ⏭️ Skipping category heading: '{title}'")
                            event_data = None  # Skip this event
                    if event_data:  # Only proceed if not skipped
                        description = override_data.get('description') if override_data and override_data.get('description') else event_data.get('description')
                        image_url = override_data.get('image_url') if override_data and override_data.get('image_url') else event_data.get('image_url')
                        meeting_point = override_data.get('location') if override_data and override_data.get('location') else event_data.get('location')
                        
                        # Parse dates from event_data
                        start_date = None
                        end_date = None
                        if override_data and override_data.get('start_date'):
                            try:
                                start_date = datetime.strptime(override_data['start_date'], '%Y-%m-%d').date()
                            except:
                                pass
                        if not start_date and event_data.get('start_date'):
                            try:
                                if isinstance(event_data['start_date'], str):
                                    start_date = datetime.strptime(event_data['start_date'], '%Y-%m-%d').date()
                                else:
                                    start_date = event_data['start_date']
                            except:
                                pass
                        
                        if override_data and override_data.get('end_date'):
                            try:
                                end_date = datetime.strptime(override_data['end_date'], '%Y-%m-%d').date()
                            except:
                                pass
                        if not end_date and event_data.get('end_date'):
                            try:
                                if isinstance(event_data['end_date'], str):
                                    end_date = datetime.strptime(event_data['end_date'], '%Y-%m-%d').date()
                                else:
                                    end_date = event_data['end_date']
                            except:
                                pass
                        elif start_date:
                            end_date = start_date
                        
                        # Parse times from event_data
                        from datetime import time as dt_time
                        start_time = None
                        end_time = None
                        
                        # Parse start_time from string like "5:30 p.m." or "5:30pm"
                        if override_data and override_data.get('start_time'):
                            start_time_str = override_data['start_time']
                            start_time = _parse_time_string_npg(start_time_str)
                        elif event_data.get('start_time'):
                            start_time_str = event_data['start_time']
                            start_time = _parse_time_string_npg(start_time_str)
                        
                        # Parse end_time
                        if override_data and override_data.get('end_time'):
                            end_time_str = override_data['end_time']
                            end_time = _parse_time_string_npg(end_time_str)
                        elif event_data.get('end_time'):
                            end_time_str = event_data['end_time']
                            end_time = _parse_time_string_npg(end_time_str)
                        
                        schedule_info = None
                        days_of_week = []
                        event_type = event_data.get('event_type', 'event')
                        
                        # Store extracted values back in event_data dict so they're accessible later
                        # when creating/updating events. Keep the original event_data dict intact
                        # with all fields (registration_info, price, etc.) for later use.
                        # The local variables (title, description, etc.) are already set above
                        # and will be used directly in event creation.
                        event_data['processed'] = True  # Flag to indicate this is already processed
                        # Ensure all extracted fields are in event_data dict
                        event_data['title'] = title
                        event_data['description'] = description
                        event_data['start_date'] = start_date
                        event_data['end_date'] = end_date
                        event_data['start_time'] = start_time
                        event_data['end_time'] = end_time
                        event_data['location'] = meeting_point
                        event_data['image_url'] = image_url
                        event_data['event_type'] = event_type
            except Exception as e:
                logger.warning(f"NPG extraction failed in scrape_event_from_url: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                event_data = None
        
        # Check if this is an OCMA event - use extract_event_data_from_url which has OCMA-specific logic
        if not event_data and 'ocma.art' in url.lower() and '/calendar/' in url.lower():
            try:
                logger.info(f"🎯 Detected OCMA event in scrape_event_from_url - using extract_event_data_from_url")
                event_data = extract_event_data_from_url(url)
                if event_data and event_data.get('title'):
                    logger.info(f"✅ Successfully extracted OCMA event data")
                    # Process OCMA event_data to extract dates and times
                    title = override_data.get('title') if override_data and override_data.get('title') else event_data.get('title')
                    if title:
                        title = title.strip()
                        # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                        from scripts.utils import is_category_heading
                        if is_category_heading(title):
                            logger.warning(f"   ⏭️ Skipping category heading: '{title}'")
                            event_data = None  # Skip this event
                    if event_data:  # Only proceed if not skipped
                        description = override_data.get('description') if override_data and override_data.get('description') else event_data.get('description')
                        image_url = override_data.get('image_url') if override_data and override_data.get('image_url') else event_data.get('image_url')
                        meeting_point = override_data.get('location') if override_data and override_data.get('location') else event_data.get('location')
                        
                        # Parse dates from event_data
                        start_date = None
                        end_date = None
                        if override_data and override_data.get('start_date'):
                            try:
                                start_date = datetime.strptime(override_data['start_date'], '%Y-%m-%d').date()
                            except:
                                pass
                        if not start_date and event_data.get('start_date'):
                            try:
                                if isinstance(event_data['start_date'], str):
                                    start_date = datetime.strptime(event_data['start_date'], '%Y-%m-%d').date()
                                else:
                                    start_date = event_data['start_date']
                            except:
                                pass
                        
                        if override_data and override_data.get('end_date'):
                            try:
                                end_date = datetime.strptime(override_data['end_date'], '%Y-%m-%d').date()
                            except:
                                pass
                        if not end_date and event_data.get('end_date'):
                            try:
                                if isinstance(event_data['end_date'], str):
                                    end_date = datetime.strptime(event_data['end_date'], '%Y-%m-%d').date()
                                else:
                                    end_date = event_data['end_date']
                            except:
                                pass
                        
                        # Parse times from event_data
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
                    event_type = event_data.get('event_type', 'event')
            except Exception as e:
                logger.warning(f"OCMA extraction failed in scrape_event_from_url: {e}")
                event_data = None
        
        # Use override data if provided, otherwise scrape
        # Skip if NPG data was already extracted (event_data will have 'processed' flag)
        if override_data and any(override_data.values()) and not (event_data and event_data.get('processed')):
            title = override_data.get('title', '').strip() if override_data.get('title') else None
            if title:
                # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                from scripts.utils import is_category_heading
                if is_category_heading(title):
                    logger.warning(f"   ⏭️ Skipping category heading: '{title}'")
                    return {
                        'success': False,
                        'events_created': 0,
                        'events': [],
                        'error': f'Invalid title: "{title}" is a category heading, not an event title'
                    }
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
            
            # Initialize event_type to None - will be determined later
            event_type = None
        elif not event_data or not event_data.get('processed'):
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
        
        # For exhibitions, use the scraped start_date if available, otherwise use period_start
        if event_data and '/exhibitions/' in url.lower() and 'start_date' in locals() and start_date:
            event_dates = [start_date]  # Use the actual exhibition start date
        # For NPG, OCMA events or when start_date is provided in override_data, use the scraped start_date
        elif (('npg.si.edu' in url.lower() and '/event/' in url.lower() and 'start_date' in locals() and start_date) or
              ('ocma.art' in url.lower() and '/calendar/' in url.lower() and 'start_date' in locals() and start_date) or
              ('start_date' in locals() and start_date)):
            event_dates = [start_date]  # Use the actual event start date
        elif days_of_week:
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
        
        # Validate title before creating events
        if title:
            from scripts.utils import is_category_heading
            if is_category_heading(title):
                logger.warning(f"   ⏭️ Skipping category heading: '{title}'")
                return {
                    'success': False,
                    'events_created': 0,
                    'events': [],
                    'error': f'Invalid title: "{title}" is a category heading, not an event title'
                }
        
        # Create events in database
        events_created = 0
        created_events = []
        
        with app.app_context():
            for event_date in event_dates:
                # Check if event already exists - for exhibitions/tours, match by URL first
                existing = None
                
                # For exhibitions and tours, match by URL (they're typically single events with unique URLs)
                # Check event_type safely (it might not be set yet)
                event_type_lower = (event_type or '').lower()
                if url and ('exhibition' in event_type_lower or 'tour' in event_type_lower or '/exhibitions/' in url.lower() or '/calendar/' in url.lower()):
                    # Normalize URL for comparison (remove trailing slash, normalize protocol)
                    normalized_url = url.rstrip('/')
                    # Also try without protocol for more flexible matching
                    url_without_protocol = normalized_url.replace('http://', '').replace('https://', '')
                    
                    # For URL-based events (exhibitions, calendar events), match by URL first
                    # Try exact URL match or URL with trailing slash, with or without protocol
                    existing = Event.query.filter(
                        (Event.url == url) | 
                        (Event.url == normalized_url) | 
                        (Event.url == url.rstrip('/')) |
                        (Event.url.like(f"{normalized_url}%")) | 
                        (Event.url.like(f"{url}%")) |
                        (Event.url.like(f"%{url_without_protocol}%"))
                    ).filter_by(city_id=city.id).first()
                    
                    # If not found by URL in same city, try without city filter (in case city was wrong)
                    if not existing:
                        existing = Event.query.filter(
                            (Event.url == url) | 
                            (Event.url == normalized_url) | 
                            (Event.url == url.rstrip('/')) |
                            (Event.url.like(f"{normalized_url}%")) | 
                            (Event.url.like(f"{url}%")) |
                            (Event.url.like(f"%{url_without_protocol}%"))
                        ).first()
                    
                    # If still not found by URL, try by title + venue (without date requirement for URL-based events)
                    if not existing and title:
                        filter_dict = {
                            'city_id': city.id
                        }
                        if venue:
                            filter_dict['venue_id'] = venue.id
                        # Match by title and venue, regardless of date (since URL-based events are unique by URL)
                        existing = Event.query.filter_by(**filter_dict).filter(
                            db.func.lower(Event.title) == db.func.lower(title)
                        ).first()
                        
                        # If still not found, try by title + date + venue as fallback
                        if not existing:
                            filter_dict['start_date'] = event_date
                            existing = Event.query.filter_by(**filter_dict).filter(
                                db.func.lower(Event.title) == db.func.lower(title)
                            ).first()
                else:
                    # For other events, use standard matching
                    filter_dict = {
                        'url': url,
                        'start_date': event_date,
                        'city_id': city.id
                    }
                    if venue:
                        filter_dict['venue_id'] = venue.id
                    existing = Event.query.filter_by(**filter_dict).first()
                
                # If existing event found, update it instead of skipping
                if existing:
                    logger.info(f"Event already exists (ID: {existing.id}), updating with new data")
                    updated = False
                    
                    # Update fields if new data is available or existing field is None
                    if title and (not existing.title or title != existing.title):
                        existing.title = title
                        updated = True
                    if description and (not existing.description or description != existing.description):
                        existing.description = description
                        updated = True
                    if url and (not existing.url or url != existing.url):
                        existing.url = url
                        updated = True
                    if image_url and (not existing.image_url or image_url != existing.image_url):
                        existing.image_url = image_url
                        updated = True
                    if meeting_point and (not existing.start_location or meeting_point != existing.start_location):
                        existing.start_location = meeting_point
                        updated = True
                    if event_type and (not existing.event_type or event_type != existing.event_type):
                        existing.event_type = event_type
                        updated = True
                    # Update dates if provided
                    if event_date and (not existing.start_date or event_date != existing.start_date):
                        existing.start_date = event_date
                        updated = True
                    # Update end_date: use extracted end_date if available, otherwise use start_date for single-day events
                    event_end_date = None
                    if 'end_date' in locals() and end_date:
                        event_end_date = end_date
                    elif event_date:
                        event_end_date = event_date  # For single-day events, end_date = start_date
                    if event_end_date and (not existing.end_date or event_end_date != existing.end_date):
                        existing.end_date = event_end_date
                        updated = True
                    # Update times if provided (for tours)
                    if start_time and (not existing.start_time or start_time != existing.start_time):
                        existing.start_time = start_time
                        updated = True
                    if end_time and (not existing.end_time or end_time != existing.end_time):
                        existing.end_time = end_time
                        updated = True
                    # Update language if provided
                    language = 'English'  # Default
                    if override_data and override_data.get('language'):
                        language = override_data.get('language')
                    elif 'event_data' in locals() and event_data and event_data.get('language'):
                        language = event_data.get('language')
                    else:
                        # Try to detect language if not provided
                        try:
                            import cloudscraper
                            scraper = cloudscraper.create_scraper()
                            response = scraper.get(url, timeout=15)
                            soup = BeautifulSoup(response.text, 'html.parser')
                            page_text = soup.get_text()
                            language = _detect_language(soup, title, description, page_text)
                        except:
                            language = existing.language or 'English'  # Keep existing or default
                    
                    if language and (not existing.language or language != existing.language):
                        existing.language = language
                        updated = True
                    
                    # Update registration fields if available (from NPG events)
                    if hasattr(existing, 'is_registration_required'):
                        reg_required = False
                        if override_data and override_data.get('is_registration_required') is not None:
                            reg_required = override_data.get('is_registration_required')
                        elif 'event_data' in locals() and event_data and event_data.get('is_registration_required') is not None:
                            reg_required = event_data.get('is_registration_required')
                        if existing.is_registration_required != reg_required:
                            existing.is_registration_required = reg_required
                            updated = True
                    
                    if hasattr(existing, 'registration_url'):
                        reg_url = None
                        if override_data and override_data.get('registration_url'):
                            reg_url = override_data.get('registration_url')
                        elif 'event_data' in locals() and event_data and event_data.get('registration_url'):
                            reg_url = event_data.get('registration_url')
                        if reg_url and existing.registration_url != reg_url:
                            existing.registration_url = reg_url
                            updated = True
                    
                    if hasattr(existing, 'registration_info'):
                        reg_info = None
                        # Check override_data first, then event_data, to get registration_info
                        if override_data and override_data.get('registration_info'):
                            reg_info = override_data.get('registration_info')
                        elif 'event_data' in locals() and event_data and event_data.get('registration_info'):
                            reg_info = event_data.get('registration_info')
                        # Update if we have registration_info and it's different
                        if reg_info is not None:
                            if not existing.registration_info or existing.registration_info != reg_info:
                                existing.registration_info = reg_info
                                updated = True
                    
                    if hasattr(existing, 'price'):
                        event_price = None
                        if override_data and override_data.get('price') is not None:
                            price_val = override_data.get('price')
                            # Convert "Free" string to 0.0 float
                            if isinstance(price_val, str):
                                if price_val.lower() in ['free', '0', '0.0']:
                                    event_price = 0.0
                                else:
                                    try:
                                        event_price = float(price_val)
                                    except (ValueError, TypeError):
                                        event_price = None
                            else:
                                event_price = price_val
                        elif 'event_data' in locals() and event_data and event_data.get('price') is not None:
                            price_val = event_data.get('price')
                            # Convert "Free" string to 0.0 float
                            if isinstance(price_val, str):
                                if price_val.lower() in ['free', '0', '0.0']:
                                    event_price = 0.0
                                else:
                                    try:
                                        event_price = float(price_val)
                                    except (ValueError, TypeError):
                                        event_price = None
                            else:
                                event_price = price_val
                        if event_price is not None and existing.price != event_price:
                            existing.price = event_price
                            updated = True
                    
                    if updated:
                        db.session.commit()
                        logger.info(f"✅ Updated existing event: {existing.title} (ID: {existing.id})")
                    else:
                        logger.info(f"ℹ️  Event already up to date: {existing.title} (ID: {existing.id})")
                    
                    events_created += 1  # Count as "created" for the response
                    created_events.append({
                        'title': existing.title,
                        'start_date': existing.start_date.isoformat() if existing.start_date else None,
                        'start_time': existing.start_time.isoformat() if existing.start_time else None,
                        'end_time': existing.end_time.isoformat() if existing.end_time else None,
                        'description': existing.description[:100] if existing.description else None
                    })
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
                # For exhibitions, use the scraped end_date if available
                # For single-day events, end_date should be the same as start_date
                event_end_date = event_date  # Default to same as start_date for single-day events
                if 'end_date' in locals() and end_date:
                    event_end_date = end_date
                elif event_date:
                    event_end_date = event_date
                
                # Get language from event_data or override_data, or detect it
                language = 'English'  # Default
                if override_data and override_data.get('language'):
                    language = override_data.get('language')
                elif 'event_data' in locals() and event_data and event_data.get('language'):
                    language = event_data.get('language')
                elif 'language' in locals():
                    pass  # Already set from detection
                else:
                    # Detect language if not already set
                    try:
                        import cloudscraper
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url, timeout=15)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        page_text = soup.get_text()
                        language = _detect_language(soup, title, description, page_text)
                    except:
                        language = 'English'  # Fallback to default
                
                # Get registration and price fields from event_data or override_data
                # Prefer override_data if provided, but fall back to event_data for missing fields
                is_registration_required = None
                registration_url = None
                registration_info = None
                event_price = None
                
                # Check override_data first for these fields
                if override_data:
                    # Use override_data values if they're provided
                    if 'is_registration_required' in override_data:
                        is_registration_required = override_data.get('is_registration_required')
                    if 'registration_url' in override_data:
                        registration_url = override_data.get('registration_url')
                    if 'registration_info' in override_data:
                        registration_info = override_data.get('registration_info')
                    if 'price' in override_data:
                        price_val = override_data.get('price')
                        # Convert "Free" string to 0.0 float
                        if isinstance(price_val, str):
                            if price_val.lower() in ['free', '0', '0.0']:
                                event_price = 0.0
                            else:
                                try:
                                    event_price = float(price_val)
                                except (ValueError, TypeError):
                                    event_price = None
                        else:
                            event_price = price_val
                
                # Fill in missing values from event_data if available
                if 'event_data' in locals() and event_data:
                    if is_registration_required is None and event_data.get('is_registration_required') is not None:
                        is_registration_required = event_data.get('is_registration_required', False)
                    if registration_url is None and event_data.get('registration_url'):
                        registration_url = event_data.get('registration_url')
                    if registration_info is None and event_data.get('registration_info'):
                        registration_info = event_data.get('registration_info')
                    if event_price is None and event_data.get('price') is not None:
                        price_val = event_data.get('price')
                        # Convert "Free" string to 0.0 float
                        if isinstance(price_val, str):
                            if price_val.lower() in ['free', '0', '0.0']:
                                event_price = 0.0
                            else:
                                try:
                                    event_price = float(price_val)
                                except (ValueError, TypeError):
                                    event_price = None
                        else:
                            event_price = price_val
                
                # Set defaults if still None
                if is_registration_required is None:
                    is_registration_required = False
                
                # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                from scripts.utils import is_category_heading
                if is_category_heading(title):
                    logger.debug(f"   ⏭️ Skipping category heading: '{title}'")
                    continue
                
                # Detect if event is baby-friendly
                is_baby_friendly = False
                title_lower = title.lower()
                description_lower = (description or '').lower()
                combined_text = f"{title_lower} {description_lower}"
                
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
                
                if any(keyword in combined_text for keyword in baby_keywords):
                    is_baby_friendly = True
                    logger.info(f"   👶 Detected baby-friendly event: '{title}'")
                
                event = Event(
                    title=title,
                    description=description,
                    start_date=event_date,
                    end_date=event_end_date,
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
                    is_selected=True,  # Show events from quick link discovery
                    language=language
                )
                
                # Add registration and price fields if they exist on the model
                if hasattr(Event, 'is_registration_required'):
                    event.is_registration_required = is_registration_required
                if hasattr(Event, 'registration_url'):
                    event.registration_url = registration_url
                if hasattr(Event, 'registration_info'):
                    event.registration_info = registration_info
                if hasattr(Event, 'price'):
                    event.price = event_price
                
                # Set baby-friendly flag if detected
                if hasattr(Event, 'is_baby_friendly'):
                    event.is_baby_friendly = is_baby_friendly
                
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


def _clean_title(title):
    """Clean and normalize title text to fix common issues"""
    if not title:
        return title
    
    import re
    
    # Remove trailing commas and whitespace
    title = re.sub(r',\s*$', '', title)
    title = title.strip()
    
    # Remove dates from title (e.g., "December 10, 2025," or "Dec 10, 2025")
    # Pattern: Month Day, Year or Month Day Year
    date_patterns = [
        r'\s*[A-Z][a-z]+\s+\d{1,2},?\s+\d{4},?\s*$',  # "December 10, 2025," or "December 10, 2025"
        r'\s*[A-Z][a-z]{2,3}\.?\s+\d{1,2},?\s+\d{4},?\s*$',  # "Dec. 10, 2025," or "Dec 10, 2025"
        r'\s*\d{1,2}/\d{1,2}/\d{4},?\s*$',  # "12/10/2025,"
        r'\s*\d{1,2}-\d{1,2}-\d{4},?\s*$',  # "12-10-2025,"
    ]
    for pattern in date_patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    
    # Fix missing spaces after apostrophes (e.g., "Bellows'sLove" -> "Bellows's Love")
    title = re.sub(r"([a-z]'s)([A-Z])", r"\1 \2", title)
    
    # Fix missing spaces after colons (e.g., "Title:Subtitle" -> "Title: Subtitle")
    title = re.sub(r"([^:]):([A-Za-z])", r"\1: \2", title)
    
    # Fix missing spaces after periods (e.g., "Mr.John" -> "Mr. John")
    title = re.sub(r"([a-z])\.([A-Z])", r"\1. \2", title)
    
    # Fix missing spaces before capital letters after lowercase (e.g., "wordWord" -> "word Word")
    # But be careful not to break acronyms or proper nouns
    title = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", title)
    
    # Normalize multiple spaces to single space
    title = re.sub(r'\s+', ' ', title)
    
    # Strip leading/trailing whitespace
    title = title.strip()
    
    return title


def _detect_language(soup, title, description, page_text):
    """
    Detect event language from multiple sources:
    1. Language tags in HTML (e.g., "En español", "In Spanish")
    2. Title analysis (NLP detection of Spanish/French/German/etc.)
    3. Description analysis
    4. Common language indicators in page content
    
    Returns:
        str: Language name (e.g., "Spanish", "English", "French") or "English" as default
    """
    if not title and not description and not page_text:
        return 'English'  # Default
    
    # Combine all text for analysis
    combined_text = f"{title} {description} {page_text}".lower()
    
    # Method 1: Check for explicit language tags in HTML
    # Look for common language indicators in tags, buttons, badges, etc.
    language_indicators = {
        'spanish': [
            r'\ben\s+español\b',
            r'\bin\s+spanish\b',
            r'\bespañol\b',
            r'\bspanish\b',
            r'\bvisita\s+en\s+español\b',
            r'\btour\s+en\s+español\b',
        ],
        'french': [
            r'\ben\s+français\b',
            r'\bin\s+french\b',
            r'\bfrançais\b',
            r'\bfrench\b',
        ],
        'german': [
            r'\bauf\s+deutsch\b',
            r'\bin\s+german\b',
            r'\bdeutsch\b',
            r'\bgerman\b',
        ],
    }
    
    # Check page HTML for language tags/badges
    # Look for common patterns: <span>, <div>, <li> with language text
    for lang, patterns in language_indicators.items():
        for pattern in patterns:
            # Check in text content
            if re.search(pattern, combined_text, re.IGNORECASE):
                logger.info(f"🌐 Detected language '{lang}' from tag/indicator: {pattern}")
                return lang.capitalize()
            
            # Check in HTML elements (tags, badges, buttons)
            for tag in ['span', 'div', 'li', 'p', 'a', 'button', 'label']:
                elements = soup.find_all(tag, string=re.compile(pattern, re.IGNORECASE))
                if elements:
                    logger.info(f"🌐 Detected language '{lang}' from HTML tag: {tag}")
                    return lang.capitalize()
    
    # Method 2: NLP-based detection from title/description
    # Check for common Spanish words and patterns
    spanish_indicators = [
        # Common Spanish words
        r'\b(que|de|la|el|en|y|a|es|son|para|con|por|del|las|los|una|un|este|esta|estos|estas)\b',
        # Spanish-specific words in event contexts
        r'\b(visita|galería|galerías|exposición|exposiciones|arte|artista|artistas|museo|museos)\b',
        r'\b(conversaci[oó]n|conversaciones|charla|charlas|taller|talleres|recorrido|recorridos)\b',
        r'\b(desde|hasta|actualidad|contemporáneo|contemporánea|moderno|moderna)\b',
        # Spanish accented characters in context
        r'[áéíóúñü]',
    ]
    
    french_indicators = [
        r'\b(visite|galerie|galeries|exposition|expositions|art|artiste|artistes|musée|musées)\b',
        r'\b(conversation|conversations|conférence|conférences|atelier|ateliers|parcours|parcours)\b',
        r'[àâäéèêëïîôùûüÿç]',
    ]
    
    german_indicators = [
        r'\b(besuch|galerie|galerien|ausstellung|ausstellungen|kunst|künstler|künstlerin|museum|museen)\b',
        r'\b(gespräch|gespräche|vortrag|vorträge|workshop|workshops|rundgang|rundgänge)\b',
        r'[äöüß]',
    ]
    
    # Count indicators for each language
    spanish_count = sum(len(re.findall(pattern, combined_text, re.IGNORECASE)) for pattern in spanish_indicators)
    french_count = sum(len(re.findall(pattern, combined_text, re.IGNORECASE)) for pattern in french_indicators)
    german_count = sum(len(re.findall(pattern, combined_text, re.IGNORECASE)) for pattern in german_indicators)
    
    # Check title specifically (most reliable indicator)
    title_lower = title.lower() if title else ''
    title_spanish = sum(len(re.findall(pattern, title_lower, re.IGNORECASE)) for pattern in spanish_indicators)
    title_french = sum(len(re.findall(pattern, title_lower, re.IGNORECASE)) for pattern in french_indicators)
    title_german = sum(len(re.findall(pattern, title_lower, re.IGNORECASE)) for pattern in german_indicators)
    
    # Weight title more heavily (title is most reliable)
    total_spanish = spanish_count + (title_spanish * 3)
    total_french = french_count + (title_french * 3)
    total_german = german_count + (title_german * 3)
    
    # Determine language based on highest count
    if total_spanish > 2:  # Threshold to avoid false positives
        logger.info(f"🌐 Detected language 'Spanish' from NLP analysis (score: {total_spanish})")
        return 'Spanish'
    elif total_french > 2:
        logger.info(f"🌐 Detected language 'French' from NLP analysis (score: {total_french})")
        return 'French'
    elif total_german > 2:
        logger.info(f"🌐 Detected language 'German' from NLP analysis (score: {total_german})")
        return 'German'
    
    # Method 3: Check HTML lang attribute
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        lang_attr = html_tag.get('lang').lower()
        if lang_attr.startswith('es'):
            return 'Spanish'
        elif lang_attr.startswith('fr'):
            return 'French'
        elif lang_attr.startswith('de'):
            return 'German'
    
    # Default to English
    return 'English'


def _extract_title(soup, url):
    """Extract event title from page"""
    # Try page title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Clean up title
        if '|' in title:
            title = title.split('|')[0].strip()
        title = _clean_title(title)
        if title and title != 'Untitled':
            return title
    
    # Try h1
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        return _clean_title(title)
    
    # Try URL
    url_parts = url.split('/')
    if url_parts:
        # Get last non-empty part
        for part in reversed(url_parts):
            if part and part not in ['', 'events', 'tours']:
                # Convert URL slug to title
                title = part.replace('-', ' ').replace('_', ' ').title()
                return _clean_title(title)
    
    return 'Untitled Event'


def _extract_description(soup):
    """Extract event description from page using shared utility function"""
    from scripts.utils import extract_description_from_soup
    return extract_description_from_soup(soup, max_length=2000)


def _extract_image(soup, url):
    """Extract primary event image from page (backward compatible)"""
    images = _extract_images(soup, url)
    return images[0] if images else None


def _extract_images(soup, url, max_images=10):
    """
    Extract multiple images from page, prioritizing hero/feature images.
    Returns a list of image URLs, filtered to exclude logos, icons, and small images.
    
    Args:
        soup: BeautifulSoup object
        url: Base URL for resolving relative image paths
        max_images: Maximum number of images to return
    
    Returns:
        List of image URLs (strings)
    """
    from urllib.parse import urljoin
    
    image_urls = []
    seen_urls = set()
    
    # Skip patterns for non-content images
    skip_patterns = ['logo', 'icon', 'avatar', 'placeholder', 'spacer', 'button', 
                     'badge', 'social', 'share', 'menu', 'nav', 'header', 'footer']
    
    # Priority 1: Open Graph image (usually the best featured image)
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        img_url = og_image.get('content')
        if img_url not in seen_urls:
            if not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
            image_urls.append(img_url)
            seen_urls.add(img_url)
    
    # Priority 2: Hero/feature/main images (exhibition/event specific)
    hero_selectors = [
        ('img', {'class': re.compile(r'hero|feature|main|exhibition|event|banner', re.I)}),
        ('img', {'id': re.compile(r'hero|feature|main|exhibition|event|banner', re.I)}),
        ('img', {'data-class': re.compile(r'hero|feature|main|exhibition|event', re.I)}),
    ]
    
    for tag, attrs in hero_selectors:
        hero_imgs = soup.find_all(tag, attrs)
        for img in hero_imgs:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            if src and src not in seen_urls:
                # Check if it's a content image (not a logo/icon)
                if not any(skip in src.lower() for skip in skip_patterns):
                    if not src.startswith('http'):
                        src = urljoin(url, src)
                    image_urls.append(src)
                    seen_urls.add(src)
                    if len(image_urls) >= max_images:
                        return image_urls
    
    # Priority 3: Images in main content areas (article, main, content sections)
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|body|exhibition', re.I))
    if main_content:
        content_imgs = main_content.find_all('img')
        for img in content_imgs:
            # Skip if it's inside a figure/caption (might be decorative)
            if img.find_parent(['figure', 'figcaption']):
                continue
            
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            if src and src not in seen_urls:
                # Check if it's a content image
                if not any(skip in src.lower() for skip in skip_patterns):
                    # Check image size if available (prefer larger images)
                    img_width = img.get('width')
                    img_height = img.get('height')
                    is_substantial = True
                    
                    if img_width and img_height:
                        try:
                            width = int(img_width)
                            height = int(img_height)
                            # Prefer images that are at least 200x200 pixels
                            if width < 200 or height < 200:
                                is_substantial = False
                        except (ValueError, TypeError):
                            pass
                    
                    if is_substantial:
                        if not src.startswith('http'):
                            src = urljoin(url, src)
                        image_urls.append(src)
                        seen_urls.add(src)
                        if len(image_urls) >= max_images:
                            return image_urls
    
    # Priority 4: All other substantial images (fallback)
    all_imgs = soup.find_all('img')
    for img in all_imgs:
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
        if src and src not in seen_urls:
            # Check if it's a content image
            if not any(skip in src.lower() for skip in skip_patterns):
                # Check image size
                img_width = img.get('width')
                img_height = img.get('height')
                is_substantial = True
                
                if img_width and img_height:
                    try:
                        width = int(img_width)
                        height = int(img_height)
                        if width < 200 or height < 200:
                            is_substantial = False
                    except (ValueError, TypeError):
                        pass
                
                if is_substantial:
                    if not src.startswith('http'):
                        src = urljoin(url, src)
                    image_urls.append(src)
                    seen_urls.add(src)
                    if len(image_urls) >= max_images:
                        return image_urls
    
    return image_urls


def _extract_meeting_point(page_text):
    """Extract meeting point information"""
    meeting_patterns = [
        # NGA format: "West Building Main Floor, Gallery 40" - capture full string up to pipe or newline
        r'(West Building|East Building)[^|\n]*?(?:Main Floor|Ground Floor|Floor \d+)?[^|\n]*?Gallery\s+\d+[^|\n]*',
        # NGA format: "East Building Mezzanine Terrace" - capture building with special locations
        r'(West Building|East Building)[^|\n]*?(?:Mezzanine Terrace|Terrace|Mezzanine|Atrium|Lobby|Auditorium|Theater|Theatre)[^|\n]*',
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
    
    # Check for tour events FIRST (more specific, should take priority)
    tour_keywords = [
        'guided tour',
        'walking tour',
        'museum tour',
        'collection tour',
        'tour',
    ]
    
    if any(keyword in content for keyword in tour_keywords):
        return 'tour'
    
    # Check for talk/conversation events (after tours, since "talk" can appear in tour descriptions)
    talk_keywords = [
        'talks & conversations',
        'talk and conversation',
        'conversation',
        'discussion',
        'lecture',
        'speaker',
        'presentation',
        'finding awe',  # NGA specific talk series
        'workshop',  # Often includes talks
        'talk',  # Generic "talk" - check last to avoid false positives
    ]
    
    if any(keyword in content for keyword in talk_keywords):
        return 'talk'
    
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
    
    # Default to event for museum/venue events (generic catch-all)
    return 'event'


def _extract_date(page_text, url):
    """Extract date from page text or URL parameter"""
    from datetime import date
    import calendar
    
    # First, try to extract from URL parameter (e.g., evd=202601311530 or evd=202512161900)
    # evd can be 8 digits (YYYYMMDD) or 12 digits (YYYYMMDDHHMM)
    url_date_match = re.search(r'evd=(\d{8,12})', url)
    if url_date_match:
        evd_value = url_date_match.group(1)
        try:
            # Extract date (first 8 digits)
            year = int(evd_value[0:4])
            month = int(evd_value[4:6])
            day = int(evd_value[6:8])
            return date(year, month, day)
        except (ValueError, IndexError):
            pass
    
    # Try to extract from page text (e.g., "Saturday, Jan 31, 2026" or "Jan 16" or "January 16, 2025")
    date_patterns = [
        # NGA format: "Saturday, Jan 31, 2026"
        r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        # Standard format with full month: "January 31, 2026" or "January 31 2026"
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
        # Abbreviated month: "Jan 31, 2026" or "Jan 31 2026"
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        # Abbreviated month without year (assume current or next year): "Jan 16" or "Jan 16,"
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})(?:\s|,|$)',
        # ISO format: "2026-01-31"
        r'(\d{4})-(\d{2})-(\d{2})',
    ]
    
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    month_names_full = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    for pattern in date_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3:
                    # Check if first group is a month name
                    first_group = groups[0].lower()
                    if first_group in month_names_full or first_group[:3] in month_names:
                        # Month name format with year
                        month_name = first_group[:3] if first_group[:3] in month_names else first_group
                        day = int(groups[1])
                        year = int(groups[2])
                        month = month_names.get(month_name) or month_names_full.get(first_group)
                        if month:
                            return date(year, month, day)
                    elif groups[0].isdigit():
                        # ISO format
                        year = int(groups[0])
                        month = int(groups[1])
                        day = int(groups[2])
                        return date(year, month, day)
                elif len(groups) == 2:
                    # Abbreviated month without year (e.g., "Jan 16")
                    month_name = groups[0].lower()[:3]
                    day = int(groups[1])
                    month = month_names.get(month_name)
                    if month:
                        # Use current year, or next year if the month has already passed
                        today = date.today()
                        year = today.year
                        try:
                            test_date = date(year, month, day)
                            if test_date < today:
                                year += 1
                            return date(year, month, day)
                        except ValueError:
                            pass
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
    # Also: "December 6, 2025 | 11:30 am–12:30 pm" (Hirshhorn format)
    day_time_patterns = [
        # Hirshhorn format: "December 6, 2025 | 11:30 am–12:30 pm"
        r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s*([ap]m)\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap]m)',
        # NGA format: "Saturday, Jan 31, 2026 | 10:30 a.m. – 12:15 p.m."
        # This pattern captures the date in the middle: (Jan|Feb|...) (\d{1,2}), (\d{4})
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.',
        # Full pattern with time range (standard format)
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Weekday|Weekend)s?\s+(\d{1,2}):(\d{2})\s*([ap]m)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]m)',
        # Single time
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Weekday|Weekend)s?\s+(\d{1,2}):(\d{2})\s*([ap]m)',
        # Range of days with time
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*-\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2}):(\d{2})\s*([ap]m)',
        # Just time range without day: "11:30 am–12:30 pm"
        r'(\d{1,2}):(\d{2})\s*([ap]m)\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap]m)',
    ]
    
    for pattern in day_time_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            schedule_info = match.group(0)
            
            # Check if this is Hirshhorn format (starts with month name)
            if len(match.groups()) >= 7 and re.match(r'^[A-Z][a-z]+', match.group(1) or ''):
                # Hirshhorn format: "December 6, 2025 | 11:30 am–12:30 pm"
                # Groups: month_day_year, start_hour, start_min, start_ampm, end_hour, end_min, end_ampm
                try:
                    hour = int(match.group(2))
                    minute = int(match.group(3))
                    ampm_raw = match.group(4).upper()
                    day_mentioned = None  # No day of week in this format
                    days_of_week = []
                except (IndexError, ValueError):
                    continue
            elif len(match.groups()) >= 6 and not any(day in (match.group(1) or '').lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'weekday', 'weekend']):
                # Just time range without day: "11:30 am–12:30 pm"
                # Groups: start_hour, start_min, start_ampm, end_hour, end_min, end_ampm
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    ampm_raw = match.group(3).upper()
                    day_mentioned = None
                    days_of_week = []
                except (IndexError, ValueError):
                    continue
            else:
                # Standard format with day
                day_mentioned = match.group(1).lower() if match.group(1) else None
                
                # Parse day(s)
                if day_mentioned:
                    if 'weekday' in day_mentioned:
                        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
                    elif 'weekend' in day_mentioned:
                        days_of_week = ['saturday', 'sunday']
                    else:
                        days_of_week = [day_mentioned]
                else:
                    days_of_week = []
            
            # Parse start time
            try:
                # Check if this is the NGA format with date (has more groups)
                if len(match.groups()) >= 10 and day_mentioned and day_mentioned in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                    # NGA format: groups are: day, month, day_num, year, start_hour, start_min, start_ampm, end_hour, end_min, end_ampm
                    hour = int(match.group(5))
                    minute = int(match.group(6))
                    ampm_raw = match.group(7).upper()
                elif len(match.groups()) >= 7 and day_mentioned:
                    # Standard format: groups are: day, start_hour, start_min, start_ampm, ...
                    hour = int(match.group(2))
                    minute = int(match.group(3))
                    ampm_raw = match.group(4).upper()
                elif len(match.groups()) >= 6 and not day_mentioned:
                    # Hirshhorn or time-only format - already parsed above
                    pass
                else:
                    continue
                
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
                if len(match.groups()) >= 10 and day_mentioned and day_mentioned in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                    # NGA format
                    end_hour = int(match.group(8))
                    end_minute = int(match.group(9))
                    end_ampm_raw = match.group(10).upper()
                elif len(match.groups()) >= 7 and day_mentioned:
                    # Standard format with day
                    end_hour = int(match.group(5))
                    end_minute = int(match.group(6))
                    end_ampm_raw = match.group(7).upper()
                elif len(match.groups()) >= 6 and not day_mentioned:
                    # Hirshhorn or time-only format
                    if len(match.groups()) == 7:
                        # Hirshhorn format: groups 5, 6, 7 are end time
                        end_hour = int(match.group(5))
                        end_minute = int(match.group(6))
                        end_ampm_raw = match.group(7).upper()
                    elif len(match.groups()) == 6:
                        # Time-only format: groups 4, 5, 6 are end time
                        end_hour = int(match.group(4))
                        end_minute = int(match.group(5))
                        end_ampm_raw = match.group(6).upper()
                    else:
                        end_hour = None
                        end_minute = None
                        end_ampm_raw = None
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

