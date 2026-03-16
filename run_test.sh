#!/bin/bash
# Run tests with the project venv (bypasses python/python3 aliases)
cd "$(dirname "$0")"
./venv/bin/python "$@"
