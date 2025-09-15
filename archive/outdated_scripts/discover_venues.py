#!/usr/bin/env python3
"""
LLM-powered tour venue discovery
Asks LLM specifically about cultural institutions that offer tours in a given city
"""

import sys
import os
import json
import requests
import logging
from typing import List, Dict, Optional
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue
from scripts.fetch_venue_details import LLMVenueDetailSearcher
from scripts.duplicate_prevention import DuplicatePrevention, DiscoveryStatusTracker
from scripts.utils import query_llm_for_venues, get_llm_status
from scripts.env_config import ensure_env_loaded, get_app_config

# Ensure environment is loaded
ensure_env_loaded()

# Setup logging for venue discovery
def setup_venue_logging():
    """Setup logging for venue discovery script"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, 'venue_discovery.log')),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('venue_discovery')

# Setup logging
venue_logger = setup_venue_logging()

# Get app configuration
app_config = get_app_config()
DEFAULT_MAX_VENUES = app_config['max_venues_per_city']

class LLMTourVenueDiscovery:
    """Uses LLM to discover venues that offer tours in specific cities"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Check LLM setup using utilities
        llm_status = get_llm_status()
        
        if llm_status['system_ready']:
            self.use_mock = False
            self.provider = llm_status['primary_provider']
            print(f"✅ Using {self.provider} LLM")
        else:
            print("⚠️  No LLM providers configured.")
            print("   Falling back to knowledge base for demonstration.")
            self.use_mock = True
    
    def _get_venue_fields_prompt(self) -> str:
        """Dynamically generate venue fields prompt from Venue model"""
        try:
            # Get all columns from Venue model
            venue_columns = Venue.__table__.columns.keys()
            
            # Filter out internal fields
            display_fields = [col for col in venue_columns if col not in ['id', 'created_at']]
            
            # Create field descriptions
            field_descriptions = []
            for field in display_fields:
                if field == 'name':
                    field_descriptions.append(f"- {field}: Full official name of the venue")
                elif field == 'venue_type':
                    field_descriptions.append(f"- {field}: Type of venue (museum, gallery, cultural_center, etc.)")
                elif field == 'description':
                    field_descriptions.append(f"- {field}: Detailed description of the venue and its offerings")
                elif field == 'address':
                    field_descriptions.append(f"- {field}: Complete street address")
                elif field == 'website_url':
                    field_descriptions.append(f"- {field}: Official website URL")
                elif field == 'latitude':
                    field_descriptions.append(f"- {field}: GPS latitude coordinate")
                elif field == 'longitude':
                    field_descriptions.append(f"- {field}: GPS longitude coordinate")
                elif field == 'image_url':
                    field_descriptions.append(f"- {field}: URL to venue's main image")
                elif field == 'instagram_url':
                    field_descriptions.append(f"- {field}: Instagram profile URL")
                elif field == 'facebook_url':
                    field_descriptions.append(f"- {field}: Facebook page URL")
                elif field == 'twitter_url':
                    field_descriptions.append(f"- {field}: Twitter profile URL")
                elif field == 'youtube_url':
                    field_descriptions.append(f"- {field}: YouTube channel URL")
                elif field == 'tiktok_url':
                    field_descriptions.append(f"- {field}: TikTok profile URL")
                elif field == 'opening_hours':
                    field_descriptions.append(f"- {field}: Regular opening hours (e.g., 'Mon-Fri 9AM-5PM')")
                elif field == 'holiday_hours':
                    field_descriptions.append(f"- {field}: Special holiday hours or closures")
                elif field == 'phone_number':
                    field_descriptions.append(f"- {field}: Contact phone number")
                elif field == 'email':
                    field_descriptions.append(f"- {field}: Contact email address")
                elif field == 'tour_info':
                    field_descriptions.append(f"- {field}: Detailed information about tours offered")
                elif field == 'admission_fee':
                    field_descriptions.append(f"- {field}: Admission fees and pricing information")
                elif field == 'city_id':
                    field_descriptions.append(f"- {field}: ID of the city (will be set automatically)")
                else:
                    field_descriptions.append(f"- {field}: {field.replace('_', ' ').title()}")
            
            return "\n".join(field_descriptions)
            
        except Exception as e:
            print(f"Warning: Could not generate dynamic fields prompt: {e}")
            return "- name: Full official name of the venue\n- venue_type: Type of venue\n- description: Detailed description\n- address: Complete street address\n- website_url: Official website URL\n- tour_info: Information about tours offered\n- admission_fee: Admission fees and pricing"
    
    def discover_tour_venues_for_city(self, city_name: str, country: str = None, event_type: str = 'tours') -> List[Dict]:
        """
        Ask LLM specifically about venues that offer tours in a city
        
        Args:
            city_name: Name of the city
            country: Country name (optional)
            event_type: Type of events to look for (tours, exhibitions, etc.)
        
        Returns:
            List of venue dictionaries with tour-specific information
        """
        venue_logger.info(f"Starting venue discovery for {city_name}, {country}, event_type: {event_type}")
        
        if self.use_mock:
            venue_logger.info(f"Using mock data for {city_name}")
            print(f"   Using knowledge base for {city_name}...")
            return self._get_mock_tour_venues(city_name, event_type)
        
        try:
            venue_logger.info(f"Querying LLM for {event_type} venues in {city_name}")
            print(f"   Querying LLM for {event_type} venues in {city_name}...")
            result = query_llm_for_venues(city_name, country, event_type, max_venues=DEFAULT_MAX_VENUES)
            
            venue_logger.debug(f"LLM query result: {result}")
            
            if result['success']:
                venues = self._parse_llm_response(result['response'])
                venue_logger.info(f"Successfully parsed {len(venues)} venues from LLM response")
                return venues
            else:
                venue_logger.warning(f"LLM query failed: {result['error']}")
                print(f"❌ LLM query failed: {result['error']}")
                print("   Falling back to knowledge base...")
                return self._get_mock_tour_venues(city_name, event_type)
                
        except Exception as e:
            venue_logger.error(f"Exception in venue discovery: {str(e)}", exc_info=True)
            print(f"❌ LLM query failed: {e}")
            print("   Falling back to knowledge base...")
            return self._get_mock_tour_venues(city_name, event_type)
    
    def _parse_llm_response(self, response) -> List[Dict]:
        """Parse LLM response and extract venue information"""
        try:
            # Handle empty response
            if not response:
                return []
            
            # If response is already a list or dict, handle it properly
            if isinstance(response, dict):
                # Check if response has a 'venues' key
                if 'venues' in response:
                    return response['venues']
                # Check for other common keys like 'museums', 'galleries', etc.
                elif any(key in response for key in ['museums', 'galleries', 'cultural_centers', 'venues']):
                    for key in ['museums', 'galleries', 'cultural_centers', 'venues']:
                        if key in response:
                            return response[key]
                # If it's a single venue dict, wrap it in a list
                elif 'name' in response:
                    return [response]
                else:
                    return []
            elif isinstance(response, list):
                return response
            
            # If response is a string, try to parse as JSON
            if isinstance(response, str):
                if not response.strip():
                    return []
                
                import json
                data = json.loads(response)
                
                # Ensure it's a list
                if isinstance(data, dict):
                    data = [data]
                elif not isinstance(data, list):
                    data = []
                
                return data
            
            return []
            
        except Exception as e:
            print(f"Warning: Could not parse LLM response: {e}")
            return []
    
    def _validate_venue_data(self, venue: Dict) -> bool:
        """Validate that venue data has required fields"""
        required_fields = ['name', 'venue_type', 'description']
        return all(field in venue and venue[field] for field in required_fields)
    
    def _get_mock_tour_venues(self, city_name: str, event_type: str) -> List[Dict]:
        """Fallback knowledge base for demonstration"""
        
        # Tour-specific knowledge base
        tour_venues = {
            'Washington': [
                {
                    'name': 'Smithsonian National Museum of Natural History',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of world-class natural history collections including dinosaur fossils, gems, and cultural artifacts.',
                    'address': '10th St. & Constitution Ave. NW, Washington, DC 20560',
                    'website_url': 'https://naturalhistory.si.edu',
                    'tour_info': 'Daily guided tours, self-guided audio tours, special behind-the-scenes tours',
                    'significance': 'Part of the Smithsonian Institution, offers comprehensive natural history tours'
                },
                {
                    'name': 'National Gallery of Art',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of masterpieces from the Renaissance to contemporary works.',
                    'address': 'Constitution Ave NW, Washington, DC 20565',
                    'website_url': 'https://www.nga.gov',
                    'tour_info': 'Daily docent-led tours, audio tours, special exhibition tours',
                    'significance': 'Premier art museum with expert-guided tours of world-class collections'
                },
                {
                    'name': 'Hirshhorn Museum and Sculpture Garden',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of modern and contemporary art with focus on sculpture.',
                    'address': 'Independence Ave SW, Washington, DC 20560',
                    'website_url': 'https://hirshhorn.si.edu',
                    'tour_info': 'Guided tours of permanent collection and special exhibitions',
                    'significance': 'Part of Smithsonian Institution, specialized in modern art tours'
                },
                {
                    'name': 'National Air and Space Museum',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of historic aircraft and spacecraft collections.',
                    'address': '600 Independence Ave SW, Washington, DC 20560',
                    'website_url': 'https://airandspace.si.edu',
                    'tour_info': 'Daily guided tours, special aviation history tours, IMAX theater experiences',
                    'significance': 'Most visited museum in the world, offers comprehensive aviation tours'
                },
                {
                    'name': 'Smithsonian American Art Museum',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of American art from colonial times to contemporary works.',
                    'address': '8th and F Streets NW, Washington, DC 20004',
                    'website_url': 'https://americanart.si.edu',
                    'tour_info': 'Daily guided tours, special exhibition tours, audio tours',
                    'significance': 'Premier collection of American art with comprehensive tour programs'
                },
                {
                    'name': 'National Museum of African American History and Culture',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours exploring African American history, culture, and contributions.',
                    'address': '1400 Constitution Ave NW, Washington, DC 20560',
                    'website_url': 'https://nmaahc.si.edu',
                    'tour_info': 'Daily guided tours, special themed tours, audio tours',
                    'significance': 'Important cultural institution with comprehensive historical tours'
                },
                {
                    'name': 'United States Holocaust Memorial Museum',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of Holocaust history and memorial exhibits.',
                    'address': '100 Raoul Wallenberg Pl SW, Washington, DC 20024',
                    'website_url': 'https://ushmm.org',
                    'tour_info': 'Guided tours, audio tours, special educational programs',
                    'significance': 'Important memorial museum with educational tour programs'
                },
                {
                    'name': 'National Museum of American History',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of American history through artifacts and exhibits.',
                    'address': '1300 Constitution Ave NW, Washington, DC 20560',
                    'website_url': 'https://americanhistory.si.edu',
                    'tour_info': 'Daily guided tours, special exhibition tours, audio tours',
                    'significance': 'Comprehensive American history museum with expert-guided tours'
                }
            ],
            'New York': [
                {
                    'name': 'Metropolitan Museum of Art',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of over 5,000 years of art from around the world.',
                    'address': '1000 5th Ave, New York, NY 10028',
                    'website_url': 'https://www.metmuseum.org',
                    'tour_info': 'Daily guided tours, audio tours, special exhibition tours, private group tours',
                    'significance': 'One of the largest art museums with comprehensive guided tour programs'
                },
                {
                    'name': 'Museum of Modern Art (MoMA)',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of modern and contemporary art collections.',
                    'address': '11 W 53rd St, New York, NY 10019',
                    'website_url': 'https://www.moma.org',
                    'tour_info': 'Daily guided tours, audio tours, special exhibition tours',
                    'significance': 'Premier modern art museum with expert-guided tours'
                },
                {
                    'name': 'Guggenheim Museum',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of modern art in Frank Lloyd Wright\'s iconic spiral building.',
                    'address': '1071 5th Ave, New York, NY 10128',
                    'website_url': 'https://www.guggenheim.org',
                    'tour_info': 'Guided tours of permanent collection and special exhibitions',
                    'significance': 'Famous architecture and modern art tours'
                }
            ],
            'London': [
                {
                    'name': 'British Museum',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of human history, art and culture collections.',
                    'address': 'Great Russell St, London WC1B 3DG, UK',
                    'website_url': 'https://www.britishmuseum.org',
                    'tour_info': 'Daily guided tours, audio tours, special exhibition tours',
                    'significance': 'One of the world\'s largest museums with comprehensive tour programs'
                },
                {
                    'name': 'National Gallery',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of Western European paintings.',
                    'address': 'Trafalgar Square, London WC2N 5DN, UK',
                    'website_url': 'https://nationalgallery.org.uk',
                    'tour_info': 'Daily guided tours, audio tours, special exhibition tours',
                    'significance': 'Premier art museum with expert-guided tours'
                },
                {
                    'name': 'Tate Modern',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of modern and contemporary art.',
                    'address': 'Bankside, London SE1 9TG, UK',
                    'website_url': 'https://tate.org.uk',
                    'tour_info': 'Daily guided tours, audio tours, special exhibition tours',
                    'significance': 'World\'s most visited modern art gallery with comprehensive tours'
                },
                {
                    'name': 'Victoria and Albert Museum',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of decorative arts and design collections.',
                    'address': 'Cromwell Rd, London SW7 2RL, UK',
                    'website_url': 'https://vam.ac.uk',
                    'tour_info': 'Daily guided tours, themed tours, special exhibition tours',
                    'significance': 'World\'s leading museum of art and design with expert tours'
                },
                {
                    'name': 'Natural History Museum',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of natural history collections and exhibitions.',
                    'address': 'Cromwell Rd, London SW7 5BD, UK',
                    'website_url': 'https://nhm.ac.uk',
                    'tour_info': 'Daily guided tours, dinosaur tours, special exhibition tours',
                    'significance': 'Famous for dinosaur exhibits and comprehensive natural history tours'
                },
                {
                    'name': 'Science Museum',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of science and technology collections.',
                    'address': 'Exhibition Rd, London SW7 2DD, UK',
                    'website_url': 'https://sciencemuseum.org.uk',
                    'tour_info': 'Daily guided tours, interactive tours, special exhibition tours',
                    'significance': 'Interactive science museum with engaging tour programs'
                },
                {
                    'name': 'Tate Britain',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of British art from 1500 to present.',
                    'address': 'Millbank, London SW1P 4RG, UK',
                    'website_url': 'https://tate.org.uk/visit/tate-britain',
                    'tour_info': 'Daily guided tours, British art tours, special exhibition tours',
                    'significance': 'Premier collection of British art with expert-guided tours'
                },
                {
                    'name': 'Imperial War Museum',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of military history and war collections.',
                    'address': 'Lambeth Rd, London SE1 6HZ, UK',
                    'website_url': 'https://iwm.org.uk',
                    'tour_info': 'Daily guided tours, war history tours, special exhibition tours',
                    'significance': 'Comprehensive military history museum with educational tours'
                },
                {
                    'name': 'Museum of London',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of London\'s history and culture.',
                    'address': '150 London Wall, London EC2Y 5HN, UK',
                    'website_url': 'https://museumoflondon.org.uk',
                    'tour_info': 'Daily guided tours, London history tours, special exhibition tours',
                    'significance': 'Dedicated to London\'s rich history with comprehensive tours'
                },
                {
                    'name': 'Royal Academy of Arts',
                    'venue_type': 'museum',
                    'description': 'Offers guided tours of contemporary art exhibitions and collections.',
                    'address': 'Burlington House, Piccadilly, London W1J 0BD, UK',
                    'website_url': 'https://royalacademy.org.uk',
                    'tour_info': 'Daily guided tours, contemporary art tours, special exhibition tours',
                    'significance': 'Leading contemporary art institution with expert tours'
                },
                {
                    'name': 'Design Museum',
                    'venue_type': 'museum',
                    'description': 'Provides guided tours of design collections and exhibitions.',
                    'address': '224-238 Kensington High St, London W8 6AG, UK',
                    'website_url': 'https://designmuseum.org',
                    'tour_info': 'Daily guided tours, design tours, special exhibition tours',
                    'significance': 'Premier design museum with comprehensive tour programs'
                },
                {
                    'name': 'Serpentine Galleries',
                    'venue_type': 'gallery',
                    'description': 'Offers guided tours of contemporary art exhibitions.',
                    'address': 'Kensington Gardens, London W2 3XA, UK',
                    'website_url': 'https://serpentinegalleries.org',
                    'tour_info': 'Daily guided tours, contemporary art tours, special exhibition tours',
                    'significance': 'Leading contemporary art galleries with expert tours'
                }
            ],
            'Los Angeles': [
                {
                    'name': 'The Getty Center',
                    'venue_type': 'museum',
                    'description': 'World-class art museum offering guided tours of European paintings, sculptures, and decorative arts.',
                    'address': '1200 Getty Center Dr, Los Angeles, CA 90049',
                    'website_url': 'https://getty.edu',
                    'tour_info': 'Daily guided tours, architecture tours, garden tours, special exhibition tours',
                    'significance': 'Premier art museum with comprehensive tour programs and stunning architecture'
                },
                {
                    'name': 'Los Angeles County Museum of Art (LACMA)',
                    'venue_type': 'museum',
                    'description': 'Largest art museum in the western United States with diverse collections and guided tours.',
                    'address': '5905 Wilshire Blvd, Los Angeles, CA 90036',
                    'website_url': 'https://lacma.org',
                    'tour_info': 'Daily guided tours, audio tours, special exhibition tours, family tours',
                    'significance': 'Major cultural institution with extensive tour programs'
                },
                {
                    'name': 'The Broad',
                    'venue_type': 'museum',
                    'description': 'Contemporary art museum featuring guided tours of modern and contemporary works.',
                    'address': '221 S Grand Ave, Los Angeles, CA 90012',
                    'website_url': 'https://thebroad.org',
                    'tour_info': 'Guided tours, audio tours, special exhibition tours',
                    'significance': 'Leading contemporary art museum with expert-guided tours'
                },
                {
                    'name': 'Griffith Observatory',
                    'venue_type': 'observatory',
                    'description': 'Public observatory offering guided tours of astronomy exhibits and telescope viewing.',
                    'address': '2800 E Observatory Rd, Los Angeles, CA 90027',
                    'website_url': 'https://griffithobservatory.org',
                    'tour_info': 'Guided tours, planetarium shows, telescope viewing sessions',
                    'significance': 'Iconic LA landmark with educational astronomy tours'
                },
                {
                    'name': 'Huntington Library, Art Museum, and Botanical Gardens',
                    'venue_type': 'museum',
                    'description': 'Comprehensive cultural institution offering guided tours of art, rare books, and gardens.',
                    'address': '1151 Oxford Rd, San Marino, CA 91108',
                    'website_url': 'https://huntington.org',
                    'tour_info': 'Guided tours of art collections, library tours, garden tours',
                    'significance': 'World-renowned cultural institution with diverse tour programs'
                }
            ],
            'Tokyo': [
                {
                    'name': 'Tokyo National Museum',
                    'venue_type': 'museum',
                    'description': 'Japan\'s oldest and largest museum offering guided tours of Japanese art and cultural artifacts.',
                    'address': '13-9 Ueno Park, Taito City, Tokyo 110-8712, Japan',
                    'website_url': 'https://tnm.jp',
                    'tour_info': 'Guided tours, audio tours, special exhibition tours, English tours',
                    'significance': 'Premier Japanese art museum with comprehensive tour programs'
                },
                {
                    'name': 'National Museum of Modern Art, Tokyo',
                    'venue_type': 'museum',
                    'description': 'Leading museum of modern and contemporary art with guided tours of Japanese and international works.',
                    'address': '3-1 Kitanomaru Koen, Chiyoda City, Tokyo 102-8322, Japan',
                    'website_url': 'https://momat.go.jp',
                    'tour_info': 'Guided tours, audio tours, special exhibition tours',
                    'significance': 'Major modern art museum with expert-guided tours'
                },
                {
                    'name': 'Edo-Tokyo Museum',
                    'venue_type': 'museum',
                    'description': 'Comprehensive museum offering guided tours of Tokyo\'s history from Edo period to present.',
                    'address': '1-4-1 Yokoami, Sumida City, Tokyo 130-0015, Japan',
                    'website_url': 'https://edotokyo-museum.or.jp',
                    'tour_info': 'Guided tours, audio tours, special exhibition tours, English tours',
                    'significance': 'Essential Tokyo history museum with comprehensive tour programs'
                },
                {
                    'name': 'Senso-ji Temple',
                    'venue_type': 'temple',
                    'description': 'Tokyo\'s oldest temple offering guided tours of Buddhist architecture and cultural significance.',
                    'address': '2-3-1 Asakusa, Taito City, Tokyo 111-0032, Japan',
                    'website_url': 'https://senso-ji.jp',
                    'tour_info': 'Guided temple tours, cultural tours, traditional craft demonstrations',
                    'significance': 'Iconic Tokyo landmark with cultural and spiritual tour programs'
                },
                {
                    'name': 'Tokyo Skytree',
                    'venue_type': 'observation_tower',
                    'description': 'Tallest structure in Japan offering guided tours and observation deck experiences.',
                    'address': '1-1-2 Oshiage, Sumida City, Tokyo 131-0045, Japan',
                    'website_url': 'https://tokyoskytree.jp',
                    'tour_info': 'Guided tours, observation deck tours, special event tours',
                    'significance': 'Modern Tokyo landmark with comprehensive tour experiences'
                }
            ]
        }
        
        # Return tour-specific venues or generic ones
        return tour_venues.get(city_name, [
            {
                'name': f'{city_name} Art Museum',
                'venue_type': 'museum',
                'description': f'Major art museum in {city_name} offering guided tours of local and international collections.',
                'address': f'{city_name}',
                'website_url': f'https://{city_name.lower().replace(" ", "")}artmuseum.org',
                'tour_info': f'Guided tours available daily',
                'significance': f'Important cultural institution in {city_name} with tour programs'
            }
        ])

def discover_tour_venues_for_city(city_name: str, country: str = None, event_type: str = 'tours', max_venues: int = DEFAULT_MAX_VENUES, output_json: bool = False):
    """
    Discover venues that offer specific types of events (tours, exhibitions, etc.) for a city
    
    Args:
        city_name: Name of the city
        country: Country name (optional)
        event_type: Type of events to look for (tours, exhibitions, festivals, etc.)
        max_venues: Maximum number of venues to add
        output_json: If True, return JSON data instead of adding to database
    """
    import sys
    from io import StringIO
    
    # Suppress print statements when output_json=True
    if output_json:
        old_stdout = sys.stdout
        sys.stdout = StringIO()
    
    discovery = LLMTourVenueDiscovery()
    
    with app.app_context():
        # Find the city
        city = City.query.filter_by(name=city_name).first()
        if not city:
            print(f"❌ City '{city_name}' not found in database")
            return
        
        print(f"\n🔍 Discovering venues that offer {event_type} in {city_name}...")
        
        # Discover venues using LLM
        venues_data = discovery.discover_tour_venues_for_city(city_name, country, event_type)
        
        # Initialize LLM detail searcher
        detail_searcher = LLMVenueDetailSearcher()
        
        if not venues_data:
            print(f"❌ No venues discovered for {event_type} in {city_name}")
            return
        
        print(f"✅ Discovered {len(venues_data)} venues that offer {event_type}:")
        
        added_count = 0
        for venue_data in venues_data[:max_venues]:
            # Check if venue already exists using duplicate prevention
            existing_venue = DuplicatePrevention.check_venue_exists(venue_data['name'], city.id)
            if existing_venue:
                print(f"   ⚠️  Venue already exists: {venue_data['name']}")
                continue
            
            # Search for comprehensive venue details using LLM
            print(f"   🔍 Searching LLM for comprehensive details about {venue_data['name']}...")
            details = detail_searcher.search_venue_details(
                venue_data['name'], 
                city_name, 
                venue_data.get('address', '')
            )
            
            # Create new venue with comprehensive details from LLM search
            venue = Venue(
                name=venue_data['name'],
                venue_type=venue_data['venue_type'],
                description=details.get('description', venue_data['description']),
                address=details.get('address', ''),
                website_url=details.get('website_url', ''),
                latitude=details.get('latitude'),
                longitude=details.get('longitude'),
                image_url=details.get('image_url', ''),
                instagram_url=details.get('instagram_url', ''),
                facebook_url=details.get('facebook_url', ''),
                twitter_url=details.get('twitter_url', ''),
                youtube_url=details.get('youtube_url', ''),
                tiktok_url=details.get('tiktok_url', ''),
                opening_hours=details.get('opening_hours', ''),
                holiday_hours=details.get('holiday_hours', ''),
                phone_number=details.get('phone_number', ''),
                email=details.get('email', ''),
                tour_info=details.get('tour_info', ''),
                admission_fee=details.get('admission_fee', ''),
                city_id=city.id,
                updated_at=details.get('updated_at', None)
            )
            
            # Add venue to session and commit
            db.session.add(venue)
            db.session.commit()
            
            added_count += 1
            print(f"   ✅ Added: {venue_data['name']}")
            if 'tour_info' in venue_data:
                print(f"      Tour Info: {venue_data['tour_info']}")
        
        if output_json:
            # Restore stdout
            sys.stdout = old_stdout
            # Return JSON data for API consumption
            return {
                'success': True,
                'venues': venues_data[:max_venues],
                'message': f'Discovered {len(venues_data)} venues for {city_name}',
                'added_count': added_count
            }
        
        if added_count > 0:
            db.session.commit()
            print(f"\n🎉 Successfully added {added_count} new {event_type} venues to {city_name}")
        else:
            print(f"\nℹ️  No new venues added to {city_name}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Discover venues that offer specific events using LLM')
    parser.add_argument('--city', required=True, help='City name to discover venues for')
    parser.add_argument('--country', help='Country name (optional)')
    parser.add_argument('--event-type', default='tours', choices=['tours', 'exhibitions', 'festivals', 'photowalks'], 
                       help='Type of events to look for')
    parser.add_argument('--max-venues', type=int, default=15, help='Maximum venues to add per city')
    parser.add_argument('--output-json', action='store_true', help='Output JSON data instead of adding to database')
    
    args = parser.parse_args()
    
    result = discover_tour_venues_for_city(args.city, args.country, args.event_type, args.max_venues, args.output_json)
    
    if args.output_json and result:
        print(json.dumps(result, indent=2))
