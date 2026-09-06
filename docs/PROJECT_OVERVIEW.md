# Vex Desktop Video Editor

## Project Overview

**Vex Desktop Video Editor** is a Linux and macOS application that wraps the [Vex](https://github.com/AKMessi/vex) AI video editing agent in a PySide6 GUI.

### What is Vex?

Vex is an open-source Python agent that edits video from natural language (e.g. "Trim the first 10 seconds", "Add subtitles", "Insert B-roll").

### Goal

Turn the Vex CLI into a desktop editor: import a file, describe the edit, preview the result, export. Linux is the MVP platform; macOS uses the same code and a separate build.

### Key features planned

- Drag-and-drop video import
- Real-time video preview (Qt Multimedia)
- Natural language chat for edits
- Visual timeline and undo/redo
- One-click social export
- Full Vex agent capabilities (LLM, Whisper, FFmpeg)

### Tech stack

- **UI**: PySide6 (Qt 6)
- **Backend**: Vex agent (Python)
- **Preview**: Qt Multimedia (FFmpeg backend)
- **Edits**: FFmpeg + MoviePy
- **Packaging**: PyInstaller — Linux AppImage, macOS DMG, published as GitHub Releases (no App Store)

Windows is not a target.
