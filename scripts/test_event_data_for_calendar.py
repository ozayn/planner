"""Compatibility shim — canonical path: scripts/diagnostics/test_event_data_for_calendar.py"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.diagnostics.test_event_data_for_calendar import *  # noqa: F403

if __name__ == "__main__":
    import runpy
    runpy.run_path(
        str(Path(__file__).resolve().parent / "diagnostics" / "test_event_data_for_calendar.py"),
        run_name="__main__",
    )
