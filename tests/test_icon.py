from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from PySide6.QtGui import QImage


def test_packaged_icon_is_512px():
    path = Path(str(files("vex_desktop.ui").joinpath("icon.png")))
    assert path.is_file()
    image = QImage(str(path))
    assert not image.isNull()
    assert image.width() == 512
    assert image.height() == 512


def test_assets_icon_matches_package():
    from vex_desktop.platform_support import repo_root

    assets = repo_root() / "assets" / "icon.png"
    packaged = Path(str(files("vex_desktop.ui").joinpath("icon.png")))
    assert assets.is_file()
    assert assets.read_bytes() == packaged.read_bytes()


def test_application_sets_window_icon():
    from vex_desktop.app import create_application

    app = create_application([])
    icon = app.windowIcon()
    assert icon is not None
    assert not icon.isNull()
