"""Unit tests for SkillStore, SkillState, compose_preamble, injection, and Skills UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QCheckBox, QFileDialog, QMessageBox

from vex_desktop.agent.service import AgentService
from vex_desktop.agent.stub import StubBackend
from vex_desktop.skills import SkillState, SkillStore, compose_preamble

ROOT = Path(__file__).resolve().parents[1]
TRUST_NOTICE = (
    "Skills are instructions the AI agent will follow while editing. Only add files you trust."
)
EMPTY_HINT = "Drop SKILL.md files here"


def test_frontmatter_and_fallback(tmp_path):
    store = SkillStore(tmp_path)
    (tmp_path / "bare.md").write_text("just body\n", encoding="utf-8")
    (tmp_path / "named").mkdir()
    (tmp_path / "named" / "SKILL.md").write_text(
        "---\nname: Named\ndescription: \"A desc\"\n---\nDo X.\n",
        encoding="utf-8",
    )
    infos = {s.id: s for s in store.scan()}
    assert infos["bare"].name == "bare"
    assert infos["bare"].description == ""
    assert infos["named"].name == "Named"
    assert infos["named"].description == "A desc"


def test_malformed_frontmatter_fallback(tmp_path):
    store = SkillStore(tmp_path)
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text(
        "---\nname: Broken\nno closing fence\nBody only.\n",
        encoding="utf-8",
    )
    infos = {s.id: s for s in store.scan()}
    assert infos["broken"].name == "broken"
    assert infos["broken"].description == ""
    assert "Body only." in store.body(infos["broken"])


def test_compose_preamble_identity_without_skills():
    text, warnings = compose_preamble([], "Trim the first 10 seconds")
    assert text == "Trim the first 10 seconds"
    assert warnings == []


def test_compose_preamble_format():
    text, warnings = compose_preamble(
        [("Named", "Do X.\n")],
        "Trim the first 10 seconds",
    )
    assert warnings == []
    assert text.startswith(
        "Active skills for this session follow. Follow them when relevant to\n"
        "the user's request; otherwise ignore them.\n"
    )
    assert "=== Skill: Named ===\nDo X.\n\n=== End skill: Named ===" in text
    assert text.endswith("User command: Trim the first 10 seconds")


def test_compose_preamble_per_skill_cap():
    body = "A" * 50
    marker = "[skill Big truncated]"
    text, warnings = compose_preamble(
        [("Big", body)],
        "cmd",
        per_cap=40,
        total_cap=16000,
    )
    assert marker in text
    assert "=== Skill: Big ===" in text
    before_marker = text.split(marker, 1)[0]
    # Marker counts inside per_cap, so body slice is shorter than per_cap.
    assert "A" * (40 - len(marker)) in before_marker
    assert "A" * (40 - len(marker) + 1) not in before_marker.split("=== Skill: Big ===\n", 1)[-1]
    assert warnings
    assert any("Big" in w and "truncated" in w.lower() for w in warnings)


def test_compose_preamble_equal_caps_includes_truncated():
    """Regression: per_cap == total_cap must still emit truncated skills."""
    body = "X" * 100
    text, warnings = compose_preamble(
        [("Huge", body)],
        "cmd",
        per_cap=50,
        total_cap=50,
    )
    assert "=== Skill: Huge ===" in text
    assert "[skill Huge truncated]" in text
    assert "User command: cmd" in text
    assert any("truncated" in w.lower() for w in warnings)
    assert not any("skip" in w.lower() for w in warnings)


def test_compose_preamble_total_cap_skips_remaining():
    text, warnings = compose_preamble(
        [("One", "x" * 30), ("Two", "y" * 30), ("Three", "z" * 30)],
        "cmd",
        per_cap=100,
        total_cap=40,
    )
    assert "=== Skill: One ===" in text
    assert "=== Skill: Two ===" not in text
    assert "=== Skill: Three ===" not in text
    assert any("total" in w.lower() or "skip" in w.lower() for w in warnings)
    assert "User command: cmd" in text


def test_scan_sorted_by_name_and_chars(tmp_path):
    store = SkillStore(tmp_path)
    (tmp_path / "zeta.md").write_text("---\nname: Zeta\n---\nZZ\n", encoding="utf-8")
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "SKILL.md").write_text(
        "---\nname: Alpha\ndescription: first\n---\nAA\n",
        encoding="utf-8",
    )
    infos = store.scan()
    assert [s.name for s in infos] == ["Alpha", "Zeta"]
    assert infos[0].chars == len("AA\n")
    assert infos[1].chars == len("ZZ\n")


def test_body_appends_references(tmp_path):
    store = SkillStore(tmp_path)
    skill_dir = tmp_path / "with-refs"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: Refs\n---\nMain body.\n",
        encoding="utf-8",
    )
    refs = skill_dir / "references"
    refs.mkdir()
    (refs / "b.md").write_text("Ref B\n", encoding="utf-8")
    (refs / "a.md").write_text("Ref A\n", encoding="utf-8")
    info = {s.id: s for s in store.scan()}["with-refs"]
    body = store.body(info)
    assert body.startswith("Main body.\n")
    assert "Ref A\n" in body
    assert "Ref B\n" in body
    assert body.index("Ref A") < body.index("Ref B")


def test_import_path_normalizes_bare_md_and_collision(tmp_path):
    store = SkillStore(tmp_path / "skills")
    src = tmp_path / "my-skill.md"
    src.write_text("---\nname: Mine\n---\nBody\n", encoding="utf-8")
    first = store.import_path(str(src))
    assert first.id == "my-skill"
    assert (tmp_path / "skills" / "my-skill" / "SKILL.md").is_file()
    second = store.import_path(str(src))
    assert second.id == "my-skill-2"
    assert (tmp_path / "skills" / "my-skill-2" / "SKILL.md").is_file()


def test_import_folder_and_remove(tmp_path):
    store = SkillStore(tmp_path / "skills")
    src = tmp_path / "folder-skill"
    src.mkdir()
    (src / "SKILL.md").write_text("---\nname: Folder\n---\nHi\n", encoding="utf-8")
    info = store.import_path(str(src))
    assert info.id == "folder-skill"
    assert info.name == "Folder"
    store.remove("folder-skill")
    assert store.scan() == []
    assert not (tmp_path / "skills" / "folder-skill").exists()


def test_skill_state_round_trip(tmp_path):
    state = SkillState(tmp_path)
    assert state.enabled == []
    assert state.seeded is False
    state.enabled = ["a", "b"]
    state.seeded = True
    state.save()
    path = tmp_path / "skills.json"
    assert path.is_file()
    loaded = SkillState(tmp_path)
    assert loaded.enabled == ["a", "b"]
    assert loaded.seeded is True


def _enable_skill_on_disk(tmp_path: Path, monkeypatch, skill_id: str, name: str, body: str) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    store_dir = tmp_path / "share" / "Vex" / "skills"
    store_dir.mkdir(parents=True)
    skill_dir = store_dir / skill_id
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A desc\n---\n{body}",
        encoding="utf-8",
    )


def test_process_command_injects_enabled_skill(sample_video, tmp_path, monkeypatch):
    _enable_skill_on_disk(tmp_path, monkeypatch, "named", "Named", "Do X.\n")
    service = AgentService(StubBackend())
    service.handle("load_project", {"video_path": str(sample_video)})
    enabled = service.handle("set_skills", {"ids": ["named"]})
    assert enabled.success
    result = service.handle("process_command", {"command": "Trim the first 10 seconds"})
    assert result.success
    assert "=== Skill:" in result.message
    assert "User command: Trim the first 10 seconds" in result.message


def test_process_command_omits_skill_when_disabled(sample_video, tmp_path, monkeypatch):
    _enable_skill_on_disk(tmp_path, monkeypatch, "named", "Named", "Do X.\n")
    service = AgentService(StubBackend())
    service.handle("load_project", {"video_path": str(sample_video)})
    service.handle("set_skills", {"ids": ["named"]})
    service.handle("set_skills", {"ids": []})
    result = service.handle("process_command", {"command": "Trim the first 10 seconds"})
    assert result.success
    assert "=== Skill:" not in result.message
    assert "User command:" not in result.message
    assert "Trim the first 10 seconds" in result.message


def test_skill_body_export_word_does_not_steal_edit(sample_video, tmp_path, monkeypatch):
    _enable_skill_on_disk(
        tmp_path,
        monkeypatch,
        "guide",
        "Guide",
        "When relevant, export for youtube using 1080p.\n",
    )
    service = AgentService(StubBackend())
    service.handle("load_project", {"video_path": str(sample_video)})
    service.handle("set_skills", {"ids": ["guide"]})
    result = service.handle("process_command", {"command": "Trim the first 10 seconds"})
    assert result.success
    assert result.exported_path is None
    assert "=== Skill:" in result.message
    assert "User command: Trim the first 10 seconds" in result.message


def _isolate_data(tmp_path: Path, monkeypatch, *, seeded: bool | None = None) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setenv("HOME", str(tmp_path))
    if seeded is not None:
        from vex_desktop.platform_support import data_dir

        root = data_dir()
        root.mkdir(parents=True, exist_ok=True)
        payload = '{"enabled": [], "seeded": true}\n' if seeded else '{"enabled": [], "seeded": false}\n'
        (root / "skills.json").write_text(payload, encoding="utf-8")


def _make_window(qtbot, tmp_path: Path, monkeypatch, *, seeded: bool | None = None):
    from vex_desktop.app import create_application
    from vex_desktop.ui.main_window import MainWindow

    _isolate_data(tmp_path, monkeypatch, seeded=seeded)
    create_application([])
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


def _open_skills_dialog(qtbot, win):
    from vex_desktop.ui.skills_dialog import SkillsDialog

    dialog = SkillsDialog(None, win._agent)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    return dialog


def _shutdown_window(qtbot, win, dialog=None) -> None:
    if dialog is not None:
        dialog._disconnect_client()
        dialog.close()
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    win._timeline.shutdown()
    win._agent.shutdown()


def _skill_ids(dialog) -> list[str]:
    return [row["id"] for row in dialog._skills]


def _checkbox(dialog, skill_id: str) -> QCheckBox:
    box = dialog.findChild(QCheckBox, f"skillCheckbox_{skill_id}")
    assert box is not None, f"missing checkbox for {skill_id}"
    return box


def test_maybe_seed_bundled_skills_copies_examples(tmp_path):
    from vex_desktop.skills import maybe_seed_bundled_skills

    store = SkillStore(tmp_path / "skills")
    state = SkillState(tmp_path)
    maybe_seed_bundled_skills(store, state)
    ids = {info.id for info in store.scan()}
    assert "youtube-metadata" in ids
    assert "tiktok-format" in ids
    assert state.seeded is True
    by_id = {info.id: info for info in store.scan()}
    youtube = store.body(by_id["youtube-metadata"])
    assert "100" in youtube
    assert "hashtag" in youtube.lower()
    tiktok = store.body(by_id["tiktok-format"])
    assert "9:16" in tiktok
    assert "1080" in tiktok
    assert "1920" in tiktok
    assert "hashtag" in tiktok.lower()


def test_maybe_seed_does_not_reseed_after_delete(tmp_path):
    from vex_desktop.skills import maybe_seed_bundled_skills

    store = SkillStore(tmp_path / "skills")
    state = SkillState(tmp_path)
    maybe_seed_bundled_skills(store, state)
    store.remove("youtube-metadata")
    maybe_seed_bundled_skills(store, state)
    ids = {info.id for info in store.scan()}
    assert "youtube-metadata" not in ids
    assert "tiktok-format" in ids
    assert state.seeded is True


def test_agent_service_seeds_on_first_init(tmp_path, monkeypatch):
    _isolate_data(tmp_path, monkeypatch)
    service = AgentService(StubBackend())
    result = service.handle("list_skills", {})
    ids = {row["id"] for row in result.skills}
    assert "youtube-metadata" in ids
    assert "tiktok-format" in ids
    youtube = next(row for row in result.skills if row["id"] == "youtube-metadata")
    assert "body" in youtube
    assert "100" in youtube["body"]


def test_bundled_skill_files_and_spec_datas():
    youtube = ROOT / "assets" / "skills" / "youtube-metadata" / "SKILL.md"
    tiktok = ROOT / "assets" / "skills" / "tiktok-format" / "SKILL.md"
    assert youtube.is_file()
    assert tiktok.is_file()
    yt_text = youtube.read_text(encoding="utf-8")
    tk_text = tiktok.read_text(encoding="utf-8")
    assert "100" in yt_text
    assert "hashtag" in yt_text.lower()
    assert "9:16" in tk_text
    assert "1080" in tk_text and "1920" in tk_text
    spec = (ROOT / "vex.spec").read_text(encoding="utf-8")
    assert "assets" in spec and "skills" in spec
    assert 'ROOT / "assets" / "skills"' in spec


def test_skills_dialog_opens_from_toolbar(qtbot, tmp_path, monkeypatch):
    from vex_desktop.ui.skills_dialog import SkillsDialog

    win = _make_window(qtbot, tmp_path, monkeypatch)
    labels = [action.text().replace("&", "") for action in win.findChildren(QAction)]
    assert "Skills" in labels
    assert "Skills…" in labels or "Skills..." in labels
    action = next(a for a in win.findChildren(QAction) if a.text().replace("&", "") == "Skills")
    titles: list[str] = []

    def fake_exec(self) -> int:
        titles.append(self.windowTitle())
        qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
        self._disconnect_client()
        return int(SkillsDialog.DialogCode.Rejected)

    monkeypatch.setattr(SkillsDialog, "exec", fake_exec)
    action.trigger()
    assert titles == ["Skills"]
    _shutdown_window(qtbot, win)


def test_skills_dialog_loads_catalog_after_agent_idle(qtbot, tmp_path, monkeypatch):
    from vex_desktop.ui.skills_dialog import SkillsDialog

    win = _make_window(qtbot, tmp_path, monkeypatch)
    win._agent._set_busy(True)
    dialog = SkillsDialog(None, win._agent)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    assert win._agent.busy
    assert dialog._list.count() == 0
    win._agent._set_busy(False)
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    qtbot.waitUntil(lambda: dialog._list.count() >= 1, timeout=5000)
    ids = set(_skill_ids(dialog))
    assert "youtube-metadata" in ids
    assert "tiktok-format" in ids
    _shutdown_window(qtbot, win, dialog)


def test_skills_checkbox_disabled_until_preview_selected(qtbot, tmp_path, monkeypatch):
    win = _make_window(qtbot, tmp_path, monkeypatch)
    dialog = _open_skills_dialog(qtbot, win)
    qtbot.waitUntil(lambda: dialog._list.count() >= 1, timeout=5000)
    assert TRUST_NOTICE in dialog._notice.text()
    skill_id = _skill_ids(dialog)[0]
    box = _checkbox(dialog, skill_id)
    assert not box.isEnabled()
    dialog._list.setCurrentRow(0)
    assert box.isEnabled()
    preview = dialog._preview.toPlainText()
    assert preview
    assert skill_id.replace("-", " ").split()[0].lower() in preview.lower() or "hashtag" in preview.lower()
    _shutdown_window(qtbot, win, dialog)


def test_skills_toggle_calls_set_skills(qtbot, tmp_path, monkeypatch):
    win = _make_window(qtbot, tmp_path, monkeypatch)
    calls: list[list[str]] = []
    original = win._agent.set_skills

    def wrapped(ids: list[str]) -> None:
        calls.append(list(ids))
        original(ids)

    monkeypatch.setattr(win._agent, "set_skills", wrapped)
    dialog = _open_skills_dialog(qtbot, win)
    qtbot.waitUntil(lambda: dialog._list.count() >= 1, timeout=5000)
    skill_id = _skill_ids(dialog)[0]
    dialog._list.setCurrentRow(0)
    box = _checkbox(dialog, skill_id)
    assert box.isEnabled()
    box.setChecked(True)
    qtbot.waitUntil(lambda: bool(calls), timeout=5000)
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    assert skill_id in calls[-1]
    _shutdown_window(qtbot, win, dialog)


def test_skills_empty_state_hint(qtbot, tmp_path, monkeypatch):
    win = _make_window(qtbot, tmp_path, monkeypatch, seeded=True)
    dialog = _open_skills_dialog(qtbot, win)
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    assert dialog._list.count() == 0
    assert dialog._empty.isVisible()
    assert EMPTY_HINT in dialog._empty.text()
    _shutdown_window(qtbot, win, dialog)


def test_skills_import_via_file_picker(qtbot, tmp_path, monkeypatch):
    src = tmp_path / "custom-voice.md"
    src.write_text("---\nname: Custom voice\ndescription: Brand voice.\n---\nSay it this way.\n", encoding="utf-8")
    win = _make_window(qtbot, tmp_path, monkeypatch, seeded=True)
    dialog = _open_skills_dialog(qtbot, win)
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(src), "Skill files (*.md)"),
    )
    dialog._add_btn.click()
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    qtbot.waitUntil(lambda: "custom-voice" in _skill_ids(dialog), timeout=5000)
    assert not dialog._empty.isVisible()
    _shutdown_window(qtbot, win, dialog)


def test_skills_remove_with_confirmation(qtbot, tmp_path, monkeypatch):
    win = _make_window(qtbot, tmp_path, monkeypatch)
    dialog = _open_skills_dialog(qtbot, win)
    qtbot.waitUntil(lambda: dialog._list.count() >= 1, timeout=5000)
    skill_id = _skill_ids(dialog)[0]
    dialog._list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    dialog._remove_btn.click()
    qtbot.waitUntil(lambda: not win._agent.busy, timeout=5000)
    qtbot.waitUntil(lambda: skill_id not in _skill_ids(dialog), timeout=5000)
    _shutdown_window(qtbot, win, dialog)
