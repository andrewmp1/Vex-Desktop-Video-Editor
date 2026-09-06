"""Skills dialog. All file changes go through AgentClient ops."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from vex_desktop.agent.qt import AgentClient
from vex_desktop.protocol import AgentResult

TRUST_NOTICE = (
    "Skills are instructions the AI agent will follow while editing. Only add files you trust."
)
EMPTY_HINT = "Drop SKILL.md files here"
_SKILL_OPS = frozenset({"list_skills", "import_skill", "remove_skill", "set_skills"})


class _SkillRow(QFrame):
    clicked = Signal(str)
    toggled = Signal(str, bool)

    def __init__(self, skill: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("skillRow")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._skill_id = str(skill["id"])

        self.checkbox = QCheckBox()
        self.checkbox.setObjectName(f"skillCheckbox_{self._skill_id}")
        self.checkbox.setEnabled(False)
        self.checkbox.setChecked(bool(skill.get("enabled")))
        self.checkbox.toggled.connect(
            lambda checked, sid=self._skill_id: self.toggled.emit(sid, checked)
        )

        name = QLabel(str(skill.get("name") or self._skill_id))
        desc = QLabel(str(skill.get("description") or ""))
        desc.setObjectName("hintLabel")
        desc.setWordWrap(True)
        chars = QLabel(f"{int(skill.get('chars') or 0)} chars")
        chars.setObjectName("hintLabel")

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        text.addWidget(name)
        if skill.get("description"):
            text.addWidget(desc)
        text.addWidget(chars)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text, 1)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._skill_id)
        super().mousePressEvent(event)


class _SkillList(QScrollArea):
    currentRowChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("skillsList")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._host = QWidget()
        self._layout = QVBoxLayout(self._host)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.addStretch(1)
        self.setWidget(self._host)
        self._rows: list[_SkillRow] = []
        self._current = -1

    def count(self) -> int:
        return len(self._rows)

    def currentRow(self) -> int:
        return self._current

    def setCurrentRow(self, row: int) -> None:
        if row < 0 or row >= len(self._rows):
            if self._current != -1:
                self._current = -1
                self._refresh_highlight()
                self.currentRowChanged.emit(-1)
            return
        if row == self._current:
            self.currentRowChanged.emit(row)
            return
        self._current = row
        self._refresh_highlight()
        self.currentRowChanged.emit(row)

    def clear(self) -> None:
        self._current = -1
        rows = self._rows
        self._rows = []
        for row in rows:
            self._layout.removeWidget(row)
            row.hide()
            row.setParent(None)

    def add_row(self, row: _SkillRow) -> None:
        index = len(self._rows)
        self._rows.append(row)
        self._layout.insertWidget(index, row)
        row.clicked.connect(lambda _sid, i=index: self.setCurrentRow(i))

    def _refresh_highlight(self) -> None:
        for index, row in enumerate(self._rows):
            row.setProperty("selected", index == self._current)
            row.style().unpolish(row)
            row.style().polish(row)


class SkillsDialog(QDialog):
    def __init__(self, parent: QWidget | None, client: AgentClient) -> None:
        super().__init__(parent)
        self.setWindowTitle("Skills")
        self.setObjectName("skillsDialog")
        self.resize(860, 520)
        self.setAcceptDrops(True)
        self.setModal(True)

        self._client = client
        self._skills: list[dict] = []
        self._viewed: set[str] = set()
        self._checkboxes: dict[str, QCheckBox] = {}
        self._import_queue: list[str] = []
        self._updating = False
        self._connected = False

        self._notice = QLabel(TRUST_NOTICE)
        self._notice.setObjectName("skillsTrustNotice")
        self._notice.setWordWrap(True)

        self._empty = QLabel(EMPTY_HINT)
        self._empty.setObjectName("skillsEmptyHint")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)

        self._list = _SkillList()
        self._list.currentRowChanged.connect(self._on_row_changed)

        self._preview = QPlainTextEdit()
        self._preview.setObjectName("skillsPreview")
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("Select a skill to preview its contents.")

        self._add_btn = QPushButton("Add…")
        self._add_btn.setObjectName("skillsAddButton")
        self._add_btn.setToolTip("Add a SKILL.md file. Drop a skill folder on this dialog.")
        self._add_btn.clicked.connect(self._add_skill)
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.setObjectName("skillsRemoveButton")
        self._remove_btn.setEnabled(False)
        self._remove_btn.clicked.connect(self._remove_skill)

        self._status = QLabel("")
        self._status.setObjectName("hintLabel")
        self._status.setWordWrap(True)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._empty)
        left_layout.addWidget(self._list, stretch=1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([320, 500])

        buttons = QHBoxLayout()
        buttons.addWidget(self._add_btn)
        buttons.addWidget(self._remove_btn)
        buttons.addStretch(1)
        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        close_box.accepted.connect(self.accept)
        buttons.addWidget(close_box)

        layout = QVBoxLayout(self)
        layout.addWidget(self._notice)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self._status)
        layout.addLayout(buttons)

        self._apply_catalog([])
        self._client.result_ready.connect(self._on_result)
        self._client.failed.connect(self._on_failed)
        self._client.busy_changed.connect(self._on_busy)
        self._connected = True
        if not self._client.busy:
            self._client.list_skills()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._disconnect_client()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        self._disconnect_client()
        super().done(result)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._drop_paths(event):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = self._drop_paths(event)
        if not paths:
            return
        event.acceptProposedAction()
        for path in paths:
            self._import_path(path)

    def _drop_paths(self, event: QDragEnterEvent | QDropEvent) -> list[str]:
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return []
        paths: list[str] = []
        for url in mime.urls():
            path = url.toLocalFile()
            if not path:
                continue
            source = Path(path)
            if source.is_dir() or source.suffix.lower() == ".md":
                paths.append(path)
        return paths

    @Slot()
    def _add_skill(self) -> None:
        path, selected_filter = QFileDialog.getOpenFileName(
            self,
            "Add Skill",
            str(Path.home()),
            "Skill files (*.md);;Skill folder (*);;All files (*)",
        )
        if not path and "folder" in (selected_filter or "").lower():
            path = QFileDialog.getExistingDirectory(self, "Add Skill Folder", str(Path.home()))
        if path:
            self._import_path(path)

    @Slot()
    def _remove_skill(self) -> None:
        skill = self._current_skill()
        if skill is None:
            return
        name = skill.get("name") or skill["id"]
        answer = QMessageBox.question(
            self,
            "Remove skill",
            f"Remove {name}? This deletes the files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._client.busy:
            return
        self._client.remove_skill(str(skill["id"]))

    def _import_path(self, path: str) -> None:
        if not path:
            return
        if self._client.busy:
            self._import_queue.append(path)
            return
        self._client.import_skill(path)

    def _flush_queue(self) -> None:
        if self._import_queue and not self._client.busy:
            self._client.import_skill(self._import_queue.pop(0))

    def _current_skill(self) -> dict | None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._skills):
            return None
        return self._skills[row]

    @Slot(int)
    def _on_row_changed(self, row: int) -> None:
        if self._updating:
            return
        if row < 0 or row >= len(self._skills):
            self._preview.clear()
            self._remove_btn.setEnabled(False)
            return
        skill = self._skills[row]
        skill_id = str(skill["id"])
        self._viewed.add(skill_id)
        box = self._checkboxes.get(skill_id)
        if box is not None:
            box.setEnabled(True)
        self._preview.setPlainText(str(skill.get("body") or ""))
        self._remove_btn.setEnabled(not self._client.busy)

    def _on_toggled(self, skill_id: str, checked: bool) -> None:
        if self._updating:
            return
        if skill_id not in self._viewed or self._client.busy:
            box = self._checkboxes.get(skill_id)
            if box is not None:
                box.blockSignals(True)
                box.setChecked(not checked)
                box.blockSignals(False)
            return
        enabled = [sid for sid, box in self._checkboxes.items() if box.isChecked()]
        self._client.set_skills(enabled)

    def _apply_catalog(self, skills: list[dict]) -> None:
        selected = None
        current = self._current_skill()
        if current is not None:
            selected = current["id"]
        self._updating = True
        self._checkboxes.clear()
        self._list.clear()
        self._skills = list(skills)
        for skill in self._skills:
            skill_id = str(skill["id"])
            row = _SkillRow(skill)
            if skill_id in self._viewed:
                row.checkbox.setEnabled(True)
            row.toggled.connect(self._on_toggled)
            self._list.add_row(row)
            self._checkboxes[skill_id] = row.checkbox
        empty = not self._skills
        self._empty.setVisible(empty)
        self._list.setVisible(not empty)
        restore = -1
        if selected:
            for index, skill in enumerate(self._skills):
                if skill["id"] == selected:
                    restore = index
                    break
        self._updating = False
        if restore >= 0:
            self._list.setCurrentRow(restore)
        else:
            self._preview.clear()
            self._remove_btn.setEnabled(False)

    @Slot(object)
    def _on_result(self, result: AgentResult) -> None:
        if result.op not in _SKILL_OPS:
            return
        self._status.setText(result.message or "")
        self._apply_catalog(list(result.skills or []))
        self._flush_queue()

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        if message:
            self._status.setText(message)

    @Slot(bool)
    def _on_busy(self, busy: bool) -> None:
        self._add_btn.setEnabled(not busy)
        self._remove_btn.setEnabled(not busy and self._list.currentRow() >= 0)
        if not busy:
            self._flush_queue()

    def _disconnect_client(self) -> None:
        if not self._connected:
            return
        self._connected = False
        self._client.result_ready.disconnect(self._on_result)
        self._client.failed.disconnect(self._on_failed)
        self._client.busy_changed.disconnect(self._on_busy)
