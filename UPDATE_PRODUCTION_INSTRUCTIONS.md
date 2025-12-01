# Update Production Cities - Instructions

## Current Status
- ✅ Local database: State College added, duplicate removed
- ⏳ Production: Needs to be updated

## Quick Update (No Deployment Needed)

### Step 1: Add State College to Production
```bash
curl -X POST https://planner.ozayn.com/api/admin/add-city \
  -H "Content-Type: application/json" \
  -d '{"name": "State College", "state": "Pennsylvania", "country": "United States", "timezone": "America/New_York"}'
```

### Step 2: Check for Duplicate Silver Spring
```bash
curl -s https://planner.ozayn.com/api/admin/cities | python3 -m json.tool | grep -B 2 -A 5 "Silver Spring"
```

### Step 3: Delete Duplicate (if found)
Replace `<ID>` with the duplicate city ID (the one with fewer venues/events):
```bash
curl -X DELETE https://planner.ozayn.com/api/admin/cities/<ID>
```

### Step 4: Verify Changes
```bash
./verify_production_cities.sh
```

Or manually:
```bash
# Check for State College
curl -s https://planner.ozayn.com/api/admin/cities | python3 -m json.tool | grep -A 5 "State College"

# Check for duplicates
curl -s https://planner.ozayn.com/api/admin/cities | python3 -m json.tool | grep -i "silver spring"
```

## Alternative: Use the Automated Script
```bash
chmod +x update_production_cities.sh
./update_production_cities.sh
```

## After Updating
Once production is updated, you can:
1. Push changes to GitHub (for future deployments)
2. The production database will now match local changes


