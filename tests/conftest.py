from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("VEX_AGENT_BACKEND", "stub")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")
os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", ",")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SCREENSHOT_DIR = ROOT / "tests" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def screenshot_dir() -> Path:
    return SCREENSHOT_DIR


@pytest.fixture
def window(qtbot, screenshot_dir):
    from vex_desktop.app import create_application
    from vex_desktop.ui.main_window import MainWindow

    create_application([])
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    yield win
    win._agent.shutdown()


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    path = tmp_path / "sample.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=darkblue:s=640x360:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not path.is_file():
        pytest.skip(f"ffmpeg could not create a sample clip: {result.stderr[-400:]}")
    return path
