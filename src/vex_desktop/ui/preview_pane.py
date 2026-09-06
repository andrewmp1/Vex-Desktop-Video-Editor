from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


class PreviewPane(QWidget):
    file_dropped = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._path: str | None = None

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)

        self._video = QVideoWidget(self)
        self._video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._player.setVideoOutput(self._video)

        self._placeholder = QLabel("Drop a video here\nor File → Open Video / Open YouTube")
        self._placeholder.setObjectName("placeholderLabel")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._placeholder)
        self._stack.addWidget(self._video)

        self._title = QLabel("No clip loaded")
        self._title.setObjectName("clipTitle")
        self._title.setWordWrap(True)

        self._play = QPushButton("Play")
        self._play.setEnabled(False)
        self._play.clicked.connect(self._toggle_play)

        self._position = QSlider(Qt.Orientation.Horizontal)
        self._position.setRange(0, 0)
        self._position.sliderMoved.connect(self._player.setPosition)

        self._time = QLabel("00:00 / 00:00")

        self._volume = QSlider(Qt.Orientation.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(80)
        self._volume.setFixedWidth(90)
        self._volume.valueChanged.connect(self._on_volume)
        self._audio.setVolume(0.8)

        transport = QHBoxLayout()
        transport.addWidget(self._play)
        transport.addWidget(self._position, stretch=1)
        transport.addWidget(self._time)
        transport.addWidget(QLabel("Vol"))
        transport.addWidget(self._volume)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.addWidget(self._title)
        layout.addWidget(self._stack, stretch=1)
        layout.addLayout(transport)

        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)

    @property
    def current_path(self) -> str | None:
        return self._path

    def load(self, path: str) -> None:
        file_path = Path(path)
        if not file_path.is_file():
            self._placeholder.setText(f"File not found:\n{path}")
            self._stack.setCurrentWidget(self._placeholder)
            self._play.setEnabled(False)
            return
        self._player.stop()
        self._path = str(file_path)
        self._title.setText(file_path.name)
        self._player.setSource(QUrl.fromLocalFile(self._path))
        self._stack.setCurrentWidget(self._video)
        self._play.setEnabled(True)
        self._player.play()

    def dragEnterEvent(self, event):  # noqa: N802
        if self._urls(event):
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        urls = self._urls(event)
        if urls:
            self.file_dropped.emit(urls[0])
            event.acceptProposedAction()

    def _urls(self, event) -> list[str]:
        if not event.mimeData().hasUrls():
            return []
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and Path(path).suffix.lower() in VIDEO_SUFFIXES:
                paths.append(path)
        return paths

    @Slot()
    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    @Slot(int)
    def _on_position(self, position: int) -> None:
        if not self._position.isSliderDown():
            self._position.setValue(position)
        self._time.setText(f"{_fmt(position)} / {_fmt(self._player.duration())}")

    @Slot(int)
    def _on_duration(self, duration: int) -> None:
        self._position.setRange(0, max(duration, 0))

    @Slot(QMediaPlayer.PlaybackState)
    def _on_state(self, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play.setText("Pause" if playing else "Play")

    @Slot(int)
    def _on_volume(self, value: int) -> None:
        self._audio.setVolume(value / 100.0)


def _fmt(ms: int) -> str:
    seconds = max(ms, 0) // 1000
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
