#!/bin/bash

# Quick restart script for local development
# Usage: ./restart_local.sh

echo "🚀 Restarting local planner application..."
echo "=========================================="

# Navigate to project directory
cd "$(dirname "$0")"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Start the application using the bulletproof startup script
echo "🚀 Starting Flask application..."
echo "📱 Will be available at: http://localhost:5001"
echo "🔧 Admin page: http://localhost:5001/admin"
echo "=========================================="
echo "Press Ctrl+C to stop the server"
echo "=========================================="

python start.py


