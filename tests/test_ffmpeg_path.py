from __future__ import annotations

import sys
from pathlib import Path


def test_ffmpeg_path_prefers_sibling_of_executable(tmp_path, monkeypatch):
    from vex_desktop.platform_support import ffmpeg_path

    fake_app = tmp_path / "Vex"
    fake_app.write_bytes(b"")
    bundled = tmp_path / "ffmpeg"
    bundled.write_bytes(b"")
    bundled.chmod(0o755)

    monkeypatch.setattr(sys, "executable", str(fake_app))
    monkeypatch.delenv("FFMPEG_BINARY", raising=False)
    monkeypatch.delenv("IMAGEIO_FFMPEG_EXE", raising=False)
    monkeypatch.delenv("FFMPEG_PATH", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert ffmpeg_path() == str(bundled)


def test_spec_collects_ffmpeg():
    spec = Path(__file__).resolve().parents[1] / "vex.spec"
    text = spec.read_text(encoding="utf-8")
    assert "BINARIES" in text
    assert "vendor" in text
    assert "shutil.which" in text
