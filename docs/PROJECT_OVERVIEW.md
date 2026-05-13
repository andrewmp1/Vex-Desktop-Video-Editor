# Vex Desktop Video Editor

## Project Overview

**Vex Desktop Video Editor** is a desktop application that brings the power of the [Vex](https://github.com/AKMessi/vex) AI video editing agent into an intuitive, modern graphical user interface.

### What is Vex?
Vex is an open-source Python-based AI agent that allows users to edit videos using natural language commands (e.g., "Trim the first 10 seconds", "Add subtitles", "Insert B-roll footage").

### Goal of this Project
Transform the CLI-based Vex agent into a full-featured desktop video editor app using **Flet** for the UI, making advanced AI-powered video editing accessible and user-friendly on macOS (and other platforms).

### Key Features Planned
- Drag-and-drop video import
- Real-time video preview
- Natural language chat interface for edits
- Visual timeline and undo/redo stack
- One-click exports for social media
- Integration with Vex’s full agent capabilities (LLM-powered editing, Whisper transcription, FFmpeg rendering, etc.)

### Tech Stack
- **Backend**: Vex agent (forked/integrated)
- **Frontend**: Flet (Python + Flutter)
- **Video**: flet-video + FFmpeg
- **Packaging**: Flet build tools for macOS .app

---

This repository contains the source code for the desktop application.