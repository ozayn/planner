# Washington DC Venue Scraping Improvements

## 📊 Current Status

- **Total DC Venues**: 68
- **Museums**: 15
- **Galleries**: 4 (embedded in museums category)
- **Theaters**: 2
- **Memorials/Monuments**: 8

## 🎯 Major Museums Identified for Improvement

1. **National Gallery of Art** (`https://www.nga.gov`)
   - Special handling needed for calendar pages
   - Finding Awe series events
   - Exhibition listing pages

2. **Hirshhorn Museum and Sculpture Garden** (`https://hirshhorn.si.edu`)
   - Special date format handling
   - Exhibitions-events page structure

3. **International Spy Museum** (`https://www.spymuseum.org`)
   - Exhibition-experiences gallery structure
   - Individual gallery pages vs listing pages

4. **The Phillips Collection** (`https://www.phillipscollection.org`)
   - Exhibition format handling
   - Calendar event structure

5. **Smithsonian Museums** (Multiple)
   - Permanent/ongoing exhibition handling
   - Better date extraction for exhibitions without end dates
   - Listing page detection improvements

## 🔧 Recommended Improvements

### 1. Venue-Specific Scraping Patterns

Add specialized handlers for each major DC museum:

#### National Gallery of Art
- **Calendar Page Detection**: `/calendar/` URLs need special parsing
- **Finding Awe Events**: `/calendar/finding-awe/` series needs dedicated extractor
- **Exhibition Listings**: Better handling of `/exhibitions/` listing pages

#### Hirshhorn Museum
- **Date Format**: Dates often in h2 tags after h1 titles
- **Exhibitions-Events Page**: Combined page structure needs special parsing
- **Permanent Exhibitions**: Handle ongoing exhibitions without end dates

#### International Spy Museum
- **Gallery Structure**: Exhibition-experiences are individual galleries
- **Listing vs Individual**: Better detection of listing pages vs individual gallery pages
- **Gallery Names**: Extract gallery names as exhibition titles

#### Phillips Collection
- **Exhibition Format**: Standard exhibition pages with date ranges
- **Calendar Integration**: Events calendar needs better parsing

### 2. Smithsonian Museum Improvements

#### Date Extraction for Permanent Exhibitions
- Currently skipping exhibitions without start dates
- Should handle "ongoing" and "permanent" exhibitions
- Set start_date to current date if missing
- Set end_date to far future (e.g., 2 years from now) for permanent exhibitions

#### Listing Page Detection
- Improve detection of listing pages vs individual exhibition pages
- Smithsonian uses `/whats-on/exhibitions/` for listings
- Individual pages have slugs after `/exhibitions/`

#### Exhibition Status Handling
- "Ongoing" exhibitions should be included
- "Permanent" exhibitions should be marked appropriately
- Date range parsing for exhibitions with only end dates

### 3. General Improvements

#### Error Handling
- Better retry logic for failed requests
- Exponential backoff for rate limiting
- Skip venues after 3 consecutive failures

#### Timeout Handling
- Increase timeout for slow-loading pages (currently 10s)
- Per-venue timeout tracking
- Skip venue if timeout occurs multiple times

#### Rate Limiting
- Implement smarter rate limiting between requests
- Respect robots.txt (if present)
- Add delays between venue scrapes

#### Duplicate Detection
- Improve URL normalization
- Better title matching (fuzzy matching)
- Check database before adding events

#### Date Parsing
- Better handling of date ranges
- Support for "through", "until", "until further notice"
- Handle ongoing exhibitions
- Parse relative dates ("Today", "This week", etc.)

## 📝 Implementation Plan

### Phase 1: Venue-Specific Handlers
1. Create `dc_venue_scrapers.py` module with specialized scrapers
2. Add NGA calendar page handler
3. Add Hirshhorn date format handler
4. Add Spy Museum gallery handler
5. Add Phillips Collection handler

### Phase 2: Smithsonian Improvements
1. Update date extraction for permanent exhibitions
2. Improve listing page detection
3. Add "ongoing" exhibition handling
4. Test on all Smithsonian museums

### Phase 3: General Improvements
1. Enhance error handling and retry logic
2. Implement better timeout handling
3. Add smart rate limiting
4. Improve duplicate detection

### Phase 4: Testing & Validation
1. Test on all 68 DC venues
2. Generate scraping report
3. Fix identified issues
4. Validate event extraction quality

## 🚀 Quick Wins

1. **Handle Permanent Exhibitions**: Don't skip exhibitions without start dates
2. **Better Listing Page Detection**: Fix Spy Museum and Smithsonian listing detection
3. **Improve Date Parsing**: Support "ongoing" and date ranges better
4. **Error Recovery**: Skip failed venues gracefully and continue

## 📊 Success Metrics

- **Event Discovery Rate**: >80% of venues should yield events
- **Exhibition Extraction**: >90% success rate for major museums
- **Date Accuracy**: All events should have valid dates
- **Duplicate Rate**: <5% duplicate events

## 🔍 Testing Strategy

1. Test on sample of 10 major museums
2. Identify common failure patterns
3. Fix issues and retest
4. Expand to all 68 venues
5. Generate comprehensive report

## 📚 Related Files

- `scripts/venue_event_scraper.py` - Main scraper (needs enhancements)
- `scripts/smithsonian_scraper.py` - Smithsonian-specific scraper
- `scripts/test_dc_venue_scraping.py` - Testing script
- `scripts/improve_dc_venue_scraping.py` - Analysis script

