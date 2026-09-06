from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def titled_pane(title: str, body: QWidget) -> QWidget:
    frame = QFrame()
    frame.setObjectName("pane")
    header = QLabel(title)
    header.setObjectName("paneTitle")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(header)
    layout.addWidget(body, stretch=1)
    return frame
