from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vex_desktop.projects_index import list_projects


class OpenProjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Open Project")
        self.resize(560, 420)
        self._projects = list_projects()

        self._list = QListWidget()
        for project in self._projects:
            label = project["project_name"]
            extra = project["source_url"] or project["working_file"]
            item = QListWidgetItem(f"{label}\n{extra}")
            item.setData(Qt.ItemDataRole.UserRole, project)
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())

        hint = QLabel("Projects from ~/.video-agent/projects (same as the Vex CLI).")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        if not self._projects:
            hint.setText("No Vex projects found yet. Open a video or paste a YouTube URL.")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(bool(self._projects))

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self._list, stretch=1)
        layout.addWidget(buttons)

    def selected_project(self) -> dict | None:
        item = self._list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return dict(value) if isinstance(value, dict) else None
