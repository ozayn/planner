# Eventbrite API Setup Guide

This guide explains how to set up the Eventbrite API token to enable event scraping from Eventbrite.

## Why Use Eventbrite API?

The Eventbrite API allows you to:
- Fetch events from venues that have Eventbrite organizer pages
- Automatically extract organizer IDs from Eventbrite URLs
- Get structured event data (dates, times, descriptions, images)
- Access real-time event information

## How to Get an Eventbrite API Token

### Step 1: Create an Eventbrite Account

1. Go to [Eventbrite.com](https://www.eventbrite.com)
2. Sign up for a free account (if you don't have one)
3. Log in to your account

### Step 2: Access API Settings

1. Go to [Eventbrite API Keys](https://www.eventbrite.com/platform/api-keys/)
2. Or navigate: **Account Settings** → **Developer Links** → **API Keys**

### Step 3: Generate a Personal OAuth Token

1. Click **"Create API Key"** or **"Generate Token"**
2. You'll be asked to:
   - Name your application (e.g., "Event Planner Scraper")
   - Select permissions (you'll need at least "Read" access to public events)
3. Click **"Create"** or **"Generate"**
4. **Copy the token immediately** - you won't be able to see it again!

### Step 4: Add Token to Your .env File

1. Open your `.env` file in the project root
2. Add the following line:
   ```bash
   EVENTBRITE_API_TOKEN=your_actual_token_here
   ```
3. Replace `your_actual_token_here` with the token you copied
4. Save the file

### Step 5: Verify Setup

Test that your token works:

```bash
# Test extracting organizer ID from URL
python scripts/eventbrite_scraper.py --test-url "https://www.eventbrite.com/o/korean-cultural-center-washington-dc-30268623512"

# Test scraping events for a venue (requires venue with Eventbrite URL)
python scripts/eventbrite_scraper.py --venue-id 1 --time-range this_month
```

## API Token Format

Eventbrite API tokens are OAuth 2.0 Bearer tokens. They look like:
```
PERSONAL_OAUTH_TOKEN_ABC123XYZ789...
```

## API Rate Limits

Eventbrite API has rate limits:
- **Free tier**: Limited requests per hour
- **Paid tiers**: Higher limits available

The scraper includes automatic pagination and respects rate limits.

## Using the Eventbrite Scraper

### Via API Endpoint

```bash
# Scrape all Eventbrite venues
curl -X POST http://localhost:5001/api/admin/scrape-eventbrite

# Scrape for specific city
curl -X POST http://localhost:5001/api/admin/scrape-eventbrite \
  -H "Content-Type: application/json" \
  -d '{"city_id": 1, "time_range": "this_month"}'

# Scrape for specific venue
curl -X POST http://localhost:5001/api/admin/scrape-eventbrite \
  -H "Content-Type: application/json" \
  -d '{"venue_id": 123, "time_range": "this_week"}'
```

### Via Command Line

```bash
# Scrape all Eventbrite venues in a city
python scripts/eventbrite_scraper.py --city-id 1 --time-range this_month

# Scrape events for a specific venue
python scripts/eventbrite_scraper.py --venue-id 123 --time-range this_week

# Test organizer ID extraction
python scripts/eventbrite_scraper.py --test-url "https://www.eventbrite.com/o/organizer-name-1234567890"
```

## Time Range Options

- `today` - Events happening today only
- `this_week` - Events in the next 7 days
- `this_month` - Events in the next 30 days
- `all` - All upcoming events (no date filter)

## Troubleshooting

### "No API token found" Warning

**Problem**: The scraper warns about missing API token.

**Solution**: 
1. Make sure you've added `EVENTBRITE_API_TOKEN` to your `.env` file
2. Restart your Flask app to load the new environment variable
3. Verify the token is correct (no extra spaces or quotes)

### "401 Unauthorized" Error

**Problem**: API returns 401 Unauthorized.

**Solution**:
1. Check that your token is correct
2. Make sure the token hasn't expired (regenerate if needed)
3. Verify you have the correct permissions

### "403 Forbidden" Error

**Problem**: API returns 403 Forbidden.

**Solution**:
1. Check your API key permissions
2. Make sure you have "Read" access to public events
3. Some organizers may restrict API access to their events

### No Events Found

**Problem**: Scraper runs but finds no events.

**Possible Causes**:
1. Venue doesn't have an Eventbrite ticketing URL
2. Organizer ID couldn't be extracted from URL
3. No events match the time range filter
4. Organizer has no live events

**Solution**:
1. Check that venue has `ticketing_url` with Eventbrite URL
2. Test organizer ID extraction: `python scripts/eventbrite_scraper.py --test-url "YOUR_URL"`
3. Try a broader time range (e.g., `this_month` instead of `today`)

## Finding Eventbrite Organizer URLs

To find Eventbrite organizer pages for venues:

1. **From Event Page**: 
   - Visit any event page on Eventbrite
   - Click on the organizer name
   - Copy the organizer page URL

2. **From Search**:
   - Search Eventbrite for the venue name
   - Look for events organized by the venue
   - Click through to find the organizer page

3. **Format**: 
   - Organizer URLs look like: `https://www.eventbrite.com/o/organizer-name-1234567890`
   - The number at the end is the organizer ID

## Example: Adding Eventbrite URL to Venue

1. Find the venue's Eventbrite organizer page URL
2. In the admin interface, edit the venue
3. Paste the URL into the "Ticketing URL" field
4. Save the venue
5. Run the Eventbrite scraper to fetch events

## Additional Resources

- [Eventbrite API Documentation](https://www.eventbrite.com/platform/api/)
- [Eventbrite API Reference](https://www.eventbrite.com/platform/api#/reference/introduction)
- [Eventbrite API Keys Page](https://www.eventbrite.com/platform/api-keys/)
