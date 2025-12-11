#!/usr/bin/env python3
"""
Comprehensive scraper for National Gallery of Art (NGA)
Scrapes Finding Awe, tours, exhibitions, talks, and other events
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import cloudscraper

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VENUE_NAME = "National Gallery of Art"
CITY_NAME = "Washington, DC"

# NGA URLs for different event types
NGA_BASE_URL = 'https://www.nga.gov'
NGA_CALENDAR_URL = 'https://www.nga.gov/calendar'
NGA_FINDING_AWE_URL = 'https://www.nga.gov/calendar/finding-awe'
NGA_EXHIBITIONS_URL = 'https://www.nga.gov/calendar?tab=exhibitions'
NGA_TOURS_URL = 'https://www.nga.gov/calendar?tab=tours'  # Tours are on calendar page with tab parameter
NGA_TALKS_URL = 'https://www.nga.gov/calendar/talks'
NGA_LECTURES_URL = 'https://www.nga.gov/calendar/lectures'


def create_scraper():
    """Create a cloudscraper session to bypass bot detection"""
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'darwin',
            'desktop': True
        }
    )
    
    scraper.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    })
    
    # Try to establish a session by visiting the main page first
    try:
        logger.info("   🔧 Establishing session with NGA website...")
        scraper.get(NGA_BASE_URL, timeout=15)
        import time
        time.sleep(1)  # Small delay after initial request
    except Exception as e:
        logger.warning(f"   ⚠️  Could not establish initial session: {e}")
    
    return scraper


def fetch_with_retry(scraper, url, max_retries=3, delay=2):
    """Fetch URL with retry logic and exponential backoff"""
    import time
    
    if not scraper:
        logger.error(f"   ❌ Scraper is None, cannot fetch {url}")
        return None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait_time = delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.info(f"   ⏳ Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            
            response = scraper.get(url, timeout=20)
            
            # If we get a 403, try refreshing the session
            if response.status_code == 403 and attempt < max_retries - 1:
                logger.warning(f"   ⚠️  403 Forbidden on attempt {attempt + 1}, refreshing session...")
                # Try to re-establish session
                try:
                    scraper.get(NGA_BASE_URL, timeout=15)
                    time.sleep(2)
                except:
                    pass
                continue
            
            response.raise_for_status()
            return response
            
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"   ⚠️  Error on attempt {attempt + 1}: {e}")
    
    return None


def scrape_all_nga_events():
    """Scrape all NGA events: Finding Awe, tours, exhibitions, talks, and other events"""
    all_events = []
    
    try:
        scraper = create_scraper()
        
        # 1. Scrape Finding Awe events
        logger.info("🔍 Scraping Finding Awe events...")
        from scripts.nga_finding_awe_scraper import scrape_all_finding_awe_events
        finding_awe_events = scrape_all_finding_awe_events()
        all_events.extend(finding_awe_events)
        logger.info(f"   ✅ Found {len(finding_awe_events)} Finding Awe events")
        
        # 2. Scrape exhibitions
        logger.info("🔍 Scraping exhibitions...")
        try:
            exhibitions = scrape_nga_exhibitions(scraper)
            all_events.extend(exhibitions)
            logger.info(f"   ✅ Found {len(exhibitions)} exhibitions")
        except Exception as e:
            logger.error(f"   ❌ Error scraping exhibitions: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue with other event types even if exhibitions fail
        
        # 3. Scrape tours
        logger.info("🔍 Scraping tours...")
        try:
            tours = scrape_nga_tours(scraper)
            all_events.extend(tours)
            logger.info(f"   ✅ Found {len(tours)} tours")
        except Exception as e:
            logger.error(f"   ❌ Error scraping tours: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if tours fail
        
        # 4. Scrape talks/lectures (DISABLED FOR NOW - focusing on tours)
        # logger.info("🔍 Scraping talks and lectures...")
        # talks = scrape_nga_talks(scraper)
        # all_events.extend(talks)
        # logger.info(f"   ✅ Found {len(talks)} talks/lectures")
        
        # 5. Scrape other calendar events (DISABLED FOR NOW - focusing on tours)
        # logger.info("🔍 Scraping other calendar events...")
        # other_events = scrape_nga_calendar_events(scraper)
        # all_events.extend(other_events)
        # logger.info(f"   ✅ Found {len(other_events)} other events")
        
        logger.info(f"✅ Total NGA events scraped: {len(all_events)}")
        return all_events
        
    except Exception as e:
        logger.error(f"Error scraping NGA events: {e}")
        import traceback
        traceback.print_exc()
        return all_events


def scrape_nga_exhibitions(scraper):
    """Scrape NGA exhibitions from the calendar page with pagination"""
    events = []
    
    if not scraper:
        logger.error("   ❌ Scraper is None, cannot scrape exhibitions")
        return events
    
    try:
        # Get all exhibition links from paginated calendar page
        exhibition_links = []
        page = 1
        max_pages = 10  # Limit to first 10 pages
        
        logger.info(f"   📄 Fetching exhibitions from: {NGA_EXHIBITIONS_URL}")
        
        while page <= max_pages:
            # Build URL with page parameter
            if page == 1:
                url = NGA_EXHIBITIONS_URL
            else:
                url = f"{NGA_EXHIBITIONS_URL}&page={page}"
            
            try:
                logger.info(f"   📄 Fetching exhibitions page {page}...")
                response = fetch_with_retry(scraper, url, max_retries=3, delay=2)
                if not response:
                    logger.warning(f"   ⚠️  Failed to fetch exhibitions page {page} after retries")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all exhibition links on this page
                page_links = []
                all_links = soup.find_all('a', href=True)
                
                for link in all_links:
                    href = link.get('href', '')
                    # Match exhibition URLs: /exhibitions/name (not just /exhibitions)
                    if '/exhibitions/' in href.lower() and href.lower() != '/exhibitions' and href.lower() != '/exhibitions/':
                        full_url = href if href.startswith('http') else urljoin(NGA_BASE_URL, href)
                        # Make sure it's a specific exhibition page, not the main exhibitions page
                        if full_url not in exhibition_links and full_url not in page_links:
                            # Check if it's a valid exhibition URL (has a slug after /exhibitions/)
                            url_parts = full_url.split('/exhibitions/')
                            if len(url_parts) > 1 and url_parts[1].strip():
                                page_links.append(full_url)
                
                if not page_links:
                    # No more links found, we've reached the end
                    logger.info(f"   No more exhibition links found on page {page}, stopping pagination")
                    break
                
                exhibition_links.extend(page_links)
                logger.info(f"   Found {len(page_links)} exhibition links on page {page} (total: {len(exhibition_links)})")
                
                page += 1
                
                # Delay to be respectful and avoid rate limiting
                import time
                time.sleep(2)  # Increased delay to avoid 403 errors
                
            except Exception as e:
                logger.warning(f"   ⚠️  Error fetching exhibitions page {page}: {e}")
                break
        
        logger.info(f"   Found {len(exhibition_links)} total exhibition links")
        
        # Scrape each exhibition
        for i, exhibition_url in enumerate(exhibition_links, 1):
            try:
                logger.info(f"   📄 Scraping exhibition {i}/{len(exhibition_links)}: {exhibition_url}")
                event_data = scrape_nga_exhibition_page(exhibition_url, scraper)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                logger.warning(f"   ⚠️  Error scraping exhibition {exhibition_url}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error scraping NGA exhibitions: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_nga_exhibition_page(exhibition_url, scraper):
    """Scrape a single NGA exhibition page"""
    try:
        response = fetch_with_retry(scraper, exhibition_url, max_retries=2, delay=1)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title - prioritize OG title, then title tag, then H1 (skip generic H1s like "Global Search")
        title = None
        
        # Try OG title first (most reliable)
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content', '').strip()
        
        # Try title tag if OG title not found
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        # Clean title: remove venue name suffix
        if title:
            from scripts.utils import clean_event_title
            title = clean_event_title(title)
        
        # Try H1, but skip generic ones like "Global Search"
        if not title:
            h1 = soup.find('h1')
            if h1:
                h1_text = h1.get_text(strip=True)
                # Skip generic H1s
                if h1_text.lower() not in ['global search', 'search', 'menu', 'navigation']:
                    title = h1_text
        
        if not title:
            return None
        
        # Extract description - handle all languages (English, Spanish, etc.)
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
        
        # If meta description is too short or missing, try OG description
        # Note: We don't filter by length for non-English content which might be shorter
        if not description or (len(description) < 50 and 'og:description' not in str(soup)):
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                description = og_desc.get('content').strip()
        
        # If still no description, try to extract from main content (for non-English pages)
        if not description or len(description) < 30:
            # Look for main content paragraphs
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|description', re.I))
            if main_content:
                paragraphs = main_content.find_all('p')
                description_parts = []
                for p in paragraphs[:3]:  # Get first 3 paragraphs
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # Reasonable length for any language
                        description_parts.append(text)
                if description_parts:
                    description = ' '.join(description_parts)
        
        # Extract dates
        start_date, end_date = extract_exhibition_dates(page_text, soup)
        
        # Extract image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '').strip()
        
        # Extract location
        location = extract_exhibition_location(page_text, soup)
        
        event_data = {
            'title': title,
            'description': description,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'start_time': None,
            'end_time': None,
            'location': location,
            'url': exhibition_url,
            'image_url': image_url,
            'event_type': 'exhibition',
            'is_online': False,
        }
        
        return event_data
        
    except Exception as e:
        logger.error(f"Error scraping exhibition page {exhibition_url}: {e}")
        return None


def extract_exhibition_dates(page_text, soup):
    """Extract start and end dates from exhibition page"""
    start_date = None
    end_date = None
    
    # First, try to find dates in structured HTML (dt/dd elements or h3/div structures)
    dates_text = None
    
    # Try dt/dd structure first
    dates_dt = soup.find('dt', string=re.compile('Dates?', re.I))
    if dates_dt:
        dates_dd = dates_dt.find_next_sibling('dd')
        if dates_dd:
            dates_text = dates_dd.get_text(strip=True)
    
    # If not found, try h3 structure (NGA uses h3 for "Dates")
    if not dates_text:
        dates_h3 = soup.find('h3', string=re.compile('^Dates?$', re.I))
        if dates_h3:
            # Check next sibling first
            next_sibling = dates_h3.find_next_sibling()
            if next_sibling:
                dates_text = next_sibling.get_text(strip=True)
            # If empty, check all siblings of the parent
            if not dates_text or len(dates_text.strip()) < 10:
                if dates_h3.parent:
                    siblings = dates_h3.parent.find_all(['div', 'p', 'span'], recursive=False)
                    for sibling in siblings:
                        sibling_text = sibling.get_text(strip=True)
                        if sibling_text and ('may' in sibling_text.lower() or 'august' in sibling_text.lower() or '2026' in sibling_text):
                            dates_text = sibling_text
                            break
    
    # If still not found, try finding "Dates" text and getting the following content
    if not dates_text:
        dates_elem = soup.find(string=re.compile('^Dates?$', re.I))
        if dates_elem:
            parent = dates_elem.find_parent()
            if parent:
                # Look for next sibling or next element that contains dates
                next_elem = parent.find_next_sibling()
                if next_elem:
                    dates_text = next_elem.get_text(strip=True)
                else:
                    # Try parent's next sibling
                    if parent.parent:
                        parent_sibling = parent.parent.find_next_sibling()
                        if parent_sibling:
                            dates_text = parent_sibling.get_text(strip=True)
    
    if dates_text:
            # Try to parse the dates from the structured text
            # Pattern 1: "May 23 - August 23, 2026" (year only at end)
            date_range_match = re.search(
                r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s*[–-]\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
                dates_text,
                re.IGNORECASE
            )
            # Pattern 2: "May 23, 2026 - August 23, 2026" (year after each date)
            if not date_range_match:
                date_range_match = re.search(
                    r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\s*[–-]\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
                    dates_text,
                    re.IGNORECASE
                )
            if date_range_match:
                # Parse the structured dates
                groups = date_range_match.groups()
                if len(groups) == 5:
                    # Pattern 1: "May 23 - August 23, 2026" (year only at end)
                    start_month_name = groups[0].lower().rstrip('.')
                    start_day = int(groups[1])
                    end_month_name = groups[2].lower().rstrip('.')
                    end_day = int(groups[3])
                    start_year = int(groups[4])
                    end_year = int(groups[4])  # Same year for both
                elif len(groups) == 6:
                    # Pattern 2: "May 23, 2026 - August 23, 2026" (year after each date)
                    start_month_name = groups[0].lower().rstrip('.')
                    start_day = int(groups[1])
                    start_year = int(groups[2])
                    end_month_name = groups[3].lower().rstrip('.')
                    end_day = int(groups[4])
                    end_year = int(groups[5])
                else:
                    date_range_match = None
                
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
                
                start_month = month_map_full.get(start_month_name) or month_map_abbrev.get(start_month_name[:3])
                end_month = month_map_full.get(end_month_name) or month_map_abbrev.get(end_month_name[:3])
                
                if start_month and end_month:
                    start_date = date(start_year, start_month, start_day)
                    end_date = date(end_year, end_month, end_day)
                    return start_date, end_date
    
    # If structured dates not found, look for date patterns in page text
    # But prioritize dates that appear BEFORE "Other venues" section
    other_venues_pos = page_text.lower().find('other venues')
    search_text = page_text[:other_venues_pos] if other_venues_pos > 0 else page_text
    
    date_patterns = [
        # "[Month] [Day] - [Month] [Day], [Year]" (NGA format - year only at end)
        r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s*[–-]\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        # "[Month] [Day], [Year] - [Month] [Day], [Year]" (year after each date)
        r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\s*[–-]\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        # "On view: [Month] [Day], [Year] - [Month] [Day], [Year]"
        r'on\s+view[:\s]+(?:from\s+)?(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\s*[–-]\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        # "Through [Month] [Day], [Year]"
        r'through\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        # "Opens [Month] [Day], [Year]"
        r'opens\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
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
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 5:
                    # Pattern: "May 23 - August 23, 2026" (year only at end)
                    start_month_name = groups[0].lower().rstrip('.')
                    start_day = int(groups[1])
                    end_month_name = groups[2].lower().rstrip('.')
                    end_day = int(groups[3])
                    start_year = int(groups[4])
                    end_year = int(groups[4])  # Same year for both
                elif len(groups) == 6:  # Pattern: "May 23, 2026 - August 23, 2026" (year after each date)
                    start_month_name = groups[0].lower().rstrip('.')
                    start_day = int(groups[1])
                    start_year = int(groups[2])
                    end_month_name = groups[3].lower().rstrip('.')
                    end_day = int(groups[4])
                    end_year = int(groups[5])
                    
                    start_month = month_map_full.get(start_month_name) or month_map_abbrev.get(start_month_name[:3])
                    end_month = month_map_full.get(end_month_name) or month_map_abbrev.get(end_month_name[:3])
                    
                    if start_month and end_month:
                        start_date = date(start_year, start_month, start_day)
                        end_date = date(end_year, end_month, end_day)
                        break
                elif len(groups) == 3:  # Through or Opens
                    month_name = groups[0].lower().rstrip('.')
                    day = int(groups[1])
                    year = int(groups[2])
                    month = month_map_full.get(month_name) or month_map_abbrev.get(month_name[:3])
                    
                    if month:
                        if 'through' in match.group(0).lower():
                            end_date = date(year, month, day)
                        elif 'opens' in match.group(0).lower():
                            start_date = date(year, month, day)
                        break
            except (ValueError, IndexError) as e:
                logger.debug(f"Error parsing exhibition date: {e}")
                continue
    
    return start_date, end_date


def extract_exhibition_location(page_text, soup):
    """Extract exhibition location"""
    location = None
    
    # Look for building and gallery information
    location_patterns = [
        r'(East Building|West Building)[^.\n]*(?:Gallery\s+\d+[-\w]*|Upper Level|Lower Level|Main Floor)',
        r'Gallery\s+\d+[-\w]*(?:\s*[^.\n]{0,50})?',
        r'(West Building|East Building|Main Floor)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            location = match.group(0).strip()
            location = ' '.join(location.split())
            location = location.rstrip('.,;:')
            break
    
    return location


def scrape_nga_tours(scraper):
    """Scrape NGA tours from the calendar page - only next 2 months"""
    events = []
    
    try:
        # Calculate date range: today to 1 month from now (approximately 30 days)
        today = date.today()
        one_month_later = today + timedelta(days=30)
        
        logger.info(f"   📅 Scraping tours from {today} to {one_month_later}")
        
        # First, get all tour links from pages, but filter by date
        tour_links = []
        page = 1
        max_pages = 4  # Limit to first 4 pages
        skipped_future = 0
        
        logger.info(f"   📄 Fetching tours from: {NGA_TOURS_URL}")
        
        while page <= max_pages:
            # Build URL with page parameter
            if page == 1:
                url = NGA_TOURS_URL
            else:
                url = f"{NGA_TOURS_URL}&page={page}"
            
            try:
                logger.info(f"   📄 Fetching page {page}...")
                response = fetch_with_retry(scraper, url, max_retries=3, delay=2)
                if not response:
                    logger.warning(f"   ⚠️  Failed to fetch tours page {page} after retries")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all tour event links on this page
                page_links = []
                all_links = soup.find_all('a', href=True)
                
                for link in all_links:
                    href = link.get('href', '')
                    
                    # Look for calendar event links with evd parameter (these are individual tour events)
                    if '/calendar/' in href and '?evd=' in href:
                        full_url = href if href.startswith('http') else urljoin(NGA_BASE_URL, href)
                        
                        # Extract date from evd parameter to check if it's within 2 months
                        parsed_url = urlparse(full_url)
                        from urllib.parse import parse_qs
                        query_params = parse_qs(parsed_url.query) if parsed_url.query else {}
                        
                        if 'evd' in query_params and query_params['evd']:
                            evd_value = query_params['evd'][0]
                            if len(evd_value) >= 8:  # At least YYYYMMDD
                                try:
                                    year = int(evd_value[0:4])
                                    month = int(evd_value[4:6])
                                    day = int(evd_value[6:8])
                                    tour_date = date(year, month, day)
                                    
                                    # Only include tours within the next month
                                    if tour_date >= today and tour_date <= one_month_later:
                                        if full_url not in tour_links and full_url not in page_links:
                                            page_links.append(full_url)
                                    elif tour_date > one_month_later:
                                        skipped_future += 1
                                        # If we're seeing dates beyond 1 month, we can stop pagination
                                        # (assuming pages are in chronological order)
                                        if skipped_future > 5:  # If we see several future dates, likely past our range
                                            logger.info(f"   ⏭️  Skipping future tours beyond 1 month, stopping pagination")
                                            break
                                except (ValueError, IndexError):
                                    # If we can't parse the date, include it anyway
                                    if full_url not in tour_links and full_url not in page_links:
                                        page_links.append(full_url)
                        else:
                            # No evd parameter, include it anyway
                            if full_url not in tour_links and full_url not in page_links:
                                page_links.append(full_url)
                
                if not page_links:
                    # No more links found, we've reached the end
                    logger.info(f"   No more tour links found on page {page}, stopping pagination")
                    break
                
                tour_links.extend(page_links)
                logger.info(f"   Found {len(page_links)} tour links on page {page} (total: {len(tour_links)}, skipped future: {skipped_future})")
                
                # If we skipped many future dates, stop pagination
                if skipped_future > 10:
                    break
                
                page += 1
                
                # Delay to be respectful and avoid rate limiting
                import time
                time.sleep(2)  # Increased delay to avoid 403 errors
                
            except Exception as e:
                logger.warning(f"   ⚠️  Error fetching page {page}: {e}")
                break
        
        logger.info(f"   ✅ Found {len(tour_links)} tour event links within next month (skipped {skipped_future} future tours)")
        
        # Scrape each tour event page
        for idx, tour_url in enumerate(tour_links, 1):
            try:
                logger.info(f"   📄 Scraping tour {idx}/{len(tour_links)}: {tour_url}")
                event_data = scrape_nga_tour_page(tour_url, scraper)
                if event_data:
                    # Double-check the date is within range (in case page content differs from URL)
                    if event_data.get('start_date'):
                        try:
                            event_date = datetime.fromisoformat(event_data['start_date']).date()
                            if event_date >= today and event_date <= one_month_later:
                                events.append(event_data)
                                logger.info(f"   ✅ Successfully scraped: {event_data.get('title', 'Unknown')} ({event_date})")
                            else:
                                logger.info(f"   ⏭️  Skipped tour outside date range: {event_data.get('title', 'Unknown')} ({event_date})")
                        except (ValueError, TypeError):
                            # If we can't parse the date, include it anyway
                            events.append(event_data)
                            logger.info(f"   ✅ Successfully scraped: {event_data.get('title', 'Unknown')}")
                    else:
                        # No date, include it anyway
                        events.append(event_data)
                        logger.info(f"   ✅ Successfully scraped: {event_data.get('title', 'Unknown')}")
                else:
                    logger.warning(f"   ⚠️  No data extracted from: {tour_url}")
            except Exception as e:
                logger.warning(f"   ⚠️  Error scraping tour {tour_url}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error scraping NGA tours: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def scrape_nga_tour_page(tour_url, scraper):
    """Scrape a single NGA tour page"""
    try:
        response = fetch_with_retry(scraper, tour_url, max_retries=2, delay=1)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title - prioritize OG title and title tag over H1 (H1 might be navigation)
        title = None
        
        # First try OG title (most reliable)
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title.get('content').strip()
        
        # Then try title tag
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        # Last resort: try H1 (but skip if it's "Global Search" or other navigation)
        if not title:
            h1 = soup.find('h1')
            if h1:
                h1_text = h1.get_text(strip=True)
                # Skip common navigation H1s
                if h1_text.lower() not in ['global search', 'menu', 'directions']:
                    title = h1_text
        
        # Clean title: remove venue name suffix
        if title:
            from scripts.utils import clean_event_title
            title = clean_event_title(title)
        
        if not title:
            logger.warning(f"   ⚠️  No title found for {tour_url}")
            return None
        
        # Extract description - handle all languages (English, Spanish, etc.)
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
        
        # If meta description is too short or missing, try OG description
        # Note: We don't filter by length for non-English content which might be shorter
        if not description or (len(description) < 50 and 'og:description' not in str(soup)):
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                description = og_desc.get('content').strip()
        
        # If still no description, try to extract from main content (for non-English pages)
        if not description or len(description) < 30:
            # Look for main content paragraphs
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|description', re.I))
            if main_content:
                paragraphs = main_content.find_all('p')
                description_parts = []
                for p in paragraphs[:3]:  # Get first 3 paragraphs
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # Reasonable length for any language
                        description_parts.append(text)
                if description_parts:
                    description = ' '.join(description_parts)
        
        # Extract date and time - first try HTML time element (most reliable), then page text
        event_date = None
        start_time = None
        end_time = None
        
        # Try to get from <time datetime=""> attribute first (most reliable)
        time_elem = soup.find('time', class_='datetime')
        if time_elem and time_elem.get('datetime'):
            try:
                from datetime import datetime as dt
                datetime_str = time_elem.get('datetime')
                # Parse ISO format: "2025-12-03T11:00:00-05:00"
                dt_obj = dt.fromisoformat(datetime_str.replace('Z', '+00:00'))
                event_date = dt_obj.date()
                start_time = dt_obj.time()
                logger.info(f"   📅 Extracted from <time datetime>: {event_date} {start_time}")
                
                # For end time, get parent's text (end time is in next sibling)
                # Parent text: "Wednesday, Dec 3, 2025 | 11:00 a.m.\n – 12:00 p.m.\n"
                parent = time_elem.parent
                if parent:
                    parent_text = parent.get_text()
                    # Look for end time pattern: "– 12:00 p.m."
                    end_time_match = re.search(r'[–-]\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?', parent_text, re.IGNORECASE)
                    if end_time_match:
                        end_hour = int(end_time_match.group(1))
                        end_min = int(end_time_match.group(2))
                        end_ampm = end_time_match.group(3).upper()
                        if end_ampm == 'P' and end_hour != 12:
                            end_hour += 12
                        elif end_ampm == 'A' and end_hour == 12:
                            end_hour = 0
                        end_time = time(end_hour, end_min)
                        logger.info(f"   ⏰ Extracted end time from parent text: {end_time}")
            except Exception as e:
                logger.debug(f"   Could not parse time element datetime: {e}")
        
        # If we didn't get times from HTML element, use page text extraction
        if not event_date or not start_time or not end_time:
            event_date, start_time, end_time = extract_event_datetime(page_text, tour_url)
        
        # Extract location (page clearly shows: "West Building Rotunda")
        location = extract_tour_location(page_text, soup)
        
        # Extract image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '').strip()
        
        # Extract registration info
        is_registration_required, registration_url, registration_info = extract_registration_info(page_text, soup)
        
        # Determine event type - check for "Guided Tours" tag or tour indicators
        event_type = 'tour'  # Default for tour pages
        if 'Guided Tours' in page_text or 'guided tour' in page_text.lower():
            event_type = 'tour'
        elif 'tour' in page_text.lower() or 'tour' in title.lower():
            event_type = 'tour'
        
        event_data = {
            'title': title,
            'description': description,
            'start_date': event_date.isoformat() if event_date else None,
            'end_date': event_date.isoformat() if event_date else None,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'location': location,
            'url': tour_url,
            'image_url': image_url,
            'event_type': event_type,
            'is_online': False,
            'is_registration_required': is_registration_required,
            'registration_url': registration_url,
            'registration_info': registration_info,
        }
        
        return event_data
        
    except Exception as e:
        logger.error(f"Error scraping tour page {tour_url}: {e}")
        return None


def scrape_nga_talks(scraper):
    """Scrape NGA talks and lectures"""
    events = []
    
    try:
        # Try both talks and lectures URLs
        urls_to_check = [NGA_TALKS_URL, NGA_LECTURES_URL]
        
        for url in urls_to_check:
            try:
                logger.info(f"   📄 Fetching from: {url}")
                response = fetch_with_retry(scraper, url, max_retries=3, delay=2)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all talk/lecture links
                talk_links = []
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if '/talks/' in href.lower() or '/lectures/' in href.lower() or '/calendar/' in href.lower():
                        full_url = href if href.startswith('http') else urljoin(NGA_BASE_URL, href)
                        if full_url not in talk_links and full_url != url:
                            talk_links.append(full_url)
                
                logger.info(f"   Found {len(talk_links)} talk/lecture links from {url}")
                
                # Scrape each talk
                for talk_url in talk_links:
                    try:
                        event_data = scrape_nga_talk_page(talk_url, scraper)
                        if event_data:
                            events.append(event_data)
                    except Exception as e:
                        logger.warning(f"   ⚠️  Error scraping talk {talk_url}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"   ⚠️  Error fetching {url}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error scraping NGA talks: {e}")
    
    return events


def scrape_nga_talk_page(talk_url, scraper):
    """Scrape a single NGA talk/lecture page"""
    try:
        response = fetch_with_retry(scraper, talk_url, max_retries=2, delay=1)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title
        title = None
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
            # Clean title: remove venue name suffix
            from scripts.utils import clean_event_title
            title = clean_event_title(title)
        
        if not title:
            return None
        
        # Extract description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
        
        # Extract date and time
        event_date, start_time, end_time = extract_event_datetime(page_text, talk_url)
        
        # Extract location
        location = extract_tour_location(page_text, soup)
        
        # Extract image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '').strip()
        
        # Extract registration info
        is_registration_required, registration_url, registration_info = extract_registration_info(page_text, soup)
        
        # Check if online
        is_online = bool(re.search(r'\bonline\b|\bvirtual\b|\bzoom\b', page_text, re.IGNORECASE))
        
        event_data = {
            'title': title,
            'description': description,
            'start_date': event_date.isoformat() if event_date else None,
            'end_date': event_date.isoformat() if event_date else None,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'location': location if not is_online else "Online",
            'url': talk_url,
            'image_url': image_url,
            'event_type': 'talk',
            'is_online': is_online,
            'is_registration_required': is_registration_required,
            'registration_url': registration_url,
            'registration_info': registration_info,
        }
        
        return event_data
        
    except Exception as e:
        logger.error(f"Error scraping talk page {talk_url}: {e}")
        return None


def scrape_nga_calendar_events(scraper):
    """Scrape other events from NGA calendar"""
    events = []
    
    try:
        logger.info(f"   📄 Fetching calendar events from: {NGA_CALENDAR_URL}")
        response = fetch_with_retry(scraper, NGA_CALENDAR_URL, max_retries=3, delay=2)
        if not response:
            return events
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all event links (excluding ones we've already scraped)
        event_links = []
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Match calendar event URLs
            if '/calendar/' in href.lower():
                # Exclude Finding Awe, tours, talks, lectures
                if not any(exclude in href.lower() for exclude in ['finding-awe', '/tours', '/talks', '/lectures']):
                    full_url = href if href.startswith('http') else urljoin(NGA_BASE_URL, href)
                    if full_url not in event_links and full_url != NGA_CALENDAR_URL:
                        event_links.append(full_url)
        
        logger.info(f"   Found {len(event_links)} other calendar event links")
        
        # Scrape each event
        for event_url in event_links:
            try:
                event_data = scrape_nga_generic_event_page(event_url, scraper)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                logger.warning(f"   ⚠️  Error scraping event {event_url}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error scraping NGA calendar events: {e}")
    
    return events


def scrape_nga_generic_event_page(event_url, scraper):
    """Scrape a generic NGA event page"""
    try:
        response = fetch_with_retry(scraper, event_url, max_retries=2, delay=1)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title
        title = None
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
            # Clean title: remove venue name suffix
            from scripts.utils import clean_event_title
            title = clean_event_title(title)
        
        if not title:
            return None
        
        # Extract description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
        
        # Extract date and time
        event_date, start_time, end_time = extract_event_datetime(page_text, event_url)
        
        # Extract location
        location = extract_tour_location(page_text, soup)
        
        # Extract image
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '').strip()
        
        # Extract registration info
        is_registration_required, registration_url, registration_info = extract_registration_info(page_text, soup)
        
        # Check if online
        is_online = bool(re.search(r'\bonline\b|\bvirtual\b|\bzoom\b', page_text, re.IGNORECASE))
        
        # Determine event type
        event_type = 'talk'  # default
        if 'tour' in page_text.lower() or 'tour' in title.lower():
            event_type = 'tour'
        elif 'workshop' in page_text.lower() or 'workshop' in title.lower():
            event_type = 'workshop'
        elif 'performance' in page_text.lower() or 'performance' in title.lower():
            event_type = 'performance'
        
        event_data = {
            'title': title,
            'description': description,
            'start_date': event_date.isoformat() if event_date else None,
            'end_date': event_date.isoformat() if event_date else None,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'location': location if not is_online else "Online",
            'url': event_url,
            'image_url': image_url,
            'event_type': event_type,
            'is_online': is_online,
            'is_registration_required': is_registration_required,
            'registration_url': registration_url,
            'registration_info': registration_info,
        }
        
        return event_data
        
    except Exception as e:
        logger.error(f"Error scraping generic event page {event_url}: {e}")
        return None


def extract_event_datetime(page_text, event_url):
    """Extract date and time from event page text
    Page format: "Wednesday, Dec 3, 2025 | 11:00 a.m. – 12:00 p.m."
    Always use page text - it's what's actually displayed and accurate
    """
    import urllib.parse
    
    event_date = None
    start_time = None
    end_time = None
    
    # Extract from page text - this is what users see and is always correct
    # Date patterns
    date_patterns = [
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
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
                if len(groups) == 4:
                    month_name = match.group(2).lower().rstrip('.')
                    day = int(match.group(3))
                    year = int(match.group(4))
                    month = month_map_full.get(month_name) or month_map_abbrev.get(month_name[:3])
                    if month:
                        event_date = date(year, month, day)
                        break
                elif len(groups) == 3:
                    first_group = groups[0].lower().rstrip('.')
                    if first_group in month_map_full or first_group[:3] in month_map_abbrev:
                        month_name = first_group
                        day = int(groups[1])
                        year = int(groups[2])
                        month = month_map_full.get(month_name) or month_map_abbrev.get(month_name[:3])
                        if month:
                            event_date = date(year, month, day)
                            break
                    else:
                        if '/' in match.group(0):
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                            event_date = date(year, month, day)
                            break
                        else:
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                            event_date = date(year, month, day)
                            break
            except (ValueError, IndexError):
                continue
    
    # Time patterns - handle multiline text (time range may be split across lines)
    # PRIORITY: Always extract from page text first (it's more accurate than URL)
    # Normalize whitespace first to handle newlines
    normalized_text = ' '.join(page_text.split())
    
    time_patterns = [
        # Pattern matching the exact NGA format: "Wednesday, Dec 3, 2025 | 11:00 a.m. – 12:00 p.m."
        # This pattern looks for the pipe separator followed by time range
        r'\|\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?\s+[–-]\s+(\d{1,2}):(\d{2})\s+([ap])\.?m\.?',
        # Pattern with spaces/newlines between times: "11:00 a.m. – 12:00 p.m."
        r'(\d{1,2}):(\d{2})\s+([ap])\.?m\.?\s+[–-]\s+(\d{1,2}):(\d{2})\s+([ap])\.?m\.?',
        # Pattern with optional spaces: "11:00 a.m. – 12:00 p.m."
        r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
        # Pattern without spaces: "11:00am-12:00pm"
        r'(\d{1,2}):(\d{2})([ap])m\s*[–-]\s*(\d{1,2}):(\d{2})([ap])m',
        # Pattern with uppercase: "11:00 AM – 12:00 PM"
        r'(\d{1,2}):(\d{2})\s+([AP])M\s+[–-]\s+(\d{1,2}):(\d{2})\s+([AP])M',
    ]
    
    for time_pattern in time_patterns:
        # Try normalized text first (handles newlines)
        time_match = re.search(time_pattern, normalized_text, re.IGNORECASE)
        if not time_match:
            # Fallback to original text with multiline support
            time_match = re.search(time_pattern, page_text, re.IGNORECASE | re.DOTALL)
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
                logger.info(f"   ⏰ Parsed time from page text: {start_time} - {end_time}")
                break
            except (ValueError, IndexError) as e:
                logger.debug(f"   ⚠️  Error parsing time: {e}")
                continue
    
    # Only use URL fallback if we absolutely couldn't extract from page text
    # This should rarely happen, but URL times are often incorrect
    if not start_time or not end_time:
        logger.warning(f"   ⚠️  Could not extract time from page text, trying URL fallback (may be inaccurate)")
    
    # If we still don't have times but have a date, try to extract from URL evd parameter as fallback
    # (in case the page parsing failed but URL has the info)
    if event_date and (not start_time or not end_time):
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
                        # Default end time: 60 minutes later (standard tour duration)
                        end_hour = hour
                        end_minute = minute + 60
                        if end_minute >= 60:
                            end_hour += end_minute // 60
                            end_minute = end_minute % 60
                        if end_hour >= 24:
                            end_hour = end_hour % 24
                        end_time = time(end_hour, end_minute)
                        logger.warning(f"   ⚠️  Using URL time (may be incorrect): {start_time} - {end_time}")
                except (ValueError, IndexError) as e:
                    logger.debug(f"   ⚠️  Could not parse time from evd parameter: {e}")
    
    # If we still don't have a date, try URL as fallback
    if not event_date:
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
                    logger.info(f"   📅 Extracted date from URL evd parameter (fallback): {event_date}")
                except (ValueError, IndexError) as e:
                    logger.debug(f"   ⚠️  Could not parse date from evd parameter: {e}")
    
    return event_date, start_time, end_time


def extract_tour_location(page_text, soup):
    """Extract location from tour/talk page"""
    location = None
    
    # Prioritize more specific location patterns first
    location_patterns = [
        # Most specific: Building + specific location (Rotunda, Atrium, etc.)
        r'(West Building|East Building)\s+(Rotunda|Atrium|Mezzanine|Terrace|Lobby|Auditorium|Theater|Theatre|Gallery\s+\d+[-\w]*)',
        # Building + Level + Gallery
        r'(East Building|West Building)[^.\n]*(?:Upper Level|Lower Level|Main Floor|Level \d+)[^.\n]*(?:Gallery\s+\d+[-\w]*)',
        # Building + Mezzanine/Terrace/Atrium
        r'(East Building|West Building)[^.\n]*(?:Mezzanine Terrace|Terrace|Mezzanine|Atrium|Lobby|Auditorium|Theater|Theatre)[^.\n]*',
        # Building + Gallery
        r'(East Building|West Building)[^.\n]*(?:Gallery\s+\d+[-\w]*)',
        # Building + Level
        r'(East Building|West Building)[^.\n]*(?:Upper Level|Lower Level|Main Floor|Level \d+)',
        # Just Gallery
        r'Gallery\s+\d+[-\w]*(?:\s*[^.\n]{0,50})?',
        # Fallback: Just Building
        r'(West Building|East Building|Main Floor)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            location = match.group(0).strip()
            location = ' '.join(location.split())  # Normalize whitespace
            location = location.rstrip('.,;:')
            # Clean up - remove extra words that might have been captured
            # Stop at common delimiters
            for delimiter in ['|', '\n', '•', '*']:
                if delimiter in location:
                    location = location.split(delimiter)[0].strip()
            break
    
    return location


def extract_registration_info(page_text, soup):
    """Extract registration information"""
    is_registration_required = False
    registration_url = None
    registration_info = None
    
    registration_keywords = [
        r'\bregistration\s+required\b',
        r'\bregister\s+to\s+attend\b',
        r'\bregistration\s+opens\b',
        r'\bregister\s+now\b',
        r'\badvance\s+registration\b',
    ]
    
    page_text_lower = page_text.lower()
    for keyword in registration_keywords:
        if re.search(keyword, page_text_lower):
            is_registration_required = True
            break
    
    # Look for registration URL
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        href = link.get('href', '')
        link_text = link.get_text(strip=True).lower()
        href_lower = href.lower()
        
        if any(word in href_lower for word in ['register', 'registration', 'rsvp', 'ticket']):
            if not any(domain in href_lower for domain in ['facebook.com', 'twitter.com', 'instagram.com']):
                registration_url = href
                if not registration_url.startswith('http'):
                    registration_url = urljoin(NGA_BASE_URL, registration_url)
                break
    
    return is_registration_required, registration_url, registration_info


def create_events_in_database(events):
    """Create scraped events in the database with update-or-create logic
    Returns (created_count, updated_count)
    """
    # Always use app.app_context() to ensure db is properly bound
    # This works even when called from Flask routes (Flask handles nested contexts)
    with app.app_context():
        # Find venue and city
        venue = Venue.query.filter(
            db.func.lower(Venue.name).like(f'%{VENUE_NAME.lower()}%')
        ).first()
        
        if not venue:
            logger.error(f"❌ Venue '{VENUE_NAME}' not found")
            return 0, 0
        
        logger.info(f"✅ Found venue: {venue.name} (ID: {venue.id})")
        
        city = City.query.filter(
            db.func.lower(City.name).like(f'%{CITY_NAME.lower().split(",")[0]}%')
        ).first()
        
        if not city:
            logger.error(f"❌ City '{CITY_NAME}' not found")
            return 0, 0
        
        logger.info(f"✅ Found city: {city.name} (ID: {city.id})")
        logger.info(f"📊 Processing {len(events)} events...")
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for event_data in events:
            try:
                # Validate required fields
                title = event_data.get('title', '').strip()
                if not title:
                    logger.warning(f"   ⚠️  Skipping event: missing title")
                    skipped_count += 1
                    continue
                
                # Skip category headings (like "Past Exhibitions", "Traveling Exhibitions")
                from scripts.utils import is_category_heading, get_ongoing_exhibition_dates, detect_ongoing_exhibition
                if is_category_heading(title):
                    logger.debug(f"   ⏭️ Skipping category heading: '{title}'")
                    skipped_count += 1
                    continue
                
                # Detect if event is baby-friendly
                is_baby_friendly = False
                title_lower = title.lower()
                description_lower = (event_data.get('description', '') or '').lower()
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
                
                # Handle missing start_date - check if it might be ongoing/permanent
                if not event_data.get('start_date'):
                    # Check if event might be ongoing/permanent
                    description_text = event_data.get('description', '') or ''
                    event_type = event_data.get('event_type', '').lower()
                    is_ongoing = detect_ongoing_exhibition(description_text) or detect_ongoing_exhibition(title)
                    
                    # If it's an exhibition without dates, treat as ongoing
                    if event_type == 'exhibition' or 'exhibition' in title.lower():
                        is_ongoing = True
                    
                    if is_ongoing:
                        # Set dates for ongoing exhibition
                        start_date_obj, end_date_obj = get_ongoing_exhibition_dates()
                        event_data['start_date'] = start_date_obj
                        event_data['end_date'] = end_date_obj
                        logger.info(f"   🔄 Treating '{title}' as ongoing/permanent exhibition (start: {start_date_obj.isoformat()}, end: {end_date_obj.isoformat()})")
                    else:
                        logger.warning(f"   ⚠️  Skipping event '{title}': missing start_date")
                        skipped_count += 1
                        continue
                
                # Parse date - handle both string and date object
                try:
                    start_date_value = event_data['start_date']
                    if isinstance(start_date_value, date):
                        event_date = start_date_value
                    elif isinstance(start_date_value, str):
                        event_date = datetime.fromisoformat(start_date_value).date()
                    else:
                        raise ValueError(f"Unexpected date type: {type(start_date_value)}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"   ⚠️  Skipping event '{event_data.get('title')}': invalid date format: {e}")
                    skipped_count += 1
                    continue
                
                # Check if event already exists (by URL or title+venue+date)
                existing = None
                if event_data.get('url'):
                    existing = Event.query.filter_by(
                        url=event_data.get('url'),
                        city_id=city.id
                    ).first()
                    if existing:
                        logger.debug(f"   Found existing event by URL: {event_data.get('title')}")
                
                if not existing:
                    # Check by title+venue+date (more flexible matching)
                    venue_id_for_check = venue.id if not event_data.get('is_online') else None
                    existing = Event.query.filter_by(
                        title=event_data.get('title'),
                        venue_id=venue_id_for_check,
                        start_date=event_date,
                        city_id=city.id
                    ).first()
                    if existing:
                        logger.debug(f"   Found existing event by title+venue+date: {event_data.get('title')}")
                
                # Parse times
                start_time_obj = None
                end_time_obj = None
                if event_data.get('start_time'):
                    try:
                        start_time_obj = time.fromisoformat(event_data['start_time'])
                    except (ValueError, TypeError):
                        pass
                
                if event_data.get('end_time'):
                    try:
                        end_time_obj = time.fromisoformat(event_data['end_time'])
                    except (ValueError, TypeError):
                        pass
                
                # Determine venue_id
                is_online = event_data.get('is_online', False)
                venue_id_for_event = None if is_online else venue.id
                
                # Ensure location is set for online events
                location = event_data.get('location')
                if is_online and not location:
                    location = "Online"
                
                if existing:
                    # Update existing event
                    updated = False
                    
                    # Update title if different (scraped title is more accurate)
                    if event_data.get('title') and existing.title != event_data.get('title'):
                        existing.title = event_data.get('title')
                        updated = True
                    
                    # Update event_type if different (should be 'tour' for tours)
                    if event_data.get('event_type') and existing.event_type != event_data.get('event_type'):
                        existing.event_type = event_data.get('event_type')
                        updated = True
                    
                    # Update fields if new data is available or existing is None
                    if event_data.get('description') and (not existing.description or len(event_data['description']) > len(existing.description or '')):
                        existing.description = event_data.get('description')
                        updated = True
                    
                    if event_data.get('url') and existing.url != event_data.get('url'):
                        existing.url = event_data.get('url')
                        updated = True
                    
                    if event_data.get('image_url') and not existing.image_url:
                        existing.image_url = event_data.get('image_url')
                        updated = True
                    
                    if location and existing.start_location != location:
                        existing.start_location = location
                        updated = True
                    
                    # Force update times if missing or different
                    if start_time_obj and (not existing.start_time or existing.start_time != start_time_obj):
                        existing.start_time = start_time_obj
                        updated = True
                    
                    if end_time_obj and (not existing.end_time or existing.end_time != end_time_obj):
                        existing.end_time = end_time_obj
                        updated = True
                    
                    # Update registration fields
                    if event_data.get('is_registration_required') is not None:
                        existing.is_registration_required = event_data.get('is_registration_required')
                        updated = True
                    
                    if event_data.get('registration_url') and not existing.registration_url:
                        existing.registration_url = event_data.get('registration_url')
                        updated = True
                    
                    if event_data.get('registration_info') and not existing.registration_info:
                        existing.registration_info = event_data.get('registration_info')
                        updated = True
                    
                    # Ensure is_selected is True for NGA events
                    if not existing.is_selected:
                        existing.is_selected = True
                        updated = True
                    
                    # Update baby-friendly flag if detected
                    if hasattr(Event, 'is_baby_friendly') and is_baby_friendly:
                        if not existing.is_baby_friendly:
                            existing.is_baby_friendly = True
                            updated = True
                    
                    if updated:
                        db.session.commit()
                        updated_count += 1
                        logger.info(f"   ✅ Updated: {event_data['title']}")
                        
                        # Update progress file every 5 events for real-time table updates
                        if (created_count + updated_count) % 5 == 0:
                            try:
                                import json
                                progress_file = os.path.join(project_root, 'scraping_progress.json')
                                if os.path.exists(progress_file):
                                    with open(progress_file, 'r') as f:
                                        progress_data = json.load(f)
                                    progress_data.update({
                                        'events_saved': created_count,
                                        'events_updated': updated_count,
                                        'percentage': min(80 + int(((created_count + updated_count) / max(len(events), 1)) * 20), 99),
                                        'message': f'Saving events to database... ({created_count + updated_count}/{len(events)})',
                                        'timestamp': datetime.now().isoformat()
                                    })
                                    with open(progress_file, 'w') as f:
                                        json.dump(progress_data, f)
                            except Exception as e:
                                logger.debug(f"Could not update progress file: {e}")
                    else:
                        # Event exists but no updates needed - this is fine, just log at debug level
                        logger.debug(f"   ℹ️  Event already exists (no updates needed): {event_data['title']} on {event_date}")
                        # Don't count as skipped - it's a valid duplicate
                else:
                    # Create new event
                    event = Event(
                        title=event_data['title'],
                        description=event_data.get('description'),
                        start_date=event_date,
                        end_date=event_data['end_date'] if isinstance(event_data.get('end_date'), date) else (datetime.fromisoformat(event_data['end_date']).date() if event_data.get('end_date') else event_date),
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        start_location=location,
                        venue_id=venue_id_for_event,
                        city_id=city.id,
                        event_type=event_data.get('event_type', 'talk'),
                        url=event_data.get('url'),
                        image_url=event_data.get('image_url'),
                        source='website',
                        source_url=NGA_CALENDAR_URL,
                        is_selected=True,
                        is_online=is_online,
                        is_registration_required=event_data.get('is_registration_required', False),
                        registration_url=event_data.get('registration_url'),
                        registration_info=event_data.get('registration_info'),
                    )
                    
                    # Set baby-friendly flag if detected
                    if hasattr(Event, 'is_baby_friendly'):
                        event.is_baby_friendly = is_baby_friendly
                    
                    try:
                        db.session.add(event)
                        db.session.commit()
                        created_count += 1
                        logger.info(f"   ✅ Created: {event_data['title']} on {event_date}")
                    except Exception as commit_error:
                        db.session.rollback()
                        logger.error(f"   ❌ Database error creating event '{event_data.get('title')}': {commit_error}")
                        import traceback
                        logger.debug(traceback.format_exc())
                        error_count += 1
                        continue
                    
                    # Update progress file every 5 events for real-time table updates
                    if (created_count + updated_count) % 5 == 0:
                        try:
                            import json
                            progress_file = os.path.join(project_root, 'scraping_progress.json')
                            if os.path.exists(progress_file):
                                with open(progress_file, 'r') as f:
                                    progress_data = json.load(f)
                                progress_data.update({
                                    'events_saved': created_count,
                                    'events_updated': updated_count,
                                    'percentage': min(80 + int(((created_count + updated_count) / max(len(events), 1)) * 20), 99),
                                    'message': f'Saving events to database... ({created_count + updated_count}/{len(events)})',
                                    'timestamp': datetime.now().isoformat()
                                })
                                with open(progress_file, 'w') as f:
                                    json.dump(progress_data, f)
                        except Exception as e:
                            logger.debug(f"Could not update progress file: {e}")
            
            except Exception as e:
                logger.error(f"   ❌ Error processing event {event_data.get('title', 'Unknown')}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                error_count += 1
                db.session.rollback()
                continue
        
        logger.info(f"✅ Created {created_count} new events, updated {updated_count} existing events")
        if skipped_count > 0:
            logger.info(f"⚠️  Skipped {skipped_count} events (missing fields or invalid data)")
        if error_count > 0:
            logger.warning(f"❌ Errors processing {error_count} events")
        if created_count == 0 and updated_count == 0 and len(events) > 0:
            logger.warning(f"⚠️  No events were created or updated, but {len(events)} events were scraped.")
            logger.warning(f"   - Skipped: {skipped_count}, Errors: {error_count}")
            logger.warning(f"   - This might indicate all events are duplicates or there's an issue with event processing.")
        
        return created_count, updated_count


if __name__ == '__main__':
    print("🔍 Scraping all NGA events...")
    events = scrape_all_nga_events()
    
    if events:
        print(f"\n📋 Found {len(events)} events:")
        for event in events:
            print(f"   - {event['title']} ({event.get('event_type', 'unknown')})")
            if event.get('start_date'):
                print(f"     Date: {event['start_date']}")
            if event.get('start_time'):
                print(f"     Time: {event['start_time']}")
        
        print(f"\n💾 Creating/updating events in database...")
        created, updated = create_events_in_database(events)
        print(f"✅ Created {created} new events, updated {updated} existing events")
    else:
        print("❌ No events found")

