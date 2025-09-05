import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from datetime import datetime, date, time as dt_time
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GenericEventScraper:
    """Generic scraper for museum and event websites"""
    
    def __init__(self, headless: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup Selenium for dynamic content
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        
    def scrape_museum_tours(self, museum_url: str, museum_name: str) -> List[Dict]:
        """Scrape tours from a museum website"""
        tours = []
        
        try:
            # Try requests first
            response = self.session.get(museum_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                tours.extend(self._parse_tours_from_soup(soup, museum_name, museum_url))
            
            # If no tours found, try Selenium for dynamic content
            if not tours:
                tours.extend(self._scrape_with_selenium(museum_url, museum_name))
                
        except Exception as e:
            logger.error(f"Error scraping {museum_name}: {e}")
            
        return tours
    
    def _parse_tours_from_soup(self, soup: BeautifulSoup, museum_name: str, base_url: str) -> List[Dict]:
        """Parse tours from BeautifulSoup object"""
        tours = []
        
        # Common selectors for tour information
        tour_selectors = [
            '.tour', '.event', '.program', '.activity',
            '[class*="tour"]', '[class*="event"]', '[class*="program"]'
        ]
        
        for selector in tour_selectors:
            tour_elements = soup.select(selector)
            
            for element in tour_elements:
                tour_data = self._extract_tour_data(element, museum_name, base_url)
                if tour_data:
                    tours.append(tour_data)
        
        return tours
    
    def _extract_tour_data(self, element, museum_name: str, base_url: str) -> Optional[Dict]:
        """Extract tour data from a single element"""
        try:
            # Extract title
            title_element = element.find(['h1', 'h2', 'h3', 'h4', '.title', '.name'])
            title = title_element.get_text(strip=True) if title_element else None
            
            if not title:
                return None
            
            # Extract description
            desc_element = element.find(['p', '.description', '.summary'])
            description = desc_element.get_text(strip=True) if desc_element else None
            
            # Extract time information
            time_info = self._extract_time_info(element)
            
            # Extract location
            location = self._extract_location(element)
            
            # Extract image
            image_url = self._extract_image_url(element, base_url)
            
            # Extract link
            link_element = element.find('a', href=True)
            link = link_element['href'] if link_element else None
            if link and not link.startswith('http'):
                link = f"{base_url.rstrip('/')}/{link.lstrip('/')}"
            
            return {
                'title': title,
                'description': description,
                'start_time': time_info.get('start_time'),
                'end_time': time_info.get('end_time'),
                'start_date': time_info.get('start_date'),
                'meeting_location': location,
                'image_url': image_url,
                'url': link,
                'museum_name': museum_name
            }
            
        except Exception as e:
            logger.error(f"Error extracting tour data: {e}")
            return None
    
    def _extract_time_info(self, element) -> Dict:
        """Extract time information from element"""
        time_info = {}
        
        # Look for time patterns
        text = element.get_text()
        
        # Time patterns (12-hour and 24-hour)
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*[-–—]\s*(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*to\s*(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*until\s*(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_hour, start_min, end_hour, end_min = match.groups()
                
                # Convert to 24-hour format
                start_time = self._convert_to_24hour(start_hour, start_min, text)
                end_time = self._convert_to_24hour(end_hour, end_min, text)
                
                time_info['start_time'] = start_time
                time_info['end_time'] = end_time
                break
        
        # Look for single time
        if not time_info:
            single_time_pattern = r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?'
            match = re.search(single_time_pattern, text)
            if match:
                hour, minute = match.groups()
                start_time = self._convert_to_24hour(hour, minute, text)
                time_info['start_time'] = start_time
        
        return time_info
    
    def _convert_to_24hour(self, hour: str, minute: str, context: str) -> Optional[str]:
        """Convert time to 24-hour format"""
        try:
            hour = int(hour)
            minute = int(minute)
            
            # Check if PM is mentioned in context
            is_pm = 'pm' in context.lower() or 'p.m.' in context.lower()
            
            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
            
        except ValueError:
            return None
    
    def _extract_location(self, element) -> Optional[str]:
        """Extract meeting location from element"""
        location_keywords = ['meet', 'location', 'entrance', 'lobby', 'rotunda', 'floor']
        
        text = element.get_text().lower()
        
        for keyword in location_keywords:
            # Look for sentences containing location keywords
            sentences = text.split('.')
            for sentence in sentences:
                if keyword in sentence:
                    return sentence.strip().capitalize()
        
        return None
    
    def _extract_image_url(self, element, base_url: str) -> Optional[str]:
        """Extract image URL from element"""
        img_element = element.find('img')
        if img_element and img_element.get('src'):
            img_url = img_element['src']
            if not img_url.startswith('http'):
                img_url = f"{base_url.rstrip('/')}/{img_url.lstrip('/')}"
            return img_url
        return None
    
    def _scrape_with_selenium(self, url: str, museum_name: str) -> List[Dict]:
        """Scrape using Selenium for dynamic content"""
        tours = []
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(url)
            
            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tours = self._parse_tours_from_soup(soup, museum_name, url)
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"Selenium scraping error for {museum_name}: {e}")
        
        return tours
    
    def scrape_instagram_events(self, instagram_url: str, city_name: str) -> List[Dict]:
        """Scrape events from Instagram accounts"""
        events = []
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(instagram_url)
            
            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for posts with event information
            posts = driver.find_elements(By.CSS_SELECTOR, 'article')
            
            for post in posts[:10]:  # Limit to recent posts
                try:
                    # Extract post text
                    text_element = post.find_element(By.CSS_SELECTOR, 'span')
                    text = text_element.text if text_element else ""
                    
                    # Look for event keywords
                    event_keywords = ['photowalk', 'tour', 'event', 'meetup', 'walk']
                    if any(keyword in text.lower() for keyword in event_keywords):
                        
                        # Extract image
                        img_element = post.find_element(By.CSS_SELECTOR, 'img')
                        image_url = img_element.get_attribute('src') if img_element else None
                        
                        events.append({
                            'title': text[:100] + "..." if len(text) > 100 else text,
                            'description': text,
                            'image_url': image_url,
                            'url': instagram_url,
                            'event_type': 'photowalk',
                            'city_name': city_name
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing Instagram post: {e}")
                    continue
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"Error scraping Instagram {instagram_url}: {e}")
        
        return events

def scrape_museum_data(museum_config: Dict) -> List[Dict]:
    """Scrape data for a specific museum"""
    scraper = GenericEventScraper()
    
    tours = scraper.scrape_museum_tours(
        museum_config['url'], 
        museum_config['name']
    )
    
    return tours

def scrape_city_events(city_config: Dict) -> Dict[str, List[Dict]]:
    """Scrape all events for a city"""
    scraper = GenericEventScraper()
    events = {
        'tours': [],
        'photowalks': []
    }
    
    # Scrape museum tours
    for museum in city_config.get('museums', []):
        tours = scraper.scrape_museum_tours(museum['url'], museum['name'])
        events['tours'].extend(tours)
    
    # Scrape Instagram photowalks
    for instagram_account in city_config.get('instagram_accounts', []):
        photowalks = scraper.scrape_instagram_events(
            instagram_account['url'], 
            city_config['name']
        )
        events['photowalks'].extend(photowalks)
    
    return events
