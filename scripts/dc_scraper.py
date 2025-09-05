#!/usr/bin/env python3
"""
Washington DC Data Scraper
Scrapes live data from DC museums, venues, and events
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime, timedelta, date
from urllib.parse import urljoin, urlparse
import re
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DCDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup Selenium WebDriver
        self.driver = None
        self.setup_driver()
        
        self.base_urls = {
            'smithsonian': 'https://www.si.edu',
            'national_gallery': 'https://www.nga.gov',
            'kennedy_center': 'https://www.kennedy-center.org',
            'library_congress': 'https://www.loc.gov',
            'national_archives': 'https://www.archives.gov',
            'holocaust_museum': 'https://www.ushmm.org',
            'spy_museum': 'https://www.spymuseum.org',
            'air_space': 'https://airandspace.si.edu',
            'natural_history': 'https://naturalhistory.si.edu',
            'american_history': 'https://americanhistory.si.edu'
        }
        
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            self.driver = None
        
    def delay(self):
        """Add random delay to be respectful"""
        time.sleep(random.uniform(2, 5))
        
    def scrape_smithsonian_events(self):
        """Scrape events from Smithsonian website"""
        logger.info("Scraping Smithsonian events...")
        events = []
        
        try:
            # Use Selenium to handle JavaScript
            if self.driver:
                self.driver.get("https://www.si.edu/events")
                self.delay()
                
                # Wait for events to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "event-item"))
                    )
                except TimeoutException:
                    logger.warning("Timeout waiting for Smithsonian events to load")
                    return events
                
                # Extract event data
                event_elements = self.driver.find_elements(By.CLASS_NAME, "event-item")
                
                for element in event_elements[:10]:  # Limit to 10 events
                    try:
                        title_elem = element.find_element(By.CLASS_NAME, "event-title")
                        title = title_elem.text.strip()
                        
                        # Try to get date
                        date_elem = element.find_element(By.CLASS_NAME, "event-date")
                        date_text = date_elem.text.strip()
                        
                        # Try to get venue
                        venue_elem = element.find_element(By.CLASS_NAME, "event-venue")
                        venue = venue_elem.text.strip()
                        
                        # Try to get description
                        desc_elem = element.find_element(By.CLASS_NAME, "event-description")
                        description = desc_elem.text.strip()
                        
                        # Try to get URL
                        link_elem = element.find_element(By.TAG_NAME, "a")
                        url = link_elem.get_attribute("href")
                        
                        event = {
                            'title': title,
                            'description': description,
                            'venue_name': venue,
                            'start_date': self.parse_date(date_text),
                            'url': url,
                            'source': 'Smithsonian'
                        }
                        events.append(event)
                        
                    except NoSuchElementException as e:
                        logger.warning(f"Could not extract event data: {e}")
                        continue
                        
            else:
                # Fallback to requests if Selenium fails
                response = self.session.get("https://www.si.edu/events")
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for event elements
                event_elements = soup.find_all('div', class_='event-item')
                
                for element in event_elements[:5]:  # Limit to 5 events
                    try:
                        title_elem = element.find('h3', class_='event-title')
                        title = title_elem.text.strip() if title_elem else "Smithsonian Event"
                        
                        date_elem = element.find('span', class_='event-date')
                        date_text = date_elem.text.strip() if date_elem else ""
                        
                        venue_elem = element.find('span', class_='event-venue')
                        venue = venue_elem.text.strip() if venue_elem else "Smithsonian Institution"
                        
                        desc_elem = element.find('p', class_='event-description')
                        description = desc_elem.text.strip() if desc_elem else "Smithsonian event"
                        
                        link_elem = element.find('a')
                        url = link_elem.get('href') if link_elem else ""
                        
                        event = {
                            'title': title,
                            'description': description,
                            'venue_name': venue,
                            'start_date': self.parse_date(date_text),
                            'url': url,
                            'source': 'Smithsonian'
                        }
                        events.append(event)
                        
                    except Exception as e:
                        logger.warning(f"Could not extract event data: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping Smithsonian events: {e}")
            
        logger.info(f"Scraped {len(events)} Smithsonian events")
        return events
        
    def scrape_national_gallery_events(self):
        """Scrape events from National Gallery of Art"""
        logger.info("Scraping National Gallery events...")
        events = []
        
        try:
            if self.driver:
                self.driver.get("https://www.nga.gov/calendar")
                self.delay()
                
                # Wait for calendar to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "calendar-event"))
                    )
                except TimeoutException:
                    logger.warning("Timeout waiting for National Gallery calendar to load")
                    return events
                
                # Extract event data
                event_elements = self.driver.find_elements(By.CLASS_NAME, "calendar-event")
                
                for element in event_elements[:8]:  # Limit to 8 events
                    try:
                        title_elem = element.find_element(By.CLASS_NAME, "event-title")
                        title = title_elem.text.strip()
                        
                        date_elem = element.find_element(By.CLASS_NAME, "event-date")
                        date_text = date_elem.text.strip()
                        
                        desc_elem = element.find_element(By.CLASS_NAME, "event-description")
                        description = desc_elem.text.strip()
                        
                        link_elem = element.find_element(By.TAG_NAME, "a")
                        url = link_elem.get_attribute("href")
                        
                        event = {
                            'title': title,
                            'description': description,
                            'venue_name': 'National Gallery of Art',
                            'start_date': self.parse_date(date_text),
                            'url': url,
                            'source': 'National Gallery'
                        }
                        events.append(event)
                        
                    except NoSuchElementException as e:
                        logger.warning(f"Could not extract National Gallery event data: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping National Gallery events: {e}")
            
        logger.info(f"Scraped {len(events)} National Gallery events")
        return events
        
    def scrape_kennedy_center_events(self):
        """Scrape events from Kennedy Center"""
        logger.info("Scraping Kennedy Center events...")
        events = []
        
        try:
            if self.driver:
                self.driver.get("https://www.kennedy-center.org/calendar")
                self.delay()
                
                # Wait for events to load
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "event-card"))
                    )
                except TimeoutException:
                    logger.warning("Timeout waiting for Kennedy Center events to load")
                    return events
                
                # Extract event data
                event_elements = self.driver.find_elements(By.CLASS_NAME, "event-card")
                
                for element in event_elements[:6]:  # Limit to 6 events
                    try:
                        title_elem = element.find_element(By.CLASS_NAME, "event-title")
                        title = title_elem.text.strip()
                        
                        date_elem = element.find_element(By.CLASS_NAME, "event-date")
                        date_text = date_elem.text.strip()
                        
                        desc_elem = element.find_element(By.CLASS_NAME, "event-description")
                        description = desc_elem.text.strip()
                        
                        link_elem = element.find_element(By.TAG_NAME, "a")
                        url = link_elem.get_attribute("href")
                        
                        event = {
                            'title': title,
                            'description': description,
                            'venue_name': 'Kennedy Center',
                            'start_date': self.parse_date(date_text),
                            'url': url,
                            'source': 'Kennedy Center'
                        }
                        events.append(event)
                        
                    except NoSuchElementException as e:
                        logger.warning(f"Could not extract Kennedy Center event data: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping Kennedy Center events: {e}")
            
        logger.info(f"Scraped {len(events)} Kennedy Center events")
        return events
        
    def parse_date(self, date_text):
        """Parse date text and return formatted date string"""
        if not date_text:
            return datetime.now().strftime('%Y-%m-%d')
            
        try:
            # Try to parse common date formats
            date_formats = [
                '%B %d, %Y',  # September 5, 2025
                '%b %d, %Y',  # Sep 5, 2025
                '%m/%d/%Y',   # 09/05/2025
                '%Y-%m-%d',   # 2025-09-05
                '%B %d',      # September 5
                '%b %d'       # Sep 5
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    # If no year, assume current year
                    if parsed_date.year == 1900:
                        parsed_date = parsed_date.replace(year=datetime.now().year)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
                    
            # If all parsing fails, return today's date
            return datetime.now().strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.warning(f"Could not parse date '{date_text}': {e}")
            return datetime.now().strftime('%Y-%m-%d')
            
    def create_venues(self):
        """Create venue data"""
        logger.info("Creating venue data...")
        
        venues = [
            {
                'name': 'Smithsonian National Museum of Natural History',
                'venue_type': 'museum',
                'address': '10th St. & Constitution Ave. NW, Washington, DC 20560',
                'latitude': 38.8913,
                'longitude': -77.0262,
                'image_url': 'https://naturalhistory.si.edu/sites/default/files/styles/hero_image/public/media/images/natural-history-museum-exterior.jpg',
                'website_url': 'https://naturalhistory.si.edu',
                'description': 'Explore the natural world through exhibits on dinosaurs, gems, human origins, and more.',
                'instagram_url': 'https://instagram.com/naturalhistory'
            },
            {
                'name': 'Smithsonian National Air and Space Museum',
                'venue_type': 'museum',
                'address': '600 Independence Ave SW, Washington, DC 20560',
                'latitude': 38.8882,
                'longitude': -77.0199,
                'image_url': 'https://airandspace.si.edu/sites/default/files/styles/hero_image/public/media/images/air-space-museum-exterior.jpg',
                'website_url': 'https://airandspace.si.edu',
                'description': 'Discover the history of aviation and space exploration through interactive exhibits.',
                'instagram_url': 'https://instagram.com/airandspacemuseum'
            },
            {
                'name': 'National Gallery of Art',
                'venue_type': 'museum',
                'address': '6th St. & Constitution Ave. NW, Washington, DC 20565',
                'latitude': 38.8914,
                'longitude': -77.0200,
                'image_url': 'https://www.nga.gov/content/ngaweb/collection/overview.html',
                'website_url': 'https://www.nga.gov',
                'description': 'Home to one of the finest collections of paintings, sculptures, and decorative arts.',
                'instagram_url': 'https://instagram.com/ngadc'
            },
            {
                'name': 'Kennedy Center',
                'venue_type': 'performing_arts',
                'address': '2700 F St NW, Washington, DC 20566',
                'latitude': 38.8969,
                'longitude': -77.0558,
                'image_url': 'https://www.kennedy-center.org/images/kennedy-center-exterior.jpg',
                'website_url': 'https://www.kennedy-center.org',
                'description': 'The national performing arts center featuring theater, music, and dance.',
                'instagram_url': 'https://instagram.com/kennedycenter'
            }
        ]
        
        return venues
        
    def scrape_all_dc_data(self):
        """Scrape all DC data"""
        logger.info("Starting DC data scraping...")
        
        # Create venues
        venues = self.create_venues()
        
        # Scrape events
        all_events = []
        
        # Define scraping steps with progress tracking
        scraping_steps = [
            {
                'name': 'Smithsonian Museums',
                'url': 'https://naturalhistory.si.edu',
                'method': self.scrape_smithsonian_events,
                'progress': 25
            },
            {
                'name': 'National Gallery of Art',
                'url': 'https://www.nga.gov',
                'method': self.scrape_national_gallery_events,
                'progress': 50
            },
            {
                'name': 'Kennedy Center',
                'url': 'https://www.kennedy-center.org',
                'method': self.scrape_kennedy_center_events,
                'progress': 75
            }
        ]
        
        # Only return real scraped data - no sample data
        if not all_events:
            logger.info("No real events were scraped from websites")
        
        # Create comprehensive dataset
        data = {
            'venues': venues,
            'events': all_events,
            'scraped_at': datetime.now().isoformat(),
            'total_venues': len(venues),
            'total_events': len(all_events),
            'scraping_steps': scraping_steps
        }
        
        # Save to JSON file
        with open('dc_scraped_data.json', 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Data saved to dc_scraped_data.json")
        logger.info(f"Scraped {len(venues)} venues")
        logger.info(f"Scraped {len(all_events)} events")
        
        return data
        
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

def main():
    """Main function"""
    scraper = DCDataScraper()
    
    try:
        data = scraper.scrape_all_dc_data()
        print(f"\nScraping completed!")
        print(f"Scraped {data['total_venues']} venues")
        print(f"Scraped {data['total_events']} events")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()
