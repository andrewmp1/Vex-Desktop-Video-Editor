# Skills System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Users add, preview, and toggle local Agent Skills that inject into `process_command` only.

**Architecture:** Qt-free `SkillStore` / `SkillState` / `compose_preamble` in `vex_desktop.skills`. Composition happens in `AgentService.handle("process_command")` before any backend. New protocol ops (`list_skills`, `import_skill`, `remove_skill`, `set_skills`). UI talks only to `AgentClient`.

**Tech Stack:** PySide6, existing `data_dir()`, pytest / pytest-qt. No new dependencies.

**Spec:** [docs/superpowers/specs/2026-09-06-skills-system-design.md](../specs/2026-09-06-skills-system-design.md)

## Global Constraints

- Wrapper-only. No changes to the pinned Vex tree.
- UI imports `AgentClient` + protocol only.
- Injection only on `process_command`. Export / undo / redo / load unchanged.
- Local files only; preview-before-enable; persist enabled set in `data_dir()/skills.json`.
- `PROTOCOL_VERSION = 2`.
- Offscreen tests: `QT_QPA_PLATFORM=offscreen VEX_AGENT_BACKEND=stub pytest`.

## File map

- Create: `src/vex_desktop/skills.py`
- Create: `src/vex_desktop/ui/skills_dialog.py`
- Create: `assets/skills/youtube-metadata/SKILL.md`, `assets/skills/tiktok-format/SKILL.md`
- Create: `tests/test_skills.py`, `tests/test_skills_protocol.py`
- Modify: `protocol.py`, `agent/service.py`, `agent/qt.py`, `ui/main_window.py`, `vex.spec`, docs listed in spec §8

---

### Task 1: SkillStore + frontmatter + compose_preamble

**Files:**
- Create: `src/vex_desktop/skills.py`
- Test: `tests/test_skills.py`

**Produces:**
- `SkillInfo(id, name, description, path, chars)`
- `SkillStore.scan() -> list[SkillInfo]`
- `SkillStore.import_path(src) -> SkillInfo`
- `SkillStore.remove(id)`
- `SkillStore.body(skill) -> str`
- `compose_preamble(skills, command, per_cap=16000, total_cap=16000) -> tuple[str, list[str]]`
- `SkillState` with `enabled: list[str]`, `seeded: bool`, `skills.json`

- [ ] **Step 1: Write failing tests**

```python
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
    assert infos["named"].name == "Named"
    assert infos["named"].description == "A desc"

def test_compose_preamble_identity_without_skills():
    text, warnings = compose_preamble([], "Trim the first 10 seconds")
    assert text == "Trim the first 10 seconds"
    assert warnings == []
```

- [ ] **Step 2:** `pytest tests/test_skills.py::test_compose_preamble_identity_without_skills -v` fails (import error).
- [ ] **Step 3:** Implement parser, store, compose format from spec §4.1. No-skills path returns `(command, [])` byte-for-byte.
- [ ] **Step 4:** Tests pass. Caps: truncate with `[skill {name} truncated]`; skip remainder at total cap; both add warnings.
- [ ] **Step 5:** Commit `feat: add SkillStore and compose_preamble`

---

### Task 2: Protocol v2 + AgentService ops + injection

**Files:**
- Modify: `src/vex_desktop/protocol.py` (`PROTOCOL_VERSION = 2`, ops, `AgentResult.skills`)
- Modify: `src/vex_desktop/agent/service.py` (ops + compose before `process_command`)
- Modify: `src/vex_desktop/agent/qt.py` (`list_skills`, `import_skill`, `remove_skill`, `set_skills`)
- Test: `tests/test_skills.py`, `tests/test_export.py` (export chat still routes)

**Produces:**
- `AgentClient.set_skills(ids: list[str])` etc., same QThread pattern as `set_config`
- `process_command` payload still `{command}`; service prepends preamble internally

- [ ] **Step 1: Failing tests**

```python
def test_process_command_injects_enabled_skill(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    store_dir = tmp_path / "share" / "Vex" / "skills"  # match data_dir()
    # write a skill, enable it, handle process_command
    result = service.handle("process_command", {"command": "Trim the first 10 seconds"})
    assert "=== Skill:" in result.message
    assert "User command: Trim the first 10 seconds" in result.message

def test_export_chat_still_resolves_youtube(sample_video, tmp_path, monkeypatch):
    # enable a skill then "export for youtube" still exports
```

- [ ] **Step 2:** Run tests — fail on unknown ops / no injection.
- [ ] **Step 3:** Add ops to `OPS`. `AgentService` owns `SkillStore`/`SkillState` under `data_dir()/skills`. `process_command` uses `compose_preamble` then `backend.process_command(composed)`. Stub echoes composed text. Export path still uses `looks_like_export` on the **user** command (not the preamble) — important: match export **before** compose, or strip to the `User command:` tail. Spec: regexes are `\b`-anchored; test that enabled skills do not break `export for youtube`.
- [ ] **Step 4:** pytest green for skills + existing `test_export.py`.
- [ ] **Step 5:** Commit `feat: protocol v2 skills ops and process_command injection`

---

### Task 3: Skills dialog + seed examples

**Files:**
- Create: `src/vex_desktop/ui/skills_dialog.py`
- Create: `assets/skills/youtube-metadata/SKILL.md`, `assets/skills/tiktok-format/SKILL.md`
- Modify: `src/vex_desktop/ui/main_window.py` (Skills action)
- Modify: `vex.spec` datas for `assets/skills`
- Test: `tests/test_skills.py` UI cases + screenshot in `scripts/capture_ui.py`

**Produces:** Dialog as spec §4.3. Checkbox disabled until preview viewed this session. Trust notice always visible.

- [ ] **Step 1:** pytest-qt: open dialog, checkbox disabled, select row → checkbox enabled, toggle calls `set_skills`.
- [ ] **Step 2:** Fail until dialog exists.
- [ ] **Step 3:** Implement dialog; seed on first `SkillStore` init from packaged examples; `seeded: true` prevents reseed.
- [ ] **Step 4:** UI tests + `scripts/capture_ui.py` writes `tests/screenshots/` skills shot if capture script is extended.
- [ ] **Step 5:** Commit `feat: Skills dialog with preview-before-enable`

---

### Task 4: Docs

**Files:** `docs/API_WRAPPER_SPEC.md`, `docs/ARCHITECTURE.md`, `README.md`, `docs/project-plan.md`, `docs/user-guide.md`

- [ ] Document PROTOCOL_VERSION 2, four ops, data dir location, trust model.
- [ ] Commit `docs: skills protocol and user-facing notes`

**Verify:** `QT_QPA_PLATFORM=offscreen VEX_AGENT_BACKEND=stub pytest`

**Acceptance (from spec §9):** pytest green; stub chat shows preamble; export still routes; core check is manual later.
