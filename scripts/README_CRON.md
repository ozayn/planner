# Cronjob Setup for DC Event Scraping

This guide explains how to set up weekly cronjobs to automatically scrape Washington DC events.

## Available Scripts

1. **`cron_scrape_dc.py`** - Scrapes ALL venues in DC (museums, galleries, embassies, etc.)
2. **`cron_scrape_dc_museums.py`** - Scrapes ONLY museums in DC (focused on museums)

## Scripts Overview

### `cron_scrape_dc.py` - All Venues
Scrapes all active venues in Washington DC:
- All venues (museums, galleries, embassies, etc.)
- Uses specialized scrapers for museums (NGA, SAAM, NPG, etc.)
- Scrapes event sources (Instagram pages, websites, etc.)
- Save events to the database
- Log results for monitoring

### `cron_scrape_dc_museums.py` - Museums Only
Scrapes only museums in Washington DC:
- Filters to museums only (by name and venue type)
- Uses specialized scrapers (NGA, SAAM, NPG, Asian Art, African Art, Hirshhorn, etc.)
- More focused logging per museum
- Ideal for museum-specific scraping schedules

## Setup Instructions

### 1. Test the Script Manually

First, test that the script works:

**For all venues:**
```bash
cd /Users/oz/Dropbox/2025/planner
source venv/bin/activate
python scripts/cron_scrape_dc.py
```

**For museums only:**
```bash
cd /Users/oz/Dropbox/2025/planner
source venv/bin/activate
python scripts/cron_scrape_dc_museums.py
```

### 2. Set Up Cronjob

#### Option A: Using crontab (Recommended)

1. Open your crontab:
```bash
crontab -e
```

2. Add one of these lines (choose based on your preference):

**All venues - every Monday at 2 AM:**
```bash
0 2 * * 1 cd /Users/oz/Dropbox/2025/planner && source venv/bin/activate && python scripts/cron_scrape_dc.py >> logs/cron_scrape_dc.log 2>&1
```

**Museums only - every Monday at 3 AM:**
```bash
0 3 * * 1 cd /Users/oz/Dropbox/2025/planner && source venv/bin/activate && python scripts/cron_scrape_dc_museums.py >> logs/cron_scrape_dc_museums.log 2>&1
```

**Museums only - every Sunday at 3 AM:**
```bash
0 3 * * 0 cd /Users/oz/Dropbox/2025/planner && source venv/bin/activate && python scripts/cron_scrape_dc_museums.py >> logs/cron_scrape_dc_museums.log 2>&1
```

**All venues - every day at 2 AM:**
```bash
0 2 * * * cd /Users/oz/Dropbox/2025/planner && source venv/bin/activate && python scripts/cron_scrape_dc.py >> logs/cron_scrape_dc.log 2>&1
```

#### Option B: Using a Shell Script Wrapper

Create a wrapper script for easier management:

1. Create `scripts/run_cron_scrape.sh`:
```bash
#!/bin/bash
cd /Users/oz/Dropbox/2025/planner
source venv/bin/activate
python scripts/cron_scrape_dc.py
```

2. Make it executable:
```bash
chmod +x scripts/run_cron_scrape.sh
```

3. Add to crontab (for all venues):
```bash
0 2 * * 1 /Users/oz/Dropbox/2025/planner/scripts/run_cron_scrape.sh >> /Users/oz/Dropbox/2025/planner/logs/cron_scrape_dc.log 2>&1
```

Or create a separate wrapper for museums:
```bash
0 3 * * 1 /Users/oz/Dropbox/2025/planner/scripts/run_cron_scrape_museums.sh >> /Users/oz/Dropbox/2025/planner/logs/cron_scrape_dc_museums.log 2>&1
```

### 3. Verify Cronjob is Set Up

Check your crontab:
```bash
crontab -l
```

### 4. Monitor Logs

Logs are written to:
- `logs/cron_scrape_dc_YYYYMMDD.log` - Daily log files (all venues)
- `logs/cron_scrape_dc_museums_YYYYMMDD.log` - Daily log files (museums only)
- `logs/cron_scrape_dc.log` - If using the redirect in crontab (all venues)
- `logs/cron_scrape_dc_museums.log` - If using the redirect in crontab (museums)

View recent logs:
```bash
# All venues
tail -f logs/cron_scrape_dc.log
# or
tail -f logs/cron_scrape_dc_$(date +%Y%m%d).log

# Museums only
tail -f logs/cron_scrape_dc_museums.log
# or
tail -f logs/cron_scrape_dc_museums_$(date +%Y%m%d).log
```

## Cronjob Schedule Examples

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Weekly (Monday 2 AM) | `0 2 * * 1` | Every Monday at 2:00 AM |
| Weekly (Sunday 3 AM) | `0 3 * * 0` | Every Sunday at 3:00 AM |
| Daily (2 AM) | `0 2 * * *` | Every day at 2:00 AM |
| Twice Weekly (Mon & Thu) | `0 2 * * 1,4` | Monday and Thursday at 2:00 AM |
| Monthly (1st of month) | `0 2 1 * *` | First day of month at 2:00 AM |

## What the Scripts Do

### `cron_scrape_dc.py` (All Venues)
1. **Finds Washington DC** in the database
2. **Gets all active venues** (skips closed venues like Newseum)
3. **Scrapes venues** using:
   - Specialized scrapers for NGA, SAAM, NPG, Asian Art, African Art
   - Generic scraper for other venues
   - Built-in methods for Hirshhorn
4. **Scrapes event sources** (Instagram, websites, etc.)
5. **Saves events** to database (skips duplicates)
6. **Logs results** with statistics

### `cron_scrape_dc_museums.py` (Museums Only)
1. **Finds Washington DC** in the database
2. **Filters to museums only** (by name and venue type keywords)
3. **Scrapes each museum individually** with detailed logging:
   - Specialized scrapers for NGA, SAAM, NPG, Asian Art, African Art, Hirshhorn
   - Generic scraper for other museums
4. **Saves events** to database (skips duplicates)
5. **Logs results** with per-museum statistics

## Configuration

You can modify these settings in the scripts:

**In both scripts:**
- `time_range = 'this_month'` - Change to 'this_week', 'all', etc.
- `max_events_per_venue = 50` - Maximum events per venue
- `max_exhibitions_per_venue = 20` - Maximum exhibitions per venue

**In `cron_scrape_dc_museums.py` only:**
- `is_museum()` function - Modify museum detection keywords if needed

## Troubleshooting

### Script doesn't run
- Check that the path is correct in crontab
- Verify virtual environment path
- Check cron service is running: `sudo service cron status` (Linux) or check System Preferences > Users & Groups > Login Items (macOS)

### Permission errors
- Make sure the script is executable: `chmod +x scripts/cron_scrape_dc.py`
- Check file permissions on the logs directory

### Import errors
- Make sure virtual environment is activated in the cron command
- Verify all dependencies are installed: `pip install -r requirements.txt`

### Database connection errors
- Check that the database is accessible
- Verify `.env` file has correct database credentials
- For Railway deployment, ensure environment variables are set

## For Railway Deployment

If deploying to Railway, you can use Railway's cron jobs feature:

1. Go to Railway project settings
2. Add a new cron job
3. Schedule: `0 2 * * 1` (every Monday at 2 AM)
4. Command: `python scripts/cron_scrape_dc.py`

Or use Railway's scheduled tasks feature in the dashboard.
