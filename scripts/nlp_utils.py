"""
NLP Utilities for Intelligent Text Normalization
Provides reusable NLP functions for city names, country names, venue names, etc.
"""

import re
from typing import Optional, List, Dict, Tuple

def normalize_text_with_nlp(text: str, text_type: str = 'general') -> str:
    """
    Use NLP to intelligently normalize text based on type
    
    Args:
        text: Input text to normalize
        text_type: Type of text ('country', 'city', 'venue', 'general')
    
    Returns:
        Normalized text
    """
    if not text:
        return text
    
    # Clean and normalize the input
    text = text.strip()
    if not text:
        return text
    
    try:
        # Basic normalization - just clean up capitalization
        # The specific normalization functions are defined later in this file
        return text.title()
            
    except Exception as e:
        print(f"⚠️ NLP normalization failed for '{text}': {e}")
        return text.title()

def validate_city_country_relationship(city: str, country: str) -> Optional[str]:
    """
    Validate that a city-country combination makes sense
    Returns the correct country if the combination is invalid
    """
    try:
        # Major city-country mappings
        city_country_map = {
            # German cities
            'berlin': 'Germany',
            'munich': 'Germany', 
            'hamburg': 'Germany',
            'cologne': 'Germany',
            'frankfurt': 'Germany',
            'stuttgart': 'Germany',
            'düsseldorf': 'Germany',
            'dortmund': 'Germany',
            'essen': 'Germany',
            'leipzig': 'Germany',
            'bremen': 'Germany',
            'dresden': 'Germany',
            'hannover': 'Germany',
            'nuremberg': 'Germany',
            
            # French cities
            'paris': 'France',
            'lyon': 'France',
            'marseille': 'France',
            'toulouse': 'France',
            'nice': 'France',
            'nantes': 'France',
            'strasbourg': 'France',
            'montpellier': 'France',
            'bordeaux': 'France',
            'lille': 'France',
            
            # UK cities
            'london': 'United Kingdom',
            'manchester': 'United Kingdom',
            'birmingham': 'United Kingdom',
            'liverpool': 'United Kingdom',
            'leeds': 'United Kingdom',
            'sheffield': 'United Kingdom',
            'bristol': 'United Kingdom',
            'newcastle': 'United Kingdom',
            'nottingham': 'United Kingdom',
            'leicester': 'United Kingdom',
            
            # Italian cities
            'rome': 'Italy',
            'milan': 'Italy',
            'naples': 'Italy',
            'turin': 'Italy',
            'palermo': 'Italy',
            'genoa': 'Italy',
            'bologna': 'Italy',
            'florence': 'Italy',
            'venice': 'Italy',
            
            # Spanish cities
            'madrid': 'Spain',
            'barcelona': 'Spain',
            'valencia': 'Spain',
            'seville': 'Spain',
            'zaragoza': 'Spain',
            'málaga': 'Spain',
            'murcia': 'Spain',
            'palma': 'Spain',
            'las palmas': 'Spain',
            'bilbao': 'Spain',
            
            # Japanese cities
            'tokyo': 'Japan',
            'osaka': 'Japan',
            'nagoya': 'Japan',
            'sapporo': 'Japan',
            'fukuoka': 'Japan',
            'kobe': 'Japan',
            'kyoto': 'Japan',
            'yokohama': 'Japan',
            'kawasaki': 'Japan',
            'saitama': 'Japan',
            
            # Chinese cities
            'beijing': 'China',
            'shanghai': 'China',
            'guangzhou': 'China',
            'shenzhen': 'China',
            'tianjin': 'China',
            'wuhan': 'China',
            'chengdu': 'China',
            'nanjing': 'China',
            'hangzhou': 'China',
            'xian': 'China',
            
            # Canadian cities
            'toronto': 'Canada',
            'montreal': 'Canada',
            'vancouver': 'Canada',
            'calgary': 'Canada',
            'edmonton': 'Canada',
            'ottawa': 'Canada',
            'winnipeg': 'Canada',
            'quebec city': 'Canada',
            'halifax': 'Canada',
            'victoria': 'Canada',
            
            # Australian cities
            'sydney': 'Australia',
            'melbourne': 'Australia',
            'brisbane': 'Australia',
            'perth': 'Australia',
            'adelaide': 'Australia',
            'canberra': 'Australia',
            'hobart': 'Australia',
            'darwin': 'Australia',
            
            # Iranian cities
            'tehran': 'Iran',
            'mashhad': 'Iran',
            'isfahan': 'Iran',
            'shiraz': 'Iran',
            'tabriz': 'Iran',
            'karaj': 'Iran',
            'ahvaz': 'Iran',
            'qom': 'Iran',
            'kermanshah': 'Iran',
            'urmia': 'Iran',
            
            # US cities (major ones)
            'new york': 'United States',
            'los angeles': 'United States',
            'chicago': 'United States',
            'houston': 'United States',
            'phoenix': 'United States',
            'philadelphia': 'United States',
            'san antonio': 'United States',
            'san diego': 'United States',
            'dallas': 'United States',
            'san jose': 'United States',
            'austin': 'United States',
            'jacksonville': 'United States',
            'fort worth': 'United States',
            'columbus': 'United States',
            'charlotte': 'United States',
            'san francisco': 'United States',
            'indianapolis': 'United States',
            'seattle': 'United States',
            'denver': 'United States',
            'washington': 'United States',
            'boston': 'United States',
            'el paso': 'United States',
            'nashville': 'United States',
            'detroit': 'United States',
            'oklahoma city': 'United States',
            'portland': 'United States',
            'las vegas': 'United States',
            'memphis': 'United States',
            'louisville': 'United States',
            'baltimore': 'United States',
            'milwaukee': 'United States',
            'albuquerque': 'United States',
            'tucson': 'United States',
            'fresno': 'United States',
            'sacramento': 'United States',
            'mesa': 'United States',
            'kansas city': 'United States',
            'atlanta': 'United States',
            'long beach': 'United States',
            'colorado springs': 'United States',
            'raleigh': 'United States',
            'miami': 'United States',
            'virginia beach': 'United States',
            'omaha': 'United States',
            'oakland': 'United States',
            'minneapolis': 'United States',
            'tulsa': 'United States',
            'arlington': 'United States',
            'tampa': 'United States',
            'new orleans': 'United States',
            'wichita': 'United States',
            'cleveland': 'United States',
            'bakersfield': 'United States',
            'aurora': 'United States',
            'anaheim': 'United States',
            'honolulu': 'United States',
            'santa ana': 'United States',
            'corpus christi': 'United States',
            'riverside': 'United States',
            'lexington': 'United States',
            'stockton': 'United States',
            'henderson': 'United States',
            'saint paul': 'United States',
            'st. louis': 'United States'
        }
        
        # Normalize city name for lookup
        normalized_city = city.lower().strip()
        
        # Check if we have a mapping for this city
        if normalized_city in city_country_map:
            correct_country = city_country_map[normalized_city]
            
            # Check if the provided country matches (simple comparison for now)
            normalized_provided = country.lower().strip()
            normalized_correct = correct_country.lower().strip()
            
            if normalized_provided != normalized_correct:
                print(f"🚨 City-country mismatch detected: '{city}' should be in '{correct_country}', not '{country}'")
                return correct_country
        
        # If no mapping found or country matches, return None (no correction needed)
        return None
        
    except Exception as e:
        print(f"⚠️ Error validating city-country relationship: {e}")
        return None

def normalize_country_with_nlp(country: str, city_context: str = None) -> str:
    """Use NLP to intelligently normalize country names with optional city context"""
    try:
        from fuzzywuzzy import fuzz, process
        import re
        
        # Clean and normalize the input
        cleaned_country = re.sub(r'[^\w\s]', '', country.lower().strip())
        
        # If we have city context, validate the city-country relationship first
        if city_context:
            validated_country = validate_city_country_relationship(city_context, country)
            if validated_country:
                print(f"🌍 City-country validation: '{city_context}' should be in '{validated_country}'")
                return validated_country
        
        # Comprehensive list of canonical country names
        canonical_countries = [
            'United States', 'United Kingdom', 'Canada', 'Australia', 'Germany', 'France',
            'Italy', 'Spain', 'Japan', 'China', 'India', 'Brazil', 'Mexico', 'Argentina',
            'Russia', 'Turkey', 'Egypt', 'Nigeria', 'Kenya', 'Morocco', 'Tunisia',
            'Iran', 'Iraq', 'Saudi Arabia', 'Israel', 'Palestine', 'Lebanon', 'Jordan',
            'Syria', 'Thailand', 'Vietnam', 'Indonesia', 'Malaysia', 'Singapore',
            'Philippines', 'Taiwan', 'South Korea', 'North Korea', 'New Zealand',
            'Czech Republic', 'Dominican Republic', 'Central African Republic',
            'Democratic Republic of the Congo', 'Republic of the Congo', 'Hong Kong',
            'Macau', 'United Arab Emirates', 'South Africa', 'Netherlands', 'Belgium',
            'Switzerland', 'Austria', 'Sweden', 'Norway', 'Denmark', 'Finland',
            'Poland', 'Portugal', 'Greece', 'Ireland', 'Iceland', 'Luxembourg',
            'Estonia', 'Latvia', 'Lithuania', 'Slovenia', 'Slovakia', 'Hungary',
            'Romania', 'Bulgaria', 'Croatia', 'Serbia', 'Bosnia and Herzegovina',
            'Montenegro', 'Albania', 'Macedonia', 'Moldova', 'Ukraine', 'Belarus',
            'Georgia', 'Armenia', 'Azerbaijan', 'Kazakhstan', 'Uzbekistan', 'Kyrgyzstan',
            'Tajikistan', 'Turkmenistan', 'Afghanistan', 'Pakistan', 'Bangladesh',
            'Sri Lanka', 'Nepal', 'Bhutan', 'Myanmar', 'Laos', 'Cambodia', 'Mongolia',
            'Chile', 'Peru', 'Colombia', 'Venezuela', 'Ecuador', 'Bolivia', 'Paraguay',
            'Uruguay', 'Guyana', 'Suriname', 'French Guiana', 'Cuba', 'Jamaica',
            'Haiti', 'Dominican Republic', 'Puerto Rico', 'Trinidad and Tobago',
            'Barbados', 'Saint Lucia', 'Saint Vincent and the Grenadines',
            'Grenada', 'Antigua and Barbuda', 'Saint Kitts and Nevis', 'Belize',
            'Costa Rica', 'Panama', 'Guatemala', 'Honduras', 'El Salvador',
            'Nicaragua', 'Ethiopia', 'South Sudan', 'Sudan', 'Libya', 'Algeria',
            'Mali', 'Burkina Faso', 'Niger', 'Chad', 'Cameroon', 'Central African Republic',
            'Democratic Republic of the Congo', 'Republic of the Congo', 'Gabon',
            'Equatorial Guinea', 'São Tomé and Príncipe', 'Angola', 'Zambia',
            'Zimbabwe', 'Botswana', 'Namibia', 'South Africa', 'Lesotho', 'Swaziland',
            'Mozambique', 'Madagascar', 'Mauritius', 'Seychelles', 'Comoros',
            'Djibouti', 'Somalia', 'Eritrea', 'Uganda', 'Rwanda', 'Burundi',
            'Tanzania', 'Malawi', 'Ghana', 'Togo', 'Benin', 'Senegal', 'Gambia',
            'Guinea-Bissau', 'Guinea', 'Sierra Leone', 'Liberia', 'Côte d\'Ivoire',
            'Mauritania', 'Cape Verde'
        ]
        
        # Create lowercase versions for matching
        canonical_lower = [c.lower() for c in canonical_countries]
        
        # First, try exact match
        if cleaned_country in canonical_lower:
            return canonical_countries[canonical_lower.index(cleaned_country)]
        
        # Try fuzzy matching with high threshold
        best_match = process.extractOne(cleaned_country, canonical_lower, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= 85:  # High confidence threshold
            matched_country = canonical_countries[canonical_lower.index(best_match[0])]
            print(f"🤖 NLP matched '{country}' -> '{matched_country}' (confidence: {best_match[1]}%)")
            return matched_country
        
        # Try partial matching for abbreviations and common variations (with better logic)
        for canonical in canonical_lower:
            # Only do partial matching for longer inputs (3+ chars) to avoid false matches
            if len(cleaned_country) >= 3:
                # Check if input is contained in canonical or vice versa
                if ((cleaned_country in canonical or canonical in cleaned_country) and
                    len(cleaned_country) / len(canonical) >= 0.4):  # At least 40% overlap
                    matched_country = canonical_countries[canonical_lower.index(canonical)]
                    print(f"🤖 NLP partial matched '{country}' -> '{matched_country}'")
                    return matched_country
        
        # Special handling for common abbreviations
        abbreviation_map = {
            'us': 'United States',
            'usa': 'United States',
            'uk': 'United Kingdom',
            'uae': 'United Arab Emirates',
            'sa': 'South Africa',
            'nz': 'New Zealand',
            'dr': 'Dominican Republic',
            'car': 'Central African Republic',
            'drc': 'Democratic Republic of the Congo',
            'hk': 'Hong Kong',
            'macao': 'Macau'
        }
        
        if cleaned_country in abbreviation_map:
            print(f"🤖 NLP abbreviation matched '{country}' -> '{abbreviation_map[cleaned_country]}'")
            return abbreviation_map[cleaned_country]
        
        # If no match found, return title case
        print(f"🤖 NLP no match for '{country}', using title case")
        return country.title()
        
    except Exception as e:
        print(f"⚠️ NLP normalization failed for '{country}': {e}")
        return country.title()

def normalize_city_with_nlp(city: str) -> str:
    """Use NLP to intelligently normalize city names and correct typos"""
    try:
        from fuzzywuzzy import fuzz, process
        import re
        
        # Clean and normalize the input
        cleaned_city = re.sub(r'[^\w\s]', '', city.lower().strip())
        
        # Comprehensive list of major cities worldwide
        canonical_cities = [
            # US Cities
            'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia',
            'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville',
            'Fort Worth', 'Columbus', 'Charlotte', 'San Francisco', 'Indianapolis',
            'Seattle', 'Denver', 'Washington', 'Boston', 'El Paso', 'Nashville',
            'Detroit', 'Oklahoma City', 'Portland', 'Las Vegas', 'Memphis', 'Louisville',
            'Baltimore', 'Milwaukee', 'Albuquerque', 'Tucson', 'Fresno', 'Sacramento',
            'Mesa', 'Kansas City', 'Atlanta', 'Long Beach', 'Colorado Springs', 'Raleigh',
            'Miami', 'Virginia Beach', 'Omaha', 'Oakland', 'Minneapolis', 'Tulsa',
            'Arlington', 'Tampa', 'New Orleans', 'Wichita', 'Cleveland', 'Bakersfield',
            'Aurora', 'Anaheim', 'Honolulu', 'Santa Ana', 'Corpus Christi', 'Riverside',
            'Lexington', 'Stockton', 'Henderson', 'Saint Paul', 'St. Louis', 'Milwaukee',
            
            # International Cities
            'London', 'Paris', 'Tokyo', 'Sydney', 'Berlin', 'Madrid', 'Rome', 'Amsterdam',
            'Vienna', 'Prague', 'Budapest', 'Warsaw', 'Moscow', 'Saint Petersburg',
            'Istanbul', 'Cairo', 'Lagos', 'Nairobi', 'Cape Town', 'Johannesburg',
            'Dubai', 'Riyadh', 'Tehran', 'Baghdad', 'Damascus', 'Beirut', 'Jerusalem',
            'Tel Aviv', 'Bangkok', 'Ho Chi Minh City', 'Jakarta', 'Kuala Lumpur',
            'Manila', 'Seoul', 'Beijing', 'Shanghai', 'Hong Kong', 'Singapore',
            'Taipei', 'Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad',
            'Karachi', 'Lahore', 'Dhaka', 'Colombo', 'Kathmandu', 'Yangon',
            'Bangkok', 'Hanoi', 'Phnom Penh', 'Vientiane', 'Ulaanbaatar',
            'São Paulo', 'Rio de Janeiro', 'Buenos Aires', 'Lima', 'Bogotá',
            'Caracas', 'Quito', 'La Paz', 'Asunción', 'Montevideo', 'Santiago',
            'Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana',
            'Toronto', 'Montreal', 'Vancouver', 'Calgary', 'Edmonton', 'Ottawa',
            'Winnipeg', 'Quebec City', 'Halifax', 'Victoria', 'Hamilton', 'London',
            'Manchester', 'Birmingham', 'Liverpool', 'Leeds', 'Sheffield', 'Bristol',
            'Newcastle', 'Nottingham', 'Leicester', 'Coventry', 'Bradford',
            'Cardiff', 'Belfast', 'Edinburgh', 'Glasgow', 'Aberdeen', 'Dundee',
            'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes', 'Strasbourg',
            'Montpellier', 'Bordeaux', 'Lille', 'Rennes', 'Reims', 'Saint-Étienne',
            'Toulon', 'Le Havre', 'Grenoble', 'Dijon', 'Angers', 'Nîmes',
            'Munich', 'Cologne', 'Frankfurt', 'Stuttgart', 'Düsseldorf', 'Dortmund',
            'Essen', 'Leipzig', 'Bremen', 'Dresden', 'Hannover', 'Nuremberg',
            'Duisburg', 'Bochum', 'Wuppertal', 'Bielefeld', 'Bonn', 'Münster',
            'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Canberra', 'Hobart',
            'Darwin', 'Newcastle', 'Wollongong', 'Gold Coast', 'Sunshine Coast',
            'Townsville', 'Cairns', 'Geelong', 'Ballarat', 'Bendigo', 'Albury',
            'Launceston', 'Mackay',
            
            # Iranian Cities
            'Tehran', 'Mashhad', 'Isfahan', 'Shiraz', 'Tabriz', 'Karaj', 'Ahvaz',
            'Qom', 'Kermanshah', 'Urmia', 'Rasht', 'Zahedan', 'Hamadan', 'Kerman',
            'Yazd', 'Arak', 'Ardabil', 'Bandar Abbas', 'Esfahan', 'Zanjan', 'Sanandaj',
            'Qazvin', 'Khorramabad', 'Gorgan', 'Sari', 'Shahrekord', 'Yasuj',
            'Borujerd', 'Abadan', 'Dezful', 'Kashan', 'Najafabad', 'Sabzevar',
            'Amol', 'Qaemshahr', 'Babol', 'Varamin', 'Malayer', 'Bushehr',
            'Ilam', 'Birjand', 'Maragheh', 'Bojnurd', 'Semnan', 'Mahabad',
            'Saveh', 'Khoy', 'Miandoab', 'Marand', 'Shahin Shahr', 'Marivan',
            'Quchan', 'Jahrom', 'Torbat-e Heydariyeh', 'Sirjan', 'Bam', 'Rafsanjan',
            'Marvdasht', 'Gonbad-e Kavus', 'Izeh', 'Baneh', 'Parsabad', 'Langarud',
            'Andimeshk', 'Shahr-e Kord', 'Khorramshahr', 'Masjed Soleyman',
            'Mahshahr', 'Behbahan', 'Dorud', 'Nahavand', 'Kamyaran', 'Bijar',
            'Takestan', 'Shahriar', 'Robat Karim', 'Pakdasht', 'Qods', 'Baharestan',
            'Malard', 'Fardis', 'Hashtgerd', 'Andisheh', 'Pardis', 'Shahriar',
            'Eslamshahr', 'Rey', 'Varamin', 'Damavand', 'Firoozkooh', 'Pishva',
            'Qarchak', 'Javadabad', 'Kahrizak', 'Shahreza', 'Dehaqan', 'Lenjan',
            'Mobarakeh', 'Falavarjan', 'Tiran', 'Kashan', 'Ardestan', 'Natanz',
            'Nain', 'Anarak', 'Khur', 'Tabas', 'Ferdows', 'Qaen', 'Birjand',
            'Darmian', 'Sarayan', 'Boshruyeh', 'Ferdows', 'Tabas', 'Khorasan',
            'Mashhad', 'Sabzevar', 'Torbat-e Heydariyeh', 'Kashmar', 'Bardaskan',
            'Khalilabad', 'Gonabad', 'Bajestan', 'Ferdows', 'Tabas', 'Birjand',
            'Qaen', 'Darmian', 'Sarayan', 'Boshruyeh', 'Ferdows', 'Tabas'
        ]
        
        # Create lowercase versions for matching
        canonical_lower = [c.lower() for c in canonical_cities]
        
        # First, try exact match
        if cleaned_city in canonical_lower:
            return canonical_cities[canonical_lower.index(cleaned_city)]
        
        # Try fuzzy matching with high threshold for typos
        best_match = process.extractOne(cleaned_city, canonical_lower, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= 80:  # High confidence threshold for cities
            matched_city = canonical_cities[canonical_lower.index(best_match[0])]
            print(f"🏙️ NLP city matched '{city}' -> '{matched_city}' (confidence: {best_match[1]}%)")
            return matched_city
        
        # Try partial matching for abbreviations and common variations
        for canonical in canonical_lower:
            if len(cleaned_city) >= 3:
                if ((cleaned_city in canonical or canonical in cleaned_city) and
                    len(cleaned_city) / len(canonical) >= 0.5):  # At least 50% overlap for cities
                    matched_city = canonical_cities[canonical_lower.index(canonical)]
                    print(f"🏙️ NLP city partial matched '{city}' -> '{matched_city}'")
                    return matched_city
        
        # If no match found, return title case
        print(f"🏙️ NLP no city match for '{city}', using title case")
        return city.title()
        
    except Exception as e:
        print(f"⚠️ NLP city normalization failed for '{city}': {e}")
        return city.title()

def normalize_venue_with_nlp(venue: str) -> str:
    """Use NLP to intelligently normalize venue names"""
    try:
        from fuzzywuzzy import fuzz, process
        import re
        
        # Clean and normalize the input
        cleaned_venue = re.sub(r'[^\w\s]', '', venue.lower().strip())
        
        # Common venue types and patterns
        venue_patterns = {
            'museum': ['museum', 'gallery', 'art center', 'art centre', 'exhibition'],
            'theater': ['theater', 'theatre', 'playhouse', 'stage', 'auditorium'],
            'library': ['library', 'archive', 'collection'],
            'park': ['park', 'garden', 'plaza', 'square', 'commons'],
            'church': ['church', 'cathedral', 'temple', 'mosque', 'synagogue'],
            'university': ['university', 'college', 'institute', 'academy', 'school'],
            'hospital': ['hospital', 'medical center', 'clinic'],
            'hotel': ['hotel', 'inn', 'resort', 'lodge'],
            'restaurant': ['restaurant', 'cafe', 'bistro', 'diner', 'bar'],
            'shopping': ['mall', 'shopping center', 'market', 'bazaar', 'store']
        }
        
        # Try to identify venue type and normalize
        for venue_type, patterns in venue_patterns.items():
            for pattern in patterns:
                if pattern in cleaned_venue:
                    # Found a venue type pattern, normalize the name
                    normalized = venue.title()
                    print(f"🏛️ NLP venue type detected '{venue}' -> '{normalized}' (type: {venue_type})")
                    return normalized
        
        # If no specific pattern found, return title case
        return venue.title()
        
    except Exception as e:
        print(f"⚠️ NLP venue normalization failed for '{venue}': {e}")
        return venue.title()

def are_texts_same(text1: str, text2: str, text_type: str = 'general') -> bool:
    """
    Check if two texts refer to the same entity using NLP
    
    Args:
        text1: First text
        text2: Second text  
        text_type: Type of text ('country', 'city', 'venue', 'general')
    
    Returns:
        True if texts refer to the same entity
    """
    if not text1 or not text2:
        return False
    
    # Normalize both texts
    norm1 = normalize_text_with_nlp(text1, text_type).lower()
    norm2 = normalize_text_with_nlp(text2, text_type).lower()
    
    # Direct match after normalization
    return norm1 == norm2

def find_similar_texts(input_text: str, text_list: List[str], text_type: str = 'general', threshold: int = 80) -> List[Tuple[str, int]]:
    """
    Find similar texts in a list using NLP
    
    Args:
        input_text: Text to find matches for
        text_list: List of texts to search in
        text_type: Type of text ('country', 'city', 'venue', 'general')
        threshold: Minimum similarity threshold (0-100)
    
    Returns:
        List of (text, similarity_score) tuples
    """
    try:
        from fuzzywuzzy import fuzz, process
        
        # Normalize input
        normalized_input = normalize_text_with_nlp(input_text, text_type)
        
        # Find matches
        matches = process.extract(normalized_input, text_list, scorer=fuzz.ratio, limit=5)
        
        # Filter by threshold
        return [(match[0], match[1]) for match in matches if match[1] >= threshold]
        
    except Exception as e:
        print(f"⚠️ Error finding similar texts: {e}")
        return []

def cleanup_duplicates_with_nlp(items: List[Dict], key_fields: List[str], text_types: Dict[str, str]) -> Dict:
    """
    Clean up duplicates in a list of items using NLP
    
    Args:
        items: List of dictionaries representing items
        key_fields: List of field names to use for duplicate detection
        text_types: Dictionary mapping field names to text types
    
    Returns:
        Dictionary with cleanup results
    """
    try:
        print(f"🧹 Starting NLP-powered cleanup for {len(items)} items...")
        
        # Group items by normalized keys
        item_groups = {}
        duplicates_found = 0
        items_to_remove = []
        
        for item in items:
            # Create normalized key
            key_parts = []
            for field in key_fields:
                if field in item and item[field]:
                    text_type = text_types.get(field, 'general')
                    normalized = normalize_text_with_nlp(str(item[field]), text_type).lower()
                    key_parts.append(normalized)
            
            if key_parts:
                key = '|'.join(key_parts)
                
                if key not in item_groups:
                    item_groups[key] = []
                item_groups[key].append(item)
        
        # Find groups with duplicates
        for key, group_items in item_groups.items():
            if len(group_items) > 1:
                duplicates_found += len(group_items) - 1
                print(f"🔄 Found {len(group_items)} duplicates for key: {key}")
                
                # Sort by quality (prefer items with more complete data)
                def item_quality_score(item):
                    score = 0
                    for field in item:
                        if item[field] and str(item[field]).strip():
                            score += len(str(item[field]))
                    return score
                
                group_items.sort(key=item_quality_score, reverse=True)
                
                # Keep the best item, mark others for removal
                best_item = group_items[0]
                print(f"   ✅ Keeping: {best_item}")
                
                for item in group_items[1:]:
                    print(f"   ❌ Marking for removal: {item}")
                    items_to_remove.append(item)
        
        if duplicates_found == 0:
            print("✅ No duplicates found!")
            return {'success': True, 'message': 'No duplicates found', 'duplicates_removed': 0}
        
        print(f"✅ NLP cleanup completed! Found {duplicates_found} duplicates.")
        
        return {
            'success': True,
            'message': f'Successfully identified {duplicates_found} duplicates using NLP',
            'duplicates_found': duplicates_found,
            'items_to_remove': items_to_remove
        }
        
    except Exception as e:
        print(f"❌ Error during NLP cleanup: {e}")
        return {'success': False, 'error': str(e)}

# Convenience functions for common use cases
def normalize_country(country: str, city_context: str = None) -> str:
    """Convenience function for country normalization with city context"""
    return normalize_country_with_nlp(country, city_context)

def normalize_city(city: str) -> str:
    """Convenience function for city normalization"""
    return normalize_city_with_nlp(city)

def normalize_venue(venue: str) -> str:
    """Convenience function for venue normalization"""
    return normalize_venue_with_nlp(venue)

def countries_are_same(country1: str, country2: str) -> bool:
    """Convenience function to check if two countries are the same"""
    return are_texts_same(country1, country2, 'country')

def cities_are_same(city1: str, city2: str) -> bool:
    """Convenience function to check if two cities are the same"""
    return are_texts_same(city1, city2, 'city')

def venues_are_same(venue1: str, venue2: str) -> bool:
    """Convenience function to check if two venues are the same"""
    return are_texts_same(venue1, venue2, 'venue')
