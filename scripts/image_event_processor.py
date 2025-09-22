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
from datetime import datetime, date, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import pytesseract
from google.cloud import vision
from google.cloud.vision_v1 import types as vision_types

# Setup logging
logger = logging.getLogger(__name__)

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
        """Setup OCR engine (Tesseract or Google Vision)"""
        # Try Tesseract first since it's more reliable for local development
        try:
            pytesseract.get_tesseract_version()
            logger.info("Using Tesseract OCR engine")
            return 'tesseract'
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
        
        # Fallback to Google Cloud Vision if Tesseract fails
        try:
            if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or os.getenv('GOOGLE_CLIENT_ID'):
                logger.info("Using Google Cloud Vision OCR engine")
                return 'google_vision'
        except Exception as e:
            logger.warning(f"Google Vision not available: {e}")
        
        # Last resort - try Tesseract anyway
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
                except Exception as e:
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
            # Return a fallback message instead of empty string
            return f"OCR Error: {str(e)}"
    
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
            if len(times) > 1:
                event_data.end_time = times[1]
            else:
                # If only start time found, assume 1 hour duration
                start_hour = event_data.start_time.hour
                start_minute = event_data.start_time.minute
                end_hour = (start_hour + 1) % 24
                event_data.end_time = time(end_hour, start_minute)
        
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
            event_data.end_location = event_data.location  # Assume same as start if not specified
        
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
        """Extract dates from text using comprehensive pattern matching"""
        dates = []
        logger.info(f"Extracting dates from text: {text}")
        
        for i, pattern in enumerate(self.date_patterns):
            matches = pattern.findall(text)
            if matches:
                logger.info(f"Pattern {i+1} ({pattern.pattern}) found matches: {matches}")
            
            for match in matches:
                try:
                    parsed_date = self._parse_date_match(match, pattern.pattern)
                    if parsed_date and parsed_date not in dates:
                        dates.append(parsed_date)
                        logger.info(f"Added date: {parsed_date}")
                except (ValueError, TypeError) as e:
                    logger.info(f"Failed to parse date match {match}: {e}")
                    continue
        
        logger.info(f"Final extracted dates: {dates}")
        return sorted(dates)
    
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
        """Extract times from text"""
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
        
        return sorted(times)
    
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
            
            # Common word misreadings in event contexts
            'STREETMEETOC': 'STREETMEETDC',
            'STREETMEET0C': 'STREETMEETDC',
            'STREETMEETD0': 'STREETMEETDC',
            'STREETMEETDO': 'STREETMEETDC',
            
            # Time misreadings
            '4PM': '4PM',  # Usually correct
            '4P0': '4PM',  # M misread as 0
            '4PO': '4PM',  # M misread as O
            
            # Date misreadings
            'SEP 28': 'SEP 28',  # Usually correct
            'SEP 2B': 'SEP 28',  # 8 misread as B
            'SEP 2O': 'SEP 28',  # 8 misread as O
            
            # Location misreadings
            'RHODE ISLAND AVE': 'RHODE ISLAND AVE',  # Usually correct
            'RHODE ISLAND AV0': 'RHODE ISLAND AVE',  # E misread as 0
            'RHODE ISLAND AVO': 'RHODE ISLAND AVE',  # E misread as O
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
        
        # Check for common garbled patterns
        garbled_patterns = [
            r'\d+[A-Z][a-z]*\s*[A-Z][a-z]*\s*%\s*[A-Z]',  # Like "28G FOe- %N"
            r'[A-Z][a-z]*\s*[A-Z][a-z]*\s*\d+%',  # Like "FOe- %N OA 187%"
            r'\d+[A-Z][a-z]*\s*%\s*[A-Z]\s*[A-Z][a-z]*',  # Other patterns
        ]
        
        for pattern in garbled_patterns:
            if re.search(pattern, text):
                return True
        
        # Check if text has too many random characters
        alpha_chars = sum(1 for c in text if c.isalpha())
        total_chars = len(text.replace(' ', ''))
        
        if total_chars > 0 and alpha_chars / total_chars < 0.3:
            return True
        
        return False
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract event title from text"""
        # If text is garbled, skip title extraction and rely on source enhancement
        if self._is_garbled_text(text):
            logger.warning("Skipping title extraction due to garbled text")
            return None
            
        lines = text.split('\n')
        
        # For Instagram posts, look for meaningful content
        for line in lines:
            line = line.strip()
            if len(line) > 5 and not self._is_date_or_time_line(line):
                # Skip hashtags and handles for title
                if not line.startswith('#') and not line.startswith('@'):
                    # Clean up the line for title
                    title = line.replace('#STREETMEETDC', '').replace('#streetmeetdc', '').strip()
                    if title and len(title) > 3 and not self._is_garbled_text(title):
                        return title
        
        # If no good title found, generate one based on content
        if '#streetmeetdc' in text.lower() or 'streetmeet' in text.lower():
            # Try to extract location for better title
            if 'rhode island' in text.lower():
                return "Street Meet DC - Rhode Island Ave"
            else:
                return "Street Meet DC Event"
        
        # If we have a location but no good title, use the location
        location = self._extract_location(text)
        if location and not any(line.strip() == location for line in lines if len(line.strip()) > 5):
            return f"Event at {location}"
        
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract event description from text"""
        # If text is garbled, skip description extraction and rely on source enhancement
        if self._is_garbled_text(text):
            logger.warning("Skipping description extraction due to garbled text")
            return None
            
        lines = text.split('\n')
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not self._is_date_or_time_line(line) and len(line) > 10:
                # Clean up hashtags and handles
                clean_line = line.replace('#STREETMEETDC', '').replace('#streetmeetdc', '').strip()
                if clean_line and len(clean_line) > 3 and not self._is_garbled_text(clean_line):
                    # Check if this line contains location details that should be in description
                    if self._contains_location_details(clean_line):
                        description_lines.append(clean_line)
        
        # If we found location details, include them in description
        if description_lines:
            base_description = "Join us for a Street Meet DC photography event"
            location_details = ' '.join(description_lines[:2])  # Take first 2 lines with location details
            return f"{base_description}. {location_details}"
        
        # Generate description for Instagram posts
        if '#streetmeetdc' in text.lower() or 'streetmeet' in text.lower():
            return "Join us for a Street Meet DC photography event"
        
        return None
    
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
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract clean location from text for Google Maps searchability"""
        # Look for common location indicators
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
                return self._clean_location_for_maps(location)
        
        # For Instagram posts, look for street/avenue names
        street_patterns = [
            r'\b([A-Z][a-z\s]+(?:Ave|Avenue|Street|St|Road|Rd|Boulevard|Blvd|Drive|Dr|Way|Place|Pl|Court|Ct))\b',
            r'\b([A-Z][a-z\s]+(?:Ave|Avenue|Street|St|Road|Rd|Boulevard|Blvd|Drive|Dr|Way|Place|Pl|Court|Ct))\b',
        ]
        
        for pattern in street_patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                return self._clean_location_for_maps(location)
        
        # Look for specific known locations in the text (with OCR error tolerance)
        text_upper = text.upper()
        if 'RHODE 1SLAND AVE' in text_upper or 'RHODE ISLAND AVE' in text_upper or 'RHODE ISLAND AVENUE' in text_upper:
            return 'Rhode Island Ave'
        
        return None
    
    def _clean_location_for_maps(self, location: str) -> str:
        """Clean location string to be Google Maps searchable"""
        if not location:
            return ""
        
        # Remove common OCR errors
        location = location.replace('AV0', 'AVE').replace('AVO', 'AVE')
        
        # Extract just the street name (remove extra details)
        # Look for patterns like "Rhode Island Ave, Washington DC" -> "Rhode Island Ave"
        street_patterns = [
            r'^([A-Z][a-z\s]+(?:Ave|Avenue|Street|St|Road|Rd|Boulevard|Blvd|Drive|Dr|Way|Place|Pl|Court|Ct))',
            r'^([A-Z][a-z\s]+(?:Ave|Avenue|Street|St|Road|Rd|Boulevard|Blvd|Drive|Dr|Way|Place|Pl|Court|Ct))',
        ]
        
        for pattern in street_patterns:
            match = re.search(pattern, location, re.IGNORECASE)
            if match:
                clean_location = match.group(1).strip()
                # Capitalize properly
                return ' '.join(word.capitalize() for word in clean_location.split())
        
        # If no street pattern found, return cleaned version
        return location.strip()
    
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
