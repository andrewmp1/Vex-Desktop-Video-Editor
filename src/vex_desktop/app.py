from __future__ import annotations

import os
import sys
from importlib.resources import as_file, files

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from vex_desktop.ui.main_window import MainWindow


def configure_qt() -> None:
    os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")
    # Empty list = software decode. Qt otherwise tries VAAPI for AV1 even when
    # the GPU has no AV1 decoder (YouTube sources are often AV1).
    os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", ",")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def apply_theme(app: QApplication) -> None:
    app.setApplicationName("Vex")
    app.setOrganizationName("Drew Purdy")
    app.setStyle("Fusion")
    qss = files("vex_desktop.ui").joinpath("theme.qss").read_text(encoding="utf-8")
    app.setStyleSheet(qss)
    icon_ref = files("vex_desktop.ui").joinpath("icon.png")
    with as_file(icon_ref) as icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))


def create_application(argv: list[str] | None = None) -> QApplication:
    configure_qt()
    existing = QApplication.instance()
    if existing is not None:
        apply_theme(existing)
        return existing
    app = QApplication(argv if argv is not None else sys.argv)
    apply_theme(app)
    return app


def run() -> int:
    app = create_application()
    window = MainWindow()
    window.show()

    if os.environ.get("VEX_SMOKE_TEST"):
        QTimer.singleShot(1500, app.quit)

    return app.exec()
