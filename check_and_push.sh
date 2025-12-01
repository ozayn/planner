#!/bin/bash
# Comprehensive script to check git status and push changes

echo "🔍 Checking Git Status..."
echo "=================================="

# Check if we're in a git repo
if [ ! -d .git ]; then
    echo "❌ Not a git repository!"
    exit 1
fi

# Show current branch
echo "📍 Current branch:"
git branch --show-current

echo ""
echo "📊 Files that have been modified:"
git status --short

echo ""
echo "📦 Files staged for commit:"
git diff --cached --name-only

echo ""
echo "📝 Recent commits (last 5):"
git log --oneline -5

echo ""
echo "🔄 Commits ahead of origin:"
git log origin/master..HEAD --oneline 2>/dev/null || echo "No commits ahead (or origin/master doesn't exist)"

echo ""
echo "=================================="
echo ""

# Check what needs to be done
UNCOMMITTED=$(git status --porcelain | grep -v "^??" | wc -l | tr -d ' ')
UNPUSHED=$(git log origin/master..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')

if [ "$UNCOMMITTED" -gt 0 ]; then
    echo "⚠️  You have $UNCOMMITTED uncommitted file(s)"
    echo ""
    read -p "Do you want to stage and commit all changes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Staging files..."
        git add data/cities.json
        git add scripts/check_duplicates.py
        git add scripts/data_integrity_validator.py
        git add scripts/pre_commit_data_check.py
        git add docs/MISTAKE_PREVENTION_CHECKLIST.md
        git add docs/QUICK_REFERENCE.md
        
        echo "💾 Committing..."
        git commit -m "Add State College PA, remove duplicate city, and implement duplicate checker

- Add State College, Pennsylvania to cities (ID 26)
- Remove duplicate Silver Spring entry (ID 25)
- Create scripts/check_duplicates.py for checking duplicates in cities, venues, and events
- Integrate duplicate checking into data_integrity_validator.py and pre_commit_data_check.py
- Update documentation to require duplicate checks before data changes
- Update cities.json metadata and total count"
        
        echo "✅ Committed!"
        UNPUSHED=$(git log origin/master..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')
    fi
fi

if [ "$UNPUSHED" -gt 0 ]; then
    echo ""
    echo "📤 You have $UNPUSHED commit(s) ready to push"
    echo ""
    read -p "Do you want to push to GitHub? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Pushing to GitHub..."
        git push origin master
        if [ $? -eq 0 ]; then
            echo "✅ Successfully pushed to GitHub!"
        else
            echo "❌ Push failed. Check your git remote and permissions."
        fi
    fi
else
    echo "✅ Everything is up to date with GitHub!"
fi

echo ""
echo "=================================="
echo "✅ Done!"


