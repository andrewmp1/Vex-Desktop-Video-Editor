# Vex Desktop Video Editor — User guide

Linux and macOS. There is no Windows build and no Mac App Store listing. Downloads come from [GitHub Releases](https://github.com/andrewmp1/Vex-Desktop-Video-Editor/releases).

This walkthrough matches the shipped app: open a clip, describe an edit in chat, preview, export.

## Install

### Linux (AppImage)

1. From a GitHub Release, download `Vex-x86_64.AppImage` (and optionally `SHA256SUMS`).
2. Make it executable and run it:

```bash
chmod +x Vex-x86_64.AppImage
./Vex-x86_64.AppImage
```

If the file will not mount (missing FUSE), run:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./Vex-x86_64.AppImage
```

### macOS (DMG)

1. Download `Vex.dmg` from the same Release.
2. Open the DMG and drag **Vex** into **Applications**.
3. First launch: if Gatekeeper blocks an unsigned build, right-click the app → **Open**.

Notarization is optional and may be absent. That is not an App Store install.

### From source (developers)

```bash
git clone https://github.com/andrewmp1/Vex-Desktop-Video-Editor.git
cd Vex-Desktop-Video-Editor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
VEX_AGENT_BACKEND=stub vex-desktop
```

`stub` is for UI work without Vex. Real edits need a local Vex checkout (see [Run against a local Vex install](#run-against-a-local-vex-install)).

## Set a Gemini API key

Natural-language edits on the **core** backend call Gemini by default.

1. **File → Settings…** (or the **Settings** toolbar button).
2. Provider: `gemini`.
3. Model: leave `gemini` or enter a Gemini model id.
4. Paste the API key. Leave the field blank to keep a key already stored.
5. OK.

The key is stored in the OS keyring (`vex-desktop` / `gemini_api_key`), with a file fallback under the app data directory if keyring is unavailable.

**Claude:** choose provider `claude` and paste an Anthropic key. **Ollama** is listed in Settings for a local OpenAI-compatible server; Gemini is the path this guide assumes.

## Open a video

The window has **PREVIEW**, **CHAT**, and **TIMELINE**. Use the toolbar or **File** menu.

| Action | What it does |
|--------|----------------|
| **Open Video** | Local file (mp4 and other common video types). Drag-and-drop onto the preview also works. |
| **YouTube** | Paste a `https://www.youtube.com/watch?v=…` URL. Core downloads it into a Vex project; stub cannot fetch YouTube. |
| **Open Project** | Pick an existing Vex project from `~/.video-agent/projects`. |
| **Open Project File…** | Open a `.vex` zip (saved from **Save Project…**). |
| **Save Project…** | Write a `.vex` zip of the current project (core: Vex project folder; stub: working file). |

You can also paste a YouTube URL into chat on core.

Do **not** attach the desktop **core** backend to a project while a CLI `vex` process is encoding that same project.

## Edit in chat

Type a plain-language instruction and press Enter or **Send**. Examples:

- `Trim the first 10 seconds`
- `Add subtitles`
- `Undo` / **Edit → Undo** (also **Edit → Redo**, **Edit → Cancel**)

**Edit** (menu and toolbar) also sends the same chat commands without typing:

- **Add subtitles** → `Add subtitles`
- **Insert B-roll…** → pick a clip, then `Insert B-roll from <path>`
- **Add a simple effect** → `Add a subtle zoom effect`

The timeline pane shows a filmstrip of frames from the current working file. Click a frame to seek the preview. Edit history under the filmstrip still comes from the agent snapshot (undo/redo). Preview plays the working file after a successful edit. It is not the edit engine; FFmpeg/Vex write files off the UI thread.

## Skills

Skills are markdown instruction files the AI agent follows while editing in chat. They do not add new tools; they shape how the agent uses existing ones. Export, undo, redo, and load are not affected.

1. Open **File → Skills…** or the toolbar **Skills** button.
2. Notice: *"Skills are instructions the AI agent will follow while editing. Only add files you trust."*
3. **Add…** (or drag-and-drop) a local `.md` file or a folder that contains `SKILL.md`. There is no marketplace or URL fetch.
4. Select a skill in the list to preview its body. The enable checkbox stays locked until you have previewed it in this session.
5. Check **Enable**. Enabled skills apply on the next chat command.

Bundled examples `youtube-metadata` and `tiktok-format` are copied into your data dir on first run (you can delete them). Skill files live under the app data `skills/` folder; the enabled set is stored in `skills.json` (see [Where files go](#where-files-go)).

## Export

**File → Export** and the toolbar **Export** menu list:

- YouTube 1080p (default)
- YouTube 4K
- Instagram Reels
- Instagram Square
- TikTok
- X
- Podcast audio (`.mp3`; not loaded into the video preview)

Chat `export for youtube` (or `export for tiktok`, `export podcast audio`, …) uses the same `export` op. The chat message includes the output path when it succeeds.

If you export with no clip loaded, chat shows **Load a video**.

## Where files go

| What | Location |
|------|----------|
| Vex CLI / core projects | `~/.video-agent/projects/` |
| App data (stub exports, file-fallback secrets, skills) | Linux: `~/.local/share/Vex/` · macOS: `~/Library/Application Support/Vex/` |
| Skills files | `…/Vex/skills/` (`SKILL.md` folders or bare `.md`) |
| Enabled skills | `…/Vex/skills.json` |
| Stub default export | `…/Vex/exports/<name>_<preset>.mp4` (podcast: `.mp3`) |
| Core export | Path printed in chat (usually inside the project directory) |
| `.vex` project zip | Wherever you save it; unpack extracts into the Vex projects dir |

Override the Vex project root with `AGENT_PROJECTS_DIR` if you need an isolated tree.

## Preview notes (AV1)

Many YouTube downloads are AV1. The app forces software decode (`QT_FFMPEG_DECODING_HW_DEVICE_TYPES=,`) so GPUs without AV1 VAAPI/VideoToolbox do not spam errors. Preview can still be slow or black in a headless/offscreen session; that is not a failed export. The exported file path in chat is the source of truth.

## Run against a local Vex install

Use the Vex virtualenv so FFmpeg and LLM dependencies match the CLI:

```bash
source ~/claude_work/vex/.venv/bin/activate
cd /path/to/Vex-Desktop-Video-Editor
pip install -e ".[dev]"
VEX_CORE_PATH=~/claude_work/vex VEX_AGENT_BACKEND=core vex-desktop
```

Do not run GUI **core** and the CLI encoder on the same project at the same time.

## One-pass checklist

1. Install the AppImage or DMG (or run from source).
2. Settings → Gemini API key.
3. **Open Video** (local mp4) or **YouTube** on core.
4. (Optional) **Skills** → preview and enable an example such as `youtube-metadata`.
5. Chat: `Trim the first 10 seconds`.
6. Confirm preview/timeline updated.
7. **Export → YouTube 1080p** or chat `export for youtube`.
8. Copy the path from chat and open that file in a player.

Roadmap and packaging internals: [project-plan.md](project-plan.md).
