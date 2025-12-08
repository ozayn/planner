# Eventbrite Organizer Search Limitations

## Why We Can't Automatically Look Up Organizers

### The Core Problem

Eventbrite **deprecated and removed their public search API** in December 2019, with full deactivation by February 20, 2020. This means:

1. ❌ **No public organizer search endpoint** - There's no API endpoint to search for organizers by name
2. ❌ **No public event search endpoint** - The `/v3/events/search/` endpoint was removed
3. ❌ **Limited access** - API access is now restricted to authenticated users accessing their own organizations/events

### What the API Still Supports

The Eventbrite API v3 currently supports:

✅ **Retrieve specific events by ID**
- `GET /v3/events/:event_id/`

✅ **List events by organization** (if you have access)
- `GET /v3/organizations/:organization_id/events/`

✅ **List events by venue** (if you have access)
- `GET /v3/venues/:venue_id/events/`

✅ **Get organizers for an organization** (if you have access)
- `GET /v3/organizations/:organization_id/organizers/`

✅ **Get organizer details by ID** (if you have the ID)
- `GET /v3/organizers/:organizer_id/`

✅ **Get events for an organizer** (if you have the ID)
- `GET /v3/organizers/:organizer_id/events/`

### The Key Limitation

**You need an `organization_id` to list organizers**, but:
- We don't have organization IDs
- We only have venue names
- There's no way to search for organizations by name
- The `/v3/organizations/{organization_id}/organizers/` endpoint only works if you have access to that organization

### Why Web Scraping Doesn't Work Well

Our web scraping approach (`search_organizers_by_venue_name`) has limitations:

1. **JavaScript-rendered pages** - Eventbrite uses React/JavaScript to render content, so basic HTML parsing doesn't find organizer links
2. **Bot protection** - Eventbrite may have anti-scraping measures
3. **Dynamic content** - Organizer links are loaded dynamically, not in initial HTML

### Current Workarounds

#### ✅ What Works

1. **URL Extraction** - If you have an Eventbrite organizer URL, we can:
   - Extract the organizer ID from the URL
   - Verify it via the API
   - Get organizer details and event counts
   - Fetch events from that organizer

2. **Manual Search** - Users can:
   - Search Eventbrite's website manually
   - Find the organizer page URL
   - Paste it into our system
   - We verify and extract the organizer ID

3. **Direct API Access** - Once we have an organizer ID, we can:
   - Get all events from that organizer
   - Convert them to our event format
   - Store them in the database

#### ❌ What Doesn't Work

1. **Automatic organizer discovery** - Can't search by venue name
2. **Event search API** - The `/v3/events/search/` endpoint returns 404
3. **Organization search** - No way to find organizations by name
4. **Web scraping** - Limited by JavaScript rendering

### Alternative Approaches

#### Option 1: Use Eventbrite's Embedded Widgets
- Eventbrite provides embeddable widgets
- But these don't give us structured data for our database

#### Option 2: Manual Curation
- Users manually find and add Eventbrite organizer URLs
- We verify and extract organizer IDs
- Then we can automatically fetch events going forward

#### Option 3: Partner/Integration
- If you're an Eventbrite partner, you might have access to additional APIs
- Requires business relationship with Eventbrite

#### Option 4: Enhanced Web Scraping
- Use tools like Selenium/Playwright to render JavaScript
- More complex, slower, and may violate Eventbrite's ToS
- Requires maintaining browser automation

### Recommended Workflow

Given these limitations, here's the recommended workflow:

1. **Manual Discovery Phase**
   - Users search Eventbrite website for venues
   - Find organizer page URLs
   - Add them to our system via admin panel

2. **Automated Maintenance Phase**
   - Once we have organizer IDs, we can:
     - Automatically fetch new events
     - Update existing events
     - Monitor for changes

3. **Search Feature**
   - Our search endpoint provides:
     - Instructions for manual search
     - Direct links to Eventbrite search pages
     - URL verification if user pastes an organizer URL

### Code References

- **Eventbrite Scraper**: `scripts/eventbrite_scraper.py`
  - `extract_organizer_id_from_url()` - ✅ Works
  - `get_organizer_by_id()` - ✅ Works (if you have ID)
  - `get_organizer_events()` - ✅ Works (if you have ID)
  - `search_organizers_by_venue_name()` - ⚠️ Limited by web scraping
  - `search_events_by_keyword()` - ❌ Deprecated endpoint (404)

- **API Endpoint**: `app.py` → `/api/admin/search-eventbrite-organizer`
  - Handles URL extraction and verification
  - Provides manual search instructions
  - Attempts web scraping (limited success)

### References

- [Eventbrite API Deprecation Notice](https://github.com/Automattic/eventbrite-api/issues/83)
- [Eventbrite API Documentation](https://www.eventbrite.com/platform/api/)
- [Rollout.com Integration Guide](https://rollout.com/integration-guides/eventbrite/api-essentials)

### Can We Get Followed Organizers?

**Short answer: No.**

The Eventbrite API does **not** provide an endpoint to retrieve organizers that you follow. We tested:

- ❌ `/users/me/following/` - Not found (404)
- ❌ `/users/me/following/organizers/` - Not found (404)
- ❌ `/users/me/organizers/` - Not found (404)
- ❌ `/users/{user_id}/organizers/` - Not found (404)

**What we CAN access:**
- ✅ `/users/me/organizations/` - Organizations you own
- ✅ `/organizations/{org_id}/organizers/` - Organizers in organizations you own
- ✅ `/organizers/{organizer_id}/` - Any organizer (if you have the ID)

**The limitation**: Eventbrite's API only exposes organizers that are part of organizations you own or have access to. It does not expose your "followed" or "subscribed" organizers list.

### Conclusion

**The fundamental issue**: Eventbrite removed public search capabilities from their API. This was a strategic decision to limit external access to their event database.

**Our solution**: Focus on what works:
1. URL extraction and verification ✅
2. Event fetching once we have organizer IDs ✅
3. Manual discovery with automated maintenance ✅

**Additional limitation**: We cannot access your followed organizers list through the API.

The system is designed to work well once organizer URLs are provided, but automatic discovery is not possible due to API limitations.
