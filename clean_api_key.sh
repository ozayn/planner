#!/bin/bash
# Script to clean API key from git history

echo "🧹 Cleaning API key from git history..."

# Create a script that will be used by filter-branch
cat > /tmp/clean_api_key.sh << 'EOF'
#!/bin/bash
if [ -f data/venues.json ]; then
    sed -i.bak 's/key=AIzaSyBJ0v90GfvkWSIjzceNk2uPbwdmlrDxkYw/key=YOUR_GOOGLE_MAPS_API_KEY/g' data/venues.json
    rm -f data/venues.json.bak
fi
EOF

chmod +x /tmp/clean_api_key.sh

# Run filter-branch
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --force --tree-filter '/tmp/clean_api_key.sh' --prune-empty --tag-name-filter cat -- --all

# Clean up
rm -f /tmp/clean_api_key.sh
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "✅ API key cleaned from git history"
