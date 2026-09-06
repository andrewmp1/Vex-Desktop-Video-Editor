# Feature Comparison - Vex Desktop Video Editor

Updated 2026-09-06. Canonical remaining work: [project-plan.md](project-plan.md). User guide: [user-guide.md](user-guide.md).

| Area | Desktop app | Vex CLI |
|------|-------------|---------|
| Natural-language edit | Yes (core backend → `VideoAgent.run`) | Yes |
| Video preview | Qt Multimedia | Files on disk |
| Timeline / history | Filmstrip from working file + history list + undo/redo | Internal timeline JSON |
| Undo/redo | Yes (agent ops) | Yes |
| Open file / YouTube / existing project | Yes | Yes |
| Export YouTube 1080p | Yes (`export` op + chat + File → Export) | Yes |
| Other export presets | File → Export / toolbar menu (Instagram, TikTok, X, podcast audio) | Yes |
| Auto shorts / B-roll / visuals | Via chat to core only; no dedicated UI | Yes |
| Skills (local markdown instructions) | Yes (dialog + protocol ops; inject on chat only) | No dedicated skill store |
| Packaging | AppImage + DMG; tag `v*` GitHub Release with checksums | N/A |
| Tests | pytest-qt + stub/core export | Large CLI suite |
