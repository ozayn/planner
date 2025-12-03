# Automatic Page Discovery System

## Overview

The automatic page discovery system finds exhibition and tour pages on venue websites without requiring manual research or configuration. This makes the scraper work for any venue, even ones we're not familiar with.

## Discovery Strategies

The system uses **4 complementary strategies** to find relevant pages:

### 1. **Sitemap Discovery** (`_discover_via_sitemap`)
- Checks for `sitemap.xml`, `sitemap_index.xml`, etc.
- Parses XML sitemaps to find all pages
- Handles sitemap indexes (sitemaps that reference other sitemaps)
- Filters URLs by event type keywords

**Why it works:** Most modern websites have sitemaps that list all pages. This is the most reliable method.

### 2. **Navigation Menu Discovery** (`_discover_via_navigation`)
- Analyzes navigation menus (`<nav>`, `.menu`, `.navigation`, etc.)
- Looks for links with relevant keywords in text or href
- Follows category pages (e.g., "View All Exhibitions") to find individual pages
- Uses semantic analysis of link text

**Why it works:** Navigation menus are designed to help users find content, so they're a great source of relevant links.

### 3. **URL Pattern Discovery** (`_discover_via_url_patterns`)
- Tries common URL patterns:
  - Exhibitions: `/exhibitions`, `/art/exhibitions`, `/current-exhibitions`, etc.
  - Tours: `/tours`, `/guided-tours`, `/visit/tours`, etc.
- Uses HEAD requests to check if pages exist
- Follows listing pages to find individual pages

**Why it works:** Many websites follow common URL conventions. This catches standard patterns.

### 4. **Site Structure Discovery** (`_discover_via_structure`)
- Analyzes breadcrumbs
- Finds "See All" / "View All" links
- Follows site hierarchy

**Why it works:** Site structure often reveals how content is organized.

## How It Works

```python
from scripts.page_discovery import PageDiscovery

discoverer = PageDiscovery(session)
discovered_urls = discoverer.discover_pages(
    base_url="https://museum.org",
    event_type="exhibition",  # or "tour" or None for both
    max_pages=20
)
```

The scraper automatically uses this when scraping venues:

1. **Discovery Phase**: Finds relevant pages using all 4 strategies
2. **Validation Phase**: Filters out irrelevant pages (contact, shop, etc.)
3. **Scraping Phase**: Scrapes discovered pages for events
4. **Fallback**: If discovery fails, uses original method

## Benefits

✅ **No Manual Configuration**: Works for any venue automatically  
✅ **Comprehensive**: Uses multiple strategies for better coverage  
✅ **Smart Filtering**: Only discovers relevant pages  
✅ **Resilient**: Falls back to original method if discovery fails  
✅ **Efficient**: Limits pages to prevent excessive requests  

## Example Flow

For a museum website:

1. **Sitemap**: Finds `/sitemap.xml` → discovers 50 exhibition URLs
2. **Navigation**: Finds "Exhibitions" in main menu → follows to `/exhibitions`
3. **URL Patterns**: Tries `/exhibitions` → finds listing page
4. **Structure**: Finds "View All" link → discovers individual exhibition pages

Result: Automatically finds all exhibition pages without manual research!

## Future Enhancements

Potential improvements:
- **Machine Learning**: Train a model to identify exhibition/tour pages
- **Content Analysis**: Analyze page content to determine if it's an exhibition/tour page
- **Link Graph**: Build a graph of site structure for better discovery
- **Caching**: Cache discovered pages to avoid re-discovery
- **Confidence Scoring**: Score discovered pages by relevance

## Testing

To test the discovery system:

```python
from scripts.page_discovery import PageDiscovery
import requests

session = requests.Session()
discoverer = PageDiscovery(session)

# Test with a museum
urls = discoverer.discover_pages(
    "https://www.lacma.org",
    event_type="exhibition"
)

print(f"Discovered {len(urls)} exhibition pages")
for url in urls[:5]:
    print(f"  - {url}")
```

