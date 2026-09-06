"""Optional checkout launcher. Prefer `vex-desktop` or `python -m vex_desktop` after `pip install -e ".[dev]"`."""

from __future__ import annotations

import sys
from pathlib import Path

src = Path(__file__).resolve().parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from vex_desktop.app import run

if __name__ == "__main__":
    raise SystemExit(run())
