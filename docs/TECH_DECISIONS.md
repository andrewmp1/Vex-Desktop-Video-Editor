# Technology Decisions

## Why Flet?

- Pure Python UI framework based on Flutter
- Excellent macOS support and native look
- Built-in video component via flet-video
- Easy packaging to .app bundle
- Fast development and hot reload

## Alternatives Considered

| Framework | Pros | Cons | Decision |
|-----------|------|------|----------|
| Flet | Pure Python, modern, easy packaging | Slightly less native widgets | **Chosen** |
| PyQt6/PySide6 | Most native feel, powerful video | C++ bindings, steeper curve | Backup |
| Toga (BeeWare) | Native widgets | Less mature video support | Not chosen |
| Electron | Web tech | Heavy, not Python-native | Avoided |

## LLM & Video Stack

- **LLM**: Start with Gemini (as in original Vex), support Claude/OpenAI/Local
- **Video Engine**: FFmpeg + MoviePy (bundled)
- **Transcription**: Whisper (local or API)
- **Visuals**: Hyperframes, Manim, fallback to Blender

## Packaging

- `flet build macos` for native .app
- Bundle static FFmpeg binary
- Code signing & notarization plan