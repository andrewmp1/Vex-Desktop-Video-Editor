#!/usr/bin/env python3
"""Grab offscreen screenshots of the desktop UI (stub backend).

  python scripts/capture_ui.py
  python scripts/capture_ui.py --out /tmp/vex-ui
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("VEX_AGENT_BACKEND", "stub")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(ROOT / "src"))


def _wait(app, pred, timeout_s: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        app.processEvents()
        if pred():
            return True
        time.sleep(0.05)
    return False


def _save(window, dest: Path) -> None:
    pixmap = window.grab()
    if pixmap.isNull() or not pixmap.save(str(dest), "PNG"):
        raise SystemExit(f"Failed to write {dest}")
    print(dest)


def _sample_clip(folder: Path) -> Path | None:
    path = folder / "sample.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=darkblue:s=640x360:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return path if result.returncode == 0 and path.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "tests" / "screenshots")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    from vex_desktop.app import create_application
    from vex_desktop.ui.main_window import MainWindow

    app = create_application([])
    window = MainWindow()
    window.resize(1440, 900)
    window.show()
    app.processEvents()
    time.sleep(0.2)
    app.processEvents()
    _save(window, args.out / "empty.png")

    with tempfile.TemporaryDirectory() as tmp:
        clip = _sample_clip(Path(tmp))
        if clip is not None:
            window.open_source(str(clip))
            _wait(app, lambda: not window._agent.busy and "Loaded" in window._chat.transcript())
            window._chat.submit_text("Trim the first 10 seconds")
            _wait(app, lambda: "Stub:" in window._chat.transcript() or "Load a video" in window._chat.transcript())
            app.processEvents()
            time.sleep(0.3)
            app.processEvents()
            _save(window, args.out / "loaded-sample.png")

    window._agent.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
