from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStyle,
    QToolBar,
    QToolButton,
)

from vex_desktop.agent.qt import AgentClient
from vex_desktop.exporting import PRESETS, preset_label
from vex_desktop.platform_support import ffmpeg_path, is_linux, is_macos
from vex_desktop.protocol import AgentResult, ProgressEvent, ProjectSnapshot
from vex_desktop.ui.chat_pane import ChatPane
from vex_desktop.ui.chrome import titled_pane
from vex_desktop.ui.preview_pane import VIDEO_SUFFIXES, PreviewPane
from vex_desktop.ui.project_dialog import OpenProjectDialog
from vex_desktop.ui.settings_dialog import SettingsDialog
from vex_desktop.ui.timeline_pane import TimelinePane

_YOUTUBE_HINT = "https://www.youtube.com/watch?v="


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vex")
        self.resize(1440, 900)
        icon = QApplication.instance().windowIcon() if QApplication.instance() else None
        if icon is not None and not icon.isNull():
            self.setWindowIcon(icon)
        self._snapshot = ProjectSnapshot()
        self._export_actions: list[QAction] = []

        self._agent = AgentClient(self)
        self._agent.progress.connect(self._on_progress)
        self._agent.result_ready.connect(self._on_result)
        self._agent.failed.connect(self._on_failed)
        self._agent.busy_changed.connect(self._on_busy)

        self._preview = PreviewPane()
        self._chat = ChatPane()
        self._timeline = TimelinePane()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(titled_pane("PREVIEW", self._preview))
        splitter.addWidget(titled_pane("CHAT", self._chat))
        splitter.addWidget(titled_pane("TIMELINE", self._timeline))
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([720, 420, 300])
        self.setCentralWidget(splitter)

        self._preview.file_dropped.connect(self._open_source)
        self._chat.command_submitted.connect(self._on_command)
        self._timeline.undo_requested.connect(self._agent.undo)
        self._timeline.redo_requested.connect(self._agent.redo)

        self._build_menu()
        self._build_toolbar()
        self._update_status()
        self._chat.focus_input()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._agent.shutdown()
        super().closeEvent(event)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self._action("Open Video…", self._choose_video, QKeySequence.StandardKey.Open))
        file_menu.addAction(self._action("Open YouTube URL…", self._choose_youtube))
        file_menu.addAction(self._action("Open Project…", self._choose_project))
        file_menu.addSeparator()
        file_menu.addMenu(self._make_export_menu("&Export", remember=True))
        file_menu.addSeparator()
        file_menu.addAction(self._action("Settings…", self._open_settings))
        file_menu.addSeparator()
        file_menu.addAction(self._action("Quit", self.close, QKeySequence.StandardKey.Quit))

        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self._action("Undo", self._agent.undo, QKeySequence.StandardKey.Undo))
        edit_menu.addAction(self._action("Redo", self._agent.redo, QKeySequence.StandardKey.Redo))
        edit_menu.addAction(self._action("Cancel", self._agent.cancel, QKeySequence.StandardKey.Cancel))

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self._action("About", self._about))

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main")
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        style = self.style()
        open_act = self._action("Open Video", self._choose_video)
        open_act.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        bar.addAction(open_act)
        bar.addAction(self._action("YouTube", self._choose_youtube))
        bar.addAction(self._action("Project", self._choose_project))
        bar.addSeparator()
        export_button = QToolButton()
        export_button.setText("Export")
        export_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        export_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        export_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        export_button.setMenu(self._make_export_menu("Export"))
        bar.addWidget(export_button)
        bar.addSeparator()
        bar.addAction(self._action("Settings", self._open_settings))
        self.addToolBar(bar)

    def _make_export_menu(self, title: str, remember: bool = False) -> QMenu:
        menu = QMenu(title, self)
        for preset in PRESETS:
            action = QAction(preset_label(preset), self)
            action.setData(preset)
            action.triggered.connect(self._on_export_action)
            menu.addAction(action)
            if remember:
                self._export_actions.append(action)
        return menu

    def _action(self, text: str, slot, shortcut=None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action

    @Slot()
    def _choose_video(self) -> None:
        filters = " ".join(f"*{s}" for s in sorted(VIDEO_SUFFIXES))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            str(Path.home()),
            f"Video files ({filters})",
        )
        if path:
            self._open_source(path)

    @Slot()
    def _choose_youtube(self) -> None:
        url, ok = QInputDialog.getText(self, "Open YouTube URL", "URL:", text=_YOUTUBE_HINT)
        if ok and url.strip() and url.strip() != _YOUTUBE_HINT:
            self._open_source(url.strip())

    @Slot()
    def _choose_project(self) -> None:
        dialog = OpenProjectDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        project = dialog.selected_project()
        if not project:
            return
        if self._agent.backend_name == "core":
            self._open_source(project["project_id"])
        elif project.get("working_exists") and project.get("working_file"):
            self._open_source(str(project["working_file"]))
        else:
            self._open_source(project["project_id"])

    def open_source(self, source: str) -> None:
        self._open_source(source)

    def wait_idle(self, timeout_ms: int = 15000) -> bool:
        import time

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        deadline = time.monotonic() + timeout_ms / 1000
        saw_busy = self._agent.busy
        while time.monotonic() < deadline:
            if app is not None:
                app.processEvents()
            if self._agent.busy:
                saw_busy = True
            elif saw_busy or not self._agent.busy:
                if not self._agent.busy and saw_busy:
                    return True
            time.sleep(0.02)
        return not self._agent.busy

    @Slot(str)
    def _open_source(self, source: str) -> None:
        label = Path(source).name if Path(source).suffix else source
        self._chat.append_system(f"Opening {label}…")
        self._agent.load_project(source)

    @Slot(str)
    def _on_command(self, command: str) -> None:
        self._agent.process_command(command)

    @Slot()
    def _open_settings(self) -> None:
        dialog = SettingsDialog(
            self,
            provider=self._snapshot.provider,
            model=self._snapshot.model,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        dialog.save_secrets()
        provider, model = dialog.values()
        self._agent.set_config(provider, model)

    @Slot(object)
    def _on_progress(self, event: ProgressEvent) -> None:
        self._chat.set_progress(event.message)

    @Slot()
    def _on_export_action(self) -> None:
        action = self.sender()
        if not isinstance(action, QAction):
            return
        preset = str(action.data() or "")
        if preset:
            self._export_preset(preset)

    def _export_preset(self, preset: str) -> None:
        self._chat.append_system(f"Exporting {preset_label(preset)}…")
        self._agent.export(preset)

    @Slot(object)
    def _on_result(self, result: AgentResult) -> None:
        self._apply_snapshot(result.snapshot)
        if result.message:
            if result.op in {"process_command", "undo", "redo", "export"}:
                self._chat.append_agent(result.message)
            else:
                self._chat.append_system(result.message)
        if not result.success:
            return
        video = result.exported_path or result.new_video or result.snapshot.working_file
        if video and result.op in {"load_project", "process_command", "undo", "redo", "export"}:
            if not str(video).lower().endswith(".mp3"):
                self._preview.load(video)

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self._chat.append_system(message)

    @Slot(bool)
    def _on_busy(self, busy: bool) -> None:
        self._chat.set_busy(busy)
        self._update_status()

    def _apply_snapshot(self, snapshot: ProjectSnapshot) -> None:
        self._snapshot = snapshot
        self._timeline.apply_snapshot(snapshot)
        name = snapshot.project_name or "Vex"
        self.setWindowTitle(f"{name} — Vex")
        self._update_status()

    def _update_status(self) -> None:
        os_name = "macOS" if is_macos() else "Linux" if is_linux() else sys.platform
        ffmpeg = ffmpeg_path() or "ffmpeg not found"
        busy = "busy" if self._agent.busy else "idle"
        backend = self._snapshot.backend or self._agent.backend_name
        self.statusBar().showMessage(f"{os_name}  ·  {backend}  ·  {busy}  ·  {ffmpeg}")

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About Vex",
            "Vex Desktop Video Editor\n"
            "Linux and macOS · PySide6\n"
            "The window talks to a VexAgent service; FFmpeg and the LLM stay off the UI thread.",
        )
