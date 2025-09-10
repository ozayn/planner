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
    def get_venue_fields() -> List[str]:
        """Get all venue fields from the Venue model"""
        # Define venue fields without importing from app to avoid circular imports
        return [
            'id', 'name', 'venue_type', 'description', 'address', 'latitude', 'longitude', 
            'website_url', 'phone', 'email', 'hours', 'price_range', 'rating', 
            'amenities', 'accessibility', 'parking', 'public_transport', 
            'special_features', 'capacity', 'age_restrictions', 'dress_code', 
            'booking_info', 'cancellation_policy', 'city_id', 'created_at', 'updated_at'
        ]
    
    @staticmethod
    def get_event_fields() -> List[str]:
        """Get all event fields from the Event model"""
        # Define event fields without importing from app to avoid circular imports
        return [
            'id', 'title', 'description', 'start_date', 'end_date', 'start_time', 
            'end_time', 'duration', 'price', 'language', 'max_participants', 
            'difficulty_level', 'equipment_needed', 'age_restrictions', 'dress_code', 
            'booking_info', 'cancellation_policy', 'organizer', 'special_requirements',
            'start_location', 'end_location', 'venue_id', 'city_id', 'start_latitude',
            'start_longitude', 'end_latitude', 'end_longitude', 'tour_type',
            'exhibition_location', 'curator', 'admission_price', 'festival_type',
            'multiple_locations', 'event_type', 'created_at', 'updated_at'
        ]
    
    @staticmethod
    def get_city_fields() -> List[str]:
        """Get all city fields from the City model"""
        # Define city fields without importing from app to avoid circular imports
        return ['id', 'name', 'state', 'country', 'timezone', 'created_at', 'updated_at']
    
    @staticmethod
    def generate_venue_discovery_prompt(city_name: str, country: str = None, event_type: str = 'tours', max_venues: int = 6) -> str:
        """Generate dynamic venue discovery prompt"""
        venue_fields = DynamicPromptGenerator.get_venue_fields()
        
        # Create field descriptions
        field_descriptions = []
        for field in venue_fields:
            # Skip system fields
            if field in ['id', 'city_id', 'created_at', 'updated_at']:
                continue
                
            if field == 'name':
                field_descriptions.append(f"- {field}: Full official name of the venue")
            elif field == 'venue_type':
                field_descriptions.append(f"- {field}: Type of venue (museum, gallery, cultural_center, etc.)")
            elif field == 'description':
                field_descriptions.append(f"- {field}: Brief description of the venue and its offerings")
            elif field == 'address':
                field_descriptions.append(f"- {field}: Complete street address")
            elif field == 'website_url':
                field_descriptions.append(f"- {field}: Official website URL")
            elif field == 'phone':
                field_descriptions.append(f"- {field}: Contact phone number")
            elif field == 'email':
                field_descriptions.append(f"- {field}: Contact email address")
            elif field == 'hours':
                field_descriptions.append(f"- {field}: Operating hours")
            elif field == 'price_range':
                field_descriptions.append(f"- {field}: Price range (e.g., '$10-25', 'Free', '$$')")
            elif field == 'rating':
                field_descriptions.append(f"- {field}: Average rating (1-5 stars)")
            elif field == 'amenities':
                field_descriptions.append(f"- {field}: List of amenities")
            elif field == 'accessibility':
                field_descriptions.append(f"- {field}: Accessibility information")
            elif field == 'parking':
                field_descriptions.append(f"- {field}: Parking availability")
            elif field == 'public_transport':
                field_descriptions.append(f"- {field}: Public transport access")
            elif field == 'special_features':
                field_descriptions.append(f"- {field}: Special features or highlights")
            elif field == 'capacity':
                field_descriptions.append(f"- {field}: Venue capacity")
            elif field == 'age_restrictions':
                field_descriptions.append(f"- {field}: Age restrictions")
            elif field == 'dress_code':
                field_descriptions.append(f"- {field}: Dress code requirements")
            elif field == 'booking_info':
                field_descriptions.append(f"- {field}: Booking information")
            elif field == 'cancellation_policy':
                field_descriptions.append(f"- {field}: Cancellation policy")
            else:
                field_descriptions.append(f"- {field}: {field.replace('_', ' ').title()}")
        
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
    def generate_venue_details_prompt(venue_name: str, city: str = None) -> str:
        """Generate dynamic venue details prompt"""
        venue_fields = DynamicPromptGenerator.get_venue_fields()
        
        # Create field descriptions
        field_descriptions = []
        for field in venue_fields:
            if field in ['id', 'created_at', 'updated_at']:
                continue  # Skip system fields
            
            if field == 'name':
                field_descriptions.append(f"- {field}: Full official name of the venue")
            elif field == 'venue_type':
                field_descriptions.append(f"- {field}: Type of venue")
            elif field == 'description':
                field_descriptions.append(f"- {field}: Detailed description")
            elif field == 'address':
                field_descriptions.append(f"- {field}: Full address")
            elif field == 'website_url':
                field_descriptions.append(f"- {field}: Official website URL")
            elif field == 'phone':
                field_descriptions.append(f"- {field}: Contact phone number")
            elif field == 'email':
                field_descriptions.append(f"- {field}: Contact email")
            elif field == 'hours':
                field_descriptions.append(f"- {field}: Operating hours")
            elif field == 'price_range':
                field_descriptions.append(f"- {field}: Price range")
            elif field == 'rating':
                field_descriptions.append(f"- {field}: Average rating (1-5 stars)")
            elif field == 'amenities':
                field_descriptions.append(f"- {field}: List of amenities")
            elif field == 'accessibility':
                field_descriptions.append(f"- {field}: Accessibility information")
            elif field == 'parking':
                field_descriptions.append(f"- {field}: Parking availability")
            elif field == 'public_transport':
                field_descriptions.append(f"- {field}: Public transport access")
            elif field == 'special_features':
                field_descriptions.append(f"- {field}: Special features")
            elif field == 'capacity':
                field_descriptions.append(f"- {field}: Venue capacity")
            elif field == 'age_restrictions':
                field_descriptions.append(f"- {field}: Age restrictions")
            elif field == 'dress_code':
                field_descriptions.append(f"- {field}: Dress code requirements")
            elif field == 'booking_info':
                field_descriptions.append(f"- {field}: Booking information")
            elif field == 'cancellation_policy':
                field_descriptions.append(f"- {field}: Cancellation policy")
            else:
                field_descriptions.append(f"- {field}: {field.replace('_', ' ').title()}")
        
        fields_text = '\n'.join(field_descriptions)
        
        return f"""Provide comprehensive details for the venue "{venue_name}" in {city or 'any city'}.

Include:
{fields_text}

Return as JSON object with these exact field names."""
    
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
