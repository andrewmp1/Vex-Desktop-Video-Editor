# Vex Desktop Video Editor - Project Plan

## Objective
Build a polished desktop video editing application by integrating the Vex AI agent with a modern Flet-based GUI.

## Phases

### Phase 1: Foundation & Setup (1-2 days)
- [x] Create private GitHub repository
- [x] Initialize project structure (src/, docs/, assets/)
- [ ] Set up Python environment, requirements.txt, and Flet basics
- [ ] Create initial Flet main.py with basic layout (video preview + chat)
- [ ] Add docs/ folder with this plan and overview

### Phase 2: Vex Agent Integration (3-5 days)
- Wrap Vex core into a clean Python library/API (`vex_agent.py`)
- Run agent in background thread
- Implement command processing with progress streaming to UI
- Handle project state, timeline, and video file management

### Phase 3: Core GUI Development (1-2 weeks)
- Video preview pane using flet-video
- Natural language chat interface
- Timeline / history panel
- Drag-and-drop video import
- Settings panel (API keys, model selection)
- Dark mode + macOS-native styling

### Phase 4: Advanced Features
- Live preview updates after edits
- Undo/redo integration
- Export presets (social media formats)
- B-roll, subtitles, effects via natural language
- Local model support (Ollama)
- Project save/load (.vex or folder-based)

### Phase 5: Packaging & Distribution
- Build macOS .app bundle
- Bundle FFmpeg binary
- Code signing and notarization
- Auto-update system
- Windows & Linux support

### Phase 6: Polish & Release
- Testing with real video workflows
- Performance optimization
- User documentation
- Public release (GitHub + optional Mac App Store)

## Success Criteria
- Users can load a video and make meaningful edits via natural language
- UI remains responsive during long operations
- Application bundles cleanly as a standalone macOS app
- Maintains or exceeds the capabilities of the original Vex CLI

**Target MVP Completion**: 3-4 weeks with focused effort.