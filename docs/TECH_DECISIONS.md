# Technology Decisions

## Platforms

Linux and macOS only. Windows is out of scope.

Linux is the development and MVP target. macOS is a first-class second target, built on a Mac or `macos-14` CI runner. Qt/PyInstaller cannot cross-compile: Linux builds Linux, macOS builds macOS.

## UI framework: PySide6

PySide6 (Qt for Python, LGPL) is the desktop shell.

| Framework | Pros | Cons | Decision |
|-----------|------|------|----------|
| **PySide6** | Native widgets, splitters, menus; `QMediaPlayer` / `QVideoWidget`; timeline-grade custom painting; mature Linux + macOS packaging | C++ bindings, larger install | **Chosen** |
| Flet | Fast to sketch, Flutter look | Weaker timeline/video-editor widgets; Linux video needs extra `libmpv` / desktop flavor; packaging is a relocatable dir, not an editor-class app | Replaced |
| PyQt6 | Same Qt widgets | GPL unless a commercial license is bought | Not chosen |
| Toga | Native widgets | Immature video | Not chosen |
| Electron | Web ecosystem | Heavy, not Python-native | Avoided |

Why this works on both OSes:

- Qt 6.5+ Multimedia defaults to an **FFmpeg** backend on Linux and macOS (native fallbacks: GStreamer on embedded Linux, AVFoundation via `QT_MEDIA_BACKEND=darwin` on macOS).
- Widgets, dialogs, drag-and-drop, and the menu bar behave correctly on GTK/Wayland and Cocoa without a second UI toolkit.
- Official wheels dynamically link Qt, which keeps the LGPL obligation straightforward (do not statically link).

Preview (`QMediaPlayer`) is **not** the edit engine. Edits still go through FFmpeg / MoviePy / Vex. If preview needs frame-accurate scrubbing later, swap the widget for libmpv and leave the agent API unchanged.

## UI / agent split

The desktop window is a client of a frozen agent protocol (`vex_desktop.protocol`). `AgentService` is Qt-free and can run in-process (QThread) or over JSONL stdio. Upstream Vex (`VideoAgent`, `ProjectState`) stays behind `VexCoreBackend`. That keeps FFmpeg/LLM crashes and imports out of the GUI module graph, and lets a CLI reuse the same ops later.

## LLM & video stack

- **LLM**: Gemini first (as in upstream Vex), then Claude / OpenAI / Ollama
- **Edit engine**: FFmpeg CLI + MoviePy, resolved once via `vex_desktop.platform_support.ffmpeg_path()`
- **Preview**: Qt Multimedia (FFmpeg backend). Hardware decode is off by default (`QT_FFMPEG_DECODING_HW_DEVICE_TYPES=,`) so AV1 YouTube files do not spam VAAPI errors on GPUs without AV1. Set that variable to `vaapi` or `videotoolbox` to re-enable.
- **Secrets**: `keyring` (libsecret on Linux, Keychain on macOS)
- **Paths**: `platformdirs` — never hardcode `~/Library` or `~/.local/share`
- **Transcription**: Whisper (local or API), later
- **Visuals**: Hyperframes / Manim / Blender stay Phase 4+, not MVP

## Packaging

- **Tool**: PyInstaller (`vex.spec`)
- **Linux**: `dist/Vex/` relocatable dir, then AppImage (optional `.deb` / AUR)
- **macOS**: `Vex.app` → DMG
- **Distribution**: GitHub Releases (and optionally a website that links to those files). Users download and run; there is no store listing.
- Bundle a static FFmpeg next to the app so MoviePy does not depend on PATH
- Out of scope: Mac App Store, Sparkle/auto-update, Windows installers
- Apple notarization is optional later if Gatekeeper blocks unsigned DMGs; it is not an App Store requirement

## Licensing note

PySide6 is LGPL-3. Ship the official pip wheels (dynamic link) and include the Qt/PySide licenses in the installer. Do not freeze Qt into a single static binary.