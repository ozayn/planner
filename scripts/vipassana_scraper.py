#!/usr/bin/env python3
"""
Scraper for Vipassana Meditation Virtual Events
Scrapes virtual group sitting events from: https://www.dhamma.org/en/os/locations/virtual_events
Extracts zoom links, locations, timezones, and schedules for Google Calendar export
"""
import os
import sys
import re
import logging
from datetime import datetime, date, time, timedelta
from bs4 import BeautifulSoup
import cloudscraper
import pytz

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue, City, Source

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VIPASSANA_URL = 'https://www.dhamma.org/en/os/locations/virtual_events'
VENUE_NAME = "Vipassana Meditation (Virtual)"
SOURCE_NAME = "Dhamma.org Virtual Events"

def _get_vipassana_credentials():
    """Get Vipassana credentials from environment variables"""
    import os
    from scripts.env_config import ensure_env_loaded
    ensure_env_loaded()
    
    username = os.getenv('VIPASSANA_USERNAME') or os.getenv('DHAMMA_USERNAME')
    password = os.getenv('VIPASSANA_PASSWORD') or os.getenv('DHAMMA_PASSWORD')
    
    return username, password

def scrape_vipassana_events():
    """Scrape all virtual Vipassana meditation events from dhamma.org"""
    events = []
    
    try:
        # Create a cloudscraper session to bypass bot detection
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        
        # Add comprehensive headers to look like a real browser
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.dhamma.org/'
        })
        
        logger.info(f"🔍 Scraping Vipassana virtual events from: {VIPASSANA_URL}")
        
        # Get credentials for authentication
        username, password = _get_vipassana_credentials()
        auth = None
        if username and password:
            logger.info(f"   🔐 Using authentication credentials")
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(username, password)
        else:
            logger.warning("   ⚠️  No credentials found in environment variables")
            logger.warning("   Set VIPASSANA_USERNAME and VIPASSANA_PASSWORD (or DHAMMA_USERNAME/DHAMMA_PASSWORD) in your .env file")
        
        # First, visit the base domain to establish a session (helps with 401 errors)
        base_url = 'https://www.dhamma.org'
        try:
            logger.info(f"   📍 Establishing session with base domain: {base_url}")
            scraper.get(base_url, timeout=15, auth=auth)
            import time
            time.sleep(2)  # Brief pause to let session establish
        except Exception as e:
            logger.warning(f"   ⚠️  Could not visit base domain (continuing anyway): {e}")
        
        # Now try to fetch the actual page with retry logic
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 * attempt
                    logger.info(f"   ⏳ Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                    import time
                    time.sleep(wait_time)
                    # Recreate scraper for fresh session on retry
                    scraper = cloudscraper.create_scraper(
                        browser={
                            'browser': 'chrome',
                            'platform': 'darwin',
                            'desktop': True
                        }
                    )
                    scraper.headers.update({
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Referer': 'https://www.dhamma.org/'
                    })
                    # Re-establish session
                    try:
                        scraper.get(base_url, timeout=15, auth=auth)
                        time.sleep(1)
                    except:
                        pass
                
                response = scraper.get(VIPASSANA_URL, timeout=30, auth=auth)
                
                # Handle 401/403 errors
                if response.status_code in [401, 403]:
                    logger.warning(f"   ⚠️  {response.status_code} {'Unauthorized' if response.status_code == 401 else 'Forbidden'} on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"   ❌ Failed to access page after {max_retries} attempts - got {response.status_code}")
                        logger.error(f"   Response text: {response.text[:500]}")
                        raise Exception(f"Page returned {response.status_code} - may require authentication or have IP-based blocking")
                
                response.raise_for_status()
                break
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"   ⚠️  Error on attempt {attempt + 1}: {e}")
        
        if not response:
            # Try Playwright as a last resort if available
            logger.warning("   ⚠️  Standard scraping failed, trying browser automation (Playwright)...")
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    logger.info(f"   🌐 Loading page with browser: {VIPASSANA_URL}")
                    
                    # Set up authentication if credentials are available
                    username, password = _get_vipassana_credentials()
                    if username and password:
                        logger.info("   🔐 Using browser authentication")
                        page.set_extra_http_headers({
                            'Authorization': f'Basic {__import__("base64").b64encode(f"{username}:{password}".encode()).decode()}'
                        })
                    
                    page.goto(VIPASSANA_URL, wait_until='networkidle', timeout=30000)
                    html_content = page.content()
                    browser.close()
                
                # Create response-like object for compatibility
                class MockResponse:
                    def __init__(self, text, status_code):
                        self.text = text
                        self.status_code = status_code
                    def raise_for_status(self):
                        if self.status_code >= 400:
                            raise Exception(f"HTTP {self.status_code}")
                
                # Check if content is valid HTML
                if not html_content.strip().startswith('<') and '<html' not in html_content[:200].lower():
                    logger.warning("   ⚠️  Browser automation response doesn't appear to be HTML")
                    logger.warning(f"   First 100 chars: {repr(html_content[:100])}")
                
                response = MockResponse(html_content, 200)
                logger.info(f"   ✅ Successfully fetched page with browser automation")
                logger.info(f"   Page size: {len(html_content)} characters")
            except ImportError:
                logger.warning("   ⚠️  Playwright not available - install with: pip install playwright && playwright install chromium")
                raise Exception("Failed to fetch page after all retries. The page may require authentication or browser automation.")
            except Exception as browser_error:
                logger.error(f"   ❌ Browser automation also failed: {browser_error}")
                raise Exception(f"Failed to fetch page. The page returned 401 Authorization Required, which suggests it requires authentication or has IP-based access control. Error: {browser_error}")
        
        if response.status_code in [401, 403]:
            error_msg = f"Page returned {response.status_code} - "
            if response.status_code == 401:
                error_msg += "Authorization Required. The page may require:"
                error_msg += "\n   1. Login credentials or session cookies"
                error_msg += "\n   2. IP allowlisting"
                error_msg += "\n   3. A different URL path"
                error_msg += f"\n\nPlease verify the URL is correct: {VIPASSANA_URL}"
                error_msg += "\nYou can try accessing it manually in a browser to confirm it's publicly accessible."
            else:
                error_msg += "Forbidden - the server is blocking automated access."
            raise Exception(error_msg)
        
        logger.info(f"   ✅ Successfully fetched page (status: {response.status_code})")
        
        # Check content type and encoding
        content_type = response.headers.get('Content-Type', '')
        content_encoding = response.headers.get('Content-Encoding', '')
        logger.info(f"   Content-Type: {content_type}")
        logger.info(f"   Content-Encoding: {content_encoding}")
        
        # Try to decode the response properly
        try:
            html_content = response.text
            # Check if content looks like binary/garbled
            if len(html_content) > 0 and ord(html_content[0]) > 127 and '\n' not in html_content[:100]:
                logger.warning("   ⚠️  Response appears to be binary/compressed, trying alternative decoding...")
                # Try decoding as bytes
                html_content = response.content.decode('utf-8', errors='replace')
        except Exception as decode_error:
            logger.warning(f"   ⚠️  Decoding error: {decode_error}, trying alternative...")
            try:
                html_content = response.content.decode('latin-1', errors='ignore')
            except:
                html_content = response.content.decode('utf-8', errors='replace')
        
        logger.info(f"   Page size: {len(html_content)} characters")
        
        # Check if page might be JavaScript-rendered
        page_text_preview = html_content[:5000].lower()
        if 'react' in page_text_preview or 'vue' in page_text_preview or 'angular' in page_text_preview:
            logger.warning("   ⚠️  Page might be JavaScript-rendered (React/Vue/Angular detected)")
        if len(response.text) < 5000:
            logger.warning("   ⚠️  Page is very small - might be a shell that loads content via JavaScript")
        if 'noscript' in page_text_preview or 'loading' in page_text_preview:
            logger.warning("   ⚠️  Page might require JavaScript to load content")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Debug: Log page title and some content
        page_title = soup.find('title')
        logger.info(f"   Page title: {page_title.get_text() if page_title else 'No title'}")
        
        # Save a sample of the page for debugging
        page_sample = html_content[:2000] if len(html_content) > 2000 else html_content
        logger.info(f"   Page content sample: {page_sample[:500]}...")
        
        # Check if content is actually HTML
        if not html_content.strip().startswith('<') and '<html' not in html_content[:200].lower():
            logger.warning("   ⚠️  Response doesn't appear to be HTML - might be encrypted or wrong format")
            logger.warning(f"   First 100 chars: {repr(html_content[:100])}")
        
        # Try to find the main content area - look for common patterns
        main_content = None
        content_selectors = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', class_=re.compile(r'content|main|container', re.I)),
            soup.find('div', id=re.compile(r'content|main', re.I)),
        ]
        for selector in content_selectors:
            if selector:
                main_content = selector
                logger.info(f"   Found main content area: {selector.name} with class/id")
                break
        
        if not main_content:
            main_content = soup  # Use entire page if no main content found
        
        # Find all location entries - they're typically in tables, divs, or lists
        # Look for patterns like location names, timezones, zoom links, and schedules
        
        # Try to find location containers - be more aggressive in searching
        location_containers = []
        search_area = main_content if main_content else soup
        
        # Method 1: Look for table rows
        tables = search_area.find_all('table')
        logger.info(f"   Found {len(tables)} tables")
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    location_containers.append(row)
        
        # Method 2: Look for divs with location information (more flexible class matching)
        divs = search_area.find_all('div', class_=re.compile(r'location|center|event|timezone|sitting|group|meditation', re.I))
        logger.info(f"   Found {len(divs)} divs with relevant classes")
        location_containers.extend(divs)
        
        # Method 3: Look for sections or articles
        sections = search_area.find_all(['section', 'article'])
        logger.info(f"   Found {len(sections)} sections/articles")
        for section in sections:
            text = section.get_text()
            if any(keyword in text.lower() for keyword in ['timezone', 'cet', 'est', 'pst', 'wednesday', 'sunday', 'zoom', 'teams']):
                location_containers.append(section)
        
        # Method 4: Look for list items
        lists = search_area.find_all(['ul', 'ol'])
        logger.info(f"   Found {len(lists)} lists")
        for ul in lists:
            items = ul.find_all('li')
            for item in items:
                text = item.get_text()
                # Check if it contains location-like information
                if any(keyword in text.lower() for keyword in ['zoom', 'time', 'timezone', 'am', 'pm', 'dhamma', 'cet', 'est', 'wednesday', 'sunday']):
                    location_containers.append(item)
        
        # Method 5: Look for any element containing zoom/teams links
        meeting_links = search_area.find_all('a', href=re.compile(r'zoom|teams|meet', re.I))
        logger.info(f"   Found {len(meeting_links)} meeting links (zoom/teams)")
        for link in meeting_links:
            # Find parent container (go up multiple levels if needed)
            parent = link.find_parent(['div', 'td', 'li', 'p', 'section', 'article'])
            if parent:
                # Go up one more level to get the full section
                grandparent = parent.find_parent(['div', 'section', 'article'])
                container = grandparent if grandparent else parent
                if container and container not in location_containers:
                    location_containers.append(container)
        
        # Method 6: Look for elements containing timezone patterns
        all_text = search_area.get_text()
        if any(pattern in all_text for pattern in ['CET', 'EST', 'PST', 'Central European', 'Eastern Time']):
            logger.info(f"   Page contains timezone keywords")
            # Find elements containing timezone info
            for element in search_area.find_all(['div', 'p', 'section', 'article', 'li']):
                text = element.get_text()
                if any(pattern in text for pattern in ['CET', 'EST', 'PST', 'Central European', 'Eastern Time', 'Pacific Time']) and len(text) > 30:
                    if element not in location_containers:
                        location_containers.append(element)
        
        # Method 7: Look for elements with "Click to Join" or similar text
        join_elements = search_area.find_all(string=re.compile(r'click\s+to\s+join|join\s+(?:this\s+)?(?:online\s+)?(?:group\s+)?sitting', re.I))
        logger.info(f"   Found {len(join_elements)} 'Click to Join' text elements")
        for text_node in join_elements:
            parent = text_node.find_parent(['div', 'p', 'section', 'article', 'li', 'td'])
            if parent and parent not in location_containers:
                location_containers.append(parent)
        
        logger.info(f"   Found {len(location_containers)} potential location containers")
        
        # Process each location container
        processed_locations = set()
        # Track events by timezone+time combination to prefer English versions
        events_by_timezone_time = {}  # Key: (timezone, time_str), Value: event_data
        
        def is_english_text(text):
            """Check if text appears to be in English"""
            if not text:
                return False
            # Common English words/patterns in meditation context
            english_indicators = [
                'zoom', 'meeting', 'time', 'am', 'pm', 'daily', 'group', 'sitting',
                'meditation', 'virtual', 'link', 'password', 'timezone', 'eastern',
                'pacific', 'central', 'mountain', 'est', 'pst', 'cst', 'mst'
            ]
            text_lower = text.lower()
            # Count how many English indicators we find
            matches = sum(1 for indicator in english_indicators if indicator in text_lower)
            # If we find several English indicators, it's likely English
            return matches >= 2
        
        for container in location_containers:
            try:
                text = container.get_text(separator='\n', strip=True)
                html = str(container)
                
                # Skip if too short or doesn't contain relevant keywords
                if len(text) < 20:
                    continue
                
                if not any(keyword in text.lower() for keyword in ['zoom', 'time', 'dhamma', 'vipassana', 'meditation', 'sitting']):
                    continue
                
                # Extract location name
                location_name = None
                location_patterns = [
                    r'Dhamma\s+([A-Z][a-zA-Z\s]+)',
                    r'([A-Z][a-zA-Z\s]+)\s+(?:Center|Meditation|Group)',
                    r'Location[:\s]+([A-Z][a-zA-Z\s]+)',
                ]
                
                for pattern in location_patterns:
                    match = re.search(pattern, text)
                    if match:
                        location_name = match.group(1).strip()
                        break
                
                # If no location name found, try to extract from headings
                if not location_name:
                    heading = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
                    if heading:
                        location_name = heading.get_text(strip=True)
                
                # Extract join link (could be Zoom, Teams, or other meeting platforms)
                join_link = None
                link_text = None
                
                # Look for "Click to Join" or similar text with a link
                join_link_patterns = [
                    r'click\s+to\s+join[^\n]*',
                    r'join\s+(?:this\s+)?(?:online\s+)?(?:group\s+)?sitting[^\n]*',
                    r'join\s+meeting[^\n]*',
                ]
                
                # First, try to find the link text and then get the associated link
                for pattern in join_link_patterns:
                    match = re.search(pattern, text, re.I)
                    if match:
                        link_text = match.group(0)
                        logger.info(f"      🔗 Found join text: {link_text[:50]}")
                        # Find the link near this text
                        # Look for <a> tags in the container
                        link_tags = container.find_all('a', href=True)
                        for link_tag in link_tags:
                            link_text_content = link_tag.get_text(strip=True).lower()
                            link_href = link_tag.get('href', '')
                            # Check if link text contains join keywords OR if href contains meeting platform
                            if ('join' in link_text_content or 'click' in link_text_content or 
                                any(platform in link_href.lower() for platform in ['zoom', 'teams', 'meet', 'webex'])):
                                join_link = link_href
                                if join_link and not join_link.startswith('http'):
                                    # Relative URL - make it absolute
                                    if join_link.startswith('/'):
                                        join_link = f"https://www.dhamma.org{join_link}"
                                    else:
                                        join_link = f"https://www.dhamma.org/{join_link}"
                                logger.info(f"      ✅ Found join link: {join_link}")
                                break
                        if join_link:
                            break
                
                # Fallback: Look for zoom/teams links directly
                if not join_link:
                    meeting_link_patterns = [
                        # Teams links (various formats)
                        r'https?://[^\s]*teams\.microsoft\.com/[^\s\)]+',
                        r'https?://teams\.microsoft\.com/l/[^\s\)]+',
                        r'https?://teams\.microsoft\.com/meetup-join/[^\s\)]+',
                        # Zoom links
                        r'https?://[^\s]*zoom\.(?:us|com)/[^\s\)]+',
                        r'zoom\.(?:us|com)/j/[^\s\)]+',
                        # Google Meet links
                        r'https?://meet\.google\.com/[^\s\)]+',
                        # Generic meeting links
                        r'meeting\s+id[:\s]+(\d+)',
                        r'zoom\s+id[:\s]+(\d+)',
                    ]
                    
                    for pattern in meeting_link_patterns:
                        match = re.search(pattern, text + ' ' + html, re.I)
                        if match:
                            matched_text = match.group(0)
                            if matched_text.startswith('http'):
                                join_link = matched_text
                            elif 'meeting\s+id' in pattern or 'zoom\s+id' in pattern:
                                # Handle meeting ID patterns
                                if match.lastindex and match.group(1):
                                    join_link = f"https://zoom.us/j/{match.group(1)}"
                            break
                
                # Also check for <a> tags with meeting links
                if not join_link:
                    link_tags = container.find_all('a', href=True)
                    for link_tag in link_tags:
                        href = link_tag.get('href', '')
                        href_lower = href.lower()
                        # Check for various meeting platforms
                        if any(platform in href_lower for platform in ['zoom', 'teams.microsoft', 'teams', 'meet.google', 'webex', 'gotomeeting']):
                            join_link = href
                            if not join_link.startswith('http'):
                                # Handle relative URLs
                                if join_link.startswith('/'):
                                    join_link = f"https://www.dhamma.org{join_link}"
                                else:
                                    join_link = 'https://' + join_link
                            logger.info(f"      ✅ Found meeting link: {join_link}")
                            break
                
                # Use join_link as zoom_link for compatibility
                zoom_link = join_link
                
                # Extract timezone with location code (e.g., "SE, Central European Time (CET)")
                timezone = None
                timezone_full = None  # Full timezone string including location code
                timezone_patterns = [
                    r'([A-Z]{2}),\s*([^\(]+)\s*\(([^\)]+)\)',  # "SE, Central European Time (CET)"
                    r'([A-Z]{2}),\s*([^\(]+)',  # "SE, Central European Time" without abbreviation
                    r'(?:timezone|tz)[:\s]+([A-Z][a-zA-Z/]+)',
                    r'([A-Z][a-zA-Z/]+)\s+time',
                    r'(EST|EDT|PST|PDT|CST|CDT|MST|MDT|UTC|GMT|CET|CEST|IST|ICT|JST)',
                ]
                
                for pattern in timezone_patterns:
                    match = re.search(pattern, text, re.I)
                    if match:
                        if len(match.groups()) >= 3:
                            # Full format: "SE, Central European Time (CET)"
                            location_code = match.group(1).strip()
                            timezone_name = match.group(2).strip()
                            timezone_abbr = match.group(3).strip()
                            timezone_full = f"{location_code}, {timezone_name} ({timezone_abbr})"
                            logger.info(f"      ✅ Found timezone: {timezone_full}")
                            # Map to standard timezone
                            tz_map = {
                                'CET': 'Europe/Berlin',
                                'CEST': 'Europe/Berlin',
                                'EST': 'America/New_York',
                                'EDT': 'America/New_York',
                                'PST': 'America/Los_Angeles',
                                'PDT': 'America/Los_Angeles',
                                'CST': 'America/Chicago',
                                'CDT': 'America/Chicago',
                                'MST': 'America/Denver',
                                'MDT': 'America/Denver',
                                'IST': 'Asia/Kolkata',
                                'ICT': 'Asia/Ho_Chi_Minh',
                                'JST': 'Asia/Tokyo',
                            }
                            timezone = tz_map.get(timezone_abbr.upper(), 'Europe/Berlin')
                        elif len(match.groups()) >= 2:
                            # Format: "SE, Central European Time"
                            location_code = match.group(1).strip()
                            timezone_name = match.group(2).strip()
                            timezone_full = f"{location_code}, {timezone_name}"
                            logger.info(f"      ✅ Found timezone: {timezone_full}")
                            timezone = 'Europe/Berlin'  # Default for European timezones
                        else:
                            tz_str = match.group(1).strip()
                            logger.info(f"      ✅ Found timezone abbreviation: {tz_str}")
                            # Map common timezone abbreviations
                            tz_map = {
                                'EST': 'America/New_York',
                                'EDT': 'America/New_York',
                                'PST': 'America/Los_Angeles',
                                'PDT': 'America/Los_Angeles',
                                'CST': 'America/Chicago',
                                'CDT': 'America/Chicago',
                                'MST': 'America/Denver',
                                'MDT': 'America/Denver',
                                'CET': 'Europe/Berlin',
                                'CEST': 'Europe/Berlin',
                                'IST': 'Asia/Kolkata',
                                'ICT': 'Asia/Ho_Chi_Minh',
                                'JST': 'Asia/Tokyo',
                            }
                            timezone = tz_map.get(tz_str.upper(), tz_str)
                        break
                
                # Extract schedule with days of week and times (e.g., "Wednesdays 7:00 p.m., Sundays 8:00 a.m.")
                schedule_entries = []  # List of (day_of_week, time) tuples
                
                # Pattern to match: "Wednesdays 7:00 p.m." or "Sundays 8:00 a.m."
                # Also handle: "Wednesday 7:00 p.m." (singular)
                day_time_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)s?\s+(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?|AM|PM)'
                matches = re.finditer(day_time_pattern, text, re.I)
                
                for match in matches:
                    day_name = match.group(1).strip()
                    hour = int(match.group(2))
                    minute = int(match.group(3)) if match.group(3) else 0
                    ampm = match.group(4).upper().replace('.', '')
                    
                    # Convert to 24-hour format
                    if ampm == 'PM' and hour != 12:
                        hour += 12
                    elif ampm == 'AM' and hour == 12:
                        hour = 0
                    
                    schedule_time = time(hour, minute)
                    schedule_entries.append((day_name, schedule_time))
                    logger.info(f"      📅 Found schedule: {day_name} at {schedule_time.strftime('%H:%M')}")
                
                # If no day-specific schedules found, look for general times (daily)
                if not schedule_entries:
                    time_patterns = [
                        r'(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm|a\.?m\.?|p\.?m\.?)',
                        r'(\d{1,2})\s*(AM|PM|am|pm|a\.?m\.?|p\.?m\.?)',
                    ]
                    
                    for pattern in time_patterns:
                        matches = re.finditer(pattern, text, re.I)
                        for match in matches:
                            hour = int(match.group(1))
                            minute = int(match.group(2)) if match.group(2) else 0
                            ampm = match.group(3).upper().replace('.', '')
                            
                            # Convert to 24-hour format
                            if ampm == 'PM' and hour != 12:
                                hour += 12
                            elif ampm == 'AM' and hour == 12:
                                hour = 0
                            
                            # If no day specified, treat as daily
                            schedule_entries.append(('Daily', time(hour, minute)))
                
                # If still no times found, look for common patterns like "daily at 7 AM and 6 PM"
                if not schedule_entries:
                    daily_pattern = r'daily\s+(?:at\s+)?(\d{1,2}):?(\d{2})?\s*(AM|PM|a\.?m\.?|p\.?m\.?)'
                    matches = re.finditer(daily_pattern, text, re.I)
                    for match in matches:
                        hour = int(match.group(1))
                        minute = int(match.group(2)) if match.group(2) else 0
                        ampm = match.group(3).upper().replace('.', '')
                        
                        if ampm == 'PM' and hour != 12:
                            hour += 12
                        elif ampm == 'AM' and hour == 12:
                            hour = 0
                        
                        schedule_entries.append(('Daily', time(hour, minute)))
                
                # Extract password if mentioned
                password = None
                password_patterns = [
                    r'password[:\s]+([^\s\)]+)',
                    r'passcode[:\s]+([^\s\)]+)',
                    r'pwd[:\s]+([^\s\)]+)',
                ]
                
                for pattern in password_patterns:
                    match = re.search(pattern, text, re.I)
                    if match:
                        password = match.group(1).strip()
                        break
                
                # Create a unique identifier for this location
                location_id = f"{location_name or 'Unknown'}_{zoom_link or 'no_link'}"
                if location_id in processed_locations:
                    continue
                processed_locations.add(location_id)
                
                # Log what we found in this container
                logger.info(f"   📦 Processing container:")
                logger.info(f"      Location: {location_name or 'None'}")
                logger.info(f"      Timezone: {timezone_full or timezone or 'None'}")
                logger.info(f"      Join Link: {zoom_link or 'None'}")
                logger.info(f"      Schedule entries: {len(schedule_entries)}")
                
                # If we have at least a join link or location name, create recurring events
                if zoom_link or location_name:
                    # Check if this container text is in English
                    is_english = is_english_text(text)
                    
                    # Create an event for each schedule entry (day + time combination)
                    if schedule_entries:
                        for day_name, schedule_time in schedule_entries:
                            time_str = schedule_time.strftime('%H:%M')
                            end_time = (datetime.combine(date.today(), schedule_time) + timedelta(hours=1)).time()
                            end_time_str = end_time.strftime('%H:%M')
                            
                            # Build specific title based on what was scraped
                            title_parts = ["Vipassana Group Sitting"]
                            
                            # Add day of week to title
                            if day_name != 'Daily':
                                title_parts.append(day_name)
                            
                            # Add timezone info
                            if timezone_full:
                                title_parts.append(timezone_full)
                            elif timezone:
                                title_parts.append(timezone)
                            elif location_name:
                                title_parts.append(location_name)
                            
                            # Add time to title for clarity
                            time_display = schedule_time.strftime('%I:%M %p').lstrip('0')
                            title_parts.append(f"at {time_display}")
                            
                            title = " - ".join(title_parts)
                            
                            # Build recurrence rule based on day
                            if day_name == 'Daily':
                                recurrence_rule = 'FREQ=DAILY'
                                key = (timezone_full or timezone or 'Unknown', time_str, 'Daily')
                            else:
                                # Map day name to RRULE day code
                                day_map = {
                                    'Monday': 'MO',
                                    'Tuesday': 'TU',
                                    'Wednesday': 'WE',
                                    'Thursday': 'TH',
                                    'Friday': 'FR',
                                    'Saturday': 'SA',
                                    'Sunday': 'SU'
                                }
                                day_code = day_map.get(day_name, 'MO')
                                recurrence_rule = f'FREQ=WEEKLY;BYDAY={day_code}'
                                key = (timezone_full or timezone or 'Unknown', time_str, day_code)
                            
                            event_data = {
                                'title': title,
                                'description': _build_description(location_name, zoom_link, password, timezone_full or timezone),
                                'start_date': date.today().isoformat(),
                                'end_date': date.today().isoformat(),
                                'start_time': time_str,
                                'end_time': end_time_str,
                                'event_type': 'meditation',
                                'url': zoom_link or VIPASSANA_URL,
                                'venue_name': f"{VENUE_NAME} - {location_name}" if location_name else VENUE_NAME,
                                'city_name': _extract_city_name(location_name, timezone),
                                'source': SOURCE_NAME,
                                'zoom_link': zoom_link,
                                'zoom_password': password,
                                'timezone': timezone_full or timezone,
                                'location_name': location_name,
                                'is_recurring': True,
                                'recurrence_rule': recurrence_rule,
                                'is_english': is_english,
                                'day_of_week': day_name
                            }
                            
                            # Check if we already have an event for this timezone+time+day combination
                            if key in events_by_timezone_time:
                                existing_event = events_by_timezone_time[key]
                                existing_is_english = existing_event.get('is_english', False)
                                
                                # Prefer English version
                                if is_english and not existing_is_english:
                                    logger.info(f"   🔄 Replacing non-English event with English version for {key}")
                                    events_by_timezone_time[key] = event_data
                                elif is_english == existing_is_english:
                                    logger.debug(f"   ⏭️  Skipping duplicate event for {key} (same language)")
                                else:
                                    logger.debug(f"   ⏭️  Keeping existing English event for {key}")
                            else:
                                events_by_timezone_time[key] = event_data
                                logger.info(f"   ✅ Added event: {day_name} at {time_str} for {timezone_full or timezone} ({'English' if is_english else 'non-English'})")
                    else:
                        # If no specific schedule, create a default daily recurring event
                        time_str = '19:00'
                        timezone_key = timezone_full or timezone or 'Unknown'
                        key = (timezone_key, time_str, 'Daily')
                        
                        # Build specific title
                        title_parts = ["Vipassana Group Sitting"]
                        if timezone_key != 'Unknown':
                            title_parts.append(timezone_key)
                        if location_name:
                            title_parts.append(location_name)
                        title = " - ".join(title_parts)
                        
                        event_data = {
                            'title': title,
                            'description': _build_description(location_name, zoom_link, password, timezone_full or timezone),
                            'start_date': date.today().isoformat(),
                            'end_date': date.today().isoformat(),
                            'start_time': '19:00',
                            'end_time': '20:00',
                            'event_type': 'meditation',
                            'url': zoom_link or VIPASSANA_URL,
                            'venue_name': f"{VENUE_NAME} - {location_name}" if location_name else VENUE_NAME,
                            'city_name': _extract_city_name(location_name, timezone),
                            'source': SOURCE_NAME,
                            'zoom_link': zoom_link,
                            'zoom_password': password,
                            'timezone': timezone_full or timezone,
                            'location_name': location_name,
                            'is_recurring': True,
                            'recurrence_rule': 'FREQ=DAILY',
                            'is_english': is_english,
                            'day_of_week': 'Daily'
                        }
                        
                        if key in events_by_timezone_time:
                            existing_event = events_by_timezone_time[key]
                            existing_is_english = existing_event.get('is_english', False)
                            if is_english and not existing_is_english:
                                logger.info(f"   🔄 Replacing non-English event with English version for {key}")
                                events_by_timezone_time[key] = event_data
                            elif is_english == existing_is_english:
                                logger.debug(f"   ⏭️  Skipping duplicate event for {key}")
                            else:
                                logger.debug(f"   ⏭️  Keeping existing English event for {key}")
                        else:
                            events_by_timezone_time[key] = event_data
                            logger.info(f"   ✅ Added default event for {timezone_key} ({'English' if is_english else 'non-English'})")
                    
                    logger.info(f"   ✅ Found location: {location_name or 'Unknown'} with {len(schedule_entries) or 1} schedule entry/entries")
            except Exception as container_error:
                logger.warning(f"   ⚠️  Error processing container: {container_error}")
                continue
        
        # Convert the deduplicated events dictionary to a list
        events = list(events_by_timezone_time.values())
        logger.info(f"   📊 After language filtering: {len(events)} unique events (timezone+time+day combinations)")
        
        # Log summary of events found
        if events:
            logger.info(f"   📋 Events summary:")
            for event in events[:10]:  # Show first 10
                title = event.get('title', 'Unknown')
                day = event.get('day_of_week', 'Daily')
                time = event.get('start_time', 'Unknown')
                tz = event.get('timezone', 'Unknown')
                logger.info(f"      - {title} ({day} at {time}, {tz})")
            if len(events) > 10:
                logger.info(f"      ... and {len(events) - 10} more events")
        
        # If we didn't find structured data, try to extract from raw text with more aggressive patterns
        if not events:
            logger.warning("   ⚠️  No structured events found, trying aggressive raw text extraction...")
            page_text = soup.get_text(separator='\n')
            html_text = str(soup)
            
            # Debug: Log a sample of the page text
            logger.info(f"   Page text sample (first 2000 chars): {page_text[:2000]}")
            
            # Try to find sections by looking for timezone patterns in the text
            # Split text into lines and look for timezone + schedule patterns
            lines = page_text.split('\n')
            logger.info(f"   Analyzing {len(lines)} lines of text...")
            
            current_section = []
            sections = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                # Look for timezone indicators
                if any(indicator in line_lower for indicator in ['timezone', 'cet', 'est', 'pst', 'central european', 'eastern time', 'pacific time']):
                    # Save previous section if it had content
                    if current_section and len(' '.join(current_section)) > 50:
                        sections.append('\n'.join(current_section))
                    # Start new section
                    current_section = [line]
                elif current_section:
                    # Continue building current section
                    current_section.append(line)
                    # If section gets too long or we hit a clear separator, save it
                    if len(current_section) > 20 or line.strip() == '':
                        if len(' '.join(current_section)) > 50:
                            sections.append('\n'.join(current_section))
                        current_section = []
            
            # Save last section
            if current_section and len(' '.join(current_section)) > 50:
                sections.append('\n'.join(current_section))
            
            logger.info(f"   Found {len(sections)} potential timezone sections")
            
            # Process each section
            for section_text in sections:
                logger.info(f"   Processing section ({len(section_text)} chars): {section_text[:200]}...")
                
                # Extract timezone from section
                timezone_full = None
                timezone = None
                tz_match = re.search(r'([A-Z]{2}),\s*([^\(]+)\s*\(([^\)]+)\)', section_text)
                if tz_match:
                    location_code = tz_match.group(1).strip()
                    timezone_name = tz_match.group(2).strip()
                    timezone_abbr = tz_match.group(3).strip()
                    timezone_full = f"{location_code}, {timezone_name} ({timezone_abbr})"
                    tz_map = {'CET': 'Europe/Berlin', 'CEST': 'Europe/Berlin', 'EST': 'America/New_York', 'EDT': 'America/New_York', 'PST': 'America/Los_Angeles', 'PDT': 'America/Los_Angeles'}
                    timezone = tz_map.get(timezone_abbr.upper(), 'Europe/Berlin')
                
                # Extract day+time patterns from section
                day_time_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)s?\s+(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?|AM|PM)'
                schedule_matches = re.finditer(day_time_pattern, section_text, re.I)
                
                for match in schedule_matches:
                    day_name = match.group(1).strip()
                    hour = int(match.group(2))
                    minute = int(match.group(3)) if match.group(3) else 0
                    ampm = match.group(4).upper().replace('.', '')
                    
                    # Convert to 24-hour format
                    if ampm == 'PM' and hour != 12:
                        hour += 12
                    elif ampm == 'AM' and hour == 12:
                        hour = 0
                    
                    schedule_time = time(hour, minute)
                    end_time = (datetime.combine(date.today(), schedule_time) + timedelta(hours=1)).time()
                    
                    # Extract join link from section (look in HTML near this text)
                    join_link = None
                    # Find the section in HTML
                    section_html_match = re.search(re.escape(section_text[:100]), html_text, re.I)
                    if section_html_match:
                        # Get HTML around this match
                        start_pos = max(0, section_html_match.start() - 500)
                        end_pos = min(len(html_text), section_html_match.end() + 500)
                        section_html = html_text[start_pos:end_pos]
                        section_soup = BeautifulSoup(section_html, 'html.parser')
                        
                        # Look for links
                        links = section_soup.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            if any(platform in href.lower() for platform in ['zoom', 'teams', 'meet']):
                                join_link = href
                                if not join_link.startswith('http'):
                                    if join_link.startswith('/'):
                                        join_link = f"https://www.dhamma.org{join_link}"
                                    else:
                                        join_link = f"https://www.dhamma.org/{join_link}"
                                break
                    
                    # Build title
                    title_parts = ["Vipassana Group Sitting", day_name]
                    if timezone_full:
                        title_parts.append(timezone_full)
                    time_display = schedule_time.strftime('%I:%M %p').lstrip('0')
                    title_parts.append(f"at {time_display}")
                    title = " - ".join(title_parts)
                    
                    # Build recurrence rule
                    day_map = {'Monday': 'MO', 'Tuesday': 'TU', 'Wednesday': 'WE', 'Thursday': 'TH', 'Friday': 'FR', 'Saturday': 'SA', 'Sunday': 'SU'}
                    day_code = day_map.get(day_name, 'MO')
                    recurrence_rule = f'FREQ=WEEKLY;BYDAY={day_code}'
                    
                    # Check if English
                    is_english = is_english_text(section_text)
                    key = (timezone_full or timezone or 'Unknown', schedule_time.strftime('%H:%M'), day_code)
                    
                    event_data = {
                        'title': title,
                        'description': f"Virtual Vipassana meditation group sitting.\n\nTimezone: {timezone_full or timezone or 'Unknown'}\n\nJoin Link: {join_link or 'See main page'}\n\nSource: {VIPASSANA_URL}",
                        'start_date': date.today().isoformat(),
                        'end_date': date.today().isoformat(),
                        'start_time': schedule_time.strftime('%H:%M'),
                        'end_time': end_time.strftime('%H:%M'),
                        'event_type': 'meditation',
                        'url': join_link or VIPASSANA_URL,
                        'venue_name': VENUE_NAME,
                        'city_name': 'Virtual',
                        'source': SOURCE_NAME,
                        'zoom_link': join_link,
                        'timezone': timezone_full or timezone,
                        'is_recurring': True,
                        'recurrence_rule': recurrence_rule,
                        'is_english': is_english,
                        'day_of_week': day_name
                    }
                    
                    # Check for duplicates
                    if key not in events_by_timezone_time:
                        events_by_timezone_time[key] = event_data
                        logger.info(f"   ✅ Extracted from raw text: {day_name} at {schedule_time.strftime('%H:%M')} for {timezone_full or timezone}")
                    elif is_english and not events_by_timezone_time[key].get('is_english', False):
                        events_by_timezone_time[key] = event_data
                        logger.info(f"   🔄 Replaced with English version: {day_name} at {schedule_time.strftime('%H:%M')}")
            
            # Update events list
            events = list(events_by_timezone_time.values())
            
            # Look for zoom links in the entire page (more flexible pattern)
            # Try multiple patterns to catch different zoom link formats
            zoom_patterns = [
                r'https?://[^\s\)]*zoom\.(?:us|com)/[^\s\)]+',
                r'https?://zoom\.(?:us|com)/j/[^\s\)]+',
                r'zoom\.(?:us|com)/j/[^\s\)]+',
                r'zoom\.(?:us|com)/[^\s\)]+',
            ]
            
            zoom_links = []
            for pattern in zoom_patterns:
                matches = re.findall(pattern, page_text, re.I)
                zoom_links.extend(matches)
            
            # Also try to find zoom links in HTML attributes
            html_text = str(soup)
            for pattern in zoom_patterns:
                matches = re.findall(pattern, html_text, re.I)
                zoom_links.extend(matches)
            
            # Also check all <a> tags
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if 'zoom' in href.lower():
                    if href not in zoom_links:
                        zoom_links.append(href)
            
            # Clean and normalize zoom links
            cleaned_links = []
            for link in zoom_links:
                # Remove trailing punctuation
                link = link.rstrip('.,;:!?)')
                # Ensure it's a full URL
                if link.startswith('http'):
                    cleaned_links.append(link)
                elif link.startswith('zoom.us') or link.startswith('zoom.com'):
                    cleaned_links.append(f"https://{link}")
            
            if cleaned_links:
                unique_links = list(set(cleaned_links))
                logger.info(f"   Found {len(unique_links)} unique zoom links: {unique_links[:3]}...")
                # Create a basic event for each unique zoom link
                for zoom_link in unique_links:
                    # Create a single recurring event instead of individual daily events
                    today = date.today()
                    time_str = '19:00'
                    timezone_key = 'Unknown'
                    key = (timezone_key, time_str)
                    
                    # Check if we already have this zoom link
                    if key not in events_by_timezone_time:
                        event_data = {
                            'title': "Vipassana Group Sitting",
                            'description': f"Virtual Vipassana meditation group sitting.\n\nZoom Link: {zoom_link}\n\nSource: {VIPASSANA_URL}",
                            'start_date': today.isoformat(),
                            'end_date': today.isoformat(),
                            'start_time': '19:00',
                            'end_time': '20:00',
                            'event_type': 'meditation',
                            'url': zoom_link,
                            'venue_name': VENUE_NAME,
                            'city_name': 'Virtual',
                            'source': SOURCE_NAME,
                            'zoom_link': zoom_link,
                            'is_recurring': True,  # Flag to indicate this is a recurring event
                            'recurrence_rule': 'FREQ=DAILY',  # Daily recurrence, no end date
                            'is_english': True  # Assume English for raw text extraction
                        }
                        events_by_timezone_time[key] = event_data
                        logger.info(f"   ✅ Created recurring event for: {zoom_link}")
                    else:
                        logger.debug(f"   ⏭️  Skipping duplicate zoom link: {zoom_link}")
                
                # Update events list from dictionary
                events = list(events_by_timezone_time.values())
            else:
                logger.warning("   ⚠️  No zoom links found anywhere on the page")
                logger.warning("   This might mean:")
                logger.warning("   1. The page structure is different than expected")
                logger.warning("   2. Zoom links are loaded dynamically via JavaScript")
                logger.warning("   3. The page requires authentication or has bot protection")
                
                # As a last resort, create a placeholder event pointing to the main page
                logger.info("   Creating a placeholder event with link to the main page...")
                today = date.today()
                event_data = {
                    'title': "Vipassana Group Sitting",
                    'description': f"Virtual Vipassana meditation group sitting.\n\nPlease visit {VIPASSANA_URL} for zoom links and schedules.\n\nSource: {VIPASSANA_URL}",
                    'start_date': today.isoformat(),
                    'end_date': today.isoformat(),
                    'start_time': '19:00',
                    'end_time': '20:00',
                    'event_type': 'meditation',
                    'url': VIPASSANA_URL,
                    'venue_name': VENUE_NAME,
                    'city_name': 'Virtual',
                    'source': SOURCE_NAME,
                    'is_recurring': True,
                    'recurrence_rule': 'FREQ=DAILY'
                }
                events.append(event_data)
        
        logger.info(f"✅ Scraped {len(events)} Vipassana events")
        
        # If still no events, try LLM fallback to extract from page text
        if not events:
            logger.warning("   ⚠️  No events found via pattern matching, trying LLM extraction...")
            events = _try_llm_extraction(soup, response.text)
        
        # Don't create placeholder events - only return real events found
        if not events:
            logger.warning("   ⚠️  No events found. The scraper couldn't extract any schedule information from the page.")
            logger.warning("   This might mean:")
            logger.warning("   1. The page structure is different than expected")
            logger.warning("   2. Zoom/Teams links are loaded dynamically via JavaScript")
            logger.warning("   3. The page requires authentication or has bot protection")
            logger.warning("   4. The page content has changed")
        
        return events
        
    except Exception as e:
        logger.error(f"❌ Error scraping Vipassana events: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Don't create placeholder events on error - return empty list
        logger.error("   Returning empty list - no placeholder events will be created")
        return []


def _try_llm_extraction(soup, html_text):
    """Try to use LLM to extract schedule information from page text"""
    events = []
    
    try:
        from scripts.enhanced_llm_fallback import EnhancedLLMFallback
        
        logger.info("   🤖 Attempting LLM extraction...")
        llm = EnhancedLLMFallback(silent=True)
        
        # Get page text (first 8000 chars to stay within token limits)
        page_text = soup.get_text(separator='\n')[:8000]
        
        prompt = f"""Extract Vipassana meditation group sitting schedule information from this webpage text.

Webpage text:
{page_text}

I need you to extract all virtual group sitting schedules. For each timezone/location, extract:
1. Timezone information (e.g., "SE, Central European Time (CET)" or "Eastern Time (ET)")
2. Days of the week and times (e.g., "Wednesdays 7:00 p.m., Sundays 8:00 a.m.")
3. Join links (Zoom, Teams, or other meeting platform links)
4. Any passwords if mentioned

Return a JSON array with this structure:
[
    {{
        "timezone_full": "SE, Central European Time (CET)" or location code + timezone,
        "timezone": "Europe/Berlin" or standard timezone name,
        "schedule": [
            {{"day": "Wednesday", "time": "19:00"}},
            {{"day": "Sunday", "time": "08:00"}}
        ],
        "join_link": "https://zoom.us/... or https://teams.microsoft.com/...",
        "password": "password if mentioned or null",
        "location_name": "location name if mentioned or null"
    }}
]

Important:
- Return ONLY valid JSON array, no other text
- Extract ALL timezone sections you find
- For each timezone, extract ALL day+time combinations
- Include the join link if you can find it (look for "Click to Join" or similar text)
- Use 24-hour format for times (e.g., "19:00" for 7:00 PM, "08:00" for 8:00 AM)
- If end time is not specified, assume 1-hour duration
- Prefer English language entries if multiple languages exist for the same timezone+time"""
        
        response = llm.query_with_fallback(prompt)
        
        if response and response.get('success') and response.get('content'):
            content = response['content']
            import json
            import re
            
            # Look for JSON array in the response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                try:
                    llm_data = json.loads(json_match.group())
                    logger.info(f"   ✅ LLM extracted {len(llm_data)} timezone sections")
                    
                    today = date.today()
                    events_by_timezone_time = {}
                    
                    for section_data in llm_data:
                        timezone_full = section_data.get('timezone_full', '')
                        timezone = section_data.get('timezone', 'Europe/Berlin')
                        schedule = section_data.get('schedule', [])
                        join_link = section_data.get('join_link')
                        password = section_data.get('password')
                        location_name = section_data.get('location_name')
                        
                        for schedule_item in schedule:
                            day_name = schedule_item.get('day', 'Daily')
                            time_str = schedule_item.get('time', '19:00')
                            
                            # Parse time
                            try:
                                hour, minute = map(int, time_str.split(':'))
                                schedule_time = time(hour, minute)
                            except:
                                schedule_time = time(19, 0)  # Default
                            
                            end_time = (datetime.combine(today, schedule_time) + timedelta(hours=1)).time()
                            
                            # Build title
                            title_parts = ["Vipassana Group Sitting"]
                            if day_name != 'Daily':
                                title_parts.append(day_name)
                            if timezone_full:
                                title_parts.append(timezone_full)
                            time_display = schedule_time.strftime('%I:%M %p').lstrip('0')
                            title_parts.append(f"at {time_display}")
                            title = " - ".join(title_parts)
                            
                            # Build recurrence rule
                            if day_name == 'Daily':
                                recurrence_rule = 'FREQ=DAILY'
                                key = (timezone_full or timezone, schedule_time.strftime('%H:%M'), 'Daily')
                            else:
                                day_map = {'Monday': 'MO', 'Tuesday': 'TU', 'Wednesday': 'WE', 'Thursday': 'TH', 'Friday': 'FR', 'Saturday': 'SA', 'Sunday': 'SU'}
                                day_code = day_map.get(day_name, 'MO')
                                recurrence_rule = f'FREQ=WEEKLY;BYDAY={day_code}'
                                key = (timezone_full or timezone, schedule_time.strftime('%H:%M'), day_code)
                            
                            event_data = {
                                'title': title,
                                'description': _build_description(location_name, join_link, password, timezone_full or timezone),
                                'start_date': today.isoformat(),
                                'end_date': today.isoformat(),
                                'start_time': schedule_time.strftime('%H:%M'),
                                'end_time': end_time.strftime('%H:%M'),
                                'event_type': 'meditation',
                                'url': join_link or VIPASSANA_URL,
                                'venue_name': f"{VENUE_NAME} - {location_name}" if location_name else VENUE_NAME,
                                'city_name': 'Virtual',
                                'source': SOURCE_NAME,
                                'zoom_link': join_link,
                                'zoom_password': password,
                                'timezone': timezone_full or timezone,
                                'location_name': location_name,
                                'is_recurring': True,
                                'recurrence_rule': recurrence_rule,
                                'is_english': True,  # LLM should prefer English
                                'day_of_week': day_name
                            }
                            
                            if key not in events_by_timezone_time:
                                events_by_timezone_time[key] = event_data
                                logger.info(f"   ✅ LLM extracted: {day_name} at {schedule_time.strftime('%H:%M')} for {timezone_full or timezone}")
                    
                    events = list(events_by_timezone_time.values())
                    logger.info(f"   ✅ LLM extraction created {len(events)} events")
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"   ⚠️  Failed to parse LLM JSON response: {e}")
                    logger.debug(f"   LLM response: {content[:500]}")
            else:
                logger.warning("   ⚠️  LLM response did not contain valid JSON array")
        else:
            logger.warning("   ⚠️  LLM fallback did not return valid response")
            
    except Exception as e:
        logger.warning(f"   ⚠️  LLM extraction failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    return events


def _build_description(location_name, zoom_link, password, timezone):
    """Build event description with all relevant information"""
    desc_parts = []
    
    if location_name:
        desc_parts.append(f"Location: {location_name}")
    
    if zoom_link:
        desc_parts.append(f"\nZoom Link: {zoom_link}")
    
    if password:
        desc_parts.append(f"Password: {password}")
    
    if timezone:
        desc_parts.append(f"Timezone: {timezone}")
    
    desc_parts.append(f"\nSource: {VIPASSANA_URL}")
    desc_parts.append("\nVirtual Vipassana meditation group sitting. Please join a few minutes early.")
    
    return "\n".join(desc_parts)


def _extract_city_name(location_name, timezone):
    """Extract city name from location name or timezone"""
    if location_name:
        # Try to extract city from location name
        # Common patterns: "Dhamma [City]", "[City] Center", etc.
        city_match = re.search(r'Dhamma\s+([A-Z][a-zA-Z\s]+)', location_name)
        if city_match:
            return city_match.group(1).strip()
        
        # Remove common suffixes
        city = re.sub(r'\s+(?:Center|Meditation|Group|Sitting)$', '', location_name, flags=re.I)
        if city != location_name:
            return city
    
    # Fallback to timezone-based city
    if timezone:
        tz_city_map = {
            'America/New_York': 'New York',
            'America/Los_Angeles': 'Los Angeles',
            'America/Chicago': 'Chicago',
            'America/Denver': 'Denver',
        }
        return tz_city_map.get(timezone, 'Virtual')
    
    return 'Virtual'


def create_events_in_database(events):
    """Create events in the database from scraped data"""
    created_count = 0
    
    with app.app_context():
        # Get or create a virtual city for these events
        city = City.query.filter_by(name='Virtual', country='Global').first()
        if not city:
            city = City(
                name='Virtual',
                country='Global',
                timezone='UTC'
            )
            db.session.add(city)
            db.session.commit()
            logger.info(f"✅ Created virtual city")
        
        # Get or create venue
        venue = Venue.query.filter_by(name=VENUE_NAME, city_id=city.id).first()
        if not venue:
            venue = Venue(
                name=VENUE_NAME,
                city_id=city.id,
                website_url=VIPASSANA_URL,
                venue_type="virtual",
                description="Virtual Vipassana meditation group sittings from various Dhamma centers worldwide"
            )
            db.session.add(venue)
            db.session.commit()
            logger.info(f"✅ Created venue: {VENUE_NAME}")
        
        # Get or create source
        source = Source.query.filter_by(url=VIPASSANA_URL).first()
        if not source:
            source = Source(
                name=SOURCE_NAME,
                handle='',  # Required field, empty for website sources
                url=VIPASSANA_URL,
                city_id=city.id,
                source_type='website'
            )
            db.session.add(source)
            db.session.commit()
            logger.info(f"✅ Created source: {SOURCE_NAME}")
        
        for event_data in events:
            try:
                # Remove internal tracking fields before saving
                event_data.pop('is_english', None)
                event_data.pop('day_of_week', None)
                
                # Validate title
                title = event_data.get('title', '').strip()
                if not title:
                    logger.warning(f"   ⚠️  Skipping event: missing title")
                    continue
                
                # Check if event already exists (by title, date, time, and zoom link)
                start_date = datetime.fromisoformat(event_data['start_date']).date()
                start_time = time.fromisoformat(event_data['start_time'])
                zoom_link = event_data.get('zoom_link')
                
                existing = Event.query.filter_by(
                    title=title,
                    start_date=start_date,
                    start_time=start_time,
                    venue_id=venue.id
                ).first()
                
                if existing:
                    # Update zoom link if we have one and it's missing
                    if zoom_link and not existing.url:
                        existing.url = zoom_link
                        db.session.commit()
                    logger.debug(f"   ⏭️  Event already exists: {title}")
                    continue
                
                # Create new event
                description = event_data.get('description', '')
                
                # Add recurrence info to description if this is a recurring event
                if event_data.get('is_recurring'):
                    recurrence_rule = event_data.get('recurrence_rule', 'FREQ=DAILY')
                    description += f"\n\n[RECURRING: {recurrence_rule}]"
                
                event = Event(
                    title=title,
                    description=description,
                    start_date=start_date,
                    end_date=datetime.fromisoformat(event_data.get('end_date', event_data['start_date'])).date(),
                    start_time=start_time,
                    end_time=time.fromisoformat(event_data.get('end_time', '23:59')),
                    event_type=event_data.get('event_type', 'meditation'),
                    url=zoom_link or event_data.get('url', VIPASSANA_URL),
                    venue_id=venue.id,
                    city_id=city.id,
                    source='website',
                    source_url=VIPASSANA_URL
                )
                
                db.session.add(event)
                db.session.commit()
                created_count += 1
                logger.info(f"   ✅ Created event: {title} on {start_date} at {start_time}")
                
            except Exception as e:
                logger.error(f"   ❌ Error creating event {event_data.get('title', 'Unknown')}: {e}")
                db.session.rollback()
                continue
        
        logger.info(f"✅ Created {created_count} new events in database")
        return created_count


if __name__ == '__main__':
    print("🔍 Scraping Vipassana virtual events...")
    events = scrape_vipassana_events()
    
    if events:
        print(f"\n✅ Found {len(events)} events")
        print("\n📋 Sample Events:")
        for event in events[:5]:
            print(f"  - {event['title']} on {event['start_date']} at {event['start_time']}")
            if event.get('zoom_link'):
                print(f"    Zoom: {event['zoom_link']}")
        
        print("\n💾 Creating events in database...")
        created = create_events_in_database(events)
        print(f"✅ Created {created} new events")
    else:
        print("❌ No events found")
