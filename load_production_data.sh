#!/bin/bash
# Load all data into production database via API

echo "🔄 Loading all data into production database..."
echo "=================================="

echo "📋 Calling /api/admin/load-all-data endpoint..."
RESPONSE=$(curl -s -X POST https://planner.ozayn.com/api/admin/load-all-data \
  -H "Content-Type: application/json")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

echo ""
echo "✅ Data loading initiated!"
echo ""
echo "📊 Verifying data was loaded..."
sleep 3

# Check counts
echo "Checking database counts:"
curl -s https://planner.ozayn.com/api/admin/stats | python3 -m json.tool

echo ""
echo "=================================="
echo "✅ Done!"


