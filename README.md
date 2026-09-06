# Vex Desktop Video Editor

Linux and macOS desktop app wrapping the Vex AI video editing agent. The UI is **PySide6** (Qt 6). Windows is not a target.

The window is a client of a Qt-free `AgentService`. Edits can run on a **stub** backend (UI work) or on a local Vex checkout (**core**).

Followable roadmap: [docs/project-plan.md](docs/project-plan.md).

## Install and run

```bash
git clone https://github.com/andrewmp1/Vex-Desktop-Video-Editor.git
cd Vex-Desktop-Video-Editor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
VEX_AGENT_BACKEND=stub vex-desktop
```

Equivalent: `python -m vex_desktop`. Toolbar: **Open Video**, **YouTube**, **Project**, **Export** (preset menu). File → Export lists YouTube, Instagram, TikTok, X, and podcast audio. Chat `export for youtube` uses the same agent op.

## Tests and screenshots

```bash
source .venv/bin/activate
pytest
python scripts/capture_ui.py
```

Offscreen by default (`QT_QPA_PLATFORM=offscreen`). PNGs land in `tests/screenshots/`.

## Run against a local Vex install

Use the Vex virtualenv so FFmpeg/LLM dependencies match the CLI. Do not attach `core` to a project while a CLI encode is running on it.

```bash
source ~/claude_work/vex/.venv/bin/activate
pip install -e ".[dev]"
cd /path/to/Vex-Desktop-Video-Editor
VEX_CORE_PATH=~/claude_work/vex VEX_AGENT_BACKEND=core vex-desktop
```

## Packaging

PyInstaller cannot cross-compile. Build on each OS, then attach the files to a GitHub Release. No Mac App Store.

```bash
# Linux AppImage (also writes dist/Vex/)
bash scripts/build_appimage.sh

# macOS DMG (on a Mac; also writes dist/Vex.app)
bash scripts/build_dmg.sh
```

- Linux: `dist/Vex-x86_64.AppImage` (relocatable `dist/Vex/` is kept as a backup)
- macOS: `dist/Vex.dmg` (and `dist/Vex.app`)
- GitHub Release (tag `v*`): AppImage + DMG + `SHA256SUMS`. No Mac App Store.
