# Eventbrite API Credentials Guide

Eventbrite provides several types of credentials. Here's which ones you need and how to save them.

## Credential Types

When you create an Eventbrite API key, you get:

1. **API Key (Client ID)** - Used for OAuth 2.0 flow
2. **Client Secret** - Used for OAuth 2.0 flow  
3. **Personal OAuth Token (Private Token)** ⭐ **USE THIS ONE**
4. **Public Token** - For anonymous access (limited)

## Which One to Use?

### ✅ **Personal OAuth Token (Private Token)** - RECOMMENDED

**Use this for:** Reading public events from Eventbrite organizers

**Why:** 
- Simplest authentication method
- No OAuth flow needed
- Full access to public event data
- Perfect for scraping public events

**How to find it:**
1. Go to [Eventbrite API Keys](https://www.eventbrite.com/platform/api-keys/)
2. Find your app
3. Expand the app details
4. Look for **"Personal OAuth Token"** or **"Private Token"**
5. Copy the token (starts with `PERSONAL_OAUTH_TOKEN_...`)

**Save in .env as:**
```bash
EVENTBRITE_API_TOKEN=your_personal_oauth_token_here
# OR
EVENTBRITE_PRIVATE_TOKEN=your_personal_oauth_token_here
```

### ❌ **API Key + Client Secret** - NOT NEEDED

**Use this for:** OAuth 2.0 flow when authenticating on behalf of other users

**Why not needed:**
- We're only reading public events
- Don't need to authenticate as other users
- More complex setup required

**When you'd use it:**
- Building an app that lets users connect their Eventbrite accounts
- Accessing private/organizer-only data
- Creating events on behalf of users

### ⚠️ **Public Token** - LIMITED USE

**Use this for:** Anonymous access to public events (very limited)

**Why limited:**
- Can only access a small subset of public data
- No access to organizer-specific endpoints
- Rate limits are stricter

**When you'd use it:**
- Quick testing without authentication
- Public event discovery (very basic)

**Save in .env as (optional):**
```bash
EVENTBRITE_PUBLIC_TOKEN=ZRQRSTL4V3Y5X2X5X2X5
```

## Recommended .env Configuration

For our event scraping use case, add this to your `.env` file:

```bash
# Eventbrite API - Personal OAuth Token (Private Token)
# This is the token you get from Eventbrite API Keys page
EVENTBRITE_API_TOKEN=your_personal_oauth_token_here
```

**That's it!** You only need the Personal OAuth Token.

## Complete Example .env Section

```bash
# Eventbrite API (optional - for scraping Eventbrite events)
# Use Personal OAuth Token (Private Token) - this is what you need for reading public events
EVENTBRITE_API_TOKEN=your_personal_oauth_token_here

# Alternative name (both work):
# EVENTBRITE_PRIVATE_TOKEN=your_personal_oauth_token_here

# Optional: Public token for anonymous access (limited functionality)
# EVENTBRITE_PUBLIC_TOKEN=ZRQRSTL4V3Y5X2X5X2X5

# Note: API Key and Client Secret are NOT needed for our use case
# EVENTBRITE_API_KEY=your_api_key_here
# EVENTBRITE_CLIENT_SECRET=your_client_secret_here
```

## Security Notes

1. **Never commit `.env` file** - It contains sensitive tokens
2. **Keep tokens private** - Don't share them publicly
3. **Rotate if compromised** - Generate a new token if exposed
4. **Use different tokens** - Separate tokens for dev/production if needed

## Testing Your Token

After adding the token, test it:

```bash
# Test organizer ID extraction
python scripts/eventbrite_scraper.py --test-url "https://www.eventbrite.com/o/korean-cultural-center-washington-dc-30268623512"

# Test API access (if you have a venue with Eventbrite URL)
python scripts/eventbrite_scraper.py --venue-id 1 --time-range this_month
```

## Troubleshooting

### "401 Unauthorized" Error
- Check that you're using the **Personal OAuth Token**, not the API Key
- Make sure there are no extra spaces or quotes in the token
- Verify the token hasn't expired (regenerate if needed)

### "403 Forbidden" Error  
- Some organizers restrict API access
- Try a different organizer/venue
- Check if the events are truly public

### Token Not Working
- Make sure you copied the **entire token** (they're long!)
- Check for hidden characters or line breaks
- Regenerate the token if unsure
