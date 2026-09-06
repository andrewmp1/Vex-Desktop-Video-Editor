"""Adapter for a local Vex install (AKMessi/vex).

The UI never imports this module. AgentService loads it only when a Vex
tree is on disk. Prefers the live checkout at ~/claude_work/vex.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from vex_desktop.agent.errors import AgentError, CoreUnavailable, ProjectError
from vex_desktop.exporting import exported_path_from_vex_message, resolve_preset
from vex_desktop.platform_support import (
    SECRET_ANTHROPIC,
    SECRET_GEMINI,
    SECRET_OPENAI,
    ffmpeg_path,
    get_secret,
    repo_root,
)
from vex_desktop.protocol import AgentResult, ProgressEvent, ProjectSnapshot


def vex_core_root() -> Path:
    override = os.environ.get("VEX_CORE_PATH")
    if override:
        return Path(override).expanduser().resolve()
    for candidate in (
        Path.home() / "claude_work" / "vex",
        repo_root() / "vex_core",
    ):
        if (candidate / "agent.py").is_file() and (candidate / "state.py").is_file():
            return candidate.resolve()
    return (Path.home() / "claude_work" / "vex").resolve()


def is_core_available() -> bool:
    root = vex_core_root()
    return (root / "agent.py").is_file() and (root / "state.py").is_file()


class VexCoreBackend:
    name = "core"

    def __init__(self) -> None:
        if not is_core_available():
            raise CoreUnavailable(
                "No Vex tree found. Set VEX_CORE_PATH or keep a checkout at ~/claude_work/vex."
            )
        self._root = vex_core_root()
        env_file = self._root / ".env"
        if env_file.is_file():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_file)
            except Exception:
                pass
        if str(self._root) not in sys.path:
            sys.path.insert(0, str(self._root))
        try:
            import config as vex_config
            from agent import VideoAgent
            from sources import extract_youtube_url
            from state import ProjectState
        except ModuleNotFoundError as exc:
            raise CoreUnavailable(
                f"Vex is at {self._root} but this Python env is missing {exc.name}. "
                "Run the desktop app with ~/claude_work/vex/.venv (after pip install PySide6 platformdirs)."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise CoreUnavailable(f"Failed to import Vex from {self._root}: {exc}") from exc

        if hasattr(vex_config, "reload_settings"):
            vex_config.reload_settings()
        self._config = vex_config
        self._VideoAgent = VideoAgent
        self._ProjectState = ProjectState
        self._extract_youtube_url = extract_youtube_url
        ffmpeg = ffmpeg_path()
        if ffmpeg:
            self._config.FFMPEG_PATH = ffmpeg
        gemini_key = get_secret(SECRET_GEMINI)
        if gemini_key:
            self._config.GEMINI_API_KEY = gemini_key
        anthropic_key = get_secret(SECRET_ANTHROPIC)
        if anthropic_key:
            self._config.ANTHROPIC_API_KEY = anthropic_key
        openai_key = get_secret(SECRET_OPENAI)
        if openai_key and hasattr(self._config, "OPENAI_COMPAT_API_KEY"):
            self._config.OPENAI_COMPAT_API_KEY = openai_key
        self._create_project = None
        self._create_project_from_youtube = None
        self._find_project_for_source_url = None
        try:
            from main import (
                create_project,
                create_project_from_youtube,
                find_project_for_source_url,
                initialize_runtime,
            )

            initialize_runtime(require_provider=False)
            self._create_project = create_project
            self._create_project_from_youtube = create_project_from_youtube
            self._find_project_for_source_url = find_project_for_source_url
        except SystemExit as exc:
            raise CoreUnavailable(f"Vex config failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise CoreUnavailable(f"Failed to initialize Vex runtime: {exc}") from exc

        self._state: Any = None
        self._provider_name = str(getattr(self._config, "PROVIDER", "gemini") or "gemini")
        self._model = str(getattr(self._config, "GEMINI_MODEL", "") or "gemini")
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def load_project(self, video_path: str, progress) -> AgentResult:
        self._cancel = False
        source = video_path.strip().strip('"').strip("'")
        url = self._extract_youtube_url(source)
        if url:
            progress(ProgressEvent("load_project", "youtube", f"Loading {url}"))
            existing = None
            if self._find_project_for_source_url is not None:
                existing = self._find_project_for_source_url(url)
            if existing is not None:
                self._state = existing
                snapshot = self.snapshot()
                return AgentResult(
                    op="load_project",
                    success=True,
                    message=f"Resumed project {snapshot.project_name}",
                    snapshot=snapshot,
                    new_video=snapshot.working_file,
                )
            if self._create_project_from_youtube is None:
                raise ProjectError("YouTube ingest is unavailable in this Vex tree.")
            progress(ProgressEvent("load_project", "download", "Downloading with yt-dlp…"))
            self._state = self._create_project_from_youtube(
                url, None, self._provider_name, self._model
            )
            snapshot = self.snapshot()
            return AgentResult(
                op="load_project",
                success=True,
                message=f"Downloaded {snapshot.project_name}",
                snapshot=snapshot,
                new_video=snapshot.working_file,
            )

        path = Path(source).expanduser()
        if path.is_file():
            progress(ProgressEvent("load_project", "open", f"Creating project from {path.name}"))
            if self._create_project is None:
                raise ProjectError("create_project is unavailable in this Vex tree.")
            self._state = self._create_project(
                str(path.resolve()), None, self._provider_name, self._model
            )
            snapshot = self.snapshot()
            return AgentResult(
                op="load_project",
                success=True,
                message=f"Loaded {path.name}",
                snapshot=snapshot,
                new_video=snapshot.working_file,
            )

        try:
            self._state = self._ProjectState.load(source)
        except Exception as exc:
            raise ProjectError(f"Video not found: {video_path}") from exc
        snapshot = self.snapshot()
        return AgentResult(
            op="load_project",
            success=True,
            message=f"Opened project {snapshot.project_name}",
            snapshot=snapshot,
            new_video=snapshot.working_file,
        )

    def process_command(self, command: str, progress) -> AgentResult:
        self._cancel = False
        command = command.strip()
        if not command:
            raise AgentError("Empty command")
        if self._state is None:
            url = self._extract_youtube_url(command)
            path = Path(command).expanduser()
            if url or path.is_file():
                loaded = self.load_project(command if path.is_file() else (url or command), progress)
                remainder = command
                if url and remainder == url:
                    return loaded
                if path.is_file() and remainder in {str(path), str(path.resolve())}:
                    return loaded
            else:
                raise ProjectError("Load a video or paste a YouTube URL first.")
        progress(ProgressEvent("process_command", "plan", "Running Vex agent…"))
        provider = self._make_provider()
        video_agent = self._VideoAgent(self._state, provider)

        def trace_callback(event) -> None:
            title = getattr(event, "title", "") or "Working…"
            kind = getattr(event, "kind", "agent")
            progress(ProgressEvent("process_command", str(kind), str(title)))

        try:
            response = video_agent.run(command, trace_callback=trace_callback)
        except Exception as exc:  # noqa: BLE001
            raise AgentError(str(exc)) from exc
        self._state = video_agent.state
        snapshot = self.snapshot()
        success = bool(getattr(response, "success", True))
        message = str(getattr(response, "message", "") or "Done.")
        tools = list(getattr(response, "tools_called", []) or [])
        exported = exported_path_from_vex_message(message) if "export_video" in tools else None
        return AgentResult(
            op="process_command",
            success=success,
            message=message,
            snapshot=snapshot,
            tools_called=tools,
            suggestions=list(getattr(response, "suggestions", []) or []),
            new_video=exported or snapshot.working_file,
            exported_path=exported,
        )

    def undo(self, progress) -> AgentResult:
        if self._state is None:
            raise ProjectError("No project loaded.")
        progress(ProgressEvent("undo", "timeline", "Undo"))
        op = self._state.undo()
        if op is None:
            raise AgentError("Nothing to undo.")
        snapshot = self.snapshot()
        return AgentResult(
            op="undo",
            success=True,
            message=f"Undid {op.get('op', 'edit')}",
            snapshot=snapshot,
            new_video=snapshot.working_file,
        )

    def redo(self, progress) -> AgentResult:
        if self._state is None:
            raise ProjectError("No project loaded.")
        progress(ProgressEvent("redo", "timeline", "Redo"))
        op = self._state.redo()
        if op is None:
            raise AgentError("Nothing to redo.")
        snapshot = self.snapshot()
        return AgentResult(
            op="redo",
            success=True,
            message=f"Redid {op.get('op', 'edit')}",
            snapshot=snapshot,
            new_video=snapshot.working_file,
        )

    def snapshot(self) -> ProjectSnapshot:
        state = self._state
        if state is None:
            return ProjectSnapshot(backend=self.name, provider=self._provider_name, model=self._model)
        history = [
            str(op.get("description") or op.get("op") or "edit")
            for op in (state.timeline or [])
        ]
        source = (state.source_files or [None])[0]
        source_url = None
        artifacts = getattr(state, "artifacts", None) or {}
        if isinstance(artifacts, dict):
            source_url = artifacts.get("source_url")
        return ProjectSnapshot(
            project_id=state.project_id,
            project_name=state.project_name,
            source_path=source_url or source,
            working_file=state.working_file,
            history=history,
            can_undo=bool(state.timeline),
            can_redo=bool(state.redo_stack),
            provider=state.provider or self._provider_name,
            model=state.model or self._model,
            backend=self.name,
        )

    def export(self, preset: str, output_path: str | None, progress) -> AgentResult:
        if self._state is None:
            raise ProjectError("Load a video before exporting.")
        resolved = resolve_preset(preset) or preset
        progress(ProgressEvent("export", "encode", f"Exporting {resolved}…", tool="export_video"))
        try:
            from tools.export import execute
        except Exception as exc:  # noqa: BLE001
            raise AgentError(f"Vex export tool is unavailable: {exc}") from exc
        params: dict[str, Any] = {"preset_name": resolved}
        if output_path:
            params["output_path"] = output_path
        result = execute(params, self._state)
        self._state = result.get("updated_state", self._state)
        message = str(result.get("message") or "")
        if not result.get("success"):
            raise AgentError(message or "Export failed.")
        saved = output_path or exported_path_from_vex_message(message)
        snapshot = self.snapshot()
        preview = saved if saved and not str(saved).lower().endswith(".mp3") else snapshot.working_file
        return AgentResult(
            op="export",
            success=True,
            message=message or f"Exported to {saved}",
            snapshot=snapshot,
            tools_called=["export_video"],
            new_video=preview,
            exported_path=saved,
        )

    def set_config(self, provider: str, model: str) -> AgentResult:
        self._provider_name = provider.strip() or self._provider_name
        self._model = model.strip() or self._model
        if self._state is not None:
            self._state.provider = self._provider_name
            self._state.model = self._model
            self._state.save()
        snapshot = self.snapshot()
        return AgentResult(
            op="set_config",
            success=True,
            message=f"Using {self._provider_name}/{self._model}.",
            snapshot=snapshot,
        )

    def _make_provider(self):
        try:
            from providers import get_provider
        except Exception as exc:  # noqa: BLE001
            raise AgentError(f"Could not create LLM provider: {exc}") from exc
        if self._model:
            if self._provider_name == "claude":
                self._config.CLAUDE_MODEL = self._model
            elif self._provider_name in {"ollama", "openai_compatible", "lmstudio", "llama_cpp"}:
                for attr in ("OLLAMA_MODEL", "OPENAI_COMPAT_MODEL", "LM_STUDIO_MODEL", "LLAMA_CPP_MODEL"):
                    if hasattr(self._config, attr):
                        setattr(self._config, attr, self._model)
            else:
                self._config.GEMINI_MODEL = self._model
        try:
            return get_provider(self._provider_name)
        except Exception as exc:  # noqa: BLE001
            raise AgentError(f"Could not create LLM provider: {exc}") from exc
