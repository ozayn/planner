#!/usr/bin/env python3
"""
DYNAMIC PROMPT GENERATION UTILITIES
Generates LLM prompts dynamically based on database models and field requirements
"""

import sys
import os
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DynamicPromptGenerator:
    """Generates dynamic prompts based on database models"""
    
    @staticmethod
    def get_model_fields(model_class) -> List[str]:
        """Dynamically get all fields from any SQLAlchemy model"""
        try:
            fields = []
            for column in model_class.__table__.columns:
                fields.append(column.name)
            return sorted(fields)
        except Exception as e:
            print(f"Warning: Could not get fields from {model_class.__name__}: {e}")
            return []
    
    @staticmethod
    def get_venue_fields() -> List[str]:
        """Get venue fields dynamically from Venue model"""
        try:
            from app import Venue
            return DynamicPromptGenerator.get_model_fields(Venue)
        except ImportError:
            print("Warning: Could not import Venue model")
            return []
    
    @staticmethod
    def get_event_fields() -> List[str]:
        """Get event fields dynamically from Event model"""
        try:
            from app import Event
            return DynamicPromptGenerator.get_model_fields(Event)
        except ImportError:
            print("Warning: Could not import Event model")
            return []
    
    @staticmethod
    def get_city_fields() -> List[str]:
        """Get city fields dynamically from City model"""
        try:
            from app import City
            return DynamicPromptGenerator.get_model_fields(City)
        except ImportError:
            print("Warning: Could not import City model")
            return []
    
    @staticmethod
    def generate_field_description(field_name: str, column_info: dict = None) -> str:
        """Generate dynamic field description based on field name and type"""
        # Basic field name to description mapping
        descriptions = {
            'id': 'Unique identifier',
            'name': 'Full official name',
            'venue_type': 'Type of venue - MUST match one of these EXACT values: Museum, Science Museum, Gallery, Theater, Performing Arts Center, Concert Hall, Park, Botanical Garden, Library, Historic Site, Historic District, Historic Trail, Monument, Memorial, Landmark, Cultural Center, Arts Center, Community Center, Convention Center, Exhibition Hall, Auditorium, Stadium, Arena, Market, Shopping District, Art District, Government Building, Observation Tower, Observation Deck, Observatory, Aquarium, Zoo, Cathedral, Church, Temple, Shrine, Bridge, Castle, Palace, Beach, Waterfront, Waterway, Avenue, or Other',
            'event_type': 'Type of event (tour, exhibition, festival, etc.)',
            'description': 'Detailed description',
            'address': 'Complete street address',
            'website_url': 'Official website URL',
            'image_url': 'Image URL (leave empty, will be filled by Google Maps)',
            'instagram_url': 'Instagram handle (e.g., @museumname)',
            'facebook_url': 'Facebook page URL',
            'twitter_url': 'Twitter handle (e.g., @museumname)',
            'youtube_url': 'YouTube channel URL',
            'tiktok_url': 'TikTok handle (e.g., @museumname)',
            'phone_number': 'Contact phone number',
            'email': 'Contact email address',
            'opening_hours': 'Operating hours (e.g., Mon-Fri: 9AM-5PM)',
            'holiday_hours': 'Holiday hours or special hours',
            'tour_info': 'Tour information and details',
            'admission_fee': 'Admission fee (e.g., Free, $15, $10-20)',
            'additional_info': 'Additional venue information (JSON format)',
            'latitude': 'Latitude coordinate',
            'longitude': 'Longitude coordinate',
            'city_id': 'City identifier',
            'venue_id': 'Venue identifier',
            'start_date': 'Event start date',
            'end_date': 'Event end date',
            'start_time': 'Event start time',
            'end_time': 'Event end time',
            'created_at': 'Creation timestamp',
            'updated_at': 'Last update timestamp'
        }
        
        # Return specific description if available, otherwise generate from field name
        if field_name in descriptions:
            return descriptions[field_name]
        else:
            # Generate description from field name
            return field_name.replace('_', ' ').title()
    
    @staticmethod
    def generate_field_descriptions(fields: List[str], exclude_fields: List[str] = None) -> List[str]:
        """Generate descriptions for a list of fields"""
        if exclude_fields is None:
            exclude_fields = ['id', 'created_at', 'updated_at']
        
        field_descriptions = []
        for field in fields:
            if field not in exclude_fields:
                description = DynamicPromptGenerator.generate_field_description(field)
                field_descriptions.append(f"- {field}: {description}")
        
        return field_descriptions
    
    @staticmethod
    def generate_venue_discovery_prompt(city_name: str, country: str = None, event_type: str = 'tours', max_venues: int = 6) -> str:
        """Generate dynamic venue discovery prompt"""
        venue_fields = DynamicPromptGenerator.get_venue_fields()
        
        # Generate field descriptions dynamically
        field_descriptions = DynamicPromptGenerator.generate_field_descriptions(
            venue_fields, 
            exclude_fields=['id', 'city_id', 'created_at', 'updated_at']
        )
        fields_text = '\n'.join(field_descriptions)
        
        # Create location context with full details
        location_context = city_name
        if country:
            location_context += f", {country}"
        
        return f"""Find {max_venues} venues in {location_context} that offer {event_type}.

For each venue, provide:
{fields_text}

Return as JSON array. Focus on venues that actually offer {event_type}.
Include the full location details: city name, state/province/equivalent, and country in the address field."""
    
    @staticmethod
    def generate_venue_details_prompt(venue_name: str, city: str = None, country: str = None) -> str:
        """Generate simple, direct venue details prompt"""
        location = city or 'any city'
        if country:
            location += f", {country}"
        
        return f"""Find CURRENT and ACCURATE information about "{venue_name}" in {location}.

IMPORTANT: For admission_fee, provide the CURRENT 2024-2025 pricing. Many museums have changed from free to paid admission in recent years. Check the most recent information.

Return ONLY a JSON object with these fields:
- name: Official name
- address: Full street address
- venue_type: Type - MUST be one of these EXACT values: Museum, Science Museum, Gallery, Theater, Performing Arts Center, Concert Hall, Park, Botanical Garden, Library, Historic Site, Historic District, Historic Trail, Monument, Memorial, Landmark, Cultural Center, Arts Center, Community Center, Convention Center, Exhibition Hall, Auditorium, Stadium, Arena, Market, Shopping District, Art District, Government Building, Observation Tower, Observation Deck, Observatory, Aquarium, Zoo, Cathedral, Church, Temple, Shrine, Bridge, Castle, Palace, Beach, Waterfront, Waterway, Avenue, or Other. Choose the MOST APPROPRIATE type from this list.
- description: Brief description
- website_url: Official website
- phone_number: Contact phone
- email: Contact email
- opening_hours: Operating hours
- admission_fee: CURRENT admission cost (e.g., "Free", "$20", "$15-25", "$20 adults, $15 seniors, free under 18")
- latitude: Latitude coordinate
- longitude: Longitude coordinate
- instagram_url: Instagram handle (e.g., "@venue")
- facebook_url: Facebook page URL
- twitter_url: Twitter handle (e.g., "@venue")
- youtube_url: YouTube channel URL
- tiktok_url: TikTok handle (e.g., "@venue")
- tour_info: Tour information
- holiday_hours: Holiday hours
- additional_info: Additional details (JSON object)

Return ONLY valid JSON, no other text."""
    
    @staticmethod
    def generate_event_details_prompt(event_name: str, venue_name: str = None, city: str = None) -> str:
        """Generate dynamic event details prompt"""
        event_fields = DynamicPromptGenerator.get_event_fields()
        
        # Create field descriptions
        field_descriptions = []
        for field in event_fields:
            if field in ['id', 'venue_id', 'city_id', 'created_at', 'updated_at']:
                continue  # Skip system fields
            
            if field == 'name':
                field_descriptions.append(f"- {field}: Event name")
            elif field == 'event_type':
                field_descriptions.append(f"- {field}: Type of event")
            elif field == 'description':
                field_descriptions.append(f"- {field}: Detailed description")
            elif field == 'start_time':
                field_descriptions.append(f"- {field}: Start time")
            elif field == 'end_time':
                field_descriptions.append(f"- {field}: End time")
            elif field == 'duration':
                field_descriptions.append(f"- {field}: Duration")
            elif field == 'price':
                field_descriptions.append(f"- {field}: Price information")
            elif field == 'language':
                field_descriptions.append(f"- {field}: Language(s)")
            elif field == 'max_participants':
                field_descriptions.append(f"- {field}: Maximum participants")
            elif field == 'difficulty_level':
                field_descriptions.append(f"- {field}: Difficulty level")
            elif field == 'equipment_needed':
                field_descriptions.append(f"- {field}: Required equipment")
            elif field == 'age_restrictions':
                field_descriptions.append(f"- {field}: Age restrictions")
            elif field == 'dress_code':
                field_descriptions.append(f"- {field}: Dress code")
            elif field == 'booking_info':
                field_descriptions.append(f"- {field}: Booking information")
            elif field == 'cancellation_policy':
                field_descriptions.append(f"- {field}: Cancellation policy")
            elif field == 'organizer':
                field_descriptions.append(f"- {field}: Organizer information")
            elif field == 'special_requirements':
                field_descriptions.append(f"- {field}: Special requirements")
            else:
                field_descriptions.append(f"- {field}: {field.replace('_', ' ').title()}")
        
        fields_text = '\n'.join(field_descriptions)
        location_context = f" at {venue_name}" if venue_name else ""
        city_context = f" in {city}" if city else ""
        
        return f"""Provide comprehensive details for the event "{event_name}"{location_context}{city_context}.

Include:
{fields_text}

Return as JSON object with these exact field names."""
    
    @staticmethod
    def generate_city_lookup_prompt(city_name: str, country: str = None) -> str:
        """Generate dynamic city lookup prompt"""
        city_fields = DynamicPromptGenerator.get_city_fields()
        
        # Create field descriptions
        field_descriptions = []
        for field in city_fields:
            if field in ['id', 'created_at', 'updated_at']:
                continue  # Skip system fields
            
            if field == 'name':
                field_descriptions.append(f"- {field}: Official city name")
            elif field == 'state':
                field_descriptions.append(f"- {field}: State/province/region")
            elif field == 'country':
                field_descriptions.append(f"- {field}: Country name")
            elif field == 'timezone':
                field_descriptions.append(f"- {field}: Timezone (e.g., 'America/New_York')")
            else:
                field_descriptions.append(f"- {field}: {field.replace('_', ' ').title()}")
        
        fields_text = '\n'.join(field_descriptions)
        
        return f"""Provide accurate information for the city "{city_name}" in {country or 'any country'}.

Include:
{fields_text}

Return as JSON object with these exact field names."""

if __name__ == "__main__":
    # Test the dynamic prompt generator
    print("🧪 Testing Dynamic Prompt Generator")
    print("=" * 50)
    
    generator = DynamicPromptGenerator()
    
    print("\n1. Venue Fields:")
    venue_fields = generator.get_venue_fields()
    print(f"   Found {len(venue_fields)} fields: {venue_fields[:5]}...")
    
    print("\n2. Event Fields:")
    event_fields = generator.get_event_fields()
    print(f"   Found {len(event_fields)} fields: {event_fields[:5]}...")
    
    print("\n3. City Fields:")
    city_fields = generator.get_city_fields()
    print(f"   Found {len(city_fields)} fields: {city_fields}")
    
    print("\n4. Sample Venue Discovery Prompt:")
    prompt = generator.generate_venue_discovery_prompt("Paris", "France", "tours", 3)
    print(f"   Length: {len(prompt)} characters")
    print(f"   Preview: {prompt[:200]}...")
    
    print("\n✅ Dynamic Prompt Generator test complete!")
