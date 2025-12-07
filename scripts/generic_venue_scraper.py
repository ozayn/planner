#!/usr/bin/env python3
"""
Generic Venue Event Scraper - Optimized for Museums
A universal scraper optimized for museums that works for any venue/location by using 
common patterns learned from specialized scrapers. This serves as a fallback when no 
specialized scraper exists for a venue.

Key Features (Museum-Optimized):
- Museum-specific event selectors (exhibitions, gallery talks, programs, tours)
- Enhanced exhibition detection and date range parsing
- Improved bot protection handling with cloudscraper
- Extracts events from common HTML patterns
- Handles various date/time formats (especially exhibition date ranges)
- Extracts titles, descriptions, images, locations
- Works with different event listing page structures
- Handles registration information
- Supports multiple event types (exhibitions, talks, lectures, tours, workshops, etc.)
- Museum-specific event type detection
"""

import os
import sys
import re
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
from urllib3.exceptions import NameResolutionError, NewConnectionError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class GenericVenueScraper:
    """
    Generic scraper that works for any venue by using common patterns.
    This is designed to work alongside specialized scrapers as a fallback.
    """
    
    def __init__(self):
        """Initialize the generic scraper with common patterns"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
        # Disable SSL verification for sites with certificate issues
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configure retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            connect=3,
            read=3,
            redirect=3
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Cloudscraper instance (created on demand)
        self._cloudscraper = None
        
        # Initialize selectors and patterns
        self._initialize_selectors()
    
    def _get_cloudscraper(self, base_url=None):
        """Get or create a cloudscraper instance with enhanced headers"""
        if self._cloudscraper is None and CLOUDSCRAPER_AVAILABLE:
            self._cloudscraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
            self._cloudscraper.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            })
            self._cloudscraper.verify = False
            
            # Establish session by visiting base URL if provided
            if base_url:
                try:
                    logger.debug(f"   🔧 Establishing cloudscraper session with {base_url}...")
                    self._cloudscraper.get(base_url, timeout=15)
                    import time
                    time.sleep(1)
                except Exception as e:
                    logger.debug(f"   ⚠️  Could not establish initial session: {e}")
        
        return self._cloudscraper
    
    def _fetch_with_retry(self, url, use_cloudscraper=False, base_url=None, max_retries=3, delay=2):
        """Fetch URL with retry logic and exponential backoff"""
        import time
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = delay * (2 ** (attempt - 1))
                    logger.debug(f"   ⏳ Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                
                if use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
                    scraper = self._get_cloudscraper(base_url or url)
                    response = scraper.get(url, timeout=20, verify=False)
                else:
                    response = self.session.get(url, timeout=20)
                
                # If we get a 403 and not using cloudscraper yet, try cloudscraper
                if response.status_code == 403 and not use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
                    logger.info(f"   ⚠️  403 Forbidden, trying cloudscraper for {url}")
                    if attempt < max_retries - 1:
                        scraper = self._get_cloudscraper(base_url or url)
                        # Refresh session
                        try:
                            scraper.get(base_url or url, timeout=15, verify=False)
                            time.sleep(2)
                        except:
                            pass
                        continue
                
                response.raise_for_status()
                return response
                
            except (NameResolutionError, NewConnectionError) as e:
                logger.error(f"❌ DNS resolution failed for {url}: {e}")
                return None
            except Exception as e:
                if attempt == max_retries - 1:
                    if use_cloudscraper or not CLOUDSCRAPER_AVAILABLE:
                        raise
                    # Last attempt: try cloudscraper if we haven't already
                    logger.info(f"   ⚠️  Final attempt with cloudscraper for {url}")
                    try:
                        scraper = self._get_cloudscraper(base_url or url)
                        response = scraper.get(url, timeout=20, verify=False)
                        response.raise_for_status()
                        return response
                    except:
                        raise
                logger.debug(f"   ⚠️  Error on attempt {attempt + 1}: {e}")
        
        return None
    
    def _initialize_selectors(self):
        """Initialize event selectors and patterns"""
        # Museum-specific event selectors (prioritized for museums)
        self.museum_event_selectors = [
            # Exhibition selectors (highest priority for museums)
            '.exhibition', '.exhibitions', '.exhibition-item', '.exhibition-card',
            '.exhibition-teaser', '.exhibition-summary', '.exhibition-list-item',
            '.current-exhibition', '.upcoming-exhibition', '.past-exhibition',
            '.exhibition-block', '.exhibition-tile', '.exhibition-grid-item',
            # Museum program selectors
            '.program', '.program-item', '.program-card', '.program-entry',
            '.program-teaser', '.program-list-item', '.program-block',
            # Gallery talk/lecture selectors
            '.gallery-talk', '.curator-talk', '.artist-talk', '.lecture-series',
            '.talk', '.talks', '.lecture', '.lectures', '.speaker-event',
            '.panel-discussion', '.conversation', '.symposium',
            # Museum tour selectors
            '.tour', '.tours', '.guided-tour', '.walking-tour', '.tour-item',
            '.docent-tour', '.highlights-tour', '.special-tour',
            # Workshop/class selectors
            '.workshop', '.workshops', '.class', '.classes', '.course', '.courses',
            '.studio-class', '.art-class', '.family-program',
            # General event selectors
            '.event', '.events', '.event-item', '.event-card', '.event-list-item',
            '.event-entry', '.event-entry-item', '.event-teaser', '.event-summary',
            '.calendar-event', '.upcoming-event', '.past-event', '.featured-event',
            # Generic patterns (museum-specific)
            '[class*="exhibition"]', '[class*="program"]', '[class*="gallery"]',
            '[class*="event"]', '[class*="tour"]', '[class*="workshop"]',
            '[class*="lecture"]', '[class*="talk"]',
            # Data attributes
            '[data-event]', '[data-event-id]', '[data-event-type]',
            '[data-exhibition]', '[data-exhibition-id]',
            # Semantic HTML (museum-specific)
            'article.event', 'article.program', 'article.exhibition',
            'article.gallery-talk', 'article.lecture',
            'li.event', 'li.program', 'li.exhibition', 'li.talk',
            'div[itemtype*="Event"]', 'div[itemtype*="ExhibitionEvent"]',
            'div[itemtype*="VisualArtsEvent"]',
            # Common CMS patterns (museum websites)
            '.node-event', '.node-exhibition', '.node-program',
            '.view-events', '.view-exhibitions', '.view-programs',
            '.event-list', '.exhibition-list', '.program-list',
            '.events-grid', '.exhibitions-grid', '.programs-grid',
            # Museum-specific patterns
            '.collection-highlight', '.special-exhibition', '.featured-exhibition',
            '.on-view', '.current-show', '.upcoming-show'
        ]
        
        # Fallback to general event selectors if museum-specific ones don't work
        self.event_selectors = self.museum_event_selectors
        
        # Common date/time patterns
        self.date_patterns = [
            # Full dates with time (comma-separated format: "December 5, 2025, 5:00–6:00 PM")
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "December 5, 2025, 5:00–6:00 PM"
            # Full dates with time (pipe-separated format: "December 5, 2025 | 11:30 am–12:00 pm")
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?',  # "December 5, 2025 | 11:30 am–12:00 pm"
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # Date ranges (museum exhibitions often use these)
            r'(\w+)\s+(\d{1,2})\s*[–-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23 - August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*[–-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 - August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*[–—\-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 – August 23, 2026" (em dash)
            r'(\w+)\s+(\d{1,2})\s*[–—\-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23 – August 23, 2026" (em dash)
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+through\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 through August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+to\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 to August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*–\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026–August 23, 2026" (no spaces)
            # Standard formats
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "December 5, 2025"
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # "5 December 2025"
        ]
        
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am–12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*-\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am - 12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s+to\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am to 12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([AP]M)\s*[–-]\s*(\d{1,2}):(\d{2})\s*([AP]M)',  # "11:30 AM–12:00 PM"
            r'(\d{1,2}):(\d{2})\s*([AP]M)',  # "11:30 AM"
            r'(\d{1,2}):(\d{2})',  # "11:30"
        ]
    
    def scrape_venue_events(self, venue_url: str, venue_name: str = None, 
                           event_type: str = None, time_range: str = 'this_month') -> List[Dict]:
        """
        Main method to scrape events from any venue URL.
        
        Args:
            venue_url: The venue's website URL
            venue_name: Optional venue name for context
            event_type: Optional filter for event type
            time_range: Time range filter ('today', 'this_week', 'this_month')
            
        Returns:
            List of event dictionaries
        """
        events = []
        llm_fallback_used = False  # Track if we've already used LLM fallback
        
        try:
            logger.info(f"🔍 Generic scraper: Starting scrape for {venue_url}")
            logger.info(f"   Venue: {venue_name}")
            logger.info(f"   Event type filter: {event_type}")
            logger.info(f"   Time range: {time_range}")
            
            # Try to find event listing pages
            event_pages = self._discover_event_pages(venue_url)
            logger.info(f"   Discovered {len(event_pages)} event pages")
            
            # Scrape each event page
            for i, page_url in enumerate(event_pages, 1):
                logger.info(f"   Scraping event page {i}/{len(event_pages)}: {page_url}")
                page_events = self._scrape_event_page(
                    page_url, venue_name, event_type, time_range, 
                    use_llm_fallback=not llm_fallback_used
                )
                # If LLM fallback was used and returned events, mark it
                if page_events and any(e.get('llm_extracted') for e in page_events):
                    llm_fallback_used = True
                logger.info(f"      Found {len(page_events)} events on this page")
                events.extend(page_events)
            
            # Also scrape the main page (only use LLM if not already used)
            logger.info(f"   Scraping main page: {venue_url}")
            main_events = self._scrape_event_page(
                venue_url, venue_name, event_type, time_range,
                use_llm_fallback=not llm_fallback_used
            )
            if main_events and any(e.get('llm_extracted') for e in main_events):
                llm_fallback_used = True
            logger.info(f"      Found {len(main_events)} events on main page")
            events.extend(main_events)
            
            logger.info(f"   Total events before deduplication: {len(events)}")
            
            # Deduplicate
            events = self._deduplicate_events(events)
            
            logger.info(f"✅ Generic scraper: Found {len(events)} unique events")
            if events:
                logger.info(f"   Event titles: {[e.get('title', 'N/A')[:50] for e in events[:5]]}")
            return events
            
        except Exception as e:
            logger.error(f"❌ Error in generic scraper for {venue_url}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _discover_event_pages(self, base_url: str) -> List[str]:
        """Discover event listing pages from the main page"""
        event_pages = []
        seen_urls = set()
        
        try:
            # First, try common paths directly (many museums use standard paths)
            common_paths = [
                '/exhibitions', '/exhibition', '/exhibitions/current', '/exhibitions/on-view',
                '/events', '/event', '/calendar', '/programs', '/program',
                '/whats-on', '/whats-on/current', '/whats-on/exhibitions',
                '/visit/exhibitions', '/see/exhibitions', '/explore/exhibitions',
                '/collection/exhibitions', '/art/exhibitions',
                '/current-exhibitions', '/upcoming-exhibitions', '/on-view',
                '/gallery', '/galleries', '/shows', '/shows/current'
            ]
            
            parsed_base = urlparse(base_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            
            # Try common paths first (fast and often works)
            for path in common_paths:
                test_url = base_domain + path
                if test_url not in seen_urls:
                    seen_urls.add(test_url)
                    event_pages.append(test_url)
            
            # Then fetch the main page and discover links
            response = self._fetch_with_retry(base_url, base_url=base_url)
            if not response:
                logger.info(f"📄 Discovered {len(event_pages)} potential event pages (from common paths)")
                return event_pages[:10]  # Return common paths even if main page fails
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Museum-specific event page keywords (prioritized)
            museum_keywords = [
                'exhibitions', 'exhibition', 'on-view', 'current-exhibitions',
                'upcoming-exhibitions', 'past-exhibitions', 'gallery',
                'programs', 'program', 'events', 'event', 'calendar',
                'talks', 'lectures', 'gallery-talks', 'curator-talks',
                'tours', 'guided-tours', 'workshops', 'classes',
                'whats-on', 'what\'s-on', 'whats-on', 'visit', 'see',
                'schedule', 'upcoming', 'current', 'featured', 'shows'
            ]
            
            # General event keywords (fallback)
            event_keywords = museum_keywords + [
                'activity', 'activities', 'happening', 'special-events'
            ]
            
            # Also check navigation menus and footer links
            nav_links = soup.find_all(['nav', 'header', 'footer'])
            all_links = soup.find_all('a', href=True)
            
            # Add nav/header/footer links first (they're more likely to be event pages)
            for nav in nav_links:
                for link in nav.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()
                    
                    if any(keyword in href.lower() or keyword in text for keyword in event_keywords):
                        full_url = urljoin(base_url, href)
                        # Clean up URL (remove fragments, query params that are just tracking)
                        parsed = urlparse(full_url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        if clean_url not in seen_urls and clean_url != base_url:
                            seen_urls.add(clean_url)
                            event_pages.append(clean_url)
            
            # Then check all other links
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                if any(keyword in href.lower() or keyword in text for keyword in event_keywords):
                    full_url = urljoin(base_url, href)
                    parsed = urlparse(full_url)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if clean_url not in seen_urls and clean_url != base_url:
                        seen_urls.add(clean_url)
                        event_pages.append(clean_url)
            
            # Try to find sitemap and extract exhibition/event URLs
            try:
                sitemap_urls = [
                    urljoin(base_url, '/sitemap.xml'),
                    urljoin(base_url, '/sitemap_index.xml'),
                    urljoin(base_url, '/sitemap-exhibitions.xml'),
                    urljoin(base_url, '/sitemap-events.xml')
                ]
                for sitemap_url in sitemap_urls:
                    try:
                        sitemap_response = self._fetch_with_retry(sitemap_url, base_url=base_url, timeout=5)
                        if sitemap_response and sitemap_response.status_code == 200:
                            sitemap_soup = BeautifulSoup(sitemap_response.content, 'xml')
                            # Find URLs in sitemap
                            for url_tag in sitemap_soup.find_all('url'):
                                loc = url_tag.find('loc')
                                if loc:
                                    url_text = loc.get_text()
                                    if any(keyword in url_text.lower() for keyword in ['exhibition', 'event', 'program', 'show']):
                                        parsed = urlparse(url_text)
                                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                                        if clean_url not in seen_urls and clean_url != base_url:
                                            seen_urls.add(clean_url)
                                            event_pages.append(clean_url)
                            logger.info(f"   Found {len([e for e in event_pages if sitemap_url in str(e)])} URLs from sitemap")
                            break  # Found a sitemap, no need to try others
                    except:
                        continue
            except Exception as sitemap_error:
                logger.debug(f"Error checking sitemap: {sitemap_error}")
            
            logger.info(f"📄 Discovered {len(event_pages)} potential event pages")
            
        except Exception as e:
            logger.debug(f"Error discovering event pages: {e}")
        
        return event_pages[:10]  # Increased limit to 10 pages
    
    def _is_javascript_rendered(self, soup: BeautifulSoup) -> bool:
        """Detect if a page is JavaScript-rendered (SPA) with minimal HTML content"""
        try:
            # Check for very few links (JavaScript-rendered pages often have minimal HTML)
            all_links = soup.find_all('a', href=True)
            page_text = soup.get_text()
            text_length = len(page_text.strip())
            
            # If page has very few links (< 5) and very little text (< 500 chars), likely JS-rendered
            if len(all_links) < 5 and text_length < 500:
                logger.info(f"⚠️  Detected JavaScript-rendered page: {len(all_links)} links, {text_length} chars of text")
                return True
            
            # Also check if page has common SPA indicators
            scripts = soup.find_all('script')
            has_react = any('react' in str(script).lower() or 'react-dom' in str(script).lower() for script in scripts)
            has_vue = any('vue' in str(script).lower() for script in scripts)
            has_angular = any('angular' in str(script).lower() for script in scripts)
            has_nextjs = any('__next' in str(script).lower() or 'next.js' in str(script).lower() for script in scripts)
            
            if (has_react or has_vue or has_angular or has_nextjs) and len(all_links) < 10:
                logger.info(f"⚠️  Detected SPA framework (React/Vue/Angular/Next.js) with minimal links")
                return True
            
            return False
        except Exception as e:
            logger.debug(f"Error checking if page is JS-rendered: {e}")
            return False
    
    def _use_llm_fallback_for_venue(self, venue_url: str, venue_name: str = None, 
                                    event_type: str = None) -> List[Dict]:
        """Use LLM fallback to extract events when web scraping fails"""
        events = []
        
        try:
            logger.info(f"🤖 Using LLM fallback for {venue_name or venue_url}")
            
            from scripts.enhanced_llm_fallback import EnhancedLLMFallback
            llm = EnhancedLLMFallback(silent=True)
            
            prompt = f"""I need to find current and upcoming exhibitions/events at {venue_name or 'this museum'} (website: {venue_url}).

The website appears to be JavaScript-rendered, so I cannot scrape it directly. Based on your knowledge, can you help me find:

1. Current and upcoming exhibitions with their dates
2. Any special events or programs

Please provide a JSON array of events with this structure:
[
    {{
        "title": "exhibition or event name",
        "description": "brief description",
        "start_date": "YYYY-MM-DD or null",
        "end_date": "YYYY-MM-DD or null",
        "event_type": "exhibition or event",
        "url": "{venue_url}/exhibitions/... or similar"
    }}
]

Important:
- Return ONLY valid JSON array, no other text
- Include only current or upcoming events (not past)
- Use null for missing dates
- Be as accurate as possible based on your knowledge"""

            response = llm.query_with_fallback(prompt)
            
            if response and response.get('success') and response.get('content'):
                content = response['content']
                # Try to extract JSON from response
                import json
                import re
                
                # Look for JSON array in the response
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        llm_events = json.loads(json_match.group())
                        for event_data in llm_events:
                            event = {
                                'title': event_data.get('title', ''),
                                'description': event_data.get('description', ''),
                                'start_date': event_data.get('start_date'),
                                'end_date': event_data.get('end_date'),
                                'event_type': event_data.get('event_type', event_type or 'exhibition'),
                                'url': event_data.get('url', venue_url),
                                'venue_name': venue_name,
                                'llm_extracted': True,
                                'confidence': 'medium'
                            }
                            if event['title']:
                                events.append(event)
                        logger.info(f"✅ LLM fallback extracted {len(events)} events")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse LLM JSON response: {e}")
                else:
                    logger.warning("LLM response did not contain valid JSON array")
            else:
                logger.warning("LLM fallback did not return valid response")
                
        except Exception as e:
            logger.debug(f"Error in LLM fallback: {e}")
        
        return events
    
    def _scrape_event_page(self, url: str, venue_name: str = None, 
                          event_type: str = None, time_range: str = 'this_month',
                          use_llm_fallback: bool = True) -> List[Dict]:
        """Scrape events from a single page
        
        Args:
            url: Page URL to scrape
            venue_name: Optional venue name
            event_type: Optional event type filter
            time_range: Time range filter
            use_llm_fallback: Whether to use LLM fallback if page is JS-rendered (default: True)
        """
        events = []
        
        try:
            # Use fetch_with_retry which handles cloudscraper automatically
            base_url = urlparse(url).scheme + '://' + urlparse(url).netloc
            response = self._fetch_with_retry(url, base_url=base_url)
            
            if not response:
                return events
            
            html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check if page is JavaScript-rendered
            if self._is_javascript_rendered(soup) and use_llm_fallback:
                logger.info(f"⚠️  Page appears to be JavaScript-rendered, trying LLM fallback...")
                # Try LLM fallback for the main venue URL
                llm_events = self._use_llm_fallback_for_venue(base_url, venue_name, event_type)
                if llm_events:
                    return llm_events
                # Continue with normal extraction as fallback
            
            # Museum-specific: Check for exhibition listing pages (highest priority)
            url_lower = url.lower()
            is_exhibition_page = any(keyword in url_lower for keyword in [
                '/exhibitions', '/exhibition', '/on-view', '/current-exhibitions',
                '/upcoming-exhibitions', '/gallery', '/show', '/shows'
            ])
            
            if is_exhibition_page or event_type == 'exhibition':
                exhibition_events = self._extract_exhibitions_from_listing_page(soup, url, venue_name, time_range)
                if exhibition_events:
                    logger.info(f"✅ Found {len(exhibition_events)} exhibitions from listing page")
                    events.extend(exhibition_events)
            
            # Museum-specific: Check for program/event listing pages
            is_program_page = any(keyword in url_lower for keyword in [
                '/programs', '/program', '/events', '/calendar', '/talks',
                '/lectures', '/workshops', '/tours', '/whats-on'
            ])
            
            if is_program_page and not is_exhibition_page:
                # Extract programs/events with enhanced museum patterns
                program_events = self._extract_museum_programs(soup, url, venue_name, event_type, time_range)
                if program_events:
                    logger.info(f"✅ Found {len(program_events)} museum programs from listing page")
                    events.extend(program_events)
            
            # Try JSON-LD first (structured data)
            json_ld_events = self._extract_json_ld_events(soup, url)
            events.extend(json_ld_events)
            
            # Extract events from HTML
            html_events = self._extract_events_from_html(soup, url, venue_name, event_type, time_range)
            # Filter out invalid events before adding
            valid_html_events = [e for e in html_events if self._is_valid_generic_event(e)]
            events.extend(valid_html_events)
            
        except Exception as e:
            logger.debug(f"Error scraping page {url}: {e}")
        
        return events
    
    def _extract_json_ld_events(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract events from JSON-LD structured data"""
        events = []
        
        try:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    script_content = script.string if script.string else script.get_text()
                    data = json.loads(script_content)
                    
                    # Handle both single objects and arrays
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        if item.get('@type') in ['Event', 'ExhibitionEvent', 'TheaterEvent']:
                            event = self._parse_json_ld_event(item, base_url)
                            if event:
                                events.append(event)
                                
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Error parsing JSON-LD: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extracting JSON-LD: {e}")
        
        return events
    
    def _parse_json_ld_event(self, data: Dict, base_url: str) -> Optional[Dict]:
        """Parse a single JSON-LD event"""
        try:
            title = data.get('name', '')
            description = data.get('description', '')
            
            # Extract dates
            start_date = None
            end_date = None
            start_time = None
            end_time = None
            
            if 'startDate' in data:
                start_datetime = self._parse_iso_datetime(data['startDate'])
                if start_datetime:
                    start_date = start_datetime.date()
                    start_time = start_datetime.time()
            
            if 'endDate' in data:
                end_datetime = self._parse_iso_datetime(data['endDate'])
                if end_datetime:
                    end_date = end_datetime.date()
                    end_time = end_datetime.time()
            
            # Extract location
            location = None
            if 'location' in data:
                loc = data['location']
                if isinstance(loc, dict):
                    location = loc.get('name', '')
                    if not location and 'address' in loc:
                        addr = loc['address']
                        if isinstance(addr, dict):
                            location = addr.get('streetAddress', '')
                elif isinstance(loc, str):
                    location = loc
            
            # Extract image
            image_url = None
            if 'image' in data:
                img = data['image']
                if isinstance(img, str):
                    image_url = img
                elif isinstance(img, list) and len(img) > 0:
                    image_url = img[0] if isinstance(img[0], str) else img[0].get('url', '')
                elif isinstance(img, dict):
                    image_url = img.get('url', '')
            
            # Extract URL
            url = data.get('url', base_url)
            if url and not url.startswith('http'):
                url = urljoin(base_url, url)
            
            # Determine event type
            event_type = self._determine_event_type(title, description, data.get('@type', ''))
            
            return {
                'title': title,
                'description': description,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location,
                'url': url,
                'image_url': image_url,
                'event_type': event_type
            }
            
        except Exception as e:
            logger.debug(f"Error parsing JSON-LD event: {e}")
            return None
    
    def _should_skip_element(self, element) -> bool:
        """Check if element should be skipped (navigation, calendar UI, etc.)"""
        # Skip elements inside navigation menus
        nav_parents = element.find_parents(['nav', 'header', 'footer', '.nav', '.navigation', '.menu'])
        if nav_parents:
            return True
        
        # Skip elements inside calendar UI (day headers, navigation)
        calendar_parents = element.find_parents(['.calendar', '.datepicker', '.event-calendar', 
                                                  '.tribe-events', '.calendar-nav', '.calendar-header'])
        if calendar_parents:
            # But allow if it's inside an event item within calendar
            event_item_parents = element.find_parents(['.event-item', '.event-card', '.event', '[class*="event"]'])
            if not event_item_parents:
                return True
        
        # Skip script and style elements
        if element.name in ['script', 'style', 'noscript']:
            return True
        
        # Skip very small text elements (likely navigation labels)
        text = element.get_text(strip=True)
        if text and len(text) <= 2:
            return True
        
        return False
    
    def _extract_events_from_html(self, soup: BeautifulSoup, base_url: str, 
                                  venue_name: str = None, event_type: str = None, 
                                  time_range: str = 'this_month') -> List[Dict]:
        """Extract events from HTML using museum-specific selectors first, then fallback"""
        events = []
        seen_elements = set()  # Track elements we've already processed

        # Prioritize museum-specific selectors
        selectors_to_try = self.museum_event_selectors if hasattr(self, 'museum_event_selectors') else self.event_selectors

        # Try each selector
        for selector in selectors_to_try:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.debug(f"Found {len(elements)} elements with selector: {selector}")

                    for element in elements:
                        # Skip if we've already processed this element
                        element_id = id(element)
                        if element_id in seen_elements:
                            continue
                        seen_elements.add(element_id)
                        
                        # Skip navigation and calendar UI elements
                        if self._should_skip_element(element):
                            continue

                        event = self._parse_event_element(element, base_url, venue_name, event_type, time_range)
                        if event:
                            # Enhance event type detection for museums
                            if not event.get('event_type'):
                                event['event_type'] = self._detect_museum_event_type(
                                    event.get('title', ''),
                                    event.get('description', ''),
                                    element
                                )
                            events.append(event)

            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue

        return events
    
    def _is_valid_event_title(self, title: str) -> bool:
        """Validate that a title is actually an event title, not navigation/page element"""
        if not title or len(title) < 3:
            return False
        
        title_lower = title.lower().strip()
        title_original = title.strip()
        
        # Filter out navigation and page elements
        invalid_patterns = [
            # Calendar navigation - day abbreviations (with or without double letters)
            r'^(s?sun|m?mon|t?tue|w?wed|t?thu|f?fri|s?sat)$',
            # Calendar event counts
            r'^\d+\s+events?,\s*\d+$',  # "0 events,3", "1 event,5"
            r'^\d+\s+event,\d+$',  # "1 event,5"
            r'^\d+\s+event,\s*\d+$',  # "1 event, 5"
            # Navigation elements
            r'^events?\s+search',  # "Events Search"
            r'^event\s+views?\s+navigation',  # "Event Views Navigation"
            r'^calendar\s+of\s+events?$',  # "Calendar of Events"
            r'^view\s+calendar$',
            r'^view\s+all\s+events?$',
            r'^upcoming\s+events?$',
            r'^past\s+events?$',
            r'^all\s+events?$',
            # Generic page elements
            r'^(details?|organizer|venue|location|date|time)$',
            r'^(filter|search|browse|explore)$',
            r'^(loading|loading\s+view)$',
            r'^(month|list|week|photo|day)$',
            r'^(select\s+date|this\s+month)$',
            # JavaScript/function code
            r'^\s*\(?\s*function\s*\(',
            r'^\s*var\s+\w+\s*=',
            r'^\s*if\s*\(',
            # Very short or generic
            r'^[a-z]$',  # Single letter
            r'^\d+$',  # Just numbers
            r'^[a-z]\d+$',  # "M1", "T2", etc.
            # Date-only patterns without event name
            r'^(december|january|february|march|april|may|june|july|august|september|october|november)\s+\d+\s*@?\s*\d+:\d+',  # "December 5 @ 10:00"
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, title_lower, re.IGNORECASE):
                return False
        
        # Filter out titles that are clearly not events (exact matches)
        invalid_keywords = [
            'details', 'organizer', 'venue', 'location', 'date:', 'time:',
            'filter', 'search', 'browse', 'explore', 'loading', 'select',
            'month', 'list', 'week', 'photo', 'day', 'sun', 'mon', 'tue',
            'wed', 'thu', 'fri', 'sat', 'view calendar', 'view all',
            'upcoming events', 'past events', 'all events', 'all past events', 'all past events→', 'calendar of events',
            'ssun', 'mmon', 'ttue', 'wwed', 'tthu', 'ffri', 'ssat',
            'events search and views navigation', 'event views navigation',
            'upcoming events', 'past events', 'all events'
        ]
        
        if title_lower in invalid_keywords:
            return False
        
        # Filter out titles that end with navigation symbols (arrows, etc.)
        if title.endswith('→') or title.endswith('←') or title.endswith('›') or title.endswith('»'):
            return False
        
        # Filter out titles that start with invalid keywords (partial match)
        for keyword in ['details', 'organizer', 'venue', 'filter', 'search', 'loading']:
            if title_lower.startswith(keyword + ' ') or title_lower == keyword:
                return False
        
        # Filter out titles that are just dates/times without event info
        # Pattern: "Month Day @ Time" or "Month Day Time"
        date_time_pattern = r'^(december|january|february|march|april|may|june|july|august|september|october|november)\s+\d+(\s*@\s*|\s+)\d+:\d+'
        if re.match(date_time_pattern, title_lower):
            # This is just a date/time string, not an event title
            return False
        
        # Filter out very short titles that are likely navigation
        if len(title_original) <= 5 and title_lower in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']:
            return False
        
        return True
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize title text to fix common issues"""
        if not title:
            return title
        
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
        
        # Remove "Through" dates from title (e.g., "TitleThrough Jan 25, 2026")
        # Pattern: "Through Month Day, Year" or "through Month Day, Year"
        through_patterns = [
            r'[Tt]hrough\s+[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}\s*$',  # "Through January 25, 2026"
            r'[Tt]hrough\s+[A-Z][a-z]{2,3}\.?\s+\d{1,2},?\s+\d{4}\s*$',  # "Through Jan 25, 2026"
        ]
        for pattern in through_patterns:
            title = re.sub(pattern, '', title)
        
        # Remove date ranges from title (e.g., "Title Month Day, Year – Month Day, Year")
        date_range_pattern = r'[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}\s*[–—\-]\s*[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}\s*$'
        title = re.sub(date_range_pattern, '', title, flags=re.IGNORECASE)
        
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
    
    def _parse_event_element(self, element, base_url: str, venue_name: str = None,
                            event_type: str = None, time_range: str = 'this_month') -> Optional[Dict]:
        """Parse a single event element from HTML"""
        try:
            # Extract title
            title = self._extract_text(element, [
                'h1', 'h2', 'h3', 'h4', '.title', '.event-title', '.name',
                '[itemprop="name"]', 'meta[property="og:title"]'
            ])
            
            if not title or len(title) < 3:
                return None
            
            # Extract dates from title BEFORE cleaning (in case dates are concatenated)
            # Pattern: "TitleThrough Month Day, Year" or "Title Through Month Day, Year"
            extracted_start_date = None
            extracted_end_date = None
            
            # Look for "Through" or "through" followed by date (common in museum exhibitions)
            through_pattern = r'[Tt]hrough\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'
            through_match = re.search(through_pattern, title)
            if through_match:
                end_date_str = through_match.group(1)
                extracted_end_date = self._parse_single_date_string(end_date_str)
                # For exhibitions, if we only have end date, set start to today (ongoing exhibition)
                if extracted_end_date:
                    from datetime import date
                    extracted_start_date = date.today()
                    logger.debug(f"   📅 Extracted end date from title: {extracted_end_date}, set start_date to {extracted_start_date}")
            
            # Also look for date ranges in title: "Title Month Day, Year – Month Day, Year"
            if not extracted_start_date:
                title_date_range = self._parse_date_range_string(title)
                if title_date_range:
                    extracted_start_date = title_date_range.get('start_date')
                    extracted_end_date = title_date_range.get('end_date')
                    logger.debug(f"   📅 Extracted date range from title: {extracted_start_date} to {extracted_end_date}")
            
            # Validate title is actually an event, not navigation/page element
            if not self._is_valid_event_title(title):
                return None
            
            # Clean title to remove dates, trailing commas, etc.
            title = self._clean_title(title)
            
            # Extract description
            description = self._extract_text(element, [
                '.description', '.summary', '.content', 'p', '.event-description',
                '[itemprop="description"]', 'meta[property="og:description"]'
            ])
            
            # Extract date/time
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when', '.schedule',
                '[itemprop="startDate"]', '[itemprop="endDate"]', 'time[datetime]'
            ])
            
            start_date, end_date, start_time, end_time = self._parse_dates_and_times(
                date_text, element, base_url
            )
            
            # Use dates extracted from title if we don't have them from date_text
            if not start_date and extracted_start_date:
                start_date = extracted_start_date
            if not end_date and extracted_end_date:
                end_date = extracted_end_date
            
            # Extract location
            location = self._extract_text(element, [
                '.location', '.venue', '.where', '.address', '.meeting-point',
                '[itemprop="location"]', '[itemprop="address"]'
            ])
            
            # Extract URL
            url = self._extract_url(element, base_url)
            
            # Extract image from listing page - search thoroughly
            image_url = None
            
            # Strategy 1: Look in the element itself
            image_url = self._extract_image(element, base_url)
            
            # Strategy 2: Look in parent container
            if not image_url and element.parent:
                image_url = self._extract_image(element.parent, base_url)
            
            # Strategy 3: Look at siblings (common pattern: image and event info are siblings)
            if not image_url and element.parent:
                # Check previous sibling
                prev_sibling = element.previous_sibling
                while prev_sibling and not image_url:
                    if hasattr(prev_sibling, 'find'):
                        image_url = self._extract_image(prev_sibling, base_url)
                    prev_sibling = prev_sibling.previous_sibling if hasattr(prev_sibling, 'previous_sibling') else None
                
                # Check next sibling
                if not image_url:
                    next_sibling = element.next_sibling
                    while next_sibling and not image_url:
                        if hasattr(next_sibling, 'find'):
                            image_url = self._extract_image(next_sibling, base_url)
                        next_sibling = next_sibling.next_sibling if hasattr(next_sibling, 'next_sibling') else None
            
            # IMPORTANT: Fetch individual event page for better data extraction (times, descriptions, etc.)
            # Note: We already extracted image from listing page above, but will try event page if not found
            # This is similar to what we do in the OCMA scraper
            if url and url != base_url and url.startswith('http'):
                try:
                    logger.debug(f"   🔍 Fetching individual event page for better extraction: {url}")
                    # Use fetch_with_retry for better bot protection handling
                    event_response = self._fetch_with_retry(url, base_url=base_url)
                    if event_response and event_response.status_code == 200:
                        event_soup = BeautifulSoup(event_response.content, 'html.parser')
                        event_main_content = event_soup.find('article') or event_soup.find('main') or event_soup
                        
                        # First, try to extract date/time from h2 tags (common pattern, e.g., OCMA)
                        # Look for patterns like "December 5, 2025, 5:00–6:00 PM" in h2 tags
                        h2_tags = event_soup.find_all('h2') if event_soup else []
                        for h2 in h2_tags:
                            h2_text = h2.get_text(strip=True)
                            # Check for combined date+time pattern
                            combined_pattern = r'(\w+)\s+(\d{1,2}),?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?'
                            match = re.search(combined_pattern, h2_text, re.IGNORECASE)
                            if match:
                                groups = match.groups()
                                try:
                                    # Parse date
                                    month = self._month_name_to_num(groups[0])
                                    day = int(groups[1])
                                    year = int(groups[2])
                                    start_date = date(year, month, day)
                                    
                                    # Parse start time
                                    start_hour = int(groups[3])
                                    start_min = int(groups[4])
                                    start_ampm = groups[5].lower()
                                    if start_ampm == 'p' and start_hour != 12:
                                        start_hour += 12
                                    elif start_ampm == 'a' and start_hour == 12:
                                        start_hour = 0
                                    start_time = time(start_hour, start_min)
                                    
                                    # Parse end time
                                    if len(groups) >= 9:
                                        end_hour = int(groups[6])
                                        end_min = int(groups[7])
                                        end_ampm = groups[8].lower()
                                        if end_ampm == 'p' and end_hour != 12:
                                            end_hour += 12
                                        elif end_ampm == 'a' and end_hour == 12:
                                            end_hour = 0
                                        end_time = time(end_hour, end_min)
                                    
                                    logger.info(f"   ✅ Extracted date+time from h2 tag: {start_date} {start_time}-{end_time}")
                                    break
                                except (ValueError, IndexError) as e:
                                    logger.debug(f"Error parsing h2 date+time: {e}")
                                    continue
                        
                        # Extract description from event page (more complete)
                        if event_main_content:
                            event_desc_elem = event_main_content.find('p')
                            if event_desc_elem:
                                event_description = event_desc_elem.get_text(strip=True)
                                # Get all paragraphs for full description
                                all_paragraphs = event_main_content.find_all('p')
                                if len(all_paragraphs) > 1:
                                    event_description = ' '.join([p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True)])
                                
                                # Use event page description if it's longer/more complete
                                if event_description and (not description or len(event_description) > len(description)):
                                    description = event_description
                                    logger.debug(f"   📝 Updated description from event page (length: {len(description)} chars)")
                            
                            # Extract date/time from event page (more accurate)
                            # Use the full text from the event page for better extraction
                            event_text = event_main_content.get_text()
                            
                            # Re-parse dates and times from the full event page text
                            # This will use the combined patterns to extract "December 5, 2025, 5:00–6:00 PM"
                            if event_text:
                                # Create a dummy element to pass to _parse_dates_and_times
                                from bs4 import Tag
                                dummy_elem = Tag(name='div')
                                dummy_elem.string = event_text
                                
                                # Re-parse with full event page text
                                parsed_start_date, parsed_end_date, parsed_start_time, parsed_end_time = self._parse_dates_and_times(
                                    event_text, dummy_elem, url
                                )
                                
                                # Update if we got better data from event page
                                if parsed_start_date and not start_date:
                                    start_date = parsed_start_date
                                    logger.debug(f"   📅 Extracted date from event page: {start_date}")
                                if parsed_end_date and not end_date:
                                    end_date = parsed_end_date
                                if parsed_start_time and not start_time:
                                    start_time = parsed_start_time
                                    logger.debug(f"   ⏰ Extracted start time from event page: {start_time}")
                                if parsed_end_time and not end_time:
                                    end_time = parsed_end_time
                                    logger.debug(f"   ⏰ Extracted end time from event page: {end_time}")
                        
                        # Extract image from event page if not found (use enhanced extraction)
                        if not image_url:
                            # Use the enhanced image extraction method on the event page
                            image_url = self._extract_image(event_soup, url)
                            if image_url:
                                logger.debug(f"   ✅ Found image from event page: {image_url[:80]}")
                except Exception as e:
                    logger.debug(f"Error fetching individual event page {url}: {e}")
            
            # Determine event type
            if not event_type:
                event_type = self._determine_event_type(title, description)
            
            # Filter by time range (only if we have a date)
            # For events without dates (ongoing exhibitions), include them
            if start_date:
                if not self._is_in_time_range(start_date, time_range):
                    logger.debug(f"   ⏭️  Event '{title}' filtered out (date {start_date} not in {time_range})")
                    return None
                else:
                    logger.debug(f"   ✅ Event '{title}' passed time_range filter (date: {start_date})")
            else:
                # No date - include it (might be ongoing exhibition or event without specific date)
                logger.debug(f"   ⚠️  Event '{title}' has no date, including anyway (might be ongoing)")
            
            return {
                'title': title.strip(),
                'description': description.strip() if description else '',
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location.strip() if location else None,
                'url': url,
                'image_url': image_url,
                'event_type': event_type
            }
            
        except Exception as e:
            logger.debug(f"Error parsing event element: {e}")
            return None
    
    def _extract_text(self, element, selectors: List[str]) -> Optional[str]:
        """Extract text using multiple selector strategies (enhanced from specialized scrapers)"""
        # Try CSS selectors first
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    text = found.get_text(strip=True)
                    if text and len(text) > 3:  # Minimum length check
                        return text
            except:
                continue

        # Try meta tags
        if 'meta[' in str(selectors):
            for selector in selectors:
                if 'meta[' in selector:
                    try:
                        meta = element.select_one(selector)
                        if meta:
                            content = meta.get('content', '')
                            if content and len(content) > 3:
                                return content
                    except:
                        continue

        # Enhanced: For descriptions, try multiple strategies (learned from specialized scrapers)
        if any('description' in s.lower() or 'summary' in s.lower() or 'content' in s.lower() for s in selectors):
            # Strategy 1: Look for description/summary/intro classes in parent containers
            parent = element
            for _ in range(3):  # Check up to 3 levels up
                if parent:
                    desc_elem = parent.find(['div', 'p', 'section'], 
                                          class_=re.compile(r'description|summary|intro|content', re.I))
                    if desc_elem:
                        text = desc_elem.get_text(strip=True)
                        if text and len(text) > 50:  # Only use substantial descriptions
                            return text
                    parent = parent.parent if hasattr(parent, 'parent') else None
            
            # Strategy 2: Get first substantial paragraph
            first_p = element.find('p')
            if first_p:
                text = first_p.get_text(strip=True)
                if text and len(text) > 50:
                    return text

        # Fallback: get text from element itself
        text = element.get_text(strip=True)
        if text and len(text) > 3:
            return text

        return None
    
    def _extract_url(self, element, base_url: str) -> Optional[str]:
        """Extract event URL"""
        # Try link
        link = element.find('a', href=True)
        if link:
            return urljoin(base_url, link['href'])
        
        # Try data attributes
        for attr in ['data-url', 'data-href', 'data-link']:
            if element.get(attr):
                return urljoin(base_url, element[attr])
        
        return base_url
    
    def _extract_image(self, element, base_url: str) -> Optional[str]:
        """Extract event image URL using multiple strategies (learned from specialized scrapers)"""
        image_url = None
        
        # Strategy 1: Look for hero/feature/main images by class (highest priority)
        img_elem = element.find('img', class_=re.compile(r'hero|feature|main|exhibition|header|event', re.I))
        if img_elem:
            img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src') or img_elem.get('data-original')
            if img_src:
                image_url = urljoin(base_url, img_src)
                return image_url
        
        # Strategy 2: Look for images with keywords in URL
        if not image_url:
            all_imgs = element.find_all('img')
            for img in all_imgs:
                img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                if img_src:
                    src_lower = img_src.lower()
                    # Skip small icons/logos/decoration (learned from specialized scrapers)
                    skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'twitter', 'facebook', 
                                   'instagram', 'svg', 'site-header', 'nav-background', 'hero-background']
                    if any(pattern in src_lower for pattern in skip_patterns):
                        continue
                    
                    # Prefer images with certain keywords in path
                    if any(keyword in src_lower for keyword in ['exhibition', 'hero', 'feature', 'header', 'banner', 'event']):
                        image_url = urljoin(base_url, img_src)
                        break
        
        # Strategy 3: Find first substantial image (jpg/png/webp) not in nav/footer
        if not image_url:
            all_imgs = element.find_all('img')
            for img in all_imgs:
                img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                if img_src:
                    src_lower = img_src.lower()
                    # Skip icons/logos
                    skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg']
                    if any(pattern in src_lower for pattern in skip_patterns):
                        continue
                    
                    # Check if it's a real image file
                    if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        # Check if it's not in navigation/footer
                        parent = img.parent
                        skip_containers = ['nav', 'header', 'footer', 'menu']
                        parent_tag = parent.name if parent else ''
                        parent_classes = ' '.join(parent.get('class', [])) if parent and hasattr(parent, 'get') else ''
                        
                        if parent_tag not in skip_containers and not any(skip in parent_classes.lower() for skip in skip_containers):
                            image_url = urljoin(base_url, img_src)
                            break
        
        # Strategy 4: Try meta tags (og:image)
        if not image_url:
            og_image = element.select_one('meta[property="og:image"]')
            if og_image:
                image_url = og_image.get('content', '')
                if image_url and not image_url.startswith('http'):
                    image_url = urljoin(base_url, image_url)
        
        return image_url
    
    def _parse_dates_and_times(self, date_text: str, element, base_url: str) -> Tuple:
        """Parse dates and times from text and HTML attributes"""
        start_date = None
        end_date = None
        start_time = None
        end_time = None
        today = date.today()
        
        # Get full text from element if date_text is limited
        full_text = element.get_text() if element else date_text or ''
        search_text = full_text if len(full_text) > len(date_text or '') else (date_text or '')
        
        # Try time[datetime] attribute first
        time_elem = element.find('time', datetime=True) if element else None
        if time_elem:
            datetime_str = time_elem.get('datetime', '')
            parsed = self._parse_iso_datetime(datetime_str)
            if parsed:
                start_date = parsed.date()
                start_time = parsed.time()
                # Try to get end time from text content
                time_text = time_elem.get_text(strip=True)
                if time_text:
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', time_text, re.IGNORECASE)
                    if time_match:
                        _, parsed_end = self._parse_time_match(time_match)
                        if parsed_end:
                            end_time = parsed_end
        
        # Parse combined date+time patterns first (e.g., "December 5, 2025, 5:00–6:00 PM")
        # These patterns extract both date and time together
        combined_patterns = [
            # "December 5, 2025, 5:00–6:00 PM" (comma-separated)
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # "December 5, 2025 | 5:00–6:00 PM" (pipe-separated)
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
        ]
        
        for pattern in combined_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    # Parse date
                    month = self._month_name_to_num(groups[0])
                    day = int(groups[1])
                    year = int(groups[2])
                    start_date = date(year, month, day)
                    
                    # Parse start time
                    start_hour = int(groups[3])
                    start_min = int(groups[4])
                    start_ampm = groups[5].lower()
                    if start_ampm == 'p' and start_hour != 12:
                        start_hour += 12
                    elif start_ampm == 'a' and start_hour == 12:
                        start_hour = 0
                    start_time = time(start_hour, start_min)
                    
                    # Parse end time
                    if len(groups) >= 9:
                        end_hour = int(groups[6])
                        end_min = int(groups[7])
                        end_ampm = groups[8].lower()
                        if end_ampm == 'p' and end_hour != 12:
                            end_hour += 12
                        elif end_ampm == 'a' and end_hour == 12:
                            end_hour = 0
                        end_time = time(end_hour, end_min)
                    
                    logger.debug(f"   ✅ Extracted date+time from combined pattern: {start_date} {start_time}-{end_time}")
                    break
                except (ValueError, IndexError) as e:
                    logger.debug(f"Error parsing combined date+time pattern: {e}")
                    continue
        
        # Parse from text if we don't have dates yet
        # Enhanced: Try date range parsing first (learned from specialized scrapers)
        if date_text and not start_date:
            # Try to parse date ranges with multiple separators (like specialized scrapers)
            date_range = self._parse_date_range_string(search_text)
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
            else:
                # Fallback to pattern matching
                for pattern in self.date_patterns:
                    match = re.search(pattern, search_text, re.IGNORECASE)
                    if match:
                        parsed_start, parsed_end = self._parse_date_match(match, search_text)
                        if parsed_start:
                            start_date = parsed_start
                            end_date = parsed_end
                            break
        
        # Parse times from text if we don't have them yet
        if search_text and not start_time:
            # Try time patterns
            for pattern in self.time_patterns:
                match = re.search(pattern, search_text, re.IGNORECASE)
                if match:
                    parsed_start, parsed_end = self._parse_time_match(match)
                    if parsed_start:
                        start_time = parsed_start
                        end_time = parsed_end
                        break
        
        # If we have a start time but no end time, assume 1-hour duration
        if start_time and not end_time:
            start_datetime = datetime.combine(today, start_time)
            end_datetime = start_datetime + timedelta(hours=1)
            end_time = end_datetime.time()
        
        return start_date, end_date, start_time, end_time
    
    def _parse_iso_datetime(self, iso_string: str) -> Optional[datetime]:
        """Parse ISO 8601 datetime string"""
        try:
            # Remove timezone info for simplicity
            iso_string = re.sub(r'[+-]\d{2}:\d{2}$', '', iso_string)
            iso_string = re.sub(r'Z$', '', iso_string)
            
            # Try different formats
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(iso_string[:len(fmt) + 5], fmt)
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error parsing ISO datetime {iso_string}: {e}")
        
        return None
    
    def _parse_date_match(self, match: re.Match, text: str) -> Tuple[Optional[date], Optional[date]]:
        """Parse date from regex match"""
        try:
            groups = match.groups()
            today = date.today()
            
            # Pattern: "May 23 - August 23, 2026" (year only at end)
            if len(groups) >= 5 and groups[4]:  # Has year at end
                try:
                    month1 = self._month_name_to_num(groups[0])
                    day1 = int(groups[1])
                    month2 = self._month_name_to_num(groups[2])
                    day2 = int(groups[3])
                    year = int(groups[4])
                    
                    start_date = date(year, month1, day1)
                    end_date = date(year, month2, day2)
                    return start_date, end_date
                except:
                    pass
            
            # Pattern: "May 23, 2026 - August 23, 2026" (year after each date)
            if len(groups) >= 6:
                try:
                    month1 = self._month_name_to_num(groups[0])
                    day1 = int(groups[1])
                    year1 = int(groups[2])
                    month2 = self._month_name_to_num(groups[3])
                    day2 = int(groups[4])
                    year2 = int(groups[5])
                    
                    start_date = date(year1, month1, day1)
                    end_date = date(year2, month2, day2)
                    return start_date, end_date
                except:
                    pass
            
            # Pattern: "December 5, 2025" (single date)
            if len(groups) >= 3:
                try:
                    month = self._month_name_to_num(groups[1] if len(groups) > 1 else groups[0])
                    day = int(groups[2] if len(groups) > 2 else groups[1])
                    year = int(groups[3] if len(groups) > 3 else groups[2])
                    
                    start_date = date(year, month, day)
                    return start_date, None
                except:
                    pass
            
            # Pattern: MM/DD/YYYY
            if len(groups) >= 3:
                try:
                    month = int(groups[0])
                    day = int(groups[1])
                    year = int(groups[2])
                    start_date = date(year, month, day)
                    return start_date, None
                except:
                    pass
            
            # Pattern: YYYY-MM-DD
            if len(groups) >= 3:
                try:
                    year = int(groups[0])
                    month = int(groups[1])
                    day = int(groups[2])
                    start_date = date(year, month, day)
                    return start_date, None
                except:
                    pass
            
        except Exception as e:
            logger.debug(f"Error parsing date match: {e}")
        
        return None, None
    
    def _parse_date_range_string(self, date_string: str) -> Optional[Dict[str, date]]:
        """
        Parse date range string like "November 25, 2025–July 12, 2026" (learned from specialized scrapers)
        Returns dict with 'start_date' and 'end_date' or None if parsing fails
        """
        if not date_string:
            return None
        
        # Clean up the date string
        date_string = date_string.strip()
        
        # Handle different separators (learned from specialized scrapers)
        separators = ['–', '-', '—', 'to', 'through']
        for sep in separators:
            if sep in date_string:
                parts = date_string.split(sep, 1)
                if len(parts) == 2:
                    start_str = parts[0].strip()
                    end_str = parts[1].strip()
                    
                    try:
                        start_date = self._parse_single_date_string(start_str)
                        end_date = self._parse_single_date_string(end_str)
                        
                        if start_date and end_date:
                            return {
                                'start_date': start_date,
                                'end_date': end_date
                            }
                    except Exception as e:
                        logger.debug(f"Error parsing date range '{date_string}': {e}")
                        continue
        
        # Try to parse as single date
        single_date = self._parse_single_date_string(date_string)
        if single_date:
            return {
                'start_date': single_date,
                'end_date': single_date
            }
        
        return None
    
    def _parse_single_date_string(self, date_string: str) -> Optional[date]:
        """Parse a single date string in various formats (learned from specialized scrapers)"""
        if not date_string:
            return None
        
        date_string = date_string.strip()
        
        # Try common date formats
        date_formats = [
            '%B %d, %Y',      # November 25, 2025
            '%b %d, %Y',      # Nov 25, 2025
            '%d %B %Y',       # 25 November 2025
            '%d %b %Y',       # 25 Nov 2025
            '%Y-%m-%d',       # 2025-11-25
            '%m/%d/%Y',       # 11/25/2025
            '%d/%m/%Y',       # 25/11/2025
            '%B %Y',          # November 2025
            '%b %Y',          # Nov 2025
            '%Y',             # 2025
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_string, fmt).date()
                return parsed
            except ValueError:
                continue
        
        # Try regex patterns for more flexible parsing
        month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        day_pattern = r'(\d{1,2})'
        year_pattern = r'(\d{4})'
        
        # Pattern: "Month Day, Year"
        pattern1 = rf'{month_pattern}\s+{day_pattern},?\s+{year_pattern}'
        match = re.search(pattern1, date_string, re.IGNORECASE)
        if match:
            try:
                month_str = match.group(1)
                day = int(match.group(2))
                year = int(match.group(3))
                
                month = self._month_name_to_num(month_str)
                if month:
                    return date(year, month, day)
            except (ValueError, IndexError):
                pass
        
        logger.debug(f"Could not parse date: {date_string}")
        return None
    
    def _month_name_to_num(self, month_name: str) -> int:
        """Convert month name to number"""
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        return months.get(month_name.lower(), 1)
    
    def _parse_time_match(self, match: re.Match) -> Tuple[Optional[time], Optional[time]]:
        """Parse time from regex match"""
        try:
            groups = match.groups()
            
            # Pattern: "11:30 am–12:00 pm"
            if len(groups) >= 6:
                start_hour = int(groups[0])
                start_min = int(groups[1])
                start_ampm = groups[2].lower()
                
                if start_ampm == 'p' and start_hour != 12:
                    start_hour += 12
                elif start_ampm == 'a' and start_hour == 12:
                    start_hour = 0
                
                start_time = time(start_hour, start_min)
                
                # End time
                if len(groups) >= 6:
                    end_hour = int(groups[3])
                    end_min = int(groups[4])
                    end_ampm = groups[5].lower()
                    
                    if end_ampm == 'p' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'a' and end_hour == 12:
                        end_hour = 0
                    
                    end_time = time(end_hour, end_min)
                    return start_time, end_time
                
                return start_time, None
            
        except Exception as e:
            logger.debug(f"Error parsing time match: {e}")
        
        return None, None
    
    def _determine_event_type(self, title: str, description: str = '', json_type: str = '') -> str:
        """Determine event type from title, description, and JSON-LD type"""
        content = f"{title} {description}".lower()
        
        if 'exhibition' in content or 'exhibit' in content or 'ExhibitionEvent' in json_type:
            return 'exhibition'
        elif 'tour' in content or 'guided' in content:
            return 'tour'
        elif 'workshop' in content or 'class' in content:
            return 'workshop'
        elif 'talk' in content or 'lecture' in content or 'discussion' in content:
            return 'talk'
        elif 'performance' in content or 'concert' in content or 'show' in content:
            return 'festival'
        elif 'festival' in content:
            return 'festival'
        else:
            return 'event'  # Generic fallback
    
    def _is_in_time_range(self, event_date: date, time_range: str) -> bool:
        """Check if event date is within the specified time range"""
        today = date.today()
        
        if time_range == 'today':
            return event_date == today
        elif time_range == 'this_week':
            week_end = today + timedelta(days=7)
            return today <= event_date <= week_end
        elif time_range == 'this_month':
            month_end = today + timedelta(days=30)
            return today <= event_date <= month_end
        else:
            return True  # No filter
    
    def _is_valid_generic_event(self, event: Dict) -> bool:
        """Additional validation for generic scraper events"""
        title = event.get('title', '')
        
        # Must have a valid title
        if not self._is_valid_event_title(title):
            return False
        
        # Must have at least one of: date, URL (different from base), or meaningful description
        has_date = event.get('start_date') is not None
        url = event.get('url', '')
        # URL is valid if it exists and is not just the base page
        has_url = bool(url and len(url) > 10)  # Basic check that URL is substantial
        description = event.get('description', '')
        has_description = description and len(description.strip()) >= 20
        
        if not (has_date or has_url or has_description):
            return False
        
        # Filter out events with URLs that are clearly not event pages
        if url:
            url_lower = url.lower()
            invalid_url_patterns = [
                'javascript:', 'mailto:', 'tel:',
                '#',  # Anchor links only
            ]
            # Reject if URL matches invalid patterns
            if any(pattern in url_lower for pattern in invalid_url_patterns):
                return False
            
            # Reject calendar listing pages without specific event identifiers
            if '/calendar' in url_lower or '/event/' in url_lower or '/events/' in url_lower:
                # Allow if it has an event ID or slug (e.g., /events/specific-event-name)
                if not re.search(r'/events?/[^/]+$', url_lower) and not re.search(r'event[_-]?id=', url_lower):
                    # Might be a listing page, but allow if it has a date
                    if not has_date:
                        return False
        
        return True
    
    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        """Remove duplicate events based on title, date, and URL"""
        seen = set()
        unique_events = []
        
        for event in events:
            title = event.get('title', '').lower().strip()
            start_date = event.get('start_date')
            url = event.get('url', '')
            
            # Create multiple keys for better deduplication
            # Key 1: title + date (most common)
            key1 = (title, start_date)
            
            # Key 2: URL + date (for events with unique URLs)
            key2 = (url, start_date) if url and url != event.get('source_url', '') else None
            
            # Key 3: title + URL (for recurring events)
            key3 = (title, url) if url and url != event.get('source_url', '') else None
            
            # Check if we've seen any of these keys
            is_duplicate = key1 in seen
            if key2:
                is_duplicate = is_duplicate or key2 in seen
            if key3:
                is_duplicate = is_duplicate or key3 in seen
            
            if not is_duplicate:
                seen.add(key1)
                if key2:
                    seen.add(key2)
                if key3:
                    seen.add(key3)
                unique_events.append(event)
        
        return unique_events
    
    def _extract_exhibitions_from_listing_page(self, soup: BeautifulSoup, base_url: str, 
                                               venue_name: str = None, time_range: str = 'this_month') -> List[Dict]:
        """Extract exhibitions from a listing page (e.g., OCMA exhibitions page)"""
        events = []
        
        try:
            # Look for exhibition sections (Current, Upcoming, etc.)
            # OCMA format: Title followed by date range on same line or nearby
            # Example: "Cynthia Daignault: Light Atlas September 20, 2025 – February 8, 2026"
            
            # Find all headings that might indicate exhibition sections
            headings = soup.find_all(['h1', 'h2', 'h3'], string=lambda text: text and any(
                keyword in text.lower() for keyword in ['current', 'upcoming', 'exhibition', 'on view']
            ))
            
            # Also look for links to individual exhibition pages
            exhibition_links = soup.find_all('a', href=lambda href: href and '/exhibitions/' in str(href).lower())
            
            seen_titles = set()
            
            # Method 1: Extract from links to individual exhibition pages
            for link in exhibition_links:
                href = link.get('href', '')
                if not href or href == '/exhibitions/' or href.endswith('/exhibitions/'):
                    continue
                
                # Get the link text as potential title
                link_text = link.get_text(strip=True)
                
                # Find parent container (li, div, article, etc.)
                parent = link.find_parent(['li', 'div', 'article', 'section', 'p'])
                if not parent:
                    parent = link.parent
                
                # Get all text from the parent element
                parent_text = parent.get_text() if parent else ''
                
                # Pattern 1: Title followed by date range on same line
                # Example: "Cynthia Daignault: Light Atlas September 20, 2025 – February 8, 2026"
                date_range_pattern = re.compile(
                    r'([A-Z][^:]+(?:[:][^:]+)?)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*[–—\-]\s*([A-Z][a-z]+\s+\d{1,2},?\s+(\d{4}))',
                    re.MULTILINE
                )
                
                title = None
                date_text = None
                
                # Try to match the pattern in parent text
                match = date_range_pattern.search(parent_text)
                if match:
                    title = match.group(1).strip()
                    date_text = f"{match.group(2).strip()} – {match.group(3).strip()}"
                else:
                    # Pattern 2: Title on one line, date range on next line or nearby
                    # Look for date range pattern anywhere in parent
                    date_match = re.search(
                        r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*[–—\-]\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                        parent_text
                    )
                    if date_match:
                        date_text = date_match.group(0)
                        # Title might be the link text or text before the date
                        title = link_text if link_text and len(link_text) > 5 else None
                        if not title:
                            # Try to extract title from text before the date
                            text_before_date = parent_text[:date_match.start()].strip()
                            # Take the last meaningful phrase (likely the title)
                            title_parts = text_before_date.split('\n')
                            for part in reversed(title_parts):
                                part = part.strip()
                                if part and len(part) > 5 and self._is_valid_event_title(part):
                                    title = part
                                    break
                
                # Fallback: use link text as title if we have a date
                if not title and link_text and len(link_text) > 5:
                    title = link_text
                
                # If we still don't have a title, try to extract from the URL slug
                if not title or not self._is_valid_event_title(title):
                    # Extract from URL: /exhibitions/yoshitomo-nara-i-dont-want-to-grow-up/ -> "Yoshitomo Nara: I Don't Want to Grow Up"
                    url_slug = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    if url_slug and url_slug != 'exhibitions':
                        # Convert slug to title: replace hyphens with spaces, capitalize words
                        title = ' '.join(word.capitalize() for word in url_slug.replace('-', ' ').split())
                
                # Skip if title is invalid or already seen
                if not title or not self._is_valid_event_title(title) or title.lower() in seen_titles:
                    continue
                
                seen_titles.add(title.lower())
                
                # Parse dates from date_text
                start_date = None
                end_date = None
                if date_text:
                    # Use the date range parser
                    date_range = self._parse_date_range_string(date_text)
                    if date_range:
                        start_date = date_range.get('start_date')
                        end_date = date_range.get('end_date')
                
                # Also try to extract dates from title if we don't have them yet
                # Pattern: "TitleThrough Month Day, Year" or "Title Through Month Day, Year"
                if not start_date and title:
                    # Look for "Through" or "through" followed by date
                    through_pattern = r'[Tt]hrough\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'
                    through_match = re.search(through_pattern, title)
                    if through_match:
                        end_date_str = through_match.group(1)
                        end_date = self._parse_single_date_string(end_date_str)
                        # Clean title by removing the date part
                        title = re.sub(r'[Tt]hrough\s+[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}', '', title).strip()
                        # For exhibitions, if we only have end date, set start to today
                        if end_date and not start_date:
                            from datetime import date
                            start_date = date.today()
                    
                    # Also look for date ranges in title: "Title Month Day, Year – Month Day, Year"
                    if not start_date:
                        title_date_range = self._parse_date_range_string(title)
                        if title_date_range:
                            start_date = title_date_range.get('start_date')
                            end_date = title_date_range.get('end_date')
                            # Clean title by removing date range
                            title = re.sub(r'[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}\s*[–—\-]\s*[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}', '', title).strip()
                
                # Build full URL
                from urllib.parse import urljoin
                full_url = urljoin(base_url, href)
                
                # Only include current and upcoming exhibitions (not past)
                # If no date, include it (might be ongoing)
                if start_date:
                    # For 'this_month' time_range, include if it's current or upcoming
                    if time_range == 'this_month':
                        # Include if end date is in the future (current or upcoming)
                        from datetime import date
                        if end_date and end_date < date.today():
                            continue  # Skip past exhibitions
                    elif not self._is_in_time_range(start_date, time_range):
                        continue
                
                # Extract description from parent or nearby elements
                description = None
                if parent:
                    # Look for paragraph after the link
                    desc_elem = parent.find('p')
                    if desc_elem:
                        desc_text = desc_elem.get_text(strip=True)
                        # Skip if it's just the date
                        if not re.match(r'^[A-Z][a-z]+\s+\d{1,2}', desc_text):
                            description = desc_text[:500]
                    
                    # Also try meta description
                    if not description:
                        meta_desc = soup.find('meta', property='og:description')
                        if meta_desc:
                            description = meta_desc.get('content', '')[:500]
                
                # Extract image from listing page - search thoroughly before fetching individual page
                image_url = None
                
                # Strategy 1: Look in the link element itself
                if not image_url:
                    image_url = self._extract_image(link, base_url)
                
                # Strategy 2: Look in parent container
                if not image_url and parent:
                    image_url = self._extract_image(parent, base_url)
                
                # Strategy 3: Look in parent's parent (common pattern: article > div > a)
                if not image_url and parent and parent.parent:
                    image_url = self._extract_image(parent.parent, base_url)
                
                # Strategy 4: Look at next/previous siblings (common pattern: image and link are siblings)
                if not image_url and parent:
                    # Check previous sibling
                    prev_sibling = parent.previous_sibling
                    while prev_sibling and not image_url:
                        if hasattr(prev_sibling, 'find'):
                            image_url = self._extract_image(prev_sibling, base_url)
                        prev_sibling = prev_sibling.previous_sibling if hasattr(prev_sibling, 'previous_sibling') else None
                    
                    # Check next sibling
                    if not image_url:
                        next_sibling = parent.next_sibling
                        while next_sibling and not image_url:
                            if hasattr(next_sibling, 'find'):
                                image_url = self._extract_image(next_sibling, base_url)
                            next_sibling = next_sibling.next_sibling if hasattr(next_sibling, 'next_sibling') else None
                
                # Strategy 5: Look for images in the same container as the link (search up the tree)
                if not image_url:
                    container = parent
                    for _ in range(3):  # Search up to 3 levels up
                        if not container:
                            break
                        if hasattr(container, 'find_all'):
                            # Find all images in this container
                            imgs = container.find_all('img', limit=5)
                            for img in imgs:
                                img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                                if img_src:
                                    src_lower = img_src.lower()
                                    # Skip icons/logos
                                    if any(skip in src_lower for skip in ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg']):
                                        continue
                                    # Prefer substantial images
                                    if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                        from urllib.parse import urljoin
                                        image_url = urljoin(base_url, img_src)
                                        logger.debug(f"   ✅ Found image in container: {image_url[:80]}")
                                        break
                        if image_url:
                            break
                        container = container.parent if hasattr(container, 'parent') else None
                
                # Only fetch individual page as last resort if no image found on listing page
                if not image_url and full_url and full_url != base_url:
                    try:
                        logger.debug(f"   🖼️  No image on listing page, fetching individual exhibition page: {full_url}")
                        event_response = self._fetch_with_retry(full_url, base_url=base_url)
                        if event_response and event_response.status_code == 200:
                            event_soup = BeautifulSoup(event_response.content, 'html.parser')
                            # Use enhanced image extraction on the full page
                            image_url = self._extract_image(event_soup, base_url)
                            if image_url:
                                logger.debug(f"   ✅ Found image from exhibition page: {image_url[:80]}")
                    except Exception as e:
                        logger.debug(f"   ⚠️  Error fetching exhibition page for image: {e}")
                
                events.append({
                    'title': title,
                    'description': description or '',
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'start_time': None,
                    'end_time': None,
                    'start_location': venue_name,
                    'url': full_url,
                    'image_url': image_url,
                    'event_type': 'exhibition'
                })
            
            # Method 2: Extract from text patterns (for OCMA-style listings)
            # Look for patterns like "Title Title Date Range"
            page_text = soup.get_text()
            
            # Pattern: Title (with colon or multiple words) followed by date range
            exhibition_pattern = re.compile(
                r'([A-Z][^:]+(?:[:][^:]+)?)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*[–—\-]\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                re.MULTILINE
            )
            
            for match in exhibition_pattern.finditer(page_text):
                title = match.group(1).strip()
                start_date_str = match.group(2).strip()
                end_date_str = match.group(3).strip()
                
                # Skip if title is too generic
                if not self._is_valid_event_title(title) or title.lower() in seen_titles:
                    continue
                
                seen_titles.add(title.lower())
                
                # Parse dates
                start_date = None
                end_date = None
                
                # Parse dates using the single date parser
                start_date = None
                end_date = None
                try:
                    # Parse start date
                    start_date = self._parse_single_date_string(start_date_str)
                    
                    # Parse end date
                    end_date = self._parse_single_date_string(end_date_str)
                except Exception as e:
                    logger.debug(f"Error parsing dates from pattern match: {e}")
                    pass
                
                # Only include if in time range
                if start_date and not self._is_in_time_range(start_date, time_range):
                    continue
                
                # Try to find the URL for this exhibition
                exhibition_url = base_url
                for link in exhibition_links:
                    link_text = link.get_text(strip=True)
                    if title.lower() in link_text.lower() or link_text.lower() in title.lower():
                        from urllib.parse import urljoin
                        exhibition_url = urljoin(base_url, link.get('href', ''))
                        break
                
                # Extract image from listing page - search in the full page soup
                image_url = None
                
                # Try to find image associated with this exhibition in the listing page
                # Look for images near exhibition links that match the title
                if exhibition_links:
                    for link in exhibition_links:
                        link_text = link.get_text(strip=True)
                        if title.lower() in link_text.lower() or link_text.lower() in title.lower():
                            # Found matching link, extract image from its container
                            link_parent = link.parent
                            if link_parent:
                                image_url = self._extract_image(link_parent, base_url)
                                if not image_url and link_parent.parent:
                                    image_url = self._extract_image(link_parent.parent, base_url)
                            if image_url:
                                logger.debug(f"   ✅ Found image from listing page: {image_url[:80]}")
                                break
                
                # If still no image, try searching the full page for images near the title text
                if not image_url:
                    # Find all images in the page
                    all_imgs = soup.find_all('img')
                    for img in all_imgs:
                        img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                        if img_src:
                            src_lower = img_src.lower()
                            # Skip icons/logos
                            if any(skip in src_lower for skip in ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg']):
                                continue
                            # Check if image is near exhibition-related content
                            img_parent = img.parent
                            if img_parent:
                                parent_text = img_parent.get_text().lower()
                                # If image is in a container that mentions the title or exhibition keywords
                                if title.lower()[:20] in parent_text or any(kw in parent_text for kw in ['exhibition', 'show', 'gallery']):
                                    from urllib.parse import urljoin
                                    image_url = urljoin(base_url, img_src)
                                    logger.debug(f"   ✅ Found image near exhibition content: {image_url[:80]}")
                                    break
                
                # Only fetch individual page as last resort
                if not image_url and exhibition_url and exhibition_url != base_url:
                    try:
                        logger.debug(f"   🖼️  No image on listing page, fetching exhibition page: {exhibition_url}")
                        event_response = self._fetch_with_retry(exhibition_url, base_url=base_url)
                        if event_response and event_response.status_code == 200:
                            event_soup = BeautifulSoup(event_response.content, 'html.parser')
                            # Use enhanced image extraction on the full page
                            image_url = self._extract_image(event_soup, base_url)
                            if image_url:
                                logger.debug(f"   ✅ Found image from exhibition page: {image_url[:80]}")
                    except Exception as e:
                        logger.debug(f"   ⚠️  Error fetching exhibition page for image: {e}")
                
                events.append({
                    'title': title,
                    'description': '',
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'start_time': None,
                    'end_time': None,
                    'start_location': venue_name,
                    'url': exhibition_url,
                    'image_url': image_url,
                    'event_type': 'exhibition'
                })
            
            logger.info(f"📦 Extracted {len(events)} exhibitions from listing page")

        except Exception as e:
            logger.debug(f"Error extracting exhibitions from listing page: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        return events
    
    def _extract_museum_programs(self, soup: BeautifulSoup, base_url: str,
                                 venue_name: str = None, event_type: str = None,
                                 time_range: str = 'this_month') -> List[Dict]:
        """Extract museum programs (talks, lectures, workshops, tours) from listing pages"""
        events = []
        
        try:
            # Use museum-specific selectors first
            for selector in self.museum_event_selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} elements with museum selector: {selector}")
                        
                        for element in elements:
                            if self._should_skip_element(element):
                                continue
                            
                            event = self._parse_event_element(element, base_url, venue_name, event_type, time_range)
                            if event:
                                # Enhance event type detection for museum programs
                                if not event.get('event_type'):
                                    event['event_type'] = self._detect_museum_event_type(
                                        event.get('title', ''),
                                        event.get('description', ''),
                                        element
                                    )
                                events.append(event)
                except Exception as e:
                    logger.debug(f"Error with museum selector {selector}: {e}")
                    continue
            
            # Also extract from JSON-LD for museum events
            json_ld_events = self._extract_json_ld_events(soup, base_url)
            for event in json_ld_events:
                if not event.get('event_type'):
                    event['event_type'] = self._detect_museum_event_type(
                        event.get('title', ''),
                        event.get('description', ''),
                        None
                    )
            events.extend(json_ld_events)
            
        except Exception as e:
            logger.debug(f"Error extracting museum programs: {e}")
        
        return events
    
    def _detect_museum_event_type(self, title: str, description: str, element=None) -> str:
        """Detect museum-specific event types"""
        content = (title + ' ' + description).lower()
        
        # Museum-specific patterns
        if any(keyword in content for keyword in ['gallery talk', 'curator talk', 'curator\'s talk']):
            return 'talk'
        elif any(keyword in content for keyword in ['artist talk', 'artist conversation', 'artist discussion']):
            return 'talk'
        elif any(keyword in content for keyword in ['panel discussion', 'symposium', 'conference']):
            return 'talk'
        elif any(keyword in content for keyword in ['docent tour', 'guided tour', 'highlights tour']):
            return 'tour'
        elif any(keyword in content for keyword in ['workshop', 'studio class', 'art class']):
            return 'workshop'
        elif any(keyword in content for keyword in ['family program', 'family day', 'kids program']):
            return 'program'
        elif any(keyword in content for keyword in ['lecture', 'lecture series']):
            return 'talk'
        elif any(keyword in content for keyword in ['exhibition', 'exhibit', 'on view']):
            return 'exhibition'
        
        # Check element classes if available
        if element:
            classes = ' '.join(element.get('class', []))
            if 'exhibition' in classes.lower():
                return 'exhibition'
            elif 'talk' in classes.lower() or 'lecture' in classes.lower():
                return 'talk'
            elif 'tour' in classes.lower():
                return 'tour'
            elif 'workshop' in classes.lower() or 'class' in classes.lower():
                return 'workshop'
        
        return 'event'  # Default fallback



