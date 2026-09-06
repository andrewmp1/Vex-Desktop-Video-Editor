# Skills System — Design Spec

**Date:** 2026-09-06
**Status:** Approved design, pending implementation plan
**Scope:** Wrapper-only. No changes to the pinned external Vex tree.

## 1. Motivation

Users can extend the editing agent with skills: markdown instruction files
following the [Agent Skills spec](https://agentskills.io) (a `SKILL.md` with
YAML-ish frontmatter, optionally with `references/`). Skills serve two
purposes, delivered the same way — as instructions the LLM follows:

1. **Knowledge that shapes existing ops** — platform specs, brand voice for
   captions, a YouTube title/description formula.
2. **Workflows** — multi-step recipes composed of ops Vex already has
   (trim, subtitles, B-roll, export). No new agent capabilities are added;
   skills are prose.

Decisions made during brainstorming (all settled):

- Purpose: general-purpose (knowledge + workflows).
- Sources: curated examples + user-added local files. No network fetching.
- Activation: explicit toggles. Only active skills are injected.

## 2. Goals and non-goals

### Goals

- Add/list/enable/disable/remove skills via the UI and the agent protocol.
- Inject active skill content into `process_command` only.
- Preview-before-enable security gate and a persistent trust notice.
- Survive restarts (enabled set persists; skills live in the app data dir).
- Fully testable offscreen (stub backend), consistent with repo conventions.

### Non-goals (v1)

- No marketplace, URL, or git fetching of skills.
- No keyword auto-routing (explicit toggles only; the regex table in
  `exporting.py` is the natural future hook).
- No Vex-core changes, no per-skill permissions model, no Windows.

## 3. Architecture

```
Skills dialog (drag-drop / file picker)
      │ import_skill / remove_skill ops
      ▼
data_dir()/skills/<id>/SKILL.md        (or data_dir()/skills/<id>.md)
      │ SkillStore scans (frontmatter: name, description)
      ▼
UI toggle → AgentClient.set_skills([ids])
      ▼
AgentService (holds SkillState; composes preamble)
      ▼
backend.process_command(preamble + "\n\nUser command: " + command)
      ▼
VexCoreBackend → video_agent.run(...)   (unchanged)
```

**Composition lives in `AgentService.handle("process_command")`**, before
dispatch to any backend. One injection point, backend-agnostic, identical for
the in-process and stdio-JSONL hosts. The stub backend is unchanged; its
result message echoes the composed command, which is exactly what the
injection tests assert.

**Injection is confined to `process_command`** — the only LLM-mediated op.
`export` runs through `tools.export.execute` with fixed parameters, so skills
cannot alter encoding behavior. Undo/redo are unaffected (the core timeline
records edit ops, not raw prompts).

## 4. Components

### 4.1 `src/vex_desktop/skills.py` (new, Qt-free)

- **`SkillInfo`** — `id`, `name`, `description`, `path`, `chars`
  (body length after frontmatter strip).
- **`SkillStore(skills_dir)`**
  - `scan() -> list[SkillInfo]`. Accepts `<id>/SKILL.md` (spec layout,
    optional `references/` files appended after the body) or a bare
    `<id>.md`. Sorted by name.
  - `import_path(src: str) -> SkillInfo` — copies a file or folder into
    `skills_dir`, normalizing to `<id>/SKILL.md` when a bare `.md` is
    imported. `id` derives from the folder/file stem; collisions get a
    numeric suffix (`my-skill-2`).
  - `remove(id)` — deletes the skill folder/file.
  - `body(skill) -> str` — frontmatter stripped; `references/` flattened.
  - Frontmatter parser: minimal, no new dependency. Read the block between
    leading `---` lines; match `name:` and `description:` at line starts;
    strip quotes. Missing frontmatter or fields → fall back to the file
    stem as `name`, empty description.
- **`SkillState(data_dir)`** — persisted to `data_dir()/skills.json` as
  `{"enabled": [...], "seeded": true}` (enabled ids and the first-run seed
  flag). Loaded at service start.
- **`compose_preamble(skills, per_cap=16000, total_cap=16000)`**
  — returns `(preamble: str, warnings: list[str])`.

  Format (deterministic):

  ```
  Active skills for this session follow. Follow them when relevant to
  the user's request; otherwise ignore them.

  === Skill: {name} ===
  {body}
  === End skill: {name} ===

  User command: {command}
  ```

  Skills that exceed the per-skill cap are truncated with an inline
  `[skill {name} truncated]` marker; once the running total hits the total
  cap, remaining skills are skipped. Both cases add entries to `warnings`.

  With no active skills, `compose_preamble` returns `(command, [])` — the
  current behavior, byte-for-byte.

### 4.2 Protocol (additive bump)

`protocol.py`:

- `PROTOCOL_VERSION = 2`.
- New ops in `OPS`: `list_skills`, `import_skill`, `remove_skill`,
  `set_skills`.
- `AgentResult` gains an optional `skills: list[dict[str, Any]]` field
  (default `[]`), used by the four skills ops to return the current
  catalog (id, name, description, enabled, chars). `from_dict` is already
  tolerant of unknown keys; `to_dict` includes the new field. Snapshot is
  included in skills-op results as with `set_config`.

Op payloads and behavior (all handled by `AgentService`, fast and local,
no backend involvement except `snapshot()`):

| Op | Payload | Behavior |
|----|---------|----------|
| `list_skills` | `{}` | Scan store, return catalog with enabled flags. |
| `import_skill` | `{"path": "..."}` | Copy into skills dir, return catalog. Errors (missing file, unreadable) raise `AgentError` with a chat-safe message. |
| `remove_skill` | `{"id": "..."}` | Delete from disk and enabled set, return catalog. |
| `set_skills` | `{"ids": ["a", "b"]}` | Persist enabled set; unknown ids are ignored with a warning in the result message. Result message summarizes: `"2 skills active: a, b (c truncated)"`. |

Rationale for four ops instead of the UI touching `SkillStore` directly:
the repo constraint says the window talks only to `AgentClient` + the
protocol. The stdio-JSONL host inherits skills management for free.

`AgentClient` (qt.py) gains `set_skills(ids)`, `list_skills()`,
`import_skill(path)`, `remove_skill(id)` mirroring `set_config`'s
QThread pattern.

### 4.3 UI — Skills dialog

Toolbar button **Skills** opens a modal dialog:

- List (left): installed skills — name, description, char count, enable
  checkbox.
- **Preview pane** (right): read-only full markdown of the selected skill.
- **Enable gate:** a skill's checkbox stays disabled until the skill is
  selected in the list — i.e., its content has been rendered in the
  preview pane in this dialog session (a per-session `viewed` set).
  Selecting it once unlocks the checkbox.
- Buttons: **Add…** (file picker for `.md` or a folder) plus dialog-level
  drag-and-drop; **Remove** (confirmed, deletes the files).
- Persistent notice label: *"Skills are instructions the AI agent will
  follow while editing. Only add files you trust."*
- Empty state: hint text ("Drop SKILL.md files here") when the list is empty.

Every change routes through `AgentClient` ops; the dialog holds no file
logic.

### 4.4 First-run seeding

On `SkillStore` construction, if `skills_dir` does not exist, create it and
copy bundled examples from `assets/skills/` (packaged into the app via the
PyInstaller spec's `datas`). Two examples ship:

- `youtube-metadata` — title/description/hashtag guidance for exports
  (title ≤ 100 chars, 3–5 hashtags).
- `tiktok-format` — 9:16 1080×1920, captions, ≤ 5 hashtags.

Both are normal skills in the user's data dir — deletable, editable. A
`seeded` flag inside `skills.json` prevents reseeding after user deletion
(`skills.json: {"enabled": [...], "seeded": true}`).

## 5. Error handling

| Case | Behavior |
|------|----------|
| Missing/malformed frontmatter | Filename stem as name; empty description |
| Skill file deleted while enabled | Skipped at scan/compose; chat notice via `set_skills`/`list_skills` warnings |
| Oversized skill | Truncated at per-skill cap, inline marker + warning |
| Total cap reached | Remaining skills skipped + warning |
| Duplicate import name | Numeric suffix on the id |
| Import of nonexistent/unreadable path | `AgentError`, chat-safe message |
| Empty skills dir | Dialog empty-state hint |
| Bare `looks_like_export` regression | Composed command must still route export presets (regexes are `\b`-anchored); covered by a test |

## 6. Security

Skills are untrusted prompt content for an agent that performs real file
operations. Mitigations (all in v1):

- **Local files only** — no network path exists.
- **Preview-before-enable** — content must be viewed before it can be
  activated.
- **Trust notice** — persistent, in the dialog.
- **Size caps** — bound context influence.
- **Injection surface = `process_command` only** — export params, load,
  undo/redo are not LLM-mediated and cannot be steered by skills.

## 7. Testing (offscreen; repo conventions)

- **Unit** — frontmatter parser (present, missing, quoted, fallback);
  `SkillStore.scan` for both layouts; `import_path` collision suffixing;
  `compose_preamble` format, caps, warnings, and the no-skills
  byte-identity case; `SkillState` round-trip.
- **Protocol** — `set_skills`/`list_skills`/`import_skill`/`remove_skill`
  over the stdio JSONL host; `PROTOCOL_VERSION == 2`; `AgentResult.skills`
  round-trips.
- **Integration (stub)** — enable a skill → `process_command` → stub result
  message contains the preamble and `User command:` text; disable → absent.
  Composed command containing "export for youtube" still routes to the
  export preset path.
- **UI** — pytest-qt: dialog opens with catalog; checkbox disabled until
  preview viewed, enabled after; import via file picker (monkeypatched
  path); remove with confirmation; screenshot added via
  `scripts/capture_ui.py` into `tests/screenshots/`.

## 8. Documentation updates

- `docs/API_WRAPPER_SPEC.md` — `set_skills` and the three management ops;
  `PROTOCOL_VERSION 2`; updated client example.
- `docs/ARCHITECTURE.md` — skills module and composition point.
- `README.md` — short "Skills" section (what users can add, where they
  live).
- `docs/project-plan.md` — new work item with Depends on/Verify entries.

## 9. Acceptance

1. `pytest` green, including new suites; new screenshot captured.
2. Stub run: add example skill via dialog → enable → chat command → stub
   message shows injected preamble.
3. Core run (manual, Linux): active skill demonstrably changes agent
   behavior (e.g., `youtube-metadata` alters a title it proposes) without
   any Vex-tree modification.
4. Protocol doc updated; version bumped; stdio host round-trip works.
