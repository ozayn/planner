"""Compatibility shim — canonical path: scripts/one_off/embassy_research_helper.py"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.one_off.embassy_research_helper import *  # noqa: F403

if __name__ == "__main__":
    import runpy
    runpy.run_path(
        str(Path(__file__).resolve().parent / "one_off" / "embassy_research_helper.py"),
        run_name="__main__",
    )
