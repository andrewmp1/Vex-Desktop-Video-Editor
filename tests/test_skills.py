"""Unit tests for SkillStore, SkillState, and compose_preamble."""

from __future__ import annotations

from pathlib import Path

from vex_desktop.skills import SkillState, SkillStore, compose_preamble


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
