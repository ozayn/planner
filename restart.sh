#!/bin/bash
# BULLETPROOF RESTART SCRIPT
# One command to get back to where you left off

echo "🛡️  BULLETPROOF RESTART"
echo "========================"
echo "This will get you back to where you left off!"
echo ""

# Navigate to project directory
cd /Users/oz/Dropbox/2025/planner

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Run the bulletproof startup
echo "🚀 Starting bulletproof system..."
python start.py



