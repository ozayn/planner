#!/usr/bin/env python3
"""
Custom scraper for National Gallery of Art Finding Awe series
Scrapes all events from the Finding Awe series page
"""
import os
import sys
import re
import logging
import time as time_module
from datetime import datetime, date, time, timedelta
from bs4 import BeautifulSoup
import cloudscraper

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City, Source

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FINDING_AWE_URL = 'https://www.nga.gov/calendar/finding-awe'
VENUE_NAME = "National Gallery of Art"
CITY_NAME = "Washington, DC"

def scrape_all_finding_awe_events(save_incrementally=False, max_days_ahead=30):
    """Scrape all Finding Awe events from the series page
    
    Args:
        save_incrementally: If True, save events in batches as they're scraped.
                          If False, return all events for batch saving later.
        max_days_ahead: Maximum number of days ahead to scrape events (default: 30 days = 1 month).
                       Set to None to scrape all events regardless of date.
    
    Returns:
        If save_incrementally=True: (events_list, total_created, total_updated)
        If save_incrementally=False: events_list
    """
    events = []
    batch = []  # For incremental saving
    batch_size = 5
    total_created = 0
    total_updated = 0
    
    # Calculate date range for filtering
    today = date.today()
    if max_days_ahead is not None:
        cutoff_date = today + timedelta(days=max_days_ahead)
        logger.info(f"📅 Filtering Finding Awe events: only events from {today} to {cutoff_date} (next {max_days_ahead} days)")
    else:
        cutoff_date = None
        logger.info(f"📅 Scraping all Finding Awe events (no date filter)")
    
    try:
        # Create a cloudscraper session to bypass bot detection
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info(f"🔍 Scraping Finding Awe series from: {FINDING_AWE_URL}")
        
        # Fetch the main page with retry logic for 403 errors
        response = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 * attempt
                    logger.info(f"   ⏳ Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                    time_module.sleep(wait_time)
                    # Recreate scraper for fresh session
                    scraper = cloudscraper.create_scraper(
                        browser={
                            'browser': 'chrome',
                            'platform': 'darwin',
                            'desktop': True
                        }
                    )
                    scraper.headers.update({
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    })
                    # Visit base URL first to establish session
                    try:
                        scraper.get('https://www.nga.gov', timeout=15)
                        time_module.sleep(2)
                    except:
                        pass
                
                response = scraper.get(FINDING_AWE_URL, timeout=20)
                
                # Handle 403 errors
                if response.status_code == 403 and attempt < max_retries - 1:
                    logger.warning(f"   ⚠️  403 Forbidden on attempt {attempt + 1}, will retry...")
                    continue
                
                response.raise_for_status()
                break
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"   ❌ Failed to fetch Finding Awe page after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"   ⚠️  Error on attempt {attempt + 1}: {e}")
        
        if not response:
            logger.error(f"   ❌ Could not fetch Finding Awe page")
            return events if not save_incrementally else (events, total_created, total_updated)
        
        # Find all event links - check multiple pages if pagination exists
        event_links = []
        page = 1
        max_pages = 20  # Safety limit to prevent infinite loops
        
        while page <= max_pages:
            # Build URL with page parameter if not first page
            if page == 1:
                url = FINDING_AWE_URL
            else:
                # Try common pagination patterns
                url = f"{FINDING_AWE_URL}?page={page}"
            
            try:
                # Fetch with retry logic for 403 errors
                page_response = None
                for page_attempt in range(3):
                    try:
                        if page_attempt > 0:
                            time_module.sleep(2 * page_attempt)
                            # Refresh session
                            try:
                                scraper.get('https://www.nga.gov', timeout=15)
                                time_module.sleep(1)
                            except:
                                pass
                        
                        page_response = scraper.get(url, timeout=20)
                        
                        if page_response.status_code == 403 and page_attempt < 2:
                            logger.warning(f"   ⚠️  403 Forbidden on page {page}, attempt {page_attempt + 1}, retrying...")
                            continue
                        
                        page_response.raise_for_status()
                        break
                    except Exception as e:
                        if page_attempt == 2:
                            logger.warning(f"   ⚠️  Failed to fetch page {page} after 3 attempts: {e}")
                            raise
                
                if not page_response:
                    break
                
                soup = BeautifulSoup(page_response.text, 'html.parser')
                
                # Find event links on this page
                page_links = []
                
                # Look for links that contain "finding-awe" in the URL (but not the main series page)
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    # Match finding-awe URLs but exclude the main series page
                    if 'finding-awe' in href.lower() and href != FINDING_AWE_URL and '/finding-awe/' in href.lower():
                        # Exclude the main series page URL
                        if not href.lower().endswith('/finding-awe') and not href.lower().endswith('/finding-awe/'):
                            full_url = href if href.startswith('http') else f"https://www.nga.gov{href}"
                            # Only add if it's a specific event page (has a title/name in the URL)
                            if full_url != FINDING_AWE_URL and full_url not in event_links and full_url not in page_links:
                                page_links.append(full_url)
                
                # Also look for event cards/listings that might have links
                event_cards = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'event|calendar|program|listing', re.I))
                for card in event_cards:
                    card_links = card.find_all('a', href=True)
                    for link in card_links:
                        href = link.get('href', '')
                        if 'finding-awe' in href.lower() and '/finding-awe/' in href.lower():
                            if not href.lower().endswith('/finding-awe') and not href.lower().endswith('/finding-awe/'):
                                full_url = href if href.startswith('http') else f"https://www.nga.gov{href}"
                                if full_url != FINDING_AWE_URL and full_url not in event_links and full_url not in page_links:
                                    page_links.append(full_url)
                
                # If no new links found on this page, stop pagination
                if not page_links:
                    if page == 1:
                        logger.warning(f"   ⚠️  No event links found on first page - page structure may have changed")
                    else:
                        logger.info(f"   No more event links found on page {page}, stopping pagination")
                    break
                
                event_links.extend(page_links)
                logger.info(f"   Found {len(page_links)} event links on page {page} (total: {len(event_links)})")
                
                # Check if there's a "next page" link or button
                has_next_page = False
                next_indicators = soup.find_all(['a', 'button'], string=re.compile(r'next|more|load.*more|see.*all', re.I))
                if next_indicators:
                    has_next_page = True
                
                # Also check for pagination indicators
                pagination = soup.find_all(['a', 'span', 'div'], class_=re.compile(r'pagination|next|page', re.I))
                for pag_elem in pagination:
                    if 'next' in pag_elem.get('class', []) or 'next' in (pag_elem.get_text() or '').lower():
                        has_next_page = True
                        break
                
                # If no next page indicator and we're past page 1, stop
                if page > 1 and not has_next_page:
                    logger.info(f"   No next page indicator found, stopping pagination")
                    break
                
                page += 1
                
                # Small delay between pages to be respectful
                time_module.sleep(1)
                
            except Exception as e:
                if page == 1:
                    # If first page fails, raise the error
                    raise
                else:
                    # If later pages fail, just stop pagination
                    logger.info(f"   Error fetching page {page}: {e}, stopping pagination")
                    break
        
        logger.info(f"   Found {len(event_links)} unique Finding Awe event links across {page - 1} page(s)")
        
        # Pre-filter event links by date from URL evd parameter (if available) to avoid scraping old events
        if cutoff_date is not None:
            filtered_event_links = []
            skipped_old = 0
            skipped_future = 0
            
            for event_url in event_links:
                # Try to extract date from evd parameter in URL
                import urllib.parse
                parsed_url = urllib.parse.urlparse(event_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                if 'evd' in query_params and query_params['evd']:
                    evd_value = query_params['evd'][0]
                    if len(evd_value) >= 8:  # At least YYYYMMDD
                        try:
                            year = int(evd_value[0:4])
                            month = int(evd_value[4:6])
                            day = int(evd_value[6:8])
                            event_date = date(year, month, day)
                            
                            # Only include events within the date range
                            if event_date >= today and event_date <= cutoff_date:
                                filtered_event_links.append(event_url)
                            elif event_date < today:
                                skipped_old += 1
                            else:
                                skipped_future += 1
                        except (ValueError, IndexError):
                            # If we can't parse the date, include it anyway (will be filtered after scraping)
                            filtered_event_links.append(event_url)
                else:
                    # No evd parameter, include it anyway (will be filtered after scraping)
                    filtered_event_links.append(event_url)
            
            event_links = filtered_event_links
            logger.info(f"   📅 Pre-filtered to {len(event_links)} events within date range (skipped {skipped_old} old, {skipped_future} future)")
        
        # Extract events from links
        total_links = len(event_links)
        for idx, event_url in enumerate(event_links):
            try:
                # Update progress during Finding Awe scraping
                if total_links > 0:
                    try:
                        # Update progress with current event count
                        # Note: We don't change step here, just update message and events_found
                        import json
                        progress_file = os.path.join(project_root, 'scraping_progress.json')
                        if os.path.exists(progress_file):
                            with open(progress_file, 'r') as f:
                                progress_data = json.load(f)
                            progress_data.update({
                                'message': f'Scraping Finding Awe events... ({idx+1}/{total_links})',
                                'timestamp': datetime.now().isoformat(),
                                'events_found': len(events)
                            })
                            with open(progress_file, 'w') as f:
                                json.dump(progress_data, f)
                    except Exception:
                        pass  # Don't fail if progress update fails
                
                logger.info(f"   📄 Scraping ({idx+1}/{len(event_links)}): {event_url}")
                event_data = scrape_individual_event(event_url, scraper)
                if event_data:
                    # Filter by date if max_days_ahead is set
                    if cutoff_date is not None:
                        event_start_date = None
                        if event_data.get('start_date'):
                            try:
                                event_start_date = datetime.fromisoformat(event_data['start_date']).date()
                            except (ValueError, TypeError):
                                # Try parsing as string date
                                try:
                                    event_start_date = datetime.strptime(event_data['start_date'], '%Y-%m-%d').date()
                                except:
                                    pass
                        
                        # Only include events within the date range
                        if event_start_date:
                            if event_start_date < today or event_start_date > cutoff_date:
                                logger.info(f"   ⏭️  Skipped event outside date range: {event_data.get('title', 'Unknown')} ({event_start_date})")
                                continue
                        else:
                            # If no date found, include it anyway (better to have it than miss it)
                            logger.debug(f"   ⚠️  Event has no date, including anyway: {event_data.get('title', 'Unknown')}")
                    
                    events.append(event_data)
                    logger.info(f"   ✅ Successfully scraped: {event_data.get('title', 'Unknown')}")
                    
                    # If saving incrementally, add to batch and save when batch is full
                    if save_incrementally:
                        batch.append(event_data)
                        logger.debug(f"   📦 Added to batch: {event_data.get('title', 'Unknown')} (batch size: {len(batch)}/{batch_size})")
                        if len(batch) >= batch_size:
                            logger.info(f"   💾 Saving batch of {len(batch)} events...")
                            try:
                                created, updated = create_events_in_database(batch)
                                total_created += created
                                total_updated += updated
                                logger.info(f"   ✅ Saved batch: {created} created, {updated} updated (total: {total_created} created, {total_updated} updated)")
                                if created == 0 and updated == 0:
                                    logger.warning(f"   ⚠️  Batch saved but no events created/updated - all may be duplicates")
                            except Exception as save_error:
                                logger.error(f"   ❌ Error saving batch: {save_error}")
                                import traceback
                                logger.error(traceback.format_exc())
                            finally:
                                batch = []  # Reset batch even if save failed
            except Exception as e:
                logger.warning(f"   ⚠️  Error scraping event from {event_url}: {e}")
                continue
        
        # Save any remaining events in the batch
        if save_incrementally and batch:
            logger.info(f"   💾 Saving final batch of {len(batch)} events...")
            try:
                created, updated = create_events_in_database(batch)
                total_created += created
                total_updated += updated
                logger.info(f"   ✅ Saved final batch: {created} created, {updated} updated (total: {total_created} created, {total_updated} updated)")
                if created == 0 and updated == 0 and len(batch) > 0:
                    logger.warning(f"   ⚠️  Final batch saved but no events created/updated - all may be duplicates")
            except Exception as save_error:
                logger.error(f"   ❌ Error saving final batch: {save_error}")
                import traceback
                logger.error(traceback.format_exc())
        elif save_incrementally and not batch:
            logger.info(f"   ℹ️  No remaining events to save (all batches already saved)")
        
        logger.info(f"✅ Scraped {len(events)} Finding Awe events")
        if save_incrementally:
            return events, total_created, total_updated
        return events
        
    except Exception as e:
        logger.error(f"Error scraping Finding Awe series: {e}")
        import traceback
        traceback.print_exc()
        if save_incrementally:
            return [], 0, 0
        return []


def scrape_individual_event(event_url, scraper=None):
    """Scrape a single Finding Awe event from its detail page"""
    if not scraper:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
    
    try:
        logger.info(f"   📄 Scraping event: {event_url}")
        
        # Fetch with retry logic for 403 errors
        response = None
        for attempt in range(3):
            try:
                if attempt > 0:
                    time_module.sleep(2 * attempt)
                    # Refresh session if needed
                    if attempt == 1:
                        try:
                            scraper.get('https://www.nga.gov', timeout=15)
                            time_module.sleep(1)
                        except:
                            pass
                
                response = scraper.get(event_url, timeout=20)
                
                if response.status_code == 403 and attempt < 2:
                    logger.warning(f"   ⚠️  403 Forbidden on attempt {attempt + 1}, retrying...")
                    continue
                
                response.raise_for_status()
                break
            except Exception as e:
                if attempt == 2:
                    logger.error(f"   ❌ Failed to fetch event page after 3 attempts: {e}")
                    raise
                logger.warning(f"   ⚠️  Error on attempt {attempt + 1}: {e}")
        
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title
        title = None
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        if not title or 'finding awe' not in title.lower():
            # Try to find title in meta tags
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
        
        if not title:
            logger.warning(f"   ⚠️  No title found for {event_url}")
            return None
        
        # Clean title: remove venue name suffix
        from scripts.utils import clean_event_title
        title = clean_event_title(title)
        
        # Extract description - improved extraction
        description = None
        
        # Extract description using shared utility function
        from scripts.utils import extract_description_from_soup
        description = extract_description_from_soup(soup, max_length=2000)
        
        # Extract date and time
        # PRIORITY: Page text > URL parameter (page text is more accurate)
        event_date = None
        start_time = None
        end_time = None
        
        # First, try to extract date/time from page text (most accurate)
        # Look for date patterns - handle both full and abbreviated month names
        date_patterns = [
            # Full month names: "Saturday, February 7, 2026"
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            # Abbreviated month names: "Saturday, Feb 7, 2026" or "Feb 7, 2026"
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
            # Date without day name: "February 7, 2026" or "Feb 7, 2026"
            r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
            # MM/DD/YYYY format
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            # YYYY-MM-DD format
            r'(\d{4})-(\d{2})-(\d{2})',
        ]
        
        month_map_full = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        month_map_abbrev = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 4:  # Day name, month name, day, year
                        month_name = match.group(2).lower().rstrip('.')
                        day = int(match.group(3))
                        year = int(match.group(4))
                        month = month_map_full.get(month_name) or month_map_abbrev.get(month_name[:3])
                        if month:
                            event_date = date(year, month, day)
                            logger.info(f"   📅 Parsed date: {event_date}")
                            break
                    elif len(groups) == 3:
                        # Check if first group is a month name
                        first_group = groups[0].lower().rstrip('.')
                        if first_group in month_map_full or first_group[:3] in month_map_abbrev:
                            # Month name format: "Feb 7, 2026" or "February 7, 2026"
                            month_name = first_group
                            day = int(groups[1])
                            year = int(groups[2])
                            month = month_map_full.get(month_name) or month_map_abbrev.get(month_name[:3])
                            if month:
                                event_date = date(year, month, day)
                                logger.info(f"   📅 Parsed date: {event_date}")
                                break
                        else:
                            # Numeric format: MM/DD/YYYY or YYYY-MM-DD
                            if '/' in match.group(0):
                                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                                event_date = date(year, month, day)
                                logger.info(f"   📅 Parsed date: {event_date}")
                                break
                            else:
                                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                                event_date = date(year, month, day)
                                logger.info(f"   📅 Parsed date: {event_date}")
                                break
                except (ValueError, IndexError, AttributeError) as e:
                    logger.debug(f"   ⚠️  Error parsing date: {e}")
                    continue
        
        # Extract time from page text (always try this first - it's more accurate)
        # Extract time - handle various formats
        time_patterns = [
            # "2:15 p.m. – 4:00 p.m." or "2:15 p.m. - 4:00 p.m."
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # "2:15pm – 4:00pm"
            r'(\d{1,2}):(\d{2})([ap])m\s*[–-]\s*(\d{1,2}):(\d{2})([ap])m',
            # "2:15 PM – 4:00 PM"
            r'(\d{1,2}):(\d{2})\s*([AP])M\s*[–-]\s*(\d{1,2}):(\d{2})\s*([AP])M',
        ]
        
        for time_pattern in time_patterns:
            time_match = re.search(time_pattern, page_text, re.IGNORECASE)
            if time_match:
                try:
                    start_hour = int(time_match.group(1))
                    start_min = int(time_match.group(2))
                    start_ampm = time_match.group(3).upper()
                    end_hour = int(time_match.group(4))
                    end_min = int(time_match.group(5))
                    end_ampm = time_match.group(6).upper()
                    
                    if start_ampm == 'P' and start_hour != 12:
                        start_hour += 12
                    elif start_ampm == 'A' and start_hour == 12:
                        start_hour = 0
                    
                    if end_ampm == 'P' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'A' and end_hour == 12:
                        end_hour = 0
                    
                    start_time = time(start_hour, start_min)
                    end_time = time(end_hour, end_min)
                    logger.info(f"   ⏰ Parsed time from page: {start_time} - {end_time}")
                    break
                except (ValueError, IndexError) as e:
                    logger.debug(f"   ⚠️  Error parsing time: {e}")
                    continue
        
        # If we still don't have times but have a date, try to extract from URL evd parameter as fallback
        # (in case the page parsing failed but URL has the info)
        if event_date and (not start_time or not end_time):
            import urllib.parse
            parsed_url = urllib.parse.urlparse(event_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'evd' in query_params and query_params['evd']:
                evd_value = query_params['evd'][0]
                if len(evd_value) >= 12:  # YYYYMMDDHHMM format
                    try:
                        hour = int(evd_value[8:10])
                        minute = int(evd_value[10:12])
                        if not start_time:
                            start_time = time(hour, minute)
                        if not end_time:
                            # Default end time: 90 minutes later (standard Finding Awe duration)
                            end_hour = hour
                            end_minute = minute + 90
                            if end_minute >= 60:
                                end_hour += end_minute // 60
                                end_minute = end_minute % 60
                            if end_hour >= 24:
                                end_hour = end_hour % 24
                            end_time = time(end_hour, end_minute)
                            logger.info(f"   ⏰ Extracted time from URL evd parameter: {start_time} - {end_time}")
                    except (ValueError, IndexError) as e:
                        logger.debug(f"   ⚠️  Could not parse time from evd parameter: {e}")
        
        # Detect if event is online/virtual
        is_online = False
        online_indicators = [
            r'\bonline\b',
            r'\bvirtual\b',
            r'\bzoom\b',
            r'\bwebinar\b',
            r'\bstreaming\b',
            r'\blive stream\b',
            r'\bwebcast\b',
            r'\bdigital\b',
        ]
        
        page_text_lower = page_text.lower()
        for indicator in online_indicators:
            if re.search(indicator, page_text_lower):
                is_online = True
                logger.info(f"   🌐 Detected online event")
                break
        
        # Extract location - get more detailed location information
        location = None
        if is_online:
            location = "Online"
        else:
            # Look for detailed location information
            # Try to find location in structured format first (e.g., "East Building Upper Level, Gallery 415-A")
            location_patterns = [
                # Full location: "East Building Upper Level, Gallery 415-A"
                r'(East Building|West Building)[^.\n]*(?:Upper Level|Lower Level|Main Floor|Level \d+)[^.\n]*(?:Gallery\s+\d+[-\w]*)',
                # NGA special locations: "East Building Mezzanine Terrace"
                r'(East Building|West Building)[^.\n]*(?:Mezzanine Terrace|Terrace|Mezzanine|Atrium|Lobby|Auditorium|Theater|Theatre)[^.\n]*',
                # Building with gallery: "East Building, Gallery 415-A"
                r'(East Building|West Building)[^.\n]*(?:Gallery\s+\d+[-\w]*)',
                # Just building and level: "East Building Upper Level"
                r'(East Building|West Building)[^.\n]*(?:Upper Level|Lower Level|Main Floor|Level \d+)',
                # Gallery with building context
                r'Gallery\s+\d+[-\w]*(?:\s*[^.\n]{0,50})?',
                # Fallback to just building
                r'(West Building|East Building|Main Floor)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    location = match.group(0).strip()
                    # Clean up the location text
                    location = ' '.join(location.split())  # Normalize whitespace
                    # Remove extra punctuation
                    location = location.rstrip('.,;:')
                    logger.info(f"   📍 Found location: {location}")
                    break
            
            # If still no location, try to find it in HTML structure
            if not location:
                # Look for location in list items or specific elements
                location_elements = soup.find_all(['div', 'span', 'p', 'li'], string=re.compile(r'East Building|West Building|Gallery \d+|Mezzanine|Terrace', re.I))
                for elem in location_elements:
                    text = elem.get_text(strip=True)
                    # Check if it contains building or location keywords
                    if any(keyword in text for keyword in ['Building', 'Gallery', 'Mezzanine', 'Terrace', 'Atrium', 'Lobby']):
                        # Clean up the text - remove date/time patterns
                        text = re.sub(r'\s+\d{1,2}:\d{2}\s*[ap]\.?m\.?.*$', '', text, flags=re.IGNORECASE)
                        text = re.sub(r'\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*$', '', text, flags=re.IGNORECASE)
                        text = text.split('|')[0].strip()  # Stop at pipe if present
                        if len(text) > 5 and len(text) < 100:  # Reasonable length
                            location = text
                            logger.info(f"   📍 Found location in HTML: {location}")
                            break
        
        # Extract image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '').strip()
        
        # Extract registration information
        is_registration_required = False
        registration_opens_date = None
        registration_opens_time = None
        registration_url = None
        registration_info = None
        
        # Look for registration indicators - check both page text and HTML elements
        registration_keywords = [
            r'\bregistration\s+required\b',
            r'\bregister\s+to\s+attend\b',
            r'\bregistration\s+opens\b',
            r'\bregister\s+now\b',
            r'\badvance\s+registration\b',
            r'\bpre-registration\b',
            r'\bwe encourage you to register\b',
            r'\bplease register\b',
        ]
        
        page_text_lower = page_text.lower()
        for keyword in registration_keywords:
            if re.search(keyword, page_text_lower):
                is_registration_required = True
                logger.info(f"   📝 Detected registration required: {keyword}")
                break
        
        # Also check for "Registration Required" text in visible elements
        if not is_registration_required:
            reg_required_elements = soup.find_all(string=re.compile(r'registration\s+required', re.I))
            if reg_required_elements:
                is_registration_required = True
                logger.info(f"   📝 Detected 'Registration Required' text in page")
        
        # Look for registration URL - be very strict and avoid false positives
        excluded_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 
            'pinterest.com', 'linkedin.com', 'tiktok.com', 'snapchat.com',
            'reddit.com', 'tumblr.com', 'flickr.com', 'vimeo.com'
        ]
        
        excluded_patterns = ['social', 'share', 'follow', 'like', 'subscribe', 'newsletter', 'email']
        
        # Look for links where BOTH the href AND text indicate registration
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()
            href_lower = href.lower()
            
            # Skip if it's a social media or excluded domain
            if any(domain in href_lower for domain in excluded_domains):
                continue
            
            # Skip if it contains excluded patterns
            if any(pattern in href_lower for pattern in excluded_patterns):
                continue
            
            # The href MUST contain registration-related keywords
            href_has_registration = any(word in href_lower for word in [
                'register', 'registration', 'rsvp', 'ticket', 'book', 'reserve', 
                'signup', 'sign-up', 'eventbrite', 'ticketmaster', 'event'
            ])
            
            if href_has_registration:
                registration_url = href
                if not registration_url.startswith('http'):
                    from urllib.parse import urljoin
                    registration_url = urljoin(event_url, registration_url)
                logger.info(f"   🔗 Found registration URL: {registration_url}")
                break
        
        # Look for registration opens date/time
        registration_opens_patterns = [
            r'registration\s+opens\s+(?:on\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            r'registration\s+opens\s+(\d{1,2})/(\d{1,2})/(\d{4})',
            r'registration\s+opens\s+(\d{4})-(\d{2})-(\d{2})',
        ]
        
        for pattern in registration_opens_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 3:  # Month name, day, year
                        month_name = match.group(1)
                        day = int(match.group(2))
                        year = int(match.group(3))
                        month_map = {
                            'january': 1, 'february': 2, 'march': 3, 'april': 4,
                            'may': 5, 'june': 6, 'july': 7, 'august': 8,
                            'september': 9, 'october': 10, 'november': 11, 'december': 12
                        }
                        month = month_map.get(month_name.lower())
                        if month:
                            registration_opens_date = date(year, month, day)
                            break
                    elif len(match.groups()) == 3:  # MM/DD/YYYY or YYYY-MM-DD
                        if '/' in match.group(0):
                            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                            registration_opens_date = date(year, month, day)
                        else:
                            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                            registration_opens_date = date(year, month, day)
                        break
                except (ValueError, IndexError):
                    continue
        
        # Extract registration info text
        registration_info_patterns = [
            r'registration\s+(?:opens|begins|starts)\s+[^.\n]+',
            r'registration\s+required[^.\n]*',
            r'advance\s+registration[^.\n]*',
        ]
        for pattern in registration_info_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                registration_info = match.group(0).strip()
                break
        
        event_data = {
            'title': title,
            'description': description,
            'start_date': event_date.isoformat() if event_date else None,
            'end_date': event_date.isoformat() if event_date else None,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'location': location,
            'url': event_url,
            'image_url': image_url,
            'event_type': 'talk',
            'is_online': is_online,
            'is_registration_required': is_registration_required,
            'registration_opens_date': registration_opens_date.isoformat() if registration_opens_date else None,
            'registration_opens_time': registration_opens_time.isoformat() if registration_opens_time else None,
            'registration_url': registration_url,
            'registration_info': registration_info,
        }
        
        logger.info(f"   ✅ Extracted: {title}")
        return event_data
        
    except Exception as e:
        logger.error(f"   ❌ Error scraping event {event_url}: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_event_from_element(element):
    """Extract event data from an element on the main page"""
    # This would parse event cards/listings on the main Finding Awe page
    # Implementation depends on the actual HTML structure
    return None


def create_events_in_database(events):
    """Create scraped events in the database with update-or-create logic
    Returns (created_count, updated_count)
    Uses shared event_database_handler for common logic.
    """
    from scripts.event_database_handler import create_events_in_database as shared_create_events
    
    if not events:
        logger.warning("⚠️  No events to save")
        return 0, 0
    
    # Always use app.app_context() to ensure db is properly bound
    # Flask supports nested contexts, so this is safe even if called from within an endpoint
    try:
        with app.app_context():
            # Find venue and city
            venue = Venue.query.filter(
                db.func.lower(Venue.name).like(f'%{VENUE_NAME.lower()}%')
            ).first()
            
            if not venue:
                logger.error(f"❌ Venue '{VENUE_NAME}' not found")
                return 0, 0
            
            logger.info(f"✅ Found venue: {venue.name} (ID: {venue.id})")
            logger.info(f"📊 Processing {len(events)} events...")
            
            # Custom processor for Finding Awe-specific fields
            def finding_awe_event_processor(event_data):
                """Add Finding Awe-specific fields to event data"""
                event_data['is_selected'] = True
                event_data['source'] = 'website'
                event_data['source_url'] = FINDING_AWE_URL
            
            # Use shared handler for all common logic
            created_count, updated_count, skipped_count = shared_create_events(
                events=events,
                venue_id=venue.id,
                city_id=venue.city_id,
                venue_name=venue.name,
                db=db,
                Event=Event,
                Venue=Venue,
                batch_size=5,
                logger_instance=logger,
                source_url=FINDING_AWE_URL,
                custom_event_processor=finding_awe_event_processor
            )
            
            logger.info(f"✅ Created {created_count} new events, updated {updated_count} existing events")
            return created_count, updated_count
    except Exception as e:
        logger.error(f"❌ Error in create_events_in_database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, 0
        
        # Old code removed - replaced with shared handler above
        # The following was the old individual event processing loop:
        # (removed ~200 lines of duplicate logic)
if __name__ == '__main__':
    print("🔍 Scraping all Finding Awe events...")
    events = scrape_all_finding_awe_events()
    
    if events:
        print(f"\n📋 Found {len(events)} events:")
        for event in events:
            print(f"   - {event['title']}")
            if event.get('start_date'):
                print(f"     Date: {event['start_date']}")
            if event.get('start_time'):
                print(f"     Time: {event['start_time']}")
        
        print(f"\n💾 Creating events in database...")
        created = create_events_in_database(events)
        print(f"✅ Created {created} new events")
    else:
        print("❌ No events found")
