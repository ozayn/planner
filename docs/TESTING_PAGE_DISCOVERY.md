# Testing Page Discovery

## Quick Test Methods

### Method 1: Test Script (Recommended)

Run the test script with any venue URL:

```bash
# Test exhibition discovery
python scripts/test_page_discovery.py https://www.lacma.org exhibition

# Test tour discovery
python scripts/test_page_discovery.py https://www.lacma.org tour

# Test with any venue
python scripts/test_page_discovery.py https://www.metmuseum.org exhibition
```

**What to look for:**
- ✅ Should find multiple relevant pages (10-20+)
- ✅ URLs should contain "exhibition" or "tour" keywords
- ✅ Should complete in 10-30 seconds

### Method 2: Test Through the UI

1. **Start the app:**
   ```bash
   python app.py
   ```

2. **Go to the scraping interface:**
   - Select a city (e.g., Los Angeles)
   - Select "Exhibitions" as event type
   - Select a venue (e.g., LACMA)
   - Click "Scrape Events"

3. **Check the logs:**
   - Look for: `🔍 Auto-discovered X relevant pages`
   - Should see discovery messages in the console/logs

### Method 3: Python Interactive Test

```python
from scripts.page_discovery import PageDiscovery
import requests

session = requests.Session()
discoverer = PageDiscovery(session)

# Test discovery
urls = discoverer.discover_pages(
    "https://www.lacma.org",
    event_type="exhibition",
    max_pages=20
)

print(f"Found {len(urls)} pages")
for url in urls[:5]:
    print(f"  - {url}")
```

## What Success Looks Like

### ✅ Good Results:
- Finds 10-30+ relevant pages
- URLs are specific exhibition/tour pages
- Discovery completes quickly (< 30 seconds)
- Pages are from the same domain

### ⚠️ Partial Success:
- Finds 1-5 pages (may need more strategies)
- Some pages are category pages (still useful)
- Takes longer (> 30 seconds)

### ❌ Issues:
- Finds 0 pages (will use fallback method)
- Finds wrong pages (contact, shop, etc.)
- Errors/timeouts

## Testing Different Venues

Test with various venue types:

```bash
# Large museum
python scripts/test_page_discovery.py https://www.metmuseum.org exhibition

# Art gallery
python scripts/test_page_discovery.py https://www.guggenheim.org exhibition

# Science museum
python scripts/test_page_discovery.py https://www.si.edu exhibition

# Any venue you want to test
python scripts/test_page_discovery.py <venue-url> <event-type>
```

## Debugging

If discovery isn't working:

1. **Check if venue has a sitemap:**
   ```bash
   curl -I https://venue-url.com/sitemap.xml
   ```

2. **Check navigation structure:**
   - Visit the venue website
   - Look for "Exhibitions" or "Tours" in the main menu
   - Check if URLs follow common patterns

3. **Check logs:**
   - Look for discovery messages
   - Check for errors or timeouts
   - Verify which strategies found pages

## Expected Behavior

The system should:
1. ✅ Try sitemap first (fastest, most reliable)
2. ✅ Check navigation menus
3. ✅ Try common URL patterns
4. ✅ Analyze site structure
5. ✅ Fall back to original method if needed

Even if discovery finds 0 pages, the scraper will still work using the original method (looking for links on the homepage).

