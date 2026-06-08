#!/bin/bash
# Compatibility shim — use scripts/cron/run_cron_scrape_protected.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cron/run_cron_scrape_protected.sh" "$@"
