from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from vex_desktop.agent.errors import AgentError, ProjectError
from vex_desktop.agent.service import AgentService
from vex_desktop.agent.stub import StubBackend
from vex_desktop.bundle import pack_project_dir, pack_working_file, unpack_bundle
from vex_desktop.protocol import OPS, PROTOCOL_VERSION


def test_pack_working_file_round_trip(tmp_path: Path, sample_video: Path):
    dest = tmp_path / "clip.vex"
    pack_working_file(sample_video, dest, project_id="stub-1")
    assert dest.is_file()
    with zipfile.ZipFile(dest) as zf:
        manifest = json.loads(zf.read("vex-bundle.json"))
    assert manifest["format"] == 1
    assert manifest["project_id"] == "stub-1"
    assert manifest["kind"] == "working_file"
    info = unpack_bundle(dest, tmp_path / "projects")
    assert info["project_id"] == "stub-1"
    assert info["kind"] == "working_file"
    loaded = Path(info["load_path"])
    assert loaded.is_file()
    assert loaded.stat().st_size == sample_video.stat().st_size


def test_pack_project_dir_round_trip(tmp_path: Path):
    proj = tmp_path / "src" / "abc"
    proj.mkdir(parents=True)
    (proj / "abc.json").write_text('{"project_id": "abc", "project_name": "Demo"}\n', encoding="utf-8")
    (proj / "clip.mp4").write_bytes(b"not-a-real-mp4")
    dest = tmp_path / "abc.vex"
    pack_project_dir(proj, dest, project_id="abc")
    out_root = tmp_path / "restored"
    info = unpack_bundle(dest, out_root)
    assert info["project_id"] == "abc"
    assert info["kind"] == "project"
    assert info["load_path"] == "abc"
    restored = out_root / "abc"
    assert (restored / "abc.json").is_file()
    assert (restored / "clip.mp4").read_bytes() == b"not-a-real-mp4"


def test_unpack_rejects_missing_file(tmp_path: Path):
    with pytest.raises(AgentError, match="not found"):
        unpack_bundle(tmp_path / "missing.vex", tmp_path)


def _service(tmp_path: Path, monkeypatch) -> AgentService:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_PROJECTS_DIR", str(tmp_path / "vex-projects"))
    return AgentService(StubBackend())


def test_protocol_includes_pack_and_unpack_ops():
    assert PROTOCOL_VERSION == 3
    assert "pack_project" in OPS
    assert "unpack_project" in OPS


def test_pack_without_video_fails(tmp_path: Path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    with pytest.raises((AgentError, ProjectError), match="Load a video"):
        service.handle("pack_project", {"output_path": str(tmp_path / "x.vex")})


def test_pack_and_unpack_via_service(tmp_path: Path, sample_video: Path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    loaded = service.handle("load_project", {"video_path": str(sample_video)})
    assert loaded.success
    dest = tmp_path / "out.vex"
    packed = service.handle("pack_project", {"output_path": str(dest)})
    assert packed.success
    assert dest.is_file()
    assert packed.exported_path == str(dest)
    other = _service(tmp_path, monkeypatch)
    opened = other.handle("unpack_project", {"path": str(dest)})
    assert opened.success
    assert opened.snapshot.working_file
    assert Path(opened.snapshot.working_file).is_file()
    assert Path(opened.snapshot.working_file).stat().st_size == sample_video.stat().st_size


def _isolate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_PROJECTS_DIR", str(tmp_path / "vex-projects"))


def _make_window(qtbot, tmp_path: Path, monkeypatch):
    from vex_desktop.app import create_application
    from vex_desktop.ui.main_window import MainWindow

    _isolate(tmp_path, monkeypatch)
    create_application([])
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


def _action(window, text: str):
    from PySide6.QtGui import QAction

    for action in window.findChildren(QAction):
        if action.text().replace("&", "") == text:
            return action
    raise AssertionError(f"missing action {text!r}")


def _shutdown(qtbot, win) -> None:
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=8000)
    win._timeline.shutdown()
    win._agent.shutdown()


def test_save_and_open_project_file(qtbot, tmp_path, sample_video, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    dest = tmp_path / "bundle.vex"
    win = _make_window(qtbot, tmp_path, monkeypatch)
    win.open_source(str(sample_video))
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=8000)
    qtbot.waitUntil(lambda: win._timeline.thumbnail_count() >= 1, timeout=20000)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(dest), "Vex project"))
    _action(win, "Save Project…").trigger()
    qtbot.waitUntil(lambda: dest.is_file() or "Saved project" in win._chat.transcript(), timeout=8000)
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=8000)
    assert dest.is_file()
    assert "Saved project" in win._chat.transcript()
    _shutdown(qtbot, win)

    other = _make_window(qtbot, tmp_path, monkeypatch)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(dest), "Vex project"))
    _action(other, "Open Project File…").trigger()
    qtbot.waitUntil(lambda: not other._agent.busy, timeout=8000)
    assert other._snapshot.working_file
    assert Path(other._snapshot.working_file).is_file()
    assert "Opened project" in other._chat.transcript()
    _shutdown(qtbot, other)


