#!/usr/bin/env python3
"""
Source Event Scraper
Scrapes events from event sources (websites, Instagram pages, etc.)
"""

import os
import sys
import requests
import logging
import json
import re
from datetime import datetime, timedelta, date, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Source, Event, City

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceEventScraper:
    """Scrapes events from various event sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.scraped_events = []
    
    def scrape_source_events(self, source_ids=None, city_id=None, event_type=None, time_range=None):
        """Scrape events from selected sources
        
        Args:
            source_ids: List of source IDs to scrape
            city_id: City ID to scrape sources from
            event_type: Type of events to scrape
            time_range: Time range for events
        """
        try:
            with app.app_context():
                # Get sources to scrape
                if source_ids:
                    sources = Source.query.filter(Source.id.in_(source_ids)).all()
                elif city_id:
                    sources = Source.query.filter_by(city_id=city_id).all()
                else:
                    sources = Source.query.limit(10).all()
                
                logger.info(f"Scraping events from {len(sources)} sources")
                
                # Track unique events to prevent duplicates
                unique_events = set()
                
                for source in sources:
                    try:
                        logger.info(f"Scraping events from: {source.name}")
                        
                        # Only scrape website sources for now
                        if source.source_type == 'website':
                            events = self._scrape_website_source(source)
                        elif source.source_type == 'instagram':
                            events = self._scrape_instagram_source(source)
                        else:
                            logger.info(f"Source type '{source.source_type}' not yet supported for {source.name}")
                            events = []
                        
                        # Add unique events only with better deduplication
                        for event in events:
                            # Create a more comprehensive unique key
                            title_clean = event['title'].lower().strip()
                            date_key = event.get('start_time', '')[:10] if event.get('start_time') else ''
                            source_key = f"{source.name}_{source.id}"
                            event_key = f"{title_clean}_{date_key}_{source_key}"
                            
                            if event_key not in unique_events:
                                unique_events.add(event_key)
                                self.scraped_events.append(event)
                                logger.debug(f"✅ Added unique event: {event['title']}")
                            else:
                                logger.debug(f"⚠️ Skipped duplicate event: {event['title']}")
                        
                        # Rate limiting
                        import time
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error scraping {source.name}: {e}")
                        continue
                
                logger.info(f"Total unique events scraped from sources: {len(self.scraped_events)}")
                return self.scraped_events
                
        except Exception as e:
            logger.error(f"Error in scrape_source_events: {e}")
            return []
    
    def _scrape_website_source(self, source):
        """Scrape events from a website source"""
        events = []
        
        if not source.url:
            return events
        
        try:
            logger.info(f"Scraping website: {source.url}")
            response = self.session.get(source.url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract events based on common patterns
            events = self._extract_events_from_html(soup, source)
            
        except Exception as e:
            logger.error(f"Error scraping website {source.url}: {e}")
        
        return events
    
    def _scrape_instagram_source(self, source):
        """Scrape events from an Instagram source"""
        events = []
        
        if not source.url and not source.handle:
            logger.warning(f"No URL or handle for Instagram source: {source.name}")
            return events
        
        try:
            # Check if this is an individual post URL
            if source.url and ('/p/' in source.url or '/reel/' in source.url):
                # Scrape individual post
                logger.info(f"📱 Scraping individual Instagram post: {source.url}")
                post_data = self._scrape_instagram_post_page(source.url, source)
                if post_data:
                    event_data = self._parse_instagram_post_as_event(post_data, source)
                    if event_data:
                        events.append(event_data)
                return events
            
            # Extract username from handle or URL
            username = None
            if source.handle:
                username = source.handle.replace('@', '').strip()
            elif source.url:
                match = re.search(r'instagram\.com/([^/?]+)', source.url)
                if match:
                    username = match.group(1)
            
            if not username:
                logger.warning(f"Could not extract username from source: {source.name}")
                return events
            
            logger.info(f"📱 Scraping Instagram: @{username}")
            
            # Import Instagram scraping function
            from scripts.source_scraper import scrape_instagram_info
            from scripts.source_scraper import get_resource_limits, is_railway_environment
            
            # Get environment limits
            limits = get_resource_limits()
            
            # Scrape Instagram profile page
            url = f"https://www.instagram.com/{username}/"
            
            # Enhanced headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Referer': 'https://www.instagram.com/',
            }
            
            response = self.session.get(url, headers=headers, timeout=limits['request_timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract posts from embedded JSON data
            posts = self._extract_instagram_posts(soup, username, source)
            
            # Process each post to extract events
            for post in posts:
                event_data = self._parse_instagram_post_as_event(post, source)
                if event_data:
                    events.append(event_data)
            
            logger.info(f"   ✅ Found {len(events)} events from {len(posts)} posts")
            
        except Exception as e:
            logger.error(f"Error scraping Instagram source {source.name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return events
    
    def _scrape_instagram_post_page(self, post_url, source):
        """Scrape an individual Instagram post page"""
        try:
            from scripts.source_scraper import get_resource_limits
            
            limits = get_resource_limits()
            
            # Enhanced headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Referer': 'https://www.instagram.com/',
            }
            
            response = self.session.get(post_url, headers=headers, timeout=limits['request_timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract shortcode from URL
            shortcode_match = re.search(r'/p/([^/]+)/', post_url)
            shortcode = shortcode_match.group(1) if shortcode_match else None
            
            # Try to extract post data from embedded JSON
            post_data = None
            
            # Method 1: Look for window._sharedData
            all_scripts = soup.find_all('script')
            for script in all_scripts:
                if not script.string:
                    continue
                
                script_text = script.string
                
                # Look for window._sharedData pattern
                if 'window._sharedData' in script_text:
                    try:
                        match = re.search(r'window\._sharedData\s*=\s*({.+?});', script_text, re.DOTALL)
                        if match:
                            data = json.loads(match.group(1))
                            # Navigate to post data
                            if 'entry_data' in data:
                                post_page = data['entry_data'].get('PostPage', [])
                                if post_page and len(post_page) > 0:
                                    media = post_page[0].get('graphql', {}).get('shortcode_media', {})
                                    if media:
                                        # Extract caption
                                        caption_edges = media.get('edge_media_to_caption', {}).get('edges', [])
                                        caption = caption_edges[0].get('node', {}).get('text', '') if caption_edges else ''
                                        
                                        # Extract image
                                        display_url = media.get('display_url') or media.get('display_src')
                                        
                                        # Extract timestamp
                                        taken_at = media.get('taken_at_timestamp')
                                        
                                        # Extract username
                                        owner = media.get('owner', {})
                                        username = owner.get('username', '')
                                        
                                        post_data = {
                                            'shortcode': shortcode or media.get('shortcode'),
                                            'caption': caption,
                                            'display_url': display_url,
                                            'taken_at_timestamp': taken_at,
                                            'is_video': media.get('is_video', False),
                                            'url': post_url,
                                            'username': username
                                        }
                                        break
                    except (json.JSONDecodeError, KeyError, AttributeError) as e:
                        logger.debug(f"Could not parse Instagram post embedded data: {e}")
                        continue
                
                # Method 2: Look for JSON-LD structured data
                if script.get('type') == 'application/ld+json':
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'ImageObject':
                            # Extract from JSON-LD
                            caption = data.get('caption', '')
                            image_url = data.get('contentUrl') or data.get('url')
                            
                            if caption or image_url:
                                post_data = {
                                    'shortcode': shortcode,
                                    'caption': caption,
                                    'display_url': image_url,
                                    'taken_at_timestamp': None,
                                    'is_video': False,
                                    'url': post_url,
                                    'username': None
                                }
                                break
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # Method 3: Fallback - extract from meta tags and HTML
            if not post_data:
                # Extract from Open Graph tags
                og_title = soup.find('meta', property='og:title')
                og_description = soup.find('meta', property='og:description')
                og_image = soup.find('meta', property='og:image')
                
                caption = ''
                if og_description:
                    caption = og_description.get('content', '')
                elif og_title:
                    caption = og_title.get('content', '')
                
                image_url = og_image.get('content') if og_image else None
                
                # Try to extract username from page
                username = None
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    username_match = re.search(r'@(\w+)', title_text)
                    if username_match:
                        username = username_match.group(1)
                
                # Method 4: Try to extract from visible text on the page
                if not caption:
                    # Look for article or main content area
                    article = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile(r'content|post|caption', re.I))
                    if article:
                        # Get all text, but prioritize certain elements
                        caption_parts = []
                        
                        # Look for specific caption containers
                        caption_elem = article.find(['span', 'div', 'p'], class_=re.compile(r'caption|description|text', re.I))
                        if caption_elem:
                            caption_parts.append(caption_elem.get_text(strip=True))
                        
                        # Get all paragraph text
                        for p in article.find_all('p'):
                            p_text = p.get_text(strip=True)
                            if p_text and len(p_text) > 20:  # Skip very short text
                                caption_parts.append(p_text)
                        
                        # Get all span text
                        for span in article.find_all('span'):
                            span_text = span.get_text(strip=True)
                            if span_text and len(span_text) > 30 and span_text not in caption_parts:
                                caption_parts.append(span_text)
                        
                        if caption_parts:
                            caption = ' '.join(caption_parts[:3])  # Take first 3 meaningful parts
                
                # Method 5: Extract from any meta tags
                if not caption:
                    meta_tags = soup.find_all('meta')
                    for meta in meta_tags:
                        name = meta.get('name', '').lower()
                        property_attr = meta.get('property', '').lower()
                        content = meta.get('content', '')
                        
                        if content and len(content) > 20:
                            if 'description' in name or 'description' in property_attr:
                                caption = content
                                break
                            elif 'title' in name or 'title' in property_attr:
                                if not caption:
                                    caption = content
                
                # Extract image if not found yet
                if not image_url:
                    # Look for images in the page
                    img_tags = soup.find_all('img')
                    for img in img_tags:
                        src = img.get('src') or img.get('data-src')
                        if src and ('instagram' in src or 'cdninstagram' in src):
                            image_url = src
                            break
                
                if caption or image_url:
                    post_data = {
                        'shortcode': shortcode,
                        'caption': caption,
                        'display_url': image_url,
                        'taken_at_timestamp': None,
                        'is_video': False,
                        'url': post_url,
                        'username': username
                    }
            
            if post_data:
                logger.info(f"   ✅ Extracted post data: {len(post_data.get('caption', ''))} chars caption")
            else:
                logger.warning(f"   ⚠️ Could not extract post data from {post_url}")
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error scraping Instagram post page {post_url}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _extract_instagram_posts(self, soup, username, source, max_posts=12):
        """Extract Instagram posts from page HTML"""
        posts = []
        
        try:
            # Method 1: Look for JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    # Instagram embeds post data in various formats
                    if isinstance(data, dict):
                        # Check for post items
                        if 'itemListElement' in data:
                            for item in data['itemListElement']:
                                if isinstance(item, dict) and 'item' in item:
                                    posts.append(item['item'])
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # Method 2: Look for window._sharedData or similar embedded JSON
            # Instagram often embeds data in script tags with specific patterns
            all_scripts = soup.find_all('script')
            for script in all_scripts:
                if not script.string:
                    continue
                
                script_text = script.string
                
                # Look for window._sharedData pattern
                if 'window._sharedData' in script_text or 'window.__additionalDataLoaded' in script_text:
                    try:
                        # Extract JSON from script
                        # Pattern: window._sharedData = {...};
                        match = re.search(r'window\._sharedData\s*=\s*({.+?});', script_text, re.DOTALL)
                        if match:
                            data = json.loads(match.group(1))
                            # Navigate to posts data
                            if 'entry_data' in data:
                                profile_page = data['entry_data'].get('ProfilePage', [])
                                if profile_page and len(profile_page) > 0:
                                    user = profile_page[0].get('graphql', {}).get('user', {})
                                    media = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
                                    for edge in media[:max_posts]:
                                        node = edge.get('node', {})
                                        posts.append({
                                            'shortcode': node.get('shortcode'),
                                            'caption': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                                            'display_url': node.get('display_url'),
                                            'taken_at_timestamp': node.get('taken_at_timestamp'),
                                            'is_video': node.get('is_video', False),
                                            'url': f"https://www.instagram.com/p/{node.get('shortcode')}/" if node.get('shortcode') else None
                                        })
                    except (json.JSONDecodeError, KeyError, AttributeError) as e:
                        logger.debug(f"Could not parse Instagram embedded data: {e}")
                        continue
                
                # Look for additionalDataLoaded pattern
                if 'window.__additionalDataLoaded' in script_text:
                    try:
                        # Extract posts from additional data
                        match = re.search(r'window\.__additionalDataLoaded\([^,]+,\s*({.+?})\);', script_text, re.DOTALL)
                        if match:
                            data = json.loads(match.group(1))
                            # Navigate to posts
                            if 'graphql' in data:
                                user = data['graphql'].get('user', {})
                                media = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
                                for edge in media[:max_posts]:
                                    node = edge.get('node', {})
                                    posts.append({
                                        'shortcode': node.get('shortcode'),
                                        'caption': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                                        'display_url': node.get('display_url'),
                                        'taken_at_timestamp': node.get('taken_at_timestamp'),
                                        'is_video': node.get('is_video', False),
                                        'url': f"https://www.instagram.com/p/{node.get('shortcode')}/" if node.get('shortcode') else None
                                    })
                    except (json.JSONDecodeError, KeyError, AttributeError) as e:
                        logger.debug(f"Could not parse Instagram additional data: {e}")
                        continue
            
            # Method 3: Look for post links and scrape individual posts
            # If we couldn't get post data from embedded JSON, try to find post URLs
            if not posts:
                post_links = soup.find_all('a', href=re.compile(r'/p/[^/]+/'))
                seen_shortcodes = set()
                for link in post_links[:max_posts]:
                    href = link.get('href', '')
                    match = re.search(r'/p/([^/]+)/', href)
                    if match:
                        shortcode = match.group(1)
                        if shortcode not in seen_shortcodes:
                            seen_shortcodes.add(shortcode)
                            # Try to get post data from the link's parent
                            post_container = link.find_parent(['article', 'div'])
                            if post_container:
                                # Extract image
                                img = post_container.find('img')
                                display_url = img.get('src') if img else None
                                
                                # Extract caption (might be in alt text or nearby)
                                caption = img.get('alt', '') if img else ''
                                
                                posts.append({
                                    'shortcode': shortcode,
                                    'caption': caption,
                                    'display_url': display_url,
                                    'url': f"https://www.instagram.com/p/{shortcode}/" if shortcode else None
                                })
            
        except Exception as e:
            logger.warning(f"Error extracting Instagram posts: {e}")
        
        return posts[:max_posts]  # Limit to max_posts
    
    def _parse_instagram_post_as_event(self, post, source):
        """Parse an Instagram post and extract event information"""
        try:
            caption = post.get('caption', '') or ''
            post_url = post.get('url', '')
            image_url = post.get('display_url')
            timestamp = post.get('taken_at_timestamp')
            
            # If no caption but we have a URL, still try to create an event
            # (the caption might be in the image alt text or elsewhere)
            if not caption:
                # For individual posts, we should still try to extract something
                # Return a minimal event so user can see the post was found
                if post_url:
                    return {
                        'title': 'Instagram Post',
                        'description': f'Post from {post_url}',
                        'event_type': 'event',
                        'source_url': post_url,
                        'social_media_platform': 'instagram',
                        'social_media_url': post_url,
                        'image_url': image_url,
                        'language': 'English',
                    }
                return None
            
            # Check if post contains event-like content
            # Look for date patterns, event keywords, etc.
            caption_lower = caption.lower()
            event_keywords = [
                'event', 'exhibition', 'tour', 'workshop', 'lecture', 'talk', 
                'performance', 'concert', 'show', 'opening', 'reception',
                'tickets', 'register', 'rsvp', 'free', 'admission',
                'january', 'february', 'march', 'april', 'may', 'june',
                'july', 'august', 'september', 'october', 'november', 'december',
                'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                'pm', 'am', ':', 'at ', 'on ', 'from ', 'to '
            ]
            
            # Check if caption has event indicators
            has_event_keywords = any(keyword in caption_lower for keyword in event_keywords)
            has_date_pattern = bool(re.search(r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}', caption_lower)) or \
                              bool(re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', caption))
            
            # For individual posts, be less strict - if we have a caption, try to extract it
            # Don't filter out posts that might be events
            # Only skip if it's clearly not event-related AND we're scraping a profile (not individual post)
            is_individual_post = '/p/' in post_url or '/reel/' in post_url
            if not is_individual_post and not (has_event_keywords or has_date_pattern):
                # For profile scraping, only include posts that look like events
                return None
            
            # Extract title (first line or first sentence of caption)
            title = None
            caption_lines = caption.split('\n')
            if caption_lines:
                # First non-empty line is often the title
                for line in caption_lines[:3]:
                    line = line.strip()
                    if line and len(line) > 10 and len(line) < 200:
                        # Skip lines that are just hashtags or mentions
                        if not (line.startswith('#') or line.startswith('@')):
                            title = line
                            break
            
            if not title:
                # Use first 100 characters as title
                title = caption[:100].split('\n')[0].strip()
                if len(title) < 10:
                    return None
            
            # Clean title
            title = re.sub(r'^[#@]\w+\s*', '', title)  # Remove leading hashtags/mentions
            title = title.strip()
            
            # Extract description (full caption, cleaned)
            description = caption.strip()
            # Remove excessive hashtags at the end
            description = re.sub(r'\n+#\w+(?:\s+#\w+)*\s*$', '', description, flags=re.MULTILINE)
            
            # Use shared utility for description extraction if we have HTML
            # For now, just use the caption text
            
            # Extract dates from caption
            from scripts.utils import parse_date_range, extract_date_range_from_soup
            from datetime import datetime, date
            
            start_date = None
            end_date = None
            start_time = None
            end_time = None
            
            # Try to parse dates from caption
            date_range = parse_date_range(caption)
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
            
            # If no date range found, try to extract single date
            if not start_date:
                # Look for date patterns
                date_patterns = [
                    r'([A-Za-z]+day,?\s+[A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # Friday, December 5, 2025
                    r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})',  # December 5, 2025
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # 12/5/2025 or 12-5-2025
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, caption, re.I)
                    if match:
                        date_str = match.group(1)
                        # Try to parse
                        try:
                            if '/' in date_str or '-' in date_str:
                                # Try different date formats
                                for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%d-%m-%Y']:
                                    try:
                                        parsed_date = datetime.strptime(date_str, fmt).date()
                                        start_date = parsed_date
                                        end_date = parsed_date
                                        break
                                    except ValueError:
                                        continue
                            else:
                                # Try month name format
                                date_range = parse_date_range(date_str)
                                if date_range:
                                    start_date = date_range.get('start_date')
                                    end_date = date_range.get('end_date')
                        except:
                            pass
                        
                        if start_date:
                            break
            
            # If still no date, use post timestamp as fallback
            if not start_date and timestamp:
                try:
                    post_date = datetime.fromtimestamp(timestamp).date()
                    # Only use if post is recent (within last 6 months)
                    from datetime import timedelta
                    if post_date >= (date.today() - timedelta(days=180)):
                        start_date = post_date
                        end_date = post_date
                except:
                    pass
            
            # Extract time from caption
            time_pattern = r'\b([1-9]|1[0-2]):([0-5]\d)\s*([ap]\.?m\.?)\b'
            time_matches = re.findall(time_pattern, caption, re.I)
            if time_matches:
                try:
                    hour = int(time_matches[0][0])
                    minute = int(time_matches[0][1])
                    am_pm = time_matches[0][2].upper()
                    
                    if 'PM' in am_pm and hour != 12:
                        hour += 12
                    elif 'AM' in am_pm and hour == 12:
                        hour = 0
                    
                    start_time = time(hour, minute)
                    
                    # Check for end time
                    if len(time_matches) > 1:
                        hour = int(time_matches[1][0])
                        minute = int(time_matches[1][1])
                        am_pm = time_matches[1][2].upper()
                        
                        if 'PM' in am_pm and hour != 12:
                            hour += 12
                        elif 'AM' in am_pm and hour == 12:
                            hour = 0
                        
                        end_time = time(hour, minute)
                except:
                    pass
            
            # Determine event type from caption
            event_type = self._determine_event_type_from_text(caption, source)
            
            # Extract location if mentioned
            location = None
            location_patterns = [
                r'at\s+([A-Z][^.!?\n]{5,50})',
                r'@\s*([A-Z][^.!?\n]{5,50})',
                r'location[:\s]+([^.!?\n]{5,50})',
                r'venue[:\s]+([^.!?\n]{5,50})',
            ]
            for pattern in location_patterns:
                match = re.search(pattern, caption, re.I)
                if match:
                    location = match.group(1).strip()
                    # Clean up location
                    location = re.sub(r'[.!?]$', '', location)
                    if len(location) > 5 and len(location) < 100:
                        break
            
            # Build event data
            event_data = {
                'title': title,
                'description': description[:2000] if len(description) > 2000 else description,  # Limit description length
                'event_type': event_type,
                'source_url': post_url or source.url,
                'social_media_platform': 'instagram',
                'social_media_url': post_url or source.url,
                'social_media_handle': source.handle or f"@{username}",
                'organizer': source.name,
            }
            
            if start_date:
                event_data['start_date'] = start_date
                event_data['end_date'] = end_date or start_date
            
            if start_time:
                event_data['start_time'] = start_time
                if end_time:
                    event_data['end_time'] = end_time
            
            if location:
                event_data['location'] = location
                event_data['meeting_point'] = location
            
            if image_url:
                event_data['image_url'] = image_url
            
            # Set city from source
            if source.city_id:
                event_data['city_id'] = source.city_id
            
            # Language detection (filter non-English)
            combined_text = f"{title} {description}".lower()
            if re.search(r'(?:in|tour|conducted|presented|given|led)\s+(?:spanish|español|mandarin|普通話)', combined_text, re.I):
                # Non-English event, mark as not selected
                event_data['language'] = 'Spanish' if 'spanish' in combined_text or 'español' in combined_text else 'Mandarin'
                event_data['is_selected'] = False
            else:
                event_data['language'] = 'English'
            
            logger.info(f"   ✅ Extracted event: {title}")
            return event_data
            
        except Exception as e:
            logger.debug(f"Error parsing Instagram post: {e}")
            return None
    
    def _determine_event_type_from_text(self, text, source):
        """Determine event type from text content"""
        text_lower = text.lower()
        
        # Check source's event_types if available
        if source.event_types:
            try:
                source_event_types = json.loads(source.event_types) if isinstance(source.event_types, str) else source.event_types
                if isinstance(source_event_types, list) and source_event_types:
                    # If source has specific event types, prefer those
                    for event_type in source_event_types:
                        if event_type.lower() in text_lower:
                            return event_type
            except:
                pass
        
        # Determine from keywords
        if any(kw in text_lower for kw in ['exhibition', 'exhibit', 'on view', 'now on view']):
            return 'exhibition'
        elif any(kw in text_lower for kw in ['tour', 'guided tour', 'walking tour', 'collection tour']):
            return 'tour'
        elif any(kw in text_lower for kw in ['workshop', 'class', 'masterclass', 'training']):
            return 'workshop'
        elif any(kw in text_lower for kw in ['performance', 'concert', 'recital', 'show']):
            return 'performance'
        elif any(kw in text_lower for kw in ['talk', 'lecture', 'discussion', 'conversation']):
            return 'talk'
        elif any(kw in text_lower for kw in ['festival', 'celebration']):
            return 'festival'
        else:
            return 'event'  # Default
    
    def _extract_events_from_html(self, soup, source):
        """Extract events from HTML content"""
        events = []
        
        logger.info(f"🔍 Parsing HTML for {source.name}...")
        
        # Common selectors for events on tour/event websites
        event_selectors = [
            '.tour', '.tours', '.tour-item', '.tour-card',
            '.event', '.events', '.event-item', '.event-card',
            '.calendar-event', '.upcoming-event', '.scheduled-tour',
            '[class*="tour"]', '[class*="event"]', '[class*="schedule"]'
        ]
        
        total_elements_found = 0
        for selector in event_selectors:
            event_elements = soup.select(selector)
            if event_elements:
                logger.info(f"   Selector '{selector}' found {len(event_elements)} elements")
                total_elements_found += len(event_elements)
            
            for element in event_elements:
                try:
                    event_data = self._parse_event_element(element, source)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.debug(f"Error parsing event element: {e}")
                    continue
        
        logger.info(f"   Total event elements found: {total_elements_found}, Valid events extracted: {len(events)}")
        return events
    
    def _parse_event_element(self, element, source):
        """Parse individual event element"""
        try:
            # Extract title
            title = self._extract_text(element, [
                'h1', 'h2', 'h3', 'h4', '.title', '.tour-title', '.event-title', '.name'
            ])
            
            if not title:
                logger.debug(f"   ❌ No title found in element")
                return None
            
            logger.info(f"   📝 Extracted title: '{title}'")
            
            # Clean title to remove dates, trailing commas, etc.
            title = self._clean_title(title)
            
            # Extract description
            description = self._extract_text(element, [
                '.description', '.summary', '.content', 'p', '.tour-description'
            ])
            
            # Extract date/time information
            date_text = self._extract_text(element, [
                '.date', '.time', '.datetime', '.when', '.schedule'
            ])
            
            # Extract location
            location = self._extract_text(element, [
                '.location', '.venue', '.where', '.address', '.meeting-point'
            ])
            
            # Extract URL
            url = self._extract_url(element, source.url)
            
            # Extract image
            image_url = self._extract_image(element, source)
            
            # Parse dates (use simple parsing for now)
            start_date, end_date, start_time, end_time = self._parse_dates(date_text)
            
            # Determine event type from source's event types or content
            event_type = self._determine_event_type(source, title, description)
            
            event_data = {
                'title': title,
                'description': description or '',
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'start_location': location or '',
                'city_id': source.city_id,
                'event_type': event_type,
                'url': url,
                'image_url': image_url,
                'source': source.source_type,
                'source_url': source.url,
                'organizer': source.name,
                'social_media_platform': source.source_type if source.source_type != 'website' else None,
                'social_media_handle': source.handle if source.source_type != 'website' else None,
                'social_media_url': source.url if source.source_type != 'website' else None
            }
            
            # Validate event quality
            if not self._is_valid_event(event_data):
                logger.info(f"⚠️ Filtered out: '{title}'")
                logger.info(f"   Reason: Has time={event_data.get('start_time') is not None}, Has URL={event_data.get('url') != event_data.get('source_url')}, Has desc={bool(description)}, Desc len={len(description or '')}")
                return None
            
            logger.info(f"✅ Valid event found: '{title}'")
            return event_data
            
        except Exception as e:
            logger.debug(f"Error parsing event element: {e}")
            return None
    
    def _clean_title(self, title):
        """Clean and normalize title text to fix common issues"""
        if not title:
            return title
        
        # First remove venue name suffixes
        from scripts.utils import clean_event_title
        title = clean_event_title(title)
        
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
    
    def _extract_text(self, element, selectors):
        """Extract text from element using multiple selectors"""
        for selector in selectors:
            found = element.select_one(selector)
            if found and found.get_text(strip=True):
                return found.get_text(strip=True)
        return None
    
    def _extract_url(self, element, base_url):
        """Extract URL from event element"""
        link = element.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('/'):
                return urljoin(base_url, href)
            elif not href.startswith('http'):
                return urljoin(base_url, href)
            return href
        
        parent_link = element.find_parent('a', href=True)
        if parent_link:
            href = parent_link['href']
            if href.startswith('/'):
                return urljoin(base_url, href)
            elif not href.startswith('http'):
                return urljoin(base_url, href)
            return href
        
        return base_url
    
    def _extract_image(self, element, source):
        """Extract image from event element"""
        import re
        
        img = element.find('img')
        if img:
            img_src = (img.get('src') or 
                      img.get('data-src') or 
                      img.get('data-lazy-src') or
                      img.get('data-original'))
            
            if not img_src and img.get('srcset'):
                srcset = img.get('srcset')
                srcset_match = re.search(r'([^\s,]+\.(?:jpg|jpeg|png|gif|webp))', srcset, re.IGNORECASE)
                if srcset_match:
                    img_src = srcset_match.group(1)
            
            if img_src:
                if img_src.startswith('/'):
                    img_src = urljoin(source.url, img_src)
                elif not img_src.startswith('http'):
                    img_src = urljoin(source.url, img_src)
                
                if not (img_src.startswith('data:') or 'placeholder' in img_src.lower()):
                    return img_src
        
        return None
    
    def _parse_dates(self, date_text):
        """Parse date and time from text"""
        if not date_text:
            return None, None, None, None
        
        # For now, use today as default (can be enhanced with better date parsing)
        today = date.today()
        start_date = today
        end_date = today
        start_time = None
        end_time = None
        
        # Try to extract time from text
        import re
        time_pattern = r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?'
        time_matches = re.findall(time_pattern, date_text)
        
        if time_matches:
            hour, minute, period = time_matches[0]
            hour = int(hour)
            minute = int(minute)
            
            if period and period.upper() == 'PM' and hour != 12:
                hour += 12
            elif period and period.upper() == 'AM' and hour == 12:
                hour = 0
            
            from datetime import time
            start_time = time(hour, minute)
        
        return start_date, end_date, start_time, end_time
    
    def _determine_event_type(self, source, title, description):
        """Determine event type based on source and content"""
        content = f"{title} {description}".lower()
        
        # Check source's event types
        import json
        if source.event_types:
            try:
                event_types = json.loads(source.event_types) if isinstance(source.event_types, str) else source.event_types
                if event_types:
                    # Map source event types to our event types
                    if any(t in ['tours', 'walking_tours', 'historical_tours', 'tour'] for t in event_types):
                        return 'tour'
                    elif any(t in ['exhibitions', 'art_exhibitions', 'exhibition'] for t in event_types):
                        return 'exhibition'
                    elif any(t in ['festivals', 'festival'] for t in event_types):
                        return 'festival'
                    elif any(t in ['photowalks', 'photography'] for t in event_types):
                        return 'photowalk'
            except:
                pass
        
        # Fallback to content-based detection
        if 'tour' in content or 'walk' in content or 'guided' in content:
            return 'tour'
        elif 'exhibition' in content or 'exhibit' in content or 'gallery' in content:
            return 'exhibition'
        elif 'festival' in content:
            return 'festival'
        elif 'photowalk' in content or 'photo walk' in content:
            return 'photowalk'
        else:
            return 'tour'
    
    def _is_valid_event(self, event_data):
        """Validate event quality to filter out generic/incomplete events"""
        
        if not event_data.get('title'):
            return False
        
        title = event_data.get('title', '').lower().strip()
        description = event_data.get('description', '').lower()
        
        # Filter out overly generic single-word titles
        generic_titles = [
            'tour', 'tours', 'visit', 'admission', 'hours', 
            'tickets', 'information', 'about', 'overview', 'home',
            'location', 'contact', 'directions', 'address'
        ]
        if title in generic_titles:
            return False
        
        # Filter out very short or generic titles
        if len(title) < 5:
            return False
        
        # RELAXED VALIDATION: Accept events from known sources
        # If we have a source_id or city_id, we trust it's a real event
        has_source = event_data.get('source_url') is not None or event_data.get('city_id') is not None
        
        # Must have either a specific time OR a URL OR a meaningful description
        # BUT if it's from a known source, be more lenient
        has_specific_time = event_data.get('start_time') is not None
        has_url = event_data.get('url') and event_data['url'] != event_data.get('source_url')
        has_meaningful_description = description and len(description) >= 15  # Lowered from 30 to 15
        
        # If from a known source, accept if it has ANY description or URL
        if has_source:
            if description or has_url:
                return True
        
        # For other events, require at least one quality indicator
        if not (has_specific_time or has_url or has_meaningful_description):
            return False
        
        # Additional quality checks
        # Reject if description is just a location/address without event info
        location_indicators = ['meet your driver', 'meet at', 'pickup location', 'departure point']
        if any(indicator in description for indicator in location_indicators):
            # Only allow if it also has other meaningful content
            if not (has_specific_time or has_url or len(description) >= 50):  # Lowered from 100 to 50
                return False
        
        return True
