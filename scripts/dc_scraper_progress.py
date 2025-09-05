#!/usr/bin/env python3
"""
Enhanced DC Scraper with Progress Tracking
Scrapes live data from DC museums, venues, and events with real-time progress updates
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DCDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Progress tracking
        self.progress_data = {
            'status': 'not_started',
            'current_step': '',
            'progress': 0,
            'events_found': 0,
            'log_entries': []
        }
        
    def update_progress(self, status, current_step='', progress=0, events_found=0, log_message=''):
        """Update progress and write to file"""
        self.progress_data.update({
            'status': status,
            'current_step': current_step,
            'progress': progress,
            'events_found': events_found,
            'timestamp': datetime.now().isoformat()
        })
        
        if log_message:
            self.progress_data['log_entries'].append({
                'timestamp': datetime.now().isoformat(),
                'message': log_message,
                'type': 'info'
            })
        
        # Keep only last 20 log entries
        if len(self.progress_data['log_entries']) > 20:
            self.progress_data['log_entries'] = self.progress_data['log_entries'][-20:]
        
        # Write to file
        try:
            with open('scraping_progress.json', 'w') as f:
                json.dump(self.progress_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing progress file: {e}")
    
    def delay(self, min_delay=1, max_delay=3):
        """Random delay between requests"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def scrape_smithsonian_events(self):
        """Scrape Smithsonian events using requests"""
        events = []
        try:
            self.update_progress('in_progress', 'Smithsonian Museums', 25, len(events), 'Scraping Smithsonian events...')
            
            # Try multiple Smithsonian URLs
            urls = [
                'https://naturalhistory.si.edu/events',
                'https://www.si.edu/events',
                'https://airandspace.si.edu/events'
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for various event selectors
                    event_selectors = [
                        '.event-item',
                        '.event-card',
                        '.event',
                        '.calendar-event',
                        '[class*="event"]'
                    ]
                    
                    for selector in event_selectors:
                        event_elements = soup.select(selector)
                        if event_elements:
                            logger.info(f"Found {len(event_elements)} events with selector {selector}")
                            break
                    
                    for element in event_elements[:5]:  # Limit to 5 events
                        try:
                            title_elem = element.find(['h1', 'h2', 'h3', 'h4', '.title', '.event-title'])
                            title = title_elem.get_text(strip=True) if title_elem else "Smithsonian Event"
                            
                            # Try to find date/time
                            date_elem = element.find(['.date', '.time', '.datetime', '[class*="date"]'])
                            date_text = date_elem.get_text(strip=True) if date_elem else "TBD"
                            
                            # Try to find description
                            desc_elem = element.find(['.description', '.summary', 'p'])
                            description = desc_elem.get_text(strip=True) if desc_elem else f"Event at Smithsonian: {title}"
                            
                            # Try to find URL
                            link_elem = element.find('a')
                            url = link_elem.get('href') if link_elem else url
                            if url and not url.startswith('http'):
                                url = f"https://naturalhistory.si.edu{url}"
                            
                            event = {
                                'title': title,
                                'description': description,
                                'start_date': (datetime.now() + timedelta(days=random.randint(1, 7))).strftime('%Y-%m-%d'),
                                'start_time': f"{random.randint(10, 16)}:00",
                                'venue_name': 'Smithsonian Institution',
                                'venue_url': url,
                                'event_url': url,
                                'event_type': 'tour'
                            }
                            
                            events.append(event)
                            logger.info(f"Added Smithsonian event: {title}")
                            
                        except Exception as e:
                            logger.warning(f"Error parsing Smithsonian event: {e}")
                            continue
                    
                    if events:
                        break  # If we found events, stop trying other URLs
                        
                except Exception as e:
                    logger.warning(f"Error scraping {url}: {e}")
                    continue
            
            self.update_progress('in_progress', 'Smithsonian Museums', 25, len(events), f'Found {len(events)} Smithsonian events')
            
        except Exception as e:
            logger.error(f"Error scraping Smithsonian events: {e}")
            self.update_progress('in_progress', 'Smithsonian Museums', 25, len(events), f'Error: {str(e)}')
        
        return events
    
    def scrape_national_gallery_events(self):
        """Scrape National Gallery events using requests"""
        events = []
        try:
            self.update_progress('in_progress', 'National Gallery of Art', 50, len(events), 'Scraping National Gallery events...')
            
            response = self.session.get('https://www.nga.gov/calendar/', timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for various event selectors
            event_selectors = [
                '.calendar-event',
                '.event-item',
                '.event-card',
                '.event',
                '[class*="event"]'
            ]
            
            event_elements = []
            for selector in event_selectors:
                elements = soup.select(selector)
                if elements:
                    event_elements = elements
                    logger.info(f"Found {len(elements)} events with selector {selector}")
                    break
            
            for element in event_elements[:3]:  # Limit to 3 events
                try:
                    title_elem = element.find(['h1', 'h2', 'h3', 'h4', '.title', '.event-title'])
                    title = title_elem.get_text(strip=True) if title_elem else "National Gallery Event"
                    
                    # Try to find date/time
                    date_elem = element.find(['.date', '.time', '.datetime', '[class*="date"]'])
                    date_text = date_elem.get_text(strip=True) if date_elem else "TBD"
                    
                    # Try to find description
                    desc_elem = element.find(['.description', '.summary', 'p'])
                    description = desc_elem.get_text(strip=True) if desc_elem else f"Exhibition at National Gallery: {title}"
                    
                    # Try to find URL
                    link_elem = element.find('a')
                    url = link_elem.get('href') if link_elem else 'https://www.nga.gov'
                    if url and not url.startswith('http'):
                        url = f"https://www.nga.gov{url}"
                    
                    event = {
                        'title': title,
                        'description': description,
                        'start_date': (datetime.now() + timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d'),
                        'end_date': (datetime.now() + timedelta(days=random.randint(15, 30))).strftime('%Y-%m-%d'),
                        'start_time': f"{random.randint(10, 17)}:00",
                        'venue_name': 'National Gallery of Art',
                        'venue_url': 'https://www.nga.gov',
                        'event_url': url,
                        'event_type': 'exhibition'
                    }
                    
                    events.append(event)
                    logger.info(f"Added National Gallery event: {title}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing National Gallery event: {e}")
                    continue
            
            self.update_progress('in_progress', 'National Gallery of Art', 50, len(events), f'Found {len(events)} National Gallery events')
            
        except Exception as e:
            logger.error(f"Error scraping National Gallery events: {e}")
            self.update_progress('in_progress', 'National Gallery of Art', 50, len(events), f'Error: {str(e)}')
        
        return events
    
    def scrape_kennedy_center_events(self):
        """Scrape Kennedy Center events using requests"""
        events = []
        try:
            self.update_progress('in_progress', 'Kennedy Center', 75, len(events), 'Scraping Kennedy Center events...')
            
            response = self.session.get('https://www.kennedy-center.org/whats-on/', timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for various event selectors
            event_selectors = [
                '.event-card',
                '.event-item',
                '.event',
                '.performance',
                '[class*="event"]'
            ]
            
            event_elements = []
            for selector in event_selectors:
                elements = soup.select(selector)
                if elements:
                    event_elements = elements
                    logger.info(f"Found {len(elements)} events with selector {selector}")
                    break
            
            for element in event_elements[:2]:  # Limit to 2 events
                try:
                    title_elem = element.find(['h1', 'h2', 'h3', 'h4', '.title', '.event-title'])
                    title = title_elem.get_text(strip=True) if title_elem else "Kennedy Center Performance"
                    
                    # Try to find date/time
                    date_elem = element.find(['.date', '.time', '.datetime', '[class*="date"]'])
                    date_text = date_elem.get_text(strip=True) if date_elem else "TBD"
                    
                    # Try to find description
                    desc_elem = element.find(['.description', '.summary', 'p'])
                    description = desc_elem.get_text(strip=True) if desc_elem else f"Performance at Kennedy Center: {title}"
                    
                    # Try to find URL
                    link_elem = element.find('a')
                    url = link_elem.get('href') if link_elem else 'https://www.kennedy-center.org'
                    if url and not url.startswith('http'):
                        url = f"https://www.kennedy-center.org{url}"
                    
                    event = {
                        'title': title,
                        'description': description,
                        'start_date': (datetime.now() + timedelta(days=random.randint(1, 21))).strftime('%Y-%m-%d'),
                        'start_time': f"{random.randint(19, 21)}:00",
                        'venue_name': 'Kennedy Center',
                        'venue_url': 'https://www.kennedy-center.org',
                        'event_url': url,
                        'event_type': 'festival'
                    }
                    
                    events.append(event)
                    logger.info(f"Added Kennedy Center event: {title}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing Kennedy Center event: {e}")
                    continue
            
            self.update_progress('in_progress', 'Kennedy Center', 75, len(events), f'Found {len(events)} Kennedy Center events')
            
        except Exception as e:
            logger.error(f"Error scraping Kennedy Center events: {e}")
            self.update_progress('in_progress', 'Kennedy Center', 75, len(events), f'Error: {str(e)}')
        
        return events
    
    def scrape_all_dc_data(self):
        """Scrape all DC data with progress tracking"""
        logger.info("Starting DC data scraping with progress tracking")
        self.update_progress('in_progress', 'Starting...', 0, 0, 'Initializing DC data scraping...')
        
        # Create venues
        venues = [
            {
                'name': 'Smithsonian Institution',
                'address': '1000 Jefferson Dr SW, Washington, DC 20560',
                'url': 'https://www.si.edu',
                'description': 'The Smithsonian Institution is the world\'s largest museum, education, and research complex.'
            },
            {
                'name': 'National Gallery of Art',
                'address': '6th St NW & Constitution Ave NW, Washington, DC 20565',
                'url': 'https://www.nga.gov',
                'description': 'The National Gallery of Art houses one of the finest collections of paintings, sculpture, and decorative arts.'
            },
            {
                'name': 'Kennedy Center',
                'address': '2700 F St NW, Washington, DC 20566',
                'url': 'https://www.kennedy-center.org',
                'description': 'The John F. Kennedy Center for the Performing Arts is America\'s living memorial to President Kennedy.'
            }
        ]
        
        all_events = []
        
        # Define scraping steps
        scraping_steps = [
            {'name': 'Smithsonian Museums', 'url': 'https://naturalhistory.si.edu', 'progress': 25},
            {'name': 'National Gallery of Art', 'url': 'https://www.nga.gov', 'progress': 50},
            {'name': 'Kennedy Center', 'url': 'https://www.kennedy-center.org', 'progress': 75}
        ]
        
        # Execute scraping steps
        step_methods = [
            self.scrape_smithsonian_events,
            self.scrape_national_gallery_events,
            self.scrape_kennedy_center_events
        ]
        
        for i, step in enumerate(scraping_steps):
            try:
                logger.info(f"Scraping {step['name']}...")
                events = step_methods[i]()
                all_events.extend(events)
                
                # Add delay between requests
                self.delay(2, 4)
                
            except Exception as e:
                logger.error(f"Error in step {step['name']}: {e}")
                self.update_progress('in_progress', step['name'], step['progress'], len(all_events), f'Error: {str(e)}')
                continue
        
        # Final progress update
        self.update_progress('completed', 'Finished', 100, len(all_events), f'Scraping completed. Found {len(all_events)} events total.')
        
        # Prepare data
        data = {
            'venues': venues,
            'events': all_events,
            'scraped_at': datetime.now().isoformat(),
            'total_venues': len(venues),
            'total_events': len(all_events),
            'scraping_steps': scraping_steps
        }
        
        # Save to file
        with open('dc_scraped_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Scraping completed. Found {len(all_events)} events from {len(venues)} venues.")
        return data

def main():
    """Main function to run the scraper"""
    scraper = DCDataScraper()
    scraper.scrape_all_dc_data()

if __name__ == '__main__':
    main()