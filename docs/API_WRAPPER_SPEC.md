# API Wrapper Specification

## `VexAgent` Class

This wrapper turns the original Vex CLI agent into a clean, callable library for the Flet GUI.

### Core Methods

```python
class VexAgent:
    def __init__(self, project_path: str = None, model: str = "gemini"):
        ...

    def process_command(self, command: str) -> CommandResult:
        """Execute natural language command and return result."""

    def load_project(self, video_path: str) -> ProjectState:
        """Create or load a Vex project."""

    def get_timeline(self) -> dict:
        """Return current timeline/state as JSON-serializable dict."""

    def undo(self) -> bool:
        """Undo last operation."""

    async def process_command_async(self, command: str):
        """For streaming progress in UI."""
```

## Events & Callbacks

- Progress callbacks for long-running operations (FFmpeg renders, LLM calls)
- State change listeners for live UI updates

## Error Handling

Standardized exceptions with user-friendly messages.

See `src/vex_agent.py` for implementation details (to be created).