from __future__ import annotations

import os
import subprocess
import sys
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


def test_spec_macos_bundle_has_icon_and_version():
    spec = (ROOT / "vex.spec").read_text(encoding="utf-8")
    assert 'name="Vex.app"' in spec
    assert 'bundle_identifier="com.drewpurdy.vex"' in spec
    assert 'ROOT / "assets" / "icon.png"' in spec
    assert "CFBundleShortVersionString" in spec
    assert "public.app-category.video" in spec


def test_build_dmg_script_is_macos_only():
    script = ROOT / "scripts" / "build_dmg.sh"
    text = script.read_text(encoding="utf-8")
    assert script.is_file()
    assert "create-dmg" in text
    assert "dist/Vex.dmg" in text
    assert "dist/Vex.app" in text
    assert "Darwin" in text
    if sys.platform != "darwin":
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        assert result.returncode == 1
        assert "macOS-only" in (result.stderr + result.stdout)


def test_macos_ci_writes_dist_dmg():
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    assert "macos-14" in workflow
    assert "scripts/build_dmg.sh" in workflow
    assert "dist/Vex.dmg" in workflow
    assert "Skipping notarization" in workflow
    assert "|| true" not in workflow


def test_tag_release_attaches_appimage_dmg_and_checksums():
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    assert "needs: [build-linux, build-macos]" in workflow
    assert "Vex-x86_64.AppImage" in workflow
    assert "Vex.dmg" in workflow
    assert "SHA256SUMS" in workflow
    assert "softprops/action-gh-release@v2" in workflow
    assert "fail_on_unmatched_files: true" in workflow
    assert workflow.count("action-gh-release") == 1
