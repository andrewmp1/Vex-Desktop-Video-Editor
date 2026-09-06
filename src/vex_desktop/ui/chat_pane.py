from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ChatPane(QWidget):
    command_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._messages: list[tuple[str, str, str]] = []
        self._progress: str | None = None
        self._bubbles: list[QWidget] = []
        self._progress_bubble: QWidget | None = None

        self._host = QWidget()
        self._host_layout = QVBoxLayout(self._host)
        self._host_layout.setContentsMargins(4, 4, 4, 16)
        self._host_layout.setSpacing(12)
        self._host_layout.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._host)

        self._input = QLineEdit()
        self._input.setPlaceholderText(
            'Describe an edit, or paste a YouTube URL — e.g. "Trim the first 10 seconds"'
        )
        self._input.returnPressed.connect(self._submit)

        self._send = QPushButton("Send")
        self._send.setObjectName("primaryButton")
        self._send.clicked.connect(self._submit)

        row = QHBoxLayout()
        row.addWidget(self._input, stretch=1)
        row.addWidget(self._send)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.addWidget(self._scroll, stretch=1)
        layout.addLayout(row)

        self.append_system(
            "Open a video, an existing Vex project, or paste a YouTube URL. "
            "Then describe the edit in plain language."
        )

    def append_user(self, text: str) -> None:
        self._messages.append(("you", "You", text))
        self._add_bubble("you", "You", text)
        self._scroll_to_bottom()

    def append_agent(self, text: str) -> None:
        self.clear_progress()
        self._messages.append(("vex", "Vex", text))
        self._add_bubble("vex", "Vex", text)
        self._scroll_to_bottom()

    def append_system(self, text: str) -> None:
        self._messages.append(("system", "System", text))
        self._add_bubble("system", "System", text)
        self._scroll_to_bottom()

    def set_progress(self, text: str) -> None:
        self._progress = text
        if self._progress_bubble is None:
            self._progress_bubble = self._add_bubble("progress", "Vex", text)
        else:
            body = self._progress_bubble.findChild(QLabel, "chatBody")
            if body is not None:
                body.setText(text)
        self._scroll_to_bottom()

    def clear_progress(self) -> None:
        self._progress = None
        if self._progress_bubble is not None:
            self._progress_bubble.deleteLater()
            self._progress_bubble = None

    def set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send.setEnabled(not busy)
        if not busy:
            self.clear_progress()

    def focus_input(self) -> None:
        self._input.setFocus()

    def transcript(self) -> str:
        lines = [f"{who}: {text}" for _kind, who, text in self._messages]
        if self._progress:
            lines.append(f"Vex: {self._progress}")
        return "\n".join(lines)

    def submit_text(self, text: str) -> None:
        self._input.setText(text)
        self._submit()

    def _add_bubble(self, kind: str, who: str, text: str) -> QWidget:
        frame = QFrame()
        frame.setObjectName(f"chatBubble_{kind}")
        who_label = QLabel(who)
        who_label.setObjectName("chatWho")
        body = QLabel(text)
        body.setObjectName("chatBody")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        column = QVBoxLayout(frame)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        column.addWidget(who_label)
        column.addWidget(body)
        stretch = self._host_layout.count() - 1
        self._host_layout.insertWidget(max(stretch, 0), frame)
        self._bubbles.append(frame)
        return frame

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, self._jump_bottom)

    def _jump_bottom(self) -> None:
        target = self._progress_bubble or (self._bubbles[-1] if self._bubbles else None)
        if target is not None:
            self._scroll.ensureWidgetVisible(target, 0, 12)
            return
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    @Slot()
    def _submit(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.append_user(text)
        self.command_submitted.emit(text)
