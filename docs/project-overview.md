# Vex Desktop Video Editor

## Project Overview

**Vex Desktop Video Editor** is a native-feeling macOS (and cross-platform) desktop application that wraps the powerful open-source Vex AI video editing agent.

It transforms Vex from a command-line REPL into an intuitive graphical video editor where users can edit videos using natural language commands (e.g., "Remove the first 10 seconds, add subtitles, and insert B-roll footage").

### Core Goals
- Make advanced AI-driven video editing accessible to non-technical users
- Leverage the full capabilities of the existing Vex project
- Deliver a polished, responsive desktop experience using Flet
- Support local and cloud LLM backends
- Maintain full undo/redo, timeline, and project state management

### Tech Stack
- **Frontend**: Flet (Python + Flutter)
- **Backend**: Vex agent (Python)
- **Video Processing**: FFmpeg + MoviePy
- **LLM Integration**: Gemini, Claude, or local models
- **Packaging**: Flet build / py2app for macOS .app bundle

**Status**: Early development - Repository initialization phase.