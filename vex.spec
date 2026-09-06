# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "src" / "vex_desktop" / "ui" / "theme.qss"), "vex_desktop/ui"),
        (str(ROOT / "src" / "vex_desktop" / "ui" / "icon.png"), "vex_desktop/ui"),
        (str(ROOT / "assets" / "icon.png"), "assets"),
    ],
    hiddenimports=[
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPdf",
        "PySide6.QtQuick3D",
        "tkinter",
        "matplotlib",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Vex",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Vex",
)

app = BUNDLE(
    coll,
    name="Vex.app",
    icon=str(ROOT / "assets" / "icon.png"),
    bundle_identifier="com.drewpurdy.vex",
    info_plist={
        "CFBundleName": "Vex",
        "CFBundleDisplayName": "Vex Desktop Video Editor",
        "NSHighResolutionCapable": True,
    },
)
