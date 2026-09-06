# Visual Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Filmstrip of working-file stills in the TIMELINE pane; `snapshot.history` stays the edit list.

**Architecture:** `ui/thumbs.py` pulls frames with FFmpeg on a `QThread`. `TimelinePane` shows the strip and history. Click seeks `PreviewPane`. No protocol change.

**Tech Stack:** PySide6, FFmpeg/ffprobe via `platform_support`, pytest-qt.

**Spec:** [docs/superpowers/specs/2026-09-06-visual-timeline-design.md](../specs/2026-09-06-visual-timeline-design.md)

## Global Constraints

- UI imports `AgentClient` + protocol only; no `vex_core`.
- Linux + macOS only.
- Tests offscreen: `QT_QPA_PLATFORM=offscreen VEX_AGENT_BACKEND=stub pytest`.

---

### Task 1: Frame extraction

**Files:**
- Create: `src/vex_desktop/ui/thumbs.py`
- Modify: `src/vex_desktop/platform_support.py` (`ffprobe_path`)
- Test: `tests/test_thumbs.py`

**Produces:** `extract_thumbnails(path, count, width) -> list[tuple[int, QImage]]`, `video_duration_ms(path) -> int | None`

- [x] **Step 1–4:** Tests in `tests/test_thumbs.py`; implementation in `thumbs.py` + `ffprobe_path()`.
- [x] **Step 5:** Covered by `pytest tests/test_thumbs.py`.

### Task 2: Filmstrip UI + seek

**Files:**
- Modify: `src/vex_desktop/ui/timeline_pane.py`, `preview_pane.py`, `main_window.py`, `theme.qss`, `tests/conftest.py`, `tests/test_ui_smoke.py`

**Produces:** `TimelinePane.thumbnail_count()`, `seek_requested`, `PreviewPane.seek`, `position_changed`

- [x] Filmstrip, worker thread, seek/playhead, history unchanged.
- [x] UI tests wait for thumbs after load; history still recorded after stub edit.

### Task 3: Docs

**Files:** `docs/FEATURE_COMPARISON.md`, `docs/project-plan.md`, `docs/user-guide.md`

- [x] Filmstrip documented; history still from snapshot.

**Verify:** `QT_QPA_PLATFORM=offscreen VEX_AGENT_BACKEND=stub pytest`
