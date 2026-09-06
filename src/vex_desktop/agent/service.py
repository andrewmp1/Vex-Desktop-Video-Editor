"""Blocking agent service. No Qt.

The GUI talks to this through AgentClient (QThread) or JSONL stdio.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from vex_desktop.agent.backend import AgentBackend
from vex_desktop.agent.core import VexCoreBackend, is_core_available
from vex_desktop.agent.errors import AgentError, CoreUnavailable
from vex_desktop.agent.stub import StubBackend
from vex_desktop.protocol import OPS, AgentResult, ProgressEvent


ProgressFn = Callable[[ProgressEvent], None]


def create_backend(mode: str | None = None) -> AgentBackend:
    selected = (mode or os.environ.get("VEX_AGENT_BACKEND") or "auto").strip().lower()
    if selected == "stub":
        return StubBackend()
    if selected == "core":
        return VexCoreBackend()
    if selected == "auto":
        if is_core_available():
            try:
                return VexCoreBackend()
            except CoreUnavailable:
                return StubBackend()
        return StubBackend()
    raise AgentError(f"Unknown agent backend: {selected}")


class AgentService:
    def __init__(self, backend: AgentBackend | None = None):
        self._backend = backend or create_backend()

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def cancel(self) -> None:
        self._backend.cancel()

    def handle(self, op: str, payload: dict, progress: ProgressFn | None = None) -> AgentResult:
        if op not in OPS:
            raise AgentError(f"Unknown agent op: {op}")
        emit = progress or (lambda _event: None)
        if op == "cancel":
            self.cancel()
            return AgentResult(
                op="cancel",
                success=True,
                message="Cancel requested.",
                snapshot=self._backend.snapshot(),
            )
        if op == "snapshot":
            snapshot = self._backend.snapshot()
            return AgentResult(
                op="snapshot",
                success=True,
                message="",
                snapshot=snapshot,
                new_video=snapshot.working_file,
            )
        if op == "load_project":
            return self._backend.load_project(str(payload.get("video_path") or ""), emit)
        if op == "process_command":
            return self._backend.process_command(str(payload.get("command") or ""), emit)
        if op == "undo":
            return self._backend.undo(emit)
        if op == "redo":
            return self._backend.redo(emit)
        if op == "set_config":
            return self._backend.set_config(
                str(payload.get("provider") or ""),
                str(payload.get("model") or ""),
            )
        if op == "export":
            preset = str(payload.get("preset") or payload.get("preset_name") or "youtube_1080p")
            output_path = payload.get("output_path")
            return self._backend.export(
                preset,
                str(output_path) if output_path else None,
                emit,
            )
        raise AgentError(f"Unhandled op: {op}")
