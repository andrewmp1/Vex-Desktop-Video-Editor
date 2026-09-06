"""Qt client. The only agent API the UI is allowed to import."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from vex_desktop.agent.errors import AgentError
from vex_desktop.agent.service import AgentService
from vex_desktop.protocol import AgentResult, ProgressEvent


class _Worker(QObject):
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, service: AgentService):
        super().__init__()
        self._service = service

    @Slot(str, dict)
    def handle(self, op: str, payload: dict) -> None:
        try:

            def on_progress(event: ProgressEvent) -> None:
                self.progress.emit(event)

            result = self._service.handle(op, payload, on_progress)
        except AgentError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Agent failed: {exc}")
        else:
            self.finished.emit(result)

    @Slot()
    def cancel(self) -> None:
        self._service.cancel()


class AgentClient(QObject):
    """Fire-and-forget client. All Vex work runs on a worker thread."""

    _submit_op = Signal(str, dict)
    _cancel_op = Signal()

    progress = Signal(object)
    result_ready = Signal(object)
    failed = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None, service: AgentService | None = None):
        super().__init__(parent)
        self._busy = False
        resolved = service or AgentService()
        self._backend_name = resolved.backend_name
        self._thread = QThread(self)
        self._worker = _Worker(resolved)
        self._worker.moveToThread(self._thread)
        self._submit_op.connect(self._worker.handle)
        self._cancel_op.connect(self._worker.cancel)
        self._worker.progress.connect(self.progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def load_project(self, video_path: str) -> None:
        self._submit("load_project", {"video_path": video_path})

    def process_command(self, command: str) -> None:
        self._submit("process_command", {"command": command})

    def undo(self) -> None:
        self._submit("undo", {})

    def redo(self) -> None:
        self._submit("redo", {})

    def refresh(self) -> None:
        self._submit("snapshot", {})

    def set_config(self, provider: str, model: str) -> None:
        self._submit("set_config", {"provider": provider, "model": model})

    def export(self, preset: str = "youtube_1080p", output_path: str | None = None) -> None:
        payload: dict = {"preset": preset}
        if output_path:
            payload["output_path"] = output_path
        self._submit("export", payload)

    def cancel(self) -> None:
        self._cancel_op.emit()

    def shutdown(self) -> None:
        self._thread.quit()
        self._thread.wait(2000)

    def _submit(self, op: str, payload: dict) -> None:
        if self._busy:
            self.failed.emit("Agent is busy.")
            return
        self._set_busy(True)
        self._submit_op.emit(op, payload)

    @Slot(object)
    def _on_finished(self, result: AgentResult) -> None:
        self._set_busy(False)
        self.result_ready.emit(result)

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.failed.emit(message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.busy_changed.emit(busy)
