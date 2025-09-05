import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, time as dt_time, timedelta
from typing import List, Dict, Optional
import re
import logging
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmithsonianScraper:
    """Scraper for Smithsonian museums"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://www.si.edu"
    
    def scrape_natural_history_tours(self) -> List[Dict]:
        """Scrape tours from Smithsonian Natural History Museum"""
        tours = []
        
        try:
            # Natural History Museum tours page
            url = "https://naturalhistory.si.edu/visit/daily-tours"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for tour information
                tour_sections = soup.find_all(['div', 'section'], class_=re.compile(r'tour|program|event'))
                
                for section in tour_sections:
                    tour_data = self._extract_smithsonian_tour(section, "Smithsonian National Museum of Natural History")
                    if tour_data:
                        tours.append(tour_data)
                
                # Look for additional tour information
                additional_tours = self._find_additional_tours(soup, "Smithsonian National Museum of Natural History")
                tours.extend(additional_tours)
                
        except Exception as e:
            logger.error(f"Error scraping Natural History tours: {e}")
        
        return tours
    
    def scrape_air_space_tours(self) -> List[Dict]:
        """Scrape tours from Smithsonian Air and Space Museum"""
        tours = []
        
        try:
            url = "https://airandspace.si.edu/visit/things-do/tours"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for tour information
                tour_elements = soup.find_all(['div', 'article'], class_=re.compile(r'tour|program|event'))
                
                for element in tour_elements:
                    tour_data = self._extract_smithsonian_tour(element, "Smithsonian National Air and Space Museum")
                    if tour_data:
                        tours.append(tour_data)
                
        except Exception as e:
            logger.error(f"Error scraping Air and Space tours: {e}")
        
        return tours
    
    def _extract_smithsonian_tour(self, element, museum_name: str) -> Optional[Dict]:
        """Extract tour data from Smithsonian element"""
        try:
            # Extract title
            title_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5'], class_=re.compile(r'title|heading'))
            if not title_element:
                title_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            
            title = title_element.get_text(strip=True) if title_element else None
            
            if not title or len(title) < 5:
                return None
            
            # Extract description
            desc_element = element.find(['p', 'div'], class_=re.compile(r'description|summary|content'))
            if not desc_element:
                desc_element = element.find('p')
            
            description = desc_element.get_text(strip=True) if desc_element else None
            
            # Extract time information
            time_info = self._extract_smithsonian_time(element)
            
            # Extract location
            location = self._extract_smithsonian_location(element)
            
            # Extract image
            image_url = self._extract_image_url(element)
            
            # Extract link
            link_element = element.find('a', href=True)
            link = link_element['href'] if link_element else None
            if link and not link.startswith('http'):
                link = urljoin(self.base_url, link)
            
            return {
                'title': title,
                'description': description,
                'start_time': time_info.get('start_time'),
                'end_time': time_info.get('end_time'),
                'start_date': time_info.get('start_date'),
                'meeting_location': location,
                'image_url': image_url,
                'url': link,
                'museum_name': museum_name,
                'tour_type': time_info.get('tour_type', 'general')
            }
            
        except Exception as e:
            logger.error(f"Error extracting Smithsonian tour: {e}")
            return None
    
    def _extract_smithsonian_time(self, element) -> Dict:
        """Extract time information from Smithsonian element"""
        time_info = {}
        text = element.get_text()
        
        # Smithsonian specific time patterns
        patterns = [
            # Daily at specific times
            r'daily\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'every\s+day\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*daily',
            
            # Specific days
            r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            
            # Time ranges
            r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*[-–—]\s*(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    hour, minute = groups[0], groups[1]
                    start_time = self._convert_to_24hour(hour, minute, text)
                    time_info['start_time'] = start_time
                    
                    # Check if it's a time range
                    if len(groups) >= 4:
                        end_hour, end_minute = groups[2], groups[3]
                        end_time = self._convert_to_24hour(end_hour, end_minute, text)
                        time_info['end_time'] = end_time
                    
                    # Determine tour type
                    if 'daily' in text.lower() or 'every day' in text.lower():
                        time_info['tour_type'] = 'daily'
                    elif any(day in text.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                        time_info['tour_type'] = 'weekly'
                    
                    break
        
        return time_info
    
    def _extract_smithsonian_location(self, element) -> Optional[str]:
        """Extract meeting location from Smithsonian element"""
        text = element.get_text().lower()
        
        # Common Smithsonian meeting locations
        locations = [
            'ocean hall entrance',
            'main entrance',
            'constitution avenue entrance',
            'rotunda',
            'fossil hall',
            'dinosaur hall',
            'human origins hall',
            'ground floor',
            'first floor',
            'second floor',
            'information desk',
            'visitor services'
        ]
        
        for location in locations:
            if location in text:
                return location.title()
        
        return None
    
    def _extract_image_url(self, element) -> Optional[str]:
        """Extract image URL from element"""
        img_element = element.find('img')
        if img_element and img_element.get('src'):
            img_url = img_element['src']
            if not img_url.startswith('http'):
                img_url = urljoin(self.base_url, img_url)
            return img_url
        return None
    
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

class NationalGalleryScraper:
    """Scraper for National Gallery of Art"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://www.nga.gov"
    
    def scrape_tours(self) -> List[Dict]:
        """Scrape tours from National Gallery of Art"""
        tours = []
        
        try:
            # National Gallery tours page
            url = "https://www.nga.gov/visit/tours.html"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for tour information
                tour_sections = soup.find_all(['div', 'section', 'article'], class_=re.compile(r'tour|program|event'))
                
                for section in tour_sections:
                    tour_data = self._extract_nga_tour(section)
                    if tour_data:
                        tours.append(tour_data)
                
                # Look for additional tour information
                additional_tours = self._find_additional_tours(soup, "National Gallery of Art")
                tours.extend(additional_tours)
                
        except Exception as e:
            logger.error(f"Error scraping National Gallery tours: {e}")
        
        return tours
    
    def _extract_nga_tour(self, element) -> Optional[Dict]:
        """Extract tour data from National Gallery element"""
        try:
            # Extract title
            title_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5'], class_=re.compile(r'title|heading'))
            if not title_element:
                title_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            
            title = title_element.get_text(strip=True) if title_element else None
            
            if not title or len(title) < 5:
                return None
            
            # Extract description
            desc_element = element.find(['p', 'div'], class_=re.compile(r'description|summary|content'))
            if not desc_element:
                desc_element = element.find('p')
            
            description = desc_element.get_text(strip=True) if desc_element else None
            
            # Extract time information
            time_info = self._extract_nga_time(element)
            
            # Extract location
            location = self._extract_nga_location(element)
            
            # Extract image
            image_url = self._extract_image_url(element)
            
            # Extract link
            link_element = element.find('a', href=True)
            link = link_element['href'] if link_element else None
            if link and not link.startswith('http'):
                link = urljoin(self.base_url, link)
            
            return {
                'title': title,
                'description': description,
                'start_time': time_info.get('start_time'),
                'end_time': time_info.get('end_time'),
                'start_date': time_info.get('start_date'),
                'meeting_location': location,
                'image_url': image_url,
                'url': link,
                'museum_name': 'National Gallery of Art',
                'tour_type': time_info.get('tour_type', 'general')
            }
            
        except Exception as e:
            logger.error(f"Error extracting National Gallery tour: {e}")
            return None
    
    def _extract_nga_time(self, element) -> Dict:
        """Extract time information from National Gallery element"""
        time_info = {}
        text = element.get_text()
        
        # National Gallery specific time patterns
        patterns = [
            # Daily tours
            r'daily\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'every\s+day\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*daily',
            
            # Specific days
            r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            
            # Time ranges
            r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*[-–—]\s*(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    hour, minute = groups[0], groups[1]
                    start_time = self._convert_to_24hour(hour, minute, text)
                    time_info['start_time'] = start_time
                    
                    # Check if it's a time range
                    if len(groups) >= 4:
                        end_hour, end_minute = groups[2], groups[3]
                        end_time = self._convert_to_24hour(end_hour, end_minute, text)
                        time_info['end_time'] = end_time
                    
                    # Determine tour type
                    if 'daily' in text.lower() or 'every day' in text.lower():
                        time_info['tour_type'] = 'daily'
                    elif any(day in text.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                        time_info['tour_type'] = 'weekly'
                    
                    break
        
        return time_info
    
    def _extract_nga_location(self, element) -> Optional[str]:
        """Extract meeting location from National Gallery element"""
        text = element.get_text().lower()
        
        # Common National Gallery meeting locations
        locations = [
            'west building rotunda',
            'east building entrance',
            'main entrance',
            'constitution avenue entrance',
            'madison drive entrance',
            'information desk',
            'visitor services',
            'ground floor',
            'first floor',
            'second floor'
        ]
        
        for location in locations:
            if location in text:
                return location.title()
        
        return None
    
    def _extract_image_url(self, element) -> Optional[str]:
        """Extract image URL from element"""
        img_element = element.find('img')
        if img_element and img_element.get('src'):
            img_url = img_element['src']
            if not img_url.startswith('http'):
                img_url = urljoin(self.base_url, img_url)
            return img_url
        return None
    
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
    
    def _find_additional_tours(self, soup, museum_name: str) -> List[Dict]:
        """Find additional tour information in the page"""
        tours = []
        
        # Look for common tour patterns in text
        text = soup.get_text()
        
        # Common tour patterns
        tour_patterns = [
            r'daily\s+tours?\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'guided\s+tours?\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
            r'highlights\s+tour\s+at\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?',
        ]
        
        for pattern in tour_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                hour, minute = match.groups()
                start_time = self._convert_to_24hour(hour, minute, text)
                
                tour_data = {
                    'title': f'Daily Tour at {hour}:{minute}',
                    'description': f'Regular guided tour of {museum_name}',
                    'start_time': start_time,
                    'end_time': None,  # Will be calculated
                    'meeting_location': 'Main entrance',
                    'museum_name': museum_name,
                    'tour_type': 'daily'
                }
                
                # Calculate end time (assume 1 hour duration)
                if start_time:
                    try:
                        start_hour, start_min = map(int, start_time.split(':'))
                        end_hour = (start_hour + 1) % 24
                        tour_data['end_time'] = f"{end_hour:02d}:{start_min:02d}"
                    except:
                        pass
                
                tours.append(tour_data)
        
        return tours

def scrape_washington_dc_museums() -> Dict[str, List[Dict]]:
    """Scrape all Washington DC museums"""
    events = {
        'tours': [],
        'exhibitions': []
    }
    
    # Scrape Smithsonian museums
    smithsonian_scraper = SmithsonianScraper()
    
    # Natural History Museum tours
    natural_history_tours = smithsonian_scraper.scrape_natural_history_tours()
    events['tours'].extend(natural_history_tours)
    
    # Air and Space Museum tours
    air_space_tours = smithsonian_scraper.scrape_air_space_tours()
    events['tours'].extend(air_space_tours)
    
    # Scrape National Gallery
    nga_scraper = NationalGalleryScraper()
    nga_tours = nga_scraper.scrape_tours()
    events['tours'].extend(nga_tours)
    
    return events

if __name__ == "__main__":
    # Test the scrapers
    events = scrape_washington_dc_museums()
    
    print(f"Found {len(events['tours'])} tours")
    for tour in events['tours'][:5]:  # Show first 5
        print(f"- {tour['title']} at {tour['start_time']} ({tour['museum_name']})")
