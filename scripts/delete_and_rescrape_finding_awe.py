"""Compatibility shim — canonical path: scripts/cleanup/delete_and_rescrape_finding_awe.py"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.cleanup.delete_and_rescrape_finding_awe import *  # noqa: F403

if __name__ == "__main__":
    import runpy
    runpy.run_path(
        str(Path(__file__).resolve().parent / "cleanup" / "delete_and_rescrape_finding_awe.py"),
        run_name="__main__",
    )
