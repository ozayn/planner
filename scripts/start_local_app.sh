#!/bin/bash
# Start the Flask planner app locally (default port 5001 — see app.py).
# Usage: ./scripts/start_local_app.sh
#        or: bash scripts/start_local_app.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [ ! -f "venv/bin/activate" ]; then
    echo "Error: venv not found at $PROJECT_ROOT/venv/bin/activate"
    exit 1
fi

# shellcheck source=/dev/null
source venv/bin/activate

echo "Starting planner at http://localhost:5001 (admin: http://localhost:5001/admin)"
echo "Press Ctrl+C to stop."
exec python app.py
