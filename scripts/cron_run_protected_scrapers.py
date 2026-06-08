#!/usr/bin/env python3
"""
Protected cron entrypoint: Cloudflare / 403 / proxy-sensitive Smithsonian scrapers.

Runs Asian Art, NPG, and Hirshhorn in isolation from the stable cron.
See scripts/cron_bucket_config.py to add or reclassify scrapers.

Usage:
    source venv/bin/activate && python scripts/cron_run_protected_scrapers.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.cron_bucket_config import BUCKET_PROTECTED
from scripts.cron_run_scheduled_scrapers import run_scheduled_scrapers

if __name__ == '__main__':
    sys.exit(run_scheduled_scrapers(BUCKET_PROTECTED))
