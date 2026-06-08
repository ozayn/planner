"""Compatibility shim — canonical path: scripts/scrapers/hirshhorn_scraper.py"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.scrapers.hirshhorn_scraper import *  # noqa: F403

if __name__ == "__main__":
    import runpy
    runpy.run_path(
        str(Path(__file__).resolve().parent / "scrapers" / "hirshhorn_scraper.py"),
        run_name="__main__",
    )
