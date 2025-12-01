#!/bin/bash
# Update production database with city changes

echo "🔄 Updating production database..."
echo "=================================="

# Step 1: Add State College
echo "📋 Step 1: Adding State College, Pennsylvania..."
RESPONSE=$(curl -s -X POST https://planner.ozayn.com/api/admin/add-city \
  -H "Content-Type: application/json" \
  -d '{"name": "State College", "state": "Pennsylvania", "country": "United States", "timezone": "America/New_York"}')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

if echo "$RESPONSE" | grep -q "already exists"; then
    echo "✅ State College already exists in production"
elif echo "$RESPONSE" | grep -q '"success".*true\|"city_id"'; then
    echo "✅ State College added successfully"
else
    echo "⚠️  Response: $RESPONSE"
fi

# Step 2: Find duplicate Silver Spring entries
echo ""
echo "🔍 Step 2: Finding duplicate Silver Spring entries..."
CITIES_JSON=$(curl -s https://planner.ozayn.com/api/admin/cities)

# Extract Silver Spring entries and find the one to delete
DELETE_ID=$(echo "$CITIES_JSON" | python3 << 'PYTHON'
import sys, json
cities = json.load(sys.stdin)
silver_springs = [c for c in cities if c['name'] == 'Silver Spring' and c.get('state') == 'Maryland']
if len(silver_springs) > 1:
    print("Found duplicate Silver Spring entries:")
    for city in silver_springs:
        print(f"  ID {city['id']}: venues={city.get('venue_count', 0)}, events={city.get('event_count', 0)}")
    # Find the one with fewer venues/events (or first one if equal)
    to_delete = min(silver_springs, key=lambda c: (c.get('venue_count', 0), c.get('event_count', 0)))
    print(f"\nWill delete ID {to_delete['id']} (has fewer venues/events)")
    print(to_delete['id'])
else:
    print("No duplicates found")
PYTHON
)

# Step 3: Delete duplicate if found
if [ ! -z "$DELETE_ID" ] && echo "$DELETE_ID" | grep -q "^[0-9]"; then
    echo ""
    echo "🗑️  Step 3: Deleting duplicate Silver Spring (ID: $DELETE_ID)..."
    DELETE_RESPONSE=$(curl -s -X DELETE https://planner.ozayn.com/api/admin/cities/$DELETE_ID)
    echo "$DELETE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DELETE_RESPONSE"
    
    if echo "$DELETE_RESPONSE" | grep -q "deleted successfully\|Item deleted"; then
        echo "✅ Duplicate deleted successfully"
    else
        echo "⚠️  Response: $DELETE_RESPONSE"
    fi
else
    echo ""
    echo "✅ No duplicates to delete"
fi

# Step 4: Verify final state
echo ""
echo "✅ Step 4: Verifying final state..."
echo ""
echo "Checking for State College:"
STATE_COLLEGE=$(curl -s https://planner.ozayn.com/api/admin/cities | python3 -c "import sys, json; cities = json.load(sys.stdin); sc = [c for c in cities if 'State College' in c['name']]; print(f'Found {len(sc)} State College entries:'); [print(f\"  ID {c['id']}: {c['name']}, {c.get('state')}\") for c in sc]" 2>/dev/null)
if [ -z "$STATE_COLLEGE" ]; then
    echo "  ❌ State College not found"
else
    echo "$STATE_COLLEGE"
fi

echo ""
echo "Checking for Silver Spring duplicates:"
SILVER_COUNT=$(curl -s https://planner.ozayn.com/api/admin/cities | python3 -c "import sys, json; cities = json.load(sys.stdin); ss = [c for c in cities if c['name'] == 'Silver Spring' and c.get('state') == 'Maryland']; print(len(ss))" 2>/dev/null || echo "0")
if [ "$SILVER_COUNT" = "1" ]; then
    echo "  ✅ Found 1 Silver Spring (no duplicates)"
elif [ "$SILVER_COUNT" = "0" ]; then
    echo "  ⚠️  No Silver Spring found"
else
    echo "  ❌ Found $SILVER_COUNT Silver Spring entries (should be 1)"
fi

echo ""
echo "=================================="
echo "✅ Update complete!"


