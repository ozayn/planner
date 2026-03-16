#!/bin/bash
# Wrapper script for running scheduled scrapers cronjob
# This makes it easier to run from cron and ensures proper environment setup

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found at venv/bin/activate"
    exit 1
fi

# Run the scheduled scrapers script
python scripts/cron_run_scheduled_scrapers.py

# Exit with the same code as the Python script
exit $?
