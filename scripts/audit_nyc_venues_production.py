"""Compatibility shim — canonical path: scripts/diagnostics/audit_nyc_venues_production.py"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.diagnostics.audit_nyc_venues_production import *  # noqa: F403

if __name__ == "__main__":
    import runpy
    runpy.run_path(
        str(Path(__file__).resolve().parent / "diagnostics" / "audit_nyc_venues_production.py"),
        run_name="__main__",
    )
