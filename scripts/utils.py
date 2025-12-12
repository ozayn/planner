#!/usr/bin/env python3
"""
CONSOLIDATED UTILITIES
All reusable utility functions for the planner application
"""

import os
import sys
import re
import sqlite3
import requests
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import quote
# Import centralized environment configuration
from scripts.env_config import ensure_env_loaded, get_app_config, get_api_keys, get_available_llm_providers

# Flask-SQLAlchemy imports for database functions
# Note: These will be imported dynamically when needed to avoid circular imports
db = None
City = None
Venue = None
Event = None

# Ensure environment is loaded
ensure_env_loaded()

# Get app configuration
app_config = get_app_config()
DEFAULT_MAX_VENUES = app_config['max_venues_per_city']

# Ensure environment is loaded
ensure_env_loaded()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import NLP utilities
from scripts.nlp_utils import (
    normalize_text_with_nlp,
    normalize_country_with_nlp,
    normalize_city_with_nlp,
    normalize_venue_with_nlp,
    validate_city_country_relationship,
    are_texts_same,
    find_similar_texts,
    cleanup_duplicates_with_nlp
)

# Import dynamic prompt generator
from scripts.dynamic_prompts import DynamicPromptGenerator

# Import venue types from centralized module
from scripts.venue_types import get_allowed_venue_types

# Virtual environment auto-activation
def ensure_venv_activated():
    """Ensure virtual environment is activated and dependencies are available"""
    import sys
    import os
    
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return True  # Already in virtual environment
    
    # Try to find and activate virtual environment
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_path = os.path.join(project_root, 'venv')
    
    if os.path.exists(venv_path):
        # Add virtual environment site-packages to Python path
        site_packages = os.path.join(venv_path, 'lib', 'python3.13', 'site-packages')
        if os.path.exists(site_packages):
            sys.path.insert(0, site_packages)
            return True
    
    return False

def check_city_duplicate_active(name, state, country, exclude_id=None):
    """Check if a city already exists (prevents duplicates during save)"""
    # Import here to avoid circular imports
    try:
        from app import City
        
        # Normalize the input
        normalized_name = normalize_city_with_nlp(name) if name else ""
        normalized_state = state.strip().upper() if state else ""  # Normalize state to uppercase
        normalized_country = country.strip() if country else ""
        
        # Query for existing cities in the same country
        query = City.query.filter_by(country=normalized_country)
        all_cities = query.all()
        
        for city in all_cities:
            if city.id == exclude_id:
                continue
                
            # Normalize existing city data
            city_name_lower = city.name.lower().strip()
            city_state_normalized = city.state.strip().upper() if city.state else ""
            input_name_lower = normalized_name.lower().strip()
            
            # Check for exact matches (same name and state)
            if (city_name_lower == input_name_lower and 
                city_state_normalized == normalized_state):
                return city, "exact"
            
            # Check for common city name variations
            variations = [
                ("new york city", "new york"),
                ("los angeles", "la"),
                ("san francisco", "sf"),
                ("washington dc", "washington"),
                ("washington d.c.", "washington"),
                ("chicago", "chi"),
            ]
            
            for var1, var2 in variations:
                if ((city_name_lower == var1 and input_name_lower == var2) or 
                    (city_name_lower == var2 and input_name_lower == var1)):
                    # Also check if states match (or one is empty)
                    if (city_state_normalized == normalized_state or 
                        not city_state_normalized or not normalized_state):
                        return city, "variation"
            
            # Check if names are very similar and states match
            if (city_name_lower == input_name_lower and 
                (city_state_normalized == normalized_state or 
                 not city_state_normalized or not normalized_state)):
                return city, "similar"
        
        return None, None
    except Exception as e:
        print(f"Error in check_city_duplicate_active: {e}")
        return None, None

def check_event_duplicate(title, start_date, venue_id=None, city_id=None, exclude_id=None):
    """Check if an event already exists (prevents duplicates during save)"""
    # Import here to avoid circular imports
    try:
        from app import Event
        
        # Normalize the input
        normalized_title = normalize_text_field(title) if title else ""
        normalized_date = start_date  # Date should already be in proper format
        
        # Query for existing events
        query = Event.query.filter_by(start_date=normalized_date)
        all_events = query.all()
        
        for event in all_events:
            if event.id == exclude_id:
                continue
                
            # Normalize existing event data
            event_title_lower = event.title.lower().strip()
            input_title_lower = normalized_title.lower().strip()
            
            # Check for exact title match
            if event_title_lower == input_title_lower:
                # Check if they're in the same venue or city
                if venue_id and event.venue_id == venue_id:
                    return event, "exact_venue"
                elif city_id and event.city_id == city_id:
                    return event, "exact_city"
                elif not venue_id and not city_id:
                    # If no specific location, check if both have no location
                    if not event.venue_id and not event.city_id:
                        return event, "exact_no_location"
            
            # Check for very similar titles (fuzzy match)
            if abs(len(event_title_lower) - len(input_title_lower)) <= 3:
                # Simple similarity check - if titles are very close in length and content
                if (event_title_lower in input_title_lower or 
                    input_title_lower in event_title_lower):
                    if venue_id and event.venue_id == venue_id:
                        return event, "similar_venue"
                    elif city_id and event.city_id == city_id:
                        return event, "similar_city"
        
        return None, None
    except Exception as e:
        print(f"Error in check_event_duplicate: {e}")
        return None, None

def check_venue_duplicate(name, city_id, exclude_id=None):
    """Check if a venue already exists in the same city (prevents duplicates during save)"""
    # Import here to avoid circular imports
    try:
        from app import Venue
        
        # Normalize the input
        normalized_name = normalize_text_field(name) if name else ""
        
        # Query for existing venues in the same city
        query = Venue.query.filter_by(city_id=city_id)
        all_venues = query.all()
        
        for venue in all_venues:
            if venue.id == exclude_id:
                continue
                
            # Normalize existing venue data
            venue_name_lower = venue.name.lower().strip()
            input_name_lower = normalized_name.lower().strip()
            
            # Check for exact matches (city_id + name)
            if venue_name_lower == input_name_lower:
                return venue, "exact"
            
            # Check for very similar names
            if abs(len(venue_name_lower) - len(input_name_lower)) <= 3:
                if (venue_name_lower in input_name_lower or 
                    input_name_lower in venue_name_lower):
                    return venue, "similar"
        
        return None, None
    except Exception as e:
        print(f"Error in check_venue_duplicate: {e}")
        return None, None

# Field cleaning utilities
def clean_event_title(title: str) -> str:
    """
    Clean event title by removing venue name suffixes.
    Removes patterns like "| National Gallery of Art", "- Museum Name", etc.
    
    Args:
        title: The event title to clean
        
    Returns:
        Cleaned title with venue name suffixes removed
    """
    if not title:
        return title
    
    title = title.strip()
    
    # Split on pipe character and take first part
    if '|' in title:
        title = title.split('|')[0].strip()
    
    # Remove common venue name suffix patterns (case-insensitive)
    # Pattern: | Venue Name or - Venue Name at the end
    patterns = [
        r'\s*\|\s*National Gallery of Art\s*$',
        r'\s*-\s*National Gallery of Art\s*$',
        r'\s*\|\s*Smithsonian.*?Museum\s*$',
        r'\s*-\s*Smithsonian.*?Museum\s*$',
        r'\s*\|\s*.*?Museum\s*$',  # Generic | Museum Name
        r'\s*-\s*.*?Museum\s*$',   # Generic - Museum Name
    ]
    
    for pattern in patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    
    return title.strip()


def detect_ongoing_exhibition(text: str) -> bool:
    """
    Detect if an exhibition is ongoing/permanent based on text content.
    
    Args:
        text: Text content to analyze (can be description, date text, etc.)
        
    Returns:
        True if the text indicates an ongoing/permanent exhibition, False otherwise
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Patterns that indicate ongoing/permanent exhibitions
    ongoing_patterns = [
        r'\bongoing\b',
        r'\bpermanent(?:ly)?\b',
        r'\bindefinitely\b',
        r'\bon\s+view\s+(?:indefinitely|permanently|ongoing)',
        r'permanent(?:ly)?\s+(?:on\s+view|exhibition|collection)',
        r'always\s+on\s+view',
        r'always\s+on\s+display',
    ]
    
    for pattern in ongoing_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    return False


def get_ongoing_exhibition_dates(start_date=None):
    """
    Get standardized dates for ongoing/permanent exhibitions.
    
    Rule: Set start_date to today (or provided start_date) and end_date to 2 years from today.
    This allows ongoing exhibitions to naturally expire and be re-scraped to check if still ongoing.
    
    Args:
        start_date: Optional start date (date object). If None, uses today's date.
        
    Returns:
        Tuple of (start_date, end_date) as date objects
    """
    from datetime import date, timedelta
    
    if start_date is None:
        start_date = date.today()
    
    # Set end_date to 2 years from today (approximately 730 days)
    end_date = date.today() + timedelta(days=730)
    
    return start_date, end_date


def process_ongoing_exhibition_dates(date_range: Optional[Dict], text: str = None, 
                                     start_date: Optional[date] = None) -> Optional[Dict]:
    """
    Process dates for exhibitions, handling ongoing/permanent exhibitions.
    
    This function:
    1. Checks if the exhibition is marked as ongoing/permanent
    2. If ongoing and no end_date, sets end_date to 2 years from today
    3. If ongoing and no dates at all, sets both start and end dates
    4. If end_date is very far in the future (>2 years), treats as ongoing
    
    Args:
        date_range: Dictionary with 'start_date' and/or 'end_date' keys (date objects)
        text: Optional text content to check for ongoing indicators
        start_date: Optional start_date if date_range is None
        
    Returns:
        Updated date_range dictionary, or None if no dates can be determined
    """
    from datetime import date, timedelta
    
    if date_range is None:
        date_range = {}
    
    # Check if text indicates ongoing
    is_ongoing = False
    if text:
        is_ongoing = detect_ongoing_exhibition(text)
    
    # Check if end_date is very far in the future (indicates ongoing)
    # BUT: Don't override valid end dates! Only treat as ongoing if:
    # 1. Text explicitly says "ongoing" OR
    # 2. End date is unreasonably far (10+ years) - likely a placeholder
    # For dates 2-10 years out, keep them as-is (they're valid exhibition end dates)
    if date_range.get('end_date'):
        ten_years_from_now = date.today() + timedelta(days=3650)  # 10 years
        # Only treat as ongoing if end_date is unreasonably far (10+ years)
        # This prevents legitimate 2-5 year exhibitions from being treated as "ongoing"
        if date_range['end_date'] > ten_years_from_now:
            is_ongoing = True
            # For very far future dates, treat as ongoing and set to 2 years
            if date_range.get('start_date'):
                _, end_date = get_ongoing_exhibition_dates(date_range['start_date'])
            else:
                start_date_obj = start_date if start_date else date.today()
                start_date_obj, end_date = get_ongoing_exhibition_dates(start_date_obj)
                date_range['start_date'] = start_date_obj
            date_range['end_date'] = end_date
    
    # Handle ongoing exhibitions
    if is_ongoing:
        if not date_range.get('end_date'):
            # No end_date but marked as ongoing - set to 2 years from today
            if date_range.get('start_date'):
                _, end_date = get_ongoing_exhibition_dates(date_range['start_date'])
            else:
                start_date_obj = start_date if start_date else date.today()
                start_date_obj, end_date = get_ongoing_exhibition_dates(start_date_obj)
                date_range['start_date'] = start_date_obj
            date_range['end_date'] = end_date
        elif not date_range.get('start_date'):
            # Has end_date but no start_date - set start_date to today
            date_range['start_date'] = date.today()
    
    # If no dates at all and marked as ongoing, set both
    if is_ongoing and not date_range.get('start_date') and not date_range.get('end_date'):
        start_date_obj, end_date = get_ongoing_exhibition_dates(start_date)
        date_range['start_date'] = start_date_obj
        date_range['end_date'] = end_date
    
    return date_range if date_range.get('start_date') or date_range.get('end_date') else None

def extract_description_from_soup(soup, max_length: int = 2000) -> Optional[str]:
    """
    Extract description from BeautifulSoup object with comprehensive methods.
    Filters out captions and image-related text.
    
    Args:
        soup: BeautifulSoup object
        max_length: Maximum length of description (default 2000)
    
    Returns:
        Description string or None
    """
    if not soup:
        return None
    
    description = None
    
    # Method 1: Look for meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        desc = meta_desc.get('content')
        if len(desc) > 50:
            description = desc
    
    # Method 2: Look for Open Graph description
    if not description:
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            desc = og_desc.get('content')
            if len(desc) > 50:
                description = desc
    
    # Method 3: Find main content area (exclude navigation, headers, footers)
    if not description:
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|body', re.I))
        if not main_content:
            main_content = soup
        
        # Look for explicit description/summary/intro sections
        desc_elem = main_content.find('div', class_=re.compile(r'description|summary|intro|excerpt', re.I))
        if desc_elem:
            # Make sure it's not a caption
            if not any(excluded in str(desc_elem.get('class', [])).lower() for excluded in ['caption', 'image', 'photo']):
                description = desc_elem.get_text(separator=' ', strip=True)
                # Clean up extra whitespace
                description = ' '.join(description.split())
        
        # Method 4: Look for paragraphs in main content, excluding captions
        if not description:
            paragraphs = main_content.find_all('p')
            for p in paragraphs:
                # Skip if it's inside a figure or caption element
                if p.find_parent(['figure', 'figcaption']):
                    continue
                
                # Skip if it's very short (likely a caption)
                p_text = p.get_text(strip=True)
                if len(p_text) < 50:
                    continue
                
                # Skip if it contains caption-like text
                if any(keyword in p_text.lower() for keyword in ['credit:', 'photo:', 'image:', 'courtesy of', '©']):
                    continue
                
                # Skip if it's near an image (check siblings)
                prev_sibling = p.find_previous_sibling()
                next_sibling = p.find_next_sibling()
                if (prev_sibling and prev_sibling.find('img')) or (next_sibling and next_sibling.find('img')):
                    # Check if it's actually a caption (short text near image)
                    if len(p_text) < 100:
                        continue
                
                # This looks like a real description paragraph
                description = p_text
                # Try to get additional paragraphs if they're part of the description
                desc_paragraphs = [p_text]
                current = p.find_next_sibling('p')
                while current and len(desc_paragraphs) < 3:  # Limit to 3 paragraphs
                    current_text = current.get_text(strip=True)
                    # Stop if we hit a caption or very short text
                    if (len(current_text) < 50 or 
                        current.find_parent(['figure', 'figcaption']) or
                        any(keyword in current_text.lower() for keyword in ['credit:', 'photo:', 'image:', 'courtesy of', '©'])):
                        break
                    desc_paragraphs.append(current_text)
                    current = current.find_next_sibling('p')
                
                description = ' '.join(desc_paragraphs)
                break
        
        # Method 5: Look for divs with substantial text content (not captions)
        if not description:
            content_divs = main_content.find_all('div', class_=re.compile(r'text|body|content|paragraph', re.I))
            for div in content_divs:
                # Skip if it's a caption or image container
                if any(excluded in str(div.get('class', [])).lower() for excluded in ['caption', 'image', 'photo', 'figure']):
                    continue
                
                div_text = div.get_text(separator=' ', strip=True)
                # Must be substantial text (at least 100 characters)
                if len(div_text) > 100:
                    # Check if it contains actual content (not just metadata)
                    if not any(keyword in div_text.lower() for keyword in ['credit:', 'photo:', 'image:', 'courtesy of', '©']):
                        description = ' '.join(div_text.split())
                        break
    
    # Clean up description if found
    if description:
        # Remove extra whitespace
        description = ' '.join(description.split())
        # Remove very short descriptions that might be captions
        if len(description) < 50:
            description = None
        # Limit length to reasonable size
        elif len(description) > max_length:
            description = description[:max_length] + '...'
    
    return description


def parse_date_range(date_string: str) -> Optional[Dict[str, date]]:
    """
    Parse date range strings like:
    - "June 21, 2025 – November 30, 2025"
    - "March 2, 2024–January 11, 2026"
    - "April 12, 2025 – April 26, 2026"
    - "April 27, 2024–April 29, 2029"
    - "December 9, 2023–2026" (year only for end)
    - "March 25, 2023–ongoing"
    Returns dict with 'start_date' and 'end_date' or None
    """
    if not date_string or not isinstance(date_string, str):
        return None
    
    # Clean up the string
    date_string = date_string.strip()
    
    # Handle "ongoing" dates - set end date far in the future
    if 'ongoing' in date_string.lower():
        # Extract start date
        start_match = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})', date_string)
        if start_match:
            start_str = start_match.group(1).strip()
            start_date = None
            try:
                start_date = datetime.strptime(start_str, '%B %d, %Y').date()
            except ValueError:
                try:
                    start_date = datetime.strptime(start_str, '%B %d %Y').date()
                except ValueError:
                    pass
            if start_date:
                # Set end date to 10 years in the future for ongoing exhibitions
                end_date = start_date + timedelta(days=3650)
                return {'start_date': start_date, 'end_date': end_date}
    
    # Try to match date range pattern with full dates
    # Pattern: "Month Day, Year – Month Day, Year" or "Month Day, Year–Month Day, Year"
    range_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})\s*[–-]\s*([A-Za-z]+\s+\d{1,2},?\s+20\d{2})'
    match = re.search(range_pattern, date_string)
    
    if match:
        start_str = match.group(1).strip()
        end_str = match.group(2).strip()
        
        try:
            start_date = datetime.strptime(start_str, '%B %d, %Y').date()
            end_date = datetime.strptime(end_str, '%B %d, %Y').date()
            return {'start_date': start_date, 'end_date': end_date}
        except ValueError:
            try:
                # Try without comma
                start_date = datetime.strptime(start_str, '%B %d %Y').date()
                end_date = datetime.strptime(end_str, '%B %d %Y').date()
                return {'start_date': start_date, 'end_date': end_date}
            except ValueError:
                pass
    
    # Try pattern with year only for end date: "December 9, 2023–2026"
    year_only_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})\s*[–-]\s*(20\d{2})'
    match = re.search(year_only_pattern, date_string)
    if match:
        start_str = match.group(1).strip()
        end_year = int(match.group(2))
        try:
            start_date = datetime.strptime(start_str, '%B %d, %Y').date()
            # Set end date to end of the year
            end_date = date(end_year, 12, 31)
            return {'start_date': start_date, 'end_date': end_date}
        except ValueError:
            try:
                start_date = datetime.strptime(start_str, '%B %d %Y').date()
                end_date = date(end_year, 12, 31)
                return {'start_date': start_date, 'end_date': end_date}
            except ValueError:
                pass
    
    # Try single date pattern
    single_pattern = r'([A-Za-z]+\s+\d{1,2},?\s+20\d{2})'
    match = re.search(single_pattern, date_string)
    if match:
        date_str = match.group(1).strip()
        try:
            single_date = datetime.strptime(date_str, '%B %d, %Y').date()
            return {'start_date': single_date, 'end_date': None}
        except ValueError:
            try:
                single_date = datetime.strptime(date_str, '%B %d %Y').date()
                return {'start_date': single_date, 'end_date': None}
            except ValueError:
                pass
    
    return None


def extract_date_range_from_soup(soup) -> Optional[str]:
    """
    Extract date range text from BeautifulSoup object using structured HTML.
    Looks for h3/dt elements with "Dates" heading.
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        Date range string (e.g., "April 27, 2024–April 29, 2029") or None
    """
    if not soup:
        return None
    
    date_text = None
    
    # First, try to extract dates from structured HTML (h3/dt elements)
    # Look for structured date format: h3 with "Dates" followed by date range
    dates_h3 = soup.find('h3', string=re.compile('^Dates?$', re.I))
    if dates_h3:
        # Check next sibling for date text
        next_sibling = dates_h3.find_next_sibling()
        if next_sibling:
            date_text = next_sibling.get_text(strip=True)
        # If not found, check parent's siblings
        if not date_text and dates_h3.parent:
            siblings = dates_h3.parent.find_all(['div', 'p', 'span', 'li'], recursive=False)
            for sibling in siblings:
                sibling_text = sibling.get_text(strip=True)
                # Check if it looks like a date range
                if re.search(r'[A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}[–-]', sibling_text):
                    date_text = sibling_text
                    break
    
    # Also try dt/dd structure
    if not date_text:
        dates_dt = soup.find('dt', string=re.compile('Dates?', re.I))
        if dates_dt:
            dates_dd = dates_dt.find_next_sibling('dd')
            if dates_dd:
                date_text = dates_dd.get_text(strip=True)
    
    # Also try looking for date in list items (li) after "Dates" heading
    if not date_text:
        # Look for list items that might contain dates
        for li in soup.find_all('li'):
            li_text = li.get_text(strip=True)
            # Check if it looks like a date range
            if re.search(r'[A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}[–-]', li_text):
                # Check if there's a "Dates" heading nearby
                parent = li.parent
                if parent:
                    # Look for "Dates" in parent's text or siblings
                    parent_text = parent.get_text()
                    if re.search(r'\bDates?\b', parent_text, re.I):
                        date_text = li_text
                        break
    
    return date_text


def is_category_heading(title: str) -> bool:
    """
    Check if a title is a category heading (like "Past Exhibitions", "Upcoming Exhibitions")
    rather than an actual exhibition title.
    
    Args:
        title: The title to check
        
    Returns:
        True if the title is a category heading, False otherwise
    """
    if not title:
        return False
    
    title_lower = title.lower().strip()
    
    # Exact matches for common category headings
    category_headings = [
        'past exhibitions',
        'traveling exhibitions',
        'upcoming exhibitions',
        'current exhibitions',
        'past exhibition',
        'traveling exhibition',
        'upcoming exhibition',
        'current exhibition',
        'browse exhibitions',
        'view all exhibitions',
        'all exhibitions',
        'exhibitions',
        'exhibition'
    ]
    
    if title_lower in category_headings:
        return True
    
    # Pattern matches for category headings
    import re
    category_patterns = [
        r'^(past|traveling|upcoming|current)\s+exhibitions?$',
        r'^browse\s+exhibitions?$',
        r'^view\s+all\s+exhibitions?$',
        r'^all\s+exhibitions?$',
    ]
    
    for pattern in category_patterns:
        if re.match(pattern, title_lower):
            return True
    
    return False


def clean_text_field(value):
    """Clean text fields by removing markdown formatting and extra whitespace"""
    if not value:
        return None
    
    # Convert to string and strip whitespace
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Remove markdown links like [text](url) and keep just the text
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    
    # Remove markdown formatting
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)        # Code
    cleaned = re.sub(r'#{1,6}\s*', '', cleaned)           # Headers
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_url_field(value):
    """Clean URL fields by removing markdown formatting and extracting URLs"""
    if not value:
        return None
    
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Extract URL from markdown link format [text](url)
    url_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', cleaned)
    if url_match:
        return url_match.group(2).strip()
    
    # Remove markdown formatting but keep the URL
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_email_field(value):
    """Clean email fields by extracting email from markdown links"""
    if not value:
        return None
    
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Extract email from markdown link format [email](mailto:email@domain.com)
    email_match = re.search(r'\[([^\]]+)\]\(mailto:([^)]+)\)', cleaned)
    if email_match:
        return email_match.group(2).strip()
    
    # Extract email from regular email format
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', cleaned)
    if email_match:
        return email_match.group(1).strip()
    
    # Clean markdown formatting
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_phone_field(value):
    """Clean phone number fields"""
    if not value:
        return None
    
    cleaned = str(value).strip()
    
    if not cleaned:
        return None
    
    # Remove markdown formatting
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

def clean_numeric_field(value):
    """Clean numeric fields (latitude, longitude, price, etc.)"""
    if not value:
        return None
    
    try:
        # Convert to string and clean markdown formatting first
        cleaned = str(value).strip()
        if not cleaned:
            return None
        
        # Remove markdown formatting
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)        # Code
        cleaned = re.sub(r'#{1,6}\s*', '', cleaned)           # Headers
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()        # Normalize whitespace
        
        if not cleaned:
            return None
            
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def clean_integer_field(value):
    """Clean integer fields (max_participants, etc.)"""
    if not value:
        return None
    
    try:
        # Convert to string and clean markdown formatting first
        cleaned = str(value).strip()
        if not cleaned:
            return None
        
        # Remove markdown formatting
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)        # Code
        cleaned = re.sub(r'#{1,6}\s*', '', cleaned)           # Headers
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()        # Normalize whitespace
        
        if not cleaned:
            return None
            
        return int(float(cleaned))  # Convert to int via float to handle "25.0"
    except (ValueError, TypeError):
        return None

# Database field constants to avoid hardcoding
class DatabaseFields:
    """Database field names to avoid hardcoding"""
    
    # City fields
    CITY_ID = 'id'
    CITY_NAME = 'name'
    CITY_STATE = 'state'
    CITY_COUNTRY = 'country'
    CITY_TIMEZONE = 'timezone'
    CITY_CREATED_AT = 'created_at'
    CITY_UPDATED_AT = 'updated_at'
    
    # Venue fields
    VENUE_ID = 'id'
    VENUE_NAME = 'name'
    VENUE_TYPE = 'venue_type'
    VENUE_ADDRESS = 'address'
    VENUE_LATITUDE = 'latitude'
    VENUE_LONGITUDE = 'longitude'
    VENUE_IMAGE_URL = 'image_url'
    VENUE_INSTAGRAM_URL = 'instagram_url'
    VENUE_FACEBOOK_URL = 'facebook_url'
    VENUE_TWITTER_URL = 'twitter_url'
    VENUE_YOUTUBE_URL = 'youtube_url'
    VENUE_TIKTOK_URL = 'tiktok_url'
    VENUE_WEBSITE_URL = 'website_url'
    VENUE_DESCRIPTION = 'description'
    VENUE_OPENING_HOURS = 'opening_hours'
    VENUE_HOLIDAY_HOURS = 'holiday_hours'
    VENUE_PHONE_NUMBER = 'phone_number'
    VENUE_EMAIL = 'email'
    VENUE_TOUR_INFO = 'tour_info'
    VENUE_ADMISSION_FEE = 'admission_fee'
    VENUE_CITY_ID = 'city_id'
    VENUE_CREATED_AT = 'created_at'
    VENUE_UPDATED_AT = 'updated_at'
    
    # Event fields (unified)
    EVENT_ID = 'id'
    EVENT_NAME = 'name'
    EVENT_TYPE = 'event_type'
    EVENT_START_DATE = 'start_date'
    EVENT_END_DATE = 'end_date'
    EVENT_START_TIME = 'start_time'
    EVENT_END_TIME = 'end_time'
    EVENT_DESCRIPTION = 'description'
    EVENT_IMAGE_URL = 'image_url'
    EVENT_URL = 'url'
    EVENT_START_LOCATION = 'start_location'
    EVENT_END_LOCATION = 'end_location'
    EVENT_VENUE_ID = 'venue_id'
    EVENT_CITY_ID = 'city_id'
    EVENT_START_LATITUDE = 'start_latitude'
    EVENT_START_LONGITUDE = 'start_longitude'
    EVENT_END_LATITUDE = 'end_latitude'
    EVENT_END_LONGITUDE = 'end_longitude'
    EVENT_TOUR_TYPE = 'tour_type'
    EVENT_MAX_PARTICIPANTS = 'max_participants'
    EVENT_PRICE = 'price'
    EVENT_LANGUAGE = 'language'
    EVENT_EXHIBITION_LOCATION = 'exhibition_location'
    EVENT_CURATOR = 'curator'
    EVENT_ADMISSION_PRICE = 'admission_price'
    EVENT_FESTIVAL_TYPE = 'festival_type'
    EVENT_MULTIPLE_LOCATIONS = 'multiple_locations'
    EVENT_DIFFICULTY_LEVEL = 'difficulty_level'
    EVENT_EQUIPMENT_NEEDED = 'equipment_needed'
    EVENT_ORGANIZER = 'organizer'
    EVENT_CREATED_AT = 'created_at'
    EVENT_UPDATED_AT = 'updated_at'

class DatabaseConfig:
    """Database configuration constants"""
    
    # Database path
    # Use the same database path logic as app.py
    if os.getenv('DATABASE_URL'):
        DB_PATH = os.getenv('DATABASE_URL').replace('sqlite:///', '')
    else:
        # Development database - use project directory
        DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'events.db')
    
    # Table names
    CITIES_TABLE = 'cities'
    VENUES_TABLE = 'venues'
    EVENTS_TABLE = 'events'
    
    # Required indexes
    INDEXES = [
        ('idx_cities_name_country', 'cities', 'name, country'),
        ('idx_venues_city_id', 'venues', 'city_id'),
        ('idx_venues_name', 'venues', 'name'),
        ('idx_events_start_date', 'events', 'start_date'),
        ('idx_events_event_type', 'events', 'event_type'),
        ('idx_events_venue_id', 'events', 'venue_id'),
        ('idx_events_city_id', 'events', 'city_id')
    ]

# Text formatting utilities
def format_city_name(name: str) -> str:
    """Format city name using NLP-based intelligent normalization"""
    return normalize_city_with_nlp(name)

def format_country_name(country: str, city_context: str = None) -> str:
    """Format country name using NLP-based intelligent normalization with city context"""
    return normalize_country_with_nlp(country, city_context)

def format_venue_name(venue: str) -> str:
    """Format venue name using NLP-based intelligent normalization"""
    return normalize_venue_with_nlp(venue)

# Database validation utilities

# Geocoding utilities
def get_timezone_for_city(name: str, country: str, state: str = None) -> str:
    """Get timezone for a city using geopy and timezonefinder"""
    try:
        from geopy.geocoders import Nominatim
        from timezonefinder import TimezoneFinder
        
        # Create geocoder
        geolocator = Nominatim(user_agent="planner_app")
        
        # Build location string
        location_parts = [name]
        if state:
            location_parts.append(state)
        location_parts.append(country)
        
        location_str = ", ".join(location_parts)
        
        # Geocode the location
        location = geolocator.geocode(location_str, timeout=10)
        
        if location:
            # Get timezone using coordinates
            tf = TimezoneFinder()
            timezone = tf.timezone_at(lat=location.latitude, lng=location.longitude)
            
            if timezone:
                print(f"🌍 Found timezone for {location_str}: {timezone}")
                return timezone
        
        # Fallback to manual lookup
        return get_timezone_for_city_manual(name, country, state)
        
    except Exception as e:
        print(f"⚠️ Error getting timezone for {name}: {e}")
        # Fallback to manual lookup
        return get_timezone_for_city_manual(name, country, state)

def get_timezone_for_city_manual(name: str, country: str, state: str = None) -> str:
    """Fallback manual timezone lookup"""
    # US cities timezone mapping
    us_timezones = {
        'New York': 'America/New_York',
        'Los Angeles': 'America/Los_Angeles',
        'Chicago': 'America/Chicago',
        'Denver': 'America/Denver',
        'Phoenix': 'America/Phoenix',
        'Anchorage': 'America/Anchorage',
        'Honolulu': 'Pacific/Honolulu'
    }
    
    # International cities timezone mapping
    international_timezones = {
        'London': 'Europe/London',
        'Paris': 'Europe/Paris',
        'Berlin': 'Europe/Berlin',
        'Rome': 'Europe/Rome',
        'Madrid': 'Europe/Madrid',
        'Amsterdam': 'Europe/Amsterdam',
        'Vienna': 'Europe/Vienna',
        'Prague': 'Europe/Prague',
        'Warsaw': 'Europe/Warsaw',
        'Moscow': 'Europe/Moscow',
        'Istanbul': 'Europe/Istanbul',
        'Cairo': 'Africa/Cairo',
        'Dubai': 'Asia/Dubai',
        'Tehran': 'Asia/Tehran',
        'Bangkok': 'Asia/Bangkok',
        'Tokyo': 'Asia/Tokyo',
        'Seoul': 'Asia/Seoul',
        'Beijing': 'Asia/Shanghai',
        'Shanghai': 'Asia/Shanghai',
        'Hong Kong': 'Asia/Hong_Kong',
        'Singapore': 'Asia/Singapore',
        'Mumbai': 'Asia/Kolkata',
        'Delhi': 'Asia/Kolkata',
        'Sydney': 'Australia/Sydney',
        'Melbourne': 'Australia/Melbourne',
        'Brisbane': 'Australia/Brisbane',
        'Perth': 'Australia/Perth',
        'Adelaide': 'Australia/Adelaide',
        'Toronto': 'America/Toronto',
        'Montreal': 'America/Toronto',
        'Vancouver': 'America/Vancouver',
        'Calgary': 'America/Edmonton',
        'São Paulo': 'America/Sao_Paulo',
        'Rio de Janeiro': 'America/Sao_Paulo',
        'Buenos Aires': 'America/Argentina/Buenos_Aires',
        'Lima': 'America/Lima',
        'Mexico City': 'America/Mexico_City'
    }
    
    # Check US cities first
    if country.lower() in ['united states', 'us', 'usa'] and name in us_timezones:
        return us_timezones[name]
    
    # Check international cities
    if name in international_timezones:
        return international_timezones[name]
    
    # Default fallback
    print(f"⚠️ No timezone mapping found for {name}, {country}. Using UTC.")
    return 'UTC'

def get_city_details_with_geopy(name: str, country: str) -> Dict[str, Any]:
    """Get comprehensive city details using geopy"""
    try:
        from geopy.geocoders import Nominatim
        
        # Create geocoder
        geolocator = Nominatim(user_agent="planner_app")
        
        # Build location string
        location_str = f"{name}, {country}"
        
        # Geocode the location
        location = geolocator.geocode(location_str, timeout=10)
        
        if location:
            # Extract address components
            address_parts = location.raw.get('display_name', '').split(', ')
            
            # Initialize result
            result = {
                'name': name,
                'country': country,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'state': None,
                'timezone': get_timezone_for_city(name, country)
            }
            
            # Extract state/province/region based on country
            if country.lower() in ['united states', 'us', 'usa']:
                # US states
                for part in address_parts:
                    if any(state in part for state in ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming']):
                        result['state'] = part.strip()
                        break
            
            elif country.lower() in ['canada']:
                # Canadian provinces
                for part in address_parts:
                    if any(province in part for province in ['Alberta', 'British Columbia', 'Manitoba', 'New Brunswick', 'Newfoundland and Labrador', 'Northwest Territories', 'Nova Scotia', 'Nunavut', 'Ontario', 'Prince Edward Island', 'Quebec', 'Saskatchewan', 'Yukon']):
                        result['state'] = part.strip()
                        break
            
            elif country.lower() in ['united kingdom', 'uk']:
                # UK regions
                for part in address_parts:
                    if any(region in part for region in ['England', 'Scotland', 'Wales', 'Northern Ireland']):
                        result['state'] = part.strip()
                        break
            
            elif country.lower() in ['france']:
                # French regions
                for part in address_parts:
                    if any(region in part for region in ['Île-de-France', 'Auvergne-Rhône-Alpes', 'Hauts-de-France', 'Grand Est', 'Pays de la Loire', 'Bretagne', 'Nouvelle-Aquitaine', 'Occitanie', 'Provence-Alpes-Côte d\'Azur', 'Normandie', 'Bourgogne-Franche-Comté', 'Centre-Val de Loire', 'Corse']):
                        result['state'] = part.strip()
                        break
            
            elif country.lower() in ['germany']:
                # German states
                for part in address_parts:
                    if any(state in part for state in ['Baden-Württemberg', 'Bayern', 'Berlin', 'Brandenburg', 'Bremen', 'Hamburg', 'Hessen', 'Mecklenburg-Vorpommern', 'Niedersachsen', 'Nordrhein-Westfalen', 'Rheinland-Pfalz', 'Saarland', 'Sachsen', 'Sachsen-Anhalt', 'Schleswig-Holstein', 'Thüringen']):
                        result['state'] = part.strip()
                        break
            
            elif country.lower() in ['australia']:
                # Australian states/territories
                for part in address_parts:
                    if any(state in part for state in ['New South Wales', 'Victoria', 'Queensland', 'Western Australia', 'South Australia', 'Tasmania', 'Australian Capital Territory', 'Northern Territory']):
                        result['state'] = part.strip()
                        break
            
            elif country.lower() in ['japan']:
                # Japanese prefectures
                for part in address_parts:
                    if any(prefecture in part for prefecture in ['Hokkaido', 'Aomori', 'Iwate', 'Miyagi', 'Akita', 'Yamagata', 'Fukushima', 'Ibaraki', 'Tochigi', 'Gunma', 'Saitama', 'Chiba', 'Tokyo', 'Kanagawa', 'Niigata', 'Toyama', 'Ishikawa', 'Fukui', 'Yamanashi', 'Nagano', 'Gifu', 'Shizuoka', 'Aichi', 'Mie', 'Shiga', 'Kyoto', 'Osaka', 'Hyogo', 'Nara', 'Wakayama', 'Tottori', 'Shimane', 'Okayama', 'Hiroshima', 'Yamaguchi', 'Tokushima', 'Kagawa', 'Ehime', 'Kochi', 'Fukuoka', 'Saga', 'Nagasaki', 'Kumamoto', 'Oita', 'Miyazaki', 'Kagoshima', 'Okinawa']):
                        result['state'] = part.strip()
                        break
            
            return result
        
        # Fallback if geocoding fails
        return {
            'name': name,
            'country': country,
            'latitude': None,
            'longitude': None,
            'state': None,
            'timezone': 'UTC'
        }
        
    except Exception as e:
        print(f"⚠️ Error getting city details for {name}: {e}")
        return {
            'name': name,
            'country': country,
            'latitude': None,
            'longitude': None,
            'state': None,
            'timezone': 'UTC'
        }

# Database schema utilities
def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    """Get schema information for a table"""
    try:
        conn = sqlite3.connect(DatabaseConfig.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        conn.close()
        
        schema = []
        for col in columns:
            schema.append({
                'name': col[1],
                'type': col[2],
                'not_null': bool(col[3]),
                'default': col[4],
                'primary_key': bool(col[5])
            })
        
        return schema
        
    except Exception as e:
        print(f"❌ Error getting schema for {table_name}: {e}")
        return []

def get_table_indexes(table_name: str) -> List[Dict[str, Any]]:
    """Get index information for a table"""
    try:
        conn = sqlite3.connect(DatabaseConfig.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        
        conn.close()
        
        index_info = []
        for idx in indexes:
            index_info.append({
                'name': idx[1],
                'unique': bool(idx[2]),
                'origin': idx[3],
                'partial': bool(idx[4])
            })
        
        return index_info
        
    except Exception as e:
        print(f"❌ Error getting indexes for {table_name}: {e}")
        return []

def validate_database_schema() -> Dict[str, Any]:
    """Validate that database schema matches expected structure"""
    try:
        expected_tables = [DatabaseConfig.CITIES_TABLE, DatabaseConfig.VENUES_TABLE, DatabaseConfig.EVENTS_TABLE]
        
        conn = sqlite3.connect(DatabaseConfig.DB_PATH)
        cursor = conn.cursor()
        
        # Check if all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in expected_tables if table not in existing_tables]
        
        if missing_tables:
            conn.close()
            return {
                'valid': False,
                'error': f"Missing tables: {missing_tables}",
                'missing_tables': missing_tables
            }
        
        # Check indexes
        missing_indexes = []
        for index_name, table_name, columns in DatabaseConfig.INDEXES:
            cursor.execute(f"PRAGMA index_list({table_name})")
            table_indexes = [row[1] for row in cursor.fetchall()]
            
            if index_name not in table_indexes:
                missing_indexes.append(index_name)
        
        conn.close()
        
        if missing_indexes:
            return {
                'valid': False,
                'error': f"Missing indexes: {missing_indexes}",
                'missing_indexes': missing_indexes
            }
        
        return {
            'valid': True,
            'message': 'Database schema is valid'
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': f"Database validation error: {e}"
        }

# File utilities
def ensure_directory_exists(path: str) -> bool:
    """Ensure a directory exists, create if it doesn't"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"❌ Error creating directory {path}: {e}")
        return False

def get_database_path() -> str:
    """Get the database path, ensuring directory exists"""
    db_dir = os.path.dirname(DatabaseConfig.DB_PATH)
    ensure_directory_exists(db_dir)
    return DatabaseConfig.DB_PATH

# LLM Configuration and Utilities
class LLMConfig:
    """LLM configuration constants"""
    
    # Get API keys from centralized environment
    _api_keys = get_api_keys()
    
    # API Keys (from centralized environment)
    GROQ_API_KEY = _api_keys['GROQ_API_KEY']
    OPENAI_API_KEY = _api_keys['OPENAI_API_KEY']
    ANTHROPIC_API_KEY = _api_keys['ANTHROPIC_API_KEY']
    COHERE_API_KEY = _api_keys['COHERE_API_KEY']
    GOOGLE_API_KEY = _api_keys['GOOGLE_API_KEY']
    MISTRAL_API_KEY = _api_keys['MISTRAL_API_KEY']
    
    # Model configurations
    MODELS = {
        'groq': {
            'name': 'llama-3.3-70b-versatile',
            'base_url': 'https://api.groq.com/openai/v1',
            'max_tokens': 4000,
            'temperature': 0.7,
            'cost_tier': 'free',
            'priority': 1
        },
        'openai': {
            'name': 'gpt-3.5-turbo',
            'base_url': 'https://api.openai.com/v1',
            'max_tokens': 4000,
            'temperature': 0.7,
            'cost_tier': 'low',
            'priority': 2
        },
        'anthropic': {
            'name': 'claude-3-sonnet-20240229',
            'base_url': 'https://api.anthropic.com/v1',
            'max_tokens': 4000,
            'temperature': 0.7,
            'cost_tier': 'medium',
            'priority': 3
        }
    }

def get_available_llm_providers_utils() -> List[str]:
    """Get list of available LLM providers"""
    return get_available_llm_providers()

def get_primary_llm_provider() -> Optional[str]:
    """Get the primary LLM provider (highest priority available)"""
    available = get_available_llm_providers()
    
    if not available:
        return None
    
    # Return the provider with highest priority
    priorities = {provider: LLMConfig.MODELS.get(provider, {}).get('priority', 999) 
                 for provider in available}
    
    return min(available, key=lambda p: priorities[p])

def check_llm_setup() -> Dict[str, Any]:
    """Check LLM setup and return status"""
    available_providers = get_available_llm_providers()
    primary_provider = get_primary_llm_provider()
    
    return {
        'available_providers': available_providers,
        'primary_provider': primary_provider,
        'total_providers': len(available_providers),
        'has_setup': len(available_providers) > 0,
        'recommendations': _get_llm_recommendations(available_providers)
    }

def _get_llm_recommendations(available_providers: List[str]) -> List[str]:
    """Get recommendations for LLM setup"""
    recommendations = []
    
    if not available_providers:
        recommendations.extend([
            "Set GROQ_API_KEY for free LLM access (recommended)",
            "Set OPENAI_API_KEY for high-quality responses",
            "Set ANTHROPIC_API_KEY for Claude models"
        ])
    elif 'groq' not in available_providers:
        recommendations.append("Consider adding GROQ_API_KEY for free LLM access")
    
    return recommendations

def validate_llm_api_key(provider: str) -> bool:
    """Validate if an API key is set for a provider"""
    api_keys = {
        'groq': LLMConfig.GROQ_API_KEY,
        'openai': LLMConfig.OPENAI_API_KEY,
        'anthropic': LLMConfig.ANTHROPIC_API_KEY,
        'cohere': LLMConfig.COHERE_API_KEY,
        'google': LLMConfig.GOOGLE_API_KEY,
        'mistral': LLMConfig.MISTRAL_API_KEY
    }
    
    return bool(api_keys.get(provider))

def get_llm_model_config(provider: str) -> Optional[Dict[str, Any]]:
    """Get model configuration for a provider"""
    return LLMConfig.MODELS.get(provider)

# Convenience functions for LLM setup
def setup_llm_environment() -> Dict[str, Any]:
    """Setup and validate LLM environment"""
    setup_status = check_llm_setup()
    
    if setup_status['has_setup']:
        print(f"✅ LLM Setup Complete!")
        print(f"   Primary Provider: {setup_status['primary_provider']}")
        print(f"   Available Providers: {', '.join(setup_status['available_providers'])}")
    else:
        print("⚠️  No LLM providers configured")
        print("   Recommendations:")
        for rec in setup_status['recommendations']:
            print(f"   - {rec}")
    
    return setup_status

def test_llm_provider(provider: str) -> Dict[str, Any]:
    """Test a specific LLM provider"""
    if not validate_llm_api_key(provider):
        return {
            'success': False,
            'error': f'No API key found for {provider}',
            'provider': provider
        }
    
    try:
        # Import the enhanced LLM fallback system
        from scripts.enhanced_llm_fallback import EnhancedLLMFallback
        
        llm = EnhancedLLMFallback(silent=True)
        
        # Test with a simple query
        test_prompt = "What is the capital of France?"
        response = llm.query_with_fallback(test_prompt)
        
        return {
            'success': response['success'],
            'provider': provider,
            'response': response.get('content', '') if response['success'] else response.get('error', ''),
            'message': f'{provider} is working correctly' if response['success'] else f'{provider} failed: {response.get("error", "Unknown error")}'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'provider': provider
        }

# Core LLM Query Functions
def query_llm(prompt: str, provider: str = None, max_tokens: int = 4000, temperature: float = 0.7) -> Dict[str, Any]:
    """Query LLM with automatic provider selection and fallback"""
    try:
        from scripts.enhanced_llm_fallback import EnhancedLLMFallback
        
        llm = EnhancedLLMFallback(silent=True)
        
        # Use specified provider or auto-select
        if provider and validate_llm_api_key(provider):
            # Set specific provider if requested and available
            pass  # EnhancedLLMFallback handles this internally
        elif not provider:
            provider = get_primary_llm_provider()
        
        if not provider:
            return {
                'success': False,
                'error': 'No LLM providers available',
                'fallback_used': True
            }
        
        response = llm.query_with_fallback(prompt)
        
        if response['success']:
            return {
                'success': True,
                'response': response['content'],
                'provider': response.get('provider', provider),
                'fallback_used': False
            }
        else:
            return {
                'success': False,
                'error': response.get('error', 'Unknown error'),
                'provider': provider,
                'fallback_used': True
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'provider': provider,
            'fallback_used': True
        }

def query_llm_for_venues(city_name: str, country: str = None, event_type: str = 'tours', max_venues: int = DEFAULT_MAX_VENUES) -> Dict[str, Any]:
    """Query LLM specifically for venue discovery using dynamic prompts"""
    prompt = DynamicPromptGenerator.generate_venue_discovery_prompt(city_name, country, event_type, max_venues)
    
    result = query_llm(prompt, max_tokens=4000)
    
    if result['success']:
        # Clean up the response to handle markdown code blocks
        response = result['response']
        if isinstance(response, str):
            # Remove markdown code blocks
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]  # Remove ```json
            if response.startswith('```'):
                response = response[3:]   # Remove ```
            if response.endswith('```'):
                response = response[:-3]   # Remove trailing ```
            response = response.strip()
            
            # Try to parse as JSON
            try:
                import json
                parsed_response = json.loads(response)
                result['response'] = parsed_response
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw response
                pass
        elif isinstance(response, (list, dict)):
            # Response is already parsed, keep it as is
            pass
    
    return result

def query_llm_for_venue_details(venue_name: str, city: str = None, country: str = None) -> Dict[str, Any]:
    """Query LLM specifically for detailed venue information using dynamic prompts"""
    prompt = DynamicPromptGenerator.generate_venue_details_prompt(venue_name, city, country)
    
    return query_llm(prompt, max_tokens=3000)

def query_llm_for_event_details(event_name: str, venue_name: str = None, city: str = None) -> Dict[str, Any]:
    """Query LLM specifically for event information using dynamic prompts"""
    prompt = DynamicPromptGenerator.generate_event_details_prompt(event_name, venue_name, city)
    
    return query_llm(prompt, max_tokens=3000)

# LLM Setup and Management
def initialize_llm_system() -> Dict[str, Any]:
    """Initialize the complete LLM system"""
    setup_status = setup_llm_environment()
    
    if setup_status['has_setup']:
        # Test the primary provider
        primary_provider = setup_status['primary_provider']
        test_result = test_llm_provider(primary_provider)
        
        setup_status['test_result'] = test_result
        setup_status['system_ready'] = test_result['success']
    else:
        setup_status['system_ready'] = False
        setup_status['test_result'] = None
    
    return setup_status

def get_llm_status() -> Dict[str, Any]:
    """Get current LLM system status"""
    return {
        'setup': check_llm_setup(),
        'available_providers': get_available_llm_providers(),
        'primary_provider': get_primary_llm_provider(),
        'system_ready': len(get_available_llm_providers()) > 0
    }

# Event type utilities
def get_event_type_fields(event_type: str) -> List[str]:
    """Get relevant fields for a specific event type"""
    base_fields = [
        DatabaseFields.EVENT_NAME,
        DatabaseFields.EVENT_TYPE,
        DatabaseFields.EVENT_START_DATE,
        DatabaseFields.EVENT_END_DATE,
        DatabaseFields.EVENT_START_TIME,
        DatabaseFields.EVENT_END_TIME,
        DatabaseFields.EVENT_DESCRIPTION,
        DatabaseFields.EVENT_IMAGE_URL,
        DatabaseFields.EVENT_URL,
        DatabaseFields.EVENT_VENUE_ID,
        DatabaseFields.EVENT_CITY_ID
    ]
    
    type_specific_fields = {
        'tour': [
            DatabaseFields.EVENT_START_LOCATION,
            DatabaseFields.EVENT_END_LOCATION,
            DatabaseFields.EVENT_TOUR_TYPE,
            DatabaseFields.EVENT_MAX_PARTICIPANTS,
            DatabaseFields.EVENT_PRICE,
            DatabaseFields.EVENT_LANGUAGE
        ],
        'exhibition': [
            DatabaseFields.EVENT_EXHIBITION_LOCATION,
            DatabaseFields.EVENT_CURATOR,
            DatabaseFields.EVENT_ADMISSION_PRICE,
            'artists',
            'exhibition_type',
            'collection_period',
            'number_of_artworks',
            'opening_reception_date',
            'opening_reception_time',
            'is_permanent',
            'related_exhibitions'
        ],
        'festival': [
            DatabaseFields.EVENT_FESTIVAL_TYPE,
            DatabaseFields.EVENT_MULTIPLE_LOCATIONS
        ],
        'photowalk': [
            DatabaseFields.EVENT_START_LOCATION,
            DatabaseFields.EVENT_END_LOCATION,
            DatabaseFields.EVENT_DIFFICULTY_LEVEL,
            DatabaseFields.EVENT_EQUIPMENT_NEEDED,
            DatabaseFields.EVENT_ORGANIZER
        ]
    }
    
    return base_fields + type_specific_fields.get(event_type, [])

def validate_event_data(event_data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
    """Validate event data for a specific event type"""
    required_fields = get_event_type_fields(event_type)
    
    missing_fields = []
    for field in required_fields:
        if field not in event_data or not event_data[field]:
            missing_fields.append(field)
    
    return {
        'valid': len(missing_fields) == 0,
        'missing_fields': missing_fields,
        'message': f"Missing required fields: {missing_fields}" if missing_fields else "Event data is valid"
    }

# Database utility functions
def check_city_duplicate(name: str, country: str, state: str = None) -> tuple[bool, str]:
    """Check if a city already exists in the database"""
    try:
        # Import here to avoid circular imports
        from app import City, db
        
        # Format the names first
        formatted_name = format_city_name(name)
        formatted_country = format_country_name(country)
        formatted_state = format_city_name(state) if state else None
        
        # Check for exact match
        existing_city = City.query.filter_by(
            name=formatted_name,
            country=formatted_country,
            state=formatted_state
        ).first()
        
        if existing_city:
            return True, f"City '{formatted_name}, {formatted_country}' already exists"
        
        # Check for similar names (case-insensitive) with country alias recognition
        # First, get all cities with the same formatted name
        similar_cities = City.query.filter(
            db.func.lower(City.name) == formatted_name.lower()
        ).all()
        
        # Check if any of these cities are in the same country (considering aliases)
        for city in similar_cities:
            if _countries_are_same(formatted_country, city.country):
                return True, f"Similar city '{city.name}, {city.country}' already exists"
        
        return False, ""
        
    except Exception as e:
        return False, f"Error checking duplicates: {str(e)}"

def _countries_are_same(country1: str, country2: str) -> bool:
    """Check if two country names refer to the same country"""
    if not country1 or not country2:
        return False
    
    # Normalize both countries using the smart formatting function
    norm1 = format_country_name(country1).lower()
    norm2 = format_country_name(country2).lower()
    
    # Direct match after normalization
    return norm1 == norm2

def cleanup_duplicate_cities():
    """Clean up duplicate cities using NLP-based intelligent matching"""
    try:
        # Import here to avoid circular imports
        from app import City, Venue, Event, db
        
        print("🧹 Starting NLP-powered city cleanup process...")
        
        # Get all cities
        all_cities = City.query.all()
        print(f"📊 Found {len(all_cities)} total cities")
        
        # First, normalize all country names using NLP
        print("🤖 Normalizing country names with NLP...")
        for city in all_cities:
            original_country = city.country
            normalized_country = normalize_country(city.country)
            if original_country != normalized_country:
                print(f"   🔄 Normalized '{original_country}' -> '{normalized_country}'")
                city.country = normalized_country
        
        # Also normalize city names using NLP
        print("🏙️ Normalizing city names with NLP...")
        for city in all_cities:
            original_name = city.name
            normalized_name = normalize_city(city.name)
            if original_name != normalized_name:
                print(f"   🔄 Normalized '{original_name}' -> '{normalized_name}'")
                city.name = normalized_name
        
        # Commit normalization
        db.session.commit()
        
        # Group cities by normalized name and country using NLP
        city_groups = {}
        duplicates_found = 0
        cities_to_delete = []
        
        for city in all_cities:
            # Create a normalized key using NLP
            normalized_name = city.name.lower().strip()
            normalized_country = city.country.lower()  # Already normalized above
            key = f"{normalized_name}|{normalized_country}"
            
            if key not in city_groups:
                city_groups[key] = []
            city_groups[key].append(city)
        
        # Find groups with duplicates
        for key, cities in city_groups.items():
            if len(cities) > 1:
                duplicates_found += len(cities) - 1
                print(f"🔄 Found {len(cities)} duplicates for: {cities[0].name}, {cities[0].country}")
                
                # Sort cities by quality (prefer better formatted data)
                def city_quality_score(city):
                    score = 0
                    # Prefer longer country names (more complete)
                    score += len(city.country)
                    # Prefer cities with state information
                    if city.state:
                        score += 50
                    # Prefer newer entries (more recent)
                    if city.created_at:
                        score += city.created_at.timestamp()
                    # Prefer cities with more complete data
                    if city.timezone and city.timezone != 'UTC':
                        score += 25
                    return score
                
                cities.sort(key=city_quality_score, reverse=True)
                
                # Keep the best city, mark others for deletion
                best_city = cities[0]
                print(f"   ✅ Keeping: {best_city.name}, {best_city.country} (ID: {best_city.id})")
                
                for city in cities[1:]:
                    print(f"   ❌ Marking for deletion: {city.name}, {city.country} (ID: {city.id})")
                    cities_to_delete.append(city)
        
        if duplicates_found == 0:
            print("✅ No duplicates found! Database is clean.")
            return {'success': True, 'message': 'No duplicates found', 'duplicates_removed': 0}
        
        # Delete duplicate cities and update foreign key references
        deleted_count = 0
        for city_to_delete in cities_to_delete:
            try:
                # Find the best city in the same group
                normalized_name = city_to_delete.name.lower().strip()
                normalized_country = city_to_delete.country.lower()
                key = f"{normalized_name}|{normalized_country}"
                
                best_city = None
                for city in city_groups[key]:
                    if city.id != city_to_delete.id:
                        best_city = city
                        break
                
                if best_city:
                    # Update venues to point to the best city
                    venues_to_update = Venue.query.filter_by(city_id=city_to_delete.id).all()
                    for venue in venues_to_update:
                        venue.city_id = best_city.id
                        print(f"   🔄 Updated venue '{venue.name}' to point to city ID {best_city.id}")
                    
                    # Update events to point to the best city
                    events_to_update = Event.query.filter_by(city_id=city_to_delete.id).all()
                    for event in events_to_update:
                        event.city_id = best_city.id
                        print(f"   🔄 Updated event '{event.title}' to point to city ID {best_city.id}")
                
                # Delete the duplicate city
                db.session.delete(city_to_delete)
                deleted_count += 1
                
            except Exception as e:
                print(f"   ❌ Error deleting city {city_to_delete.id}: {e}")
                continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"✅ NLP cleanup completed! Removed {deleted_count} duplicate cities.")
        
        return {
            'success': True, 
            'message': f'Successfully removed {deleted_count} duplicate cities using NLP',
            'duplicates_removed': deleted_count
        }
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error during NLP cleanup: {e}")
        return {'success': False, 'error': str(e)}

# Convenience functions for backward compatibility
# Note: These functions are imported from scripts.nlp_utils above

def normalize_text_field(value):
    """Normalize text field for comparison purposes"""
    if not value:
        return ""
    return str(value).strip().lower()

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

# Google Maps API Functions

def get_google_maps_image(venue_name: str, city: str = None, state: str = None, country: str = None, api_key: str = None) -> Optional[str]:
    """
    Fetch Google Maps first location image for a venue using Google Places API
    
    Args:
        venue_name: Name of the venue
        city: City name (optional)
        state: State/province name (optional) 
        country: Country name (optional)
        api_key: Google Maps API key (optional, will use env var if not provided)
    
    Returns:
        Google Maps image URL or None if not found
    """
    # Ensure environment is loaded
    ensure_env_loaded()
    
    # Get API key
    if not api_key:
        api_keys = get_api_keys()
        api_key = api_keys.get('GOOGLE_MAPS_API_KEY')
    
    if not api_key:
        print("❌ GOOGLE_MAPS_API_KEY not found in environment variables")
        print("   Please add GOOGLE_MAPS_API_KEY to your .env file or pass it as parameter")
        return None
    
    try:
        # Step 1: Build search query
        search_query = venue_name
        if city:
            search_query += f" {city}"
        if state:
            search_query += f" {state}"
        if country:
            search_query += f" {country}"
        
        print(f"🔍 Searching Google Places for: {search_query}")
        
        # Step 2: Search for the place using Places API
        places_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        places_params = {
            'query': search_query,
            'key': api_key
        }
        
        places_response = requests.get(places_url, params=places_params, timeout=10)
        places_response.raise_for_status()
        
        places_data = places_response.json()
        
        if places_data.get('status') != 'OK' or not places_data.get('results'):
            print(f"❌ No results found for {venue_name}")
            return None
        
        # Get the first result
        place = places_data['results'][0]
        place_id = place['place_id']
        place_name = place['name']
        
        print(f"✅ Found place: {place_name} (ID: {place_id})")
        
        # Step 3: Get place details including photos
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            'place_id': place_id,
            'fields': 'photos,name,formatted_address',
            'key': api_key
        }
        
        details_response = requests.get(details_url, params=details_params, timeout=10)
        details_response.raise_for_status()
        
        details_data = details_response.json()
        
        if details_data.get('status') != 'OK':
            print(f"❌ Could not get details for place {place_id}")
            return None
        
        place_details = details_data['result']
        
        # Check if there are photos
        if not place_details.get('photos'):
            print(f"❌ No photos found for {place_name}")
            return None
        
        # Get the first photo
        first_photo = place_details['photos'][0]
        photo_reference = first_photo['photo_reference']
        
        print(f"✅ Found photo reference: {photo_reference[:50]}...")
        
        # Step 4: Construct the image URL
        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_reference}&key={api_key}"
        
        print(f"✅ Generated Google Maps image URL")
        
        return image_url
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error fetching Google Maps image: {e}")
        return None

def test_google_maps_image_url(image_url: str) -> bool:
    """
    Test if a Google Maps image URL is accessible
    
    Args:
        image_url: The Google Maps image URL to test
    
    Returns:
        True if accessible, False otherwise
    """
    if not image_url:
        return False
    
    try:
        response = requests.head(image_url, timeout=10)
        return response.status_code == 200
    except:
        return False

def get_google_maps_image_for_venue(venue_data: Dict[str, str], api_key: str = None) -> Optional[str]:
    """
    Convenience function to get Google Maps image for a venue dictionary
    
    Args:
        venue_data: Dictionary containing venue information with keys:
                   'name', 'city', 'state', 'country' (optional)
        api_key: Google Maps API key (optional)
    
    Returns:
        Google Maps image URL or None if not found
    """
    venue_name = venue_data.get('name', '')
    city = venue_data.get('city', '')
    state = venue_data.get('state', '')
    country = venue_data.get('country', '')
    
    if not venue_name:
        print("❌ Venue name is required")
        return None
    
    return get_google_maps_image(venue_name, city, state, country, api_key)
