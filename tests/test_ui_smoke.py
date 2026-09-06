from __future__ import annotations

from pathlib import Path


def _grab(window, screenshot_dir: Path, name: str) -> Path:
    path = screenshot_dir / name
    pixmap = window.grab()
    assert not pixmap.isNull()
    assert pixmap.save(str(path), "PNG")
    assert path.is_file() and path.stat().st_size > 0
    return path


def test_empty_window_screenshot(window, qtbot, screenshot_dir):
    qtbot.wait(200)
    path = _grab(window, screenshot_dir, "empty.png")
    assert path.name == "empty.png"
    assert "Vex" in window.windowTitle()
    text = window._chat.transcript()
    assert "Open a video" in text


def test_stub_chat_roundtrip(window, qtbot):
    window._chat.submit_text("Trim the first 10 seconds")
    qtbot.waitUntil(
        lambda: "Stub:" in window._chat.transcript() or "Load a video" in window._chat.transcript(),
        timeout=8000,
    )
    text = window._chat.transcript()
    assert "You: Trim the first 10 seconds" in text
    assert "Load a video" in text or "Stub:" in text


def test_open_sample_video_updates_preview(window, qtbot, sample_video, screenshot_dir):
    window.open_source(str(sample_video))
    qtbot.waitUntil(
        lambda: "Loaded" in window._chat.transcript() or "Opening" in window._chat.transcript(),
        timeout=8000,
    )
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    qtbot.wait(400)
    _grab(window, screenshot_dir, "loaded-sample.png")
    assert window._preview.current_path == str(sample_video)
    assert sample_video.name in window._chat.transcript()
