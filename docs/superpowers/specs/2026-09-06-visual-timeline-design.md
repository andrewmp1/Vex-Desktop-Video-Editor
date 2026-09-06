# Visual Timeline — Design Spec

**Date:** 2026-09-06
**Status:** Implemented on `feature/visual-timeline`
**Scope:** Desktop UI only. No protocol bump. No Vex-core changes.

## 1. Goal

Replace the text-only TIMELINE pane with a filmstrip of stills from the
current working file, while keeping `ProjectSnapshot.history` as the
source of truth for edits (undo/redo and the numbered list).

## 2. Non-goals

- Not an NLE with clips, tracks, or ripple edits.
- No new agent op. Thumbnails are a preview concern, like `QMediaPlayer`.
- Audio-only working files (`.mp3` and similar) have no filmstrip.

## 3. Architecture

```
working_file (snapshot)
      │
      ▼
ui/thumbs.py  (ffmpeg + ffprobe, off GUI thread)
      │ list[(ms, QImage)]
      ▼
TimelinePane filmstrip  --seek_requested(ms)--> PreviewPane.seek
PreviewPane.position_changed(ms) --> TimelinePane.set_playhead
History list still bound to snapshot.history
```

FFmpeg is resolved via `platform_support.ffmpeg_path()` /
`ffprobe_path()`. The UI must not import `vex_core` or `tools.*`.

## 4. Behavior

- When `working_file` exists and is a video, extract up to 8 evenly spaced
  frames (4 if duration &lt; 3s). Cache by path + mtime + size.
- Click a frame seeks the preview. The nearest frame is highlighted from
  playhead position.
- History labels remain `"{n}. {entry}"` from `snapshot.history`.
- Missing ffmpeg, missing file, or audio-only: filmstrip hidden; history
  and undo/redo still work.

## 5. Testing

- Unit: `extract_thumbnails` on the pytest `sample_video` fixture yields
  non-null images.
- UI: after Open Video, `thumbnail_count() >= 1`; after a stub edit,
  history still contains the command and thumbs remain.
- Offscreen pytest-qt; screenshots via existing `loaded-sample.png`.

## 6. Acceptance

1. `pytest` green.
2. Loaded sample shows a filmstrip.
3. Chat edit still appends to history; thumbs still present.
