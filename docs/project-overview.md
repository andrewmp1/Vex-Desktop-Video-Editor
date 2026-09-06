# Vex Desktop Video Editor

Canonical overview: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md).

**Vex Desktop Video Editor** is a Linux and macOS PySide6 app around the open-source Vex AI video editing agent. It turns the Vex CLI into a GUI where users edit with natural language.

### Core goals

- Make AI-driven editing usable for non-technical users
- Keep the full Vex agent, not a reduced command set
- Stay responsive while FFmpeg and LLMs run
- Support cloud and local LLM backends
- Undo/redo, timeline, and project state

### Tech stack

- **Frontend**: PySide6 (Qt 6)
- **Backend**: Vex agent (Python)
- **Preview**: Qt Multimedia
- **Edits**: FFmpeg + MoviePy
- **Packaging**: PyInstaller (Linux AppImage + macOS DMG via GitHub Releases)

**Status**: Early development — PySide6 shell in place, agent still stubbed.

Windows is not a target.
