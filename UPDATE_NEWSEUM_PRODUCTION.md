# Update Newseum Closure Status in Production

## To Update Production Database:

### Option 1: Run Update Script (Easiest)
```bash
python scripts/update_newseum_production.py
```

This script will:
- Find Newseum in production database
- Update it to mark as permanently closed
- Set closure_status and opening_hours

### Option 2: Manual Update via Admin
1. Go to https://planner.ozayn.com/admin
2. Find Newseum in the venues list
3. Edit it and set:
   - Opening hours: "Permanently closed"
   - Additional info: `{"closure_status": "closed", "closure_reason": "Newseum permanently closed in December 2019.", "last_updated": "2025-12-15T..."}`

### Option 3: Use API Directly
```bash
# First, get Newseum ID
curl https://planner.ozayn.com/api/admin/venues | grep -i newseum

# Then update it (replace VENUE_ID with actual ID)
curl -X PUT https://planner.ozayn.com/api/admin/venues/VENUE_ID \
  -H "Content-Type: application/json" \
  -d '{
    "opening_hours": "Permanently closed",
    "additional_info": "{\"closure_status\": \"closed\", \"closure_reason\": \"Newseum permanently closed in December 2019.\"}"
  }'
```

## Verify:
Check that Newseum shows as closed in production:
```bash
curl https://planner.ozayn.com/api/admin/venues | grep -i newseum -A 10
```

## Changes:
- `opening_hours`: "Permanently closed"
- `closure_status`: "closed"
- `closure_reason`: "Newseum permanently closed in December 2019."
