from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from vex_desktop.protocol import ProjectSnapshot
from vex_desktop.ui.thumbs import extract_thumbnails


class _ThumbJob(QObject):
    finished = Signal(object, object)

    def __init__(self, path: str, stamp: tuple[str, int, int]):
        super().__init__()
        self.path = path
        self.stamp = stamp
        self.cancel = threading.Event()

    @Slot()
    def run(self) -> None:
        frames: list = []
        try:
            frames = extract_thumbnails(self.path, cancel=self.cancel)
        except Exception:
            frames = []
        self.finished.emit(self.stamp, frames)


class _ThumbFrame(QFrame):
    clicked = Signal(int)

    def __init__(self, ms: int, image: QImage, parent: QWidget | None = None):
        super().__init__(parent)
        self.ms = ms
        self.setObjectName("timelineThumb")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        picture = QLabel()
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        picture.setPixmap(QPixmap.fromImage(image))
        caption = QLabel(_fmt_ms(ms))
        caption.setObjectName("hintLabel")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(picture)
        layout.addWidget(caption)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.ms)
        super().mousePressEvent(event)


class TimelinePane(QWidget):
    undo_requested = Signal()
    redo_requested = Signal()
    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._thumb_stamp: tuple[str, int, int] | None = None
        self._pending_stamp: tuple[str, int, int] | None = None
        self._playhead_ms = 0
        self._current_thumb: _ThumbFrame | None = None
        self._thumbs: list[_ThumbFrame] = []
        self._thread: QThread | None = None
        self._job: _ThumbJob | None = None

        self._name = QLabel("No project")
        self._name.setObjectName("clipTitle")
        self._name.setWordWrap(True)
        self._name.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._meta = QLabel("Open a video to start a timeline.")
        self._meta.setObjectName("hintLabel")
        self._meta.setWordWrap(True)
        self._meta.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self._strip_host = QWidget()
        self._strip_layout = QHBoxLayout(self._strip_host)
        self._strip_layout.setContentsMargins(0, 0, 0, 0)
        self._strip_layout.setSpacing(6)
        self._strip_layout.addStretch(1)

        self._strip = QScrollArea()
        self._strip.setWidgetResizable(True)
        self._strip.setFrameShape(QFrame.Shape.NoFrame)
        self._strip.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._strip.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._strip.setFixedHeight(118)
        self._strip.setWidget(self._strip_host)
        self._strip.hide()

        self._empty = QLabel("History will appear here after edits.")
        self._empty.setObjectName("hintLabel")
        self._empty.setWordWrap(True)
        self._empty.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self._history_host = QWidget()
        self._history_layout = QVBoxLayout(self._history_host)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(8)
        self._history_layout.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._history_host)

        self._undo = QPushButton("Undo")
        self._undo.setEnabled(False)
        self._undo.clicked.connect(self.undo_requested.emit)
        self._redo = QPushButton("Redo")
        self._redo.setEnabled(False)
        self._redo.clicked.connect(self.redo_requested.emit)

        buttons = QHBoxLayout()
        buttons.addWidget(self._undo)
        buttons.addWidget(self._redo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.addWidget(self._name)
        layout.addWidget(self._meta)
        layout.addWidget(self._strip)
        layout.addWidget(self._empty)
        layout.addWidget(self._scroll, stretch=1)
        layout.addLayout(buttons)

    def thumbnail_count(self) -> int:
        return len(self._thumbs)

    def apply_snapshot(self, snapshot: ProjectSnapshot) -> None:
        name = snapshot.project_name or "Untitled project"
        self._name.setText(name)
        self._meta.setText(_meta_line(snapshot))
        self._set_history(snapshot.history)
        self._empty.setVisible(not snapshot.history)
        self._undo.setEnabled(snapshot.can_undo)
        self._redo.setEnabled(snapshot.can_redo)
        self._request_thumbs(snapshot.working_file)

    def set_playhead(self, ms: int) -> None:
        self._playhead_ms = max(0, int(ms))
        if not self._thumbs:
            return
        nearest = min(self._thumbs, key=lambda thumb: abs(thumb.ms - self._playhead_ms))
        if nearest is self._current_thumb:
            return
        if self._current_thumb is not None:
            self._current_thumb.setProperty("current", False)
            self._current_thumb.style().unpolish(self._current_thumb)
            self._current_thumb.style().polish(self._current_thumb)
        nearest.setProperty("current", True)
        nearest.style().unpolish(nearest)
        nearest.style().polish(nearest)
        self._current_thumb = nearest

    def _request_thumbs(self, working_file: str | None) -> None:
        stamp = _file_stamp(working_file)
        if stamp == self._thumb_stamp and (self._thumbs or self._job_running()):
            return
        self._thumb_stamp = stamp
        if self._job_running():
            self._pending_stamp = stamp
            if self._job is not None:
                self._job.cancel.set()
            return
        self._pending_stamp = None
        if stamp is None:
            self._clear_thumbs()
            return
        self._launch(stamp)

    def _job_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _launch(self, stamp: tuple[str, int, int]) -> None:
        self._thread = QThread(self)
        self._job = _ThumbJob(stamp[0], stamp)
        self._job.moveToThread(self._thread)
        self._thread.started.connect(self._job.run)
        self._job.finished.connect(self._on_thumbs)
        self._job.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def shutdown(self) -> None:
        self._pending_stamp = None
        if self._job is not None:
            self._job.cancel.set()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(8000)

    def _on_thread_finished(self) -> None:
        if self.sender() is not self._thread:
            return
        self._thread = None
        self._job = None

    @Slot(object, object)
    def _on_thumbs(self, stamp: object, frames: object) -> None:
        if self._pending_stamp is not None:
            nxt = self._pending_stamp
            self._pending_stamp = None
            self._thumb_stamp = nxt
            if nxt is None:
                self._clear_thumbs()
                return
            self._launch(nxt)
            return
        if stamp != self._thumb_stamp:
            return
        if not isinstance(frames, list):
            return
        self._clear_thumbs()
        for ms, image in frames:
            if not isinstance(image, QImage) or image.isNull():
                continue
            thumb = _ThumbFrame(int(ms), image)
            thumb.clicked.connect(self.seek_requested.emit)
            self._strip_layout.insertWidget(len(self._thumbs), thumb)
            self._thumbs.append(thumb)
        self._strip.setVisible(bool(self._thumbs))
        if self._thumbs:
            self.set_playhead(self._playhead_ms)

    def _clear_thumbs(self) -> None:
        for thumb in self._thumbs:
            self._strip_layout.removeWidget(thumb)
            thumb.deleteLater()
        self._thumbs.clear()
        self._current_thumb = None
        self._strip.hide()

    def _set_history(self, entries: list[str]) -> None:
        while self._history_layout.count() > 1:
            item = self._history_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, entry in enumerate(entries, start=1):
            label = QLabel(f"{index}. {entry}")
            label.setObjectName("historyItem")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            self._history_layout.insertWidget(index - 1, label)


def _file_stamp(path: str | None) -> tuple[str, int, int] | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        return None
    stat = file_path.stat()
    return (str(file_path), int(stat.st_mtime_ns), int(stat.st_size))


def _meta_line(snapshot: ProjectSnapshot) -> str:
    bits: list[str] = []
    if snapshot.backend:
        bits.append(snapshot.backend)
    project_id = (snapshot.project_id or "").strip()
    if project_id and project_id not in {snapshot.backend, snapshot.project_name}:
        bits.append(project_id[:8] if len(project_id) > 8 else project_id)
    file_name = Path(snapshot.working_file).name if snapshot.working_file else ""
    if file_name and file_name != (snapshot.project_name or ""):
        bits.append(file_name)
    return " · ".join(bits) if bits else "No clip yet."


def _fmt_ms(ms: int) -> str:
    seconds = max(ms, 0) // 1000
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
