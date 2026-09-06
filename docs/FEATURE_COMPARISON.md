# Feature Comparison - Vex Desktop Video Editor

Updated 2026-09-05. Canonical remaining work: [project-plan.md](project-plan.md).

| Area | Desktop app | Vex CLI |
|------|-------------|---------|
| Natural-language edit | Yes (core backend → `VideoAgent.run`) | Yes |
| Video preview | Qt Multimedia | Files on disk |
| Timeline / history | Text list + undo/redo from snapshot | Internal timeline JSON |
| Undo/redo | Yes (agent ops) | Yes |
| Open file / YouTube / existing project | Yes | Yes |
| Export YouTube 1080p | Yes (`export` op + chat) | Yes |
| Other export presets | Op supports names; UI is YouTube-only until P1 | Yes |
| Auto shorts / B-roll / visuals | Via chat to core only; no dedicated UI | Yes |
| Packaging | Spec + CI sketch; AppImage/DMG is P5–P7 | N/A |
| Tests | pytest-qt + stub/core export | Large CLI suite |
