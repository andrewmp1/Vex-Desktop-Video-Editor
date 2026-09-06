from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from vex_desktop.agent.errors import ProjectError
from vex_desktop.agent.service import AgentService
from vex_desktop.agent.stub import StubBackend
from vex_desktop.exporting import PRESETS, preset_label, preset_suffix, resolve_preset
from vex_desktop.protocol import AgentResult, ProjectSnapshot


def test_resolve_preset_youtube():
    assert resolve_preset("export for youtube") == "youtube_1080p"
    assert resolve_preset("youtube_1080p") == "youtube_1080p"
    assert resolve_preset("tiktok") == "tiktok"


def test_stub_export_writes_file(sample_video, tmp_path):
    service = AgentService(StubBackend())
    loaded = service.handle("load_project", {"video_path": str(sample_video)})
    assert loaded.success
    dest = tmp_path / "clip_youtube_1080p.mp4"
    result = service.handle(
        "export",
        {"preset": "youtube_1080p", "output_path": str(dest)},
    )
    assert result.success
    assert result.exported_path == str(dest)
    assert dest.is_file() and dest.stat().st_size > 0
    assert "Exported to" in result.message


def test_stub_export_via_chat_command(sample_video, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    service = AgentService(StubBackend())
    service.handle("load_project", {"video_path": str(sample_video)})
    result = service.handle("process_command", {"command": "export for youtube"})
    assert result.success
    assert result.exported_path
    assert Path(result.exported_path).is_file()
    assert "export youtube_1080p" in result.snapshot.history


def test_stub_export_without_video_fails():
    service = AgentService(StubBackend())
    with pytest.raises(ProjectError):
        service.handle("export", {"preset": "youtube_1080p"})


@pytest.mark.parametrize("preset", ["tiktok", "podcast_audio"])
def test_stub_export_preset_suffix(sample_video, tmp_path, monkeypatch, preset):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    service = AgentService(StubBackend())
    service.handle("load_project", {"video_path": str(sample_video)})
    result = service.handle("export", {"preset": preset})
    assert result.success
    path = Path(result.exported_path)
    assert path.suffix == preset_suffix(preset)
    assert path.is_file() and path.stat().st_size > 0
    if preset == "podcast_audio":
        assert result.new_video is None
    else:
        assert result.new_video == str(path)


def test_ui_export_from_toolbar(window, qtbot, sample_video, tmp_path, screenshot_dir):
    dest = tmp_path / "ui-export.mp4"
    window.open_source(str(sample_video))
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    window._agent.export("youtube_1080p", str(dest))
    qtbot.waitUntil(lambda: dest.is_file() or "Exported" in window._chat.transcript(), timeout=8000)
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    qtbot.wait(300)
    pixmap = window.grab()
    assert pixmap.save(str(screenshot_dir / "exported-sample.png"), "PNG")
    assert dest.is_file() and dest.stat().st_size > 0
    assert "Exported" in window._chat.transcript()


def test_export_menu_lists_presets(window):
    labels = [action.text() for action in window._export_actions]
    assert labels == [preset_label(preset) for preset in PRESETS]
    assert "TikTok" in labels
    assert "Podcast audio" in labels
    assert "X" in labels


def test_export_without_video_shows_chat_error(window, qtbot):
    window._export_preset("youtube_1080p")
    qtbot.waitUntil(lambda: "Load a video" in window._chat.transcript(), timeout=8000)
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    assert "Load a video" in window._chat.transcript()


def test_failed_result_still_shows_message(window):
    window._on_result(
        AgentResult(
            op="process_command",
            success=False,
            message="0 clips passed QA",
            snapshot=ProjectSnapshot(backend="stub"),
        )
    )
    assert "0 clips passed QA" in window._chat.transcript()


def test_ui_export_tiktok_from_menu(window, qtbot, sample_video, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    window.open_source(str(sample_video))
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    window._export_preset("tiktok")
    qtbot.waitUntil(lambda: "Exported" in window._chat.transcript(), timeout=8000)
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    assert "Exporting TikTok" in window._chat.transcript()


def _probe(path: Path) -> dict[str, str]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height",
            "-of",
            "default=nw=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


@pytest.mark.skipif(
    os.environ.get("VEX_SKIP_CORE_EXPORT") == "1",
    reason="core export skipped by env",
)
def test_core_export_encodes_sample(sample_video, tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.setenv("VEX_AGENT_BACKEND", "core")
    from vex_desktop.agent.core import VexCoreBackend, is_core_available
    from vex_desktop.agent.errors import CoreUnavailable

    if not is_core_available():
        pytest.skip("Vex checkout is not available")
    try:
        backend = VexCoreBackend()
    except CoreUnavailable as exc:
        pytest.skip(str(exc))

    service = AgentService(backend)
    loaded = service.handle("load_project", {"video_path": str(sample_video)})
    assert loaded.success
    dest = tmp_path / "core-youtube.mp4"
    result = service.handle(
        "export",
        {"preset": "youtube_1080p", "output_path": str(dest)},
    )
    assert result.success, result.message
    assert dest.is_file() and dest.stat().st_size > 0
    probe = _probe(dest)
    assert probe.get("codec_name") == "h264"
    assert probe.get("width") == "1920"
    assert probe.get("height") == "1080"
