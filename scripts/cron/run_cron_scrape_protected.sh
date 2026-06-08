#!/bin/bash
# Wrapper for protected/troublesome scrapers cron (Asian Art, NPG, Hirshhorn)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found at venv/bin/activate"
    exit 1
fi

python scripts/cron/cron_run_protected_scrapers.py
exit $?
