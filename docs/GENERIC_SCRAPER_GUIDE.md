# Generic Venue Scraper Guide

## Overview

The `GenericVenueScraper` is a universal scraper that works for any venue/location by using common patterns learned from specialized scrapers. It serves as a fallback when no specialized scraper exists for a venue.

## Key Features

- **Universal Compatibility**: Works with any venue website
- **Pattern-Based Extraction**: Uses common HTML patterns learned from specialized scrapers
- **Multiple Extraction Methods**: 
  - JSON-LD structured data
  - Common CSS selectors
  - Meta tags
  - HTML attributes
- **Robust Date/Time Parsing**: Handles various date and time formats
- **Event Type Detection**: Automatically determines event type from content
- **Bot Protection Handling**: Automatically falls back to cloudscraper for 403 errors
- **SSL Error Handling**: Handles certificate issues gracefully

## Architecture

### Specialized Scrapers (Priority)
1. **Hirshhorn Scraper** - `venue_event_scraper.py` (Hirshhorn-specific methods)
2. **NGA Scraper** - `nga_comprehensive_scraper.py` (NGA-specific methods)
3. **Other specialized scrapers** as needed

### Generic Scraper (Fallback)
- **GenericVenueScraper** - `scripts/generic_venue_scraper.py`
- Used when no specialized scraper exists
- Uses common patterns that work across many websites

## Usage

### Basic Usage

```python
from scripts.generic_venue_scraper import GenericVenueScraper

scraper = GenericVenueScraper()
events = scraper.scrape_venue_events(
    venue_url="https://example-venue.com",
    venue_name="Example Venue",
    event_type=None,  # Optional filter
    time_range='this_month'  # 'today', 'this_week', 'this_month'
)

for event in events:
    print(f"{event['title']} - {event.get('start_date')}")
```

### Integration with Existing System

The generic scraper should be integrated into `venue_event_scraper.py` as a fallback:

```python
def _scrape_venue_website(self, venue, ...):
    # Try specialized scrapers first
    if 'hirshhorn' in venue.name.lower():
        # Use specialized Hirshhorn scraper
        ...
    elif 'nga.gov' in venue.website_url.lower():
        # Use specialized NGA scraper
        ...
    else:
        # Fall back to generic scraper
        from scripts.generic_venue_scraper import GenericVenueScraper
        generic_scraper = GenericVenueScraper()
        events = generic_scraper.scrape_venue_events(
            venue_url=venue.website_url,
            venue_name=venue.name,
            event_type=event_type,
            time_range=time_range
        )
        return events
```

## Extraction Patterns

### Event Selectors
The generic scraper tries these CSS selectors in order:
- `.event`, `.events`, `.event-item`, `.event-card`
- `.calendar-event`, `.upcoming-event`
- `.program`, `.program-item`
- `.tour`, `.tours`, `.guided-tour`
- `.exhibition`, `.exhibitions`
- `[class*="event"]`, `[data-event]`, etc.

### Date Patterns
Handles multiple date formats:
- "December 5, 2025 | 11:30 am–12:00 pm"
- "May 23 - August 23, 2026"
- "2025-12-05"
- "12/05/2025"
- And many more...

### Time Patterns
Extracts times in various formats:
- "11:30 am–12:00 pm"
- "11:30 AM - 12:00 PM"
- "11:30 am to 12:00 pm"
- "11:30 AM"
- 24-hour format: "11:30-12:30"

### JSON-LD Support
Automatically extracts structured data from `<script type="application/ld+json">` tags, which many modern websites use.

## Event Type Detection

The scraper automatically determines event type from title and description:
- **exhibition**: Contains "exhibition" or "exhibit"
- **tour**: Contains "tour" or "guided"
- **workshop**: Contains "workshop" or "class"
- **talk**: Contains "talk", "lecture", or "discussion"
- **festival**: Contains "festival" or "performance"
- **event**: Generic fallback

## Error Handling

- **403 Forbidden**: Automatically retries with cloudscraper
- **SSL Errors**: Handles certificate verification issues
- **Connection Errors**: Retries with exponential backoff
- **Timeout Errors**: Gracefully handles timeouts

## Limitations

1. **Less Accurate**: Generic scraper may be less accurate than specialized scrapers
2. **Pattern Matching**: Relies on common patterns, may miss unique structures
3. **Date Parsing**: May not handle all date formats perfectly
4. **Event Quality**: May extract lower-quality events than specialized scrapers

## Best Practices

1. **Use Specialized Scrapers First**: Always check for specialized scrapers before using generic
2. **Test on Sample Venues**: Test the generic scraper on a few venues before deploying
3. **Monitor Results**: Review extracted events to ensure quality
4. **Iterate**: As you find new patterns, update the generic scraper

## Future Improvements

- Machine learning for better pattern recognition
- More sophisticated date/time parsing
- Better event type classification
- Support for more languages
- Improved handling of dynamic content (JavaScript-rendered pages)

