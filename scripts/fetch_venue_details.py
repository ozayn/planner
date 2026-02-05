#!/usr/bin/env python3
"""
LLM-based venue detail searcher
Uses LLM to find comprehensive venue information instead of web scraping
"""

import requests
import json
import os
import sys
from typing import Optional, Dict, List
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.duplicate_prevention import DuplicatePrevention
from scripts.utils import query_llm_for_venue_details, get_llm_status

class LLMVenueDetailSearcher:
    """Uses LLM to search for comprehensive venue details"""
    
    def __init__(self, api_key: Optional[str] = None, silent: bool = False):
        # Check LLM setup using utilities
        llm_status = get_llm_status()
        
        if llm_status['system_ready']:
            self.use_mock = False
            self.provider = llm_status['primary_provider']
            if not silent:
                print(f"✅ Using {self.provider} LLM for venue details")
        else:
            if not silent:
                print("⚠️  No LLM providers configured.")
                print("   Falling back to mock data for demonstration.")
            self.use_mock = True
            self.provider = None
    
    def search_venue_details(self, venue_name: str, city: str = None, address: str = None, silent: bool = False) -> Dict[str, str]:
        """
        Search for comprehensive venue details using LLM
        
        Args:
            venue_name: Name of the venue
            city: City name (optional)
            address: Full address (optional)
            
        Returns:
            Dictionary with venue details
        """
        if self.use_mock:
            if not silent:
                print(f"   Using mock data for {venue_name}...")
            return self._get_fallback_details(venue_name, city)
        
        if not silent:
            print(f"🔍 Searching LLM for details about {venue_name}...")
        
        try:
            # Extract country from city if it contains country info
            country = None
            if city and ',' in city:
                parts = city.split(',')
                if len(parts) > 1:
                    country = parts[-1].strip()
                    city = parts[0].strip()
            
            result = query_llm_for_venue_details(venue_name, city, country)
            
            if result['success']:
                return self._parse_llm_response(result['response'])
            else:
                if not silent:
                    print(f"❌ LLM search failed: {result['error']}")
                return self._get_fallback_details(venue_name, city)
                
        except Exception as e:
            if not silent:
                print(f"❌ LLM search failed: {e}")
            return self._get_fallback_details(venue_name, city)
    
    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        """Parse LLM response and extract venue details"""
        try:
            # Handle empty response
            if not response or not response.strip():
                return {}
            
            # Clean up the response content
            content = response.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json
            elif content.startswith('```'):
                content = content[3:]   # Remove ```
            
            if content.endswith('```'):
                content = content[:-3]  # Remove trailing ```
            
            # Try to find JSON object in the content
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx + 1]
            else:
                json_content = content
            
            # Try to parse as JSON
            if isinstance(json_content, str):
                import json
                data = json.loads(json_content.strip())
            else:
                data = json_content
            
            # Convert to the expected format
            result = {}
            for key, value in data.items():
                if value is not None:
                    result[key] = str(value)
                else:
                    result[key] = ""
            
            return result
            
        except Exception as e:
            print(f"Warning: Could not parse LLM response: {e}")
            return {}
    
    def _query_groq_api(self, prompt: str, silent: bool = False) -> Dict[str, str]:
        """Query Groq API for venue details"""
        url = 'https://api.groq.com/openai/v1/chat/completions'
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful cultural venue expert. Always respond with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
            'max_tokens': 2000
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse JSON response
            try:
                # Clean up the response content
                content = content.strip()
                
                # Remove markdown code blocks if present
                if content.startswith('```json'):
                    content = content[7:]  # Remove ```json
                elif content.startswith('```'):
                    content = content[3:]   # Remove ```
                
                if content.endswith('```'):
                    content = content[:-3]  # Remove trailing ```
                
                # Try to find JSON object in the content
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx + 1]
                else:
                    json_content = content
                
                # Parse the JSON
                details = json.loads(json_content.strip())
                
                # Validate that we got meaningful data
                if not details.get('name'):
                    if not silent:
                        print(f"❌ No venue name found in response")
                    return self._get_fallback_details(venue_name, city)
                
                if not silent:
                    print(f"✅ Found comprehensive details via Groq")
                return details
                
            except json.JSONDecodeError as e:
                if not silent:
                    print(f"❌ Failed to parse Groq response as JSON: {e}")
                    print(f"Raw response: {content[:200]}...")
                return self._get_fallback_details("", "")
            
        except Exception as e:
            if not silent:
                print(f"❌ Groq API request failed: {e}")
            raise
    
    def _query_openai_api(self, prompt: str, silent: bool = False) -> Dict[str, str]:
        """Query OpenAI API for venue details"""
        url = 'https://api.openai.com/v1/chat/completions'
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful cultural venue expert. Always respond with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
            'max_tokens': 2000
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse JSON response
            try:
                details = json.loads(content.strip())
                if not silent:
                    print(f"✅ Found comprehensive details via OpenAI")
                return details
                
            except json.JSONDecodeError as e:
                if not silent:
                    print(f"❌ Failed to parse OpenAI response as JSON: {e}")
                return self._get_fallback_details("", "")
            
        except Exception as e:
            if not silent:
                print(f"❌ OpenAI API request failed: {e}")
            raise
    
    def _get_fallback_details(self, venue_name: str, city: str) -> Dict[str, str]:
        """Fallback details when LLM is not available"""
        print(f"⚠️  Using fallback details for {venue_name}")
        
        # Use placeholder image URL
        image_url = f"https://placehold.co/400x300/cccccc/666666?text={quote_plus(venue_name)}"
        
        return {
            'image_url': image_url or '',
            'website_url': '',
            'address': '',
            'latitude': None,
            'longitude': None,
            'instagram_url': '',
            'facebook_url': '',
            'twitter_url': '',
            'youtube_url': '',
            'tiktok_url': '',
            'opening_hours': '',
            'holiday_hours': '',
            'phone_number': '',
            'email': '',
            'description': f'Cultural venue in {city}' if city else 'Cultural venue'
        }
    
    def search_multiple_venues(self, venues: List[Dict]) -> Dict[str, Dict[str, str]]:
        """
        Search details for multiple venues
        
        Args:
            venues: List of venue dictionaries with 'name', 'city', 'address' keys
            
        Returns:
            Dictionary mapping venue names to their details
        """
        results = {}
        
        for venue in venues:
            venue_name = venue.get('name', '')
            city = venue.get('city', '')
            address = venue.get('address', '')
            
            if venue_name:
                details = self.search_venue_details(venue_name, city, address)
                results[venue_name] = details
        
        return results

def test_llm_searcher():
    """Test the LLM venue detail searcher"""
    searcher = LLMVenueDetailSearcher()
    
    test_venues = [
        {'name': 'British Museum', 'city': 'London', 'address': 'Great Russell St, London WC1B 3DG'},
        {'name': 'National Gallery', 'city': 'London', 'address': 'Trafalgar Square, London WC2N 5DN'},
        {'name': 'Tate Modern', 'city': 'London', 'address': 'Bankside, London SE1 9TG'}
    ]
    
    print("🧪 Testing LLM venue detail searcher...")
    results = searcher.search_multiple_venues(test_venues)
    
    print(f"\n📊 Results:")
    for venue_name, details in results.items():
        print(f"\n🏛️  {venue_name}:")
        for key, value in details.items():
            if value:
                print(f"   {key}: {value}")
    
    return results

if __name__ == '__main__':
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Fetch comprehensive details for a venue using LLM')
    parser.add_argument('--venue-id', type=int, help='Venue ID to fetch details for')
    parser.add_argument('--venue-name', help='Venue name to fetch details for')
    parser.add_argument('--city', help='City name (required if using venue-name)')
    
    args = parser.parse_args()
    
    if args.venue_id:
        # Fetch details for specific venue by ID
        from app import app, db, Venue
        
        with app.app_context():
            venue = Venue.query.get(args.venue_id)
            if not venue:
                print(f"❌ Venue with ID {args.venue_id} not found")
                sys.exit(1)
            
            print(f"🔍 Fetching details for venue: {venue.name}")
            searcher = LLMVenueDetailSearcher()
            details = searcher.search_venue_details(venue.name, venue.city.name if venue.city else '')
            
            if details:
                # Update venue with fetched details
                venue.image_url = details.get('image_url', venue.image_url)
                venue.instagram_url = details.get('instagram_url', venue.instagram_url)
                venue.facebook_url = details.get('facebook_url', venue.facebook_url)
                venue.twitter_url = details.get('twitter_url', venue.twitter_url)
                venue.youtube_url = details.get('youtube_url', venue.youtube_url)
                venue.tiktok_url = details.get('tiktok_url', venue.tiktok_url)
                venue.phone_number = details.get('phone_number', venue.phone_number)
                venue.email = details.get('email', venue.email)
                venue.opening_hours = details.get('opening_hours', venue.opening_hours)
                venue.holiday_hours = details.get('holiday_hours', venue.holiday_hours)
                venue.address = details.get('address', venue.address)
                venue.website_url = details.get('website_url', venue.website_url)
                venue.latitude = details.get('latitude', venue.latitude)
                venue.longitude = details.get('longitude', venue.longitude)
                
                db.session.commit()
                print(f"✅ Successfully updated venue details for {venue.name}")
            else:
                print(f"⚠️ No details found for {venue.name}")
    
    elif args.venue_name and args.city:
        # Test mode with venue name and city
        print(f"🔍 Testing venue detail search for: {args.venue_name} in {args.city}")
        searcher = LLMVenueDetailSearcher()
        details = searcher.search_venue_details(args.venue_name, args.city)
        
        if details:
            print("✅ Found details:")
            for key, value in details.items():
                if value:
                    print(f"   {key}: {value}")
        else:
            print("❌ No details found")
    
    else:
        # Run test function
        test_llm_searcher()

