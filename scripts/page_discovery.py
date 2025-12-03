#!/usr/bin/env python3
"""
Automatic page discovery for exhibitions and tours
Discovers relevant pages without manual configuration
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

class PageDiscovery:
    """Automatically discover exhibition and tour pages from venue websites"""
    
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def discover_pages(self, base_url, event_type=None, max_pages=20, timeout=30):
        """
        Discover exhibition or tour pages from a venue website
        
        Args:
            base_url: Base URL of the venue website
            event_type: 'exhibition', 'tour', or None for both
            max_pages: Maximum number of pages to discover
            timeout: Maximum time in seconds to spend on discovery
        
        Returns:
            List of discovered page URLs
        """
        import time
        start_time = time.time()
        discovered_urls = set()
        
        try:
            # Strategy 1: Check sitemap.xml (fastest, most reliable)
            if time.time() - start_time < timeout:
                try:
                    sitemap_urls = self._discover_via_sitemap(base_url, event_type)
                    discovered_urls.update(sitemap_urls)
                    logger.info(f"Found {len(sitemap_urls)} URLs via sitemap")
                    # If sitemap found many URLs, we can skip other strategies
                    if len(sitemap_urls) >= 10:
                        valid_urls = self._validate_urls(list(discovered_urls), base_url, event_type)
                        return valid_urls[:max_pages]
                except Exception as e:
                    logger.debug(f"Error in sitemap discovery: {e}")
            
            # Strategy 2: Follow navigation menus
            if time.time() - start_time < timeout:
                try:
                    nav_urls = self._discover_via_navigation(base_url, event_type)
                    discovered_urls.update(nav_urls)
                    logger.info(f"Found {len(nav_urls)} URLs via navigation")
                except Exception as e:
                    logger.debug(f"Error in navigation discovery: {e}")
            
            # Strategy 3: Try common URL patterns
            if time.time() - start_time < timeout:
                try:
                    pattern_urls = self._discover_via_url_patterns(base_url, event_type)
                    discovered_urls.update(pattern_urls)
                    logger.info(f"Found {len(pattern_urls)} URLs via URL patterns")
                except Exception as e:
                    logger.debug(f"Error in URL pattern discovery: {e}")
            
            # Strategy 4: Follow breadcrumbs and site structure (skip if we have enough)
            if len(discovered_urls) < 5 and time.time() - start_time < timeout:
                try:
                    structure_urls = self._discover_via_structure(base_url, event_type)
                    discovered_urls.update(structure_urls)
                    logger.info(f"Found {len(structure_urls)} URLs via site structure")
                except Exception as e:
                    logger.debug(f"Error in structure discovery: {e}")
        
        except Exception as e:
            logger.warning(f"Error in page discovery: {e}")
        
        # Filter and validate URLs
        valid_urls = self._validate_urls(list(discovered_urls), base_url, event_type)
        
        return valid_urls[:max_pages]
    
    def _discover_via_sitemap(self, base_url, event_type=None):
        """Discover pages by parsing sitemap.xml"""
        urls = []
        
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap1.xml',
            '/sitemap-1.xml'
        ]
        
        for path in sitemap_paths:
            try:
                sitemap_url = urljoin(base_url, path)
                response = self.session.get(sitemap_url, timeout=10)
                if response.status_code == 200:
                    # Check if it's a sitemap index
                    if 'sitemapindex' in response.text.lower():
                        # Parse sitemap index and get individual sitemaps
                        soup = BeautifulSoup(response.content, 'xml')
                        sitemap_tags = soup.find_all('sitemap')
                        for sitemap_tag in sitemap_tags[:5]:  # Limit to first 5 sitemaps
                            loc = sitemap_tag.find('loc')
                            if loc:
                                sub_sitemap_url = loc.text
                                urls.extend(self._parse_sitemap(sub_sitemap_url, event_type))
                    else:
                        urls.extend(self._parse_sitemap(sitemap_url, event_type))
                    break  # Found a sitemap, no need to try others
            except Exception as e:
                logger.debug(f"Error checking sitemap {path}: {e}")
                continue
        
        return urls
    
    def _parse_sitemap(self, sitemap_url, event_type=None):
        """Parse a sitemap XML file"""
        urls = []
        try:
            response = self.session.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                url_tags = soup.find_all('url')
                
                for url_tag in url_tags:
                    loc = url_tag.find('loc')
                    if loc:
                        url = loc.text
                        if self._is_relevant_url(url, event_type):
                            urls.append(url)
        except Exception as e:
            logger.debug(f"Error parsing sitemap {sitemap_url}: {e}")
        
        return urls
    
    def _discover_via_navigation(self, base_url, event_type=None):
        """Discover pages by following navigation menus"""
        urls = []
        
        try:
            response = self.session.get(base_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find navigation elements
                nav_selectors = [
                    'nav', 'nav a', '.navigation', '.nav', '.menu', '.main-menu',
                    '[role="navigation"]', '.header-nav', '.site-nav',
                    'ul.menu', 'ul.nav', '.navbar', '.nav-menu'
                ]
                
                nav_links = []
                for selector in nav_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        links = element.find_all('a', href=True)
                        nav_links.extend(links)
                
                # Look for relevant navigation items
                keywords = self._get_keywords(event_type)
                for link in nav_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()
                    
                    # Check if link text or href matches keywords
                    if any(keyword in text or keyword in href.lower() for keyword in keywords):
                        full_url = urljoin(base_url, href)
                        if self._is_relevant_url(full_url, event_type):
                            urls.append(full_url)
                            
                            # Also check if this is a category page - follow it
                            if self._is_category_page(text, href):
                                category_urls = self._discover_from_category_page(full_url, event_type)
                                urls.extend(category_urls)
        
        except Exception as e:
            logger.debug(f"Error discovering via navigation: {e}")
        
        return urls
    
    def _discover_via_url_patterns(self, base_url, event_type=None):
        """Discover pages by trying common URL patterns"""
        urls = []
        
        # Common URL patterns for exhibitions and tours
        patterns = []
        
        if not event_type or event_type == 'exhibition':
            patterns.extend([
                '/exhibitions', '/exhibition', '/exhibits', '/exhibit',
                '/art/exhibitions', '/art/exhibition', '/art/exhibits',
                '/current-exhibitions', '/upcoming-exhibitions', '/past-exhibitions',
                '/on-view', '/onview', '/whats-on', '/whats-on/exhibitions',
                '/programs/exhibitions', '/visit/exhibitions'
            ])
        
        if not event_type or event_type == 'tour':
            patterns.extend([
                '/tours', '/tour', '/guided-tours', '/guided-tour',
                '/visit/tours', '/visit/tour', '/programs/tours',
                '/tours-and-programs', '/tours-programs',
                '/public-tours', '/private-tours', '/group-tours',
                '/walking-tours', '/audio-tours', '/virtual-tours'
            ])
        
        for pattern in patterns:
            try:
                test_url = urljoin(base_url, pattern)
                response = self.session.head(test_url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    urls.append(test_url)
                    
                    # If it's a listing page, try to find individual pages
                    if self._is_listing_page(response):
                        listing_urls = self._discover_from_listing_page(test_url, event_type)
                        urls.extend(listing_urls)
            except Exception:
                continue
        
        return urls
    
    def _discover_via_structure(self, base_url, event_type=None):
        """Discover pages by analyzing site structure and breadcrumbs"""
        urls = []
        
        try:
            response = self.session.get(base_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for breadcrumbs
                breadcrumbs = soup.find_all(['nav', 'ol', 'ul'], 
                    class_=lambda c: c and ('breadcrumb' in str(c).lower() or 'bread-crumb' in str(c).lower()))
                
                # Look for "See all" or "View all" links
                keywords = self._get_keywords(event_type)
                see_all_links = soup.find_all('a', 
                    string=re.compile(r'(see all|view all|browse all|all .*)', re.I))
                
                for link in see_all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()
                    if any(keyword in text for keyword in keywords):
                        full_url = urljoin(base_url, href)
                        if self._is_relevant_url(full_url, event_type):
                            urls.append(full_url)
        
        except Exception as e:
            logger.debug(f"Error discovering via structure: {e}")
        
        return urls
    
    def _discover_from_category_page(self, category_url, event_type=None):
        """Discover individual pages from a category/listing page"""
        urls = []
        
        try:
            response = self.session.get(category_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find links that look like individual event/exhibition pages
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    full_url = urljoin(category_url, href)
                    
                    # Check if it's a detail page (not another category)
                    if self._is_detail_page(full_url, link):
                        if self._is_relevant_url(full_url, event_type):
                            urls.append(full_url)
        except Exception as e:
            logger.debug(f"Error discovering from category page: {e}")
        
        return urls[:10]  # Limit to 10 per category
    
    def _discover_from_listing_page(self, listing_url, event_type=None):
        """Discover individual pages from a listing page"""
        return self._discover_from_category_page(listing_url, event_type)
    
    def _is_relevant_url(self, url, event_type=None):
        """Check if URL is relevant to the requested event type"""
        url_lower = url.lower()
        
        if event_type == 'exhibition':
            return any(keyword in url_lower for keyword in ['exhibition', 'exhibit', 'on-view', 'onview'])
        elif event_type == 'tour':
            return 'tour' in url_lower
        else:
            return any(keyword in url_lower for keyword in ['exhibition', 'exhibit', 'tour', 'on-view'])
    
    def _is_category_page(self, text, href):
        """Check if a link points to a category/listing page"""
        category_indicators = ['all', 'view all', 'see all', 'browse', 'list', 'index']
        return any(indicator in text for indicator in category_indicators) or \
               any(indicator in href.lower() for indicator in ['/exhibitions', '/tours', '/exhibition', '/tour'])
    
    def _is_listing_page(self, response):
        """Check if a response is a listing page"""
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            return False
        
        # Could add more sophisticated checks here
        return True
    
    def _is_detail_page(self, url, link_element):
        """Check if a URL is a detail page (not a category/listing)"""
        url_lower = url.lower()
        text = link_element.get_text(strip=True).lower()
        
        # Detail pages usually have specific patterns
        detail_indicators = [
            '/exhibition/', '/exhibit/', '/tour/',
            re.search(r'/\d{4}/', url_lower),  # Year in URL
            re.search(r'/[a-z-]+-[a-z-]+/', url_lower)  # Multi-word slug
        ]
        
        # Category pages usually have these patterns
        category_indicators = ['/exhibitions', '/tours', '/all', '/list', '/index']
        
        has_detail_pattern = any(detail_indicators)
        has_category_pattern = any(indicator in url_lower for indicator in category_indicators)
        
        return has_detail_pattern and not has_category_pattern
    
    def _get_keywords(self, event_type=None):
        """Get relevant keywords for event type"""
        if event_type == 'exhibition':
            return ['exhibition', 'exhibit', 'on view', 'onview', 'show', 'gallery']
        elif event_type == 'tour':
            return ['tour', 'tours', 'guided', 'walking', 'audio', 'virtual']
        else:
            return ['exhibition', 'exhibit', 'tour', 'tours', 'on view', 'guided']
    
    def _validate_urls(self, urls, base_url, event_type=None):
        """Validate and filter discovered URLs"""
        valid_urls = []
        base_domain = urlparse(base_url).netloc
        
        for url in urls:
            try:
                parsed = urlparse(url)
                # Must be same domain
                if parsed.netloc != base_domain and parsed.netloc:
                    continue
                
                # Must be relevant
                if not self._is_relevant_url(url, event_type):
                    continue
                
                # Skip common non-content pages
                skip_patterns = ['/search', '/contact', '/about', '/donate', '/shop', '/tickets', '/calendar']
                if any(pattern in url.lower() for pattern in skip_patterns):
                    continue
                
                valid_urls.append(url)
            except Exception:
                continue
        
        return valid_urls

