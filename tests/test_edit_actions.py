from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog


def _action(window, text: str) -> QAction:
    for action in window.findChildren(QAction):
        if action.text().replace("&", "") == text:
            return action
    raise AssertionError(f"missing action {text!r}")


def test_add_subtitles_sends_process_command(window, qtbot, sample_video):
    window.open_source(str(sample_video))
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    qtbot.waitUntil(lambda: window._timeline.thumbnail_count() >= 1, timeout=20000)
    _action(window, "Add subtitles").trigger()
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    text = window._chat.transcript()
    assert "You: Add subtitles" in text
    assert "Add subtitles" in window._snapshot.history or "Add subtitles" in text
    assert "Stub:" in text


def test_add_simple_effect_sends_process_command(window, qtbot, sample_video):
    window.open_source(str(sample_video))
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    qtbot.waitUntil(lambda: window._timeline.thumbnail_count() >= 1, timeout=20000)
    _action(window, "Add a simple effect").trigger()
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    text = window._chat.transcript()
    assert "You: Add a subtle zoom effect" in text
    assert "Stub:" in text


def test_insert_broll_includes_picked_path(window, qtbot, sample_video, tmp_path, monkeypatch):
    broll = tmp_path / "broll.mp4"
    broll.write_bytes(sample_video.read_bytes())
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(broll), "Video files"),
    )
    window.open_source(str(sample_video))
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    qtbot.waitUntil(lambda: window._timeline.thumbnail_count() >= 1, timeout=20000)
    _action(window, "Insert B-roll…").trigger()
    qtbot.waitUntil(lambda: not window._agent.busy, timeout=8000)
    text = window._chat.transcript()
    assert f"You: Insert B-roll from {broll}" in text
    assert "Stub:" in text
