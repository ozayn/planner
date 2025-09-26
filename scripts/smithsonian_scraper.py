#!/usr/bin/env python3
"""
Specialized Smithsonian Museum Event Scraper
Scrapes events from Smithsonian museums using their specific website structures.
"""

import os
import sys
import requests
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import logging

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue without it

class SmithsonianScraper:
    """Specialized scraper for Smithsonian museums."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger = logging.getLogger(__name__)
        
        # Smithsonian-specific patterns
        self.smithsonian_patterns = {
            'event_urls': [
                r'href="([^"]*events[^"]*)"',
                r'href="([^"]*programs[^"]*)"',
                r'href="([^"]*calendar[^"]*)"',
                r'href="([^"]*exhibitions[^"]*)"'
            ],
            'event_titles': [
                r'<h[1-6][^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h[1-6]>',
                r'<h[1-6][^>]*>([^<]+)</h[1-6]>',
                r'class="[^"]*event-title[^"]*"[^>]*>([^<]+)<',
                r'<title>([^<]+)</title>'
            ],
            'event_dates': [
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\w+ \d{1,2}, \d{4})',
                r'(\d{1,2} \w+ \d{4})'
            ],
            'event_times': [
                r'(\d{1,2}:\d{2}\s*[AP]M)',
                r'(\d{1,2}:\d{2})',
                r'(\d{1,2}\s*[AP]M)'
            ]
        }
    
    def scrape_smithsonian_museum(self, museum_name: str, website_url: str) -> List[Dict]:
        """Scrape events from a Smithsonian museum."""
        events = []
        
        try:
            self.logger.info(f"Scraping {museum_name} at {website_url}")
            
            # Get main page
            response = self.session.get(website_url, timeout=10)
            response.raise_for_status()
            
            # Find event-related URLs
            event_urls = self._find_event_urls(response.text, website_url)
            self.logger.info(f"Found {len(event_urls)} event URLs")
            
            # Scrape each event URL
            for url in event_urls[:10]:  # Limit to first 10 events
                try:
                    event_data = self._scrape_event_page(url, museum_name)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    self.logger.error(f"Error scraping event page {url}: {e}")
            
            # Also try to scrape events directly from main page
            main_page_events = self._scrape_main_page_events(response.text, museum_name, website_url)
            events.extend(main_page_events)
            
        except Exception as e:
            self.logger.error(f"Error scraping {museum_name}: {e}")
        
        return events
    
    def _find_event_urls(self, html_content: str, base_url: str) -> List[str]:
        """Find event-related URLs in HTML content."""
        urls = set()
        
        for pattern in self.smithsonian_patterns['event_urls']:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                full_url = urljoin(base_url, match)
                urls.add(full_url)
        
        return list(urls)
    
    def _scrape_event_page(self, url: str, museum_name: str) -> Optional[Dict]:
        """Scrape individual event page."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            content = response.text
            
            # Extract event details
            title = self._extract_title(content)
            description = self._extract_description(content)
            date_info = self._extract_date_time(content)
            location = self._extract_location(content)
            price = self._extract_price(content)
            
            if not title:
                return None
            
            event = {
                'title': title,
                'description': description or f"Event at {museum_name}",
                'start_date': date_info.get('date'),
                'start_time': date_info.get('time'),
                'location': location or museum_name,
                'price': price,
                'source_url': url,
                'organizer': museum_name,
                'event_type': 'museum_event',
                'social_media_platform': 'website',
                'social_media_url': url,
                'confidence_score': self._calculate_confidence(title, description, date_info)
            }
            
            return event
            
        except Exception as e:
            self.logger.error(f"Error scraping event page {url}: {e}")
            return None
    
    def _scrape_main_page_events(self, html_content: str, museum_name: str, base_url: str) -> List[Dict]:
        """Scrape events directly from main page."""
        events = []
        
        # Look for event listings on main page
        event_sections = re.findall(r'<div[^>]*class="[^"]*event[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL | re.IGNORECASE)
        
        for section in event_sections[:5]:  # Limit to first 5 sections
            title = self._extract_title(section)
            if title and len(title) > 10:
                date_info = self._extract_date_time(section)
                
                event = {
                    'title': title,
                    'description': f"Event at {museum_name}",
                    'start_date': date_info.get('date'),
                    'start_time': date_info.get('time'),
                    'location': museum_name,
                    'source_url': base_url,
                    'organizer': museum_name,
                    'event_type': 'museum_event',
                    'social_media_platform': 'website',
                    'social_media_url': base_url,
                    'confidence_score': self._calculate_confidence(title, None, date_info)
                }
                
                events.append(event)
        
        return events
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract event title from content."""
        for pattern in self.smithsonian_patterns['event_titles']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if len(title) > 5 and not any(skip in title.lower() for skip in ['home', 'about', 'contact', 'menu']):
                    return title
        return None
    
    def _extract_description(self, content: str) -> Optional[str]:
        """Extract event description from content."""
        # Look for description patterns
        desc_patterns = [
            r'<p[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</p>',
            r'<div[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</div>',
            r'<meta[^>]*name="description"[^>]*content="([^"]*)"'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 20:
                    return desc
        
        return None
    
    def _extract_date_time(self, content: str) -> Dict[str, Optional[str]]:
        """Extract date and time from content."""
        date_info = {'date': None, 'time': None}
        
        # Extract date
        for pattern in self.smithsonian_patterns['event_dates']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                date_info['date'] = match.group(1)
                break
        
        # Extract time
        for pattern in self.smithsonian_patterns['event_times']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                date_info['time'] = match.group(1)
                break
        
        return date_info
    
    def _extract_location(self, content: str) -> Optional[str]:
        """Extract location from content."""
        location_patterns = [
            r'location[^>]*>([^<]+)<',
            r'venue[^>]*>([^<]+)<',
            r'where[^>]*>([^<]+)<'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) > 5:
                    return location
        
        return None
    
    def _extract_price(self, content: str) -> Optional[str]:
        """Extract price from content."""
        price_patterns = [
            r'\$(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*dollars?',
            r'free',
            r'no charge',
            r'admission[^>]*>([^<]+)<'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _calculate_confidence(self, title: str, description: Optional[str], date_info: Dict) -> float:
        """Calculate confidence score for scraped event."""
        score = 0.0
        
        if title and len(title.strip()) > 5:
            score += 0.4
        
        if description and len(description.strip()) > 20:
            score += 0.2
        
        if date_info.get('date'):
            score += 0.2
        
        if date_info.get('time'):
            score += 0.1
        
        # Bonus for Smithsonian-specific keywords
        smithsonian_keywords = ['exhibition', 'program', 'lecture', 'tour', 'event', 'gallery']
        if any(keyword in title.lower() for keyword in smithsonian_keywords):
            score += 0.1
        
        return min(score, 1.0)

class SmithsonianEventScraper:
    """Main class for scraping Smithsonian events."""
    
    def __init__(self):
        self.scraper = SmithsonianScraper()
        self.logger = logging.getLogger(__name__)
        
        # Smithsonian museums in DC
        self.smithsonian_museums = [
            {
                'name': 'National Air and Space Museum',
                'url': 'https://airandspace.si.edu/',
                'type': 'museum'
            },
            {
                'name': 'National Museum of Natural History',
                'url': 'https://naturalhistory.si.edu/',
                'type': 'museum'
            },
            {
                'name': 'National Museum of American History',
                'url': 'https://americanhistory.si.edu/',
                'type': 'museum'
            },
            {
                'name': 'National Museum of African American History and Culture',
                'url': 'https://nmaahc.si.edu/',
                'type': 'museum'
            },
            {
                'name': 'National Portrait Gallery',
                'url': 'https://npg.si.edu/',
                'type': 'museum'
            },
            {
                'name': 'Hirshhorn Museum and Sculpture Garden',
                'url': 'https://hirshhorn.si.edu/',
                'type': 'museum'
            },
            {
                'name': 'Freer Gallery of Art',
                'url': 'https://asia.si.edu/',
                'type': 'museum'
            },
            {
                'name': 'Arthur M. Sackler Gallery',
                'url': 'https://asia.si.edu/',
                'type': 'museum'
            }
        ]
    
    def scrape_all_smithsonian_events(self) -> List[Dict]:
        """Scrape events from all Smithsonian museums."""
        all_events = []
        
        for museum in self.smithsonian_museums:
            try:
                events = self.scraper.scrape_smithsonian_museum(
                    museum['name'], 
                    museum['url']
                )
                all_events.extend(events)
                self.logger.info(f"Scraped {len(events)} events from {museum['name']}")
            except Exception as e:
                self.logger.error(f"Error scraping {museum['name']}: {e}")
        
        # Remove duplicates
        unique_events = self._deduplicate_events(all_events)
        
        return unique_events
    
    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        """Remove duplicate events."""
        seen = set()
        unique_events = []
        
        for event in events:
            key = (event['title'].lower().strip(), event.get('start_date'))
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    scraper = SmithsonianEventScraper()
    events = scraper.scrape_all_smithsonian_events()
    
    print(f"Found {len(events)} Smithsonian events:")
    for event in events[:5]:  # Show first 5
        print(f"- {event['title']} (confidence: {event['confidence_score']:.2f})")
        if event.get('start_date'):
            print(f"  Date: {event['start_date']}")
        if event.get('start_time'):
            print(f"  Time: {event['start_time']}")
        print()
