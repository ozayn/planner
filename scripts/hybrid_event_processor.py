#!/usr/bin/env python3
"""
Hybrid Event Processor: Vision API + LLM Intelligence
Combines Google Vision API for OCR with OpenAI LLM for intelligent event extraction
"""

import os
import json
import logging
import re
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
import pytz

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Google Vision API
from google.cloud import vision

# Google Gemini API
import google.generativeai as genai

# OCR fallback
import pytesseract
from PIL import Image

# Local imports
from scripts.image_event_processor import ExtractedEventData, setup_google_credentials

logger = logging.getLogger(__name__)

@dataclass
class HybridEventData:
    """Enhanced event data with LLM processing and Instagram context"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    event_type: Optional[str] = None
    city: Optional[str] = None
    city_id: Optional[int] = None
    confidence: float = 0.0
    source: str = "instagram"
    raw_text: Optional[str] = None
    llm_reasoning: Optional[str] = None
    
    # Social media fields (generic for multiple platforms)
    social_media_platform: Optional[str] = None
    social_media_handle: Optional[str] = None
    social_media_page_name: Optional[str] = None
    social_media_posted_by: Optional[str] = None
    social_media_url: Optional[str] = None
    
    # Legacy Instagram fields for backward compatibility
    instagram_page: Optional[str] = None
    instagram_handle: Optional[str] = None
    instagram_posted_by: Optional[str] = None

class HybridEventProcessor:
    """Hybrid processor combining Vision API OCR with LLM intelligence"""
    
    def __init__(self, ocr_engine_preference='auto'):
        """Initialize the hybrid processor"""
        self.vision_client = None
        self.gemini_model = None
        self.ocr_engine = None
        self.ocr_engine_preference = ocr_engine_preference
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup Google Vision, Gemini, and OCR clients with smart defaults"""
        # Check for user-specified OCR engine preference first
        if self.ocr_engine_preference and self.ocr_engine_preference != 'auto':
            if self.ocr_engine_preference == 'google_vision':
                logger.info("🔧 User selected Google Vision API")
                self._setup_vision_api_first()
            elif self.ocr_engine_preference == 'tesseract':
                logger.info("🔧 User selected Tesseract OCR")
                self._setup_tesseract_first()
        else:
            # Check for forced OCR engine preference from environment
            forced_ocr = os.getenv('FORCE_OCR_ENGINE', '').lower()
            
            if forced_ocr == 'google_vision':
                logger.info("🔧 Forced Google Vision API via FORCE_OCR_ENGINE environment variable")
                self._setup_vision_api_first()
            elif forced_ocr == 'tesseract':
                logger.info("🔧 Forced Tesseract OCR via FORCE_OCR_ENGINE environment variable")
                self._setup_tesseract_first()
            else:
                # Determine environment (local vs deployment)
                is_deployment = self._is_deployment_environment()
                
                if is_deployment:
                    # Deployment: Prefer Google Vision API (more reliable in cloud)
                    logger.info("🌐 Deployment environment detected - using Google Vision API")
                    self._setup_vision_api_first()
                else:
                    # Local: Use Tesseract with optimized settings for speed and accuracy
                    logger.info("💻 Local environment detected - using Tesseract OCR with optimized settings")
                    self._setup_tesseract_first()
        
        # Setup Google Gemini API (always needed for intelligent processing)
        self._setup_gemini()
    
    def _is_deployment_environment(self) -> bool:
        """Detect if we're running in a deployment environment"""
        # Check for common deployment indicators
        deployment_indicators = [
            os.getenv('RAILWAY_ENVIRONMENT'),  # Railway
            os.getenv('HEROKU_APP_NAME'),      # Heroku
            os.getenv('VERCEL'),               # Vercel
            os.getenv('AWS_LAMBDA_FUNCTION_NAME'),  # AWS Lambda
            os.getenv('GOOGLE_CLOUD_PROJECT'), # Google Cloud
            os.getenv('PORT') and int(os.getenv('PORT')) != 5001,  # Non-default port
        ]
        
        return any(deployment_indicators)
    
    def _setup_vision_api_first(self):
        """Setup Vision API first, fallback to Tesseract"""
        try:
            setup_google_credentials()
            self.vision_client = vision.ImageAnnotatorClient()
            self.ocr_engine = 'google_vision'
            logger.info("✅ Google Vision API client initialized (deployment default)")
        except Exception as e:
            logger.warning(f"⚠️ Google Vision API failed: {e}")
            # Fallback to Tesseract
            try:
                pytesseract.get_tesseract_version()
                self.ocr_engine = 'tesseract'
                logger.info("✅ Tesseract OCR fallback initialized")
            except Exception as e2:
                logger.error(f"❌ Failed to setup Tesseract OCR: {e2}")
                self.ocr_engine = None
    
    def _setup_tesseract_first(self):
        """Setup Tesseract first, fallback to Vision API"""
        try:
            pytesseract.get_tesseract_version()
            self.ocr_engine = 'tesseract'
            logger.info("✅ Tesseract OCR initialized (local default)")
        except Exception as e:
            logger.warning(f"⚠️ Tesseract OCR failed: {e}")
            # Fallback to Vision API
            try:
                setup_google_credentials()
                self.vision_client = vision.ImageAnnotatorClient()
                self.ocr_engine = 'google_vision'
                logger.info("✅ Google Vision API fallback initialized")
            except Exception as e2:
                logger.error(f"❌ Failed to setup Google Vision API: {e2}")
                self.ocr_engine = None
    
    def _setup_gemini(self):
        """Setup Google Gemini API"""
        try:
            google_api_key = os.getenv('GOOGLE_API_KEY')
            if not google_api_key:
                logger.warning("⚠️ GOOGLE_API_KEY not found in environment variables")
                return
            
            genai.configure(api_key=google_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("✅ Google Gemini API client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to setup Google Gemini API: {e}")
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using available OCR engine"""
        if not self.ocr_engine:
            raise Exception("No OCR engine available")
        
        if self.ocr_engine == 'google_vision':
            return self._extract_text_with_vision_api(image_path)
        elif self.ocr_engine == 'tesseract':
            return self._extract_text_with_tesseract(image_path)
        else:
            raise Exception(f"Unknown OCR engine: {self.ocr_engine}")
    
    def _extract_text_with_vision_api(self, image_path: str) -> str:
        """Extract text using Google Vision API"""
        if not self.vision_client:
            raise Exception("Google Vision API client not initialized")
        
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = self.vision_client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            texts = response.text_annotations
            if texts:
                # Return the first (full) text annotation
                extracted_text = texts[0].description
                logger.info(f"✅ Vision API extracted {len(extracted_text)} characters")
                return extracted_text
            else:
                logger.warning("⚠️ No text found in image with Vision API")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Error extracting text with Vision API: {e}")
            raise
    
    def _extract_text_with_tesseract(self, image_path: str) -> str:
        """Extract text using Tesseract OCR"""
        try:
            # Open image with PIL
            image = Image.open(image_path)
            
            # Extract text using Tesseract with optimized settings
            # PSM 6: Assume a single uniform block of text
            # OEM 3: Default OCR Engine Mode
            config = '--psm 6 --oem 3'
            extracted_text = pytesseract.image_to_string(image, config=config)
            
            logger.info(f"✅ Tesseract extracted {len(extracted_text)} characters")
            return extracted_text
            
        except Exception as e:
            logger.error(f"❌ Error extracting text with Tesseract: {e}")
            raise
    
    def process_image_with_llm(self, image_path: str) -> HybridEventData:
        """Process image using hybrid OCR + LLM approach"""
        logger.info(f"🔍 Processing image with hybrid approach: {image_path}")
        logger.info(f"📷 Using OCR engine: {self.ocr_engine}")
        
        # Step 1: Extract text using available OCR engine
        try:
            raw_text = self.extract_text_from_image(image_path)
            logger.info(f"📝 Raw text extracted: {len(raw_text)} characters")
            logger.info(f"📝 Raw OCR text: {repr(raw_text)}")
        except Exception as e:
            logger.error(f"❌ Failed to extract text: {e}")
            return HybridEventData()
        
        # Step 2: Process with LLM
        try:
            event_data = self._process_text_with_llm(raw_text)
            event_data.raw_text = raw_text
            logger.info("✅ LLM processing completed")
            return event_data
        except Exception as e:
            logger.error(f"❌ Failed to process with LLM: {e}")
            # Fallback to basic extraction
            return self._fallback_extraction(raw_text)
    
    def _process_text_with_llm(self, text: str) -> HybridEventData:
        """Process extracted text using Google Gemini"""
        if not self.gemini_model:
            raise Exception("Google Gemini API client not initialized")
        
        prompt = self._create_extraction_prompt(text)
        
        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for consistent results
                    max_output_tokens=1000,
                )
            )
            
            llm_response = response.text
            logger.info(f"🤖 Gemini response received: {len(llm_response)} characters")
            logger.info(f"🤖 LLM response: {repr(llm_response)}")
            
            # Parse the LLM response
            event_data = self._parse_llm_response(llm_response)
            event_data.llm_reasoning = llm_response
            
            return event_data
            
        except Exception as e:
            logger.error(f"❌ Google Gemini API error: {e}")
            raise
    
    def _create_extraction_prompt(self, text: str) -> str:
        """Create a structured prompt for event extraction with social media context"""
        return f"""
Extract event information from this social media post text. Be intelligent and logical.

TEXT TO ANALYZE:
{text}

INSTRUCTIONS:
1. IGNORE timestamps like "12:18 Posts", "3 days ago", "2 hours ago" - these are post metadata, not event times
2. EXTRACT the actual event information
3. ALWAYS extract a meaningful title - use the event name, page name, or create one from context
4. USE FULL location names (e.g., "Rhode Island Ave" not "Island Ave")
5. ALWAYS estimate end time if not explicitly mentioned - add 2 hours to start time
6. USE same location for end location if not specified
7. RECOGNIZE social media context and extract platform/handle information
8. IDENTIFY the social media platform and page that posted this event
9. NEVER return the same time for both start_time and end_time
10. NEVER return null for title - always provide a meaningful event title
11. INFER city from location context - if location mentions "Rhode Island Ave", "DC", "Washington", "streetmeetdc", etc., set city to "Washington"
12. INFER city from social media handle - if handle contains "dc" (like "streetmeetdc"), set city to "Washington"

RETURN ONLY a JSON object with this exact structure:
{{
    "title": "meaningful event title (REQUIRED - never null)",
    "description": "brief event description or null", 
    "start_date": "YYYY-MM-DD or null",
    "end_date": "YYYY-MM-DD or null",
    "start_time": "HH:MM:SS or null",
    "end_time": "HH:MM:SS or null",
    "start_location": "full location name or null",
    "end_location": "full location name or null",
    "event_type": "photowalk|meetup|tour|exhibition|festival|other or null",
    "city": "city name or null",
    "confidence": 0.0-1.0,
    "social_media_platform": "instagram|meetup|eventbrite|facebook|other or null",
    "social_media_handle": "handle without @ (e.g., 'streetmeetdc') or null",
    "social_media_page_name": "page/group name (e.g., 'DC Street Meet') or null",
    "social_media_posted_by": "who posted this (page name) or null",
    "social_media_url": "direct URL to post/event or null"
}}

        EXAMPLES:
        - "SEP 28 | 4PM" → start_date: "2025-09-28", start_time: "16:00:00", end_time: "18:00:00" (4PM + 2 hours)
        - "MEET AT 11:00, WALK AT 11:30" → start_time: "11:00:00", end_time: "13:30:00", description: "Meet at 11:00 AM, walk starts at 11:30 AM"
        - "Rhode Island Ave metro station" → start_location: "Rhode Island Ave", city: "Washington"
        - "streetmeetdc" → social_media_platform: "instagram", social_media_handle: "streetmeetdc", social_media_page_name: "DC Street Meet", city: "Washington"
        - "DC streetmeetdc" → social_media_platform: "instagram", social_media_page_name: "DC Street Meet", social_media_handle: "streetmeetdc", city: "Washington"
        - If only start time mentioned: ALWAYS add 2 hours for end time
        - If meet time and walk time mentioned: use meet time as start_time, add 2 hours from walk time for end_time
        - ALWAYS use year 2025 for current events (we are in 2025)
        - If date is in the past for 2025, assume it's for next year (2026)
        - City inference: "Rhode Island Ave" + "streetmeetdc" → city: "Washington"
        - Include timing details in description when multiple times are mentioned

Be precise and logical. If uncertain, use null.
"""
    
    def _parse_llm_response(self, response: str) -> HybridEventData:
        """Parse LLM response into structured event data"""
        try:
            # Extract JSON from response (handle markdown formatting)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            # Convert to HybridEventData
            event_data = HybridEventData()
            
            # Basic fields
            event_data.title = data.get('title')
            event_data.description = data.get('description')
            event_data.event_type = data.get('event_type')
            event_data.city = self._normalize_city_name(data.get('city'))
            event_data.city_id = self._get_city_id(event_data.city)
            event_data.confidence = float(data.get('confidence', 0.0))
            
            # Dates - use city timezone if available
            city_timezone = None
            if event_data.city:
                city_timezone = self._get_city_timezone(event_data.city)
            
            if data.get('start_date'):
                event_data.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if data.get('end_date'):
                event_data.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            elif event_data.start_date:
                event_data.end_date = event_data.start_date  # Same day
            
            # Times
            if data.get('start_time'):
                event_data.start_time = datetime.strptime(data['start_time'], '%H:%M:%S').time()
            if data.get('end_time'):
                event_data.end_time = datetime.strptime(data['end_time'], '%H:%M:%S').time()
            
            # Apply our rule: if end time is not provided OR same as start time, estimate 2 hours later
            if not data.get('end_time') or (event_data.start_time and event_data.end_time and event_data.start_time == event_data.end_time):
                if event_data.start_time:
                    event_data.end_time = self._estimate_end_time(event_data.start_time)
                    logger.info(f"🕐 Applied 2-hour rule: {event_data.start_time} → {event_data.end_time}")
            
            # Locations
            event_data.start_location = data.get('start_location')
            event_data.end_location = data.get('end_location') or event_data.start_location
            
            # If start_location is empty but description contains location info, extract it
            if not event_data.start_location and event_data.description:
                location_match = re.search(r'(?:join us at|meet at|at)\s*([A-Za-z\s]+(?:Ave|Street|St|Road|Rd|Metro|Station|Circle|Square|Mall|Park|Center|Building|Museum|Gallery|Theater|Theatre))', event_data.description, re.IGNORECASE)
                if location_match:
                    event_data.start_location = location_match.group(1).strip()
                    event_data.end_location = event_data.start_location
                    logger.info(f"📍 Extracted location from description: {event_data.start_location}")
            
            # Social media fields
            event_data.social_media_platform = data.get('social_media_platform')
            event_data.social_media_handle = data.get('social_media_handle')
            event_data.social_media_page_name = data.get('social_media_page_name')
            event_data.social_media_posted_by = data.get('social_media_posted_by')
            event_data.social_media_url = data.get('social_media_url')
            
            # Legacy Instagram fields for backward compatibility
            event_data.instagram_page = data.get('instagram_page')
            event_data.instagram_handle = data.get('instagram_handle')
            event_data.instagram_posted_by = data.get('instagram_posted_by')
            
            logger.info("✅ Successfully parsed LLM response")
            return event_data
            
        except Exception as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            logger.error(f"Response was: {response}")
            raise
    
    def _estimate_end_time(self, start_time: time) -> time:
        """Estimate end time (2 hours default)"""
        start_hour = start_time.hour
        start_minute = start_time.minute
        
        # Add 2 hours
        total_minutes = start_hour * 60 + start_minute + 120
        end_hour = (total_minutes // 60) % 24
        end_minute = total_minutes % 60
        
        return time(end_hour, end_minute)
    
    def _estimate_end_location(self, start_location: Optional[str], text: str) -> Optional[str]:
        """Estimate end location if not specified"""
        if not start_location:
            return None
        
        # Look for "from X to Y" patterns
        from_to_pattern = r'from\s+([^,\n]+?)\s+to\s+([^,\n]+)'
        match = re.search(from_to_pattern, text, re.IGNORECASE)
        if match:
            return match.group(2).strip()
        
        # Default: same as start location
        return start_location
    
    def _normalize_city_name(self, city_name: Optional[str]) -> Optional[str]:
        """Normalize city name to match database entries using comprehensive city recognition"""
        if not city_name:
            return None
        
        # Direct city name mapping for common cases
        city_mappings = {
            'washington': 'Washington',
            'washington dc': 'Washington',
            'washington, dc': 'Washington',
            'washington d.c.': 'Washington',
            'washington, d.c.': 'Washington',
            'dc': 'Washington',
            'new york': 'New York',
            'nyc': 'New York',
            'new york city': 'New York',
            'los angeles': 'Los Angeles',
            'la': 'Los Angeles',
            'san francisco': 'San Francisco',
            'sf': 'San Francisco',
            'chicago': 'Chicago',
            'boston': 'Boston',
            'seattle': 'Seattle',
            'miami': 'Miami'
        }
        
        # Check direct mapping first
        city_lower = city_name.lower().strip()
        if city_lower in city_mappings:
            return city_mappings[city_lower]
        
        # Fallback to text extraction for complex cases
        city_info = self._extract_city_info(city_name)
        return city_info.get('city')
    
    def _get_city_id(self, city_name: Optional[str]) -> Optional[int]:
        """Get city ID from city name using the city lookup"""
        if not city_name:
            return None
        
        try:
            city_lookup = self._load_city_data()
            city_lower = city_name.lower().strip()
            
            # Try direct name lookup first
            if city_lower in city_lookup:
                return city_lookup[city_lower]['id']
            
            # Try name + state lookup for Washington DC
            if city_lower == 'washington':
                dc_key = 'washington,district of columbia'
                if dc_key in city_lookup:
                    return city_lookup[dc_key]['id']
            
            logger.warning(f"City ID not found for: {city_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting city ID for {city_name}: {e}")
            return None
    
    def _get_city_timezone(self, city_name: str, state: str = None) -> Optional[str]:
        """Get timezone for a city from the city data"""
        if not city_name:
            return None
        
        # Load city data if not already loaded
        if not hasattr(self, 'city_data') or not self.city_data:
            self.city_data = self._load_city_data()
        
        city_key = city_name.lower()
        state_key = state.lower() if state else ""
        
        # Try exact match with state
        if state:
            full_key = f"{city_key},{state_key}"
            if full_key in self.city_data:
                return self.city_data[full_key].get('timezone')
        
        # Try city name only
        if city_key in self.city_data:
            return self.city_data[city_key].get('timezone')
        
        # Try partial matches
        for key, city_info in self.city_data.items():
            if city_name.lower() in city_info['name'].lower():
                if not state or state.lower() in city_info['state'].lower():
                    return city_info.get('timezone')
        
        return None
    
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
                            'country': city_info.get('country'),
                            'timezone': city_info.get('timezone')
                        }
                        
                        # Also add by name only (for cases where state might not match exactly)
                        city_lookup[name] = {
                            'id': int(city_id),
                            'name': city_info.get('name'),
                            'state': city_info.get('state'),
                            'country': city_info.get('country'),
                            'timezone': city_info.get('timezone')
                        }
                
                logger.info(f"Loaded {len(city_lookup)} city entries")
                return city_lookup
        except Exception as e:
            logger.warning(f"Could not load city data: {e}")
        
        return {}
    
    def _setup_city_mappings(self) -> Dict[str, Dict[str, str]]:
        """Setup city/state mappings for location extraction (same as image_event_processor)"""
        return {
            # Washington, DC area
            'dc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'washington dc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'washington, dc': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'washington d.c.': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
            'washington, d.c.': {'city': 'Washington', 'state': 'DC', 'country': 'United States'},
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
            
            # San Francisco
            'sf': {'city': 'San Francisco', 'state': 'CA', 'country': 'United States'},
            'san francisco': {'city': 'San Francisco', 'state': 'CA', 'country': 'United States'},
            
            # Chicago
            'chicago': {'city': 'Chicago', 'state': 'IL', 'country': 'United States'},
            
            # Boston
            'boston': {'city': 'Boston', 'state': 'MA', 'country': 'United States'},
            
            # Seattle
            'seattle': {'city': 'Seattle', 'state': 'WA', 'country': 'United States'},
            
            # Miami
            'miami': {'city': 'Miami', 'state': 'FL', 'country': 'United States'},
            
            # International cities
            'london': {'city': 'London', 'state': 'England', 'country': 'United Kingdom'},
            'paris': {'city': 'Paris', 'state': 'Île-de-France', 'country': 'France'},
            'tokyo': {'city': 'Tokyo', 'state': 'Tokyo', 'country': 'Japan'},
            'sydney': {'city': 'Sydney', 'state': 'New South Wales', 'country': 'Australia'},
            'montreal': {'city': 'Montreal', 'state': 'Quebec', 'country': 'Canada'},
            'toronto': {'city': 'Toronto', 'state': 'Ontario', 'country': 'Canada'},
            'vancouver': {'city': 'Vancouver', 'state': 'British Columbia', 'country': 'Canada'},
        }
    
    def _extract_city_info(self, text: str) -> Dict[str, str]:
        """Extract city information from text (same logic as image_event_processor)"""
        text_lower = text.lower().strip()
        city_mappings = self._setup_city_mappings()
        
        # Direct mapping lookup
        for location_key, city_info in city_mappings.items():
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
            if word in city_mappings:
                return city_mappings[word]
        
        return {'city': None, 'state': None, 'country': None}
    
    def _fallback_extraction(self, text: str) -> HybridEventData:
        """Fallback extraction when LLM fails"""
        logger.warning("⚠️ Using fallback extraction")
        
        event_data = HybridEventData()
        event_data.raw_text = text
        event_data.confidence = 0.3  # Lower confidence for fallback
        
        # Enhanced fallback logic with regex patterns
        import re
        
        # Extract dates (MMM DD, DD/MM, etc.) with timezone context
        city_timezone = None
        if event_data.city:
            city_timezone = self._get_city_timezone(event_data.city)
        
        # Get current year in city timezone
        current_year = 2025  # Default
        if city_timezone:
            try:
                tz = pytz.timezone(city_timezone)
                current_year = datetime.now(tz).year
            except:
                current_year = datetime.now().year
        else:
            current_year = datetime.now().year
        
        date_patterns = [
            r'([A-Z]{3})\s+(\d{1,2})',  # SEP 28, OCT 15
            r'(\d{1,2})[/\-](\d{1,2})',  # 28/09, 09-28
            r'(\d{1,2})\s+([A-Z]{3})',  # 28 SEP
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Try to parse the date (simplified)
                try:
                    if 'SEP' in text.upper():
                        event_data.start_date = date(current_year, 9, int(match.group(2)) if match.group(2).isdigit() else int(match.group(1)))
                    elif 'OCT' in text.upper():
                        event_data.start_date = date(current_year, 10, int(match.group(2)) if match.group(2).isdigit() else int(match.group(1)))
                    
                    # Apply rule: end_date = start_date if not explicitly mentioned
                    event_data.end_date = event_data.start_date
                    break
                except:
                    pass
        
        # Extract times (4PM, 16:00, etc.)
        time_patterns = [
            r'(\d{1,2}):(\d{2})',  # 16:00, 4:30
            r'(\d{1,2})\s*(AM|PM)',  # 4PM, 4 PM, 4AM
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if ':' in match.group(0):
                        # 24-hour format
                        hour, minute = int(match.group(1)), int(match.group(2))
                        event_data.start_time = time(hour, minute)
                    else:
                        # 12-hour format
                        hour = int(match.group(1))
                        period = match.group(2).upper()
                        if period == 'PM' and hour != 12:
                            hour += 12
                        elif period == 'AM' and hour == 12:
                            hour = 0
                        event_data.start_time = time(hour, 0)
                    
                    # Add 2 hours for end time
                    if event_data.start_time:
                        event_data.end_time = self._estimate_end_time(event_data.start_time)
                    break
                except:
                    pass
        
        # Extract locations
        location_patterns = [
            r'([A-Za-z\s]+(?:Ave|Street|St|Road|Rd|Metro|Station|Circle|Square))',
            r'(Rhode Island|Dupont|Georgetown|Capitol|National Mall)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                event_data.start_location = match.group(1).strip()
                event_data.end_location = event_data.start_location
                break
        
        # Extract event type based on keywords
        text_lower = text.lower()
        if 'streetmeet' in text_lower or 'photowalk' in text_lower:
            event_data.title = "DC Street Meet"
            event_data.event_type = "photowalk"
            event_data.city = self._normalize_city_name("DC")
        elif 'tour' in text_lower:
            event_data.event_type = "tour"
        elif 'exhibition' in text_lower or 'exhibit' in text_lower:
            event_data.event_type = "exhibition"
        elif 'festival' in text_lower:
            event_data.event_type = "festival"
        
        # Extract Instagram page/handle with multiple patterns
        instagram_patterns = [
            r'@([a-zA-Z0-9_]+)',  # @streetmeetdc
            r'instagram\.com/([a-zA-Z0-9_]+)',  # instagram.com/streetmeetdc
            r'([a-zA-Z0-9_]+)\s*instagram',  # streetmeetdc instagram
            r'([a-zA-Z0-9_]+)\s*@',  # streetmeetdc @
        ]
        
        for pattern in instagram_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                handle = match.group(1).lower()
                event_data.social_media_platform = "instagram"
                event_data.social_media_handle = handle
                
                # Convert handle to page name (capitalize and add spaces)
                if 'streetmeet' in handle:
                    event_data.social_media_page_name = "DC Street Meet"
                elif 'dc' in handle:
                    event_data.social_media_page_name = f"DC {handle.replace('dc', '').title()}"
                else:
                    event_data.social_media_page_name = handle.title()
                
                event_data.social_media_posted_by = event_data.social_media_page_name
                
                # Legacy Instagram fields for backward compatibility
                event_data.instagram_handle = handle
                event_data.instagram_page = event_data.social_media_page_name
                event_data.instagram_posted_by = event_data.social_media_posted_by
                break
        
        # If we found some basic info, set a title
        if not event_data.title and (event_data.start_date or event_data.start_time or event_data.start_location):
            event_data.title = "Event from Image"
        
        logger.info(f"📝 Fallback extracted: {event_data.title}, {event_data.start_date}, {event_data.end_date}, {event_data.start_time}, {event_data.start_location}")
        if event_data.social_media_handle:
            logger.info(f"📱 {event_data.social_media_platform.title()}: @{event_data.social_media_handle} ({event_data.social_media_page_name})")
        elif event_data.instagram_handle:
            logger.info(f"📱 Instagram: @{event_data.instagram_handle} ({event_data.instagram_page})")
        return event_data

def main():
    """Test the hybrid processor"""
    processor = HybridEventProcessor()
    
    # Test with sample image
    image_path = 'uploads/event_image_20250922_133250_2025-09-22 12.19.38.jpg'
    
    if os.path.exists(image_path):
        print(f"🧪 Testing hybrid processor on: {image_path}")
        
        try:
            result = processor.process_image_with_llm(image_path)
            
            print("\n✅ Hybrid processing results:")
            print(f"Title: {result.title}")
            print(f"Description: {result.description}")
            print(f"Start Date: {result.start_date}")
            print(f"End Date: {result.end_date}")
            print(f"Start Time: {result.start_time}")
            print(f"End Time: {result.end_time}")
            print(f"Start Location: {result.start_location}")
            print(f"End Location: {result.end_location}")
            print(f"Event Type: {result.event_type}")
            print(f"City: {result.city}")
            print(f"Confidence: {result.confidence}")
            print(f"Source: {result.source}")
            
            if result.llm_reasoning:
                print(f"\n🤖 LLM Reasoning:")
                print(result.llm_reasoning)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ Image not found: {image_path}")

if __name__ == '__main__':
    main()
