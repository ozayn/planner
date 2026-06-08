"""Compatibility shim — canonical path: scripts/diagnostics/test_event_api_response.py"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.diagnostics.test_event_api_response import *  # noqa: F403

if __name__ == "__main__":
    import runpy
    runpy.run_path(
        str(Path(__file__).resolve().parent / "diagnostics" / "test_event_api_response.py"),
        run_name="__main__",
    )
