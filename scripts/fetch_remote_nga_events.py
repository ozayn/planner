"""Compatibility shim — canonical path: scripts/admin_tools/fetch_remote_nga_events.py"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.admin_tools.fetch_remote_nga_events import *  # noqa: F403

if __name__ == "__main__":
    import runpy
    runpy.run_path(
        str(Path(__file__).resolve().parent / "admin_tools" / "fetch_remote_nga_events.py"),
        run_name="__main__",
    )
