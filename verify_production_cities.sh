#!/bin/bash
# Simple script to verify production cities

echo "🔍 Checking production cities..."
echo "=================================="

# Check current state
echo "📊 Current cities in production:"
curl -s https://planner.ozayn.com/api/admin/cities | python3 -c "
import sys, json
cities = json.load(sys.stdin)
print(f'Total cities: {len(cities)}')
print()

# Check for State College
state_college = [c for c in cities if 'State College' in c['name']]
if state_college:
    print('✅ State College found:')
    for c in state_college:
        print(f\"   ID {c['id']}: {c['name']}, {c.get('state')}\")
else:
    print('❌ State College NOT found')

print()

# Check for Silver Spring duplicates
silver_spring = [c for c in cities if c['name'] == 'Silver Spring' and c.get('state') == 'Maryland']
if len(silver_spring) == 1:
    print('✅ Silver Spring: Only 1 entry (no duplicates)')
    for c in silver_spring:
        print(f\"   ID {c['id']}: {c['name']}, {c.get('state')}\")
elif len(silver_spring) > 1:
    print(f'❌ Silver Spring: {len(silver_spring)} duplicates found:')
    for c in silver_spring:
        print(f\"   ID {c['id']}: {c['name']}, {c.get('state')} (venues: {c.get('venue_count', 0)})\")
else:
    print('⚠️  Silver Spring not found')
"

echo ""
echo "=================================="


