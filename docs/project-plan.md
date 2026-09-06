# Vex Desktop Video Editor — Project Plan

**Status:** MVP loop works on Linux (load → natural-language edit → preview → YouTube export). Remaining work is packaging, remaining presets, and docs.

**Last updated:** 2026-09-06

This document is the implementation guide. Architecture details live in [ARCHITECTURE.md](ARCHITECTURE.md). Stack choices live in [TECH_DECISIONS.md](TECH_DECISIONS.md). The agent API lives in [API_WRAPPER_SPEC.md](API_WRAPPER_SPEC.md). Feature specs and TDD plans live under [superpowers/](superpowers/README.md).

Do not start a later work item until its **Depends on** items are done and its **Verify** command has been run.

---

## 1. Product goal

A Linux and macOS desktop app that wraps the [Vex](https://github.com/AKMessi/vex) CLI agent: import a video (file, existing Vex project, or YouTube URL), describe edits in chat, preview the working file, export a downloadable movie.

**MVP (achieved on Linux):** import → one NL edit → preview updates → export a file and show its path.

**Distribution:** GitHub Releases (and optionally a site that links to those files). Users download an AppImage (Linux) or a DMG (macOS). No Mac App Store, no Windows, no in-app updater.

---

## 2. Constraints (do not revisit unless the owner changes them)

| Rule | Meaning |
|------|---------|
| Linux + macOS only | No Windows code, CI, or installers |
| PySide6 UI | Do not switch back to Flet |
| UI never imports Vex | Window talks only to `AgentClient` + `protocol` |
| Agent work off the GUI thread | `QThread` via `AgentClient` |
| Preview ≠ edit engine | `QMediaPlayer` plays files; FFmpeg/Vex write files |
| Core Vex is an external tree | `VEX_CORE_PATH` or `~/claude_work/vex`; pin in `vex_core.pin` |
| Tests first for UI | Offscreen pytest-qt + PNGs in `tests/screenshots/` |
| Downloads, not stores | GitHub Release artifacts only |

Vex itself is PolyForm Noncommercial. The desktop wrapper must not assume a commercial App Store path.

---

## 3. How to work in this repo

### Stub (UI and most tests — no LLM, no Vex job)

```bash
cd /home/andrew/code/Vex-Desktop-Video-Editor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
VEX_AGENT_BACKEND=stub vex-desktop
# equivalent: python -m vex_desktop
pytest
python scripts/capture_ui.py
```

Do not set `PYTHONPATH=src`. The editable install is the run path.

### Core (real Vex — uses `~/claude_work/vex` and `~/.video-agent/projects`)

Do not attach `core` to a project while a CLI `vex` process is encoding that project.

```bash
source ~/claude_work/vex/.venv/bin/activate
cd /home/andrew/code/Vex-Desktop-Video-Editor
pip install -e ".[dev]"
VEX_CORE_PATH=~/claude_work/vex VEX_AGENT_BACKEND=core vex-desktop
```

Core export test (creates a 1s clip in a temp dir; does not touch Kennedy/Rickroll projects):

```bash
source ~/claude_work/vex/.venv/bin/activate
cd /home/andrew/code/Vex-Desktop-Video-Editor
pip install -e ".[dev]"
VEX_CORE_PATH=~/claude_work/vex \
  python -m pytest tests/test_export.py::test_core_export_encodes_sample
```

### Environment

| Variable | Role |
|----------|------|
| `VEX_AGENT_BACKEND` | `stub` \| `core` \| `auto` (default `auto`) |
| `VEX_CORE_PATH` | Path to a Vex git checkout |
| `AGENT_PROJECTS_DIR` | Vex project root (default `~/.video-agent/projects`) |
| `QT_QPA_PLATFORM=offscreen` | Headless UI tests |
| `QT_FFMPEG_DECODING_HW_DEVICE_TYPES=,` | Software decode (set in `app.py`; needed for AV1 on GPUs without AV1 VAAPI) |

---

## 4. Current status

### Done

- Private GitHub repo, `src/vex_desktop` package, docs, PyInstaller spec, tag workflow sketch
- PySide6 editor: preview, chat, timeline, dark Fusion theme, drag-and-drop
- Toolbar: Open Video, YouTube, Project, Export, Settings
- Frozen protocol + `AgentService` + stub/core backends; UI uses `AgentClient` only
- Core backend talks to local Vex (`VideoAgent`, `create_project`, YouTube URL, `tools.export.execute`)
- Secrets via `keyring` (file fallback); Settings dialog
- Software AV1 preview (no VAAPI spam on Radeon R9 M370X)
- YouTube `youtube_1080p` export (chat, File → Export, `export` op)
- Export preset menu (Instagram, TikTok, X, podcast audio)
- Failed export and QA copy surface in chat (empty Export → “Load a video”)
- Stub pytest workflow on pull requests (`.github/workflows/test.yml`)
- PyInstaller spec collects `ffmpeg`; `ffmpeg_path()` checks the executable dir and `_internal/`
- Linux AppImage (`scripts/build_appimage.sh`; local `dist/Vex-x86_64.AppImage` smoke-launches)
- macOS DMG script + CI (`scripts/build_dmg.sh` → `dist/Vex.dmg`; notarize skipped without secrets)
- GitHub Release on `v*` tags attaches AppImage, DMG, and `SHA256SUMS`
- User guide (`docs/user-guide.md`, linked from README)
- Visual timeline filmstrip (thumbnails from the working file; history list unchanged)
- Automated tests: UI smoke + screenshots, stub export, core+ffmpeg export (skip in desktop venv)
- Layout fixes verified via `tests/screenshots/`
- App icon (`assets/icon.png`, window + PyInstaller)
- Install/run via `pip install -e ".[dev]"` then `vex-desktop`

### Not done

- `.vex` project format, Ollama as a first-class run mode, B-roll UI beyond chat

### Known limits (not bugs to “fix” unless specified)

- Offscreen screenshots of the preview pane are often black; chat/timeline/chrome are the signal
- YouTube sources are often AV1; this GPU has no AV1 hardware decode
- Auto-shorts QA can accept 0 clips on music videos (transcript gates). Surface the Vex message; do not treat as a crash
- Stub export **copies** the working file; only core **encodes** to 1080p H.264

---

## 5. Architecture (follow these rules in every change)

```
PySide6 UI  →  AgentClient (Qt, QThread)  →  AgentService (no Qt)
                                              ├─ StubBackend
                                              └─ VexCoreBackend → Vex checkout
Preview: QMediaPlayer on working_file / exported_path
```

- New agent capabilities = new protocol op **or** `process_command` text that Vex already understands. Do not call `tools.*` from `ui/`.
- `export` op payload: `{ "preset": "youtube_1080p", "output_path": optional }`. Result: `exported_path`.
- Tests that need Vex go in `tests/test_export.py::test_core_*` and must set `AGENT_PROJECTS_DIR` to a temp dir.

---

## 6. Remaining work (ordered)

P0–P8 are in tree (CI/tag verify waits on a remote build). Later items in section 7 are optional.

### P0 — Hygiene — **done**

- 512×512 `assets/icon.png` (same bytes in `src/vex_desktop/ui/icon.png`); window + `vex.spec` use it
- Default run: `pip install -e ".[dev]"` then `vex-desktop` or `python -m vex_desktop`
- FEATURE_COMPARISON and ARCHITECTURE `export` op match the code
- Desktop package deps are PySide6 / platformdirs / keyring (Vex stack stays in the Vex venv)

### P1 — Export preset menu — **done**

**Goal:** User can export Instagram / TikTok / X / podcast audio without typing a preset id.

| | |
|--|--|
| **Depends on** | P0 optional; export op already works |
| **Files** | `src/vex_desktop/ui/main_window.py`, `src/vex_desktop/exporting.py`, `tests/test_export.py` |
| **Steps** | File → Export submenu (or a dialog) listing `PRESETS` from `exporting.py`. Each action calls `AgentClient.export(preset)`. Audio-only must **not** load `.mp3` into `QMediaPlayer` (already skipped for `.mp3`). |
| **Verify** | Stub: parametrize `export` for `tiktok` and `podcast_audio`; assert file suffix. UI: one pytest-qt test that opens the menu is optional; service tests are enough. |
| **Done when** | `pytest tests/test_export.py` covers at least two presets besides `youtube_1080p`. |

### P2 — Failed-export and QA copy in chat — **done**

**Goal:** Failures look like the CLI, not a hang.

| | |
|--|--|
| **Depends on** | Nothing (chat already shows `AgentError` and result messages) |
| **Files** | `src/vex_desktop/ui/main_window.py`, `tests/test_ui_smoke.py` or `tests/test_export.py` |
| **Steps** | 1. Stub: `export` with no video already raises `ProjectError` — add a UI test that Export with no clip appends that error to chat. 2. If `result.success` is false, still show `result.message` in chat (core shorts QA). 3. Do not start a new YouTube shorts job from the GUI as a test. |
| **Verify** | `pytest` UI test: empty window → Export → transcript contains “Load a video”. |
| **Done when** | That test passes; no new CLI shorts runs were used. |

### P3 — pytest on every PR — **done** (workflow present; first green run waits on a PR)

**Goal:** Layout and stub export cannot regress unnoticed.

| | |
|--|--|
| **Depends on** | P0–P2 preferred |
| **Files** | `.github/workflows/test.yml` (new). Do **not** run core export on `ubuntu-latest` (no Vex checkout / no API). |
| **Steps** | Job: Python 3.12, `pip install -e ".[dev]"`, `sudo apt-get install ffmpeg`, `QT_QPA_PLATFORM=offscreen VEX_AGENT_BACKEND=stub pytest`. Upload `tests/screenshots/*.png` as artifacts. |
| **Verify** | Open a PR; workflow is green; screenshots artifact contains `empty.png`. |
| **Done when** | Main-branch PRs run stub tests automatically. |

### P4 — Bundle FFmpeg with the app — **done** (unit test; frozen `dist/Vex` not rebuilt this session)

**Goal:** End users do not need FFmpeg on `PATH`.

| | |
|--|--|
| **Depends on** | P3 |
| **Files** | `vex.spec`, `src/vex_desktop/platform_support.py`, packaging notes in this plan |
| **Steps** | On each build OS, download or copy a static `ffmpeg` next to the executable (same pattern `ffmpeg_path()` already checks: sibling of `sys.executable`). Add it to PyInstaller `binaries=`. Core Vex still reads `config.FFMPEG_PATH` — `VexCoreBackend` already assigns `ffmpeg_path()`. |
| **Verify** | Frozen dir runs `ffmpeg_path()` pointing inside the bundle (unit test with a fake sibling binary, plus a manual run of `dist/Vex` on Linux). |
| **Done when** | Spec collects ffmpeg; `ffmpeg_path()` finds it without `PATH`. |

### P5 — Linux AppImage — **done** (local `dist/Vex-x86_64.AppImage` smoke-launched; CI artifact waits on a tag)

**Goal:** One downloadable Linux file.

| | |
|--|--|
| **Depends on** | P4 |
| **Files** | `scripts/build_appimage.sh`, `.github/workflows/build.yml` |
| **Steps** | 1. `pyinstaller vex.spec` → `dist/Vex/`. 2. Wrap with [appimagetool](https://github.com/AppImage/appimagetool) using the desktop file + icon from P0. 3. Categories: `AudioVideo;Video;`. 4. CI `build-linux` uploads `Vex-x86_64.AppImage`. Keep the relocatable dir as a backup artifact. |
| **Verify** | On this machine: `chmod +x Vex-*.AppImage && ./Vex-*.AppImage` opens the stub or core UI. `pytest` still passes (does not replace tests). |
| **Done when** | A local AppImage launches; CI produces the same artifact on tag. |

### P6 — macOS DMG on CI — **done** (script + workflow; first DMG waits on a macOS runner / tag)

**Goal:** GitHub Release can attach a DMG. Build **on macOS** (`macos-14`); cannot cross-compile from Linux.

| | |
|--|--|
| **Depends on** | P0 icon, P4 ffmpeg (macOS static binary) |
| **Files** | `.github/workflows/build.yml`, `vex.spec` `BUNDLE` section |
| **Steps** | Keep `create-dmg` after `pyinstaller vex.spec`. Notarization stays **optional** (existing step with secrets). Upload `Vex.dmg`. |
| **Verify** | Tag `v0.1.0-test`; Actions macOS job uploads a DMG. Open on a Mac if available; otherwise CI success is the gate. |
| **Done when** | Tagged builds publish a DMG artifact. |

### P7 — GitHub Release — **done** (workflow present; first assets wait on a `v*` tag)

**Goal:** One tag produces Linux AppImage + macOS DMG as release assets.

| | |
|--|--|
| **Depends on** | P5, P6 |
| **Files** | `.github/workflows/build.yml` `softprops/action-gh-release` |
| **Steps** | On `push: tags: v*`, attach AppImage + DMG (and checksums). Generate notes. No App Store listing. |
| **Verify** | GitHub Release page for the tag lists both files. |
| **Done when** | A real `v*` tag has downloadable Linux and macOS builds. |

### P8 — User documentation — **done**

**Goal:** A stranger can install, set an API key, edit, export.

| | |
|--|--|
| **Depends on** | P7 preferred; can draft earlier |
| **Files** | `docs/user-guide.md` (new), link from README |
| **Steps** | Pages: install (AppImage / DMG), Gemini key in Settings, open file vs YouTube vs Project, chat examples (`Trim the first 10 seconds`, `export for youtube`), where files go (`~/.video-agent/projects`, export path in chat), AV1/software decode note, “don’t run GUI core + CLI on the same project at once.” |
| **Verify** | Follow the guide on a clean Linux user account (or a second local user) through one export. |
| **Done when** | README links the guide; the walkthrough matches the shipped app. |

---

## 7. Later (not blocking a public download)

Do these only after P7, and only if still wanted:

| Item | Notes |
|------|--------|
| Ollama | Settings already has an `ollama` provider; wire `VexCoreBackend.set_config` to Vex `PROVIDER=ollama` and confirm with a local model |
| B-roll / subtitles / effects | Chat `process_command` already reaches `VideoAgent.run`; no extra op unless the UI needs dedicated buttons |
| Visual timeline | **Done:** filmstrip from `working_file`; `snapshot.history` is still the edit list |
| `.vex` bundle | Optional zip of a Vex project dir; CLI already uses folder JSON |
| Gatekeeper notarization | Only if unsigned GitHub DMGs are blocked; not App Store |

---

## 8. Verification matrix

| Claim | Command / evidence |
|-------|-------------------|
| UI still lays out | `QT_QPA_PLATFORM=offscreen pytest tests/test_ui_smoke.py` + `tests/screenshots/empty.png` |
| Stub export | `pytest tests/test_export.py -k stub` |
| UI export | `pytest tests/test_export.py::test_ui_export_from_toolbar` + `tests/screenshots/exported-sample.png` |
| Real encode | Vex venv + `test_core_export_encodes_sample` (ffprobe 1920×1080 h264) |
| Live edit | Core GUI: open local file, chat trim, preview path changes, undo |
| AppImage | P5 verify |
| Release | P7 GitHub assets |

Do **not** use `vex youtube-shorts` as a desktop regression test.

---

## 9. Out of scope

- Windows
- Mac App Store / iOS / Android
- Sparkle or other auto-update
- Rewriting Vex’s shorts QA (music videos will keep failing transcript floors)
- Embedding Hyperframes/Manim/Blender in the first downloadable build

---

## 10. Definition of “1.0 downloadable”

All of P0–P8, plus:

1. Linux AppImage and macOS DMG on a GitHub Release
2. A user can set a Gemini key, open a local MP4, trim in chat, preview, export YouTube 1080p, and find the file from the chat path
3. Stub pytest green on every PR
4. This plan’s **Done** section has been updated so it does not lie
