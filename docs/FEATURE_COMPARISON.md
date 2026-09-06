# Feature Comparison - Vex Desktop Video Editor

Updated 2026-09-05. Canonical remaining work: [project-plan.md](project-plan.md).

| Area | Desktop app | Vex CLI |
|------|-------------|---------|
| Natural-language edit | Yes (core backend → `VideoAgent.run`) | Yes |
| Video preview | Qt Multimedia | Files on disk |
| Timeline / history | Text list + undo/redo from snapshot | Internal timeline JSON |
| Undo/redo | Yes (agent ops) | Yes |
| Open file / YouTube / existing project | Yes | Yes |
| Export YouTube 1080p | Yes (`export` op + chat + File → Export) | Yes |
| Other export presets | File → Export / toolbar menu (Instagram, TikTok, X, podcast audio) | Yes |
| Auto shorts / B-roll / visuals | Via chat to core only; no dedicated UI | Yes |
| Packaging | Linux AppImage + macOS DMG scripts; GitHub Release is P7 | N/A |
| Tests | pytest-qt + stub/core export | Large CLI suite |
