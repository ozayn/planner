#!/bin/bash

echo "🚀 Setting up GitHub repository..."
echo "=================================="

echo ""
echo "📋 Instructions:"
echo "1. Go to https://github.com/new"
echo "2. Create a new repository named 'planner'"
echo "3. Make it PUBLIC"
echo "4. Add description: 'Event planning web application with venue discovery and management'"
echo "5. DO NOT initialize with README, .gitignore, or license (we already have them)"
echo "6. Click 'Create repository'"
echo ""

echo "⏳ Waiting for you to create the repository..."
echo "Press Enter when you've created the repository on GitHub..."
read

echo ""
echo "🔗 Please provide your GitHub username:"
read GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ GitHub username is required!"
    exit 1
fi

echo ""
echo "🔧 Adding remote origin..."
git remote add origin https://github.com/$GITHUB_USERNAME/planner.git

echo ""
echo "📤 Pushing to GitHub..."
git push -u origin master

echo ""
echo "✅ Repository setup complete!"
echo "🌐 Your repository is now available at:"
echo "   https://github.com/$GITHUB_USERNAME/planner"
echo ""
echo "🎉 You can now share your code with the world!"
