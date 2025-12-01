#!/bin/bash
# Commit venue loading fix and reload data

echo "🔧 Committing venue loading fix..."
cd /Users/oz/Dropbox/2025/planner

git add app.py
git commit -m "Fix venue loading: improve city matching and remove early return

- Improve city name matching (case-insensitive, handle different formats)
- Remove early return that prevented sources from loading
- Add better error logging for debugging
- Include venues_skipped in response"

git push origin master

echo ""
echo "⏳ Waiting 30 seconds for Railway deployment..."
sleep 30

echo ""
echo "🔄 Reloading all data..."
curl -X POST https://planner.ozayn.com/api/admin/load-all-data

echo ""
echo "✅ Done! Check the response above for venues_loaded and venues_skipped counts."


