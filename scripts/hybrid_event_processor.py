#!/usr/bin/env python3
"""
Hybrid Event Processor: Vision API + LLM Intelligence
Combines Google Vision API for OCR with OpenAI LLM for intelligent event extraction
"""

import os
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

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
    confidence: float = 0.0
    source: str = "instagram"
    raw_text: Optional[str] = None
    llm_reasoning: Optional[str] = None
    
    # Instagram-specific fields
    instagram_page: Optional[str] = None
    instagram_handle: Optional[str] = None
    instagram_posted_by: Optional[str] = None

class HybridEventProcessor:
    """Hybrid processor combining Vision API OCR with LLM intelligence"""
    
    def __init__(self):
        """Initialize the hybrid processor"""
        self.vision_client = None
        self.gemini_model = None
        self.ocr_engine = None
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup Google Vision, Gemini, and OCR clients with smart defaults"""
        # Determine environment (local vs deployment)
        is_deployment = self._is_deployment_environment()
        
        if is_deployment:
            # Deployment: Prefer Google Vision API (more reliable in cloud)
            logger.info("🌐 Deployment environment detected - using Google Vision API")
            self._setup_vision_api_first()
        else:
            # Local: Prefer Tesseract (free and works well locally)
            logger.info("💻 Local environment detected - using Tesseract OCR")
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
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
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
            
            # Extract text using Tesseract
            extracted_text = pytesseract.image_to_string(image)
            
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
            
            # Parse the LLM response
            event_data = self._parse_llm_response(llm_response)
            event_data.llm_reasoning = llm_response
            
            return event_data
            
        except Exception as e:
            logger.error(f"❌ Google Gemini API error: {e}")
            raise
    
    def _create_extraction_prompt(self, text: str) -> str:
        """Create a structured prompt for event extraction with Instagram context"""
        return f"""
Extract event information from this Instagram post text. Be intelligent and logical.

TEXT TO ANALYZE:
{text}

INSTRUCTIONS:
1. IGNORE timestamps like "12:18 Posts", "3 days ago", "2 hours ago" - these are post metadata, not event times
2. EXTRACT the actual event information
3. USE FULL location names (e.g., "Rhode Island Ave" not "Island Ave")
4. ESTIMATE end time if not mentioned (default 2 hours for most events)
5. USE same location for end location if not specified
6. RECOGNIZE Instagram context and extract page/handle information
7. IDENTIFY the Instagram page that posted this event

RETURN ONLY a JSON object with this exact structure:
{{
    "title": "event title or null",
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
    "instagram_page": "Instagram page name (e.g., 'DC Street Meet') or null",
    "instagram_handle": "Instagram handle (e.g., 'streetmeetdc') or null",
    "instagram_posted_by": "who posted this (page name) or null"
}}

EXAMPLES:
- "SEP 28 | 4PM" → start_date: "2025-09-28", start_time: "16:00:00", end_time: "18:00:00"
- "Rhode Island Ave metro station" → start_location: "Rhode Island Ave"
- "streetmeetdc" → instagram_handle: "streetmeetdc", instagram_page: "DC Street Meet"
- "DC streetmeetdc" → instagram_page: "DC Street Meet", instagram_handle: "streetmeetdc"

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
            event_data.confidence = float(data.get('confidence', 0.0))
            
            # Dates
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
            elif event_data.start_time:
                # Estimate end time if not provided
                event_data.end_time = self._estimate_end_time(event_data.start_time)
            
            # Locations
            event_data.start_location = data.get('start_location')
            event_data.end_location = data.get('end_location') or event_data.start_location
            
            # Instagram-specific fields
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
        
        # Use the same city recognition logic as image_event_processor
        city_info = self._extract_city_info(city_name)
        return city_info.get('city')
    
    def _setup_city_mappings(self) -> Dict[str, Dict[str, str]]:
        """Setup city/state mappings for location extraction (same as image_event_processor)"""
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
        
        # Basic fallback logic
        if 'streetmeet' in text.lower():
            event_data.title = "DC Street Meet"
            event_data.event_type = "photowalk"
            event_data.city = self._normalize_city_name("DC")
        
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
