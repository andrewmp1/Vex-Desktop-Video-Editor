"""Still frames for the visual timeline. Uses FFmpeg, not the agent."""

from __future__ import annotations

import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtGui import QImage

from vex_desktop.platform_support import ffmpeg_path, ffprobe_path

THUMB_COUNT = 8
THUMB_WIDTH = 128
_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def video_duration_ms(path: str | Path) -> int | None:
    probed = _ffprobe_duration_ms(path)
    if probed is not None:
        return probed
    return _ffmpeg_duration_ms(path)


def parse_ffmpeg_duration(text: str) -> int | None:
    match = _DURATION_RE.search(text or "")
    if not match:
        return None
    hours, minutes, seconds = int(match.group(1)), int(match.group(2)), float(match.group(3))
    return int((hours * 3600 + minutes * 60 + seconds) * 1000)


def extract_thumbnails(
    path: str | Path,
    *,
    count: int = THUMB_COUNT,
    width: int = THUMB_WIDTH,
    cancel: threading.Event | None = None,
) -> list[tuple[int, QImage]]:
    source = Path(path)
    if not source.is_file() or source.suffix.lower() in _AUDIO_SUFFIXES:
        return []
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return []
    duration = video_duration_ms(source) or 0
    n = count if duration >= 3000 else min(count, 4)
    stamps = _sample_times_ms(duration, n)
    frames: list[tuple[int, QImage]] = []
    with tempfile.TemporaryDirectory(prefix="vex-thumbs-") as raw_dir:
        folder = Path(raw_dir)
        for index, ms in enumerate(stamps):
            if cancel is not None and cancel.is_set():
                break
            dest = folder / f"frame-{index:02d}.png"
            if not _grab_frame(ffmpeg, source, ms, dest, width, cancel):
                continue
            image = QImage(str(dest))
            if image.isNull():
                continue
            frames.append((ms, image.copy()))
    return frames


def _ffprobe_duration_ms(path: str | Path) -> int | None:
    probe = ffprobe_path()
    if not probe:
        return None
    try:
        result = subprocess.run(
            [
                probe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    raw = (result.stdout or "").strip().splitlines()
    if not raw:
        return None
    try:
        seconds = float(raw[0])
    except ValueError:
        return None
    if seconds < 0:
        return None
    return int(seconds * 1000)


def _ffmpeg_duration_ms(path: str | Path) -> int | None:
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return None
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostdin", "-i", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parse_ffmpeg_duration(result.stderr or "")


def _sample_times_ms(duration_ms: int, count: int) -> list[int]:
    if count <= 1 or duration_ms <= 0:
        return [0]
    n = max(count, 1)
    return [int(duration_ms * (i + 0.5) / n) for i in range(n)]


def _grab_frame(
    ffmpeg: str,
    source: Path,
    ms: int,
    dest: Path,
    width: int,
    cancel: threading.Event | None,
) -> bool:
    seconds = max(ms, 0) / 1000.0
    try:
        proc = subprocess.Popen(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-ss",
                f"{seconds:.3f}",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-vf",
                f"scale={width}:-2",
                "-an",
                str(dest),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    deadline = time.monotonic() + 20
    try:
        while proc.poll() is None:
            if cancel is not None and cancel.is_set() or time.monotonic() > deadline:
                proc.kill()
                proc.wait(timeout=5)
                return False
            try:
                proc.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                continue
    except (OSError, subprocess.TimeoutExpired):
        proc.kill()
        return False
    return proc.returncode == 0 and dest.is_file() and dest.stat().st_size > 0
