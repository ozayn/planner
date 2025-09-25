#!/usr/bin/env python3
"""
Image Event Processor

This module handles image upload, OCR text extraction, and event creation
from images containing event information (dates, times, descriptions, etc.)
"""

import os
import re
import json
import logging
import tempfile
from datetime import datetime, date, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import pytesseract
from google.cloud import vision
from google.cloud.vision_v1 import types as vision_types

# Setup logging
logger = logging.getLogger(__name__)

def setup_google_credentials():
    """Setup Google credentials from JSON environment variable if available"""
    json_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if json_creds:
        try:
            # Parse the JSON credentials
            creds_data = json.loads(json_creds)
            
            # Create a temporary file with the credentials
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(creds_data, f)
                temp_file = f.name
            
            # Set the environment variable to point to the temp file
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file
            logger.info("Google credentials set up from JSON environment variable")
            return temp_file
        except Exception as e:
            logger.warning(f"Failed to set up Google credentials from JSON: {e}")
    return None

@dataclass
class ExtractedEventData:
    """Data structure for extracted event information"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    event_type: Optional[str] = None
    price: Optional[float] = None
    organizer: Optional[str] = None
    url: Optional[str] = None
    confidence: float = 0.0
    # City information
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    # Source information
    source: Optional[str] = None
    source_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    # Database IDs
    city_id: Optional[int] = None
    # Location fields
    start_location: Optional[str] = None
    end_location: Optional[str] = None

class ImageEventProcessor:
    """Main class for processing images and extracting event data"""
    
    def __init__(self):
        self.ocr_engine = self._setup_ocr_engine()
        self.date_patterns = self._compile_date_patterns()
        self.time_patterns = self._compile_time_patterns()
        self.event_type_keywords = self._setup_event_type_keywords()
        self.city_mappings = self._setup_city_mappings()
        self.source_data = self._load_source_data()
        self.city_data = self._load_city_data()
    
    def _setup_ocr_engine(self) -> str:
        """Setup OCR engine (Google Vision preferred, Tesseract fallback)"""
        # Setup Google credentials from JSON if available
        setup_google_credentials()
        
        # Try Google Cloud Vision first for better accuracy
        try:
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            logger.info("Using Google Cloud Vision OCR engine")
            return 'google_vision'
        except Exception as e:
            logger.warning(f"Google Vision not available: {e}")
        
        # Fall back to Tesseract if Google Vision fails
        try:
            pytesseract.get_tesseract_version()
            logger.info("Using Tesseract OCR engine")
            return 'tesseract'
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
        
        # Only try Google Cloud Vision if we have proper credentials
        # Check for both service account file and application default credentials
        has_google_creds = (
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or 
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON') or
            os.getenv('GOOGLE_CLIENT_ID') or
            os.path.exists(os.path.expanduser('~/.config/gcloud/application_default_credentials.json'))
        )
        
        if has_google_creds:
            try:
                # Test if we can actually create a client
                client = vision.ImageAnnotatorClient()
                logger.info("Using Google Cloud Vision OCR engine")
                return 'google_vision'
            except Exception as e:
                logger.warning(f"Google Vision credentials found but client creation failed: {e}")
        
        # Last resort - try Tesseract anyway (might work even if version check failed)
        logger.warning("No OCR engine properly configured, attempting Tesseract anyway")
        return 'tesseract'
    
    def _compile_date_patterns(self) -> List[re.Pattern]:
        """Compile comprehensive regex patterns for date extraction"""
        patterns = [
            # Standard formats with year
            re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b'),  # MM/DD/YYYY
            re.compile(r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b'),  # MM-DD-YYYY
            re.compile(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b'),  # YYYY-MM-DD
            re.compile(r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b'),  # MM.DD.YYYY
            re.compile(r'\b(\d{1,2})\s+(\d{1,2})\s+(\d{4})\b'),  # MM DD YYYY
            
            # Full month names with year
            re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b', re.IGNORECASE),
            re.compile(r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', re.IGNORECASE),
            re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\b', re.IGNORECASE),
            
            # Full month names with ordinal numbers (28th, 1st, 2nd, 3rd, etc.)
            re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)\b', re.IGNORECASE),
            re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th),?\s+(\d{4})\b', re.IGNORECASE),
            
            # Abbreviated month names with year
            re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})\b', re.IGNORECASE),
            re.compile(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+(\d{4})\b', re.IGNORECASE),
            
            # Abbreviated month names without year (assume current year)
            re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+(\d{1,2})\b', re.IGNORECASE),
            re.compile(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', re.IGNORECASE),
            
            # Numeric formats without year (assume current year)
            re.compile(r'\b(\d{1,2})/(\d{1,2})\b'),  # MM/DD
            re.compile(r'\b(\d{1,2})-(\d{1,2})\b'),  # MM-DD
            re.compile(r'\b(\d{1,2})\.(\d{1,2})\b'),  # MM.DD
            re.compile(r'\b(\d{1,2})\s+(\d{1,2})\b'),  # MM DD
            
            # Special formats
            re.compile(r'\b(\d{1,2})st\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', re.IGNORECASE),  # 1st Jan
            re.compile(r'\b(\d{1,2})nd\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', re.IGNORECASE),  # 2nd Jan
            re.compile(r'\b(\d{1,2})rd\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', re.IGNORECASE),  # 3rd Jan
            re.compile(r'\b(\d{1,2})th\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b', re.IGNORECASE),  # 4th Jan
        ]
        logger.info(f"Compiled {len(patterns)} comprehensive date patterns")
        return patterns
    
    def _compile_time_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for time extraction"""
        patterns = [
            # HH:MM AM/PM
            re.compile(r'\b(\d{1,2}):(\d{2})\s*(AM|PM)\b', re.IGNORECASE),
            # HH:MM
            re.compile(r'\b(\d{1,2}):(\d{2})\b'),
            # H AM/PM
            re.compile(r'\b(\d{1,2})\s*(AM|PM)\b', re.IGNORECASE),
        ]
        return patterns
    
    def _setup_event_type_keywords(self) -> Dict[str, List[str]]:
        """Setup keywords for event type detection"""
        return {
            'tour': ['tour', 'guided tour', 'walking tour', 'museum tour', 'city tour', 'heritage tour'],
            'exhibition': ['exhibition', 'exhibit', 'show', 'gallery', 'art show', 'display', 'collection'],
            'festival': ['festival', 'celebration', 'fair', 'carnival', 'event', 'fest', 'gathering'],
            'photowalk': ['photowalk', 'photo walk', 'photography', 'photo tour', 'camera walk', 'photo session', 'streetmeet', 'street meet', 'meetup']
        }
    
    def _setup_city_mappings(self) -> Dict[str, Dict[str, str]]:
        """Setup city/state mappings for location extraction"""
        return {
            # Washington, DC area
            'dc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'washington dc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'washington, dc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'washington d.c.': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'rhode island ave': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'dupont circle': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'georgetown': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'capitol hill': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'national mall': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'streetmeetdc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'streetmeetoc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},  # OCR correction
            
            # New York
            'nyc': {'city': 'New York', 'state': 'NY', 'country': 'United States'},
            'new york city': {'city': 'New York', 'state': 'NY', 'country': 'United States'},
            'manhattan': {'city': 'New York', 'state': 'NY', 'country': 'United States'},
            'brooklyn': {'city': 'New York', 'state': 'NY', 'country': 'United States'},
            'queens': {'city': 'New York', 'state': 'NY', 'country': 'United States'},
            
            # Los Angeles
            'la': {'city': 'Los Angeles', 'state': 'CA', 'country': 'United States'},
            'los angeles': {'city': 'Los Angeles', 'state': 'CA', 'country': 'United States'},
            'hollywood': {'city': 'Los Angeles', 'state': 'CA', 'country': 'United States'},
            
            # San Francisco
            'sf': {'city': 'San Francisco', 'state': 'CA', 'country': 'United States'},
            'san francisco': {'city': 'San Francisco', 'state': 'CA', 'country': 'United States'},
            'bay area': {'city': 'San Francisco', 'state': 'CA', 'country': 'United States'},
            
            # Chicago
            'chicago': {'city': 'Chicago', 'state': 'IL', 'country': 'United States'},
            'the loop': {'city': 'Chicago', 'state': 'IL', 'country': 'United States'},
            
            # Boston
            'boston': {'city': 'Boston', 'state': 'MA', 'country': 'United States'},
            'back bay': {'city': 'Boston', 'state': 'MA', 'country': 'United States'},
            
            # International cities
            'london': {'city': 'London', 'state': None, 'country': 'United Kingdom'},
            'paris': {'city': 'Paris', 'state': None, 'country': 'France'},
            'tokyo': {'city': 'Tokyo', 'state': None, 'country': 'Japan'},
            'sydney': {'city': 'Sydney', 'state': 'NSW', 'country': 'Australia'},
            'toronto': {'city': 'Toronto', 'state': 'ON', 'country': 'Canada'},
            'montreal': {'city': 'Montreal', 'state': 'QC', 'country': 'Canada'},
            'vancouver': {'city': 'Vancouver', 'state': 'BC', 'country': 'Canada'},
        }
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            if self.ocr_engine == 'google_vision':
                try:
                    text = self._extract_text_google_vision(image_path)
                    if text:
                        logger.info("Successfully extracted text using Google Vision")
                    else:
                        logger.warning("Google Vision returned empty text, falling back to Tesseract")
                        text = self._extract_text_tesseract(image_path)
                except Exception as e:
                    error_msg = str(e)
                    if "credentials" in error_msg.lower() or "authentication" in error_msg.lower():
                        logger.error(f"Google Vision authentication failed: {e}")
                        logger.info("Falling back to Tesseract due to credential issues")
                    else:
                        logger.warning(f"Google Vision failed: {e}, falling back to Tesseract")
                    text = self._extract_text_tesseract(image_path)
            elif self.ocr_engine == 'tesseract':
                text = self._extract_text_tesseract(image_path)
            else:
                logger.warning("No OCR engine available, returning empty text")
                text = ""
            
            # Apply OCR text corrections for common misreadings
            text = self._correct_ocr_text(text)
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            # Provide more specific error information
            error_msg = str(e)
            if "tesseract" in error_msg.lower() or "command not found" in error_msg.lower():
                return "OCR Error: Tesseract not installed. Please contact administrator."
            elif "google" in error_msg.lower() or "vision" in error_msg.lower():
                return "OCR Error: Google Vision API issue. Please try again or contact administrator."
            else:
                return f"OCR Error: {error_msg}"
    
    def _extract_text_google_vision(self, image_path: str) -> str:
        """Extract text using Google Cloud Vision API"""
        try:
            client = vision.ImageAnnotatorClient()
            
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision_types.Image(content=content)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                return texts[0].description
            return ""
        except Exception as e:
            logger.error(f"Google Vision API error: {e}")
            return ""
    
    def _extract_text_tesseract(self, image_path: str) -> str:
        """Extract text using Tesseract OCR with multiple fallback methods"""
        try:
            image = Image.open(image_path)
            
            # Try different PSM modes to get better results
            psm_modes = [6, 3, 8, 13]  # Different page segmentation modes
            best_text = ""
            best_confidence = 0
            
            for psm in psm_modes:
                try:
                    # Extract text with confidence scores
                    data = pytesseract.image_to_data(image, config=f'--psm {psm}', output_type=pytesseract.Output.DICT)
                    
                    # Calculate average confidence
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Extract text
                    text = pytesseract.image_to_string(image, config=f'--psm {psm}')
                    
                    # Clean up the text
                    text = self._clean_ocr_text(text)
                    
                    # Choose the result with highest confidence and reasonable length
                    if avg_confidence > best_confidence and len(text.strip()) > 5:
                        best_text = text
                        best_confidence = avg_confidence
                        
                    logger.info(f"PSM {psm}: confidence={avg_confidence:.1f}, text_length={len(text)}")
                    
                except Exception as e:
                    logger.warning(f"PSM {psm} failed: {e}")
                    continue
            
            # If we got garbled text, try a simpler approach
            if self._is_garbled_text(best_text):
                logger.warning("Detected garbled text, trying simpler extraction")
                try:
                    # Try with basic settings
                    simple_text = pytesseract.image_to_string(image, config='--psm 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#.,:!? ')
                    simple_text = self._clean_ocr_text(simple_text)
                    
                    if not self._is_garbled_text(simple_text) and len(simple_text.strip()) > 3:
                        return simple_text
                except Exception as e:
                    logger.warning(f"Simple extraction failed: {e}")
            
            return best_text if best_text else ""
            
        except Exception as e:
            logger.error(f"Tesseract OCR error: {e}")
            return ""
    
    def parse_extracted_text(self, text: str) -> ExtractedEventData:
        """Parse extracted text to find event information"""
        event_data = ExtractedEventData()
        
        if not text.strip():
            return event_data
        
        # Extract dates
        dates = self._extract_dates(text)
        if dates:
            event_data.start_date = dates[0]
            if len(dates) > 1:
                event_data.end_date = dates[1]
            else:
                # If only start date found, assume same date for end date
                event_data.end_date = dates[0]
        
        # Extract times
        times = self._extract_times(text)
        if times:
            event_data.start_time = times[0]
            # Check if we have multiple different times
            unique_times = list(set(times))
            if len(unique_times) > 1:
                # Find the best end time candidate (not timestamps)
                end_time_candidate = self._find_best_end_time(unique_times, text)
                if end_time_candidate:
                    event_data.end_time = end_time_candidate
                else:
                    # If no good end time found, estimate it
                    event_data.end_time = self._estimate_end_time(times[0], text)
            else:
                # If only one unique time found, estimate end time (2 hours default)
                event_data.end_time = self._estimate_end_time(times[0], text)
        else:
            logger.info("No times found in text")
        
        # Extract event type
        event_data.event_type = self._extract_event_type(text)
        
        # Extract title (usually the first line or most prominent text)
        event_data.title = self._extract_title(text)
        
        # Extract description
        event_data.description = self._extract_description(text)
        
        # Extract location
        event_data.location = self._extract_location(text)
        
        # Set start and end locations
        if event_data.location:
            event_data.start_location = event_data.location
            # Intelligently estimate end location
            event_data.end_location = self._estimate_end_location(event_data.location, text)
        
        # Set end date to start date if not explicitly mentioned
        if event_data.start_date and not event_data.end_date:
            event_data.end_date = event_data.start_date
        
        # Set end location to start location if not explicitly mentioned
        if event_data.start_location and not event_data.end_location:
            event_data.end_location = event_data.start_location
        
        # Extract price
        event_data.price = self._extract_price(text)
        
        # Extract organizer
        event_data.organizer = self._extract_organizer(text)
        
        # Extract URL
        event_data.url = self._extract_url(text)
        
        # Extract city information
        city_info = self._extract_city_info(text)
        if city_info['city']:
            event_data.city = city_info['city']
            event_data.state = city_info['state']
            event_data.country = city_info['country']
            
            # Look up city ID
            city_id = self._lookup_city_id(city_info['city'], city_info['state'])
            if city_id:
                event_data.city_id = city_id
                logger.info(f"Found city ID {city_id} for {city_info['city']}, {city_info['state']}")
            else:
                logger.warning(f"Could not find city ID for {city_info['city']}, {city_info['state']}")
        
        # Extract Instagram information and source
        instagram_info = self._extract_instagram_info(text)
        if instagram_info['is_instagram']:
            event_data.source = 'instagram'
            event_data.instagram_handle = instagram_info['handle']
            event_data.source_url = instagram_info['url']
        
        # Enhance with source data if available
        event_data = self._enhance_with_source_data(event_data)
        
        # Calculate confidence based on extracted fields
        event_data.confidence = self._calculate_confidence(event_data)
        
        return event_data
    
    def _extract_dates(self, text: str) -> List[date]:
        """Smart date extraction with multiple strategies and context awareness"""
        dates = []
        logger.info(f"Smart date extraction from text: {text}")
        
        # Strategy 1: Direct pattern matching with context validation
        pattern_dates = self._extract_dates_by_patterns(text)
        dates.extend(pattern_dates)
        
        # Strategy 2: Natural language processing for date mentions
        nlp_dates = self._extract_dates_by_nlp(text)
        dates.extend(nlp_dates)
        
        # Strategy 3: Context-aware extraction (look for event-related dates)
        context_dates = self._extract_dates_by_context(text)
        dates.extend(context_dates)
        
        # Remove duplicates and sort by confidence
        unique_dates = list(set(dates))
        logger.info(f"Found {len(unique_dates)} unique dates: {unique_dates}")
        
        return sorted(unique_dates)
    
    def _filter_ui_elements(self, text: str) -> str:
        """Filter out obvious UI elements that might be mistaken for dates"""
        # Remove common Instagram UI patterns
        ui_patterns = [
            r'\b\d+\s*%\b',  # Percentage like "87%"
            r'\b\d+\s*▾\b',  # Dropdown arrow like "3 8 ▾"
            r'\b\d+\s*likes?\b',  # Like counts
            r'\b\d+\s*days?\s*ago\b',  # Time stamps
            r'\b\d+\s*hours?\s*ago\b',  # Time stamps
            r'\b\d+\s*weeks?\s*ago\b',  # Time stamps
            r'\b\d+\s*months?\s*ago\b',  # Time stamps
            r'\b\d+\s*years?\s*ago\b',  # Time stamps
        ]
        
        filtered_text = text
        for pattern in ui_patterns:
            filtered_text = re.sub(pattern, '', filtered_text, flags=re.IGNORECASE)
        
        return filtered_text
    
    def _is_valid_event_date(self, parsed_date: date, text: str) -> bool:
        """Check if a parsed date looks like a real event date"""
        # Check if the date is in the future (events are usually future dates)
        today = date.today()
        if parsed_date < today:
            # Allow dates within the last 30 days (for ongoing events)
            if (today - parsed_date).days > 30:
                return False
        
        # Check if the date appears in context that suggests it's an event date
        event_context_keywords = [
            'event', 'meet', 'gathering', 'tour', 'exhibition', 'festival',
            'join', 'attend', 'come', 'visit', 'at', 'on', 'pm', 'am'
        ]
        
        # Look for context around the date in the text
        date_str = parsed_date.strftime('%B %d')  # "September 28"
        date_str_alt = parsed_date.strftime('%b %d')  # "Sep 28"
        
        # Check if date appears near event-related keywords
        text_lower = text.lower()
        for keyword in event_context_keywords:
            if keyword in text_lower:
                # Check if date appears near this keyword
                keyword_pos = text_lower.find(keyword)
                date_pos1 = text_lower.find(date_str.lower())
                date_pos2 = text_lower.find(date_str_alt.lower())
                
                if keyword_pos != -1 and (date_pos1 != -1 or date_pos2 != -1):
                    return True
        
        # If no clear context, be more lenient but still filter obvious UI elements
        return True
    
    def _extract_dates_by_patterns(self, text: str) -> List[date]:
        """Extract dates using comprehensive pattern matching with smart filtering"""
        dates = []
        
        # Filter out UI elements first
        filtered_text = self._filter_ui_elements(text)
        
        for i, pattern in enumerate(self.date_patterns):
            matches = pattern.findall(filtered_text)
            if matches:
                logger.info(f"Pattern {i+1} ({pattern.pattern}) found matches: {matches}")
            
            for match in matches:
                try:
                    parsed_date = self._parse_date_match(match, pattern.pattern)
                    if parsed_date and self._is_valid_event_date(parsed_date, filtered_text):
                        dates.append(parsed_date)
                        logger.info(f"Added pattern date: {parsed_date}")
                except (ValueError, TypeError) as e:
                    logger.info(f"Failed to parse date match {match}: {e}")
                    continue
        
        return dates
    
    def _extract_dates_by_nlp(self, text: str) -> List[date]:
        """Extract dates using natural language processing approach"""
        dates = []
        
        # Look for natural language date expressions
        nlp_patterns = [
            # "Join us on September 28th"
            r'join\s+us\s+on\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?',
            # "Come to our event on Sep 28"
            r'event\s+on\s+(\w+)\s+(\d{1,2})',
            # "This Saturday", "Next Friday", etc.
            r'(this|next)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            # "Tomorrow", "Today"
            r'\b(tomorrow|today)\b',
            # "In 3 days", "Next week"
            r'(in\s+\d+\s+days?|next\s+week)',
        ]
        
        for pattern in nlp_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    parsed_date = self._parse_nlp_date(match.group(), text)
                    if parsed_date:
                        dates.append(parsed_date)
                        logger.info(f"Added NLP date: {parsed_date}")
                except Exception as e:
                    logger.info(f"Failed to parse NLP date {match.group()}: {e}")
                    continue
        
        return dates
    
    def _extract_dates_by_context(self, text: str) -> List[date]:
        """Extract dates by looking for event-related context"""
        dates = []
        
        # Split text into sentences/phrases
        sentences = re.split(r'[.!?]', text)
        
        for sentence in sentences:
            # Look for event-related keywords
            event_keywords = ['meet', 'gathering', 'event', 'tour', 'exhibition', 'festival', 'join', 'attend']
            
            if any(keyword in sentence.lower() for keyword in event_keywords):
                # Extract any date-like patterns from this sentence
                date_patterns = [
                    r'\b(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?\b',  # "September 28th"
                    r'\b(\d{1,2})/(\d{1,2})\b',  # "9/28"
                    r'\b(\d{1,2})-(\d{1,2})\b',  # "9-28"
                ]
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, sentence)
                    for match in matches:
                        try:
                            parsed_date = self._parse_context_date(match, sentence)
                            if parsed_date:
                                dates.append(parsed_date)
                                logger.info(f"Added context date: {parsed_date}")
                        except Exception as e:
                            logger.info(f"Failed to parse context date {match}: {e}")
                            continue
        
        return dates
    
    def _parse_nlp_date(self, date_expression: str, full_text: str) -> Optional[date]:
        """Parse natural language date expressions"""
        today = date.today()
        
        if 'tomorrow' in date_expression.lower():
            return today + timedelta(days=1)
        elif 'today' in date_expression.lower():
            return today
        elif 'this' in date_expression.lower() or 'next' in date_expression.lower():
            # Handle "this Saturday", "next Friday", etc.
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            for i, day in enumerate(days):
                if day in date_expression.lower():
                    target_weekday = i
                    current_weekday = today.weekday()
                    days_ahead = target_weekday - current_weekday
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    return today + timedelta(days=days_ahead)
        
        return None
    
    def _parse_context_date(self, match: tuple, sentence: str) -> Optional[date]:
        """Parse date from context-aware extraction"""
        try:
            if len(match) == 2:
                part1, part2 = match
                
                # Try to parse as month day
                if part1.isalpha() and part2.isdigit():
                    month_name = part1.lower()
                    day = int(part2)
                    
                    month_map = {
                        'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
                        'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
                        'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                        'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
                        'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
                        'december': 12, 'dec': 12
                    }
                    
                    if month_name in month_map:
                        month = month_map[month_name]
                        current_year = datetime.now().year
                        return date(current_year, month, day)
                
                # Try to parse as month/day
                elif part1.isdigit() and part2.isdigit():
                    month = int(part1)
                    day = int(part2)
                    
                    # Assume MM/DD format
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        current_year = datetime.now().year
                        return date(current_year, month, day)
        
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _parse_date_match(self, match: tuple, pattern: str) -> Optional[date]:
        """Parse a date match tuple based on the pattern used"""
        current_year = datetime.now().year
        logger.info(f"Parsing date match: {match} with pattern: {pattern}")
        
        # Simple, direct approach for ordinal patterns
        logger.info(f"Checking ordinal pattern: len(match)={len(match)}, pattern contains ordinal: {'(?:st|nd|rd|th)' in pattern}")
        if len(match) == 2 and '(?:st|nd|rd|th)' in pattern:
            # This is an ordinal pattern like "September 28th"
            logger.info(f"Processing ordinal pattern: {match}")
            month_name, day = match
            month_num = self._month_name_to_number(month_name)
            if month_num:
                result_date = date(current_year, month_num, int(day))
                logger.info(f"✅ Successfully parsed ordinal date: {result_date}")
                return result_date
        
        if len(match) == 3:
            # Three-component matches
            if '/' in pattern or '-' in pattern or '.' in pattern:
                # Numeric formats: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD, etc.
                if pattern.startswith(r'\b(\d{4})'):  # YYYY-MM-DD format
                    year, month, day = match
                    return date(int(year), int(month), int(day))
                else:  # MM/DD/YYYY or MM-DD-YYYY format
                    month, day, year = match
                    return date(int(year), int(month), int(day))
            else:
                # Month name formats
                if any(month_name in pattern.lower() for month_name in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
                    # Full month name format
                    if pattern.startswith(r'\b(January|February'):
                        month_name, day, year = match
                        month_num = self._month_name_to_number(month_name)
                        if month_num:
                            return date(int(year), month_num, int(day))
                    else:
                        day, month_name, year = match
                        month_num = self._month_name_to_number(month_name)
                        if month_num:
                            return date(int(year), month_num, int(day))
                
                # Handle ordinal numbers (28th, 1st, 2nd, 3rd, etc.)
                if '(?:st|nd|rd|th)' in pattern:
                    if pattern.startswith(r'\b(January|February'):
                        month_name, day, year = match
                        month_num = self._month_name_to_number(month_name)
                        if month_num:
                            return date(int(year), month_num, int(day))
                    else:
                        day, month_name, year = match
                        month_num = self._month_name_to_number(month_name)
                        if month_num:
                            return date(int(year), month_num, int(day))
                else:
                    # Abbreviated month name format
                    if pattern.startswith(r'\b(Jan|Feb'):
                        month_name, day, year = match
                        month_num = self._month_name_to_number(month_name)
                        if month_num:
                            return date(int(year), month_num, int(day))
                    else:
                        day, month_name, year = match
                        month_num = self._month_name_to_number(month_name)
                        if month_num:
                            return date(int(year), month_num, int(day))
        
        elif len(match) == 2:
            # Two-component matches (no year, assume current year)
            logger.info(f"Two-component match: {match}")
            if any(month_name in pattern.lower() for month_name in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                # Month name format without year
                if pattern.startswith(r'\b(Jan|Feb'):
                    month_name, day = match
                    month_num = self._month_name_to_number(month_name)
                    if month_num:
                        return date(current_year, month_num, int(day))
                else:
                    day, month_name = match
                    month_num = self._month_name_to_number(month_name)
                    if month_num:
                        return date(current_year, month_num, int(day))
            elif any(month_name in pattern.lower() for month_name in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
                # Full month name format without year (no ordinal numbers)
                logger.info(f"Full month name pattern detected: {pattern}")
                if pattern.startswith(r'\b(January|February|March|April|May|June|July|August|September|October|November|December'):
                    logger.info(f"Pattern starts with full month names, parsing: {match}")
                    month_name, day = match
                    month_num = self._month_name_to_number(month_name)
                    logger.info(f"Month name '{month_name}' -> number {month_num}")
                    if month_num:
                        result_date = date(current_year, month_num, int(day))
                        logger.info(f"Successfully parsed date: {result_date}")
                        return result_date
                else:
                    logger.info(f"Pattern doesn't start with full month names, parsing: {match}")
                    day, month_name = match
                    month_num = self._month_name_to_number(month_name)
                    logger.info(f"Month name '{month_name}' -> number {month_num}")
                    if month_num:
                        result_date = date(current_year, month_num, int(day))
                        logger.info(f"Successfully parsed date: {result_date}")
                        return result_date
            else:
                # Numeric format without year: MM/DD, MM-DD, etc.
                month, day = match
                return date(current_year, int(month), int(day))
        
        logger.info(f"No date pattern matched, returning None")
        return None
    
    def _extract_times(self, text: str) -> List[time]:
        """Smart time extraction with multiple strategies and intelligent prioritization"""
        times = []
        logger.info(f"Smart time extraction from text: {text}")
        
        # Strategy 1: Direct time pattern matching
        pattern_times = self._extract_times_by_patterns(text)
        times.extend(pattern_times)
        
        # Strategy 2: Context-aware time extraction (look near "PM" keyword)
        context_times = self._extract_times_by_context(text)
        times.extend(context_times)
        
        # Strategy 3: Natural language time expressions
        nlp_times = self._extract_times_by_nlp(text)
        times.extend(nlp_times)
        
        # Intelligent prioritization: prefer event times over timestamps
        prioritized_times = self._prioritize_event_times(times, text)
        
        logger.info(f"Found {len(prioritized_times)} prioritized times: {prioritized_times}")
        
        return prioritized_times
    
    def _prioritize_event_times(self, times: List[time], text: str) -> List[time]:
        """Intelligently prioritize event times over timestamps"""
        if not times:
            return []
        
        # Score each time based on context
        scored_times = []
        
        for t in times:
            score = self._score_time_relevance(t, text)
            scored_times.append((score, t))
        
        # Sort by score (higher is better) and return times
        scored_times.sort(key=lambda x: x[0], reverse=True)
        prioritized = [t for score, t in scored_times]
        
        logger.info(f"Time prioritization scores: {[(score, t) for score, t in scored_times]}")
        
        return prioritized
    
    def _score_time_relevance(self, t: time, text: str) -> float:
        """Score how relevant a time is to being an event time"""
        score = 0.0
        
        # Higher score for times with AM/PM (more likely to be event times)
        if t.hour > 12:  # PM times
            score += 2.0
        elif t.hour == 12:  # Noon
            score += 1.5
        elif t.hour == 0:  # Midnight
            score += 1.0
        else:  # AM times
            score += 1.0
        
        # Higher score for common event times (4-8 PM)
        if 16 <= t.hour <= 20:  # 4 PM to 8 PM
            score += 3.0
        elif 9 <= t.hour <= 11:  # 9 AM to 11 AM
            score += 2.0
        elif 13 <= t.hour <= 15:  # 1 PM to 3 PM
            score += 2.5
        
        # Lower score for very early morning times (likely timestamps)
        if 0 <= t.hour <= 6:
            score -= 2.0
        
        # Check context around the time in the text
        time_str = t.strftime('%H:%M')
        time_str_12h = t.strftime('%I:%M %p').lstrip('0')
        
        # Look for event-related context near the time
        event_keywords = ['meet', 'gathering', 'event', 'tour', 'exhibition', 'festival', 'join', 'attend', 'at', 'pm', 'am']
        
        for keyword in event_keywords:
            if keyword in text.lower():
                keyword_pos = text.lower().find(keyword)
                
                # Check if time appears near this keyword
                time_pos1 = text.find(time_str)
                time_pos2 = text.find(time_str_12h)
                
                if time_pos1 != -1 or time_pos2 != -1:
                    # Calculate distance from keyword
                    time_pos = time_pos1 if time_pos1 != -1 else time_pos2
                    distance = abs(keyword_pos - time_pos)
                    
                    if distance < 50:  # Within 50 characters
                        score += 5.0 - (distance / 10)  # Closer = higher score
        
        # Penalty for times that look like timestamps (very specific patterns)
        timestamp_patterns = [
            r'\d{1,2}:\d{2}\s*(AM|PM)?\s*Posts?',  # "12:18 Posts"
            r'\d{1,2}:\d{2}\s*(AM|PM)?\s*days?\s*ago',  # "12:18 3 days ago"
        ]
        
        for pattern in timestamp_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # If this time matches a timestamp pattern, reduce score
                if time_str in text or time_str_12h in text:
                    score -= 3.0
        
        logger.info(f"Time {t} scored {score:.1f}")
        return score
    
    def _extract_times_by_patterns(self, text: str) -> List[time]:
        """Extract times using comprehensive pattern matching"""
        times = []
        
        for pattern in self.time_patterns:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    if len(match) == 3:  # HH:MM AM/PM
                        hour, minute, ampm = match
                        hour = int(hour)
                        minute = int(minute)
                        
                        if ampm.upper() == 'PM' and hour != 12:
                            hour += 12
                        elif ampm.upper() == 'AM' and hour == 12:
                            hour = 0
                        
                        parsed_time = time(hour, minute)
                        if parsed_time not in times:
                            times.append(parsed_time)
                    
                    elif len(match) == 2:  # HH:MM or H AM/PM
                        if ':' in text[text.find(''.join(match))-1:text.find(''.join(match))+len(''.join(match))+1]:
                            # HH:MM format
                            hour, minute = match
                            parsed_time = time(int(hour), int(minute))
                        else:
                            # H AM/PM format
                            hour, ampm = match
                            hour = int(hour)
                            
                            if ampm.upper() == 'PM' and hour != 12:
                                hour += 12
                            elif ampm.upper() == 'AM' and hour == 12:
                                hour = 0
                            
                            parsed_time = time(hour, 0)
                        
                        if parsed_time not in times:
                            times.append(parsed_time)
                except (ValueError, TypeError):
                    continue
        
        return times
    
    def _extract_times_by_context(self, text: str) -> List[time]:
        """Extract times by looking for event-related context"""
        times = []
        
        # Look for time expressions near event keywords
        event_keywords = ['meet', 'gathering', 'event', 'tour', 'exhibition', 'festival', 'join', 'attend', 'at', 'pm', 'am']
        
        for keyword in event_keywords:
            if keyword in text.lower():
                # Look for time patterns near this keyword
                keyword_pos = text.lower().find(keyword)
                
                # Search in a window around the keyword
                start = max(0, keyword_pos - 50)
                end = min(len(text), keyword_pos + 50)
                context = text[start:end]
                
                # Extract times from this context
                time_patterns = [
                    r'\b(\d{1,2}):(\d{2})\s*(AM|PM)\b',
                    r'\b(\d{1,2}):(\d{2})\b',
                    r'\b(\d{1,2})\s*(AM|PM)\b',
                ]
                
                for pattern in time_patterns:
                    matches = re.findall(pattern, context, re.IGNORECASE)
                    for match in matches:
                        try:
                            parsed_time = self._parse_time_match(match, pattern)
                            if parsed_time:
                                times.append(parsed_time)
                                logger.info(f"Added context time: {parsed_time}")
                        except (ValueError, TypeError) as e:
                            logger.info(f"Failed to parse context time {match}: {e}")
                            continue
        
        return times
    
    def _extract_times_by_nlp(self, text: str) -> List[time]:
        """Extract times using natural language processing"""
        times = []
        
        # Look for natural language time expressions
        nlp_patterns = [
            r'at\s+(\d{1,2}):(\d{2})\s*(AM|PM)',
            r'at\s+(\d{1,2})\s*(AM|PM)',
            r'starting\s+at\s+(\d{1,2}):(\d{2})',
            r'begins\s+at\s+(\d{1,2}):(\d{2})',
            r'kickoff\s+at\s+(\d{1,2}):(\d{2})',
        ]
        
        for pattern in nlp_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    parsed_time = self._parse_nlp_time(match.groups())
                    if parsed_time:
                        times.append(parsed_time)
                        logger.info(f"Added NLP time: {parsed_time}")
                except Exception as e:
                    logger.info(f"Failed to parse NLP time {match.groups()}: {e}")
                    continue
        
        return times
    
    def _parse_nlp_time(self, groups: tuple) -> Optional[time]:
        """Parse natural language time expressions"""
        try:
            if len(groups) >= 2:
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) > 1 and groups[1] else 0
                
                # Handle AM/PM
                if len(groups) > 2 and groups[2]:
                    am_pm = groups[2].upper()
                    if am_pm == 'PM' and hour != 12:
                        hour += 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0
                
                return time(hour, minute)
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _parse_time_match(self, match: tuple, pattern: str) -> Optional[time]:
        """Parse a time match tuple based on the pattern used"""
        try:
            if len(match) == 3:  # HH:MM AM/PM
                hour, minute, ampm = match
                hour = int(hour)
                minute = int(minute)
                
                if ampm.upper() == 'PM' and hour != 12:
                    hour += 12
                elif ampm.upper() == 'AM' and hour == 12:
                    hour = 0
                
                return time(hour, minute)
            
            elif len(match) == 2:  # HH:MM or H AM/PM
                if ':' in pattern:  # HH:MM format
                    hour, minute = match
                    return time(int(hour), int(minute))
                else:  # H AM/PM format
                    hour, ampm = match
                    hour = int(hour)
                    
                    if ampm.upper() == 'PM' and hour != 12:
                        hour += 12
                    elif ampm.upper() == 'AM' and hour == 12:
                        hour = 0
                    
                    return time(hour, 0)
        
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _estimate_end_time(self, start_time: time, text: str) -> time:
        """Intelligently estimate end time based on start time and event context"""
        # Default duration is 2 hours
        duration_hours = 2
        
        # Adjust duration based on event type and context
        text_lower = text.lower()
        
        # Longer events
        if any(keyword in text_lower for keyword in ['festival', 'conference', 'workshop', 'seminar', 'all day']):
            duration_hours = 4
        elif any(keyword in text_lower for keyword in ['tour', 'walking tour', 'city tour']):
            duration_hours = 3
        elif any(keyword in text_lower for keyword in ['exhibition', 'gallery', 'museum']):
            duration_hours = 3
        elif any(keyword in text_lower for keyword in ['meetup', 'networking', 'social']):
            duration_hours = 2
        elif any(keyword in text_lower for keyword in ['quick', 'brief', 'short']):
            duration_hours = 1
        
        # Calculate end time
        start_hour = start_time.hour
        start_minute = start_time.minute
        
        # Add duration
        total_minutes = start_hour * 60 + start_minute + (duration_hours * 60)
        end_hour = (total_minutes // 60) % 24
        end_minute = total_minutes % 60
        
        estimated_end_time = time(end_hour, end_minute)
        logger.info(f"Estimated end time: {estimated_end_time} (duration: {duration_hours} hours)")
        
        return estimated_end_time
    
    def _estimate_end_location(self, start_location: str, text: str) -> str:
        """Intelligently estimate end location based on start location and event context"""
        # Default: same as start location
        end_location = start_location
        
        # Check if there are multiple locations mentioned in the text
        text_lower = text.lower()
        
        # Look for location patterns that might indicate different start/end locations
        location_patterns = [
            r'from\s+([^,\n]+)\s+to\s+([^,\n]+)',  # "from X to Y"
            r'starting\s+at\s+([^,\n]+)\s+ending\s+at\s+([^,\n]+)',  # "starting at X ending at Y"
            r'meet\s+at\s+([^,\n]+)\s+then\s+([^,\n]+)',  # "meet at X then Y"
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                # Found multiple locations, use the second one as end location
                start_loc, end_loc = matches[0]
                if end_loc.strip() and end_loc.strip() != start_location.lower():
                    end_location = end_loc.strip().title()
                    logger.info(f"Found end location pattern: {end_location}")
                    break
        
        # For certain event types, end location might be different
        if any(keyword in text_lower for keyword in ['tour', 'walking tour', 'city tour', 'walk']):
            # For tours, end location might be different from start
            # Look for "ends at" or "finishes at" patterns
            tour_patterns = [
                r'ends?\s+at\s+([^,\n]+)',
                r'finishes?\s+at\s+([^,\n]+)',
                r'concludes?\s+at\s+([^,\n]+)',
            ]
            
            for pattern in tour_patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    end_location = matches[0].strip().title()
                    logger.info(f"Found tour end location: {end_location}")
                    break
        
        # If no different end location found, use start location
        if end_location == start_location:
            logger.info(f"Using start location as end location: {end_location}")
        
        return end_location
    
    def _find_best_end_time(self, unique_times: List[time], text: str) -> Optional[time]:
        """Find the best end time candidate from multiple times, filtering out timestamps"""
        if len(unique_times) <= 1:
            return None
        
        # Score each time as a potential end time
        scored_times = []
        start_time = unique_times[0]  # First time is the start time
        
        for t in unique_times[1:]:  # Skip the start time
            score = self._score_end_time_candidate(t, start_time, text)
            scored_times.append((score, t))
        
        # Sort by score (higher is better)
        scored_times.sort(key=lambda x: x[0], reverse=True)
        
        # Return the highest scoring time if it's reasonable
        if scored_times and scored_times[0][0] > 0:
            best_time = scored_times[0][1]
            logger.info(f"Best end time candidate: {best_time} (score: {scored_times[0][0]})")
            return best_time
        
        return None
    
    def _score_end_time_candidate(self, candidate_time: time, start_time: time, text: str) -> float:
        """Score how good a time is as an end time candidate"""
        score = 0.0
        
        # Must be after start time
        if candidate_time <= start_time:
            return -10.0  # Heavily penalize times before or equal to start time
        
        # Higher score for reasonable durations (1-6 hours)
        duration_hours = candidate_time.hour - start_time.hour
        if candidate_time.minute < start_time.minute:
            duration_hours -= 1
        
        if 1 <= duration_hours <= 6:
            score += 5.0
        elif duration_hours > 6:
            score += 2.0  # Very long events are possible but less common
        else:
            score -= 5.0  # Very short durations are unlikely
        
        # Check if this time appears in event context
        time_str = candidate_time.strftime('%H:%M')
        time_str_12h = candidate_time.strftime('%I:%M %p').lstrip('0')
        
        # Look for event-related context near the time
        event_keywords = ['ends', 'finishes', 'concludes', 'until', 'till', 'pm', 'am']
        
        for keyword in event_keywords:
            if keyword in text.lower():
                keyword_pos = text.lower().find(keyword)
                
                # Check if time appears near this keyword
                time_pos1 = text.find(time_str)
                time_pos2 = text.find(time_str_12h)
                
                if time_pos1 != -1 or time_pos2 != -1:
                    time_pos = time_pos1 if time_pos1 != -1 else time_pos2
                    distance = abs(keyword_pos - time_pos)
                    
                    if distance < 50:  # Within 50 characters
                        score += 8.0 - (distance / 10)  # Closer = higher score
        
        # Penalty for times that look like timestamps
        timestamp_patterns = [
            r'\d{1,2}:\d{2}\s*(AM|PM)?\s*Posts?',  # "12:18 Posts"
            r'\d{1,2}:\d{2}\s*(AM|PM)?\s*days?\s*ago',  # "12:18 3 days ago"
        ]
        
        for pattern in timestamp_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if time_str in text or time_str_12h in text:
                    score -= 10.0  # Heavy penalty for timestamp patterns
        
        logger.info(f"End time candidate {candidate_time} scored {score:.1f}")
        return score
    
    def _extract_event_type(self, text: str) -> Optional[str]:
        """Extract event type from text"""
        text_lower = text.lower()
        
        for event_type, keywords in self.event_type_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return event_type
        
        return None
    
    def _extract_city_info(self, text: str) -> Dict[str, str]:
        """Extract city information from text"""
        text_lower = text.lower().strip()
        
        # Direct mapping lookup
        for location_key, city_info in self.city_mappings.items():
            if location_key in text_lower:
                return city_info
        
        # Pattern matching for common formats
        # Look for "City, State" patterns
        city_state_pattern = re.compile(r'\b([A-Za-z\s]+),\s*([A-Z]{2})\b')
        match = city_state_pattern.search(text)
        if match:
            city_name = match.group(1).strip().title()
            state_code = match.group(2).upper()
            return {
                'city': city_name,
                'state': state_code,
                'country': 'United States'
            }
        
        # Look for standalone city names that might be in our database
        words = text_lower.split()
        for word in words:
            if word in self.city_mappings:
                return self.city_mappings[word]
        
        return {'city': None, 'state': None, 'country': None}
    
    def _extract_instagram_info(self, text: str) -> Dict[str, str]:
        """Extract Instagram information from text"""
        text_lower = text.lower().strip()
        
        # Look for Instagram hashtags and handles
        instagram_patterns = [
            r'#([a-zA-Z0-9_]+)',  # Hashtags
            r'@([a-zA-Z0-9_]+)',  # Handles
            r'instagram\.com/([a-zA-Z0-9_]+)',  # Instagram URLs
        ]
        
        handles = []
        for pattern in instagram_patterns:
            matches = re.findall(pattern, text_lower)
            handles.extend(matches)
        
        # Check if this looks like an Instagram post
        is_instagram = any([
            '#streetmeetdc' in text_lower,
            '#streetmeet' in text_lower,
            'streetmeet' in text_lower,
            any(handle in ['streetmeetdc', 'streetmeet'] for handle in handles)
        ])
        
        # Extract the main handle (prefer streetmeetdc or streetmeet)
        main_handle = None
        if 'streetmeetdc' in handles:
            main_handle = 'streetmeetdc'
        elif 'streetmeet' in handles:
            main_handle = 'streetmeet'
        elif handles:
            main_handle = handles[0]
        
        return {
            'is_instagram': is_instagram,
            'handle': main_handle,
            'url': f'https://www.instagram.com/{main_handle}/' if main_handle else None
        }
    
    def _load_source_data(self) -> Dict[str, Dict]:
        """Load source data from sources.json"""
        try:
            sources_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sources.json')
            if os.path.exists(sources_file):
                with open(sources_file, 'r') as f:
                    sources_data = json.load(f)
                
                # Handle nested structure - sources might be under a 'sources' key
                if 'sources' in sources_data:
                    sources_data = sources_data['sources']
                
                # Create a lookup by handle and name
                source_lookup = {}
                for source_id, source_info in sources_data.items():
                    if isinstance(source_info, dict):
                        # Add by handle
                        if source_info.get('handle'):
                            handle = source_info['handle'].replace('@', '').lower()
                            source_lookup[handle] = source_info
                        
                        # Add by name
                        if source_info.get('name'):
                            name_key = source_info['name'].lower().replace(' ', '')
                            source_lookup[name_key] = source_info
                
                logger.info(f"Loaded {len(source_lookup)} source entries")
                return source_lookup
        except Exception as e:
            logger.warning(f"Could not load source data: {e}")
        
        return {}
    
    def _load_city_data(self) -> Dict[str, Dict]:
        """Load city data from cities.json"""
        try:
            cities_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cities.json')
            if os.path.exists(cities_file):
                with open(cities_file, 'r') as f:
                    cities_data = json.load(f)
                
                # Handle nested structure - cities might be under a 'cities' key
                if 'cities' in cities_data:
                    cities_data = cities_data['cities']
                
                # Create a lookup by name and state
                city_lookup = {}
                for city_id, city_info in cities_data.items():
                    if isinstance(city_info, dict):
                        # Add by name + state combination
                        name = city_info.get('name', '').lower()
                        state = city_info.get('state', '').lower()
                        key = f"{name},{state}" if state else name
                        city_lookup[key] = {
                            'id': int(city_id),
                            'name': city_info.get('name'),
                            'state': city_info.get('state'),
                            'country': city_info.get('country')
                        }
                        
                        # Also add by name only (for cases where state might not match exactly)
                        city_lookup[name] = {
                            'id': int(city_id),
                            'name': city_info.get('name'),
                            'state': city_info.get('state'),
                            'country': city_info.get('country')
                        }
                
                logger.info(f"Loaded {len(city_lookup)} city entries")
                return city_lookup
        except Exception as e:
            logger.warning(f"Could not load city data: {e}")
        
        return {}
    
    def _lookup_city_id(self, city_name: str, state: str = None) -> Optional[int]:
        """Look up city ID from city name and state"""
        if not city_name or not self.city_data:
            return None
        
        city_key = city_name.lower()
        state_key = state.lower() if state else ""
        
        # Try exact match with state
        if state:
            full_key = f"{city_key},{state_key}"
            if full_key in self.city_data:
                return self.city_data[full_key]['id']
        
        # Try city name only
        if city_key in self.city_data:
            return self.city_data[city_key]['id']
        
        # Try partial matches
        for key, city_info in self.city_data.items():
            if city_name.lower() in city_info['name'].lower():
                if not state or state.lower() in city_info['state'].lower():
                    return city_info['id']
        
        return None
    
    def _enhance_with_source_data(self, event_data: ExtractedEventData) -> ExtractedEventData:
        """Enhance extracted data with information from known sources"""
        if not event_data.instagram_handle or not self.source_data:
            return event_data
        
        # Look up source information
        handle_key = event_data.instagram_handle.lower()
        source_info = self.source_data.get(handle_key)
        
        if source_info:
            logger.info(f"Found source data for {event_data.instagram_handle}: {source_info.get('name', 'Unknown')}")
            
            # Enhance title if it's generic
            if not event_data.title or event_data.title in ['RHODE ISLAND AVE', 'Event at Rhode Island Ave']:
                if source_info.get('name'):
                    if event_data.location:
                        event_data.title = f"{source_info['name']} - {event_data.location}"
                    else:
                        event_data.title = f"{source_info['name']} Event"
            
            # Enhance description if it's generic
            if not event_data.description or 'Join us for a Street Meet DC photography event' in event_data.description or event_data.description == 'RHODE ISLAND AVE':
                if source_info.get('description'):
                    event_data.description = source_info['description']
            
            # Set organizer if not set
            if not event_data.organizer and source_info.get('name'):
                event_data.organizer = source_info['name']
            
            # Enhance event type based on source's event types
            if source_info.get('event_types'):
                try:
                    event_types = json.loads(source_info['event_types'])
                    if event_types and not event_data.event_type:
                        # Map source event types to our event types
                        if any('photowalk' in et.lower() or 'photo_walk' in et.lower() for et in event_types):
                            event_data.event_type = 'photowalk'
                        elif any('workshop' in et.lower() for et in event_types):
                            event_data.event_type = 'tour'
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return event_data
    
    def _correct_ocr_text(self, text: str) -> str:
        """Correct common OCR misreadings"""
        corrections = {
            # Common character misreadings
            'OC': 'DC',  # D often misread as O
            '0C': 'DC',  # D often misread as 0
            'D0': 'DC',  # C often misread as 0
            'DO': 'DC',  # C often misread as O
            '1S1AND': 'ISLAND',  # ISLAND misread as 1S1AND
            '1SLAND': 'ISLAND',  # ISLAND misread as 1SLAND
            'RH0DE': 'RHODE',  # RHODE with O misread as 0
            'RH0DE ISLAND': 'RHODE ISLAND',  # RHODE ISLAND with O misread as 0
            
            # Common word misreadings in event contexts
            'STREETMEETOC': 'STREETMEETDC',
            'STREETMEET0C': 'STREETMEETDC',
            'STREETMEETD0': 'STREETMEETDC',
            'STREETMEETDO': 'STREETMEETDC',
            
            # Time misreadings
            '4PM': '4PM',  # Usually correct
            '4P0': '4PM',  # M misread as 0
            '4PO': '4PM',  # M misread as O
            '4:05PM': '4:00PM',  # 00 misread as 05
            '4:05 PM': '4:00 PM',  # 00 misread as 05
            '4:0S PM': '4:00 PM',  # 0 misread as S
            '4:0S PM': '4:00 PM',  # 0 misread as S
            
            # Common OCR errors for dates and times
            'AUG 3O': 'AUG 30',  # 0 misread as O
            'AUG 30': 'AUG 30',  # Correct
            'SPM': '5PM',  # 5 misread as S
            '5PM': '5PM',  # Correct
            'NAT1ONAL': 'NATIONAL',  # I misread as 1
            'NAT10NAL': 'NATIONAL',  # I misread as 1 and 0
            '4:0O PM': '4:00 PM',  # 0 misread as O
            '4:0O PM': '4:00 PM',  # 0 misread as O
            
            # Date misreadings
            'SEP 28': 'SEP 28',  # Usually correct
            'SEP 2B': 'SEP 28',  # 8 misread as B
            'SEP 2O': 'SEP 28',  # 8 misread as O
            
            # Location misreadings - Rhode Island variations
            'RHODE ISLAND AVE': 'RHODE ISLAND AVE',  # Usually correct
            'RHODE ISLAND AV0': 'RHODE ISLAND AVE',  # E misread as 0
            'RHODE ISLAND AVO': 'RHODE ISLAND AVE',  # E misread as O
            'RHODE 1S1AND AVE': 'RHODE ISLAND AVE',  # Common misreading
            'RHODE 1SLAND AVE': 'RHODE ISLAND AVE',  # Common misreading
            'RH0DE ISLAND AVE': 'RHODE ISLAND AVE',  # O misread as 0
            'RH0DE 1S1AND AVE': 'RHODE ISLAND AVE',  # Multiple misreadings
            
            # Metro station variations
            'METRO STATION': 'METRO STATION',
            'METRO STATI0N': 'METRO STATION',  # O misread as 0
            'METR0 STATION': 'METRO STATION',  # O misread as 0
            
            # Common event text misreadings
            'WE 11 BE': 'WE WILL BE',  # WILL misread as 11
            'WE W1LL BE': 'WE WILL BE',  # I misread as 1
            'K1CKING': 'KICKING',  # I misread as 1
            'TH1NGS': 'THINGS',  # I misread as 1
            'OFF A': 'OFF AT',  # AT misread as A
            'M0RE': 'MORE',  # O misread as 0
            'DAYS AGO': 'DAYS AGO',
            'DAY5 AGO': 'DAYS AGO',  # S misread as 5
        }
        
        corrected_text = text
        for wrong, correct in corrections.items():
            corrected_text = corrected_text.replace(wrong, correct)
        
        return corrected_text
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean up OCR text by removing common artifacts"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common OCR artifacts
        artifacts = [
            r'[^\w\s@#.,:!?\-/]',  # Remove special characters except common ones
            r'\b\d+[A-Z][a-z]*\b',  # Remove patterns like "28G"
            r'\b[A-Z][a-z]*\d+\b',  # Remove patterns like "FOe-"
            r'%\s*[A-Z]',  # Remove patterns like "%N"
            r'\b\d+%\b',  # Remove standalone percentages
            r'~~+',  # Remove multiple tildes
        ]
        
        for pattern in artifacts:
            text = re.sub(pattern, ' ', text)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Fix common OCR errors for dates
        # Replace common misreadings
        replacements = {
            'O': '0',  # Letter O to number 0
            'I': '1',  # Letter I to number 1
            'l': '1',  # lowercase l to number 1
            '5': 'S',  # Number 5 to letter S (common OCR error)
            'B': '8',  # Letter B to number 8 (in some fonts)
            '0': 'O',  # Number 0 to letter O (when it should be O)
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Fix common date misreadings
        # If we see "22" in a date context, check if it should be "28"
        date_context = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+22\b', text, re.IGNORECASE)
        if date_context:
            # Check if the original text might have been "28"
            # This is a heuristic - if we see "22" in a month context, it might be "28"
            text = re.sub(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+22\b', 
                         lambda m: f"{m.group(1)} 28", text, flags=re.IGNORECASE)
        
        return text
    
    def _is_garbled_text(self, text: str) -> bool:
        """Check if text appears to be garbled OCR output"""
        if not text or len(text.strip()) < 3:
            return True
        
        # Check for very obvious garbled patterns (very specific)
        garbled_patterns = [
            r'\b[a-z]{20,}\d+[a-z]{20,}\b',  # Very long letter sequences with numbers like "haautifi11arsunhntnnranbe"
            r'\b[a-z]*\d+[a-z]*\d+[a-z]*\d+[a-z]*\d+[a-z]*\d+[a-z]*\b',  # Multiple digit-letter combinations (5+ digits)
            r'\b[a-z]{30,}\b',  # Very long single words (likely garbled)
        ]
        
        for pattern in garbled_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for excessive mixed alphanumeric sequences (be very lenient)
        mixed_sequences = re.findall(r'\b[a-zA-Z]*\d+[a-zA-Z]*\d+[a-zA-Z]*\b', text)
        if len(mixed_sequences) > 10:  # Increased threshold - more than 10 mixed sequences
            return True
        
        # Check if text has too few readable characters (be very lenient)
        alpha_chars = sum(1 for c in text if c.isalpha())
        total_chars = len(text.replace(' ', ''))
        
        if total_chars > 0 and alpha_chars / total_chars < 0.1:  # Reduced threshold to 10%
            return True
        
        # Check for repetitive character patterns (common in garbled OCR)
        if re.search(r'(.)\1{8,}', text):  # Same character repeated 9+ times (increased threshold)
            return True
        
        # Check for excessive special characters (be very lenient)
        special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
        if special_char_ratio > 0.7:  # Increased threshold to 70% special characters
            return True
        
        return False
    
    def _clean_text_for_extraction(self, text: str) -> str:
        """Remove comments, hashtags, handles, and other social media noise"""
        # First, remove meaningless OCR noise from the beginning
        # Pattern for meaningless phrases like "ne, ae!" at start
        text = re.sub(r'^[a-z]{1,3}[,\.!]*\s*[a-z]{1,3}[,\.!]*\s*', '', text, flags=re.IGNORECASE)
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Skip hashtags and handles
            if line.startswith('#') or line.startswith('@'):
                continue
                
            # Skip meaningless short phrases (OCR noise)
            if len(line) <= 8 and not any(char.isdigit() for char in line):
                # Skip lines like "ne, ae!", "hi!", "ok", etc.
                if re.match(r'^[a-z]{1,3}[,\.!]*[a-z]{1,3}[,\.!]*$', line.lower()):
                    continue
                
            # Skip lines that are just hashtags/handles
            if re.match(r'^[#@\s]+$', line):
                continue
                
            # Skip lines that are mostly hashtags
            hashtag_count = len(re.findall(r'#\w+', line))
            if hashtag_count > 2:
                # Remove hashtags but keep the rest if there's meaningful content
                line_without_hashtags = re.sub(r'#\w+\s*', '', line).strip()
                if len(line_without_hashtags) > 5:
                    cleaned_lines.append(line_without_hashtags)
                continue
            
            # Skip lines that look like comments or reactions
            if any(pattern in line.lower() for pattern in [
                'like', 'comment', 'share', 'follow', 'dm', 'message me',
                'tag your friends', 'double tap', 'save this post'
            ]):
                continue
                
            # Skip lines with excessive punctuation (often comments)
            if len(re.findall(r'[!]{2,}|[?]{2,}|[.]{3,}', line)) > 0:
                continue
                
            # Keep meaningful lines
            if len(line) > 3:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract simple, clean event title - ignore comments and social media noise"""
        # Clean up text first - remove comments, hashtags, handles, etc.
        cleaned_text = self._clean_text_for_extraction(text)
        
        # If cleaned text is garbled, skip title extraction
        if self._is_garbled_text(cleaned_text):
            logger.warning("Skipping title extraction due to garbled text")
            return None
        
        lines = cleaned_text.split('\n')
        
        # Look for the first meaningful line that could be a title
        # Skip meaningless OCR noise at the beginning
        for line in lines:
            line = line.strip()
            
            # Skip meaningless short phrases (like "ne, ae!")
            if len(line) <= 8 and not any(char.isdigit() for char in line):
                if re.match(r'^[a-z]{1,3}[,\.!]*[a-z]{1,3}[,\.!]*$', line.lower()):
                    continue
            line = line.strip()
            # Skip empty lines and garbled text
            if len(line) > 5 and not self._is_garbled_text(line):
                
                if line and len(line) > 3:
                    # If line contains location info, use it as title (even if it also has date/time)
                    if any(location_word in line.upper() for location_word in ['MALL', 'AVENUE', 'STREET', 'PARK', 'CENTER', 'MUSEUM']):
                        return line
                    # Skip lines that are ONLY date/time (no location or other meaningful content)
                    elif self._is_date_or_time_line(line):
                        continue
                    # Otherwise use the line as is
                    else:
                        return line
        
        # If no good title found, generate a simple one based on content
        if any(keyword in text.lower() for keyword in ['streetmeet', 'photowalk', 'meetup']):
            return "Photography Meetup"
        elif any(keyword in text.lower() for keyword in ['tour', 'walking', 'guided']):
            return "Walking Tour"
        elif any(keyword in text.lower() for keyword in ['exhibition', 'art', 'gallery']):
            return "Art Exhibition"
        else:
            return "Community Event"
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract simple event description - just the essential info"""
        # Clean up text first
        cleaned_text = self._clean_text_for_extraction(text)
        
        # If cleaned text is garbled, skip description extraction
        if self._is_garbled_text(cleaned_text):
            logger.warning("Skipping description extraction due to garbled text")
            return None
        
        # Keep it simple - just provide a basic description based on event type
        if any(keyword in cleaned_text.lower() for keyword in ['streetmeet', 'photowalk']):
            return "Photography meetup and photowalk"
        elif any(keyword in cleaned_text.lower() for keyword in ['tour', 'walking']):
            return "Walking tour"
        elif any(keyword in cleaned_text.lower() for keyword in ['exhibition', 'art']):
            return "Art exhibition"
        else:
            return "Community event"
    
    def _contains_location_details(self, text: str) -> bool:
        """Check if text contains additional location details beyond street name"""
        # Look for patterns that indicate additional location information
        location_detail_patterns = [
            r'\b(entrance|meeting point|gathering spot|start point|end point)\b',
            r'\b(near|close to|next to|across from|behind|in front of)\b',
            r'\b(intersection|crossing|corner|block|building|plaza|square)\b',
            r'\b(metro|station|bus stop|parking|garage)\b',
            r'\b(floor|level|room|hall|auditorium|gallery)\b',
        ]
        
        text_lower = text.lower()
        for pattern in location_detail_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _contains_meeting_details(self, text: str) -> bool:
        """Check if text contains meeting or event details"""
        # Look for patterns that indicate meeting instructions or details
        meeting_detail_patterns = [
            r'\b(meeting point|gathering spot|start point|entrance|meet at|meet us)\b',
            r'\b(bring|bring your|don\'t forget|remember to)\b',
            r'\b(what to expect|what to bring|what you\'ll need)\b',
            r'\b(weather|rain|sunny|cloudy)\b',
            r'\b(all skill levels|beginner|advanced|experience)\b',
            r'\b(free|cost|price|ticket|registration)\b',
        ]
        
        text_lower = text.lower()
        for pattern in meeting_detail_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract simple location name from text"""
        # Look for specific known locations first (with OCR error tolerance)
        text_upper = text.upper()
        if 'RHODE' in text_upper and ('ISLAND' in text_upper or '1SLAND' in text_upper or '1S1AND' in text_upper):
            return 'Rhode Island Ave'
        
        # Look for other common DC locations
        if 'DUPONT' in text_upper and 'CIRCLE' in text_upper:
            return 'Dupont Circle'
        if 'GEORGETOWN' in text_upper:
            return 'Georgetown'
        if 'CAPITOL' in text_upper and 'HILL' in text_upper:
            return 'Capitol Hill'
        if 'NATIONAL' in text_upper and 'MALL' in text_upper:
            return 'National Mall'
        
        # Look for street/avenue names (fallback)
        street_patterns = [
            r'\b([A-Z][a-z\s]+(?:Ave|Avenue|Street|St|Road|Rd|Boulevard|Blvd|Drive|Dr|Way|Place|Pl|Court|Ct))\b',
        ]
        
        for pattern in street_patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                return self._clean_location_name(location)
        
        # Look for venue names or general locations
        location_patterns = [
            r'at\s+([A-Z][^,\n]+)',
            r'@\s+([A-Z][^,\n]+)',
            r'location:\s*([A-Z][^,\n]+)',
            r'venue:\s*([A-Z][^,\n]+)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Only return if it's a reasonable length and not garbled
                if 3 < len(location) < 50 and not self._is_garbled_text(location):
                    return self._clean_location_name(location)
        
        return None
    
    def _clean_location_name(self, location: str) -> str:
        """Clean location name to be simple and readable"""
        if not location:
            return ""
        
        # Remove common OCR errors
        location = location.replace('AV0', 'AVE').replace('AVO', 'AVE')
        
        # Clean up and capitalize properly
        clean_location = location.strip()
        return ' '.join(word.capitalize() for word in clean_location.split())
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price from text"""
        price_patterns = [
            r'\$(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*dollars?',
            r'price:\s*\$?(\d+(?:\.\d{2})?)',
            r'cost:\s*\$?(\d+(?:\.\d{2})?)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_organizer(self, text: str) -> Optional[str]:
        """Extract organizer from text"""
        organizer_patterns = [
            r'organized by\s+([A-Z][^,\n]+)',
            r'hosted by\s+([A-Z][^,\n]+)',
            r'presented by\s+([A-Z][^,\n]+)',
            r'sponsored by\s+([A-Z][^,\n]+)',
        ]
        
        for pattern in organizer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text"""
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        
        return None
    
    def _month_name_to_number(self, month_name: str) -> Optional[int]:
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
        return months.get(month_name.lower())
    
    def _is_date_or_time_line(self, line: str) -> bool:
        """Check if a line contains only date/time information"""
        # Check if line matches date patterns
        for pattern in self.date_patterns:
            if pattern.search(line):
                return True
        
        # Check if line matches time patterns
        for pattern in self.time_patterns:
            if pattern.search(line):
                return True
        
        return False
    
    def _calculate_confidence(self, event_data: ExtractedEventData) -> float:
        """Calculate confidence score for extracted event data"""
        score = 0.0
        total_fields = 10  # Number of fields we're checking
        
        if event_data.title:
            score += 1.0
        if event_data.start_date:
            score += 1.0
        if event_data.start_time:
            score += 0.5
        if event_data.location:
            score += 0.5
        if event_data.event_type:
            score += 0.5
        if event_data.description:
            score += 0.5
        if event_data.price is not None:
            score += 0.5
        if event_data.organizer:
            score += 0.5
        if event_data.source:
            score += 0.5
        if event_data.city:
            score += 0.5
        
        return min(score / total_fields, 1.0)
    
    def process_image(self, image_path: str) -> ExtractedEventData:
        """Main method to process an image and extract event data"""
        logger.info(f"Processing image: {image_path}")
        
        # Extract text from image
        text = self.extract_text_from_image(image_path)
        logger.info(f"Extracted text: {text[:200]}...")
        
        # Parse the text to extract event data
        event_data = self.parse_extracted_text(text)
        logger.info(f"Extracted event data: {event_data}")
        
        return event_data

def main():
    """Test the image processor"""
    processor = ImageEventProcessor()
    
    # Test with a sample image (if available)
    test_image_path = "test_event_image.jpg"
    if os.path.exists(test_image_path):
        event_data = processor.process_image(test_image_path)
        print(f"Extracted Event Data: {event_data}")
    else:
        print("No test image found. Please provide an image with event information.")

if __name__ == "__main__":
    main()
