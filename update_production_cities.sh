#!/bin/bash
# Script to update production cities directly via API (no deployment needed)

echo "🔄 Updating production cities..."
echo "=================================="

# Step 1: Add State College
echo "📋 Step 1: Adding State College, Pennsylvania..."
RESPONSE=$(curl -s -X POST https://planner.ozayn.com/api/admin/add-city \
  -H "Content-Type: application/json" \
  -d '{"name": "State College", "state": "Pennsylvania", "country": "United States", "timezone": "America/New_York"}')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# Check if it was successful or if it already exists
if echo "$RESPONSE" | grep -q "already exists"; then
    echo "✅ State College already exists in production"
elif echo "$RESPONSE" | grep -q "success.*true"; then
    echo "✅ State College added successfully"
else
    echo "⚠️  Response: $RESPONSE"
fi

# Step 2: Find duplicate Silver Spring entries
echo ""
echo "🔍 Step 2: Finding duplicate Silver Spring entries..."
CITIES_JSON=$(curl -s https://planner.ozayn.com/api/admin/cities)

# Extract Silver Spring entries
SILVER_SPRING_IDS=$(echo "$CITIES_JSON" | python3 << 'PYTHON'
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
if [ ! -z "$SILVER_SPRING_IDS" ] && echo "$SILVER_SPRING_IDS" | grep -q "^[0-9]"; then
    DELETE_ID=$(echo "$SILVER_SPRING_IDS" | tail -1)
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
echo "Checking for State College:"
curl -s https://planner.ozayn.com/api/admin/cities | python3 -m json.tool | grep -A 5 "State College" || echo "State College not found"

echo ""
echo "Checking for Silver Spring duplicates:"
SILVER_COUNT=$(curl -s https://planner.ozayn.com/api/admin/cities | python3 -c "import sys, json; cities = json.load(sys.stdin); print(len([c for c in cities if c['name'] == 'Silver Spring' and c.get('state') == 'Maryland']))" 2>/dev/null || echo "0")
echo "Found $SILVER_COUNT instances of Silver Spring (should be 1)"

echo ""
echo "=================================="
echo "✅ Update complete!"


