"""In-process stub used until vex_core is checked out and wired."""

from __future__ import annotations

import shutil
from pathlib import Path

from vex_desktop.agent.errors import AgentError, ProjectError
from vex_desktop.exporting import looks_like_export, preset_suffix, resolve_preset
from vex_desktop.platform_support import data_dir
from vex_desktop.protocol import AgentResult, ProgressEvent, ProjectSnapshot


class StubBackend:
    name = "stub"

    def __init__(self) -> None:
        self._source_path: str | None = None
        self._working_file: str | None = None
        self._history: list[str] = []
        self._redo: list[str] = []
        self._provider = "gemini"
        self._model = "gemini"
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def load_project(self, video_path: str, progress) -> AgentResult:
        self._cancel = False
        path = Path(video_path)
        if not path.is_file():
            raise ProjectError(f"Video not found: {video_path}")
        progress(ProgressEvent("load_project", "open", f"Loading {path.name}"))
        self._source_path = str(path)
        self._working_file = str(path)
        self._history = []
        self._redo = []
        snapshot = self.snapshot()
        return AgentResult(
            op="load_project",
            success=True,
            message=f"Loaded {path.name} (stub backend — Vex core not connected).",
            snapshot=snapshot,
            new_video=snapshot.working_file,
        )

    def process_command(self, command: str, progress) -> AgentResult:
        self._cancel = False
        command = command.strip()
        if not command:
            raise AgentError("Empty command")
        if looks_like_export(command):
            preset = resolve_preset(command)
            if preset is None:
                raise AgentError("Unknown export preset.")
            result = self.export(preset, None, progress)
            result.op = "process_command"
            return result
        if self._working_file is None:
            raise ProjectError("Load a video before sending an edit.")
        progress(ProgressEvent("process_command", "plan", "Understanding the edit…"))
        progress(
            ProgressEvent(
                "process_command",
                "tool",
                "Stub: no FFmpeg run until vex_core is synced.",
                tool="stub",
            )
        )
        if self._cancel:
            raise AgentError("Cancelled")
        self._history.append(command)
        self._redo.clear()
        snapshot = self.snapshot()
        return AgentResult(
            op="process_command",
            success=True,
            message=f"Stub: would run {command!r} on {snapshot.working_file} with {self._provider}/{self._model}.",
            snapshot=snapshot,
            tools_called=["stub"],
            new_video=snapshot.working_file,
        )

    def undo(self, progress) -> AgentResult:
        if not self._history:
            raise AgentError("Nothing to undo.")
        progress(ProgressEvent("undo", "timeline", "Rebuilding previous cut…"))
        op = self._history.pop()
        self._redo.append(op)
        snapshot = self.snapshot()
        return AgentResult(
            op="undo",
            success=True,
            message=f"Undid: {op}",
            snapshot=snapshot,
            new_video=snapshot.working_file,
        )

    def redo(self, progress) -> AgentResult:
        if not self._redo:
            raise AgentError("Nothing to redo.")
        progress(ProgressEvent("redo", "timeline", "Re-applying edit…"))
        op = self._redo.pop()
        self._history.append(op)
        snapshot = self.snapshot()
        return AgentResult(
            op="redo",
            success=True,
            message=f"Redid: {op}",
            snapshot=snapshot,
            new_video=snapshot.working_file,
        )

    def snapshot(self) -> ProjectSnapshot:
        name = Path(self._source_path).name if self._source_path else None
        return ProjectSnapshot(
            project_id=None,
            project_name=name,
            source_path=self._source_path,
            working_file=self._working_file,
            history=list(self._history),
            can_undo=bool(self._history),
            can_redo=bool(self._redo),
            provider=self._provider,
            model=self._model,
            backend=self.name,
        )

    def export(self, preset: str, output_path: str | None, progress) -> AgentResult:
        self._cancel = False
        if self._working_file is None:
            raise ProjectError("Load a video before exporting.")
        source = Path(self._working_file)
        if not source.is_file():
            raise ProjectError(f"Working file missing: {source}")
        resolved = resolve_preset(preset) or preset
        suffix = preset_suffix(resolved)
        if output_path:
            dest = Path(output_path)
        else:
            dest = data_dir() / "exports" / f"{source.stem}_{resolved}{suffix}"
        progress(ProgressEvent("export", "encode", f"Exporting {resolved}…", tool="export_video"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        self._history.append(f"export {resolved}")
        self._redo.clear()
        snapshot = self.snapshot()
        exported = str(dest)
        preview = None if dest.suffix.lower() == ".mp3" else exported
        return AgentResult(
            op="export",
            success=True,
            message=f"Exported to {dest}",
            snapshot=snapshot,
            tools_called=["export_video"],
            new_video=preview,
            exported_path=exported,
        )

    def set_config(self, provider: str, model: str) -> AgentResult:
        self._provider = provider.strip() or self._provider
        self._model = model.strip() or self._model
        snapshot = self.snapshot()
        return AgentResult(
            op="set_config",
            success=True,
            message=f"Using {self._provider}/{self._model}.",
            snapshot=snapshot,
        )
