from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desktop_file_is_appimage_ready():
    desktop = (ROOT / "packaging" / "vex.desktop").read_text(encoding="utf-8")
    assert desktop.startswith("[Desktop Entry]\n")
    assert "Type=Application" in desktop
    assert "Name=Vex" in desktop
    assert "Exec=Vex" in desktop
    assert "Icon=vex" in desktop
    assert "Categories=AudioVideo;Video;" in desktop
    assert "Terminal=false" in desktop


def test_build_appimage_script_wraps_pyinstaller_tree():
    script = ROOT / "scripts" / "build_appimage.sh"
    text = script.read_text(encoding="utf-8")
    assert script.is_file()
    assert "vex.spec" in text
    assert "appimagetool" in text
    assert "packaging/vex.desktop" in text
    assert "assets/icon.png" in text
    assert "_internal" in text
    assert "Vex-${ARCH}.AppImage" in text or 'Vex-${ARCH}.AppImage' in text
