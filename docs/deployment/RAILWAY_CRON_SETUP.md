# Railway Cronjob Setup Guide

This guide explains how to set up automated scraping cronjobs on Railway.

## Overview

Railway supports scheduled tasks through cron jobs. You can set up a cron schedule directly in the Railway dashboard for any service.

## Option 1: Add Cron Schedule to Existing Service (Recommended)

1. **Go to Railway Dashboard**
   - Navigate to your project
   - Click on your web service (or create a new service)

2. **Add Cron Schedule**
   - Go to the **Settings** tab
   - Find the **Cron Schedule** section
   - Enter a cron expression (uses UTC time)

3. **Configure the Service**
   - **Start Command**: `python scripts/cron_scrape_dc_museums.py`
   - **Cron Schedule**: `25 20 * * 1` (every Monday at 8:25 PM UTC = 3:25 PM ET)
   
   Note: Timezone conversion:
   - **Current Setting**: `25 20 * * 1` = 3:25 PM ET (EST) / 4:25 PM ET (EDT) on Mondays
   - EST is UTC-5, so 8:25 PM UTC (20:25) = 3:25 PM EST
   - EDT is UTC-4, so 7:25 PM UTC (19:25) = 3:25 PM EDT (during daylight saving time)
   - ⚠️ **Important**: This setting uses EST. During EDT (spring/summer), it will run at 4:25 PM ET
   - To always run at 3:25 PM ET year-round, you'll need to update the schedule twice per year:
     - EST period (Nov-Mar): `25 20 * * 1` (8:25 PM UTC)
     - EDT period (Mar-Nov): `25 19 * * 1` (7:25 PM UTC)

## Option 2: Create a Separate Cron Service

1. **Create New Service**
   - In Railway dashboard, click **+ New** → **Empty Service**
   - Name it something like "DC Museums Scraper"

2. **Configure the Service**
   - **Source**: Same GitHub repo (or connect it)
   - **Start Command**: `python scripts/cron_scrape_dc_museums.py`
   - **Root Directory**: `/` (or leave default)

3. **Add Cron Schedule**
   - Go to **Settings** tab
   - Find **Cron Schedule** section
   - Enter: `25 20 * * 1` (every Monday at 8:25 PM UTC = 3:25 PM ET)

4. **Environment Variables**
   - Ensure the service has access to all required environment variables:
     - `DATABASE_URL` (Railway should auto-provide if using Railway Postgres)
     - `FLASK_ENV=production`
     - Any API keys needed (GROQ_API_KEY, etc.)

## Recommended Schedule Examples

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| **Monday 3:25 PM ET (CURRENT)** | `25 20 * * 1` | Every Monday at 3:25 PM ET (EST) / 4:25 PM ET (EDT) |
| Weekly (Monday 2 AM UTC) | `0 2 * * 1` | Every Monday at 2:00 AM UTC (9 PM Sunday EST) |
| Weekly (Sunday 3 AM UTC) | `0 3 * * 0` | Every Sunday at 3:00 AM UTC (10 PM Saturday EST) |
| Daily (2 AM UTC) | `0 2 * * *` | Every day at 2:00 AM UTC |
| **Weekly Cleanup (Sun 4 AM UTC)** | `0 4 * * 0` | Every Sunday at 4:00 AM UTC (Database Cleanup) |
| Twice Weekly (Mon & Thu 2 AM UTC) | `0 2 * * 1,4` | Monday and Thursday at 2:00 AM UTC |
| Every 12 Hours | `0 */12 * * *` | Every 12 hours (must be at least 5 minutes apart) |

**Important**: Railway cron schedules use **UTC time**. Use a timezone converter to get the right UTC time for your desired local time.

## Which Script to Use?

### `cron_scrape_dc_museums.py` (Recommended)
- Scrapes only museums and embassies
- Faster execution
- More focused logging
- **Start Command**: `python scripts/cron_scrape_dc_museums.py`

### `cron_scrape_dc.py`
- Scrapes ALL venues in DC
- Longer execution time
- More comprehensive coverage
- **Start Command**: `python scripts/cron_scrape_dc.py`

### `cron_clear_past_events.py`
- Automatically deletes expired events
- Keeps database clean
- Recommended to run weekly
- **Start Command**: `python scripts/cron_clear_past_events.py`

## Testing the Cronjob

1. **Test Locally First**
   ```bash
   python scripts/cron_scrape_dc_museums.py
   ```

2. **Test on Railway**
   - Go to your cron service
   - Click **Deployments** tab
   - Click **Manual Deploy** to test immediately
   - Check logs to verify it works

3. **Monitor Logs**
   - Railway logs show all output from the cronjob
   - Check the **Logs** tab in Railway dashboard
   - The script also creates log files: `logs/cron_scrape_dc_museums_YYYYMMDD.log`

## Important Notes

1. **Service Must Exit**: Railway cronjobs must complete and exit. The script is designed to:
   - Run the scraping process
   - Save events to database
   - Log results
   - Exit cleanly

2. **Minimum Interval**: Railway requires at least 5 minutes between cron executions.

3. **Timezone**: All cron schedules use UTC. Convert your desired local time to UTC.

4. **Database Connection**: The service needs access to `DATABASE_URL`. If using Railway Postgres, make sure the service is connected to the database.

5. **Error Handling**: The script includes error handling and will log errors without crashing.

## Troubleshooting

### Cronjob Not Running
- Check that the cron schedule is correctly set in Settings
- Verify the start command is correct
- Check Railway logs for errors

### Database Connection Errors
- Ensure `DATABASE_URL` environment variable is set
- If using Railway Postgres, verify the service has database access
- Check that the database is running

### Import Errors
- Make sure all dependencies are in `requirements.txt`
- Railway will install dependencies automatically

### Timezone Issues
- Remember Railway uses UTC for cron schedules
- Use a converter: https://www.timeanddate.com/worldclock/converter.html
- Example: 2 AM EST Monday = 7 AM UTC Monday (during EST)

## Monitoring

- **Railway Dashboard**: Check the Logs tab for real-time output
- **Local Logs**: Scripts create log files in `logs/` directory
- **Database**: Check events table to verify new events were created

## Next Steps

1. Set up the cron schedule in Railway dashboard
2. Test with a manual deploy
3. Monitor the first few runs
4. Adjust schedule if needed
