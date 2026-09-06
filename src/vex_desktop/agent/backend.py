from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from vex_desktop.protocol import AgentResult, ProgressEvent, ProjectSnapshot

ProgressFn = Callable[[ProgressEvent], None]


class AgentBackend(Protocol):
    """Blocking backend. The Qt UI never calls this directly."""

    name: str

    def load_project(self, video_path: str, progress: ProgressFn) -> AgentResult: ...

    def process_command(self, command: str, progress: ProgressFn) -> AgentResult: ...

    def undo(self, progress: ProgressFn) -> AgentResult: ...

    def redo(self, progress: ProgressFn) -> AgentResult: ...

    def snapshot(self) -> ProjectSnapshot: ...

    def set_config(self, provider: str, model: str) -> AgentResult: ...

    def export(
        self,
        preset: str,
        output_path: str | None,
        progress: ProgressFn,
    ) -> AgentResult: ...

    def cancel(self) -> None: ...
