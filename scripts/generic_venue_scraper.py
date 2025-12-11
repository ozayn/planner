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
            # Detect platform for Railway compatibility (Linux) vs local (macOS/Windows)
            import platform
            import os
            detected_platform = platform.system().lower()
            if detected_platform == 'linux' or 'RAILWAY_ENVIRONMENT' in os.environ:
                platform_name = 'linux'
            elif detected_platform == 'darwin':
                platform_name = 'darwin'
            else:
                platform_name = 'windows'
            
            self._cloudscraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': platform_name,
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
            # Disable SSL verification properly (fixes "Cannot set verify_mode to CERT_NONE when check_hostname is enabled")
            self._cloudscraper.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Fix SSL context to disable both verification and hostname checking
            import ssl
            from requests.adapters import HTTPAdapter
            from urllib3.poolmanager import PoolManager
            
            class SSLAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    kwargs['ssl_context'] = ctx
                    return super().init_poolmanager(*args, **kwargs)
            
            self._cloudscraper.mount('https://', SSLAdapter())
            
            # Establish session by visiting base URL if provided
            if base_url:
                try:
                    logger.debug(f"   🔧 Establishing cloudscraper session with {base_url}...")
                    self._cloudscraper.get(base_url, timeout=15, verify=False)
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
                        # Refresh session by visiting base URL first
                        try:
                            base = base_url or url.split('/')[0] + '//' + url.split('/')[2] if '/' in url else base_url or url
                            scraper.get(base, timeout=15, verify=False)
                            time.sleep(2)
                        except:
                            pass
                        # Now retry with cloudscraper
                        try:
                            response = scraper.get(url, timeout=20, verify=False)
                            if response.status_code == 200:
                                return response
                            # If still 403, continue to next attempt
                        except Exception as e:
                            logger.debug(f"   ⚠️  Cloudscraper attempt failed: {e}")
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
            '.exhibition-thumbnail', '.exhibition-image', '.exhibition-link',
            '.exhibition-title', '.exhibition-details', '.exhibition-meta',
            # Museum program selectors
            '.program', '.program-item', '.program-card', '.program-entry',
            '.program-teaser', '.program-list-item', '.program-block',
            '.program-thumbnail', '.program-image', '.program-link',
            # Gallery talk/lecture selectors
            '.gallery-talk', '.curator-talk', '.artist-talk', '.lecture-series',
            '.talk', '.talks', '.lecture', '.lectures', '.speaker-event',
            '.panel-discussion', '.conversation', '.symposium',
            '.artist-conversation', '.curator-conversation',
            # Museum tour selectors
            '.tour', '.tours', '.guided-tour', '.walking-tour', '.tour-item',
            '.docent-tour', '.highlights-tour', '.special-tour',
            '.collection-tour', '.gallery-tour',
            # Workshop/class selectors
            '.workshop', '.workshops', '.class', '.classes', '.course', '.courses',
            '.studio-class', '.art-class', '.family-program',
            # General event selectors
            '.event', '.events', '.event-item', '.event-card', '.event-list-item',
            '.event-entry', '.event-entry-item', '.event-teaser', '.event-summary',
            '.calendar-event', '.upcoming-event', '.past-event', '.featured-event',
            '.event-thumbnail', '.event-image', '.event-link', '.event-title',
            # Modern web patterns (common in React/Vue apps)
            '[class*="EventCard"]', '[class*="EventItem"]', '[class*="ExhibitionCard"]',
            '[class*="ProgramCard"]', '[class*="TourCard"]',
            # Generic patterns (museum-specific)
            '[class*="exhibition"]', '[class*="program"]', '[class*="gallery"]',
            '[class*="event"]', '[class*="tour"]', '[class*="workshop"]',
            '[class*="lecture"]', '[class*="talk"]', '[class*="show"]',
            # Data attributes
            '[data-event]', '[data-event-id]', '[data-event-type]',
            '[data-exhibition]', '[data-exhibition-id]', '[data-program]',
            '[data-tour]', '[data-workshop]',
            # Semantic HTML (museum-specific)
            'article.event', 'article.program', 'article.exhibition',
            'article.gallery-talk', 'article.lecture', 'article.tour',
            'li.event', 'li.program', 'li.exhibition', 'li.talk', 'li.tour',
            'div[itemtype*="Event"]', 'div[itemtype*="ExhibitionEvent"]',
            'div[itemtype*="VisualArtsEvent"]', 'div[itemtype*="TheaterEvent"]',
            # Common CMS patterns (museum websites)
            '.node-event', '.node-exhibition', '.node-program',
            '.view-events', '.view-exhibitions', '.view-programs',
            '.event-list', '.exhibition-list', '.program-list',
            '.events-grid', '.exhibitions-grid', '.programs-grid',
            # Museum-specific patterns
            '.collection-highlight', '.special-exhibition', '.featured-exhibition',
            '.on-view', '.current-show', '.upcoming-show',
            # Additional common patterns
            '.listing-item', '.content-item', '.post-item',
            '.card', '.tile', '.teaser',  # Generic card patterns
            'section.event', 'section.exhibition', 'section.program',
            # Link-based patterns (many museums use links as event containers)
            'a[href*="/exhibitions/"]', 'a[href*="/events/"]', 'a[href*="/programs/"]',
            'a[href*="/tours/"]', 'a[href*="/talks/"]', 'a[href*="/lectures/"]',
        ]
        
        # Fallback to general event selectors if museum-specific ones don't work
        self.event_selectors = self.museum_event_selectors
        
        # Common date/time patterns (expanded for better coverage)
        self.date_patterns = [
            # Full dates with time (comma-separated format: "December 5, 2025, 5:00–6:00 PM")
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "December 5, 2025, 5:00–6:00 PM"
            # Full dates with time (pipe-separated format: "December 5, 2025 | 11:30 am–12:00 pm")
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s+([ap])\.?m\.?',  # "December 5, 2025 | 11:30 am–12:00 pm"
            # Art Institute format: "Wed, Dec 17 | 12:00–12:30" (24-hour time, no AM/PM)
            r'(\w+day),?\s+(\w{3})\.?\s+(\d{1,2})\s*\|\s*(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})',  # "Wed, Dec 17 | 12:00–12:30"
            r'(\w+day),?\s+(\w{3})\.?\s+(\d{1,2}),?\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})',  # "Wed, Dec 17, 2025 | 12:00–12:30"
            r'(\w+day,?\s+)?(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # Abbreviated month formats
            r'(\w+day,?\s+)?(\w{3})\.?\s+(\d{1,2}),?\s+(\d{4})',  # "Dec. 5, 2025" or "Dec 5, 2025"
            r'(\w{3})\.?\s+(\d{1,2}),?\s+(\d{4})',  # "Dec 5, 2025" (no day of week)
            # Date ranges (museum exhibitions often use these)
            r'(\w+)\s+(\d{1,2})\s*[–-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23 - August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*[–-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 - August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*[–—\-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 – August 23, 2026" (em dash)
            r'(\w+)\s+(\d{1,2})\s*[–—\-]\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23 – August 23, 2026" (em dash)
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+through\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 through August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+to\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 to August 23, 2026"
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*–\s*(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026–August 23, 2026" (no spaces)
            # Abbreviated month date ranges
            r'(\w{3})\.?\s+(\d{1,2})\s*[–-]\s*(\w{3})\.?\s+(\d{1,2}),?\s+(\d{4})',  # "May 23 - Aug 23, 2026"
            r'(\w{3})\.?\s+(\d{1,2}),?\s+(\d{4})\s*[–-]\s*(\w{3})\.?\s+(\d{1,2}),?\s+(\d{4})',  # "May 23, 2026 - Aug 23, 2026"
            # Standard formats
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "December 5, 2025"
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # "5 December 2025"
            # Relative dates (for ongoing exhibitions)
            r'(ongoing|now\s+on\s+view|currently\s+on\s+view)',  # "Ongoing" or "Now on view"
        ]
        
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am–12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*-\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am - 12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s+to\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "11:30 am to 12:00 pm"
            r'(\d{1,2}):(\d{2})\s*([AP]M)\s*[–-]\s*(\d{1,2}):(\d{2})\s*([AP]M)',  # "11:30 AM–12:00 PM"
            r'(\d{1,2}):(\d{2})\s*([AP]M)',  # "11:30 AM"
            # 24-hour format
            r'(\d{1,2}):(\d{2})\s*[–-]\s*(\d{1,2}):(\d{2})',  # "11:30-12:00" (24-hour)
            r'(\d{1,2}):(\d{2})',  # "11:30"
            # Single digit hour
            r'(\d{1}):(\d{2})\s*([ap])\.?m\.?',  # "9:30 am"
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
                try:
                    page_events = self._scrape_event_page(
                        page_url, venue_name, event_type, time_range, 
                        use_llm_fallback=not llm_fallback_used
                    )
                    # If LLM fallback was used and returned events, mark it
                    if page_events and any(e.get('llm_extracted') for e in page_events):
                        llm_fallback_used = True
                    logger.info(f"      Found {len(page_events)} events on this page")
                    events.extend(page_events)
                except Exception as e:
                    # Skip pages that don't exist or can't be scraped
                    if '404' in str(e) or 'Not Found' in str(e):
                        logger.debug(f"   ⏭️  Skipping non-existent page: {page_url}")
                    else:
                        logger.debug(f"   ⚠️  Error scraping {page_url}: {e}")
                    continue
            
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
                '/exhibitions/upcoming', '/exhibitions/past',
                '/events', '/event', '/calendar', '/programs', '/program',
                '/whats-on', '/whats-on/current', '/whats-on/exhibitions', '/whats-on/events',
                '/visit/exhibitions', '/visit/tours-and-talks', '/visit/tours', '/visit/talks',
                '/see/exhibitions', '/explore/exhibitions',
                '/collection/exhibitions', '/art/exhibitions',
                '/current-exhibitions', '/upcoming-exhibitions', '/on-view',
                '/gallery', '/galleries', '/shows', '/shows/current',
                '/tours', '/talks', '/lectures', '/workshops',
                '/learn/programs', '/experience/events',
                # Combined patterns (common in university museums)
                '/exhibitions-events', '/exhibitions-events/events', '/exhibitions-events/exhibitions',
                '/exhibitions-and-events', '/exhibitions-and-events/events', '/exhibitions-and-events/exhibitions',
                '/events-exhibitions', '/events-exhibitions/events', '/events-exhibitions/exhibitions',
                '/programs-events', '/programs-events/events', '/programs-events/programs',
                '/whats-on/exhibitions-events', '/whats-on/events-exhibitions'
            ]
            
            parsed_base = urlparse(base_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            
            # Try common paths first (they'll be validated when we try to scrape them)
            # Non-existent URLs will be skipped gracefully during scraping
            for path in common_paths:
                test_url = base_domain + path
                if test_url not in seen_urls:
                    # Filter out non-event paths (like /learn/family-programs)
                    if self._is_likely_event_page(test_url, ''):
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
                'tours-and-talks', 'tours & talks',  # Combined tours and talks pages
                'whats-on', 'what\'s-on', 'whats-on', 'visit', 'see',
                'schedule', 'upcoming', 'current', 'featured', 'shows',
                # Additional patterns for better discovery
                'what-to-see', 'on-display', 'special-exhibitions',
                'temporary-exhibitions', 'visiting-exhibitions',
                # Combined patterns (common in university museums)
                'exhibitions-events', 'exhibitions-and-events', 'events-exhibitions',
                'programs-events', 'events-programs'
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
                        
                        # Skip if URL is clearly not an event page (filter out common non-event paths)
                        if self._is_likely_event_page(clean_url, text):
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
                    
                    # Skip if URL is clearly not an event page
                    if self._is_likely_event_page(clean_url, text):
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
    
    def _is_likely_event_page(self, url: str, link_text: str = '') -> bool:
        """Check if a URL is likely to be an event/exhibition page (not a general info page)"""
        url_lower = url.lower()
        text_lower = link_text.lower()
        
        # Filter out URLs that are clearly not event pages
        # These are often navigation links that don't lead to actual event listings
        
        # Skip URLs that are just category/info pages (not actual event listings)
        non_event_patterns = [
            '/learn/',  # Learning/education pages (like /learn/family-programs)
            '/about/',  # About pages
            '/contact',  # Contact pages
            '/tickets',  # Ticket pages
            '/membership',  # Membership pages
            '/shop',  # Shop pages
            '/store',  # Store pages
            '/donate',  # Donation pages
            '/support',  # Support pages
            '/press',  # Press pages
            '/news',  # News pages (unless it's news/events)
            '/blog',  # Blog pages
            '/search',  # Search pages
            '/login',  # Login pages
            '/register',  # Registration pages
            '/account',  # Account pages
            '/cart',  # Shopping cart
            '/checkout',  # Checkout pages
            '/visiting-',  # Visiting info pages (like /visiting-louvre, /visiting-museum)
            '/plan-your-visit',  # Visit planning pages
            '/plan-a-visit',  # Visit planning pages
        ]
        
        # Check if URL matches non-event patterns
        for pattern in non_event_patterns:
            if pattern in url_lower:
                # Exception: some museums have /learn/programs or /learn/events which ARE event pages
                if '/learn/programs' in url_lower or '/learn/events' in url_lower:
                    continue  # These are OK
                logger.debug(f"   ⏭️  Skipping non-event URL pattern: {url}")
                return False
        
        # Special handling for /visit/ paths - only allow event-related ones
        if '/visit/' in url_lower:
            # Allow event-related visit pages
            if '/visit/events' in url_lower or '/visit/exhibitions' in url_lower:
                return True  # These are OK
            # Filter out all other /visit/ pages (hours, admission, directions, etc.)
            visit_info_pages = [
                '/visit/hours', '/visit/admission', '/visit/directions',
                '/visit/parking', '/visit/accessibility', '/visit/access',
                '/visit/map', '/visit/transportation', '/visit/getting-here',
                '/visit/faq', '/visit/information', '/visit/info',
                '/visit/plan', '/visit/plan-your-visit', '/visit/guide'
            ]
            for info_page in visit_info_pages:
                if info_page in url_lower:
                    logger.debug(f"   ⏭️  Skipping visit info page: {url}")
                    return False
            # If it's /visit/ but not in our allow list, skip it to be safe
            logger.debug(f"   ⏭️  Skipping unknown /visit/ page: {url}")
            return False
        
        # Skip URLs that end with common non-event paths
        non_event_endings = [
            '/contact',
            '/about',
            '/tickets',
            '/membership',
            '/donate',
            '/shop',
            '/store',
            '/visiting',  # Visiting pages
        ]
        
        for ending in non_event_endings:
            if url_lower.endswith(ending) or url_lower.endswith(ending + '/'):
                logger.debug(f"   ⏭️  Skipping non-event URL ending: {url}")
                return False
        
        # Filter out URLs that contain visiting-related keywords (but aren't event pages)
        visiting_keywords = [
            '/visiting-',  # /visiting-louvre, /visiting-museum, etc.
            '/plan-your-visit',
            '/plan-a-visit',
            '/prepare-your-visit',
            '/before-you-visit',
        ]
        
        for keyword in visiting_keywords:
            if keyword in url_lower:
                logger.debug(f"   ⏭️  Skipping visiting info page: {url}")
                return False
        
        # URLs with event/exhibition keywords are likely event pages
        event_indicators = [
            '/exhibitions', '/exhibition', '/events', '/event',
            '/programs', '/program', '/calendar', '/tours',
            '/talks', '/lectures', '/workshops', '/shows',
            '/whats-on', '/on-view', '/current', '/upcoming'
        ]
        
        has_event_indicator = any(indicator in url_lower for indicator in event_indicators)
        
        # If link text has event keywords, it's more likely to be an event page
        text_has_event_keywords = any(keyword in text_lower for keyword in [
            'exhibition', 'event', 'program', 'calendar', 'tour',
            'talk', 'lecture', 'workshop', 'show', 'on view'
        ])
        
        # Accept if URL has event indicators OR link text has event keywords
        if has_event_indicator or text_has_event_keywords:
            return True
        
        # If neither, it's probably not an event page
        logger.debug(f"   ⏭️  Skipping URL without event indicators: {url}")
        return False
    
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
                                'image_url': event_data.get('image_url'),  # Include image URL from LLM extraction
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
            try:
                response = self._fetch_with_retry(url, base_url=base_url)
            except Exception as fetch_error:
                # Handle 404s and other HTTP errors gracefully
                error_str = str(fetch_error).lower()
                if '404' in error_str or 'not found' in error_str:
                    logger.debug(f"   ⏭️  Page not found (404): {url}")
                    return events
                # Re-raise other errors
                raise
            
            if not response:
                return events
            
            # Double-check status code (in case response was returned despite error)
            if response.status_code == 404:
                logger.debug(f"   ⏭️  Page not found (404): {url}")
                return events
            
            html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check if page is JavaScript-rendered (but still try pattern matching first!)
            is_js_rendered = self._is_javascript_rendered(soup)
            if is_js_rendered:
                logger.info(f"⚠️  Page appears to be JavaScript-rendered, but trying pattern matching first...")
            
            # Museum-specific: Check for exhibition listing pages (highest priority)
            url_lower = url.lower()
            
            # Check for combined paths first (e.g., /exhibitions-events/events should be treated as events page)
            is_combined_events_page = any(pattern in url_lower for pattern in [
                '/exhibitions-events/events', '/exhibitions-and-events/events',
                '/events-exhibitions/events', '/programs-events/events'
            ])
            is_combined_exhibitions_page = any(pattern in url_lower for pattern in [
                '/exhibitions-events/exhibitions', '/exhibitions-and-events/exhibitions',
                '/events-exhibitions/exhibitions'
            ])
            
            is_exhibition_page = (any(keyword in url_lower for keyword in [
                '/exhibitions', '/exhibition', '/on-view', '/current-exhibitions',
                '/upcoming-exhibitions', '/gallery', '/show', '/shows'
            ]) and not is_combined_events_page) or is_combined_exhibitions_page
            
            if is_exhibition_page or event_type == 'exhibition':
                exhibition_events = self._extract_exhibitions_from_listing_page(soup, url, venue_name, time_range)
                if exhibition_events:
                    logger.info(f"✅ Found {len(exhibition_events)} exhibitions from listing page")
                    events.extend(exhibition_events)
            
            # Museum-specific: Check for program/event listing pages
            is_program_page = (any(keyword in url_lower for keyword in [
                '/programs', '/program', '/events', '/calendar', '/talks',
                '/lectures', '/workshops', '/tours', '/whats-on'
            ]) and not is_exhibition_page) or is_combined_events_page
            
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
            # Filter out invalid events and shopping events before adding
            valid_html_events = [
                e for e in html_events 
                if self._is_valid_generic_event(e) and 
                not self._is_shopping_event(
                    e.get('title', ''),
                    e.get('description', ''),
                    e.get('url', '')
                )
            ]
            events.extend(valid_html_events)
            
            # Only use LLM fallback if:
            # 1. Page is JavaScript-rendered AND
            # 2. Pattern matching found no events AND
            # 3. LLM fallback is enabled
            if is_js_rendered and len(events) == 0 and use_llm_fallback:
                logger.info(f"⚠️  Pattern matching found no events on JS-rendered page, trying LLM fallback...")
                llm_events = self._use_llm_fallback_for_venue(base_url, venue_name, event_type)
                if llm_events:
                    logger.info(f"✅ LLM fallback found {len(llm_events)} events")
                    return llm_events
        
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
            event_type = self._determine_event_type(title, description, data.get('@type', ''), url)
            
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
        """Extract events from HTML using museum-specific selectors"""
        events = []
        seen_elements = set()

        selectors_to_try = self.museum_event_selectors if hasattr(self, 'museum_event_selectors') else self.event_selectors

        for selector in selectors_to_try:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"   Found {len(elements)} elements with selector: {selector}")

                    for element in elements:
                        element_id = id(element)
                        if element_id in seen_elements:
                            continue
                        seen_elements.add(element_id)
                        
                        if self._should_skip_element(element):
                            continue

                        try:
                            event = self._parse_event_element(element, base_url, venue_name, event_type, time_range)
                            if event:
                                if not event.get('event_type'):
                                    event['event_type'] = self._detect_museum_event_type(
                                        event.get('title', ''),
                                        event.get('description', ''),
                                        element,
                                        event.get('url', '')
                                    )
                                # Filter out events that are actually articles/videos (returned None)
                                if event.get('event_type') is None:
                                    logger.debug(f"   ⏭️  Skipping non-event content: {event.get('title', 'N/A')[:50]} (URL: {event.get('url', 'N/A')[:60]})")
                                    continue
                                events.append(event)
                                logger.debug(f"   ✅ Extracted event: {event.get('title', 'N/A')[:50]}")
                        except Exception as e:
                            logger.debug(f"   ⚠️  Error parsing event element: {e}")
                            continue  # Continue with next element instead of failing

            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue

        logger.info(f"   Extracted {len(events)} events from HTML patterns")
        return events
    
    def _is_valid_event_title(self, title: str, url: str = None) -> bool:
        """Validate that a title is actually an event title, not navigation/page element"""
        if not title or len(title) < 3:
            return False
        
        title_lower = title.lower().strip()
        title_original = title.strip()
        
        # Filter out permanent collection/gallery pages (not temporary exhibitions)
        permanent_collection_patterns = [
            r'^gallery\s+highlights?$',
            r'^permanent\s+collection',
            r'^collection\s+highlights?',
            r'^on\s+view\s+permanent',
            r'^permanent\s+galleries?',
            r'^highlights?\s+of\s+the\s+collection',
        ]
        for pattern in permanent_collection_patterns:
            if re.match(pattern, title_lower, re.IGNORECASE):
                return False
        
        # Filter out URLs that indicate permanent galleries (not exhibitions)
        if url:
            url_lower = url.lower()
            permanent_url_patterns = [
                '/gallery/',  # MFA uses /gallery/monet for permanent galleries
                '/collection/',
                '/permanent-',
                '/galleries/',
            ]
            # Check if URL contains permanent gallery indicators but NOT exhibition indicators
            has_permanent_indicator = any(pattern in url_lower for pattern in permanent_url_patterns)
            has_exhibition_indicator = any(indicator in url_lower for indicator in ['/exhibition', '/exhibit', '/show', '/on-view'])
            if has_permanent_indicator and not has_exhibition_indicator:
                return False
        
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
            'upcoming events', 'past events', 'all events',
            'gallery highlights',  # Permanent collection pages
        ]
        
        if title_lower in invalid_keywords:
            return False
        
        # Filter out titles that end with navigation symbols (arrows, etc.)
        if title.endswith('→') or title.endswith('←') or title.endswith('›') or title.endswith('»'):
            return False
        
        # Filter out titles that start with invalid keywords (partial match)
        for keyword in ['details', 'organizer', 'venue', 'filter', 'search', 'loading', 'gallery highlights']:
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
        
        # First remove venue name suffixes
        from scripts.utils import clean_event_title
        title = clean_event_title(title)
        
        # Remove HTML entities
        title = title.replace('&nbsp;', ' ').replace('&amp;', '&')
        title = title.replace('&quot;', '"').replace('&#39;', "'")
        title = title.replace('\xa0', ' ')  # Non-breaking space
        
        # Normalize whitespace (multiple spaces/newlines to single space)
        title = re.sub(r'\s+', ' ', title)
        
        # Remove "Museum Exhibition" prefix if it appears multiple times (indicates concatenation)
        # Pattern: "Museum Exhibition Title1 ... Museum Exhibition Title2 ..."
        if title.count('Museum Exhibition') > 1:
            # Take only the first exhibition title
            parts = title.split('Museum Exhibition')
            if len(parts) > 1:
                # Get the first part after "Museum Exhibition"
                first_exhibition = parts[1].strip()
                # Remove date ranges and other exhibitions from the end
                # Look for the next "Museum Exhibition" or date pattern
                next_exhibition_match = re.search(r'(Museum Exhibition|October|November|December|January|February|March|April|May|June|July|August|September)', first_exhibition[100:])
                if next_exhibition_match:
                    first_exhibition = first_exhibition[:100 + next_exhibition_match.start()].strip()
                title = 'Museum Exhibition ' + first_exhibition
                logger.debug(f"   🧹 Cleaned concatenated title, kept first: {title[:80]}")
        
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
        
        # Remove common HTML entities and special characters
        title = title.replace('&nbsp;', ' ').replace('&amp;', '&')
        title = title.replace('\xa0', ' ')  # Non-breaking space
        
        # Strip leading/trailing whitespace
        title = title.strip()
        
        return title
    
    def _clean_description(self, description: str) -> str:
        """Clean and normalize description text"""
        if not description:
            return description
        
        # Remove HTML entities
        description = description.replace('&nbsp;', ' ').replace('&amp;', '&')
        description = description.replace('&quot;', '"').replace('&#39;', "'")
        description = description.replace('\xa0', ' ')  # Non-breaking space
        
        # Normalize whitespace (multiple spaces/newlines to single space)
        description = re.sub(r'\s+', ' ', description)
        
        # Remove leading/trailing whitespace
        description = description.strip()
        
        # Remove common prefixes that aren't useful
        prefixes_to_remove = [
            r'^Description:\s*',
            r'^About:\s*',
            r'^Details:\s*',
        ]
        for prefix in prefixes_to_remove:
            description = re.sub(prefix, '', description, flags=re.IGNORECASE)
        
        return description
    
    def _parse_event_element(self, element, base_url: str, venue_name: str = None,
                            event_type: str = None, time_range: str = 'this_month') -> Optional[Dict]:
        """Parse a single event element from HTML"""
        try:
            # Extract title (enhanced with more selectors)
            title = self._extract_text(element, [
                'h1', 'h2', 'h3', 'h4', '.title', '.event-title', '.name',
                '.exhibition-title', '.program-title', '.event-name',
                '[itemprop="name"]', 'meta[property="og:title"]',
                'a.title', 'a.event-title', '.heading', '.headline'
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
            
            # Extract URL first (needed for validation)
            url = self._extract_url(element, base_url)
            
            # Validate title is actually an event, not navigation/page element
            if not self._is_valid_event_title(title, url):
                return None
            
            # Clean title to remove dates, trailing commas, etc.
            title = self._clean_title(title)
            
            # Extract description (enhanced)
            description = self._extract_text(element, [
                '.description', '.summary', '.content', 'p', '.event-description',
                '.exhibition-description', '.program-description',
                '[itemprop="description"]', 'meta[property="og:description"]',
                '.excerpt', '.blurb', '.intro'
            ])
            
            # Extract date/time
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when', '.schedule',
                '[itemprop="startDate"]', '[itemprop="endDate"]', 'time[datetime]',
                '.exhibition-date', '.event-date', '.date-range', '.on-view',
                '.dates', '.duration', '.period'
            ])
            
            # Also check parent and sibling elements for dates (common pattern)
            if not date_text and element.parent:
                parent_date_text = self._extract_text(element.parent, [
                    '.date', '.time', '.datetime', '.when', '.schedule',
                    '[itemprop="startDate"]', '[itemprop="endDate"]', 'time[datetime]',
                    '.exhibition-date', '.event-date', '.date-range', '.on-view'
                ])
                if parent_date_text:
                    date_text = parent_date_text
            
            start_date, end_date, start_time, end_time = self._parse_dates_and_times(
                date_text, element, base_url
            )
            
            # Use dates extracted from title if we don't have them from date_text
            if not start_date and extracted_start_date:
                start_date = extracted_start_date
            if not end_date and extracted_end_date:
                end_date = extracted_end_date
            
            # If still no dates and this is an exhibition, try to extract from description
            # Some museums embed dates in descriptions like "On view through January 2026"
            if not start_date and not end_date and description:
                # Look for "through" or "until" patterns in description
                through_pattern = r'(?:through|until|thru)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'
                through_match = re.search(through_pattern, description, re.IGNORECASE)
                if through_match:
                    end_date_str = through_match.group(1)
                    parsed_end_date = self._parse_single_date_string(end_date_str)
                    if parsed_end_date:
                        from datetime import date
                        end_date = parsed_end_date
                        # For exhibitions ending in the future, assume they started recently or are ongoing
                        # Set start_date to today if not already set
                        if not start_date:
                            start_date = date.today()
                        logger.debug(f"   📅 Extracted end date from description: {end_date}, set start_date to {start_date}")
                
                # Look for date ranges in description
                if not start_date or not end_date:
                    desc_date_range = self._parse_date_range_string(description)
                    if desc_date_range:
                        if not start_date:
                            start_date = desc_date_range.get('start_date')
                        if not end_date:
                            end_date = desc_date_range.get('end_date')
                        logger.debug(f"   📅 Extracted date range from description: {start_date} to {end_date}")
            
            # Extract location
            location = self._extract_text(element, [
                '.location', '.venue', '.where', '.address', '.meeting-point',
                '[itemprop="location"]', '[itemprop="address"]'
            ])
            
            # URL already extracted above for validation
            
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
                        # Try to find the main content area, but be more specific
                        # Look for article, main, or content containers, but prefer more specific ones
                        event_main_content = None
                        # Try specific content containers first
                        for selector in ['article', 'main', '[role="main"]', '.content', '.main-content', '.page-content']:
                            event_main_content = event_soup.select_one(selector)
                            if event_main_content:
                                break
                        if not event_main_content:
                            event_main_content = event_soup
                        
                        # Extract title from event page (more accurate than listing page)
                        # Prioritize h1, then og:title meta tag
                        event_page_title = None
                        h1 = event_soup.find('h1')
                        if h1:
                            event_page_title = h1.get_text(strip=True)
                            # Clean up the title - remove extra whitespace and newlines
                            event_page_title = re.sub(r'\s+', ' ', event_page_title)
                            # Remove date ranges that might be in the h1
                            event_page_title = re.sub(r'\s+[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}\s*[–—\-]\s*[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}\s*$', '', event_page_title)
                            logger.debug(f"   📝 Extracted title from h1: {event_page_title[:80]}")
                        
                        if not event_page_title:
                            og_title = event_soup.find('meta', property='og:title')
                            if og_title:
                                event_page_title = og_title.get('content', '').strip()
                                logger.debug(f"   📝 Extracted title from og:title: {event_page_title[:80]}")
                        
                        # Use event page title if we have one and it's reasonable
                        if event_page_title:
                            # Clean the event page title
                            event_page_title = self._clean_title(event_page_title)
                            # Check if it looks like a valid title (not too long, not multiple exhibitions)
                            if event_page_title and len(event_page_title) < 200:
                                # Check if it contains multiple "Museum Exhibition" patterns (indicates concatenation)
                                museum_exhibition_count = event_page_title.count('Museum Exhibition')
                                if museum_exhibition_count <= 1:
                                    title = event_page_title
                                    logger.info(f"   ✅ Updated title from event page: {title[:80]}")
                                else:
                                    logger.debug(f"   ⚠️  Title appears to contain multiple exhibitions, keeping original")
                        
                        # First, try to extract date/time from h2 tags (common pattern, e.g., OCMA)
                        # Look for patterns like "December 5, 2025, 5:00–6:00 PM" or "Dec 13 @ 1:00 pm – 3:00 pm" in h2 tags
                        h2_tags = event_soup.find_all('h2') if event_soup else []
                        for h2 in h2_tags:
                            h2_text = h2.get_text(strip=True)
                            # Check for combined date+time patterns (including @ format)
                            combined_patterns = [
                                r'(\w+)\s+(\d{1,2})\s*@\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "Dec 13 @ 1:00 pm – 3:00 pm"
                                r'(\w+)\s+(\d{1,2}),?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',  # "December 5, 2025, 5:00–6:00 PM"
                            ]
                            match = None
                            for pattern in combined_patterns:
                                match = re.search(pattern, h2_text, re.IGNORECASE)
                                if match:
                                    break
                            if match:
                                groups = match.groups()
                                try:
                                    # Parse date - handle patterns with and without year
                                    month = self._month_name_to_num(groups[0])
                                    day = int(groups[1])
                                    
                                    # Check if year is present (patterns with year have it in position 2)
                                    if len(groups) >= 8 and groups[2].isdigit() and len(groups[2]) == 4:
                                        year = int(groups[2])
                                        time_start_idx = 3
                                    else:
                                        # No year - use current year or next year if month has passed
                                        today = date.today()
                                        year = today.year
                                        if month < today.month or (month == today.month and day < today.day):
                                            year = today.year + 1
                                        time_start_idx = 2
                                    
                                    start_date = date(year, month, day)
                                    
                                    # Parse start time
                                    start_hour = int(groups[time_start_idx])
                                    start_min = int(groups[time_start_idx + 1])
                                    start_ampm = groups[time_start_idx + 2].lower()
                                    if start_ampm == 'p' and start_hour != 12:
                                        start_hour += 12
                                    elif start_ampm == 'a' and start_hour == 12:
                                        start_hour = 0
                                    start_time = time(start_hour, start_min)
                                    
                                    # Parse end time
                                    if len(groups) >= time_start_idx + 6:
                                        end_hour = int(groups[time_start_idx + 3])
                                        end_min = int(groups[time_start_idx + 4])
                                        end_ampm = groups[time_start_idx + 5].lower()
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
                            # But limit to the main content area to avoid getting text from other exhibitions
                            event_text = event_main_content.get_text() if event_main_content else ''
                            
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
                        
                        # Extract image from event page (prioritize event page image over listing page)
                        # Strategy 1: Try og:image meta tag first (most reliable for individual pages)
                        og_image = event_soup.find('meta', property='og:image')
                        if og_image:
                            og_image_url = og_image.get('content', '')
                            if og_image_url:
                                if not og_image_url.startswith('http'):
                                    og_image_url = urljoin(url, og_image_url)
                                image_url = og_image_url
                                logger.info(f"   ✅ Found image from og:image meta tag: {image_url[:80]}")
                        
                        # Strategy 2: If no og:image, prioritize first image in article content (main event image)
                        if not image_url and event_main_content:
                            # Find first image in the main content area (not in sidebars)
                            article_imgs = event_main_content.find_all('img')
                            for img in article_imgs:
                                # Skip if in sidebar/related sections
                                ancestor = img.parent
                                in_sidebar = False
                                for _ in range(6):
                                    if not ancestor:
                                        break
                                    if hasattr(ancestor, 'get'):
                                        classes = ' '.join(ancestor.get('class', []))
                                        if any(pattern in classes.lower() for pattern in [
                                            'sidebar', 'footer', 'related', 'explore', 'spotlight', 
                                            'recommended', 'more', 'also', 'other', 'secondary'
                                        ]):
                                            in_sidebar = True
                                            break
                                    ancestor = ancestor.parent if hasattr(ancestor, 'parent') else None
                                
                                if not in_sidebar:
                                    img_src = (img.get('src') or img.get('data-src') or 
                                              img.get('data-lazy-src') or img.get('data-original'))
                                    if img_src:
                                        # Skip icons/logos
                                        src_lower = img_src.lower()
                                        if not any(skip in src_lower for skip in ['icon', 'logo', 'favicon', 'avatar', 'social']):
                                            if not img_src.startswith('http'):
                                                img_src = urljoin(url, img_src)
                                            image_url = img_src
                                            logger.info(f"   ✅ Found first image in article content: {image_url[:80]}")
                                            break
                        
                        # Strategy 3: If still no image, use the enhanced image extraction method
                        if not image_url:
                            event_page_image = self._extract_image(event_soup, url)
                            if event_page_image:
                                image_url = event_page_image
                                logger.info(f"   ✅ Found image from event page extraction: {image_url[:80]}")
                            else:
                                logger.debug(f"   ⚠️  No image found on event page: {url[:60]}")
                except Exception as e:
                    logger.debug(f"Error fetching individual event page {url}: {e}")
            
            # Determine event type
            if not event_type:
                event_type = self._determine_event_type(title, description, '', url)
            
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
            
            # Clean description
            if description:
                description = self._clean_description(description)
            
            return {
                'title': title.strip(),
                'description': description if description else '',
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
        """Extract text using multiple selector strategies"""
        # Try CSS selectors first
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    text = found.get_text(strip=True)
                    if text and len(text) > 3:
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
        
        # Fallback: try common heading/text patterns in element
        if not element:
            return None
        
        # Check if element is a BeautifulSoup element (has find method), not a string
        if not hasattr(element, 'find'):
            return None
        
        # Try h1-h4 tags
        for tag in ['h1', 'h2', 'h3', 'h4']:
            try:
                heading = element.find(tag)
                if heading:
                    text = heading.get_text(strip=True)
                    if text and len(text) > 3:
                        return text
            except (TypeError, AttributeError):
                continue
        
        # Try first link text (often contains title)
        try:
            link = element.find('a')
            if link:
                text = link.get_text(strip=True)
                if text and len(text) > 3:
                    return text
        except (TypeError, AttributeError):
            pass
        
        # Try first strong/b tag
        try:
            strong = element.find(['strong', 'b'])
            if strong:
                text = strong.get_text(strip=True)
                if text and len(text) > 3:
                    return text
        except (TypeError, AttributeError):
            pass

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
            try:
                first_p = element.find('p')
                if first_p:
                    text = first_p.get_text(strip=True)
                    if text and len(text) > 50:
                        return text
            except (TypeError, AttributeError):
                pass

        # Fallback: get text from element itself
        if hasattr(element, 'get_text'):
            try:
                text = element.get_text(strip=True)
                if text and len(text) > 3:
                    return text
            except (TypeError, AttributeError):
                pass

        return None
    
    def _extract_url(self, element, base_url: str) -> Optional[str]:
        """Extract event URL"""
        # Try link (check element itself and parent)
        link = element.find('a', href=True)
        if not link and element.parent:
            link = element.parent.find('a', href=True)
        if not link and hasattr(element, 'parent') and element.parent and hasattr(element.parent, 'parent'):
            link = element.parent.parent.find('a', href=True) if element.parent.parent else None
        
        if link:
            href = link.get('href', '')
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                return urljoin(base_url, href)
        
        # Try data attributes
        for attr in ['data-url', 'data-href', 'data-link', 'data-permalink']:
            if element.get(attr):
                url_val = element[attr]
                if url_val and not url_val.startswith('#') and not url_val.startswith('javascript:'):
                    return urljoin(base_url, url_val)
        
        # Try onclick attribute (sometimes contains URL)
        onclick = element.get('onclick', '')
        if onclick:
            url_match = re.search(r'["\']([^"\']+\.html?[^"\']*)["\']', onclick)
            if url_match:
                return urljoin(base_url, url_match.group(1))
        
        return base_url
    
    def _extract_image(self, element, base_url: str) -> Optional[str]:
        """Extract event image URL using multiple strategies (learned from specialized scrapers)"""
        image_url = None
        
        # Helper function to check if image is in sidebar/related/explore sections
        def is_in_sidebar_or_related(img):
            """Check if image is in sidebar, footer, or related content sections"""
            ancestor = img.parent
            for _ in range(6):  # Check up to 6 levels up
                if not ancestor:
                    break
                if hasattr(ancestor, 'get'):
                    classes = ' '.join(ancestor.get('class', []))
                    tag = ancestor.name if hasattr(ancestor, 'name') else ''
                    # Check for sidebar/related/explore patterns
                    if any(pattern in classes.lower() for pattern in [
                        'sidebar', 'footer', 'related', 'explore', 'spotlight', 
                        'recommended', 'more', 'also', 'other', 'secondary'
                    ]):
                        return True
                    # Check for specific section tags that are usually sidebars
                    if tag in ['aside', 'footer']:
                        return True
                ancestor = ancestor.parent if hasattr(ancestor, 'parent') else None
            return False
        
        # Strategy 1: Look for hero/feature/main images by class (highest priority)
        img_elem = None
        if hasattr(element, 'find'):
            try:
                img_elem = element.find('img', class_=re.compile(r'hero|feature|main|exhibition|header|event', re.I))
            except (TypeError, AttributeError):
                pass
        if img_elem:
            # Skip if in sidebar/related
            if not is_in_sidebar_or_related(img_elem):
                img_src = (img_elem.get('src') or img_elem.get('data-src') or 
                          img_elem.get('data-lazy-src') or img_elem.get('data-original') or
                          img_elem.get('data-srcset') or img_elem.get('data-image'))
                if img_src:
                    # Handle srcset (take first URL)
                    if ',' in img_src:
                        img_src = img_src.split(',')[0].strip().split()[0]
                    image_url = urljoin(base_url, img_src)
                    return image_url
        
        # Strategy 2: Look for images with keywords in URL (but skip sidebar/related)
        if not image_url and hasattr(element, 'find_all'):
            try:
                all_imgs = element.find_all('img')
                for img in all_imgs:
                    # Skip images in sidebar/related sections
                    if is_in_sidebar_or_related(img):
                        continue
                    
                    img_src = (img.get('src') or img.get('data-src') or 
                              img.get('data-lazy-src') or img.get('data-original') or
                              img.get('data-srcset') or img.get('data-image'))
                    if img_src:
                        # Handle srcset
                        if ',' in img_src:
                            img_src = img_src.split(',')[0].strip().split()[0]
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
            except (TypeError, AttributeError):
                pass
        
        # Strategy 3: Find first substantial image (jpg/png/webp) not in nav/footer/sidebar
        if not image_url and hasattr(element, 'find_all'):
            try:
                all_imgs = element.find_all('img')
                for img in all_imgs:
                    # Skip images in sidebar/related sections
                    if is_in_sidebar_or_related(img):
                        continue
                    
                    img_src = (img.get('src') or img.get('data-src') or 
                              img.get('data-lazy-src') or img.get('data-original') or
                              img.get('data-srcset') or img.get('data-image'))
                    if img_src:
                        # Handle srcset
                        if ',' in img_src:
                            img_src = img_src.split(',')[0].strip().split()[0]
                        src_lower = img_src.lower()
                        # Skip icons/logos
                        skip_patterns = ['icon', 'logo', 'favicon', 'avatar', 'social', 'svg']
                        if any(pattern in src_lower for pattern in skip_patterns):
                            continue
                        
                        # Check if it's a real image file
                        if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            # Check if it's not in navigation/footer
                            parent = img.parent
                            skip_containers = ['nav', 'header', 'footer', 'menu', 'aside']
                            parent_tag = parent.name if parent else ''
                            parent_classes = ' '.join(parent.get('class', [])) if parent and hasattr(parent, 'get') else ''
                            
                            if parent_tag not in skip_containers and not any(skip in parent_classes.lower() for skip in skip_containers):
                                image_url = urljoin(base_url, img_src)
                                break
            except (TypeError, AttributeError):
                pass
        
        # Strategy 4: Try meta tags (og:image) - highest priority for individual pages
        if hasattr(element, 'select_one'):
            try:
                og_image = element.select_one('meta[property="og:image"]')
                if og_image:
                    og_image_url = og_image.get('content', '')
                    if og_image_url:
                        if not og_image_url.startswith('http'):
                            og_image_url = urljoin(base_url, og_image_url)
                        # Use og:image if we don't have one yet, or if current one seems wrong
                        if not image_url or is_in_sidebar_or_related(element):
                            image_url = og_image_url
                            logger.debug(f"   ✅ Using og:image: {image_url[:80]}")
            except (TypeError, AttributeError):
                pass
        
        return image_url
    
    def _parse_dates_and_times(self, date_text: str, element, base_url: str) -> Tuple:
        """Parse dates and times from text and HTML attributes"""
        start_date = None
        end_date = None
        start_time = None
        end_time = None
        today = date.today()
        
        # Get full text from element if date_text is limited
        # Check if element is a BeautifulSoup element (has get_text method), not a string
        if element and hasattr(element, 'get_text'):
            full_text = element.get_text()
        else:
            full_text = date_text or ''
        search_text = full_text if len(full_text) > len(date_text or '') else (date_text or '')
        
        # Try time[datetime] attribute first
        # Only call find() if element is a BeautifulSoup element, not a string
        time_elem = None
        if element and hasattr(element, 'find'):
            try:
                time_elem = element.find('time', datetime=True)
            except (TypeError, AttributeError):
                # Element might be a string or not a BeautifulSoup element
                time_elem = None
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
            # Art Institute format: "Wed, Dec 17 | 12:00–12:30" (24-hour format, no AM/PM)
            # Handles both abbreviated (Wed, Mon, Tue) and full (Wednesday, Monday) day names
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w{3})\.?\s+(\d{1,2}),?\s*(?:(\d{4}))?\s*\|\s*(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})',
            # Art Institute format without day of week: "Dec 17 | 12:00–12:30"
            r'(\w{3})\.?\s+(\d{1,2}),?\s*(?:(\d{4}))?\s*\|\s*(\d{1,2}):(\d{2})\s*[–—\-]\s*(\d{1,2}):(\d{2})',
            # "Dec 13 @ 1:00 pm – 3:00 pm" (at-symbol format, abbreviated month, no year)
            r'(\w+)\s+(\d{1,2})\s*@\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # "December 13 @ 1:00 pm – 3:00 pm" (at-symbol format, full month, no year)
            r'(\w+)\s+(\d{1,2})\s*@\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # "Dec 13, 2025 @ 1:00 pm – 3:00 pm" (at-symbol format with year)
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*@\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # "December 5, 2025, 5:00–6:00 PM" (comma-separated)
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
            # "December 5, 2025 | 5:00–6:00 PM" (pipe-separated with AM/PM)
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s*\|\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*[–—\-]\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?',
        ]
        
        for pattern_idx, pattern in enumerate(combined_patterns):
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    # Handle Art Institute format: "Wed, Dec 17 | 12:00–12:30"
                    # Pattern 0: groups[0]=month, groups[1]=day, groups[2]=year (optional), groups[3]=start_hour, groups[4]=start_min, groups[5]=end_hour, groups[6]=end_min
                    # Pattern 1: groups[0]=month, groups[1]=day, groups[2]=year (optional), groups[3]=start_hour, groups[4]=start_min, groups[5]=end_hour, groups[6]=end_min
                    if pattern_idx == 0:  # "Wed, Dec 17 | 12:00–12:30" (with day of week, no year)
                        month = self._month_name_to_num(groups[0])
                        day = int(groups[1])
                        # Check if year is present (groups[2] if it exists and is 4 digits)
                        if len(groups) >= 7 and groups[2] and groups[2].isdigit() and len(groups[2]) == 4:
                            year = int(groups[2])
                            time_start_idx = 3
                        else:
                            # No year - use current year or next year if month has passed
                            today = date.today()
                            year = today.year
                            if month < today.month or (month == today.month and day < today.day):
                                year = today.year + 1
                            time_start_idx = 2
                        
                        start_date = date(year, month, day)
                        
                        # Parse 24-hour time
                        start_hour = int(groups[time_start_idx])
                        start_min = int(groups[time_start_idx + 1])
                        start_time = time(start_hour, start_min)
                        
                        end_hour = int(groups[time_start_idx + 2])
                        end_min = int(groups[time_start_idx + 3])
                        end_time = time(end_hour, end_min)
                        
                        logger.debug(f"   ✅ Extracted date+time from Art Institute format (with day of week): {start_date} {start_time}-{end_time}")
                        break
                    elif pattern_idx == 1:  # "Dec 17 | 12:00–12:30" (no day of week)
                        month = self._month_name_to_num(groups[0])
                        day = int(groups[1])
                        # Check if year is present
                        if len(groups) >= 6 and groups[2] and groups[2].isdigit() and len(groups[2]) == 4:
                            year = int(groups[2])
                            time_start_idx = 3
                        else:
                            # No year - use current year or next year if month has passed
                            today = date.today()
                            year = today.year
                            if month < today.month or (month == today.month and day < today.day):
                                year = today.year + 1
                            time_start_idx = 2
                        
                        start_date = date(year, month, day)
                        
                        # Parse 24-hour time
                        start_hour = int(groups[time_start_idx])
                        start_min = int(groups[time_start_idx + 1])
                        start_time = time(start_hour, start_min)
                        
                        end_hour = int(groups[time_start_idx + 2])
                        end_min = int(groups[time_start_idx + 3])
                        end_time = time(end_hour, end_min)
                        
                        logger.debug(f"   ✅ Extracted date+time from Art Institute format (no day of week): {start_date} {start_time}-{end_time}")
                        break
                    else:
                        # Original patterns (at-symbol and pipe-separated with AM/PM)
                        # Parse date - handle patterns with and without year
                        month = self._month_name_to_num(groups[0])
                        day = int(groups[1])
                        
                        # Check if year is in groups (patterns with year have it in position 2)
                        # Patterns without year: groups[0]=month, groups[1]=day, groups[2]=hour
                        # Patterns with year: groups[0]=month, groups[1]=day, groups[2]=year, groups[3]=hour
                        if len(groups) >= 8 and groups[2].isdigit() and len(groups[2]) == 4:
                            # Has year in position 2
                            year = int(groups[2])
                            time_start_idx = 3
                        else:
                            # No year - use current year or next year if month has passed
                            today = date.today()
                            year = today.year
                            if month < today.month or (month == today.month and day < today.day):
                                year = today.year + 1
                            time_start_idx = 2
                        
                        start_date = date(year, month, day)
                        
                        # Parse start time (index depends on whether year was present)
                        start_hour = int(groups[time_start_idx])
                        start_min = int(groups[time_start_idx + 1])
                        start_ampm = groups[time_start_idx + 2].lower()
                        if start_ampm == 'p' and start_hour != 12:
                            start_hour += 12
                        elif start_ampm == 'a' and start_hour == 12:
                            start_hour = 0
                        start_time = time(start_hour, start_min)
                        
                        # Parse end time
                        if len(groups) >= time_start_idx + 6:
                            end_hour = int(groups[time_start_idx + 3])
                            end_min = int(groups[time_start_idx + 4])
                            end_ampm = groups[time_start_idx + 5].lower()
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
                        # Parse dates - if year is missing, infer it intelligently
                        start_date = self._parse_single_date_string(start_str)
                        end_date = self._parse_single_date_string(end_str)
                        
                        if start_date and end_date:
                            # If start_date is after end_date, it means we inferred wrong years
                            # This happens with ranges like "Nov 28 – Dec 31" where both should be same year
                            if start_date > end_date:
                                # Check if both dates are missing years (both parsed with inferred years)
                                # If so, they should be in the same year
                                from datetime import date
                                today = date.today()
                                
                                # Re-parse with smarter year inference for ranges
                                # If start month > end month (e.g., Nov > Dec), they're in same year
                                # Otherwise, end is in next year
                                start_month = start_date.month
                                end_month = end_date.month
                                
                                # Extract just month and day from strings
                                import re
                                start_match = re.search(r'([A-Z][a-z]+)\s+(\d{1,2})', start_str)
                                end_match = re.search(r'([A-Z][a-z]+)\s+(\d{1,2})', end_str)
                                
                                if start_match and end_match and not any(c.isdigit() and len(c) == 4 for c in [start_str, end_str]):
                                    # Both dates missing years - infer same year
                                    year = today.year
                                    # If both months have passed, use next year
                                    if start_month < today.month and end_month < today.month:
                                        year = today.year + 1
                                    # If start month has passed but end hasn't, use current year
                                    elif start_month < today.month <= end_month:
                                        year = today.year
                                    
                                    start_day = int(start_match.group(2))
                                    end_day = int(end_match.group(2))
                                    start_date = date(year, start_month, start_day)
                                    end_date = date(year, end_month, end_day)
                                    
                                    # If end month is before start month (e.g., Dec to Jan), end is next year
                                    if end_month < start_month:
                                        end_date = date(year + 1, end_month, end_day)
                            
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
        
        # Try common date formats (including British format: "2 October 2025")
        date_formats = [
            '%d %B %Y',       # 2 October 2025 (British format - try first for Tate)
            '%d %b %Y',       # 2 Oct 2025 (British format abbreviated)
            '%B %d, %Y',      # November 25, 2025 (American format)
            '%b %d, %Y',      # Nov 25, 2025 (American format abbreviated)
            '%B %d %Y',       # November 25 2025 (American format without comma)
            '%b %d %Y',       # Nov 25 2025 (American format abbreviated without comma)
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
        
        # Pattern 1: "Day Month Year" (British format: "2 October 2025")
        pattern_british = rf'{day_pattern}\s+{month_pattern}\s+{year_pattern}'
        match_british = re.search(pattern_british, date_string, re.IGNORECASE)
        if match_british:
            try:
                day = int(match_british.group(1))
                month_str = match_british.group(2)
                year = int(match_british.group(3))
                month = self._month_name_to_num(month_str)
                if month:
                    return date(year, month, day)
            except (ValueError, IndexError):
                pass
        
        # Pattern 2: "Month Day, Year" (American format: "October 2, 2025")
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
        
        # Pattern: "Month Day" (without year - assume current year or next year if month has passed)
        pattern2 = rf'{month_pattern}\s+{day_pattern}$'
        match = re.search(pattern2, date_string, re.IGNORECASE)
        if match:
            try:
                month_str = match.group(1)
                day = int(match.group(2))
                month = self._month_name_to_num(month_str)
                if month:
                    # Use current year, or next year if the month has already passed
                    today = date.today()
                    year = today.year
                    # If the month is in the past (and we're past that day), use next year
                    if month < today.month or (month == today.month and day < today.day):
                        year = today.year + 1
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
    
    def _determine_event_type(self, title: str, description: str = '', json_type: str = '', url: str = '') -> str:
        """Determine event type from title, description, JSON-LD type, and URL"""
        content = f"{title} {description}".lower()
        url_lower = url.lower() if url else ''
        
        # Filter out non-event content based on URL patterns
        non_event_url_patterns = [
            '/article/', '/articles/',  # Articles (like /article/video-kerry-james-marshall)
            '/video/', '/videos/',  # Videos
            '/blog/', '/blogs/',  # Blog posts
            '/news/', '/press/',  # News/press releases
            '/magazine/', '/magazines/',  # Magazine articles
            '/story/', '/stories/',  # Stories
            '/feature/', '/features/',  # Features
            '/essay/', '/essays/',  # Essays
            '/interview/', '/interviews/',  # Interviews
            '/podcast/', '/podcasts/',  # Podcasts
            '/collection/', '/collections/',  # Collection items (not events)
            '/artwork/', '/artworks/',  # Artwork pages
            '/artist/', '/artists/',  # Artist pages (unless it's an artist talk event)
        ]
        
        # If URL matches non-event patterns, don't classify as tour
        for pattern in non_event_url_patterns:
            if pattern in url_lower:
                # These are content pages, not events - return None or 'event' but not 'tour'
                # Check if it might still be an event (e.g., artist talk event page)
                if 'talk' in content or 'lecture' in content or 'event' in content:
                    # Might be an event page, but not a tour
                    if 'tour' not in content:
                        if 'talk' in content or 'lecture' in content:
                            return 'talk'
                        return 'event'
                # Otherwise, it's probably not an event at all
                return None  # Signal that this shouldn't be treated as an event
        
        if 'exhibition' in content or 'exhibit' in content or 'ExhibitionEvent' in json_type:
            return 'exhibition'
        elif 'tour' in content or 'guided' in content:
            # Only classify as tour if it's clearly a tour (not just containing the word "tour")
            # Check for specific tour indicators
            tour_indicators = ['guided tour', 'docent tour', 'highlights tour', 'collection tour', 
                             'gallery tour', 'walking tour', 'tour of', 'tour at', 'tour on',
                             'public tour', 'private tour', 'group tour']
            if any(indicator in content for indicator in tour_indicators):
                return 'tour'
            # If URL has /tour/ or /tours/, it's likely a tour (but not /article/ or /video/)
            if ('/tour/' in url_lower or '/tours/' in url_lower) and '/article/' not in url_lower and '/video/' not in url_lower:
                return 'tour'
            # Otherwise, don't assume it's a tour just because "tour" appears in the text
            # Fall through to check other event types
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
        
        # Must have a valid title (pass URL if available)
        url = event.get('url', '')
        if not self._is_valid_event_title(title, url if url else None):
            return False
        
        # Must have at least one of: date, URL, description, or valid title
        has_date = event.get('start_date') is not None
        url = event.get('url', '')
        has_url = bool(url and len(url) > 10)
        description = event.get('description', '')
        has_description = description and len(description.strip()) >= 15  # Reduced from 20
        has_good_title = title and len(title.strip()) >= 10  # Title with some substance
        
        if not (has_date or has_url or has_description or has_good_title):
            return False
        
        # Filter out events with URLs that are clearly not event pages
        if url:
            url_lower = url.lower()
            invalid_url_patterns = [
                'javascript:', 'mailto:', 'tel:',
                '#',  # Anchor links only
            ]
            
            # Check if URL is just an anchor or invalid protocol
            for pattern in invalid_url_patterns:
                if url_lower.startswith(pattern):
                    logger.debug(f"   ⏭️  Skipping event with invalid URL pattern: {url}")
                    return False
            
            # Filter out non-event content URLs (articles, videos, blogs, etc.)
            non_event_url_patterns = [
                '/article/', '/articles/',  # Articles (like /article/video-kerry-james-marshall)
                '/video/', '/videos/',  # Videos
                '/blog/', '/blogs/',  # Blog posts
                '/news/', '/press/',  # News/press releases
                '/magazine/', '/magazines/',  # Magazine articles
                '/story/', '/stories/',  # Stories
                '/feature/', '/features/',  # Features
                '/essay/', '/essays/',  # Essays
                '/interview/', '/interviews/',  # Interviews
                '/podcast/', '/podcasts/',  # Podcasts
            ]
            
            for pattern in non_event_url_patterns:
                if pattern in url_lower:
                    logger.debug(f"   ⏭️  Skipping non-event content URL: {url}")
                    return False
            
            # If URL is just the base domain or homepage, it's probably not a real event page
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            if not path or path in ['', 'index', 'home', 'index.html', 'home.html']:
                # Allow if it's an exhibition/event listing page (no specific event)
                if not any(keyword in url_lower for keyword in ['/exhibitions', '/events', '/programs', '/calendar']):
                    logger.debug(f"   ⏭️  Skipping event with homepage URL: {url}")
                    return False
            
            # Validate URL is likely an event page (not a general info page)
            if not self._is_likely_event_page(url, title):
                logger.debug(f"   ⏭️  Skipping event with non-event page URL: {url}")
                return False
            
            # Reject calendar listing pages without specific event identifiers
            if '/calendar' in url_lower or '/event/' in url_lower or '/events/' in url_lower:
                # Allow if it has an event ID or slug (e.g., /events/specific-event-name)
                if not re.search(r'/events?/[^/]+$', url_lower) and not re.search(r'event[_-]?id=', url_lower):
                    # Might be a listing page, but allow if it has a date
                    if not has_date:
                        logger.debug(f"   ⏭️  Skipping calendar listing page without date: {url}")
                        return False
        
        # Additional validation: Events should have meaningful content
        # If it's just a title with no other info, it's probably not a real event
        if not has_date and not has_description and not has_url:
            logger.debug(f"   ⏭️  Skipping event with only title, no other info: {title[:50]}")
            return False
        
        # CRITICAL: Tours and talks must have a start time - if they don't, they're probably not actually tours/talks
        event_type = event.get('event_type', '').lower()
        if event_type in ['tour', 'talk']:
            start_time = event.get('start_time')
            if not start_time or start_time == 'None' or (isinstance(start_time, str) and start_time.strip() == ''):
                logger.debug(f"   ⏭️  Skipping {event_type} without start time: {title[:50]}")
                return False
        
        # Filter out non-event content (articles, videos, etc.) - these return None as event_type
        if event.get('event_type') is None:
            logger.debug(f"   ⏭️  Skipping non-event content: {title[:50]} (URL: {url[:60] if url else 'N/A'})")
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
            # Normalize title for comparison (lowercase, remove extra spaces)
            title_normalized = re.sub(r'\s+', ' ', title.lower().strip()) if title else ''
            
            # Key 1: normalized title + date (most common)
            key1 = (title_normalized, start_date)
            
            # Key 2: URL + date (for events with unique URLs)
            key2 = (url, start_date) if url and url != event.get('source_url', '') and len(url) > 20 else None
            
            # Key 3: normalized title + URL (for recurring events)
            key3 = (title_normalized, url) if url and url != event.get('source_url', '') and len(url) > 20 else None
            
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
                    # Pattern 2: MoPOP-style "Open now through [Date]" or "Opens [Date]"
                    # Look for "Open now through" or "Open through" patterns
                    open_through_match = re.search(
                        r'(?:Open\s+now\s+through|Open\s+through)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                        parent_text,
                        re.IGNORECASE
                    )
                    if open_through_match:
                        date_text = open_through_match.group(0)  # "Open now through November 10, 2025"
                        # Title might be the link text or heading before this
                        title = link_text if link_text and len(link_text) > 5 else None
                        if not title:
                            # Look for heading before the date text
                            text_before_date = parent_text[:open_through_match.start()].strip()
                            title_parts = text_before_date.split('\n')
                            for part in reversed(title_parts):
                                part = part.strip()
                                if part and len(part) > 5 and self._is_valid_event_title(part, None):
                                    title = part
                                    break
                    
                    # Pattern 3: "Opens [Date]" (start date only)
                    if not date_text:
                        opens_match = re.search(
                            r'Opens\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                            parent_text,
                            re.IGNORECASE
                        )
                        if opens_match:
                            date_text = opens_match.group(0)  # "Opens March 4, 2017"
                            title = link_text if link_text and len(link_text) > 5 else None
                            if not title:
                                text_before_date = parent_text[:opens_match.start()].strip()
                                title_parts = text_before_date.split('\n')
                                for part in reversed(title_parts):
                                    part = part.strip()
                                    if part and len(part) > 5 and self._is_valid_event_title(part, None):
                                        title = part
                                        break
                    
                    # Pattern 4: Title on one line, date range on next line or nearby
                    if not date_text:
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
                                    # URL not available yet at this point, so pass None
                                    if part and len(part) > 5 and self._is_valid_event_title(part, None):
                                        title = part
                                        break
                
                # Fallback: use link text as title if we have a date
                if not title and link_text and len(link_text) > 5:
                    title = link_text
                
                # Build full URL first (needed for validation)
                from urllib.parse import urljoin
                full_url = urljoin(base_url, href)
                
                # If we still don't have a title, try to extract from the URL slug
                if not title or not self._is_valid_event_title(title, full_url):
                    # Extract from URL: /exhibitions/yoshitomo-nara-i-dont-want-to-grow-up/ -> "Yoshitomo Nara: I Don't Want to Grow Up"
                    url_slug = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    if url_slug and url_slug != 'exhibitions':
                        # Convert slug to title: replace hyphens with spaces, capitalize words
                        title = ' '.join(word.capitalize() for word in url_slug.replace('-', ' ').split())
                
                # Skip if title is invalid or already seen
                if not title or not self._is_valid_event_title(title, full_url) or title.lower() in seen_titles:
                    continue
                
                seen_titles.add(title.lower())
                
                # Parse dates from date_text
                start_date = None
                end_date = None
                if date_text:
                    # Handle "Open now through [Date]" or just "Through [Date]" pattern
                    open_through_match = re.search(
                        r'(?:Open\s+now\s+through|Open\s+through|Through|through)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                        date_text,
                        re.IGNORECASE
                    )
                    if open_through_match:
                        end_date_str = open_through_match.group(1)
                        end_date = self._parse_single_date_string(end_date_str)
                        # For "through" patterns, set start_date to today if not already set (ongoing exhibition)
                        if end_date and not start_date:
                            from datetime import date
                            start_date = date.today()
                            logger.debug(f"   📅 Extracted 'through' date: {end_date}, set start_date to {start_date}")
                    else:
                        # Handle "Opens [Date]" pattern
                        opens_match = re.search(
                            r'Opens\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                            date_text,
                            re.IGNORECASE
                        )
                        if opens_match:
                            start_date_str = opens_match.group(1)
                            start_date = self._parse_single_date_string(start_date_str)
                            logger.debug(f"   📅 Extracted 'Opens' date: {start_date}")
                        else:
                            # Use the date range parser for standard date ranges
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
                
                # Fetch individual exhibition page to get better dates, description, and image
                # This is important for museums like MoPOP that have dates on the detail page
                if full_url and full_url != base_url:
                    try:
                        logger.debug(f"   🔍 Fetching individual exhibition page for better data: {full_url}")
                        event_response = self._fetch_with_retry(full_url, base_url=base_url)
                        
                        # Validate that the page actually exists (not 404)
                        if not event_response:
                            logger.debug(f"   ⏭️  Skipping: Could not fetch exhibition page (no response): {full_url}")
                            continue
                        
                        if event_response.status_code == 404:
                            logger.debug(f"   ⏭️  Skipping: Exhibition page does not exist (404): {full_url}")
                            continue
                        
                        if event_response.status_code != 200:
                            logger.debug(f"   ⏭️  Skipping: Exhibition page returned status {event_response.status_code}: {full_url}")
                            continue
                        
                        if event_response.status_code == 200:
                            event_soup = BeautifulSoup(event_response.content, 'html.parser')
                            
                            # Extract dates from the exhibition detail page (MoPOP format)
                            # Look for patterns like "Open now through November 10, 2025" or "Opens March 4, 2017"
                            page_text = event_soup.get_text()
                            
                            # Pattern 1: "Open now through [Date]" or "Open through [Date]" or just "Through [Date]"
                            open_through_pattern = r'(?:Open\s+now\s+through|Open\s+through|Through|through)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'
                            open_through_match = re.search(open_through_pattern, page_text, re.IGNORECASE)
                            if open_through_match:
                                end_date_str = open_through_match.group(1)
                                parsed_end_date = self._parse_single_date_string(end_date_str)
                                if parsed_end_date:
                                    end_date = parsed_end_date
                                    # If we don't have a start date, set it to today (ongoing exhibition)
                                    if not start_date:
                                        from datetime import date
                                        start_date = date.today()
                                    logger.debug(f"   📅 Extracted end date from 'through' pattern: {end_date}, set start_date to {start_date}")
                            
                            # Pattern 2: "Opens [Date]" (start date)
                            opens_pattern = r'Opens\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'
                            opens_match = re.search(opens_pattern, page_text, re.IGNORECASE)
                            if opens_match:
                                start_date_str = opens_match.group(1)
                                parsed_start_date = self._parse_single_date_string(start_date_str)
                                if parsed_start_date:
                                    start_date = parsed_start_date
                                    logger.debug(f"   📅 Extracted start date from 'Opens' pattern: {start_date}")
                            
                            # Pattern 3: Date range in various formats on the page
                            # Look for date ranges in the page text
                            if not start_date or not end_date:
                                # First, try to find dates in common HTML structures (Tate format)
                                # Look for "Dates" heading followed by date range
                                dates_heading = event_soup.find(['h2', 'h3', 'dt'], string=re.compile(r'^Dates?$', re.I))
                                if dates_heading:
                                    # Check next sibling (dd, div, p, etc.)
                                    next_sibling = dates_heading.find_next_sibling()
                                    if next_sibling:
                                        date_text = next_sibling.get_text(strip=True)
                                        if date_text:
                                            date_range = self._parse_date_range_string(date_text)
                                            if date_range:
                                                if not start_date:
                                                    start_date = date_range.get('start_date')
                                                if not end_date:
                                                    end_date = date_range.get('end_date')
                                                if start_date or end_date:
                                                    logger.debug(f"   📅 Extracted date range from 'Dates' section: {start_date} to {end_date}")
                                    
                                    # Also check parent's children (for dt/dd structure)
                                    if (not start_date or not end_date) and dates_heading.parent:
                                        for sibling in dates_heading.parent.find_all(['dd', 'div', 'p', 'span']):
                                            date_text = sibling.get_text(strip=True)
                                            if date_text and re.search(r'\d{1,2}\s+[A-Z][a-z]+\s+\d{4}', date_text):
                                                date_range = self._parse_date_range_string(date_text)
                                                if date_range:
                                                    if not start_date:
                                                        start_date = date_range.get('start_date')
                                                    if not end_date:
                                                        end_date = date_range.get('end_date')
                                                    if start_date or end_date:
                                                        logger.debug(f"   📅 Extracted date range from 'Dates' sibling: {start_date} to {end_date}")
                                                        break
                                
                                # Try to find date elements with common selectors
                                if not start_date or not end_date:
                                    date_elements = event_soup.find_all(['time', 'span', 'div', 'p'], 
                                                                        class_=re.compile(r'date|duration|period|on-view', re.I))
                                    for date_elem in date_elements:
                                        date_text = date_elem.get_text(strip=True)
                                        if date_text:
                                            # Try "through" pattern (handles "Through January 10, 2027" or "through January 10, 2027")
                                            through_match = re.search(r'(?:through|Through|until|Until)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', date_text, re.I)
                                            if through_match and not end_date:
                                                end_date_str = through_match.group(1)
                                                parsed_end_date = self._parse_single_date_string(end_date_str)
                                                if parsed_end_date:
                                                    end_date = parsed_end_date
                                                    # If we don't have a start date, set it to today (ongoing exhibition)
                                                    if not start_date:
                                                        from datetime import date
                                                        start_date = date.today()
                                                    logger.debug(f"   📅 Extracted end date from 'through' pattern in date element: {end_date}, set start_date to {start_date}")
                                                    break
                                            
                                            # Try date range (handles both "Month Day, Year" and "Day Month Year" formats)
                                            if not start_date or not end_date:
                                                date_range = self._parse_date_range_string(date_text)
                                                if date_range:
                                                    if not start_date:
                                                        start_date = date_range.get('start_date')
                                                    if not end_date:
                                                        end_date = date_range.get('end_date')
                                                    if start_date or end_date:
                                                        logger.debug(f"   📅 Extracted date range from date element: {start_date} to {end_date}")
                                                        break
                                
                                # Also search the full page text for date ranges and "through" patterns
                                if not start_date or not end_date:
                                    # First, try standalone "Through [Date]" pattern (e.g., "Through January 10, 2027")
                                    standalone_through_pattern = r'(?:^|\s)(?:Through|through)\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})'
                                    standalone_through_match = re.search(standalone_through_pattern, page_text, re.IGNORECASE | re.MULTILINE)
                                    if standalone_through_match and not end_date:
                                        end_date_str = standalone_through_match.group(1)
                                        parsed_end_date = self._parse_single_date_string(end_date_str)
                                        if parsed_end_date:
                                            end_date = parsed_end_date
                                            if not start_date:
                                                from datetime import date
                                                start_date = date.today()
                                            logger.debug(f"   📅 Extracted end date from standalone 'Through' pattern: {end_date}, set start_date to {start_date}")
                                    
                                    # Look for British format: "Day Month Year – Day Month Year"
                                    if not start_date or not end_date:
                                        british_date_range_pattern = r'(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})\s*[–—\-]\s*(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})'
                                        british_match = re.search(british_date_range_pattern, page_text, re.IGNORECASE)
                                        if british_match:
                                            try:
                                                start_day = int(british_match.group(1))
                                                start_month_name = british_match.group(2).lower()
                                                start_year = int(british_match.group(3))
                                                end_day = int(british_match.group(4))
                                                end_month_name = british_match.group(5).lower()
                                                end_year = int(british_match.group(6))
                                                
                                                start_month = self._month_name_to_num(start_month_name)
                                                end_month = self._month_name_to_num(end_month_name)
                                                
                                                if start_month and end_month:
                                                    from datetime import date
                                                    parsed_start = date(start_year, start_month, start_day)
                                                    parsed_end = date(end_year, end_month, end_day)
                                                    
                                                    if not start_date:
                                                        start_date = parsed_start
                                                    if not end_date:
                                                        end_date = parsed_end
                                                    logger.debug(f"   📅 Extracted British format date range: {start_date} to {end_date}")
                                            except (ValueError, IndexError) as e:
                                                logger.debug(f"Error parsing British date format: {e}")
                                        try:
                                            start_day = int(british_match.group(1))
                                            start_month_name = british_match.group(2).lower()
                                            start_year = int(british_match.group(3))
                                            end_day = int(british_match.group(4))
                                            end_month_name = british_match.group(5).lower()
                                            end_year = int(british_match.group(6))
                                            
                                            start_month = self._month_name_to_num(start_month_name)
                                            end_month = self._month_name_to_num(end_month_name)
                                            
                                            if start_month and end_month:
                                                from datetime import date
                                                parsed_start = date(start_year, start_month, start_day)
                                                parsed_end = date(end_year, end_month, end_day)
                                                
                                                if not start_date:
                                                    start_date = parsed_start
                                                if not end_date:
                                                    end_date = parsed_end
                                                logger.debug(f"   📅 Extracted British format date range: {start_date} to {end_date}")
                                        except (ValueError, IndexError) as e:
                                            logger.debug(f"Error parsing British date format: {e}")
                                
                                # Also check for dates in structured data (JSON-LD)
                                if not start_date or not end_date:
                                    json_ld_scripts = event_soup.find_all('script', type='application/ld+json')
                                    for script in json_ld_scripts:
                                        try:
                                            script_content = script.string if script.string else script.get_text()
                                            data = json.loads(script_content)
                                            items = data if isinstance(data, list) else [data]
                                            for item in items:
                                                if item.get('@type') in ['Event', 'ExhibitionEvent']:
                                                    if 'startDate' in item and not start_date:
                                                        start_datetime = self._parse_iso_datetime(item['startDate'])
                                                        if start_datetime:
                                                            start_date = start_datetime.date()
                                                    if 'endDate' in item and not end_date:
                                                        end_datetime = self._parse_iso_datetime(item['endDate'])
                                                        if end_datetime:
                                                            end_date = end_datetime.date()
                                                    if start_date or end_date:
                                                        logger.debug(f"   📅 Extracted dates from JSON-LD: {start_date} to {end_date}")
                                                        break
                                        except (json.JSONDecodeError, KeyError):
                                            continue
                            
                            # Extract better description from detail page
                            if not description or len(description) < 100:
                                # Look for main content area
                                main_content = event_soup.find('main') or event_soup.find('article') or event_soup.find('div', class_=re.compile(r'content|main|exhibition', re.I))
                                if main_content:
                                    # Get first substantial paragraph
                                    paragraphs = main_content.find_all('p')
                                    for p in paragraphs:
                                        p_text = p.get_text(strip=True)
                                        # Skip if it's just a date or very short
                                        if len(p_text) > 100 and not re.match(r'^[A-Z][a-z]+\s+\d{1,2}', p_text):
                                            description = p_text[:500]
                                            break
                            
                            # Extract image from detail page if not found on listing
                            if not image_url:
                                image_url = self._extract_image(event_soup, base_url)
                                if image_url:
                                    logger.debug(f"   ✅ Found image from exhibition page: {image_url[:80]}")
                    except Exception as e:
                        logger.debug(f"   ⚠️  Error fetching exhibition page: {e}")
                
                # Final validation: Only create event if we have valid data
                # Skip if URL doesn't exist (we should have checked above, but double-check)
                if not title or len(title.strip()) < 3:
                    logger.debug(f"   ⏭️  Skipping: Invalid title: {title}")
                    continue
                
                # Validate the event before adding
                event_dict = {
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
                }
                
                # Validate event before adding
                if self._is_valid_generic_event(event_dict):
                    events.append(event_dict)
                else:
                    logger.debug(f"   ⏭️  Skipping: Event failed validation: {title[:50]}")
            
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
                
                # Skip if title is too generic (no URL available in this context)
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
                        
                        # Validate that the page actually exists
                        if not event_response or event_response.status_code != 200:
                            if event_response and event_response.status_code == 404:
                                logger.debug(f"   ⏭️  Skipping: Exhibition page does not exist (404): {exhibition_url}")
                            # Don't create event if page doesn't exist
                            continue
                        
                        if event_response.status_code == 200:
                            event_soup = BeautifulSoup(event_response.content, 'html.parser')
                            # Use enhanced image extraction on the full page
                            image_url = self._extract_image(event_soup, base_url)
                            if image_url:
                                logger.debug(f"   ✅ Found image from exhibition page: {image_url[:80]}")
                    except Exception as e:
                        logger.debug(f"   ⚠️  Error fetching exhibition page for image: {e}")
                
                # Final validation before creating event
                if not title or len(title.strip()) < 3:
                    logger.debug(f"   ⏭️  Skipping: Invalid title: {title}")
                    continue
                
                event_dict = {
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
                }
                
                # Validate event before adding
                if self._is_valid_generic_event(event_dict):
                    events.append(event_dict)
                else:
                    logger.debug(f"   ⏭️  Skipping: Event failed validation: {title[:50]}")
            
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
        from urllib.parse import urljoin
        import re
        
        events = []
        logger.debug(f"   🔍 _extract_museum_programs: Starting extraction from {base_url}")

        try:
            # Special handling for view/listing containers (e.g., Drupal Views, WordPress event lists)
            # Look for containers with classes like 'view-events', 'events-list', etc.
            view_containers = soup.select('.view-events, .events-list, .programs-list, [class*="view-events"], [class*="events-list"]')
            logger.info(f"   Found {len(view_containers)} view containers")
            for container in view_containers:
                # Find all links to individual event pages inside the container
                event_links = container.find_all('a', href=True)
                logger.debug(f"   Found {len(event_links)} links in view container")
                for link in event_links:
                    try:
                        href = link.get('href', '')
                        link_text = link.get_text(strip=True)
                        
                        # Skip if text is too short or empty
                        if not link_text or len(link_text) < 3:
                            logger.debug(f"   ⏭️  Skipping link: text too short or empty (href: {href[:50]})")
                            continue
                        
                        # Check if this looks like an event page link OR if it has meaningful text (might be a listing link)
                        # For view containers, we want to process links that have dates in the text, even if href doesn't match patterns
                        has_event_pattern = any(pattern in href.lower() for pattern in ['/events/', '/event/', '/programs/', '/program/'])
                        has_date_in_text = bool(re.search(r'[A-Z][a-z]+\s+\d{1,2}', link_text))  # Check for date pattern in text
                        
                        if has_event_pattern or has_date_in_text:
                            logger.debug(f"   🔍 Processing link: {link_text[:80]} (href: {href[:60]})")
                            
                            # Extract title and date from link text (handle messy formats like "ToursCollections Highlights TourDecember 8, 2025")
                            # Try to extract date from the end of the text
                            title = link_text
                            start_date = None
                            end_date = None
                            
                            # First, try to extract date range (e.g., "Nov 28 – Dec 31" or "November 28 – December 31")
                            # Look for date ranges anywhere in the string (not just at the end)
                            date_range_pattern = r'([A-Z][a-z]+\s+\d{1,2}(?:,\s+\d{4})?)\s*[–—\-]\s*([A-Z][a-z]+\s+\d{1,2}(?:,\s+\d{4})?)(?:\s*\|.*)?'
                            date_range_match = re.search(date_range_pattern, link_text)
                            
                            if date_range_match:
                                # Found a date range
                                start_str = date_range_match.group(1).strip()
                                end_str = date_range_match.group(2).strip()
                                start_date = self._parse_single_date_string(start_str)
                                end_date = self._parse_single_date_string(end_str)
                                # Remove date range and anything after it (like time) from title
                                title = re.sub(date_range_pattern + r'.*', '', title).strip()
                                if start_date and end_date:
                                    logger.debug(f"   📅 Extracted date range from link text: {start_date} to {end_date}")
                            else:
                                # Try single date patterns - handle dates anywhere in the string (not just at end)
                                # Dates can be followed by time info like "| 3–5 p.m."
                                date_patterns = [
                                # Date with year, possibly followed by time: "December 11, 2025 | 3–5 p.m."
                                r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})(?:\s*\|.*)?',
                                # Concatenated date with year: "TourDecember 8, 2025 | ..."
                                r'([A-Z][a-z]+)([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})(?:\s*\|.*)?',
                                # Date without year: "December 8 | ..."
                                r'([A-Z][a-z]+\s+\d{1,2})(?:\s*\|.*)?',
                                # Concatenated date without year: "TourDecember 8 | ..."
                                r'([A-Z][a-z]+)([A-Z][a-z]+\s+\d{1,2})(?:\s*\|.*)?',
                            ]
                            
                            date_match = None
                            for pattern in date_patterns:
                                date_match = re.search(pattern, link_text)
                                if date_match:
                                    # If pattern has 2 groups, the date is in group 2
                                    if len(date_match.groups()) == 2:
                                        date_str = date_match.group(2).replace(',', '').strip()
                                        # Remove the date and everything after it from title
                                        title = re.sub(pattern, r'\1', title).strip()
                                    else:
                                        date_str = date_match.group(1).replace(',', '').strip()
                                        # Remove date and everything after it from title
                                        title = re.sub(pattern, '', title).strip()
                                    break
                            
                            if date_match:
                                start_date = self._parse_single_date_string(date_str)
                                if start_date:
                                    logger.debug(f"   📅 Extracted date from link text: {start_date}")
                            
                            # Clean up title - remove event type prefixes like "Tours", "Talks", "Family", "Art Making", etc.
                            title = re.sub(r'^(Tours|Talks|Workshops|Lectures|Programs|Events|Family|Art Making|Members)\s*', '', title, flags=re.IGNORECASE).strip()
                            
                            # Remove date/time suffixes that got concatenated (e.g., "TitleDecember 13, 2025 | 10 a.m.–1 p.m.")
                            # Pattern: Month Day, Year | Time
                            title = re.sub(r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\s*\|\s*[\d\s:apm–-]+$', '', title, flags=re.IGNORECASE).strip()
                            # Pattern: Just date at end
                            title = re.sub(r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})$', '', title, flags=re.IGNORECASE).strip()
                            
                            # Validate title
                            full_url = urljoin(base_url, href)
                            if not self._is_valid_event_title(title, full_url):
                                logger.debug(f"   ⏭️  Skipping: invalid title '{title[:50]}'")
                                continue
                            
                            # Check time range filter
                            if start_date and not self._is_in_time_range(start_date, time_range):
                                logger.debug(f"   ⏭️  Skipping: date {start_date} not in {time_range}")
                                continue
                            
                            # Detect if family/kid-friendly
                            is_family_friendly = self._detect_family_friendly(title, '', link)
                            
                            # Extract image from listing page - search thoroughly
                            image_url = None
                            
                            # Strategy 1: Look in the link element itself
                            image_url = self._extract_image(link, base_url)
                            
                            # Strategy 2: Look in parent container
                            if not image_url and link.parent:
                                image_url = self._extract_image(link.parent, base_url)
                            
                            # Strategy 3: Look at siblings (common pattern: image and event info are siblings)
                            if not image_url and link.parent:
                                # Check previous sibling
                                prev_sibling = link.parent.previous_sibling
                                count = 0
                                while prev_sibling and not image_url and count < 5:  # Limit to 5 siblings
                                    if hasattr(prev_sibling, 'find'):
                                        image_url = self._extract_image(prev_sibling, base_url)
                                    prev_sibling = prev_sibling.previous_sibling if hasattr(prev_sibling, 'previous_sibling') else None
                                    count += 1
                                
                                # Check next sibling
                                if not image_url:
                                    next_sibling = link.parent.next_sibling
                                    count = 0
                                    while next_sibling and not image_url and count < 5:  # Limit to 5 siblings
                                        if hasattr(next_sibling, 'find'):
                                            image_url = self._extract_image(next_sibling, base_url)
                                        next_sibling = next_sibling.next_sibling if hasattr(next_sibling, 'next_sibling') else None
                                        count += 1
                            
                            # Strategy 3b: Look in grandparent and other ancestors (sometimes image is in a wrapper)
                            if not image_url and link.parent and hasattr(link.parent, 'parent'):
                                grandparent = link.parent.parent
                                if grandparent:
                                    image_url = self._extract_image(grandparent, base_url)
                            
                            # Strategy 4: Look in the container itself (view container)
                            if not image_url and container:
                                image_url = self._extract_image(container, base_url)
                            
                            # Strategy 4b: Look for images in the same row/item as the link (common in grid layouts)
                            if not image_url and link.parent:
                                # Try to find a common ancestor that might contain both link and image
                                ancestor = link.parent
                                for _ in range(3):  # Check up to 3 levels up
                                    if ancestor and hasattr(ancestor, 'find_all'):
                                        # Look for images in this ancestor that aren't in nav/footer
                                        imgs = ancestor.find_all('img')
                                        for img in imgs:
                                            img_src = (img.get('src') or img.get('data-src') or 
                                                      img.get('data-lazy-src') or img.get('data-original'))
                                            if img_src:
                                                src_lower = img_src.lower()
                                                # Skip icons/logos
                                                if any(skip in src_lower for skip in ['icon', 'logo', 'favicon', 'avatar', 'social']):
                                                    continue
                                                # Check if it's a real image
                                                if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                                    image_url = urljoin(base_url, img_src)
                                                    break
                                    if image_url:
                                        break
                                    if ancestor and hasattr(ancestor, 'parent'):
                                        ancestor = ancestor.parent
                                    else:
                                        break
                            
                            if image_url:
                                logger.info(f"   🖼️  Found image from listing page: {image_url[:80]}")
                            else:
                                logger.debug(f"   ⚠️  No image found on listing page for: {title[:50]}")
                            
                            # Strategy 5: If no image found on listing page, try event page as fallback
                            if not image_url and full_url and full_url != base_url:
                                try:
                                    logger.debug(f"   🖼️  No image on listing page, trying event page: {full_url}")
                                    event_response = self._fetch_with_retry(full_url, base_url=base_url)
                                    if event_response and event_response.status_code == 200:
                                        event_soup = BeautifulSoup(event_response.content, 'html.parser')
                                        image_url = self._extract_image(event_soup, base_url)
                                        if image_url:
                                            logger.info(f"   ✅ Found image from event page: {image_url[:80]}")
                                        else:
                                            logger.debug(f"   ⚠️  No image found on event page either: {full_url[:60]}")
                                except Exception as e:
                                    logger.debug(f"   ⚠️  Error fetching event page for image: {e}")
                            
                            # Create event dict
                            event = {
                                'title': title,
                                'url': full_url,
                                'start_date': start_date.isoformat() if start_date else None,
                                'end_date': end_date.isoformat() if end_date else None,
                                'event_type': self._detect_museum_event_type(title, '', link, full_url),
                                'is_family_friendly': is_family_friendly,
                                'image_url': image_url  # Add image URL
                            }
                            
                            if is_family_friendly:
                                logger.debug(f"   👶 Family-friendly event detected: {title[:50]}")
                            
                            events.append(event)
                            logger.info(f"   ✅ Extracted event from view container: '{title[:50]}' (date: {start_date}, url: {full_url[:60]})")
                        else:
                            logger.debug(f"   ⏭️  Skipping link: no event pattern in href and no date in text (href: {href[:50]}, text: {link_text[:50]})")
                            continue
                    except Exception as link_error:
                        logger.debug(f"   ⚠️  Error processing link: {link_error}")
                        continue  # Continue with next link
            
            logger.info(f"   📊 _extract_museum_programs: Extracted {len(events)} events from view containers")

            # Use museum-specific selectors first
            for selector in self.museum_event_selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} elements with museum selector: {selector}")

                        for element in elements:
                            # Skip if this is a view container (already processed above)
                            if any(cls in ' '.join(element.get('class', [])).lower() for cls in ['view-events', 'events-list', 'programs-list']):
                                continue
                                
                            if self._should_skip_element(element):
                                continue

                            event = self._parse_event_element(element, base_url, venue_name, event_type, time_range)
                            if event:
                                # Skip shopping events
                                if self._is_shopping_event(
                                    event.get('title', ''),
                                    event.get('description', ''),
                                    event.get('url', '')
                                ):
                                    logger.debug(f"   🛍️  Skipping shopping event: {event.get('title', 'N/A')[:50]}")
                                    continue
                                
                                # Enhance event type detection for museum programs
                                if not event.get('event_type'):
                                    event['event_type'] = self._detect_museum_event_type(
                                        event.get('title', ''),
                                        event.get('description', ''),
                                        element,
                                        event.get('url', '')
                                    )
                                    # Filter out events that are actually articles/videos
                                    if event.get('event_type') is None:
                                        logger.debug(f"   ⏭️  Skipping non-event content: {event.get('title', 'N/A')[:50]}")
                                        continue
                                # Detect if family/kid-friendly
                                event['is_family_friendly'] = self._detect_family_friendly(
                                    event.get('title', ''),
                                    event.get('description', ''),
                                    element
                                )
                                if event.get('is_family_friendly'):
                                    logger.debug(f"   👶 Family-friendly event detected: {event.get('title', 'N/A')[:50]}")
                                events.append(event)
                except Exception as e:
                    logger.debug(f"Error with museum selector {selector}: {e}")
                    continue

            # Also extract from JSON-LD for museum events
            json_ld_events = self._extract_json_ld_events(soup, base_url)
            for event in json_ld_events:
                # Skip shopping events
                if self._is_shopping_event(
                    event.get('title', ''),
                    event.get('description', ''),
                    event.get('url', '')
                ):
                    logger.debug(f"   🛍️  Skipping shopping event from JSON-LD: {event.get('title', 'N/A')[:50]}")
                    continue
                
                if not event.get('event_type'):
                    event['event_type'] = self._detect_museum_event_type(
                        event.get('title', ''),
                        event.get('description', ''),
                        None,
                        event.get('url', '')
                    )
                    # Filter out events that are actually articles/videos
                    if event.get('event_type') is None:
                        logger.debug(f"   ⏭️  Skipping non-event content from JSON-LD: {event.get('title', 'N/A')[:50]}")
                        continue
                # Detect if family/kid-friendly
                event['is_family_friendly'] = self._detect_family_friendly(
                    event.get('title', ''),
                    event.get('description', ''),
                    None
                )
            events.extend(json_ld_events)

        except Exception as e:
            logger.debug(f"Error extracting museum programs: {e}")

        return events
    
    def _detect_museum_event_type(self, title: str, description: str, element=None, url: str = '') -> str:
        """Detect museum-specific event types"""
        content = (title + ' ' + description).lower()
        url_lower = url.lower() if url else ''
        
        # Filter out non-event content based on URL patterns
        non_event_url_patterns = [
            '/article/', '/articles/',  # Articles (like /article/video-kerry-james-marshall)
            '/video/', '/videos/',  # Videos
            '/blog/', '/blogs/',  # Blog posts
            '/news/', '/press/',  # News/press releases
            '/magazine/', '/magazines/',  # Magazine articles
            '/story/', '/stories/',  # Stories
            '/feature/', '/features/',  # Features
            '/essay/', '/essays/',  # Essays
            '/interview/', '/interviews/',  # Interviews
            '/podcast/', '/podcasts/',  # Podcasts
            '/collection/', '/collections/',  # Collection items (not events)
            '/artwork/', '/artworks/',  # Artwork pages
            '/artist/', '/artists/',  # Artist pages (unless it's an artist talk event)
        ]
        
        # If URL matches non-event patterns, don't classify as tour or any event type
        for pattern in non_event_url_patterns:
            if pattern in url_lower:
                # These are content pages, not events
                # Only allow if it's clearly an event (e.g., artist talk event page)
                if 'talk' in content or 'lecture' in content or 'event' in content:
                    if 'talk' in content or 'lecture' in content:
                        return 'talk'
                    return 'event'
                # Otherwise, return None to signal this shouldn't be an event
                return None
        
        # Museum-specific patterns
        if any(keyword in content for keyword in ['gallery talk', 'curator talk', 'curator\'s talk']):
            return 'talk'
        elif any(keyword in content for keyword in ['artist talk', 'artist conversation', 'artist discussion']):
            return 'talk'
        elif any(keyword in content for keyword in ['panel discussion', 'symposium', 'conference']):
            return 'talk'
        elif any(keyword in content for keyword in ['docent tour', 'guided tour', 'highlights tour', 'collection tour']):
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
    
    def _is_shopping_event(self, title: str, description: str = '', url: str = '') -> bool:
        """Detect if an event is shopping-related and should be excluded"""
        combined_text = f"{title.lower()} {description.lower()} {url.lower()}"
        
        # Keywords that indicate shopping events
        shopping_keywords = [
            'pop-up', 'popup', 'pop up',
            'shopping', 'retail', 'store', 'boutique',
            'sale', 'discount', 'clearance',
            'lingerie', 'fashion', 'clothing', 'apparel',
            'holiday shopping', 'shopping event', 'shopping day',
            'market', 'vendor', 'merchant',
            'exclusive shopping', 'private shopping',
            'trunk show', 'sample sale'
        ]
        
        if any(keyword in combined_text for keyword in shopping_keywords):
            return True
        
        return False
    
    def _detect_family_friendly(self, title: str, description: str = '', element=None) -> bool:
        """Detect if an event is family/kid/baby-friendly"""
        combined_text = f"{title.lower()} {description.lower()}"
        
        # Keywords that indicate family/kid/baby-friendly events
        family_keywords = [
            # Baby/toddler specific
            'baby', 'babies', 'toddler', 'toddlers', 'infant', 'infants',
            'ages 0-2', 'ages 0–2', 'ages 0 to 2', '0-2 years', '0–2 years',
            'ages 0-3', 'ages 0–3', 'ages 0 to 3', '0-3 years', '0–3 years',
            'bring your own baby', 'byob', 'baby-friendly', 'baby friendly',
            'stroller', 'strollers', 'nursing', 'breastfeeding',
            # Family general
            'family', 'families', 'family program', 'family day', 'family-friendly', 'family friendly',
            'for families', 'with families', 'family event', 'family activities',
            # Kids/children
            'kids', 'children', 'child', 'little ones', 'young families',
            'kids program', 'children\'s program', 'children program',
            'art & play', 'art and play', 'play time', 'playtime',
            'story time', 'storytime', 'story hour',
            # Age ranges that include young children
            'ages 2-5', 'ages 3-5', 'ages 4-8', 'ages 5-10', 'all ages',
            'preschool', 'pre-school', 'elementary', 'young children'
        ]
        
        if any(keyword in combined_text for keyword in family_keywords):
            return True
        
        # Check element classes if available
        if element:
            classes = ' '.join(element.get('class', []))
            class_lower = classes.lower()
            if any(keyword in class_lower for keyword in ['family', 'kids', 'children', 'baby', 'toddler']):
                return True
        
        return False



