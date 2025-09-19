#!/usr/bin/env python3
"""
Source Information Scraper
Fetches real information from various source types using web scraping
Designed for both local development and Railway deployment environments
"""

import requests
import re
import json
import os
import gc
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

# Environment detection functions
def is_railway_environment():
    """Check if running on Railway deployment"""
    return (os.getenv('RAILWAY_ENVIRONMENT') == 'production' or 
            'railway.app' in os.getenv('RAILWAY_PUBLIC_DOMAIN', '') or
            os.getenv('PORT') is not None)

def is_local_development():
    """Check if running in local development"""
    return not is_railway_environment()

def get_resource_limits():
    """Get resource limits based on environment"""
    if is_railway_environment():
        return {
            'request_timeout': 15,  # Shorter timeout for Railway
            'max_retries': 2,       # Fewer retries to conserve resources
            'delay_between_requests': 2,  # Longer delays to avoid rate limiting
            'max_concurrent_requests': 1,  # Single request at a time
        }
    else:
        return {
            'request_timeout': 30,  # Longer timeout for local
            'max_retries': 3,       # More retries for reliability
            'delay_between_requests': 1,  # Shorter delays for faster testing
            'max_concurrent_requests': 3,  # Multiple concurrent requests
        }

def scrape_instagram_info(username_or_url):
    """Scrape basic Instagram profile information with enhanced reliability"""
    # Get environment-specific resource limits
    limits = get_resource_limits()
    
    try:
        # Extract username from URL or handle
        if username_or_url.startswith('@'):
            username = username_or_url[1:]
        elif 'instagram.com' in username_or_url:
            match = re.search(r'instagram\.com/([^/?]+)', username_or_url)
            username = match.group(1) if match else None
        else:
            username = username_or_url
        
        if not username:
            return None
        
        url = f"https://www.instagram.com/{username}/"
        
        # Environment-aware User-Agent selection
        if is_railway_environment():
            # Railway: More generic User-Agent to avoid detection
            user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        else:
            # Local: Full-featured User-Agent
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Enhanced headers to better mimic a real browser
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Add Railway-specific headers if needed
        if not is_railway_environment():
            headers.update({
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"macOS"',
            })
        
        # Create session for better reliability
        session = requests.Session()
        session.headers.update(headers)
        
        # Environment-aware request with retry logic
        for attempt in range(limits['max_retries']):
            try:
                if attempt > 0:
                    time.sleep(limits['delay_between_requests'])
                    
                response = session.get(url, timeout=limits['request_timeout'])
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == limits['max_retries'] - 1:
                    raise e
                print(f"Attempt {attempt + 1} failed, retrying... ({e})")
                
        # Memory cleanup for Railway
        if is_railway_environment():
            gc.collect()
        
        # Parse the page
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Initialize with basic info
        info = {
            'name': username.replace('_', ' ').replace('-', ' ').title(),
            'description': f"Instagram account @{username}",
            'url': url,
            'source_type': 'instagram',
            'handle': f"@{username}",
            'follower_count': None,
            'bio': None,
            'profile_pic': None,
            'is_verified': False,
            'is_private': False
        }
        
        # Try to extract data from JSON-LD structured data
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'ProfilePage':
                    if 'name' in data:
                        info['name'] = data['name']
                    if 'description' in data:
                        info['bio'] = data['description']
                        info['description'] = f"Instagram: {data['description'][:100]}..." if len(data['description']) > 100 else f"Instagram: {data['description']}"
                    break
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Try to extract from meta tags
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content') and not info.get('bio'):
            content = meta_desc.get('content')
            # Parse Instagram meta description format
            if 'Followers' in content and 'Following' in content:
                # Format: "X Followers, Y Following, Z Posts - See Instagram photos and videos from NAME (@username)"
                parts = content.split(' - ')
                if len(parts) > 1:
                    stats_part = parts[0]
                    follower_match = re.search(r'([\d,K]+)\s+Followers', stats_part)
                    if follower_match:
                        info['follower_count'] = follower_match.group(1)
                
                # Extract name from the second part
                if len(parts) > 1 and 'from' in parts[1]:
                    name_match = re.search(r'from\s+(.+?)\s+\(@', parts[1])
                    if name_match:
                        info['name'] = name_match.group(1).strip()
            else:
                info['bio'] = content
                info['description'] = f"Instagram: {content[:100]}..." if len(content) > 100 else f"Instagram: {content}"
        
        # Try to extract from page title
        title_tag = soup.find('title')
        if title_tag and not info.get('bio'):
            title_text = title_tag.get_text().strip()
            # Instagram title format: "NAME (@username) • Instagram photos and videos"
            name_match = re.search(r'^(.+?)\s+\(@', title_text)
            if name_match:
                info['name'] = name_match.group(1).strip()
        
        # Try to find profile picture
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image and og_image.get('content'):
            info['profile_pic'] = og_image.get('content')
        
        # Check if account is private (basic check)
        if 'This account is private' in response.text:
            info['is_private'] = True
        
        # Check if verified (basic check)
        if 'Verified' in response.text or 'verified' in response.text.lower():
            info['is_verified'] = True
        
        return info
        
    except requests.exceptions.RequestException as e:
        print(f"Network error scraping Instagram {username_or_url}: {e}")
        return None
    except Exception as e:
        print(f"Error scraping Instagram {username_or_url}: {e}")
        return None

def scrape_website_info(url):
    """Scrape basic website information"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        parsed_url = urlparse(url)
        
        info = {
            'name': parsed_url.netloc.replace('www.', ''),
            'description': f"Website: {parsed_url.netloc}",
            'url': url,
            'source_type': 'website',
            'handle': parsed_url.netloc,
            'title': None,
            'meta_description': None
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            info['title'] = title_tag.get_text().strip()
            info['name'] = info['title'][:50] + '...' if len(info['title']) > 50 else info['title']
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            info['meta_description'] = meta_desc.get('content').strip()
            info['description'] = f"Website: {info['meta_description'][:100]}..." if len(info['meta_description']) > 100 else f"Website: {info['meta_description']}"
        
        # Try to find contact information
        contact_info = extract_contact_info(soup)
        if contact_info:
            info.update(contact_info)
        
        return info
        
    except Exception as e:
        print(f"Error scraping website {url}: {e}")
        return None

def scrape_facebook_info(url):
    """Scrape basic Facebook page information"""
    try:
        # Facebook is heavily protected, so we'll do basic URL parsing
        match = re.search(r'facebook\.com/([^/?]+)', url)
        if not match:
            return None
        
        page_name = match.group(1)
        
        info = {
            'name': page_name.replace('-', ' ').replace('_', ' ').title(),
            'description': f"Facebook page for {page_name.replace('-', ' ').replace('_', ' ')}",
            'url': url,
            'source_type': 'facebook',
            'handle': page_name,
        }
        
        return info
        
    except Exception as e:
        print(f"Error processing Facebook URL {url}: {e}")
        return None

def scrape_meetup_info(url):
    """Scrape basic Meetup group information"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract group name from URL
        match = re.search(r'meetup\.com/([^/?]+)', url)
        group_handle = match.group(1) if match else 'meetup-group'
        
        info = {
            'name': group_handle.replace('-', ' ').title(),
            'description': f"Meetup group: {group_handle.replace('-', ' ')}",
            'url': url,
            'source_type': 'meetup',
            'handle': group_handle,
        }
        
        # Try to extract group title
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            if 'Meetup' in title:
                info['name'] = title.replace(' | Meetup', '').strip()
        
        # Try to extract description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc.get('content').strip()
            info['description'] = f"Meetup: {desc[:100]}..." if len(desc) > 100 else f"Meetup: {desc}"
        
        return info
        
    except Exception as e:
        print(f"Error scraping Meetup {url}: {e}")
        return None

def extract_contact_info(soup):
    """Extract contact information from website"""
    contact_info = {}
    
    try:
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            contact_info['email'] = emails[0]  # Take the first email found
        
        # Look for phone numbers (basic pattern)
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, soup.get_text())
        if phones:
            contact_info['phone'] = phones[0]
        
    except Exception as e:
        print(f"Error extracting contact info: {e}")
    
    return contact_info

def scrape_source_info(source_url, source_type=None):
    """Main function to scrape source information based on URL/type"""
    try:
        if not source_url:
            return None
        
        # Auto-detect source type if not provided
        if not source_type:
            if 'instagram.com' in source_url or source_url.startswith('@'):
                source_type = 'instagram'
            elif 'facebook.com' in source_url:
                source_type = 'facebook'
            elif 'meetup.com' in source_url:
                source_type = 'meetup'
            elif 'eventbrite.com' in source_url:
                source_type = 'eventbrite'
            else:
                source_type = 'website'
        
        # Route to appropriate scraper
        if source_type == 'instagram':
            return scrape_instagram_info(source_url)
        elif source_type == 'facebook':
            return scrape_facebook_info(source_url)
        elif source_type == 'meetup':
            return scrape_meetup_info(source_url)
        elif source_type == 'website':
            return scrape_website_info(source_url)
        else:
            # Fallback to website scraping
            return scrape_website_info(source_url)
    
    except Exception as e:
        print(f"Error scraping source {source_url}: {e}")
        return None

if __name__ == "__main__":
    # Test the scraper
    test_sources = [
        "@princetonphotoclub",
        "https://www.instagram.com/dcphotowalks/",
        "https://example.com",
        "https://www.meetup.com/photography-group/"
    ]
    
    for source in test_sources:
        print(f"\nTesting: {source}")
        info = scrape_source_info(source)
        if info:
            print(f"  Name: {info['name']}")
            print(f"  Description: {info['description']}")
            print(f"  Type: {info['source_type']}")
        else:
            print("  Failed to scrape")
