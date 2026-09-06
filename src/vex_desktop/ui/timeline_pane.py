from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
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


class TimelinePane(QWidget):
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._name = QLabel("No project")
        self._name.setObjectName("clipTitle")
        self._name.setWordWrap(True)
        self._name.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._meta = QLabel("Open a video to start a timeline.")
        self._meta.setObjectName("hintLabel")
        self._meta.setWordWrap(True)
        self._meta.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

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
        layout.addWidget(self._empty)
        layout.addWidget(self._scroll, stretch=1)
        layout.addLayout(buttons)

    def apply_snapshot(self, snapshot: ProjectSnapshot) -> None:
        name = snapshot.project_name or "Untitled project"
        self._name.setText(name)
        self._meta.setText(_meta_line(snapshot))
        self._set_history(snapshot.history)
        self._empty.setVisible(not snapshot.history)
        self._undo.setEnabled(snapshot.can_undo)
        self._redo.setEnabled(snapshot.can_redo)

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
