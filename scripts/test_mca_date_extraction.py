#!/usr/bin/env python3
"""
Test script to debug MCA Chicago date extraction
"""
import os
import sys
import re
from bs4 import BeautifulSoup
import requests

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_mca_listing_page():
    """Test date extraction from MCA Chicago listing page"""
    url = "https://visit.mcachicago.org/events/"
    
    print(f"🔍 Fetching: {url}")
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Page loaded successfully")
        print(f"📄 Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for date patterns in the HTML
        date_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', re.I)
        
        # Check all text for dates
        page_text = soup.get_text()
        date_matches = date_pattern.findall(page_text)
        print(f"\n📅 Found {len(date_matches)} date patterns in page text")
        if date_matches:
            print(f"   First 10 matches: {date_matches[:10]}")
        
        # Look for headings with dates
        print(f"\n🔍 Checking headings (h1-h6):")
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headings = soup.find_all(tag)
            for heading in headings:
                text = heading.get_text(strip=True)
                if date_pattern.search(text):
                    print(f"   Found date in {tag}: '{text[:80]}'")
                    # Check what's near this heading
                    next_link = heading.find_next('a', href=True)
                    if next_link:
                        print(f"      Next link: {next_link.get('href', '')[:60]} - '{next_link.get_text(strip=True)[:60]}'")
        
        # Look for Alex Tatarsky specifically
        print(f"\n🔍 Looking for 'Alex Tatarsky' or 'Sad Boys':")
        alex_links = soup.find_all('a', href=True, string=re.compile(r'Alex Tatarsky|Sad Boys', re.I))
        if not alex_links:
            # Try finding by text content
            for link in soup.find_all('a', href=True):
                link_text = link.get_text()
                if 'Alex Tatarsky' in link_text or 'Sad Boys' in link_text:
                    print(f"   Found link: {link.get('href', '')[:80]}")
                    print(f"   Link text: {link_text[:100]}")
                    # Check parent and siblings for dates
                    parent = link.parent
                    if parent:
                        parent_text = parent.get_text()
                        dates_in_parent = date_pattern.findall(parent_text)
                        if dates_in_parent:
                            print(f"   Dates in parent: {dates_in_parent}")
                    # Check previous siblings
                    prev = link.find_previous(['h2', 'h3', 'h4', 'div', 'span'])
                    if prev:
                        prev_text = prev.get_text(strip=True)
                        if date_pattern.search(prev_text):
                            print(f"   Date in previous element: '{prev_text[:80]}'")
        
        # Check the structure around event links
        print(f"\n🔍 Checking event links structure:")
        event_links = soup.find_all('a', href=re.compile(r'/events/[^/]+'))
        print(f"   Found {len(event_links)} links to individual event pages")
        for i, link in enumerate(event_links[:5]):  # Check first 5
            href = link.get('href', '')
            text = link.get_text(strip=True)
            print(f"\n   Link {i+1}: {href[:60]}")
            print(f"   Text: {text[:80]}")
            # Check what's around this link
            parent = link.parent
            if parent:
                # Check for dates in parent
                parent_html = str(parent)[:500]
                if date_pattern.search(parent_html):
                    print(f"   ⚠️  Date found in parent HTML!")
                # Check siblings
                for sibling in [parent.previous_sibling, parent.next_sibling]:
                    if sibling and hasattr(sibling, 'get_text'):
                        sib_text = sibling.get_text(strip=True)
                        if date_pattern.search(sib_text):
                            print(f"   ⚠️  Date in sibling: '{sib_text[:80]}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_mca_event_page():
    """Test date extraction from individual MCA Chicago event page"""
    url = "https://visit.mcachicago.org/events/alex-tatarsky-sad-boys-in-harpy-land/"
    
    print(f"\n\n🔍 Fetching event page: {url}")
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Event page loaded successfully")
        
        date_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', re.I)
        
        # Check headings
        print(f"\n📅 Checking headings for dates:")
        for tag in ['h1', 'h2', 'h3', 'h4']:
            headings = soup.find_all(tag)
            for heading in headings:
                text = heading.get_text(strip=True)
                if date_pattern.search(text):
                    print(f"   {tag}: '{text}'")
        
        # Check common date selectors
        print(f"\n📅 Checking common date selectors:")
        selectors = ['.date', '.event-date', '[itemprop="startDate"]', 'time[datetime]', '.schedule', '.when']
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text:
                    print(f"   {selector}: '{text[:100]}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_mca_listing_page()
    test_mca_event_page()







