#!/bin/bash
# Compatibility shim — use scripts/admin_tools/security_check.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/admin_tools/security_check.sh" "$@"
